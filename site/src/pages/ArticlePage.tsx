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

const URL_AT_END = /^(https?:\/\/.*?)([.,;:)\]]*)$/;

/** **negrito**, *itálico* e endereços http(s) viram links; nada de HTML cru. */
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|https?:\/\/\S+)/g).map((s, i) => {
    if (s.startsWith('**') && s.endsWith('**') && s.length > 4) return <strong key={i}>{s.slice(2, -2)}</strong>;
    if (s.startsWith('*') && s.endsWith('*') && s.length > 2) return <em key={i}>{s.slice(1, -1)}</em>;
    const url = /^https?:\/\//.test(s) ? URL_AT_END.exec(s) : null;
    if (url) {
      return (
        <Fragment key={i}>
          <a href={url[1]} target="_blank" rel="noopener noreferrer">{url[1]}</a>
          {url[2]}
        </Fragment>
      );
    }
    return <Fragment key={i}>{s}</Fragment>;
  });
}

const isRow = (l: string) => l.trimStart().startsWith('|');
const cells = (l: string) => l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());

/** Subconjunto de Markdown usado pelos artigos: títulos, parágrafos, listas, tabelas e referências; figuras ficam de fora. */
function render(md: string): ReactNode[] {
  const out: ReactNode[] = [];
  md.trim().split(/\n{2,}/).forEach((b, i) => {
    const lines = b.split('\n').map((l) => l.replace(/\s+$/, '')).filter(Boolean);
    if (lines.length === 0) return;
    if (b.startsWith('# ')) out.push(<h1 key={i}>{b.slice(2)}</h1>);
    else if (b.startsWith('## ')) out.push(<h2 key={i}>{b.slice(3)}</h2>);
    else if (b.startsWith('### ')) out.push(<h3 key={i}>{b.slice(4)}</h3>);
    else if (lines.every((l) => /^!\[[^\]]*\]\([^)]*\)$/.test(l))) return; // figuras nao entram na leitura
    else if (lines.every(isRow)) {
      const rows = lines.map(cells).filter((r) => !r.every((c) => /^:?-{3,}:?$/.test(c)));
      const [head, ...body] = rows;
      out.push(
        <div className="article-table" key={i} role="region" aria-label="Tabela" tabIndex={0}>
          <table>
            <thead><tr>{head.map((c, j) => <th key={j} scope="col">{inline(c)}</th>)}</tr></thead>
            <tbody>{body.map((r, j) => <tr key={j}>{r.map((c, k) => <td key={k}>{inline(c)}</td>)}</tr>)}</tbody>
          </table>
        </div>,
      );
    } else if (lines.every((l) => /^[-*] /.test(l))) {
      out.push(<ul key={i}>{lines.map((l, j) => <li key={j}>{inline(l.slice(2))}</li>)}</ul>);
    } else if (lines.every((l) => /^\d+\. /.test(l))) {
      out.push(<ol key={i}>{lines.map((l, j) => <li key={j}>{inline(l.replace(/^\d+\. /, ''))}</li>)}</ol>);
    } else if (lines.length > 1 && lines.every((l) => /^\[\d+\] /.test(l))) {
      out.push(<ul className="article-refs" key={i}>{lines.map((l, j) => <li key={j}>{inline(l)}</li>)}</ul>);
    } else if (i === 1 && lines.every((l) => l.startsWith('**') && l.includes(':**'))) {
      out.push(<p className="article-meta" key={i}>{lines.map((l, j) => <Fragment key={j}>{j > 0 && <br />}{inline(l)}</Fragment>)}</p>);
    } else {
      out.push(<p key={i}>{inline(lines.join(' '))}</p>);
    }
  });
  return out;
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
