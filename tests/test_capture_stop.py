"""Parada da captura sem liberar o driver no meio de um read() (draw/camera.py).

Na troca de camera com o app rodando, o stop() da fonte antiga nao pode
destruir o driver enquanto a thread ainda esta dentro de um read():
com force=False, quem libera e a propria thread, quando o read() volta.
"""

import threading

from draw.camera import LatestFrameCapture


class _BlockingCapture:
    def __init__(self):
        self.in_read = threading.Event()
        self.unblock = threading.Event()
        self.reading = False
        self.release_calls = 0
        self.released_during_read = False

    def isOpened(self):
        return True

    def read(self):
        self.reading = True
        self.in_read.set()
        self.unblock.wait(5.0)
        self.reading = False
        return False, None

    def release(self):
        self.release_calls += 1
        if self.reading:
            self.released_during_read = True
        self.unblock.set()


def _started():
    capture = _BlockingCapture()
    source = LatestFrameCapture(capture).start()
    assert capture.in_read.wait(2.0)
    return capture, source


def test_stop_without_force_never_releases_during_a_read():
    capture, source = _started()
    source.stop(force=False)
    assert capture.release_calls == 0
    capture.unblock.set()
    source._thread.join(2.0)
    assert capture.release_calls == 1
    assert capture.released_during_read is False


def test_stop_with_force_releases_once_even_though_the_pump_also_exits():
    capture, source = _started()
    source.stop()
    source._thread.join(2.0)
    assert capture.release_calls == 1
