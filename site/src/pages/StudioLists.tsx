import { useEffect, useLayoutEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router-dom';
import StrokeThumb from '../components/StrokeThumb';
import {
  createDrawing, createProject, deleteDrawing, deleteProject, getProject, listDrawings, listProjects, renameProject,
  type Drawing, type Project,
} from '../lib/studioProjects';

const fmt = (t: number) => new Date(t).toLocaleString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

const INTRO_DELAY_MS = 450;
const INTRO_MS = 1100;

function Page({ title, sub, back, center, intro, children }: { title: string; sub?: string; back: { to: string; label: string }; center?: boolean; intro?: boolean; children: ReactNode }) {
  const titleRef = useRef<HTMLHeadingElement>(null);
  // Entrada: o titulo nasce grande no meio da tela e sobe ate o lugar dele; so depois o resto aparece.
  useLayoutEffect(() => {
    const el = titleRef.current;
    if (!intro || !el || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const r = el.getBoundingClientRect();
    const scale = Math.min(3, (window.innerWidth * 0.8) / r.width);
    const dx = window.innerWidth / 2 - (r.left + r.width / 2);
    const dy = window.innerHeight / 2 - (r.top + r.height / 2);
    const anim = el.animate(
      [{ transform: `translate(${dx}px, ${dy}px) scale(${scale})` }, { transform: `translate(${dx}px, ${dy}px) scale(${scale})`, offset: INTRO_DELAY_MS / (INTRO_DELAY_MS + INTRO_MS) }, { transform: 'none' }],
      { duration: INTRO_DELAY_MS + INTRO_MS, easing: 'cubic-bezier(.65, 0, .25, 1)', fill: 'backwards' },
    );
    return () => anim.cancel();
  }, [intro]);

  return (
    <section className={`hub-page${center ? ' is-centered' : ''}${intro ? ' has-intro' : ''}`}>
      <Link className="studio-exit" to={back.to}>← {back.label}</Link>
      <div className="hub-head">
        <h1 className="hub-title" ref={titleRef}>{title}</h1>
        {sub && <p className="hub-sub">{sub}</p>}
      </div>
      {children}
    </section>
  );
}

/** Excluir em dois toques: o primeiro pede confirmação. */
function DeleteButton({ label, onConfirm }: { label: string; onConfirm: () => void }) {
  const [asking, setAsking] = useState(false);
  return (
    <button
      type="button"
      className={`hub-delete${asking ? ' is-asking' : ''}`}
      aria-label={asking ? `Confirmar: excluir ${label}` : `Excluir ${label}`}
      onClick={() => (asking ? onConfirm() : setAsking(true))}
      onBlur={() => setAsking(false)}
    >
      {asking ? 'confirmar?' : 'excluir'}
    </button>
  );
}

export function NewProject() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [error, setError] = useState(false);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const project = createProject(name);
    if (!project) {
      setError(true);
      return;
    }
    navigate(`/app/p/${project.id}`);
  };
  return (
    <Page title="Novo projeto" back={{ to: '/app', label: 'início' }} center>
      <form className="hub-form" onSubmit={submit}>
        <label htmlFor="project-name">Nome do projeto</label>
        <input id="project-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={60} placeholder="Ex.: Suporte para fone" autoFocus autoComplete="off" />
        <button type="submit" className="hub-primary">criar projeto</button>
        {error && <p className="studio-cam-error" role="alert">Sem espaço no navegador para salvar o projeto.</p>}
      </form>
    </Page>
  );
}

function ProjectCard({ project, onRename, onDelete }: { project: Project; onRename: (name: string) => void; onDelete: () => void }) {
  const drawings = listDrawings(project.id);
  const preview = drawings.find((d) => d.strokes.length);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(project.name);
  const cancelled = useRef(false);
  const thumb = preview ? <StrokeThumb strokes={preview.strokes} /> : <span className="studio-thumb is-empty" aria-hidden="true" />;
  const meta = <span className="hub-card-meta">{plural(drawings.length, 'desenho', 'desenhos')} · {fmt(project.updatedAt)}</span>;

  const commit = () => {
    if (cancelled.current) return;
    setEditing(false);
    const next = name.trim() || project.name;
    setName(next);
    if (next !== project.name) onRename(next);
  };

  return (
    <li className="hub-card-wrap">
      {editing ? (
        <div className="hub-card is-editing">
          {thumb}
          <input
            className="hub-card-input"
            value={name}
            maxLength={60}
            aria-label="Nome do projeto"
            autoFocus
            onFocus={(e) => e.currentTarget.select()}
            onChange={(e) => setName(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === 'Enter') e.currentTarget.blur();
              if (e.key === 'Escape') {
                cancelled.current = true;
                setName(project.name);
                setEditing(false);
              }
            }}
          />
          {meta}
        </div>
      ) : (
        <>
          <Link className="hub-card" to={`/app/p/${project.id}`}>
            {thumb}
            <span className="hub-card-name">{project.name}</span>
            {meta}
          </Link>
          <button type="button" className="hub-edit" aria-label={`Renomear projeto ${project.name}`} onClick={() => { cancelled.current = false; setEditing(true); }}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20l1-4L16.5 4.5a2 2 0 0 1 3 3L8 19l-4 1zM14.5 6.5l3 3" /></svg>
          </button>
        </>
      )}
      <DeleteButton label={`projeto ${project.name}`} onConfirm={onDelete} />
    </li>
  );
}

export function ProjectList() {
  const [projects, setProjects] = useState(() => listProjects());
  const location = useLocation();
  const navigate = useNavigate();
  // A animacao so toca ao chegar pela tela de inicio; voltar de um projeto (ou recarregar) mostra a lista direto.
  const [intro] = useState(() => !!(location.state as { intro?: boolean } | null)?.intro);
  useEffect(() => {
    if (intro) navigate(location.pathname, { replace: true, state: null }); // o botao voltar do navegador nao a repete
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <Page title="Projetos" sub={projects.length ? plural(projects.length, 'projeto', 'projetos') : undefined} back={{ to: '/app', label: 'início' }} intro={intro}>
      <ul className="hub-grid">
        <li><Link className="hub-card is-new" to="/app/new"><span aria-hidden="true">＋</span>Novo projeto</Link></li>
        {projects.map((p) => (
          <ProjectCard key={p.id} project={p} onRename={(name) => { renameProject(p.id, name); setProjects(listProjects()); }} onDelete={() => { deleteProject(p.id); setProjects(listProjects()); }} />
        ))}
      </ul>
      {projects.length === 0 && <p className="hub-empty">Nenhum projeto ainda. Crie o primeiro.</p>}
    </Page>
  );
}

function DrawingCard({ drawing, onDelete }: { drawing: Drawing; onDelete?: () => void }) {
  return (
    <li className="hub-card-wrap">
      <Link className="hub-card" to={`/app/p/${drawing.projectId}/d/${drawing.id}`}>
        {drawing.strokes.length ? <StrokeThumb strokes={drawing.strokes} /> : <span className="studio-thumb is-empty" aria-hidden="true" />}
        <span className="hub-card-name">{drawing.name}</span>
        <span className="hub-card-meta">{plural(drawing.strokes.length, 'traço', 'traços')} · {fmt(drawing.updatedAt)}</span>
      </Link>
      {onDelete && <DeleteButton label={drawing.name} onConfirm={onDelete} />}
    </li>
  );
}

export function ProjectView() {
  const { projectId = '' } = useParams();
  const navigate = useNavigate();
  const project = getProject(projectId);
  const [drawings, setDrawings] = useState(() => listDrawings(projectId));
  const [error, setError] = useState(false);
  if (!project) return <Navigate to="/app/projects" replace />;

  const add = () => {
    const drawing = createDrawing(project.id);
    if (!drawing) {
      setError(true);
      return;
    }
    navigate(`/app/p/${project.id}/d/${drawing.id}`);
  };

  return (
    <Page title={project.name} sub={plural(drawings.length, 'desenho', 'desenhos')} back={{ to: '/app/projects', label: 'projetos' }}>
      <ul className="hub-grid">
        <li><button type="button" className="hub-card is-new" onClick={add}><span aria-hidden="true">＋</span>Novo</button></li>
        {drawings.map((d) => (
          <DrawingCard key={d.id} drawing={d} onDelete={() => { deleteDrawing(project.id, d.id); setDrawings(listDrawings(project.id)); }} />
        ))}
      </ul>
      {error && <p className="studio-cam-error" role="alert">Sem espaço no navegador para criar o desenho.</p>}
    </Page>
  );
}

export function Library() {
  const [projects] = useState(() => listProjects());
  const groups = projects.map((p) => ({ project: p, drawings: listDrawings(p.id).filter((d) => d.strokes.length) })).filter((g) => g.drawings.length);
  return (
    <Page title="Biblioteca" sub="todos os desenhos, de todos os projetos" back={{ to: '/app', label: 'início' }}>
      {groups.map(({ project, drawings }) => (
        <div key={project.id} className="hub-group">
          <Link className="hub-group-title" to={`/app/p/${project.id}`}>{project.name}</Link>
          <ul className="hub-grid">
            {drawings.map((d) => <DrawingCard key={d.id} drawing={d} />)}
          </ul>
        </div>
      ))}
      {groups.length === 0 && <p className="hub-empty">Nenhum desenho ainda. Abra um projeto e clique em Novo.</p>}
    </Page>
  );
}
