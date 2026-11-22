"""Provisionamento do hvcam-host.exe no Windows a partir do WSL (pacote draw.hvcam)."""

import hashlib
import io
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from ..infra.safe_io import atomic_publish

# Release oficial do hvcam-host.exe (santleme/hvcam) para provisionamento
# automatico no WSL: o binario roda no lado Windows e transmite a webcam
# via AF_HYPERV sem admin nem instalacao manual.
HVCAM_HOST_RELEASE_URL = (
    "https://github.com/santleme/hvcam/releases/download/"
    "v0.1.1-rc.1/hvcam-v0.1.1-rc.1-windows-x86_64.zip"
)
HVCAM_HOST_ZIP_SHA256 = (
    "4bb9aeaf72ca983950b7ed65df3188ead146b7fdcd5a2b53e4280d82e8247c6e"
)
HVCAM_HOST_ZIP_MEMBER = "hvcam-v0.1.1-rc.1-windows-x86_64/hvcam-host.exe"
_HVCAM_HOST_MAX_ZIP_BYTES = 16 << 20
_HVCAM_HOST_DOWNLOAD_TIMEOUT_S = 60
_MANAGED_CONNECT_TIMEOUT_MS = 10_000
_DEVICE_LINE_RE = re.compile(r"^\s*\[(\d+)\]\s*(.+?)\s*$")


def _windows_cache_dir():
    """Pasta de cache no filesystem do Windows (LocalApplicationData\\draw).

    Windows Media Foundation bloqueia o acesso a camera com 0x80070490
    quando hvcam-host.exe e executado a partir de um caminho UNC do WSL
    (\\\\wsl.localhost\\...). Copiar/extrair o binario para o disco do
    Windows evita esse bloqueio sem exigir configuracao manual.

    Usa a API de Known Folders do .NET com saida UTF-8 explicita para nao
    ler variaveis de ambiente nem quebrar em perfis com acento (CP850/1252).
    """
    cwd = "/mnt/c" if os.path.isdir("/mnt/c") else None
    ps_cmd = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "[Environment]::GetFolderPath('LocalApplicationData')"
    )
    try:
        raw_bytes = subprocess.check_output(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        raw = raw_bytes.decode("utf-8").strip()
        if not raw:
            return None
        wsl_bytes = subprocess.check_output(
            ["wslpath", raw],
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        wsl_path = wsl_bytes.decode("utf-8").strip()
        if not wsl_path:
            return None
        return Path(wsl_path) / "draw"
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return None


def _local_hvcam_host_candidates():
    """Locais onde um checkout/instalacao local do hvcam-host.exe pode morar."""
    here = Path(__file__).resolve().parent
    candidates = [
        here.parents[2] / "hvcam" / "dist" / "hvcam-host.exe",
        here.parents[2] / "hvcam" / "build" / "Release" / "hvcam-host.exe",
        Path.home() / "hvcam" / "dist" / "hvcam-host.exe",
        Path.home() / "hvcam" / "build" / "Release" / "hvcam-host.exe",
    ]
    found_in_path = shutil.which("hvcam-host.exe")
    if found_in_path:
        candidates.append(Path(found_in_path))
    return tuple(candidates)


def _atomic_write_executable(target, payload_bytes):
    """Grava `payload_bytes` em `target` de forma atomica com permissao +x."""
    with atomic_publish(target, mode=0o755) as handle:
        handle.write(payload_bytes)
    return target


def ensure_hvcam_host(
    *,
    cache_dir=None,
    urlopen=None,
    release_url=None,
    expected_sha256=None,
    local_candidates=None,
):
    """Garante hvcam-host.exe pronto no disco do Windows (copia local ou download).

    Verifica o SHA-256 do pacote zip oficial antes de extrair (fail-closed).
    Devolve o Path do executavel ou levanta RuntimeError em caso de falha.
    """
    win_dir = Path(cache_dir) if cache_dir is not None else _windows_cache_dir()
    if win_dir is None:
        raise RuntimeError(
            "nao consegui localizar %LOCALAPPDATA% no Windows via interop do WSL"
        )
    target = win_dir / "hvcam-host.exe"
    if target.is_file() and target.stat().st_size > 0:
        try:
            os.chmod(target, 0o755)
        except OSError:
            pass
        return target

    candidates = (
        _local_hvcam_host_candidates() if local_candidates is None else local_candidates
    )
    for cand in candidates:
        cand_path = Path(cand)
        if cand_path.is_file() and cand_path.stat().st_size > 0:
            try:
                _atomic_write_executable(target, cand_path.read_bytes())
                return target
            except OSError:
                continue

    url = (release_url or HVCAM_HOST_RELEASE_URL).strip()
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError(f"URL de release do hvcam precisa ser https://: {url!r}")
    want_sha = (expected_sha256 or HVCAM_HOST_ZIP_SHA256).strip().lower()
    opener = urllib.request.urlopen if urlopen is None else urlopen
    print("Baixando hvcam-host.exe da Release oficial (santleme/hvcam)...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "draw-core/0.1"})
        with opener(req, timeout=_HVCAM_HOST_DOWNLOAD_TIMEOUT_S) as resp:
            chunks = bytearray()
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                chunks.extend(chunk)
                if len(chunks) > _HVCAM_HOST_MAX_ZIP_BYTES:
                    raise RuntimeError(
                        f"download do hvcam excedeu {_HVCAM_HOST_MAX_ZIP_BYTES} bytes"
                    )
    except (urllib.error.URLError, OSError) as error:
        raise RuntimeError(
            f"falha ao baixar hvcam-host.exe de {url}: {error}"
        ) from error

    actual_sha = hashlib.sha256(chunks).hexdigest()
    if actual_sha != want_sha:
        raise RuntimeError(
            f"sha256 divergente no download do hvcam: {actual_sha} != {want_sha}"
        )
    try:
        with zipfile.ZipFile(io.BytesIO(chunks)) as zf:
            member = HVCAM_HOST_ZIP_MEMBER
            if member not in zf.namelist():
                matches = [
                    name
                    for name in zf.namelist()
                    if name.lower().endswith("/hvcam-host.exe")
                    or name.lower() == "hvcam-host.exe"
                ]
                if not matches:
                    raise RuntimeError("hvcam-host.exe nao encontrado no pacote zip")
                member = matches[0]
            exe_bytes = zf.read(member)
    except zipfile.BadZipFile as error:
        raise RuntimeError(f"pacote zip do hvcam corrompido: {error}") from error

    _atomic_write_executable(target, exe_bytes)
    print(f"hvcam-host.exe salvo e verificado em {target}.")
    return target


def list_hvcam_devices(host_exe):
    """Lista webcams disponiveis no Windows via `hvcam-host.exe --list`."""
    exe = Path(host_exe)
    cwd = "/mnt/c" if os.path.isdir("/mnt/c") else str(exe.parent)
    try:
        output = subprocess.check_output(
            [str(exe), "--list"],
            cwd=cwd,
            stderr=subprocess.STDOUT,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    try:
        text = output.decode("utf-8")
    except UnicodeDecodeError:
        text = output.decode("cp1252", errors="replace")
    devices = []
    for line in text.splitlines():
        match = _DEVICE_LINE_RE.match(line)
        if match:
            devices.append((int(match.group(1)), match.group(2).strip()))
    return devices


_MANAGED_WIDTH = 1280
_MANAGED_HEIGHT = 720
_MANAGED_FPS = 30
