"""Render de exibicao (draw/ink/render.py): canvas branco com tinta.

A confirmada sai em preto e a provisoria em cinza claro — a tinta
que o voto ainda nao fechou aparece mais clara para quem desenha
saber que pode sumir. O buffer de saida e reutilizado quando o
chamador o fornece com o formato certo.
"""

import numpy as np
import pytest

from draw.ink import render as ink_render


def test_render_canvas_paints_ink_black_on_white():
    mask = np.zeros((10, 12), np.uint8)
    mask[2:4, 3:6] = 255
    canvas = ink_render.render_canvas(mask)
    assert canvas.shape == (10, 12, 3)
    assert canvas.dtype == np.uint8
    np.testing.assert_array_equal(canvas[3, 4], (0, 0, 0))
    np.testing.assert_array_equal(canvas[0, 0], (255, 255, 255))
    # A máscara do chamador não é tocada.
    np.testing.assert_array_equal(mask[2:4, 3:6], 255)


def test_render_canvas_reuses_the_out_buffer():
    mask = np.zeros((10, 12), np.uint8)
    out = np.zeros((10, 12, 3), np.uint8)
    canvas = ink_render.render_canvas(mask, out=out)
    assert canvas is out
    # O buffer reutilizado volta branco antes de receber a tinta.
    assert (canvas == 255).all(axis=2).all()


def test_render_canvas_rejects_a_bad_out():
    mask = np.zeros((10, 12), np.uint8)
    with pytest.raises(ValueError):
        ink_render.render_canvas(mask, out=np.zeros((10, 12, 3), np.float32))
    with pytest.raises(ValueError):
        ink_render.render_canvas(mask, out=np.zeros((8, 12, 3), np.uint8))


def test_render_layered_canvas_paints_provisional_gray():
    confirmed = np.zeros((10, 12), np.uint8)
    confirmed[2:4, 3:6] = 255
    provisional = np.zeros((10, 12), np.uint8)
    provisional[2:4, 3:6] = 255  # já confirmada: não cinza
    provisional[7:9, 1:3] = 255
    canvas = ink_render.render_layered_canvas(confirmed, provisional)
    np.testing.assert_array_equal(canvas[3, 4], (0, 0, 0))
    np.testing.assert_array_equal(canvas[8, 2], (176, 176, 176))
    np.testing.assert_array_equal(canvas[0, 0], (255, 255, 255))


def test_render_layered_canvas_none_provisional_is_plain_canvas():
    confirmed = np.zeros((10, 12), np.uint8)
    confirmed[0, 0] = 255
    canvas = ink_render.render_layered_canvas(confirmed, None)
    plain = ink_render.render_canvas(confirmed)
    np.testing.assert_array_equal(canvas, plain)
