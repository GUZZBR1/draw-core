"""Tara page-clean: tinta existente vira referencia, nao tinta nova."""

import numpy as np
import pytest

from draw.contracts import InkBaselineState, WarpedPage
from draw.ink.accumulator import LayeredInkAccumulator
from draw.ink.config import InkConfig
from draw.ink.worker import PageCleanWorker

H, W = 64, 48
QUAD = np.float32([[0, 0], [W, 0], [W, H], [0, H]])


def _probability(*, vertical=False):
    prob = np.zeros((H, W), dtype=np.float32)
    prob[20:22, 5:43] = 0.95
    if vertical:
        prob[5:59, 24:26] = 0.95
    return prob


def test_baseline_suppresses_existing_lines_but_keeps_new_crossing_stroke():
    config = InkConfig(baseline=True, removal=False)
    accumulator = LayeredInkAccumulator(config.seen_threshold, config)
    old = _probability()
    old[20:22, 5:43] = 0.75
    visible = np.ones(old.shape, dtype=bool)
    coverage = np.ones(old.shape, dtype=bool)

    first = accumulator.add(
        old,
        visible,
        baseline_capture=True,
        baseline_coverage=coverage,
    )
    assert first["confirmed_px"] == first["provisional_px"] == 0

    for _ in range(3):
        unchanged = accumulator.add(old, visible, baseline_coverage=coverage)
    assert unchanged["confirmed_px"] == unchanged["provisional_px"] == 0

    crossing = old.copy()
    crossing[5:59, 24:26] = 0.95
    for _ in range(3):
        result = accumulator.add(
            crossing,
            visible,
            baseline_capture=True,
            baseline_coverage=coverage,
        )
    confirmed = result["confirmed"] > 0
    assert np.any(confirmed[5:18, 24:26])
    assert np.any(confirmed[20:22, 24:26])
    assert np.any(confirmed[24:59, 24:26])
    assert not np.any(confirmed[20:22, :23])
    assert not np.any(confirmed[20:22, 27:])


def test_new_confidence_inside_baseline_contour_is_retained():
    config = InkConfig(baseline=True, removal=False)
    accumulator = LayeredInkAccumulator(config.seen_threshold, config)
    old = _probability()
    old[20:22, 5:43] = 0.72
    visible = np.ones(old.shape, dtype=bool)
    coverage = np.ones(old.shape, dtype=bool)
    accumulator.add(
        old,
        visible,
        baseline_capture=True,
        baseline_coverage=coverage,
    )

    stronger = old.copy()
    stronger[20:22, 23:27] = 0.98
    for _ in range(3):
        result = accumulator.add(
            stronger,
            visible,
            baseline_capture=True,
            baseline_coverage=coverage,
        )
    confirmed = result["confirmed"] > 0
    assert np.any(confirmed[20:22, 23:27])
    assert not np.any(confirmed[20:22, :23])
    assert not np.any(confirmed[20:22, 27:])


def test_occluded_region_waits_for_first_clean_observation():
    config = InkConfig(baseline=True, removal=False)
    accumulator = LayeredInkAccumulator(config.seen_threshold, config)
    old = _probability()
    visible = np.ones(old.shape, dtype=bool)
    visible[:, W // 2 :] = False
    coverage = np.ones(old.shape, dtype=bool)

    accumulator.add(
        old,
        visible,
        baseline_capture=True,
        baseline_coverage=coverage,
    )
    state = accumulator.baseline_state()
    assert state.ready
    assert not state.complete
    assert state.pending_px == H * (W // 2)

    # Um quadro nao aprovado nao captura nem deixa a area pendente votar.
    clear = np.ones(old.shape, dtype=bool)
    pending = accumulator.add(
        old,
        clear,
        baseline_capture=False,
        baseline_coverage=coverage,
    )
    assert pending["confirmed_px"] == pending["provisional_px"] == 0
    assert accumulator.baseline_state().pending_px == H * (W // 2)

    # Na primeira observacao limpa aprovada, a regiao pendente e capturada.
    captured = accumulator.add(
        old,
        clear,
        baseline_capture=True,
        baseline_coverage=coverage,
    )
    assert captured["confirmed_px"] == captured["provisional_px"] == 0
    assert accumulator.baseline_state().complete
    for _ in range(3):
        result = accumulator.add(old, clear, baseline_coverage=coverage)
    assert result["confirmed_px"] == result["provisional_px"] == 0


def test_baseline_expands_with_newly_recognized_page_coverage():
    config = InkConfig(baseline=True, removal=False)
    accumulator = LayeredInkAccumulator(config.seen_threshold, config)
    visible = np.ones((H, W), dtype=bool)
    coverage = np.zeros((H, W), dtype=bool)
    coverage[:, : W // 2] = True
    blank = np.zeros((H, W), dtype=np.float32)

    accumulator.add(
        blank,
        visible,
        baseline_capture=True,
        baseline_coverage=coverage,
    )
    assert accumulator.baseline_state().complete
    first_target_px = accumulator.baseline_state().target_px

    # A temporary coverage shrink doesn't discard captured target pixels.
    shrunk = accumulator.add(
        blank,
        visible,
        baseline_capture=True,
        baseline_coverage=np.zeros_like(coverage),
    )
    assert shrunk["confirmed_px"] == 0
    assert accumulator.baseline_state().target_px == first_target_px

    # Newly recognized paper is captured once, then later strokes can vote.
    full_coverage = np.ones((H, W), dtype=bool)
    expanded = accumulator.add(
        blank,
        visible,
        baseline_capture=True,
        baseline_coverage=full_coverage,
    )
    assert expanded["confirmed_px"] == 0
    assert accumulator.baseline_state().target_px == H * W
    assert accumulator.baseline_state().complete
    stroke = blank.copy()
    stroke[8:12, W // 2 + 8 : W // 2 + 28] = 0.95
    for _ in range(3):
        result = accumulator.add(
            stroke,
            visible,
            baseline_capture=True,
            baseline_coverage=full_coverage,
        )
    assert np.any(result["confirmed"][8:12, W // 2 + 8 : W // 2 + 28])


def test_faint_baseline_marks_do_not_accumulate_into_ink():
    config = InkConfig(baseline=True, removal=False)
    accumulator = LayeredInkAccumulator(config.seen_threshold, config)
    faint = np.zeros((H, W), dtype=np.float32)
    faint[20:22, 5:43] = 0.65
    visible = np.ones(faint.shape, dtype=bool)
    coverage = np.ones(faint.shape, dtype=bool)

    accumulator.add(
        faint,
        visible,
        baseline_capture=True,
        baseline_coverage=coverage,
    )
    for _ in range(4):
        result = accumulator.add(faint, visible, baseline_coverage=coverage)
    assert result["confirmed_px"] == result["provisional_px"] == 0

    stronger = faint.copy()
    stronger[20:22, 5:43] = 0.95
    for _ in range(3):
        result = accumulator.add(
            stronger,
            visible,
            baseline_capture=True,
            baseline_coverage=coverage,
        )
    assert np.any(result["confirmed"][20:22, 5:43])


def test_removing_new_stroke_over_baseline_mark_preserves_printed_mark():
    config = InkConfig(baseline=True, removal=True)
    accumulator = LayeredInkAccumulator(config.seen_threshold, config)
    visible = np.ones((H, W), dtype=bool)
    coverage = np.ones((H, W), dtype=bool)
    printed = np.zeros((H, W), dtype=np.float32)
    printed[20:22, 5:43] = 0.75
    accumulator.add(
        printed,
        visible,
        baseline_capture=True,
        baseline_coverage=coverage,
    )

    drawing = printed.copy()
    drawing[5:59, 24:26] = 0.95
    drawing[2:18, 2:20] = 0.95
    for _ in range(3):
        result = accumulator.add(
            drawing,
            visible,
            removal_allowed=True,
            baseline_capture=True,
            baseline_coverage=coverage,
        )
    assert np.any(result["confirmed"][5:59, 24:26])

    # Erasing the crossing returns those pixels to the printed probability.
    # The separate drawing remains visible as the removal witness.
    erased = drawing.copy()
    erased[5:59, 24:26] = printed[5:59, 24:26]
    for _ in range(6):
        result = accumulator.add(
            erased,
            visible,
            removal_allowed=True,
            baseline_capture=True,
            baseline_coverage=coverage,
        )
    assert not np.any(result["confirmed"][5:59, 24:26])
    assert not np.any(result["confirmed"][20:22, 5:43])


def test_live_stroke_over_baseline_mark_survives_non_capture_passes():
    config = InkConfig(baseline=True, removal=True)
    accumulator = LayeredInkAccumulator(config.seen_threshold, config)
    visible = np.ones((H, W), dtype=bool)
    coverage = np.ones((H, W), dtype=bool)
    printed = np.zeros((H, W), dtype=np.float32)
    printed[20:22, 5:43] = 0.75
    accumulator.add(
        printed,
        visible,
        baseline_capture=True,
        baseline_coverage=coverage,
    )

    drawing = printed.copy()
    drawing[5:59, 24:26] = 0.95
    drawing[2:18, 2:20] = 0.95
    for _ in range(3):
        result = accumulator.add(
            drawing,
            visible,
            removal_allowed=True,
            baseline_capture=True,
            baseline_coverage=coverage,
        )
    assert np.any(result["confirmed"][5:59, 24:26])

    # Passadas sem captura (instavel) nao avaliam o override de mudanca:
    # a ausencia so conta quando a prob volta ao nivel da referencia.
    for _ in range(6):
        result = accumulator.add(
            drawing,
            visible,
            removal_allowed=True,
            baseline_capture=False,
            baseline_coverage=coverage,
        )
    assert np.all(result["confirmed"][5:59, 24:26])
    assert np.all(result["confirmed"][2:18, 2:20])
    on_mark = result["confirmed"][20:22] > 0
    assert np.count_nonzero(on_mark) == 4
    assert np.all(on_mark[:, 24:26])


class _MutablePageClean:
    threshold = 0.7

    def __init__(self, prob):
        self.prob = prob

    def ink_prob(self, _warped):
        return self.prob


def _submit_and_wait(worker, generation, *, stable=True):
    image = np.zeros((H, W, 3), dtype=np.uint8)
    with worker._condition:
        before = worker._passes_total
        worker.submit(
            WarpedPage(
                image,
                generation,
                QUAD,
                visible=np.ones((H, W), dtype=bool),
                coverage=np.ones((H, W), dtype=bool),
                baseline_stable=stable,
            )
        )
        assert worker._condition.wait_for(
            lambda: worker._passes_total > before or worker._stopped, timeout=5
        )
        assert worker.error is None


def test_worker_manual_rezero_clears_canvas_and_uses_current_content_as_reference(
    monkeypatch,
):
    from draw.ink import worker as worker_module

    monkeypatch.setattr(worker_module, "_PAGE_CLEAN_INTERVAL_SECONDS", 0)
    config = InkConfig(
        baseline=True,
        removal=False,
        anchor_arbitration=False,
        anchor_follow=False,
    )
    model = _MutablePageClean(_probability())
    worker = PageCleanWorker(model, config=config).start()
    generation = worker.new_generation()

    _submit_and_wait(worker, generation, stable=False)
    assert not worker.baseline_state().started
    assert not np.any(worker.poll(generation, 0).confirmed)

    _submit_and_wait(worker, generation)
    assert isinstance(worker.baseline_state(), InkBaselineState)
    assert worker.baseline_state().complete
    assert not np.any(worker.poll(generation, 0).confirmed)

    model.prob = _probability(vertical=True)
    for _ in range(3):
        _submit_and_wait(worker, generation)
    previous = worker.poll(generation, 0).confirmed > 0
    assert np.any(previous)

    assert worker.rezero_baseline()
    assert worker.baseline_state().phase == "recapturing"
    old_canvas = worker.poll(generation, 0).confirmed.copy()
    _submit_and_wait(worker, generation, stable=False)
    assert worker.baseline_state().phase == "recapturing"
    assert np.array_equal(worker.poll(generation, 0).confirmed, old_canvas)
    _submit_and_wait(worker, generation)
    assert worker.baseline_state().complete
    rezeroed = worker.poll(generation, 0)
    assert rezeroed is not None
    assert not np.any(rezeroed.confirmed)

    for _ in range(3):
        _submit_and_wait(worker, generation)
    assert not np.any(worker.poll(generation, 0).confirmed)
    worker.stop()


def test_recovery_matches_preprinted_page_and_switches_when_page_changes(monkeypatch):
    from draw.ink import worker as worker_module

    monkeypatch.setattr(worker_module, "_PAGE_CLEAN_INTERVAL_SECONDS", 0)
    config = InkConfig(
        baseline=True,
        removal=False,
        anchor_arbitration=False,
        anchor_follow=False,
    )
    printed = _probability()
    model = _MutablePageClean(printed.copy())
    worker = PageCleanWorker(model, config=config).start()
    generation = worker.new_generation()
    _submit_and_wait(worker, generation)
    assert worker.baseline_state().complete

    drawing = printed.copy()
    drawing[5:59, 24:26] = 0.95
    model.prob = drawing
    for _ in range(3):
        _submit_and_wait(worker, generation)
    saved_canvas = worker.poll(generation, 0).confirmed.copy()
    assert np.any(saved_canvas)

    recovered_generation = worker.new_generation(preserve_identity=True)
    _submit_and_wait(worker, recovered_generation)
    recovered = worker.poll(recovered_generation, 0).confirmed
    assert np.array_equal(recovered, saved_canvas)
    assert (
        worker.telemetry_snapshot()["page_identity_events"][-1]["decision"]
        == "same_page"
    )

    replacement = np.zeros_like(printed)
    replacement[8:10, 5:43] = 0.95
    model.prob = replacement
    replacement_generation = worker.new_generation(preserve_identity=True)
    for _ in range(4):
        _submit_and_wait(worker, replacement_generation)
        events = worker.telemetry_snapshot()["page_identity_events"]
        if events and events[-1]["decision"] == "new_page":
            break
    assert events[-1]["decision"] == "new_page"
    assert not np.any(worker.poll(replacement_generation, 0).confirmed)
    worker.stop()


def test_baseline_config_validates_margin_and_production_preset():
    with pytest.raises(ValueError, match="baseline_margin_px"):
        InkConfig(baseline_margin_px=5)
    assert InkConfig.production(baseline=True).baseline
