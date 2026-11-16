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

# Todo veredito que o pipeline legado produz ou propaga no slot
# `verdict`: "paper" (o interior do candidato passa no portão de
# textura — paper.py/neural.py), "blank_maybe" (candidato branco o
# bastante, mas liso demais para afirmar papel — o rastreador pede
# confirmação mais longa) e "none" (o laço rebaixa para "none" uma
# detecção fraca barrada no portão de primeira confirmação). Ausência
# de veredito é representada por None, não por "none".
SHEET_VERDICTS = frozenset({"paper", "blank_maybe", "none"})


def _corners_float32(value, name):
    """Normaliza cantos para (4, 2) float32, com cópia própria."""
    corners = np.array(value, dtype=np.float32, copy=True)
    if corners.shape != _CORNERS_SHAPE:
        raise ValueError(f"{name} precisa ter forma {_CORNERS_SHAPE}: {corners.shape}")
    corners.flags.writeable = False
    return corners


@dataclass(frozen=True, slots=True)
class FramePacket:
    """Um quadro capturado: imagem BGR (H, W, 3) uint8 e identidade.

    captured_at é um carimbo monotônico em segundos (time.monotonic);
    sequence é o número de sequência da fonte, >= 0. image é guardada
    como visão somente-leitura do buffer recebido (sem copiar o frame):
    o produtor não pode mutar o buffer depois de publicar o pacote.
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
        image = self.image.view()
        image.flags.writeable = False
        object.__setattr__(self, "image", image)


@dataclass(frozen=True, slots=True)
class SheetQuad:
    """O quadrilátero da folha no espaço da câmera.

    corners é (4, 2) float32 ou None; verdict é None ou um de
    SHEET_VERDICTS ("paper"/"blank_maybe"/"none" — a folha pode
    confirmar com o rótulo "blank_maybe" que a sustentou). O par
    sempre vem junto: sem folha confirmada é (None, None).
    detector nomeia a fonte.
    """

    corners: np.ndarray | None
    verdict: str | None
    detector: str = ""

    def __post_init__(self):
        if (self.corners is None) != (self.verdict is None):
            raise ValueError(
                "corners e verdict precisam vir juntos: "
                "(cantos, 'paper') ou (None, None)"
            )
        if self.corners is not None:
            object.__setattr__(
                self, "corners", _corners_float32(self.corners, "corners")
            )
        if self.verdict is not None and self.verdict not in SHEET_VERDICTS:
            raise ValueError(
                f"verdict precisa ser None ou um de {sorted(SHEET_VERDICTS)}: "
                f"{self.verdict!r}"
            )

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
    passada não produziu), guardadas como visões somente-leitura do
    buffer recebido: o produtor não pode mutar a máscara depois de
    publicar. anchor_corners é o quad (4, 2) que ancora a geometria
    da tinta na cena.
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
            if mask is not None:
                view = mask.view()
                view.flags.writeable = False
                object.__setattr__(self, name, view)
        if self.anchor_corners is not None:
            object.__setattr__(
                self,
                "anchor_corners",
                _corners_float32(self.anchor_corners, "anchor_corners"),
            )


@dataclass(frozen=True, slots=True)
class GateInfo:
    """O pacote do portão de primeira confirmação (frente 88).

    Extraído do rastro da detecção combinada quando ela traz os
    campos do portão: a fonte do desfecho, o logit de presença e a
    fração de aresta da máscara. Rastro sem esses campos não tem
    pacote — o laço não julga por falta de sinal.
    """

    source: str | None = None
    presence_logit: float | None = None
    edge_in: float | None = None


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """Um resultado de detecção de folha publicado pelo worker.

    sequence é o número de sequência do resultado, >= 0. corners é
    (4, 2) float32 somente-leitura quando presente; verdict é None
    ou um de SHEET_VERDICTS ("paper"/"blank_maybe"/"none") — os dois
    NÃO precisam vir juntos, porque "papel visto, quadrilátero não
    fechou" é um caso legítimo (presença sem posição). captured_at é
    o carimbo de captura do quadro
    examinado; detect_ms é a duração da detecção em ms, >= 0.
    gate_info é o pacote do portão quando o rastro o traz.
    coverage_mask e hand_mask são máscaras 2D uint8 (visões
    somente-leitura do buffer recebido) publicadas só quando o
    detector roda com cobertura; sem cobertura ficam None.
    """

    sequence: int
    corners: np.ndarray | None
    verdict: str | None
    captured_at: float
    detect_ms: float
    gate_info: GateInfo | None = None
    coverage_mask: np.ndarray | None = None
    hand_mask: np.ndarray | None = None

    def __post_init__(self):
        if self.sequence < 0:
            raise ValueError(f"sequence precisa ser >= 0: {self.sequence}")
        if self.corners is not None:
            object.__setattr__(
                self, "corners", _corners_float32(self.corners, "corners")
            )
        if self.verdict is not None and self.verdict not in SHEET_VERDICTS:
            raise ValueError(
                f"verdict precisa ser None ou um de {sorted(SHEET_VERDICTS)}: "
                f"{self.verdict!r}"
            )
        if self.detect_ms < 0:
            raise ValueError(f"detect_ms precisa ser >= 0: {self.detect_ms}")
        for name in ("coverage_mask", "hand_mask"):
            mask = getattr(self, name)
            if mask is not None and (
                not isinstance(mask, np.ndarray)
                or mask.ndim != 2
                or mask.dtype != np.uint8
            ):
                raise ValueError(f"{name} precisa ser máscara 2D uint8 ou None")
            if mask is not None:
                view = mask.view()
                view.flags.writeable = False
                object.__setattr__(self, name, view)
