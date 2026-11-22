# Auditoria de arquitetura e código morto — 2026-11-21

Revisão estrutural do `draw-core` com três frentes: grafo de importações a partir
do entry point (`draw.app:main`), inventário dos diretórios fora do runtime, e
forense do histórico git/PRs. Objetivo: achar o que está morto, desconectado ou
acumulando remendo-sobre-remendo, e propor um plano de simplificação.

Contexto: repositório com ~5 dias de vida (primeiro commit 2026-11-16), ~330
commits locais e ~150 PRs — a fadiga de manutenção é de velocidade e de camadas
de remendos, não de anos de decaimento.

## Mapa de alcançabilidade (entry point `draw.app:main`)

Alcançável e vivo: `camera`, `config`, `contracts`, `exposure`, `geometry`,
`hand`, `hand_presence`, `auto_orient`, `paper`, `page_clean`, `perception`,
`photometry`, `pipeline`, `settings`, `tracker`, `view`, `protocol`,
`hvcam` + `_hvcam_mjpeg`, `stream` (só com `--stream-*`), `ink/*` inteiro,
`infra/*` inteiro.

**Não alcançável do app** (só testes e lab): `exporters/vectorize.py`,
`exporters/export_vectors.py`.

## Achados — código morto / desconectado (verificado em `origin/main`)

### Morto confirmado — nenhum chamador em `src/`, `lab/` ou `tools/`

| Símbolo | Local | LOC | Estado |
|---|---|---|---|
| `view.fit` | `view.py:51` | ~15 | vivo em main, zero chamadores |
| `paper.detect_sheet` | `paper.py:329` | ~10 | wrapper morto; `detect_sheet_with_confidence` é a API viva |
| `hand_presence.MediaPipeHandPresence.present` | `hand_presence.py:83` | ~3 | worker só chama `.sample()` |
| `safe_io.read_image`, `safe_io.iter_jsonl` | `infra/safe_io.py:154,193` | ~40 | só testes |
| `geometry.fit_quad` | `geometry.py:922` | ~14 | wrapper público só de teste; produção usa `_fit_quad_impl` |
| `paper.warp_sheet_uvmap` | `paper.py:468` | ~55 | só `test_paper_formats.py`; caminho neural de mapa denso nunca ligado |
| `view.point_in_card` | `view.py:516` | ~10 | só `test_view.py` |
| `app._video_nodes` | `app.py:588` | ~9 | duplica `camera._video_nodes` (`camera.py:754`) — deduplicar, não apagar |

Já removidos por `chore/dead-code` (mergeado): `app._detect_sheet_combined`,
`paper.warp_points`, `hvcam._probe_hvcam_frame`, `config.MARKER_SIZE_PX`,
sobras de `tests/rr.py`, `lab/seg_metrics` (dice_per_class etc.), `judge_candidate.REPO`.

### Desconectado do app, mas API pública do pacote (CORRIGIDO pós-verificação)

A primeira leitura marcou `exporters/`, o lado consumidor de `stream.py` e o
lado cliente de `protocol.py` como "ferramentas dentro do runtime". Isso está
**errado**: `../drawlink` (processo separado, `draw-core` pinado por commit no
`pyproject.toml` dele) importa todos eles ao vivo:

- `draw.exporters.vectorize`: `fill_pinholes`, `vectorize_clean`
  (`drawlink/src/drawlink/incremental.py:22`) — o vetorizador incremental do
  drawlink usa o batch por componente.
- `draw.exporters.export_vectors`: `write_svg` (`drawlink/svg.py:15`).
- `draw.stream`: `DEFAULT_PORT`, `iter_records`, `records_from_file`,
  `InkCanvas`, `InkRecord` (`drawlink/source.py`, `session.py`, `live.py`).
- `draw.protocol`: `AuthenticationError`, `ProtocolError`, `resolve_token`,
  `client_handshake`, `server_handshake` (`drawlink/source.py`, `cli.py`).
- `draw.contracts`, `draw.config` (módulos).

**Veredito: tudo isso fica.** É a fronteira pública do pacote — o pacote não é
só o app, é também a biblioteca do drawlink. Remover `vectorize.py` quebraria
`drawlink.incremental`. O `run.sh` exigir `cv2.ximgproc` também se explica por
isso (o vetorizador precisa do wheel contrib).

### Dormant feature — campo de config sem caminho até o usuário

`PipelineConfig.ink_divnorm` (`settings.py:106`, `pipeline.py:505`,
`worker.py` bloco divnorm, `photometry.division_normalize`): ~150 LOC ligados
por trás de um flag que **nenhuma CLI seta** (`app.py:2332–2337` nunca passa
`ink_divnorm`). Entrou pelo PR #110 (perf #101) e nunca foi exposto.

**Decisão do dono (2026-11-21): fica vivo** — o plano do modelo v4 de tinta é
sobre `division_normalize`. O que falta é só o setter (flag CLI) quando o v4
chegar; não remover.

### APIs de observabilidade test/lab dentro do worker

`PageCleanWorker.poll/pump/telemetry_snapshot/anchor_corners/
last_registration/canvas_epoch` (~250 LOC): usadas por testes e `lab/`; não
fazem parte do caminho de produção (`pipeline` consome `poll_display`/
`poll_delta`). Não remover às cegas — são a superfície de teste do motor.

## Achados — epicentro da dor de manutenção

O cansaço não é difuso: concentra em três pontos.

1. **`src/draw/ink/worker.py` (2242 LOC)** — ~~`_run_pass` era um único método
   de ~1040 linhas~~ **RESOLVIDO (#154, ver seção "Split do `_run_pass`")**:
   orquestrador + 7 estágios nomeados. O método acumulava: rest/wake cadence, geo-wake, sonda ociosa, janela
   pós-saída, motion-veto, histerese, remoção de pauta, divnorm, migração por
   grade de cobertura, e agora a guarda de papel #129 (orçamento de sombra,
   `frozen_pending_px`). `InkConfig` tem **~20 campos, quase todos opt-in**,
   cada um uma camada de fix-PR (#43, #53, #56, #68, #122, #129). Sintoma
   máximo: **5 PRs abertos agora (#138, #139, #140, #144, #145) remendam o
   mesmo problema** — tinta apagada sob mão/sombra/pauta/borda (issues
   #129–#133) — e um sexto, `feat/page-model` (#150), se propõe a ser a
   correção de raiz que os substitui. O subsistema claramente carece de um
   modelo de estado por-região; cada incidente vira mais uma guarda.
2. **`src/draw/app.py` (2388 → 1368 LOC em main)** — god-file já parcialmente
   dividido (`ui.py` 634 + `selfcheck.py` 420 extraídos). Segue denso
   (CLI + run loop + provisioning + hvcam + auto-rotação + streaming);
   `run()` de ~730 linhas é o maior método do repo.
3. ~~**`src/draw/hvcam.py` (1851 LOC)**~~ — **RESOLVIDO (#158)**: virou pacote
   `hvcam/` com 8 módulos unidirecionais (`_wire`, `_lib`, `_transport`,
   `_mjpeg`, `_capture`, `_provision`, `_reverse`, `_process`).

Secundários: `pipeline.py` (ciclo de vida da máscara de mão, ~14 fix commits na
mesma família de timing), `auto_orient.py` (chain de ~15 fixes que chegou a ser
revertido no PR #80), `lab/` (~20 scripts com drivers pump/eval quase
idênticos; `refactor/lab-helpers` já extrai a duplicação).

## Achados — fora do runtime

- `tools/helper_receiver.py` (393 LOC): shim fino sobre `draw.protocol`; só
  testes o exercitam. Manter (ferramenta de operação documentada) ou dobrar
  para `python -m draw.protocol`.
- `bridge/windows_helper.py` (743 LOC): remetente Windows, em grande parte
  suplantado por hvcam; papel único restante é injeção de cursor ("later" no
  protocolo). Candidato a arquivo se a injeção morrer. `bridge/README.md` e
  `PROTOCOL.md` têm referências obsoletas (`tools/step0_latency.py`,
  `scripts/setup_camera_wsl.sh` inexistem; "untested sketch" está datado).
- `lab/judge_candidate.py`: depende de `~/workspace/draw-lab/judging-bench` +
  `mlvenv` externos — só roda na máquina do dono. Candidato a arquivo se a
  banca de juízes não voltar.
- `lab/perf/` **não existe**: o spec (L106) previa `perf_sampler`/
  `summarize_perf` para a decisão C++ — peça faltante, não peso morto.
- `lab/seg_metrics.py` (682 LOC): folha sem consumidor no repo (consumidor real
  é o futuro draw-training).
- Órfãos: `lapis-amarelo.svg` (raiz, zero refs), `site/public/images/papers/0*.svg`
  (8 cópias não referenciadas das figuras de `docs/research/figures`),
  `docs/research/figures/generated/*.jpg` (8 arquivos, zero refs, não
  regenerados por `make_figures.py`), `docs/research/v1/` (~4–5k LOC de
  backups de artigos; história já está no git), `draw_core.egg-info/` na raiz
  (artefato obsoleto, ignorado mas presente).
- `docs/FALHAS.md` e `docs/SETUP_WINDOWS.md` não existem — o spec dizia para
  mantê-los (aparados); decisão pendente.
- Higiene de branches: ~60 locais, ~56 remotas, ~14 worktrees; ~25 locais e
  ~15 remotas mortas/mergeadas; worktrees em `/tmp` e `~/draw-core-*` para
  podar. Parte real da fadiga operacional.

## O que NÃO remover (verificado como decisão deliberada)

- **`exporters/`, lado consumidor de `stream.py`, lado cliente de
  `protocol.py`, `contracts`, `config`**: API pública importada por
  `../drawlink` (ver seção corrigida acima).
- `--markers` e `--legacy-ink`: mantidos por decisão registrada no spec
  (origin/main, seção `ink.py`: "`--markers` stays as a live mode", PRs
  #50/#84/#91; `--legacy-ink` como modo de comparação).
- `contracts.SheetQuad/PageIdentity/InkState`: scaffolding da migração
  (AGENTS.md permite shapes legados até a integração).
- `ink_divnorm`/`photometry.division_normalize`: plano do modelo de tinta v4
  (decisão do dono, 2026-11-21).
- `geometry.fit_quad`, `safe_io.read_image`/`iter_jsonl`: superfície de API
  pequena e testada — mantidas como interface pública/infra.
- `hand_presence` vs `hand`: contratos diferentes (presença assíncrona vs
  máscara de oclusão por frame). `_hvcam_mjpeg` vs `hvcam`: complementares.
  `settings`/`config`/`ink.config`: três escopos distintos. ~~`config.py`
  tinha globais mutáveis~~ **RESOLVIDO (#157)**: `PaperSpec` congelado via
  `config.current()`, `apply_format` troca o spec atomicamente.
- `stream.py` receiver API: exigida pelo contrato `bridge/STREAM.md` E por
  drawlink.

## Armadilha de ambiente — qual o `draw` o pytest importa

O `.venv` da raiz tem `draw-core` instalado a partir de `~/draw-core/src` —
ou seja, pytest rodado num worktree (/tmp/*) usa a **fonte do checkout
principal**, não a do worktree. Para testar a fonte de um worktree:
`PYTHONPATH=<worktree>/src pytest ...`. (Uma "falha em main" observada na
rodada era só esse artefato: o teste de retenção de mão rodava contra a
branch `fix/ink-paper-evidence-guard`.)

## Plano de simplificação (PRs independentes, conforme AGENTS.md)

**P0 — remoção sem risco** — ✅ EXECUTADO (branch `chore/dead-code-round-2`,
worktree /tmp/draw-cleanup, −924 linhas em 34 arquivos): `view.fit`,
`view.point_in_card`, `paper.detect_sheet`, `paper.warp_sheet_uvmap` (+helpers
_UVMAP e os 11 testes do contrato dormente), `hand_presence.present`. Órfãos:
`lapis-amarelo.svg`, `site/public/images/papers/*.svg` (8),
`docs/research/figures/generated/*.jpg` (8), `docs/research/v1/` (12).
Refs obsoletas em `bridge/README.md`/`PROTOCOL.md` corrigidas (#159:
"untested" e dois links mortos). `geometry.fit_quad` e
`safe_io.read_image/iter_jsonl` ficaram (API pequena e testada).

**P0 — higiene operacional** — ✅ EXECUTADO: 16 branches locais mergeadas
deletadas, 20 branches remotas mergeadas deletadas, 5 worktrees de branches
mergeadas removidos, 6 worktrees obsoletos de /tmp podados, refs temporários
(refs/tmp/*, refs/remotes/pr/*) limpos, `main` local avançado para
origin/main. Restam ~40 branches locais NÃO mergeadas (backups e cópias
locais de PRs) — lista para o dono avaliar `-D`.

**P1 — ~~tirar ferramentas do pacote~~ CANCELADO**: `exporters/` +
`stream`/`protocol` são a API do drawlink. Ficam. (Ver seção corrigida.)

**P1 — `ink_divnorm`**: fica vivo (plano v4); falta apenas o setter/flag
quando o modelo chegar.

**P2 — estrutural, o que de fato reduz manutenção**:
1. `ink/worker.py`: quebrar `_run_pass` (~1040 linhas) em estágios nomeados
   (rest/wake, oclusão, voto, registro, publicação) — preparação para o
   `feat/page-model` (#150), que parece ser a resposta de raiz ao cluster
   #129–#133 e, se aterrissar, torna obsoletos os 4 fix-PRs paralelos.
   Aprovado para começar já, em paralelo, aceitando conflitos.
2. `refactor/app-split`: continuar (main já extraiu ui.py+selfcheck.py).
3. Consolidar `InkConfig`: revisar os ~20 campos opt-in e promover/matar os
   que nunca são ligados (varrer setters reais como foi feito com
   `ink_divnorm`).

**P3 — decisões de escopo do spec**: `lab/judge_candidate.py` e
`lab/seg_metrics.py` (arquivar ou assumir como dev-only documentado);
`bridge/windows_helper.py` (arquivar se injeção de cursor estiver morta);
`docs/FALHAS.md`/`SETUP_WINDOWS.md` (portar aparados ou atualizar o spec);
~~`config.py` globais mutáveis → `Config` imutável~~ **feito (#157)**;
`lab/perf/` (portar do legado quando a decisão C++ voltar à mesa).

Resultado real da rodada: **~924 LOC removidas** + ~40 branches/worktrees
podados.

## Split do `_run_pass` — executado (PR #154, branch `refactor/ink-worker-stages`, `c0a8b8d`)

O método de ~1040 linhas virou um orquestrador de ~45 linhas mais sete
estágios nomeados; as ~50 variáveis locais viajam no dataclass interno
`_Pass` (scratch mutável da passada, módulo-privado — o spec pede dataclass
nas fronteiras de estágio e `_Pass` é o passo estrutural sem widar os shapes
legados):

- `_run_pass(job)` — unpack, guard de geração, try/except → `_error`,
  despacho dos estágios;
- `_pass_evidence(p)` — visível camera→página, divnorm, modelo, guarda de
  papel, pauta (toda a parte cara, fora do lock);
- `_pass_anchor_state(p)` — âncora/mediana/deadband + `anchor_ink` sob o
  lock; devolve `None` ou o bool de abort;
- `_pass_register_motion_coverage(p)` — registro, portão de movimento
  (ECC), portão de cobertura (`_covered`/`_gate` ficaram nested);
- `_pass_commit(p)` — sob o lock: `_pass_identity` → `_pass_anchor_gates`
  (arbitragem + follow, re-registro deduplicado em `_reregister_current`)
  → `_pass_vote_and_publish` (abstenções, acumulador, contadores,
  publicação, telemetria; devolve `delta_job` gravado após o lock).

Ordem, pontos de lock, mutação de `self`, telemetria e saídas preservados.
Verificação: `ruff check`/`format` limpos; **453 testes focados do worker**
e suíte completa **1756 passed, 1 skipped** (com `PYTHONPATH` apontando
para o worktree — ver armadilha de ambiente).

## Desfechos da rodada (2026-11-21, pós-split)

- **#154 mergeado** (`c65eb82`): split do `_run_pass` na main.
- **`feat/page-model` rebaseada localmente** sobre a main nova: o hunk
  PageModel foi portado para `_pass_vote_and_publish` (233 testes verdes);
  aguarda review + `--force-with-lease` do dono. A versão local já está
  além disso — reestruturação em curso movendo o PageModel para fora do
  lock (`_pass_prepare_vote`/`_pass_paper_and_page_model`, epochs `pm_*`,
  baseline `_identity_baseline` absorvendo o issue-130).
- **#139 rebaseada e pushed** (só `ruling.py`, 142 testes verdes,
  `MERGEABLE`). **#140** é de fork (`GUZZBR1`), não toca `worker.py` e já
  está `MERGEABLE` — não precisa de rebase.
- **#138/#144/#145: NÃO rebasear agora.** O #138 é merge semântico (15
  commits, remove `paper_evidence` inteiro, reescreve identidade/recovery,
  +1.300 linhas de teste) e #144/#145 tocam o mesmo trecho que a
  reestruturação do page-model move — portar agora = fazer duas vezes.
  Sequência certa: aterrissa o page-model, depois eles.
- **#155 mergeado** (`1781bd4`): dead-code round 2, −924 LOC.
- **#156 mergeado** (`5b4a99e`): este relatório na main.
- **#157 mergeado** (`454f9eb`): `config.py` → `PaperSpec` imutável +
  `config.current()`; globais mutáveis eliminados; review apontou e foi
  corrigido: `marker_centers` virou `MappingProxyType` somente-leitura e
  `warp_sheet` lê o spec uma única vez para matriz+dsize.
- **#158 mergeado** (`cbc840f`): `hvcam.py` (1820 LOC) → pacote `hvcam/`
  com 8 módulos (`_wire`, `_process`, `_lib`, `_transport`, `_mjpeg`,
  `_capture`, `_provision`, `_reverse`). Review pegou e foram corrigidas
  regressões de base `__file__` (candidatos de lib/host subiram um nível)
  + `_MANAGED_*` duplicado + teste novo de checkout irmão offline.
- Worktrees podados (appsplit/corpus/pr115/config/hvcam — todos mergeados).

## Auditoria `InkConfig` — quais campos têm caminho real

Vias de produção (`app.py`): `--ink-vote` (strict_vote + **desliga
paper_guard**), `--ink-interval` (pass_interval_s), `--no-ink-ruling`,
`--legacy-ink` (InkConfig() cru + paper_guard off), `--sketch`, `--technical`,
default `production()`. Vias dev: `lab/bench_ink.py` aceita override
genérico `ink.X=1` — os campos "dormentes" têm caminho legítimo de bancada
by design ("opt-in até a régua provar").

| Grupo | Campos | Caminho |
|---|---|---|
| Produção | vote_*, pass_interval_s, ruling_removal, hysteresis, motion_veto, paper_guard, post_exit_full_window (sketch) | flags + presets |
| Bancada-by-design | reg_deadband, reg_anchor_median, t_high, t_low, provisional_min_px, seen_threshold, motion_veto_px, occlusion_hold_passes, page_model | `ink.X=` no replay |
| Sempre-True kill-switches | removal, anchor_arbitration, anchor_follow, follow_move | nenhum consumidor desliga; só testes |

Candidatos reais de simplificação: os 4 always-True (remover campo = sumir
com a variante nunca usada — médio risco, ganho modesto) e
`reg_deadband`/`reg_anchor_median` (maquinaria inteira bench-only;
decisão do dono se a régua ainda vai provar ganho).

## Docs do spec pendentes

`docs/FALHAS.md` e `docs/SETUP_WINDOWS.md`: referenciados pelo
MIGRATION_SPEC (linhas 93/125/133) mas nunca existiram neste repo —
a fonte é o repo legado. Decisão pendente: portar aparados ou atualizar
o spec. `bridge/README.md` e `PROTOCOL.md` corrigidos: README chamava
`windows_helper` de "untested" (datado — tem testes estruturais e de
segurança) e linkava `scripts/setup_camera_wsl.sh` inexistente;
PROTOCOL linkava `tools/step0_latency.py` inexistente (ficou como
referência ao repo legado).
