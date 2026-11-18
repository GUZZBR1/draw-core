"""F-11 Block 2: identidade por geracao no worker real, sem tracker paralelo."""

import numpy as np
import pytest

from draw.contracts import WarpedPage
from draw.ink import identity as identity_mod
from draw.ink import worker as worker_mod

SHAPE = (120, 100)
QUAD = np.float32([[0, 0], [100, 0], [100, 120], [0, 120]])


def page(other=False):
    prob = np.zeros(SHAPE, np.float32)
    prob[80:115, 65:95] = 0.95 if other else 0.0
    if not other:
        prob[10:65, 10:60] = 0.95
    return prob


class Model:
    threshold = 0.7

    def ink_prob(self, warped):
        return warped


@pytest.fixture
def worker(monkeypatch):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(worker_mod, "_IDLE_PROBE_SECONDS", 0)
    instance = worker_mod.PageCleanWorker(Model()).start()
    try:
        yield instance
    finally:
        instance.stop()


def drive(worker, generation, prob=None, corners=QUAD, visible=None):
    with worker._condition:
        before = worker._passes_total
        worker.submit(
            WarpedPage(page() if prob is None else prob, generation, corners, visible)
        )
        assert worker._condition.wait_for(
            lambda: worker._passes_total > before or worker._stopped, timeout=5
        ), "a passada nao executou"
        assert worker.error is None
        assert worker._passes_total == before + 1
    return worker.telemetry_snapshot()["records"][-1]


def settle(worker):
    generation = worker.new_generation()
    for _ in range(4):
        drive(worker, generation)
    canvas = worker.poll(generation, 0).confirmed
    np.testing.assert_array_equal(canvas > 0, page() > 0.7)
    return canvas


def last_event(worker):
    return worker.telemetry_snapshot()["page_identity_events"][-1]


def test_occlusion_defers_and_preserves_canvas(worker):
    canvas = settle(worker)
    anchor = worker._anchor_corners.copy()
    generation = worker.new_generation(preserve_identity=True)
    reference = worker._identity_reference
    for count in range(1, 4):
        record = drive(
            worker,
            generation,
            corners=QUAD + [30, 15],
            visible=np.zeros(SHAPE, bool),
        )
        event = last_event(worker)
        assert event["decision"] == "deferred_occlusion"
        assert event["quarantine_reason"] == "occlusion"
        assert event["deferred"] is True
        assert event["quarantine_frames"] == count
        assert record["page_identity_decision"] == event["decision"]
        assert record["quarantine_frames"] == count
        assert worker._identity_reference is reference
        assert worker._identity_recovery_requested
        np.testing.assert_array_equal(worker._anchor_corners, anchor)
        np.testing.assert_array_equal(worker._identity_reference_corners, anchor)
        np.testing.assert_array_equal(worker._accumulator._confirmed, canvas)
        np.testing.assert_array_equal(worker.poll(generation, 0).confirmed, canvas)

    drive(worker, generation)
    event = last_event(worker)
    assert event["decision"] == "same_page"
    assert event["deferred"] is False
    assert event["quarantine_frames"] == 0
    assert worker._identity_defer_count == 0
    assert worker._identity_reference is None
    assert worker._identity_reference_corners is None
    assert not worker._identity_recovery_requested
    np.testing.assert_array_equal(worker._anchor_corners, anchor)
    np.testing.assert_array_equal(worker.poll(generation, 0).confirmed, canvas)


def test_deferral_fields_declared_in_all_states(worker):
    # Recuperacao sem referencia tambem declara os campos de quarentena.
    generation = worker.new_generation(preserve_identity=True)
    drive(worker, generation)
    assert last_event(worker)["decision"] == "new_page"
    settle(worker)
    generation = worker.new_generation(preserve_identity=True)
    drive(worker, generation, visible=np.zeros(SHAPE, bool))
    assert last_event(worker)["decision"] == "deferred_occlusion"
    drive(worker, generation)
    assert last_event(worker)["decision"] == "same_page"
    generation = worker.new_generation(preserve_identity=True)
    for _ in range(2):
        drive(worker, generation, page(other=True))
        assert last_event(worker)["decision"] == "deferred_switch_consensus"
    drive(worker, generation, page(other=True))
    assert last_event(worker)["decision"] == "new_page"
    drive(worker, generation, page(other=True))
    assert worker.telemetry_snapshot()["records"][-1]["page_identity_decision"] is None
    for record in (
        worker.telemetry_snapshot()["records"]
        + worker.telemetry_snapshot()["page_identity_events"]
    ):
        assert "quarantine_reason" in record
        assert type(record["deferred"]) is bool
        assert type(record["quarantine_frames"]) is int


def test_legitimate_page_turn_commits(worker):
    canvas = settle(worker)
    anchor = worker._anchor_corners.copy()
    generation = worker.new_generation(preserve_identity=True)
    reference = worker._identity_reference
    for count in range(1, 3):
        drive(worker, generation, page(other=True))
        assert last_event(worker)["decision"] == "deferred_switch_consensus"
        assert worker._identity_switch_votes == count
        assert worker._identity_defer_count == 0
        assert worker._identity_reference is reference
        np.testing.assert_array_equal(worker._identity_reference_corners, anchor)
        np.testing.assert_array_equal(worker._anchor_corners, anchor)
        np.testing.assert_array_equal(worker.poll(generation, 0).confirmed, canvas)
    drive(worker, generation, page(other=True))
    event = last_event(worker)
    assert event["decision"] == "new_page"
    assert event["quarantine_frames"] == 0
    assert not event["deferred"]
    assert worker._identity_reference is None
    assert worker._identity_reference_corners is None
    assert not worker._identity_recovery_requested
    assert worker._identity_switch_votes == 0
    assert worker._identity_defer_count == 0
    for _ in range(3):
        drive(worker, generation, page(other=True))
    np.testing.assert_array_equal(
        worker.poll(generation, 0).confirmed > 0, page(other=True) > 0.7
    )


def test_switch_consensus_preserves_state_and_abstains(worker):
    canvas = settle(worker)
    anchor = worker._anchor_corners.copy()
    worker.set_hand_presence(False)
    generation = worker.new_generation(preserve_identity=True)
    reference = worker._identity_reference
    moved = QUAD + [3, -2]
    for count in range(1, 3):
        drive(worker, generation, page(other=True), corners=moved)
        assert last_event(worker)["decision"] == "deferred_switch_consensus"
        assert worker._identity_switch_votes == count
        assert worker._identity_defer_count == 0
        assert worker._identity_reference is reference
        assert worker._identity_recovery_requested
        np.testing.assert_array_equal(worker._identity_reference_corners, anchor)
        np.testing.assert_array_equal(worker._anchor_corners, anchor)
        np.testing.assert_array_equal(worker._accumulator._confirmed, canvas)
        np.testing.assert_array_equal(worker.poll(generation, 0).confirmed, canvas)
        assert not np.any(worker._accumulator._window[-1])
        with worker._condition:
            worker._generation_passes = worker_mod._REST_MIN_GENERATION_PASSES
            worker._quiet_passes = worker_mod._REST_QUIET_PASSES
            worker._confirm_once = False
            assert not worker._at_rest()
    drive(worker, generation, page(other=True), corners=moved)
    assert last_event(worker)["decision"] == "new_page"
    np.testing.assert_array_equal(worker._anchor_corners, moved)
    assert np.any(worker._accumulator._window[-1])
    assert not np.any(worker._accumulator._confirmed)


@pytest.mark.parametrize("blank", [False, True])
def test_switch_consensus_publishes_reset_canvas(worker, blank):
    settle(worker)
    generation = worker.new_generation(preserve_identity=True)
    candidate = np.zeros(SHAPE, np.float32) if blank else page(other=True)
    for _ in range(2):
        drive(worker, generation, candidate)
    version = worker.poll(generation, 0).version
    display_version = worker.poll_display(generation, 0).version
    publishes = worker.telemetry_snapshot()["publishes"]
    drive(worker, generation, candidate)
    assert last_event(worker)["decision"] == "new_page"
    published = worker.poll(generation, version)
    display = worker.poll_display(generation, display_version)
    assert published is not None
    assert display is not None
    assert not np.any(published.confirmed)
    assert not np.any(display.confirmed)
    np.testing.assert_array_equal(display.provisional > 0, candidate > 0.7)
    assert worker.telemetry_snapshot()["publishes"] == publishes + 1


def test_dirty_pass_breaks_switch_consensus(worker):
    settle(worker)
    generation = worker.new_generation(preserve_identity=True)
    reference = worker._identity_reference
    for _ in range(2):
        drive(worker, generation, page(other=True))
    assert worker._identity_switch_votes == 2
    drive(
        worker,
        generation,
        page(other=True),
        visible=np.zeros(SHAPE, bool),
    )
    assert last_event(worker)["decision"] == "deferred_occlusion"
    assert worker._identity_switch_votes == 0
    assert worker._identity_defer_count == 1
    for count in range(1, 3):
        drive(worker, generation, page(other=True))
        assert last_event(worker)["decision"] == "deferred_switch_consensus"
        assert worker._identity_switch_votes == count
        assert worker._identity_defer_count == 1
        assert worker._identity_reference is reference
    drive(worker, generation, page(other=True))
    assert last_event(worker)["decision"] == "new_page"
    assert worker._identity_switch_votes == 0
    assert worker._identity_defer_count == 0
    assert worker._identity_reference is None


def test_same_page_ends_pending_switch_without_consensus(worker):
    canvas = settle(worker)
    anchor = worker._anchor_corners.copy()
    generation = worker.new_generation(preserve_identity=True)
    drive(worker, generation, page(other=True))
    assert worker._identity_switch_votes == 1
    drive(worker, generation)
    assert last_event(worker)["decision"] == "same_page"
    assert worker._identity_switch_votes == 0
    assert worker._identity_reference is None
    np.testing.assert_array_equal(worker._anchor_corners, anchor)
    np.testing.assert_array_equal(worker.poll(generation, 0).confirmed, canvas)


def test_switch_consensus_telemetry_declares_deferral_fields(worker):
    settle(worker)
    generation = worker.new_generation(preserve_identity=True)
    for decision in (
        "deferred_switch_consensus",
        "deferred_switch_consensus",
        "new_page",
    ):
        record = drive(worker, generation, page(other=True))
        event = worker._identity_events[-1]
        assert event["decision"] == record["page_identity_decision"] == decision
        for entry in (event, record):
            assert entry["quarantine_frames"] == 0
            assert entry["quarantine_reason"] is None
            assert entry["deferred"] is False


@pytest.mark.parametrize("preserve", [False, True])
def test_new_generation_resets_switch_votes(worker, preserve):
    settle(worker)
    generation = worker.new_generation(preserve_identity=True)
    for _ in range(2):
        drive(worker, generation, page(other=True))
    assert worker._identity_switch_votes == 2
    generation = worker.new_generation(preserve_identity=preserve)
    assert worker._identity_switch_votes == 0
    drive(worker, generation, page(other=True))
    if preserve:
        assert last_event(worker)["decision"] == "deferred_switch_consensus"
        assert worker._identity_switch_votes == 1
    else:
        assert worker._identity_switch_votes == 0


def test_switch_consensus_does_not_spend_or_reset_quarantine_budget(worker):
    canvas = settle(worker)
    generation = worker.new_generation(preserve_identity=True)
    for count in range(1, identity_mod._PAGE_IDENTITY_MAX_DEFERRALS + 2):
        for _ in range(2):
            drive(worker, generation, page(other=True))
            assert last_event(worker)["decision"] == "deferred_switch_consensus"
            assert worker._identity_defer_count == count - 1
            np.testing.assert_array_equal(worker.poll(generation, 0).confirmed, canvas)
        drive(
            worker,
            generation,
            page(other=True),
            visible=np.zeros(SHAPE, bool),
        )
        assert worker._identity_switch_votes == 0
        assert last_event(worker)["quarantine_frames"] == count
        assert last_event(worker)["decision"] != "new_page"
    assert last_event(worker)["decision"] == "quarantine_timeout"
    assert worker._identity_reference is None
    assert worker._identity_defer_count == 0
    assert worker._identity_switch_votes == 0
    assert worker._anchor_corners is None


@pytest.mark.parametrize("limit", [None, 2])
def test_quarantine_timeout(worker, monkeypatch, limit):
    if limit is not None:
        monkeypatch.setattr(identity_mod, "_PAGE_IDENTITY_MAX_DEFERRALS", limit)
    maximum = identity_mod._PAGE_IDENTITY_MAX_DEFERRALS
    canvas = settle(worker)
    # A quarentena precisa continuar mesmo com a mao ausente e a saida quieta.
    worker.set_hand_presence(False)
    generation = worker.new_generation(preserve_identity=True)
    version = 0
    for count in range(1, maximum + 2):
        record = drive(
            worker,
            generation,
            page(other=True),
            visible=np.zeros(SHAPE, bool),
        )
        event = last_event(worker)
        assert event["quarantine_frames"] == count
        assert record["quarantine_frames"] == count
        assert event["quarantine_reason"] == "occlusion"
        assert event["decision"] != "new_page"
        assert event["deferred"] is True
        if count <= maximum:
            assert worker._identity_reference is not None
            _snap = worker.poll(generation, 0)
            version, published = _snap.version, _snap.confirmed
            np.testing.assert_array_equal(published, canvas)
    assert last_event(worker)["decision"] == "quarantine_timeout"
    assert worker._identity_reference is None
    assert worker._identity_reference_corners is None
    assert not worker._identity_recovery_requested
    assert worker._identity_defer_count == 0
    assert worker._anchor_corners is None
    lost_lock = worker.poll(generation, version)
    assert lost_lock is not None
    assert not np.any(lost_lock.confirmed)
    display = worker.poll_display(generation, 0)
    assert display is not None
    assert not np.any(display.confirmed)
    assert not np.any(display.provisional)
    assert worker.error is None
    for _ in range(4):
        drive(worker, generation, page(other=True))
    np.testing.assert_array_equal(worker._anchor_corners, QUAD)
    np.testing.assert_array_equal(
        worker.poll(generation, 0).confirmed > 0, page(other=True) > 0.7
    )
    assert last_event(worker)["decision"] == "quarantine_timeout"


@pytest.mark.parametrize("preserve", [False, True])
def test_new_generation_resets_quarantine_count(worker, preserve):
    settle(worker)
    generation = worker.new_generation(preserve_identity=True)
    drive(worker, generation, visible=np.zeros(SHAPE, bool))
    assert worker._identity_defer_count == 1
    generation = worker.new_generation(preserve_identity=preserve)
    assert worker._identity_defer_count == 0
    drive(worker, generation)
    assert worker._identity_defer_count == 0
    if preserve:
        assert last_event(worker)["decision"] == "same_page"


def test_source_change_keeps_confirmed_ink_and_reanchors_to_the_new_camera(worker):
    """Mesma pagina por outra camera: o canvas fica, a ancora vira a nova."""
    canvas = settle(worker)
    new_camera = QUAD * 2.0 + [320.0, 40.0]
    generation = worker.new_generation(preserve_identity=True, source_changed=True)
    drive(worker, generation, corners=new_camera)
    drive(worker, generation, corners=new_camera)
    assert last_event(worker)["decision"] == "same_page"
    np.testing.assert_array_equal(worker._anchor_corners, new_camera)
    np.testing.assert_array_equal(worker.poll(generation, 0).confirmed, canvas)
    for _ in range(3):
        drive(worker, generation, corners=new_camera)
    np.testing.assert_array_equal(worker.poll(generation, 0).confirmed, canvas)
    assert worker._identity_source_changed is False


def test_same_camera_recovery_still_registers_against_the_old_anchor(worker):
    """Sem source_changed o comportamento de queda do rastreador nao muda."""
    settle(worker)
    anchor = worker._anchor_corners.copy()
    generation = worker.new_generation(preserve_identity=True)
    assert worker._identity_source_changed is False
    drive(worker, generation)
    drive(worker, generation)
    assert last_event(worker)["decision"] == "same_page"
    np.testing.assert_array_equal(worker._anchor_corners, anchor)


def test_source_change_deferred_by_occlusion_does_not_vote_new_strokes(worker):
    """Mao cobrindo a tinta antiga: a folha nova nao entra no canvas confirmado."""
    canvas = settle(worker)
    new_camera = QUAD * 2.0 + [320.0, 40.0]
    generation = worker.new_generation(preserve_identity=True, source_changed=True)
    covered = np.ones(SHAPE, bool)
    covered[10:65, 10:60] = False
    other = page(other=True)
    for _ in range(identity_mod._PAGE_IDENTITY_MAX_DEFERRALS - 1):
        drive(worker, generation, other, corners=new_camera, visible=covered)
        assert last_event(worker)["decision"] == "deferred_occlusion"
        np.testing.assert_array_equal(worker.poll(generation, 0).confirmed, canvas)
        np.testing.assert_array_equal(worker._accumulator._confirmed, canvas)


def test_source_change_identity_trace_is_not_marked_as_geometrically_registered(
    worker,
):
    settle(worker)
    new_camera = QUAD * 2.0 + [320.0, 40.0]
    generation = worker.new_generation(preserve_identity=True, source_changed=True)
    drive(worker, generation, corners=new_camera)
    assert last_event(worker)["geometry_registered"] is False
    settle(worker)
    generation = worker.new_generation(preserve_identity=True)
    drive(worker, generation)
    assert last_event(worker)["geometry_registered"] is True


def test_source_hold_passes_do_not_count_toward_rest(worker):
    """A janela de voto so enche com passadas elegiveis depois da troca."""
    settle(worker)
    new_camera = QUAD * 2.0 + [320.0, 40.0]
    generation = worker.new_generation(preserve_identity=True, source_changed=True)
    covered = np.ones(SHAPE, bool)
    covered[10:65, 10:60] = False
    for _ in range(3):
        drive(worker, generation, corners=new_camera, visible=covered)
        assert last_event(worker)["decision"] == "deferred_occlusion"
        assert worker._generation_passes == 0
        assert worker._quiet_passes == 0
    drive(worker, generation, corners=new_camera)
    assert last_event(worker)["decision"] == "same_page"
    assert worker._generation_passes == 1
    assert worker._generation_passes < worker_mod._REST_MIN_GENERATION_PASSES
