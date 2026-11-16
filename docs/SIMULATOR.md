# Simulador fechado de escrita

O simulador planeja texto como movimentos de caneta, escreve num papel
sintético em perspectiva e entrega imagens BGR ao mesmo laço de captura,
detecção, retificação e tinta do Draw. O ground truth só entra na avaliação
depois da captura. Nenhum estágio recebe cantos ou máscaras verdadeiros
para facilitar a detecção.

Os módulos vivem em `lab/` (fora do runtime): `gen_synthetic.py`
(corpus/cena), `sim_text.py` (planejador de escrita), `sim_isp.py`
(gêmeo óptico/físico) e `sim_source.py` (fonte de captura e exportador).

## Gerar e observar

Na raiz do repositório, com o venv do projeto:

```sh
python lab/sim_source.py --text "Olá, Draw!" --out captures/sim.mp4
```

O exportador grava `sim.mp4` (512×512, codec `mp4v`), `sim.gt.npz`,
`sim_ink_full.npy` e `sim.json`. O bundle NPZ contém o desenho completo no
espaço da câmera na pose final (`ink_full`), o estado final da tinta
pós-borracha/redesenho na mesma pose (`ink_final`), ambos no espaço
original do papel (`page_ink_full`, `page_ink_final`), a homografia
papel→câmera inicial e final, e as polylines individuais. Fases
geométricas declaram `quad_end` em `events` — a pose no último frame
da fase — para reconstrução por checkpoint. Não usa pickle. O
manifesto identifica seed, FPS, número de frames, traços e se há mão
placeholder. Os campos `*_final` são determinísticos: o GT sai correto
antes ou depois de consumir o vídeo.

O planejamento suporta letras latinas, dígitos, pontuação básica, acentos
portugueses, espaços e novas linhas. Maiúsculas usam formas cursivas
minúsculas ampliadas. Uma tabela vetorial de glifos, interpolada por
Catmull–Rom com jitter suave, gera laços e ligaduras entre letras;
pontos, acentos e outras levantadas de caneta são specs separadas.
O texto quebra na margem por caractere. Caracteres desconhecidos ou
texto que excede uma página geram erro explícito. Não é um modelo de
caligrafia humana nem uma fonte tipográfica completa.

```sh
python lab/sim_source.py --text "ação 123" --seed 7 --fps 15 \
  --stroke-seconds 0.3 --warmup-seconds 1 --settle-seconds 4 \
  --height 22 --hand --out captures/sim.mp4
```

Há um intervalo inicial sem tinta, crescimento progressivo dentro de
cada traço e um intervalo final sem mão para o acumulador confirmar o
desenho. `--hand` usa a mão sintética placeholder existente, acompanhando
a ponta da caneta; a máscara visível respeita mão sobre tinta e o
`ink_full` continua completo. FPS/tempos controlam a dinâmica. A pose
da folha é fixa, com textura, fundo e ruído de sensor do gerador original.
Movimento de papel e comportamento real de mão/modelos exigem outros
cenários; os resultados aqui são exclusivamente sintéticos.

## Cenário escrever → apagar → redesenhar → mover

A fonte também encadeia fases além da escrita: uma borracha visível
varre uma região da folha e devolve o papel original, um segundo texto
cai sobre a área limpa e a folha desliza/gira no fim. As fases são
declaradas no GT (`events`, `stroke_phase` 0 para o texto inicial e 1
para o redesenho, `stroke_erased`, `erase_rect`, `page_ink_final` com o
estado real da folha no fim e as poses inicial/final). Sem os flags, a
linha do tempo é exatamente warmup → escrita → settle, como sempre foi.

```sh
python lab/sim_source.py --text "Draw ok" --seed 7 --fps 15 \
  --stroke-seconds 0.3 --warmup-seconds 2 --settle-seconds 8 \
  --height 26 --hand --erase-stroke -1 --redraw-text "ui" \
  --erase-seconds 1.2 --hold-seconds 6 \
  --move 35,22,2.5 --move-seconds 0.8 --out captures/sim-e3.mp4
```

`--erase-stroke N` apaga a caixa do traço N (índice negativo conta do
fim); `--erase-rect x,y,w,h` apaga um retângulo explícito em pixels de
página. As duas opções são alternativas. `--redraw-text` exige uma
região apagada e centraliza o novo texto nela. `--hold-seconds` é a
parada de cena entre fases — dê passadas suficientes para a confirmação
amadurecer antes do próximo evento. `--move dx,dy,graus` desloca e gira
a folha em `move-seconds`; sem ele, não há fase de movimento.

## Cenário lift & return (folha sai de cena e volta)

`--lift dx,dy` encadeia três fases depois das anteriores: `lift_out`
(a folha desliza até sair do frame), `absent` (só a mesa na cena por
`--absent-seconds` — a tinta vai junto, fica na folha) e `return` (a
folha desliza de volta). `--return-pose dx,dy,graus` define a pose do
retorno relativa à pose de saída — rotação de verdade, como quem pega
a folha, vira e repousa. É o gesto mais comum da mesa real e o que
mais estressa a vigia de identidade: mesma página ou página nova?

```sh
python lab/sim_source.py --text "Draw v6" --fps 15 \
  --warmup-seconds 1 --settle-seconds 8 --hold-seconds 4 \
  --lift 400,250 --return-pose -50,40,20 \
  --absent-seconds 2.5 --out captures/sim-lift.mp4
```

### Limite medido do detector (2026-11-12, bancada do legado)

A primeira auditoria deste cenário expôs um gap de dados, não de
código: a folha retorna rodada 20° e **nenhum dos seis modelos de
segmentação instalados a reconhece** — logit de presença ~-6,5 por
8 s de settle com a folha inteira visível. Girando um frame que o
modelo detecta, o envelope sai: logit positivo até ~12°, cruza zero
perto de 15°, fundo confiante a partir de 20°. O gerador de corpus
amostra rotação em `uniform(-18°, 18°)` (`_sample_normal_quad`,
lab/gen_synthetic.py) — a folha nunca existiu no treino além desse
teto, e o modelo falha logo na borda dele. Rotacionar a folha é gesto
rotineiro na mesa real; a correção é augment de rotação no corpus do
próximo treino, e este cenário vira a bancada de regressão dele.

## Cenário mão em massa (palma, sweep, pegada)

A mão de instrumento (`--hand`) só existe colada na caneta/borracha —
o que o humano faz com a mão SEM instrumento nunca estressava o laço.
Três fases novas cobrem o resto:

- `--rest-hand-seconds S` — fase `rest_hand`: palma apoiada na folha
  depois de cada `hold` (e cria um hold se o cenário não tem nenhum).
  A palma pousa no centro da tinta escrita — cobre o canvas confirmado.
- `--sweep-seconds S` — fase `sweep` antes das fases de geometria: a
  mão atravessa a faixa de texto de ponta a ponta. Estressa a fronteira
  de abstenção do juiz de virada (`visible_px >= 50%` do canvas para
  decidir) — a mão cobre/descobre tinta a cada quadro.
- `--grab-hand` — a mão segura a folha (`grab_at`, borda inferior em
  espaço de página) durante `move`, `lift_out` e `return` — acompanha
  o quad: sai de cena com a folha e volta com ela. Em `absent` não há
  mão (saiu de cena junto). `--hand-scale` dimensiona o sprite de
  palma (default 1.0; o sprite de instrumento segue em 0.6).

```sh
python lab/sim_source.py --text "draw hand" --fps 15 \
  --erase-rect 60,60,300,90 --redraw-text "go" \
  --rest-hand-seconds 2.0 --sweep-seconds 1.5 \
  --move 120,60,8 --grab-hand --hand --out captures/sim-hand.mp4
```

### O que a bancada mediu (2026-11-12, legado)

- **Palma e sweep são benignos por projeto confirmado**: o canvas
  confirmado ficou estável (14,5k→14,5k px) em três `rest_hand` e um
  `sweep` — zero eventos de virada/split. O juiz de virada abstém com
  <50% de tinta visível, como foi escrito para fazer.
- **Falha séria — detector cego a folha clipada**: `move 120,60`
  levou a folha ~10% para fora do frame 512². A partir daí: drop do
  tracker e `no_canvas` permanente — a folha estacionou 90% visível
  na mesa por 87 quadros e nunca foi re-adquirida (logit ~-4). O
  envelope medido deslocando uma cena detectável: clipe na borda
  **direita ou esquerda cega já com ~7-9% fora**; no **topo**, ~7%;
  em **baixo** tolera ~17% — assimetria consistente com viés do
  corpus (folha pendurada na borda frontal da mesa). É o mesmo tipo
  de gap do envelope de rotação: dados, não código — a bancada para
  o augment de clipe é este cenário.
- **Pegada durante o move degrada a detecção**: a palma sobre ~40%
  da folha produziu quad parcial e logit 1,17 no meio do gesto — o
  que acompanhou a queda do tracking. Todo move real tem mão.
- **Tinta fantasma congela sob palma estacionada**: o confirmado na
  região apagada ficou travado (~5,1k px) enquanto a palma cobria
  100% do retângulo — `retained` exige `visible`, e pixel sem visão
  não retrai. Semântica correta (não julga o que não vê), consequência
  real: a tinta apagada segue "viva" na tela enquanto a palma estiver
  parada sobre ela. Com a remoção de tinta ligada (hoje default no
  `InkConfig`) a bancada mediu `confirmed_in_erased_px: 0` — a
  retração acontece em toda região visível após a borracha sair.
- Dieta do corpus — `lab/gen_synthetic.py` tem `--clip-fraction`
  (folha 5-40% fora por qualquer borda) e `--rotation-fraction` +
  `--rotation-max` (rotação além do teto ±18° histórico), opt-in,
  registrados em `manifest.diet`. Cobrem os dois gaps medidos do
  detector: clipe ~7-9% nas laterais/topo e cego acima de ~15°.
  A fração zero preserva o comportamento histórico byte a byte.

## Gêmeo óptico e físico (sim-to-real gap)

Os flags abaixo implementam os efeitos que separam a colagem simples
da mesa real — todos opt-in e registrados no manifesto (`isp`,
`hand_shadow`, `ink_sheen`, `page_curl`, `background`). Sem eles, a
sequência é a fotometria histórica, byte a byte.

- `--isp` (ou `--ae --awb --motion-blur` separados): o firmware da
  webcam. A auto-exposição mede a luminância da cena composta e
  aproxima o ganho com constante de tempo de frames — mão ou folha
  grande entrando derruba a exposição até convergir, o regime em que
  o traço fino perde contraste. O AWB faz o mesmo por canal
  (gray-world com deriva lenta). O ruído de sensor escala com o
  ganho, como ISO. `--jpeg-quality N` (10–100) soma compressão JPEG
  controlada por frame, além dos artefatos do mp4v.
- `--motion-blur`: blur direcional proporcional à velocidade real —
  mão, borracha e palma borram na direção do gesto (a velocidade é a
  do sprite na cena, não um valor fixo); a folha em `move`/`lift`/
  `return` borra junto, e a franja de movimento vira rótulo ambíguo
  (ignore) via cobertura, como na mesa real.
- `--hand-shadow`: a mão/borracha projeta penumbra suave deslocada na
  direção da luz (uma direção sorteada por captura, coerente entre
  frames), caindo sobre folha, tinta e mesa.
- `--ink-sheen S` (0–1): faixa especular alongada na direção da luz
  incidente — dentro dela o traço preto vira cinza claro, o caso em
  que a tinta some no reflexo.
- `--page-curl C` (0–1): a folha deixa de ser plano. Uma dobra
  cilíndrica com eixo, início e ângulo sorteados encurta a folha em
  direção à dobra (foreshortening), sombreia a área curvada e expõe
  mesa onde a pose plana cobriria. O detector vê o contorno real da
  folha curvada — o GT deixa de ser projetável por homografia e o
  bundle carrega os mapas densos `scene_to_page_*` das poses inicial
  e final.
- `--background SRC`: troca o fundo procedural (valores de
  `BACKGROUND_SOURCES`); em Python, `background=<ndarray HxWx3>`
  injeta uma foto real de mesa como fundo da cena.

```sh
python lab/sim_source.py --text "draw" --fps 15 --hand --grab-hand \
  --move 120,60,8 --isp --jpeg-quality 65 --hand-shadow \
  --ink-sheen 0.5 --page-curl 0.4 --out captures/sim-twin.mp4
```

Nenhum efeito toca o ground truth além do que a câmera veria: sombra
e brilho mudam pixels, não classes; a curvatura muda a geometria e o
GT exporta o mapa correspondente. Achado de sim continua sendo
hipótese — a régua sintética não substitui a confirmação na mesa.

## Fonte ao vivo em Python

```python
from lab.sim_source import SyntheticCapture

camera = SyntheticCapture("Olá!", seed=42)
camera.save_ground_truth("sim.gt.npz")
try:
    while True:
        ok, frame = camera.read()
        if not ok:
            break
        # alimentar o pipeline com o frame BGR...
finally:
    camera.release()
```

`SyntheticCapture` implementa `isOpened/read/release/get`, gera cada frame
sob demanda e não armazena uma sequência de imagens em memória. `get`
expõe FPS, dimensões, contagem e posição em frames/ms; propriedades não
suportadas retornam 0. EOF retorna `(False, None)`. `realtime=True` limita
a entrega ao FPS no relógio de parede; o padrão offline não espera.

O simulador reutiliza `_paper_base`, `_background`, `_sample_normal_quad`,
`_apply_stroke`, `_warp_paper`, composição da mão, `_ambiguity_ignore` e
`_sequence_photometric` de `lab/gen_synthetic.py`. A função
`compose_scene_sequence` materializa uma lista inteira e escolhe suas
próprias specs aleatórias; por isso a fonte lazy compõe com as mesmas
primitivas, em vez de chamar essa função ou mudar sua assinatura.

O planejador por texto fica em `lab/sim_text.py`.
