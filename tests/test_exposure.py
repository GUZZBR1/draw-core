"""Ganho digital da página (draw.exposure)."""

import time

import numpy as np
import pytest

from draw import exposure


def _page(paper, ink=20, shape=(120, 90)):
    img = np.full((*shape, 3), paper, np.uint8)
    img[40:50, 10:80] = ink
    return img


def test_dark_page_is_lifted_to_target():
    out, gain = exposure.apply_paper_gain(_page(80))
    assert gain == pytest.approx(200 / 80)
    assert float(np.percentile(out, 90)) == pytest.approx(200, abs=1)


def test_bright_page_passes_untouched():
    page = _page(230)
    out, gain = exposure.apply_paper_gain(page)
    assert gain == 1.0
    assert out is page  # nem cópia: cena bem exposta não muda


def test_gain_is_capped_for_near_black_frames():
    out, gain = exposure.apply_paper_gain(_page(10, ink=2))
    assert gain == exposure._MAX_GAIN
    assert out.max() <= 30


def test_gain_preserves_level_order():
    page = _page(90, ink=30)
    out, _ = exposure.apply_paper_gain(page)
    assert out[45, 20, 0] < out[5, 5, 0]
    assert out.dtype == np.uint8 and out.shape == page.shape


def test_temporal_gain_suppresses_small_jitter_and_tracks_real_exposure_change():
    smoother = exposure.PaperGainSmoother()
    values = [smoother.update(2.5, 0.0)]
    for index, target in enumerate((2.55, 2.45, 2.54, 2.46, 2.5), start=1):
        values.append(smoother.update(target, index * 0.1))

    assert max(values) - min(values) == 0.0

    for index in range(1, 41):
        gain = smoother.update(1.5, 0.5 + index * 0.1)
    assert 1.5 <= gain <= 1.55

    smoother.reset()
    assert smoother.update(1.35, 10.0) == pytest.approx(1.35)


def test_unity_gain_clears_a_previous_boost_without_clipping_bright_strokes():
    smoother = exposure.PaperGainSmoother()
    smoother.update(1.0256, 0.0)

    gain = smoother.update(1.0, 0.1)
    bright_paper = np.array([[[254, 254, 254], [251, 251, 251]]], np.uint8)
    out = exposure.apply_gain(bright_paper, gain)

    assert gain == 1.0
    np.testing.assert_array_equal(out, bright_paper)


def test_deadband_releases_a_decrease_that_clips_paper_pixels():
    """Devin Review PR #140: p90 194→199 mantém o alvo (1,005) dentro da
    banda morta sobre o ganho retido (1,031) — mas o resíduo clipa a faixa
    clara junto do traço fraco, então o decréscimo fura a banda."""
    brighter = _page(199, ink=248)
    brighter[20:60, 20:70] = 252  # faixa clara: 1,031 satura, 1,005 preserva

    smoother = exposure.PaperGainSmoother()
    first = smoother.update(200 / 194, 0.0)
    held = smoother.update(200 / 199, 0.1)  # sem imagem a banda segura
    assert held == first

    gain = smoother.update(200 / 199, 0.2, image=brighter)
    assert gain < first  # o decréscimo saiu da banda morta

    for index in range(3, 15):
        gain = smoother.update(200 / 199, index * 0.1, image=brighter)
    out = exposure.apply_gain(brighter, gain)
    assert out[30, 30, 0] < 255  # faixa clara recupera nível próprio
    assert out[30, 30, 0] > out[45, 15, 0]  # e segue acima do traço


def test_deadband_clip_release_checks_each_color_channel():
    smoother = exposure.PaperGainSmoother()
    first = smoother.update(200 / 194, 0.0)
    page = np.full((120, 90, 3), 199, np.uint8)
    page[20:60, 20:70] = (250, 100, 100)

    gain = smoother.update(200 / 199, 0.1, image=page)

    assert gain < first  # vermelho clippa mesmo com brilho médio abaixo da banda


def test_masked_clip_release_counts_pixels_not_channels():
    """Devin Review PR #140: com máscara o sample vira (N, 3) — um canal
    saturando deve contar o pixel inteiro, não 1/3 dele. O pipeline
    sempre passa gain_mask, então o caminho mascarado é o real."""
    smoother = exposure.PaperGainSmoother()
    first = smoother.update(200 / 194, 0.0)
    page = np.full((500, 500, 3), 199, np.uint8)
    page[8, 8] = (250, 100, 100)  # 1 pixel amostrado, 1 canal no limiar
    visible = np.full(page.shape[:2], 255, np.uint8)

    gain = smoother.update(200 / 199, 0.1, image=page, mask=visible)

    # 1/3969 pixels saturando > 1e-4 (conta por canal daria 1/11907 < 1e-4)
    assert gain < first


def test_global_exposure_shift_detected_at_gain_ceiling():
    """Devin Review PR #140: o p90 sai da amostra, não do alvo clipado.
    Saindo do teto _MAX_GAIN (p90 64 -> 68), mediana e p90 acompanham
    a mudança real de ~6% e a correção pela razão sai do teto na hora."""
    visible = np.ones((120, 90), dtype=bool)
    dark = np.full((120, 90, 3), 64, np.uint8)
    brighter = np.full((120, 90, 3), 68, np.uint8)

    smoother = exposure.PaperGainSmoother()
    first = smoother.update(
        exposure.paper_gain(dark, visible), 0.0, image=dark, mask=visible
    )
    assert first == 3.0  # 200/64 = 3,125 clipa no teto

    target = exposure.paper_gain(brighter, visible)
    gain = smoother.update(target, 0.1, image=brighter, mask=visible)
    assert gain == pytest.approx(first * 64 / 68)  # razão medida, ~2,82
    assert gain < target < first  # corrige sem saltar direto ao alvo


def test_exposure_shift_correction_uses_shared_ratio_over_new_mask_target():
    """Devin Review PR #140: papel clareando e mão cobrindo a margem
    clara no mesmo quadro. O alvo da máscara nova SOBE (o p90 perdeu os
    pixels claros), mas a exposição subiu — a correção usa a razão dos
    pixels compartilhados e o ganho desce."""
    margin = np.full((120, 120, 3), 80, np.uint8)
    margin[:, 100:] = 90  # margem clara: p90 = 90, alvo ~2,222
    full = np.ones((120, 120), dtype=bool)
    hand = full.copy()
    hand[:, 100:] = False

    smoother = exposure.PaperGainSmoother()
    first = smoother.update(
        exposure.paper_gain(margin, full), 0.0, image=margin, mask=full
    )
    assert first == pytest.approx(200 / 90)

    occluded = np.full((120, 120, 3), 88, np.uint8)  # papel clareou 10%
    target = exposure.paper_gain(occluded, hand)  # ~2,273: subiu
    gain = smoother.update(target, 0.1, image=occluded, mask=hand)

    assert gain == pytest.approx(first * 80 / 88)  # ~2,02: compensação
    assert gain < first < target


def _dark_paper_with_bright_desk(desk_fraction=0.14, shape=(1200, 850)):
    h, w = shape
    img = np.full((h, w, 3), 80, np.uint8)
    desk_rows = int(h * desk_fraction)
    img[:desk_rows] = 225  # mesa clara no topo do crop
    paper = np.ones((h, w), bool)
    paper[:desk_rows] = False
    return img, paper


def test_bright_desk_does_not_cancel_the_paper_gain():
    """Review #52: com >10% de mesa clara no crop o p90 da imagem inteira
    virava ~225 e o ganho 1,0, deixando o papel escuro como estava."""
    img, paper = _dark_paper_with_bright_desk()
    assert exposure.paper_gain(img) == 1.0  # sem máscara, a mesa vence
    assert exposure.paper_gain(img, paper) == pytest.approx(200 / 80, rel=0.01)
    out, gain = exposure.apply_paper_gain(img, paper)
    assert gain == pytest.approx(2.5, rel=0.01)
    assert out[800, 400, 0] == pytest.approx(200, abs=2)


def test_empty_mask_falls_back_to_the_whole_image():
    img = np.full((120, 90, 3), 80, np.uint8)
    nothing = np.zeros((120, 90), bool)
    assert exposure.paper_gain(img, nothing) == pytest.approx(2.5, rel=0.01)


def test_lut_gain_matches_the_naive_per_pixel_result():
    rng = np.random.default_rng(1)
    img = np.clip(rng.normal(90, 30, (240, 200, 3)), 0, 255).astype(np.uint8)
    out, gain = exposure.apply_paper_gain(img)
    naive = np.clip(img.astype(np.float32) * gain, 0, 255).astype(np.uint8)
    np.testing.assert_array_equal(out, naive)


@pytest.mark.slow
def test_gain_is_much_cheaper_than_the_naive_full_frame_version():
    """Roda no laço de UI (33 ms a 30 fps): medido ~24 ms ingênuo contra
    ~1 ms agora. Compara com a versão ingênua na MESMA máquina."""
    rng = np.random.default_rng(2)
    img = np.clip(rng.normal(80, 12, (1200, 850, 3)), 0, 255).astype(np.uint8)

    def naive():
        gray = img.mean(axis=2)
        gain = float(np.clip(200.0 / np.percentile(gray, 90), 1.0, 3.0))
        return np.clip(img.astype(np.float32) * gain, 0, 255).astype(np.uint8)

    def best(fn, runs=7):
        times = []
        for _ in range(runs):
            t0 = time.perf_counter()
            fn()
            times.append(time.perf_counter() - t0)
        return min(times)

    assert best(lambda: exposure.apply_paper_gain(img)) < 0.35 * best(naive)


@pytest.mark.parametrize("period", [24, 28, 32, 40])
def test_sparse_estimate_tracks_the_full_resolution_gain_on_ruled_pages(period):
    """Review #52: o percentil sai de uma amostra com passo fixo de 8; em
    pauta de período múltiplo do passo, a amostra poderia cair sempre na
    linha (ou sempre fora dela). Compara com o p90 de resolução cheia em
    todos os deslocamentos da pauta."""
    h, w = 600, 420
    img = np.empty((h, w, 3), np.uint8)
    pos = 0.9 * (h * w - 1)
    lo_rank = int(np.floor(pos)) + 1
    hi_rank = int(np.ceil(pos)) + 1
    frac = pos - np.floor(pos)
    for paper in (80, 110):
        for offset in range(period):
            img.fill(paper)
            for y in range(offset, h, period):
                img[y : y + 2] = 25  # linha de pauta escura de 2 px
            img[200:260, 100:300] = 30  # uma mancha de tinta
            cdf = np.cumsum(np.bincount(img[:, :, 0].ravel(), minlength=256))
            lo_idx = int(np.searchsorted(cdf, lo_rank))
            hi_idx = int(np.searchsorted(cdf, hi_rank))
            p90 = lo_idx + frac * (hi_idx - lo_idx)
            full = float(np.clip(200.0 / p90, 1.0, 3.0))
            sampled = exposure.paper_gain(img)
            assert sampled == pytest.approx(full, rel=0.02), (period, offset, paper)
