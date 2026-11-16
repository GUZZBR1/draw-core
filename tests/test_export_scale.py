"""Escala de exportação SVG/DXF: a inferência por formato exige a grade.

Auditoria do PR #47 (2026-11-08): ``_export_scale`` devolvia a escala
uniforme do formato (mm_per_px = altura_mm/1200) para QUALQUER imagem
cujas dimensões em mm batessem com um formato conhecido — inclusive
imagens fora da grade canônica, onde a escala em x saía errada em até
+17,9% em silêncio. Estes testes fixam a extensão absoluta em mm.

Aqui ``formats`` é injetado (o chamador com acesso a draw.config monta
a mesma tripla a partir de FORMATS/paper_grid/mm_per_px); os valores
replicam a entrada "a4" do legado.
"""

import numpy as np

from draw.exporters.export_vectors import _export_scale, write_svg

# (nome, dimensoes_mm, grade_px, mm_por_px) — replica de draw.config["a4"].
FORMATS = [("a4", (210.0, 297.0), (850, 1200), 297.0 / 1200)]


def test_on_grid_a4_uses_uniform_format_scale():
    sx, sy = _export_scale(850, 1200, 210, 297, formats=FORMATS)
    assert sx == sy == 297.0 / 1200


def test_off_grid_image_falls_back_to_per_axis():
    # 400x560 com mm de A4: NÃO é a grade (850x1200) — fallback por eixo.
    sx, sy = _export_scale(400, 560, 210, 297, formats=FORMATS)
    assert sx == 210 / 400
    assert sy == 297 / 560
    assert sx != 297.0 / 1200


def test_explicit_scale_wins():
    assert _export_scale(400, 560, 210, 297, scale=(0.5, 0.25)) == (0.5, 0.25)


def test_no_formats_falls_back_to_per_axis():
    # Sem tabela de formatos, a escala uniforme do formato não existe.
    sx, sy = _export_scale(850, 1200, 210, 297)
    assert sx == 210 / 850
    assert sy == 297 / 1200


def test_svg_absolute_extent_off_grid(tmp_path):
    # Um segmento de canto a canto numa página 400x560 "A4" tem que medir
    # 210x297 mm no SVG — nem um fio a mais em x.
    lines = [{"points": np.array([[0.0, 0.0], [399.0, 559.0]]), "closed": False}]
    out = tmp_path / "extent.svg"
    write_svg(lines, str(out), 400, 560, 210, 297, 0.3, formats=FORMATS)
    text = out.read_text(encoding="utf-8")
    assert 'width="210mm"' in text
    assert 'height="297mm"' in text
    assert 'viewBox="0 0 210 297"' in text
    # E o ponto final do segmento cai no canto (209.48, 296.47) — a
    # escala por eixo aplicada, nao a uniforme do formato (0,2475
    # daria 98.75 em x).
    assert "209.48 296.47" in text
