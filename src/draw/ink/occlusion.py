"""Photometric guard for page regions darkened by hands or shadows."""

import cv2
import numpy as np

from ..contracts import ExposureAssessment

_REFERENCE_TILE_PX = 24
_PAGE_REFERENCE_PERCENTILE = 70.0
_MIN_DARKENING = 5.0
_DARKENING_FRACTION = 0.20
_CHROMA_CHANGE = 0.20
_VISIBLE_TILE_FRACTION = 0.85
# Um deslocamento fotométrico da página inteira (luz da sala caindo,
# auto-exposição da câmera, balanço de branco) move a quase totalidade
# dos tiles de uma vez — não é oclusão local. Quando a parcela anômala
# dos tiles avaliáveis chega a _GLOBAL_SHIFT_FRACTION as referências
# cedem ao nível novo, em vez de congelar a página num único bloco:
# a referência que só sobe não distingue uma queda global de >20% de
# um occluder, e sem esta saída a página inteira virava veto
# (Devin Review do PR #144).
_GLOBAL_SHIFT_FRACTION = 0.8
_GLOBAL_SHIFT_MIN_TILES = 4
# Recuperação por preenchimento: um bloco escuro que o modelo lê como
# tinta, passada após passada e com a mão fora do tile, é conteúdo da
# página — não oclusor. Até _FILL_RECOVERY_PASSES seguidas o veto de
# adição vale como sempre; depois ele cai só para o voto de adição.
# A remoção segue exigindo papel exposto, que o preenchimento nunca
# produz: o tile continua anômalo para o segundo veredito.
_FILL_INK_TILE_SUPPORT = 0.5
_FILL_RECOVERY_PASSES = 4


class PaperExposureGuard:
    """Track the brightest observed paper level and reject darkened tiles.

    The page-clean model can report a confirmed stroke as absent when a
    hand or shadow covers it. This guard uses the warped camera image, not
    the hand model, and turns such regions into unknown evidence. Its
    brightness reference only moves upward, so a brief shadow cannot become
    the new baseline — except when nearly the whole visible page changes
    at once, which is a global illumination shift, not an occluder: then
    the references follow the scene instead of blocking the page. A coarse
    chroma reference also rejects objects whose brightness resembles the
    paper. The low-resolution references keep the per-pass cost small and
    make fine pen strokes too small to trigger the guard.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self._reference = None
        self._color_reference = None
        self._page_reference = None
        self._page_color_reference = None
        self._ink_streak = None

    def observe(self, image, visible=None, ink_prob=None):
        """Return separate masks for safe additions and paper exposure.

        Only uint8 camera images carry reliable photometric evidence. An
        unsupported image fails closed for erasure at the accumulator
        boundary, while preserving existing callers that provide only ink
        probabilities. A thin mark can change paper luminance without
        looking like an object block: it remains available for drawing,
        but its pixels still cannot prove that prior ink disappeared.

        `ink_prob` (o mapa de probabilidade desta passada, na mesma
        grade) alimenta a recuperação por preenchimento: um bloco que o
        modelo lê como tinta por _FILL_RECOVERY_PASSES passadas, sempre
        com o tile à vista, deixa de vetar adições. Sem o mapa o veto é
        permanente, como antes.
        """
        if not isinstance(image, np.ndarray) or image.dtype != np.uint8:
            return None
        if image.ndim not in (2, 3) or (image.ndim == 3 and image.shape[2] != 3):
            return None

        height, width = image.shape[:2]
        grid_width = max(1, (width + _REFERENCE_TILE_PX - 1) // _REFERENCE_TILE_PX)
        grid_height = max(1, (height + _REFERENCE_TILE_PX - 1) // _REFERENCE_TILE_PX)
        size = (grid_width, grid_height)
        reduced = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
        if image.ndim == 3:
            current = cv2.cvtColor(reduced, cv2.COLOR_BGR2GRAY).astype(np.float32)
            color = reduced.astype(np.float32)
        else:
            current = reduced.astype(np.float32)
            color = None

        if visible is None:
            updateable = np.ones(current.shape, dtype=bool)
        else:
            visible = np.asarray(visible, dtype=bool)
            if visible.shape != (height, width):
                updateable = np.zeros(current.shape, dtype=bool)
            elif np.all(visible):
                updateable = np.ones(current.shape, dtype=bool)
            else:
                fraction = cv2.resize(
                    visible.astype(np.uint8), size, interpolation=cv2.INTER_AREA
                )
                updateable = fraction >= _VISIBLE_TILE_FRACTION

        if self._reference is None or self._reference.shape != current.shape:
            self._reference = np.full(current.shape, np.nan, dtype=np.float32)
            self._color_reference = (
                None
                if color is None
                else np.full((*current.shape, 3), np.nan, dtype=np.float32)
            )
            self._page_reference = None
            self._page_color_reference = None
            self._ink_streak = np.zeros(current.shape, dtype=np.uint8)

        known = np.isfinite(self._reference)
        candidates = current[updateable]
        if candidates.size:
            page_reference = float(
                np.percentile(candidates, _PAGE_REFERENCE_PERCENTILE)
            )
            if self._page_reference is None:
                self._page_reference = page_reference
            else:
                self._page_reference = max(self._page_reference, page_reference)

        # A tile with no clean history is compared to the page's robust
        # brightness estimate. This catches a hand already present on the
        # first sampled frame, before its darkness can become its baseline.
        expected = np.where(known, self._reference, self._page_reference or 0.0)
        drop = np.maximum(_MIN_DARKENING, expected * _DARKENING_FRACTION)
        darkened = current < expected - drop

        color_anomaly = np.zeros(current.shape, dtype=bool)
        if color is not None:
            chroma = color / np.maximum(current[..., None], 20.0)
            color_tiles = updateable & ~darkened
            if np.any(color_tiles):
                self._page_color_reference = np.median(
                    chroma[color_tiles], axis=0
                ).astype(np.float32)
            if self._page_color_reference is not None:
                expected_color = (
                    np.where(
                        known[..., None],
                        self._color_reference,
                        self._page_color_reference,
                    )
                    if self._color_reference is not None
                    else np.broadcast_to(self._page_color_reference, chroma.shape)
                )
                color_anomaly = (
                    np.linalg.norm(chroma - expected_color, axis=2) > _CHROMA_CHANGE
                )

        anomalous = darkened | color_anomaly
        updateable_px = int(np.count_nonzero(updateable))
        shifted = int(np.count_nonzero(anomalous & updateable))
        if shifted >= _GLOBAL_SHIFT_MIN_TILES and shifted >= (
            _GLOBAL_SHIFT_FRACTION * updateable_px
        ):
            # Quase toda a página à vista mudou junta: é a iluminação
            # global, não um oclusor. As referências cedem ao nível
            # novo de uma vez; sem isso o quarto escurecido congelava
            # a página atrás de um bloco único.
            self._reference[updateable] = current[updateable]
            if self._color_reference is not None:
                self._color_reference[updateable] = chroma[updateable]
            anomalous = np.zeros(current.shape, dtype=bool)

        # Recuperação por preenchimento: o streak conta as passadas
        # seguidas em que o tile anômalo, à vista, é lido como tinta
        # pelo modelo. A mão sobre o tile (updateable False) não
        # deixa a contagem andar — a adoção só acontece com a mão
        # fora do caminho ou quando a cena não tem máscara alguma.
        supported = np.zeros(current.shape, dtype=bool)
        if ink_prob is not None and np.any(anomalous):
            ink_prob = np.asarray(ink_prob, dtype=np.float32)
            if ink_prob.shape == (height, width):
                supported = (
                    anomalous
                    & updateable
                    & (
                        cv2.resize(ink_prob, size, interpolation=cv2.INTER_AREA)
                        >= _FILL_INK_TILE_SUPPORT
                    )
                )
        self._ink_streak[supported] = np.minimum(
            self._ink_streak[supported].astype(np.uint16) + 1, 255
        ).astype(np.uint8)
        self._ink_streak[~supported] = 0
        adopted = self._ink_streak >= _FILL_RECOVERY_PASSES

        # The removal test uses every anomalous tile. For additions, require
        # a two-dimensional block before suppressing pixels; a thin dark pen
        # stroke is not an object or a shadow boundary.
        block = np.zeros(anomalous.shape, dtype=np.uint8)
        if np.any(anomalous):
            count, labels, stats, _ = cv2.connectedComponentsWithStats(
                anomalous.astype(np.uint8), connectivity=8
            )
            for label in range(1, count):
                _x, _y, block_width, block_height, area = stats[label]
                if block_width >= 3 and block_height >= 3 and area >= 9:
                    block[labels == label] = 1
        if np.any(adopted):
            block[adopted] = 0
        if np.any(block):
            block = cv2.dilate(block, np.ones((3, 3), dtype=np.uint8))

        initialize = updateable & ~known & ~anomalous
        self._reference[initialize] = current[initialize]
        if self._color_reference is not None:
            self._color_reference[initialize] = chroma[initialize]
        refresh = updateable & known & ~anomalous
        np.maximum(self._reference, current, out=self._reference, where=refresh)

        # A clean first sample can seed and use its own tile immediately;
        # anomalously dark tiles remain unknown and cannot authorize votes.
        paper_grid = (known | initialize) & ~anomalous
        paper_exposed = (
            True
            if paper_grid.all()
            else cv2.resize(
                paper_grid.astype(np.uint8),
                (width, height),
                interpolation=cv2.INTER_NEAREST,
            )
            > 0
        )
        visible = None
        if np.any(block):
            visible = (
                cv2.resize(
                    (block == 0).astype(np.uint8),
                    (width, height),
                    interpolation=cv2.INTER_NEAREST,
                )
                > 0
            )
        return ExposureAssessment(
            visible=visible,
            paper_exposed=paper_exposed,
        )
