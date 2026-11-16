"""Contratos tipados entre os estágios do pipeline.

Dataclasses congeladas (frozen, slots): os módulos trocam objetos
imutáveis destes tipos, nunca dicts soltos ou tuplas posicionais
(docs/MIGRATION_SPEC.md, "Rules for what gets copied"). Nenhuma
dependência além de numpy — o contrato é a fronteira para uma
futura implementação nativa dos estágios quentes.
"""

from dataclasses import dataclass
from typing import Literal, get_args

import numpy as np

_CORNERS_SHAPE = (4, 2)
_PageDecision = Literal["same", "new_page", "defer"]


def _corners_float32(value, name):
    """Normaliza cantos para (4, 2) float32, com cópia própria."""
    corners = np.array(value, dtype=np.float32, copy=True)
    if corners.shape != _CORNERS_SHAPE:
        raise ValueError(f"{name} precisa ter forma {_CORNERS_SHAPE}: {corners.shape}")
    return corners


@dataclass(frozen=True, slots=True)
class FramePacket:
    """Um quadro capturado: imagem BGR (H, W, 3) uint8 e identidade.

    captured_at é um carimbo monotônico em segundos (time.monotonic);
    sequence é o número de sequência da fonte, >= 0.
    """

    image: np.ndarray
    captured_at: float
    sequence: int

    def __post_init__(self):
        if not isinstance(self.image, np.ndarray) or self.image.ndim != 3:
            raise ValueError("image precisa ser um ndarray (H, W, 3)")
        if self.image.shape[2] != 3:
            raise ValueError(f"image precisa ter 3 canais: {self.image.shape}")
        if self.image.dtype != np.uint8:
            raise ValueError(f"image precisa ser uint8: {self.image.dtype}")
        if self.sequence < 0:
            raise ValueError(f"sequence precisa ser >= 0: {self.sequence}")


@dataclass(frozen=True, slots=True)
class SheetQuad:
    """O quadrilátero da folha no espaço da câmera.

    corners é (4, 2) float32 ou None; verdict é "paper" ou None
    (o detector devolve a dupla (cantos, veredito); sem folha
    confirmada o par é (None, None)). detector nomeia a fonte.
    """

    corners: np.ndarray | None
    verdict: str | None
    detector: str = ""

    def __post_init__(self):
        if self.corners is not None:
            object.__setattr__(
                self, "corners", _corners_float32(self.corners, "corners")
            )
        if self.verdict is not None and self.verdict != "paper":
            raise ValueError(f"verdict precisa ser None ou 'paper': {self.verdict!r}")

    @property
    def present(self):
        """True quando há quadrilátero de folha."""
        return self.corners is not None


@dataclass(frozen=True, slots=True)
class PageIdentity:
    """Decisão de identidade da página (F-11).

    generation identifica a sessão de página; decision é o desfecho
    do juiz; recall/containment são as evidências do confronto, em
    [0, 1] quando presentes.
    """

    generation: int
    decision: _PageDecision
    recall: float | None = None
    containment: float | None = None

    def __post_init__(self):
        if self.decision not in get_args(_PageDecision):
            raise ValueError(f"decision inválida: {self.decision!r}")
        for name in ("recall", "containment"):
            value = getattr(self, name)
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} precisa estar em [0, 1]: {value}")


@dataclass(frozen=True, slots=True)
class InkState:
    """Estado da tinta numa geração de página.

    confirmed e provisional são máscaras 2D uint8 (None enquanto a
    passada não produziu); anchor_corners é o quad (4, 2) que ancora
    a geometria da tinta na cena.
    """

    confirmed: np.ndarray | None
    provisional: np.ndarray | None
    generation: int
    anchor_corners: np.ndarray | None = None

    def __post_init__(self):
        for name in ("confirmed", "provisional"):
            mask = getattr(self, name)
            if mask is not None and (
                not isinstance(mask, np.ndarray)
                or mask.ndim != 2
                or mask.dtype != np.uint8
            ):
                raise ValueError(f"{name} precisa ser máscara 2D uint8 ou None")
        if self.anchor_corners is not None:
            object.__setattr__(
                self,
                "anchor_corners",
                _corners_float32(self.anchor_corners, "anchor_corners"),
            )
