"""Ciclo de vida dos hvcam-host.exe gerenciados pelo Draw (pacote draw.hvcam)."""

import atexit
import subprocess

_MANAGED_HOST_PROCS = set()


def _terminate_host_process(proc):
    """Encerra um hvcam-host.exe iniciado pelo Draw, sem vazar processo."""
    if proc is None:
        return
    _MANAGED_HOST_PROCS.discard(proc)
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2.0)
    except OSError:
        pass
    finally:
        for stream in (
            getattr(proc, "stdout", None),
            getattr(proc, "stderr", None),
            getattr(proc, "stdin", None),
        ):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass


def _cleanup_managed_hosts():
    for proc in list(_MANAGED_HOST_PROCS):
        _terminate_host_process(proc)


atexit.register(_cleanup_managed_hosts)
