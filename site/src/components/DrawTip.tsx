import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { useLang } from '../i18n';

// Frases dos balões: cada ocorrência de "Draw" ganha a próxima frase ainda não usada.
const TIPS: { pt: string; en: string }[] = [
  { pt: 'Todo traço começa como um ponto.', en: 'Every stroke starts as a dot.' },
  { pt: 'Desenhar é pensar com a mão.', en: 'Drawing is thinking with the hand.' },
  { pt: 'O papel lembra o que o olho esquece.', en: 'Paper remembers what the eye forgets.' },
  { pt: 'Errar a linha também é desenhar.', en: 'Missing the line is still drawing.' },
  { pt: 'Uma linha só já diz muita coisa.', en: 'A single line already says a lot.' },
  { pt: 'O branco da página também faz parte.', en: 'The white of the page is part of it.' },
  { pt: 'Devagar, o traço fica mais seu.', en: 'Slowly, the stroke becomes more yours.' },
  { pt: 'Primeiro rabisque, depois decida.', en: 'Scribble first, decide later.' },
  { pt: 'Toda forma foi um rascunho um dia.', en: 'Every shape was a draft once.' },
  { pt: 'Seu caderno, seu ritmo.', en: 'Your notebook, your pace.' },
  { pt: 'Olhar bem já é metade do desenho.', en: 'Looking well is half the drawing.' },
  { pt: 'A mão sabe coisas que a gente não sabe dizer.', en: 'The hand knows things we cannot say.' },
  { pt: 'Nenhum risco é em vão.', en: 'No mark is wasted.' },
  { pt: 'Entre o gesto e a tela, uma ponte.', en: 'Between the gesture and the screen, a bridge.' },
  { pt: 'Curvas pedem paciência.', en: 'Curves ask for patience.' },
  { pt: 'Hoje é dia de começar algo torto.', en: 'Today is a good day to start something crooked.' },
  { pt: 'A tinta seca, a ideia continua.', en: 'The ink dries, the idea goes on.' },
  { pt: 'Quem desenha enxerga mais.', en: 'Those who draw see more.' },
  { pt: 'Um bom desenho ainda está respirando.', en: 'A good drawing is still breathing.' },
  { pt: 'Cada página, uma pequena aposta.', en: 'Every page, a small bet.' },
  { pt: 'Sombras também são traços.', en: 'Shadows are strokes too.' },
  { pt: 'Faça de novo, mas diferente.', en: 'Do it again, but differently.' },
  { pt: 'O lápis não tem pressa.', en: 'The pencil is in no hurry.' },
  { pt: 'Existe um mundo dentro de um rabisco.', en: 'There is a world inside a doodle.' },
];

const WORD = 'Draw';

type Hit = { rect: DOMRect; key: string };

function caretAt(x: number, y: number): { node: Node; offset: number } | null {
  const doc = document as Document & {
    caretPositionFromPoint?: (x: number, y: number) => { offsetNode: Node; offset: number } | null;
    caretRangeFromPoint?: (x: number, y: number) => Range | null;
  };
  if (doc.caretPositionFromPoint) {
    const p = doc.caretPositionFromPoint(x, y);
    return p ? { node: p.offsetNode, offset: p.offset } : null;
  }
  const r = doc.caretRangeFromPoint?.(x, y);
  return r ? { node: r.startContainer, offset: r.startOffset } : null;
}

// Acha a palavra "Draw" sob o ponteiro, em qualquer texto da página (sem marcar nada no HTML).
function findDraw(x: number, y: number, target: EventTarget | null): Hit | null {
  const el = target instanceof Element ? target : null;
  if (!el || el.closest('.draw-tip, .wordmark, input, textarea, canvas')) return null;
  const caret = caretAt(x, y);
  if (!caret || caret.node.nodeType !== Node.TEXT_NODE) return null;
  const text = caret.node.textContent ?? '';
  const isLetter = (c: string) => /\p{L}/u.test(c);
  let a = Math.min(caret.offset, text.length);
  let b = a;
  while (a > 0 && isLetter(text[a - 1])) a--;
  while (b < text.length && isLetter(text[b])) b++;
  if (text.slice(a, b) !== WORD) return null;
  const range = document.createRange();
  range.setStart(caret.node, a);
  range.setEnd(caret.node, b);
  const rect = range.getBoundingClientRect();
  const slack = 3;
  if (x < rect.left - slack || x > rect.right + slack || y < rect.top - slack || y > rect.bottom + slack) return null;
  // Chave estável: posição do nó no documento + deslocamento.
  const nodes: Node[] = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) if (n.textContent?.includes(WORD)) nodes.push(n);
  return { rect, key: `${location.pathname}:${nodes.indexOf(caret.node)}:${a}` };
}

export default function DrawTip() {
  const { lang } = useLang();
  const [tip, setTip] = useState<{ left: number; top: number; below: boolean; index: number } | null>(null);
  const assigned = useRef(new Map<string, number>());
  const keyRef = useRef<string | null>(null);

  useEffect(() => {
    let frame = 0;
    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== 'mouse') return;
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const hit = findDraw(e.clientX, e.clientY, e.target);
        if (!hit) { keyRef.current = null; setTip((t) => (t ? null : t)); return; }
        if (keyRef.current === hit.key) return;
        keyRef.current = hit.key;
        let index = assigned.current.get(hit.key);
        if (index === undefined) {
          index = assigned.current.size % TIPS.length;
          assigned.current.set(hit.key, index);
        }
        const below = hit.rect.top < 70;
        const left = Math.min(Math.max(hit.rect.left + hit.rect.width / 2, 130), window.innerWidth - 130);
        setTip({ left, top: below ? hit.rect.bottom + 12 : hit.rect.top - 12, below, index });
      });
    };
    const hide = () => { keyRef.current = null; setTip(null); };
    document.addEventListener('pointermove', onMove, { passive: true });
    document.addEventListener('pointerleave', hide);
    window.addEventListener('scroll', hide, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerleave', hide);
      window.removeEventListener('scroll', hide);
    };
  }, []);

  if (!tip) return null;
  const phrase = TIPS[tip.index];
  return (
    <div
      className={`draw-tip${tip.below ? ' is-below' : ''}`}
      style={{ left: tip.left, top: tip.top, '--tint': `${12 + (tip.index % 6) * 5}%` } as CSSProperties}
      aria-hidden="true"
    >
      {lang === 'en' ? phrase.en : phrase.pt}
    </div>
  );
}
