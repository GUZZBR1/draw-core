export type Pt = [number, number];
export type Stroke = { pts: Pt[]; ink: string };
export type Project = { id: string; name: string; createdAt: number; updatedAt: number };
export type Drawing = { id: string; projectId: string; name: string; createdAt: number; updatedAt: number; strokes: Stroke[] };

// Tudo fica no armazenamento local do navegador: uma lista de projetos e, para cada projeto, uma lista de desenhos.
const PROJECTS_KEY = 'draw-studio-projects';
const drawingsKey = (projectId: string) => `draw-studio-drawings:${projectId}`;
const LEGACY_KEY = 'draw-studio-saves'; // salvamentos da barra lateral antiga (sem projetos)
const LEGACY_TTL_MS = 24 * 60 * 60 * 1000;

const newId = () => crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
const round = (n: number) => Math.round(n * 1000) / 1000;

function read<T>(key: string, valid: (v: unknown) => v is T): T[] {
  try {
    const raw = JSON.parse(localStorage.getItem(key) ?? '[]');
    return Array.isArray(raw) ? raw.filter(valid) : [];
  } catch {
    return [];
  }
}

function write(key: string, value: unknown): boolean {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false; // sem armazenamento ou cota cheia: o desenho continua na tela
  }
}

const isProject = (v: unknown): v is Project => !!v && typeof (v as Project).id === 'string' && typeof (v as Project).name === 'string';
const isDrawing = (v: unknown): v is Drawing => !!v && typeof (v as Drawing).id === 'string' && Array.isArray((v as Drawing).strokes);

let migrated = false;
/** Traz os salvamentos da barra lateral antiga para um projeto, uma única vez. */
function migrateLegacy() {
  if (migrated) return;
  migrated = true;
  let raw: unknown;
  try {
    raw = JSON.parse(localStorage.getItem(LEGACY_KEY) ?? 'null');
  } catch {
    return;
  }
  if (!Array.isArray(raw)) return;
  const now = Date.now();
  const old = raw.filter((e) => e && typeof e.id === 'string' && Array.isArray(e.strokes) && e.strokes.length && (e.permanent || now - e.updatedAt < LEGACY_TTL_MS));
  if (old.length) {
    const project: Project = { id: newId(), name: 'Salvamentos anteriores', createdAt: now, updatedAt: now };
    const drawings: Drawing[] = old.map((e, i) => ({
      id: newId(),
      projectId: project.id,
      name: `Desenho ${old.length - i}`,
      createdAt: e.updatedAt ?? now,
      updatedAt: e.updatedAt ?? now,
      strokes: e.strokes,
    }));
    if (!write(drawingsKey(project.id), drawings) || !write(PROJECTS_KEY, [...read(PROJECTS_KEY, isProject), project])) return; // sem espaço: tenta de novo na próxima visita
  }
  try { localStorage.removeItem(LEGACY_KEY); } catch { /* nada a fazer */ }
}

export function listProjects(): Project[] {
  migrateLegacy();
  return read(PROJECTS_KEY, isProject).sort((a, b) => b.updatedAt - a.updatedAt);
}

export const getProject = (id: string) => listProjects().find((p) => p.id === id) ?? null;

export function createProject(name: string): Project | null {
  const now = Date.now();
  const project: Project = { id: newId(), name: name.trim() || 'Sem nome', createdAt: now, updatedAt: now };
  return write(PROJECTS_KEY, [...listProjects(), project]) ? project : null;
}

export function renameProject(id: string, name: string): boolean {
  const list = listProjects();
  const project = list.find((p) => p.id === id);
  if (!project) return false;
  project.name = name.trim() || project.name;
  return write(PROJECTS_KEY, list);
}

export function deleteProject(id: string) {
  write(PROJECTS_KEY, listProjects().filter((p) => p.id !== id));
  try { localStorage.removeItem(drawingsKey(id)); } catch { /* nada a fazer */ }
}

export function listDrawings(projectId: string): Drawing[] {
  return read(drawingsKey(projectId), isDrawing).sort((a, b) => b.updatedAt - a.updatedAt);
}

export const getDrawing = (projectId: string, id: string) => listDrawings(projectId).find((d) => d.id === id) ?? null;

/** Os desenhos mais recentes de todos os projetos (só os que já têm traços). */
export function recentDrawings(limit: number): Drawing[] {
  return listProjects()
    .flatMap((p) => listDrawings(p.id))
    .filter((d) => d.strokes.length)
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, limit);
}

export function createDrawing(projectId: string): Drawing | null {
  const list = listDrawings(projectId);
  const now = Date.now();
  const drawing: Drawing = { id: newId(), projectId, name: `Desenho ${list.length + 1}`, createdAt: now, updatedAt: now, strokes: [] };
  if (!write(drawingsKey(projectId), [...list, drawing])) return null;
  touchProject(projectId, now);
  return drawing;
}

/** Grava os traços e/ou o nome de um desenho. Devolve false se o navegador recusou a gravação. */
export function saveDrawing(projectId: string, id: string, patch: { strokes?: Stroke[]; name?: string }): boolean {
  const list = listDrawings(projectId);
  const found = list.find((d) => d.id === id);
  if (!found) return false;
  if (patch.strokes) found.strokes = patch.strokes.map((s) => ({ ink: s.ink, pts: s.pts.map(([x, y]) => [round(x), round(y)] as Pt) }));
  if (patch.name !== undefined) found.name = patch.name.trim() || 'Sem título';
  found.updatedAt = Date.now();
  const ok = write(drawingsKey(projectId), list);
  if (ok) touchProject(projectId, found.updatedAt);
  return ok;
}

export function deleteDrawing(projectId: string, id: string) {
  write(drawingsKey(projectId), listDrawings(projectId).filter((d) => d.id !== id));
}

function touchProject(id: string, at: number) {
  const list = listProjects();
  const project = list.find((p) => p.id === id);
  if (project) {
    project.updatedAt = at;
    write(PROJECTS_KEY, list);
  }
}
