import { useEffect, useState } from 'react';
import { historicDrawings } from '../data/historic-drawings';
import SketchPad from '../components/SketchPad';

// Tempo que cada cartao fica em destaque (igual ao hover) antes de passar ao proximo.
const HIGHLIGHT_MS = 7000;

export default function HomePage() {
  const [active, setActive] = useState(0);
  useEffect(() => {
    // Com "reduzir movimento" nao ha destaque automatico: so o hover reage.
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (reduce.matches) return;
    const timer = window.setInterval(
      () => setActive((current) => (current + 1) % historicDrawings.length),
      HIGHLIGHT_MS,
    );
    return () => window.clearInterval(timer);
  }, []);

  return (
    <main className="home-stage" id="page-content" aria-label="Draw, início">
      <section className="archive-gallery" aria-label="Desenhos que abriram caminhos">
        {historicDrawings.map((drawing, index) => (
          <a
            className={`archive-card${index === active ? ' is-active' : ''}`}
            href={drawing.source}
            key={drawing.title}
            target="_blank"
            rel="noreferrer"
            style={{ '--i': index } as React.CSSProperties}
            aria-label={`${drawing.title}, por ${drawing.artist}, ${drawing.year}. Abrir fonte.`}
          >
            <span className="archive-art-surface">
              <svg className="archive-trace" aria-hidden="true">
                <rect pathLength="1" />
              </svg>
              <img src={drawing.image} alt={drawing.alt} loading="lazy" />
            </span>
            <span className="archive-caption">
              <span className="archive-work">
                <span className="archive-title">{drawing.title}</span>
                <span className="archive-credit">
                  {drawing.artist} · {drawing.year}
                </span>
              </span>
              <span className="archive-source" aria-hidden="true">↗</span>
            </span>
          </a>
        ))}
      </section>
      <SketchPad />
    </main>
  );
}
