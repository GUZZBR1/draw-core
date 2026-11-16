"""HandMasker sobre um mediapipe falso (sys.modules).

O mediapipe e extra opcional: importar draw.hand nunca depende
dele, e toda falha (pacote, arquivo, criacao) degrada para "sem
mascara". O landmarker fecha deterministicamente por close() —
idempotente e via context manager —, nunca por __del__.
"""

import sys
import types
from types import SimpleNamespace

import numpy as np
import pytest

from draw import hand as hand_module


def _landmarks_result():
    hand = [
        SimpleNamespace(x=0.10 + 0.01 * (i % 5), y=0.10 + 0.01 * (i // 5))
        for i in range(21)
    ]
    return SimpleNamespace(hand_landmarks=[hand])


class _StubLandmarker:
    def __init__(self, mode, log, raise_video_detect=False, close_raises=False):
        self._mode = mode
        self._log = log
        self._raise_video_detect = raise_video_detect
        self._close_raises = close_raises
        self.closed = 0

    def detect(self, _image):
        self._log.append(("image", self._mode))
        return _landmarks_result()

    def detect_for_video(self, _image, timestamp_ms):
        self._log.append(("video", timestamp_ms))
        if self._raise_video_detect:
            raise RuntimeError("detect_for_video falhou neste stub")
        return _landmarks_result()

    def close(self):
        self.closed += 1
        if self._close_raises:
            raise RuntimeError("close falhou neste stub")


def _install_fake_mediapipe(
    monkeypatch, fail_video=False, raise_video_detect=False, close_raises=False
):
    log = []
    created = []

    class _RunningMode:
        IMAGE = "image"
        VIDEO = "video"

    def _create(options):
        mode = options.running_mode
        if fail_video and mode == _RunningMode.VIDEO:
            raise RuntimeError("sem video neste stub")
        landmarker = _StubLandmarker(
            mode,
            log,
            raise_video_detect=raise_video_detect,
            close_raises=close_raises,
        )
        created.append(landmarker)
        return landmarker

    vision = SimpleNamespace(
        RunningMode=_RunningMode,
        HandLandmarkerOptions=lambda **kwargs: SimpleNamespace(**kwargs),
        HandLandmarker=SimpleNamespace(create_from_options=_create),
    )
    fake = types.ModuleType("mediapipe")
    fake.tasks = SimpleNamespace(
        BaseOptions=lambda **kwargs: SimpleNamespace(**kwargs),
        vision=vision,
    )
    fake.Image = lambda **kwargs: SimpleNamespace(**kwargs)
    fake.ImageFormat = SimpleNamespace(SRGB="srgb")
    monkeypatch.setitem(sys.modules, "mediapipe", fake)
    return log, created


def _model(tmp_path):
    model = tmp_path / "hand_landmarker.task"
    model.write_bytes(b"stub")
    return str(model)


def test_import_and_mask_without_mediapipe_degrade_once(tmp_path, capsys, monkeypatch):
    # O pacote e extra opcional: importar draw.hand ja aconteceu no
    # topo; sys.modules[...] = None forca o ImportError do uso.
    monkeypatch.setitem(sys.modules, "mediapipe", None)
    masker = hand_module.HandMasker(_model(tmp_path), verify=None)
    frame = np.zeros((40, 50, 3), dtype=np.uint8)
    assert masker.mask(frame) is None
    assert masker.mask(frame) is None
    assert capsys.readouterr().out.count("mascara de mao indisponivel") == 1


def test_verify_receives_the_resolved_model_path(tmp_path):
    calls = []
    masker = hand_module.HandMasker(_model(tmp_path), verify=calls.append)
    assert calls == [masker._requested_path]


def test_verify_is_a_required_named_argument(tmp_path):
    # Integridade fail-closed: esquecer o verificador e erro de
    # chamada, nao "desligado por acidente"; o None explicito e o
    # opt-out.
    with pytest.raises(TypeError):
        hand_module.HandMasker(_model(tmp_path))


def test_loading_uses_the_explicit_model_and_image_mode(monkeypatch, tmp_path):
    _log, created = _install_fake_mediapipe(monkeypatch)
    masker = hand_module.HandMasker(_model(tmp_path), verify=None)
    frame = np.zeros((80, 100, 3), dtype=np.uint8)
    mask = masker.mask(frame)
    assert len(created) == 1
    assert mask is not None and mask.shape == (80, 100)


def test_detected_hand_fills_scaled_hull_and_forearm(monkeypatch, tmp_path):
    _install_fake_mediapipe(monkeypatch)
    masker = hand_module.HandMasker(_model(tmp_path), verify=None)
    frame = np.zeros((80, 100, 3), dtype=np.uint8)
    mask = masker.mask(frame)
    assert mask is not None
    # Os marcos falsos cobrem ~15x15 px no canto; o casco escalado
    # de 1,3 + trapezio do antebraco + dilatacao de 15 px cobrem
    # bastante mais.
    assert np.count_nonzero(mask) > 15 * 15


def test_close_is_idempotent_and_permanent(monkeypatch, tmp_path):
    _log, created = _install_fake_mediapipe(monkeypatch)
    masker = hand_module.HandMasker(_model(tmp_path), verify=None)
    frame = np.zeros((80, 100, 3), dtype=np.uint8)
    assert masker.mask(frame) is not None
    assert len(created) == 1
    masker.close()
    masker.close()
    assert created[0].closed == 1
    # Depois do fechamento nao recria: mascara indisponivel.
    assert masker.mask(frame) is None
    assert len(created) == 1


def test_failed_video_inference_closes_the_landmarker(monkeypatch, tmp_path):
    _log, created = _install_fake_mediapipe(monkeypatch, raise_video_detect=True)
    masker = hand_module.HandMasker(_model(tmp_path), verify=None)
    frame = np.zeros((80, 100, 3), dtype=np.uint8)
    signature = masker.presence_signature(frame, timestamp_ms=1000)
    # O landmarker VIDEO falho fecha antes de ser descartado; a
    # presenca cai para o landmarker IMAGE recem-criado.
    assert created[0].closed == 1
    assert len(created) == 2
    assert signature is not None


def test_failed_video_inference_tolerates_a_broken_close(monkeypatch, tmp_path):
    _install_fake_mediapipe(monkeypatch, raise_video_detect=True, close_raises=True)
    masker = hand_module.HandMasker(_model(tmp_path), verify=None)
    frame = np.zeros((80, 100, 3), dtype=np.uint8)
    # O close do landmarker falho levanta, mas a degradacao para o
    # IMAGE nao pode ser derrubada por ele.
    signature = masker.presence_signature(frame, timestamp_ms=1000)
    assert signature is not None
    masker.close()


def test_close_also_closes_the_video_landmarker(monkeypatch, tmp_path):
    _log, created = _install_fake_mediapipe(monkeypatch)
    masker = hand_module.HandMasker(_model(tmp_path), verify=None)
    frame = np.zeros((80, 100, 3), dtype=np.uint8)
    masker.presence_signature(frame, timestamp_ms=1000)
    masker.presence_signature(frame)
    assert len(created) == 2
    masker.close()
    assert all(landmarker.closed == 1 for landmarker in created)


def test_context_manager_closes(monkeypatch, tmp_path):
    _log, created = _install_fake_mediapipe(monkeypatch)
    frame = np.zeros((80, 100, 3), dtype=np.uint8)
    with hand_module.HandMasker(_model(tmp_path), verify=None) as masker:
        masker.mask(frame)
    assert created[0].closed == 1


def test_hand_model_available_requires_a_real_file(tmp_path):
    model = tmp_path / "hand_landmarker.task"
    assert hand_module.hand_model_available(str(model)) is False
    model.write_bytes(b"stub")
    assert hand_module.hand_model_available(str(model)) is True


def test_no_model_path_and_no_default_means_unavailable(tmp_path, monkeypatch):
    # Sem argumento e sem models/hand_landmarker.task convencional:
    # resolve None e a mascara degrada sem criar nada.
    monkeypatch.setattr(
        hand_module, "_DEFAULT_CANDIDATES", (str(tmp_path / "nada.task"),)
    )
    masker = hand_module.HandMasker(verify=None)
    assert masker.mask(np.zeros((10, 10, 3), dtype=np.uint8)) is None
