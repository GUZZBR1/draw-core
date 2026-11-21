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
        "    site = prefix / 'site'\n"
        "    def _dists():\n"
        "        out = []\n"
        "        for p in site.glob('*.dist-info'):\n"
        "            meta_file = p / 'METADATA'\n"
        "            name = p.name.rsplit('-', 1)[0]\n"
        "            if meta_file.exists():\n"
        "                name = next(\n"
        "                    line.split(':', 1)[1].strip()\n"
        "                    for line in meta_file.read_text().splitlines()\n"
        "                    if line.startswith('Name:')\n"
        "                )\n"
        "            out.append(types.SimpleNamespace(metadata={'Name': name}, _path=p))\n"
        "        return out\n"
        "    meta = types.ModuleType('importlib.metadata')\n"
        "    meta.distributions = _dists\n"
        "    sys.modules['importlib.metadata'] = meta\n"
        "    if (prefix / 'hand-installed').exists():\n"
        "        sys.modules['mediapipe'] = types.ModuleType('mediapipe')\n"
        "    else:\n"
        "        sys.modules['mediapipe'] = None\n"
        "    exec(sys.argv[2])\n"
        "else:\n"
        "    site = prefix / 'site'\n"
        "    with open('commands', 'a') as log:\n"
        "        print(' '.join(sys.argv[1:]), file=log)\n"
        "    if sys.argv[-1] == '.[gui,hand]':\n"
        "        if not Path('hand-available').exists():\n"
        "            sys.exit(7)\n"
        "        (prefix / 'hand-installed').touch()\n"
        "    elif sys.argv[-1] != 'pip' and not Path('gui-available').exists():\n"
        "        sys.exit(7)\n"
        "    if '-e' in sys.argv:\n"
        "        for pkg in ('opencv-contrib-python-headless', 'opencv-contrib-python'):\n"
        "            dist = site / (pkg.replace('-', '_') + '-5.0.0.93.dist-info')\n"
        "            dist.mkdir(parents=True, exist_ok=True)\n"
        "            (dist / 'METADATA').write_text('Name: ' + pkg + '\\n')\n"
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
        [_INSTALL_SYNC_HAND, _INSTALL_SYNC_GUI]
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
    assert (
        "sync --inexact --extra gui --no-install-package "
        "opencv-contrib-python-headless\n" not in commands
    )
    assert marker.stat().st_mtime > 1
    launched = (tmp_path / "launches").read_text().strip()
    assert tmp_path / launched == tmp_path / ".venv/bin/draw"


FAKE_UV = """#!/bin/sh
printf "%s\\n" "$*" >> commands
add_dist() {
    dir="$1/site/$(echo "$2" | tr - _)-5.0.0.93.dist-info"
    mkdir -p "$dir" && printf "Name: %s\\n" "$2" > "$dir/METADATA"
}
if [ "$1" = "sync" ]; then
    [ -n "$UV_PROJECT_ENVIRONMENT" ] || exit 1
    case " $* " in
        *" --locked "*) [ -f uv.lock ] || exit 1 ;;
    esac
    case " $* " in
        *" --offline "*) [ -f wheel-cached ] || exit 1 ;;
    esac
    prefix="$UV_PROJECT_ENVIRONMENT"
    if [ "$prefix" != .venv ]; then
        mkdir -p "$prefix/bin"
        cp .venv/bin/python .venv/bin/draw "$prefix/bin/"
    fi
    case " $* " in
        *" --extra hand "*) touch "$prefix/hand-installed" ;;
    esac
    case " $* " in
        *" --no-install-package opencv-contrib-python-headless "*) ;;
        *)
            if [ ! -d "$prefix/site/opencv_contrib_python_headless-5.0.0.93.dist-info" ]; then
                add_dist "$prefix" opencv-contrib-python-headless
                touch "$prefix/gui-broken"
            fi ;;
    esac
    case " $* " in
        *" --reinstall-package opencv-contrib-python "*)
            add_dist "$prefix" opencv-contrib-python
            rm -f "$prefix/gui-broken" ;;
        *" --extra gui "*)
            add_dist "$prefix" opencv-contrib-python
            [ -e "$prefix/site/opencv_contrib_python_headless-5.0.0.93.dist-info" ] ||
                rm -f "$prefix/gui-broken" ;;
    esac
    exit 0
fi
exit 0
"""

MINI_PYPROJECT = """\
[project]
name = "opencv-provider-fixture"
version = "0.0.0"
requires-python = ">=3.11"
dependencies = ["opencv-contrib-python-headless>=4.8,<5.1"]

[project.optional-dependencies]
gui = ["opencv-contrib-python>=4.8,<5.1"]

[tool.uv]
package = false
"""

_CV2_GUI_CHECK = (
    "import re, sys, cv2\n"
    "m = re.search(r'^[ \\t]*GUI:[ \\t]*(\\S*)', cv2.getBuildInformation(), re.M)\n"
    "sys.exit(0 if m and m.group(1).upper() not in ('NONE','NO','OFF','FALSE','0') "
    "else 1)\n"
)

# Mesmo script do _drop_extra_cv2_providers no run.sh.
_CV2_DROP_EXTRAS = (
    "import shutil\n"
    "from importlib.metadata import distributions\n"
    "names = {d.metadata['Name'].lower() for d in distributions()}\n"
    "if 'opencv-contrib-python' in names:\n"
    "    for d in distributions():\n"
    "        if d.metadata['Name'].lower() in {\n"
    "            'opencv-contrib-python-headless',\n"
    "            'opencv-python',\n"
    "            'opencv-python-headless',\n"
    "        }:\n"
    "            path = getattr(d, '_path', None)\n"
    "            if path is not None:\n"
    "                shutil.rmtree(path, ignore_errors=True)\n"
)


def _fake_uv(launcher):
    uv = launcher / "uv"
    uv.write_text(FAKE_UV)
    uv.chmod(0o755)


def _commands(tmp_path):
    return (tmp_path / "commands").read_text().splitlines()


_INSTALL_SYNC_GUI = (
    "sync --inexact --extra gui --no-install-package opencv-contrib-python-headless"
)

_INSTALL_SYNC_HAND = _INSTALL_SYNC_GUI + " --extra hand"

_REPAIR_SYNC = (
    "sync --locked --offline --inexact --extra gui "
    "--reinstall-package opencv-contrib-python "
    "--no-install-package opencv-contrib-python-headless"
)

_REPAIR_SYNC_FALLBACK = (
    "sync --inexact --extra gui --reinstall-package opencv-contrib-python "
    "--no-install-package opencv-contrib-python-headless"
)


def _add_provider(venv, name):
    dist_info = venv / "site" / f"{name.replace('-', '_')}-5.0.0.93.dist-info"
    dist_info.mkdir(parents=True, exist_ok=True)
    (dist_info / "METADATA").write_text(f"Name: {name}\n")
    return dist_info


def test_armed_env_collapses_providers_offline(tmp_path, launcher):
    """Par de providers registrado + GUI funcionando + uv quebrado:
    o launcher remove so o dist-info extra e lanca — sem sync, sem
    uninstall e sem wheel algum. Regressao do review: o repair antigo
    desinstalava os providers antes de saber se havia wheel."""
    contrib = _add_provider(tmp_path / ".venv", "opencv-contrib-python")
    headless = _add_provider(tmp_path / ".venv", "opencv-contrib-python-headless")
    (tmp_path / ".venv" / "hand-installed").touch()
    uv = launcher / "uv"
    uv.write_text("#!/bin/sh\nprintf '%s\\n' \"$*\" >> commands\nexit 7\n")
    uv.chmod(0o755)

    subprocess.run(
        [BASH, "run.sh", "--check"],
        cwd=tmp_path,
        env={"PATH": str(launcher)},
        check=True,
        timeout=10,
    )
    assert not headless.exists()
    assert contrib.exists()
    assert not (tmp_path / "commands").exists()
    launched = (tmp_path / "launches").read_text().strip()
    assert tmp_path / launched == tmp_path / ".venv/bin/draw"


def test_uv_repair_prefers_locked_offline_sync(tmp_path, launcher):
    """Headless por cima + cache quente: o repair reinstala o contrib
    travado por cima via `uv sync --locked --offline` e derruba o
    dist-info extra — resolve pelo uv.lock, sem listagem, sem rede e
    sem uninstall."""
    headless = _add_provider(tmp_path / ".venv", "opencv-contrib-python-headless")
    (tmp_path / ".venv" / "gui-broken").touch()
    (tmp_path / "wheel-cached").touch()
    (tmp_path / "uv.lock").touch()
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
        _INSTALL_SYNC_HAND,
        _REPAIR_SYNC,
    ]
    assert all("uninstall" not in c for c in commands)
    assert not headless.exists()
    launched = (tmp_path / "launches").read_text().strip()
    assert tmp_path / launched == tmp_path / ".venv/bin/draw"


def test_uv_repair_falls_back_to_network_without_cache(tmp_path, launcher):
    """Sem o wheel no cache: `sync --offline` falha e so entao vai a rede."""
    _add_provider(tmp_path / ".venv", "opencv-contrib-python-headless")
    (tmp_path / ".venv" / "gui-broken").touch()
    (tmp_path / "uv.lock").touch()
    _fake_uv(launcher)

    subprocess.run(
        [BASH, "run.sh", "--check"],
        cwd=tmp_path,
        env={"PATH": str(launcher)},
        check=True,
        timeout=10,
    )
    syncs = [c for c in _commands(tmp_path) if c.startswith("sync")]
    assert syncs == [_INSTALL_SYNC_HAND, _REPAIR_SYNC, _REPAIR_SYNC_FALLBACK]
    launched = (tmp_path / "launches").read_text().strip()
    assert tmp_path / launched == tmp_path / ".venv/bin/draw"


def test_uv_hand_retry_syncs_inexact_and_repairs_hand_env(tmp_path, launcher):
    """Todo `uv sync` do launcher leva --inexact (pytest/ruff/drawlink
    editavel sobrevivem) e o repair roda no env -hand, nao no base."""
    marker = tmp_path / ".venv" / ".no_hand"
    marker.touch()
    os.utime(marker, (1, 1))
    (tmp_path / ".venv-hand" / "bin").mkdir(parents=True)
    headless = _add_provider(tmp_path / ".venv-hand", "opencv-contrib-python-headless")
    (tmp_path / ".venv-hand" / "gui-broken").touch()
    (tmp_path / "wheel-cached").touch()
    (tmp_path / "uv.lock").touch()
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
    assert syncs == [_INSTALL_SYNC_HAND, _REPAIR_SYNC]
    assert all("uninstall" not in c for c in commands)
    assert not headless.exists()
    assert (tmp_path / ".venv-hand" / "hand-installed").is_file()
    launched = (tmp_path / "launches").read_text().strip()
    assert tmp_path / launched == tmp_path / ".venv-hand/bin/draw"


def test_pip_repair_keeps_single_cv2_provider(tmp_path, launcher):
    """Fallback pip: forca-reinstala o contrib por cima e derruba o
    dist-info extra — um unico dono de cv2/ registrado, sem uninstall."""
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
    assert all("uninstall" not in c for c in commands)
    assert commands[-1] == (
        "-m pip install --no-deps --force-reinstall opencv-contrib-python>=4.8,<5.1"
    )
    venv = tmp_path / ".venv"
    providers = [p.name for p in (venv / "site").glob("*.dist-info")]
    assert providers == ["opencv_contrib_python-5.0.0.93.dist-info"]
    launched = (tmp_path / "launches").read_text().strip()
    assert tmp_path / launched == tmp_path / ".venv/bin/draw"


@pytest.mark.slow
def test_real_uv_plain_sync_keeps_cv2_importable(tmp_path):
    """Cache real populado so por `uv sync` travado (sem listagem de
    indice): o par contrib+headless armado e desarmado so por
    metadados, o repair offline reinstala o contrib pelo uv.lock por
    cima de um headless ativo, e syncs posteriores trocam o provedor
    sem matar `import cv2` nem a janela — tudo sem uninstall."""
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv nao esta no PATH")
    env = {
        key: value
        for key, value in os.environ.items()
        if key != "VIRTUAL_ENV" and not key.startswith("UV_")
    }
    env["UV_CACHE_DIR"] = str(tmp_path / "uvcache")
    (tmp_path / "pyproject.toml").write_text(MINI_PYPROJECT)
    lock = subprocess.run(
        [uv, "lock"],
        cwd=tmp_path,
        env=env,
        check=False,
        timeout=120,
        capture_output=True,
    )
    if lock.returncode != 0:
        pytest.skip("sem rede para resolver o lock do fixture")

    def run(args):
        subprocess.run(args, cwd=tmp_path, env=env, check=True, timeout=300)

    run([uv, "sync", "--extra", "gui"])
    python = tmp_path / ".venv" / "bin" / "python"
    # Cache de um clone que so rodou `uv sync` travado: wheel baixado,
    # sem listagem de indice — o cenario em que `uv pip install` falha.
    shutil.rmtree(tmp_path / "uvcache" / "simple-v21", ignore_errors=True)

    def drop_extras():
        run([str(python), "-c", _CV2_DROP_EXTRAS])

    def repair():
        # A sequencia real do _repair_opencv: reinstala o contrib por
        # cima e derruba os dist-infos extras — nunca desinstala.
        run(
            [
                uv,
                "sync",
                "--locked",
                "--offline",
                "--inexact",
                "--extra",
                "gui",
                "--reinstall-package",
                "opencv-contrib-python",
                "--no-install-package",
                "opencv-contrib-python-headless",
            ]
        )
        drop_extras()

    def providers():
        return subprocess.run(
            [uv, "pip", "list", "--python", str(python)],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def gui_opens():
        return (
            subprocess.run([str(python), "-c", _CV2_GUI_CHECK], check=False).returncode
            == 0
        )

    def only_contrib():
        dists = providers()
        return "opencv-contrib-python" in dists and not any(
            name in dists
            for name in (
                "opencv-contrib-python-headless",
                "opencv-python",
                "opencv-python-headless",
            )
        )

    # Apos `uv sync --extra gui` o env ja esta armado: os dois dists
    # registrados, contrib por cima. O colapso so-metadados do launcher
    # desarma sem wheel e sem rede — mesmo com o cache frio.
    assert gui_opens()
    assert not only_contrib()
    drop_extras()
    assert gui_opens()
    assert only_contrib()

    # `uv sync` exato manual: troca o provedor para o headless travado,
    # mas o cv2 segue importavel — provedor unico sai limpo.
    run([uv, "sync"])
    run([str(python), "-c", "import cv2"])
    assert not gui_opens()
    assert "opencv-contrib-python-headless" in providers()
    assert "opencv-contrib-python " not in providers()

    # O sync do proprio launcher (--inexact --extra gui
    # --no-install-package) reinstala o contrib por cima sem
    # desregistrar o headless — a janela abre, o par fica armado de
    # novo e o launcher o desarma no lancamento seguinte.
    run(
        [
            uv,
            "sync",
            "--inexact",
            "--extra",
            "gui",
            "--no-install-package",
            "opencv-contrib-python-headless",
        ]
    )
    assert gui_opens()
    assert not only_contrib()
    drop_extras()
    assert gui_opens()
    assert only_contrib()

    # `uv sync --inexact` manual (sem extra gui): mantem o contrib e
    # instala o headless por cima — a janela nao abre, o cv2 importa, e
    # o repair offline restaura o provedor unico com janela.
    run([uv, "sync", "--inexact"])
    assert not gui_opens()
    run([str(python), "-c", "import cv2"])
    repair()
    assert gui_opens()
    assert only_contrib()
