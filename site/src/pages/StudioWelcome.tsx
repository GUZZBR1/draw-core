import { useEffect, useMemo, useRef } from 'react';
import { Link } from 'react-router-dom';
import StrokeThumb from '../components/StrokeThumb';
import { listProjects, recentDrawings } from '../lib/studioProjects';

/** Tela de entrada: o bonequinho da webcam pergunta o que construir; os desenhos mais recentes giram em volta. */
export default function StudioWelcome() {
  const recents = useMemo(() => recentDrawings(12), []);
  const projects = useMemo(() => listProjects(), []);
  const drawingCount = useMemo(() => recentDrawings(Infinity).length, []);
  const ringRef = useRef<HTMLDivElement>(null);

  // Carrossel elíptico: cada desenho percorre a elipse da tela; os de trás ficam menores e mais apagados.
  useEffect(() => {
    const ring = ringRef.current;
    if (!ring) return;
    const cards = Array.from(ring.children) as HTMLElement[];
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let angle = -Math.PI / 2;
    let last = performance.now();
    let raf = 0;
    const place = () => {
      const w = ring.clientWidth;
      const h = ring.clientHeight;
      const cw = cards[0]?.offsetWidth ?? 0;
      const ch = cards[0]?.offsetHeight ?? 0;
      const rx = Math.max(0, w / 2 - cw / 2 - 12);
      const ry = Math.max(0, h / 2 - ch / 2 - 12);
      cards.forEach((el, i) => {
        const a = angle + (i / cards.length) * Math.PI * 2;
        const depth = (Math.sin(a) + 1) / 2; // 0 = fundo (em cima), 1 = frente (embaixo)
        const scale = 0.7 + depth * 0.3;
        el.style.transform = `translate(${w / 2 + Math.cos(a) * rx - cw / 2}px, ${h / 2 + Math.sin(a) * ry - ch / 2}px) scale(${scale})`;
        el.style.opacity = String(0.4 + depth * 0.6);
        el.style.zIndex = String(Math.round(depth * 10));
      });
    };
    const tick = (now: number) => {
      angle += ((now - last) / 1000) * 0.07;
      last = now;
      place();
      raf = requestAnimationFrame(tick);
    };
    const run = () => {
      if (raf) return; // um unico laco, mesmo com ponteiro e foco pedindo ao mesmo tempo
      last = performance.now();
      raf = requestAnimationFrame(tick);
    };
    const stop = () => { cancelAnimationFrame(raf); raf = 0; };
    place();
    window.addEventListener('resize', place);
    if (!reduce) {
      run();
      // para enquanto o mouse ou o foco estiver sobre um desenho, para dar para clicar
      ring.addEventListener('pointerover', stop);
      ring.addEventListener('pointerout', run);
      ring.addEventListener('focusin', stop);
      ring.addEventListener('focusout', run);
    }
    return () => {
      stop();
      window.removeEventListener('resize', place);
      ring.removeEventListener('pointerover', stop);
      ring.removeEventListener('pointerout', run);
      ring.removeEventListener('focusin', stop);
      ring.removeEventListener('focusout', run);
    };
  }, [recents]);

  return (
    <section className="hub">
      <div className="hub-orbit" ref={ringRef} aria-label="Desenhos recentes">
        {recents.map((d) => (
          <Link key={d.id} className="hub-orbit-card" to={`/app/p/${d.projectId}/d/${d.id}`} aria-label={`Abrir ${d.name}`}>
            <StrokeThumb strokes={d.strokes} />
            <span>{d.name}</span>
          </Link>
        ))}
      </div>

      <div className="hub-welcome">
        <div className="hub-mascot">
          <p className="hub-bubble">O que vamos construir hoje?</p>
          <svg className="webcam-icon hub-mascot-art" viewBox="0 0 64 56" aria-hidden="true">
            <rect x="5" y="4" width="54" height="26" rx="9" />
            <circle className="webcam-lens" cx="32" cy="17" r="8" />
            <circle className="webcam-aperture hub-mascot-eye" cx="32" cy="17" r="3" />
            <circle className="webcam-status" cx="51" cy="12" r="2.2" />
            <path className="hub-mascot-smile" d="M27 24.5c1.6 1.6 3.4 2.2 5 2.2s3.4-.6 5-2.2" />
            <path d="M27 30v3c0 1.8 1.4 3 3 3h4c1.7 0 3-1.3 3-3v-3" />
            <path className="hub-mascot-arm" d="M5 20 1 27M59 20l4 7" />
            <path className="hub-mascot-arm" d="M29 36l-5 15M35 36l5 15" />
          </svg>
        </div>

        <nav className="hub-menu" aria-label="Começar">
          <Link className="hub-item" to="/app/new"><span aria-hidden="true">＋</span>Iniciar novo projeto</Link>
          <Link className="hub-item" to="/app/projects" state={{ intro: true }}><span aria-hidden="true">▤</span>Carregar projeto<em>{projects.length || ''}</em></Link>
          <Link className="hub-item" to="/app/library"><span aria-hidden="true">◫</span>Biblioteca<em>{drawingCount || ''}</em></Link>
        </nav>
      </div>
    </section>
  );
}
