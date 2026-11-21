"""Remocao de pauta por DP (draw.ink.ruling), medida na regua lab.bench_ink."""

import dataclasses
import sys

import numpy as np
import pytest
from lab import bench_ink as bench

from draw import app as app_module
from draw.contracts import WarpedPage
from draw.ink import ruling
from draw.ink.config import InkConfig
from draw.ink.worker import PageCleanWorker


def _score(page):
    return bench.score_filter(page, lambda prob: ruling.RulingFilter().apply(prob))


@pytest.fixture(scope="module")
def straight():
    return bench.make_synthetic_page(seed=0)


@pytest.fixture(scope="module")
def tilted():
    return bench.make_synthetic_page(seed=0, tilt=0.35)


def test_removes_the_ruling_and_keeps_crossings_and_short_strokes(straight):
    s = _score(straight)
    assert s["ruling_removed"] > 0.95
    assert s["crossing_preserved"] >= 0.98
    assert s["short_stroke_recall"] >= 0.97
    assert s["on_line_recall"] >= 0.97  # braco do E sobre a linha


def test_open_notebook_with_opposite_slopes_in_each_half(tilted):
    """Caderno aberto torto: as duas metades sao rastreadas por separado.
    Sem isso (uma unica inclinacao) a remocao cai para ~79%."""
    s = _score(tilted)
    assert s["ruling_removed"] > 0.90
    assert s["crossing_preserved"] >= 0.98
    assert s["short_stroke_recall"] >= 0.97
    model = ruling.estimate(tilted.prob.copy())
    assert len(model.segments) == 2
    assert {seg.x0 < 600 for seg in model.segments} == {True, False}


def test_page_without_ruling_is_a_noop():
    rng = np.random.default_rng(0)
    prob = (rng.random((850, 1200)) * 0.05).astype(np.float32)
    before = prob.copy()
    f = ruling.RulingFilter()
    out = f.apply(prob)
    np.testing.assert_array_equal(out, before)
    assert f.last_info["lines"] == 0
    assert ruling.estimate(before) is None


def test_isolated_pen_strokes_without_ruling_are_untouched():
    prob = np.zeros((850, 1200), np.float32)
    prob[300:306, 100:700] = 0.95  # um traco grosso horizontal
    prob[100:800, 400:405] = 0.95  # e uma haste
    before = prob.copy()
    np.testing.assert_array_equal(ruling.RulingFilter().apply(prob), before)


def test_filter_caches_the_model_between_passes(monkeypatch, straight):
    calls = []
    real = ruling.estimate
    monkeypatch.setattr(
        ruling, "estimate", lambda *a, **k: calls.append(1) or real(*a, **k)
    )
    f = ruling.RulingFilter(reestimate_every=3)
    for _ in range(7):
        f.apply(straight.prob.copy())
    assert len(calls) == 3  # passadas 1, 4 e 7


def test_reset_and_shape_change_force_a_new_estimate(monkeypatch, straight):
    calls = []
    real = ruling.estimate
    monkeypatch.setattr(
        ruling, "estimate", lambda *a, **k: calls.append(1) or real(*a, **k)
    )
    f = ruling.RulingFilter()
    f.apply(straight.prob.copy())
    f.apply(straight.prob.copy())
    assert len(calls) == 1
    f.reset()
    f.apply(straight.prob.copy())
    assert len(calls) == 2
    f.apply(straight.prob[:700, :1000].copy())
    assert len(calls) == 3


def test_a_single_thick_column_on_the_ruling_is_not_an_anchor(straight):
    """Um ponto isolado de espessura maior (flutuacao da propria pauta) nao
    protege colunas em volta: so cruzamento de 2+ colunas seguidas."""
    prob = straight.prob.copy()
    model = ruling.estimate(prob.copy())
    # coluna longe de qualquer glifo: uma linha so de pauta
    glyphs = np.zeros(prob.shape, bool)
    for mask in straight.glyphs.values():
        glyphs |= mask
    seg = model.segments[0]
    for x in range(seg.x0 + 20, seg.x1 - 60):
        y = int(round(seg.paths[5, x - seg.x0]))
        if not glyphs[y - 8 : y + 9, x - 4 : x + 41].any():
            break
    else:
        pytest.fail("sem trecho de pauta limpa")
    base = ruling.RulingFilter().apply(prob.copy())
    prob[y - 5 : y + 6, x] = 0.95  # coluna unica engrossada
    out = ruling.RulingFilter().apply(prob.copy())
    # fora da coluna e da folga de 2 colunas, o resultado e o do caso sem o ponto
    window = (slice(y - 8, y + 9), slice(x + 1, x + 40))
    np.testing.assert_array_equal(out[window], base[window])
    assert (out[window] > 0.5).sum() == 0


@pytest.mark.slow
def test_cost_per_pass_stays_inside_the_budget(straight):
    f = ruling.RulingFilter()
    f.apply(straight.prob.copy())  # estima
    t = bench.time_ms(lambda p: f.apply(p), straight.prob, runs=15)
    assert t["p50_ms"] < 8.0  # meta 3 ms; folga p/ CI lento, o numero real vai na regua


def test_estimate_has_no_python_loop_over_y():
    """A DP e vetorizada em y: o laco e sobre colunas reduzidas."""
    import inspect

    src = inspect.getsource(ruling._comb_track) + inspect.getsource(ruling._refine)
    assert "for y" not in src and "for row" not in src


def test_default_config_is_off_and_the_worker_builds_the_filter_on_demand():
    class _Ink:
        threshold = 0.5

    assert InkConfig().ruling_removal is False
    assert PageCleanWorker(_Ink())._ruling is None
    on = PageCleanWorker(_Ink(), config=InkConfig(ruling_removal=True))
    assert isinstance(on._ruling, ruling.RulingFilter)


def test_main_default_is_on_and_no_ink_ruling_turns_it_off(monkeypatch):
    seen = []
    monkeypatch.setattr(app_module, "run", lambda **kw: seen.append(kw))
    monkeypatch.setattr(sys, "argv", ["draw"])
    app_module.main()
    ink = seen[-1]["pipeline_config"].ink
    assert ink.ruling_removal is True
    assert ink.vote_score_strong > 1.9  # coexiste com o voto estrito
    monkeypatch.setattr(sys, "argv", ["draw", "--no-ink-ruling"])
    app_module.main()
    assert seen[-1]["pipeline_config"].ink.ruling_removal is False


def _ruled_page(thick_cols=(), thick=4, stroke_cols=None):
    """Pagina so de pauta (2 px), com trechos mais grossos e/ou uma haste."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        for x in thick_cols:
            prob[y : y + thick, x] = 0.95
    if stroke_cols is not None:
        prob[60:560, stroke_cols] = 0.95
    return prob


def test_margin_above_h_pauta_still_counts_as_ruling():
    """A pauta real oscila (3-6 px no e5): um trecho ate h_pauta + 2 e
    pauta, nao cruzamento. Com margem 0 ele virava ancora e ficava."""
    cols = list(range(300, 360))
    prob = _ruled_page(thick_cols=cols, thick=4)
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out > 0.5).sum() == 0


def test_a_stroke_crossing_the_ruling_is_kept_with_two_columns_of_margin():
    stroke = slice(700, 706)
    prob = _ruled_page(stroke_cols=stroke)
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[60:560, stroke] > 0.5).all()  # o traco inteiro
    row = 80 + 2 * 40  # uma linha da pauta
    assert (out[row, 698:700] > 0.5).all()  # folga de 2 colunas a esquerda
    assert (out[row, 706:708] > 0.5).all()  # e a direita
    assert (out[row, 690:697] > 0.5).sum() == 0  # alem dela a pauta sai
    assert (out[row, 709:720] > 0.5).sum() == 0


class _RuledInk:
    threshold = 0.7

    def __init__(self, prob):
        self._prob = prob

    def ink_prob(self, _warped):
        return self._prob.copy()


def _worker(prob, enabled):
    now = [1000.0]
    worker = PageCleanWorker(
        _RuledInk(prob),
        clock=lambda: now[0],
        config=InkConfig(ruling_removal=enabled),
    )
    return worker, now


def _run_one_pass(worker, now, shape, generation):
    now[0] += 10.0  # vence qualquer cadencia
    worker.submit(WarpedPage(np.zeros((*shape, 3), np.uint8), generation))
    assert worker.pump() is True


def test_worker_filters_the_probability_before_the_vote_only_when_enabled():
    prob = _ruled_page()
    for enabled in (False, True):
        worker, now = _worker(prob, enabled)
        gen = worker.new_generation()
        for _ in range(3):
            _run_one_pass(worker, now, prob.shape, gen)
        shown = worker.poll_display(gen, -1)
        confirmed = np.count_nonzero(shown.confirmed) if shown else 0
        if enabled:
            assert not confirmed  # pauta pura: nada entra no canvas
        else:
            assert confirmed  # sem a flag, a pauta entra (comportamento atual)


def test_worker_drops_the_cached_model_when_the_generation_changes(monkeypatch):
    prob = _ruled_page()
    worker, now = _worker(prob, True)
    resets = []
    real = worker._ruling.reset
    monkeypatch.setattr(worker._ruling, "reset", lambda: resets.append(1) or real())
    gen = worker.new_generation()
    _run_one_pass(worker, now, prob.shape, gen)
    n = len(resets)
    _run_one_pass(worker, now, prob.shape, gen)
    assert len(resets) == n  # mesma folha: reaproveita
    gen2 = worker.new_generation()
    _run_one_pass(worker, now, prob.shape, gen2)
    assert len(resets) == n + 1  # outra folha: reestima


# ------------------------------------------------ achados do Devin (#56)


@pytest.mark.parametrize(("x0", "x1"), [(300, 440), (80, 219)])
def test_a_local_hatch_of_pen_strokes_is_not_mistaken_for_ruling(x0, x1):
    """8 tracos de caneta igualmente espacados numa faixa so, em papel liso:
    periodicos, mas sem suporte ao longo da folha. (300-440) atravessa a
    divisoria das metades; (80-219) fica inteiro na metade esquerda (review
    #56)."""
    prob = np.zeros((850, 850), np.float32)
    for i in range(8):
        prob[200 + 40 * i : 202 + 40 * i, x0:x1] = 0.95
    before = prob.copy()
    assert ruling.estimate(before) is None
    f = ruling.RulingFilter()
    np.testing.assert_array_equal(f.apply(prob), before)
    assert f.last_info["lines"] == 0


def test_ruling_that_reaches_the_right_edge_of_an_850_wide_page_is_erased():
    """850 // 6 = 141 colunas: o passo real nao e 6. As ultimas 4 colunas
    ficavam sem caminho e a pauta ali sobrevivia ao voto (review #56)."""
    prob = np.zeros((1200, 850), np.float32)
    for k in range(18):
        prob[100 + 50 * k : 102 + 50 * k, :] = 0.95
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out > 0.5).sum() == 0
    assert (out[:, 840:] > 0.5).sum() == 0  # inclusive as colunas 846-849


def test_soft_fringe_of_the_thickest_erasable_run_is_erased_too():
    """Run de h_pauta + 2 linhas: a franja suave de baixo ficava (o laco
    parava uma linha antes)."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 4, 300:360] = 0.95  # trecho de h_pauta + 2
        prob[y + 4, 300:360] = 0.3  # franja suave logo abaixo
        prob[y - 1, 300:360] = 0.3  # e acima
    out = ruling.RulingFilter().apply(prob.copy())
    assert out[:, 300:360].max() == 0.0


def _count_estimates(monkeypatch):
    calls = []
    real = ruling.estimate
    monkeypatch.setattr(
        ruling, "estimate", lambda *a, **k: calls.append(1) or real(*a, **k)
    )
    return calls


def test_a_missed_estimate_under_a_hand_is_retried_as_soon_as_the_hand_leaves(
    monkeypatch,
):
    """Sem pauta achada com a mao tapando a folha, o negativo nao pode ficar
    em cache por 24 passadas: a pauta seria confirmada como tinta (review
    #56)."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        prob[80 + 40 * k : 82 + 40 * k, :] = 0.95
    covered = np.zeros(prob.shape, bool)  # `visible` = sem mao: tudo tapado
    f = ruling.RulingFilter()
    f.apply(prob.copy(), covered)
    assert f.last_info["lines"] == 0
    out = f.apply(prob.copy(), None)  # a mao saiu: reestima JA nesta passada
    assert f.last_info["lines"] > 0 and (out > 0.5).sum() == 0


def test_blank_page_with_a_small_hand_does_not_estimate_every_pass(monkeypatch):
    """Em papel liso a mao esta quase sempre no quadro: so uma oclusao grande
    justifica reestimar cedo, e mesmo assim com recuo (review #56)."""
    calls = _count_estimates(monkeypatch)
    blank = np.zeros((600, 1200), np.float32)
    small_hand = np.ones(blank.shape, bool)
    small_hand[:, :120] = False  # 10% tapado
    f = ruling.RulingFilter()
    for _ in range(10):
        f.apply(blank.copy(), small_hand)
    assert len(calls) == 1
    big_hand = np.zeros(blank.shape, bool)  # tudo tapado: tenta de novo, com recuo
    calls.clear()
    f = ruling.RulingFilter()
    for _ in range(10):
        f.apply(blank.copy(), big_hand)
    assert 2 <= len(calls) <= 4  # a cada _RETRY_PASSES, nao a cada passada
    # e sem mao, um negativo continua em cache
    calls.clear()
    f = ruling.RulingFilter()
    for _ in range(10):
        f.apply(blank.copy(), None)
    assert len(calls) == 1


def test_paths_use_pixel_index_coordinates_and_do_not_grab_a_neighbour_stroke():
    """O centro de um bloco reduzido 2:1 que cobre as linhas y e y+1 e y+0,5
    (coordenadas de indice), nao y+1: o erro de meio pixel fazia o arredondamento
    escolher um traco de caneta vizinho (review #56)."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        prob[80 + 40 * k : 82 + 40 * k, :] = 0.95
    model = ruling.estimate(prob.copy())
    paths = model.segments[0].paths
    first = paths[int(np.argmin(np.abs(np.median(paths, axis=1) - 80.5)))]
    assert abs(float(np.median(first)) - 80.5) < 0.3
    # traco de caneta (2 px) colado a pauta, separado por UMA linha em branco
    pen = np.zeros_like(prob)
    pen[80 + 40 * 3 + 3 : 80 + 40 * 3 + 5, 400:520] = 0.95
    merged = np.maximum(prob, pen)
    out = ruling.RulingFilter().apply(merged.copy())
    assert (out[80 + 40 * 3 + 3 : 80 + 40 * 3 + 5, 400:520] > 0.5).all()  # ficou
    assert (out[80 + 40 * 3 : 80 + 40 * 3 + 2, 540:700] > 0.5).sum() == 0  # pauta saiu


@pytest.mark.parametrize("x0", [0, 7, 19, 30, 41, 53])
def test_span_cutoff_does_not_depend_on_window_alignment(x0):
    """O mesmo tracejado deslocado dentro da metade tem de dar o mesmo
    veredito (review #56): a extensao e medida em colunas, nao em janelas."""
    prob = np.zeros((850, 850), np.float32)
    for i in range(8):
        prob[200 + 40 * i : 202 + 40 * i, 80 + x0 : 80 + x0 + 146] = 0.95
    assert ruling.estimate(prob) is None


def _confirmed_after_votes(prob, config, passes=4):
    from draw.ink.worker import PageCleanWorker

    now = [1000.0]
    worker = PageCleanWorker(_RuledInk(prob), clock=lambda: now[0], config=config)
    gen = worker.new_generation()
    for _ in range(passes):
        _run_one_pass(worker, now, prob.shape, gen)
    shown = worker.poll_display(gen, -1)
    return np.asarray(shown.confirmed) > 0


@pytest.mark.parametrize("level", [None, 0.85])
def test_filter_holds_up_through_the_live_vote(straight, level):
    """A regua mede o mapa; aqui o mapa filtrado passa pelo voto REAL do
    worker (padrao e estrito) e o canvas confirmado e medido (review #56)."""
    cfg = InkConfig(ruling_removal=True)
    if level is not None:
        cfg = InkConfig.strict_vote(level, ruling_removal=True)
    confirmed = _confirmed_after_votes(straight.prob, cfg)
    # mesma regra de voto, sem o filtro: separa o que o voto rejeita do que a
    # remocao de pauta apaga
    plain = _confirmed_after_votes(
        straight.prob, dataclasses.replace(cfg, ruling_removal=False)
    )
    iso = straight.ruling_only
    assert confirmed[iso].sum() < 0.1 * plain[iso].sum()  # pauta: >= 90% fora do canvas
    arms = np.zeros_like(confirmed)
    for name in bench.SHORT_STROKE_GLYPHS:
        arms |= straight.arms[name]
    assert (confirmed & arms).sum() >= 0.97 * (plain & arms).sum()  # braços ficam


# ------------------------------------------------ caderno aberto com vinco (#132)


def _shaded_notebook(tilt, house=None):
    """Duas paginas curvas, pauta com lacunas e vinco sombreado: na faixa
    central TODAS as linhas engrossam (sombra), com probabilidade menor."""
    page = bench.make_synthetic_page(seed=0, tilt=tilt)
    prob = page.prob.copy()
    h, w = prob.shape
    mid = w // 2
    rng = np.random.default_rng(1)
    band = (slice(None), slice(mid - 40, mid + 40))
    shade = (
        np.asarray(
            __import__("cv2").dilate(
                page.ruling[band].astype(np.uint8), np.ones((5, 1), np.uint8)
            )
        )
        > 0
    )
    sub = prob[band]
    sub[shade] = np.maximum(sub[shade], rng.uniform(0.6, 0.9, int(shade.sum())))
    for x in range(30, w, 53):  # lacunas na pauta, longe do vinco
        if abs(x - mid) > 60:
            prob[page.ruling_only[:, x : x + 7].any(axis=1), x : x + 7] *= 0.4
    strokes = np.zeros(prob.shape, bool)
    if house is not None:
        import cv2

        x0, y0, size = house
        mask = np.zeros(prob.shape, np.uint8)
        pts = [
            (x0, y0 + size),
            (x0, y0),
            (x0 + size, y0),
            (x0 + size, y0 + size),
            (x0, y0 + size),
        ]
        roof = [(x0, y0), (x0 + size // 2, y0 - size // 2), (x0 + size, y0)]
        for line in (pts, roof):
            cv2.polylines(mask, [np.array(line, np.int32)], False, 255, 5)
        strokes = mask > 0
        prob[strokes] = 0.97
    return page, prob, strokes


def _leftover_in_fold(page, prob, out):
    """Pixels que sobram no vinco (rows sem a borda externa), incluindo a franja
    de sombra que `ruling_only` nao cobre, fora dos glifos do desenho."""
    cv2 = __import__("cv2")
    mid = prob.shape[1] // 2
    zone = np.zeros(prob.shape, bool)
    zone[40:-40, mid - 50 : mid + 50] = True
    pen = cv2.dilate(page.strokes.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    ink = (prob > 0.5) & zone & ~pen
    return int(((out > 0.5) & ink).sum()), int(ink.sum())


@pytest.mark.parametrize("tilt", [0.0, 0.35])
def test_shaded_gutter_does_not_leave_a_staircase_of_ruling(tilt):
    page, prob, _ = _shaded_notebook(tilt)
    out = ruling.RulingFilter().apply(prob.copy())
    left, total = _leftover_in_fold(page, prob, out)
    assert left < 0.01 * total  # inclui a franja de sombra, nao so a pauta


def _house_parts(x0, y0=300, size=150):
    import cv2

    shapes = {
        "left": [(x0, y0 + size), (x0, y0)],
        "top": [(x0, y0), (x0 + size, y0)],
        "right": [(x0 + size, y0), (x0 + size, y0 + size)],
        "bottom": [(x0 + size, y0 + size), (x0, y0 + size)],
        "roof": [(x0, y0), (x0 + size // 2, y0 - size // 2), (x0 + size, y0)],
    }
    parts = {}
    for name, line in shapes.items():
        mask = np.zeros((850, 1200), np.uint8)
        cv2.polylines(mask, [np.array(line, np.int32)], False, 255, 5)
        parts[name] = mask > 0
    return parts


@pytest.mark.parametrize("x0", [150, 520])  # 520: o topo cruza o vinco
def test_a_house_drawn_over_the_ruling_keeps_each_stroke(x0):
    page, prob, house = _shaded_notebook(0.35, house=(x0, 300, 150))
    out = ruling.RulingFilter().apply(prob.copy())
    for name, part in _house_parts(x0).items():
        kept = ((out > 0.5) & part).sum() / part.sum()
        assert kept >= 0.97, name  # cada lado, nao a media do desenho


def test_a_short_pen_dash_entirely_inside_the_fold_is_kept():
    """Traco curto sobre uma linha sombreada, sem continuacao fora do vinco.
    Aqui a sombra tem ~7 px, entao o traco de marcador tem 9."""
    page, prob, _ = _shaded_notebook(0.0)
    mid = prob.shape[1] // 2
    rows = np.flatnonzero(page.ruling[:, mid])
    y = int(rows[len(rows) // 2])
    dash = np.zeros(prob.shape, bool)
    dash[y - 4 : y + 5, mid - 10 : mid + 4] = True  # 9 px x 14 colunas
    prob[dash] = 0.97
    out = ruling.RulingFilter().apply(prob.copy())
    assert ((out > 0.5) & dash).sum() >= 0.97 * dash.sum()


def test_a_7px_dash_on_a_6px_shaded_rule_is_kept_and_the_rest_is_erased():
    """Caso do review: pauta de 2 px engrossa para 6 no vinco; um traco de 7 px
    e 14 colunas numa so linha (prob 0,97) fica, a sombra das outras sai."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:640] = 0.8
    dash = np.zeros(prob.shape, bool)
    dash[80 + 40 * 5 - 1 : 80 + 40 * 5 + 6, 590:604] = True
    prob[dash] = 0.97
    out = ruling.RulingFilter().apply(prob.copy())
    assert ((out > 0.5) & dash).sum() >= 0.97 * dash.sum()
    assert ((out > 0.5) & ~dash)[:, 560:640].sum() == 0


def test_pen_mark_on_a_predicted_row_of_an_unruled_section_is_kept():
    """Pauta so de y=100 para baixo; uma marca de 40 colunas na linha prevista
    acima dela nao pode validar a propria linha extrapolada."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        prob[100 + 40 * k : 102 + 40 * k, :] = 0.95
    prob[60:62, 300:340] = 0.95  # fora da pauta, no passo dela
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[60:62, 300:340] > 0.5).all()
    assert (out[100:580] > 0.5).sum() == 0  # e a pauta de verdade sai


def test_ruling_only_in_the_middle_of_the_page_is_still_detected():
    """Areas em branco acima e abaixo nao podem derrubar o segmento."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(7):
        prob[160 + 40 * k : 162 + 40 * k, :] = 0.95
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out > 0.5).sum() == 0


def test_a_shadow_centered_on_the_page_split_is_erased_on_both_sides():
    """Faixa de 16 colunas repartida 8 + 8 entre as metades (divisa em 600)."""
    prob = _ruled_page(thick_cols=range(592, 608), thick=6)
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[:, 584:616] > 0.5).sum() == 0


def test_uneven_shadow_shoulders_do_not_exempt_the_whole_fold():
    """Algumas linhas ficam grossas 2 colunas alem da faixa (sombra que afina
    irregular), sem caneta: o interior da faixa sai por inteiro."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:640] = 0.95  # a faixa
        if k % 2 == 0:
            prob[y : y + 6, 558:560] = 0.95  # ombros
            prob[y : y + 6, 640:642] = 0.95
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[:, 566:634] > 0.5).sum() == 0


def test_staggered_shadow_shoulders_longer_than_a_stroke_do_not_exempt_the_fold():
    """Ombros de 13 colunas (acima do minimo de continuacao) em linhas
    alternadas: a sombra que afina de forma escalonada nao e um traco.
    Continuacao em muitas linhas nao isenta a faixa (review #139)."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:640] = 0.95
        if k % 2 == 0:
            prob[y : y + 6, 547:560] = 0.95  # ombros de 13 colunas
            prob[y : y + 6, 640:653] = 0.95
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[:, 566:634] > 0.5).sum() == 0
    # Nos ombros (< 60% das linhas), as linhas finas (impares) saem e as
    # marcas dos ombros (pares) ficam fora de _gutter_mask
    odd_rows = np.concatenate(
        [np.arange(80 + 40 * k, 82 + 40 * k) for k in range(1, 12, 2)]
    )
    assert (out[odd_rows, 547:560] > 0.5).sum() == 0
    assert (out[odd_rows, 640:653] > 0.5).sum() == 0
    even_rows = np.concatenate(
        [np.arange(80 + 40 * k, 86 + 40 * k) for k in range(0, 12, 2)]
    )
    assert (out[even_rows, 547:560] > 0.5).all()
    assert (out[even_rows, 640:653] > 0.5).all()


def test_shadow_shoulders_covering_most_rules_are_erased_with_the_fold():
    """Ombros em >= 60% das linhas (8 de 12) entram em _gutter_mask e saem."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:640] = 0.95
        if k % 3 != 0:  # 8 de 12 linhas (66,7% >= 60%)
            prob[y : y + 6, 547:560] = 0.95
            prob[y : y + 6, 640:653] = 0.95
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[:, 550:650] > 0.5).sum() == 0


def test_a_stroke_crossing_the_fold_through_staggered_shoulders_is_kept():
    """Caso do review: ombros de 13 colunas em linhas alternadas E um traco
    de 6 px na linha 7, de 540 a 660. O padrao comum e sombra (sai), mas o
    traco continua ALEM do comprimento comum e o miolo dele fica."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:640] = 0.95
        if k % 2 == 0:
            prob[y : y + 6, 547:560] = 0.95
            prob[y : y + 6, 640:653] = 0.95
    y = 80 + 40 * 7
    prob[y : y + 6, 540:660] = 0.95  # mesma espessura da sombra
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[y : y + 6, 566:634] > 0.5).all()  # o miolo do traco
    others = out[:, 566:634] > 0.5
    others[y : y + 6, :] = False
    assert others.sum() == 0  # e so ele


def test_shadow_shoulders_that_grow_down_the_page_do_not_exempt_the_fold():
    """Ombros de largura crescente (12 a 22 colunas) em linhas alternadas:
    o corte nao pode ser so uma margem sobre a mediana — exige um gap claro
    ate o ombro mais longo das outras linhas (review #139)."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:640] = 0.95
    for i, k in enumerate(range(0, 12, 2)):
        y = 80 + 40 * k
        sh = 12 + 2 * i  # 12, 14, 16, 18, 20, 22
        prob[y : y + 6, 560 - sh : 560] = 0.95
        prob[y : y + 6, 640 : 640 + sh] = 0.95
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[:, 566:634] > 0.5).sum() == 0


def test_shadow_shoulders_with_a_gap_at_the_fold_edge_do_not_exempt_it():
    """Ombros de 13 colunas em linhas alternadas, 4 delas finas so na coluna
    vizinha da faixa (o voto tolera 11/12). A medida da extensao honra a
    mesma tolerancia: nenhuma isenta (review #139)."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:640] = 0.95
    for k in range(0, 12, 2):
        y = 80 + 40 * k
        prob[y : y + 6, 547:560] = 0.95
        prob[y : y + 6, 640:653] = 0.95
    for k in (0, 4, 6, 8):  # gap na coluna vizinha da faixa
        y = 80 + 40 * k
        prob[y : y + 6, 559] = 0.0
        prob[y : y + 6, 640] = 0.0
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[:, 566:634] > 0.5).sum() == 0


def test_two_equal_strokes_crossing_the_fold_are_both_kept():
    """Caso do review: dois tracos de 6 px com a MESMA extensao (20 colunas
    de cada lado) entre quatro ombros de 13. Antes, cada traco era o "ombro
    mais longo" do outro e os dois perdiam o miolo; agrupando por gap, os
    dois atravessam ALEM do grupo dos ombros (review #139)."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:640] = 0.95
        if k % 3 == 0:  # k in {0, 3, 6, 9}: quatro linhas com ombros
            prob[y : y + 6, 547:560] = 0.95
            prob[y : y + 6, 640:653] = 0.95
    strokes = (80 + 40 * 1, 80 + 40 * 7)  # fora do grupo dos ombros
    for y in strokes:
        prob[y : y + 6, 540:660] = 0.95  # 20 colunas de cada lado
    out = ruling.RulingFilter().apply(prob.copy())
    for y in strokes:
        assert (out[y : y + 6, 566:634] > 0.5).all()  # o miolo de cada traco
    others = out[:, 566:634] > 0.5
    for y in strokes:
        others[y : y + 6, :] = False
    assert others.sum() == 0  # e so eles


def test_a_stroke_crossing_a_split_fold_gets_one_verdict_on_both_halves():
    """Ombros assimetricos: 13 colunas a esquerda e 20 a direita do vinco
    [560,700), que a divisa das metades parte em 600. Um traco com 18
    colunas de continuacao de cada lado era medido por um ombro diferente
    em cada trilha (passava na esquerda, nao na direita) e saia pela
    metade; julgado pelo MESMO ombro comum (o maior dos dois lados), o
    veredito e unico: nao passa em nenhuma (review #139)."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:700] = 0.95  # a faixa cruza a divisa em 600
        if k % 2 == 0:
            prob[y : y + 6, 547:560] = 0.95  # ombros de 13 a esquerda
            prob[y : y + 6, 700:720] = 0.95  # ombros de 20 a direita
    y = 80 + 40 * 7
    prob[y : y + 6, 542:718] = 0.95  # traco: 18 colunas de cada lado
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[:, 562:698] > 0.5).sum() == 0  # o vinco inteiro sai


def test_a_clear_stroke_crossing_a_split_fold_is_kept_on_both_halves():
    """Mesma geometria (ombros 13/20, vinco na divisa), mas o traco vai 30
    colunas alem de cada ponta — claramente alem do ombro comum (20 + 3):
    o miolo fica INTEIRO nas duas metades (review #139)."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:700] = 0.95
        if k % 2 == 0:
            prob[y : y + 6, 547:560] = 0.95
            prob[y : y + 6, 700:720] = 0.95
    y = 80 + 40 * 7
    prob[y : y + 6, 530:730] = 0.95  # traco: 30 colunas de cada lado
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[y : y + 6, 560:600] > 0.5).all()  # miolo a esquerda da divisa
    assert (out[y : y + 6, 600:698] > 0.5).all()  # e a direita
    others = out[:, 562:698] > 0.5
    others[y : y + 6, :] = False
    assert others.sum() == 0  # e so ele


def test_a_long_continuation_on_a_single_line_is_still_a_stroke():
    """Ombros de 20 colunas dos dois lados, mas numa linha so: continuacao
    rara = traco de caneta. A faixa dessa linha fica; a das outras sai
    (review #139)."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:640] = 0.95
    y = 80 + 40 * 5
    prob[y : y + 6, 540:560] = 0.95
    prob[y : y + 6, 640:660] = 0.95
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[y : y + 6, 566:634] > 0.5).all()  # a linha do traco
    others = out[:, 566:634] > 0.5
    others[y : y + 6, :] = False
    assert others.sum() == 0  # e so ela


def test_an_8_column_dash_inside_the_fold_is_kept():
    """Traco mais curto que 12 colunas inteiro dentro do vinco: na sombra
    uniforme, o desvio de uma so linha ja o separa das vizinhas (review
    #139)."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:640] = 0.8
    dash = np.zeros(prob.shape, bool)
    dash[80 + 40 * 5 - 1 : 80 + 40 * 5 + 6, 580:588] = True  # 7 px x 8 colunas
    prob[dash] = 0.97
    out = ruling.RulingFilter().apply(prob.copy())
    assert ((out > 0.5) & dash).sum() >= 0.97 * dash.sum()
    assert ((out > 0.5) & ~dash)[:, 560:640].sum() == 0


def test_a_shadow_ripple_shared_by_many_lines_is_erased():
    """Ondulacao da sombra: seis linhas engrossam 1 px a mais por 8 colunas
    dentro do vinco. Desvio compartilhado = sombra, nao seis tracos curtos;
    so o desvio isolado vale como caneta (review #139)."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:640] = 0.8
        if k % 2 == 0:
            prob[y : y + 7, 580:588] = 0.8  # a ondulacao
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[:, 566:634] > 0.5).sum() == 0


def test_a_dash_thicker_than_a_shared_ripple_is_kept():
    """Ondulacao de 7 px em quatro linhas e, nas mesmas 8 colunas, um traco
    de 8 px numa quinta linha: o nivel compartilhado sai, quem vai acima
    dele fica (review #139)."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:640] = 0.8
        if k % 3 == 0:  # quatro linhas: 0, 3, 6, 9
            prob[y : y + 7, 580:588] = 0.8
    dash = np.zeros(prob.shape, bool)
    y = 80 + 40 * 5  # fora da ondulacao
    dash[y - 1 : y + 7, 580:588] = True  # 8 px
    prob[dash] = 0.95
    out = ruling.RulingFilter().apply(prob.copy())
    assert ((out > 0.5) & dash).sum() >= 0.97 * dash.sum()
    assert ((out > 0.5) & ~dash)[:, 560:640].sum() == 0


def test_a_fold_ending_a_vote_window_before_the_split_is_erased():
    """A faixa termina a exatas 12 colunas da divisa das metades: a janela
    de voto ainda existe, mas a cauda alem dela e vazia. A medida da
    extensao nao pode quebrar nesse caso (argmax num eixo vazio) e o
    interior da faixa sai (review #139)."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:588] = 0.95  # a faixa: borda direita em 600 - 12
        if k % 2 == 0:  # seis linhas seguem grossas nas janelas de voto
            prob[y : y + 6, 547:560] = 0.95
            prob[y : y + 6, 588:600] = 0.95
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[:, 566:582] > 0.5).sum() == 0


def _two_line_segment(n, second):
    paths = np.stack([np.full(n, 100.0), second]).astype(np.float32)
    return ruling.Segment(0, n, paths, 40.0, np.array([False, True]))


def test_a_dash_on_a_predicted_line_clipped_to_the_last_columns_is_not_ruling():
    """Linha prevista que so aparece nas ultimas 30 colunas, com um traco de
    27 sobre ela: sozinho ele nao autoriza apagar (review #139)."""
    x = np.arange(600)
    seg = _two_line_segment(600, 599.0 - (x - 570.0))
    prob = np.zeros((600, 600), np.float32)
    prob[99:101, :] = 0.95
    for c in range(572, 600):
        r = int(round(seg.paths[1, c]))
        prob[r : r + 2, c] = 0.95
    assert ruling._drop_unsupported(prob, seg).paths.shape[0] == 1


def test_a_blank_partial_window_does_not_dilute_the_support_of_a_gapped_rule():
    """Metade de 422 px (8 janelas + 38 vazios): tinta em 3 das 8 janelas
    inteiras (37,5%) continua valendo (review #139)."""
    seg = _two_line_segment(422, np.full(422, 200.0))
    prob = np.zeros((600, 422), np.float32)
    prob[99:101, :] = 0.95
    for w in (0, 4, 7):
        prob[200:202, w * 48 : w * 48 + 48] = 0.95
    assert ruling._drop_unsupported(prob, seg).paths.shape[0] == 2


def test_the_partial_tail_window_counts_only_when_it_has_ink():
    """Linha que entra a meio da trilha (120 colunas visiveis: duas janelas
    inteiras e um resto de 24). Tinta so na janela inteira final: 1/2. Com
    tinta tambem no resto: 2/3. Resto vazio nao dilui (review #139)."""
    inside = np.zeros((1, 600), bool)
    inside[0, 480:] = True
    base = np.zeros((1, 600), bool)
    base[0, 528:576] = True  # janela inteira final
    frac_blank, _ = ruling._window_support(base, inside)
    tail = base.copy()
    tail[0, 576:] = True  # e o resto parcial
    frac_tail, _ = ruling._window_support(tail, inside)
    assert frac_blank[0] == pytest.approx(1 / 2)
    assert frac_tail[0] == pytest.approx(2 / 3)
    # e o resto de 24 colunas tem de existir: sem ele (janelas inteiras so) a
    # tinta do resto seria ignorada e frac_tail seria 1/2
    assert frac_tail[0] > frac_blank[0]


def test_the_inked_partial_tail_is_what_keeps_a_tilted_extrapolated_line():
    """O mesmo cenario, ponta a ponta pelo filtro de linhas: a prevista so
    entra na vista nas ultimas 168 colunas (3 janelas inteiras + resto de
    24). Tinta na primeira janela inteira: 1/3 < 35% e ela cai. Com tinta
    tambem no resto: 2/4 e ela fica — so a cauda parcial a salva (review
    #139)."""
    x = np.arange(600)
    seg = _two_line_segment(600, 599.0 + (432.0 - x) * 0.5)
    prob = np.zeros((600, 600), np.float32)
    prob[99:101, :] = 0.95
    for c in range(432, 480):  # primeira janela inteira visivel
        r = int(round(seg.paths[1, c]))
        prob[r : r + 2, c] = 0.95
    assert ruling._drop_unsupported(prob, seg).paths.shape[0] == 1
    with_tail = prob.copy()
    for c in range(576, 600):  # e o resto parcial
        r = int(round(seg.paths[1, c]))
        with_tail[r : r + 2, c] = 0.95
    assert ruling._drop_unsupported(with_tail, seg).paths.shape[0] == 2


def test_a_stroke_with_unequal_valid_extensions_across_a_split_fold_is_kept_on_both_halves():
    """Ombros 13/20 e vinco [560,700) na divisa 600; traco com 18 col a esquerda
    e 30 a direita vence os dois ombros locais e fica inteiro nos dois lados."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:700] = 0.95
        if k % 2 == 0:
            prob[y : y + 6, 547:560] = 0.95  # 13 a esquerda
            prob[y : y + 6, 700:720] = 0.95  # 20 a direita
    y = 80 + 40 * 7
    prob[y : y + 6, 542:730] = 0.95  # 18 a esquerda, 30 a direita
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[y : y + 6, 560:600] > 0.5).all()
    assert (out[y : y + 6, 600:698] > 0.5).all()
    others = out[:, 562:698] > 0.5
    others[y : y + 6, :] = False
    assert others.sum() == 0


def test_a_fold_ending_8_columns_before_the_split_uses_adjacent_track_for_vote():
    """Faixa [560, 592) termina 8 colunas antes da divisa em 600: a janela de
    voto (12 col) cruza a divisa e usa amostras da trilha direita."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:592] = 0.95
        if k % 2 == 0:
            prob[y : y + 6, 547:560] = 0.95
            prob[y : y + 6, 592:605] = 0.95  # cruza a divisa em 600
    out_plain = ruling.RulingFilter().apply(prob.copy())
    assert (out_plain[:, 566:586] > 0.5).sum() == 0

    y = 80 + 40 * 7
    prob[y : y + 6, 540:612] = 0.95  # 20 col a esquerda, 20 a direita
    out_stroke = ruling.RulingFilter().apply(prob.copy())
    assert (out_stroke[y : y + 6, 562:590] > 0.5).all()
    others = out_stroke[:, 566:586] > 0.5
    others[y : y + 6, :] = False
    assert others.sum() == 0


def test_a_narrow_vertical_crossing_inside_the_fold_is_kept():
    """Cruzamento vertical estreito (8 px x 3 col) no meio da sombra (6 px)
    fica protegido mesmo abaixo do teto elevado da faixa."""
    prob = np.zeros((600, 1200), np.float32)
    for k in range(12):
        y = 80 + 40 * k
        prob[y : y + 2, :] = 0.95
        prob[y : y + 6, 560:640] = 0.8
    dash = np.zeros(prob.shape, bool)
    y = 80 + 40 * 5
    dash[y - 1 : y + 7, 575:578] = True  # 8 px x 3 col = 24 px
    prob[dash] = 0.95
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[y - 1 : y + 7, 575:578] > 0.5).all()
    assert ((out > 0.5) & ~dash)[:, 560:640].sum() == 0


def test_off_frame_extrapolated_rule_does_not_erase_border_dash():
    """Linha extrapolada inclinada (0,15 px/col) que entra na imagem no fim da
    metade direita nao pode apagar um traco desconectado na borda onde ela
    ainda esta fora da imagem, e deve apagar o trecho que entra."""
    prob = np.zeros((600, 1200), np.float32)
    xs = np.arange(1200)
    for k in range(18):
        ys = np.round(-160.0 + 40.0 * k + 0.15 * xs).astype(np.int32)
        for dy in (0, 1):
            r = ys + dy
            ok = (r >= 0) & (r < 600)
            prob[r[ok], xs[ok]] = 0.95
    # Entre 952 e 975, a linha k=0 esta em y <= -13,75 (fora da imagem)
    prob[5:7, 952:976] = 0.95  # traco 2x24 = 48 px na borda superior
    out = ruling.RulingFilter().apply(prob.copy())
    assert (out[5:7, 952:976] > 0.5).all()
    # O trecho da linha k=0 que entra na imagem (x >= 1075) e apagado
    enter_x = np.arange(1075, 1200)
    enter_y = np.round(-160.0 + 0.15 * enter_x).astype(np.int32)
    assert (out[enter_y, enter_x] > 0.5).sum() == 0
    assert (out[enter_y + 1, enter_x] > 0.5).sum() == 0
