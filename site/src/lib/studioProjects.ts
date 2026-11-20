export type Pt = [number, number];
export type Stroke = { pts: Pt[]; ink: string };
export type Project = { id: string; name: string; createdAt: number; updatedAt: number };
export type Drawing = { id: string; projectId: string; name: string; createdAt: number; updatedAt: number; strokes: Stroke[]; rev?: number };

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
// Importacao que o navegador nao deixou gravar (sem espaco para uma segunda copia): continua visivel, so em memoria,
// e a gravacao e tentada de novo a cada leitura. O arquivo antigo so e apagado depois que o novo esta gravado.
let legacyPending: { project: Project; drawings: Drawing[] } | null = null;
const isPendingProject = (id: string) => legacyPending?.project.id === id;

function commitLegacy(project: Project, drawings: Drawing[]): boolean {
  if (!write(drawingsKey(project.id), drawings)) return false;
  const stored = read(PROJECTS_KEY, isProject).filter((p) => p.id !== project.id); // sem duplicar se ja estiver gravado
  if (!write(PROJECTS_KEY, [...stored, project])) {
    try { localStorage.removeItem(drawingsKey(project.id)); } catch { /* nada a fazer */ } // sem registro orfao ocupando cota
    return false;
  }
  try { localStorage.removeItem(LEGACY_KEY); } catch { /* nada a fazer */ }
  return true;
}

/** Traz os salvamentos da barra lateral antiga para um projeto, uma única vez. */
function migrateLegacy() {
  if (legacyPending) {
    let sourceLeft = true;
    try { sourceLeft = localStorage.getItem(LEGACY_KEY) !== null; } catch { /* sem leitura: tenta como antes */ }
    if (!sourceLeft) { // outra aba ja concluiu esta importacao: descarta a copia em memoria desta
      legacyPending = null;
      return;
    }
    if (commitLegacy(legacyPending.project, legacyPending.drawings)) legacyPending = null;
    return;
  }
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
    if (!commitLegacy(project, drawings)) legacyPending = { project, drawings };
    return;
  }
  try { localStorage.removeItem(LEGACY_KEY); } catch { /* nada a fazer */ }
}

/** Só o que está gravado: todo caminho de escrita parte daqui (o projeto pendente só existe em memória). */
const storedProjects = () => read(PROJECTS_KEY, isProject);

export function listProjects(): Project[] {
  migrateLegacy();
  const list = storedProjects();
  if (legacyPending) list.push(legacyPending.project);
  return list.sort((a, b) => b.updatedAt - a.updatedAt);
}

/** O projeto é a importação ainda não gravada: abre só para leitura (nada que se faça nele pode ser gravado). */
export const isPendingImport = (projectId: string) => isPendingProject(projectId);

export const getProject = (id: string) => listProjects().find((p) => p.id === id) ?? null;

export function createProject(name: string): Project | null {
  const now = Date.now();
  const project: Project = { id: newId(), name: name.trim() || 'Sem nome', createdAt: now, updatedAt: now };
  return write(PROJECTS_KEY, [...storedProjects(), project]) ? project : null;
}

export function renameProject(id: string, name: string): boolean {
  const list = storedProjects();
  const project = list.find((p) => p.id === id);
  if (!project || isPendingProject(id)) return false;
  project.name = name.trim() || project.name;
  return write(PROJECTS_KEY, list);
}

export function deleteProject(id: string) {
  if (isPendingProject(id)) return; // ainda nao gravado: nada a apagar (e o arquivo antigo segue intacto)
  write(PROJECTS_KEY, storedProjects().filter((p) => p.id !== id));
  try { localStorage.removeItem(drawingsKey(id)); } catch { /* nada a fazer */ }
}

export function listDrawings(projectId: string): Drawing[] {
  if (legacyPending && isPendingProject(projectId)) return [...legacyPending.drawings].sort((a, b) => b.updatedAt - a.updatedAt);
  return read(drawingsKey(projectId), isDrawing).sort((a, b) => b.updatedAt - a.updatedAt);
}

export const getDrawing = (projectId: string, id: string) => listDrawings(projectId).find((d) => d.id === id) ?? null;

/** Quantos desenhos existem (inclusive os em branco): a mesma conta da Biblioteca. */
export const drawingCount = () => listProjects().reduce((n, p) => n + listDrawings(p.id).length, 0);

/** Os desenhos mais recentes de todos os projetos (só os que já têm traços). */
export function recentDrawings(limit: number): Drawing[] {
  return listProjects()
    .flatMap((p) => listDrawings(p.id))
    .filter((d) => d.strokes.length)
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, limit);
}

export function createDrawing(projectId: string): Drawing | null {
  if (isPendingProject(projectId)) return null;
  const list = listDrawings(projectId);
  const now = Date.now();
  const drawing: Drawing = { id: newId(), projectId, name: `Desenho ${list.length + 1}`, createdAt: now, updatedAt: now, strokes: [] };
  if (!write(drawingsKey(projectId), [...list, drawing])) return null;
  touchProject(projectId, now);
  return drawing;
}

/** Grava os traços e/ou o nome de um desenho. Devolve false se o navegador recusou a gravação. */
export function saveDrawing(projectId: string, id: string, patch: { strokes?: Stroke[]; name?: string }): boolean {
  if (isPendingProject(projectId)) return false;
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

export type StrokesSave = { status: 'ok' | 'failed' | 'stale'; rev: number };

const snapshot = (strokes: Stroke[]) => strokes.map((s) => ({ ink: s.ink, pts: s.pts.map(([x, y]) => [round(x), round(y)] as Pt) }));

/**
 * Grava os traços de um desenho só se o armazenamento ainda estiver na revisão que o editor carregou ou gravou por
 * último. Com outra aba tendo gravado antes ('stale'), nada é sobrescrito; quem chama guarda os traços em outro lugar.
 */
export function saveStrokes(projectId: string, id: string, strokes: Stroke[], baseRev: number): StrokesSave {
  if (isPendingProject(projectId)) return { status: 'failed', rev: baseRev };
  const list = listDrawings(projectId);
  const found = list.find((d) => d.id === id);
  if (!found) return { status: 'failed', rev: baseRev };
  const current = found.rev ?? 0;
  if (current !== baseRev) return { status: 'stale', rev: current };
  found.strokes = snapshot(strokes);
  found.rev = current + 1;
  found.updatedAt = Date.now();
  if (!write(drawingsKey(projectId), list)) return { status: 'failed', rev: baseRev };
  touchProject(projectId, found.updatedAt);
  return { status: 'ok', rev: found.rev };
}

/** Guarda traços que não puderam sobrescrever o desenho original como um desenho novo do mesmo projeto. */
export function saveStrokesAsCopy(projectId: string, name: string, strokes: Stroke[]): Drawing | null {
  if (isPendingProject(projectId)) return null;
  const list = listDrawings(projectId);
  const now = Date.now();
  const copy: Drawing = { id: newId(), projectId, name: `${name} (cópia)`, createdAt: now, updatedAt: now, strokes: snapshot(strokes), rev: 1 };
  if (!write(drawingsKey(projectId), [...list, copy])) return null;
  touchProject(projectId, now);
  return copy;
}

export function deleteDrawing(projectId: string, id: string) {
  if (isPendingProject(projectId)) return;
  write(drawingsKey(projectId), listDrawings(projectId).filter((d) => d.id !== id));
}

function touchProject(id: string, at: number) {
  const list = storedProjects();
  const project = list.find((p) => p.id === id);
  if (project) {
    project.updatedAt = at;
    write(PROJECTS_KEY, list);
  }
}
