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


def _submit_and_wait(
    worker,
    generation,
    *,
    stable=True,
    image=None,
    visible=None,
    coverage=None,
    corners=QUAD,
):
    if image is None:
        image = np.full((H, W, 3), 220, dtype=np.uint8)
    if visible is None:
        visible = np.ones((H, W), dtype=bool)
    if coverage is None:
        coverage = np.ones((H, W), dtype=bool)
    with worker._condition:
        before = worker._passes_total
        worker.submit(
            WarpedPage(
                image,
                generation,
                corners,
                visible=visible,
                coverage=coverage,
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


def test_new_stroke_adjacent_to_dark_baseline_mark_is_not_permanently_vetoed():
    config = InkConfig(baseline=True, baseline_margin_px=1, removal=False)
    accumulator = LayeredInkAccumulator(config.seen_threshold, config)
    printed = np.zeros((H, W), dtype=np.float32)
    printed[20:22, 10:30] = 0.95
    visible = np.ones(printed.shape, dtype=bool)
    coverage = np.ones(printed.shape, dtype=bool)

    accumulator.add(
        printed,
        visible,
        baseline_capture=True,
        baseline_coverage=coverage,
    )

    adjacent = printed.copy()
    adjacent[19, 12:28] = 1.0  # pixel em branco adjacente dentro da margem de 1 px
    for _ in range(3):
        result = accumulator.add(
            adjacent,
            visible,
            baseline_capture=True,
            baseline_coverage=coverage,
        )
    assert np.all(result["confirmed"][19, 12:28] > 0)
    assert not np.any(result["confirmed"][20:22, 10:30])


def test_removal_works_in_coverage_gap_for_confirmed_ink():
    config = InkConfig(baseline=True, removal=True)
    accumulator = LayeredInkAccumulator(config.seen_threshold, config)
    visible = np.ones((H, W), dtype=bool)
    full_coverage = np.ones((H, W), dtype=bool)
    blank = np.zeros((H, W), dtype=np.float32)

    accumulator.add(
        blank,
        visible,
        baseline_capture=True,
        baseline_coverage=full_coverage,
    )

    drawing = blank.copy()
    drawing[5:35, 10:12] = 0.95
    drawing[5:35, 30:36] = 0.95  # testemunha retida fora da lacuna (>= 65% do canvas)
    for _ in range(3):
        result = accumulator.add(
            drawing,
            visible,
            removal_allowed=True,
            baseline_capture=True,
            baseline_coverage=full_coverage,
        )
    assert np.any(result["confirmed"][5:35, 10:12])

    erased = drawing.copy()
    erased[5:35, 10:12] = 0.0
    gapped_coverage = full_coverage.copy()
    gapped_coverage[:, :20] = False  # segmentador deixa de cobrir o traco apagado
    for _ in range(6):
        result = accumulator.add(
            erased,
            visible,
            removal_allowed=True,
            baseline_capture=True,
            baseline_coverage=gapped_coverage,
        )
    assert not np.any(result["confirmed"][5:35, 10:12])
    assert np.any(result["confirmed"][5:35, 30:36])


def test_recovery_keeps_small_sketch_on_large_preprinted_form(monkeypatch):
    """Impressao dominante fora do rabisco nao derruba a identidade: a
    referencia guarda impressao + caligrafia, igual ao que a camera ve.

    Uma copia limpa do MESMO formulario continua casando (o impresso
    domina o recall), exatamente como sem baseline, onde o impresso e
    tinta confirmada — limitacao da identidade por conteudo, nao do
    baseline.
    """
    from draw.ink import worker as worker_module

    monkeypatch.setattr(worker_module, "_PAGE_CLEAN_INTERVAL_SECONDS", 0)
    config = InkConfig(
        baseline=True,
        removal=False,
        anchor_arbitration=False,
        anchor_follow=False,
    )
    printed = np.zeros((H, W), dtype=np.float32)
    # Marca impressa grande (> 70% dos pixels totais com tinta)
    printed[8:12, 4:44] = 0.95
    printed[40:44, 4:44] = 0.95
    model = _MutablePageClean(printed.copy())
    worker = PageCleanWorker(model, config=config).start()
    generation = worker.new_generation()
    _submit_and_wait(worker, generation)

    # Rabisco pequeno do usuario (~10% da tinta total)
    drawing = printed.copy()
    drawing[20:28, 22:25] = 0.95
    model.prob = drawing
    for _ in range(3):
        _submit_and_wait(worker, generation)
    saved_canvas = worker.poll(generation, 0).confirmed.copy()
    assert np.any(saved_canvas)

    # Mesma folha volta: mesmo com marca impressa dominante, o rabisco sobrevive.
    same_gen = worker.new_generation(preserve_identity=True)
    _submit_and_wait(worker, same_gen)
    assert np.array_equal(worker.poll(same_gen, 0).confirmed, saved_canvas)
    assert (
        worker.telemetry_snapshot()["page_identity_events"][-1]["decision"]
        == "same_page"
    )
    # O baseline da folha sobrevive a identidade confirmada: a impressao
    # segue fora do canvas nas passadas seguintes.
    for _ in range(3):
        _submit_and_wait(worker, same_gen)
    assert np.array_equal(worker.poll(same_gen, 0).confirmed, saved_canvas)
    assert not np.any(worker.poll(same_gen, 0).confirmed[8:12, 4:44])
    worker.stop()


def test_rezero_waits_for_paper_guard_eligible_pass(monkeypatch):
    from draw.ink import worker as worker_module

    monkeypatch.setattr(worker_module, "_PAGE_CLEAN_INTERVAL_SECONDS", 0)
    h_pg, w_pg = 64, 64
    quad_pg = np.float32([[0, 0], [w_pg, 0], [w_pg, h_pg], [0, h_pg]])
    prob_h = np.zeros((h_pg, w_pg), dtype=np.float32)
    prob_h[20:22, 5:55] = 0.95
    prob_v = prob_h.copy()
    prob_v[5:59, 24:26] = 0.95

    config = InkConfig(
        baseline=True,
        paper_guard=True,
        occlusion_hold_passes=2,
        removal=False,
        anchor_arbitration=False,
        anchor_follow=False,
    )
    paper_frame = np.full((h_pg, w_pg, 3), 220, dtype=np.uint8)
    shadow_frame = np.zeros((h_pg, w_pg, 3), dtype=np.uint8)
    model = _MutablePageClean(prob_h)
    worker = PageCleanWorker(model, config=config).start()
    generation = worker.new_generation()

    def submit_pg(image, *, stable=True):
        with worker._condition:
            before = worker._passes_total
            worker.submit(
                WarpedPage(
                    image,
                    generation,
                    quad_pg,
                    visible=np.ones((h_pg, w_pg), dtype=bool),
                    coverage=np.ones((h_pg, w_pg), dtype=bool),
                    baseline_stable=stable,
                )
            )
            assert worker._condition.wait_for(
                lambda: worker._passes_total > before or worker._stopped, timeout=5
            )
            assert worker.error is None

    submit_pg(paper_frame)
    assert worker.baseline_state().complete

    model.prob = prob_v
    for _ in range(3):
        submit_pg(paper_frame)
    old_canvas = worker.poll(generation, 0).confirmed.copy()
    assert np.any(old_canvas)

    assert worker.rezero_baseline()
    # Quadro todo em sombra e rejeitado pela guarda de papel: canvas nao zera!
    submit_pg(shadow_frame)
    assert worker.baseline_state().phase == "recapturing"
    assert np.array_equal(worker.poll(generation, 0).confirmed, old_canvas)

    # Passadas de hold apos sombra ainda seguram; apos o hold, quadro claro conclui rezero.
    for _ in range(3):
        submit_pg(paper_frame)
    assert worker.baseline_state().complete
    assert not np.any(worker.poll(generation, 0).confirmed)
    worker.stop()


def test_worker_does_not_rest_while_baseline_has_zero_captured_pixels(monkeypatch):
    from draw.ink import worker as worker_module

    monkeypatch.setattr(worker_module, "_PAGE_CLEAN_INTERVAL_SECONDS", 0)
    h_pg, w_pg = 64, 64
    quad_pg = np.float32([[0, 0], [w_pg, 0], [w_pg, h_pg], [0, h_pg]])
    prob_h = np.zeros((h_pg, w_pg), dtype=np.float32)
    prob_h[20:22, 5:55] = 0.95
    config = InkConfig(
        baseline=True, paper_guard=True, occlusion_hold_passes=0, removal=False
    )
    model = _MutablePageClean(prob_h)
    worker = PageCleanWorker(model, config=config).start()
    generation = worker.new_generation()

    paper_frame = np.full((h_pg, w_pg, 3), 220, dtype=np.uint8)
    shadow_frame = np.zeros((h_pg, w_pg, 3), dtype=np.uint8)

    def submit_pg(image, *, stable=True):
        with worker._condition:
            before = worker._passes_total
            worker.submit(
                WarpedPage(
                    image,
                    generation,
                    quad_pg,
                    visible=np.ones((h_pg, w_pg), dtype=bool),
                    coverage=np.ones((h_pg, w_pg), dtype=bool),
                    baseline_stable=stable,
                )
            )
            assert worker._condition.wait_for(
                lambda: worker._passes_total > before or worker._stopped, timeout=5
            )
            assert worker.error is None

    # Primeira passada instavel com papel claro estabelece referencia fotometrica.
    submit_pg(paper_frame, stable=False)
    assert not worker.baseline_state().started

    # Passada estavel inteiramente em sombra: started=True, ready=False.
    submit_pg(shadow_frame, stable=True)
    assert worker.baseline_state().started
    assert not worker.baseline_state().ready

    worker.set_hand_presence(False)
    worker._generation_passes = 5
    worker._quiet_passes = 5
    worker._confirm_once = False
    assert not worker._at_rest()

    # Garante que uma passada clara subsequente captura sem precisar acordar por mao.
    submit_pg(paper_frame, stable=True)
    assert worker.baseline_state().ready
    worker.stop()


def test_recovery_keeps_partially_occluded_small_sketch(monkeypatch):
    """Rabisco < 32 px com a ponta sob o dedo: a quarentena nao
    pode exigir todos os pixels visiveis — o trecho exposto
    decide."""
    from draw.ink import worker as worker_module

    monkeypatch.setattr(worker_module, "_PAGE_CLEAN_INTERVAL_SECONDS", 0)
    config = InkConfig(
        baseline=True,
        removal=False,
        anchor_arbitration=False,
        anchor_follow=False,
    )
    printed = np.zeros((H, W), dtype=np.float32)
    printed[8:12, 4:44] = 0.95
    printed[40:44, 4:44] = 0.95
    model = _MutablePageClean(printed.copy())
    worker = PageCleanWorker(model, config=config).start()
    generation = worker.new_generation()
    _submit_and_wait(worker, generation)

    # Rabisco pequeno do usuario (24 px, ~10% da tinta total).
    drawing = printed.copy()
    drawing[20:28, 22:25] = 0.95
    model.prob = drawing
    for _ in range(3):
        _submit_and_wait(worker, generation)
    saved_canvas = worker.poll(generation, 0).confirmed.copy()
    assert np.any(saved_canvas)

    # A folha volta com um dedo sobre 4 px da ponta do rabisco:
    # exigir os 24 px visiveis adiava a decisao ate o timeout
    # apagar o desenho — o trecho exposto basta para decidir.
    same_gen = worker.new_generation(preserve_identity=True)
    occluded = np.ones((H, W), dtype=bool)
    occluded[24:28, 24] = False
    _submit_and_wait(worker, same_gen, visible=occluded)
    assert np.array_equal(worker.poll(same_gen, 0).confirmed, saved_canvas)
    assert (
        worker.telemetry_snapshot()["page_identity_events"][-1]["decision"]
        == "same_page"
    )
    worker.stop()


def test_confidence_drift_on_dark_print_does_not_confirm_unchanged_mark():
    config = InkConfig(baseline=True, removal=False)
    accumulator = LayeredInkAccumulator(config.seen_threshold, config)
    visible = np.ones((H, W), dtype=bool)
    coverage = np.ones((H, W), dtype=bool)
    printed = np.zeros((H, W), dtype=np.float32)
    printed[20:22, 5:43] = 0.995
    accumulator.add(
        printed,
        visible,
        baseline_capture=True,
        baseline_coverage=coverage,
    )

    # Drift de um centesimo na mesma linha impressa: nao e traco
    # novo — no pixel impresso a exigencia e reference + delta,
    # nao o proprio maximo capturado.
    drifted = printed.copy()
    drifted[20:22, 5:43] = 0.996
    for _ in range(4):
        result = accumulator.add(
            drifted,
            visible,
            baseline_capture=True,
            baseline_coverage=coverage,
        )
    assert not np.any(result["confirmed"])

    # O traco novo adjacente a impressao escura segue elegivel: o
    # teto de 0.99 vale para a margem dilatada, nao para o pixel
    # que ja era impressao.
    adjacent = drifted.copy()
    adjacent[19, 5:43] = 1.0
    for _ in range(3):
        result = accumulator.add(
            adjacent,
            visible,
            baseline_capture=True,
            baseline_coverage=coverage,
        )
    assert np.all(result["confirmed"][19, 5:43])
    assert not np.any(result["confirmed"][20:22, 5:43])


def test_baseline_recapture_uses_new_anchor_grid_after_reanchor(monkeypatch):
    """A recaptura roda na grade da ancora nova: a mascara de
    cobertura com falha distingue a grade velha da nova quando o
    follow re-registra a passada da troca."""
    from draw.ink import worker as worker_module

    monkeypatch.setattr(worker_module, "_PAGE_CLEAN_INTERVAL_SECONDS", 0)
    config = InkConfig(
        baseline=True,
        removal=False,
        anchor_arbitration=False,
        anchor_follow=True,
    )
    model = _MutablePageClean(_probability())
    worker = PageCleanWorker(model, config=config).start()
    generation = worker.new_generation()

    # Faixa fixa de fora-da-folha na camera: no quad deslocado a
    # lacuna da grade da ancora anda ~12 colunas para a esquerda.
    coverage = np.ones((H, W), dtype=bool)
    coverage[:, 30:38] = False
    for _ in range(4):
        _submit_and_wait(worker, generation, coverage=coverage)

    step_quad = QUAD + np.float32([12.0, 0.0])
    assert worker.rezero_baseline()
    reanchored = False
    for _ in range(6):
        _submit_and_wait(worker, generation, coverage=coverage, corners=step_quad)
        if worker._anchor_corners is not None and np.allclose(
            worker._anchor_corners, step_quad
        ):
            reanchored = True
            break
    assert reanchored

    # Na passada da re-ancoragem a cobertura sai na grade nova
    # (STEP): a lacuna fica em ~18:26 e o trecho 31:35 e coberto
    # — a mascara da grade velha teria a falha em 30:38.
    current = worker._accumulator._baseline_current_coverage
    assert not np.any(current[8:56, 19:25])
    assert np.all(current[8:56, 31:35])
    # A mascara registrada atualiza em qualquer add; o alvo da
    # captura so cresce quando a recaptura roda — prova de que a
    # grade nova alimentou o baseline, nao apenas a mascara.
    assert np.all(worker._accumulator._baseline_target[8:56, 31:35])
    worker.stop()


def test_recovery_keeps_partially_occluded_medium_sketch(monkeypatch):
    """Rabisco de 34 px com 4 px sob o dedo: o piso proporcional
    nao salta para 32 px exigidos logo acima da fronteira."""
    from draw.ink import worker as worker_module

    monkeypatch.setattr(worker_module, "_PAGE_CLEAN_INTERVAL_SECONDS", 0)
    config = InkConfig(
        baseline=True,
        removal=False,
        anchor_arbitration=False,
        anchor_follow=False,
    )
    printed = np.zeros((H, W), dtype=np.float32)
    printed[8:12, 4:44] = 0.95
    model = _MutablePageClean(printed.copy())
    worker = PageCleanWorker(model, config=config).start()
    generation = worker.new_generation()
    _submit_and_wait(worker, generation)

    # Rabisco de 34 px: 17 linhas x 2 colunas.
    drawing = printed.copy()
    drawing[20:37, 22:24] = 0.95
    model.prob = drawing
    for _ in range(3):
        _submit_and_wait(worker, generation)
    saved_canvas = worker.poll(generation, 0).confirmed.copy()
    assert np.any(saved_canvas)

    # 4 px sob o dedo: 30 visiveis — um piso absoluto de 32 px
    # adiaria a decisao ate o timeout; 25% de 34 pede so 8.
    same_gen = worker.new_generation(preserve_identity=True)
    occluded = np.ones((H, W), dtype=bool)
    occluded[33:37, 23] = False
    _submit_and_wait(worker, same_gen, visible=occluded)
    assert np.array_equal(worker.poll(same_gen, 0).confirmed, saved_canvas)
    assert (
        worker.telemetry_snapshot()["page_identity_events"][-1]["decision"]
        == "same_page"
    )
    worker.stop()


def test_crossing_stroke_over_dark_print_edge_confirms():
    """A exigencia no pixel impresso e contra a propria captura +
    delta e, em paralelo, contra o maximo da vizinhanca — sem
    segunda margem: o traco que cruza a borda de uma impressao
    escura nao fica vetado acima de 1.0."""
    config = InkConfig(baseline=True, removal=False)
    accumulator = LayeredInkAccumulator(config.seen_threshold, config)
    visible = np.ones((H, W), dtype=bool)
    coverage = np.ones((H, W), dtype=bool)
    printed = np.zeros((H, W), dtype=np.float32)
    printed[20:22, 5:43] = 0.95
    printed[22, 5:43] = 0.80
    accumulator.add(
        printed,
        visible,
        baseline_capture=True,
        baseline_coverage=coverage,
    )

    # O traco cruza a borda (0.80 -> 1.00): aumento local de 0.20
    # passa de delta, e 1.00 supera o maximo da vizinhanca (0.95).
    # Vizinhanca + delta pediria 1.10 — veto permanente.
    crossing = printed.copy()
    crossing[22, 5:43] = 1.0
    for _ in range(3):
        result = accumulator.add(
            crossing,
            visible,
            baseline_capture=True,
            baseline_coverage=coverage,
        )
    assert np.all(result["confirmed"][22, 5:43])
    # O nucleo segue suprimido: drift sobre a propria captura
    # escura continua insuficiente.
    assert not np.any(result["confirmed"][20:22, 5:43])


def test_recovery_keeps_stroke_confirmed_inside_print_guard(monkeypatch):
    """Traco confirmado dentro da guarda impressa: na volta da
    mesma folha ele vale como evidencia de caligrafia — supera a
    referencia salva, diferente da impressao inalterada."""
    from draw.ink import worker as worker_module

    monkeypatch.setattr(worker_module, "_PAGE_CLEAN_INTERVAL_SECONDS", 0)
    config = InkConfig(
        baseline=True,
        removal=False,
        anchor_arbitration=False,
        anchor_follow=False,
    )
    printed = np.zeros((H, W), dtype=np.float32)
    printed[20:24, 4:44] = 0.70
    model = _MutablePageClean(printed.copy())
    worker = PageCleanWorker(model, config=config).start()
    generation = worker.new_generation()
    _submit_and_wait(worker, generation)

    # Traco sobre a impressao fraca: aumento forte dentro da
    # guarda confirma como tinta do usuario.
    drawing = printed.copy()
    # 2x28 px: acima do piso absoluto de evidencia visivel da identidade.
    drawing[21:23, 10:38] = 0.98
    model.prob = drawing
    for _ in range(3):
        _submit_and_wait(worker, generation)
    saved_canvas = worker.poll(generation, 0).confirmed.copy()
    assert np.any(saved_canvas[21:23, 10:38])

    # A mesma folha volta: todo o traco esta dentro da guarda,
    # mas ainda supera a referencia — nao pode apagar o desenho.
    same_gen = worker.new_generation(preserve_identity=True)
    _submit_and_wait(worker, same_gen)
    assert np.array_equal(worker.poll(same_gen, 0).confirmed, saved_canvas)
    assert (
        worker.telemetry_snapshot()["page_identity_events"][-1]["decision"]
        == "same_page"
    )
    worker.stop()


def test_margin_drift_noise_does_not_confirm_ghost_ink():
    """A margem da guarda exige vizinhanca + delta: um drift de
    registro que relê a borda 0.82 sobre referencia 0.80 nao e
    tinta nova."""
    config = InkConfig(baseline=True, removal=False)
    accumulator = LayeredInkAccumulator(config.seen_threshold, config)
    visible = np.ones((H, W), dtype=bool)
    coverage = np.ones((H, W), dtype=bool)
    printed = np.zeros((H, W), dtype=np.float32)
    printed[20:23, 5:43] = 0.80
    accumulator.add(
        printed,
        visible,
        baseline_capture=True,
        baseline_coverage=coverage,
    )

    # A folha desloca 1 px: a margem passa a ler a borda da
    # impressao — 0.82 supera a referencia mas nao o delta.
    drifted = printed.copy()
    drifted[19, 5:43] = 0.82
    for _ in range(4):
        result = accumulator.add(
            drifted,
            visible,
            baseline_capture=True,
            baseline_coverage=coverage,
        )
    assert not np.any(result["confirmed"])


def test_crossing_stroke_at_098_clears_faint_edge_but_not_dark():
    """Fronteira do teto de 0.99: traco a 0.98 cruza a borda de
    impressao fraca (exigencia 0.95), mas nao a borda ao lado de
    impressao escura — la a guarda de registro segura em 0.99."""
    config = InkConfig(baseline=True, removal=False)
    visible = np.ones((H, W), dtype=bool)
    coverage = np.ones((H, W), dtype=bool)

    faint_acc = LayeredInkAccumulator(config.seen_threshold, config)
    faint = np.zeros((H, W), dtype=np.float32)
    faint[20:23, 5:43] = 0.80
    faint_acc.add(faint, visible, baseline_capture=True, baseline_coverage=coverage)
    crossing = faint.copy()
    crossing[22, 5:43] = 0.98
    for _ in range(3):
        result = faint_acc.add(
            crossing,
            visible,
            baseline_capture=True,
            baseline_coverage=coverage,
        )
    assert np.all(result["confirmed"][22, 5:43])

    dark_acc = LayeredInkAccumulator(config.seen_threshold, config)
    dark = np.zeros((H, W), dtype=np.float32)
    dark[20:22, 5:43] = 0.95
    dark[22, 5:43] = 0.80
    dark_acc.add(dark, visible, baseline_capture=True, baseline_coverage=coverage)
    crossing = dark.copy()
    crossing[22, 5:43] = 0.98
    for _ in range(4):
        result = dark_acc.add(
            crossing,
            visible,
            baseline_capture=True,
            baseline_coverage=coverage,
        )
    assert not np.any(result["confirmed"][22, 5:43])


def test_stroke_shifted_across_guard_boundary_recovers(monkeypatch):
    """Traco montado na fronteira da guarda dilatada (linhas
    27-28, dentro e fora) desloca 1 px para dentro com a folha:
    sem o realinhamento toda a evidencia cai na regiao mascarada
    e o recall zera; com ele a tinta volta a grade salva."""
    from draw.ink import worker as worker_module

    monkeypatch.setattr(worker_module, "_PAGE_CLEAN_INTERVAL_SECONDS", 0)
    config = InkConfig(
        baseline=True,
        removal=False,
        anchor_arbitration=False,
        anchor_follow=False,
    )
    # Impressao 20:24 -> guarda dilatada cobre 17:27; a linha 27
    # e a ultima dentro da guarda, a 28 a primeira fora.
    printed = np.zeros((H, W), dtype=np.float32)
    printed[20:24, 4:44] = 0.80
    model = _MutablePageClean(printed.copy())
    worker = PageCleanWorker(model, config=config).start()
    generation = worker.new_generation()
    _submit_and_wait(worker, generation)

    # Traco cruzando a fronteira: a linha 27 (dentro, 0.98 supera
    # a referencia 0.95 da margem) e a 28 (fora) confirmam.
    drawing = printed.copy()
    drawing[27:29, 22:26] = 0.98
    model.prob = drawing
    for _ in range(3):
        _submit_and_wait(worker, generation)
    saved_canvas = worker.poll(generation, 0).confirmed.copy()
    assert np.any(saved_canvas[27:29, 22:26])

    # A mesma folha volta registrada 1 px acima: o traco le nas
    # linhas 26-27 — todo dentro da guarda salva. Sem realinhar,
    # o pixel de referencia fora da guarda (28) fica sem
    # evidencia e a folha viraria pagina nova.
    shifted = np.zeros((H, W), dtype=np.float32)
    shifted[19:23, 4:44] = 0.80
    shifted[26:28, 22:26] = 0.98
    model.prob = shifted
    same_gen = worker.new_generation(preserve_identity=True)
    _submit_and_wait(worker, same_gen)
    assert (
        worker.telemetry_snapshot()["page_identity_events"][-1]["decision"]
        == "same_page"
    )
    worker.stop()


def test_stroke_shifted_into_guard_recovers(monkeypatch):
    """Sentido inverso: traco salvo logo fora da guarda (linha
    28) que desloca 1 px para dentro — a impressao deslocada nao
    pode esconder o rabisco real nem ser confundida com ele."""
    from draw.ink import worker as worker_module

    monkeypatch.setattr(worker_module, "_PAGE_CLEAN_INTERVAL_SECONDS", 0)
    config = InkConfig(
        baseline=True,
        removal=False,
        anchor_arbitration=False,
        anchor_follow=False,
    )
    printed = np.zeros((H, W), dtype=np.float32)
    printed[20:24, 4:44] = 0.80
    model = _MutablePageClean(printed.copy())
    worker = PageCleanWorker(model, config=config).start()
    generation = worker.new_generation()
    _submit_and_wait(worker, generation)

    # Traco fora da guarda salva (linha 28, a 4 px da impressao).
    drawing = printed.copy()
    drawing[28, 22:26] = 0.98
    model.prob = drawing
    for _ in range(3):
        _submit_and_wait(worker, generation)
    assert np.any(worker.poll(generation, 0).confirmed[28, 22:26])

    # Volta 1 px acima: o traco le na linha 27 — dentro da
    # guarda salva, onde `seen & ~prior_bl` o mascararia.
    shifted = np.zeros((H, W), dtype=np.float32)
    shifted[19:23, 4:44] = 0.80
    shifted[27, 22:26] = 0.98
    model.prob = shifted
    same_gen = worker.new_generation(preserve_identity=True)
    _submit_and_wait(worker, same_gen)
    assert (
        worker.telemetry_snapshot()["page_identity_events"][-1]["decision"]
        == "same_page"
    )
    worker.stop()
