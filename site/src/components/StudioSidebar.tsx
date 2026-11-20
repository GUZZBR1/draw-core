import { forwardRef, useEffect, useRef, useState } from 'react';
import { AUTOSAVE_TTL_MS, type SaveEntry } from '../lib/studioSaves';

function Thumb({ strokes }: { strokes: SaveEntry['strokes'] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current!;
    const ctx = c.getContext('2d')!;
    const ink = getComputedStyle(document.body).getPropertyValue('--ink').trim() || '#22231f';
    ctx.clearRect(0, 0, c.width, c.height);
    ctx.lineWidth = 1.6;
    ctx.lineCap = ctx.lineJoin = 'round';
    for (const s of strokes) {
      ctx.strokeStyle = s.ink === '#22231f' ? ink : s.ink;
      ctx.beginPath();
      s.pts.forEach(([x, y], i) => (i ? ctx.lineTo(x * c.width, y * c.height) : ctx.moveTo(x * c.width, y * c.height)));
      ctx.stroke();
    }
  }, [strokes]);
  return <canvas ref={ref} width={96} height={64} className="studio-thumb" aria-hidden="true" />;
}

function when(entry: SaveEntry, now: number) {
  const time = new Date(entry.updatedAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  if (entry.permanent) return `${time} · salvo`;
  const left = Math.max(0, AUTOSAVE_TTL_MS - (now - entry.updatedAt));
  const h = Math.floor(left / 3_600_000);
  const m = Math.floor((left % 3_600_000) / 60_000);
  return `${time} · expira em ${h ? `${h} h ` : ''}${m} min`;
}

type Props = {
  open: boolean;
  saves: SaveEntry[];
  onOpenEntry: (e: SaveEntry) => void;
  onSave: (id: string) => void;
  onDelete: (id: string) => void;
  onClose: () => void;
};

const StudioSidebar = forwardRef<HTMLElement, Props>(function StudioSidebar({ open, saves, onOpenEntry, onSave, onDelete, onClose }, ref) {
  const [selected, setSelected] = useState<string | null>(null);
  const now = Date.now();
  const permanent = saves.filter((s) => s.permanent);
  const auto = saves.filter((s) => !s.permanent);
  const current = saves.find((s) => s.id === selected);

  const row = (e: SaveEntry) => (
    <li key={e.id}>
      <button type="button" className="studio-save" aria-pressed={e.id === selected} onClick={() => setSelected(e.id === selected ? null : e.id)}>
        <Thumb strokes={e.strokes} />
        <span className="studio-save-meta">
          <span>{e.strokes.length} {e.strokes.length === 1 ? 'traço' : 'traços'}</span>
          <span>{when(e, now)}</span>
        </span>
      </button>
    </li>
  );

  return (
    <aside ref={ref} id="studio-side" className={`studio-side${open ? ' is-open' : ''}`} aria-label="Salvamentos" aria-hidden={!open} inert={!open}>
      <div className="studio-side-head">
        <span>salvamentos</span>
        <button type="button" className="studio-exit" onClick={onClose} aria-label="Fechar barra lateral">fechar</button>
      </div>
      <p className="studio-side-note">O desenho é salvo automaticamente e fica guardado por 24 h. Para mantê-lo, escolha-o e toque em salvar.</p>

      {saves.length === 0 && <p className="studio-side-empty">Nada salvo ainda. Faça um traço.</p>}

      {permanent.length > 0 && (<><p className="studio-side-title">Salvos</p><ul className="studio-saves">{permanent.map(row)}</ul></>)}
      {auto.length > 0 && (<><p className="studio-side-title">Automáticos · 24 h</p><ul className="studio-saves">{auto.map(row)}</ul></>)}

      {current && (
        <div className="studio-side-actions">
          <button type="button" onClick={() => { onOpenEntry(current); }}>abrir</button>
          {current.permanent
            ? <button type="button" disabled>salvo</button>
            : <button type="button" onClick={() => onSave(current.id)}>salvar</button>}
          <button type="button" onClick={() => { onDelete(current.id); setSelected(null); }}>excluir</button>
        </div>
      )}
    </aside>
  );
});

export default StudioSidebar;
