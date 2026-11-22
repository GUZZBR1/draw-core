"""Acumulador de tinta em camadas: voto entre passadas."""

from collections import deque

import cv2
import numpy as np

from ..contracts import InkBaselineState
from . import hysteresis, identity, registration, votes
from .config import InkConfig

_BASELINE_CHANGE_THRESHOLD = 0.15


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

    def __init__(self, threshold=0.7, config=None):
        self.threshold = float(threshold)
        self._config = config if config is not None else InkConfig()
        self.reset()

    def reset(self, *, preserve_hold=False):
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
        if not preserve_hold:
            self._hold = None
        self.reset_baseline()

    def reset_baseline(self):
        """Descarta a referencia sem tocar nas camadas da tinta."""
        self._baseline_seen = None
        self._baseline_guard = None
        self._baseline_allowed = None
        self._baseline_not_guard = None
        self._baseline_exact_max = None
        self._baseline_reference_max = None
        self._baseline_change_threshold = None
        self._baseline_changed = None
        self._baseline_removal_visible = None
        self._baseline_capture_scratch = None
        self._baseline_current_coverage = None
        self._baseline_effective = None
        self._baseline_target = None
        self._baseline_last_coverage_source = None
        self._baseline_has_guard = False
        self._baseline_kernel = None
        self._baseline_started = False
        self._baseline_target_px = 0
        self._baseline_pending_px = 0

    def baseline_state(self):
        """Prontidao e cobertura capturada da referencia atual."""
        if not self._config.baseline:
            return InkBaselineState(
                False, False, False, False, 0, 0, 0, 0.0, "disabled"
            )
        captured_px = self._baseline_target_px - self._baseline_pending_px
        ready = captured_px > 0
        complete = ready and self._baseline_pending_px == 0
        phase = (
            "stabilizing"
            if not self._baseline_started
            else "ready"
            if complete
            else "ready_partial"
            if ready
            else "waiting_visibility"
        )
        return InkBaselineState(
            True,
            self._baseline_started,
            ready,
            complete,
            captured_px,
            self._baseline_target_px,
            self._baseline_pending_px,
            0.0
            if self._baseline_target_px == 0
            else captured_px / self._baseline_target_px,
            phase,
        )

    def _baseline_filter(self, prob, visible, capture_allowed, coverage):
        """Captura areas visiveis e veta evidencia page-clean inalterada.

        O mapa recebido ja esta registrado na grade ancora. A margem espacial
        absorve residuos de registro; novos tracos que cruzam conteudo antigo
        seguem elegiveis quando elevam a probabilidade sobre a referencia.
        """
        if not self._config.baseline:
            return prob, visible

        shape = prob.shape
        if self._baseline_seen is None or self._baseline_seen.shape != shape:
            self.reset_baseline()
            self._baseline_seen = np.zeros(shape, dtype=bool)
            self._baseline_guard = np.zeros(shape, dtype=bool)
            self._baseline_allowed = np.zeros(shape, dtype=bool)
            self._baseline_not_guard = np.ones(shape, dtype=bool)
            self._baseline_exact_max = np.zeros(shape, dtype=np.float32)
            self._baseline_reference_max = np.zeros(shape, dtype=np.float32)
            self._baseline_change_threshold = np.full(shape, np.inf, dtype=np.float32)
            self._baseline_changed = np.zeros(shape, dtype=bool)
            self._baseline_removal_visible = np.zeros(shape, dtype=bool)
            self._baseline_capture_scratch = np.zeros(shape, dtype=np.float32)
            self._baseline_effective = np.zeros(shape, dtype=bool)

        current_coverage = (
            np.ones(shape, dtype=bool)
            if coverage is None
            else np.asarray(coverage, dtype=bool)
        )
        if current_coverage.shape != shape:
            current_coverage = np.ones(shape, dtype=bool)
        self._baseline_current_coverage = current_coverage

        if capture_allowed and not self._baseline_started:
            self._baseline_started = True
            self._baseline_target = current_coverage.copy()
            self._baseline_target_px = int(np.count_nonzero(self._baseline_target))
            self._baseline_pending_px = self._baseline_target_px
        elif (
            capture_allowed
            and self._baseline_started
            and coverage is not None
            and coverage is not self._baseline_last_coverage_source
        ):
            newly_covered = current_coverage & ~self._baseline_target
            newly_covered_px = int(np.count_nonzero(newly_covered))
            if newly_covered_px:
                np.logical_or(
                    self._baseline_target, newly_covered, out=self._baseline_target
                )
                self._baseline_target_px += newly_covered_px
                self._baseline_pending_px += newly_covered_px
        if capture_allowed:
            self._baseline_last_coverage_source = coverage

        if capture_allowed and self._baseline_started and self._baseline_pending_px:
            candidates = current_coverage & self._baseline_target & ~self._baseline_seen
            if visible is not None:
                candidates &= visible
            captured_px = int(np.count_nonzero(candidates))
            if captured_px:
                np.logical_or(self._baseline_seen, candidates, out=self._baseline_seen)
                source = cv2.compare(prob, self._config.vote_hit, cv2.CMP_GE) > 0
                np.logical_and(source, candidates, out=source)
                source_pixels = int(np.count_nonzero(source))
                if self._config.baseline_margin_px:
                    margin = self._config.baseline_margin_px
                    if self._baseline_kernel is None:
                        self._baseline_kernel = np.ones(
                            (2 * margin + 1, 2 * margin + 1), np.uint8
                        )
                    source = cv2.dilate(source.astype(np.uint8), self._baseline_kernel)
                    self._baseline_has_guard |= source_pixels > 0
                    source = source > 0
                else:
                    self._baseline_has_guard |= source_pixels > 0
                np.logical_or(self._baseline_guard, source, out=self._baseline_guard)
                np.copyto(self._baseline_capture_scratch, 0.0)
                np.copyto(self._baseline_capture_scratch, prob, where=candidates)
                if self._config.baseline_margin_px:
                    neighborhood = cv2.dilate(
                        self._baseline_capture_scratch, self._baseline_kernel
                    )
                else:
                    neighborhood = self._baseline_capture_scratch
                np.maximum(
                    self._baseline_exact_max,
                    self._baseline_capture_scratch,
                    out=self._baseline_exact_max,
                )
                np.maximum(
                    self._baseline_reference_max,
                    neighborhood,
                    out=self._baseline_reference_max,
                )
                np.logical_not(self._baseline_guard, out=self._baseline_not_guard)
                np.logical_and(
                    self._baseline_seen,
                    self._baseline_not_guard,
                    out=self._baseline_allowed,
                )
                np.logical_and(
                    self._baseline_seen,
                    self._baseline_guard,
                    out=self._baseline_changed,
                )
                np.copyto(self._baseline_change_threshold, np.inf)
                np.add(
                    self._baseline_exact_max,
                    _BASELINE_CHANGE_THRESHOLD,
                    out=self._baseline_change_threshold,
                    where=self._baseline_changed,
                )
                # Dois criterios, sem margem dupla: no pixel impresso o
                # aumento vale contra a propria captura (exact + delta —
                # um drift de centesimos nao reconfirma a impressao como
                # tinta nova), e qualquer pixel da guarda ainda precisa
                # superar o maximo da vizinhanca, que e a protecao contra
                # drift de registro. Um traco que cruza a borda de uma
                # impressao escura passa: exigir vizinhanca + delta
                # colocaria a exigencia acima de 1.0.
                np.maximum(
                    self._baseline_change_threshold,
                    self._baseline_reference_max,
                    out=self._baseline_change_threshold,
                    where=self._baseline_changed,
                )
                # Evita veto permanente em pixels vizinhos a impressao escura:
                # o teto de 0.99 so vale para a margem dilatada.
                np.less(
                    self._baseline_exact_max,
                    self._config.vote_hit,
                    out=self._baseline_not_guard,
                )
                np.logical_and(
                    self._baseline_not_guard,
                    self._baseline_changed,
                    out=self._baseline_not_guard,
                )
                np.minimum(
                    self._baseline_change_threshold,
                    np.float32(0.99),
                    out=self._baseline_change_threshold,
                    where=self._baseline_not_guard,
                )
                self._baseline_pending_px = max(
                    0, self._baseline_pending_px - captured_px
                )

        if capture_allowed and self._baseline_started and self._baseline_has_guard:
            np.greater(
                prob,
                self._baseline_change_threshold,
                out=self._baseline_changed,
            )
            np.logical_or(
                self._baseline_allowed,
                self._baseline_changed,
                out=self._baseline_effective,
            )
        else:
            np.copyto(self._baseline_effective, self._baseline_allowed)
        effective_visible = (
            self._baseline_effective
            if visible is None
            else self._baseline_effective & visible
        )
        return prob, effective_visible

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
        hit = self._config.vote_hit
        hits[...] = window[0] >= hit
        for item in window[1:]:
            np.add(hits, item >= hit, out=hits)
        seen = self._seen_buf
        seen[...] = window[0] > self.threshold
        for item in window[1:]:
            np.logical_or(seen, item > self.threshold, out=seen)
        return score, hits, seen

    def would_freeze(self, paper_ok, shape=None):
        """Mascara booleana de pixels congelados por paper_ok/hold sem mutar estado."""
        if paper_ok is None:
            return None
        paper_ok = np.asarray(paper_ok, dtype=bool)
        if shape is not None and paper_ok.shape != shape:
            return None
        if self._hold is None or self._hold.shape != paper_ok.shape:
            hold = np.zeros(paper_ok.shape, dtype=np.uint8)
        else:
            hold = self._hold.copy()
            np.subtract(hold, 1, out=hold, where=hold > 0)
        hold[~paper_ok] = self._config.occlusion_hold_passes + 1
        return ~paper_ok | (hold > 0)

    def add(
        self,
        prob,
        visible=None,
        *,
        removal_allowed=True,
        baseline_capture=False,
        baseline_coverage=None,
        paper_ok=None,
    ):
        """Uma passada. paper_ok (bool, forma de prob) e a evidencia
        fotometrica de papel exposto (draw.ink.paper_evidence): onde e
        False — e por occlusion_hold_passes passadas depois — a regiao
        congela como oclusao (sem voto, sem remocao, provisoria
        parada). None mantem o comportamento sem guarda."""
        prob = np.asarray(prob, dtype=np.float32)
        if visible is not None:
            visible = np.asarray(visible, dtype=bool)
            if visible.shape != prob.shape:
                visible = None
        # Sem mascara de visibilidade nao ha evidencia negativa
        # confiavel — a guarda nao a inventa.
        raw_visible = visible
        had_visibility = raw_visible is not None
        frozen = None
        if paper_ok is not None:
            paper_ok = np.asarray(paper_ok, dtype=bool)
            if paper_ok.shape != prob.shape:
                paper_ok = None
        if self._confirmed is None or self._confirmed.shape != prob.shape:
            self._removal_streak = None
            self._confirmed = np.zeros(prob.shape, dtype=np.uint8)
            self._provisional = np.zeros(prob.shape, dtype=np.uint8)
            self._provisional_ever = np.zeros(prob.shape, dtype=bool)
            self._retracted_ever = np.zeros(prob.shape, dtype=bool)
            self._window.clear()
            self._low_overlap_streak = 0
            self._turn_fired = False
        if paper_ok is not None:
            if self._hold is None or self._hold.shape != prob.shape:
                self._hold = np.zeros(prob.shape, dtype=np.uint8)
            np.subtract(self._hold, 1, out=self._hold, where=self._hold > 0)
            # +1: a passada em que a evidencia some ainda e a 1a do hold; o
            # decremento da passada seguinte nao pode soltar uma cedo.
            self._hold[~paper_ok] = self._config.occlusion_hold_passes + 1
            frozen = ~paper_ok | (self._hold > 0)
            visible = ~frozen if visible is None else visible & ~frozen
        physical_visible = visible
        prob, visible = self._baseline_filter(
            prob, visible, baseline_capture, baseline_coverage
        )
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
        evidence = prob if visible is None else np.where(visible, prob, np.float32(0.0))
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
        score, hits, seen_as_ink = self._window_stats()
        confirmed_rule = (score >= self._config.vote_score_strong) | (
            (hits >= votes._INK_VOTE_MIN_HITS) & (score >= self._config.vote_score)
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
        if self._config.hysteresis and np.any(confirmed_rule):
            # Poeira isolada: um candidato so confirma se a media da janela
            # e >= t_low e o componente dele tem uma ancora (media >= t_high
            # ou tinta ja confirmada). Escala da media, nao do seen.
            cfg = self._config
            # Janela ainda enchendo: passada faltante e evidencia zero.
            mean = score / votes._INK_VOTE_WINDOW
            # Tolerancia de float32: 3 x 0.9 somado em float32 e dividido por 3 da
            # 0.8999999 < 0.9, e o traco constante exatamente em t_high nunca
            # confirmava (medido na auditoria de 2026-11-19).
            eps = hysteresis.FLOAT_EPS
            strong = confirmed_rule & (mean >= cfg.t_high - eps)
            weak = confirmed_rule & ~strong & (mean >= cfg.t_low - eps)
            kept = hysteresis.keep_anchored(weak, strong | confirmed_before)
            confirmed_rule = strong | kept
        if frozen is not None:
            # Votos antigos da janela nao confirmam o que esta congelado:
            # regiao suspeita de oclusao nao entra no canvas.
            confirmed_rule &= ~frozen
        new_confirmed = confirmed_rule & ~confirmed_before
        new_confirmed_px = int(np.count_nonzero(new_confirmed))
        if new_confirmed_px:
            self._confirmed[new_confirmed] = 255
        removed_px = 0
        witnessed = False
        if self._config.removal:
            if self._removal_streak is None:
                self._removal_streak = np.zeros(prob.shape, dtype=np.uint8)
            # Sem máscara de visibilidade não há evidência negativa confiável.
            witnessed = False
            removal_visible = visible
            baseline_suppressed = None
            if self._config.baseline:
                removal_visible = None
            if (
                self._config.baseline
                and had_visibility
                and physical_visible is not None
                and canvas_before
                and removal_allowed
            ):
                np.logical_or(
                    self._baseline_current_coverage,
                    confirmed_before,
                    out=self._baseline_removal_visible,
                )
                np.logical_and(
                    self._baseline_removal_visible,
                    physical_visible,
                    out=self._baseline_removal_visible,
                )
                np.logical_and(
                    self._baseline_removal_visible,
                    self._baseline_seen,
                    out=self._baseline_removal_visible,
                )
                removal_visible = self._baseline_removal_visible
                # "Ausente" e prob consistente com a referencia salva
                # (<= max da propria captura + delta ou da vizinhanca),
                # nao "fora do effective desta passada": nas passadas sem
                # captura o effective nao recebe o override de mudanca e
                # todo pixel do guard pareceria apagado — um traco vivo
                # sobre marca impressa ganharia streak de remocao.
                np.less_equal(
                    prob,
                    self._baseline_change_threshold,
                    out=self._baseline_not_guard,
                )
                np.logical_and(
                    self._baseline_seen,
                    self._baseline_guard,
                    out=self._baseline_changed,
                )
                np.logical_and(
                    self._baseline_changed,
                    self._baseline_not_guard,
                    out=self._baseline_changed,
                )
                baseline_suppressed = self._baseline_changed
            if (
                removal_allowed
                and had_visibility
                and removal_visible is not None
                and canvas_before
            ):
                retained = np.count_nonzero(
                    confirmed_before & removal_visible & mask_now
                )
                witnessed = (
                    retained >= registration._REMOVAL_RETAINED_FRACTION * canvas_before
                    or retained >= registration._REMOVAL_WITNESS_FLOOR_PX
                )
            if witnessed:
                missing_ink = np.isfinite(prob) & (
                    (prob <= registration._REMOVAL_LOW_PROB)
                    | (
                        baseline_suppressed
                        if baseline_suppressed is not None
                        else False
                    )
                )
                missing = confirmed_before & removal_visible & missing_ink
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
                resettable = removal_visible & ~missing
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
                seen_as_ink[removed] = False
                score[removed] = 0
                hits[removed] = 0
        confirmed_now = self._confirmed > 0
        provisional_now = seen_as_ink & ~confirmed_now
        if self._config.hysteresis:
            provisional_now = hysteresis.filter_provisional(
                provisional_now,
                evidence,
                confirmed_now,
                t_high=self._config.t_high,
                min_px=self._config.provisional_min_px,
            )
            if visible is not None:
                # Ancora nova no lado visivel nao revela o lado coberto: o
                # coberto so mantem o que ja era mostrado (merge abaixo).
                provisional_now = provisional_now & visible
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
        # bool→u8 *255: np.where+astype gastava dois temporários de
        # página inteira por passada (~1,7 ms nesta VM; ~0,04 ms
        # assim — issue #102). Buffer reusado com copyto+*= mediu
        # PIOR (~+4 ms) — provável custo de laço escalar no *= de
        # atributo; astype*255 repõe o array como sempre fez.
        self._provisional = provisional_now.astype(np.uint8) * 255
        frozen_pending_px = 0
        if frozen is not None:
            unmasked_frozen = frozen if raw_visible is None else (raw_visible & frozen)
            pending = unmasked_frozen & ~confirmed_before & (prob > self.threshold)
            if (
                self._config.removal
                and removal_allowed
                and had_visibility
                and canvas_before
                and paper_ok is not None
            ):
                exposed_visible = raw_visible & paper_ok
                exposed_retained = np.count_nonzero(
                    confirmed_before & exposed_visible & (prob > self.threshold)
                )
                hold_witnessed = witnessed or (
                    exposed_retained
                    >= registration._REMOVAL_RETAINED_FRACTION * canvas_before
                    or exposed_retained >= registration._REMOVAL_WITNESS_FLOOR_PX
                )
                if hold_witnessed:
                    pending = pending | (
                        confirmed_before
                        & exposed_visible
                        & (self._hold > 0)
                        & np.isfinite(prob)
                        & (prob <= registration._REMOVAL_LOW_PROB)
                    )
            frozen_pending_px = int(np.count_nonzero(pending))
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
            "frozen_px": 0 if frozen is None else int(np.count_nonzero(frozen)),
            "frozen_pending_px": frozen_pending_px,
            # Papel que JA voltou a aparecer mas ainda esta no hold: sombra
            # em recuperacao (limitada pelo hold). Borda/sombra permanente
            # tem paper_ok False a cada passada e nao entra aqui.
            "recovering_px": (
                0
                if paper_ok is None
                else int(np.count_nonzero(paper_ok & (self._hold > 0)))
            ),
        }
        if self._config.removal:
            result["removed_confirmed_px"] = removed_px
        return result
