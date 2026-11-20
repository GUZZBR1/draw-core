"""Gera as figuras dos artigos. Rode: python3 -I docs/research/figures/make_figures.py

Cada artigo ganha uma funcao `fig_NN_k` e uma linha em FIGURES. As duas abaixo sao
exemplos do padrao: copie a forma, troque rotulos.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import figkit as k  # noqa: E402


def fig_08_1() -> str:
    """Cadeia de medicao como caixa-preta (artigo 08, F1)."""
    parts = [
        k.text(
            40,
            44,
            "Cadeia de medição da latência (sistema como caixa-preta)",
            20,
            k.INK,
            True,
        ),
        k.row(
            40,
            100,
            [
                "Gesto observável",
                "Sistema de desenho assistido por câmera",
                "Resposta visível",
            ],
            w=340,
            gap=40,
        ),
        k.text(210, 200, "t₀: instante do gesto", 14, k.MUTED, False, "middle"),
        k.text(950, 200, "t₁: a resposta aparece", 14, k.MUTED, False, "middle"),
        k.arrow(210, 215, 950, 215, dashed=True),
        k.text(
            545,
            255,
            "latência de ponta a ponta = t₁ − t₀ (medida por câmera externa)",
            14,
            k.TEAL,
            True,
            "middle",
        ),
    ]
    return k.svg(
        1200,
        300,
        "Cadeia de medição",
        "Gesto, sistema e resposta visível, com a latência entre eles.",
        *parts,
    )


def fig_08_2() -> str:
    """Forma esquematica de uma distribuicao acumulada, sem dados."""
    parts = [
        k.text(40, 44, "Distribuição de latência: forma ilustrativa", 20, k.INK, True),
        k.curve_placeholder(
            135,
            80,
            900,
            220,
            "observações ordenadas",
            "proporção acumulada",
            falling=False,
        ),
    ]
    return k.svg(
        1200,
        390,
        "Distribuição de latência, ilustrativa",
        "Curva conceitual sem amostras, valores ou unidades nos eixos.",
        *parts,
    )


def fig_08_3() -> str:
    """Desenho conceitual de uma condicao com atraso experimental."""
    parts = [
        k.text(40, 44, "Condição opcional com atraso controlado", 20, k.INK, True),
        k.row(
            70,
            115,
            ["Gesto", "Atraso experimental", "Resposta visível"],
            w=300,
            h=78,
            gap=65,
        ),
        k.text(
            600,
            250,
            "Comparar condições sem observar etapas internas",
            16,
            k.MUTED,
            False,
            "middle",
        ),
    ]
    return k.svg(
        1200,
        310,
        "Teste opcional com atraso",
        "Gesto, condição temporal controlada e resposta visível como eventos externos.",
        *parts,
    )


def fig_06_1() -> str:
    """Catalogo conceitual de perturbacoes ambientais comuns."""
    labels = [
        (45, 115, "Reflexo", "brilho localizado"),
        (335, 115, "Sombra", "sombra projetada"),
        (625, 115, "Desfoque", "perda de nitidez"),
        (915, 115, "Ruído", "variação visual"),
        (45, 265, "Dobra / amassado", "papel deformado"),
        (335, 265, "Fundo", "superfície ao redor"),
        (625, 265, "Cor do papel", "tons diferentes"),
        (915, 265, "Fonte de luz", "origem e direção"),
    ]
    parts = [k.text(40, 44, "Perturbações observáveis na cena", 20, k.INK, True)]
    for x, y, title, detail in labels:
        parts.append(k.box(x, y, 250, 92, title, k.TEAL, detail))
    return k.svg(
        1200,
        420,
        "Catálogo de perturbações ambientais",
        "Oito fatores esquemáticos que podem variar em uma avaliação de robustez.",
        *parts,
    )


def fig_06_2() -> str:
    """Comparacao em blocos de referencia, fator isolado e combinacoes."""
    parts = [
        k.text(40, 44, "Blocos de avaliação de robustez", 20, k.INK, True),
        k.row(
            45,
            125,
            ["Referência", "Variação isolada", "Combinações planejadas"],
            w=330,
            h=88,
            gap=60,
        ),
        k.text(
            600,
            290,
            "Registrar condição e resposta observável em cada bloco",
            16,
            k.MUTED,
            False,
            "middle",
        ),
    ]
    return k.svg(
        1200,
        350,
        "Protocolo conceitual de variação",
        "Comparação experimental por referência, fatores isolados e combinações planejadas.",
        *parts,
    )


def fig_06_3() -> str:
    """Forma esperada da curva de degradação (artigo 06, F3). Sem dados."""
    parts = [
        k.text(40, 44, "Forma esperada da curva de degradação", 20, k.INK, True),
        k.curve_placeholder(
            120, 80, 900, 230, "nível da perturbação (do leve ao forte)", "desempenho"
        ),
    ]
    return k.svg(
        1200,
        400,
        "Curva de degradação ilustrativa",
        "Eixos sem valores e curva tracejada, sem dados.",
        *parts,
    )


def fig_03_1() -> str:
    """Linha do tempo de eventos de identidade da pagina."""
    parts = [
        k.text(40, 44, "Eventos observáveis ao longo da sessão", 20, k.INK, True),
        k.timeline(
            70,
            185,
            1060,
            [
                (0.0, "página visível"),
                (0.2, "desloca"),
                (0.4, "ausente"),
                (0.6, "página parecida"),
                (0.8, "retorno"),
                (1.0, "fim da sessão"),
            ],
        ),
        k.text(
            600,
            315,
            "Registrar evento, decisão relatada e consequência visível",
            15,
            k.MUTED,
            False,
            "middle",
        ),
    ]
    return k.svg(
        1200,
        370,
        "Linha do tempo de identidade",
        "Eventos externos de permanência, deslocamento, ausência e retorno de páginas.",
        *parts,
    )


def fig_03_2() -> str:
    """Relacao conceitual entre eventos, decisoes e custos observaveis."""
    parts = [
        k.text(40, 44, "Eventos, decisões e consequências", 20, k.INK, True),
        k.row(
            40,
            105,
            ["Evento observado", "Decisão relatada", "Consequência visível"],
            w=330,
            h=78,
            gap=55,
        ),
        k.box(
            145, 250, 390, 88, "Fusão indevida", k.CLAY, "páginas distintas associadas"
        ),
        k.box(
            665,
            250,
            390,
            88,
            "Separação indevida",
            k.VIOLET,
            "uma página tratada como nova",
        ),
        k.text(
            600,
            390,
            "Categorias para análise externa, sem descrever regra de identidade",
            14,
            k.MUTED,
            False,
            "middle",
        ),
    ]
    return k.svg(
        1200,
        430,
        "Taxonomia de decisões de identidade",
        "Relação conceitual entre anotação externa, decisão e classes de erro avaliadas.",
        *parts,
    )


def fig_03_3() -> str:
    """Forma ilustrativa de erro por duracao de ausencia, sem dados."""
    parts = [
        k.text(40, 44, "Erro de identidade e ausência", 20, k.INK, True),
        k.curve_placeholder(
            135,
            80,
            900,
            220,
            "duração da ausência (qualitativa)",
            "erro de identidade",
        ),
    ]
    return k.svg(
        1200,
        390,
        "Curva ilustrativa de erro de identidade",
        "Forma conceitual sem pontos, valores ou observações experimentais.",
        *parts,
    )


def fig_10_1() -> str:
    """Rastreabilidade conceitual entre planejamento, evidencias e relato."""
    parts = [
        k.text(40, 44, "Fluxo conceitual de rastreabilidade", 20, k.INK, True),
        k.row(
            55,
            115,
            ["Pergunta", "Protocolo", "Registros", "Relato"],
            w=235,
            h=76,
            gap=50,
        ),
        k.text(
            600,
            250,
            "Cada ligação deve poder ser examinada sem expor detalhes internos do sistema",
            16,
            k.MUTED,
            False,
            "middle",
        ),
    ]
    return k.svg(
        1200,
        310,
        "Rastreabilidade experimental",
        "Pergunta, protocolo, registros e relato ligados em uma cadeia conceitual.",
        *parts,
    )


def fig_10_2() -> str:
    """Distincao conceitual entre repetir, replicar e reproduzir."""
    parts = [
        k.text(40, 44, "Níveis de repetição de uma avaliação", 20, k.INK, True),
        k.row(
            70,
            115,
            ["Repetir", "Replicar", "Reproduzir"],
            w=310,
            h=105,
            gap=55,
        ),
        k.text(225, 245, "mesma equipe e materiais", 14, k.MUTED, False, "middle"),
        k.text(
            590,
            245,
            "outra equipe, protocolo compartilhado",
            14,
            k.MUTED,
            False,
            "middle",
        ),
        k.text(955, 245, "implementação independente", 14, k.MUTED, False, "middle"),
        k.text(
            600,
            270,
            "Os termos dependem da convenção adotada; declarar a definição usada",
            15,
            k.MUTED,
            False,
            "middle",
        ),
    ]
    return k.svg(
        1200,
        330,
        "Níveis de reprodutibilidade",
        "Três categorias de repetição com mudanças graduais de equipe, materiais e implementação.",
        *parts,
    )


def fig_10_3() -> str:
    """Forma ilustrativa de uma exibicao futura da variacao entre repeticoes."""
    parts = [
        k.text(40, 44, "Variação entre repetições: esquema de relato", 20, k.INK, True),
        k.curve_placeholder(
            135,
            82,
            900,
            220,
            "condições ou blocos comparados",
            "dispersão entre repetições",
            falling=False,
        ),
    ]
    return k.svg(
        1200,
        390,
        "Variação entre repetições, ilustrativa",
        "Eixos sem números e curva tracejada para indicar apenas uma forma de apresentação futura.",
        *parts,
    )


def fig_02_1() -> str:
    """Cenas esquematicas para tres fatores de captura."""
    parts = [
        k.text(40, 44, "Fatores de cena na avaliação da página", 20, k.INK, True),
        k.box(65, 105, 300, 90, "Iluminação", k.TEAL, "uniforme ou com sombra"),
        k.box(450, 105, 300, 90, "Oclusão", k.CLAY, "livre ou parcialmente encoberta"),
        k.box(
            835, 105, 300, 90, "Enquadramento", k.VIOLET, "centrado ou junto à borda"
        ),
        k.text(
            600,
            255,
            "Rótulos esquemáticos; cada variação exige cena anotada",
            16,
            k.MUTED,
            False,
            "middle",
        ),
    ]
    return k.svg(
        1200,
        310,
        "Fatores esquemáticos de cena",
        "Três categorias de cena sem fotografias ou resultados do sistema.",
        *parts,
    )


def fig_02_2() -> str:
    """Matriz vazia de fatores e niveis qualitativos."""
    parts = [
        k.text(40, 44, "Grade conceitual de condições", 20, k.INK, True),
        k.matrix(
            210,
            125,
            ["Luz", "Oclusão", "Enquadramento", "Fundo"],
            ["menor", "médio", "maior"],
            cell=80,
        ),
        k.text(
            600,
            475,
            "Células reservadas para o desenho do estudo",
            14,
            k.MUTED,
            False,
            "middle",
        ),
    ]
    return k.svg(
        1200,
        510,
        "Matriz de fatores de cena",
        "Células vazias para fatores e níveis descritos sem valores de resultado.",
        *parts,
    )


def fig_02_3() -> str:
    """Curva ilustrativa sem observacoes de deteccao."""
    parts = [
        k.text(40, 44, "Relação esperada entre cena e detecção", 20, k.INK, True),
        k.curve_placeholder(
            135,
            80,
            900,
            220,
            "nível qualitativo da perturbação",
            "desempenho de detecção",
        ),
    ]
    return k.svg(
        1200,
        390,
        "Forma ilustrativa de desempenho",
        "Eixos sem valores e curva tracejada, sem dados medidos.",
        *parts,
    )


def fig_01_1() -> str:
    """Geometria conceitual de camera e folha em pose inclinada."""
    page = (
        '<polygon points="760,110 1050,145 1015,315 725,280" '
        'fill="#FFFFFF" stroke="%s" stroke-width="3"/>' % k.VIOLET
    )
    parts = [
        k.text(40, 44, "Geometria conceitual da cena", 20, k.INK, True),
        k.box(70, 170, 210, 100, "Câmera", k.TEAL, "ponto de observação"),
        k.arrow(290, 220, 700, 220),
        page,
        k.text(870, 215, "Folha", 18, k.INK, True, "middle"),
        k.text(490, 195, "distância de captura", 15, k.MUTED, False, "middle"),
        k.text(955, 345, "pose angular", 15, k.MUTED, False, "middle"),
        k.text(
            600,
            385,
            "A posição e a orientação são condições de avaliação, não detalhes internos",
            15,
            k.MUTED,
            False,
            "middle",
        ),
    ]
    return k.svg(
        1200,
        430,
        "Geometria da câmera e da folha",
        "Câmera observando uma folha inclinada, com distância e orientação indicadas conceitualmente.",
        *parts,
    )


def fig_01_2() -> str:
    """Grade de distancia e angulo, avaliada em dois estados de movimento."""
    parts = [
        k.text(40, 44, "Grade de condições geométricas", 20, k.INK, True),
        k.matrix(
            245,
            145,
            ["perto", "intermediária", "distante"],
            ["ângulo menor", "ângulo médio", "ângulo maior"],
            cell=110,
        ),
        k.box(830, 145, 250, 75, "Folha parada", k.TEAL),
        k.box(830, 265, 250, 75, "Folha em movimento", k.CLAY),
        k.text(
            600,
            500,
            "Cada combinação de distância e ângulo é observada nos dois estados",
            15,
            k.MUTED,
            False,
            "middle",
        ),
    ]
    return k.svg(
        1200,
        540,
        "Grade de pose e distância",
        "Cruzamento qualitativo de ângulo e distância em estados parado e em movimento.",
        *parts,
    )


def fig_01_3() -> str:
    """Curva de erro por angulo apenas ilustrativa."""
    parts = [
        k.text(40, 44, "Erro geométrico por condição angular", 20, k.INK, True),
        k.curve_placeholder(
            135,
            80,
            900,
            220,
            "ângulo da folha (qualitativo)",
            "erro geométrico",
        ),
    ]
    return k.svg(
        1200,
        390,
        "Forma ilustrativa do erro por ângulo",
        "Eixos sem valores e curva tracejada, sem observações medidas.",
        *parts,
    )


def fig_04_1() -> str:
    """Tres esquemas de erro observavel na preservacao do traco."""
    panels = []
    for x, title, desc in [
        (55, "Deslocado", "posição divergente"),
        (445, "Fragmentado", "trecho ausente"),
        (835, "Repetido", "marca duplicada"),
    ]:
        color = k.TEAL if x == 55 else k.CLAY if x == 445 else k.VIOLET
        panels.append(
            f'<rect x="{x}" y="95" width="310" height="210" rx="12" '
            f'fill="#FFFFFF" stroke="{color}" stroke-width="2"/>'
        )
        panels.append(k.text(x + 155, 135, title, 16, k.INK, True, "middle"))
        panels.append(k.text(x + 155, 340, desc, 15, k.MUTED, False, "middle"))
    panels.extend(
        [
            '<path d="M95 205 L315 205" fill="none" stroke="%s" stroke-width="4" stroke-dasharray="8 5"/>'
            % k.MUTED,
            '<path d="M95 260 L315 260" fill="none" stroke="%s" stroke-width="4"/>'
            % k.CLAY,
            '<path d="M485 215 L555 215 M600 215 L685 215" fill="none" stroke="%s" stroke-width="4" stroke-dasharray="8 5"/>'
            % k.MUTED,
            '<path d="M485 260 L535 260 M625 260 L685 260" fill="none" stroke="%s" stroke-width="4"/>'
            % k.CLAY,
            '<path d="M875 235 L1095 235" fill="none" stroke="%s" stroke-width="4" stroke-dasharray="8 5"/>'
            % k.MUTED,
            '<path d="M875 215 L1095 215 M875 265 L1095 265" fill="none" stroke="%s" stroke-width="3"/>'
            % k.CLAY,
            k.text(
                600,
                390,
                "Tracejado: referência independente; linha contínua: exemplo observado",
                14,
                k.MUTED,
                False,
                "middle",
            ),
        ]
    )
    return k.svg(
        1200,
        430,
        "Erros observáveis de preservação da tinta",
        "Traço esquemático deslocado, interrompido ou duplicado em relação a referência.",
        k.text(40, 44, "Três discrepâncias da tinta em uma sequência", 20, k.INK, True),
        *panels,
    )


def fig_04_2() -> str:
    """Sequencia conceitual de observacoes e comparacao final."""
    parts = [
        k.text(40, 44, "Sequência de observação da tinta", 20, k.INK, True),
        k.box(70, 105, 260, 90, "Início", k.TEAL, "traço de referência"),
        k.box(470, 105, 260, 90, "Durante", k.CLAY, "observação intermediária"),
        k.box(870, 105, 260, 90, "Final", k.VIOLET, "digitalização independente"),
        k.arrow(330, 150, 460, 150),
        k.arrow(730, 150, 860, 150),
        k.timeline(
            120, 285, 960, [(0.0, "início"), (0.5, "movimento"), (1.0, "encerramento")]
        ),
        k.text(
            600,
            365,
            "As imagens de referência são comparadas fora da cadeia interna",
            15,
            k.MUTED,
            False,
            "middle",
        ),
    ]
    return k.svg(
        1200,
        420,
        "Sequência de quadros conceitual",
        "Início, observação durante a atividade e digitalização final como evidências externas.",
        *parts,
    )


def fig_04_3() -> str:
    """Forma de degradacao ilustrativa sem dados."""
    parts = [
        k.text(40, 44, "Deriva do traço sob movimento", 20, k.INK, True),
        k.curve_placeholder(
            135,
            80,
            900,
            220,
            "nível de movimento (qualitativo)",
            "deriva do traço",
        ),
    ]
    return k.svg(
        1200,
        390,
        "Forma ilustrativa de deriva",
        "Eixos sem valores e curva tracejada, sem observações medidas.",
        *parts,
    )


def fig_05_1() -> str:
    """Posturas conceituais com oclusao em regioes distintas."""
    parts = [k.text(40, 44, "Oclusão em posturas de desenho", 20, k.INK, True)]
    panels = [
        (55, "mão junto à borda"),
        (445, "mão sobre o centro"),
        (835, "instrumento próximo"),
    ]
    for x, label in panels:
        parts.append(
            f'<rect x="{x}" y="100" width="310" height="230" rx="12" fill="#FFFFFF" stroke="{k.LINE}" stroke-width="2"/>'
        )
        parts.append(
            f'<rect x="{x + 38}" y="155" width="234" height="125" rx="5" fill="#F4F6F4" stroke="{k.TEAL}" stroke-width="2"/>'
        )
        parts.append(
            f'<path d="M{x + 62} 245 L{x + 235} 190" fill="none" stroke="{k.MUTED}" stroke-width="3"/>'
        )
        parts.append(k.text(x + 155, 365, label, 14, k.MUTED, False, "middle"))
    parts.extend(
        [
            f'<ellipse cx="150" cy="210" rx="45" ry="28" fill="{k.CLAY}" opacity="0.78"/>',
            f'<ellipse cx="600" cy="218" rx="52" ry="35" fill="{k.CLAY}" opacity="0.78"/>',
            f'<path d="M900 185 L1015 250" stroke="{k.VIOLET}" stroke-width="14" stroke-linecap="round"/>',
            k.text(
                600,
                410,
                "Formas simplificadas indicam apenas regiões encobertas",
                14,
                k.MUTED,
                False,
                "middle",
            ),
        ]
    )
    return k.svg(
        1200,
        450,
        "Posturas esquemáticas de oclusão",
        "Mão ou instrumento representados por formas simples sobre uma página desenhada.",
        *parts,
    )


def fig_05_2() -> str:
    """Matriz conceitual de duracao e regiao encoberta."""
    parts = [
        k.text(40, 44, "Duração e região da oclusão", 20, k.INK, True),
        k.matrix(
            230,
            135,
            ["breve", "intermediária", "longa"],
            ["borda", "centro", "mista"],
            cell=95,
        ),
        k.text(
            650,
            455,
            "Movimento da mão é registrado como eixo adicional",
            14,
            k.MUTED,
            False,
            "middle",
        ),
    ]
    return k.svg(
        1200,
        500,
        "Matriz qualitativa de oclusão",
        "Grade vazia para cruzar duração e região com o movimento registrado separadamente.",
        *parts,
    )


def fig_05_3() -> str:
    """Forma ilustrativa de desempenho segundo fracao ocluida."""
    parts = [
        k.text(40, 44, "Desempenho e fração ocluída", 20, k.INK, True),
        k.curve_placeholder(
            135,
            80,
            900,
            220,
            "fração da região encoberta (qualitativa)",
            "desempenho",
        ),
    ]
    return k.svg(
        1200,
        390,
        "Curva ilustrativa de oclusão",
        "Eixos sem valores e curva tracejada, sem observações medidas.",
        *parts,
    )


FIGURES = {
    "08-latencia-cadeia.svg": fig_08_1,
    "08-distribuicao-latencia.svg": fig_08_2,
    "08-atraso-controlado.svg": fig_08_3,
    "02-fatores-cena.svg": fig_02_1,
    "02-matriz-fatores.svg": fig_02_2,
    "02-curva-deteccao.svg": fig_02_3,
    "01-geometria-cena.svg": fig_01_1,
    "01-grade-condicoes.svg": fig_01_2,
    "01-erro-angulo.svg": fig_01_3,
    "04-tres-erros.svg": fig_04_1,
    "04-sequencia-quadros.svg": fig_04_2,
    "04-deriva-movimento.svg": fig_04_3,
    "05-posturas-oclusao.svg": fig_05_1,
    "05-matriz-oclusao.svg": fig_05_2,
    "05-fração-ocluida.svg": fig_05_3,
    "06-catalogo-perturbacoes.svg": fig_06_1,
    "06-protocolo-variacao.svg": fig_06_2,
    "06-curva-degradacao.svg": fig_06_3,
    "03-timeline-identidade.svg": fig_03_1,
    "03-decisoes-identidade.svg": fig_03_2,
    "03-erro-ausencia.svg": fig_03_3,
    "10-rastreabilidade.svg": fig_10_1,
    "10-niveis-reprodutibilidade.svg": fig_10_2,
    "10-variacao-repeticoes.svg": fig_10_3,
}


def main() -> None:
    out = Path(__file__).parent
    for name, fn in FIGURES.items():
        (out / name).write_text(fn(), encoding="utf-8")
        print("ok", name)


if __name__ == "__main__":
    main()
