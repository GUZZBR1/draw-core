"""Lado legado do teste de paridade ponta a ponta.

Roda DENTRO do repo legado (PYTHONPATH apontado para ele): o pacote
`draw` deste processo é o antigo, com draw.loop.SheetInkLoop e os
adaptadores síncronos no protocolo de tuplas que ele espera. O lado
novo roda em lab/parity_e2e.py no draw-core, sobre o mesmo corpus e
os mesmos binários de modelo.

As 8 flags do conjunto validado (MIGRATION_SPEC, Tier A — commit
legado a95eec8 / docs/SIMULATOR.md) são ligadas AQUI, porque no
legado toda flag de comportamento nasce desligada e o default não é
a configuração validada; no draw-core elas são o default de
PipelineConfig/InkConfig.

Saída: out/telemetry.json (corners/present por frame) + out/canvas.npz
(clean_mask>0 de cada frame). Uso:

  PYTHONPATH=/caminho/do/draw python lab/parity_legacy_driver.py \
      --corpus <dir|video.mp4> --out <dir> [--frames N] [--fps 2.0]
"""

import argparse
import json
import os
from pathlib import Path

import cv2
import numpy as np

VALIDATED_FLAGS = (
    "DRAW_INK_FOLLOW_MOVE",
    "DRAW_SHEET_COVERAGE",
    "DRAW_CANVAS_PERSIST",
    "DRAW_INK_SKIP_STALE",
    "DRAW_INK_REMOVAL",
    "DRAW_SEG_HAND_OCCLUSION",
    "DRAW_ANCHOR_ARBITRATION",
    "DRAW_ANCHOR_FOLLOW",
)
for _flag in VALIDATED_FLAGS:
    os.environ[_flag] = "1"


def iter_frames(source, limit):
    """Frames de um diretório de imagens ou de um vídeo."""
    path = Path(source)
    if path.is_dir():
        files = sorted(
            p
            for p in path.iterdir()
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}
        )
        for i, f in enumerate(files):
            if i >= limit:
                break
            frame = cv2.imread(str(f))
            if frame is not None:
                yield i, frame
        return
    capture = cv2.VideoCapture(str(path))
    try:
        index = 0
        while index < limit:
            ok, frame = capture.read()
            if not ok:
                break
            yield index, frame
            index += 1
    finally:
        capture.release()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", type=int, default=120)
    ap.add_argument("--fps", type=float, default=2.0)
    ap.add_argument("--sheet-model", default="models/draw_seg_v3_dyn.onnx")
    ap.add_argument("--ink-model", default="models/page_clean_unet.onnx")
    args = ap.parse_args(argv)

    from draw.ink_layers import _PageCleanWorker
    from draw.loop import SheetInkLoop
    from draw.neural import NeuralSheetDetector
    from draw.sheet_track import _gate_info_from_trace

    from draw.app import _detect_sheet_combined_traced
    from draw.page_clean import PageCleanInk

    detector = NeuralSheetDetector(args.sheet_model)
    detector.load()
    page_clean = PageCleanInk(args.ink_model)
    page_clean.load()

    class Clock:
        def __init__(self, dt):
            self.dt = dt
            self.t = 0.0

        def __call__(self):
            return self.t

    clock = Clock(1.0 / args.fps)

    class SyncDet:
        """Protocolo de tuplas do laço legado, execução síncrona."""

        def __init__(self):
            self._result = None
            self._seq = 0
            self.error = None
            self.traces = []

        def submit(self, frame, captured_at, frame_index=None):
            outcome = _detect_sheet_combined_traced(frame, detector)
            corners, verdict, trace = outcome[0], outcome[1], outcome[2]
            extras = outcome[3] if len(outcome) > 3 else None
            self._seq += 1
            result = (self._seq, corners, verdict, captured_at, 1.0)
            gate = _gate_info_from_trace(trace)
            if gate is not None:
                result = result + (gate,)
            if extras is not None:
                if gate is None:
                    result = result + (None,)
                result = result + (extras,)
            self._result = result
            self.traces.append(trace)

        def poll(self, after_seq):
            if self._result is None or self._result[0] <= after_seq:
                return None
            return self._result

        def take_traces(self, upto_result_seq=None):
            return []

    det = SyncDet()
    worker = _PageCleanWorker(page_clean, None, clock=clock)
    loop = SheetInkLoop(
        detection_worker=det, ink_worker=worker, clock=clock, log=lambda *_a: None
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    records, canvases = [], []
    for idx, frame in iter_frames(args.corpus, args.frames):
        clock.t = idx * clock.dt
        loop.step(frame, clock.t * 1000.0)
        worker.pump()
        loop.collect_ink()
        if worker.error is not None:
            raise RuntimeError("trabalhadora de tinta legada falhou") from worker.error
        records.append(
            {
                "frame": idx,
                "present": loop.tracker.corners is not None,
                "corners": (
                    None
                    if loop.tracker.corners is None
                    else np.asarray(loop.tracker.corners, float).tolist()
                ),
            }
        )
        canvases.append(
            np.zeros((1, 1), bool)
            if loop.clean_mask is None
            else (np.asarray(loop.clean_mask) > 0)
        )
    (out / "telemetry.json").write_text(
        json.dumps({"frames": records, "flags": sorted(VALIDATED_FLAGS)}, indent=1)
    )
    np.savez_compressed(out / "canvas.npz", *canvases)
    print(json.dumps({"frames": len(records), "out": str(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
