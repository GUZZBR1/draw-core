import { flushSync } from 'react-dom';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import StudioSidebar from '../components/StudioSidebar';
import { DrawCloud, isCloudConfigured, type CloudResult, type CloudStatus } from '../lib/drawCloud';
import { makePermanent, readSaves, removeSave, upsertAutosave, type Pt, type SaveEntry, type SaveResult } from '../lib/studioSaves';

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

export default function StudioPage() {
  const paperRef = useRef<HTMLCanvasElement>(null);
  const digitalRef = useRef<HTMLCanvasElement>(null);
  const countRef = useRef<HTMLSpanElement>(null);
  const strokes = useRef<{ pts: Pt[]; ink: string }[]>([]);
  const inkRef = useRef(INKS[0]);
  const [inkIdx, setInkIdx] = useState(0);
  const clearRef = useRef<(() => void) | undefined>(undefined);
  const navigate = useNavigate();
  const [leaving, setLeaving] = useState(false);
  const leaveTimer = useRef(0);
  useEffect(() => () => window.clearTimeout(leaveTimer.current), []);

  // Saida = entrada ao contrario: o estudio estoura em branco, e o site volta de longe, encolhendo ate o tamanho normal.
  const leave = (event: React.MouseEvent) => {
    event.preventDefault();
    if (leaving) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      navigate('/product');
      return;
    }
    setSideOpen(false);
    setLeaving(true);
    leaveTimer.current = window.setTimeout(() => {
      document.body.classList.add('is-arriving');
      navigate('/product');
      window.setTimeout(() => document.body.classList.remove('is-arriving'), 1500);
    }, 1100);
  };

  const loadRef = useRef<((e: SaveEntry) => void) | undefined>(undefined);
  const sessionRef = useRef<string | null>(null);
  const saveTimer = useRef(0);
  const pendingSave = useRef(false);
  const sideRef = useRef<HTMLElement>(null);
  const brandRef = useRef<HTMLButtonElement>(null);
  const [saves, setSaves] = useState<SaveEntry[]>(() => readSaves());
  const [sideOpen, setSideOpen] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const storageFailed = useRef(false);

  // Mostra a lista devolvida; se o navegador recusou a gravacao, avisa e nao a descarta ao reabrir a barra.
  const commitSaves = useCallback((result: SaveResult) => {
    storageFailed.current = !result.ok;
    setSaveError(!result.ok);
    setSaves(result.list);
  }, []);

  // true se nao ha nada pendente ou a gravacao deu certo; em falha os tracos continuam pendentes.
  const flushAutosave = useCallback((): boolean => {
    window.clearTimeout(saveTimer.current);
    if (!pendingSave.current) return true;
    pendingSave.current = false;
    if (!strokes.current.length) return true;
    sessionRef.current ??= crypto.randomUUID?.() ?? String(Date.now());
    const result = upsertAutosave(sessionRef.current, strokes.current);
    commitSaves(result);
    if (!result.ok) pendingSave.current = true;
    return result.ok;
  }, [commitSaves]);

  const scheduleAutosave = useCallback(() => {
    pendingSave.current = true;
    window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(flushAutosave, 900);
  }, [flushAutosave]);

  useEffect(() => () => { flushAutosave(); }, [flushAutosave]);

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

  useEffect(() => {
    if (!sideOpen) return;
    if (!storageFailed.current) setSaves(readSaves()); // descarta o que passou de 24 h (com gravacao recusada, a lista em memoria e a unica copia)
    const onDown = (e: PointerEvent) => {
      const t = e.target as Node;
      if (!sideRef.current?.contains(t) && !brandRef.current?.contains(t)) setSideOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setSideOpen(false); };
    document.addEventListener('pointerdown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('pointerdown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [sideOpen]);

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

  const [dark, setDark] = useState(() => document.body.classList.contains('dark'));
  // Na visita direta ao estudio o cabecalho (que le a preferencia salva) nao esta montado: aplica o tema salvo aqui.
  useEffect(() => {
    let saved = false;
    try { saved = localStorage.getItem('draw-theme') === 'dark'; } catch { /* sem armazenamento: fica no tema atual */ }
    if (saved && !document.body.classList.contains('dark')) {
      document.body.classList.add('dark');
      document.querySelector('meta[name="theme-color"]')?.setAttribute('content', '#1b1c19');
      setDark(true);
      window.dispatchEvent(new Event('resize'));
    }
  }, []);
  const toggleTheme = () => {
    const apply = () => {
      const next = !document.body.classList.contains('dark');
      document.body.classList.toggle('dark', next);
      document.querySelector('meta[name="theme-color"]')?.setAttribute('content', next ? '#1b1c19' : '#f7f7f4');
      try { localStorage.setItem('draw-theme', next ? 'dark' : 'light'); } catch { /* sem armazenamento: o botao ainda funciona */ }
      setDark(next);
      window.dispatchEvent(new Event('resize')); // redesenha os traços com a tinta do novo tema
    };
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce || !document.startViewTransition) {
      apply();
      return;
    }
    // Explosao em onda: o novo tema se abre do centro em aneis concentricos (ondas de choque) que se espalham ate cobrir tudo.
    const root = document.documentElement;
    root.classList.add('theme-tearing', 'theme-wave');
    const transition = document.startViewTransition(() => flushSync(apply));
    transition.ready.then(() => {
      const radius = Math.hypot(window.innerWidth, window.innerHeight) / 2 + 260;
      const blast = { duration: 1500, fill: 'forwards' as const };
      root.animate(
        { '--wave-r': ['0px', `${radius}px`] },
        { ...blast, easing: 'cubic-bezier(.2,.6,.3,1)', pseudoElement: '::view-transition-new(root)' },
      );
      root.animate(
        { filter: ['brightness(2.8) saturate(1.4)', 'brightness(1.5)', 'brightness(1)'], offset: [0, 0.2, 1] },
        { ...blast, duration: 1300, pseudoElement: '::view-transition-new(root)' },
      );
      root.animate(
        { transform: ['scale(1)', 'scale(1.05)'], filter: ['blur(0px)', 'blur(3px)'], easing: ['cubic-bezier(.2,.6,.3,1)'] },
        { ...blast, pseudoElement: '::view-transition-old(root)' },
      );
    });
    transition.finished.catch(() => undefined).finally(() => root.classList.remove('theme-tearing', 'theme-wave'));
  };

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
    document.body.classList.add('in-studio');
    return () => document.body.classList.remove('in-studio');
  }, []);

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
      if (streamRef.current) return; // com a camera ligada, o papel e so visualizacao
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
    const clear = () => {
      flushAutosave(); // o que estava na folha fica nos salvamentos automaticos
      pendingSave.current = false; // se a gravacao falhou, o descarte e explicito: o pendente nao passa para a folha nova
      strokes.current = [];
      sessionRef.current = null;
      render();
    };
    loadRef.current = (entry) => {
      flushAutosave();
      pendingSave.current = false; // idem: sem isso a saida regravaria o desenho aberto, sem edicao, como copia
      strokes.current = entry.strokes.map((st) => ({ ink: st.ink, pts: st.pts.map(([x, y]) => [x, y] as Pt) }));
      sessionRef.current = null; // continuar desenhando cria um novo automatico; o original nao e alterado
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
      clearRef.current = undefined;
      loadRef.current = undefined;
    };
  }, [scheduleAutosave, flushAutosave]);

  const pick = (i: number) => {
    inkRef.current = INKS[i];
    setInkIdx(i);
  };

  return (
    <main className={`studio${leaving ? ' is-leaving' : ''}`} id="page-content">
      <div className="studio-flash" aria-hidden="true" />
      {leaving && <div className="studio-leave" aria-hidden="true" />}
      <header className="studio-bar">
        <button type="button" ref={brandRef} className="studio-mark" aria-expanded={sideOpen} aria-controls="studio-side" onClick={() => setSideOpen((o) => !o)}>Draw<i>studio</i></button>
        <span className="studio-pill"><span className={`status-dot${camId ? ' is-live' : ''}`} /> {camId ? `câmera · ${activeCam?.label || 'ativa'}${cloudLabel}` : 'sessão local · câmera desligada'}</span>
        {saveError && <span className="studio-save-error" role="alert">sem espaço para salvar — o desenho continua só nesta tela</span>}
        <button type="button" className="studio-exit" aria-label={`Ativar tema ${dark ? 'claro' : 'escuro'}`} onClick={toggleTheme}>{dark ? 'light' : 'dark'}</button>
        <Link className="studio-exit" to="/product" onClick={leave}>sair ↗</Link>
      </header>

      <StudioSidebar
        ref={sideRef}
        open={sideOpen}
        saves={saves}
        onOpenEntry={(e) => { loadRef.current?.(e); setSideOpen(false); }}
        onSave={(id) => {
          const active = id === sessionRef.current;
          // grava os ultimos tracos nesse mesmo id antes de promove-lo; se nao couberem, nao promove
          // a copia antiga como se fosse a atual (o aviso de falta de espaco ja esta na tela)
          if (active && !flushAutosave()) return;
          commitSaves(makePermanent(id));
          if (active) sessionRef.current = null; // o proximo traco abre um automatico novo, sem sobrescrever o salvo
        }}
        onDelete={(id) => {
          if (id === sessionRef.current) {
            sessionRef.current = null;
            pendingSave.current = false; // nao recria o que acabou de ser excluido
            window.clearTimeout(saveTimer.current);
          }
          commitSaves(removeSave(id));
        }}
        onClose={() => setSideOpen(false)}
      />

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
        {!camId && <div className="studio-swatches" role="group" aria-label="Tinta">
          {INKS.map((c, i) => (
            <button key={c} type="button" aria-label={`Tinta ${i + 1}`} aria-pressed={i === inkIdx} style={{ background: i === 0 ? 'var(--ink)' : c }} onClick={() => pick(i)} />
          ))}
        </div>}
        {!camId && <button type="button" className="studio-clear" onClick={() => clearRef.current?.()}>limpar</button>}
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
    </main>
  );
}
