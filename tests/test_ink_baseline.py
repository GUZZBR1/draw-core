"""Referencia inicial da tinta (#130) sobre o PageModel: prontidao e re-zero.

A supressao do conteudo pre-existente e o PageModel (draw.ink.page_model,
coberta em tests/test_page_model.py). Aqui: o estado que a interface le e
a tecla z, que faz o conteudo a vista virar a nova referencia.
"""

import time

import numpy as np

from draw.contracts import InkBaselineState, WarpedPage
from draw.ink import worker as worker_mod
from draw.ink.config import InkConfig

H, W = 96, 128
PAPER = 235.0
INK = 40.0
Q0 = np.array([(0, 0), (W, 0), (W, H), (0, H)], dtype=np.float32)


class _ScriptInk:
    """Tinta alta onde o warp esta escuro (par imagem/prob consistente)."""

    threshold = 0.7

    def ink_prob(self, warped):
        gray = warped if warped.ndim == 2 else warped.mean(axis=2)
        return (gray < 100).astype(np.float32) * 0.95


def _bgr(gray):
    return np.stack([gray] * 3, axis=-1).astype(np.uint8)


def _drive(worker, generation, image, visible=None):
    before = worker.stats()["passes_total"]
    worker.submit(WarpedPage(_bgr(image), generation, Q0, visible))
    deadline = time.monotonic() + 5.0
    while worker.stats()["passes_total"] <= before:
        if time.monotonic() > deadline:
            raise AssertionError("a passada nao executou")
        time.sleep(0.001)


def _confirmed(worker, generation):
    snap = worker.poll(generation, 0)
    return np.zeros((H, W), dtype=np.uint8) if snap is None else snap.confirmed


def _paper():
    return np.full((H, W), PAPER, dtype=np.float32)


def test_baseline_disabled_without_page_model():
    worker = worker_mod.PageCleanWorker(_ScriptInk(), config=InkConfig())
    assert worker.baseline_state() == InkBaselineState(False, False, 0.0, 0, "disabled")
    assert worker.rezero_baseline() is False


def test_baseline_state_goes_from_seeding_to_ready(monkeypatch):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = worker_mod.PageCleanWorker(
        _ScriptInk(), config=InkConfig(page_model=True)
    ).start()
    try:
        generation = worker.new_generation()
        assert worker.baseline_state().phase == "seeding"
        assert not worker.baseline_state().ready
        for _ in range(4):
            _drive(worker, generation, _paper())
        state = worker.baseline_state()
        assert state.phase == "ready"
        assert state.ready and state.pending_px == 0
        assert state.fraction == 1.0
    finally:
        worker.stop()


def test_baseline_state_is_partial_while_visible_area_is_pending(monkeypatch):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = worker_mod.PageCleanWorker(
        _ScriptInk(), config=InkConfig(page_model=True)
    ).start()
    try:
        generation = worker.new_generation()
        covered = np.ones((H, W), dtype=bool)
        covered[32:64, 32:64] = False  # mao sobre um bloco
        for _ in range(4):
            _drive(worker, generation, _paper(), covered)
        # Area coberta nao semeada: nao esta pronto, mesmo sem nada
        # visivel pendente — desenhar ali viraria referencia.
        state = worker.baseline_state()
        assert state.phase == "ready_partial"
        assert state.ready and state.pending_px > 0 and state.fraction < 1.0
        # A mao sai e o bloco semeia: so entao "ready".
        for _ in range(4):
            _drive(worker, generation, _paper())
        state = worker.baseline_state()
        assert state.phase == "ready" and state.pending_px == 0
    finally:
        worker.stop()


def test_rezero_clears_canvas_and_absorbs_current_content(monkeypatch):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = worker_mod.PageCleanWorker(
        _ScriptInk(), config=InkConfig(page_model=True)
    ).start()
    try:
        generation = worker.new_generation()
        image = _paper()
        for _ in range(3):
            _drive(worker, generation, image)
        image[50:60, 50:60] = INK  # traco novo depois da referencia
        for _ in range(4):
            _drive(worker, generation, image)
        assert np.count_nonzero(_confirmed(worker, generation)) == 100

        assert worker.rezero_baseline()
        assert worker.baseline_state().phase == "recapturing"
        _drive(worker, generation, image)
        # O canvas sai limpo na passada do re-zero...
        assert np.count_nonzero(_confirmed(worker, generation)) == 0
        assert worker.baseline_state().phase in ("seeding", "ready")
        for _ in range(6):
            _drive(worker, generation, image)
        # ...e o traco, agora parte da referencia, nao volta como tinta.
        assert np.count_nonzero(_confirmed(worker, generation)) == 0
        assert worker.baseline_state().phase == "ready"

        image[10:20, 10:20] = INK  # tinta nova depois do re-zero
        for _ in range(4):
            _drive(worker, generation, image)
        canvas = _confirmed(worker, generation)
        assert np.count_nonzero(canvas) == 100
        assert np.all(canvas[10:20, 10:20])
    finally:
        worker.stop()


def _worker_pm(**overrides):
    return worker_mod.PageCleanWorker(
        _ScriptInk(), config=InkConfig(page_model=True, **overrides)
    ).start()


def test_rezero_keeps_canvas_until_a_pass_has_usable_paper(monkeypatch):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker_pm()
    try:
        generation = worker.new_generation()
        image = _paper()
        for _ in range(3):
            _drive(worker, generation, image)
        image[50:60, 50:60] = INK
        for _ in range(4):
            _drive(worker, generation, image)
        before = _confirmed(worker, generation).copy()
        assert np.count_nonzero(before) == 100

        assert worker.rezero_baseline()
        blind = np.zeros((H, W), dtype=bool)  # nada a vista (sombra/mao)
        for _ in range(3):
            _drive(worker, generation, image, blind)
        # Sem papel utilizavel: o pedido segue pendente e o canvas fica.
        assert worker.baseline_state().phase == "recapturing"
        assert np.array_equal(_confirmed(worker, generation), before)

        _drive(worker, generation, image)
        assert np.count_nonzero(_confirmed(worker, generation)) == 0
    finally:
        worker.stop()


def test_worker_stays_awake_until_rezero_seeding_finishes(monkeypatch):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker_pm()
    try:
        generation = worker.new_generation()
        for _ in range(8):
            _drive(worker, generation, _paper())
        assert worker.rezero_baseline()
        assert not worker._at_rest()
        _drive(worker, generation, _paper())
        # Modelo novo, ainda sem semear: a pagina parada nao pode dormir.
        assert worker._pm_rezero_seeding
        assert not worker._at_rest()
        for _ in range(4):
            _drive(worker, generation, _paper())
        assert not worker._pm_rezero_seeding
        assert worker.baseline_state().phase == "ready"
    finally:
        worker.stop()


def test_new_generation_cancels_a_pending_rezero(monkeypatch):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker_pm()
    try:
        generation = worker.new_generation()
        _drive(worker, generation, _paper())
        assert worker.rezero_baseline()
        generation = worker.new_generation()
        assert not worker._pm_rezero_requested
        assert worker.baseline_state().phase != "recapturing"
        # A folha nova nao e re-zerada por um pedido da anterior.
        for _ in range(5):
            _drive(worker, generation, _paper())
        assert worker.baseline_state().phase == "ready"
    finally:
        worker.stop()


def test_erased_stroke_over_print_is_removed_from_canvas(monkeypatch):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(worker_mod.registration, "_REMOVAL_WITNESS_FLOOR_PX", 0)
    worker = _worker_pm()
    try:
        generation = worker.new_generation()
        printed = _paper()
        printed[20:30, 20:60] = 90.0  # guia impressa que ainda pontua como tinta
        for _ in range(4):
            _drive(worker, generation, printed)
        assert np.count_nonzero(_confirmed(worker, generation)) == 0

        drawn = printed.copy()
        drawn[24:26, 20:60] = 20.0  # traco escuro cruzando a guia
        drawn[50:60, 50:60] = 20.0  # desenho separado, em papel limpo
        for _ in range(5):
            _drive(worker, generation, drawn)
        canvas = _confirmed(worker, generation)
        assert np.all(canvas[24:26, 20:60]) and np.all(canvas[50:60, 50:60])

        for _ in range(14):  # apaga so o traco: a guia volta a aparencia semeada
            frame = printed.copy()
            frame[50:60, 50:60] = 20.0
            _drive(worker, generation, frame)
        canvas = _confirmed(worker, generation)
        assert not np.any(canvas[24:26, 20:60])
        assert np.all(canvas[50:60, 50:60])
    finally:
        worker.stop()
