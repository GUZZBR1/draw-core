"""Constantes do protocolo hvcam (pacote draw.hvcam).

Compartilhadas pelo cliente ctypes/Python puro (_lib), pelo transporte
vsock (_transport) e pela captura (_capture).
"""

import struct

DEFAULT_PORT = 8765

_TIMEOUT_MS = 1000
# No Hyper-V (AF_HYPERV), uma tentativa de connect() do host antes de o
# listener existir no WSL pode levar 30 s para o host rescindir a oferta
# mais 1 s de espera antes do retry do hvcam-host.exe --reverse: 35 s
# mantem o accept limitado e cobre um ciclo completo de timeout + retry.
_LISTEN_TIMEOUT_MS = 35_000
_MAX_PAYLOAD = 64 * 1024 * 1024
# Portas AF_VSOCK sao uint32; 0xFFFFFFFF e VMADDR_PORT_ANY (reservado).
_VSOCK_PORT_MAX = 0xFFFFFFFF - 1
_TCP_PORT_MAX = 65535
_HVCAM_MAGIC = 0x4856434D  # "HVCM"
_HVCAM_VERSION = 1
_HVCAM_REQ = b"Q"
_HEADER_STRUCT = struct.Struct("<IHHQQHHII")
_MIN_REQ_SECONDS = 0.020
_NAP_SECONDS = 0.015
