"""Resultados de replay do corpus, deltas e serializacao JSONL."""

import dataclasses
import json
import math
from pathlib import Path


def _safe_float(value, default=0.0) -> float:
    if value is None:
        return float(default)
    val = float(value)
    return val


def _json_float(value: float) -> float | None:
    if math.isnan(value) or math.isinf(value):
        return None
    return float(value)


@dataclasses.dataclass
class ClipResult:
    """Metricas e vereditos de uma combinacao (clipe, bundle)."""

    clip: str
    bundle: str
    flags: list
    frames: int
    canvas_px: int
    provisional_median_px: float
    provisional_last_px: float
    retracted_px_total: int
    passes: int
    wall_s: float
    cpu_s_per_scene_s: float
    writing_px: int | None = None
    ruling_px: int | None = None
    expected_verdicts: list = dataclasses.field(default_factory=list)
    error: str | None = None

    @classmethod
    def from_run_dict(cls, clip, bundle, flags, d: dict) -> "ClipResult":
        """Converte o dicionario de ``bench_ink.run_clip`` descartando ``_canvas``."""
        return cls(
            clip=str(clip),
            bundle=str(bundle),
            flags=list(flags),
            frames=int(d.get("frames", 0)),
            canvas_px=int(d.get("canvas_px", 0)),
            provisional_median_px=_safe_float(d.get("provisional_median_px")),
            provisional_last_px=_safe_float(d.get("provisional_last_px")),
            retracted_px_total=int(d.get("retracted_px_total", 0)),
            passes=int(d.get("passes", 0)),
            wall_s=_safe_float(d.get("wall_s")),
            cpu_s_per_scene_s=_safe_float(
                d.get("cpu_s_per_scene_s"), default=float("nan")
            ),
            writing_px=(None if d.get("writing_px") is None else int(d["writing_px"])),
            ruling_px=(None if d.get("ruling_px") is None else int(d["ruling_px"])),
            expected_verdicts=list(d.get("expected_verdicts") or []),
            error=d.get("error"),
        )

    def to_dict(self) -> dict:
        """Serializa para dicionario seguro para JSON estrito."""
        return {
            "clip": self.clip,
            "bundle": self.bundle,
            "flags": list(self.flags),
            "frames": self.frames,
            "canvas_px": self.canvas_px,
            "provisional_median_px": _json_float(self.provisional_median_px),
            "provisional_last_px": _json_float(self.provisional_last_px),
            "retracted_px_total": self.retracted_px_total,
            "passes": self.passes,
            "wall_s": _json_float(self.wall_s),
            "cpu_s_per_scene_s": _json_float(self.cpu_s_per_scene_s),
            "writing_px": self.writing_px,
            "ruling_px": self.ruling_px,
            "expected_verdicts": list(self.expected_verdicts),
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ClipResult":
        """Reconstroi ``ClipResult`` a partir de dicionario desserializado."""
        return cls(
            clip=str(d["clip"]),
            bundle=str(d["bundle"]),
            flags=list(d.get("flags") or []),
            frames=int(d.get("frames", 0)),
            canvas_px=int(d.get("canvas_px", 0)),
            provisional_median_px=_safe_float(d.get("provisional_median_px")),
            provisional_last_px=_safe_float(d.get("provisional_last_px")),
            retracted_px_total=int(d.get("retracted_px_total", 0)),
            passes=int(d.get("passes", 0)),
            wall_s=_safe_float(d.get("wall_s")),
            cpu_s_per_scene_s=_safe_float(
                d.get("cpu_s_per_scene_s"), default=float("nan")
            ),
            writing_px=d.get("writing_px"),
            ruling_px=d.get("ruling_px"),
            expected_verdicts=list(d.get("expected_verdicts") or []),
            error=d.get("error"),
        )


def delta(base: ClipResult, cand: ClipResult) -> dict:
    """Diferenca ``cand - base`` para as metricas principais."""
    cpu_delta = (
        None
        if (math.isnan(base.cpu_s_per_scene_s) or math.isnan(cand.cpu_s_per_scene_s))
        else cand.cpu_s_per_scene_s - base.cpu_s_per_scene_s
    )
    return {
        "canvas_px_delta": cand.canvas_px - base.canvas_px,
        "canvas_px_ratio": (
            cand.canvas_px / base.canvas_px if base.canvas_px > 0 else None
        ),
        "provisional_delta": cand.provisional_median_px - base.provisional_median_px,
        "retracted_delta": cand.retracted_px_total - base.retracted_px_total,
        "passes_delta": cand.passes - base.passes,
        "cpu_delta": cpu_delta,
    }


def write_results(path, results: list[ClipResult]) -> Path:
    """Grava resultados em JSONL (um ``to_dict()`` por linha)."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(res.to_dict(), ensure_ascii=False) for res in results]
    text = ("\n".join(lines) + "\n") if lines else ""
    out_path.write_text(text, encoding="utf-8")
    return out_path


def load_results(path) -> list[ClipResult]:
    """Carrega lista de ``ClipResult`` de um arquivo JSONL."""
    in_path = Path(path)
    results = []
    for line in in_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            results.append(ClipResult.from_dict(json.loads(stripped)))
    return results
