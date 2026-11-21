"""Evidencia fotometrica de "papel exposto", independente do MediaPipe.

A remocao de tinta confirmada (draw.ink.accumulator) so pode confiar em
uma regiao quando ela PARECE papel: luminancia compativel com a
referencia da folha e sem anomalia escura de bloco (mao, braco, caneta,
sombra). Incerteza congela a regiao — nunca a libera.

Tudo em blocos (media por INTER_AREA): custo de ~1 passada de resize,
sem float de pagina inteira.
"""

import cv2
import numpy as np

_SAMPLE_STRIDE = 8
_MIN_SAMPLES = 64
# Bloco so e papel se a media dele for >= esta fracao da referencia. Traco
# de caneta cobre poucos % do bloco; mao/sombra derrubam a media em >25%.
_MIN_RATIO = 0.78
_BLOCK_PX = 32
# Reducao previa por area (px por lado) antes do maximo por bloco.
_REDUCE_PX = 4
# Cor: pele tem B/R bem abaixo do papel (que e quase neutro). Tolera
# desvio relativo do B/R do bloco contra a referencia.
_CHROMA_TOL = 0.18


def paper_reference(image, visible=None):
    """(nivel de papel p90, razao B/R do papel) ou None se incerto.

    Amostrado com stride em pixels visiveis. Menos de _MIN_SAMPLES
    amostras => None (a regiao inteira congela).
    """
    sample = image[::_SAMPLE_STRIDE, ::_SAMPLE_STRIDE]
    gray = sample.mean(axis=2) if sample.ndim == 3 else sample.astype(np.float32)
    keep = None
    if visible is not None:
        keep = np.asarray(visible)[::_SAMPLE_STRIDE, ::_SAMPLE_STRIDE] > 0
        if keep.shape != gray.shape or int(np.count_nonzero(keep)) < _MIN_SAMPLES:
            return None
        values = gray[keep]
    else:
        values = gray.ravel()
    if values.size < _MIN_SAMPLES:
        return None
    level = float(np.percentile(values, 90))
    if level <= 1.0:
        return None
    ratio = 1.0
    if sample.ndim == 3 and sample.shape[2] >= 3:
        bright = gray >= level * 0.9
        if keep is not None:
            bright &= keep
        if int(np.count_nonzero(bright)) >= _MIN_SAMPLES // 4:
            blue = float(sample[..., 0][bright].mean())
            red = float(sample[..., 2][bright].mean())
            ratio = blue / red if red > 1.0 else 1.0
    return level, ratio


def paper_exposed(image, reference, *, min_ratio=_MIN_RATIO, block=_BLOCK_PX):
    """Mascara bool HxW: True onde ha evidencia de papel exposto.

    reference e o par de paper_reference; None => tudo False (incerteza
    congela). A estatistica e o MAXIMO (por canal) numa janela deslizante
    de `block` px centrada em cada amostra: traco de caneta, mesmo
    grosso, deixa papel claro na janela; mao, braco e sombra mais largos
    que a janela escurecem ate o pixel mais claro dela, onde quer que
    caiam em relacao a uma grade (nao ha fronteira de bloco para o dedo
    se esconder). Janela com o claro abaixo de min_ratio * nivel, ou com
    B/R fora da tolerancia da referencia (pele, sombra colorida), nao e
    papel. O resultado e erodido em meia janela: fail-closed na borda.
    """
    height, width = image.shape[:2]
    if reference is None:
        return np.zeros((height, width), dtype=bool)
    level, ratio = reference
    step = _REDUCE_PX
    cells = max(1, block // step)
    sample = image[::step, ::step]
    peak = cv2.dilate(sample, np.ones((cells, cells), np.uint8))
    if peak.ndim == 3 and peak.shape[2] >= 3:
        peak = peak.astype(np.float32)
        gray = peak.mean(axis=2)
        ok = gray >= min_ratio * level
        red = peak[..., 2]
        local = np.divide(peak[..., 0], red, out=np.ones_like(red), where=red > 1.0)
        ok &= np.abs(local - ratio) <= _CHROMA_TOL * max(ratio, 1e-3)
    else:
        ok = peak.astype(np.float32) >= min_ratio * level
    half = max(1, cells // 2)
    ok = cv2.erode(
        ok.astype(np.uint8),
        np.ones((2 * half + 1, 2 * half + 1), np.uint8),
        borderValue=1,
    )
    # Fator inteiro exato (sem esticar a ultima celula), recortado ao tamanho.
    grown = cv2.resize(ok, None, fx=step, fy=step, interpolation=cv2.INTER_NEAREST)
    return grown[:height, :width].view(bool)
