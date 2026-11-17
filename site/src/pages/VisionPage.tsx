import { useEffect, useRef } from 'react';
import VisionAsciiPortrait from '../components/VisionAsciiPortrait';

const paragraphs = [
  'A gente pensa primeiro no papel. Antes de abrir menus, escolher ferramentas ou ajustar camadas, vem um gesto simples: desenhar para descobrir.',
  'Draw transforma esse gesto em uma ponte em tempo real. Uma câmera acompanha os traços; visão computacional os converte em modelos que podem chegar ao CAD, à robótica e a simuladores — sem interromper o pensamento.',
  'A visão é que o desenho não termine na captura. Uma linha pode se tornar uma peça, uma parede ou o caminho de um robô. A simulação devolve respostas enquanto a pessoa ainda desenha, para que ideia e modelo evoluam juntos.',
  'Começamos pela fundação: capturar cada traço com fidelidade, inclusive ao apagar e corrigir. O destino é mais ambicioso: pensar no papel e criar diretamente nos sistemas que projetam, testam e dão forma ao mundo.',
];

export default function VisionPage() {
  const titleLineOne = useRef<HTMLSpanElement>(null);
  const titleLineTwo = useRef<HTMLSpanElement>(null);
  const paragraphRefs = useRef<Array<HTMLParagraphElement | null>>([]);
  const signoff = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const segments: Array<{ element: HTMLElement; text: string; pace: number }> = [];
    if (titleLineOne.current) segments.push({ element: titleLineOne.current, text: 'O papel é só', pace: 62 });
    if (titleLineTwo.current) segments.push({ element: titleLineTwo.current, text: 'o início.', pace: 62 });
    paragraphs.forEach((text, index) => {
      const element = paragraphRefs.current[index];
      if (element) segments.push({ element, text, pace: 32 });
    });
    if (signoff.current) segments.push({ element: signoff.current, text: 'do papel à vida, sem perder o gesto.', pace: 34 });

    const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const reducedMotion = motionPreference.matches;
    if (reducedMotion) {
      segments.forEach(({ element, text }) => { element.textContent = text; });
      return;
    }

    let segmentIndex = 0;
    let letterIndex = 0;
    let timer = 0;
    let revealed = false;

    const reveal = () => {
      if (revealed) return;
      revealed = true;
      window.clearTimeout(timer);
      removeIntent();
      const mists: HTMLSpanElement[] = [];
      segments.forEach(({ element, text }, index) => {
        if (index < segmentIndex) return;
        const rest = index === segmentIndex ? text.slice(letterIndex) : text;
        if (!rest) return;
        const mist = document.createElement('span');
        mist.className = 'vision-mist';
        mist.textContent = rest;
        mist.style.transitionDelay = `${mists.length * 70}ms`;
        element.append(mist);
        mists.push(mist);
      });
      requestAnimationFrame(() => requestAnimationFrame(() => mists.forEach((mist) => mist.classList.add('is-clear'))));
    };

    const RESISTANCE = 260;
    let travel = 0;
    let idle = 0;
    let lastTouchY = 0;
    const push = (distance: number) => {
      if (distance <= 0) return;
      travel += distance;
      window.clearTimeout(idle);
      idle = window.setTimeout(() => { travel = 0; }, 450);
      if (travel >= RESISTANCE) reveal();
    };
    const onWheel = (event: WheelEvent) => {
      const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? window.innerHeight : 1;
      push(event.deltaY * unit);
    };
    const onTouchStart = (event: TouchEvent) => { lastTouchY = event.touches[0].clientY; };
    const onTouchMove = (event: TouchEvent) => {
      const y = event.touches[0].clientY;
      push(lastTouchY - y);
      lastTouchY = y;
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      if (['PageDown', 'End', ' ', 'ArrowDown'].includes(event.key)) push(event.key === 'ArrowDown' ? 60 : RESISTANCE);
    };
    const onScroll = () => { if (window.scrollY > 700) reveal(); };
    window.addEventListener('wheel', onWheel, { passive: true });
    window.addEventListener('touchstart', onTouchStart, { passive: true });
    window.addEventListener('touchmove', onTouchMove, { passive: true });
    window.addEventListener('keydown', onKey);
    window.addEventListener('scroll', onScroll, { passive: true });
    function removeIntent() {
      window.clearTimeout(idle);
      window.removeEventListener('wheel', onWheel);
      window.removeEventListener('touchstart', onTouchStart);
      window.removeEventListener('touchmove', onTouchMove);
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('scroll', onScroll);
    }

    const writeNext = () => {
      if (motionPreference.matches) {
        removeIntent();
        segments.forEach(({ element, text }) => { element.textContent = text; });
        return;
      }
      const segment = segments[segmentIndex];
      if (!segment) return;
      if (letterIndex >= segment.text.length) {
        segmentIndex += 1;
        letterIndex = 0;
        timer = window.setTimeout(writeNext, segmentIndex < segments.length ? 260 : 0);
        return;
      }

      const letter = segment.text[letterIndex];
      segment.element.append(document.createTextNode(letter));
      letterIndex += 1;
      const pause = letter === '.' || letter === '!' || letter === '?' ? 310
        : letter === ',' ? 150
          : letter === ';' || letter === ':' || letter === '—' ? 190 : 0;
      timer = window.setTimeout(writeNext, (letter === ' ' ? 12 : segment.pace) + pause);
    };

    timer = window.setTimeout(writeNext, 1200);
    return () => { window.clearTimeout(timer); removeIntent(); };
  }, [paragraphs]);

  return (
    <main className="vision-page" id="page-content">
      <VisionAsciiPortrait />
      <header className="vision-intro">
        <h1 className="vision-headline" aria-label="O papel é só o início.">
          <span className="vision-title-line" aria-hidden="true" ref={titleLineOne} />
          <span className="vision-title-line" aria-hidden="true" ref={titleLineTwo} />
        </h1>
      </header>

      <div className="vision-copy">
        {paragraphs.map((paragraph, index) => (
          <p aria-label={paragraph} key={paragraph} ref={(element) => { paragraphRefs.current[index] = element; }} />
        ))}
      </div>

      <p className="vision-signoff" aria-label="do papel à vida, sem perder o gesto.">
        <span aria-hidden="true" ref={signoff} />
      </p>
    </main>
  );
}
