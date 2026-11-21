"""PageModel: a referencia persistente da pagina limpa.

O mecanismo classico de captura por camera fixa (classificar cada
pixel contra uma imagem de fundo mantida no tempo) respondendo as
cinco falhas da fila de robustez de 2026-11-21:

- regiao nunca vista limpa fica pendente e nao entrega evidencia
  (a extensao do "quem nao ve, se abstem" para a vida da geracao);
- o que estava na pagina quando o pixel foi visto pela primeira
  vez semeia a referencia — conteudo antigo, pauta e vinco nunca
  viram tinta nova (a semantica do baseline do #130);
- a referencia rastreia devagar onde ha papel — deriva de
  iluminacao (#133) afunda nela, nao no voto;
- traco nunca afunda na referencia — a mascara `paper` o exclui,
  e so o que ESCURECEU contra a referencia e conteudo novo, entao
  borracha nunca le como tinta.
"""

import threading
import time

import numpy as np
import pytest

from draw.contracts import WarpedPage
from draw.ink import identity as identity_mod
from draw.ink import page_model as pm_mod
from draw.ink import worker as worker_mod
from draw.ink.config import InkConfig

H, W = 96, 128
PAPER = 235.0
INK = 40.0


def _paper(shape=(H, W)):
    return np.full(shape, PAPER, dtype=np.float32)


def test_pending_until_confirm_observations():
    model = pm_mod.PageModel((H, W), confirm_obs=3)
    gray = _paper()
    for _ in range(2):
        model.observe(gray)
    assert np.count_nonzero(model.seeded) == 0
    assert np.count_nonzero(model.admissible()) == 0
    model.observe(gray)
    assert np.all(model.seeded)
    assert np.all(model.admissible())


def test_occluded_block_never_seeds_and_revealed_content_is_not_novel():
    model = pm_mod.PageModel((H, W), confirm_obs=2)
    gray = _paper()
    gray[32:64, 32:64] = INK  # desenho antigo sob a mao
    covered = np.ones((H, W), dtype=bool)
    covered[32:64, 32:64] = False
    for _ in range(5):
        model.observe(gray, visible=covered)
    # O bloco central nunca foi visto: pendente, sem evidencia.
    assert not np.any(model.seeded[32:64, 32:64])
    assert not np.any(model.admissible()[32:64, 32:64])
    # A mao sai: a primeira observacao limpa semeia COM o desenho —
    # ele e pagina, nao tinta nova (o "pending" do #130).
    for _ in range(2):
        model.observe(gray)
    assert np.all(model.seeded)
    assert not np.any(model.novel(gray))
    assert not np.any(model.pending())


def test_seeded_content_stays_not_novel_but_new_stroke_is():
    model = pm_mod.PageModel((H, W), confirm_obs=2)
    gray = _paper()
    gray[10:20, 10:20] = INK  # conteudo presente desde a semeadura
    for _ in range(2):
        model.observe(gray)
    assert not np.any(model.novel(gray))
    # Traco novo, mais escuro que a referencia: conteudo novo.
    after = gray.copy()
    after[50:60, 50:60] = INK
    novel = model.novel(after)
    assert np.all(novel[50:60, 50:60])
    assert np.count_nonzero(novel) == 100


def test_erasure_is_not_novel():
    model = pm_mod.PageModel((H, W), confirm_obs=1)
    gray = _paper()
    gray[10:20, 10:20] = INK
    model.observe(gray)
    erased = _paper()
    # Pixel mais CLARO que a referencia e mudanca, mas nao tinta:
    # borracha e mao saindo nao podem escrever.
    assert not np.any(model.novel(erased))


def test_tracking_absorbs_shading_drift():
    model = pm_mod.PageModel((H, W), confirm_obs=1, rate=0.5)
    gray = _paper()
    model.observe(gray, paper=np.ones((H, W), dtype=bool))
    # Sombra chegando devagar: a referencia segue o papel e o pixel
    # nunca vira "novo" — a oscilacao do #133 afunda na referencia.
    for level in (220, 200, 180):
        dark = np.full((H, W), float(level), dtype=np.float32)
        model.observe(dark, paper=np.ones((H, W), dtype=bool))
    for _ in range(8):
        model.observe(
            np.full((H, W), 180.0, dtype=np.float32),
            paper=np.ones((H, W), dtype=bool),
        )
    assert not np.any(model.novel(np.full((H, W), 180.0, np.float32)))
    np.testing.assert_allclose(model.reference, 180.0, atol=1.0)


def test_ink_never_sinks_into_reference():
    model = pm_mod.PageModel((H, W), confirm_obs=1, rate=0.5)
    model.observe(_paper(), paper=np.ones((H, W), dtype=bool))
    stroked = _paper()
    stroked[40:50, 40:50] = INK
    paper = np.ones((H, W), dtype=bool)
    paper[40:50, 40:50] = False  # a trabalhadora exclui evidencia de tinta
    for _ in range(40):
        model.observe(stroked, paper=paper)
    # Sem a mascara `paper` a referencia engoliria o traco e ele
    # deixaria de ser novo — o afundamento que a exclusao impede.
    assert np.all(model.novel(stroked)[40:50, 40:50])
    np.testing.assert_allclose(model.reference[40:50, 40:50], PAPER)


def test_ragged_grid_seeds_partial_border_blocks():
    model = pm_mod.PageModel((70, 100), confirm_obs=2)
    gray = _paper((70, 100))
    for _ in range(2):
        model.observe(gray)
    assert np.all(model.seeded)


def test_partial_visibility_block_threshold():
    model = pm_mod.PageModel((H, W), confirm_obs=1, block=32)
    visible = np.zeros((H, W), dtype=bool)
    visible[:32, :16] = True  # metade de um bloco de 32: visto
    visible[:32, 32:48] = True
    model.observe(_paper(), visible=visible)
    # O bloco [0:32, 0:32] tem 50% visivel -> semeado; o que ele
    # semeou foi so a metade vista — a metade coberta segue pendente.
    assert np.all(model.seeded[:32, :16])
    assert not np.any(model.seeded[:32, 16:32])
    assert np.all(model.seeded[:32, 32:48])


def test_novel_and_admissible_need_reference():
    model = pm_mod.PageModel((H, W), confirm_obs=1)
    gray = _paper()
    assert not np.any(model.novel(gray))
    assert not np.any(model.admissible())
    assert np.all(model.pending())


def test_shape_mismatch_raises():
    model = pm_mod.PageModel((H, W))
    with pytest.raises(ValueError):
        model.observe(np.zeros((H + 1, W), dtype=np.float32))


def test_observe_budget_on_a4_grid():
    model = pm_mod.PageModel((1200, 850), confirm_obs=3)
    gray = _paper((1200, 850))
    visible = np.ones((1200, 850), dtype=bool)
    paper = np.ones((1200, 850), dtype=bool)
    model.observe(gray, visible=visible, paper=paper)  # aquece
    start = time.monotonic()
    for _ in range(20):
        model.observe(gray, visible=visible, paper=paper)
    per_pass_ms = (time.monotonic() - start) / 20 * 1000
    assert per_pass_ms < 10.0


class _ScriptInk:
    """Tinta falsa guiada pelo conteudo do proprio warp.

    ink_prob devolve alto onde a imagem esta escura — o par
    (imagem, prob) da passada fica consistente como na passada real.
    """

    threshold = 0.7

    def ink_prob(self, warped):
        gray = warped if warped.ndim == 2 else warped.mean(axis=2)
        return (gray < 100).astype(np.float32) * 0.95


def _bgr(gray):
    return np.stack([gray] * 3, axis=-1).astype(np.uint8)


Q0 = np.array([(0, 0), (W, 0), (W, H), (0, H)], dtype=np.float32)


def _drive(worker, generation, image, visible=None):
    before = worker.stats()["passes_total"]
    worker.submit(WarpedPage(_bgr(image), generation, Q0, visible))
    deadline = time.monotonic() + 5.0
    while worker.stats()["passes_total"] <= before:
        if time.monotonic() > deadline:
            raise AssertionError("a passada nao executou")
        time.sleep(0.001)


def _confirmed(worker, generation):
    snap = worker.poll(generation, 0)
    return np.zeros((H, W), dtype=np.uint8) if snap is None else snap.confirmed


def _worker(config):
    return worker_mod.PageCleanWorker(
        _ScriptInk(),
        config=config,
    ).start()


def test_page_model_suppresses_pre_existing_content(monkeypatch):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True))
    try:
        generation = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        image[10:20, 10:20] = INK  # desenho antigo ja na folha
        for _ in range(7):
            _drive(worker, generation, image)
        canvas = _confirmed(worker, generation)
        # Semeado com o desenho dentro: nunca foi conteudo novo.
        assert np.count_nonzero(canvas) == 0
        # Controle na mesma cena sem o modelo: o voto confirma.
        worker2 = _worker(InkConfig())
        try:
            gen2 = worker2.new_generation()
            for _ in range(7):
                _drive(worker2, gen2, image)
            assert np.count_nonzero(_confirmed(worker2, gen2)) == 100
        finally:
            worker2.stop()
    finally:
        worker.stop()


def test_page_model_confirms_new_stroke_after_seeding(monkeypatch):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True))
    try:
        generation = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        for _ in range(3):
            _drive(worker, generation, image)
        image[50:60, 50:60] = INK  # traco novo apos a referencia
        for _ in range(4):
            _drive(worker, generation, image)
        canvas = _confirmed(worker, generation)
        assert np.count_nonzero(canvas) == 100
    finally:
        worker.stop()


def test_page_model_pending_region_freezes_then_seeds_content(monkeypatch):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True))
    try:
        generation = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        image[40:60, 40:60] = INK  # conteudo sob a mao desde o inicio
        covered = np.ones((H, W), dtype=bool)
        covered[32:64, 32:64] = False
        for _ in range(5):
            _drive(worker, generation, image, visible=covered)
        assert np.count_nonzero(_confirmed(worker, generation)) == 0
        # Mao fora: o bloco ainda esta pendente — conteudo revelado
        # nao vota ate semear; quando semeia, semeia COM o conteudo.
        for _ in range(6):
            _drive(worker, generation, image)
        assert np.count_nonzero(_confirmed(worker, generation)) == 0
    finally:
        worker.stop()


def test_page_model_seeds_the_full_grid(monkeypatch):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True))
    try:
        generation = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        for _ in range(3):
            _drive(worker, generation, image)
        assert worker._page_model is not None
        assert worker._page_model.seeded_fraction == pytest.approx(1.0)
    finally:
        worker.stop()


def _drive_page(worker, generation, page):
    before = worker.stats()["passes_total"]
    worker.submit(page)
    deadline = time.monotonic() + 5.0
    while worker.stats()["passes_total"] <= before:
        if time.monotonic() > deadline:
            raise AssertionError("a passada nao executou")
        time.sleep(0.001)


def test_page_model_reacquires_same_sheet_with_baseline_and_handwriting(monkeypatch):
    """Issue 1: marcas de baseline suprimidas do canvas nao derrubam containment."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True))
    try:
        gen1 = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        # 900 px de conteudo pre-existente (faixas finas para passar na guarda 32x32)
        image[10:20, 10:55] = INK
        image[24:34, 10:55] = INK
        for _ in range(3):
            _drive(worker, gen1, image)
        assert np.count_nonzero(_confirmed(worker, gen1)) == 0

        # 100 px de escrita nova confirmada (containment sem baseline = 100/1000 = 10% < 50%)
        image[60:70, 80:90] = INK
        for _ in range(4):
            _drive(worker, gen1, image)
        assert np.count_nonzero(_confirmed(worker, gen1)) == 100
        pm_before = worker._page_model

        gen2 = worker.new_generation(preserve_identity=True)
        _drive(worker, gen2, image)
        events = worker.telemetry_snapshot()["page_identity_events"]
        assert events[-1]["decision"] == "same_page"
        assert events[-1]["recall"] == pytest.approx(1.0)
        assert events[-1]["containment"] == pytest.approx(1.0)
        confirmed = _confirmed(worker, gen2)
        assert np.count_nonzero(confirmed) == 100
        assert np.all(confirmed[60:70, 80:90] > 0)
        assert not np.any(confirmed[10:34, 10:55] > 0)
        assert worker._page_model is pm_before
    finally:
        worker.stop()


def test_page_model_reacquisition_control_rejects_different_sheet(monkeypatch):
    """Issue 1 (controle): folha diferente continua sendo rejeitada como new_page."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True))
    try:
        gen1 = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        image[10:20, 10:55] = INK
        image[24:34, 10:55] = INK
        for _ in range(3):
            _drive(worker, gen1, image)
        image[60:70, 80:90] = INK
        for _ in range(4):
            _drive(worker, gen1, image)
        assert np.count_nonzero(_confirmed(worker, gen1)) == 100
        pm_before = worker._page_model

        other = np.full((H, W), PAPER, dtype=np.float32)
        other[75:85, 15:65] = INK
        gen2 = worker.new_generation(preserve_identity=True)
        for _ in range(identity_mod._PAGE_IDENTITY_SWITCH_CONSENSUS_FRAMES):
            _drive(worker, gen2, other)
        events = worker.telemetry_snapshot()["page_identity_events"]
        assert events[-1]["decision"] == "new_page"
        assert np.count_nonzero(_confirmed(worker, gen2)) == 0
        assert worker._page_model is not pm_before
    finally:
        worker.stop()


def test_page_model_supports_consecutive_cornerless_submissions(monkeypatch):
    """Issue 2: submissoes consecutivas sem cantos usam identidade sem crashar."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True))
    try:
        generation = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        image[10:20, 10:20] = INK
        for _ in range(3):
            _drive_page(worker, generation, WarpedPage(_bgr(image), generation))
        assert worker.error is None
        assert worker.last_registration is None
        assert worker._page_model is not None
        assert worker._page_model.seeded_fraction == pytest.approx(1.0)
        assert np.count_nonzero(_confirmed(worker, generation)) == 0

        image[50:60, 50:60] = INK
        for _ in range(4):
            _drive_page(worker, generation, WarpedPage(_bgr(image), generation))
        assert worker.error is None
        confirmed = _confirmed(worker, generation)
        assert np.count_nonzero(confirmed) == 100
        assert np.all(confirmed[50:60, 50:60] > 0)
    finally:
        worker.stop()


def test_page_model_handles_cornered_then_cornerless_submission(monkeypatch):
    """Issue 2: passada com cantos seguida de passada sem cantos nao derruba worker."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True))
    try:
        generation = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        _drive_page(worker, generation, WarpedPage(_bgr(image), generation, Q0))
        _drive_page(worker, generation, WarpedPage(_bgr(image), generation, None))
        _drive_page(worker, generation, WarpedPage(_bgr(image), generation, None))
        assert worker.error is None
        assert worker.last_registration is None
        assert worker._page_model.seeded_fraction == pytest.approx(1.0)
    finally:
        worker.stop()


def test_page_model_seeding_remaining_ignores_hidden_blocks():
    """Issue 4: seeding_remaining conta apenas blocos expostos em semeadura ativa."""
    model = pm_mod.PageModel((H, W), confirm_obs=3)
    gray = _paper()
    vis = np.ones((H, W), dtype=bool)
    vis[0:32, 0:64] = False
    for _ in range(3):
        model.observe(gray, visible=vis)
    assert model.seeding_remaining == 0

    # Expõe [0:32, 0:32] mantendo [0:32, 32:64] oculto (streak=0)
    vis[0:32, 0:32] = True
    model.observe(gray, visible=vis)
    assert model.seeding_remaining == 2
    model.observe(gray, visible=vis)
    assert model.seeding_remaining == 1
    model.observe(gray, visible=vis)
    assert model.seeding_remaining == 0
    assert np.all(model.seeded[0:32, 0:32])
    assert not np.any(model.seeded[0:32, 32:64])


def test_page_model_hand_exit_seeds_exposed_blocks_before_rest_and_allows_writing(
    monkeypatch,
):
    """Issue 4: saida da mao mantem passadas suficientes para semear bloco recem-exposto."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.02)
    monkeypatch.setattr(worker_mod, "_IDLE_PROBE_SECONDS", 0.05)
    now = [1000.0]
    worker = worker_mod.PageCleanWorker(
        _ScriptInk(),
        config=InkConfig(page_model=True),
        clock=lambda: now[0],
    )
    generation = worker.new_generation()
    image = np.full((H, W), PAPER, dtype=np.float32)
    covered = np.ones((H, W), dtype=bool)
    covered[32:64, 32:64] = False

    worker.set_hand_presence(True)
    for _ in range(4):
        worker.submit(WarpedPage(_bgr(image), generation, Q0, covered))
        assert worker.pump()
        now[0] += 0.05
    assert not np.any(worker._page_model.seeded[32:64, 32:64])

    # Mao sai e folha fica limpa: deve semear o bloco recem-exposto antes de descansar
    worker.set_hand_presence(False)
    for _ in range(10):
        worker.submit(WarpedPage(_bgr(image), generation, Q0))
        worker.pump()
        now[0] += 0.06
        if worker.stats()["resting"]:
            break
    assert worker.stats()["resting"]
    assert np.all(worker._page_model.seeded[32:64, 32:64])

    # Pausa ociosa de 10 s: nenhuma passada roda em descanso
    passes_at_rest = worker.stats()["passes_total"]
    for _ in range(10):
        worker.submit(WarpedPage(_bgr(image), generation, Q0))
        assert not worker.pump()
        now[0] += 1.0
    assert worker.stats()["passes_total"] == passes_at_rest

    # Escrita subsequente no bloco recem-semeado confirma normalmente
    worker.set_hand_presence(True, moved=True)
    image[40:50, 40:50] = INK
    for _ in range(4):
        worker.submit(WarpedPage(_bgr(image), generation, Q0))
        assert worker.pump()
        now[0] += 0.05
    snap = worker.poll(generation, 0)
    assert snap is not None
    assert np.count_nonzero(snap.confirmed[40:50, 40:50]) == 100


def test_page_model_rests_when_block_remains_hidden(monkeypatch):
    """Issue 4: bloco que permanece oculto nao impede o descanso total."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.02)
    monkeypatch.setattr(worker_mod, "_IDLE_PROBE_SECONDS", 0.05)
    now = [1000.0]
    worker = worker_mod.PageCleanWorker(
        _ScriptInk(),
        config=InkConfig(page_model=True),
        clock=lambda: now[0],
    )
    generation = worker.new_generation()
    image = np.full((H, W), PAPER, dtype=np.float32)
    covered = np.ones((H, W), dtype=bool)
    covered[0:32, 0:32] = False
    covered[32:64, 32:64] = False

    worker.set_hand_presence(True)
    for _ in range(4):
        worker.submit(WarpedPage(_bgr(image), generation, Q0, covered))
        assert worker.pump()
        now[0] += 0.05

    # Mao sai, [32:64, 32:64] exposto mas [0:32, 0:32] segue oculto
    still_hidden = np.ones((H, W), dtype=bool)
    still_hidden[0:32, 0:32] = False
    worker.set_hand_presence(False)
    for _ in range(12):
        worker.submit(WarpedPage(_bgr(image), generation, Q0, still_hidden))
        worker.pump()
        now[0] += 0.06
        if worker.stats()["resting"]:
            break
    assert worker.stats()["resting"]
    assert np.all(worker._page_model.seeded[32:64, 32:64])
    assert not np.any(worker._page_model.seeded[0:32, 0:32])


def test_page_model_resets_on_identity_timeout_within_same_generation(monkeypatch):
    """Issue 5: quarantine_timeout reseta o PageModel junto do acumulador."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True))
    try:
        gen1 = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        for _ in range(3):
            _drive(worker, gen1, image)
        image[10:20, 10:20] = INK
        for _ in range(4):
            _drive(worker, gen1, image)
        assert np.count_nonzero(_confirmed(worker, gen1)) == 100

        gen2 = worker.new_generation(preserve_identity=True)
        occluded = np.ones((H, W), dtype=bool)
        occluded[0:32, 0:32] = False
        for _ in range(identity_mod._PAGE_IDENTITY_MAX_DEFERRALS):
            _drive(worker, gen2, image, visible=occluded)
        assert (
            worker.telemetry_snapshot()["page_identity_events"][-1]["decision"]
            == "deferred_occlusion"
        )
        assert worker._page_model is not None

        # Passada que estoura a quarentena: reseta acumulador e PageModel
        _drive(worker, gen2, image, visible=occluded)
        assert (
            worker.telemetry_snapshot()["page_identity_events"][-1]["decision"]
            == "quarantine_timeout"
        )
        assert worker._page_model is None

        # Nova folha na mesma geracao: marca pre-existente semeia e traco novo confirma
        new_sheet = np.full((H, W), PAPER, dtype=np.float32)
        new_sheet[50:60, 50:60] = INK
        for _ in range(3):
            _drive(worker, gen2, new_sheet)
        assert np.count_nonzero(_confirmed(worker, gen2)) == 0
        new_sheet[10:20, 10:20] = INK
        for _ in range(4):
            _drive(worker, gen2, new_sheet)
        assert np.count_nonzero(_confirmed(worker, gen2)[10:20, 10:20]) == 100
    finally:
        worker.stop()


def test_page_model_resets_on_new_page_after_deferred_occlusion(monkeypatch):
    """Issue 5: new_page apos deferred_occlusion descarta a referencia da ancora velha."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True))
    try:
        gen1 = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        for _ in range(3):
            _drive(worker, gen1, image)
        image[10:20, 10:20] = INK
        for _ in range(4):
            _drive(worker, gen1, image)
        assert np.count_nonzero(_confirmed(worker, gen1)) == 100

        gen2 = worker.new_generation(preserve_identity=True)
        occluded = np.ones((H, W), dtype=bool)
        occluded[0:32, 0:32] = False
        _drive(worker, gen2, image, visible=occluded)
        old_pm = worker._page_model
        assert old_pm is not None

        # Folha diferente visivel: 3 passadas de consenso -> new_page
        other = np.full((H, W), PAPER, dtype=np.float32)
        other[60:70, 60:70] = INK
        for _ in range(identity_mod._PAGE_IDENTITY_SWITCH_CONSENSUS_FRAMES):
            _drive(worker, gen2, other)
        assert (
            worker.telemetry_snapshot()["page_identity_events"][-1]["decision"]
            == "new_page"
        )
        assert worker._page_model is not old_pm
        # Mais 2 passadas terminam de semear a folha nova com [60:70, 60:70] como baseline
        for _ in range(2):
            _drive(worker, gen2, other)
        assert np.count_nonzero(_confirmed(worker, gen2)) == 0
        # Traco novo desenhado em [10:20, 10:20] (onde havia tinta na pagina velha) confirma
        other[10:20, 10:20] = INK
        for _ in range(4):
            _drive(worker, gen2, other)
        assert np.count_nonzero(_confirmed(worker, gen2)[10:20, 10:20]) == 100
    finally:
        worker.stop()


def test_page_model_does_not_seed_synthetic_fill_when_coverage_expands(monkeypatch):
    """Issue 6: preenchimento sintetico fora de coverage nao semeia baseline."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True))
    try:
        generation = worker.new_generation()
        real_sheet = np.full((H, W), PAPER, dtype=np.float32)
        real_sheet[10:20, 10:20] = INK  # marca pre-existente na faixa esquerda

        # Cobertura inicial exclui as primeiras 32 colunas (preenchidas com cor de papel)
        cov_clipped = np.ones((H, W), dtype=bool)
        cov_clipped[:, :32] = False
        filled = real_sheet.copy()
        filled[:, :32] = PAPER
        for _ in range(4):
            _drive_page(
                worker,
                generation,
                WarpedPage(_bgr(filled), generation, Q0, coverage=cov_clipped),
            )
        assert not np.any(worker._page_model.seeded[:, :32])
        assert np.all(worker._page_model.seeded[:, 32:])
        assert np.count_nonzero(_confirmed(worker, generation)) == 0

        # Cobertura expande e revela a marca pre-existente real: semeia como fundo
        cov_full = np.ones((H, W), dtype=bool)
        for _ in range(4):
            _drive_page(
                worker,
                generation,
                WarpedPage(_bgr(real_sheet), generation, Q0, coverage=cov_full),
            )
        assert np.all(worker._page_model.seeded)
        assert np.count_nonzero(_confirmed(worker, generation)) == 0

        # Traco novo na faixa recem-semeada confirma normalmente
        real_sheet[50:60, 10:20] = INK
        for _ in range(4):
            _drive_page(
                worker,
                generation,
                WarpedPage(_bgr(real_sheet), generation, Q0, coverage=cov_full),
            )
        confirmed = _confirmed(worker, generation)
        assert np.count_nonzero(confirmed) == 100
        assert np.all(confirmed[50:60, 10:20] > 0)
    finally:
        worker.stop()


def test_page_model_coverage_drop_preserves_confirmed_ink_reconfirmation(monkeypatch):
    """Issue 6: queda de coverage sobre tinta ja confirmada nao corrompe ref nem bloqueia voto."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True))
    try:
        generation = worker.new_generation()
        cov_full = np.ones((H, W), dtype=bool)
        image = np.full((H, W), PAPER, dtype=np.float32)
        for _ in range(3):
            _drive_page(
                worker,
                generation,
                WarpedPage(_bgr(image), generation, Q0, coverage=cov_full),
            )
        image[50:60, 50:60] = INK
        for _ in range(4):
            _drive_page(
                worker,
                generation,
                WarpedPage(_bgr(image), generation, Q0, coverage=cov_full),
            )
        assert np.count_nonzero(_confirmed(worker, generation)[50:60, 50:60]) == 100

        # Queda semantica de coverage sobre o traco confirmado
        cov_drop = np.ones((H, W), dtype=bool)
        cov_drop[45:65, 45:65] = False
        for _ in range(4):
            _drive_page(
                worker,
                generation,
                WarpedPage(_bgr(image), generation, Q0, coverage=cov_drop),
            )
        assert np.count_nonzero(_confirmed(worker, generation)[50:60, 50:60]) == 100
    finally:
        worker.stop()


def test_page_model_missed_hand_over_seeded_paper_is_blocked(monkeypatch):
    """Issue 7: mao nao mascarada sobre papel ja semeado nao vota nem puxa ref."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True))
    try:
        generation = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        for _ in range(3):
            _drive(worker, generation, image)
        assert worker._page_model.seeded_fraction == pytest.approx(1.0)

        # Mao escura/quente 48x48 (visible=True) com vincos onde _ScriptInk da 0.95
        hand_bgr = _bgr(image)
        hand_bgr[24:72, 40:88] = (90, 110, 150)
        hand_bgr[42:52, 55:65] = (30, 35, 45)
        for _ in range(5):
            _drive_page(worker, generation, WarpedPage(hand_bgr, generation, Q0))
        assert np.count_nonzero(_confirmed(worker, generation)) == 0
        np.testing.assert_allclose(
            worker._page_model.reference[24:72, 40:88], PAPER, atol=1e-3
        )
    finally:
        worker.stop()


def test_page_model_missed_hand_preserves_existing_confirmed_ink(monkeypatch):
    """Issue 7: mao nao mascarada sobre traco confirmado nao o apaga nem corrompe ref."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True, removal=True))
    try:
        generation = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        for _ in range(3):
            _drive(worker, generation, image)
        image[44:52, 54:64] = INK
        for _ in range(4):
            _drive(worker, generation, image)
        assert np.count_nonzero(_confirmed(worker, generation)[44:52, 54:64]) == 80

        # Palma sem mascara (gray ~120 -> prob=0 no _ScriptInk) cobrindo o traco
        hand_bgr = _bgr(image)
        hand_bgr[24:72, 40:88] = (110, 120, 140)
        for _ in range(10):
            _drive_page(worker, generation, WarpedPage(hand_bgr, generation, Q0))
        assert np.count_nonzero(_confirmed(worker, generation)[44:52, 54:64]) == 80
    finally:
        worker.stop()


def test_page_model_occlusion_hold_blocks_recovery_edge_shadow(monkeypatch):
    """Issue 7: occlusion_hold_passes segura residuo de sombra logo apos a mao sair."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True, occlusion_hold_passes=2))
    try:
        generation = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        for _ in range(3):
            _drive(worker, generation, image)

        # 1 passada com mao nao mascarada
        hand_bgr = _bgr(image)
        hand_bgr[24:72, 40:88] = (80, 90, 110)
        _drive_page(worker, generation, WarpedPage(hand_bgr, generation, Q0))

        # Nas 2 passadas seguintes (dentro do hold=2), residuo escuro na regiao nao vota
        residue = image.copy()
        residue[42:52, 55:65] = INK
        for _ in range(2):
            _drive(worker, generation, residue)
        assert np.count_nonzero(_confirmed(worker, generation)) == 0

        # Solto o hold, mais passadas confirmam o traco real
        for _ in range(3):
            _drive(worker, generation, residue)
        assert np.count_nonzero(_confirmed(worker, generation)[42:52, 55:65]) == 100
    finally:
        worker.stop()


def test_page_model_work_does_not_block_submit(monkeypatch):
    """Issue 8: PageModel roda fora de _condition e nao bloqueia submit()."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    entered = threading.Event()
    release = threading.Event()
    orig_observe = pm_mod.PageModel.observe
    calls = [0]

    def _slow_observe(self, *args, **kwargs):
        calls[0] += 1
        if calls[0] == 1:
            entered.set()
            release.wait(timeout=5.0)
        return orig_observe(self, *args, **kwargs)

    monkeypatch.setattr(pm_mod.PageModel, "observe", _slow_observe)
    worker = _worker(InkConfig(page_model=True))
    try:
        generation = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        worker.submit(WarpedPage(_bgr(image), generation, Q0))
        assert entered.wait(timeout=5.0)

        t0 = time.monotonic()
        worker.submit(WarpedPage(_bgr(image), generation, Q0))
        elapsed = time.monotonic() - t0
        assert elapsed < 0.2
        assert not release.is_set()
        release.set()

        _drive(worker, generation, image)
        assert worker.error is None
    finally:
        release.set()
        worker.stop()


def test_page_model_generation_change_mid_pass_discards_safely(monkeypatch):
    """Issue 8: troca de geracao enquanto PageModel roda fora do lock descarta passada velha."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    entered = threading.Event()
    release = threading.Event()
    orig_observe = pm_mod.PageModel.observe
    armed = [False]

    def _hooked_observe(self, *args, **kwargs):
        res = orig_observe(self, *args, **kwargs)
        if armed[0]:
            armed[0] = False
            entered.set()
            release.wait(timeout=5.0)
        return res

    monkeypatch.setattr(pm_mod.PageModel, "observe", _hooked_observe)
    worker = _worker(InkConfig(page_model=True))
    try:
        gen1 = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        for _ in range(3):
            _drive(worker, gen1, image)

        stroked = image.copy()
        stroked[50:60, 50:60] = INK
        _drive(worker, gen1, stroked)
        armed[0] = True
        worker.submit(WarpedPage(_bgr(stroked), gen1, Q0))
        assert entered.wait(timeout=5.0)

        gen2 = worker.new_generation()
        release.set()
        for _ in range(3):
            _drive(worker, gen2, image)
        assert worker.error is None
        assert np.count_nonzero(_confirmed(worker, gen2)) == 0
    finally:
        release.set()
        worker.stop()


def test_page_model_counters_exclude_zero_and_hidden_pixels(monkeypatch):
    """Issue 9: pm_suppressed_px e pm_novel_px contam apenas votos no dominio visivel."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True))
    try:
        generation = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        image[10:20, 10:20] = INK  # 100 px baseline pre-existente
        for _ in range(3):
            _drive(worker, generation, image)

        # Confirma 50 px em [30:35, 10:20]
        image[30:35, 10:20] = INK
        for _ in range(4):
            _drive(worker, generation, image)
        assert np.count_nonzero(_confirmed(worker, generation)) == 50

        # Nova passada com:
        # - 100 px baseline visivel [10:20, 10:20] (suprimido)
        # - 50 px ja confirmado [30:35, 10:20]
        # - 80 px novo visivel [50:58, 10:20] (novel)
        # - 200 px escuro mas OCULTO [70:80, 10:30] (visible=False)
        image[50:58, 10:20] = INK
        image[70:80, 10:30] = INK
        vis = np.ones((H, W), dtype=bool)
        vis[70:80, 10:30] = False
        _drive(worker, generation, image, visible=vis)
        record = worker.telemetry_snapshot()["records"][-1]
        assert record["pm_suppressed_px"] == 100
        assert record["pm_novel_px"] == 80
        assert record["mask_px"] == 80 + 50
    finally:
        worker.stop()


def test_page_model_counters_under_non_identity_warp_border(monkeypatch):
    """Issue 9: borda borderValue=0 fora do warp registrado nao infla pm_novel_px."""
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.01)
    worker = _worker(InkConfig(page_model=True, anchor_follow=False))
    try:
        generation = worker.new_generation()
        image = np.full((H, W), PAPER, dtype=np.float32)
        for _ in range(3):
            _drive(worker, generation, image)

        shifted_quad = Q0 + np.float32([[6, 4], [6, 4], [6, 4], [6, 4]])
        vis_cam = np.ones((H, W), dtype=bool)
        _drive_page(
            worker,
            generation,
            WarpedPage(_bgr(image), generation, shifted_quad, visible=vis_cam),
        )
        record = worker.telemetry_snapshot()["records"][-1]
        assert record["pm_novel_px"] == 0
        assert record["pm_suppressed_px"] == 0
    finally:
        worker.stop()
