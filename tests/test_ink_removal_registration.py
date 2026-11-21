import cv2
import numpy as np
import pytest

import rr
from draw.contracts import WarpedPage
from draw.ink import accumulator as accumulator_mod
from draw.ink import occlusion as occlusion_mod
from draw.ink import registration as registration_mod
from draw.ink.config import InkConfig
from rr import _ProbIsWarp


def ink():
    prob = np.zeros((100, 120), np.float32)
    prob[15:45, 15:55] = 0.95
    prob[65:75, 65:85] = 0.95
    return prob


def _big_ink():
    prob = np.zeros((260, 400), np.float32)
    prob[10:190, 10:200] = 0.95  # ~34k px confirmados
    return prob


def confirmed(acc, prob):
    visible = np.ones(prob.shape, bool)
    for _ in range(16):
        result = acc.add(prob, visible, paper_exposed=visible)
    return result["confirmed"].copy()


def test_erasure_is_published_and_does_not_resurrect():
    acc = accumulator_mod.LayeredInkAccumulator()
    prob = ink()
    original = confirmed(acc, prob)
    erased = prob.copy()
    erased[65:75, 65:85] = 0
    visible = np.ones(prob.shape, bool)
    for _ in range(registration_mod._REMOVAL_PASSES - 1):
        result = acc.add(erased, visible, paper_exposed=visible)
        np.testing.assert_array_equal(result["confirmed"], original)
    result = acc.add(erased, visible, paper_exposed=visible)
    assert result["confirmed_changed"] and result["removed_confirmed_px"] == 200
    for _ in range(20):
        result = acc.add(erased, visible, paper_exposed=visible)
        assert not result["confirmed"][65:75, 65:85].any()
        assert not result["provisional"][65:75, 65:85].any()
    assert np.all(result["confirmed"][15:45, 15:55] == 255)
    confirmed(acc, prob)
    assert np.all(acc._confirmed[65:75, 65:85] == 255)  # redraw still works


@pytest.mark.parametrize(
    "mode", ["occlusion", "no_visibility", "turn", "registration", "flicker"]
)
def test_negative_evidence_fails_closed(mode):
    acc = accumulator_mod.LayeredInkAccumulator()
    prob = ink()
    original = confirmed(acc, prob)
    erased = prob.copy()
    erased[65:75, 65:85] = 0
    visible = np.ones(prob.shape, bool)
    if mode == "occlusion":
        visible[65:75, 65:85] = False
    elif mode == "no_visibility":
        visible = None
    elif mode == "turn":
        erased[:] = 0
    for i in range(20):
        current = prob if mode == "flicker" and i % 2 else erased
        result = acc.add(
            current,
            visible,
            paper_exposed=visible,
            removal_allowed=mode != "registration",
        )
    np.testing.assert_array_equal(result["confirmed"], original)


def test_removal_off_is_byte_identical_and_monotone():
    acc = accumulator_mod.LayeredInkAccumulator(config=InkConfig(removal=False))
    original = confirmed(acc, ink())
    for _ in range(20):
        result = acc.add(np.zeros_like(ink()), np.ones(ink().shape, bool))
    np.testing.assert_array_equal(original, result["confirmed"])
    assert "removed_confirmed_px" not in result


def drive(sequence, config=None):
    clock = rr.SceneClock()
    worker = rr.make_ink_worker(_ProbIsWarp(), clock, config=config)
    gen = worker.new_generation()
    for prob, corners in sequence:
        clock.now += 1
        worker.submit(
            WarpedPage(
                prob,
                gen,
                corners,
                rr.camera_mask(np.ones(prob.shape, bool), corners),
            )
        )
        assert worker.pump()
        assert worker.error is None
    return worker


def test_live_telemetry_records_arbitration_config(monkeypatch):
    prob = ink()
    worker = drive(
        [(prob, rr.base_quad(prob.shape))] * 8,
        config=InkConfig(anchor_arbitration=False),
    )
    record = worker.telemetry_snapshot()["records"][-1]
    assert record["anchor_arbitration_enabled"] is False
    assert record["sequence"] == 8 and record["pass_gap_s"] == 1
    assert record["registration_is_identity"]
    assert "new_confirmed_px" in record and "removed_confirmed_px" in record


def test_worker_publishes_erasure_through_the_real_path():
    prob = ink()
    page = np.full((*prob.shape, 3), 220, dtype=np.uint8)
    erased = prob.copy()
    erased[65:75, 65:85] = 0

    class _MutablePageClean:
        threshold = 0.7

        def __init__(self):
            self.prob = prob

        def ink_prob(self, _image):
            return self.prob

    clock = rr.SceneClock()
    page_clean = _MutablePageClean()
    worker = rr.make_ink_worker(page_clean, clock)
    generation = worker.new_generation()
    corners = rr.base_quad(prob.shape)
    visible = np.ones((720, 1280), bool)
    for current in [prob] * 16 + [erased] * 10:
        page_clean.prob = current
        clock.now += 1
        worker.submit(WarpedPage(page, generation, corners, visible=visible))
        assert worker.pump()
        assert worker.error is None
    assert not worker._accumulator._confirmed[65:75, 65:85].any()
    assert np.all(worker._accumulator._confirmed[15:45, 15:55])
    records = worker.telemetry_snapshot()["records"]
    assert sum(r["removed_confirmed_px"] for r in records) == 200
    assert not worker._at_rest() or worker._accumulator._removal_streak.max() == 0


def test_erasure_advances_on_unobstructed_page_without_hand_mask():
    """Caminho clássico (detecção de folha sem modelo de mão): com a
    página à vista e a guarda confirmando papel, a remoção corre — o
    "sem bloco" fotométrico vira evidência de visibilidade, não buraco
    (Devin Review do PR #144)."""
    prob = ink()
    page = np.full((*prob.shape, 3), 220, dtype=np.uint8)
    erased = prob.copy()
    erased[65:75, 65:85] = 0

    class _MutablePageClean:
        threshold = 0.7

        def __init__(self):
            self.prob = prob

        def ink_prob(self, _image):
            return self.prob

    clock = rr.SceneClock()
    page_clean = _MutablePageClean()
    worker = rr.make_ink_worker(page_clean, clock)
    generation = worker.new_generation()
    corners = rr.base_quad(prob.shape)
    for current in [prob] * 16 + [erased] * 10:
        page_clean.prob = current
        clock.now += 1
        worker.submit(WarpedPage(page, generation, corners))
        assert worker.pump()
        assert worker.error is None
    assert not worker._accumulator._confirmed[65:75, 65:85].any()
    assert np.all(worker._accumulator._confirmed[15:45, 15:55])
    records = worker.telemetry_snapshot()["records"]
    assert sum(r["removed_confirmed_px"] for r in records) == 200


def test_worker_confirms_fill_after_sustained_ink_evidence():
    """E2E do preenchimento: depois que a referência do papel claro
    está de pé, uma área pintada de escuro confirma como tinta — a
    guarda para de vetar adições com a evidência sustentada, em vez
    de congelar a região para sempre (Devin Review do PR #144)."""
    shape = (120, 160)
    paper = np.full((*shape, 3), 220, dtype=np.uint8)
    filled = paper.copy()
    filled[24:96, 24:96] = 60
    prob_fill = np.zeros(shape, np.float32)
    prob_fill[24:96, 24:96] = 0.95

    class _MutablePageClean:
        threshold = 0.7

        def __init__(self):
            self.prob = np.zeros(shape, np.float32)

        def ink_prob(self, _image):
            return self.prob

    clock = rr.SceneClock()
    page_clean = _MutablePageClean()
    worker = rr.make_ink_worker(page_clean, clock)
    generation = worker.new_generation()
    corners = rr.base_quad(shape)

    def pass_page(image, prob):
        page_clean.prob = prob
        clock.now += 1
        worker.submit(WarpedPage(image, generation, corners))
        assert worker.pump()
        assert worker.error is None

    for _ in range(3):
        pass_page(paper, np.zeros(shape, np.float32))
    for _ in range(occlusion_mod._FILL_RECOVERY_PASSES - 1):
        pass_page(filled, prob_fill)
        assert not worker._accumulator._confirmed[24:96, 24:96].any()
    for _ in range(4):
        pass_page(filled, prob_fill)
    assert worker._accumulator._confirmed[24:96, 24:96].all()


def test_page_recovery_defers_when_shadow_covers_prior_ink():
    """O bloqueio fotométrico também rege o reencontro: a sombra que
    o detector de mão perdeu esconde a tinta anterior — a identidade
    adia em vez de condenar a página (Devin Review do PR #144)."""
    shape = (120, 160)
    paper = np.full((*shape, 3), 220, dtype=np.uint8)
    prob = np.zeros(shape, np.float32)
    prob[40:50, 60:140] = 0.95  # traço comprido dentro da futura sombra
    shadowed = paper.copy()
    shadowed[24:96, 48:144] = 60  # bloco 3x4 tiles sobre o traço
    dark = np.zeros(shape, np.float32)

    class _MutablePageClean:
        threshold = 0.7

        def __init__(self):
            self.prob = prob

        def ink_prob(self, _image):
            return self.prob

    clock = rr.SceneClock()
    page_clean = _MutablePageClean()
    worker = rr.make_ink_worker(page_clean, clock)
    generation = worker.new_generation()
    corners = rr.base_quad(shape)
    for _ in range(6):
        page_clean.prob = prob
        clock.now += 1
        worker.submit(WarpedPage(paper, generation, corners))
        assert worker.pump()
        assert worker.error is None

    generation = worker.new_generation(preserve_identity=True)
    page_clean.prob = dark
    clock.now += 1
    worker.submit(WarpedPage(shadowed, generation, corners))
    assert worker.pump()
    assert worker.error is None
    event = worker.telemetry_snapshot()["page_identity_events"][-1]
    assert event["decision"] == "deferred_occlusion"


def test_witness_floor_unblocks_stale_canvas():
    """retained < 65% mas >= piso: a testemunha existe e a remocao corre.

    O catch-22 medido no sim-hand: mais de ~35% do canvas velho e os
    proprios pixels errados impediam a fracao de existir — retained
    0,33% e a saida congelava com a folha limpa a vista. Com o piso,
    4k px de re-testemunho comprovam o modelo vivo e a evidencia
    negativa dele conta.
    """
    acc = accumulator_mod.LayeredInkAccumulator()
    prob = _big_ink()
    confirmed(acc, prob)
    _canvas = int((acc._confirmed > 0).sum())
    # Copia defasada: metade da tinta "some" (stale), metade segue.
    stale = prob.copy()
    stale[10:190, 10:110] = 0.0
    visible = np.ones(prob.shape, bool)
    # retained ~17k de ~34k = ~50% < 65% mas >= 4k -> testemunhada.
    for _ in range(registration_mod._REMOVAL_PASSES):
        acc.add(stale, visible, paper_exposed=visible)
    assert not acc._confirmed[10:190, 10:110].any()
    assert np.all(acc._confirmed[10:190, 110:200] == 255)


def test_witness_floor_keeps_total_darkness_closed():
    """Modelo escurecendo por inteiro segue vedado: nada de varredura."""
    acc = accumulator_mod.LayeredInkAccumulator()
    prob = _big_ink()
    original = confirmed(acc, prob)
    dark = np.zeros_like(prob)
    visible = np.ones(prob.shape, bool)
    for _ in range(2 * registration_mod._REMOVAL_PASSES):
        acc.add(dark, visible, paper_exposed=visible)
    np.testing.assert_array_equal(acc._confirmed > 0, original > 0)


def test_absence_streak_survives_unwitnessed_and_occlusion():
    """Passada sem testemunha ou pixel ocluido seguram o streak.

    A ausencia do F-10 precisa ser persistente, nao consecutiva:
    em cena real a testemunha oscila e a mao cobre a regiao —
    interromper a contagem a cada buraco congelava a copia
    defasada para sempre.
    """
    acc = accumulator_mod.LayeredInkAccumulator()
    prob = _big_ink()
    confirmed(acc, prob)
    stale = prob.copy()
    stale[10:190, 10:60] = 0.0  # regiao que vai ser removida
    visible = np.ones(prob.shape, bool)
    occluded = visible.copy()
    occluded[10:190, 10:60] = False
    for _ in range(3):
        acc.add(stale, visible, paper_exposed=visible)  # 3 testemunhadas ausentes
    acc.add(
        stale, visible, paper_exposed=visible, removal_allowed=False
    )  # sem info: segura
    acc.add(stale, occluded, paper_exposed=occluded)  # regiao ocluida: segura tambem
    assert (acc._confirmed > 0)[10:190, 10:60].any()
    for _ in range(registration_mod._REMOVAL_PASSES - 3):
        acc.add(stale, visible, paper_exposed=visible)  # completa as 6 testemunhadas
    assert not acc._confirmed[10:190, 10:60].any()
    assert np.all(acc._confirmed[10:190, 60:200] == 255)


def test_paper_exposure_guard_freezes_a_dark_block_when_hand_mask_misses():
    guard = occlusion_mod.PaperExposureGuard()
    baseline = np.full((120, 160, 3), 220, dtype=np.uint8)
    visible = np.ones(baseline.shape[:2], dtype=bool)

    baseline_assessment = guard.observe(baseline, visible)
    assert baseline_assessment.paper_exposed is True
    assert baseline_assessment.visible is None
    baseline_assessment = guard.observe(baseline, visible)
    assert baseline_assessment.paper_exposed is True
    assert baseline_assessment.visible is None
    shadow = baseline.copy()
    shadow[24:96, 24:96] = 75
    assessment = guard.observe(shadow, visible)  # visible=True simulates a miss

    assert not assessment.paper_exposed[50:65, 50:65].any()
    assert not assessment.visible[50:65, 50:65].any()
    assert assessment.paper_exposed[0:12, 0:12].all()
    baseline_assessment = guard.observe(baseline, visible)
    assert baseline_assessment.paper_exposed is True
    assert baseline_assessment.visible is None

    first_frame_guard = occlusion_mod.PaperExposureGuard()
    first_frame_hand = baseline.copy()
    first_frame_hand[24:96, 24:96] = 75
    first_frame_exposed = first_frame_guard.observe(first_frame_hand, visible)
    assert not first_frame_exposed.paper_exposed[30:60, 30:60].any()
    assert not first_frame_exposed.visible[30:60, 30:60].any()

    color_guard = occlusion_mod.PaperExposureGuard()
    baseline_assessment = color_guard.observe(baseline, visible)
    assert baseline_assessment.paper_exposed is True
    assert baseline_assessment.visible is None
    colored_object = baseline.copy()
    colored_object[24:96, 24:96] = (255, 200, 190)  # quase mesma luminância
    color_exposed = color_guard.observe(colored_object, visible)
    assert not color_exposed.visible[30:60, 30:60].any()


def test_global_dimming_is_absorbed_not_blocked():
    """Queda global de >20% (luz da sala, auto-exposição): as
    referências cedem ao nível novo — a página não congela atrás de
    um bloco único (Devin Review do PR #144)."""
    guard = occlusion_mod.PaperExposureGuard()
    bright = np.full((120, 160, 3), 220, dtype=np.uint8)
    visible = np.ones(bright.shape[:2], dtype=bool)
    assert guard.observe(bright, visible).paper_exposed is True

    dim = np.full((120, 160, 3), 150, dtype=np.uint8)
    assessment = guard.observe(dim, visible)
    assert assessment.visible is None
    assert assessment.paper_exposed is True

    # Com o nível novo absorvido, um bloco escuro real segue lido
    # como oclusão — a absorção não anestesia a guarda.
    shadow = dim.copy()
    shadow[24:96, 24:96] = 60
    assessment = guard.observe(shadow, visible)
    assert assessment.visible is not None
    assert not assessment.visible[60, 60]


def test_global_color_shift_is_absorbed_not_blocked():
    """Mudança global de temperatura de cor (luz azul sobre papel
    neutro): o croma é canal/grayscale e passa de 2 — com o teto
    antigo na referência de cor sobrava um resíduo permanente e a
    página inteira ficava vetada enquanto a luz durasse (Devin
    Review do PR #144)."""
    guard = occlusion_mod.PaperExposureGuard()
    neutral = np.full((120, 160, 3), 220, dtype=np.uint8)
    visible = np.ones(neutral.shape[:2], dtype=bool)
    assert guard.observe(neutral, visible).paper_exposed is True

    # BGR (190, 65, 55): grayscale ~76, croma do canal B ~2.5.
    blue_lit = np.full((120, 160, 3), (190, 65, 55), dtype=np.uint8)
    for _ in range(2):
        assessment = guard.observe(blue_lit, visible)
        assert assessment.visible is None
        assert assessment.paper_exposed is True

    # Sob a luz nova, um recorte que foge do ambiente — papel no tom
    # neutro antigo — segue bloqueado: a absorção não anestesia a
    # guarda.
    pale = blue_lit.copy()
    pale[24:96, 24:96] = (220, 220, 220)
    assessment = guard.observe(pale, visible)
    assert assessment.visible is not None
    assert not assessment.visible[60, 60]
    assert not assessment.paper_exposed[60, 60]

    # E o tom azulado num recorte local sobre papel neutro continua
    # sendo anomalia — nunca vira referência global.
    local = occlusion_mod.PaperExposureGuard()
    assert local.observe(neutral, visible).paper_exposed is True
    patch = neutral.copy()
    patch[24:96, 24:96] = (190, 65, 55)
    assessment = local.observe(patch, visible)
    assert assessment.visible is not None
    assert not assessment.visible[60, 60]
    assert not assessment.paper_exposed[60, 60]


def test_global_dimming_preserves_a_simultaneous_local_shadow():
    """O fator global da sala não pode ensinar junto uma sombra
    local: papel_exposed fica falso durante toda a janela de remoção."""
    guard = occlusion_mod.PaperExposureGuard()
    bright = np.full((240, 240, 3), 220, dtype=np.uint8)
    visible = np.ones(bright.shape[:2], dtype=bool)
    guard.observe(bright, visible)

    dim_shadow = np.full_like(bright, 150)
    dim_shadow[96:120, 96:120] = 60
    for _ in range(registration_mod._REMOVAL_PASSES + 2):
        assessment = guard.observe(dim_shadow, visible)
        assert not assessment.paper_exposed[100:110, 100:110].any()


def test_fill_recovery_exempts_supported_pixels_across_tile_borders():
    """Um preenchimento deslocado da grade recupera também pixels
    fortes das tiles de borda e sobrevive à dilatação dos vizinhos."""
    guard = occlusion_mod.PaperExposureGuard()
    paper = np.full((120, 168, 3), 220, dtype=np.uint8)
    guard.observe(paper)
    filled = paper.copy()
    filled[37:83, 37:83] = 60
    prob = np.zeros((120, 168), np.float32)
    prob[37:83, 37:83] = 0.95

    for _ in range(occlusion_mod._FILL_RECOVERY_PASSES):
        assessment = guard.observe(filled, ink_prob=prob)

    assert assessment.visible is not None
    assert assessment.visible[37:83, 37:83].all()
    assert not assessment.paper_exposed[37:83, 37:83].any()


def test_fill_region_recovers_additions_but_never_proves_paper():
    """Preenchimento: o veto de adição cai com evidência de tinta
    sustentada e a mão fora do tile; o de remoção fica — papel
    exposto nunca é provado sobre o preenchimento."""
    guard = occlusion_mod.PaperExposureGuard()
    paper = np.full((120, 168, 3), 210, dtype=np.uint8)
    for _ in range(2):
        assert guard.observe(paper).paper_exposed is True

    filled = paper.copy()
    filled[24:96, 0:72] = 60  # tiles (1:4, 0:3): o preenchimento
    filled[24:96, 96:168] = 60  # tiles (1:4, 4:7): oclusor escuro
    ink = np.zeros((120, 168), np.float32)
    ink[24:96, 0:72] = 0.95  # o modelo lê o preenchimento como tinta

    first = guard.observe(filled, ink_prob=ink)
    assert not first.visible[48, 48]
    assert not first.visible[48, 120]
    for _ in range(occlusion_mod._FILL_RECOVERY_PASSES - 1):
        last = guard.observe(filled, ink_prob=ink)
    assert last.visible[48, 48]
    assert not last.visible[48, 120]
    assert not last.paper_exposed[48, 48]
    assert not last.paper_exposed[48, 120]


def test_fill_streak_only_counts_with_a_clear_hand():
    """A contagem de evidência não anda com a mão sobre o tile —
    a adoção do preenchimento exige a mão fora do caminho."""
    guard = occlusion_mod.PaperExposureGuard()
    paper = np.full((96, 96, 3), 210, dtype=np.uint8)
    guard.observe(paper)

    filled = paper.copy()
    filled[24:96, 24:96] = 60
    ink = np.zeros((96, 96), np.float32)
    ink[24:96, 24:96] = 0.95
    hand = np.ones((96, 96), dtype=bool)
    hand[24:96, 24:96] = False
    for _ in range(occlusion_mod._FILL_RECOVERY_PASSES + 1):
        covered = guard.observe(filled, hand, ink_prob=ink)
    assert not covered.visible[48, 48]

    clear = np.ones((96, 96), dtype=bool)
    for _ in range(occlusion_mod._FILL_RECOVERY_PASSES):
        last = guard.observe(filled, clear, ink_prob=ink)
    # A única anomalia era o preenchimento: adotado, o bloco esvazia e
    # a região volta a votar (à vista ou mascarada só onde restou
    # veto) — mas papel exposto continua não provado sobre ela.
    assert last.visible is None or last.visible[48, 48]
    assert not last.paper_exposed[48, 48]


def test_uncertain_photometry_does_not_advance_removal_streak():
    acc = accumulator_mod.LayeredInkAccumulator()
    prob = _big_ink()
    confirmed(acc, prob)
    missing = prob.copy()
    missing[10:190, 10:110] = 0.0
    visible = np.ones(prob.shape, bool)  # MediaPipe missed the hand
    exposed = visible.copy()
    exposed[10:190, 10:110] = False  # photo guard sees a dark block

    for _ in range(2 * registration_mod._REMOVAL_PASSES):
        acc.add(missing, visible, paper_exposed=exposed)

    assert np.all(acc._confirmed[10:190, 10:110] == 255)
    assert not acc._removal_streak[10:190, 10:110].any()


def test_hand_mask_dropouts_cannot_erase_or_add_hand_edges_and_exit_confirms():
    shape = (240, 320)
    old = np.zeros(shape, np.float32)
    old[90:106, 90:120] = 0.95
    old[10:25, 10:35] = 0.95  # tinta-testemunha distante da mão
    new = old.copy()
    new[180:196, 260:284] = 0.95
    shadow = np.full((*shape, 3), 220, dtype=np.uint8)
    hand = shadow.copy()
    hand[48:144, 48:168] = 75
    hand_edge = old.copy()
    hand_edge[60:70, 145:160] = 0.95
    covered_old = hand_edge.copy()
    covered_old[90:106, 90:120] = 0.0

    class _MutablePageClean:
        threshold = 0.7

        def __init__(self):
            self.prob = old

        def ink_prob(self, _image):
            return self.prob

    clock = rr.SceneClock()
    page_clean = _MutablePageClean()
    worker = rr.make_ink_worker(page_clean, clock, config=InkConfig(removal=True))
    generation = worker.new_generation()
    corners = rr.base_quad(shape)
    camera_to_page = registration_mod._corners_page_matrix(corners, shape[1], shape[0])

    def camera_visibility_for(page_visibility):
        return cv2.warpPerspective(
            page_visibility.astype(np.uint8),
            np.linalg.inv(camera_to_page),
            (1280, 720),
            flags=cv2.INTER_NEAREST,
            borderValue=1,
        ).astype(bool)

    all_visible = np.ones(shape, bool)

    def pass_page(image, probability, visible):
        page_clean.prob = probability
        clock.now += 1
        worker.submit(
            WarpedPage(
                image,
                generation,
                corners,
                visible=camera_visibility_for(visible),
            )
        )
        assert worker.pump()
        assert worker.error is None

    for _ in range(16):
        pass_page(shadow, old, all_visible)
    original = worker._accumulator._confirmed.copy()
    assert original[90:106, 90:120].all()

    hand_visible = all_visible.copy()
    hand_visible[48:144, 48:168] = False
    for index in range(registration_mod._REMOVAL_PASSES * 2):
        # A periodic all-visible result models 1–3 missed masks while
        # the image itself keeps the photometric guard active.
        visible = all_visible if index % 4 == 0 else hand_visible
        pass_page(hand, covered_old, visible)

    result = worker._accumulator
    np.testing.assert_array_equal(result._confirmed, original)
    assert not result._provisional[48:144, 48:168].any()
    assert not result._confirmed[60:70, 145:160].any()

    for _ in range(8):
        pass_page(shadow, new, all_visible)
    assert result._confirmed[90:106, 90:120].all()
    assert result._confirmed[180:196, 260:284].all()


def test_global_dimming_releases_tiles_hidden_by_the_hand():
    """A absorção de shift global escala TODAS as referências
    conhecidas — inclusive as escondidas pela mão. Sem isso o tile
    coberto ficava claro demais e, ao reaparecer no nível novo,
    virava um bloco escuro permanente (Devin Review do PR #144)."""
    guard = occlusion_mod.PaperExposureGuard()
    bright = np.full((120, 160, 3), 220, dtype=np.uint8)
    clear = np.ones(bright.shape[:2], dtype=bool)
    for _ in range(2):
        assert guard.observe(bright, clear).paper_exposed is True

    hand = clear.copy()
    hand[24:96, 24:96] = False  # 3x3 tiles sob a mão
    dim = np.full((120, 160, 3), 150, dtype=np.uint8)
    absorbed = guard.observe(dim, hand)
    assert absorbed.visible is None  # shift absorvido, não bloqueio

    revealed = guard.observe(dim, clear)
    assert revealed.visible is None
    assert revealed.paper_exposed is True


def test_fill_recovery_keeps_the_worker_awake_past_the_exit_window():
    """A janela pós-saída do voto legado tem 1 passada, mas o streak
    de preenchimento precisa de _FILL_RECOVERY_PASSES limpas: sem a
    trava, a trabalhadora dormia no meio da contagem e a tinta
    adotável nunca votava (Devin Review do PR #144)."""
    shape = (120, 160)
    paper = np.full((*shape, 3), 220, dtype=np.uint8)
    filled = paper.copy()
    filled[24:96, 24:96] = 60
    prob_fill = np.zeros(shape, np.float32)
    prob_fill[24:96, 24:96] = 0.95

    class _MutablePageClean:
        threshold = 0.7

        def __init__(self):
            self.prob = np.zeros(shape, np.float32)

        def ink_prob(self, _image):
            return self.prob

    clock = rr.SceneClock()
    page_clean = _MutablePageClean()
    worker = rr.make_ink_worker(page_clean, clock)
    generation = worker.new_generation()
    corners = rr.base_quad(shape)
    clear = np.ones(shape, dtype=bool)
    hand_covered = clear.copy()
    hand_covered[24:96, 24:96] = False

    def pass_page(image, prob, page_visible):
        page_clean.prob = prob
        clock.now += 1
        worker.submit(
            WarpedPage(
                image,
                generation,
                corners,
                visible=rr.camera_mask(page_visible, corners),
            )
        )
        ran = worker.pump()
        assert worker.error is None
        return ran

    worker.set_hand_presence(True)
    for _ in range(2):
        assert pass_page(filled, prob_fill, hand_covered)
    worker.set_hand_presence(False)

    ran = [
        pass_page(filled, prob_fill, clear)
        for _ in range(occlusion_mod._FILL_RECOVERY_PASSES + 3)
    ]
    assert all(ran)  # a porta de descanso não fechou durante o streak
    assert worker._accumulator._confirmed[24:96, 24:96].all()


def test_page_recovery_ignores_false_ink_inside_the_photometric_veto():
    """Tinta falsa lida DENTRO do bloqueio fotométrico não entra na
    contenção nem fabrica recall dilatada: sem a interseção com a
    máscara à vista, a sombra acusava troca de página mesmo com a
    tinta anterior intacta à vista (Devin Review do PR #144)."""
    shape = (120, 160)
    paper = np.full((*shape, 3), 220, dtype=np.uint8)
    prob = np.zeros(shape, np.float32)
    prob[10:20, 5:20] = 0.95  # traço real fora da futura sombra
    shadowed = paper.copy()
    shadowed[24:96, 48:144] = 60  # bloco 3x4 tiles
    ghost = prob.copy()
    ghost[30:90, 60:130] = 0.95  # "tinta" lida sob a sombra

    class _MutablePageClean:
        threshold = 0.7

        def __init__(self):
            self.prob = prob

        def ink_prob(self, _image):
            return self.prob

    clock = rr.SceneClock()
    page_clean = _MutablePageClean()
    worker = rr.make_ink_worker(page_clean, clock)
    generation = worker.new_generation()
    corners = rr.base_quad(shape)
    for _ in range(6):
        page_clean.prob = prob
        clock.now += 1
        worker.submit(WarpedPage(paper, generation, corners))
        assert worker.pump()
        assert worker.error is None

    generation = worker.new_generation(preserve_identity=True)
    page_clean.prob = ghost
    clock.now += 1
    worker.submit(WarpedPage(shadowed, generation, corners))
    assert worker.pump()
    assert worker.error is None
    event = worker.telemetry_snapshot()["page_identity_events"][-1]
    assert event["decision"] == "same_page"
