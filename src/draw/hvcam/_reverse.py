"""Modo reverse: o Draw escuta e o hvcam-host.exe conecta (pacote draw.hvcam)."""

import os
import subprocess
import tempfile
from pathlib import Path

from ._capture import HvcamCapture
from ._process import _MANAGED_HOST_PROCS, _terminate_host_process
from ._provision import (
    _MANAGED_CONNECT_TIMEOUT_MS,
    ensure_hvcam_host,
    list_hvcam_devices,
)
from ._wire import _TIMEOUT_MS, DEFAULT_PORT

_MANAGED_WIDTH = 1280
_MANAGED_HEIGHT = 720
_MANAGED_FPS = 30


def open_managed_reverse(
    port=DEFAULT_PORT,
    device=0,
    *,
    timeout_ms=_TIMEOUT_MS,
    connect_timeout_ms=_MANAGED_CONNECT_TIMEOUT_MS,
    host_exe=None,
    devices=None,
    try_all=False,
    width=_MANAGED_WIDTH,
    height=_MANAGED_HEIGHT,
    fps=_MANAGED_FPS,
    popen=subprocess.Popen,
    capture_cls=None,
):
    """Sobe `hvcam-host.exe --reverse` automaticamente e conecta via vsock.

    Pede 1280x720@30fps por padrao (evita que webcams 1080p/4K derrubem o
    desempenho). Se a camera abrir mas entregar MJPEG corrompido no probe,
    tenta automaticamente o mesmo dispositivo com `--format nv12` (sem JPEG).
    Quando `try_all=True` (padrao para `--source 0`), percorre as demais
    webcams encontradas no Windows ate achar uma que funcione. O processo host
    fica preso ao `HvcamCapture` retornado e e encerrado no `release()`.
    Devolve `(HvcamCapture, device_index, device_name)` ou `(None, None, None)`.
    """
    exe = Path(host_exe) if host_exe is not None else ensure_hvcam_host()
    discovered = list_hvcam_devices(exe) if devices is None else list(devices)
    names = dict(discovered)

    order = [(int(device), names.get(int(device), f"Camera {device}"))]
    if try_all:
        for idx, name in discovered:
            if idx != int(device):
                order.append((idx, name))

    url = (
        "hvcam+reverse://"
        if int(port) == DEFAULT_PORT
        else f"hvcam+reverse://:{int(port)}"
    )
    run_cwd = "/mnt/c" if os.path.isdir("/mnt/c") else str(exe.parent)
    cls = HvcamCapture if capture_cls is None else capture_cls

    base_mode = []
    if width is not None and height is not None:
        base_mode.extend(["--width", str(int(width)), "--height", str(int(height))])
    if fps is not None:
        base_mode.extend(["--fps", str(int(fps))])

    retry_native = False

    def _attempt(dev_idx, extra_args):
        nonlocal retry_native
        retry_native = False
        proc_box = [None]
        host_error = None
        # A file lets the host keep logging after connect without a pipe reader.
        # The child keeps its own descriptor until it exits.
        with tempfile.TemporaryFile() as stderr_log:

            def _spawn(idx=dev_idx, box=proc_box, mode_args=extra_args):
                proc = popen(
                    [
                        str(exe),
                        "--reverse",
                        "--port",
                        str(int(port)),
                        *mode_args,
                        "--device",
                        str(idx),
                    ],
                    cwd=run_cwd,
                    stdout=subprocess.DEVNULL,
                    stderr=stderr_log,
                )
                box[0] = proc
                _MANAGED_HOST_PROCS.add(proc)

            def _aborted(box=proc_box):
                proc = box[0]
                return proc is not None and proc.poll() is not None

            try:
                cap = cls(
                    url,
                    timeout_ms=timeout_ms,
                    connect_timeout_ms=connect_timeout_ms,
                    on_listening=_spawn,
                    abort_check=_aborted,
                )
                if cap.isOpened():
                    retry_native = True
                    needs_probe = try_all or (
                        capture_cls is None and hasattr(cap, "read")
                    )
                    if not needs_probe:
                        cap._host_proc = proc_box[0]
                        proc_box[0] = None
                        return cap, False, None, None
                    ok_probe, measured_fps = _probe_hvcam_stream(cap)
                    mjpeg_failed = getattr(cap, "mjpeg_decode_errors", 0) > 0
                    if ok_probe and not mjpeg_failed:
                        cap._host_proc = proc_box[0]
                        proc_box[0] = None
                        return cap, False, measured_fps, None
                    cap.release()
                    return None, mjpeg_failed, None, None
                if _aborted():
                    retry_native = True
                    size = stderr_log.seek(0, os.SEEK_END)
                    stderr_log.seek(max(0, size - 16_384))
                    err_msg = stderr_log.read(16_384).decode("utf-8", errors="replace")
                    if err_msg.strip():
                        host_error = err_msg.strip()
                cap.release()
                return None, False, None, host_error
            finally:
                _terminate_host_process(proc_box[0])

    def _try_raw_formats(dev_idx, mode_prefix, accept=None):
        """Tenta NV12 e YUY2. `accept(fps)` rejeita um raw limpo (ex.: lento
        demais) e segue para o proximo formato; o primeiro rejeitado fica em
        `rejected_fmt` como ultimo recurso. Devolve (cap, erro, rejected_fmt)."""
        err_last = None
        rejected_fmt = None
        for fallback_fmt in ("nv12", "yuy2"):
            raw_cap, _raw_mjpeg, raw_fps, raw_err = _attempt(
                dev_idx, [*mode_prefix, "--format", fallback_fmt]
            )
            if raw_cap is not None:
                if accept is None or accept(raw_fps):
                    return raw_cap, None, None
                raw_cap.release()
                if rejected_fmt is None:
                    rejected_fmt = fallback_fmt
                continue
            if raw_err:
                err_last = raw_err
        return None, err_last, rejected_fmt

    last_host_error = None
    for dev_idx, dev_name in order:
        cap, mjpeg_failed, measured_fps, err = _attempt(dev_idx, base_mode)
        requested_can_retry = retry_native
        if cap is not None:
            # Se 720p reduziu o FPS abaixo de 75% do alvo (ex.: camera so oferece
            # 720p@15fps e 1080p@30fps), testa o modo nativo (rate-first) e fica
            # com ele se entregar taxa mais alta.
            if (
                base_mode
                and fps is not None
                and measured_fps is not None
                and measured_fps < 0.75 * float(fps)
            ):
                cap.release()
                nat_cap, nat_mjpeg, nat_fps, nat_err = _attempt(dev_idx, [])
                # Ultimo recurso se 720p sumir: modo nativo que funcionou mas nao
                # provou ser mais rapido.
                native_last_args = None

                def _faster(f, m=measured_fps):
                    # Taxa desconhecida (ex.: um unico quadro) nao e upgrade.
                    return f is not None and f > m * 1.15

                if nat_cap is not None and _faster(nat_fps):
                    return nat_cap, dev_idx, dev_name
                if nat_cap is not None:
                    nat_cap.release()
                    native_last_args = []
                elif nat_mjpeg:
                    # Raw nativo costuma ser mais lento (USB2): so troca o 720p
                    # MJPEG limpo se a taxa medida for claramente maior.
                    raw_cap, raw_err, native_raw_fmt = _try_raw_formats(
                        dev_idx, [], accept=_faster
                    )
                    if raw_cap is not None:
                        return raw_cap, dev_idx, dev_name
                    if native_raw_fmt is not None:
                        native_last_args = ["--format", native_raw_fmt]
                    elif raw_err:
                        last_host_error = raw_err
                if nat_err:
                    last_host_error = nat_err
                # Nativo nao superou 720p: reabre 720p (menor carga de CPU).
                cap2, mjpeg2, _f2, err2 = _attempt(dev_idx, base_mode)
                if cap2 is not None:
                    return cap2, dev_idx, dev_name
                if err2:
                    last_host_error = err2
                if mjpeg2:
                    raw_cap, raw_err, _rej = _try_raw_formats(dev_idx, base_mode)
                    if raw_cap is not None:
                        return raw_cap, dev_idx, dev_name
                    if raw_err:
                        last_host_error = raw_err
                if native_last_args is not None:
                    raw_cap, _m, _f, _e = _attempt(dev_idx, native_last_args)
                    if raw_cap is not None:
                        return raw_cap, dev_idx, dev_name
                continue
            return cap, dev_idx, dev_name
        if err:
            last_host_error = err
        # Se a camera abriu mas o fluxo MJPEG veio corrompido, tenta NV12/YUY2 (sem JPEG).
        if mjpeg_failed:
            raw_cap, raw_err, _rej = _try_raw_formats(dev_idx, base_mode)
            if raw_cap is not None:
                return raw_cap, dev_idx, dev_name
            if raw_err:
                last_host_error = raw_err
        if base_mode and requested_can_retry:
            # O modo pedido (720p) nao abriu ou nao deu video utilizavel: tenta o
            # mesmo dispositivo sem sobrescritas, como antes do 720p, antes de
            # passar para outra camera. Timeout com host vivo nao repete:
            # evita somar outro timeout por camera.
            nat_cap, nat_mjpeg, _nf, nat_err = _attempt(dev_idx, [])
            if nat_cap is not None:
                return nat_cap, dev_idx, dev_name
            if nat_err:
                last_host_error = nat_err
            if nat_mjpeg:
                raw_cap, raw_err, _rej = _try_raw_formats(dev_idx, [])
                if raw_cap is not None:
                    return raw_cap, dev_idx, dev_name
                if raw_err:
                    last_host_error = raw_err
    if last_host_error:
        raise RuntimeError(last_host_error)
    return None, None, None


def _probe_hvcam_stream(capture, attempts=3):
    """Confirma que a fonte hvcam entrega quadros limpos e mede o FPS real.

    Falha imediatamente se ocorrer qualquer erro de decode MJPEG (mesmo que
    outra leitura funcione), para acionar o fallback de formato cru. Quando a
    fonte expoe `last_capture_ts_ms`, coleta ate `attempts` quadros para medir
    o FPS entregue sem depender de clock local.
    """
    timestamps = []
    got_frame = False
    for _ in range(attempts):
        ok, frame = capture.read()
        if getattr(capture, "mjpeg_decode_errors", 0) > 0:
            return False, None
        if ok and frame is not None:
            got_frame = True
            ts = getattr(capture, "last_capture_ts_ms", None)
            if ts is None:
                return True, None
            timestamps.append(ts)
    if not got_frame:
        return False, None
    measured_fps = None
    if len(timestamps) >= 2 and timestamps[-1] > timestamps[0]:
        measured_fps = (len(timestamps) - 1) * 1000.0 / (timestamps[-1] - timestamps[0])
    return True, measured_fps
