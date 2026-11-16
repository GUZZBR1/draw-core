"""Regra de voto da tinta entre passadas (janela, score, portas)."""

import os
from collections import deque

import cv2
import numpy as np

# Confirmacao entre passadas (regras medidas no diagnostico de
# 2026-11-01, draw-lab/stall-diagnosis-2026-11-01): sobre a soma
# das probabilidades das ultimas _INK_VOTE_WINDOW passadas, um
# pixel confirma quando (a) a soma chega a _INK_VOTE_SCORE_STRONG
# (tinta forte confirma na 2a passada) ou (b) ele aparece com
# prob >= _INK_VOTE_HIT nas 3 passadas da janela e a soma chega a
# _INK_VOTE_SCORE (o lapis fraco estavel confirma na 3a). Copia
# deslocada de tremor e FP de mobiliario aparecem de forma
# intermitente por posicao e nao fecham nem (a) nem (b).
_INK_VOTE_WINDOW = 3


_INK_VOTE_SCORE = 1.4


_INK_VOTE_SCORE_STRONG = 1.9


_INK_VOTE_HIT = 0.5


_INK_VOTE_MIN_HITS = 3


# Porta de fronteira da confirmacao (medida na regua de replay,
# draw-lab/replay-ruler-2026-11-01, modo hold sobre o codigo sem
# ela): com a pagina desenhada parada, o canvas confirmado
# crescia em degraus a cada alinhamento de fase entre o ciclo do
# warp e a janela do voto — um salto de +9.999 px na passada 89
# e 6.144 px confirmados que passada nenhuma viu acima do
# limiar. O mecanismo: o warp treme, copias deslocadas do mesmo
# traco somam probabilidade SUB-limiar (0,5-0,7) no ombro do
# traco e o voto fecha sobre a soma, camada sobre camada, sem
# nenhuma passada ter chamado aquilo de tinta.
# A porta: pixel dentro da faixa do ombro — dilatacao de
# _INK_FRONTIER_RADIUS px sobre (tinta confirmada ∪ tinta que
# a janela viu acima do limiar) — so confirma se alguma
# passada da janela o viu acima do limiar: evidencia nova
# SUBSTITUI a posicao da antiga, nao soma um ombro novo ao
# redor dela. O raio e o ombro medido nos mapas reais do
# cache da regua: a banda 0,5-0,7 mora a p50 = 1 px e
# p90 ≈ 3 px do nucleo > 0,7. Longe do ombro o voto segue
# intacto: e ele que descobre o lapis fraco consistente
# (0,55 x 3) em regiao nova. Varredura offline sobre os warps
# f28-f30 em ciclo, 300 passadas: fora-da-referencia cai de
# 8.567 px (sem porta) para 419 px (raio 3 ancorado), e o
# crescimento total satura no teto da uniao das passadas.
_INK_FRONTIER_RADIUS = 3


_INK_FRONTIER_KERNEL = np.ones(
    (2 * _INK_FRONTIER_RADIUS + 1, 2 * _INK_FRONTIER_RADIUS + 1),
    dtype=np.uint8,
)


# Regra de voto E3 (frente 89, desenho + prototipos offline em
# draw-lab/live-audit-2026-11-10/89-regra-do-voto.md; implementacao
# da frente 90): a candidata vencedora da F89, porto fiel da bancada
# dela (frente89/f89_bench4.py, classe CommitE3). A regra atual
# confirma sobre janelas deslizantes sobrepostas e o canvas cresce
# 2,90x na regua de 17 passadas (relatorios 86/89): a franja que
# pisca 2x na mesma posicao dentro de alguma janela confirma. A E3
# separa a geracao em duas fases:
# - Fase 1 (as _INK_VOTE_E3_PHASE1_PASSES primeiras passadas): o
#   canvas nasce UMA vez, do nucleo de consenso espacial das 3
#   passadas — tinta a <= _INK_FRONTIER_RADIUS px do pixel nas 3
#   passadas, vista acima do limiar ao menos 1x no proprio pixel e
#   soma das 3 probabilidades >= _INK_VOTE_E3_CORE_MIN_SUM (6.539 px
#   e contencao 0,904 na regua). A uniao de tudo que foi visto acima
#   do limiar nessas passadas vira "conteudo velho" da geracao.
# - Fase 2: so entra tinta de componente conexo NOVO — componente
#   (acima do limiar, area >= _INK_VOTE_E3_MIN_COMPONENT_PX) com
#   menos de metade da area sobre o conteudo velho dilatado e fora
#   das trilhas ja abertas. Componente sobre o velho e absorvido
#   pelo velho (copia deslocada e franja nunca abrem trilha). A
#   regiao do componente novo (dilatada) abre uma trilha lateral
#   onde so a evidencia da regiao vota, com persistencia
#   consecutiva estrita dividida por tamanho: componente grande
#   (>= _INK_VOTE_E3_BIG_COMPONENT_PX) confirma com
#   _INK_VOTE_E3_BIG_WINDOW passadas consecutivas acima do limiar e
#   soma >= _INK_VOTE_E3_BIG_SCORE; componente pequeno confirma com
#   _INK_VOTE_E3_SMALL_WINDOW e soma >= _INK_VOTE_E3_SMALL_SCORE.
# Custos medidos da F89, assumidos: o canvas final cobre menos da
# tinta de cada passada que o da regra atual (completude 0,308 x
# 0,634 no prototipo offline — a regua formal e da frente 90);
# marca pequena confirma devagar (trilha lenta); conteudo das 3
# primeiras passadas fora do nucleo e "velho" pra sempre na
# geracao. Atras de DRAW_INK_VOTE_E3 (padrao 0): com a flag
# desligada o acumulador roda a regra atual sem tocar em nenhum
# estado da E3. A flag e LIDA UMA VEZ por geracao (na primeira
# passada apos o reset): trocar a variavel no meio da geracao nao
# mistura as duas regras no mesmo canvas.
_INK_VOTE_E3_ENV = "DRAW_INK_VOTE_E3"
_INK_VOTE_E3_PHASE1_PASSES = 3
_INK_VOTE_E3_CORE_MIN_SUM = 1.0
_INK_VOTE_E3_MIN_COMPONENT_PX = 20
_INK_VOTE_E3_BIG_COMPONENT_PX = 100
_INK_VOTE_E3_BIG_WINDOW = 3
_INK_VOTE_E3_BIG_SCORE = 2.1
_INK_VOTE_E3_SMALL_WINDOW = 5
_INK_VOTE_E3_SMALL_SCORE = 3.5
_INK_VOTE_E3_DILATE_KERNEL = cv2.getStructuringElement(
    cv2.MORPH_ELLIPSE,
    (2 * _INK_FRONTIER_RADIUS + 1, 2 * _INK_FRONTIER_RADIUS + 1),
)
_INK_VOTE_E3_REGION_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))


def _ink_vote_e3_enabled():
    value = os.environ.get(_INK_VOTE_E3_ENV, "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


# Regra de voto E5-S (frentes 106/107, implementacao da frente 108;
# draw-lab/live-audit-2026-11-10/106-voto-e4-sucessor-e3.md e
# 107-voto-e5-subdivisao.md): sucessora da E3, atras de
# DRAW_INK_VOTE_E4 (o nome da flag e o da familia E4 desenhada na
# F106; o mecanismo implementado e a E5-S = E4j + subdivisao por
# nascimento, a configuracao que a F107 validou em prototipo).
# A E3 confunde "visto" com "velho" (a uniao de tudo que foi visto
# na fase 1 vira barreira e conteudo nascido encostado nela nunca
# abre trilha: hachura progressiva 0,072 no simulador). A E5-S
# separa as duas coisas e subdivide o resto:
# - "Velho" = so o instantaneo de ABERTURA da geracao: a mascara
#   da 1a passada congelada, que nunca expande por absorcao, mais
#   o MAPA de probabilidade da abertura — componente com >=50%
#   da area sobre o velho dilatado (r3) OU com >=50% dos pixels
#   com evidencia de abertura >= _INK_VOTE_E4_OPENING_EVIDENCE
#   e pre-existente naquela passada, sem virar estado.
# - Fase 1 identica a da E3 (nucleo de consenso espacial das 3
#   primeiras passadas, _e3_phase1_core), mas o residuo dela —
#   visto, nao confirmado — NAO vira barreira: na fase 2 ele e
#   reclassificado como qualquer componente novo.
# - Novidade e cobertura medidas contra o CONFIRMADO dilatado e
#   as regioes de trilhas ja abertas, nunca contra a uniao do
#   visto. Componente com <50% sobre a cobertura abre trilha pela
#   propria forma/distancia: longe do confirmado (>=50% da area
#   a mais de 8 px dele) abre trilha por tamanho — grande
#   (>=100 px, 3 consecutivas, soma >= 2,1, regiao r6), pequena
#   (20-99 px, 5 consecutivas, soma >= 3,5, regiao r6) ou FINA
#   (forma de linha: lado maior >= 50 e area <= 3,5x o lado;
#   voto com tolerancia espacial de 1 px, 3 consecutivas,
#   soma >= 2,1, regiao r3 — a linha de 1 px tremula +-1 px e o
#   hit estrito no mesmo pixel nao fecha); na banda 3-8 px do
#   confirmado abre a trilha LENTA (5 consecutivas, soma >= 3,5,
#   regiao r3) — a persistencia estrita separa a copia deslocada
#   do traco novo encostado.
# - SUBDIVISAO POR NASCIMENTO (a peca da F107): componente com
#   >=50% sobre a cobertura nao morre inteiro — o RESIDUO fora
#   da cobertura e re-componentizado e cada sub-componente
#   >= 20 px abre a SUA trilha, classificado pela sua propria
#   forma/distancia, com regiao r3. E o que fecha a classe da
#   absorcao da hachura (bloco de um componente so: as linhas
#   novas, minoria dele, nunca abriam trilha): prototipo
#   hachura 0,749 -> 0,996, cursiva 0,886 -> 0,997, CAD
#   0,943 -> 1,000. A parte coberta segue ignorada.
# Portoes e ressalvas assumidas (F107, re-registro do Lucas de
# 2026-11-12): o crescimento no simulador e julgado como
# "<= default em recall equalizado, por cenario" (nao na classe
# da E3); 1 px segue teto de modelo (forte 0,641 no prototipo;
# medio com teto 0,35); eventos crescem um pouco sobre a E3
# (3,73 x 3,34 no prototipo — copia deslocada e indistinguivel
# de conteudo novo para a regra local; e problema de registro).
# Coexistencia com a E3: as duas flags podem estar ligadas; a
# PRECEDENCIA DECLARADA e E4 > E3 — com as duas ligadas roda so
# a E5-S (a telemetria e a da E4). Como a E3, a flag e LIDA UMA
# VEZ por geracao; com ela desligada o acumulador roda a regra
# de sempre sem tocar em nenhum estado da E4.
_INK_VOTE_E4_ENV = "DRAW_INK_VOTE_E4"
_INK_VOTE_E4_OPENING_EVIDENCE = 0.35
_INK_VOTE_E4_MIN_COMPONENT_PX = 20
_INK_VOTE_E4_BIG_COMPONENT_PX = 100
_INK_VOTE_E4_BIG_WINDOW = 3
_INK_VOTE_E4_BIG_SCORE = 2.1
_INK_VOTE_E4_SMALL_WINDOW = 5
_INK_VOTE_E4_SMALL_SCORE = 3.5
_INK_VOTE_E4_SLOW_WINDOW = 5
_INK_VOTE_E4_SLOW_SCORE = 3.5
_INK_VOTE_E4_THIN_WINDOW = 3
_INK_VOTE_E4_THIN_SCORE = 2.1
_INK_VOTE_E4_THIN_MIN_LENGTH = 50
_INK_VOTE_E4_THIN_MAX_AREA_RATIO = 3.5
_INK_VOTE_E4_FAR_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))
_INK_VOTE_E4_TOLERANCE_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))


def _ink_vote_e4_enabled():
    value = os.environ.get(_INK_VOTE_E4_ENV, "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


# Corte de latencia voto->canvas (frente 94, 2026-11-12;
# draw-lab/live-audit-2026-11-10/94-latencia-voto-canvas.md).
# A medicao da F94 separou o que as F89/F90 mediam fundido: a
# tinta FORTE ja fica VISIVEL na 1a passada nos dois bracos (a
# provisoria pinta o que a janela viu acima do limiar), mas so
# CONFIRMA na 2a (regra atual) ou na 3a/5a (E3: nucleo/trilha
# grande/trilha pequena); a tinta FRACA canonica (0,55, o lapis
# do comentario do voto) NAO fica visivel antes de confirmar —
# a provisoria so mostra o que passou do limiar de tinta (0,7),
# e a evidencia de hit (>= _INK_VOTE_HIT) nao pintava nada: na
# regra atual ela surge de supetao na 3a passada, ja confirmada;
# na E3 nunca surge (componente <= limiar nao abre trilha nem
# entra no nucleo).
# O corte que a F94 ENTREGA, atras de DRAW_INK_VOTE_FAST
# (padrao 0, lida uma vez por geracao junto com a da E3), e so
# na camada provisoria (exibicao): pixel com
# >= _INK_VOTE_FAST_PROV_MIN_HITS hits na janela e soma
# >= _INK_VOTE_FAST_PROV_MIN_SCORE entra na provisoria antes de
# confirmar — a tinta fraca fica visivel na 2a passada nos dois
# bracos, em vez de surgir confirmada na 3a (regra atual) ou
# nunca (E3). A confirmada NAO muda: quem consome canvas
# (poll) nao ve pixel nenhum a mais, e as reguas de crescimento/
# contencao/completude ficam byte-identicas nos dois bracos; a
# provisoria que nao confirma segue retratando ao sair da
# janela, e a contagem de retratados mede o custo.
# O corte de CONFIRMACAO (regra forte de 2 passadas — soma
# >= 1,9, a paridade com _INK_VOTE_SCORE_STRONG — nas trilhas
# e no nucleo da fase 1 da E3) foi implementado e MEDIDO nesta
# frente e REPROVADO na regua: crescimento 1,216-1,554x contra
# o portao de 1,15x em todas as variantes (so trilhas, so
# nucleo, so trilha grande, soma 1,96, com consenso espacial —
# a condicao de vizinhanca e vazia na franja, que sempre tem
# tinta a <= 3 px). O tremor entre passadas vizinhas e
# correlacionado: 2 passadas fortes consecutivas no mesmo
# pixel acontecem na franja do flicker, nao so no traco novo.
# A latencia de confirmacao da E3 esta no piso da evidencia
# que os portoes permitem; nao ha corte de confirmacao nesta
# camada sem devolver o crescimento que a E3 eliminou.
_INK_VOTE_FAST_ENV = "DRAW_INK_VOTE_FAST"
_INK_VOTE_FAST_PROV_MIN_HITS = 2
_INK_VOTE_FAST_PROV_MIN_SCORE = 1.0


def _ink_vote_fast_enabled():
    value = os.environ.get(_INK_VOTE_FAST_ENV, "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _e3_phase1_core(maps, threshold):
    """Nucleo de consenso espacial das primeiras passadas (F89).

    Confirma o pixel que tem tinta (prob > limiar) a
    <= _INK_FRONTIER_RADIUS px em TODAS as passadas da fase 1, foi
    visto acima do limiar ao menos uma vez no proprio pixel e cuja
    soma de probabilidades na fase chega a _INK_VOTE_E3_CORE_MIN_SUM.
    """
    total = maps[0].copy()
    for item in maps[1:]:
        np.add(total, item, out=total)
    hits = np.zeros(maps[0].shape, dtype=np.int32)
    neighbours = np.zeros(maps[0].shape, dtype=np.int32)
    for item in maps:
        ink = item > threshold
        np.add(hits, ink, out=hits)
        np.add(
            neighbours,
            cv2.dilate(ink.astype(np.uint8), _INK_VOTE_E3_DILATE_KERNEL) > 0,
            out=neighbours,
        )
    return (
        (neighbours >= len(maps)) & (hits >= 1) & (total >= _INK_VOTE_E3_CORE_MIN_SUM)
    )


class _E3SideVote:
    """Voto estrito de uma trilha lateral da E3 (bancada da F89).

    Janela deslizante das ultimas `window` passadas ALIMENTADAS (a
    trilha so e alimentada nas passadas em que a regiao dela
    existe); o pixel confirma quando foi visto acima do limiar em
    TODAS as passadas da janela cheia e a soma chega a min_score —
    persistencia consecutiva, sem a janela sobreposta da regra
    principal. A porta de fronteira e a mesma da regra principal
    (kernel quadrado de _INK_FRONTIER_RADIUS sobre visto u
    confirmado da trilha): dentro do ombro, so confirma quem a
    janela viu acima do limiar.
    """

    def __init__(self, window, min_score, threshold):
        self._window_len = int(window)
        self._min_score = float(min_score)
        self._threshold = float(threshold)
        self.reset()

    def reset(self):
        self._maps = deque(maxlen=self._window_len)
        self._confirmed = None

    def migrate(self, matrix, size):
        if self._confirmed is None:
            return
        self._confirmed = (
            cv2.warpPerspective(
                self._confirmed.astype(np.uint8),
                matrix,
                size,
                flags=cv2.INTER_NEAREST,
                borderValue=0,
            )
            > 0
        )
        self._maps = deque(
            (
                cv2.warpPerspective(
                    item, matrix, size, flags=cv2.INTER_LINEAR, borderValue=0.0
                )
                for item in self._maps
            ),
            maxlen=self._window_len,
        )

    def add(self, prob):
        if self._confirmed is None or self._confirmed.shape != prob.shape:
            self._confirmed = np.zeros(prob.shape, dtype=bool)
            self._maps.clear()
        self._maps.append(prob.copy())
        maps = list(self._maps)
        score = maps[0].copy()
        for item in maps[1:]:
            np.add(score, item, out=score)
        hits = (maps[0] > self._threshold).astype(np.int32)
        for item in maps[1:]:
            np.add(hits, item > self._threshold, out=hits)
        seen = hits > 0
        rule = (hits >= self._window_len) & (score >= self._min_score)
        if np.any(rule):
            anchor = seen | self._confirmed
            near_anchor = cv2.dilate(anchor.astype(np.uint8), _INK_FRONTIER_KERNEL) > 0
            rule &= seen | ~near_anchor
        self._confirmed |= rule
        return self._confirmed


class _E4ThinSideVote:
    """Voto da trilha fina da E5-S: estrito com tolerancia de 1 px.

    Porto do SideTol dos prototipos das F106/F107: a linha de
    1 px tremula +-1 px entre passadas e o hit no mesmo pixel em
    toda a janela nao fecha. Aqui o hit conta na vizinhanca r1
    (vizinhanca >= janela), o pixel precisa de >= 1 hit proprio
    e a soma da janela sobre os mapas dilatados r1 fecha em
    min_score. A porta de fronteira e a mesma das outras
    trilhas. Interface identica a do _E3SideVote (reset/migrate/
    add; _confirmed/_maps com os mesmos nomes) para o caminho de
    remocao (DRAW_INK_REMOVAL) limpar as duas familias igual.
    """

    def __init__(self, window, min_score, threshold):
        self._window_len = int(window)
        self._min_score = float(min_score)
        self._threshold = float(threshold)
        self.reset()

    def reset(self):
        self._maps = deque(maxlen=self._window_len)
        self._confirmed = None

    def migrate(self, matrix, size):
        if self._confirmed is None:
            return
        self._confirmed = (
            cv2.warpPerspective(
                self._confirmed.astype(np.uint8),
                matrix,
                size,
                flags=cv2.INTER_NEAREST,
                borderValue=0,
            )
            > 0
        )
        self._maps = deque(
            (
                cv2.warpPerspective(
                    item, matrix, size, flags=cv2.INTER_LINEAR, borderValue=0.0
                )
                for item in self._maps
            ),
            maxlen=self._window_len,
        )

    def add(self, prob):
        if self._confirmed is None or self._confirmed.shape != prob.shape:
            self._confirmed = np.zeros(prob.shape, dtype=bool)
            self._maps.clear()
        self._maps.append(prob.copy())
        maps = list(self._maps)
        if len(maps) < self._window_len:
            return self._confirmed
        score = None
        hits = None
        neighbours = None
        seen = None
        for item in maps:
            dilated = cv2.dilate(item, _INK_VOTE_E4_TOLERANCE_KERNEL)
            score = dilated.copy() if score is None else score + dilated
            hit = (item > self._threshold).astype(np.int32)
            hits = hit if hits is None else hits + hit
            near_hit = (
                cv2.dilate(
                    (item > self._threshold).astype(np.uint8),
                    _INK_VOTE_E4_TOLERANCE_KERNEL,
                )
                > 0
            ).astype(np.int32)
            neighbours = near_hit if neighbours is None else neighbours + near_hit
            seen = (hit > 0) if seen is None else (seen | (hit > 0))
        rule = (
            (neighbours >= self._window_len) & (hits >= 1) & (score >= self._min_score)
        )
        if np.any(rule):
            anchor = seen | self._confirmed
            near_anchor = cv2.dilate(anchor.astype(np.uint8), _INK_FRONTIER_KERNEL) > 0
            rule &= seen | ~near_anchor
        self._confirmed |= rule
        return self._confirmed
