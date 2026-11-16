"""Fumaça do bridge: windows_helper.py compila e é stdlib-only.

O helper é um esboço Windows (ctypes/SendInput) — importar teria
efeitos colaterais de plataforma, então o teste compila e varre os
imports via ast em vez de executar.
"""

import ast
import py_compile
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
