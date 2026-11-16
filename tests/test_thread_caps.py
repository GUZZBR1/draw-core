"""Teto combinado de threads: padroes dos pools ORT e do OpenCV.

Medido na mesa do Lucas (2026-11-02): pools 4+8+16 somavam
550,8% de CPU desenhando; 2+4 mediram 289,8% com passada igual.
Os padroes viram detector 3 + tinta 4 + OpenCV 4 — agora como
parametro de construtor, sem variaveis de ambiente no runtime.
A parte do OpenCV mora no app, ainda nao migrada.
"""

import sys
import types

from draw import perception


def _fake_ort(captured):
    fake = types.ModuleType("onnxruntime")

    class _Options:
        def __init__(self):
            self.intra_op_num_threads = None
            self.entries = []

        def add_session_config_entry(self, key, value):
            self.entries.append((key, value))

    def _session(path, sess_options, providers):
        captured["threads"] = sess_options.intra_op_num_threads
        captured["entries"] = sess_options.entries
        return object()

    fake.SessionOptions = _Options
    fake.InferenceSession = _session
    return fake


def test_intra_threads_default_is_three(monkeypatch, tmp_path):
    model = tmp_path / "m.onnx"
    model.write_bytes(b"x")
    captured = {}
    monkeypatch.setitem(sys.modules, "onnxruntime", _fake_ort(captured))
    perception._load_session(str(model), verify=None)
    assert captured["threads"] == 3


def test_intra_threads_param_overrides_default(monkeypatch, tmp_path):
    model = tmp_path / "m.onnx"
    model.write_bytes(b"x")
    captured = {}
    monkeypatch.setitem(sys.modules, "onnxruntime", _fake_ort(captured))
    perception._load_session(str(model), verify=None, intra_threads=5)
    assert captured["threads"] == 5


def test_session_always_runs_with_spin_disabled(monkeypatch, tmp_path):
    model = tmp_path / "m.onnx"
    model.write_bytes(b"x")
    captured = {}
    monkeypatch.setitem(sys.modules, "onnxruntime", _fake_ort(captured))
    perception._load_session(str(model), verify=None)
    assert ("session.intra_op.allow_spinning", "0") in captured["entries"]
    assert ("session.inter_op.allow_spinning", "0") in captured["entries"]
