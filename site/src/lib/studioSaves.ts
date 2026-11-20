export type Pt = [number, number];
export type Stroke = { pts: Pt[]; ink: string };
export type SaveEntry = { id: string; updatedAt: number; strokes: Stroke[]; permanent: boolean };

const KEY = 'draw-studio-saves';
export const AUTOSAVE_TTL_MS = 24 * 60 * 60 * 1000;

function persist(list: SaveEntry[]): boolean {
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
    return true;
  } catch {
    return false; // sem armazenamento ou cota cheia: o desenho continua na tela
  }
}

/** Le os salvamentos e descarta os automaticos com mais de 24 h. */
export function readSaves(now = Date.now()): SaveEntry[] {
  let list: SaveEntry[] = [];
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? '[]');
    if (Array.isArray(raw)) list = raw.filter((e) => e && typeof e.id === 'string' && Array.isArray(e.strokes));
  } catch {
    list = [];
  }
  const alive = list.filter((e) => e.permanent || now - e.updatedAt < AUTOSAVE_TTL_MS);
  if (alive.length !== list.length) persist(alive);
  return alive.sort((a, b) => b.updatedAt - a.updatedAt);
}

const round = (n: number) => Math.round(n * 1000) / 1000;

export function upsertAutosave(id: string, strokes: Stroke[]): SaveEntry[] {
  const list = readSaves();
  const snapshot = strokes.map((s) => ({ ink: s.ink, pts: s.pts.map(([x, y]) => [round(x), round(y)] as Pt) }));
  const found = list.find((e) => e.id === id);
  if (found) {
    found.strokes = snapshot;
    found.updatedAt = Date.now();
  } else {
    list.push({ id, strokes: snapshot, updatedAt: Date.now(), permanent: false });
  }
  persist(list);
  return list.sort((a, b) => b.updatedAt - a.updatedAt);
}

export function makePermanent(id: string): SaveEntry[] {
  const list = readSaves();
  const entry = list.find((e) => e.id === id);
  if (entry) entry.permanent = true;
  persist(list);
  return list;
}

export function removeSave(id: string): SaveEntry[] {
  const list = readSaves().filter((e) => e.id !== id);
  persist(list);
  return list;
}
