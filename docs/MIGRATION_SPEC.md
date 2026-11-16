# Migration spec: santleme/draw -> draw-core

Status: draft for review. Legacy repo: `santleme/draw` (kept intact as the
historical lab; tag `legacy-final` marks the last state).

## Goal

A clean production repo for the real-time Draw engine: modular, typed
contracts between stages, fast test suite, and a boundary clean enough
that the hot path can later move to C++ without touching the rest.

## Rules for what gets copied

1. **Runtime imports no training stack.** `src/draw/` depends only on
   `numpy`, `opencv-python-headless`, `onnxruntime` (+ optional
   `mediapipe` extra). No `torch`, no `pandas`.
2. **Everything crosses stages through `contracts.py`.** Frozen
   dataclasses, no loose dicts or positional tuples between modules.
3. **Test-driven migration.** One module per PR, together with its tests.
   A module counts as migrated only when `pytest` is green in this repo.
4. **One PR per change.** Each PR is small, reviewable, and CI-green.
5. **No dead flags.** A `DRAW_*` flag survives only if it is on in the
   production configuration. Rejected or default-off experiments stay in
   legacy (see Flags).

## Target layout

```
draw-core/
├── pyproject.toml
├── assets/manifest.json        # sha256 of production models (not the binaries)
├── src/draw/
│   ├── contracts.py            # FramePacket, SheetQuad, InkState, PageIdentity
│   ├── infra/                  # safe_io, manifest verification, config, telemetry
│   ├── camera.py               # capture + latest-wins queue + FPS control
│   ├── perception.py           # ONNX sessions (sheet + ink), unified preprocess
│   ├── geometry.py             # corner fit, warp, optional ECC refine
│   ├── tracker.py              # SheetTracker + F-11 page identity state machine
│   ├── accumulator.py          # confirmed/provisional ink, votes, registration
│   ├── hand.py                 # optional hand presence/occlusion
│   ├── exporters.py            # SVG, DXF (locked scale), CAD bridge
│   └── pipeline.py             # frame -> events orchestration (threads)
├── lab/                        # replay, simulator, judges (not runtime)
├── site/                       # React site (moved as-is, own CI job)
├── bridge/                     # Windows camera helper
└── tests/
```

Separate repo `draw-training` (not created yet): `training/`, dataset
tools, labeling, Kaggle runner, `draw/selflearn/`, `gpu_augmenter.py`.
It delivers only approved `.onnx` files + hashes to `assets/manifest.json`.

## Contracts (first sketch, to be refined in the contracts PR)

- `FramePacket`: image (H,W,3 uint8), monotonic timestamp, sequence id.
- `SheetQuad`: 4x2 float32 corners in camera space, confidence,
  detector id, `present: bool`.
- `PageIdentity`: generation id, decision (`same` / `new_page` / `defer`),
  recall/containment evidence.
- `InkState`: confirmed mask, provisional mask, generation id, anchor corners.
- `Config`: immutable settings resolved once from env/CLI (replaces scattered
  `os.environ.get` calls; legacy has ~40 `DRAW_*` reads).

## Legacy inventory

| Legacy | Action | Destination |
|---|---|---|
| `draw/ink_layers.py` (4001 lines) | split | `accumulator.py` (+ `votes`, `registration`, `page_clean_worker`, `render`) |
| `draw/app.py`, `draw/loop.py` | split | `pipeline.py` + thin CLI; drop dead `ink_model` path and `legacy_ink` |
| `draw/neural.py` | split | `perception.py` (ONNX) + `geometry.py` (corner fit/refit) |
| `draw/sheet_track.py` | migrate | `tracker.py` |
| `draw/capture.py` | migrate | `camera.py` |
| `draw/paper.py`, `page_clean.py`, `view.py`, `lk_propagate.py` | migrate | engine |
| `draw/hand.py`, `hand_presence.py` | migrate | `hand.py` (mediapipe extra) |
| `draw/manifest.py`, `safe_io.py`, `config.py`, `telemetry.py`, `net_policy.py`, `session_report.py` | migrate | `infra/` |
| `draw/ink.py`, `draw/fusion.py` | verify use, then migrate or archive | - |
| `draw/gpu_augmenter.py`, `draw/selflearn/` | archive | `draw-training` |
| `tools/` replay, sim_*, judge*, eval_*, falsify, seg_metrics | migrate | `lab/` |
| `tools/` dataset, label, kaggle, runner, export/merge | archive | `draw-training` |
| `tools/replay_reregister*.py` | archive | hash-anchored; bytes must not change |
| `training/` | archive | `draw-training` |
| `site/`, `bridge/` | migrate | same names (monorepo) |
| `docs/` | keep README, SIMULATOR, SETUP_WINDOWS, a trimmed FALHAS | dated pre-registrations stay in legacy |

Tests: ~60 module tests migrate with their module; sim/judge/replay tests go
to `lab/`; training and selflearn tests go to `draw-training`; pre-registration
and doc-lint tests stay in legacy.

## Legacy loose files (decided)

| File | Decision | Why |
|---|---|---|
| `diag_live*.py` (8) | archive in legacy | one-off scripts with hardcoded `~/draw` paths; superseded by replay lab |
| `diag_live_desk.py` | keep idea, port later to `lab/desk_capture.py` | headless real-desk driver with flag support; needs path cleanup |
| `diag_quickdraw_*` | archive in legacy | depends on external `~/draw-lab/ink-data/quickdraw` corpus |
| `perf_sampler.py`, `summarize_perf.py` | migrate to `lab/perf/` (late) | per-thread CPU profiling is required before any C++ decision |
| `install-v6-swap.py`, `prove-v6-on-desk.py` | archive | one-time swap with hardcoded paths; result is recorded in the manifest |
| `r`, `pr76_comments.txt` | drop | run output / review dump, no lasting value |
| `draw-hack/` | drop (superseded by `site/`) | same pages/components as `site/`; extra README/asset only |
| `site/public/images/vision/sailor-moon-hair-wind.png` | exclude until rights confirmed | possible copyright issue |
| `models/lab/*.onnx`, `models/*.bak` | not migrated | experimental/rollback binaries; hashes of former production are in the manifest |

## Production models (assets/manifest.json)

Source of truth is the legacy manifest at `1fa3d76+3`:
sheet detector T16 `5e20a89f...`, page-clean v6 `613e250f...`, MediaPipe
hand landmarker (unmodified, Apache-2.0). Former production (`e20a89f0`,
`a470bd28`) is recorded only as rollback references.

## Flags policy

Legacy has ~40 `DRAW_*` variables, most default `0`. Process:

1. Ask which are on in the real desk configuration.
2. On in production -> become the default behavior, flag removed.
3. Off/rejected (e.g. `DRAW_ANCHOR_MOTION_ABSTAIN`, v1 anchor migration) ->
   stay in legacy, not copied.
4. Model paths and `DRAW_MODEL_STRICT` stay as real configuration.

## PR sequence

Every item is its own PR against `main`.

1. Scaffold: pyproject, ruff, CI, `.gitattributes`, manifest, this spec.
2. `contracts.py` + tests.
3. `infra/`: safe_io, manifest verification, config (+ tests).
4. `geometry.py` (+ `test_native_scale_parity`, neural quad guards).
5. `perception.py` (+ ONNX contract/preprocess tests).
6. `tracker.py` (+ sheet tracker, page identity, loss clock tests).
7. `camera.py` (+ capture tests).
8. `accumulator.py` split from `ink_layers.py`, in 2-3 PRs (votes,
   registration/identity, worker), each with its ink tests.
9. `hand.py`, `exporters.py`.
10. `pipeline.py` + CLI.
11. `lab/`: replay lab, simulator (with final-state GT), judges, falsifier.
12. `site/`, `bridge/`.
13. Parity gate: replay the same recorded sessions through legacy and
    this repo; deterministic core (geometry, tracker, accumulator) must match.

## Invariants to preserve

- Page identity (F-11): same page survives re-entry; distinct content is rejected.
- Export scale locked for DXF.
- GT end-of-video is `ink_final` (post-erase), per-phase pose via `quad_end`,
  dense scene->page maps when the page curls.
- Model sha256/size verified at load; mismatch refused unless explicitly relaxed.
- Latest-wins capture; worker rest/wake cadence.

## C++ (deferred)

Not in scope now. Revisit only after per-stage profiling (`lab/perf/`) shows a
stage dominated by non-ONNX Python time. Today ~12 FPS is dominated by ONNX
inference, which is already native. Boundary for a future port: the contract
types in `contracts.py`.

## Open questions

- Which `DRAW_*` flags are on in the desk configuration?
- Keep `draw/ink.py` / `fusion.py` (legacy ink stack) or drop?
- Release hosting for model binaries (Release in this repo vs legacy `models-2026-11-06`)?
- Rights for the sailor-moon image before it enters the site.
