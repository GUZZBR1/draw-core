"""Testes de execucao, metricas, sweep e relatorios do corpus."""

import json
from types import SimpleNamespace

import pytest
from lab.corpus.metrics import (
    ClipResult,
    delta,
    load_results,
    write_results,
)
from lab.corpus.report import render_markdown, render_summary
from lab.corpus.run import evaluate_expected, run_bundle, run_corpus
from lab.corpus.sweep import grid_bundles, parse_grid, run_sweep

from draw import config as draw_config


def test_clip_result_from_run_dict_and_roundtrip():
    run_dict = {
        "clip": "sombra",
        "frames": 100,
        "canvas_px": 1500,
        "provisional_median_px": 42.5,
        "provisional_last_px": 12.0,
        "retracted_px_total": 3,
        "retracted_over_canvas": 0.002,
        "passes": 25,
        "cpu_s_per_scene_s": 0.45,
        "wall_s": 1.25,
        "writing_px": 1400,
        "ruling_px": 10,
        "_canvas": "ignored-ndarray",
    }
    res = ClipResult.from_run_dict("sombra", "base", ["coverage=1"], run_dict)
    res.expected_verdicts = [{"rule": "ink_present", "ok": True, "detail": "ok"}]
    assert res.writing_px == 1400
    assert res.ruling_px == 10

    raw = res.to_dict()
    assert "_canvas" not in raw
    restored = ClipResult.from_dict(raw)
    assert restored == res


def test_delta_arithmetic_and_zero_base_ratio():
    base = ClipResult(
        clip="c",
        bundle="base",
        flags=[],
        frames=10,
        canvas_px=100,
        provisional_median_px=20.0,
        provisional_last_px=5.0,
        retracted_px_total=4,
        passes=10,
        wall_s=1.0,
        cpu_s_per_scene_s=0.5,
    )
    cand = ClipResult(
        clip="c",
        bundle="cand",
        flags=[],
        frames=10,
        canvas_px=150,
        provisional_median_px=15.0,
        provisional_last_px=5.0,
        retracted_px_total=1,
        passes=12,
        wall_s=1.1,
        cpu_s_per_scene_s=0.6,
    )
    d = delta(base, cand)
    assert d["canvas_px_delta"] == 50
    assert d["canvas_px_ratio"] == pytest.approx(1.5)
    assert d["provisional_delta"] == pytest.approx(-5.0)
    assert d["retracted_delta"] == -3
    assert d["passes_delta"] == 2
    assert d["cpu_delta"] == pytest.approx(0.1)

    zero_base = ClipResult.from_dict({**base.to_dict(), "canvas_px": 0})
    assert delta(zero_base, cand)["canvas_px_ratio"] is None


def test_write_and_load_results_jsonl(tmp_path):
    r1 = ClipResult(
        clip="a",
        bundle="base",
        flags=[],
        frames=5,
        canvas_px=10,
        provisional_median_px=1.0,
        provisional_last_px=0.0,
        retracted_px_total=0,
        passes=2,
        wall_s=0.1,
        cpu_s_per_scene_s=0.2,
    )
    r2 = ClipResult(
        clip="b",
        bundle="cand",
        flags=["ink.x=1"],
        frames=0,
        canvas_px=0,
        provisional_median_px=0.0,
        provisional_last_px=0.0,
        retracted_px_total=0,
        passes=0,
        wall_s=0.0,
        cpu_s_per_scene_s=0.0,
        error="falhou",
    )
    path = write_results(tmp_path / "out" / "results.jsonl", [r1, r2])
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert load_results(path) == [r1, r2]


def test_evaluate_expected_rules():
    clip = SimpleNamespace(
        expected=[
            {"rule": "no_ink"},
            {"rule": "ink_present", "min_px": 50},
            {"rule": "canvas_stable"},
            {"rule": "desconhecida"},
        ]
    )
    res_bad = SimpleNamespace(canvas_px=20, retracted_px_total=3)
    verdicts_bad = evaluate_expected(clip, res_bad)
    # Retracao provisoria nao derruba canvas_stable: a regua olha o
    # confirmado, e sem traco o fallback e o ponto final (sem colapso).
    assert [v["ok"] for v in verdicts_bad] == [False, False, True, False]

    res_ok = SimpleNamespace(canvas_px=0, retracted_px_total=0)
    verdicts_ok = evaluate_expected(clip, res_ok)
    assert verdicts_ok[0]["ok"] is True
    assert verdicts_ok[1]["ok"] is False
    assert verdicts_ok[2]["ok"] is True

    res_ink = SimpleNamespace(canvas_px=60, retracted_px_total=0)
    assert evaluate_expected(clip, res_ink)[1]["ok"] is True


def _trace(points):
    """[(px, gen), ...] -> lista de pontos _trace com quadros 0..n."""
    return [{"frame": i, "px": px, "gen": gen} for i, (px, gen) in enumerate(points)]


def test_canvas_stable_catches_confirmed_collapse_and_reopen():
    """canvas_stable mede o CONFIRMADO: queda a zero ou reabertura de
    sessao (geracao nova) falham; retracao so provisoria nao."""
    clip = SimpleNamespace(expected=[{"rule": "canvas_stable"}])
    res = SimpleNamespace(canvas_px=2000, retracted_px_total=0)

    # Colapso transiente: 2000 px confirmados zeram e voltam (o bug do
    # review — antes passava porque retracted_px_total ficava 0).
    run = {"_trace": _trace([(2000, 1), (2000, 1), (0, 1), (2000, 1)])}
    assert evaluate_expected(clip, res, run)[0]["ok"] is False

    # Reabertura sem queda visivel: a republicacao esconde o px, mas a
    # geracao trocou — o canvas exibido foi limpo ao reabrir a sessao.
    run = {"_trace": _trace([(100, 1), (100, 2), (100, 2)])}
    assert evaluate_expected(clip, res, run)[0]["ok"] is False

    # So provisorio retraiu: confirmado cresce e devolve um resto sem
    # zerar nem reabrir — estavel (retracted_px_total nao entra na regua).
    res_ret = SimpleNamespace(canvas_px=800, retracted_px_total=99)
    run = {"_trace": _trace([(0, 1), (500, 1), (900, 1), (800, 1)])}
    assert evaluate_expected(clip, res_ret, run)[0]["ok"] is True

    # Nunca confirmou tinta: nada a colapsar.
    res_empty = SimpleNamespace(canvas_px=0, retracted_px_total=0)
    run = {"_trace": _trace([(0, 1), (0, 1), (0, 1)])}
    assert evaluate_expected(clip, res_empty, run)[0]["ok"] is True


def test_expected_scopes_restrict_ink_to_window_and_region():
    """Tinta fora da janela de frames ou do retangulo nao satisfaz a regra."""
    clip = SimpleNamespace(
        expected=[
            {"rule": "ink_present", "min_px": 100, "frames": [1, 3]},
            {"rule": "ink_present", "min_px": 100, "region": [0, 0, 400, 1200]},
            {"rule": "no_ink", "frames": [2, 4], "region": [0, 0, 400, 1200]},
            {
                "rule": "ink_present",
                "min_px": 100,
                "frames": [0, 1],
                "region": [0, 0, 400, 1200],
            },
        ]
    )
    res = SimpleNamespace(canvas_px=500, retracted_px_total=0)
    rect = (0, 0, 400, 1200)

    # Tinta so no quadro 5 (depois da janela) e nunca dentro do retangulo.
    run = {
        "_trace": _trace([(0, 1)] * 5 + [(500, 1)]),
        "_scope_px": {rect: [0] * 6},
    }
    assert [v["ok"] for v in evaluate_expected(clip, res, run)] == [
        False,
        False,
        True,
        False,
    ]

    # Tinta dentro da janela e do retangulo a partir do quadro 2.
    run = {
        "_trace": _trace([(0, 1), (0, 1), (150, 1), (150, 1), (150, 1)]),
        "_scope_px": {rect: [0, 0, 120, 120, 120]},
    }
    # A 4a regra pede tinta na janela 0..1 do retangulo — a tinta chega no
    # quadro 2, fora dela.
    assert [v["ok"] for v in evaluate_expected(clip, res, run)] == [
        True,
        True,
        False,
        False,
    ]

    # Recorte pedido sem serie medida: a regra nao pode ser satisfeita.
    run = {"_trace": _trace([(150, 1)] * 5)}
    assert evaluate_expected(clip, res, run)[1]["ok"] is False

    # Janela fora do replay inteiro: falha explicita, nao vazio que passa.
    clip_far = SimpleNamespace(expected=[{"rule": "no_ink", "frames": [9, 12]}])
    assert evaluate_expected(clip_far, res, run)[0]["ok"] is False


def _write_fake_clip_json(clip_dir, expected=None):
    clip_dir.mkdir(parents=True, exist_ok=True)
    (clip_dir / "clip.json").write_text(
        json.dumps(
            {
                "version": 2,
                "scene_fps": 10.0,
                "frames": 2,
                "desc": "fake",
                "expected": expected or [],
            }
        ),
        encoding="utf-8",
    )


def test_run_bundle_success_and_error_paths(monkeypatch, tmp_path):
    import lab.bench_ink as bench_ink

    clip_dir = tmp_path / "c1"
    _write_fake_clip_json(clip_dir, expected=[{"rule": "ink_present", "min_px": 50}])

    orig_w, orig_h = draw_config.PAPER_W, draw_config.PAPER_H

    def fake_run_clip(cdir, flags, **_kw):
        draw_config.apply_format("a4", "paisagem")
        return {
            "clip": cdir.name,
            "frames": 2,
            "canvas_px": 120,
            "provisional_median_px": 4.0,
            "provisional_last_px": 0.0,
            "retracted_px_total": 0,
            "passes": 1,
            "cpu_s_per_scene_s": 0.3,
            "wall_s": 0.1,
            "_canvas": None,
        }

    monkeypatch.setattr(bench_ink, "run_clip", fake_run_clip)
    res = run_bundle(clip_dir, "base", ["coverage=1"])
    assert res.error is None
    assert res.canvas_px == 120
    assert res.expected_verdicts == [
        {"rule": "ink_present", "ok": True, "detail": "canvas_px=120 (min=50)"}
    ]
    assert (draw_config.PAPER_W, draw_config.PAPER_H) == (orig_w, orig_h)

    def boom(*_a, **_kw):
        raise RuntimeError("quebrou no meio")

    monkeypatch.setattr(bench_ink, "run_clip", boom)
    err_res = run_bundle(clip_dir, "cand", [])
    assert err_res.error == "quebrou no meio"
    assert err_res.canvas_px == 0
    assert (draw_config.PAPER_W, draw_config.PAPER_H) == (orig_w, orig_h)


def test_run_corpus_ordering_only_and_sweep(monkeypatch, tmp_path):
    import lab.bench_ink as bench_ink

    _write_fake_clip_json(tmp_path / "alpha")
    _write_fake_clip_json(tmp_path / "beta")

    seen = []

    def fake_run_clip(cdir, flags, **_kw):
        seen.append((cdir.name, list(flags)))
        return {
            "clip": cdir.name,
            "frames": 2,
            "canvas_px": 10,
            "provisional_median_px": 1.0,
            "provisional_last_px": 0.0,
            "retracted_px_total": 0,
            "passes": 1,
            "cpu_s_per_scene_s": 0.1,
            "wall_s": 0.05,
        }

    monkeypatch.setattr(bench_ink, "run_clip", fake_run_clip)
    bundles = {"b1": ["x=1"], "b2": ["x=2"]}
    results = run_corpus(tmp_path, bundles)
    assert [(r.clip, r.bundle) for r in results] == [
        ("alpha", "b1"),
        ("alpha", "b2"),
        ("beta", "b1"),
        ("beta", "b2"),
    ]

    only_beta = run_corpus(tmp_path, bundles, only={"beta"})
    assert [r.clip for r in only_beta] == ["beta", "beta"]

    sweep_res = run_sweep(tmp_path, "ink.x=0,1", base_flags=["coverage=1"])
    assert len(sweep_res) == 4
    assert seen[-1][1] == ["coverage=1", "ink.x=1"]


def test_parse_grid_and_grid_bundles():
    grid = parse_grid("a.x=0,1;b.y=2,3")
    assert grid == {"a.x": ["0", "1"], "b.y": ["2", "3"]}

    bundles = grid_bundles(grid, base_flags=["coverage=1"])
    assert list(bundles) == [
        "x=0+y=2",
        "x=0+y=3",
        "x=1+y=2",
        "x=1+y=3",
    ]
    assert bundles["x=0+y=2"] == ["coverage=1", "a.x=0", "b.y=2"]
    assert grid_bundles({}, base_flags=["coverage=1"]) == {"base": ["coverage=1"]}

    for bad in ("sem_igual", "=1", "a=", "a=1,,2", "a=1;a=2"):
        with pytest.raises(ValueError):
            parse_grid(bad)


def test_render_markdown_and_summary():
    r_base = ClipResult(
        clip="c1",
        bundle="base",
        flags=[],
        frames=10,
        canvas_px=100,
        provisional_median_px=5.0,
        provisional_last_px=1.0,
        retracted_px_total=0,
        passes=5,
        wall_s=0.2,
        cpu_s_per_scene_s=0.4,
        expected_verdicts=[{"rule": "ink_present", "ok": True, "detail": "ok"}],
    )
    r_cand = ClipResult(
        clip="c1",
        bundle="cand",
        flags=["x=1"],
        frames=10,
        canvas_px=125,
        provisional_median_px=4.0,
        provisional_last_px=1.0,
        retracted_px_total=0,
        passes=5,
        wall_s=0.2,
        cpu_s_per_scene_s=0.5,
        expected_verdicts=[{"rule": "no_ink", "ok": False, "detail": "125"}],
    )
    r_err = ClipResult(
        clip="c2",
        bundle="base",
        flags=[],
        frames=0,
        canvas_px=0,
        provisional_median_px=0.0,
        provisional_last_px=0.0,
        retracted_px_total=0,
        passes=0,
        wall_s=0.0,
        cpu_s_per_scene_s=0.0,
        error="modelo ausente",
    )

    md = render_markdown([r_base, r_cand, r_err], baseline="base", title="Teste")
    assert "# Corpus: Teste" in md
    assert "## c1" in md
    assert "## c2" in md
    assert "| base | 100 |" in md
    assert "+25 px (+25%)" in md
    assert "⚠ erro: modelo ausente" in md
    assert "### Expectativas" in md

    summary = render_summary([r_base, r_cand, r_err], baseline="base")
    assert summary["clips"] == 2
    assert summary["bundles"] == 2
    assert summary["failures"] == 1
    assert len(summary["expected_failures"]) == 1
    assert summary["expected_failures"][0]["clip"] == "c1"
