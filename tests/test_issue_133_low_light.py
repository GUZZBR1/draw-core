"""Replay sintético para estabilidade de tinta em baixa luz (#133)."""

import numpy as np
import pytest

from draw import exposure
from draw.ink.accumulator import LayeredInkAccumulator
from draw.ink.config import InkConfig

H, W = 80, 120
SHADOW = (slice(10, 28), slice(40, 80))
STROKE = (slice(40, 44), slice(20, 90))
STROKE_ANCHOR = (slice(40, 44), slice(20, 25))
HAND_MARGIN = (slice(8, 72), slice(104, 120))
# ~13% da folha num brilho acima do gradiente: o p90 mora aqui (duas
# colunas do passo de 8), então o jitter desta faixa é jitter da
# ESTIMATIVA — a cena física (sombra, traço) não muda com ele.
GLINT = (slice(0, H), slice(88, 104))
DELTAS = (0, 1, -1, 1, 0, -1, 0)
GLINT_LEVELS = (80, 85, 77, 84, 78, 83, 80)


def _low_light_page(delta, glint, hand_at_margin):
    gradient = np.linspace(42, 76, W, dtype=np.float32)
    page = np.repeat(gradient[None, :], H, axis=0)
    page = np.repeat(page[..., None], 3, axis=2)
    page[SHADOW] -= 10.0
    page[STROKE] = 28.0
    if glint is not None:
        page[GLINT] = float(glint)
    if hand_at_margin:
        page[HAND_MARGIN] = 235.0
    return np.clip(page + delta, 0, 255).astype(np.uint8)


def _ink_prob(ink_input, reference):
    """Proxy determinístico do page-clean sobre os pixels efetivamente
    entregues à inferência (a LUT do ganho já entrou). A sombra responde
    mais à variação de brilho que o traço, cuja crista ancora a camada."""
    prob = np.zeros((H, W), dtype=np.float32)
    prob[SHADOW] = np.clip(
        0.84 + (float(ink_input[SHADOW].mean()) - reference[0]) * 0.02, 0, 1
    )
    prob[STROKE] = np.clip(
        0.75 + (reference[1] - float(ink_input[STROKE].mean())) * 0.01, 0, 1
    )
    prob[STROKE_ANCHOR] = 0.96
    return prob


@pytest.mark.parametrize("hand_at_margin", [False, True])
def test_low_light_shadow_replay_keeps_weak_stroke_without_shadow_flicker(
    hand_at_margin,
):
    smoother = exposure.PaperGainSmoother()
    accumulator = LayeredInkAccumulator(config=InkConfig.production())
    raw_accumulator = LayeredInkAccumulator(config=InkConfig.production())
    visible = np.ones((H, W), dtype=bool)
    if hand_at_margin:
        visible[HAND_MARGIN] = False

    target_gains = []
    stable_gains = []
    outputs = []
    raw_outputs = []
    smooth_shadow_levels = []
    raw_shadow_levels = []
    smooth_ref = raw_ref = None
    # Pequena oscilação temporal de exposição sobre gradiente e sombra
    # fixos; a faixa de brilho perturba o p90 sem mover a mediana, e a
    # mão branca ocupa a margem sem participar do p90.
    for index, (delta, glint) in enumerate(zip(DELTAS, GLINT_LEVELS, strict=True)):
        page = _low_light_page(delta, glint, hand_at_margin)
        target = exposure.paper_gain(page, visible)
        gain = smoother.update(target, index / 10.0, image=page, mask=visible)
        target_gains.append(target)
        stable_gains.append(gain)

        smooth_input = exposure.apply_gain(page, gain)
        raw_input = exposure.apply_gain(page, target)  # baseline sem suavizar
        smooth_shadow_levels.append(float(smooth_input[SHADOW].mean()))
        raw_shadow_levels.append(float(raw_input[SHADOW].mean()))
        if smooth_ref is None:
            smooth_ref = (
                float(smooth_input[SHADOW].mean()),
                float(smooth_input[STROKE].mean()),
            )
            raw_ref = (
                float(raw_input[SHADOW].mean()),
                float(raw_input[STROKE].mean()),
            )
        outputs.append(accumulator.add(_ink_prob(smooth_input, smooth_ref), visible))
        raw_outputs.append(raw_accumulator.add(_ink_prob(raw_input, raw_ref), visible))

    assert max(stable_gains) - min(stable_gains) < max(target_gains) - min(target_gains)
    for output in outputs:
        assert not output["confirmed"][SHADOW].any()
        assert not output["provisional"][SHADOW].any()
    # Baseline sem suavização: o jitter do p90 vira jitter de LUT e a
    # sombra pisca como tinta provisória — o flicker do issue #133. O
    # ganho suavizado zera esse evento (verificado acima, quadro a quadro).
    raw_shadow_frames = sum(
        1 for output in raw_outputs if output["provisional"][SHADOW].any()
    )
    assert raw_shadow_frames > 0
    assert max(smooth_shadow_levels) - min(smooth_shadow_levels) <= (
        max(raw_shadow_levels) - min(raw_shadow_levels)
    )
    assert outputs[0]["provisional"][STROKE].all()
    assert outputs[2]["confirmed"][STROKE].all()
    if hand_at_margin:
        assert not outputs[-1]["confirmed"][HAND_MARGIN].any()
        assert not outputs[-1]["provisional"][HAND_MARGIN].any()


def test_global_exposure_jitter_does_not_worsen_shadow_input_variation():
    """A variação global do sensor aparece igualmente na mediana e no p90.
    Nesse caso o alvo fresco já compensa a mudança e o deadband não deve
    aumentar a oscilação da sombra em relação ao ganho sem suavizar."""
    smoother = exposure.PaperGainSmoother()
    smooth_shadow, raw_shadow = [], []
    visible = np.ones((H, W), dtype=bool)

    for index, delta in enumerate(DELTAS):
        page = _low_light_page(delta, None, False)
        target = exposure.paper_gain(page, visible)
        gain = smoother.update(target, index / 10.0, image=page, mask=visible)
        smooth_input = exposure.apply_gain(page, gain)
        raw_input = exposure.apply_gain(page, target)
        smooth_shadow.append(float(smooth_input[SHADOW].mean()))
        raw_shadow.append(float(raw_input[SHADOW].mean()))

    smooth_range = max(smooth_shadow) - min(smooth_shadow)
    raw_range = max(raw_shadow) - min(raw_shadow)
    assert smooth_range <= raw_range + 0.1


def test_moving_hand_mask_does_not_bypass_deadband_as_exposure_shift():
    """Devin Review PR #140: a mão cobrindo a margem clara muda a
    mediana e o p90 da amostra JUNTOS — medido só sobre a máscara do
    quadro, parecia mudança global de exposição e o bypass furava a
    banda morta, fazendo a sombra intacta piscar. A estatística sobre
    os pixels visíveis nos dois quadros vê que a cena não mudou."""
    page = np.tile(
        np.linspace(60, 100, 800, dtype=np.float32)[None, :, None], (480, 1, 3)
    ).astype(np.uint8)
    full = np.ones((480, 800), dtype=bool)
    hand = full.copy()
    hand[96:288, 608:800] = False  # ~6% da margem clara sob a mão

    smoother = exposure.PaperGainSmoother()
    gains = []
    for index in range(7):
        mask = hand if index % 2 else full
        target = exposure.paper_gain(page, mask)
        gains.append(smoother.update(target, index / 10.0, image=page, mask=mask))

    # O alvo alterna 2,103 <-> 2,151 dentro da banda morta: sem o bypass
    # falso de exposição o ganho retido nunca sai do lugar.
    assert gains == [gains[0]] * len(gains)
