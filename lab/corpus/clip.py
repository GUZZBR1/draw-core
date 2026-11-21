"""Schema e validacao de clipes reais do corpus (v1 e v2)."""

import dataclasses
import json
from pathlib import Path

CLIP_JSON_VERSION = 2
CONDITION_KEYS = (
    "lighting",
    "surface",
    "content",
    "occluder",
    "motion",
    "camera",
)
EXPECTED_RULES = ("no_ink", "ink_present", "canvas_stable")


class ClipError(Exception):
    """Erro ao carregar um clipe ou seus metadados."""


@dataclasses.dataclass(frozen=True)
class ClipSpec:
    """Especificacao carregada de um clipe do corpus."""

    name: str
    dir: Path
    fps: float
    orientation: str | None
    frames: int
    desc: str
    conditions: dict
    provenance: dict
    expected: list
    issues: list
    regions: dict | None
    version: int


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def clip_frames(clip_dir) -> list[Path]:
    """Quadros ``f*.png`` do nivel raiz, em ordem.

    Inventario unico do clipe: a contagem de ``count_frames``, o hash
    do manifesto e o replay do corpus compartilham esta lista — o que
    o sha256 cobre e o que entra no replay sao os mesmos arquivos.
    """
    clip_dir = Path(clip_dir)
    if not clip_dir.is_dir():
        return []
    return sorted(p for p in clip_dir.glob("f*.png") if p.is_file())


def count_frames(clip_dir) -> int:
    """Conta quadros ``f*.png`` no nivel raiz do diretorio do clipe."""
    return len(clip_frames(clip_dir))


def _read_json_dict(path: Path, label: str) -> dict:
    if not path.is_file():
        raise ClipError(f"{label} ausente em {path.parent}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClipError(f"{label} invalido em {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ClipError(f"{label} deve ser objeto JSON: {path}")
    return data


def load_clip(clip_dir) -> ClipSpec:
    """Carrega ``clip.json`` (v1 ou v2) e ``regions.json`` opcional."""
    clip_dir = Path(clip_dir)
    raw = _read_json_dict(clip_dir / "clip.json", "clip.json")

    if "version" not in raw:
        version = 1
    else:
        raw_ver = raw["version"]
        if not _is_int(raw_ver) or raw_ver not in (1, CLIP_JSON_VERSION):
            raise ClipError(f"versao de clip.json nao suportada: {raw_ver!r}")
        version = int(raw_ver)

    for key in ("scene_fps", "frames", "desc"):
        if key not in raw:
            raise ClipError(f"campo obrigatorio ausente em clip.json: {key!r}")

    fps = raw["scene_fps"]
    if not _is_number(fps) or fps <= 0:
        raise ClipError(f"scene_fps deve ser > 0: {fps!r}")
    frames = raw["frames"]
    if not _is_int(frames) or frames < 0:
        raise ClipError(f"frames invalido: {frames!r}")
    desc = raw["desc"]
    if not isinstance(desc, str):
        raise ClipError(f"desc deve ser string: {desc!r}")

    orientation = raw.get("orientation")
    if orientation is not None and not isinstance(orientation, str):
        raise ClipError(f"orientation invalida: {orientation!r}")

    conditions = raw.get("conditions", {})
    provenance = raw.get("provenance", {})
    expected = raw.get("expected", [])
    issues = raw.get("issues", [])
    if not isinstance(conditions, dict):
        raise ClipError("conditions deve ser objeto")
    if not isinstance(provenance, dict):
        raise ClipError("provenance deve ser objeto")
    if not isinstance(expected, list):
        raise ClipError("expected deve ser lista")
    if not isinstance(issues, list):
        raise ClipError("issues deve ser lista")

    regions_path = clip_dir / "regions.json"
    regions = (
        _read_json_dict(regions_path, "regions.json") if regions_path.exists() else None
    )

    return ClipSpec(
        name=clip_dir.name,
        dir=clip_dir,
        fps=float(fps),
        orientation=orientation,
        frames=int(frames),
        desc=desc,
        conditions=dict(conditions),
        provenance=dict(provenance),
        expected=list(expected),
        issues=list(issues),
        regions=regions,
        version=version,
    )


def _validate_expected(expected) -> list[str]:
    problems = []
    if not isinstance(expected, list):
        return ["expected deve ser uma lista"]
    for idx, entry in enumerate(expected):
        if not isinstance(entry, dict):
            problems.append(f"expected[{idx}] deve ser objeto")
            continue
        rule = entry.get("rule")
        if rule not in EXPECTED_RULES:
            problems.append(f"expected[{idx}].rule desconhecida: {rule!r}")
        if "frames" in entry:
            span = entry["frames"]
            if (
                not isinstance(span, list)
                or len(span) != 2
                or not all(_is_int(v) for v in span)
                or span[0] > span[1]
            ):
                problems.append(
                    f"expected[{idx}].frames deve ser [a, b] com ints a <= b"
                )
        if "region" in entry:
            reg = entry["region"]
            if (
                not isinstance(reg, list)
                or len(reg) != 4
                or not all(_is_int(v) for v in reg)
            ):
                problems.append(f"expected[{idx}].region deve ter 4 inteiros")
        if "min_px" in entry and not _is_int(entry["min_px"]):
            problems.append(f"expected[{idx}].min_px deve ser inteiro")
    return problems


def validate_clip(clip_dir) -> list[str]:
    """Valida ``clip.json``, contagem de quadros e ``regions.json``."""
    clip_dir = Path(clip_dir)
    try:
        raw = _read_json_dict(clip_dir / "clip.json", "clip.json")
    except ClipError as exc:
        return [str(exc)]

    problems = []
    if "version" in raw:
        ver = raw["version"]
        if not _is_int(ver) or ver not in (1, CLIP_JSON_VERSION):
            problems.append(f"version invalida: {ver!r} (esperado 1 ou 2)")

    if "scene_fps" not in raw:
        problems.append("scene_fps ausente")
    elif not _is_number(raw["scene_fps"]) or raw["scene_fps"] <= 0:
        problems.append(f"scene_fps deve ser > 0: {raw['scene_fps']!r}")

    if "frames" not in raw:
        problems.append("frames ausente")
    elif not _is_int(raw["frames"]) or raw["frames"] < 0:
        problems.append(f"frames invalido: {raw['frames']!r}")
    else:
        actual = count_frames(clip_dir)
        if actual != raw["frames"]:
            problems.append(
                f"contagem de f*.png ({actual}) difere de frames ({raw['frames']})"
            )

    if "desc" not in raw:
        problems.append("desc ausente")
    elif not isinstance(raw["desc"], str):
        problems.append("desc deve ser string")

    if "conditions" in raw:
        conds = raw["conditions"]
        if not isinstance(conds, dict):
            problems.append("conditions deve ser objeto")
        else:
            for key, val in conds.items():
                if key not in CONDITION_KEYS:
                    problems.append(f"condicao desconhecida: {key!r}")
                elif not isinstance(val, str) or not val:
                    problems.append(f"condicao {key!r} deve ter valor texto nao vazio")

    if "provenance" in raw and not isinstance(raw["provenance"], dict):
        problems.append("provenance deve ser objeto")

    if "expected" in raw:
        problems.extend(_validate_expected(raw["expected"]))

    if "issues" in raw:
        issues = raw["issues"]
        if not isinstance(issues, list) or not all(_is_int(v) for v in issues):
            problems.append("issues deve ser lista de inteiros")

    regions_path = clip_dir / "regions.json"
    if regions_path.exists():
        try:
            _read_json_dict(regions_path, "regions.json")
        except ClipError as exc:
            problems.append(str(exc))

    return problems


def write_clip_json(clip_dir, data: dict) -> Path:
    """Grava ``clip.json`` (garantindo ``version`` v2 se omitida)."""
    clip_dir = Path(clip_dir)
    payload = dict(data)
    payload.setdefault("version", CLIP_JSON_VERSION)
    out_path = clip_dir / "clip.json"
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_path
