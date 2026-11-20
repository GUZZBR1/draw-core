# Plano de melhoria dos 12 artigos (para execução pelo Codex)

Escopo: só `docs/research/`. Não mexer em `site/`, `src/`, `pyproject.toml` nem em `assets/`. Não fazer commit.

## 0. Diagnóstico

Os 12 rascunhos têm de 265 a 361 palavras e o mesmo molde de 6 seções. Não têm introdução com lacuna, trabalhos relacionados, referências, método, tabelas nem figuras de evidência. "Limitações" e "Revisão de divulgação" são notas internas que ocupam o lugar do conteúdo. Cada texto diz o que "poderia" ser feito e nunca o que está definido.

**Referência estudada (IEEE 9285357):** "Avionics Systems Panel Research and Innovation Perspectives", IEEE Aerospace and Electronic Systems Magazine, dez. 2020. É um artigo de **perspectiva** (sem experimento próprio), com cerca de 7.800 palavras, 5 seções numeradas (Introdução, Panorama, Programas, Evolução, Conclusão), 5 figuras com legenda, glossário de siglas e cerca de 40 referências. Resumo de uns 220 palavras em um parágrafo. A lição: dá para ter um artigo forte sem dados próprios, desde que haja estrutura, literatura e figuras.

**Referências SciELO:** o texto sobre IA diz que ela pode ajudar em tradução, revisão de linguagem e organização, mas não substitui autoria nem senso crítico, e que os riscos são referência inventada, plágio e dado falso. O texto "futuro do artigo" defende código e dados auditáveis e cita a checagem de referências do Crossref contra a lista do PDF.

## 1. Estratégia: duas fases

- **Fase 1 (esta, o Codex faz):** transformar cada rascunho em **artigo de proposta de avaliação**, no formato de perspectiva do IEEE: contexto, literatura, taxonomia, protocolo de avaliação e estrutura de resultados. Não precisa de dados.
- **Fase 2 (depois, com medições):** preencher a seção 5 com resultados reais e ajustar resumo e conclusão. Ela não é tarefa do Codex.

## 2. Regras que valem para todos (invioláveis)

1. **Nunca inventar** número, resultado, percentual, nome de participante ou referência. Sem dado medido, a seção de resultados só descreve o que será reportado, usando `[PENDENTE-DADOS]` nos lugares dos números.
2. **Referências:** só entram se o Codex abrir o DOI ou a página e confirmar autor, título, ano e veículo (por exemplo `curl -s https://api.crossref.org/works/<DOI>`). Sem acesso à internet, marcar `[VERIFICAR: tema]` e não inventar. O texto não pode ser dado como concluído com `[VERIFICAR` ainda presente.
3. **Divulgação:** descrever o sistema só como "um sistema de desenho assistido por câmera". Não citar nome de modelo, biblioteca, formato interno, limiar, parâmetro, regra, ordem das etapas nem pseudocódigo. Teste por parágrafo: isso permite reconstruir o Draw? Se sim, cortar.
4. **Linguagem:** português do Brasil, frases de até 30 palavras em média, parágrafos de 80 a 220 palavras, voz impessoal, siglas explicadas na primeira vez. Sem adjetivos de propaganda ("inovador", "robusto", "estado da arte") sem evidência.
5. **Backup:** antes de começar, copiar os 12 originais para `docs/research/v1/` (`mkdir -p docs/research/v1 && cp docs/research/[01]*.md docs/research/v1/`). Só então sobrescrever.
6. **Declarar o uso de IA** na seção de declarações: "texto redigido com apoio de IA generativa, com revisão e responsabilidade dos autores; referências conferidas por DOI".

## 3. Molde e mínimos (todos os artigos)

Título `# ...` com até 20 palavras. Seções com `##` e estes nomes exatos, nesta ordem:

| Seção | Mínimo | Conteúdo |
|---|---|---|
| `## Resumo` | 150 a 250 palavras | 1 parágrafo: contexto, lacuna, o que o artigo faz, o que entrega, limite. Linha `**Palavras-chave:** a; b; c; d` (4 a 6) |
| `## Abstract` | 150 a 250 palavras | Tradução fiel do resumo, mais `**Keywords:**` (4 a 6) |
| `## 1. Introdução` | 600 palavras | Contexto, lacuna, pergunta, lista de 3 contribuições, roteiro das seções |
| `## 2. Trabalhos relacionados` | 900 palavras, 3 subseções `###`, 12 citações | Grupos temáticos da literatura e, no fim, a lacuna |
| `## 3. Enquadramento do problema` | 700 palavras | Núcleo conceitual específico de cada artigo (ver seção 4) |
| `## 4. Protocolo de avaliação proposto` | 900 palavras, 1 tabela de métricas | Condições, dados, métricas, análise, ameaças; sistema como caixa-preta |
| `## 5. Estrutura dos resultados` | 250 palavras | O que será reportado, com tabelas e figuras vazias (`[PENDENTE-DADOS]`). Sem número de resultado |
| `## 6. Discussão` | 400 palavras | O que cada desfecho possível significaria; relação com a literatura |
| `## 7. Limitações e ameaças à validade` | 300 palavras | Interna, externa, de construção, de dados |
| `## 8. Conclusão` | 150 a 320 palavras | O que foi proposto e o que falta |
| `## Declarações` | 6 itens com `- ` | IA, dados, código, conflito de interesses, ética, contribuição dos autores |
| `## Referências` | 25 itens, `[1] Autor. Título. Veículo, ano. https://doi.org/...` | Todas com DOI ou URL |

**Totais:** corpo (seções 1 a 8) com pelo menos **4.500 palavras** e **28.000 caracteres** (com espaços). Alguns artigos pedem mais (seção 4). Pelo menos **3 figuras** e **2 tabelas**, cada uma com a linha `**Figura N.** legenda` ou `**Tabela N.** legenda`, com **25 palavras ou mais** de legenda, citada no texto antes de aparecer. Figuras em `docs/research/figures/` como SVG (reaproveitar os existentes quando servirem; criar novos só com formas simples e rótulos legíveis, sem mostrar internos do sistema). Para figura existente: `![](figures/arquivo.svg)` logo acima da legenda.

### 3.1 Figuras próprias (como no artigo de aviônica)

O artigo de aviônica (IEEE) tem 5 figuras, e **todas são diagramas conceituais**, não gráficos de dados: áreas de foco do setor, arquitetura do sistema, desafios de certificação, evolução em etapas e o conceito de uma interface. Cada uma tem legenda curta e fonte. O nosso segue o mesmo padrão. **Não copiar nem redesenhar as imagens dele** (têm direitos autorais). Só o tipo de figura serve de modelo.

**Tipos de figura que podemos fazer agora, sem dados:**

| Tipo | Quando usar | Função em `figkit.py` |
|---|---|---|
| Visão geral / arquitetura conceitual (caixa-preta) | F1 de quase todo artigo | `row`, `box`, `arrow` |
| Fluxo ou cadeia de medição | 01, 08, 09, 10, 12 | `row`, `arrow` |
| Taxonomia ou matriz de condições | 02, 03, 05, 06, 11 | `matrix`, `box` |
| Linha do tempo de eventos | 03, 04, 05 | `timeline` |
| Curva de forma esperada (eixos sem números) | 01, 05, 06, 07, 08, 12 | `curve_placeholder` |

**Regras das figuras:**
1. SVG de 1200 de largura, fundo e cores de `figkit.py` (as mesmas das figuras já existentes), fonte Arial, texto de 13 px ou mais, título dentro da figura.
2. **Curva sem dados é sempre ilustrativa:** eixos sem números e o rótulo "ILUSTRATIVO · sem dados medidos" (a função `curve_placeholder` já faz isso). Na legenda, dizer "forma esperada, não é resultado". Nunca desenhar curva com valores inventados ou que pareça medida.
3. Mostrar o sistema só como caixa-preta (regra 3). Sem módulos internos, sem ordem das etapas.
4. Legenda de 25 palavras ou mais, citada no texto antes da figura, com fonte quando for adaptada ("Elaboração própria" quando for nossa).
5. Cada figura é uma função em `docs/research/figures/make_figures.py` e uma linha no dicionário `FIGURES`. O nome do arquivo segue `NN-assunto.svg`. Rodar `python3 -I docs/research/figures/make_figures.py`, `.venv/bin/ruff format docs/research/figures` e `.venv/bin/ruff check docs/research/figures`. Copiar o padrão das duas figuras de exemplo (`fig_08_1` e `fig_06_3`).
6. Conferir cada SVG abrindo o arquivo (texto cortado, sobreposição, setas fora das caixas). Se não puder abrir, simplificar.

**Fase 2 (com dados):** os gráficos de resultado (barras com intervalo de confiança, curvas, dispersões, matrizes de confusão) saem de um script que lê uma planilha `docs/research/data/NN-nome.csv`, com a versão do script e a semente registradas na legenda. Não criar esses gráficos antes de existir o CSV. Quando existirem, trocam as curvas ilustrativas, e o rótulo "ILUSTRATIVO" some.

**Fotos reais** (montagem experimental, cenas de captura) entram só na fase 2, com consentimento das pessoas e sem mostrar telas internas.

**Verificação automática (rodar a cada artigo):**

```
python3 -I docs/research/check_paper.py docs/research/NN-nome.md --min-total <N> --min-refs <N>
```

O script confere seções, palavras, caracteres, legendas, declarações, referências, `[VERIFICAR`, termos proibidos e números na seção 5. Corrigir até aparecer `OK`.

## 4. Plano por artigo

Formato de cada um: **hoje** (o que está fraco), **melhorar como**, **mínimos próprios**, **figuras e tabelas**, **buscar na literatura**, **não dizer**.

### 01. Geometria da folha (`01-geometria-matematica.md`)
- **Hoje:** diz que a página muda de pose, mas não define o que é "estabilidade espacial" nem quais poses interessam.
- **Como:** na seção 3, definir as grandezas (pose da folha, deslocamento do traço, erro relativo à largura da folha) e dividir a pose em ângulo, distância e movimento. Na seção 4, grade de condições (ângulo × distância × parada/em movimento) e métricas (erro em mm e como fração da largura da folha, taxa de falha). Sempre uma linha de base clássica genérica para comparar.
- **Mínimos:** corpo 5.000 palavras; 25 referências; seção 3 ≥ 800 palavras com uma tabela de grandezas e unidades.
- **Figuras:** F1 geometria da cena (câmera, folha, ângulo), F2 esquema da grade de condições, F3 forma do gráfico erro × ângulo (vazio). T1 grandezas e unidades, T2 condições e métricas.
- **Literatura:** geometria projetiva e homografia (Hartley e Zisserman), calibração de câmera, retificação de documentos, rastreamento planar.
- **Não dizer:** como a pose é estimada, quais pontos ou marcadores internos, qual transformação usada.

### 02. Achar a página (`02-visao-computacional-pagina.md`)
- **Hoje:** lista fatores (luz, oclusão, enquadramento) sem definir "detecção correta".
- **Como:** na seção 3, definir detecção correta (por exemplo, sobreposição mínima entre a região prevista e a anotada, e erro de cantos) como conceito, sem valor fixo. Na seção 4, fatores variados de forma balanceada e métricas: recall, precisão, sobreposição média, erro de cantos, tempo até a primeira detecção.
- **Mínimos:** corpo 5.000; 25 refs; seção 4 ≥ 1.000 palavras.
- **Figuras:** F1 exemplos de cena por fator (placeholders descritos), F2 tabela de fatores × níveis em figura de matriz, F3 forma do gráfico acerto por fator. T1 fatores e níveis, T2 métricas e definições.
- **Literatura:** detecção e retificação de documentos fotografados, benchmarks de documentos por câmera, segmentação clássica, avaliação por IoU.
- **Não dizer:** qual detector ou segmentador, formato dos modelos.

### 03. Identidade da folha (`03-identidade-rastreamento-pagina.md`)
- **Hoje:** fala em "taxonomia de eventos" mas nunca a apresenta.
- **Como:** a seção 3 **é** a taxonomia: eventos (permanece, desloca, some, volta, aparece outra parecida, aparece outra diferente), decisões possíveis (continuar, nova, adiar) e custo de cada erro (fundir folhas distintas × separar a mesma). Apresentar em tabela.
- **Mínimos:** corpo 4.800; 25 refs; seção 3 ≥ 900 palavras com uma tabela evento × decisão × consequência.
- **Figuras:** F1 linha do tempo de uma sessão com saída e retorno, F2 diagrama de decisões e erros, F3 forma da curva de erro × tempo de ausência. T1 taxonomia, T2 métricas (reidentificação certa, fusão indevida, separação indevida).
- **Literatura:** reidentificação, rastreamento de objetos, associação de identidade, recuperação de imagem, gestão de incerteza.
- **Não dizer:** como a identidade é calculada nem o tempo de espera.

### 04. Preservar a tinta (`04-preservacao-tinta.md`)
- **Hoje:** cita "deslocado, fragmentado, repetido" sem definição.
- **Como:** seção 3 define os três tipos de erro operacionalmente em linguagem comum e propõe como medi-los (comparação com o desenho final digitalizado ao longo do tempo). Seção 4: níveis de movimento (parada, pequeno, grande) e apagamento.
- **Mínimos:** corpo 4.800; 25 refs; tabela com os 3 erros (definição, como medir, unidade).
- **Figuras:** F1 exemplos esquemáticos dos 3 erros, F2 sequência de quadros (esquema), F3 forma do gráfico deriva × movimento. T1 erros, T2 condições.
- **Literatura:** consistência temporal em vídeo, registro e mosaico de imagens, digitalização de quadros brancos, similaridade de traços.
- **Não dizer:** como o traço é acumulado, filtrado ou fundido.

### 05. Mão e caneta (`05-oclusoes-mao-instrumento.md`)
- **Hoje:** a ideia central (oclusão é uso normal) aparece só no site, não no texto.
- **Como:** abrir a introdução com ela. Seção 3 propõe uma classificação por **duração**, **movimento** e **região encoberta** (cada eixo com níveis) e uma medida de fração ocluída. Seção 4 liga cada nível ao efeito esperado em detecção e continuidade e inclui tempo de recuperação após a mão sair.
- **Mínimos:** corpo 4.800; 25 refs; tabela 3 eixos × níveis.
- **Figuras:** F1 exemplos esquemáticos de oclusão por postura, F2 matriz duração × região, F3 forma do gráfico desempenho × fração ocluída. T1 classificação, T2 métricas.
- **Literatura:** oclusão em rastreamento, segmentação de mão, interação com caneta e papel, mesas digitais.
- **Não dizer:** como a mão é detectada ou tratada.

### 06. Mundo real (`06-robustez-condicoes-reais.md`)
- **Hoje:** genérico ("fatores ambientais") sem lista.
- **Como:** seção 3 apresenta um **catálogo de perturbações** com nome, como medir o nível e como variar em teste: reflexo, sombra, desfoque, ruído, dobra e amassado, fundo, cor do papel, fonte de luz. Seção 4: variar uma por vez e depois combinadas; curva de degradação e análise de sensibilidade.
- **Mínimos:** corpo 5.000; 25 refs; catálogo com pelo menos 8 perturbações em tabela.
- **Figuras:** F1 catálogo ilustrado, F2 protocolo de variação gradual, F3 forma da curva de degradação. T1 catálogo, T2 métricas de robustez.
- **Literatura:** robustez a corrupções comuns, avaliação em ambientes não controlados, benchmarks de robustez.
- **Não dizer:** quais perturbações o sistema trata internamente.

### 07. Dados sintéticos (`07-simulacao-dados-sinteticos.md`)
- **Hoje:** não tem a seção "Problema" preenchida e a pergunta fica solta.
- **Como:** abrir a introdução com o problema (gravar de forma sistemática é caro). Seção 3: o que a simulação pode e não pode representar, em quadro de cobertura. Seção 4: pares real × simulado por condição, medir se a ordem de dificuldade se mantém (correlação por condição) e a lacuna.
- **Mínimos:** corpo 4.800; 25 refs; quadro "pode representar / não pode / precisa de evidência real".
- **Figuras:** F1 par real × simulado (esquema), F2 fluxo de validação da simulação, F3 forma do gráfico simulado × real. T1 quadro de cobertura, T2 métricas de concordância.
- **Literatura:** lacuna sim-real, randomização de domínio, validade de dados sintéticos para teste.
- **Não dizer:** como o gerador de cenas funciona.

### 08. Tempo de resposta (`08-desempenho-temporal.md`)
- **Hoje:** diz que velocidade importa, sem definir o que se mede nem referência de percepção.
- **Como:** seção 3 define latência de ponta a ponta, jitter, quadros perdidos e distribuição (mediana, p95, p99), e cita os limiares clássicos de percepção de resposta de Nielsen como contexto (conferir a fonte). Seção 4: dispositivos de classes diferentes, atividades diferentes, medição externa por vídeo de alta taxa, e um teste opcional com atraso injetado.
- **Mínimos:** corpo 4.800; 25 refs; tabela de métricas com definição formal (uma fórmula é aceitável aqui).
- **Figuras:** F1 diagrama da cadeia de medição (caixa-preta: câmera → resposta visível), F2 exemplo de distribuição (forma), F3 desenho do teste com atraso injetado. T1 métricas, T2 dispositivos (classes, não modelos).
- **Literatura:** latência em interação humano-computador, percepção de latência em tinta digital, sistemas em tempo real.
- **Não dizer:** tempo por etapa interna, ordem das etapas.

### 09. Do papel ao arquivo (`09-exportacao-geometria.md`)
- **Hoje:** "fidelidade geométrica" sem dizer quais aspectos.
- **Como:** seção 3 lista **aspectos de fidelidade** (posição, escala, espessura, forma, ordem dos traços, cor) e para qual uso cada um importa (edição, documentação, impressão, integração). Seção 4: desenhos de referência, reimportação em ferramentas comuns, comparação com a digitalização do original, tolerância justificada por uso.
- **Mínimos:** corpo 4.800; 25 refs; tabela aspecto × uso × como medir.
- **Figuras:** F1 do papel ao arquivo (visão geral conceitual), F2 original × exportado sobreposto (esquema), F3 matriz de compatibilidade (vazia). T1 aspectos, T2 formatos de destino (por categoria).
- **Literatura:** formatos vetoriais, vetorização de imagens, fidelidade de exportação, arquivamento digital.
- **Não dizer:** formato interno, como a geometria é gerada, parâmetros de simplificação.

### 10. Reprodutibilidade (`10-reprodutibilidade-integridade.md`)
- **Hoje:** fala em "princípios de alto nível" sem listá-los. É o que mais se beneficia de lista de verificação.
- **Como:** seção 3 propõe uma **lista de verificação** com pelo menos 15 itens agrupados em dados, modelos, configuração, ambiente, execução e relato. Seção 4: estudo de caso conceitual (repetir um experimento em máquinas e datas diferentes) e variação aceitável. Citar FAIR (Wilkinson et al.), datasheets (Gebru et al.) e model cards (Mitchell et al.).
- **Mínimos:** corpo 5.500; 30 refs; lista de verificação ≥ 15 itens em tabela com "o que registrar" e "por quê".
- **Figuras:** F1 fluxo de rastreabilidade (conceitual), F2 níveis de reprodutibilidade (repetir, replicar, reproduzir), F3 forma do gráfico de variação entre repetições. T1 lista de verificação, T2 comparação com práticas existentes.
- **Literatura:** FAIR, datasheets, model cards, listas de reprodutibilidade de conferências, pesquisa reproduzível em software.
- **Não dizer:** como a integridade dos modelos é verificada, nome do manifesto, algoritmo de hash, políticas internas.

### 11. Acessibilidade (`11-acessibilidade-interacao.md`)
- **Hoje:** boa intenção, mas sem critérios nem método.
- **Como:** seção 3 organiza **barreiras** em motoras, visuais, cognitivas, de equipamento, de espaço e de conectividade. Seção 4: auditoria contra WCAG 2.x e estudo com participantes diversos, com aprovação de comitê de ética, consentimento, critérios de recrutamento e instrumentos (SUS, NASA-TLX, entrevista).
- **Mínimos:** corpo 5.000; 30 refs; tabela barreira × critério × como avaliar; declaração de ética explícita ("a ser submetido ao comitê").
- **Figuras:** F1 mapa de barreiras, F2 fluxo do estudo com participantes, F3 perfil planejado da amostra (vazio). T1 barreiras, T2 instrumentos.
- **Literatura:** WCAG, tecnologia assistiva, acessibilidade em criação e desenho, interação por câmera.
- **Não dizer:** nada interno do sistema; evitar generalizar para "todos os usuários".

### 12. Experiência (`12-qualidade-experiencia.md`)
- **Hoje:** lista dimensões (continuidade, previsibilidade, recuperação, controle) sem ligar a medidas.
- **Como:** seção 3 define cada dimensão e propõe o par **medida técnica ↔ item de questionário** (por exemplo, tempo de recuperação ↔ "o desenho voltou ao normal rápido"). Seção 4: estudo com pessoas desenhando, medida técnica e percepção na mesma sessão, análise por correlação e modelo simples, com cuidado de não afirmar causa.
- **Mínimos:** corpo 5.200; 30 refs; tabela dimensão × medida técnica × item do questionário (≥ 8 linhas).
- **Figuras:** F1 modelo conceitual medida → percepção, F2 desenho do estudo, F3 forma do gráfico técnica × percebida. T1 dimensões e medidas, T2 instrumentos.
- **Literatura:** qualidade de experiência (QoE), usabilidade (SUS), carga de trabalho (NASA-TLX), percepção de continuidade.
- **Não dizer:** causas internas; manter a diferença entre observação e interpretação. **Fazer por último**, pois cita 02, 04, 05 e 08.

## 5. Ordem de execução (um artigo por vez, o Codex é lento)

1. Criar `docs/research/v1/` com os originais (regra 5).
2. Ordem: 10, 08, 02, 01, 04, 05, 06, 03, 07, 09, 11, 12.
3. Para cada artigo: ler a seção 2 e a seção 3 deste plano e o item do artigo na seção 4; reescrever o arquivo; rodar o verificador com os mínimos do item; corrigir até `OK`; seguir para o próximo.
4. Escrever em etapas: primeiro o esqueleto com os títulos e as legendas, depois as seções na ordem, depois referências. Não tentar gerar o artigo inteiro de uma vez.
5. No fim, atualizar o `README.md` da pasta e rodar o verificador nos 12.
6. Parar e avisar se faltar internet (referências) ou se algum mínimo for impossível sem inventar conteúdo. Nunca preencher com texto de enchimento só para bater a contagem.

## 6. Revisão (outra passada, depois do Codex)

Teste de divulgação, conferência de cada referência por DOI, checagem de números e uma leitura por quem não escreveu o texto. Esta passada não é do Codex.

## 7. Prompt para colar no Codex

> Leia `docs/research/PLANO-MELHORIA.md` inteiro. Siga as seções 2, 3 e 5. Trabalhe só em `docs/research/`. Comece pelo artigo 10 (`10-reprodutibilidade-integridade.md`) usando o item correspondente da seção 4. Faça o backup em `docs/research/v1/`, reescreva o artigo, rode `python3 -I docs/research/check_paper.py docs/research/10-reprodutibilidade-integridade.md --min-total 5500 --min-refs 30` e corrija até aparecer OK. Não invente números nem referências. Não faça commit. Ao terminar, pare e liste o que ficou pendente (por exemplo, `[VERIFICAR]`). Só então siga para o próximo.
