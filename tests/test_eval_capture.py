"""lab/eval_capture.py: métricas puras, avaliação por bundle e o laço real.

O laço dirigido (run_pipeline) roda com modelos ONNX de teste gerados
na hora (onnx_fixtures) e detector clássico grampeado — o valor é
exercitar Pipeline + PageCleanWorker reais sem thread e sem câmera.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab import eval_capture as ec  # noqa: E402

onnx_fixtures = pytest.importorskip("onnx_fixtures")  # noqa: E402


def test_pixel_metrics_perfeito():
    mask = np.zeros((10, 10), bool)
    mask[2:5, 2:5] = True
    got = ec.pixel_metrics(mask, mask.copy())
    assert got["iou"] == 1.0 and got["precision"] == 1.0 and got["recall"] == 1.0
    assert got["tp"] == 9 and got["fp"] == 0 and got["fn"] == 0


def test_pixel_metrics_disjunto_e_vazio():
    a = np.zeros((10, 10), bool)
    b = np.zeros((10, 10), bool)
    a[:2] = True
    b[8:] = True
    got = ec.pixel_metrics(a, b)
    assert got["iou"] == 0.0 and got["recall"] == 0.0
    assert (
        ec.pixel_metrics(np.zeros((10, 10), bool), np.zeros((10, 10), bool))["iou"]
        == 1.0
    )
    with pytest.raises(ValueError):
        ec.pixel_metrics(np.zeros((4, 4), bool), np.zeros((5, 5), bool))


def test_compare_masks_status_por_traco():
    truth = np.zeros((20, 20), bool)
    truth[2:4, 2:4] = True
    pred = np.zeros((20, 20), bool)
    pred[2:4, 2:4] = True  # captured
    s1 = np.zeros((20, 20), bool)
    s1[2:4, 2:4] = True  # captured
    s2 = np.zeros((20, 20), bool)
    s2[10:14, 10:14] = True  # lost
    s3 = np.zeros((20, 20), bool)
    s3[16:18, 16:18] = True
    pred[16, 16] = True  # partial (recall < 0.5)
    report = ec.compare_masks(pred, truth, [s1, s2, s3])
    statuses = [s["status"] for s in report["strokes"]]
    assert statuses == ["captured", "lost", "partial"]
    assert report["stroke_counts"]["captured"] == 1
    with pytest.raises(ValueError):
        ec.compare_masks(pred, truth, [], stroke_recall=0)


def _write_bundle(path, **fields):
    base = {
        "version": np.array(1),
        "ink_full": np.zeros((40, 40), np.uint8),
        "page_ink_full": np.zeros((30, 30), np.uint8),
        "page_to_scene": np.eye(3, dtype=np.float64),
        "points": np.zeros((0, 2), np.int32),
        "offsets": np.zeros(1, np.int64),
        "thickness": np.zeros(0, np.int64),
    }
    base.update(fields)
    np.savez(path, **base)


def test_evaluate_canvas_prefere_ink_final_ao_ink_full(tmp_path):
    """O GT de fim de vídeo é a tinta sobrevivente, não a tinta total."""
    ink_full = np.zeros((40, 40), np.uint8)
    ink_full[:10] = 1  # apagado depois: só em ink_full
    ink_final = np.zeros((40, 40), np.uint8)
    ink_final[30:] = 1  # o que sobrevive
    bundle = tmp_path / "gt.npz"
    _write_bundle(bundle, ink_full=ink_full, ink_final=ink_final)
    pred = np.zeros((40, 40), bool)
    pred[30:] = True  # acertou só o estado final
    report = ec.evaluate_canvas(pred, bundle, canvas_space="scene")
    assert report["recall"] == 1.0 and report["precision"] == 1.0


def test_evaluate_canvas_sem_ink_final_cai_no_ink_full(tmp_path):
    ink_full = np.zeros((40, 40), np.uint8)
    ink_full[5:8] = 1
    bundle = tmp_path / "gt.npz"
    _write_bundle(bundle, ink_full=ink_full)
    pred = np.zeros((40, 40), bool)
    report = ec.evaluate_canvas(pred, bundle, canvas_space="scene")
    assert report["recall"] == 0.0 and report["gt_pixels"] == 120


def test_evaluate_canvas_npy_sem_cantos_exige_bundle(tmp_path):
    np.save(tmp_path / "gt.npy", np.zeros((30, 30), np.uint8))
    with pytest.raises(ValueError, match="corners|bundle"):
        ec.evaluate_canvas(
            np.zeros((30, 30), bool), tmp_path / "gt.npy", canvas_space="page"
        )


def test_load_canvas_npy_e_imagem(tmp_path):
    np.save(tmp_path / "m.npy", np.array([[0, 255], [255, 0]], np.uint8))
    got = ec.load_canvas(tmp_path / "m.npy")
    assert got.dtype == bool and got[0, 1] and got[1, 0]
    import cv2

    cv2.imwrite(str(tmp_path / "i.png"), np.array([[200, 10], [10, 200]], np.uint8))
    got = ec.load_canvas(tmp_path / "i.png", kind="image")
    assert got[1, 0] and got[0, 1] and not got[0, 0]


class _FakeNeural:
    def __init__(self):
        self.last_presence_logit = 5.0
        self.last_coverage_mask = np.full((120, 160), 255, np.uint8)
        self.last_hand_mask = np.zeros((120, 160), np.uint8)

    def __call__(self, frame, *, return_mask=True):
        corners = np.array(
            [[10, 10], [150, 10], [150, 110], [10, 110]], dtype=np.float32
        )
        return corners, "paper", np.ones(frame.shape[:2], np.uint8)


def test_detector_sincrono_publica_contrato():
    det = ec._SynchronousDetector(_FakeNeural())
    frame = np.zeros((120, 160, 3), np.uint8)
    det.submit(frame, 1.5, 7)
    result = det.poll(0)
    assert result.sequence == 1
    assert result.verdict == "paper"
    assert result.captured_at == 1.5
    assert result.coverage_mask is not None and result.coverage_mask.any()
    assert result.hand_mask is not None
    assert det.poll(0) is result  # mesma sequência não republica
    assert det.poll(1) is None


class _FakeCapture:
    """VideoCapture de mentira: folha clara com um traço escuro."""

    def __init__(self, frames, corners=(20, 10, 200, 150)):
        self._frames = frames
        self._index = 0
        self._corners = corners

    def isOpened(self):
        return True

    def get(self, prop):
        return 10.0

    def read(self):
        if self._index >= self._frames:
            return False, None
        self._index += 1
        frame = np.zeros((240, 320, 3), np.uint8)
        x0, y0, x1, y1 = self._corners
        frame[y0:y1, x0:x1] = 220  # folha
        frame[60:80, 60:160] = 20  # "tinta" escura dentro da folha
        return True, frame

    def release(self):
        pass


def test_run_pipeline_dirige_pipeline_real(tmp_path, monkeypatch):
    """Laço de ponta a ponta sem thread: detecção grampeada + worker ONNX."""

    from draw import paper as paper_module

    onnx_path = onnx_fixtures.page_clean_model(
        tmp_path / "pc.onnx", patch=256, dynamic_batch=True
    )
    corners = np.array([[20, 10], [200, 10], [200, 150], [20, 150]], dtype=np.float32)
    monkeypatch.setattr(
        paper_module,
        "detect_sheet_with_confidence",
        lambda frame: (corners.copy(), "paper"),
    )
    capture = _FakeCapture(frames=40)
    result = ec.run_pipeline(
        capture,
        fps=10,
        neural_model=None,
        page_clean_model=str(onnx_path),
        hand_model="__none__",
        verify=None,
    )
    assert result["frames"] == 40
    assert result["mode"] == "page_clean"
    assert result["detections"] > 0
    assert result["ink_passes"] is not None and result["ink_passes"] > 0
    assert result["status"] == "ok"
    # O modelo didático (logit = luminância) deve ter confirmado a
    # região escura como tinta.
    assert result["mask"] is not None and result["mask"].any()


def test_run_pipeline_rejeita_captura_fechada(tmp_path):
    class _Closed:
        def isOpened(self):
            return False

    with pytest.raises(ValueError, match="fonte de vídeo"):
        ec.run_pipeline(_Closed(), fps=10, page_clean_model="x.onnx", verify=None)


def test_run_pipeline_rejeita_fps_invalido(tmp_path):
    class _NoFps(_FakeCapture):
        def get(self, prop):
            return 0.0

    with pytest.raises(ValueError, match="FPS"):
        ec.run_pipeline(_NoFps(1), page_clean_model="x.onnx", verify=None)


def test_evaluate_canvas_projeta_gt_por_cada_ancora(tmp_path):
    # Folha andou no meio do vídeo: a tinta confirmada caiu nas duas
    # poses. Projetar o GT só pela âncora final perderia a metade
    # inicial — a união por quadro é a comparação justa.
    from lab.eval_capture import evaluate_canvas

    h, w = 40, 60
    scene_gt = np.zeros((h, w), np.uint8)
    scene_gt[5:15, 5:15] = 1
    scene_gt[20:30, 20:30] = 1
    gt_path = tmp_path / "gt.npy"
    np.save(gt_path, scene_gt)

    a1 = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    a2 = np.float32([[4, 0], [w + 4, 0], [w + 4, h], [4, h]])
    # Canvas: o traço 1 ficou sob a1, o traço 2 sob a2 (pose nova).
    prediction = np.zeros((h, w), np.uint8)
    prediction[5:15, 5:15] = 1
    prediction[20:30, 24:34] = 1

    single = evaluate_canvas(
        prediction, gt_path, canvas_space="page", corners=a2, anchors=None
    )
    multi = evaluate_canvas(
        prediction, gt_path, canvas_space="page", corners=a2, anchors=[a1]
    )
    assert multi["alignment"] == "per_frame_anchors"
    assert multi["iou"] > single["iou"]
