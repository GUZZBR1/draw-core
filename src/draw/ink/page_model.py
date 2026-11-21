"""Modelo persistente da pagina limpa na grade da ancora (PageModel).

A fila de robustez de 2026-11-21 (#129-#133, #130) e um unico defeito
batendo em portas diferentes: cada passada decide so com o quadro da
vez — prob por passada, ganho por passada, mascara de mao por passada
— e uma cascata de guardas remenda cada sintoma (mascara vazia =
pagina toda visivel, ganho p90 sem memoria, sem modelo do que ja
estava impresso, sem faixa de guarda na borda). O mecanismo que falta
e o classico da captura de quadro/documento por camera fixa (He, Liu
& Zhang, MSR 2004, "Real-Time Whiteboard Capture"): uma imagem de
referencia da superficie limpa mantida no tempo, contra a qual cada
pixel e classificado — fundo conhecido, conteudo novo ou ocluido/
pendente.

O PageModel mantem, na grade da ancora (a mesma do acumulador):

- `ref` (float32 HxW): a luminancia de referencia do papel limpo.
  Semeada pixel a pixel quando a passada o observa por
  `confirm_obs` vezes seguidas dentro do seu bloco; rastreada
  lentamente (`rate`) onde a passada afirma papel — absorve a
  deriva de iluminacao (#133) sem nunca afundar um traco (o
  chamador passa `paper` excluindo evidencia de tinta).
- `seeded` (bool HxW): o pixel tem referencia. Regiao nunca vista
  limpa fica pendente — a mao que cobre o caderno na abertura nao
  entra na referencia, e o conteudo revelado depois semeia COM ele
  dentro (a semantica "primeira observacao limpa" do #130: o que
  estava la quando o pixel foi visto pela primeira vez e pagina,
  nao tinta nova).
- `_streak` (uint8 por bloco de `block` px): quantas observacoes
  vistas seguidas o bloco tem. A grade por blocos e a da guarda
  fotometrica medida no #129 (32 px): fina o bastante para uma mao
  nao contaminar a pagina, grossa o bastante para o custo ficar
  abaixo de 1 ms por passada.

Saidas para a trabalhadora: `admissible` (so pixels com referencia
entregam evidencia — regiao pendente congela, o "freeze por falta
de testemunha" que a guarda de papel do #129 aproxima por quadro) e
`novel` (so o que esta mais escuro que a referencia e conteudo novo —
suprime pauta impressa, desenho antigo e sombra de vinco que a regra
do #132 persegue por heuristica). Apagar tinta e simetricamente
seguro: papel re-exposto fica MAIS claro que a referencia, nao mais
escuro, entao remocao nunca le como conteudo novo.

Opt-in via InkConfig.page_model; desligado, nada muda. O limiar de
"novo" (_NOVEL_DELTA, em unidades de luminancia 0-255) e uma
semente razoavel para um traco escuro sobre papel claro; o corpus
de clipes reais e quem calibra de vez.
"""

import numpy as np

# Bloco da grade de semeadura: a mesma ordem do 32 px medido na
# guarda fotometrica (#129). Fino o bastante para a mao nao
# contaminar a pagina inteira; grosso o bastante para a fracao por
# bloco custar < 1 ms.
_BLOCK = 32
# Fracao de pixels visiveis que conta o bloco como "visto" na
# passada. Blocos parciais de borda contam pelo que tem.
_SEEN_FRACTION = 0.5
# Observacoes vistas seguidas ate o bloco poder semear. Tres
# passadas a 0,15-0,25 s = 0,45-0,75 s: cabe no periodo de
# estabilizacao que a folha ja exige e cobre uma mao parada breve.
_CONFIRM_OBS = 3
# Passo do rastreio lento da referencia onde ha papel: ~1/rate
# passadas para absorver uma deriva (~20 a 0,15 s = ~3 s) — lento
# demais para apagar jitter de exposicao entre passadas, rapido o
# bastante para acompanhar nuvem e lampada (#133).
_UPDATE_RATE = 0.125
# Quanto mais escuro que a referencia um pixel precisa estar para
# ser "conteudo novo", em unidades de luminancia. Semente para
# traco escuro sobre papel claro; a calibracao real sai do corpus.
# A literatura canonica testa sombra por RAZAO (MOG2 Tau, penumbra e o
# caso dificil — docs/research/nota-page-model-literatura.md); o delta
# absoluto falha justamente no gradiente de sombra movel do #133. E o
# erro mais seguro p/ prototipo: falso `novel` cai na pipeline normal
# (status quo), falso `~novel` suprime traco claro para sempre — mas a
# decisao delta vs razao vs entrada `division_normalize` e medicao,
# nao chute: pendente de clipes reais.
_NOVEL_DELTA = 24.0


def _block_fraction(mask, block, raw=False):
    """Fracao de True por bloco de `block` px, sobre a area REAL do bloco.

    Blocos de borda (grade nao multipla de `block`) contam pelos
    pixels que existem — o padding fora da grade nao dilui a fracao,
    senao a faixa externa nunca seria "vista" nem semeada. Com
    `raw=True` devolve a contagem de True por bloco (a area real e a
    contagem da mascara de uns — o chamador cacheia e divide).
    """
    height, width = mask.shape
    bh = -(-height // block)
    bw = -(-width // block)
    padded = np.zeros((bh * block, bw * block), dtype=bool)
    padded[:height, :width] = mask
    sums = padded.reshape(bh, block, bw, block).sum(axis=(1, 3))
    if raw:
        return sums
    return sums / _block_fraction(np.ones((height, width), dtype=bool), block, raw=True)


def _expand(blocks, shape, block):
    """Mascara por bloco de volta a grade de pixels."""
    height, width = shape
    full = np.repeat(np.repeat(blocks, block, axis=0), block, axis=1)
    return full[:height, :width]


class PageModel:
    """Referencia persistente da pagina limpa na grade da ancora.

    Uma instancia por geracao e por forma de grade: a trabalhadora a
    recria quando a geracao ou o tamanho do mapa muda. A re-ancoragem
    (veredito de pouso, follow) NAO reseta: a grade e a da folha e o
    conteudo anda com ela, exatamente como o estado do acumulador.
    """

    def __init__(
        self,
        shape,
        *,
        block=_BLOCK,
        confirm_obs=_CONFIRM_OBS,
        rate=_UPDATE_RATE,
        novel_delta=_NOVEL_DELTA,
    ):
        if block < 1:
            raise ValueError("block deve ser >= 1")
        if confirm_obs < 1:
            raise ValueError("confirm_obs deve ser >= 1")
        if not 0.0 < rate <= 1.0:
            raise ValueError("rate deve estar em (0, 1]")
        if not novel_delta > 0.0:
            raise ValueError("novel_delta deve ser > 0")
        self.shape = tuple(shape)
        self.block = int(block)
        self.confirm_obs = int(confirm_obs)
        self.rate = float(rate)
        self.novel_delta = float(novel_delta)
        height, width = self.shape
        self._ref = np.zeros((height, width), dtype=np.float32)
        self._seeded = np.zeros((height, width), dtype=bool)
        self._streak = np.zeros(
            (-(-height // self.block), -(-width // self.block)), dtype=np.uint8
        )
        # Area real de cada bloco (grade nao multipla de `block` tem
        # borda parcial): cacheada — a fracao por bloco a divide todo
        # observe e a constante nao muda na vida do modelo.
        self._block_area = _block_fraction(
            np.ones(self.shape, dtype=bool), self.block, raw=True
        )

    @property
    def reference(self):
        """Luminancia de referencia do papel limpo (float32, grade da ancora)."""
        return self._ref

    @property
    def seeded(self):
        """Pixels que ja tem referencia (bool, grade da ancora)."""
        return self._seeded

    @property
    def seeded_fraction(self):
        """Fracao da grade com referencia (telemetria de prontidao)."""
        if self._seeded.size == 0:
            return 0.0
        return float(np.count_nonzero(self._seeded) / self._seeded.size)

    def observe(self, gray, visible=None, paper=None):
        """Alimenta o modelo com a luminancia desta passada (grade da ancora).

        `gray` e o warp em luminancia na grade da ancora. `visible`
        (None = tudo visivel) e a mascara de observacao da passada —
        o que ela viu de verdade. `paper` e o subconjunto que o
        chamador julga papel limpo (a trabalhadora passa
        `visible & (prob <= piso)`); onde ele e False a referencia
        nao se move — traco nunca afunda no fundo. `paper=None`
        semeia sem rastrear, o modo conservador.

        Semear exige `confirm_obs` observacoes vistas seguidas no
        bloco; o pixel semeia com a observacao da vez, nao com media
        — a media borraria o conteudo que o "nao e novo" precisa
        reconhecer depois.
        """
        gray = np.asarray(gray, dtype=np.float32)
        if gray.shape != self.shape:
            raise ValueError(f"gray na grade {gray.shape}, modelo na {self.shape}")
        if visible is None:
            visible = np.ones(self.shape, dtype=bool)
        else:
            visible = np.asarray(visible, dtype=bool)
            if visible.shape != self.shape:
                raise ValueError(
                    f"visible na grade {visible.shape}, modelo na {self.shape}"
                )
        seen = (
            _block_fraction(visible, self.block, raw=True) / self._block_area
            >= _SEEN_FRACTION
        )
        streak = self._streak
        streak[seen] = np.minimum(streak[seen].astype(np.uint16) + 1, 255).astype(
            np.uint8
        )
        streak[~seen] = 0
        ready = _expand(streak >= self.confirm_obs, self.shape, self.block)
        seed_now = ready & visible & ~self._seeded
        if np.any(seed_now):
            self._ref[seed_now] = gray[seed_now]
            self._seeded |= seed_now
        if paper is not None:
            paper = np.asarray(paper, dtype=bool)
            if paper.shape != self.shape:
                raise ValueError(
                    f"paper na grade {paper.shape}, modelo na {self.shape}"
                )
            update = self._seeded & visible & paper
            if np.any(update):
                self._ref[update] += self.rate * (gray[update] - self._ref[update])

    def admissible(self, visible=None):
        """Pixels que podem entregar evidencia: os que tem referencia.

        Com `visible`, devolve `seeded & visible` — a mascara pronta
        para o voto. Pixel pendente (nunca visto limpo) nao entrega:
        e a extensao temporal do "quem nao ve, se abstem" da
        oclusao, da passada para a vida inteira da geracao.
        """
        if visible is None:
            return self._seeded.copy()
        return self._seeded & np.asarray(visible, dtype=bool)

    def novel(self, gray):
        """Pixels mais escuros que a referencia alem de `novel_delta`.

        Assimetria intencional: so o que ESCURECEU contra a
        referencia conta. Papel re-exposto (borracha, mao saindo)
        clareia — mudanca, mas nao tinta nova. Sem referencia
        (`~seeded`) nao ha veredito: devolve False, e a porta de
        admissibilidade e quem segura o pixel.
        """
        gray = np.asarray(gray, dtype=np.float32)
        if gray.shape != self.shape:
            raise ValueError(f"gray na grade {gray.shape}, modelo na {self.shape}")
        return self._seeded & (self._ref - gray > self.novel_delta)

    def pending(self, visible=None):
        """Pixels visiveis ainda sem referencia (diagnostico/telemetria)."""
        if visible is None:
            visible = np.ones(self.shape, dtype=bool)
        return ~self._seeded & np.asarray(visible, dtype=bool)
