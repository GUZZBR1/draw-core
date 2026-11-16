"""Acumulador de tinta em camadas: voto entre passadas."""

from collections import deque

import cv2
import numpy as np

from . import identity, registration, votes


class LayeredInkAccumulator:
    """Tinta de uma geracao em duas camadas: provisoria e confirmada.

    Cada passada entrega o mapa de probabilidade do modelo. A
    camada provisoria e o que as passadas da janela viram acima do
    limiar e ainda nao confirmou: ela existe para a tela mostrar a
    tinta nova na primeira passada, e so para a tela. A camada
    confirmada e o canvas: um pixel so entra nela pelas regras de
    voto acima com a porta de fronteira (evidencia sub-limiar nao
    expande a borda da tinta ja confirmada), e dela nao sai
    dentro da geracao.

    Pixel provisorio que sai da janela sem confirmar e retratado:
    some da camada provisoria e entra na contagem de retratados.
    E essa contagem que mede o risco declarado da publicacao
    especulativa, o page-clean pegar mobiliario: a regua de replay
    le quanta tinta provisoria some depois.

    So a trabalhadora de tinta toca nesta classe.
    """

    def __init__(self, threshold=0.7):
        self.threshold = float(threshold)
        self.reset()

    def reset(self):
        self._window = deque(maxlen=votes._INK_VOTE_WINDOW)
        self._removal_streak = None
        self._confirmed = None
        self._provisional = None
        self._provisional_ever = None
        self._retracted_ever = None
        self._low_overlap_streak = 0
        self._turn_fired = False
        self._score_buf = None
        self._hits_buf = None
        self._seen_buf = None
        # Regra E3 (DRAW_INK_VOTE_E3): o modo da geracao e decidido
        # na primeira passada apos o reset (None = nao decidido) e
        # todo o estado da regra zera junto com o da geracao — uma
        # geracao nova nao herda nucleo, uniao velha nem trilhas.
        self._e3_active = None
        # Regra E5-S (DRAW_INK_VOTE_E4): idem — decidida na
        # primeira passada da geracao, com precedencia sobre a
        # E3 quando as duas flags estao ligadas (ver a constante
        # votes._INK_VOTE_E4_ENV).
        self._e4_active = None
        # Corte de latencia (DRAW_INK_VOTE_FAST): decidido junto
        # com o modo E3, na mesma primeira passada da geracao.
        self._fast_active = None
        self._reset_e3_state()
        self._reset_e4_state()

    def _reset_e3_state(self):
        self._e3_passes = 0
        self._e3_phase1_maps = []
        self._e3_old_union = None
        self._e3_region_big = None
        self._e3_region_small = None
        self._e3_side_big = votes._E3SideVote(
            votes._INK_VOTE_E3_BIG_WINDOW, votes._INK_VOTE_E3_BIG_SCORE, self.threshold
        )
        self._e3_side_small = votes._E3SideVote(
            votes._INK_VOTE_E3_SMALL_WINDOW,
            votes._INK_VOTE_E3_SMALL_SCORE,
            self.threshold,
        )
        self._e3_tracks_big = 0
        self._e3_tracks_small = 0

    def _e3_step(self, evidence):
        """Uma passada da regra E3; devolve a mascara confirmada.

        Porto fiel da bancada vencedora da F89 (CommitE3): fase 1
        confirma o nucleo de consenso espacial ao fechar a 3a
        passada; fase 2 classifica cada componente conexo novo
        contra a uniao velha dilatada e as regioes ja abertas
        (fracoes medidas contra os instantaneos do inicio da
        passada, como na bancada) e alimenta as trilhas por
        tamanho com a evidencia mascarada pela regiao.
        """
        shape = evidence.shape
        if self._e3_old_union is None or self._e3_old_union.shape != shape:
            self._e3_old_union = np.zeros(shape, dtype=bool)
            self._e3_region_big = np.zeros(shape, dtype=bool)
            self._e3_region_small = np.zeros(shape, dtype=bool)
            self._e3_phase1_maps = []
            self._e3_passes = 0
            self._e3_side_big.reset()
            self._e3_side_small.reset()
            self._e3_tracks_big = 0
            self._e3_tracks_small = 0
        ink = evidence > self.threshold
        confirmed = self._confirmed > 0
        if self._e3_passes < votes._INK_VOTE_E3_PHASE1_PASSES:
            self._e3_phase1_maps.append(evidence.copy())
            self._e3_old_union |= ink
            if self._e3_passes == votes._INK_VOTE_E3_PHASE1_PASSES - 1:
                confirmed = confirmed | votes._e3_phase1_core(
                    self._e3_phase1_maps, self.threshold
                )
            self._e3_passes += 1
            return confirmed
        old_dilated = (
            cv2.dilate(
                self._e3_old_union.astype(np.uint8), votes._INK_VOTE_E3_DILATE_KERNEL
            )
            > 0
        )
        regions = self._e3_region_big | self._e3_region_small
        regions_dilated = (
            cv2.dilate(regions.astype(np.uint8), votes._INK_VOTE_E3_DILATE_KERNEL) > 0
        )
        count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
            ink.astype(np.uint8), 8
        )
        for index in range(1, count):
            area = int(stats[index, cv2.CC_STAT_AREA])
            if area < votes._INK_VOTE_E3_MIN_COMPONENT_PX:
                continue
            component = labels == index
            frac_old = float(np.count_nonzero(component & old_dilated) / area)
            frac_region = float(np.count_nonzero(component & regions_dilated) / area)
            if frac_old >= 0.5:
                self._e3_old_union |= component
            elif frac_region < 0.5:
                dilated = (
                    cv2.dilate(
                        component.astype(np.uint8), votes._INK_VOTE_E3_REGION_KERNEL
                    )
                    > 0
                )
                if area >= votes._INK_VOTE_E3_BIG_COMPONENT_PX:
                    self._e3_region_big |= dilated
                    self._e3_tracks_big += 1
                else:
                    self._e3_region_small |= dilated
                    self._e3_tracks_small += 1
        if np.any(self._e3_region_big):
            masked = np.where(self._e3_region_big, evidence, 0.0).astype(np.float32)
            confirmed = confirmed | self._e3_side_big.add(masked)
        if np.any(self._e3_region_small):
            masked = np.where(self._e3_region_small, evidence, 0.0).astype(np.float32)
            confirmed = confirmed | self._e3_side_small.add(masked)
        self._e3_passes += 1
        return confirmed

    def _reset_e4_state(self):
        self._e4_passes = 0
        self._e4_phase1_maps = []
        self._e4_opening = None
        self._e4_opening_prob = None
        self._e4_region_big = None
        self._e4_region_small = None
        self._e4_region_slow = None
        self._e4_region_thin = None
        self._e4_side_big = votes._E3SideVote(
            votes._INK_VOTE_E4_BIG_WINDOW, votes._INK_VOTE_E4_BIG_SCORE, self.threshold
        )
        self._e4_side_small = votes._E3SideVote(
            votes._INK_VOTE_E4_SMALL_WINDOW,
            votes._INK_VOTE_E4_SMALL_SCORE,
            self.threshold,
        )
        self._e4_side_slow = votes._E3SideVote(
            votes._INK_VOTE_E4_SLOW_WINDOW,
            votes._INK_VOTE_E4_SLOW_SCORE,
            self.threshold,
        )
        self._e4_side_thin = votes._E4ThinSideVote(
            votes._INK_VOTE_E4_THIN_WINDOW,
            votes._INK_VOTE_E4_THIN_SCORE,
            self.threshold,
        )
        self._e4_tracks_big = 0
        self._e4_tracks_small = 0
        self._e4_tracks_slow = 0
        self._e4_tracks_thin = 0
        self._e4_tracks_sub = 0

    def _e4_open_track(self, component, area, width, height, far_mask, sub=False):
        """Abre a trilha de um componente (ou sub-componente) novo.

        Classificacao do prototipo da F107 (E5._open): a banda de
        distancia ao confirmado decide lenta x longe; longe, a
        forma de linha decide fina x por-tamanho. Sub-componente
        de nascimento abre com regiao r3 (a regiao r6 colaria a
        sub-trilha no conteudo coberto que a gerou).
        """
        frac_far = float(np.count_nonzero(component & far_mask) / area)
        dil3 = (
            cv2.dilate(component.astype(np.uint8), votes._INK_VOTE_E3_DILATE_KERNEL) > 0
        )
        if frac_far < 0.5:
            self._e4_region_slow |= dil3
            self._e4_tracks_slow += 1
        elif (
            max(width, height) >= votes._INK_VOTE_E4_THIN_MIN_LENGTH
            and area <= votes._INK_VOTE_E4_THIN_MAX_AREA_RATIO * max(width, height)
        ):
            self._e4_region_thin |= dil3
            self._e4_tracks_thin += 1
        elif area >= votes._INK_VOTE_E4_BIG_COMPONENT_PX:
            self._e4_region_big |= (
                dil3
                if sub
                else cv2.dilate(
                    component.astype(np.uint8), votes._INK_VOTE_E3_REGION_KERNEL
                )
                > 0
            )
            self._e4_tracks_big += 1
        else:
            self._e4_region_small |= (
                dil3
                if sub
                else cv2.dilate(
                    component.astype(np.uint8), votes._INK_VOTE_E3_REGION_KERNEL
                )
                > 0
            )
            self._e4_tracks_small += 1
        if sub:
            self._e4_tracks_sub += 1

    def _e4_step(self, evidence):
        """Uma passada da regra E5-S; devolve a mascara confirmada.

        Porto fiel do prototipo validado da F107 (frente107/
        f107_proto.py, classe E5 com use_subdiv=True,
        use_weak=False, use_thinweak=False — so a subdivisao por
        nascimento sobre a E4j): fase 1 = nucleo da E3 com a
        abertura (mascara + mapa de prob da 1a passada) congelada
        como unico "velho"; fase 2 classifica cada componente
        contra abertura, confirmado e regioes (instantaneos do
        inicio da passada, como no prototipo) e alimenta as
        quatro trilhas com a evidencia mascarada pela regiao.
        """
        shape = evidence.shape
        if self._e4_opening is None or self._e4_opening.shape != shape:
            self._e4_opening = np.zeros(shape, dtype=bool)
            self._e4_opening_prob = np.zeros(shape, dtype=np.float32)
            self._e4_region_big = np.zeros(shape, dtype=bool)
            self._e4_region_small = np.zeros(shape, dtype=bool)
            self._e4_region_slow = np.zeros(shape, dtype=bool)
            self._e4_region_thin = np.zeros(shape, dtype=bool)
            self._e4_phase1_maps = []
            self._e4_passes = 0
            self._e4_side_big.reset()
            self._e4_side_small.reset()
            self._e4_side_slow.reset()
            self._e4_side_thin.reset()
            self._e4_tracks_big = 0
            self._e4_tracks_small = 0
            self._e4_tracks_slow = 0
            self._e4_tracks_thin = 0
            self._e4_tracks_sub = 0
        ink = evidence > self.threshold
        confirmed = self._confirmed > 0
        if self._e4_passes == 0:
            self._e4_opening = ink.copy()
            self._e4_opening_prob = evidence.copy()
        if self._e4_passes < votes._INK_VOTE_E3_PHASE1_PASSES:
            self._e4_phase1_maps.append(evidence.copy())
            if self._e4_passes == votes._INK_VOTE_E3_PHASE1_PASSES - 1:
                confirmed = confirmed | votes._e3_phase1_core(
                    self._e4_phase1_maps, self.threshold
                )
            self._e4_passes += 1
            return confirmed
        confirmed_d3 = (
            cv2.dilate(confirmed.astype(np.uint8), votes._INK_VOTE_E3_DILATE_KERNEL) > 0
        )
        confirmed_d8 = (
            cv2.dilate(confirmed.astype(np.uint8), votes._INK_VOTE_E4_FAR_KERNEL) > 0
        )
        far_mask = ~confirmed_d8
        opening_d3 = (
            cv2.dilate(
                self._e4_opening.astype(np.uint8), votes._INK_VOTE_E3_DILATE_KERNEL
            )
            > 0
        )
        opening_evidence = self._e4_opening_prob >= votes._INK_VOTE_E4_OPENING_EVIDENCE
        regions = (
            self._e4_region_big
            | self._e4_region_small
            | self._e4_region_slow
            | self._e4_region_thin
        )
        regions_dilated = (
            cv2.dilate(regions.astype(np.uint8), votes._INK_VOTE_E3_DILATE_KERNEL) > 0
        )
        covered = confirmed_d3 | regions_dilated
        count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
            ink.astype(np.uint8), 8
        )
        for index in range(1, count):
            area = int(stats[index, cv2.CC_STAT_AREA])
            if area < votes._INK_VOTE_E4_MIN_COMPONENT_PX:
                continue
            component = labels == index
            if (
                float(np.count_nonzero(component & opening_d3) / area) >= 0.5
                or float(np.count_nonzero(component & opening_evidence) / area) >= 0.5
            ):
                # Pre-existente na abertura: ignorado NESTA
                # passada, sem virar estado — nada absorve pra
                # sempre (a diferenca central contra a E3).
                continue
            frac_covered = float(np.count_nonzero(component & covered) / area)
            if frac_covered < 0.5:
                self._e4_open_track(
                    component,
                    area,
                    int(stats[index, cv2.CC_STAT_WIDTH]),
                    int(stats[index, cv2.CC_STAT_HEIGHT]),
                    far_mask,
                )
                continue
            # Subdivisao por nascimento: o residuo fora da
            # cobertura e re-componentizado e cada pedaco abre a
            # sua trilha; a parte coberta segue ignorada.
            residual = component & ~covered
            if np.count_nonzero(residual) < votes._INK_VOTE_E4_MIN_COMPONENT_PX:
                continue
            sub_count, sub_labels, sub_stats, _sub = cv2.connectedComponentsWithStats(
                residual.astype(np.uint8), 8
            )
            for sub_index in range(1, sub_count):
                sub_area = int(sub_stats[sub_index, cv2.CC_STAT_AREA])
                if sub_area < votes._INK_VOTE_E4_MIN_COMPONENT_PX:
                    continue
                self._e4_open_track(
                    sub_labels == sub_index,
                    sub_area,
                    int(sub_stats[sub_index, cv2.CC_STAT_WIDTH]),
                    int(sub_stats[sub_index, cv2.CC_STAT_HEIGHT]),
                    far_mask,
                    sub=True,
                )
        for region, side in (
            (self._e4_region_big, self._e4_side_big),
            (self._e4_region_small, self._e4_side_small),
            (self._e4_region_slow, self._e4_side_slow),
            (self._e4_region_thin, self._e4_side_thin),
        ):
            if np.any(region):
                masked = np.where(region, evidence, 0.0).astype(np.float32)
                confirmed = confirmed | side.add(masked)
        self._e4_passes += 1
        return confirmed

    def migrate(self, matrix):
        """Re-projeta todo o estado da geracao para outra grade.

        matrix leva a grade atual para a nova (convencao do
        cv2.warpPerspective). Confirmada e provisoria sao mascaras:
        vizinho mais proximo, sem ombro sintetico na borda da tinta.
        A janela do voto guarda probabilidades: bilinear, borda zero
        (o mesmo tratamento da evidencia ao vivo). Os buffers de
        estatistica derivados sao invalidados e a sequencia de baixa
        cobertura zera: o conteudo deles era da grade velha.
        """
        if self._confirmed is None:
            return
        matrix = np.asarray(matrix, dtype=np.float64)
        height, width = self._confirmed.shape
        size = (width, height)

        def nearest(mask):
            return cv2.warpPerspective(
                mask, matrix, size, flags=cv2.INTER_NEAREST, borderValue=0
            )

        self._confirmed = nearest(self._confirmed)
        if self._removal_streak is not None:
            self._removal_streak = nearest(self._removal_streak)
        self._provisional = nearest(self._provisional)
        self._provisional_ever = nearest(self._provisional_ever.astype(np.uint8)) > 0
        self._retracted_ever = nearest(self._retracted_ever.astype(np.uint8)) > 0
        self._window = deque(
            (
                cv2.warpPerspective(
                    item, matrix, size, flags=cv2.INTER_LINEAR, borderValue=0.0
                )
                for item in self._window
            ),
            maxlen=self._window.maxlen,
        )
        self._score_buf = None
        self._hits_buf = None
        self._seen_buf = None
        self._low_overlap_streak = 0
        if self._e3_active:
            # Estado da E3 acompanha a grade: mascaras por vizinho
            # mais proximo, mapas de evidencia/trilha bilineares —
            # o mesmo tratamento do resto do estado da geracao.
            if self._e3_old_union is not None:
                self._e3_old_union = nearest(self._e3_old_union.astype(np.uint8)) > 0
                self._e3_region_big = nearest(self._e3_region_big.astype(np.uint8)) > 0
                self._e3_region_small = (
                    nearest(self._e3_region_small.astype(np.uint8)) > 0
                )
                self._e3_phase1_maps = [
                    cv2.warpPerspective(
                        item,
                        matrix,
                        size,
                        flags=cv2.INTER_LINEAR,
                        borderValue=0.0,
                    )
                    for item in self._e3_phase1_maps
                ]
                self._e3_side_big.migrate(matrix, size)
                self._e3_side_small.migrate(matrix, size)
        if self._e4_active:
            # Estado da E5-S acompanha a grade, como o da E3:
            # abertura e regioes por vizinho mais proximo, mapa
            # de probabilidade da abertura e mapas de evidencia/
            # trilha bilineares.
            if self._e4_opening is not None:
                self._e4_opening = nearest(self._e4_opening.astype(np.uint8)) > 0
                self._e4_region_big = nearest(self._e4_region_big.astype(np.uint8)) > 0
                self._e4_region_small = (
                    nearest(self._e4_region_small.astype(np.uint8)) > 0
                )
                self._e4_region_slow = (
                    nearest(self._e4_region_slow.astype(np.uint8)) > 0
                )
                self._e4_region_thin = (
                    nearest(self._e4_region_thin.astype(np.uint8)) > 0
                )
                self._e4_opening_prob = cv2.warpPerspective(
                    self._e4_opening_prob,
                    matrix,
                    size,
                    flags=cv2.INTER_LINEAR,
                    borderValue=0.0,
                )
                self._e4_phase1_maps = [
                    cv2.warpPerspective(
                        item,
                        matrix,
                        size,
                        flags=cv2.INTER_LINEAR,
                        borderValue=0.0,
                    )
                    for item in self._e4_phase1_maps
                ]
                self._e4_side_big.migrate(matrix, size)
                self._e4_side_small.migrate(matrix, size)
                self._e4_side_slow.migrate(matrix, size)
                self._e4_side_thin.migrate(matrix, size)

    def _window_stats(self):
        """(soma, hits, visto-como-tinta) da janela, sem empilhar.

        O caminho antigo fazia np.stack da janela (3 mapas float32
        de pagina inteira, ~12 MB) e somava/contava/maximizava
        sobre a pilha a cada passada — o maior transitorio do
        acumulador (pesquisa de performance de 2026-11-03, T10).
        Aqui as tres reducoes saem por acumulacao em buffers
        reusados: a soma adiciona os mesmos mapas na mesma ordem
        (resultado float identico), hits e visto sao contagens
        inteiras/booleanas exatas. Os buffers sao devolvidos para
        leitura imediata; a proxima chamada os sobrescreve.
        """
        window = list(self._window)
        shape = window[0].shape
        if self._score_buf is None or self._score_buf.shape != shape:
            self._score_buf = np.zeros(shape, dtype=np.float32)
            self._hits_buf = np.zeros(shape, dtype=np.int32)
            self._seen_buf = np.zeros(shape, dtype=bool)
        score = self._score_buf
        np.copyto(score, window[0])
        for item in window[1:]:
            np.add(score, item, out=score)
        hits = self._hits_buf
        hits[...] = window[0] >= votes._INK_VOTE_HIT
        for item in window[1:]:
            np.add(hits, item >= votes._INK_VOTE_HIT, out=hits)
        seen = self._seen_buf
        seen[...] = window[0] > self.threshold
        for item in window[1:]:
            np.logical_or(seen, item > self.threshold, out=seen)
        return score, hits, seen

    def add(self, prob, visible=None, *, removal_allowed=True):
        prob = np.asarray(prob, dtype=np.float32)
        if visible is not None:
            visible = np.asarray(visible, dtype=bool)
            if visible.shape != prob.shape:
                visible = None
        if self._confirmed is None or self._confirmed.shape != prob.shape:
            self._removal_streak = None
            self._confirmed = np.zeros(prob.shape, dtype=np.uint8)
            self._provisional = np.zeros(prob.shape, dtype=np.uint8)
            self._provisional_ever = np.zeros(prob.shape, dtype=bool)
            self._retracted_ever = np.zeros(prob.shape, dtype=bool)
            self._window.clear()
            self._low_overlap_streak = 0
            self._turn_fired = False
            self._e3_active = None
            self._e4_active = None
            self._fast_active = None
            self._reset_e3_state()
            self._reset_e4_state()
        if self._e3_active is None:
            # A regra da geracao decide na primeira passada e nao
            # muda no meio dela (ver votes._INK_VOTE_E3_ENV). O corte de
            # latencia da F94 decide junto, na mesma passada.
            # Precedencia declarada: DRAW_INK_VOTE_E4 ligada vence
            # a E3 — com as duas ligadas roda so a E5-S.
            self._e4_active = votes._ink_vote_e4_enabled()
            self._e3_active = votes._ink_vote_e3_enabled() and not self._e4_active
            self._fast_active = votes._ink_vote_fast_enabled()
        confirmed_before = self._confirmed > 0
        canvas_before = int(np.count_nonzero(self._confirmed))
        # Oclusao: pixel que a passada nao pode ver (a mao sobre a
        # pagina) nao entrega evidencia, nem a favor nem contra. A
        # probabilidade dele entra zerada na janela — soma zero no
        # escore, nao conta hit nem "visto como tinta" —, o
        # julgamento de virada mede a cobertura so sobre a tinta
        # confirmada visivel (ou se abstem quando quase tudo esta
        # coberto: mao segurando a pagina nao e pagina trocada) e a
        # camada provisoria congela onde nao ha visao (ver abaixo).
        evidence = (
            prob if visible is None else np.where(visible, prob, 0.0).astype(np.float32)
        )
        mask_now = evidence > self.threshold
        turn = False
        if canvas_before >= identity._INK_TURN_MIN_CANVAS_PX and not self._turn_fired:
            if visible is None:
                judge_turn = True
                turn_low = (
                    int(np.count_nonzero(mask_now & confirmed_before))
                    <= identity._INK_TURN_MAX_OVERLAP * canvas_before
                )
            else:
                visible_confirmed = confirmed_before & visible
                visible_px = int(np.count_nonzero(visible_confirmed))
                judge_turn = (
                    visible_px >= identity._OCCLUSION_TURN_MIN_VISIBLE_PX
                    and visible_px >= 0.5 * canvas_before
                )
                turn_low = judge_turn and (
                    int(np.count_nonzero(mask_now & visible_confirmed))
                    <= identity._INK_TURN_MAX_OVERLAP * visible_px
                )
            if judge_turn:
                if turn_low:
                    self._low_overlap_streak += 1
                    if self._low_overlap_streak >= identity._INK_TURN_PASSES:
                        turn = True
                        self._turn_fired = True
                else:
                    self._low_overlap_streak = 0
        self._window.append(evidence.copy())
        if self._e4_active:
            # Regra E5-S (DRAW_INK_VOTE_E4): a confirmacao sai de
            # _e4_step; a provisoria segue a janela corrente, como
            # nas outras regras — quem muda e quem confirma.
            score, hits, seen_as_ink = self._window_stats()
            new_confirmed = self._e4_step(evidence) & ~confirmed_before
        elif self._e3_active:
            # Regra E3 (DRAW_INK_VOTE_E3): a confirmacao sai de
            # _e3_step; o "visto" da camada provisoria segue sendo a
            # janela corrente, como na regra principal — a E3 muda
            # quem confirma, nao o que a tela mostra como tinta nova.
            score, hits, seen_as_ink = self._window_stats()
            new_confirmed = self._e3_step(evidence) & ~confirmed_before
        else:
            score, hits, seen_as_ink = self._window_stats()
            confirmed_rule = (score >= votes._INK_VOTE_SCORE_STRONG) | (
                (hits >= votes._INK_VOTE_MIN_HITS) & (score >= votes._INK_VOTE_SCORE)
            )
            if np.any(confirmed_rule):
                # Porta de fronteira (ver votes._INK_FRONTIER_RADIUS):
                # dentro da faixa do ombro da tinta (confirmada ou
                # vista acima do limiar nesta janela), so confirma
                # quem alguma passada viu como tinta; a soma
                # sub-limiar das copias deslocadas nao engrossa o
                # traco nem poe camada nova sobre ele.
                anchor = seen_as_ink | confirmed_before
                near_anchor = (
                    cv2.dilate(
                        anchor.astype(np.uint8),
                        votes._INK_FRONTIER_KERNEL,
                    )
                    > 0
                )
                confirmed_rule &= seen_as_ink | ~near_anchor
            new_confirmed = confirmed_rule & ~confirmed_before
        new_confirmed_px = int(np.count_nonzero(new_confirmed))
        if new_confirmed_px:
            self._confirmed[new_confirmed] = 255
        removed_px = 0
        if registration._experimental_enabled("DRAW_INK_REMOVAL"):
            if self._removal_streak is None:
                self._removal_streak = np.zeros(prob.shape, dtype=np.uint8)
            # Sem máscara de visibilidade não há evidência negativa confiável.
            witnessed = False
            if removal_allowed and visible is not None and canvas_before:
                retained = np.count_nonzero(confirmed_before & visible & mask_now)
                witnessed = (
                    retained >= registration._REMOVAL_RETAINED_FRACTION * canvas_before
                    or retained >= registration._REMOVAL_WITNESS_FLOOR_PX
                )
            missing = (
                confirmed_before
                & visible
                & np.isfinite(prob)
                & (prob <= registration._REMOVAL_LOW_PROB)
                if witnessed
                else np.zeros(prob.shape, dtype=bool)
            )
            if witnessed:
                # Com testemunha: pixel à vista e não ausente vê o
                # streak zerar (evidência positiva ou prova
                # inconclusiva); pixel ausente conta. Ocluído ou sem
                # testemunha não informa nada — o streak segura, não
                # zera: a ausência do F-10 segue precisando ser
                # persistente, mas não precisa ser em passadas
                # consecutivas nem desobstruídas (a testemunha e a
                # mão oscilam em cena real — medido: retained
                # 1,5k~13,9k alternando no sim-hand, streak nunca
                # completava).
                resettable = visible & ~missing
                self._removal_streak[resettable] = 0
                self._removal_streak[missing] = np.minimum(
                    self._removal_streak[missing].astype(np.uint16) + 1,
                    registration._REMOVAL_PASSES,
                ).astype(np.uint8)
            removed = self._removal_streak >= registration._REMOVAL_PASSES
            removed_px = int(np.count_nonzero(removed))
            if removed_px:
                self._confirmed[removed] = 0
                self._removal_streak[removed] = 0
                # Nenhuma memória de voto pode ressuscitar o traço apagado.
                for item in self._window:
                    item[removed] = 0
                self._score_buf = self._hits_buf = self._seen_buf = None
                if self._e3_active:
                    for item in self._e3_phase1_maps:
                        item[removed] = 0
                    if self._e3_old_union is not None:
                        self._e3_old_union[removed] = False
                    # Regiões são suporte geométrico para redesenhar, não votos.
                    for side in (self._e3_side_big, self._e3_side_small):
                        if side._confirmed is not None:
                            side._confirmed[removed] = False
                        for item in side._maps:
                            item[removed] = 0
                if self._e4_active:
                    # Acomodacao com o DRAW_INK_REMOVAL do PR #67:
                    # a memoria de voto da E5-S tambem nao pode
                    # ressuscitar o traco apagado.
                    for item in self._e4_phase1_maps:
                        item[removed] = 0
                    if self._e4_opening is not None:
                        self._e4_opening[removed] = False
                        self._e4_opening_prob[removed] = 0
                    for mask in (
                        self._e4_region_big,
                        self._e4_region_small,
                        self._e4_region_slow,
                        self._e4_region_thin,
                    ):
                        if mask is not None:
                            mask[removed] = False
                    for side in (
                        self._e4_side_big,
                        self._e4_side_small,
                        self._e4_side_slow,
                        self._e4_side_thin,
                    ):
                        if side._confirmed is not None:
                            side._confirmed[removed] = False
                        for item in side._maps:
                            item[removed] = 0
                seen_as_ink[removed] = False
                score[removed] = 0
                hits[removed] = 0
        confirmed_now = self._confirmed > 0
        provisional_now = seen_as_ink & ~confirmed_now
        if self._fast_active:
            # Provisoria rapida (F94, SO exibicao): a evidencia de
            # hit acumulada (>= 2 hits na janela, soma >= 1,0) pinta
            # a tinta fraca antes da confirmacao. A confirmada nao
            # muda — poll() nao ve este pixel; se o voto nao
            # fechar, a provisoria retrata ao sair da janela, como
            # qualquer provisoria.
            provisional_now |= (
                (hits >= votes._INK_VOTE_FAST_PROV_MIN_HITS)
                & (score >= votes._INK_VOTE_FAST_PROV_MIN_SCORE)
            ) & ~confirmed_now
        previous_provisional = self._provisional > 0
        if visible is not None:
            # Sem visao nao ha retracao nem estreia: o provisorio
            # coberto fica como estava. Retrair e afirmar que a
            # tinta sumiu — e quem esta sobre ela e a mao, nao o
            # apagador; sem este congelamento, toda oclusao virava
            # retracao na regua e a tinta piscava ao reaparecer.
            provisional_now = provisional_now | (previous_provisional & ~visible)
        retracted = previous_provisional & ~provisional_now & ~confirmed_now
        if np.any(retracted):
            self._retracted_ever |= retracted
        self._provisional_ever |= provisional_now
        provisional_changed = bool(np.any(provisional_now != previous_provisional))
        self._provisional = np.where(provisional_now, 255, 0).astype(np.uint8)
        result = {
            "confirmed": self._confirmed.copy(),
            "provisional": self._provisional.copy(),
            "confirmed_changed": new_confirmed_px > 0 or removed_px > 0,
            "provisional_changed": provisional_changed,
            "new_confirmed_px": new_confirmed_px,
            "confirmed_px": int(np.count_nonzero(self._confirmed)),
            "provisional_px": int(np.count_nonzero(self._provisional)),
            "provisional_ever_px": int(np.count_nonzero(self._provisional_ever)),
            "retracted_px_total": int(np.count_nonzero(self._retracted_ever)),
            "turn": turn,
        }
        if registration._experimental_enabled("DRAW_INK_REMOVAL"):
            result["removed_confirmed_px"] = removed_px
        if self._e3_active:
            # Telemetria da E3: so existe com a flag ligada, como os
            # demais mecanismos atras de flag deste arquivo.
            result["ink_vote_e3"] = True
            result["ink_vote_e3_passes"] = self._e3_passes
            result["ink_vote_e3_tracks_big"] = self._e3_tracks_big
            result["ink_vote_e3_tracks_small"] = self._e3_tracks_small
        if self._e4_active:
            # Telemetria da E5-S: idem, so com DRAW_INK_VOTE_E4
            # ligada (com E3+E4 ligadas, a precedencia e da E4 e
            # a telemetria e esta).
            result["ink_vote_e4"] = True
            result["ink_vote_e4_passes"] = self._e4_passes
            result["ink_vote_e4_tracks_big"] = self._e4_tracks_big
            result["ink_vote_e4_tracks_small"] = self._e4_tracks_small
            result["ink_vote_e4_tracks_slow"] = self._e4_tracks_slow
            result["ink_vote_e4_tracks_thin"] = self._e4_tracks_thin
            result["ink_vote_e4_tracks_sub"] = self._e4_tracks_sub
        if self._fast_active:
            # Telemetria do corte de latencia (F94): idem, so com
            # DRAW_INK_VOTE_FAST ligada.
            result["ink_vote_fast"] = True
        return result
