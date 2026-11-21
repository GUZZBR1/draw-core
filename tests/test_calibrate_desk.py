"""lab/calibrate_desk.py: recalibração dos limiares sem denominador.

A ferramenta aplica a MESMA regra da calibração de referência sobre
capturas ROTULADAS (--empty/--sheet) da mesa nova (issue #105). Os
lados vêm do rótulo do operador — não do desfecho do detector e
não do piso vigente, que censura os anéis de IoU por construção
(rejeitados < piso <= aceitos, "separados" de graça). Os testes
cobrem o fantasma aceito pelo piso velho e a folha perdida pelo
detector — as contaminações que o rótulo elimina.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab import calibrate_desk as cd  # noqa: E402


def _acq(source, logit=None, fit_reject=None):
    return {
        "event": "acquisition",
        "source": source,
        "presence_logit": logit,
        "fit_reject": fit_reject,
    }


def _snapshot(rejects=(), accepts=()):
    return {
        "coverage_iou_reject_recent": list(rejects),
        "coverage_iou_accept_recent": list(accepts),
        "t_epoch": 1.0,
    }


def _write_telemetry(tmp_path, records, name="telemetry.jsonl"):
    path = tmp_path / name
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def test_fantasma_aceito_pelo_piso_velho_conta_como_mesa_vazia(tmp_path):
    """O exemplo da revisão: captura de mesa vazia com fantasmas
    rejeitados 0.10 E ACEITO 0.23 (o piso velho deixou passar), e
    a menor folha real a 0.24. Sem rótulo, o 0.23 contaminaria o
    lado folha; rotulado, o piso sai entre 0.23 e 0.24 = 0.235."""
    empty = _write_telemetry(
        tmp_path, [_snapshot(rejects=[0.05, 0.10], accepts=[0.23])], "e.jsonl"
    )
    sheet = _write_telemetry(
        tmp_path, [_snapshot(accepts=[0.24, 0.30, 0.41])], "s.jsonl"
    )
    summary = cd.summarize([empty], [sheet])
    assert summary["empty"]["coverage"] == {0.05, 0.10, 0.23}
    assert summary["sheet"]["coverage"] == {0.24, 0.30, 0.41}
    floor = cd.suggest(summary)["coverage_iou_floor"]["value"]
    assert floor == pytest.approx(0.235)
    assert 0.23 < floor < 0.24  # separa onde o piso velho falhava


def test_folha_perdida_pelo_veto_conta_como_folha(tmp_path):
    """Regressão do detector: numa captura ROTULADA com folha, uma
    aquisição vetada é uma folha real que o veto matou — entra no
    lado folha e anula o veto que a mataria de novo."""
    empty = _write_telemetry(
        tmp_path, [_acq("veto", -6.0), _acq("none", -4.0)], "e.jsonl"
    )
    sheet = _write_telemetry(
        tmp_path,
        [
            _acq("veto", -2.5),  # folha real vetada pelo limiar velho
            _acq("classic", 1.5),
            _acq("neural", 3.0),  # imune ao veto: fica à parte
        ],
        "s.jsonl",
    )
    summary = cd.summarize([empty], [sheet])
    assert summary["empty"]["presence"] == [-6.0, -4.0]
    assert summary["sheet"]["presence"] == [-2.5, 1.5]
    assert summary["sheet"]["presence_neural"] == [3.0]
    sug = cd.suggest(summary)["presence_veto_logit"]
    # -4.0 + 4.0 = 0.0 vetaria a folha perdida a -2.5 → sem sugestão.
    assert sug["value"] is None
    assert sug["sheets_vetoed"] == 1
    assert "não separa" in sug["evidence"]


def test_sugere_veto_sobre_o_maior_logit_de_mesa_vazia(tmp_path):
    """Regra de referência: -6.98 na mesa vazia → veto -3.0.
    Aqui a mesa nova chega a -5.0 → veto -1.0, e nenhuma folha
    vetável observada cai sob ele."""
    empty = _write_telemetry(
        tmp_path, [_acq("veto", -5.0), _acq("veto", -8.2)], "e.jsonl"
    )
    sheet = _write_telemetry(
        tmp_path,
        [_acq("classic", -0.4), _acq("presence_only", 1.0), _acq("neural", 2.1)],
        "s.jsonl",
    )
    summary = cd.summarize([empty], [sheet])
    assert summary["sheet"]["source_counts"] == {
        "classic": 1,
        "presence_only": 1,
        "neural": 1,
    }
    sug = cd.suggest(summary)["presence_veto_logit"]
    assert sug["value"] == pytest.approx(-1.0)
    assert sug["sheets_vetoed"] == 0


def test_deteccao_neural_sob_o_veto_nao_e_contada_como_vetada(tmp_path):
    """A neural devolve cantos antes do check do veto: uma detecção
    neural com logit sob o veto proposto NÃO morreria — não pode
    anular a sugestão."""
    empty = _write_telemetry(tmp_path, [_acq("veto", -6.0)], "e.jsonl")
    sheet = _write_telemetry(
        tmp_path, [_acq("neural", -2.5), _acq("classic", 1.5)], "s.jsonl"
    )
    sug = cd.suggest(cd.summarize([empty], [sheet]))["presence_veto_logit"]
    assert sug["value"] == pytest.approx(-2.0)
    assert sug["sheets_vetoed"] == 0


def test_sem_um_lado_nao_ha_sugestao(tmp_path):
    """Só mesa com folha: o piso e o veto ficam sem sugestão —
    metade da distribuição não basta."""
    sheet = _write_telemetry(
        tmp_path, [_acq("classic", 1.0), _snapshot(accepts=[0.4, 0.5])]
    )
    summary = cd.summarize([], [sheet])
    sug = cd.suggest(summary)
    assert sug["coverage_iou_floor"]["value"] is None
    assert "--empty" in sug["coverage_iou_floor"]["evidence"]
    assert sug["presence_veto_logit"]["value"] is None
    assert "--empty" in sug["presence_veto_logit"]["evidence"]


def test_folhas_so_neurais_nao_confundem_evidencia(tmp_path):
    """Folhas existem mas todas vieram da neural (imune ao veto):
    a evidência diz que faltam amostras do LADO VETÁVEL — não que
    a captura não viu folha."""
    empty = _write_telemetry(tmp_path, [_acq("veto", -6.0)], "e.jsonl")
    sheet = _write_telemetry(
        tmp_path, [_acq("neural", 1.8), _acq("neural", 2.4)], "s.jsonl"
    )
    sug = cd.suggest(cd.summarize([empty], [sheet]))["presence_veto_logit"]
    assert sug["value"] is None
    assert "neural" in sug["evidence"]
    assert "2" in sug["evidence"]


def test_distribuicoes_sobrepostas_nao_separam_piso(tmp_path):
    """Fantasma acima da folha mais baixa: o ponto médio não separa
    — reportar a sobreposição em vez de inventar um limiar."""
    empty = _write_telemetry(
        tmp_path, [_snapshot(rejects=[0.30], accepts=[0.35])], "e.jsonl"
    )
    sheet = _write_telemetry(tmp_path, [_snapshot(accepts=[0.30, 0.6])], "s.jsonl")
    sug = cd.suggest(cd.summarize([empty], [sheet]))
    assert sug["coverage_iou_floor"]["value"] is None
    assert "sobrepõem" in sug["coverage_iou_floor"]["evidence"]


def test_fit_reject_e_pixel_scale_entram_na_sumarizacao(tmp_path):
    path = _write_telemetry(
        tmp_path,
        [
            {
                **_acq(
                    "veto",
                    -9.0,
                    fit_reject={"reason": "min_area", "area_ratio": 0.008},
                ),
                "tracker_after": {"pixel_scale": 1.5},
            },
            _acq("none", None, {"reason": "unsupported"}),
            # low_presence carrega FRAÇÃO DE FOREGROUND da máscara —
            # métrica diferente da razão de contorno; não entra na
            # evidência do _MIN_CONTOUR_AREA_RATIO.
            _acq("none", None, {"reason": "low_presence", "area_ratio": 0.31}),
        ],
    )
    summary = cd.summarize([path], [])
    assert summary["empty"]["fit_reject_reasons"] == {
        "min_area": 1,
        "unsupported": 1,
        "low_presence": 1,
    }
    assert summary["empty"]["fit_reject_areas"] == [0.008]
    assert summary["empty"]["pixel_scales"] == {1.5}
    assert "min_area" in cd.suggest(summary)["min_contour_area_ratio"]["evidence"]


def test_main_emite_relatorio_json(tmp_path, capsys):
    empty = _write_telemetry(
        tmp_path, [_acq("veto", -7.0), _snapshot(rejects=[0.05])], "e.jsonl"
    )
    sheet = _write_telemetry(
        tmp_path,
        [_acq("classic", 2.0), _snapshot(accepts=[0.35])],
        "s.jsonl",
    )
    assert cd.main(["--empty", str(empty), "--sheet", str(sheet)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["empty"]["acquisitions"] == 1
    assert report["sheet"]["acquisitions"] == 1
    assert report["sheet"]["source_counts"] == {"classic": 1}
    sugs = report["suggestions"]
    assert sugs["presence_veto_logit"]["value"] == pytest.approx(-3.0)
    assert sugs["coverage_iou_floor"]["value"] == pytest.approx(0.2)


def test_main_aceita_diretorio_de_sessao(tmp_path, capsys):
    session = tmp_path / "sessao-nova"
    session.mkdir()
    (session / "telemetry.jsonl").write_text(
        json.dumps(_acq("veto", -4.0)) + "\n",
        encoding="utf-8",
    )
    assert cd.main(["--empty", str(session)]) == 0
    report = json.loads(capsys.readouterr().out)
    # Só um lado: o veto fica sem validação contra folha.
    assert report["suggestions"]["presence_veto_logit"]["value"] is None


def test_main_exige_rotulos(capsys):
    with pytest.raises(SystemExit):
        cd.main([])


def test_linhas_quebradas_nao_derrubam(tmp_path):
    path = tmp_path / "telemetry.jsonl"
    path.write_text(
        '{"event": "acquisition", "source": "veto", "presence_logit": -6.0}\n'
        "{linha truncada\n"
        "\n"
        '{"coverage_iou_reject_recent": [0.07]}\n',
        encoding="utf-8",
    )
    summary = cd.summarize([path], [])
    assert summary["empty"]["presence"] == [-6.0]
    assert summary["empty"]["coverage"] == {0.07}
