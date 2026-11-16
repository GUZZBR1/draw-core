"""Regra de voto da tinta entre passadas (janela, score, portas)."""

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
