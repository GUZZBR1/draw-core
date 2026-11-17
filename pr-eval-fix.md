## Resumo

Este PR leva à main o conteúdo que os merges em cadeia de #25 e #26 deixaram no branch feat/app, mais a correção do achado novo do review:

- lab/eval_capture: avaliação do canvas contra o GT por bundle, dirigindo o Pipeline real em modo síncrono (sem threads/câmera).
- lab/sim_writer: gerador de cenários sintéticos com GT exato e auditoria pelo Pipeline real.

## Correção do achado (moved pages receive false capture scores)

A grade do canvas é indexada pela retificação da âncora, mas cada evidência de tinta entra nela pela matriz M = P(âncora)·P(quad_registro)⁻¹ da SUA passada. O avaliador projetava o GT por ancora·pose_final — correto só quando a pose de publicação coincide com a pose final. Com a folha andando depois da publicação, a tinta confirmada fica deslocada na grade e o GT era procurado no lugar errado.

- PageCleanWorker expõe last_registration: o par (âncora, quad de registro) efetivo de cada passada, incluindo quad congelado pelo deadband e re-âncoras de pouso/follow dentro da passada.
- run_pipeline grava registrations por passada; evaluate_canvas projeta o GT pela mesma matriz de registro do worker e une sobre as passadas.
- Âncoras/cantos fornecidos sem o quad da passada viram pares (quad, quad): retificação canônica é a leitura honesta de um canvas salvo.
- Teste de ouro: a projeção do avaliador é bit a bit igual à saída de _register_ink_probability do worker, inclusive com escala página≠grade.

#### Test plan
- [x] tests/test_eval_capture.py — 15 testes, cobrindo projeção por par de registro, união sobre passadas e igualdade ao registro do worker
- [x] Suíte completa: 668 testes passando
- [x] ruff check / ruff format --check limpos
