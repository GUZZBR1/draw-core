"""Canvas de exibicao: confirmada em preto, provisoria em cinza."""

import numpy as np


def render_canvas(ink_mask, out=None):
    """Renderiza canvas branco com tinta preta, reutilizando ``out`` se dado."""
    if out is None:
        canvas = np.full((*ink_mask.shape, 3), 255, dtype=np.uint8)
    else:
        expected_shape = (*ink_mask.shape, 3)
        if out.shape != expected_shape or out.dtype != np.uint8:
            raise ValueError(
                f"out de render_canvas precisa ser {expected_shape} uint8, "
                f"veio {out.shape} {out.dtype}"
            )
        canvas = out
        canvas.fill(255)
    canvas[ink_mask > 0] = (0, 0, 0)
    return canvas


def render_layered_canvas(confirmed, provisional, out=None):
    """Canvas de exibicao: confirmada em preto, provisoria em cinza.

    A provisoria e tinta que a primeira passada viu e o voto
    ainda nao confirmou. Ela aparece mais clara para quem desenha
    saber que pode sumir, e nunca entra no canvas que poll()
    entrega aos consumidores.
    """
    canvas = render_canvas(confirmed, out=out)
    if provisional is not None:
        light = (provisional > 0) & (confirmed == 0)
        if np.any(light):
            canvas[light] = (176, 176, 176)
    return canvas
