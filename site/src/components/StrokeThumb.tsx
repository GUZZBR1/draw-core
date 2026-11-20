import { useEffect, useRef, useState } from 'react';
import type { Stroke } from '../lib/studioProjects';

/** Miniatura de um desenho: redesenha os traços normalizados em um canvas pequeno. */
export default function StrokeThumb({ strokes }: { strokes: Stroke[] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  // O tema muda a tinta padrao: observa a classe do body para redesenhar a miniatura.
  const [dark, setDark] = useState(() => document.body.classList.contains('dark'));
  useEffect(() => {
    const watch = new MutationObserver(() => setDark(document.body.classList.contains('dark')));
    watch.observe(document.body, { attributes: true, attributeFilter: ['class'] });
    return () => watch.disconnect();
  }, []);
  useEffect(() => {
    const c = ref.current!;
    const ctx = c.getContext('2d')!;
    const ink = getComputedStyle(document.body).getPropertyValue('--ink').trim() || '#22231f';
    ctx.clearRect(0, 0, c.width, c.height);
    ctx.lineWidth = 2;
    ctx.lineCap = ctx.lineJoin = 'round';
    for (const s of strokes) {
      ctx.strokeStyle = s.ink === '#22231f' ? ink : s.ink;
      if (s.pts.length === 1) { // toque sem arrasto: um ponto
        ctx.fillStyle = ctx.strokeStyle;
        ctx.beginPath();
        ctx.arc(s.pts[0][0] * c.width, s.pts[0][1] * c.height, ctx.lineWidth / 2, 0, Math.PI * 2);
        ctx.fill();
        continue;
      }
      ctx.beginPath();
      s.pts.forEach(([x, y], i) => (i ? ctx.lineTo(x * c.width, y * c.height) : ctx.moveTo(x * c.width, y * c.height)));
      ctx.stroke();
    }
  }, [strokes, dark]);
  return <canvas ref={ref} width={240} height={160} className="studio-thumb" aria-hidden="true" />;
}
