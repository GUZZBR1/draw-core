#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

case "$(uname -s 2>/dev/null || echo Linux)" in
    MINGW*|MSYS*|CYGWIN*)
        HOST_KIND="win"
        if [ -x ".venv/bin/python" ] && [ ! -x ".venv/Scripts/python.exe" ]; then
            VENV_DIR=".venv-win"
        else
            VENV_DIR=".venv"
        fi
        ;;
    *)
        HOST_KIND="posix"
        if [ -x ".venv/Scripts/python.exe" ] && [ ! -x ".venv/bin/python" ]; then
            VENV_DIR=".venv-linux"
        else
            VENV_DIR=".venv"
        fi
        ;;
esac

_resolve_venv_paths() {
    if [ "$HOST_KIND" = "win" ]; then
        if [ -x "$VENV_DIR/Scripts/python.exe" ]; then
            VENV_PYTHON="$VENV_DIR/Scripts/python.exe"
            VENV_DRAW="$VENV_DIR/Scripts/draw.exe"
        elif [ -x "$VENV_DIR/bin/python" ]; then
            VENV_PYTHON="$VENV_DIR/bin/python"
            VENV_DRAW="$VENV_DIR/bin/draw"
        else
            VENV_PYTHON=""
            VENV_DRAW=""
        fi
    else
        if [ -x "$VENV_DIR/bin/python" ]; then
            VENV_PYTHON="$VENV_DIR/bin/python"
            VENV_DRAW="$VENV_DIR/bin/draw"
        else
            VENV_PYTHON=""
            VENV_DRAW=""
        fi
    fi
}

_gui_ready() {
    _resolve_venv_paths
    [ -n "$VENV_DRAW" ] && [ -x "$VENV_DRAW" ] && "$VENV_PYTHON" -c '
import cv2, onnxruntime, draw
from draw.app import _gui_backend_compiled
assert _gui_backend_compiled(), "headless opencv"
' >/dev/null 2>&1
}

_drop_extra_cv2_providers() {
    # A second registered cv2 provider is a time bomb: the next exact
    # `uv sync` uninstalls one dist and deletes the shared cv2 files.
    # When the GUI works the files are already the contrib ones — only
    # the extra dist-info registration needs to go. Pure metadata
    # removal: no wheel, no network, and nothing is ever uninstalled,
    # so a working env stays launchable even offline on a cold cache.
    _resolve_venv_paths
    [ -n "$VENV_PYTHON" ] && "$VENV_PYTHON" -c '
import shutil
from importlib.metadata import distributions
names = {d.metadata["Name"].lower() for d in distributions()}
if "opencv-contrib-python" in names:
    for d in distributions():
        if d.metadata["Name"].lower() in {
            "opencv-contrib-python-headless",
            "opencv-python",
            "opencv-python-headless",
        }:
            path = getattr(d, "_path", None)
            if path is not None:
                shutil.rmtree(path, ignore_errors=True)
' >/dev/null 2>&1 || true
}

_hand_ready() {
    "$VENV_PYTHON" -c 'import mediapipe' >/dev/null 2>&1
}

_hand_retry_due() {
    "$VENV_PYTHON" -c '
import sys, time
from pathlib import Path

try:
    age = time.time() - (Path(sys.prefix) / ".no_hand").stat().st_mtime
except FileNotFoundError:
    sys.exit(0)
sys.exit(0 <= age < 24 * 60 * 60)
'
}

if command -v uv >/dev/null 2>&1; then
    USE_UV=1
else
    USE_UV=0
fi

_install_gui() {
    if [ "$USE_UV" = 1 ]; then
        UV_PROJECT_ENVIRONMENT="$VENV_DIR" uv sync --inexact --extra gui \
            --no-install-package opencv-contrib-python-headless "$@"
    else
        local extras=gui
        if [ "$#" -gt 0 ]; then
            extras=gui,hand
        fi
        "$VENV_PYTHON" -m pip install -e ".[$extras]"
    fi
}

_prepare_pip() {
    if [ "$USE_UV" = 0 ]; then
        python3 -m venv "$VENV_DIR" || return "$?"
        _resolve_venv_paths
        "$VENV_PYTHON" -m pip install --upgrade pip
    fi
}

_repair_opencv() {
    # Force the locked contrib wheel back on top without uninstalling:
    # --reinstall-package rewrites its files in place, so a working GUI
    # survives a failed attempt, and the extra cv2 dist registrations
    # are dropped metadata-only at the end. --locked --offline resolves
    # from uv.lock alone and reinstalls straight from the wheel cache;
    # go online only for a missing wheel.
    if [ "$USE_UV" = 1 ]; then
        UV_PROJECT_ENVIRONMENT="$VENV_DIR" uv sync --locked --offline \
            --inexact --extra gui --reinstall-package opencv-contrib-python \
            --no-install-package opencv-contrib-python-headless ||
            UV_PROJECT_ENVIRONMENT="$VENV_DIR" uv sync --inexact \
                --extra gui --reinstall-package opencv-contrib-python \
                --no-install-package opencv-contrib-python-headless ||
            return "$?"
    else
        "$VENV_PYTHON" -m pip install --no-deps --force-reinstall \
            "opencv-contrib-python>=4.8,<5.1" || return "$?"
    fi
    _drop_extra_cv2_providers
}

if _gui_ready; then
    _drop_extra_cv2_providers
    if ! _hand_ready; then
        BASE_VENV_DIR="$VENV_DIR"
        VENV_DIR="$BASE_VENV_DIR-hand"
        if _gui_ready && _hand_ready; then
            _drop_extra_cv2_providers
            exec "$VENV_DRAW" "$@"
        fi
        VENV_DIR="$BASE_VENV_DIR"
        _resolve_venv_paths
        if _hand_retry_due; then
            # Keep the working GUI environment available if optional setup fails.
            if (
                VENV_DIR="$BASE_VENV_DIR-hand"
                _prepare_pip &&
                    _install_gui --extra hand &&
                    { _gui_ready || { _repair_opencv && _gui_ready; }; } &&
                    _hand_ready
            ); then
                VENV_DIR="$BASE_VENV_DIR-hand"
            else
                touch "$BASE_VENV_DIR/.no_hand" || true
            fi
        fi
    fi
else
    if [ -d "$VENV_DIR" ]; then
        echo "Reparando o OpenCV do ambiente do Draw..."
    else
        echo "Preparando ambiente do Draw (primeira execucao)..."
    fi
    _prepare_pip
    if _install_gui --extra hand; then
        rm -f "$VENV_DIR/.no_hand"
    else
        _install_gui || exit "$?"
        touch "$VENV_DIR/.no_hand"
    fi
    if ! _gui_ready; then
        _repair_opencv
    fi
fi

_resolve_venv_paths
_drop_extra_cv2_providers
exec "$VENV_DRAW" "$@"
