"""Identidade de pagina: dilatacao, recall e oclusao."""

from . import votes

# Virada (U3): canvas com pelo menos _INK_TURN_MIN_CANVAS_PX e a
# mascara da passada cobrindo <= _INK_TURN_MAX_OVERLAP dele por
# _INK_TURN_PASSES passadas seguidas = pagina trocada (conteudo
# descorrelacionado). Apagar um trecho a mao nao derruba a
# cobertura da pagina inteira a <=30%: o apagado continua no canvas
# e o resto do desenho segue coberto pela mascara.
_INK_TURN_MIN_CANVAS_PX = 2000


_INK_TURN_MAX_OVERLAP = 0.30


_INK_TURN_PASSES = 2


# Ao retomar apos um drop do tracker, a primeira mascara e registrada
# na grade antiga e precisa reencontrar a maior parte da tinta existente.
# Evidencia nova pode acrescentar tracos, mas uma pagina diferente nao
# deve herdar o canvas anterior.
_PAGE_IDENTITY_MIN_RECALL = 0.65
# Guarda dual da identidade: alem do recall da tinta antiga, a
# tinta da passada tem de cair sobre o canvas anterior (mesma
# tolerancia dilatada). O limiar e menor que o do recall porque a
# tinta nova desenhada durante o drop e legitima: medido na regua
# (2026-11-06), mesma pagina com +75% de tinta nova da
# containment 0,65 e perderia o canvas; com 0,5 aceita ~1,8x de
# crescimento. Pagina diferente mede 0,23-0,25 (sintetica), margem
# de 2x contra falso positivo.
_PAGE_IDENTITY_MIN_CONTAINMENT = 0.5
# Maximo de passadas adiadas por recuperacao, somando ECC e oclusao.
_PAGE_IDENTITY_MAX_DEFERRALS = 5
# Troca de pagina exige esta janela de vereditos limpos consecutivos.
_PAGE_IDENTITY_SWITCH_CONSENSUS_FRAMES = 3
# O canvas confirmado inclui o halo da fronteira, que uma passada
# sozinha nunca cobre no limiar do voto: a comparacao dilata os
# dois lados pela mesma tolerancia do comparador da regua.
_IDENTITY_DILATION_KERNEL = 2 * votes._INK_FRONTIER_RADIUS + 1


# Oclusao na decisao de identidade: o recall so julga a tinta
# anterior que a passada consegue VER (a mao sobre a pagina nao e
# evidencia de pagina nova). Abaixo deste minimo de tinta anterior
# visivel, a decisao e ADIADA para a proxima passada em vez de
# sair no chute com a pagina coberta.
_IDENTITY_MIN_VISIBLE_FRACTION = 0.25
_IDENTITY_MIN_VISIBLE_PX = 32

# Fechamento de same_page sob oclusao: o piso acima so habilita a
# avaliacao. Para CONSUMIR a referencia num same_page, metade da
# caligrafia anterior precisa estar a vista — um fragmento
# correspondente numa folha substituta herdaria o desenho inteiro
# antes da mao sair.
_IDENTITY_SAME_PAGE_VISIBLE_FRACTION = 0.5

# Julgamento de virada sob oclusao: a cobertura e medida sobre a
# tinta confirmada VISIVEL; com menos que isto de tinta visivel, a
# passada se abstem — nem avanca nem zera a sequencia de virada.
_OCCLUSION_TURN_MIN_VISIBLE_PX = 200
