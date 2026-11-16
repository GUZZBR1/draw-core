"""Testes do simulador sintetico: fonte, texto e GT (sem pipeline).

So os testes que nao rodam o pipeline nem tocam eval_capture/draw.*:
o que depende do avaliador (evaluate_canvas/load_canvas/metricas,
run_pipeline, CLIs) fica de fora ate a migracao daquele modulo.
"""

import json

import cv2
import numpy as np
import pytest
from lab import gen_synthetic as gs
from lab.sim_source import SyntheticCapture, export_video
from lab.sim_text import plan_text_strokes


def raster(specs, shape=(510, 360)):
    mask = np.zeros(shape, np.uint8)
    paper = np.full((*shape, 3), 255, np.uint8)
    for spec in specs:
        gs._apply_stroke(paper, mask, spec)
    return mask


def test_text_has_reproducible_resolved_curves_and_distinct_glyphs():
    def plan(text, seed=2):
        return plan_text_strokes(text, np.random.default_rng(seed), 360, 510)

    a, b = plan("Olá, Draw! 123"), plan("Olá, Draw! 123")
    assert len(a) == len(b)
    assert all(spec[:3] == other[:3] for spec, other in zip(a, b, strict=False))
    assert all(np.array_equal(s[3], t[3]) for s, t in zip(a, b, strict=False))
    assert all(s[0] == "curve" and s[3].dtype == np.int32 for s in a)
    assert not np.array_equal(raster(plan("a")), raster(plan("b")))
    assert not np.array_equal(raster(a), raster(plan("Olá, Draw! 123", seed=5)))
    assert np.array_equal(raster(plan("ação")), raster(plan("ac\u0327a\u0303o")))


def test_ligatures_pen_lifts_and_line_wrap():
    rng = np.random.default_rng
    linked = plan_text_strokes("ab", rng(1), 360, 510)
    separate = plan_text_strokes("ab", rng(1), 360, 510, ligatures=False)
    assert len(linked) == len(separate) + 1
    # i = haste + ponto; espaço e newline não ganham ligaduras.
    assert len(plan_text_strokes("i i\ni", rng(1), 360, 510)) == 6
    specs = plan_text_strokes("a" * 30, rng(1), 360, 510)
    assert max(s[3][:, 1].max() for s in specs) > 100
    assert raster(specs).sum() > 0


@pytest.mark.parametrize("text", ["🙂", "字", "a" * 1000])
def test_writer_rejects_unsupported_or_overflow(text):
    with pytest.raises(ValueError):
        plan_text_strokes(text, np.random.default_rng(1), 360, 510)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"fps": 0},
        {"fps": float("nan")},
        {"stroke_seconds": 0},
        {"settle_seconds": -1},
        {"height": float("inf")},
    ],
)
def test_source_rejects_invalid_timing_and_layout(kwargs):
    with pytest.raises(ValueError):
        SyntheticCapture("a", **kwargs)


def test_source_progressive_cumulative_deterministic_and_finite():
    options = dict(fps=4, stroke_seconds=1, warmup_seconds=0, settle_seconds=0)
    source, twin = SyntheticCapture("ab", **options), SyntheticCapture("ab", **options)
    assert np.all(source.quad >= 24) and np.all(source.quad <= gs.SIZE - 24)
    previous = np.zeros((512, 512), bool)
    areas = []
    for index in range(source.frame_count):
        ok, frame = source.read()
        other_ok, other = twin.read()
        assert ok and other_ok and np.array_equal(frame, other)
        assert frame.shape == (512, 512, 3) and frame.dtype == np.uint8
        current = source.last_scene["ink_full"] > 0
        assert np.all(current[previous])
        previous = current.copy()
        areas.append(int(current.sum()))
        assert source.get(cv2.CAP_PROP_POS_FRAMES) == index + 1
    assert areas[0] == 0 < areas[1] < areas[4]
    assert np.array_equal(source.last_scene["ink_full"], source.ink_full)
    assert source.read() == (False, None)
    assert source.isOpened()  # como VideoCapture depois de EOF
    assert source.get(cv2.CAP_PROP_FRAME_COUNT) == len(areas)
    assert source.get(cv2.CAP_PROP_FRAME_WIDTH) == 512
    assert source.get(cv2.CAP_PROP_FPS) == 4
    assert source.get(-100) == 0
    source.release()
    assert not source.isOpened() and source.read() == (False, None)
    twin.release()


def test_hand_occludes_visible_ink_but_not_ground_truth():
    source = SyntheticCapture("laços", fps=4, stroke_seconds=0.5, hand=True)
    covered = 0
    while source.read()[0]:
        scene = source.last_scene
        hidden = (scene["mask"] == gs.HAND) & (scene["ink_full"] > 0)
        covered += int(hidden.sum())
        assert not np.any(scene["mask"][hidden] == gs.INK)
    assert covered > 0
    assert not np.any(source.last_scene["mask"] == gs.HAND)
    assert np.array_equal(source.last_scene["ink_full"], source.ink_full)
    source.release()


def test_video_export_decodes_and_gt_matches_planned_geometry(tmp_path):
    source = SyntheticCapture("Oi!", fps=4, stroke_seconds=0.25, settle_seconds=0.5)
    path = tmp_path / "sim.mp4"
    manifest = export_video(source, path)
    assert not source.isOpened()
    reader = cv2.VideoCapture(str(path))
    decoded = 0
    try:
        assert reader.isOpened() and reader.get(cv2.CAP_PROP_FPS) == 4
        while True:
            ok, frame = reader.read()
            if not ok:
                break
            assert frame.shape == (512, 512, 3)
            decoded += 1
    finally:
        reader.release()
    assert decoded == manifest["frames"]
    assert json.loads(path.with_suffix(".json").read_text()) == manifest
    with np.load(path.with_suffix(".gt.npz"), allow_pickle=False) as bundle:
        assert np.array_equal(bundle["page_ink_full"], raster(source.specs))
        assert np.array_equal(bundle["ink_full"], source.ink_full)
    assert np.array_equal(np.load(tmp_path / "sim_ink_full.npy"), source.ink_full)
    with pytest.raises(ValueError, match="frame zero"):
        export_video(source, tmp_path / "again.mp4")
