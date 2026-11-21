import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(
    os.name != "posix" or not BASH, reason="requires a POSIX shell environment"
)


@pytest.fixture
def launcher(tmp_path):
    shutil.copyfile(Path(__file__).resolve().parents[1] / "run.sh", tmp_path / "run.sh")
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ("dirname", "uname", "touch", "rm", "cp", "mkdir"):
        (tools / name).symlink_to(shutil.which(name))
    venv = tmp_path / ".venv"
    bin_dir = venv / "bin"
    bin_dir.mkdir(parents=True)
    python = bin_dir / "python"
    python.write_text(
        f"#!{sys.executable}\n"
        "import sys, types\n"
        "from pathlib import Path\n"
        "prefix = Path(__file__).resolve().parents[1]\n"
        "if sys.argv[1] == '-c':\n"
        "    sys.prefix = str(prefix)\n"
        "    for name in ('cv2', 'onnxruntime', 'draw', 'draw.app'):\n"
        "        sys.modules[name] = types.ModuleType(name)\n"
        "    sys.modules['draw.app']._gui_backend_compiled = lambda: not (prefix / 'gui-broken').exists()\n"
        "    if (prefix / 'hand-installed').exists():\n"
        "        sys.modules['mediapipe'] = types.ModuleType('mediapipe')\n"
        "    else:\n"
        "        sys.modules['mediapipe'] = None\n"
        "    exec(sys.argv[2])\n"
        "else:\n"
        "    with open('commands', 'a') as log:\n"
        "        print(' '.join(sys.argv[1:]), file=log)\n"
        "    if sys.argv[-1] == '.[gui,hand]':\n"
        "        if not Path('hand-available').exists():\n"
        "            sys.exit(7)\n"
        "        (prefix / 'hand-installed').touch()\n"
        "    elif sys.argv[-1] != 'pip' and not Path('gui-available').exists():\n"
        "        sys.exit(7)\n"
        "    if '-e' in sys.argv or sys.argv[-1].startswith('opencv-contrib-python'):\n"
        "        (prefix / 'gui-broken').unlink(missing_ok=True)\n"
        "    if '-e' in sys.argv and (prefix.parent / 'gui-stubborn').exists():\n"
        "        (prefix / 'gui-broken').touch()\n"
    )
    python.chmod(0o755)
    draw = bin_dir / "draw"
    draw.write_text('#!/bin/sh\nprintf "%s\\n" "$0" >> launches\n[ "$1" = --check ]\n')
    draw.chmod(0o755)
    python3 = tools / "python3"
    python3.write_text(
        "#!/bin/sh\n"
        'if [ "$3" != .venv ]; then\n'
        '    mkdir -p "$3/bin" && cp .venv/bin/python .venv/bin/draw "$3/bin/"\n'
        "fi\n"
    )
    python3.chmod(0o755)
    return tools


@pytest.mark.parametrize("use_uv", [False, True], ids=["pip", "uv"])
def test_failed_setup_never_uninstalls_opencv(tmp_path, launcher, use_uv):
    (tmp_path / ".venv" / "gui-broken").touch()
    if use_uv:
        uv = launcher / "uv"
        uv.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> commands\nexit 7\n')
        uv.chmod(0o755)
    result = subprocess.run(
        [BASH, "run.sh", "--check"],
        cwd=tmp_path,
        env={"PATH": str(launcher)},
        check=False,
        timeout=10,
    )
    commands = (tmp_path / "commands").read_text().splitlines()
    assert all("uninstall" not in command for command in commands)
    assert commands[-2:] == (
        ["sync --inexact --extra gui --extra hand", "sync --inexact --extra gui"]
        if use_uv
        else ["-m pip install -e .[gui,hand]", "-m pip install -e .[gui]"]
    )
    assert result.returncode == 7
    assert not (tmp_path / ".venv" / ".no_hand").exists()


def test_gui_fallback_retries_hand_after_cooldown(tmp_path, launcher):
    (tmp_path / "gui-available").touch()
    (tmp_path / ".venv" / "gui-broken").touch()
    args = [BASH, "run.sh", "--check"]
    options = {
        "cwd": tmp_path,
        "env": {"PATH": str(launcher)},
        "check": True,
        "timeout": 10,
    }
    subprocess.run(args, **options)
    marker = tmp_path / ".venv" / ".no_hand"
    assert marker.is_file()
    commands = tmp_path / "commands"
    initial = commands.read_text()
    assert initial.splitlines()[-1] == "-m pip install -e .[gui]"

    subprocess.run(args, **options)
    assert commands.read_text() == initial

    os.utime(marker, (1, 1))
    (tmp_path / "hand-available").touch()
    subprocess.run(args, **options)
    assert (tmp_path / ".venv-hand" / "hand-installed").is_file()
    assert not (tmp_path / ".venv" / "hand-installed").exists()
    launches = (tmp_path / "launches").read_text().splitlines()
    assert [tmp_path / launch for launch in launches] == [
        tmp_path / ".venv/bin/draw",
        tmp_path / ".venv/bin/draw",
        tmp_path / ".venv-hand/bin/draw",
    ]


@pytest.mark.parametrize("use_uv", [False, True], ids=["pip", "uv"])
def test_expired_hand_fallback_still_launches_offline(tmp_path, launcher, use_uv):
    if use_uv:
        uv = launcher / "uv"
        uv.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> commands\nexit 7\n')
        uv.chmod(0o755)
    marker = tmp_path / ".venv" / ".no_hand"
    marker.touch()
    os.utime(marker, (1, 1))

    subprocess.run(
        [BASH, "run.sh", "--check"],
        cwd=tmp_path,
        env={"PATH": str(launcher)},
        check=True,
        timeout=10,
    )
    commands = (tmp_path / "commands").read_text()
    assert "uninstall" not in commands
    assert ".[gui]\n" not in commands
    assert "sync --inexact --extra gui\n" not in commands
    assert marker.stat().st_mtime > 1
    launched = (tmp_path / "launches").read_text().strip()
    assert tmp_path / launched == tmp_path / ".venv/bin/draw"


FAKE_UV = """#!/bin/sh
printf "%s\\n" "$*" >> commands
if [ "$1" = "sync" ]; then
    [ -n "$UV_PROJECT_ENVIRONMENT" ] || exit 1
    if [ "$UV_PROJECT_ENVIRONMENT" != .venv ]; then
        mkdir -p "$UV_PROJECT_ENVIRONMENT/bin"
        cp .venv/bin/python .venv/bin/draw "$UV_PROJECT_ENVIRONMENT/bin/"
    fi
    case " $* " in
        *" --extra hand "*) touch "$UV_PROJECT_ENVIRONMENT/hand-installed" ;;
    esac
    exit 0
fi
if [ "$1" = "pip" ] && [ "$2" = "install" ]; then
    target=""
    prev=""
    for arg in "$@"; do
        [ "$prev" = "--python" ] && target=${arg%/bin/python}
        prev="$arg"
    done
    case " $* " in
        *" --offline "*)
            [ -f wheel-cached ] || exit 1
            ;;
    esac
    rm -f "${target:-.venv}/gui-broken"
    exit 0
fi
exit 0
"""


def _fake_uv(launcher):
    uv = launcher / "uv"
    uv.write_text(FAKE_UV)
    uv.chmod(0o755)


def _commands(tmp_path):
    return (tmp_path / "commands").read_text().splitlines()


def test_uv_repair_prefers_offline_cache(tmp_path, launcher):
    """Headless por cima + cache quente: o repair reescreve o contrib com
    --offline, sem uninstall e sem acordar a rede."""
    (tmp_path / ".venv" / "gui-broken").touch()
    (tmp_path / "wheel-cached").touch()
    _fake_uv(launcher)

    subprocess.run(
        [BASH, "run.sh", "--check"],
        cwd=tmp_path,
        env={"PATH": str(launcher)},
        check=True,
        timeout=10,
    )
    commands = _commands(tmp_path)
    assert [c for c in commands if c.startswith("sync")] == [
        "sync --inexact --extra gui --extra hand"
    ]
    repairs = [c for c in commands if "reinstall-package" in c]
    assert len(repairs) == 1
    assert "--offline" in repairs[0]
    assert "--no-deps" in repairs[0]
    assert all("uninstall" not in c for c in commands)
    launched = (tmp_path / "launches").read_text().strip()
    assert tmp_path / launched == tmp_path / ".venv/bin/draw"


def test_uv_repair_falls_back_to_network_without_cache(tmp_path, launcher):
    """Sem o wheel no cache: tenta --offline, falha e so entao vai a rede."""
    (tmp_path / ".venv" / "gui-broken").touch()
    _fake_uv(launcher)

    subprocess.run(
        [BASH, "run.sh", "--check"],
        cwd=tmp_path,
        env={"PATH": str(launcher)},
        check=True,
        timeout=10,
    )
    repairs = [c for c in _commands(tmp_path) if "reinstall-package" in c]
    assert len(repairs) == 2
    assert "--offline" in repairs[0]
    assert "--offline" not in repairs[1]
    launched = (tmp_path / "launches").read_text().strip()
    assert tmp_path / launched == tmp_path / ".venv/bin/draw"


def test_uv_hand_retry_syncs_inexact_and_repairs_hand_env(tmp_path, launcher):
    """Todo `uv sync` do launcher leva --inexact (pytest/ruff/drawlink
    editavel sobrevivem) e o repair roda no env -hand, nao no base."""
    marker = tmp_path / ".venv" / ".no_hand"
    marker.touch()
    os.utime(marker, (1, 1))
    (tmp_path / ".venv-hand").mkdir()
    (tmp_path / ".venv-hand" / "gui-broken").touch()
    (tmp_path / "wheel-cached").touch()
    _fake_uv(launcher)

    subprocess.run(
        [BASH, "run.sh", "--check"],
        cwd=tmp_path,
        env={"PATH": str(launcher)},
        check=True,
        timeout=10,
    )
    commands = _commands(tmp_path)
    syncs = [c for c in commands if c.startswith("sync")]
    assert syncs == ["sync --inexact --extra gui --extra hand"]
    repairs = [c for c in commands if "reinstall-package" in c]
    assert len(repairs) == 1
    assert "--python .venv-hand/bin/python" in repairs[0]
    assert "--offline" in repairs[0]
    assert all("uninstall" not in c for c in commands)
    assert (tmp_path / ".venv-hand" / "hand-installed").is_file()
    launched = (tmp_path / "launches").read_text().strip()
    assert tmp_path / launched == tmp_path / ".venv-hand/bin/draw"


def test_pip_repair_rewrites_contrib_without_uninstall(tmp_path, launcher):
    """Fallback pip: --force-reinstall --no-deps so no contrib, sem
    desinstalar os demais wheels antes."""
    (tmp_path / "gui-available").touch()
    (tmp_path / "hand-available").touch()
    (tmp_path / "gui-stubborn").touch()
    (tmp_path / ".venv" / "gui-broken").touch()

    subprocess.run(
        [BASH, "run.sh", "--check"],
        cwd=tmp_path,
        env={"PATH": str(launcher)},
        check=True,
        timeout=10,
    )
    commands = _commands(tmp_path)
    assert commands[-1] == (
        "-m pip install --no-deps --force-reinstall opencv-contrib-python>=4.8,<5.1"
    )
    assert all("uninstall" not in c for c in commands)
    launched = (tmp_path / "launches").read_text().strip()
    assert tmp_path / launched == tmp_path / ".venv/bin/draw"
