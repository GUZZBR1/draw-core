"""Fonte hvcam:// — camera do Windows via Hyper-V socket (santleme/hvcam).

O hvcam é o transporte nativo para a webcam que mora no lado Windows:
hvcam-host.exe captura por Media Foundation e serve o quadro mais novo
por AF_HYPERV (vsock) na porta 8765 — sem IP, sem firewall, sem usbipd.
`hvcam://` conecta ao host (requer o serviço vsock registrado uma vez no
Windows); `hvcam+reverse://` escuta no WSL para `hvcam-host.exe --reverse`
e não requer registro; fora do WSL, `hvcam+tcp://host` usa TCP.

O pacote se divide por responsabilidade: `_wire` (constantes do
protocolo), `_lib` (cliente ctypes vendored + fallback Python puro),
`_transport` (escuta vsock), `_mjpeg` (sanitizacao do payload),
`_capture` (Camera/HvcamCapture/parse), `_provision` (download do
hvcam-host.exe) e `_reverse` (modo --reverse). Este `__init__` reexporta
a superficie que camera/selfcheck/testes consomem.
"""

import subprocess as subprocess  # noqa: F401 — acessado como hvcam.subprocess pelos testes

from .._hvcam_mjpeg import decode_mjpeg as _imdecode_mjpeg_strict
from ._capture import (
    Camera,
    HvcamCapture,
    is_hvcam_source,
    parse_hvcam_endpoint,
)
from ._lib import (
    HvFrameHeader,
    _lib_or_fallback,
)
from ._mjpeg import _sanitize_mjpeg
from ._process import _terminate_host_process
from ._provision import (
    HVCAM_HOST_RELEASE_URL,
    HVCAM_HOST_ZIP_MEMBER,
    HVCAM_HOST_ZIP_SHA256,
    _windows_cache_dir,
    ensure_hvcam_host,
    list_hvcam_devices,
)
from ._reverse import _probe_hvcam_stream, open_managed_reverse
from ._transport import _listen_vsock_bounded
from ._wire import (
    _LISTEN_TIMEOUT_MS,
    _TIMEOUT_MS,
    DEFAULT_PORT,
)

__all__ = [
    "Camera",
    "DEFAULT_PORT",
    "HVCAM_HOST_RELEASE_URL",
    "HVCAM_HOST_ZIP_MEMBER",
    "HVCAM_HOST_ZIP_SHA256",
    "HvFrameHeader",
    "HvcamCapture",
    "_imdecode_mjpeg_strict",
    "_lib_or_fallback",
    "_listen_vsock_bounded",
    "_probe_hvcam_stream",
    "_sanitize_mjpeg",
    "_terminate_host_process",
    "_windows_cache_dir",
    "_LISTEN_TIMEOUT_MS",
    "_TIMEOUT_MS",
    "ensure_hvcam_host",
    "is_hvcam_source",
    "list_hvcam_devices",
    "open_managed_reverse",
    "parse_hvcam_endpoint",
]
