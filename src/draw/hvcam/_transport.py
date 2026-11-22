"""Escuta AF_HYPERV limitada para o modo reverse (pacote draw.hvcam)."""

import errno
import selectors
import socket
import time

from ._wire import _LISTEN_TIMEOUT_MS


def _listen_vsock_bounded(
    port,
    timeout_ms=_LISTEN_TIMEOUT_MS,
    *,
    socket_factory=socket.socket,
    selector_factory=selectors.DefaultSelector,
    clock=time.monotonic,
    on_listening=None,
    abort_check=None,
):
    """Escuta em AF_VSOCK com prazo de accept e exige peer CID do host (2).

    `hvcam_listen` da libhvcam C chama `accept()` bloqueante sem prazo e
    sem checar o CID de origem; aqui o listener fecha no timeout com
    `-ETIMEDOUT` (para nao travar o startup nem o `--check`) e descarta
    conexoes que nao venham de `VMADDR_CID_HOST`.

    `on_listening`, se fornecido, roda logo apos `listen(1)` (ideal para
    subir `hvcam-host.exe --reverse` sem corrida de 30 s no AF_HYPERV).
    `abort_check`, se fornecido, e consultado periodicamente para abortar
    cedo caso o processo host tenha saido com erro.
    """
    if timeout_ms is not None and timeout_ms <= 0:
        return -errno.ETIMEDOUT
    af_vsock = getattr(socket, "AF_VSOCK", 40)
    cid_any = getattr(socket, "VMADDR_CID_ANY", 0xFFFFFFFF)
    cid_host = getattr(socket, "VMADDR_CID_HOST", 2)
    try:
        listener = socket_factory(af_vsock, socket.SOCK_STREAM)
    except OSError as error:
        return -(error.errno or errno.EIO)
    try:
        listener.setblocking(False)
        listener.bind((cid_any, int(port)))
        listener.listen(1)
        if on_listening is not None:
            on_listening()
        deadline = None if timeout_ms is None else clock() + (timeout_ms / 1000.0)
        with selector_factory() as selector:
            selector.register(listener, selectors.EVENT_READ)
            while True:
                if abort_check is not None and abort_check():
                    return -errno.ECONNABORTED
                remaining = None if deadline is None else deadline - clock()
                if remaining is not None and remaining <= 0:
                    return -errno.ETIMEDOUT
                wait_s = remaining
                if abort_check is not None:
                    wait_s = 0.2 if wait_s is None else min(wait_s, 0.2)
                if not selector.select(wait_s):
                    if abort_check is not None:
                        continue
                    return -errno.ETIMEDOUT
                try:
                    conn, peer = listener.accept()
                except BlockingIOError:
                    continue
                peer_cid = (
                    peer[0] if isinstance(peer, tuple) and len(peer) >= 1 else None
                )
                if peer_cid != cid_host:
                    conn.close()
                    continue
                conn.setblocking(True)
                return conn.detach()
    except OSError as error:
        return -(error.errno or errno.EIO)
    finally:
        listener.close()
