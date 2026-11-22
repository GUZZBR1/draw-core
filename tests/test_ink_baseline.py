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
        assert worker.baseline_state().phase == "ready"
        # A mao sai: o bloco aparece mas ainda nao tem referencia.
        _drive(worker, generation, _paper())
        state = worker.baseline_state()
        assert state.phase == "ready_partial"
        assert state.ready and state.pending_px > 0 and state.fraction < 1.0
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
