"""Relatorios Markdown e resumo estruturado dos resultados do corpus."""

import math

from lab.corpus.metrics import delta


def _group_results(results):
    by_clip = {}
    bundles_order = []
    seen_bundles = set()
    for res in results:
        if res.bundle not in seen_bundles:
            seen_bundles.add(res.bundle)
            bundles_order.append(res.bundle)
        by_clip.setdefault(res.clip, []).append(res)
    return by_clip, bundles_order


def _format_delta(d: dict) -> str:
    px = d["canvas_px_delta"]
    ratio = d["canvas_px_ratio"]
    if ratio is None:
        return f"{px:+d} px"
    pct = (ratio - 1.0) * 100.0
    return f"{px:+d} px ({pct:+.0f}%)"


def render_summary(results, baseline: str) -> dict:
    """Gera resumo legivel por maquina com falhas e metricas por clipe/bundle."""
    by_clip, bundles_order = _group_results(results)
    failures = sum(1 for res in results if res.error is not None)
    expected_failures = []
    per_clip = {}

    for clip_name, clip_results in by_clip.items():
        base_res = next(
            (r for r in clip_results if r.bundle == baseline and r.error is None),
            None,
        )
        clip_map = {}
        for res in clip_results:
            for verdict in res.expected_verdicts:
                if not verdict.get("ok"):
                    expected_failures.append(
                        {
                            "clip": res.clip,
                            "bundle": res.bundle,
                            "rule": verdict.get("rule"),
                            "detail": verdict.get("detail"),
                        }
                    )
            entry = {
                "canvas_px": res.canvas_px,
                "provisional_median_px": res.provisional_median_px,
                "retracted_px_total": res.retracted_px_total,
                "passes": res.passes,
                "cpu_s_per_scene_s": (
                    None if math.isnan(res.cpu_s_per_scene_s) else res.cpu_s_per_scene_s
                ),
                "error": res.error,
                "delta": (
                    delta(base_res, res)
                    if (
                        base_res is not None
                        and res.bundle != baseline
                        and res.error is None
                    )
                    else None
                ),
            }
            clip_map[res.bundle] = entry
        per_clip[clip_name] = clip_map

    return {
        "clips": len(by_clip),
        "bundles": len(bundles_order),
        "failures": failures,
        "expected_failures": expected_failures,
        "per_clip": per_clip,
    }


def render_markdown(results, baseline: str, title="Corpus") -> str:
    """Renderiza tabela de deltas por clipe e secao de expectativas em pt-BR."""
    by_clip, _ = _group_results(results)
    summary = render_summary(results, baseline)
    lines = [
        f"# Corpus: {title}",
        "",
        (
            f"{summary['clips']} clipes, {summary['bundles']} bundles, "
            f"{summary['failures']} falhas"
        ),
        "",
    ]
    expectation_lines = []

    for clip_name, clip_results in by_clip.items():
        lines.append(f"## {clip_name}")
        lines.append("")
        lines.append(
            "| bundle | canvas_px | provisório | retratado | "
            "passadas | cpu s/s cena | Δ vs base |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        base_res = next(
            (r for r in clip_results if r.bundle == baseline and r.error is None),
            None,
        )
        for res in clip_results:
            if res.error is not None:
                lines.append(
                    f"| {res.bundle} | ⚠ erro: {res.error} | - | - | - | - | - |"
                )
            else:
                cpu_str = (
                    "-"
                    if math.isnan(res.cpu_s_per_scene_s)
                    else f"{res.cpu_s_per_scene_s:.2f}"
                )
                if res.bundle == baseline or base_res is None:
                    delta_str = "-"
                else:
                    delta_str = _format_delta(delta(base_res, res))
                lines.append(
                    f"| {res.bundle} | {res.canvas_px} | "
                    f"{res.provisional_median_px:.1f} | {res.retracted_px_total} | "
                    f"{res.passes} | {cpu_str} | {delta_str} |"
                )
            for verdict in res.expected_verdicts:
                status = "ok" if verdict.get("ok") else "falha"
                expectation_lines.append(
                    f"- {res.clip}/{res.bundle}: regra {verdict.get('rule')} — "
                    f"{status} ({verdict.get('detail', '')})"
                )
        lines.append("")

    if expectation_lines:
        lines.append("### Expectativas")
        lines.append("")
        lines.extend(expectation_lines)
        lines.append("")

    lines.append(f"_Gerado por lab.corpus — baseline: {baseline}_")
    return "\n".join(lines) + "\n"
