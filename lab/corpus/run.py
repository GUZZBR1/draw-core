"""Execucao de bundles do corpus sobre ``bench_ink.run_clip``."""

from pathlib import Path

from lab.corpus.clip import (
    ClipError,
    clip_frames,
    load_clip,
    rect_problem,
    window_missing,
)
from lab.corpus.manifest import iter_clip_dirs
from lab.corpus.metrics import ClipResult


def _scope_series(entry, result, run):
    """Série ``(quadro, px confirmado, geração)`` dentro do recorte da regra.

    Sem ``_trace`` (resultado de bancada sintético) devolve um ponto só:
    o canvas final, que não admite recorte — regra com ``region`` então
    não tem dado e volta ``None``.
    """
    run = run or {}
    trace = run.get("_trace")
    region = entry.get("region")
    if not trace:
        if region is not None:
            return None
        return [(0, int(getattr(result, "canvas_px", 0) or 0), 0)]
    if region is None:
        return [(t["frame"], t["px"], t["gen"]) for t in trace]
    counts = (run.get("_scope_px") or {}).get(tuple(region))
    if counts is None:
        return None
    return [(t["frame"], px, t["gen"]) for t, px in zip(trace, counts, strict=True)]


def _window(series, entry, *, whole_clip):
    """Recorta a série à janela ``frames`` (posição no inventário, inclusiva).

    Sem ``frames``: o clipe inteiro se ``whole_clip`` (estabilidade é uma
    régua temporal), senão só o quadro final — regras de tinta medem o
    estado final do canvas, como antes do escopo existir.
    """
    span = entry.get("frames")
    if span is None:
        return series if whole_clip else series[-1:]
    a, b = span
    return [pt for pt in series if a <= pt[0] <= b]


def _scope_desc(entry) -> str:
    parts = []
    if "frames" in entry:
        a, b = entry["frames"]
        parts.append(f"janela={a}..{b}")
    if "region" in entry:
        parts.append(f"regiao={entry['region']}")
    return ", ".join(parts)


def evaluate_expected(clip, result, run=None) -> list[dict]:
    """Avalia regras ``expected`` declaradas no clipe contra um resultado.

    ``run`` é o dicionário de ``bench_ink.run_clip``: ``_trace`` dá a
    série de px confirmado/geração por quadro (régua de
    ``canvas_stable`` — queda do CONFIRMADO, não retração provisória) e
    ``_scope_px`` a mesma série restrita a cada reta ``region`` pedida.
    ``frames`` limita a janela em que regras de tinta procuram o pico —
    e exige cada índice dela no trace (posição no inventário de
    ``clip_frames``, ordem numérica): quadro que o replay pulou falha a
    regra como janela incompleta, não encolhe o recorte em silêncio.
    """
    verdicts = []
    for entry in getattr(clip, "expected", None) or []:
        rule = entry.get("rule") if isinstance(entry, dict) else None
        try:
            verdicts.append(_eval_entry(rule, entry, result, run))
        except (AttributeError, TypeError, ValueError):
            # Escopo malformado (janela/min_px/regiao fora do schema): a
            # regra falha sem derrubar o restante do resultado.
            verdicts.append({"rule": rule, "ok": False, "detail": "escopo invalido"})
    return verdicts


def _eval_entry(rule, entry, result, run) -> dict:
    if rule not in ("no_ink", "ink_present", "canvas_stable"):
        return {"rule": rule, "ok": False, "detail": "regra desconhecida"}
    series = _scope_series(entry, result, run)
    if series is None:
        return {"rule": rule, "ok": False, "detail": "sem serie do recorte"}
    scoped = "frames" in entry or "region" in entry
    if "frames" in entry:
        # Todo índice da janela rotulada precisa constar do trace:
        # quadro pulado no replay é lacuna, não recorte menor.
        missing = window_missing(entry["frames"], (pt[0] for pt in series))
        if missing:
            span = entry["frames"]
            detail = (
                f"janela {span} fora do replay"
                if len(missing) == span[1] - span[0] + 1
                else f"janela {span} incompleta no replay: sem os quadros {missing}"
            )
            return {"rule": rule, "ok": False, "detail": detail}
    if rule == "canvas_stable":
        window = _window(series, entry, whole_clip=True)
        first = next((i for i, pt in enumerate(window) if pt[1] > 0), None)
        if first is None:
            ok, detail = True, "sem tinta confirmada"
        else:
            # Depois da primeira tinta confirmada: canvas que zera
            # ou sessão que reabre (a geração troca ao reabrir, até
            # quando a republicação esconde a queda do px) é colapso.
            drops = sum(1 for pt in window[first:] if pt[1] == 0)
            reopens = sum(
                1
                for prev, cur in zip(window[first:], window[first + 1 :], strict=False)
                if cur[2] != prev[2]
            )
            ok = drops == 0 and reopens == 0
            detail = f"quedas={drops} reaberturas={reopens}"
            if scoped:
                detail += f" ({_scope_desc(entry)})"
    else:
        window = _window(series, entry, whole_clip=False)
        peak = max((pt[1] for pt in window), default=0)
        if rule == "no_ink":
            ok = peak == 0
            detail = (
                f"px={peak} ({_scope_desc(entry)})" if scoped else f"canvas_px={peak}"
            )
        else:
            min_px = int(entry.get("min_px", 1))
            ok = peak >= min_px
            detail = (
                f"px={peak} (min={min_px}, {_scope_desc(entry)})"
                if scoped
                else f"canvas_px={peak} (min={min_px})"
            )
    return {"rule": rule, "ok": bool(ok), "detail": detail}


def _expected_rects(clip) -> list:
    """Retas ``region`` válidas das regras do clipe (para ``run_clip``)."""
    from draw import config

    orientation = getattr(clip, "orientation", None) or "retrato"
    size = None
    if orientation in config.ORIENTATIONS:
        size = config.paper_grid("a4", orientation)
    rects = set()
    for entry in getattr(clip, "expected", None) or []:
        reg = entry.get("region") if isinstance(entry, dict) else None
        if reg is not None and rect_problem(reg, size) is None:
            rects.add(tuple(reg))
    return sorted(rects)


def _fresh_detector(verify):
    """Detector padrao novo, carregado fora do intervalo medido do clipe.

    O detector guarda bordas/mascara entre deteccoes: um novo por clipe x
    bundle (mesma disciplina do CLI de bench_ink) para o resultado nao
    depender da ordem de execucao.
    """
    from draw.perception import NeuralSheetDetector
    from lab.replay_lab import _default_model

    detector = NeuralSheetDetector(
        str(_default_model("draw_seg_v3_dyn.onnx")), verify=verify
    )
    detector.load()
    return detector


def _fresh_page_clean(verify):
    """Page_clean padrao, carregado fora do intervalo medido do clipe."""
    from draw.page_clean import PageCleanInk
    from lab.replay_lab import _default_model

    page_clean = PageCleanInk(
        str(_default_model("page_clean_unet.onnx")), verify=verify
    )
    page_clean.load()
    return page_clean


def run_bundle(
    clip_dir,
    bundle: str,
    flags: list,
    *,
    detector=None,
    page_clean=None,
    verify=None,
) -> ClipResult:
    """Executa um clipe com um bundle de flags e devolve ``ClipResult``."""
    from draw import config
    from lab import bench_ink

    clip_dir = Path(clip_dir)
    saved = (
        config.PAPER_FORMAT,
        config.PAPER_ORIENTATION,
        config.PAPER_W,
        config.PAPER_H,
        config.MARKER_CENTERS,
    )
    conditions = {}
    try:
        clip = load_clip(clip_dir)
        frame_files = clip_frames(clip.dir)
        if len(frame_files) != clip.frames:
            raise ClipError(
                f"{clip.name}: {len(frame_files)} quadros f*.png, "
                f"clip.json declara {clip.frames}"
            )
        if detector is None:
            detector = _fresh_detector(verify)
        if page_clean is None:
            page_clean = _fresh_page_clean(verify)
        conditions = dict(clip.conditions)
        run_dict = bench_ink.run_clip(
            clip.dir,
            list(flags),
            detector=detector,
            page_clean=page_clean,
            verify=verify,
            frame_files=frame_files,
            trace=True,
            scopes=_expected_rects(clip),
        )
        res = ClipResult.from_run_dict(clip.name, bundle, list(flags), run_dict)
        res.expected_verdicts = evaluate_expected(clip, res, run_dict)
        res.conditions = conditions
        return res
    except Exception as exc:
        return ClipResult(
            clip=clip_dir.name,
            bundle=bundle,
            flags=list(flags),
            frames=0,
            canvas_px=0,
            provisional_median_px=0.0,
            provisional_last_px=0.0,
            retracted_px_total=0,
            passes=0,
            wall_s=0.0,
            cpu_s_per_scene_s=0.0,
            error=str(exc),
            conditions=conditions,
        )
    finally:
        (
            config.PAPER_FORMAT,
            config.PAPER_ORIENTATION,
            config.PAPER_W,
            config.PAPER_H,
            config.MARKER_CENTERS,
        ) = saved


def run_corpus(
    root,
    bundles: dict,
    *,
    verify_corpus,
    only=None,
    detector=None,
    page_clean=None,
    verify=None,
    progress=None,
) -> list[ClipResult]:
    """Roda todos os clipes de ``root`` x ``bundles`` (clipe externo, bundle interno).

    ``verify_corpus`` e o callable de integridade do corpus
    (``lab.corpus.manifest.verify_manifest``): qualquer problema aborta
    a rodada antes do primeiro replay; ``None`` e o opt-out explicito
    (bancadas e testes fora do manifesto). A verificacao de MODELOS e
    independente e segue em ``verify``.
    """
    if verify_corpus is not None:
        problems = verify_corpus(root)
        if problems:
            raise ClipError(f"corpus fora do manifesto: {'; '.join(problems)}")
    clip_dirs = iter_clip_dirs(root)
    if only is not None:
        only_set = set(only)
        clip_dirs = [d for d in clip_dirs if d.name in only_set]

    results = []
    total = len(clip_dirs) * len(bundles)
    step = 0
    for clip_dir in clip_dirs:
        for bundle_name, flags in bundles.items():
            step += 1
            if progress is not None:
                progress(clip_dir.name, bundle_name, step, total)
            results.append(
                run_bundle(
                    clip_dir,
                    bundle_name,
                    flags,
                    detector=detector,
                    page_clean=page_clean,
                    verify=verify,
                )
            )
    return results
