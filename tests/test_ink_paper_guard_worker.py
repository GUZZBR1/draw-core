"""Guarda fotometrica pelo worker real (issue #129): mao sem mascara."""

import dataclasses
import time

import numpy as np

from draw.contracts import WarpedPage
from draw.ink import worker as worker_mod
from draw.ink.config import InkConfig

H, W = 256, 384
Q0 = np.array([(0, 0), (W, 0), (W, H), (0, H)], dtype=np.float32)
WITNESS = (slice(16, 112), slice(16, 160))  # ~13,8k px: passa o piso
COVERED = (slice(144, 208), slice(224, 336))
HAND = (slice(128, 224), slice(208, 352))


class _Scripted:
    threshold = 0.7

    def __init__(self):
        self.content = np.zeros((H, W), np.float32)

    def ink_prob(self, _warped):
        return self.content


def _paper():
    image = np.empty((H, W, 3), np.uint8)
    image[:] = (200, 205, 210)
    return image


def _prob(*, covered_ink=True, extra=None):
    prob = np.zeros((H, W), np.float32)
    prob[WITNESS] = 0.95
    if covered_ink:
        prob[COVERED] = 0.95
    if extra is not None:
        prob[extra] = 0.95
    return prob


def _pass(worker, generation, image):
    before = worker.stats()["passes_total"]
    worker.submit(WarpedPage(image, generation, Q0, np.ones((H, W), bool)))
    deadline = time.monotonic() + 5.0
    while worker.stats()["passes_total"] <= before:
        assert time.monotonic() < deadline, "a passada nao executou"
        time.sleep(0.001)


def _run(monkeypatch, config):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(worker_mod, "_IDLE_PROBE_SECONDS", 0.02)
    ink = _Scripted()
    worker = worker_mod.PageCleanWorker(ink, config=config).start()
    generation = worker.new_generation()
    ink.content = _prob()
    for _ in range(5):
        _pass(worker, generation, _paper())
    confirmed = worker.poll(generation, 0).confirmed
    assert confirmed[COVERED].all()
    return worker, ink, generation


def _no_idle_probe(monkeypatch):
    """Sem sonda ociosa: so as passadas submetidas votam (sem corrida)."""
    monkeypatch.setattr(worker_mod, "_IDLE_PROBE_SECONDS", 3600.0)
    time.sleep(0.1)


def _hand_image():
    image = _paper()
    image[HAND] = (60, 62, 64)  # mao/sombra escura que o MediaPipe nao viu
    return image


def test_unmasked_dark_hand_never_erases_confirmed_stroke(monkeypatch):
    worker, ink, generation = _run(monkeypatch, InkConfig())
    try:
        ink.content = _prob(covered_ink=False)
        for _ in range(14):
            _pass(worker, generation, _hand_image())
        snap = worker.poll(generation, 0)
        assert snap.confirmed[COVERED].all()
        assert snap.confirmed[WITNESS].all()
        # Mao sai, o traco continua la e tinta nova confirma.
        new = (slice(224, 240), slice(16, 120))
        ink.content = _prob(extra=new)
        for _ in range(12):
            _pass(worker, generation, _paper())
        snap = worker.poll(generation, 0)
        assert snap.confirmed[COVERED].all()
        assert snap.confirmed[new].all()
    finally:
        worker.stop()


def test_control_without_guard_erases_under_the_same_hand(monkeypatch):
    worker, ink, generation = _run(monkeypatch, InkConfig(paper_guard=False))
    try:
        ink.content = _prob(covered_ink=False)
        for _ in range(14):
            _pass(worker, generation, _hand_image())
        assert not worker.poll(generation, 0).confirmed[COVERED].any()
    finally:
        worker.stop()


def test_paper_really_erased_still_removes_with_guard(monkeypatch):
    worker, ink, generation = _run(monkeypatch, InkConfig())
    try:
        ink.content = _prob(covered_ink=False)
        for _ in range(14):
            _pass(worker, generation, _paper())
        snap = worker.poll(generation, 0)
        assert not snap.confirmed[COVERED].any()
        assert snap.confirmed[WITNESS].all()
    finally:
        worker.stop()


def test_black_frame_after_a_reference_freezes_instead_of_erasing(monkeypatch):
    worker, ink, generation = _run(monkeypatch, InkConfig())
    try:
        ink.content = _prob(covered_ink=False)
        black = np.zeros((H, W, 3), np.uint8)
        for _ in range(14):
            _pass(worker, generation, black)
        snap = worker.poll(generation, 0)
        assert snap.confirmed[COVERED].all()
    finally:
        worker.stop()


def test_post_exit_confirm_window_is_refunded_while_the_guard_freezes(monkeypatch):
    worker, ink, generation = _run(monkeypatch, InkConfig(post_exit_full_window=True))
    try:
        _no_idle_probe(monkeypatch)
        worker.set_hand_presence(True)
        # Traco novo sob a sombra: o que a espera pos-saida precisa.
        pending = (slice(130, 142), slice(212, 348))
        ink.content = _prob(covered_ink=False, extra=pending)
        worker.set_hand_presence(False)
        window = worker._post_exit_confirm_passes()
        assert window > 1
        for _ in range(2):
            _pass(worker, generation, _hand_image())
        # A guarda congelou as passadas pos-saida: a janela segue armada.
        assert worker._confirm_passes >= 1
        assert worker._confirm_masked_skips >= 1
    finally:
        worker.stop()


def test_stroke_finished_under_a_shadow_confirms_after_hand_exit_at_production(
    monkeypatch,
):
    """Producao pede 3 votos fortes pos-saida; a guarda segura a regiao por
    occlusion_hold_passes. O descanso nao pode chegar antes do traco."""
    # Hold maior que a janela de voto: a devolucao precisa cobrir o hold inteiro.
    config = dataclasses.replace(InkConfig.production(), occlusion_hold_passes=5)
    worker, ink, generation = _run(monkeypatch, config)
    try:
        for _ in range(14):  # pagina madura e parada: o descanso esta ao alcance
            _pass(worker, generation, _paper())
        worker.set_hand_presence(True)
        late = (slice(224, 240), slice(16, 120))
        ink.content = _prob(extra=late)
        shadow = _paper()
        shadow[(slice(208, 256), slice(0, 160))] = (60, 62, 64)
        for _ in range(4):
            _pass(worker, generation, shadow)
        assert not worker.poll(generation, 0).confirmed[late].any()
        worker.set_hand_presence(False)
        for _ in range(config.occlusion_hold_passes + 5):
            _pass(worker, generation, _paper())
        assert worker.poll(generation, 0).confirmed[late].all()
    finally:
        worker.stop()


def test_permanent_border_without_pending_ink_does_not_spend_refunds(monkeypatch):
    worker, ink, generation = _run(monkeypatch, InkConfig(post_exit_full_window=True))
    try:
        worker.set_hand_presence(True)
        worker.set_hand_presence(False)
        image = _paper()
        image[:, :64] = (60, 62, 64)  # borda escura permanente, sem tinta nela
        for _ in range(2):
            _pass(worker, generation, image)
        assert worker._confirm_masked_skips == 0
    finally:
        worker.stop()
