"""Testes do comparador de lab/parity_e2e (o laço ponta a ponta em si
precisa do repo legado e dos binários dos modelos)."""

import json

import numpy as np
from lab.parity_e2e import compare


def _rec(i, present=True, corners=None):
    return {"frame": i, "present": present, "corners": corners}


def _mask(px):
    m = np.zeros((10, 10), bool)
    m.flat[:px] = True
    return m


def test_compare_identical():
    q = [[0, 0], [10, 0], [10, 10], [0, 10]]
    recs = [_rec(i, corners=q) for i in range(3)]
    masks = [_mask(20) for _ in range(3)]
    report = compare(recs, masks, recs, masks, iou_min=0.999, corner_tol=0.5)
    assert report["ok"] and report["frames"] == 3
    assert report["divergences"] == []


def test_compare_flags_each_kind():
    new = [_rec(0, corners=[[0, 0], [10, 0], [10, 10], [0, 10]])]
    old = [_rec(0, present=False, corners=None)]
    report = compare(new, [_mask(50)], old, [_mask(50)], iou_min=0.999, corner_tol=0.5)
    (div,) = report["divergences"]
    assert div["present"] == {"new": True, "legacy": False}
    assert "canvas_iou" not in div

    new = [_rec(1, corners=[[0, 0], [10, 0], [10, 10], [0, 10]])]
    old = [_rec(1, corners=[[0, 0], [12, 0], [10, 10], [0, 10]])]
    report = compare(new, [_mask(50)], old, [_mask(50)], iou_min=0.999, corner_tol=0.5)
    assert report["divergences"][0]["corner_max_delta_px"] == 2.0

    report = compare(
        [_rec(2)], [_mask(50)], [_rec(2)], [_mask(20)], iou_min=0.999, corner_tol=0.5
    )
    div = report["divergences"][0]
    assert div["canvas_iou"] == 0.4
    assert div["canvas_px"] == {"new": 50, "legacy": 20}


def test_compare_masks_empty_both_ok():
    report = compare(
        [_rec(0, present=False)],
        [_mask(0)],
        [_rec(0, present=False)],
        [_mask(0)],
        iou_min=0.999,
        corner_tol=0.5,
    )
    assert report["ok"]


def test_npz_keys_numeric_order(tmp_path):
    """arr_10 não pode vir antes de arr_2 — a ordem é numérica."""
    import numpy as np

    masks = [np.full((4, 4), i % 2, bool) for i in range(12)]
    np.savez_compressed(tmp_path / "c.npz", *masks)
    with np.load(tmp_path / "c.npz") as z:
        loaded = [z[k] for k in sorted(z.files, key=lambda k: int(k.split("_")[1]))]
    for i, m in enumerate(loaded):
        assert m[0, 0] == (i % 2)


def test_compare_corpus_vazio_falha():
    from lab.parity_e2e import compare

    report = compare([], [], [], [], iou_min=0.999, corner_tol=0.5)
    assert report["ok"] is False
    assert "frames" in report["error"] or "corpus" in report["error"]


def test_compare_shape_transposta_conta_divergencia():
    from lab.parity_e2e import compare

    new = [{"frame": 0, "present": True, "corners": None}]
    old = [{"frame": 0, "present": True, "corners": None}]
    nm = np.zeros((600, 800), np.uint8)
    om = np.zeros((800, 600), np.uint8)  # mesmo size, shape transposto
    report = compare(new, [nm], old, [om], iou_min=0.999, corner_tol=0.5)
    assert report["ok"] is False
    assert report["divergences"][0]["canvas_shape"]


def test_run_legacy_limpa_env_draw(monkeypatch, tmp_path):
    import subprocess

    from lab import parity_e2e

    monkeypatch.setenv("DRAW_INK_REMOVAL", "0")
    monkeypatch.setenv("DRAW_MODEL_STRICT", "0")
    monkeypatch.setenv("PATH", "/usr/bin")
    seen = {}

    def fake_run(cmd, env=None, **kw):
        seen["env"] = env
        (tmp_path / "telemetry.json").write_text(json.dumps({"frames": []}))
        np.savez_compressed(tmp_path / "canvas.npz")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(parity_e2e.subprocess, "run", fake_run)
    parity_e2e.run_legacy(tmp_path, tmp_path, tmp_path, frames=1, fps=1.0,
                          sheet_model="s.onnx", ink_model="i.onnx")
    assert "DRAW_INK_REMOVAL" not in seen["env"]
    assert "DRAW_MODEL_STRICT" not in seen["env"]
    assert seen["env"]["PYTHONPATH"] == str(tmp_path)
    assert seen["env"]["PATH"] == "/usr/bin"
