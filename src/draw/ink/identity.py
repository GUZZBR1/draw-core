"""Identidade de pagina: dilatacao, chamfer, vigia, oclusao."""

import os

import cv2
import numpy as np

from . import registration, votes

# Virada (U3): canvas com pelo menos _INK_TURN_MIN_CANVAS_PX e a
# mascara da passada cobrindo <= _INK_TURN_MAX_OVERLAP dele por
# _INK_TURN_PASSES passadas seguidas = pagina trocada (conteudo
# descorrelacionado). Apagar um trecho a mao nao derruba a
# cobertura da pagina inteira a <=30%: o apagado continua no canvas
# e o resto do desenho segue coberto pela mascara.
_INK_TURN_MIN_CANVAS_PX = 2000


_INK_TURN_MAX_OVERLAP = 0.30


_INK_TURN_PASSES = 2


# HOTFIX 2026-11-01 (draw-lab/page-turn-falsefire-2026-11-01): o
# gatilho de cobertura acima foi REPROVADO no teste ao vivo. Na
# mesa real, o ajuste da folha do caderno aberto oscila (o proprio
# codigo registra oscilacao de ate 314 px nos cantos): o warp
# balanca, a saida do modelo desencontra do canvas acumulado e a
# cobertura desaba SEM pagina nenhuma virar — o evento disparava
# a cada 2-5 s, salvando snapshot e zerando o canvas sem parar.
# A prova offline usou warps estaticos com tremor de +-1-3 px,
# mansos demais pra expor isso; o teste negativo era borracha,
# nao balanco de geometria. Decisao: o disparo automatico por
# cobertura fica DESLIGADO por padrao, atras da flag
# DRAW_PAGE_TURN_EVENT=1, ate existir um gatilho provado contra
# serie de balanco de geometria realista. O codigo do evento e o
# snapshot ficam intactos (versao estrita futura); com a flag
# desligada, nenhum colapso de cobertura zera o canvas — a troca
# de pagina segue pelo caminho pre-existente de drop/reaparicao
# da folha, que abre geracao nova do mesmo jeito.
_ENV_TURN_EVENT_VAR = "DRAW_PAGE_TURN_EVENT"


def _page_turn_event_enabled():
    """True so com DRAW_PAGE_TURN_EVENT=1 (ver o hotfix acima)."""
    return os.environ.get(_ENV_TURN_EVENT_VAR, "").strip() == "1"


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


_IDENTITY_CHAMFER_ENV = "DRAW_IDENTITY_CHAMFER"
_IDENTITY_CHAMFER_RADII = (2, 4, 8, 16)


def _identity_chamfer_enabled():
    value = os.environ.get(_IDENTITY_CHAMFER_ENV, "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _identity_chamfer_fields(seen, reference, decision, ecc_info):
    """Diagnostico apenas: distancias euclidianas na grade da ancora."""
    fields = {
        "ecc_refine_enabled": int(registration._ecc_refinement_enabled()),
        "shadow_decision": "defer" if ecc_info.get("ecc_rejected") else decision,
    }
    for direction, source, target in (
        ("seen_to_reference", seen, reference),
        ("reference_to_seen", reference, seen),
    ):
        distances = None
        if (
            source is not None
            and target is not None
            and np.any(source)
            and np.any(target)
        ):
            distance_map = cv2.distanceTransform(
                (~target).astype(np.uint8),
                cv2.DIST_L2,
                cv2.DIST_MASK_PRECISE,
            )
            distances = distance_map[source]
        prefix = f"chamfer_{direction}"
        fields[f"{prefix}_median_px"] = (
            None if distances is None else float(np.median(distances))
        )
        for radius in _IDENTITY_CHAMFER_RADII:
            fields[f"{prefix}_coverage_{radius}px"] = (
                float(np.mean(distances <= radius))
                if distances is not None
                else 0.0
                if (source is not None and np.any(source) and target is not None)
                else None
            )
    return fields


# Oclusao na decisao de identidade: o recall so julga a tinta
# anterior que a passada consegue VER (a mao sobre a pagina nao e
# evidencia de pagina nova). Abaixo deste minimo de tinta anterior
# visivel, a decisao e ADIADA para a proxima passada em vez de
# sair no chute com a pagina coberta.
_IDENTITY_MIN_VISIBLE_FRACTION = 0.25
_IDENTITY_MIN_VISIBLE_PX = 32

# Julgamento de virada sob oclusao: a cobertura e medida sobre a
# tinta confirmada VISIVEL; com menos que isto de tinta visivel, a
# passada se abstem — nem avanca nem zera a sequencia de virada.
_OCCLUSION_TURN_MIN_VISIBLE_PX = 200

# Vigia de identidade no meio da geracao (frente 28, 2026-11-10):
# a fronteira de geracao existente so julga a identidade na VOLTA
# da folha (drop -> new_generation(preserve_identity=True)). Com a
# folha sempre presente, virar a pagina somava as duas no mesmo
# canvas — medido ao vivo: decisao de identidade None em 53/53
# passadas, 87% do canvas confirmado depois da troca. A vigia NAO
# decide nada: ela ARMA o juiz de identidade existente no meio da
# geracao, com a referencia = o canvas confirmado ate aqui. Quem
# decide e o juiz (recall/containment dilatados, consenso de 3,
# adiamento por oclusao/ECC, quarentena) — o gatilho cru de
# cobertura do U3 foi reprovado ao vivo em 2026-11-01 justamente
# por decidir sozinho sob balanco de geometria; aqui o balanco
# nem arma (a vigia exige geometria quieta) e quem arma ainda
# passa pelo juiz. Dois chamadores: (a) salto grande de pose
# confirmado pelo tracker, sinalizado pelo app via
# arm_identity_check("pose_jump"); (b) ruptura de conteudo: o
# recall dilatado do canvas na passada registrada <=
# _IDENTITY_WATCH_MAX_RECALL por _IDENTITY_WATCH_PASSES passadas
# seguidas com massa de tinta nova >= _IDENTITY_WATCH_MIN_SEEN_PX
# e deslocamento da ancora <= _IDENTITY_WATCH_MAX_DISPLACEMENT_PX.
# Virada para pagina em branco nao arma (sem massa nova nao ha o
# que somar; quando a escrita comeca na pagina nova, a vigia
# dispara). Atras de DRAW_IDENTITY_WATCH=1, desligado por padrao.
_ENV_IDENTITY_WATCH_VAR = "DRAW_IDENTITY_WATCH"
_IDENTITY_WATCH_MIN_CANVAS_PX = 2000
_IDENTITY_WATCH_MIN_SEEN_PX = 200
_IDENTITY_WATCH_MAX_RECALL = 0.30
_IDENTITY_WATCH_PASSES = 2
# Portoes de geometria da vigia — v3 (frente 32, 2026-11-10): a v1
# exigia deslocamento da ancora <= 8 px e isso (i) bloqueou as
# passadas da virada real (9,53 px, a perturbacao da propria
# virada) e (ii) cegava a vigia sob deriva. A v3 conta a passada
# quando a geometria esta ASSENTADA (degrau entre quads
# consecutivos <= _IDENTITY_WATCH_MAX_STEP_PX, a definicao da
# arbitragem) E o deslocamento acumulado da ancora segue <=
# _IDENTITY_WATCH_MAX_DISPLACEMENT_PX (trava de deriva lenta: a
# era de posicionamento que se condenou sozinha estava a >= 25 px;
# a virada precisa de >= 9,53 — margens de ~1,7x dos dois lados,
# amarradas ao material gravado). E o armamento por ruptura
# SEMEIA 1 voto de troca no juiz: as 2 passadas da vigia medem
# recall <= 0,30 — evidencia mais estrita em recall que 1 voto
# do juiz (< 0,65); o juiz segue decidindo com o consenso dele.
_IDENTITY_WATCH_MAX_DISPLACEMENT_PX = 16.0
_IDENTITY_WATCH_MAX_STEP_PX = 6.0
_IDENTITY_WATCH_SEED_VOTES = 1


def _identity_watch_enabled():
    """True so com DRAW_IDENTITY_WATCH=1 (ver o desenho acima)."""
    return os.environ.get(_ENV_IDENTITY_WATCH_VAR, "").strip() == "1"
