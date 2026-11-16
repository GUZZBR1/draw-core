"""Registro da evidencia na geometria ancora e limites do voto."""

import os
import time

import cv2
import numpy as np

# Registro da evidencia na geometria ancora da geracao (medido
# na regua desta frente, 2026-11-05, draw-lab/parallel-2026-11-05/
# repassada): o acumulador vive numa grade fixa da pagina, mas a
# geometria que retifica cada passada anda — a cadeia rastreador
# + mediana do app sustenta deslocamentos de varios px por
# dezenas de passadas quando um vies persistente (a mao sobre um
# canto) puxa o quad, e ate o tremor de +-1 px entre passadas
# basta. Sem registro, a evidencia entra na grade na posicao em
# que AQUELE quad a projetou: a janela do voto e de 0,75 s e nao
# distingue "tinta nova" de "a mesma tinta re-projetada 2 px ao
# lado" — cada alinhamento confirma a sua copia e a confirmada
# degenera para a uniao de todas as alinhagens, a tinta assentada
# reimpressa camada sobre camada. Na regua (pagina real assentada
# do cache de 2026-11-01, 300 passadas, nenhum conteudo novo):
# geometria congelada confirma 20.137 px e para; tremor de +-1 px
# confirma 45.528 px; deriva lenta de 3 px, 42.930 px; vies de
# canto sustentado, 71.548 px — contra unioes de 47.472/42.711/
# 76.302 px das mascaras das alinhagens: o voto, sob geometria
# movel, e a uniao antiga com outro nome.
# O registro: a primeira passada da geracao fixa a geometria
# ancora; o mapa de cada passada seguinte e re-projetado para a
# grade da ancora (M = A @ C^-1, homografias camera->pagina da
# ancora e da passada) antes do voto. Mover o caderno vira so
# re-registro: o conteudo confirmado nao anda nem duplica
# (registrar uma vez, adaptar por substituicao). O custo e um
# warpPerspective por passada sobre o mapa float, ~ms contra os
# ~168 ms da passada do modelo; geometria igual a da ancora (o
# caso assentado, com o quad congelado) pula o warp.
_REGISTRATION_IDENTITY_TOL = 1e-4


_ECC_REFINE_ENV = "DRAW_ECC_REFINE"


def _ecc_refinement_enabled():
    value = os.environ.get(_ECC_REFINE_ENV, "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _corners_page_matrix(corners, width, height):
    """Homografia camera->pagina de um quad, na grade do mapa.

    Mesma convencao de draw.paper.perspective_matrix (os cantos
    na ordem do rastreador, casando posicionalmente com o destino
    (0,0), (W,0), (W,H), (0,H)), com o destino no tamanho do
    mapa da passada: e nessa grade que ancora e passada
    precisam conversar.
    """
    destination = np.array(
        [(0, 0), (width, 0), (width, height), (0, height)],
        dtype=np.float32,
    )
    source = np.asarray(corners, dtype=np.float32).reshape(4, 2)
    return cv2.getPerspectiveTransform(source, destination)


def _permute_prob(prob, k):
    """A prob como o warp posicional a entrega sob rotacao de k x 90
    graus: rot90 + resize de volta ao canonico nos k impares (a
    forma medida na frente 23 — NAO e o registro com cantos
    rolados, que a frente 24 provou nao reconstruir a evidencia
    entregue: escores 0,005 contra 0,23-0,27 da permutacao)."""
    k %= 4
    if k == 0:
        return prob
    if k == 2:
        return np.rot90(prob, 2).copy()
    rotated = np.rot90(prob, 1 if k == 1 else -1)
    return cv2.resize(
        rotated,
        (prob.shape[1], prob.shape[0]),
        interpolation=cv2.INTER_LINEAR,
    )


def _registration_matrix(anchor_corners, corners, shape):
    """M que leva o mapa desta passada para a grade da ancora.

    Um ponto fisico da pagina tem UMA coordenada na ancora:
    p_ancora = A @ C^-1 @ p_passada, com A e C as homografias
    camera->pagina da ancora e desta passada.
    """
    height, width = shape
    anchor = _corners_page_matrix(anchor_corners, width, height)
    current = _corners_page_matrix(corners, width, height)
    return anchor @ np.linalg.inv(current)


def _registration_is_identity(matrix):
    """True se a matriz nao move pixel nenhum (tol sub-pixel)."""
    return bool(
        np.max(np.abs(matrix - np.eye(3, dtype=np.float64)))
        < _REGISTRATION_IDENTITY_TOL
    )


def _experimental_enabled(name):
    return os.environ.get(name, "0").strip().lower() in ("1", "true", "yes", "on")


# Protocolo inicial F-10: ausência forte, visível e persistente, com
# testemunho positivo da mesma página. Não confundir apagar tudo com virada.
_REMOVAL_LOW_PROB = 0.1
_REMOVAL_PASSES = 6
_REMOVAL_RETAINED_FRACTION = 0.65
# Piso absoluto de testemunho: a fração de 65% veda a remoção quando
# mais de ~35% do canvas confirmado está velho (cópia defasada após
# migração de âncora, contorno de mão confirmado) — os próprios pixels
# errados impedem a testemunha de existir, trava de catch-22 medida no
# sim-hand (retained 0,33%, canvas congelado com folha limpa à vista).
# Um modelo que re-testemunha >= piso px do canvas está comprovadamente
# vendo tinta: a evidência negativa dele é real. O caso que a fração
# protege (saída do modelo escurecendo por inteiro) continua vedado:
# modelo escuro não retém piso nenhum. Os pixels fora de vista seguem
# imunes pela máscara `visible` dentro de `missing`.
_REMOVAL_WITNESS_FLOOR_PX = 4000


# Disciplina de registro (M1, auditoria de 2026-11-10, draw-lab/
# live-audit-2026-11-10/, provas P2/P3a/P3b): o voto de tinta e
# destruido pelo jitter do quad de registro, e o jitter real e
# evento discreto (flip de modo do detector, pouso de salto), nao
# ruido. Duas correcoes aprovadas em replay, ambas atras de flag e
# so sobre o quad que alimenta _registration_matrix (warp do app,
# rastreador e exibicao intocados):
# - DRAW_REG_ANCHOR_MEDIAN3: a ancora da geracao e a mediana por
#   componente dos cantos das _REG_ANCHOR_MEDIAN_SAMPLES primeiras
#   passadas com quad valido (mediana das que houver antes disso),
#   nao a 1a amostra — um quad espurio na passada 0 nao projeta a
#   pagina inteira no quadro errado.
# - DRAW_REG_DEADBAND: o registro usa um quad congelado por geracao
#   enquanto o deslocamento maximo de canto contra ele for
#   < _REG_DEADBAND_TAU_PX; >= tau por _REG_DEADBAND_RELEASE_PASSES
#   passadas seguidas libera (o congelado salta para o quad da
#   passada). Spike de 1 passada nunca libera. tau precisa exceder o
#   diametro do jitter assentado: tau=3 foi medido e reprovado
#   (libera no ruido). EMA/One Euro foram reprovados na P3b (a tinta
#   fica para tras quando a pagina anda de verdade).
_REG_ANCHOR_MEDIAN_ENV = "DRAW_REG_ANCHOR_MEDIAN3"
_REG_ANCHOR_MEDIAN_SAMPLES = 3
_REG_DEADBAND_ENV = "DRAW_REG_DEADBAND"
_REG_DEADBAND_TAU_PX = 10
_REG_DEADBAND_RELEASE_PASSES = 2


def _reg_anchor_median_enabled():
    value = os.environ.get(_REG_ANCHOR_MEDIAN_ENV, "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _reg_deadband_enabled():
    value = os.environ.get(_REG_DEADBAND_ENV, "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _median_anchor(samples):
    """Mediana por componente de uma lista de quads (4, 2)."""
    return np.median(np.stack(samples), axis=0).astype(np.float32)


def _deadband_step(frozen, corners, over):
    """Um passo da banda morta: (quad de registro, congelado, over, liberou, desvio).

    over conta as passadas seguidas com desvio >= tau contra o
    congelado; a liberacao so ocorre na _REG_DEADBAND_RELEASE_PASSES-esima.
    """
    shift = float(np.max(np.linalg.norm(corners - frozen, axis=1)))
    if shift < _REG_DEADBAND_TAU_PX:
        return frozen, frozen, 0, False, shift
    over += 1
    if over >= _REG_DEADBAND_RELEASE_PASSES:
        frozen = corners.copy()
        return frozen, frozen, 0, True, shift
    return frozen, frozen, over, False, shift


# Fonte fixada pelos hashes da pre-inscricao do replay v2.
# fmt: off
def _refine_ink_ecc(reference, observed, hand_mask=None):
    """Refina somente o residuo na grade da ancora; devolve mapa, H e custo."""
    started = time.perf_counter()
    identity = np.eye(3, dtype=np.float64)
    info = {
        "ecc_rejected": False,
        "ecc_converged": False,
        "ecc_mode": "bypass",
    }

    def finish(aligned, matrix):
        info["ecc_ms"] = (time.perf_counter() - started) * 1000.0
        return aligned, matrix, info

    if reference is None or reference.shape != observed.shape:
        return finish(observed, identity)
    ref = np.asarray(reference, dtype=np.float32)
    obs = np.asarray(observed, dtype=np.float32)
    if hand_mask is not None:
        ref = ref.copy()
        obs = obs.copy()
        ref[hand_mask > 0] = 0.0
        obs[hand_mask > 0] = 0.0
    if np.array_equal(ref, obs):
        return finish(obs, identity)
    if (not np.isfinite(ref).all() or not np.isfinite(obs).all()
            or np.count_nonzero(ref > 0.7) < 500
            or np.count_nonzero(obs > 0.7) < 500):
        return finish(obs, identity)
    height, width = obs.shape
    half_size = (width // 2, height // 2)
    if min(half_size) < 2:
        return finish(obs, identity)
    ref_half = cv2.resize(ref, half_size, interpolation=cv2.INTER_AREA)
    obs_half = cv2.resize(obs, half_size, interpolation=cv2.INTER_AREA)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5)
    info["ecc_mode"] = "homography"
    try:
        _, estimated = cv2.findTransformECC(
            ref_half, obs_half, np.eye(3, dtype=np.float32),
            cv2.MOTION_HOMOGRAPHY, criteria, None, 5,
        )
        info["ecc_converged"] = True
    except cv2.error:
        info["ecc_mode"] = "affine"
        try:
            _, affine = cv2.findTransformECC(
                ref_half, obs_half, np.eye(2, 3, dtype=np.float32),
                cv2.MOTION_AFFINE, criteria, None, 5,
            )
            info["ecc_converged"] = True
            estimated = np.vstack((affine, [0.0, 0.0, 1.0]))
        except cv2.error:
            info["ecc_rejected"] = True
            return finish(obs, identity)
    scale = np.diag([half_size[0] / width, half_size[1] / height, 1.0])
    try:
        full = np.linalg.inv(scale) @ estimated @ scale
        align = np.linalg.inv(full)
        if not np.isfinite(align).all() or abs(align[2, 2]) < 1e-12:
            raise ValueError("homografia nao normalizavel")
        align /= align[2, 2]
        corners = np.array(
            [[0, 0, 1], [width, 0, 1], [width, height, 1], [0, height, 1]],
            dtype=np.float64,
        )
        projected = corners @ align.T
        if (not np.isfinite(align).all() or np.linalg.det(align) <= 1e-6
                or np.any(projected[:, 2] <= 1e-6)):
            raise ValueError("homografia degenerada")
        projected = projected[:, :2] / projected[:, 2:]
        # A margem e medida na grade titular 850x1200, inclusive
        # quando ferramentas/testes usam uma pagina reduzida.
        displacement = np.linalg.norm(
            (projected - corners[:, :2]) * [850.0 / width, 1200.0 / height],
            axis=1,
        )
        if not np.isfinite(displacement).all() or displacement.max() > 55.0:
            raise ValueError("residuo fora da margem")
    except (np.linalg.LinAlgError, ValueError):
        info["ecc_rejected"] = True
        return finish(obs, identity)
    aligned = cv2.warpPerspective(
        obs, align, (width, height), flags=cv2.INTER_LINEAR,
        borderValue=0.0,
    )
    return finish(aligned, align)


def _register_ink_probability(prob, anchor, corners, reference, visible=None):
    """Registra na ancora; o refinamento ECC fica opt-in via ambiente."""
    info = {
        "ecc_ms": 0.0,
        "ecc_rejected": False,
        "ecc_converged": False,
        "ecc_mode": "bypass",
    }
    if visible is not None:
        prob = prob.copy()
        prob[~visible] = 0.0
    if anchor is None or corners is None:
        return prob, visible, info
    matrix = _registration_matrix(anchor, corners, prob.shape)
    if not _registration_is_identity(matrix):
        size = (prob.shape[1], prob.shape[0])
        prob = cv2.warpPerspective(
            prob, matrix, size, flags=cv2.INTER_LINEAR, borderValue=0.0,
        )
        if visible is not None:
            visible = cv2.warpPerspective(
                visible.astype(np.uint8), matrix, size,
                flags=cv2.INTER_NEAREST, borderValue=0,
            ) > 0
    hand_mask = None if visible is None else ~visible
    if not _ecc_refinement_enabled():
        info["ecc_mode"] = "disabled"
        return prob, visible, info
    prob, align, info = _refine_ink_ecc(reference, prob, hand_mask)
    if visible is not None and not _registration_is_identity(align):
        visible = cv2.warpPerspective(
            visible.astype(np.uint8), align, (prob.shape[1], prob.shape[0]),
            flags=cv2.INTER_NEAREST, borderValue=0,
        ) > 0
    return prob, visible, info

# fmt: on
