# draw-core

Real-time bridge from paper to digital ink: webcam -> rectified sheet -> ink.
Clean production repo; the experimental history lives in `santleme/draw`.

See [`docs/MIGRATION_SPEC.md`](docs/MIGRATION_SPEC.md) for structure and plan.

```sh
pip install -e ".[dev]"
ruff check . && pytest -q
```
