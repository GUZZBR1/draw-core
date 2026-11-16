"""Estabilização do rastreador de folha (auditoria de 2026-11-02).

Nos frames reais de uma cena parada, os cantos crus do detector
andam dezenas de pixels por frame e os cantos exibidos andavam
junto (passo médio de 9 px, máximo de 101 px, medido em
laboratório pelo agente). Estes testes pinam as três defesas:

1. banda morta: detecção filtrada a até _SHEET_DEADBAND_PX do
   quad atual confirma presença sem mover o quad um pixel;
2. mediana das últimas 3 detecções: um salto isolado de um frame
   não move o quad;
3. candidato a salto fixo: detecções errantes que "andam" não
   confirmam salto — só uma posição sustentada pelo tempo de
   persistência confirma, e aí o quad vai para ela.
"""

import numpy as np

from draw import tracker as tracker_module

BASE = np.array(
    [[200.0, 100.0], [1000.0, 120.0], [1050.0, 650.0], [150.0, 680.0]],
    dtype=np.float32,
)


def _feed(tracker, corners, verdict, times):
    for t in times:
        tracker.update(np.asarray(corners, dtype=np.float32), verdict, True, t)


def test_small_noise_keeps_the_displayed_quad_within_a_pixel():
    tracker = tracker_module.SheetTracker()
    tracker.update(BASE.copy(), "paper", True, 0.0)
    rng = np.random.default_rng(42)
    for i in range(1, 40):
        noisy = (BASE + rng.normal(0.0, 1.0, BASE.shape)).astype(np.float32)
        tracker.update(noisy, "paper", True, i * 0.2)
        distance = tracker_module.corner_distance(tracker.corners, BASE)
        assert distance <= 1.5, (
            f"ruído de ±1 px arrastou o quad exibido {distance:.2f} px: "
            "dentro da banda morta o quad não se move, e fora dela a "
            "mediana limita o passo a uma fração do desvio"
        )


def test_single_frame_spike_does_not_move_the_quad():
    tracker = tracker_module.SheetTracker()
    tracker.update(BASE.copy(), "paper", True, 0.0)
    spiked = BASE + np.array([120.0, 0.0], dtype=np.float32)
    tracker.update(spiked, "paper", True, 0.2)
    tracker.update(BASE.copy(), "paper", True, 0.4)
    tracker.update(BASE.copy(), "paper", True, 0.6)
    assert tracker_module.corner_distance(tracker.corners, BASE) <= (
        tracker_module._SHEET_DEADBAND_PX
    )


def test_wandering_candidate_never_confirms_a_jump():
    tracker = tracker_module.SheetTracker()
    tracker.update(BASE.copy(), "paper", True, 0.0)
    # Dois modos errantes alternados, cada um longe do quad e um
    # do outro: nenhum sustenta posição por 0,3 s.
    mode_a = BASE + np.array([150.0, 0.0], dtype=np.float32)
    mode_b = BASE + np.array([-140.0, 30.0], dtype=np.float32)
    t = 0.2
    for i in range(12):
        tracker.update(mode_a if i % 2 == 0 else mode_b, "paper", True, t)
        t += 0.2
    assert tracker_module.corner_distance(tracker.corners, BASE) <= (
        tracker_module._SHEET_DEADBAND_PX
    )


def test_sustained_new_position_still_confirms():
    tracker = tracker_module.SheetTracker()
    tracker.update(BASE.copy(), "paper", True, 0.0)
    moved = BASE + np.array([150.0, 0.0], dtype=np.float32)
    _feed(tracker, moved, "paper", [0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6])
    assert tracker_module.corner_distance(tracker.corners, moved) <= (
        tracker_module._SHEET_NEAR_LIMIT_PX
    )


def test_big_jump_needs_the_longer_persistence():
    """Salto >100 px sustentado por 0,5 s ainda não confirma
    (assinatura de troca de modo do detector); sustentado por
    mais de 1 s, confirma — mover a folha de verdade paga o
    tempo, não perde o movimento."""
    tracker = tracker_module.SheetTracker()
    tracker.update(BASE.copy(), "paper", True, 0.0)
    moved = BASE + np.array([150.0, 0.0], dtype=np.float32)
    _feed(tracker, moved, "paper", [0.2, 0.4, 0.6])
    assert tracker_module.corner_distance(tracker.corners, BASE) <= (
        tracker_module._SHEET_DEADBAND_PX
    )
    _feed(tracker, moved, "paper", [0.8, 1.0, 1.2, 1.4, 1.6])
    assert tracker_module.corner_distance(tracker.corners, moved) <= (
        tracker_module._SHEET_NEAR_LIMIT_PX
    )


def test_blank_maybe_confirms_under_noisy_detections():
    """Folha branca (blank_maybe) sob ruído que antes nunca
    confirmava: no código anterior, com σ=20 px o relógio do
    candidato resetava a cada detecção e 6 s não bastavam
    (simulador da auditoria, antes/depois medidos). Com o filtro
    de mediana, confirma no mínimo desenhado de 0,6 s."""
    tracker = tracker_module.SheetTracker()
    rng = np.random.default_rng(7)
    confirmed_at = None
    for i in range(40):
        noisy = (BASE + rng.normal(0.0, 20.0, BASE.shape)).astype(np.float32)
        tracker.update(noisy, "blank_maybe", True, i * 0.15)
        if tracker.corners is not None:
            confirmed_at = i * 0.15
            break
    assert confirmed_at is not None and confirmed_at <= 3.0, (
        f"blank_maybe sob ruído σ=20 não confirmou (t={confirmed_at})"
    )


def test_blank_candidate_does_not_survive_absence():
    """blank_maybe que volta apos ausencia nao confirma na hora.

    Candidato pendente morre numa deteccao negativa mesmo antes da
    primeira confirmacao: sem a limpeza, o _pending_since velho
    satisfaz o dobro de persistencia no primeiro quadro da volta.
    """
    tracker = tracker_module.SheetTracker()
    tracker.update(BASE.copy(), "blank_maybe", True, 0.0)
    assert tracker.has_pending
    tracker.update(None, None, True, 2.0)  # deteccao rodou, nada visto
    assert not tracker.has_pending
    event = tracker.update(BASE.copy(), "blank_maybe", True, 5.0)
    assert event is None
    assert tracker.corners is None
    # Confirma so depois do dobro de persistencia do candidato novo.
    event = tracker.update(
        BASE.copy(),
        "blank_maybe",
        True,
        5.0 + 2 * tracker_module._SHEET_JUMP_PERSIST_SECONDS + 0.05,
    )
    assert event == "seen"


def test_paper_without_quad_keeps_blank_candidate_alive():
    """'paper' sem quadrilatero nao reinicia a persistencia do
    candidato blank_maybe.

    Antes da primeira confirmacao, o retorno de 'so presenca' exige
    corners confirmados; o paper-sem-quad caia no ramo de limpeza
    pre-confirmacao e apagava candidato, timer e janela da mediana.
    So deteccao negativa de verdade (veredito != 'paper') limpa.
    """
    tracker = tracker_module.SheetTracker()
    tracker.update(BASE.copy(), "blank_maybe", True, 0.0)
    assert tracker.has_pending
    # Detector afirma papel mas nao fecha quad: presenca sem posicao.
    tracker.update(None, "paper", True, 0.3)
    assert tracker.has_pending
    # O candidato original confirma no prazo dobrado de blank_maybe
    # contado desde a PRIMEIRA deteccao, nao do reinicio.
    event = tracker.update(
        BASE.copy(),
        "blank_maybe",
        True,
        2 * tracker_module._SHEET_JUMP_PERSIST_SECONDS + 0.05,
    )
    assert event == "seen"


def test_returning_sheet_does_not_inherit_stale_candidate_corners():
    """Folha em outra posicao nao herda cantos do candidato morto.

    A janela do filtro tambem faz parte do estado de candidato: sem
    a limpeza, a mediana mistura a posicao antiga com a nova e o
    candidato renasce puxado para os cantos antigos.
    """
    tracker = tracker_module.SheetTracker()
    tracker.update(BASE.copy(), "blank_maybe", True, 0.0)
    tracker.update(None, None, True, 2.0)
    moved = BASE + np.array([300.0, 200.0], dtype=np.float32)
    tracker.update(moved, "blank_maybe", True, 3.0)
    assert tracker.has_pending
    distance = tracker_module.corner_distance(tracker._pending, moved)
    assert distance <= 1.5, (
        f"candidato novo nasceu {distance:.1f} px longe da deteccao: "
        "a janela do filtro herdou os cantos antigos"
    )
