import { historicDrawings } from '../data/historic-drawings';
import SketchPad from '../components/SketchPad';

export default function HomePage() {
  return (
    <main className="home-stage" id="page-content" aria-label="Draw, início">
      <section className="archive-gallery" aria-label="Desenhos que abriram caminhos">
        {historicDrawings.map((drawing, index) => (
          <a
            className="archive-card"
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
