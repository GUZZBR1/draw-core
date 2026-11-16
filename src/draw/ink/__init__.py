"""Tinta em camadas: acumulador com voto e a trabalhadora page-clean.

O acumulador guarda a tinta de uma geracao em duas camadas — a
provisoria, que a primeira passada viu, e a confirmada, que o voto
entre passadas fechou (com a porta de fronteira contra o ombro do
tremor). A trabalhadora roda as passadas em thread propria com a
cadencia de _PAGE_CLEAN_INTERVAL_SECONDS, a porta de ociosidade
sem mao, o descanso total de pagina assentada .

Extraido de draw/app.py na modularizacao de 2026-11-05; o app
re-exporta todos os nomes deste modulo. As constantes de cadencia
e descanso sao lidas deste modulo em tempo de execucao: quem
precisa muda-las (os testes) patcheia aqui, onde a leitura mora.
"""

from .accumulator import LayeredInkAccumulator
from .config import InkConfig
from .render import render_canvas, render_layered_canvas
from .worker import PageCleanWorker

__all__ = [
    "InkConfig",
    "LayeredInkAccumulator",
    "PageCleanWorker",
    "render_canvas",
    "render_layered_canvas",
]
