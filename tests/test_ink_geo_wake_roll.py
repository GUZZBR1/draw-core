"""Pouso rodado e o despertar geometrico do descanso.

Apos um pouso rodado a ancora carrega rotulos ciclicamente
rolados (_anchor_roll), mas os quads que chegam ao submit seguem
posicionais. A comparacao de movimento do submit tem de desfazer
o roll — como os gatilhos da arbitragem ja fazem — ou toda folha
parada parece deslocada para sempre e a tinta nunca entra em
repouso (o _quiet_passes zera a cada submit).
"""

import numpy as np

from draw.ink import worker as worker_mod

H, W = 40, 60

QUAD = np.array(
    [[0.0, 0.0], [60.0, 0.0], [60.0, 40.0], [0.0, 40.0]],
    dtype=np.float32,
)


class _Prob:
    threshold = 0.7

    def ink_prob(self, _warped):
        return np.zeros((H, W), dtype=np.float32)


def _worker_with_rolled_anchor(roll):
    worker = worker_mod.PageCleanWorker(_Prob())
    # Simula o estado depois de um pouso rodado julgado pela
    # arbitragem: a ancora rotulada por `roll` sobre o quad
    # posicional da folha parada.
    worker._anchor_roll = roll
    worker._anchor_corners = np.roll(QUAD, roll, axis=0)
    return worker


def test_stationary_sheet_after_rotated_landing_is_not_away():
    worker = _worker_with_rolled_anchor(roll=1)
    warp = np.zeros((H, W, 3), dtype=np.uint8)
    # A folha segue no mesmo lugar: o quad posicional e o mesmo
    # que gerou a ancora. O roll dos rotulos nao e deslocamento.
    worker.submit(warp, 0, QUAD)
    assert worker._geo_away is False
    # Nem a quietude pode ser zerada pela permutacao de rotulos.
    worker._quiet_passes = 3
    worker.submit(warp, 0, QUAD)
    assert worker._quiet_passes == 3


def test_real_movement_after_rotated_landing_is_still_away():
    worker = _worker_with_rolled_anchor(roll=1)
    warp = np.zeros((H, W, 3), dtype=np.uint8)
    moved = QUAD + np.array([[40.0, 0.0]], dtype=np.float32)
    worker.submit(warp, 0, moved)
    assert worker._geo_away is True
