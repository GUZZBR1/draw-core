import { useEffect, useRef, type CSSProperties, type MouseEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import ProductAsciiArt from '../components/ProductAsciiArt';

export default function ProductPage() {
  const navigate = useNavigate();
  const timer = useRef<number>(0);
  useEffect(() => () => {
    window.clearTimeout(timer.current);
    document.body.classList.remove('is-falling');
  }, []);

  const enterStudio = (event: MouseEvent) => {
    event.preventDefault();
    if (document.body.classList.contains('is-falling')) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      navigate('/app');
      return;
    }
    document.body.classList.add('is-falling');
    timer.current = window.setTimeout(() => {
      navigate('/app');
      // O estudio ja nasce coberto pelo flash branco; so entao soltamos a queda.
      requestAnimationFrame(() => requestAnimationFrame(() => document.body.classList.remove('is-falling')));
    }, 1600);
  };

  return (
    <main className="product-page" id="page-content">
      <section className="product-content">
        <Link className="product-status product-emerge group" style={{ '--emerge': 300 } as CSSProperties} to="/app" onClick={enterStudio} aria-label="Em construção. Abrir o Draw.">
          <span className="status-dot" />
          em construção
          <span className="status-arrow" aria-hidden="true">↗</span>
        </Link>
        <figure className="construction-art">
          <ProductAsciiArt />
        </figure>
        <h1 className="product-headline product-emerge" style={{ '--emerge': 900 } as CSSProperties}>
          Do primeiro traço
          <br />
          <em>à próxima geração.</em>
        </h1>
        <p className="product-description product-emerge" style={{ '--emerge': 1500 } as CSSProperties}>
          Estamos construindo uma ponte entre o papel e as ferramentas que projetam e testam o
          mundo. A ideia começa à mão; o que ela pode se tornar ainda está sendo desenhado.
        </p>

        <Link className="vision-cta product-emerge" style={{ '--emerge': 2100 } as CSSProperties} to="/vision">
          Leia a visão <span aria-hidden="true">↗</span>
        </Link>
      </section>
    </main>
  );
}
