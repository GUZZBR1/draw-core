"""Entradas externas corrompidas/truncadas não derrubam nem estouram memória.

Cobre os leitores endurecidos de SECURITY_MODEL.md ("Entry points")
do repositório legado: imagens, JSON e JSONL (draw/infra/safe_io.py)
e a marcação de pastas privadas com .gitignore "*".
"""

import struct
from pathlib import Path

import cv2
import numpy as np
import pytest

from draw.infra import safe_io

ROOT = Path(__file__).resolve().parent.parent


def _png(width=32, height=24, channels=3):
    shape = (height, width, channels) if channels > 1 else (height, width)
    ok, buf = cv2.imencode(".png", np.full(shape, 200, dtype=np.uint8))
    assert ok
    return buf.tobytes()


def _jpg(width=32, height=24):
    ok, buf = cv2.imencode(".jpg", np.full((height, width, 3), 90, np.uint8))
    assert ok
    return buf.tobytes()


# --- imagens -------------------------------------------------------------


def test_image_dimensions_from_headers():
    assert safe_io.image_dimensions(_png(40, 30)) == (40, 30)
    assert safe_io.image_dimensions(_jpg(40, 30)) == (40, 30)
    assert safe_io.image_dimensions(b"GIF89a....") is None


@pytest.mark.parametrize("make", [_png, _jpg])
@pytest.mark.parametrize("cut", [0, 4, 12, 23])
def test_truncated_headers_are_rejected(make, cut):
    data = make()[:cut]
    with pytest.raises(safe_io.InputLimitError):
        safe_io.check_image_bytes(data)
    assert safe_io.decode_image(data) is None


@pytest.mark.parametrize("make", [_png, _jpg])
def test_truncated_body_never_raises(make):
    data = make(256, 256)
    for cut in (len(data) // 3, len(data) // 2, len(data) - 3):
        result = safe_io.decode_image(data[:cut])
        assert result is None or result.shape[:2] == (256, 256)


def test_png_bomb_dimensions_rejected_before_decode():
    data = bytearray(_png())
    struct.pack_into(">II", data, 16, 100_000, 100_000)
    with pytest.raises(safe_io.InputLimitError, match="dimensoes"):
        safe_io.check_image_bytes(bytes(data))
    assert safe_io.decode_image(bytes(data)) is None


def test_zero_dimension_rejected():
    data = bytearray(_png())
    struct.pack_into(">II", data, 16, 0, 10)
    assert safe_io.decode_image(bytes(data)) is None


def test_oversized_file_not_read(tmp_path):
    path = tmp_path / "grande.png"
    path.write_bytes(_png() + b"\x00" * 2048)
    assert safe_io.read_image(path, max_bytes=1024) is None
    assert safe_io.read_image(path) is not None


def test_read_image_missing_and_garbage(tmp_path):
    assert safe_io.read_image(tmp_path / "nao.png") is None
    junk = tmp_path / "lixo.png"
    junk.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\xff" * 64)
    assert safe_io.read_image(junk) is None


def test_read_image_grayscale_flag(tmp_path):
    path = tmp_path / "m.png"
    path.write_bytes(_png(16, 8, channels=1))
    assert safe_io.read_image(path, cv2.IMREAD_GRAYSCALE).shape == (8, 16)


# --- JSON / JSONL ----------------------------------------------------------


def test_read_json_limits_and_syntax(tmp_path):
    path = tmp_path / "a.json"
    path.write_text('{"a": 1}')
    assert safe_io.read_json(path) == {"a": 1}
    with pytest.raises(safe_io.InputLimitError, match="limite"):
        safe_io.read_json(path, max_bytes=4)
    path.write_text('{"a": ')
    with pytest.raises(safe_io.InputLimitError, match="JSON invalido"):
        safe_io.read_json(path)
    path.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(safe_io.InputLimitError):
        safe_io.read_json(path)


def test_read_json_deep_nesting_is_controlled(tmp_path):
    path = tmp_path / "fundo.json"
    path.write_text("[" * 200_000 + "]" * 200_000)
    with pytest.raises(safe_io.InputLimitError):
        safe_io.read_json(path)


def test_iter_jsonl_reports_line_and_limits(tmp_path):
    path = tmp_path / "m.jsonl"
    path.write_text('{"a": 1}\n\n{"b": 2}\n{"c": \n')
    rows = []
    with pytest.raises(safe_io.InputLimitError, match=":4:"):
        for row in safe_io.iter_jsonl(path):
            rows.append(row)
    assert rows == [(1, {"a": 1}), (3, {"b": 2})]
    path.write_text("[1, 2]\n")
    with pytest.raises(safe_io.InputLimitError, match="objeto"):
        list(safe_io.iter_jsonl(path))
    path.write_text('{"a": 1}\n' * 5)
    with pytest.raises(safe_io.InputLimitError, match="linhas"):
        list(safe_io.iter_jsonl(path, max_lines=3))
    path.write_text('{"a": "' + "x" * 100 + '"}\n')
    with pytest.raises(safe_io.InputLimitError, match="bytes"):
        list(safe_io.iter_jsonl(path, max_line_bytes=50))


# --- gravação privada -----------------------------------------------------


def test_ensure_private_dir_appends_catch_all_to_existing_gitignore(tmp_path):
    (tmp_path / ".gitignore").write_text("custom\n")
    safe_io.ensure_private_dir(tmp_path)
    text = (tmp_path / ".gitignore").read_text()
    assert text.startswith("custom\n")
    assert "*" in text.split()


def test_ensure_private_dir_gitignore_append_is_idempotent(tmp_path):
    (tmp_path / ".gitignore").write_text("custom\n")
    safe_io.ensure_private_dir(tmp_path)
    once = (tmp_path / ".gitignore").read_text()
    safe_io.ensure_private_dir(tmp_path)
    assert (tmp_path / ".gitignore").read_text() == once


def test_ensure_private_dir_keeps_gitignore_with_catch_all(tmp_path):
    (tmp_path / ".gitignore").write_text("# comentario\n*\n")
    safe_io.ensure_private_dir(tmp_path)
    assert (tmp_path / ".gitignore").read_text() == "# comentario\n*\n"


def test_repository_gitignore_covers_private_data():
    lines = set((ROOT / ".gitignore").read_text().splitlines())
    # dataset/ não é padrão deste repo: datasets vivem em draw-training.
    for pattern in ("captures/", "sessions/", "*.drawcap"):
        assert pattern in lines, pattern


def test_read_json_integer_past_digit_limit_is_input_limit(tmp_path):
    path = tmp_path / "big.json"
    path.write_text("9" * 5000)
    with pytest.raises(safe_io.InputLimitError):
        safe_io.read_json(path)


def test_iter_jsonl_integer_past_digit_limit_is_input_limit(tmp_path):
    path = tmp_path / "big.jsonl"
    path.write_text('{"n": ' + "9" * 5000 + "}\n")
    with pytest.raises(safe_io.InputLimitError):
        list(safe_io.iter_jsonl(path))
