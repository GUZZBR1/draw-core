"""Fumaça do bridge: windows_helper.py compila e é stdlib-only.

O helper é um esboço Windows (ctypes/SendInput) — importar teria
efeitos colaterais de plataforma, então o teste compila e varre os
imports via ast em vez de executar.
"""

import ast
import importlib.util
import py_compile
import socket
import struct
import threading
from pathlib import Path

HELPER = Path(__file__).resolve().parent.parent / "bridge" / "windows_helper.py"


def test_windows_helper_compiles():
    py_compile.compile(str(HELPER), doraise=True)


def test_windows_helper_has_no_repo_imports():
    tree = ast.parse(HELPER.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not ({"draw", "tools", "lab"} & imported)


# --- testes da logica de rede (sem Windows nem camera) ---

_spec = importlib.util.spec_from_file_location("windows_helper", HELPER)
wh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wh)

TOKEN = b"token-de-teste-para-o-bridge"  # >= TOKEN_MIN_LEN bytes


def _hello(token):
    return wh.HELLO.pack(wh.HELLO_MAGIC, wh.HELLO_VERSION, len(token)) + token


def _serve_one_client(host="127.0.0.1"):
    """Abre um listening socket efemero para alimentar o accept loop."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, 0))
    server.listen(1)
    return server


def _client(server, token=TOKEN):
    conn = socket.create_connection(server.getsockname()[:2], timeout=5)
    conn.settimeout(5)
    conn.sendall(_hello(token))
    return conn


def test_accept_loop_refuses_bad_handshake_and_keeps_listening():
    """Um par sem token e recusado e o laco continua para o proximo."""
    server = _serve_one_client()
    logs = []
    thread = threading.Thread(
        target=wh._accept_loop,
        args=(server, TOKEN, lambda: iter([b"jpeg"]), 0),
        kwargs={"log": logs.append},
        daemon=True,
    )
    thread.start()
    with _client(server, token=b"token-errado-de-teste!") as bad:
        assert bad.recv(4) == b""  # recusado: conexao fechada sem ACCEPT
    with _client(server) as good:
        assert good.recv(4) == wh.ACCEPT
        assert good.recv(wh.HEADER.size + 4)  # o laco chegou num segundo cliente
    server.close()


def test_accept_loop_survives_client_disconnect_mid_stream():
    """WSL caindo no meio do fluxo nao mata o ajudante residente."""
    server = _serve_one_client()
    logs = []
    thread = threading.Thread(
        target=wh._accept_loop,
        args=(server, TOKEN, lambda: iter([b"x" * 8] * 40), 0),
        kwargs={"log": logs.append},
        daemon=True,
    )
    thread.start()
    conn = _client(server)
    conn.recv(4)  # ACCEPT
    conn.recv(wh.HEADER.size + 8)  # um frame
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
    conn.close()  # RST: o proximo sendall do servidor levanta OSError
    with _client(server) as again:
        assert again.recv(4) == wh.ACCEPT
        assert again.recv(wh.HEADER.size + 8)
    server.close()


def test_capture_timestamp_is_relative_to_process_epoch():
    """capture_ts_us = (perf_counter_ns - start_ns)//1000 (PROTOCOL)."""
    server_conn, client_conn = socket.socketpair()
    ticks = iter([1_000_000_000, 1_500_000_000])

    def clock():
        return next(ticks)

    with server_conn:
        sent = wh._handle_client(server_conn, [b"ab", b"cd"], start_ns=0, clock=clock)
    assert sent == 2
    data = client_conn.recv(4096)
    client_conn.close()
    magic, version, _flags, frame_id, capture_ts_us, length = wh.HEADER.unpack(
        data[: wh.HEADER.size]
    )
    assert (magic, version, frame_id, length) == (wh.MAGIC, wh.VERSION, 0, 2)
    assert capture_ts_us == 1_000_000_000 // 1000  # epoch = start_ns = 0
    _, _, _, frame_id2, ts2, _ = wh.HEADER.unpack(
        data[wh.HEADER.size + 2 : wh.HEADER.size * 2 + 2]
    )
    assert frame_id2 == 1
    assert ts2 == 1_500_000_000 // 1000
