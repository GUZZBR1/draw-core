"""Execucao de bundles do corpus sobre ``bench_ink.run_clip``."""

from pathlib import Path

from lab.corpus.clip import ClipError, clip_frames, load_clip
from lab.corpus.manifest import iter_clip_dirs
from lab.corpus.metrics import ClipResult


def evaluate_expected(clip, result) -> list[dict]:
    """Avalia regras ``expected`` declaradas no clipe contra um resultado."""
    verdicts = []
    for entry in getattr(clip, "expected", None) or []:
        rule = entry.get("rule")
        if rule == "no_ink":
            ok = result.canvas_px == 0
            detail = f"canvas_px={result.canvas_px}"
        elif rule == "ink_present":
            min_px = int(entry.get("min_px", 1))
            ok = result.canvas_px >= min_px
            detail = f"canvas_px={result.canvas_px} (min={min_px})"
        elif rule == "canvas_stable":
            ok = result.retracted_px_total == 0
            detail = f"retracted_px_total={result.retracted_px_total}"
        else:
            ok = False
            detail = "regra desconhecida"
        verdicts.append({"rule": rule, "ok": bool(ok), "detail": detail})
    return verdicts


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
        run_dict = bench_ink.run_clip(
            clip.dir,
            list(flags),
            detector=detector,
            page_clean=page_clean,
            verify=verify,
            frame_files=frame_files,
        )
        res = ClipResult.from_run_dict(clip.name, bundle, list(flags), run_dict)
        res.expected_verdicts = evaluate_expected(clip, res)
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
