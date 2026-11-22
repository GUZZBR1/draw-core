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
# Um objeto claro ainda pode ter a luma e o croma do papel. Compare a
# variação relativa local com a textura de papel aprendida por tile.
_TEXTURE_CHANGE = 0.015
_TEXTURE_MIN_PAPER_FRACTION = 0.6
# Fração de tinta lida pelo modelo num tile cuja referência foi
# formada em papel: marca nova sobre papel é oclusão suspeita, não
# textura aprendida.
_TEXTURE_NEW_INK_FRACTION = 0.01
_TEXTURE_NEW_INK_MAX_FRACTION = 0.18
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
_GLOBAL_SHIFT_MIN_RATIO = 0.25
_GLOBAL_SHIFT_MAX_RATIO = 4.0
# Bloco mínimo que veta adições: componente conexo de tiles anômalos
# com os dois lados >= 3 e área >= 9 (um traço fino não é oclusor).
_BLOCK_MIN_TILE_SIDE = 3
_BLOCK_MIN_TILE_AREA = 9
# Piso de luma no denominador do croma: pixels quase pretos produzem
# croma infinito; 20 é o valor embutido no teto da referência.
_CHROMA_LUMA_FLOOR = 20.0
# O croma medido é canal / grayscale (máx. 255/20), não canal /
# canal-máximo: iluminação colorida legítima passa de 2 — papel
# neutro sob luz azul marca ~2.5 no canal B. Um teto de 2 na
# referência deixava um resíduo >= _CHROMA_CHANGE e a página
# inteira ficava vetada enquanto a luz durasse (Devin Review do
# PR #144).
_CHROMA_REFERENCE_MAX = 255.0 / _CHROMA_LUMA_FLOOR
# Recuperação por preenchimento: um bloco escuro que o modelo lê como
# tinta, passada após passada e com a mão fora do tile, é conteúdo da
# página — não oclusor. Até _FILL_RECOVERY_PASSES seguidas o veto de
# adição vale como sempre; depois ele cai só para o voto de adição.
# A remoção segue exigindo papel exposto, que o preenchimento nunca
# produz: o tile continua anômalo para o segundo veredito.
_FILL_INK_PIXEL_THRESHOLD = 0.7
# Fração do tile lendo tinta forte que conta como fill: metade do
# tile — uma faixa fina de tinta falsa na borda de sombra não alcança.
_FILL_INK_TILE_SUPPORT = 0.5
_FILL_RECOVERY_PASSES = 4
# Piso absoluto de papel exposto: a absorção de deslocamento global
# segue a iluminação, mas uma página mediana abaixo deste nível não
# pode ser papel — a lente tapada/luz apagada é um oclusor, não um
# novo ponto de referência. Sem o piso, um frame escuro inteiro era
# adotado como baseline e a tinta confirmada era apagada.
_MIN_PAPER_LUMA = 24.0
# Papel que acabou de sair de anomalia fica em recuperação por este
# número de passadas: a evidência voltou mas ainda não estabilizou —
# uma anomalia persistente nunca entra em recuperação (espelha o hold
# de `paper_ok` do guarda anterior, agora por tile).
_RECOVERY_HOLD_PASSES = 4
# Teto do tempo morto da espera da trabalhadora por recuperação
# pendente (streak de preenchimento ou hold de recuperação): cobre os
# dois orçamentos — hoje coincidem em 4, mas pertencem a mecanismos
# diferentes. O teto não corre sobre o pendente global direto: a
# trabalhadora soma a idade do item pendente mais velho
# (max_recovery_age) como carência, então o limite real é o teto
# mais a idade dele — e como idade pendente é sempre menor que este
# valor, a espera total nunca passa de 2*_RECOVERY_WAIT_PASSES - 1.
_RECOVERY_WAIT_PASSES = max(_FILL_RECOVERY_PASSES, _RECOVERY_HOLD_PASSES)


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
        self._texture_reference = None
        self._ink_streak = None
        self._fill_adopted = None
        self._last_fill_adoption = False
        self._recovering = None
        self._was_anomalous = None

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

    @property
    def recovering(self):
        """Algum tile saiu de anomalia e ainda está no hold de recuperação.

        Espelha o `recovering_px` do guarda anterior: dispara quando a
        evidência fotométrica VOLTA (sombra que sai, mão que levanta),
        não enquanto a anomalia persiste — uma borda escura permanente
        nunca entra em recuperação e deixa a trabalhadora descansar.
        """
        return self._recovering is not None and bool(np.any(self._recovering))

    @property
    def recovery_pending(self):
        """Recuperação com trabalho pendente (streak ou hold ativo)."""
        return self.pending_fill_recovery or self.recovering

    @property
    def max_recovery_age(self):
        """Idade do item pendente mais velho, em passadas; 0 sem pendente.

        `recovery_pending` é global: um streak que nasce na passada em
        que outro morre emenda os dois numa espera só, e a trabalhadora
        cobrava do preenchimento novo as passadas gastas no que morreu
        — a contagem fechava antes da leitura que o adota (Devin Review
        do PR #144). A idade devolve a régua por item: o maior streak
        ainda contando (o próprio valor) ou o hold decorrido há mais
        tempo (_RECOVERY_HOLD_PASSES - restante). Todo item pendente é
        mais novo que _RECOVERY_WAIT_PASSES, então a carência que a
        trabalhadora soma ao teto da espera é limitada por construção.
        """
        age = 0
        if self._ink_streak is not None:
            streaks = self._ink_streak[
                (self._ink_streak > 0) & (self._ink_streak < _FILL_RECOVERY_PASSES)
            ]
            if streaks.size:
                age = int(streaks.max())
        if self._recovering is not None:
            holds = self._recovering[self._recovering > 0]
            if holds.size:
                age = max(age, _RECOVERY_HOLD_PASSES - int(holds.min()))
        return age

    def _darkened(self, known, current):
        """(darkened, expected): luma por tile contra a referência."""
        expected = np.where(known, self._reference, self._page_reference or 0.0)
        drop = np.maximum(_MIN_DARKENING, expected * _DARKENING_FRACTION)
        return current < expected - drop, expected

    def _color_anomaly(self, known, chroma, shape):
        """Tiles com croma longe da referência; zeros sem evidência."""
        color_anomaly = np.zeros(shape, dtype=bool)
        if chroma is None or self._page_color_reference is None:
            return color_anomaly
        expected_color = (
            np.where(
                known[..., None],
                self._color_reference,
                self._page_color_reference,
            )
            if self._color_reference is not None
            else np.broadcast_to(self._page_color_reference, chroma.shape)
        )
        return np.linalg.norm(chroma - expected_color, axis=2) > _CHROMA_CHANGE

    def observe(
        self,
        image,
        visible=None,
        ink_prob=None,
        ink_support_threshold=None,
        confirmed_ink=None,
    ):
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
        permanente, como antes. `ink_support_threshold` é o nível de
        prob em que um pixel conta como tinta forte; o chamador passa o
        `vote_hit` da sua configuração para que a guarda some exatamente
        a evidência que a camada de voto consegue confirmar — com o
        piso fixo de 0,7 um preenchimento sustentado em [vote_hit, 0,7)
        confirmava no voto mas nunca chegava a votar (Devin Review do
        PR #144). None mantém o piso histórico.
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
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
        else:
            current = reduced.astype(np.float32)
            color = None
            gray = image.astype(np.float32)
        texture_weights = np.ones((height, width), dtype=np.float32)
        support_level = (
            _FILL_INK_PIXEL_THRESHOLD
            if ink_support_threshold is None
            else float(ink_support_threshold)
        )
        if ink_prob is not None:
            ink_prob = np.asarray(ink_prob, dtype=np.float32)
            if ink_prob.shape == (height, width):
                texture_weights = (
                    np.isfinite(ink_prob) & (ink_prob < support_level)
                ).astype(np.float32)
            else:
                texture_weights.fill(0.0)
        paper_fraction = cv2.resize(texture_weights, size, interpolation=cv2.INTER_AREA)
        ink_fraction = 1.0 - paper_fraction
        sampled_mean = cv2.resize(
            gray * texture_weights, size, interpolation=cv2.INTER_AREA
        )
        sampled_mean_square = cv2.resize(
            gray * gray * texture_weights, size, interpolation=cv2.INTER_AREA
        )
        texture_mean = np.divide(
            sampled_mean,
            paper_fraction,
            out=np.zeros_like(sampled_mean),
            where=paper_fraction > 0.0,
        )
        texture_mean_square = np.divide(
            sampled_mean_square,
            paper_fraction,
            out=np.zeros_like(sampled_mean_square),
            where=paper_fraction > 0.0,
        )
        texture_valid = paper_fraction >= _TEXTURE_MIN_PAPER_FRACTION
        texture = np.sqrt(
            np.maximum(texture_mean_square - texture_mean * texture_mean, 0.0)
        ) / np.maximum(texture_mean, _CHROMA_LUMA_FLOOR)

        if visible is None:
            updateable = np.ones(current.shape, dtype=bool)
        else:
            visible = np.asarray(visible, dtype=bool)
            if visible.shape != (height, width):
                # Máscara em geometria errada é bug do chamador: sem
                # veredito confiável devolve None (remoção congela no
                # acumulador) em vez de congelar a referência e ainda
                # varrer os streaks/adotados de preenchimento.
                return None
            if np.all(visible):
                updateable = np.ones(current.shape, dtype=bool)
            else:
                fraction = cv2.resize(
                    visible.astype(np.uint8), size, interpolation=cv2.INTER_AREA
                )
                updateable = fraction >= _VISIBLE_TILE_FRACTION

        if confirmed_ink is not None:
            confirmed_ink = np.asarray(confirmed_ink, dtype=bool)
            if confirmed_ink.shape != (height, width):
                return None

        if self._reference is None or self._reference.shape != current.shape:
            self._reference = np.full(current.shape, np.nan, dtype=np.float32)
            self._color_reference = (
                None
                if color is None
                else np.full((*current.shape, 3), np.nan, dtype=np.float32)
            )
            self._page_reference = None
            self._page_color_reference = None
            self._texture_reference = np.full(current.shape, np.nan, dtype=np.float32)
            self._texture_learned_clean = np.zeros(current.shape, dtype=bool)
            self._ink_streak = np.zeros(current.shape, dtype=np.uint8)
            self._fill_adopted = np.zeros(current.shape, dtype=bool)
            self._recovering = np.zeros(current.shape, dtype=np.uint8)
            self._was_anomalous = np.zeros(current.shape, dtype=bool)

        known = np.isfinite(self._reference)
        candidates = current[updateable]
        # Invariante explícita: sem tiles à vista não há estimativa —
        # o deslocamento global só roda com shifted >= 4, o que já
        # implica candidates não-vazio, mas o nome fica definido sempre.
        page_reference = 0.0
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
        darkened, expected = self._darkened(known, current)
        chroma = None
        if color is not None:
            chroma = color / np.maximum(current[..., None], _CHROMA_LUMA_FLOOR)
            color_tiles = updateable & ~darkened
            if np.any(color_tiles):
                self._page_color_reference = np.median(
                    chroma[color_tiles], axis=0
                ).astype(np.float32)
        color_anomaly = self._color_anomaly(known, chroma, current.shape)

        texture_known = np.isfinite(self._texture_reference)
        neighbors = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                neighbor = np.roll(self._texture_reference, (dy, dx), axis=(0, 1))
                if dy < 0:
                    neighbor[-1, :] = np.nan
                elif dy > 0:
                    neighbor[0, :] = np.nan
                if dx < 0:
                    neighbor[:, -1] = np.nan
                elif dx > 0:
                    neighbor[:, 0] = np.nan
                neighbors.append(neighbor)
        neighbor_values = np.stack(neighbors)
        neighbor_valid = np.isfinite(neighbor_values)
        neighbor_count = neighbor_valid.sum(axis=0)
        ordered_neighbors = np.sort(
            np.where(neighbor_valid, neighbor_values, np.inf), axis=0
        )
        lower = np.take_along_axis(
            ordered_neighbors,
            np.maximum((neighbor_count - 1) // 2, 0)[None],
            axis=0,
        )[0]
        upper = np.take_along_axis(
            ordered_neighbors, (neighbor_count // 2)[None], axis=0
        )[0]
        neighbor_reference = np.where(neighbor_count > 0, (lower + upper) * 0.5, 0.0)
        texture_reference = np.where(
            texture_known, self._texture_reference, neighbor_reference
        )
        texture_comparable = texture_known | (neighbor_count >= 2)
        texture_mismatch = texture_comparable & (
            np.abs(texture - texture_reference)
            > np.maximum(_TEXTURE_CHANGE, texture_reference * 0.5)
        )
        local_texture_match = (neighbor_count >= 2) & (
            np.abs(texture - neighbor_reference)
            <= np.maximum(_TEXTURE_CHANGE, neighbor_reference * 0.5)
        )
        # Tinta nova sobre tile aprendida limpa: as marcas de um
        # oclusor podem ser lidas como tinta e sair da amostra
        # ponderada — a régua passava com textura de papel e a falta
        # apagava o traço sob ela. O veto pede referência formada em
        # papel: tile que sempre teve tinta não é "novo". Cobertura
        # insuficiente barra só o aprendizado (texture_valid ali),
        # não o veto por pixel — a metade apagada de um patch denso
        # precisa poder provar papel. A contagem usa TODA a tinta que
        # o modelo lê: confirmar a marca por voto não a torna papel —
        # se a leitura parasse em "não confirmada", a régua marcada
        # confirmaria os próprios ticks em ~3 passadas e o veto
        # evaporaria sobre o traço que ela cobre (Devin Review do
        # PR #144).
        new_ink = (
            texture_known
            & self._texture_learned_clean
            & (ink_fraction >= _TEXTURE_NEW_INK_FRACTION)
            & (ink_fraction <= _TEXTURE_NEW_INK_MAX_FRACTION)
        )
        texture_anomaly = texture_mismatch | new_ink

        anomalous = darkened | color_anomaly
        updateable_px = int(np.count_nonzero(updateable))
        shifted = int(np.count_nonzero(anomalous & updateable))
        if (
            shifted >= _GLOBAL_SHIFT_MIN_TILES
            and shifted >= (_GLOBAL_SHIFT_FRACTION * updateable_px)
            and page_reference >= _MIN_PAPER_LUMA
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
                # expected ⊆ self._reference para tiles conhecidos:
                # lê a referência direto, sem recomputar o grid.
                ratio = float(np.median(current[measured] / self._reference[measured]))
            elif self._page_reference:
                ratio = page_reference / self._page_reference
            else:
                ratio = 1.0
            ratio = float(
                np.clip(ratio, _GLOBAL_SHIFT_MIN_RATIO, _GLOBAL_SHIFT_MAX_RATIO)
            )
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
                        self._color_reference[known] + color_shift,
                        0.0,
                        _CHROMA_REFERENCE_MAX,
                    )
                self._page_color_reference = np.median(
                    chroma[updateable], axis=0
                ).astype(np.float32)

            # Absorve apenas o componente comum. Um tile muito mais
            # escuro/colorido que o resto continua anômalo e não prova
            # papel exposto — inclusive sob a sombra durante a mudança.
            darkened, expected = self._darkened(known, current)
            color_anomaly = self._color_anomaly(known, chroma, current.shape)
            anomalous = darkened | color_anomaly

            # A lâmpada direcional apaga e a página nivela no brilho
            # do lado escuro: a razão mediana escala junto o gradiente
            # antigo e a faixa antes mais clara continuava "escura"
            # para sempre — área residual pequena demais para reabrir
            # a absorção e excluída do refresh, que só corrige tiles
            # sem anomalia. O tile à vista que já combina com o nível
            # NOVO da página não é oclusor: reancora a referência no
            # medido e limpa a anomalia. Um oclusor real segue abaixo
            # do nível da página e permanece vetado, assim como o tile
            # marcado só pelo croma (Devin Review do PR #144).
            page_drop = max(_MIN_DARKENING, page_reference * _DARKENING_FRACTION)
            # O veto de textura no rebaseline segura só quem SEGUE
            # anômalo agora: a régua parada não vira papel com a
            # mudança de luz, mas o tile cuja textura já voltou ao
            # normal precisa reancorar — senão a trava ficava
            # permanente depois de qualquer nivelamento (Devin
            # Review do PR #144).
            flattened = (
                updateable
                & (anomalous | texture_anomaly)
                & (~texture_anomaly | local_texture_match)
                & ~new_ink
                & ~color_anomaly
                & (current >= page_reference - page_drop)
            )
            if np.any(flattened):
                self._reference[flattened] = current[flattened]
                if self._color_reference is not None:
                    self._color_reference[flattened] = chroma[flattened]
                # A tile já validado como parte do novo nível global da
                # folha também atualiza sua textura: a iluminação anterior
                # podia criar variação local que some quando a luz nivela.
                self._texture_reference[flattened] = texture[flattened]
                texture_anomaly[flattened] = False
                anomalous &= ~flattened

        # Recuperação por preenchimento: o streak conta as passadas
        # seguidas em que o tile anômalo, à vista, é lido como tinta
        # pelo modelo. A mão sobre o tile (updateable False) não
        # deixa a contagem andar — a adoção só acontece com a mão
        # fora do caminho ou quando a cena não tem máscara alguma.
        supported = np.zeros(current.shape, dtype=bool)
        pixel_support = None
        if ink_prob is not None:
            ink_prob = np.asarray(ink_prob, dtype=np.float32)
            if ink_prob.shape == (height, width):
                pixel_support = ink_prob >= support_level
        if pixel_support is not None and np.any(anomalous):
            support_fraction = cv2.resize(
                pixel_support.astype(np.float32), size, interpolation=cv2.INTER_AREA
            )
            support_mean = cv2.resize(ink_prob, size, interpolation=cv2.INTER_AREA)
            # A adoção exige evidência DENSA no nível que o voto
            # configurado atua: metade do tile lendo tinta forte, ou a
            # média do tile no nível do hit. Um bloco preenchido
            # sustentado adota mesmo sem todos os pixels no hit; já a
            # faixa fina de tinta falsa na borda de uma sombra (~15-30%
            # do tile, média ~0,15) nunca semeia — antes 15% de pixels
            # fortes bastava para adotar a sombra como fill
            # (Devin Review do PR #144).
            # A média do tile no nível do hit conta evidência densa
            # sustentada que o voto configurado confirmaria (um bloco
            # preenchido a 0,68 sob Sketch) mesmo sem todos os pixels
            # no hit (Devin Review do PR #144).
            tile_support = (
                anomalous
                & updateable
                & (
                    (
                        (support_fraction >= _FILL_INK_TILE_SUPPORT)
                        & (support_mean >= _FILL_INK_TILE_MEAN)
                    )
                    | (support_mean >= support_level)
                )
            )
            # Só um suporte 2-D pode semear a recuperação: o veto de
            # adição só existe para manchas que cobrem >= 2 tiles em
            # ambas as dimensões, então uma faixa de uma linha de tile —
            # a borda de sombra que o modelo lê como tinta — não tinha
            # nada a recuperar e não pode ser adotada como fill
            # (Devin Review do PR #144).
            if np.any(tile_support):
                count, labels = cv2.connectedComponents(
                    tile_support.astype(np.uint8), connectivity=8
                )
                for index in range(1, count):
                    rows, cols = np.where(labels == index)
                    if (
                        rows.max() - rows.min() + 1 >= 2
                        and cols.max() - cols.min() + 1 >= 2
                    ):
                        supported |= labels == index
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
                if (
                    block_width >= _BLOCK_MIN_TILE_SIDE
                    and block_height >= _BLOCK_MIN_TILE_SIDE
                    and area >= _BLOCK_MIN_TILE_AREA
                ):
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
        texture_initialize = (
            updateable & texture_valid & ~texture_known & ~anomalous & ~texture_anomaly
        )
        self._texture_reference[texture_initialize] = texture[texture_initialize]
        texture_refresh = (
            updateable & texture_valid & texture_known & ~anomalous & ~texture_anomaly
        )
        self._texture_reference[texture_refresh] = texture[texture_refresh]
        # Referência formada com fundo visível bastante era papel:
        # tinta nova sobre ela é anomalia, não "sempre foi assim".
        self._texture_learned_clean[texture_initialize | texture_refresh] = True

        # A clean first sample can seed and use its own tile immediately;
        # anomalously dark tiles remain unknown and cannot authorize votes.
        # initialize ⊆ updateable, então a grade é "conhecido ou à vista,
        # sem anomalia".
        paper_grid = (known | updateable) & ~anomalous & ~texture_anomaly
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
        if pixel_support is not None or confirmed_ink is not None:
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
            dark_ink = np.zeros((height, width), dtype=bool)
            if pixel_support is not None:
                dark_ink |= pixel_support & (gray < expected_pixels - pixel_drop)
            if confirmed_ink is not None:
                # A confirmed stroke remains non-paper if the model
                # misses it in this pass. Cleared pixels return to the
                # paper luminance and can vote for removal independently.
                dark_ink |= confirmed_ink & (gray < expected_pixels - pixel_drop)
            if np.any(dark_ink):
                if isinstance(paper_exposed, (bool, np.bool_)):
                    paper_exposed = np.full((height, width), paper_exposed, dtype=bool)
                paper_exposed[dark_ink] = False
        unblocked = None
        if np.any(block):
            unblocked = (
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
            # Borda de preenchimento parcial: a média de prob do tile
            # de borda dilui com os pixels de papel e fica abaixo do
            # piso — o miolo adota e a borda, que é o mesmo traço,
            # ficava vetada para sempre. O piso continua valendo para
            # SEMEAR a adoção; depois dela o veto cai para o
            # componente conexo de tinta escura forte ancorado no
            # adotado — que atravessa as tiles de borda vizinhas. A
            # faixa fina isolada dentro de uma sombra não tem âncora
            # adotada e segue bloqueada (Devin Review do PR #144).
            if np.any(recovered) and np.any(dark_ink):
                # A ponte só atravessa pixels realmente à vista:
                # a mão cobrindo o fosso entre o preenchimento e
                # uma borda de sombra quebrava a conexão pelo mapa
                # cru e a borda votava junto — tinta fantasma
                # (Devin Review do PR #144).
                connectable = dark_ink if visible is None else (dark_ink & visible)
                _count, fill_labels = cv2.connectedComponents(
                    connectable.astype(np.uint8), connectivity=8
                )
                reached = np.unique(fill_labels[recovered])
                reached = reached[reached != 0]
                if reached.size:
                    recovered = recovered | np.isin(fill_labels, reached)
            if np.any(recovered):
                if unblocked is None:
                    unblocked = np.ones((height, width), dtype=bool)
                unblocked[recovered] = True
        # Hold de recuperação: decai um por passada, zera onde a
        # anomalia voltou, e o tile que saiu de anomalia recarrega o
        # hold (a evidência voltando fica aberta _RECOVERY_HOLD_PASSES).
        np.subtract(
            self._recovering, 1, out=self._recovering, where=self._recovering > 0
        )
        self._recovering[anomalous] = 0
        self._recovering[self._was_anomalous & ~anomalous] = _RECOVERY_HOLD_PASSES
        self._was_anomalous = anomalous.copy()
        return ExposureAssessment(
            visible=unblocked,
            paper_exposed=paper_exposed,
        )
