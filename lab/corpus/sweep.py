"""Varredura (sweep) de flags de configuração sobre o corpus.

Um sweep é o produto cartesiano de valores de flags do
InkConfig/PipelineConfig: cada combinação vira um bundle nomeado que
``lab.corpus.run.run_corpus`` executa como uma unidade sobre o corpus —
``"ink.reg_deadband=0,1;coverage=0,1"`` gera 4 bundles.

As flags seguem o formato ``campo=valor`` de
``lab.sim_writer._parse_flags`` (``ink.<campo>`` configura o InkConfig,
demais nomes o PipelineConfig); os valores atravessam o sweep como
strings — conversão e validação acontecem no _parse_flags, na execução.
"""

import itertools


def parse_grid(spec: str) -> dict:
    """Especificação textual -> grade {campo: [valores]}.

    ``"ink.reg_deadband=0,1;ink.strict_vote=0.8,0.9"`` ->
    ``{"ink.reg_deadband": ["0", "1"], "ink.strict_vote": ["0.8", "0.9"]}``.
    Campos separados por ``;``, valores de cada campo por ``,``; os
    valores passam como strings (quem converte é a config). Malformado
    — campo sem ``=``, nome/valor vazio, campo repetido — levanta
    ``ValueError`` (erro, nunca silêncio).
    """
    grid = {}
    for field in spec.split(";"):
        name, sep, raw = field.partition("=")
        name = name.strip()
        if not sep or not name:
            raise ValueError(f"campo do sweep espera 'nome=v1,v2,...': {field!r}")
        if name in grid:
            raise ValueError(f"campo repetido no sweep: {name!r}")
        values = [v.strip() for v in raw.split(",")]
        if any(not v for v in values):
            raise ValueError(f"campo do sweep com valor vazio: {field!r}")
        grid[name] = values
    return grid


def grid_bundles(grid: dict, base_flags=()) -> dict:
    """Grade -> {nome_do_bundle: flags} pelo produto cartesiano.

    O nome do bundle junta ``curto=valor`` com ``+`` (``curto`` = campo
    depois do último ponto: ``ink.reg_deadband`` -> ``reg_deadband``);
    as flags levam o nome completo (``ink.reg_deadband=1``), na forma
    que ``_parse_flags`` consome, precedidas de ``base_flags``.
    Grade vazia -> ``{"base": list(base_flags)}``.
    """
    if not grid:
        return {"base": list(base_flags)}
    bundles = {}
    for combo in itertools.product(*grid.values()):
        pairs = list(zip(grid, combo, strict=True))
        tag = "+".join(f"{name.rpartition('.')[2]}={value}" for name, value in pairs)
        bundles[tag] = list(base_flags) + [f"{name}={value}" for name, value in pairs]
    return bundles


def run_sweep(root, spec: str, base_flags=(), *, verify_corpus, **run_kwargs) -> list:
    """Roda o sweep inteiro: parse_grid -> grid_bundles -> run_corpus.

    ``root`` é a raiz do corpus; ``verify_corpus`` é o callable de
    integridade repassado ao ``run_corpus`` (``verify_manifest``, ou
    ``None`` como opt-out explícito). ``run_kwargs`` (``only``,
    ``detector``, ``page_clean``, ``verify``, ``progress``) é repassado
    verbatim ao ``run_corpus``. Devolve a lista de ClipResult.
    """
    # Importe preguiçoso: quem só exercita a grade não precisa do
    # run.py (e de sua pilha de corpus/modelos) importado.
    from lab.corpus.run import run_corpus

    bundles = grid_bundles(parse_grid(spec), base_flags)
    return run_corpus(root, bundles, verify_corpus=verify_corpus, **run_kwargs)
