import { Link } from 'react-router-dom';
import { useEffect, useRef, useState, type CSSProperties } from 'react';
import ProductAsciiArt from '../components/ProductAsciiArt';
import { paperLines, papers, type Paper } from '../data/papers';

const LINE_MS = 4800;
const reduceMotionInitial = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Os artigos (propostas de pesquisa) giram numa elipse em volta do título; clicar abre o resumo e a figura. */
export default function PapersPage() {
  const ringRef = useRef<HTMLDivElement>(null);
  const moreRef = useRef<HTMLElement>(null);
  const [moreSeen, setMoreSeen] = useState(reduceMotionInitial());
  const openRef = useRef(false); // com um resumo aberto o carrossel desacelera ate parar, sem corte seco
  const focusRef = useRef(false); // idem enquanto o foco do teclado esta num cartao (o alvo nao pode fugir)
  const [open, setOpen] = useState<Paper | null>(null);
  const [line, setLine] = useState(0);
  const reduce = useRef(window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  useEffect(() => { openRef.current = open !== null; }, [open]);

  // A seção de subprojetos sai da "neblina" quando entra na tela ao rolar.
  useEffect(() => {
    const el = moreRef.current;
    if (!el || moreSeen) return;
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setMoreSeen(true); io.disconnect(); }
    }, { threshold: 0.2 });
    io.observe(el);
    return () => io.disconnect();
  }, [moreSeen]);

  // Carrossel elíptico: o que passa à frente fica maior e mais nítido, o de trás menor e apagado.
  // Por quadro so se escrevem transform/opacity (nenhuma leitura de layout): medidas ficam em cache e
  // so mudam num ResizeObserver; o ponteiro nunca pausa a rotacao; so abrir um resumo ou focar um cartao a desacelera.
  useEffect(() => {
    const ring = ringRef.current;
    if (!ring) return;
    const cards = Array.from(ring.children) as HTMLElement[];
    const front = cards.map(() => false);
    let rx = 0;
    let ry = 0;
    const measure = () => {
      const cw = cards[0]?.offsetWidth ?? 0;
      const ch = cards[0]?.offsetHeight ?? 0;
      rx = Math.max(0, ring.clientWidth / 2 - cw / 2 - 8);
      ry = Math.max(0, ring.clientHeight / 2 - ch / 2 - 8);
    };
    let angle = -Math.PI / 2;
    let speed = 0.09; // rad/s
    let last = performance.now();
    let raf = 0;
    const place = () => {
      cards.forEach((el, i) => {
        const a = angle + (i / cards.length) * Math.PI * 2;
        const depth = (Math.sin(a) + 1) / 2; // 1 = frente (parte de baixo da elipse)
        const scale = 0.6 + 0.4 * depth;
        el.style.transform = `translate3d(calc(-50% + ${(Math.cos(a) * rx).toFixed(2)}px), calc(-50% + ${(Math.sin(a) * ry).toFixed(2)}px), 0) scale(${scale.toFixed(4)})`;
        el.style.opacity = (0.3 + 0.7 * depth).toFixed(3);
        const f = depth > 0.62; // atras do titulo; na frente dele so quando passa por baixo
        if (f !== front[i]) { front[i] = f; el.style.zIndex = f ? '30' : '5'; }
      });
    };
    const tick = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.05); // aba em segundo plano nao da salto
      last = now;
      const target = openRef.current || focusRef.current ? 0 : 0.09;
      speed += (target - speed) * Math.min(1, dt * 4);
      angle += speed * dt;
      place();
      raf = requestAnimationFrame(tick);
    };
    measure();
    place();
    const ro = new ResizeObserver(() => { measure(); place(); });
    ro.observe(ring);
    if (!reduce.current) raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

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
    <>
      <ProductAsciiArt src="/images/papers/macaco-cientista.png" className="papers-ascii-bg" decorative richLight />
    <main className={`papers${open ? ' has-open' : ''}`} id="page-content">
      <div
        className="papers-orbit product-emerge"
        style={{ '--emerge': 1500 } as CSSProperties}
        ref={ringRef}
        onFocus={() => { focusRef.current = true; }}
        onBlur={() => { focusRef.current = false; }}
        role="group"
        aria-label="Artigos"
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
        <h1 className="papers-title product-emerge" style={{ '--emerge': 300 } as CSSProperties}>papers</h1>
        {open ? (
          <article className="papers-detail" aria-live="polite">
            <p className="papers-detail-kicker">proposta {open.n} de {papers.length} · ainda sem resultados</p>
            <h2 className="papers-detail-title">{open.title}</h2>
            <p className="papers-detail-blurb">{open.blurb}</p>
            <div className="papers-detail-actions">
              <Link className="papers-open" to={`/papers/${open.n}`}>abrir artigo</Link>
              <button type="button" className="papers-close" onClick={() => setOpen(null)}>fechar</button>
            </div>
          </article>
        ) : (
          <div className="product-emerge" style={{ '--emerge': 900 } as CSSProperties}>
            <p className="papers-line" key={line} aria-live="off">{paperLines[line]}</p>
          </div>
        )}
      </div>
    </main>

    <section className={`papers-more${moreSeen ? ' is-in' : ''}`} ref={moreRef} aria-labelledby="papers-more-title">
      <p className="papers-more-kicker">além dos papers</p>
      <h2 className="papers-more-title" id="papers-more-title">Subprojetos</h2>
      <p className="papers-more-lead">
        Pesquisar o Draw pediu mais do que o próprio Draw: algumas peças ficaram grandes ou
        independentes o bastante para virar projetos separados. Aqui ficam os que nasceram disso.
      </p>
      <a className="papers-sub" href="https://github.com/santleme/hvcam" target="_blank" rel="noreferrer">
        <span className="papers-sub-name">
          hvcam
          <svg className="papers-sub-gh" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
            <path
              fill="currentColor"
              d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.6 7.6 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"
            />
          </svg>
        </span>
        <span className="papers-sub-text">
          Leva a webcam do Windows para dentro do WSL2, sem kernel customizado, sem usbipd e sem
          administrador. Foi a ponte de captura do Draw.
        </span>
        <span className="papers-sub-link">github.com/santleme/hvcam ↗</span>
      </a>
    </section>
    </>
  );
}
