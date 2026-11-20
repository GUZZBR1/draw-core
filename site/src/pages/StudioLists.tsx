import { useState, type FormEvent, type ReactNode } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import StrokeThumb from '../components/StrokeThumb';
import {
  createDrawing, createProject, deleteDrawing, deleteProject, getProject, listDrawings, listProjects,
  type Drawing, type Project,
} from '../lib/studioProjects';

const fmt = (t: number) => new Date(t).toLocaleString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

function Page({ title, sub, back, children }: { title: string; sub?: string; back: { to: string; label: string }; children: ReactNode }) {
  return (
    <section className="hub-page">
      <Link className="studio-exit" to={back.to}>← {back.label}</Link>
      <div className="hub-head">
        <h1 className="hub-title">{title}</h1>
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
    <Page title="Novo projeto" back={{ to: '/app', label: 'início' }}>
      <form className="hub-form" onSubmit={submit}>
        <label htmlFor="project-name">Nome do projeto</label>
        <input id="project-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={60} placeholder="Ex.: Suporte para fone" autoFocus autoComplete="off" />
        <button type="submit" className="hub-primary">criar projeto</button>
        {error && <p className="studio-cam-error" role="alert">Sem espaço no navegador para salvar o projeto.</p>}
      </form>
    </Page>
  );
}

function ProjectCard({ project, onDelete }: { project: Project; onDelete: () => void }) {
  const drawings = listDrawings(project.id);
  const preview = drawings.find((d) => d.strokes.length);
  return (
    <li className="hub-card-wrap">
      <Link className="hub-card" to={`/app/p/${project.id}`}>
        {preview ? <StrokeThumb strokes={preview.strokes} /> : <span className="studio-thumb is-empty" aria-hidden="true" />}
        <span className="hub-card-name">{project.name}</span>
        <span className="hub-card-meta">{plural(drawings.length, 'desenho', 'desenhos')} · {fmt(project.updatedAt)}</span>
      </Link>
      <DeleteButton label={`projeto ${project.name}`} onConfirm={onDelete} />
    </li>
  );
}

export function ProjectList() {
  const [projects, setProjects] = useState(() => listProjects());
  return (
    <Page title="Projetos" sub={projects.length ? plural(projects.length, 'projeto', 'projetos') : undefined} back={{ to: '/app', label: 'início' }}>
      <ul className="hub-grid">
        <li><Link className="hub-card is-new" to="/app/new"><span aria-hidden="true">＋</span>Novo projeto</Link></li>
        {projects.map((p) => (
          <ProjectCard key={p.id} project={p} onDelete={() => { deleteProject(p.id); setProjects(listProjects()); }} />
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
