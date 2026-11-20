import { useEffect, useRef, useState } from 'react';
import { paperLines, papers, type Paper } from '../data/papers';

const LINE_MS = 4800;

/** Os artigos (propostas de pesquisa) giram numa elipse em volta do título; clicar abre o resumo e a figura. */
export default function PapersPage() {
  const ringRef = useRef<HTMLDivElement>(null);
  const holdRef = useRef(false); // true enquanto ponteiro/foco estão sobre um cartão ou há um aberto
  const [open, setOpen] = useState<Paper | null>(null);
  const [line, setLine] = useState(0);
  const reduce = useRef(window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  useEffect(() => { holdRef.current = open !== null; }, [open]);

  // Carrossel elíptico: o que passa à frente fica maior e mais nítido, o de trás menor e apagado.
  useEffect(() => {
    const ring = ringRef.current;
    if (!ring) return;
    const cards = Array.from(ring.children) as HTMLElement[];
    let angle = -Math.PI / 2;
    let last = performance.now();
    let raf = 0;
    const place = () => {
      const w = ring.clientWidth;
      const h = ring.clientHeight;
      const cw = cards[0]?.offsetWidth ?? 0;
      const ch = cards[0]?.offsetHeight ?? 0;
      const rx = Math.max(0, w / 2 - cw / 2 - 8);
      const ry = Math.max(0, h / 2 - ch / 2 - 8);
      cards.forEach((el, i) => {
        const a = angle + (i / cards.length) * Math.PI * 2;
        const depth = (Math.sin(a) + 1) / 2; // 1 = frente (parte de baixo da elipse)
        const scale = 0.6 + 0.4 * depth;
        el.style.transform = `translate(-50%, -50%) translate(${Math.cos(a) * rx}px, ${Math.sin(a) * ry}px) scale(${scale})`;
        el.style.opacity = String(0.3 + 0.7 * depth);
        el.style.zIndex = depth > 0.62 ? '30' : '5'; // atras do titulo; na frente dele so quando passa por baixo
      });
    };
    const tick = (now: number) => {
      if (!holdRef.current) angle += ((now - last) / 1000) * 0.09;
      last = now;
      place();
      raf = requestAnimationFrame(tick);
    };
    place();
    window.addEventListener('resize', place);
    if (!reduce.current) raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', place);
    };
  }, []);

  // Pausa enquanto o ponteiro ou o foco estiver sobre o carrossel.
  const hold = (on: boolean) => { holdRef.current = on || open !== null; };

  useEffect(() => {
    if (reduce.current || open) return;
    const id = window.setInterval(() => setLine((l) => (l + 1) % paperLines.length), LINE_MS);
    return () => window.clearInterval(id);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(null); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  return (
    <main className={`papers${open ? ' has-open' : ''}`} id="page-content">
      <div
        className="papers-orbit"
        ref={ringRef}
        role="group"
        aria-label="Artigos"
        onPointerOver={() => hold(true)}
        onPointerOut={() => hold(false)}
        onFocus={() => hold(true)}
        onBlur={() => hold(false)}
      >
        {papers.map((p) => (
          <button
            key={p.n}
            type="button"
            className={`papers-card${open?.n === p.n ? ' is-open' : ''}`}
            aria-label={`Artigo ${p.n}: ${p.short}`}
            aria-expanded={open?.n === p.n}
            onClick={() => setOpen(open?.n === p.n ? null : p)}
          >
            <span className="papers-card-n">{p.n}</span>
            <span className="papers-card-name">{p.short}</span>
          </button>
        ))}
      </div>

      <div className="papers-center">
        <h1 className="papers-title">papers</h1>
        {open ? (
          <article className="papers-detail" aria-live="polite">
            <p className="papers-detail-kicker">proposta {open.n} de {papers.length} · ainda sem resultados</p>
            <h2 className="papers-detail-title">{open.title}</h2>
            <p className="papers-detail-blurb">{open.blurb}</p>
            <img className="papers-detail-figure" src={open.figure} alt="" loading="lazy" />
            <button type="button" className="papers-close" onClick={() => setOpen(null)}>fechar</button>
          </article>
        ) : (
          <p className="papers-line" key={line} aria-live="off">{paperLines[line]}</p>
        )}
      </div>
    </main>
  );
}
