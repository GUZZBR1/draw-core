import { Fragment, type ReactNode } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { papers } from '../data/papers';

// Inclui os textos no carregamento da página, sem uma requisição por artigo.
const sources = import.meta.glob<string>('../../../docs/research/[0-9][0-9]-*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
});
const articles = new Map(
  Object.entries(sources).map(([path, markdown]) => [path.split('/').pop()?.slice(0, 2), markdown]),
);

/** **negrito** e *itálico*, sem HTML cru. */
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((s, i) => {
    if (s.startsWith('**') && s.endsWith('**')) return <strong key={i}>{s.slice(2, -2)}</strong>;
    if (s.startsWith('*') && s.endsWith('*') && s.length > 2) return <em key={i}>{s.slice(1, -1)}</em>;
    return <Fragment key={i}>{s}</Fragment>;
  });
}

/** O molde dos artigos é pequeno: # título, ## seção, parágrafos e as linhas de metadados logo após o título. */
function render(md: string): ReactNode[] {
  const blocks = md.trim().split(/\n{2,}/);
  return blocks.map((b, i) => {
    if (b.startsWith('# ')) return <h1 key={i}>{b.slice(2)}</h1>;
    if (b.startsWith('## ')) return <h2 key={i}>{b.slice(3)}</h2>;
    const lines = b.split('\n').map((l) => l.replace(/\s+$/, ''));
    if (lines.every((l) => l.startsWith('**') && l.includes(':**')) && i === 1) {
      return <p className="article-meta" key={i}>{lines.map((l, j) => <Fragment key={j}>{j > 0 && <br />}{inline(l)}</Fragment>)}</p>;
    }
    return <p key={i}>{inline(lines.join(' '))}</p>;
  });
}

export default function ArticlePage() {
  const { n = '' } = useParams();
  const id = n.padStart(2, '0');
  const idx = papers.findIndex((p) => p.n === id);
  const md = articles.get(id);

  if (idx === -1) return <Navigate to="/papers" replace />;
  const prev = papers[idx - 1];
  const next = papers[idx + 1];

  return (
    <main className="article" id="page-content">
      <Link className="article-back" to="/papers">← papers</Link>
      {md ? <article>{render(md)}</article> : <p>Não foi possível carregar este artigo.</p>}
      <nav className="article-nav" aria-label="Artigos">
        {prev ? <Link to={`/papers/${prev.n}`}>← {prev.n} {prev.short}</Link> : <span />}
        {next ? <Link to={`/papers/${next.n}`}>{next.n} {next.short} →</Link> : <span />}
      </nav>
    </main>
  );
}
