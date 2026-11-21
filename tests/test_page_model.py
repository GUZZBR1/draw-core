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

import time

import numpy as np
import pytest

from draw.contracts import WarpedPage
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
