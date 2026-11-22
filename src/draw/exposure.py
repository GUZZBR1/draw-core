"""Ganho digital da página retificada antes do page_clean.

A 30 fps a exposição do sensor tem teto físico de 1/30 s (UVC -5 =
1/32 s); numa mesa pouco iluminada o papel chega ao modelo em
~80-100 de 255 e o page_clean v2 perde a confiança nos traços leves
— medido ao vivo (2026-11-19, lab/diag_live.py): o NYMES sai
picotado em -5 e inteiro em -3, que só entrega 8 fps. Muitos drivers
(o da mesa de referência incluso) não expõem VideoProcAmp_Gain, então
o ganho que o sensor não dá é aplicado aqui, no warp.

Ganho linear que leva o percentil 90 do papel a _TARGET_P90. Com a
máscara de cobertura da folha, só os pixels da folha entram na conta:
a mesa clara que o quad abrange não cancela o ganho do papel escuro
(review do PR #52). Nunca escurece (ganho >= 1: página bem exposta
passa intacta) e tem teto _MAX_GAIN (frame quase preto não vira ruído
amplificado). O ganho continua linear, mas sua estimativa é suavizada entre
quadros para o ruído do p90 não oscilar a entrada do modelo.

Custo: roda no laço de UI (orçamento de 33 ms a 30 fps). O percentil
sai de uma amostra esparsa (1 pixel a cada _SAMPLE_STRIDE por eixo) e o
ganho se aplica por tabela (cv2.LUT): ~1 ms num warp A4, contra ~24 ms
do cálculo ingênuo sobre todos os pixels.
"""

import math

import cv2
import numpy as np

_TARGET_P90 = 200.0
_MAX_GAIN = 3.0
_SAMPLE_STRIDE = 8
_GAIN_TIME_CONSTANT_SECONDS = 0.35
_GAIN_DEADBAND_LOG = math.log1p(0.03)
_GLOBAL_EXPOSURE_LOG_TOLERANCE = math.log1p(0.01)
_CLIP_RELEASE_FRACTION = 1e-4
_MIN_SHARED_SAMPLES = 32
_CEILING_GUARD_LOG = math.log(_MAX_GAIN) - _GAIN_DEADBAND_LOG


def _sampled_grid(image, mask):
    """Grade cinza esparsa e grade de visibilidade (passo _SAMPLE_STRIDE).

    Retorna (cinza H'xW', visível H'xW'): cada célula é a média dos
    canais do pixel amostrado e se ela entra na máscara. Máscara vazia
    vale a grade inteira, como em _sampled_gray.
    """
    sample = image[::_SAMPLE_STRIDE, ::_SAMPLE_STRIDE]
    gray = sample.mean(axis=2) if sample.ndim == 3 else sample
    if mask is None:
        return gray, np.ones(gray.shape, dtype=bool)
    sampled = np.asarray(mask)[::_SAMPLE_STRIDE, ::_SAMPLE_STRIDE] > 0
    if not sampled.any():
        sampled = np.ones(gray.shape, dtype=bool)
    return gray, sampled


def _sampled_gray(image, mask):
    """Amostra cinza esparsa (passo _SAMPLE_STRIDE) restrita à máscara."""
    gray, sampled = _sampled_grid(image, mask)
    return gray[sampled]


def paper_gain(image, mask=None):
    """Ganho que levaria o p90 do papel a _TARGET_P90, em [1, _MAX_GAIN].

    mask (bool, forma da imagem): pixels da folha. Vazia ou None, vale a
    imagem inteira.
    """
    p90 = float(np.percentile(_sampled_gray(image, mask), 90))
    if p90 <= 0:
        return _MAX_GAIN
    return float(np.clip(_TARGET_P90 / p90, 1.0, _MAX_GAIN))


def apply_paper_gain(image, mask=None):
    """(imagem uint8 com ganho aplicado, ganho usado)."""
    gain = paper_gain(image, mask)
    return apply_gain(image, gain), gain


def apply_gain(image, gain):
    """Aplica um ganho linear em [1, _MAX_GAIN] com LUT uint8."""
    gain = float(np.clip(gain, 1.0, _MAX_GAIN))
    if gain == 1.0:
        return image
    table = np.clip(np.arange(256, dtype=np.float32) * gain, 0, 255).astype(np.uint8)
    return cv2.LUT(image, table)


class PaperGainSmoother:
    """Amortece pequenas oscilações do ganho estimado entre passadas.

    A banda morta de 3% evita que ruído do p90 altere a LUT. Mudanças
    maiores são seguidas em escala logarítmica, com constante de tempo
    curta para não prender a exposição quando a iluminação realmente muda.
    Quando mediana e p90 acompanham a mesma mudança global nos pixels
    visíveis nos dois quadros, o ganho é corrigido na hora pela razão
    de brilho medida ali — sem atraso e sem depender do alvo, que uma
    máscara nova enviesa.
    Alvo 1,0 é bypass, não amortecimento: papel já bem exposto não pode
    esperar a banda morta liberar o resíduo — cada passada ganhada clipa
    o traço claro junto do papel. Pela mesma razão, um decréscimo dentro
    da banda também a fura quando o ganho retido saturaria pixels do
    papel que o alvo preservaria: contraste perdido não é jitter.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self._gain = None
        self._updated_at = None
        self._prev_sample = None
        self._prev_mask = None
        self._prev_p90_full = None
        self._ceiling_target_log = None

    def update(self, target_gain, timestamp, *, image=None, mask=None):
        """Retorna o ganho temporalmente estabilizado para `timestamp` (s).

        `image`/`mask` são o quadro e a máscara da estimativa (opcionais):
        com eles um decréscimo dentro da banda morta sai da banda quando
        o ganho retido saturaria pixels do papel que o alvo preserva. Uma
        mudança proporcional da mediana e do p90 dos pixels visíveis nos
        dois quadros sinaliza exposição global e corrige o ganho na hora
        pela razão medida (o alvo segue valendo pelo caminho normal de
        suavização).
        """
        target = float(np.clip(target_gain, 1.0, _MAX_GAIN))
        now = float(timestamp)
        if not math.isfinite(now):
            raise ValueError(f"timestamp precisa ser finito: {timestamp!r}")
        sample = sample_mask = clip_sample = None
        clip_is_color = False
        p90_full = None
        if image is not None:
            sample, sample_mask = _sampled_grid(image, mask)
            if sample_mask.any():
                p90_full = float(np.percentile(sample[sample_mask], 90))
            clip_is_color = image.ndim == 3
            clip_sample = image[::_SAMPLE_STRIDE, ::_SAMPLE_STRIDE]
            if mask is not None:
                clip_mask = np.asarray(mask)[::_SAMPLE_STRIDE, ::_SAMPLE_STRIDE] > 0
                if clip_mask.any():
                    clip_sample = clip_sample[clip_mask]
        if self._gain is None or self._updated_at is None:
            self._gain = target
            if math.log(target) >= _CEILING_GUARD_LOG:
                # O primeiro quadro vale pela mesma regra do teto —
                # sem a verificação ele cliparia a faixa clara na
                # primeira passada (Devin Review PR #140).
                self._gain = self._ceiling_safe_gain(target, clip_sample, clip_is_color)
                self._ceiling_target_log = math.log(target)
            self._updated_at = now
            self._prev_sample = sample
            self._prev_mask = sample_mask
            self._prev_p90_full = p90_full
            return self._gain

        elapsed = now - self._updated_at
        if elapsed <= 0.0:
            return self._gain
        self._updated_at = now

        shift = self._shared_exposure_shift(sample, sample_mask, p90_full)
        self._prev_sample = sample
        self._prev_mask = sample_mask
        self._prev_p90_full = p90_full

        if target == 1.0:
            self._gain = target
            self._ceiling_target_log = None
            return self._gain

        if shift is not None:
            # A compensação sai da razão medida nos pixels compartilhados,
            # não do alvo: uma mão cobrindo a margem clara neste quadro
            # mudaria o p90 da máscara nova e o alvo iria na direção
            # contrária à exposição (Devin Review PR #140).
            ratio, target_reliable = shift
            corrected = self._gain / ratio
            if not target_reliable:
                self._gain = float(np.clip(corrected, 1.0, _MAX_GAIN))
                return self._gain
            # Alvo confiável: a correção não pode segurar brilho acima
            # dele — sair do bypass 1,0 restaurando o nível anterior
            # cliparia realces (Devin Review PR #140). Sem retorno aqui,
            # o resíduo converge ao alvo pela suavização normal em vez
            # de ficar preso para sempre.
            self._gain = float(np.clip(min(corrected, target), 1.0, _MAX_GAIN))

        current_log = math.log(self._gain)
        target_log = math.log(target)
        error = target_log - current_log
        alpha = -math.expm1(-elapsed / _GAIN_TIME_CONSTANT_SECONDS)

        if target_log >= _CEILING_GUARD_LOG:
            # Alvos dentro da banda morta do teto são indistinguíveis
            # dele — e o teto não mede a cena: o limite real é o maior
            # ganho que não satura a observação (referência 1x, não o
            # ganho retido). Valer dos dois lados do teto impede o
            # flicker quando a máscara cruza o corte (Devin Review
            # PR #140): a mesma cena produz a mesma saída.
            # O alvo efetivo mistura travado→nominal sem descontinuidade:
            # na borda da banda segue o medido (alvos alternando para
            # dentro/fora da banda convergem quase ao mesmo ponto); no
            # teto vira o nominal fixo, atrator que impede a catraca.
            # Histerese do alvo na banda: trava no primeiro valor —
            # dois alvos dentro da banda estão sempre a menos de uma
            # banda morta um do outro, então seguir cada um só perseguiria
            # jitter do estimador (Devin Review PR #140). O travamento é
            # do ALVO, não do ganho: a saída segue livre para descer e
            # reabrir pela guarda de clip.
            if (
                self._ceiling_target_log is None
                or abs(target_log - self._ceiling_target_log) > _GAIN_DEADBAND_LOG
            ):
                self._ceiling_target_log = target_log
            u = min(
                1.0,
                (self._ceiling_target_log - _CEILING_GUARD_LOG) / _GAIN_DEADBAND_LOG,
            )
            eff_log = (
                self._ceiling_target_log
                + (math.log(_MAX_GAIN) - self._ceiling_target_log) * u**3
            )
            proposed = math.exp(current_log + alpha * (eff_log - current_log))
            self._gain = self._ceiling_safe_gain(proposed, clip_sample, clip_is_color)
            return self._gain

        self._ceiling_target_log = None

        if abs(error) <= _GAIN_DEADBAND_LOG:
            if error >= 0.0 or not self._saturates_newly(
                clip_sample, clip_is_color, self._gain, target
            ):
                return self._gain
            # O decréscimo fura a banda morta: segurar o ganho retido
            # cliparia pixels que o alvo novo manteria distintos
            # (Devin Review PR #140).

        self._gain = math.exp(current_log + alpha * error)
        return self._gain

    def _shared_exposure_shift(self, sample, sample_mask, p90_full):
        """Razão de exposição dos pixels visíveis nos dois quadros.

        Retorna (p90_atual/p90_anterior, alvo_confiável) quando mediana
        e p90 se movem juntos na interseção das máscaras — mudança
        global — ou None.
        Uma mão cobrindo a margem muda a máscara, não os pixels que
        seguem visíveis: comparar a interseção evita ler oclusão como
        mudança de exposição. O p90 sai direto da amostra, não do alvo
        clipado em _MAX_GAIN — no teto a mudança continua visível.
        Sem amostras compartilhadas suficientes não há comparação e o
        caminho normal de suavização decide.
        O alvo só é confiável quando a máscara nova não enviesa o
        percentil: o p90 da máscara inteira deve ter se movido com a
        razão de exposição medida nos compartilhados — poucas células
        trocadas bastam para enviesar o alvo se cruzam o corte do
        percentil (Devin Review PR #140).
        """
        if (
            self._prev_sample is None
            or self._prev_mask is None
            or sample is None
            or sample_mask is None
            or sample.shape != self._prev_sample.shape
        ):
            return None
        shared = sample_mask & self._prev_mask
        if shared.sum() < _MIN_SHARED_SAMPLES or shared.sum() * 2 < sample_mask.sum():
            return None
        prev = self._prev_sample[shared]
        cur = sample[shared]
        median_prev = float(np.median(prev))
        median_cur = float(np.median(cur))
        p90_prev = float(np.percentile(prev, 90))
        p90_cur = float(np.percentile(cur, 90))
        if min(median_prev, median_cur, p90_prev, p90_cur) <= 0.0:
            return None
        median_delta = math.log(median_cur / median_prev)
        p90_delta = math.log(p90_cur / p90_prev)
        if (
            abs(median_delta) >= _GLOBAL_EXPOSURE_LOG_TOLERANCE
            and abs(p90_delta) >= _GLOBAL_EXPOSURE_LOG_TOLERANCE
            and abs(p90_delta - median_delta) <= _GLOBAL_EXPOSURE_LOG_TOLERANCE
        ):
            target_reliable = (
                p90_full is not None
                and p90_full > 0.0
                and self._prev_p90_full is not None
                and self._prev_p90_full > 0.0
                and abs(math.log(p90_full / self._prev_p90_full) - p90_delta)
                <= _GLOBAL_EXPOSURE_LOG_TOLERANCE
            )
            return p90_cur / p90_prev, target_reliable
        return None

    def _ceiling_safe_gain(self, proposed, clip_sample, is_color):
        """Maior ganho em (1, `proposed`] que não satura a observação.

        Referência crua (1x): pixels que `proposed` cliparia e o ganho
        1x preserva. O predicado é monotônico no ganho — bisseção em
        log basta — e o resultado pode ficar ABAIXO do retido, o que
        desfaz a catraca de um clarão breve (Devin Review PR #140).
        """
        if not self._saturates_newly(clip_sample, is_color, proposed, 1.0):
            return proposed
        lo, hi = 1.0, proposed
        for _ in range(10):
            mid = math.sqrt(lo * hi)
            if self._saturates_newly(clip_sample, is_color, mid, 1.0):
                hi = mid
            else:
                lo = mid
        return lo

    def _saturates_newly(self, clip_sample, is_color, high_gain, low_gain):
        """Fração do papel que `high_gain` satura e `low_gain` preserva.

        `clip_sample` é a amostra esparsa da imagem já restrita à
        máscara, computada uma vez por update. Um pixel conta quando
        algum canal cai em [255/high_gain, 255/low_gain): vai a 255 com
        o ganho maior mas segue distinto com o menor. Retorna True se a
        fração passa o limite.
        """
        if clip_sample is None or clip_sample.size == 0 or high_gain <= low_gain:
            return False
        newly_saturated = (clip_sample >= 255.0 / high_gain) & (
            clip_sample < 255.0 / low_gain
        )
        if is_color:
            newly_saturated = newly_saturated.any(axis=-1)
        return float(newly_saturated.mean()) > _CLIP_RELEASE_FRACTION
