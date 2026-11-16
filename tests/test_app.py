"""Interface de producao: deteccao combinada, --check e CLI (draw/app.py).

Cobre o que o app acrescenta sobre os modulos: a decisao combinada
neural+classico com veto de presenca e extras de mascara, a checagem
de modelos do --check e a validacao de argumentos do main().
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from draw import app as app_module  # noqa: E402
from draw import config  # noqa: E402
from draw import paper as paper_module
from draw.infra import manifest as manifest_module  # noqa: E402
from draw.perception import PRESENCE_VETO_LOGIT  # noqa: E402


def _frame(h=120, w=160):
    return np.zeros((h, w, 3), dtype=np.uint8)


def _corners():
    return np.array([[10, 10], [150, 10], [150, 110], [10, 110]], dtype=np.float32)


class _FakeNeural:
    """Detector neural de mentira: saida e atributos programados."""

    def __init__(self, corners=None, verdict=None, logit=None, mask=None):
        self._out = (corners, verdict, mask)
        self.last_presence_logit = logit
        self.last_coverage_mask = None
        self.last_hand_mask = None
        self.calls = []

    def __call__(self, frame, *, return_mask=True):
        self.calls.append(return_mask)
        return self._out


@pytest.fixture(autouse=True)
def _restore_format():
    yield
    config.apply_format("a4")


@pytest.fixture
def classic(monkeypatch):
    """Classico programavel: devolve (corners, verdict) por chamada."""
    state = {"result": (None, None), "calls": 0}

    def fake(frame):
        state["calls"] += 1
        return state["result"]

    monkeypatch.setattr(paper_module, "detect_sheet_with_confidence", fake)
    return state


def test_neural_fecha_quad_e_publica_mascaras(classic):
    frame = _frame()
    neural = _FakeNeural(
        _corners(), "paper", logit=3.0, mask=np.ones((120, 160), np.uint8)
    )
    neural.last_coverage_mask = np.full((30, 40), 255, np.uint8)
    neural.last_hand_mask = np.zeros((30, 40), np.uint8)
    neural.last_hand_mask[10:12, 10:12] = 255
    corners, verdict, trace, extras = app_module._detect_sheet_combined_traced(
        frame, neural
    )
    assert corners is not None and verdict == "paper"
    assert trace["source"] == "neural"
    assert classic["calls"] == 0
    # Mascaras sobem retificadas na grade do quadro.
    assert extras["coverage_mask"].shape == frame.shape[:2]
    assert extras["hand_mask"].shape == frame.shape[:2]
    assert neural.calls == [True]


def test_cobertura_quase_vazia_nao_sobe(classic):
    neural = _FakeNeural(
        _corners(), "paper", logit=3.0, mask=np.ones((120, 160), np.uint8)
    )
    coverage = np.zeros((120, 160), np.uint8)
    coverage[0, 0] = 255  # 1 px: abaixo do piso de 5%
    neural.last_coverage_mask = coverage
    _, _, _, extras = app_module._detect_sheet_combined_traced(_frame(), neural)
    assert "coverage_mask" not in extras


def test_logit_forte_veta_o_classico(classic):
    classic["result"] = (_corners(), "paper")
    neural = _FakeNeural(None, None, logit=PRESENCE_VETO_LOGIT, mask=None)
    corners, verdict, trace, _ = app_module._detect_sheet_combined_traced(
        _frame(), neural
    )
    assert (corners, verdict) == (None, None)
    assert trace["source"] == "veto"
    assert classic["calls"] == 0


def test_logit_fraco_deixa_o_classico_falar(classic):
    classic["result"] = (_corners(), "blank_maybe")
    neural = _FakeNeural(None, None, logit=-1.0, mask=None)
    corners, verdict, trace, _ = app_module._detect_sheet_combined_traced(
        _frame(), neural
    )
    assert corners is not None and verdict == "blank_maybe"
    assert trace["source"] == "classic"
    assert classic["calls"] == 1


def test_presenca_sem_posicao_devolve_paper_sem_cantos(classic):
    neural = _FakeNeural(None, None, logit=2.0, mask=None)
    corners, verdict, trace, _ = app_module._detect_sheet_combined_traced(
        _frame(), neural
    )
    assert corners is None and verdict == "paper"
    assert trace["source"] == "presence_only"


def test_sem_neural_e_classico_puro_e_extras_limpos(classic):
    classic["result"] = (_corners(), "paper")
    corners, verdict, trace, extras = app_module._detect_sheet_combined_traced(
        _frame(), None
    )
    assert corners is not None and verdict == "paper"
    assert trace["source"] == "classic" and trace["neural_ran"] is False
    # extras sai sempre (mesmo vazio): e o que limpa a cobertura e a
    # mascara de mao anteriores no resultado publicado.
    assert extras == {}


def test_check_models_avisa_modelo_ausente(monkeypatch, tmp_path, capsys):
    fake = {"modelo_ausente_xyz.onnx": {"sha256": "0" * 64, "bytes": 1}}
    monkeypatch.setattr(
        manifest_module, "load_manifest", lambda path=None: (Path("m.json"), fake)
    )
    monkeypatch.setattr(manifest_module, "DEFAULT_MODELS_DIR", tmp_path)
    assert app_module._check_models() is True
    out = capsys.readouterr().out
    assert "modelo_ausente_xyz.onnx" in out
    assert "Release" in out


def test_check_models_falha_em_divergencia(monkeypatch, tmp_path, capsys):
    model = tmp_path / "modelo.onnx"
    model.write_bytes(b"binario")
    fake = {"modelo.onnx": {"sha256": "f" * 64, "bytes": 7}}
    monkeypatch.setattr(
        manifest_module, "load_manifest", lambda path=None: (Path("m.json"), fake)
    )
    monkeypatch.setattr(manifest_module, "DEFAULT_MODELS_DIR", tmp_path)
    monkeypatch.setattr(
        manifest_module,
        "verify_model",
        lambda path, **kw: (_ for _ in ()).throw(RuntimeError("sha diverge")),
    )
    assert app_module._check_models() is False
    assert "FAIL" in capsys.readouterr().out


def test_main_check_chama_run_check(monkeypatch):
    seen = {}

    def fake_check(source):
        seen["s"] = source
        return 0

    monkeypatch.setattr(app_module, "run_check", fake_check)
    monkeypatch.setattr(sys, "argv", ["draw", "--check", "--source", "3"])
    with pytest.raises(SystemExit) as error:
        app_module.main()
    assert error.value.code == 0
    assert seen["s"] == 3


def test_main_check_com_url_passa_url(monkeypatch):
    seen = {}

    def fake_check(source):
        seen["s"] = source
        return 0

    monkeypatch.setattr(app_module, "run_check", fake_check)
    monkeypatch.setattr(
        sys, "argv", ["draw", "--check", "--source", "http://10.0.0.1:8080/video"]
    )
    with pytest.raises(SystemExit):
        app_module.main()
    assert seen["s"] == "http://10.0.0.1:8080/video"


def test_main_markers_rejeita_flags_de_modelo(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["draw", "--markers", "--neural", "x.onnx"])
    with pytest.raises(SystemExit) as error:
        app_module.main()
    assert error.value.code == 2


def test_main_neural_sem_caminho_e_erro(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["draw", "--neural"])
    with pytest.raises(SystemExit) as error:
        app_module.main()
    assert error.value.code == 2


def test_main_formato_invalido_e_erro(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["draw", "--format", "paisagem"])
    with pytest.raises(SystemExit) as error:
        app_module.main()
    assert error.value.code == 2


def test_main_defaults_chamam_run(monkeypatch):
    seen = {}
    monkeypatch.setattr(app_module, "run", lambda **kw: seen.update(kw))
    monkeypatch.setattr(sys, "argv", ["draw", "--save-dir", "out"])
    app_module.main()
    assert seen["source"] == "0"
    assert seen["save_dir"] == "out"
    assert seen["markers_mode"] is False
    # Sem --page-clean, o modelo padrao resolve dentro de run/PageCleanInk.
    assert seen["page_clean_model"] is None


def test_main_erro_de_execucao_sai_2(monkeypatch):
    def boom(**kw):
        raise RuntimeError("camera morta")

    monkeypatch.setattr(app_module, "run", boom)
    monkeypatch.setattr(sys, "argv", ["draw"])
    with pytest.raises(SystemExit) as error:
        app_module.main()
    assert error.value.code == 2
