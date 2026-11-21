"""Rotulagem e migracao de clip.json (init v2 e upgrade v1 -> v2)."""

import json
from pathlib import Path

from lab.corpus.clip import (
    CLIP_JSON_VERSION,
    CONDITION_KEYS,
    ClipError,
    count_frames,
    load_clip,
)


class ClipInitError(Exception):
    """Erro ao inicializar ou atualizar metadados de um clipe."""


def _validate_conditions(conditions: dict) -> None:
    unknown = sorted(set(conditions) - set(CONDITION_KEYS))
    if unknown:
        raise ClipInitError(f"chaves de condicao desconhecidas: {', '.join(unknown)}")


def init_clip(
    clip_dir,
    *,
    fps: float,
    orientation=None,
    desc="",
    conditions=None,
    provenance=None,
    expected=None,
    issues=None,
    overwrite=False,
) -> Path:
    """Inicializa ``clip.json`` v2 num diretorio com quadros ``f*.png``."""
    clip_dir = Path(clip_dir)
    if isinstance(fps, bool) or not isinstance(fps, (int, float)) or fps <= 0:
        raise ClipInitError(f"fps deve ser > 0: {fps!r}")
    frames = count_frames(clip_dir)
    if frames == 0:
        raise ClipInitError(f"nenhum frame f*.png encontrado em {clip_dir}")

    target = clip_dir / "clip.json"
    if target.exists() and not overwrite:
        raise ClipInitError(f"clip.json ja existe em {clip_dir} (use overwrite=True)")

    cond_dict = dict(conditions or {})
    _validate_conditions(cond_dict)

    payload = {
        "version": CLIP_JSON_VERSION,
        "scene_fps": float(fps),
        "frames": frames,
        "desc": desc,
        "conditions": cond_dict,
        "provenance": dict(provenance or {}),
        "expected": list(expected or []),
        "issues": list(issues or []),
    }
    if orientation is not None:
        payload["orientation"] = orientation

    target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target


def upgrade_clip(clip_dir, *, fps=None, provenance=None) -> Path:
    """Atualiza ``clip.json`` v1 para v2 preservando campos existentes."""
    clip_dir = Path(clip_dir)
    target = clip_dir / "clip.json"
    if not target.is_file():
        raise ClipInitError(f"clip.json ausente em {clip_dir}")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClipInitError(f"clip.json invalido em {clip_dir}: {exc}") from exc
    if not isinstance(data, dict):
        raise ClipInitError(f"clip.json deve ser objeto JSON: {target}")

    data["version"] = CLIP_JSON_VERSION
    if fps is not None:
        data["scene_fps"] = float(fps)
    scene_fps = data.get("scene_fps")
    if (
        isinstance(scene_fps, bool)
        or not isinstance(scene_fps, (int, float))
        or scene_fps <= 0
    ):
        raise ClipInitError(f"scene_fps ausente ou invalido: {scene_fps!r}")

    data.setdefault("frames", count_frames(clip_dir))
    data.setdefault("desc", "")
    data.setdefault("conditions", {})
    if provenance is not None:
        data["provenance"] = dict(provenance)
    else:
        data.setdefault("provenance", {})
    data.setdefault("expected", [])
    data.setdefault("issues", [])

    target.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    try:
        load_clip(clip_dir)
    except ClipError as exc:
        raise ClipInitError(str(exc)) from exc
    return target
