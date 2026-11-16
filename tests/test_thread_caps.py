"""Teto combinado de threads: padroes dos pools ORT e do OpenCV.

Medido na mesa do Lucas (2026-11-02): pools 4+8+16 somavam
550,8% de CPU desenhando; 2+4 mediram 289,8% com passada igual.
Os padroes viram detector 3 + tinta 4 + OpenCV 4, com env
mandando em todos, como antes. A parte do OpenCV mora no app,
ainda nao migrada.
"""

from draw import perception


def test_detector_default_is_three(monkeypatch):
    monkeypatch.delenv("DRAW_ORT_THREADS", raising=False)
    assert perception._ort_intra_threads() == 3
    monkeypatch.setenv("DRAW_ORT_THREADS", "5")
    assert perception._ort_intra_threads() == 5
    monkeypatch.setenv("DRAW_ORT_THREADS", "invalido")
    assert perception._ort_intra_threads() == 3
