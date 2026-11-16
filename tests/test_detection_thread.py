"""Detecção de folha em thread própria: o laço nunca espera.

O contrato, com um detector falso que bloqueia de propósito:

1. submit() volta na hora mesmo com a detecção travada.
2. Quadros submetidos durante uma detecção em voo são
   substituídos (latest-wins): só o mais novo roda depois, e a
   contagem de descartes registra os que ficaram pelo caminho.
3. O resultado carrega o carimbo de captura do quadro que foi
   detectado, não o instante em que a detecção terminou.

Cobre também o formato da tupla de resultado (5/6/7 elementos:
rastro, portão e extras de cobertura) e o parâmetro coverage da
trabalhadora, que decide se os extras da detecção são publicados.
"""

import threading
import time

import numpy as np
import pytest

from draw.tracker import SheetDetectionWorker, _gate_info_from_trace

CORNERS = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float32)
QUAD = np.array(
    [[100.0, 100.0], [500.0, 100.0], [500.0, 400.0], [100.0, 400.0]],
    dtype=np.float32,
)
WEAK = {"source": "neural", "presence_logit": 0.32, "edge_in": 0.001}


class _BlockingDetector:
    def __init__(self):
        self.release = threading.Event()
        self.seen = []

    def __call__(self, frame):
        self.seen.append(frame)
        self.release.wait(timeout=5.0)
        return CORNERS, "paper"


def _poll_until(worker, after_seq):
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        result = worker.poll(after_seq)
        if result is not None:
            return result
        time.sleep(0.002)
    raise AssertionError("trabalhadora não publicou resultado")


def _wait_result(worker, after_seq=0, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = worker.poll(after_seq)
        if result is not None:
            return result
        time.sleep(0.005)
    raise AssertionError("a detecção nunca publicou resultado")


@pytest.mark.slow
def test_submit_never_blocks_and_latest_wins():
    detector = _BlockingDetector()
    worker = SheetDetectionWorker(detector).start()
    try:
        first = np.full((4, 4, 3), 1, dtype=np.uint8)
        second = np.full((4, 4, 3), 2, dtype=np.uint8)
        third = np.full((4, 4, 3), 3, dtype=np.uint8)
        started = time.monotonic()
        worker.submit(first, 100.0)
        deadline = time.monotonic() + 5.0
        while not detector.seen and time.monotonic() < deadline:
            time.sleep(0.002)
        assert detector.seen, "a thread nunca pegou o primeiro quadro"
        worker.submit(second, 100.1)
        worker.submit(third, 100.2)
        assert time.monotonic() - started < 0.5
        detector.release.set()
        result = _wait_result(worker)
        _seq, corners, verdict, captured_at, _ms = result
        assert verdict == "paper"
        assert np.array_equal(corners, CORNERS)
        # O poll devolve o resultado mais novo: o do terceiro
        # quadro, com o carimbo dele, nao o do primeiro.
        deadline = time.monotonic() + 5.0
        while captured_at != 100.2 and time.monotonic() < deadline:
            newer = worker.poll(result[0])
            if newer is not None:
                result = newer
                captured_at = result[3]
            time.sleep(0.005)
        assert captured_at == 100.2
        stats = worker.stats()
        assert stats["detect_submitted"] == 3
        assert stats["detect_completed"] == 2
        assert stats["detect_dropped"] == 1
        assert detector.seen[0] is first
        assert detector.seen[1] is third
    finally:
        detector.release.set()
        worker.stop()


@pytest.mark.slow
def test_detector_error_is_kept_for_the_loop():
    def boom(_frame):
        raise RuntimeError("detector quebrou")

    worker = SheetDetectionWorker(boom).start()
    try:
        worker.submit(np.zeros((4, 4, 3), dtype=np.uint8), 1.0)
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and worker.error is None:
            time.sleep(0.005)
        assert isinstance(worker.error, RuntimeError)
    finally:
        worker.stop()


# ---------- pacote do portão: rastro -> trabalhadora ----------


def test_gate_info_from_trace():
    assert _gate_info_from_trace(None) is None
    assert _gate_info_from_trace({}) is None
    trace = {"source": "neural", "presence_logit": 0.32, "edge_in": 0.001}
    assert _gate_info_from_trace(trace) == trace


def test_worker_result_arity_with_and_without_trace():
    def detect_plain(_frame):
        return QUAD.copy(), "paper"

    worker = SheetDetectionWorker(detect_plain).start()
    try:
        worker.submit(np.zeros((8, 8, 3), np.uint8), 1.0, 0)
        result = _poll_until(worker, 0)
        assert len(result) == 5
    finally:
        worker.stop()

    def detect_traced(_frame):
        return QUAD.copy(), "paper", dict(WEAK)

    worker = SheetDetectionWorker(detect_traced).start()
    try:
        worker.submit(np.zeros((8, 8, 3), np.uint8), 1.0, 0)
        result = _poll_until(worker, 0)
        assert len(result) == 6
        assert result[5] == WEAK
    finally:
        worker.stop()


# ---------- extras de cobertura: parâmetro coverage ----------


def test_worker_forwards_extras_with_coverage_on():
    mask = np.zeros((8, 8), dtype=np.uint8)

    def detect_with_extras(_frame):
        return QUAD.copy(), "paper", None, {"coverage_mask": mask}

    worker = SheetDetectionWorker(detect_with_extras, coverage=True).start()
    try:
        worker.submit(np.zeros((8, 8, 3), np.uint8), 1.0, 0)
        result = _poll_until(worker, 0)
        assert len(result) == 7
        assert result[5] is None, "sem rastro de portão, a posição 5 fica vazia"
        assert result[6] == {"coverage_mask": mask}
    finally:
        worker.stop()


def test_worker_drops_extras_with_coverage_off():
    def detect_with_extras(_frame):
        return QUAD.copy(), "paper", None, {"coverage_mask": "x"}

    worker = SheetDetectionWorker(detect_with_extras, coverage=False).start()
    try:
        worker.submit(np.zeros((8, 8, 3), np.uint8), 1.0, 0)
        result = _poll_until(worker, 0)
        assert len(result) == 5, "sem cobertura o resultado é a tupla de sempre"
    finally:
        worker.stop()
