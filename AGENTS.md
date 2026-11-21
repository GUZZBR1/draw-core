# Repository guidance

Read `docs/MIGRATION_SPEC.md` before changing anything.

- `src/draw/` is the runtime: only numpy, opencv-headless, onnxruntime (mediapipe optional). Never import torch/pandas.
- Stages exchange frozen dataclasses from `src/draw/contracts.py`, not dicts or tuples. During the migration, modules keep their legacy return shapes (tuples) until the integration PR adapts them to `contracts`; do not widen those shapes.
- Migrate one module per PR, with its tests; the PR must be CI-green. Modules with a hard mutual dependency (for example `geometry` needs `paper`/`config`, the ink engine's parts) may share a PR; say so in the description.
- Every migration PR is based on `main` and must pass CI on its own: no imports from, and no reliance on, other open PRs. Files two PRs must both change (for example `pyproject.toml`) get byte-identical edits.
- Model integrity is fail-closed: loaders take a required keyword `verify` (a callable, or an explicit `None` opt-out). The pipeline injects `draw.infra.manifest.verify_model`.
- Do not add `DRAW_*` env flags; add fields to the config object instead. The only environment read allowed in the runtime is `DRAW_MODEL_STRICT`.
- Models are never committed; `assets/manifest.json` holds sha256/size.
- During iteration, run only the touched module's tests (`pytest tests/test_<module>.py`), not the full suite.
- Before finishing: `ruff check . && ruff format --check . && pytest -q`.
