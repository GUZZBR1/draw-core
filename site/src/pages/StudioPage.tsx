import { createPortal } from 'react-dom';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, Navigate, useOutletContext, useParams } from 'react-router-dom';
import type { StudioContext } from '../components/StudioShell';
import { DrawCloud, isCloudConfigured, type CloudResult, type CloudStatus } from '../lib/drawCloud';
import { getDrawing, getProject, isPendingImport, saveDrawing, saveStrokes, saveStrokesAsCopy, type Drawing, type Pt } from '../lib/studioProjects';

const INKS = ['#22231f', '#3b5ba5', '#b5483a'];

function drawSmooth(ctx: CanvasRenderingContext2D, pts: Pt[], w: number, h: number) {
  if (pts.length === 1) { // toque sem arrasto: um ponto da cor e da espessura do traço
    ctx.fillStyle = ctx.strokeStyle;
    ctx.beginPath();
    ctx.arc(pts[0][0] * w, pts[0][1] * h, ctx.lineWidth / 2, 0, Math.PI * 2);
    ctx.fill();
    return;
  }
  if (pts.length < 2) return;
  ctx.beginPath();
  ctx.moveTo(pts[0][0] * w, pts[0][1] * h);
  for (let i = 1; i < pts.length - 1; i++) {
    const mx = ((pts[i][0] + pts[i + 1][0]) / 2) * w;
    const my = ((pts[i][1] + pts[i + 1][1]) / 2) * h;
    ctx.quadraticCurveTo(pts[i][0] * w, pts[i][1] * h, mx, my);
  }
  const last = pts[pts.length - 1];
  ctx.lineTo(last[0] * w, last[1] * h);
  ctx.stroke();
}

/** Carrega o desenho da URL; se ele não existir mais, volta para o projeto. */
export default function StudioPage() {
  const { projectId = '', drawingId = '' } = useParams();
  const project = getProject(projectId);
  const drawing = project ? getDrawing(projectId, drawingId) : null;
  if (!project || !drawing) return <Navigate to={project ? `/app/p/${projectId}` : '/app/projects'} replace />;
  return <StudioEditor key={drawing.id} projectName={project.name} drawing={drawing} />;
}

function StudioEditor({ projectName, drawing }: { projectName: string; drawing: Drawing }) {
  const { slot } = useOutletContext<StudioContext>();
  const paperRef = useRef<HTMLCanvasElement>(null);
  const digitalRef = useRef<HTMLCanvasElement>(null);
  const countRef = useRef<HTMLSpanElement>(null);
  const [initialStrokes] = useState(() => drawing.strokes.map((st) => ({ ink: st.ink, pts: st.pts.map(([x, y]) => [x, y] as Pt) })));
  const strokes = useRef<{ pts: Pt[]; ink: string }[]>(initialStrokes);
  const inkRef = useRef(INKS[0]);
  const [inkIdx, setInkIdx] = useState(0);
  const clearRef = useRef<(() => void) | undefined>(undefined);
  const [title, setTitle] = useState(drawing.name);
  const readOnly = isPendingImport(drawing.projectId); // importacao ainda nao gravada: nao aceita edicoes
  const titleRef = useRef(drawing.name); // o que esta no campo agora (a copia so o substitui se nao foi editado)
  const savedName = useRef(drawing.name); // o ultimo nome gravado (drawing.name e o do momento em que abriu)

  const saveTimer = useRef(0);
  const pendingSave = useRef(false);
  // Falhas separadas: renomear com sucesso nao pode esconder traços ainda nao gravados.
  const [strokeError, setStrokeError] = useState(false);
  const [nameError, setNameError] = useState(false);
  const [forked, setForked] = useState<string | null>(null);
  const saveError = strokeError || nameError;
  // Onde os traços sao gravados e a revisao que este editor carregou/gravou por ultimo (outra aba pode ter gravado antes).
  const target = useRef({ id: drawing.id, rev: drawing.rev ?? 0 });

  // Grava os traços; enquanto a gravacao nao der certo eles continuam pendentes (a saida tenta de novo).
  const flushAutosave = useCallback(() => {
    window.clearTimeout(saveTimer.current);
    if (!pendingSave.current) return;
    pendingSave.current = false;
    let result = saveStrokes(drawing.projectId, target.current.id, strokes.current, target.current.rev);
    if (result.status === 'stale') {
      // outra aba gravou este desenho depois que ele foi aberto aqui: nao sobrescreve, guarda uma copia
      const copy = saveStrokesAsCopy(drawing.projectId, drawing.name, strokes.current);
      if (copy) {
        target.current = { id: copy.id, rev: copy.rev ?? 0 };
        // a copia e a nova referencia gravada; um titulo que o usuario ja estava editando fica no campo e e salvo ao sair dele
        if (titleRef.current === savedName.current) {
          setTitle(copy.name);
          titleRef.current = copy.name;
        }
        savedName.current = copy.name;
        setForked(copy.name);
        result = { status: 'ok', rev: target.current.rev };
      } else {
        result = { status: 'failed', rev: target.current.rev };
      }
    } else if (result.status === 'ok') {
      target.current.rev = result.rev;
    }
    const ok = result.status === 'ok';
    if (!ok) pendingSave.current = true;
    setStrokeError(!ok);
  }, [drawing.projectId, drawing.name]);

  const scheduleAutosave = useCallback(() => {
    pendingSave.current = true;
    window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(flushAutosave, 900);
  }, [flushAutosave]);

  useEffect(() => () => flushAutosave(), [flushAutosave]);

  // Recarregar ou fechar a aba nao roda a limpeza do React: grava o que estiver pendente.
  useEffect(() => {
    const flush = () => flushAutosave();
    const onVisibility = () => { if (document.visibilityState === 'hidden') flush(); };
    window.addEventListener('pagehide', flush);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('pagehide', flush);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [flushAutosave]);

  const rename = () => {
    const name = title.trim() || 'Sem título';
    setTitle(name);
    titleRef.current = name;
    if (name === savedName.current) return;
    const ok = saveDrawing(drawing.projectId, target.current.id, { name });
    if (ok) savedName.current = name;
    setNameError(!ok);
  };

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cams, setCams] = useState<MediaDeviceInfo[]>([]);
  const [camId, setCamId] = useState<string | null>(null);
  const [camOpen, setCamOpen] = useState(false);
  const camBoxRef = useRef<HTMLDivElement>(null);
  const [camError, setCamError] = useState('');
  const camRequest = useRef(0); // invalida pedidos de camera pendentes (parar, trocar, sair)
  const cloudRef = useRef<{ quad: [number, number][] | null; img: HTMLImageElement | null } | null>(null);
  const renderRef = useRef<(() => void) | undefined>(undefined);
  const [cloudStatus, setCloudStatus] = useState<CloudStatus>('off');
  const [cloudDetail, setCloudDetail] = useState('');

  // Draw na nuvem: com a camera ligada (e VITE_DRAW_CLOUD_URL definida), manda ~4 quadros/s e mostra o que ele detecta.
  useEffect(() => {
    if (!camId || !isCloudConfigured()) return;
    const video = videoRef.current;
    if (!video) return;
    const shot = document.createElement('canvas');
    let decoding = 0;
    const cloud = new DrawCloud({
      onStatus: (status, detail) => { setCloudStatus(status); setCloudDetail(detail ?? ''); },
      onResult: (r: CloudResult) => {
        const id = ++decoding;
        if (!r.ink) {
          cloudRef.current = { quad: r.quad, img: null };
          renderRef.current?.();
          return;
        }
        const img = new Image();
        img.onload = () => {
          if (id !== decoding) return; // chegou um resultado mais novo enquanto decodificava
          cloudRef.current = { quad: r.quad, img };
          renderRef.current?.();
        };
        img.src = r.ink;
      },
    });
    cloud.connect();
    const timer = window.setInterval(() => {
      if (video.readyState < 2 || !video.videoWidth) return;
      const scale = Math.min(1, 960 / video.videoWidth);
      shot.width = Math.round(video.videoWidth * scale);
      shot.height = Math.round(video.videoHeight * scale);
      shot.getContext('2d')!.drawImage(video, 0, 0, shot.width, shot.height);
      shot.toBlob((b) => { if (b) cloud.sendFrame(b); }, 'image/jpeg', 0.8);
    }, 250);
    return () => {
      window.clearInterval(timer);
      cloud.close();
      cloudRef.current = null;
      renderRef.current?.();
    };
  }, [camId]);

  const refreshCams = useCallback(async () => {
    const all = await navigator.mediaDevices.enumerateDevices();
    setCams(all.filter((d) => d.kind === 'videoinput'));
  }, []);

  const stopCam = useCallback(() => {
    camRequest.current += 1;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setCamId(null);
  }, []);

  const startCam = useCallback(async (deviceId?: string) => {
    setCamError('');
    if (!navigator.mediaDevices?.getUserMedia) {
      setCamError('Este navegador não expõe câmeras (use https ou localhost).');
      return;
    }
    const request = ++camRequest.current;
    try {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      const stream = await navigator.mediaDevices.getUserMedia({
        video: deviceId ? { deviceId: { exact: deviceId }, width: { ideal: 1920 }, height: { ideal: 1080 } } : { width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      if (request !== camRequest.current) { // o estudio fechou ou outro pedido venceu enquanto o navegador pedia permissao
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        void videoRef.current.play().catch(() => {});
      }
      setCamId(stream.getVideoTracks()[0]?.getSettings().deviceId ?? deviceId ?? null);
      await refreshCams(); // com permissao, os nomes das câmeras aparecem
    } catch (err) {
      const name = err instanceof DOMException ? err.name : '';
      setCamError(name === 'NotAllowedError' ? 'Permissão negada. Libere a câmera nas configurações do navegador.' : name === 'NotFoundError' ? 'Nenhuma câmera encontrada.' : 'Não foi possível abrir essa câmera.');
    }
  }, [refreshCams]);

  useEffect(() => {
    if (!navigator.mediaDevices) return;
    void refreshCams();
    navigator.mediaDevices.addEventListener?.('devicechange', refreshCams);
    return () => {
      camRequest.current += 1;
      navigator.mediaDevices.removeEventListener?.('devicechange', refreshCams);
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [refreshCams]);

  useEffect(() => {
    if (!camOpen) return;
    const onDown = (e: PointerEvent) => {
      if (!camBoxRef.current?.contains(e.target as Node)) setCamOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setCamOpen(false); };
    document.addEventListener('pointerdown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('pointerdown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [camOpen]);

  const activeCam = cams.find((c) => c.deviceId === camId);
  const cloudLabel = !isCloudConfigured() ? '' : cloudStatus === 'ready' ? ' · draw ativo' : cloudStatus === 'connecting' ? ' · conectando ao draw…' : cloudStatus === 'error' ? ` · draw indisponível${cloudDetail ? ` (${cloudDetail})` : ''}` : '';

  useEffect(() => {
    const paper = paperRef.current!;
    const digital = digitalRef.current!;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const css = (name: string) => getComputedStyle(document.body).getPropertyValue(name).trim();

    const size = (c: HTMLCanvasElement) => {
      const r = c.getBoundingClientRect();
      c.width = Math.round(r.width * dpr);
      c.height = Math.round(r.height * dpr);
      return [c.width, c.height] as const;
    };

    const render = () => {
      const [pw, ph] = size(paper);
      const [dw, dh] = size(digital);
      const pc = paper.getContext('2d')!;
      const dc = digital.getContext('2d')!;
      pc.clearRect(0, 0, pw, ph);
      dc.clearRect(0, 0, dw, dh);
      for (const s of strokes.current) {
        pc.strokeStyle = s.ink === INKS[0] ? css('--ink') || s.ink : s.ink;
        pc.lineWidth = 2.2 * dpr;
        pc.lineCap = pc.lineJoin = 'round';
        if (s.pts.length === 1) {
          pc.fillStyle = pc.strokeStyle;
          pc.beginPath();
          pc.arc(s.pts[0][0] * pw, s.pts[0][1] * ph, pc.lineWidth / 2, 0, Math.PI * 2);
          pc.fill();
        } else {
          pc.beginPath();
          s.pts.forEach(([x, y], i) => (i ? pc.lineTo(x * pw, y * ph) : pc.moveTo(x * pw, y * ph)));
          pc.stroke();
        }
        dc.strokeStyle = s.ink === INKS[0] ? css('--ink') || s.ink : s.ink;
        dc.lineWidth = 3 * dpr;
        dc.lineCap = dc.lineJoin = 'round';
        drawSmooth(dc, s.pts, dw, dh);
      }
      const cloud = cloudRef.current;
      if (cloud) {
        if (cloud.quad) {
          pc.strokeStyle = '#d0342c';
          pc.lineWidth = 2 * dpr;
          pc.beginPath();
          // o video usa object-fit: cover; a quad vem normalizada sobre o quadro inteiro
          const vw = videoRef.current?.videoWidth || pw;
          const vh = videoRef.current?.videoHeight || ph;
          const k = Math.max(pw / vw, ph / vh);
          const ox = (pw - vw * k) / 2;
          const oy = (ph - vh * k) / 2;
          cloud.quad.forEach(([x, y], i) => {
            const px = x * vw * k + ox;
            const py = y * vh * k + oy;
            if (i) pc.lineTo(px, py); else pc.moveTo(px, py);
          });
          pc.closePath();
          pc.stroke();
        }
        if (cloud.img) {
          // a tinta chega no formato da folha: encaixa (contain) no painel digital
          const k = Math.min(dw / cloud.img.width, dh / cloud.img.height);
          const iw = cloud.img.width * k;
          const ih = cloud.img.height * k;
          dc.drawImage(cloud.img, (dw - iw) / 2, (dh - ih) / 2, iw, ih);
        }
      }
      if (countRef.current) countRef.current.textContent = cloud ? '··' : String(strokes.current.length).padStart(2, '0');
    };
    renderRef.current = render;

    let current: { pts: Pt[]; ink: string } | null = null;
    let activePointer = -1; // so o ponteiro que abriu o traco o move e o encerra
    const pos = (e: PointerEvent): Pt => {
      const r = paper.getBoundingClientRect();
      return [(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height];
    };
    const down = (e: PointerEvent) => {
      if (streamRef.current || readOnly) return; // com a camera ligada (ou importacao pendente), o papel e so visualizacao
      if (!e.isPrimary || (e.pointerType === 'mouse' && e.button !== 0)) return; // botao direito/auxiliar nao desenha
      paper.setPointerCapture(e.pointerId);
      activePointer = e.pointerId;
      current = { pts: [pos(e)], ink: inkRef.current };
      strokes.current.push(current);
      render(); // o toque sem arrasto ja deixa o ponto
    };
    const move = (e: PointerEvent) => {
      if (!current || e.pointerId !== activePointer) return;
      const evs = e.getCoalescedEvents?.() ?? [e];
      for (const ev of evs) current.pts.push(pos(ev));
      render();
    };
    const up = (e: PointerEvent) => {
      if (e.pointerId !== activePointer) return; // outro dedo nao encerra o traco
      if (current) scheduleAutosave();
      current = null;
      activePointer = -1;
    };

    paper.addEventListener('pointerdown', down);
    paper.addEventListener('pointermove', move);
    paper.addEventListener('pointerup', up);
    paper.addEventListener('pointercancel', up);
    window.addEventListener('resize', render);
    // os avisos mudam a altura das folhas sem disparar 'resize': mantem o tamanho dos canvases sincronizado
    const sizeWatch = new ResizeObserver(render);
    sizeWatch.observe(paper);
    const clear = () => {
      strokes.current = [];
      scheduleAutosave(); // a folha vazia tambem e gravada
      render();
    };
    clearRef.current = clear;
    render();
    return () => {
      renderRef.current = undefined;
      paper.removeEventListener('pointerdown', down);
      paper.removeEventListener('pointermove', move);
      paper.removeEventListener('pointerup', up);
      paper.removeEventListener('pointercancel', up);
      window.removeEventListener('resize', render);
      sizeWatch.disconnect();
      clearRef.current = undefined;
    };
  }, [scheduleAutosave, flushAutosave]);

  const pick = (i: number) => {
    inkRef.current = INKS[i];
    setInkIdx(i);
  };

  return (
    <>
      {slot && createPortal(
        <>
          <Link className="studio-crumb" to={`/app/p/${drawing.projectId}`} title="Voltar ao projeto" aria-label={`Voltar ao projeto ${projectName}`}><span aria-hidden="true">‹</span><span className="studio-crumb-name"> {projectName}</span></Link>
          <input
            className="studio-title"
            value={title}
            maxLength={60}
            aria-label="Nome do desenho"
            readOnly={readOnly}
            onChange={(e) => { titleRef.current = e.target.value; setTitle(e.target.value); }}
            onBlur={rename}
            onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur(); }}
          />
          <span className="studio-pill"><span className={`status-dot${camId ? ' is-live' : ''}`} /> {camId ? `câmera · ${activeCam?.label || 'ativa'}${cloudLabel}` : 'câmera desligada'}</span>
        </>,
        slot,
      )}
      <div className="studio-notices">
        <div className="studio-notices-list">
          {saveError && <span className="studio-save-error" role="alert">sem espaço para salvar — o desenho continua só nesta tela</span>}
          {readOnly && <span className="studio-save-error" role="status">importação pendente: sem espaço para gravar — somente leitura</span>}
          {forked && <span className="studio-save-error" role="status">outra aba alterou este desenho; suas mudanças foram salvas em “{forked}”</span>}
        </div>
      </div>

      <section className="studio-stage">
        <figure className="studio-pane">
          <figcaption>papel</figcaption>
          <video ref={videoRef} className="studio-video" muted playsInline aria-hidden="true" />
          <canvas ref={paperRef} className={`studio-canvas${camId ? ' is-cam' : ''}`} aria-label="Folha de papel: desenhe aqui" />
        </figure>
        <figure className="studio-pane is-digital">
          <figcaption>digital · <span ref={countRef}>00</span> traços</figcaption>
          <canvas ref={digitalRef} className="studio-canvas" role="img" aria-label="Versão digital do desenho" />
        </figure>
      </section>

      <footer className="studio-dock">
        {!camId && !readOnly && <div className="studio-swatches" role="group" aria-label="Tinta">
          {INKS.map((c, i) => (
            <button key={c} type="button" aria-label={`Tinta ${i + 1}`} aria-pressed={i === inkIdx} style={{ background: i === 0 ? 'var(--ink)' : c }} onClick={() => pick(i)} />
          ))}
        </div>}
        {!camId && !readOnly && <button type="button" className="studio-clear" onClick={() => clearRef.current?.()}>limpar</button>}
        <div className="studio-cam" ref={camBoxRef}>
          <button type="button" className="studio-clear" aria-expanded={camOpen} aria-controls="studio-cam-card" onClick={() => setCamOpen((o) => !o)}>
            <span className={`studio-rec${camId ? ' is-on' : ''}`} aria-hidden="true" /> câmera
          </button>
          {camOpen && (
            <div className="studio-cam-card" id="studio-cam-card" role="dialog" aria-label="Escolher câmera">
              <p className="studio-cam-title">Câmeras</p>
              {cams.length === 0 || cams.every((c) => !c.label) ? (
                <button type="button" className="studio-cam-row" onClick={() => void startCam()}>Permitir e detectar câmeras</button>
              ) : (
                cams.map((c, i) => (
                  <button key={c.deviceId || i} type="button" className="studio-cam-row" aria-pressed={c.deviceId === camId} onClick={() => { void startCam(c.deviceId); setCamOpen(false); }}>
                    <span className="studio-rec is-on" aria-hidden="true" style={{ opacity: c.deviceId === camId ? 1 : 0 }} />
                    {c.label || `Câmera ${i + 1}`}
                  </button>
                ))
              )}
              {camId && <button type="button" className="studio-cam-row is-off" onClick={stopCam}>Desligar câmera</button>}
              {camError && <p className="studio-cam-error" role="alert">{camError}</p>}
            </div>
          )}
        </div>
      </footer>
    </>
  );
}
