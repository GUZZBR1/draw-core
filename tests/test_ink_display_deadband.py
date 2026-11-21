"""Banda morta da camada provisoria exibida (issue #134).

O acumulador segue pixel a pixel por dentro; a camada que a tela
ve so contem os componentes >= provisional_min_px. O contrato:

1. Poeira que pisca nao republica o painel nem conta como
   atividade — com o sinal de mao ausente, a cadencia cai para a
   da sonda ociosa mesmo com a mascara interna tremulando.
2. Um traco novo aparece na primeira passada, como antes; a
   poeira sustentada nunca entra na camada exibida.
3. Na entrada do descanso total, o provisorio pendente sai da
   tela numa unica troca — o painel para na confirmada, sem
   piscar, com a mao fora ou presente e parada.
"""

import numpy as np
import pytest

from draw.contracts import WarpedPage
from draw.ink import worker as worker_mod

H, W = 40, 60
SPECK = (slice(30, 32), slice(30, 32))  # 4 px, abaixo do piso de 12
BLOB = (slice(5, 13), slice(5, 20))  # 8x15 = 120 px, acima do piso
STROKE = (slice(20, 30), slice(5, 25))  # 10x20 = 200 px


def _pump_for(worker, generation, now, seconds, step=0.01):
    warp = np.zeros((H, W, 3), dtype=np.uint8)
    end = now[0] + seconds
    while now[0] < end:
        worker.submit(WarpedPage(warp, generation))
        worker.pump()
        now[0] += step


class _SpeckInk:
    """Poeira de 4 px que entra e sai da janela do voto.

    Acesa uma passada a cada quatro: a mascara provisoria interna
    ganha e perde a poeira a cada ciclo (nunca chega a confirmar),
    mas a componente esta sempre abaixo do piso de exibicao.
    """

    threshold = 0.7

    def __init__(self):
        self.calls = 0
        self.stroke = False

    def ink_prob(self, _warped):
        self.calls += 1
        prob = np.zeros((H, W), dtype=np.float32)
        if self.calls % 4 == 1:
            prob[SPECK] = 0.9
        if self.stroke:
            prob[STROKE] = 0.95
        return prob


def test_flickering_speck_neither_republishes_nor_holds_cadence(monkeypatch):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.02)
    monkeypatch.setattr(worker_mod, "_IDLE_PROBE_SECONDS", 0.30)
    monkeypatch.setattr(worker_mod, "_NO_HAND_REST_AFTER_STILL_PASSES", 3)
    now = [1000.0]
    fake = _SpeckInk()
    worker = worker_mod.PageCleanWorker(fake, clock=lambda: now[0])
    generation = worker.new_generation()
    # Aquecimento: a primeira passada publica, a poeira interna
    # entra e sai da janela sem nunca chegar a camada exibida.
    _pump_for(worker, generation, now, 0.2)
    snap = worker.poll_display(generation, 0)
    assert snap is not None
    assert np.count_nonzero(snap.provisional) == 0
    version, calls = snap.version, fake.calls
    # Janela longa de flicker interno: nenhuma versao nova de
    # exibicao, e a cadencia cai para a sonda (~2 passadas), nao
    # para a cadencia cheia (~30) que o flicker segurava antes.
    _pump_for(worker, generation, now, 0.65)
    assert worker.poll_display(generation, version) is None
    assert fake.calls - calls <= 4


def test_real_stroke_still_appears_on_first_pass():
    now = [1000.0]
    fake = _SpeckInk()
    worker = worker_mod.PageCleanWorker(fake, clock=lambda: now[0])
    generation = worker.new_generation()
    warp = np.zeros((H, W, 3), dtype=np.uint8)
    fake.stroke = True
    worker.submit(WarpedPage(warp, generation))
    worker.pump()
    snap = worker.poll_display(generation, 0)
    assert np.count_nonzero(snap.provisional[STROKE]) == 10 * 20
    assert np.count_nonzero(snap.provisional[SPECK]) == 0
    now[0] += 0.3
    worker.submit(WarpedPage(warp, generation))
    worker.pump()
    snap = worker.poll_display(generation, snap.version)
    assert np.count_nonzero(snap.confirmed[STROKE]) == 10 * 20


class _BlobOnceInk:
    """Mancha grande vista uma unica passada.

    Fica provisoria pela janela do voto sem confirmar: e o resto
    de evidencia fraca que a tela congelava ao descansar (issue
    #134), nao um traco — o traco real confirma.
    """

    threshold = 0.7

    def __init__(self):
        self.calls = 0

    def ink_prob(self, _warped):
        self.calls += 1
        prob = np.zeros((H, W), dtype=np.float32)
        if self.calls == 1:
            prob[BLOB] = 0.95
        return prob


@pytest.mark.parametrize("hand", [False, True])
def test_rest_entry_settles_display_once(hand, monkeypatch):
    monkeypatch.setattr(worker_mod, "_PAGE_CLEAN_INTERVAL_SECONDS", 0.02)
    monkeypatch.setattr(worker_mod, "_IDLE_PROBE_SECONDS", 0.05)
    monkeypatch.setattr(worker_mod, "_HAND_REST_STILL_SECONDS", 0.05)
    now = [1000.0]
    fake = _BlobOnceInk()
    worker = worker_mod.PageCleanWorker(fake, clock=lambda: now[0])
    generation = worker.new_generation()
    worker.set_hand_presence(hand)
    warp = np.zeros((H, W, 3), dtype=np.uint8)
    worker.submit(WarpedPage(warp, generation))
    worker.pump()
    snap = worker.poll_display(generation, 0)
    assert np.count_nonzero(snap.provisional[BLOB]) == 8 * 15
    version = snap.version
    # A mancha segue provisoria e exibida quando a saida
    # confirmada fecha a quietude do descanso total: a tela
    # assenta sem ela, numa unica troca.
    _pump_for(worker, generation, now, 0.5)
    assert worker.stats()["resting"]
    settled = worker.poll_display(generation, 0)
    assert np.count_nonzero(settled.provisional) == 0
    assert settled.version == version + 1
    _pump_for(worker, generation, now, 0.3)
    assert worker.poll_display(generation, settled.version) is None
