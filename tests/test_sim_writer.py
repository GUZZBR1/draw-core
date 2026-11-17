"""Testes do parser de flags do lab/sim_writer (geracao/auditoria
precisam de corpus e modelos externos ao repo)."""

import pytest


def test_parse_flags_defaults():
    from lab.sim_writer import _parse_flags

    from draw.settings import PipelineConfig

    assert _parse_flags([]) == PipelineConfig()


def test_parse_flags_pipeline_and_ink_fields():
    from lab.sim_writer import _parse_flags

    config = _parse_flags(["coverage=0", "ink.reg_deadband=1"])
    assert config.coverage is False
    assert config.ink.reg_deadband is True
    assert config.canvas_persist is True
    assert config.ink.removal is True


@pytest.mark.parametrize(
    "flags",
    [
        ["DRAW_INK_VOTE_E3=1"],  # variavel de ambiente removida
        ["nao_existe=1"],
        ["ink.nao_existe=1"],
        ["ink=1"],
        ["coverage"],
        ["coverage=talvez"],
        ["=1"],
    ],
)
def test_parse_flags_rejects_unknown(flags):
    from lab.sim_writer import _parse_flags

    with pytest.raises(ValueError):
        _parse_flags(flags)
