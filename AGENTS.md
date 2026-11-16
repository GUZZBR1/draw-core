# Repository guidance

Read `docs/MIGRATION_SPEC.md` before changing anything.

- `src/draw/` is the runtime: only numpy, opencv-headless, onnxruntime (mediapipe optional). Never import torch/pandas.
- Stages exchange frozen dataclasses from `src/draw/contracts.py`, not dicts or tuples.
- Migrate one module per PR, with its tests; the PR must be CI-green.
- Do not add `DRAW_*` env flags; add fields to the config object instead.
- Models are never committed; `assets/manifest.json` holds sha256/size.
- Before finishing: `ruff check . && ruff format --check . && pytest -q`.
