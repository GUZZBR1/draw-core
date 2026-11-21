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
    # mistura pretendida: passou da correção pura (~2,82) rumo ao alvo
    # sem saltar direto a ele (Devin Review PR #140)
    assert first * 64 / 68 < gain < target < first


def test_ceiling_ratio_correction_not_undone_by_smoothing():
    """Devin Review PR #140: alvo travado no teto 3x nos dois níveis
    (p90 60 <-> 65). Convergir para o alvo limitado desfaz a correção
    pela razão e clipa os realces a cada clarão — tem que valer em
    clarão sustentado, não só no primeiro."""
    visible = np.ones((120, 120), dtype=bool)
    dark = np.full((120, 120, 3), 60, np.uint8)
    bright = np.full((120, 120, 3), 65, np.uint8)
    bright[8, 8] = 90
    bright[8, 16] = 91

    smoother = exposure.PaperGainSmoother()
    # Clarões alternados E fases claras sustentadas: em quadro claro
    # repetido não há shift — o caminho normal também tem que preservar.
    sequence = [dark, bright, bright, dark, bright, bright, bright, dark, bright]
    for index, page in enumerate(sequence):
        target = exposure.paper_gain(page, visible)  # 3,0 sempre
        gain = smoother.update(target, index * 0.15, image=page, mask=visible)
        if page is not bright:
            continue
        out = exposure.apply_gain(bright, gain)
        # 65 * (3 / (65/60)) ~= 180: realces 90/91 distintos em TODO clarão
        assert out[8, 8, 0] < out[8, 16, 0] < 255


def test_sustained_shadow_recovers_toward_the_safe_ceiling():
    """Devin Review PR #140: sombra irregular sustentada em cadência
    ~150 ms com o alvo no teto. Rejeitar o passo inteiro congelava o
    ganho na cadência; a bisseção acha o maior passo seguro — o ganho
    converge à borda que cliparia a faixa clara, sem clipá-la."""
    visible = np.ones((120, 120), dtype=bool)
    page = np.full((120, 120, 3), 66, np.uint8)
    page[:, 112:] = 200  # faixa clara do papel: ~7% amostrado, p90 fica 66

    smoother = exposure.PaperGainSmoother()
    smoother.update(1.0, 0.0)  # sem imagem: começa do bypass sem baseline
    target = exposure.paper_gain(page, visible)
    assert target == 3.0

    gains = []
    for index in range(1, 9):
        gains.append(smoother.update(target, index * 0.15, image=page, mask=visible))

    # Congelado em 1,0 a folha sairia ~66; o maior ganho seguro é 255/200.
    assert gains[-1] == pytest.approx(255 / 200, rel=0.02)
    out = exposure.apply_gain(page, gains[-1])
    assert out[0, 112, 0] < 255  # faixa preservada, não clipada
    assert out[0, 40, 0] > 80  # papel escuro subiu: ~84, não ~66


def test_ceiling_clip_guard_measures_the_observation_not_the_retained_gain():
    """Devin Review PR #140: a referência do clip era o ganho retido —
    pixels já saturados viravam isentos e um clarão breve na faixa
    prendia o ganho acima do ponto de clip para sempre. Com a
    observação crua (referência 1x) o ganho desce ao limite seguro e
    volta quando a faixa clareia de novo."""
    visible = np.ones((120, 120), dtype=bool)
    page = np.full((120, 120, 3), 66, np.uint8)
    page[:, 112:] = 199  # faixa ~7% amostrado: p90 fica 66 -> teto

    smoother = exposure.PaperGainSmoother()
    smoother.update(1.0, 0.0)
    target = exposure.paper_gain(page, visible)
    for index in range(1, 6):
        smoother.update(target, index * 0.15, image=page, mask=visible)

    # Clarão breve só na faixa: 199 -> 202 por duas passadas
    flash = page.copy()
    flash[:, 112:] = 202
    for index in range(6, 8):
        smoother.update(target, index * 0.15, image=flash, mask=visible)

    # Faixa de volta a 199: o ganho retorna ao nível que a preserva
    for index in range(8, 14):
        gain = smoother.update(target, index * 0.15, image=page, mask=visible)

    out = exposure.apply_gain(page, gain)
    assert gain == pytest.approx(255 / 199, rel=0.02)
    assert out[0, 112, 0] < 255  # contraste da faixa restaurado


def test_crossing_the_ceiling_keeps_a_consistent_highlight_limit():
    """Devin Review PR #140: a mão cobre a faixa média e o alvo cruza
    o teto (2,985 <-> 3,0) sem esconder a faixa clara — o papel
    inalterado piscava 197 <-> 84 conforme a guarda ligava e desligava.
    Alvos dentro da banda morta do teto são indistinguíveis dele: o
    limite de realce vale dos dois lados e a mesma cena dá a mesma
    saída."""
    page = np.full((480, 800, 3), 66, np.uint8)
    page[:, 560:680] = 67  # ~15% amostrado: p90 = 67 -> alvo ~2,985
    page[:, 680:720] = 60  # faixa escura ~5%
    page[:, 720:760] = 199  # faixa clara ~5% — a mão nunca a cobre
    full = np.ones((480, 800), dtype=bool)
    hand = full.copy()
    hand[:, 560:720] = False  # cobre a faixa média e a escura

    smoother = exposure.PaperGainSmoother()
    gains = []
    for index in range(10):
        mask = hand if index % 2 else full
        target = exposure.paper_gain(page, mask)
        gain = smoother.update(target, index * 0.15, image=page, mask=mask)
        gains.append(gain)

    # convergido: os dois estados de máscara dão a mesma saída
    assert gains[-2] == pytest.approx(gains[-1], rel=0.02)
    for gain in gains[-2:]:  # faixa preservada nos DOIS estados
        out = exposure.apply_gain(page, gain)
        assert out[0, 720, 0] < 255
        assert out[0, 40, 0] > 70  # papel escuro subiu (~84), não cru a 66


def test_first_frame_at_the_ceiling_applies_the_highlight_limit():
    """Devin Review PR #140: o primeiro update aceitava o alvo sem
    verificar clip — com alvo no teto e faixa clara visível, o ganho
    inicial já entra limitado pela observação."""
    visible = np.ones((120, 120), dtype=bool)
    page = np.full((120, 120, 3), 66, np.uint8)
    page[:, 112:] = 199  # faixa ~7%: p90 fica 66 -> teto

    smoother = exposure.PaperGainSmoother()
    target = exposure.paper_gain(page, visible)
    assert target == 3.0
    gain = smoother.update(target, 0.0, image=page, mask=visible)

    assert gain == pytest.approx(255 / 199, rel=0.02)
    out = exposure.apply_gain(page, gain)
    assert out[0, 112, 0] < 255


def test_static_scene_converges_to_the_target():
    """Invariante: cena estática converge à banda morta do alvo em
    poucas passadas — nenhum caminho pode travar o ganho num platô."""
    visible = np.ones((120, 120), dtype=bool)
    page = np.full((120, 120, 3), 100, np.uint8)

    smoother = exposure.PaperGainSmoother()
    smoother.update(1.5, 0.0)  # sem imagem: sem baseline de shift
    gains = [
        smoother.update(2.0, index / 10.0, image=page, mask=visible)
        for index in range(1, 12)
    ]

    assert gains[-1] == pytest.approx(2.0, rel=0.03)  # dentro da banda morta


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

    # ~2,02 de compensação + um passo de convergência ao alvo honesto
    assert first * 80 / 88 <= gain < first < target


def test_p90_crossing_margin_does_not_bias_ratio_correction():
    """Devin Review PR #140: a máscara perde poucas células escuras e a
    margem clara passa de ~9,9% para ~10% do visível — o p90 pula do
    papel para a margem e o alvo enviesado (1,6x) derrubaria o ganho.
    O alvo é confiável só quando o p90 da máscara inteira acompanha a
    razão medida nos compartilhados; enviesado, vale só a razão."""
    page_prev = np.full((200, 320, 3), 80, np.uint8)
    page_prev[:192, 288:] = 120
    page_prev[192:, 288:312] = 120  # 99 células amostradas: 9,9% -> p90=80
    mask_prev = np.ones(page_prev.shape[:2], dtype=bool)

    smoother = exposure.PaperGainSmoother()
    first = smoother.update(
        exposure.paper_gain(page_prev, mask_prev),
        0.0,
        image=page_prev,
        mask=mask_prev,
    )
    assert first == pytest.approx(2.5)

    page_cur = np.full((200, 320, 3), 84, np.uint8)  # exposição +5%
    page_cur[:192, 288:] = 126
    page_cur[192:, 288:312] = 126
    mask_cur = mask_prev.copy()
    mask_cur[:64, :16] = False  # perde 16 células escuras: margem vira ~10%
    target = exposure.paper_gain(page_cur, mask_cur)
    # p90 interpola no corte: ~113 -> alvo enviesado ~1,76 (honesto ~2,38)
    assert target == pytest.approx(200 / 113.4, rel=0.02)

    gain = smoother.update(target, 0.1, image=page_cur, mask=mask_cur)

    assert gain == pytest.approx(first / 1.05, rel=0.01)  # ~2,38
    assert gain > 2.0 > target  # o alvo enviesado derrubaria o ganho


def test_capped_target_recovers_toward_ceiling_under_stationary_occlusion():
    """Devin Review PR #140: alvo preso no teto + oclusão parada +
    jitter de exposição seguido. Corrigir e retornar cedo a cada quadro
    deixa o papel ~130 para sempre; a correção pela razão tem que
    convergir para o teto de novo."""
    margin = np.full((120, 120, 3), 60, np.uint8)
    margin[:, 100:] = 90
    full = np.ones((120, 120), dtype=bool)
    hand = full.copy()
    hand[:, 100:] = False

    smoother = exposure.PaperGainSmoother()
    first = smoother.update(
        exposure.paper_gain(margin, full), 0.0, image=margin, mask=full
    )
    gains = [first]
    for index, level in enumerate([62, 64, 62, 64, 62, 64, 62, 64, 62, 64]):
        page = np.full((120, 120, 3), level, np.uint8)
        target = exposure.paper_gain(page, hand)  # 3,0 em todos
        gains.append(smoother.update(target, (index + 1) / 10.0, image=page, mask=hand))

    # no nível compensado (~2,1) o papel sai ~130; a recuperação tem
    # que passar bem disso rumo ao teto
    assert gains[-1] > 2.6


def test_leaving_unity_bypass_does_not_clip_paper_highlights():
    """Devin Review PR #140: p90 oscilando 204 -> 198 ao sair do bypass
    1,0. A correção pela razão restauraria 204 de brilho corrigido —
    acima do alvo — e cliparia os realces que o alvo preserva. Com a
    máscara estável a correção é limitada pelo alvo."""
    visible = np.ones((120, 90), dtype=bool)
    bright = np.full((120, 90, 3), 204, np.uint8)
    darker = np.full((120, 90, 3), 198, np.uint8)
    darker[8, 8] = 250
    darker[8, 16] = 252

    smoother = exposure.PaperGainSmoother()
    assert smoother.update(1.0, 0.0, image=bright, mask=visible) == 1.0

    gain = smoother.update(200 / 198, 0.1, image=darker, mask=visible)
    out = exposure.apply_gain(darker, gain)
    assert out[8, 8, 0] < out[8, 16, 0] < 255  # 253 < 255, não 255 = 255


def test_exposure_shift_correction_converges_during_stationary_occlusion():
    """Devin Review PR #140: mão parada sobre a margem e jitter de
    exposição seguido. Cada quadro dispara o detector, mas o resíduo
    tem que convergir ao alvo — não ficar preso no nível compensado."""
    margin = np.full((120, 120, 3), 80, np.uint8)
    margin[:, 100:] = 90
    full = np.ones((120, 120), dtype=bool)
    hand = full.copy()
    hand[:, 100:] = False

    smoother = exposure.PaperGainSmoother()
    first = smoother.update(
        exposure.paper_gain(margin, full), 0.0, image=margin, mask=full
    )
    gains = [first]
    for index, level in enumerate([88, 90, 88, 90, 88, 90, 88]):
        page = np.full((120, 120, 3), level, np.uint8)
        target = exposure.paper_gain(page, hand)  # ~2,27 / ~2,22
        gains.append(smoother.update(target, (index + 1) / 10.0, image=page, mask=hand))

    assert gains[1] < first  # compensação inicial na direção certa
    assert gains[-1] > 2.1  # convergiu ao alvo, não travou em ~2,0


def test_exposure_shift_correction_converges_with_border_jitter():
    """Devin Review PR #140: a borda da máscara oscila uma célula
    amostrada por quadro (quad/seg/mão reais) — a estabilidade usa
    tolerância, e o resíduo segue convergindo ao alvo."""
    margin = np.full((120, 120, 3), 80, np.uint8)
    margin[:, 100:] = 90
    full = np.ones((120, 120), dtype=bool)
    hand = full.copy()
    hand[:, 100:] = False

    smoother = exposure.PaperGainSmoother()
    first = smoother.update(
        exposure.paper_gain(margin, full), 0.0, image=margin, mask=full
    )
    gains = [first]
    for index, level in enumerate([88, 90, 88, 90, 88, 90, 88]):
        mask = hand.copy()
        if index % 2:
            mask[40:48, 96:104] = False  # 1 célula amostrada a mais de mão
        page = np.full((120, 120, 3), level, np.uint8)
        target = exposure.paper_gain(page, mask)
        gains.append(smoother.update(target, (index + 1) / 10.0, image=page, mask=mask))

    assert gains[1] < first
    assert gains[-1] > 2.1  # borda tremendo não trava a convergência


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
