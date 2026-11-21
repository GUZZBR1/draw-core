"""Testes de schema, rotulagem e manifesto do corpus de clipes reais."""

import json

import cv2
import numpy as np
import pytest
from lab.corpus.clip import (
    CLIP_JSON_VERSION,
    CONDITION_KEYS,
    EXPECTED_RULES,
    ClipError,
    clip_frames,
    count_frames,
    load_clip,
    validate_clip,
    write_clip_json,
)
from lab.corpus.labels import ClipInitError, init_clip, upgrade_clip
from lab.corpus.manifest import (
    MANIFEST_NAME,
    build_manifest,
    hash_clip,
    iter_clip_dirs,
    load_manifest,
    verify_manifest,
    write_manifest,
)


def _write_frames(clip_dir, count=3, *, value=200):
    clip_dir.mkdir(parents=True, exist_ok=True)
    img = np.full((8, 8, 3), value, dtype=np.uint8)
    for i in range(count):
        cv2.imwrite(str(clip_dir / f"f{i:04d}.png"), img)


def _write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_v1_clip_loads_with_empty_defaults_and_validates(tmp_path):
    clip_dir = tmp_path / "c1"
    _write_frames(clip_dir, count=2)
    _write_json(
        clip_dir / "clip.json",
        {
            "scene_fps": 10.0,
            "orientation": "retrato",
            "frames": 2,
            "desc": "clipe v1 antigo",
        },
    )
    spec = load_clip(clip_dir)
    assert spec.version == 1
    assert spec.fps == 10.0
    assert spec.orientation == "retrato"
    assert spec.frames == 2
    assert spec.conditions == {}
    assert spec.provenance == {}
    assert spec.expected == []
    assert spec.issues == []
    assert spec.regions is None
    assert validate_clip(clip_dir) == []


def test_v2_full_clip_loads_and_validate_catches_bad_fields(tmp_path):
    clip_dir = tmp_path / "c2"
    _write_frames(clip_dir, count=3)
    write_clip_json(
        clip_dir,
        {
            "version": CLIP_JSON_VERSION,
            "scene_fps": 8.0,
            "orientation": "paisagem",
            "frames": 3,
            "desc": "sombra movel",
            "conditions": {CONDITION_KEYS[0]: "sombra-movel"},
            "provenance": {"source": "desk_capture"},
            "expected": [{"rule": EXPECTED_RULES[1], "min_px": 100}],
            "issues": [133],
        },
    )
    _write_json(clip_dir / "regions.json", {"writing": [[0, 0, 8, 8]]})

    spec = load_clip(clip_dir)
    assert spec.version == 2
    assert spec.conditions == {"lighting": "sombra-movel"}
    assert spec.provenance == {"source": "desk_capture"}
    assert spec.expected == [{"rule": "ink_present", "min_px": 100}]
    assert spec.issues == [133]
    assert spec.regions == {"writing": [[0, 0, 8, 8]]}
    assert validate_clip(clip_dir) == []

    # Condicao desconhecida, regra ruim e contagem divergente aparecem na validacao.
    _write_json(
        clip_dir / "clip.json",
        {
            "version": 2,
            "scene_fps": 8.0,
            "frames": 99,
            "desc": "ruim",
            "conditions": {"clima_inventado": "sol"},
            "expected": [{"rule": "regra_inexistente"}],
        },
    )
    problems = validate_clip(clip_dir)
    joined = "\n".join(problems)
    assert "clima_inventado" in joined
    assert "regra_inexistente" in joined
    assert "99" in joined

    with pytest.raises(ClipError):
        _write_json(clip_dir / "clip.json", {"version": 9, "scene_fps": 1})
        load_clip(clip_dir)


def test_count_frames_ignores_non_frame_pngs(tmp_path):
    clip_dir = tmp_path / "c_extra"
    _write_frames(clip_dir, count=2)
    img = np.zeros((8, 8, 3), dtype=np.uint8)
    cv2.imwrite(str(clip_dir / "mask_0000.png"), img)
    cv2.imwrite(str(clip_dir / "notes.png"), img)
    sub = clip_dir / "nested"
    sub.mkdir()
    cv2.imwrite(str(sub / "f0000.png"), img)
    assert count_frames(clip_dir) == 2


def test_clip_frames_is_the_shared_inventory(tmp_path):
    """O mesmo f*.png ordenado alimenta contagem e hash: preview.png,
    raw/ e imagens de outra extensao ficam fora dos dois."""
    clip_dir = tmp_path / "inv"
    _write_frames(clip_dir, count=2)
    img = np.zeros((8, 8, 3), dtype=np.uint8)
    cv2.imwrite(str(clip_dir / "preview.png"), img)
    raw = clip_dir / "raw"
    raw.mkdir()
    cv2.imwrite(str(raw / "f9999.png"), img)
    cv2.imwrite(str(clip_dir / "f0002.jpg"), img)

    assert [p.name for p in clip_frames(clip_dir)] == [
        "f0000.png",
        "f0001.png",
    ]
    assert count_frames(clip_dir) == 2
    h = hash_clip(clip_dir)
    cv2.imwrite(str(clip_dir / "mais_um.png"), img)
    assert hash_clip(clip_dir) == h  # fora do padrao, fora do hash


def test_init_clip_writes_v2_and_refuses_invalid_cases(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(ClipInitError):
        init_clip(empty_dir, fps=10.0)

    clip_dir = tmp_path / "ok"
    _write_frames(clip_dir, count=2)
    with pytest.raises(ClipInitError, match="desconhecida"):
        init_clip(clip_dir, fps=10.0, conditions={"foo": "bar"})

    out = init_clip(
        clip_dir,
        fps=12.0,
        orientation="retrato",
        desc="teste",
        conditions={"lighting": "baixa"},
        provenance={"source": "desk"},
        expected=[{"rule": "no_ink"}],
        issues=[129],
    )
    assert out == clip_dir / "clip.json"
    spec = load_clip(clip_dir)
    assert spec.version == 2
    assert spec.frames == 2
    assert spec.fps == 12.0
    assert spec.issues == [129]

    with pytest.raises(ClipInitError):
        init_clip(clip_dir, fps=12.0)

    init_clip(clip_dir, fps=15.0, overwrite=True)
    assert load_clip(clip_dir).fps == 15.0


def test_upgrade_clip_v1_to_v2_preserves_fields_and_is_idempotent(tmp_path):
    clip_dir = tmp_path / "legacy"
    _write_frames(clip_dir, count=2)
    _write_json(
        clip_dir / "clip.json",
        {
            "scene_fps": 7.5,
            "orientation": "paisagem",
            "frames": 2,
            "desc": "original",
            "rotate_applied": 180,
        },
    )
    upgrade_clip(clip_dir, provenance={"source": "bench-clips"})
    spec = load_clip(clip_dir)
    assert spec.version == 2
    assert spec.fps == 7.5
    assert spec.orientation == "paisagem"
    assert spec.desc == "original"
    assert spec.provenance == {"source": "bench-clips"}
    raw1 = (clip_dir / "clip.json").read_text(encoding="utf-8")
    assert json.loads(raw1)["rotate_applied"] == 180

    # Idempotente na segunda chamada
    upgrade_clip(clip_dir)
    raw2 = (clip_dir / "clip.json").read_text(encoding="utf-8")
    assert raw1 == raw2


def test_hash_clip_deterministic_sensitive_to_frames_ignores_scratch(tmp_path):
    clip_dir = tmp_path / "h"
    _write_frames(clip_dir, count=2, value=120)
    init_clip(clip_dir, fps=10.0)
    h1 = hash_clip(clip_dir)
    assert h1 == hash_clip(clip_dir)

    (clip_dir / "scratch.txt").write_text("anotacao irrelevante", encoding="utf-8")
    assert hash_clip(clip_dir) == h1

    _write_frames(clip_dir, count=2, value=40)
    assert hash_clip(clip_dir) != h1


def test_manifest_roundtrip_and_tamper_detection(tmp_path):
    c1 = tmp_path / "clip-a"
    c2 = tmp_path / "clip-b"
    _write_frames(c1, count=2, value=10)
    _write_frames(c2, count=3, value=20)
    init_clip(c1, fps=8.0, conditions={"lighting": "normal"}, issues=[129])
    init_clip(c2, fps=8.0)

    assert [d.name for d in iter_clip_dirs(tmp_path)] == ["clip-a", "clip-b"]
    manifest = build_manifest(tmp_path)
    out = write_manifest(tmp_path, manifest)
    assert out == tmp_path / MANIFEST_NAME
    loaded = load_manifest(tmp_path)
    assert loaded == manifest
    assert verify_manifest(tmp_path) == []

    # Alterar um quadro invalida o sha256.
    _write_frames(c1, count=2, value=99)
    problems = verify_manifest(tmp_path)
    assert any("sha256" in p and "clip-a" in p for p in problems)

    # Restaura o manifesto para testar diretorio faltante e clipe extra.
    write_manifest(tmp_path, build_manifest(tmp_path))
    for p in c2.iterdir():
        p.unlink()
    c2.rmdir()
    c3 = tmp_path / "clip-novo"
    _write_frames(c3, count=1)
    init_clip(c3, fps=8.0)
    problems2 = verify_manifest(tmp_path)
    assert any("clip-b" in p for p in problems2)
    assert any("clip-novo" in p for p in problems2)


def test_load_manifest_absent_and_bad_schema(tmp_path):
    assert load_manifest(tmp_path) is None
    (tmp_path / MANIFEST_NAME).write_text(
        json.dumps({"schema": 99, "clips": {}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_manifest(tmp_path)
