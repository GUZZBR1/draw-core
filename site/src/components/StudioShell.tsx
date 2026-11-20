import { flushSync } from 'react-dom';
import { useEffect, useRef, useState } from 'react';
import { Link, Outlet, useNavigate } from 'react-router-dom';

export type StudioContext = { slot: HTMLElement | null };

/** Moldura do estúdio: fundo, barra superior, tema e saída. Fica montada enquanto se navega entre as telas. */
export default function StudioShell() {
  const navigate = useNavigate();
  const [slot, setSlot] = useState<HTMLElement | null>(null);
  const [leaving, setLeaving] = useState(false);
  const leaveTimer = useRef(0);
  useEffect(() => () => window.clearTimeout(leaveTimer.current), []);

  useEffect(() => {
    document.body.classList.add('in-studio');
    return () => document.body.classList.remove('in-studio');
  }, []);

  // Saida = entrada ao contrario: o estudio estoura em branco, e o site volta de longe, encolhendo ate o tamanho normal.
  const leave = (event: React.MouseEvent) => {
    event.preventDefault();
    if (leaving) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      navigate('/product');
      return;
    }
    setLeaving(true);
    leaveTimer.current = window.setTimeout(() => {
      document.body.classList.add('is-arriving');
      navigate('/product');
      window.setTimeout(() => document.body.classList.remove('is-arriving'), 1500);
    }, 1100);
  };

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

  const context: StudioContext = { slot };

  return (
    <main className={`studio${leaving ? ' is-leaving' : ''}`} id="page-content">
      <div className="studio-flash" aria-hidden="true" />
      {leaving && <div className="studio-leave" aria-hidden="true" />}
      <header className="studio-bar">
        <Link className="studio-mark" to="/app" aria-label="Draw studio: início">Draw<i>studio</i></Link>
        <div className="studio-slot" ref={setSlot} />
        <button type="button" className="studio-exit" aria-label={`Ativar tema ${dark ? 'claro' : 'escuro'}`} onClick={toggleTheme}>{dark ? 'light' : 'dark'}</button>
        <Link className="studio-exit" to="/product" onClick={leave}>sair ↗</Link>
      </header>
      <Outlet context={context} />
    </main>
  );
}
