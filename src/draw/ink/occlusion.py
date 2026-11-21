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
_TEXTURE_CHANGE = 0.015
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
_FILL_INK_PIXEL_THRESHOLD = 0.7
_FILL_INK_TILE_SUPPORT = 0.15
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
        self._fill_adopted = None
        self._last_fill_adoption = False
        self._texture_reference = None
        self._page_texture_reference = None

    @property
    def pending_fill_recovery(self):
        """Streak de evidência de tinta contando num bloco (ainda não
        adotado): a recuperação por preenchimento tem trabalho pendente
        e precisa de passadas limpas chegando — a porta de descanso não
        pode ler essas passadas como quietude, senão a trabalhadora
        dorme no meio da contagem e o preenchimento nunca vota (Devin
        Review do PR #144)."""
        return self._ink_streak is not None and bool(
            np.any((self._ink_streak > 0) & (self._ink_streak < _FILL_RECOVERY_PASSES))
        )

    @property
    def last_fill_adoption(self):
        """True apenas na passada em que um bloco cruzou o limiar de
        adoção: é uma borda, não um estado — a trabalhadora rearma a
        janela de confirmação uma vez por preenchimento adotado, sem
        segurar o orçamento enquanto o bloco seguir adotado."""
        return self._last_fill_adoption

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
        # Borda de adoção dura uma observação: qualquer retorno —
        # precoce ou completo — apaga a do ciclo anterior antes de
        # recomputar, senão uma passada sem imagem válida a repetia
        # e a trabalhadora rearmava a janela para sempre.
        self._last_fill_adoption = False
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
            self._fill_adopted = np.zeros(current.shape, dtype=bool)
            self._last_fill_adoption = False

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
            # global, não um oclusor. A razão medida nos tiles que
            # mudaram juntos escala TODA a referência conhecida —
            # inclusive a dos tiles escondidos pela mão: ela ficava
            # clara demais e, ao reaparecer no nível novo, virava um
            # bloco escuro permanente. E a referência de página cede
            # ao percentil medido, em vez de ficar presa no máximo
            # histórico (Devin Review do PR #144).
            measured = anomalous & updateable & known
            if np.any(measured):
                ratio = float(np.median(current[measured] / expected[measured]))
            elif self._page_reference:
                ratio = page_reference / self._page_reference
            else:
                ratio = 1.0
            ratio = float(np.clip(ratio, 0.25, 4.0))
            self._reference[known] *= np.float32(ratio)
            self._page_reference = page_reference
            if self._color_reference is not None:
                # Aplica o deslocamento de croma comum; usar o valor
                # bruto por tile ensinaria junto uma sombra colorida.
                color_known = known & np.all(np.isfinite(self._color_reference), axis=2)
                color_tiles = updateable & color_known
                if np.any(color_tiles):
                    color_shift = np.median(
                        chroma[color_tiles] - self._color_reference[color_tiles], axis=0
                    )
                    self._color_reference[known] = np.clip(
                        self._color_reference[known] + color_shift, 0.0, 2.0
                    )
                self._page_color_reference = np.median(
                    chroma[updateable], axis=0
                ).astype(np.float32)

            # Absorve apenas o componente comum. Um tile muito mais
            # escuro/colorido que o resto continua anômalo e não prova
            # papel exposto — inclusive sob a sombra durante a mudança.
            expected = np.where(known, self._reference, self._page_reference)
            drop = np.maximum(_MIN_DARKENING, expected * _DARKENING_FRACTION)
            darkened = current < expected - drop
            color_anomaly = np.zeros(current.shape, dtype=bool)
            if color is not None and self._page_color_reference is not None:
                expected_color = np.where(
                    known[..., None],
                    self._color_reference,
                    self._page_color_reference,
                )
                color_anomaly = (
                    np.linalg.norm(chroma - expected_color, axis=2) > _CHROMA_CHANGE
                )
            anomalous = darkened | color_anomaly

        # Recuperação por preenchimento: o streak conta as passadas
        # seguidas em que o tile anômalo, à vista, é lido como tinta
        # pelo modelo. A mão sobre o tile (updateable False) não
        # deixa a contagem andar — a adoção só acontece com a mão
        # fora do caminho ou quando a cena não tem máscara alguma.
        supported = np.zeros(current.shape, dtype=bool)
        pixel_support = None
        if ink_prob is not None and np.any(anomalous):
            ink_prob = np.asarray(ink_prob, dtype=np.float32)
            if ink_prob.shape == (height, width):
                pixel_support = ink_prob >= _FILL_INK_PIXEL_THRESHOLD
                support_fraction = cv2.resize(
                    pixel_support.astype(np.float32), size, interpolation=cv2.INTER_AREA
                )
                supported = (
                    anomalous
                    & updateable
                    & (support_fraction >= _FILL_INK_TILE_SUPPORT)
                )
        self._ink_streak[supported] = np.minimum(
            self._ink_streak[supported].astype(np.uint16) + 1, 255
        ).astype(np.uint8)
        self._ink_streak[~supported] = 0
        # Quem perdeu o suporte desaprende a adoção: se a evidência
        # voltar e o tile readotar, a borda dispara de novo — a
        # trabalhadora rearma a janela de confirmação por borda, não
        # por estado retido (Devin Review do PR #144).
        self._fill_adopted &= self._ink_streak > 0
        adopted = self._ink_streak >= _FILL_RECOVERY_PASSES
        self._last_fill_adoption = bool(np.any(adopted & ~self._fill_adopted))
        self._fill_adopted |= adopted

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
        if pixel_support is not None:
            pixel_luma = (
                cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
                if image.ndim == 3
                else image.astype(np.float32)
            )
            expected_pixels = cv2.resize(
                expected, (width, height), interpolation=cv2.INTER_NEAREST
            )
            pixel_drop = np.maximum(
                _MIN_DARKENING, expected_pixels * _DARKENING_FRACTION
            )
            # A tile can look like paper on average even when its edge
            # contains a solid dark fill. Strong ink pixels over dark
            # camera pixels never prove exposed paper, including tiles
            # that are only partially covered by the fill.
            dark_ink = pixel_support & (pixel_luma < expected_pixels - pixel_drop)
            if np.any(dark_ink):
                if isinstance(paper_exposed, (bool, np.bool_)):
                    paper_exposed = np.full((height, width), paper_exposed, dtype=bool)
                paper_exposed[dark_ink] = False
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
        if pixel_support is not None and np.any(adopted):
            adopted_pixels = (
                cv2.resize(
                    adopted.astype(np.uint8),
                    (width, height),
                    interpolation=cv2.INTER_NEAREST,
                )
                > 0
            )
            recovered = adopted_pixels & pixel_support
            if np.any(recovered):
                if visible is None:
                    visible = np.ones((height, width), dtype=bool)
                visible[recovered] = True
        return ExposureAssessment(
            visible=visible,
            paper_exposed=paper_exposed,
        )
