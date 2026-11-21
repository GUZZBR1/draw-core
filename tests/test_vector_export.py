"""Testes leves de exporters/export_vectors.py (ponte SVG/DXF sem ximgproc)."""

import re

import cv2
import numpy as np

from draw.exporters import export_vectors as ev
from draw.exporters import vectorize as vz


def _synthetic_page():
    """Página 400x560 com retângulo, diagonal e círculo de traço grosso."""
    img = np.full((560, 400, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (60, 60), (220, 180), (0, 0, 0), thickness=5)
    cv2.line(img, (60, 300), (300, 480), (0, 0, 0), thickness=5)
    cv2.circle(img, (300, 130), 45, (0, 0, 0), thickness=4)
    return img


def test_zhang_suen_thins_to_one_pixel():
    ink = np.zeros((60, 60), dtype=bool)
    ink[28:33, 5:55] = True  # faixa horizontal de 5 px
    skel = ev.zhang_suen_thin(ink)
    assert skel.any()
    # Nenhuma coluna pode ter mais de 1 px de esqueleto na faixa afinada.
    assert skel[:, 10:50].sum(axis=0).max() <= 1


def test_pipeline_simplifies_and_roundtrips(tmp_path):
    img = _synthetic_page()
    # O pipeline export_vectors() ficou com a CLI (usa draw.config e
    # PageCleanInk); aqui os mesmos estagios puros na mesma ordem.
    h, w = img.shape[:2]
    ink = ev.filter_microfragments(ev.ink_mask_otsu(img), min_area=4)
    skel = ev.make_8_minimal(ev.zhang_suen_thin(ink))
    raw = ev.trace_polylines(skel)
    polylines = ev.simplify_polylines(raw, 1.5)
    width_px = ev.median_stroke_width(ink, skel)
    sx, sy = 210.0 / w, 297.0 / h
    assert len(polylines) >= 3
    assert sum(len(p["points"]) for p in polylines) < sum(len(p["points"]) for p in raw)

    svg_path = tmp_path / "p.svg"
    dxf_path = tmp_path / "p.dxf"
    ev.write_svg(polylines, svg_path, w, h, 210.0, 297.0, 1.0)
    ev.write_dxf(polylines, dxf_path, w, h, 210.0, 297.0, 1.0)

    svg_text = svg_path.read_text(encoding="utf-8")
    assert "<path" in svg_text and "<image" not in svg_text
    dxf_text = dxf_path.read_text(encoding="utf-8")
    assert "LWPOLYLINE" in dxf_text

    thickness = max(int(round(width_px)), 1)
    r_svg = ev.rasterize(ev.parse_svg_paths(svg_path), ink.shape, sx, sy, thickness)
    r_dxf = ev.rasterize(
        ev.parse_dxf_polylines(dxf_path),
        ink.shape,
        sx,
        sy,
        thickness,
        flip_y=True,
        paper_h_mm=297.0,
    )
    assert ev.iou(r_svg, ink) >= 0.45
    assert ev.iou(r_dxf, ink) >= 0.45


def test_two_by_two_dot_survives_thinning_and_exports(tmp_path):
    # Um ponto 2x2 passa por filter_microfragments (area=4) mas o
    # Zhang-Suen o apagava inteiro: o export omitia o ponto.
    ink = np.zeros((60, 60), dtype=bool)
    ink[10:12, 20:22] = True  # ponto 2x2
    ink[30:35, 5:55] = True  # faixa que sobrevive ao afinamento
    skel = ev.make_8_minimal(ev.zhang_suen_thin(ink))
    assert skel[10:12, 20:22].sum() == 1

    polylines = ev.trace_polylines(skel)
    singles = [p for p in polylines if len(p["points"]) == 1]
    assert len(singles) == 1
    px, py = singles[0]["points"][0]
    assert 20 <= px <= 21 and 10 <= py <= 11

    svg_path = tmp_path / "dot.svg"
    dxf_path = tmp_path / "dot.dxf"
    ev.write_svg(polylines, svg_path, 60, 60, 210.0, 297.0, 1.0)
    ev.write_dxf(polylines, dxf_path, 60, 60, 210.0, 297.0, 1.0)
    assert "<circle" in svg_path.read_text(encoding="utf-8")
    assert "LWPOLYLINE" in dxf_path.read_text(encoding="utf-8")


def test_parse_svg_paths_roundtrips_isolated_point(tmp_path):
    # <circle> (ponto isolado) nao era lido de volta pelo parser.
    lines = [
        {"points": np.array([[10.0, 10.0], [50.0, 50.0]]), "closed": False},
        {"points": np.array([[30.0, 20.0]]), "closed": False},
    ]
    svg_path = tmp_path / "rt.svg"
    ev.write_svg(lines, svg_path, 60, 60, 210.0, 297.0, 0.3)
    parsed = ev.parse_svg_paths(svg_path)
    assert len(parsed) == 2
    singles = [p for p, _c in parsed if len(p) == 1]
    assert len(singles) == 1
    # round-trip mm -> px (escala por eixo): o ponto volta para (30, 20) px
    scale = np.array([210.0 / 60, 297.0 / 60])
    assert np.allclose(singles[0][0] / scale, [30.0, 20.0], atol=0.2)


def test_per_stroke_width_flows_to_svg_and_dxf(tmp_path):
    """Pseudo-pressão por traço: o width_px que a vetorização anota vira
    o stroke-width do SVG e o grupo 43 do DXF por LWPOLYLINE — em vez de
    uma largura global igual para toda a página."""
    ink = np.zeros((80, 200), dtype=bool)
    ink[10:13, 10:190] = True  # traço fino ~3 px
    ink[40:52, 10:190] = True  # traço grosso ~12 px
    polylines = vz.vectorize_mask(ink, epsilon=1.0)
    assert len(polylines) == 2
    widths = sorted(p["width_px"] for p in polylines)
    assert widths[0] < widths[-1] / 2

    svg_path = tmp_path / "w.svg"
    dxf_path = tmp_path / "w.dxf"
    # stroke_w_mm=9.9 é o fallback: nao pode aparecer no arquivo quando
    # o width_px por traço está presente.
    ev.write_svg(polylines, svg_path, 200, 80, 210.0, 297.0, 9.9)
    ev.write_dxf(polylines, dxf_path, 200, 80, 210.0, 297.0, 9.9)

    svg_widths = sorted(
        float(w)
        for w in re.findall(
            r'stroke-width="([\d.]+)"', svg_path.read_text(encoding="utf-8")
        )
    )
    assert len(svg_widths) == 2
    assert svg_widths[0] < svg_widths[-1]
    assert 9.9 not in svg_widths

    dxf_lines = dxf_path.read_text(encoding="utf-8").splitlines()
    w43 = sorted(
        float(dxf_lines[i + 1]) for i, code in enumerate(dxf_lines) if code == "43"
    )
    assert len(w43) == 2
    assert w43[0] < w43[-1]


def test_lines_without_width_px_keep_the_uniform_fallback(tmp_path):
    """Polilinhas sem anotação (caminhos que não passam por
    vectorize_mask/stroke_widths_px) seguem com a largura global."""
    lines = [
        {"points": np.array([[0.0, 0.0], [40.0, 40.0]]), "closed": False},
        {"points": np.array([[50.0, 10.0]]), "closed": False},
    ]
    svg_path = tmp_path / "u.svg"
    dxf_path = tmp_path / "u.dxf"
    ev.write_svg(lines, svg_path, 60, 60, 210.0, 297.0, 0.5)
    ev.write_dxf(lines, dxf_path, 60, 60, 210.0, 297.0, 0.5)
    assert 'stroke-width="0.50"' in svg_path.read_text(encoding="utf-8")
    dxf_lines = dxf_path.read_text(encoding="utf-8").splitlines()
    w43 = [dxf_lines[i + 1] for i, code in enumerate(dxf_lines) if code == "43"]
    assert set(w43) == {"0.500"}
