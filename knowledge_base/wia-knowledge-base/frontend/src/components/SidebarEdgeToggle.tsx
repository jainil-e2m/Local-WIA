import { useEffect, useLayoutEffect, useRef } from 'react';
import './SidebarEdgeToggle.css';

/** Swallowtail outline in the 26x58 drawing space (shown at 21x47 px). */
const SHAPE = 'M0 0H26L17.5 29L26 58H0Z';

/** Hover sway: the ribbon moves from its root like fabric in a light draught. */
const SWAY: Keyframe[] = [
  { transform: 'skewY(0deg) scaleY(1)', easing: 'ease-in-out' },
  { transform: 'skewY(-2.6deg) scaleY(.985)', offset: .22, easing: 'ease-in-out' },
  { transform: 'skewY(1.8deg) scaleY(1.01)', offset: .48, easing: 'ease-in-out' },
  { transform: 'skewY(-1deg) scaleY(.995)', offset: .72, easing: 'ease-in-out' },
  { transform: 'skewY(0deg) scaleY(1)' },
];
const SHEEN: Keyframe[] = [{ transform: 'translateX(-160%) skewX(-18deg)' }, { transform: 'translateX(390%) skewX(-18deg)' }];
const SETTLE: KeyframeAnimationOptions = { duration: 450, easing: 'cubic-bezier(.22, 1, .36, 1)' };

/** Ease a looping animation back to rest from wherever it is, instead of letting it snap. */
function settle(element: HTMLElement | null, animation: Animation | null) {
  if (!element || !animation) return;
  const from = getComputedStyle(element).transform;
  animation.cancel();
  if (from && from !== 'none') element.animate([{ transform: from }, { transform: 'none' }], SETTLE);
}

interface Props {
  collapsed: boolean;
  onToggle: () => void;
}

/** Blue-and-gold satin ribbon on the sidebar's right edge; clicking it collapses or opens the sidebar. */
export default function SidebarEdgeToggle({ collapsed, onToggle }: Props) {
  const button = useRef<HTMLButtonElement>(null);
  const label = collapsed ? 'Expand sidebar' : 'Collapse sidebar';
  const mounted = useRef(false);

  // While the width animates, mark the sidebar so its labels hold one line (see .et-resizing in the CSS).
  // A layout effect, so the class is on before the first frame of the animation is painted.
  useLayoutEffect(() => {
    if (!mounted.current) { mounted.current = true; return; }
    const sidebar = button.current?.closest('aside');
    if (!sidebar) return;
    sidebar.classList.add('et-resizing');
    let timer = 0;
    const done = (event?: TransitionEvent) => {
      if (event && (event.target !== sidebar || event.propertyName !== 'width')) return;
      sidebar.classList.remove('et-resizing');
      sidebar.removeEventListener('transitionend', done);
      clearTimeout(timer);
    };
    sidebar.addEventListener('transitionend', done);
    timer = window.setTimeout(done, 600); // no transition (reduced motion, narrow screens)
    return () => done();
  }, [collapsed]);

  useEffect(() => {
    const root = button.current;
    if (!root) return;
    const sway = root.querySelector<HTMLElement>('.et-sway');
    const nudge = root.querySelector<HTMLElement>('.et-nudge');
    const sheen = root.querySelector<HTMLElement>('.et-sheen');
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
    let swaying: Animation | null = null, nudging: Animation | null = null, sweeping: Animation | null = null;

    const enter = (event: PointerEvent) => {
      if (event.pointerType === 'touch' || reduce.matches || swaying) return;
      // the chevron leans the way the sidebar will move
      const lean = root.closest('.sidebar')?.classList.contains('collapsed') ? 1.6 : -1.6;
      swaying = sway?.animate(SWAY, { duration: 2600, delay: 200, iterations: Infinity }) ?? null;
      nudging = nudge?.animate([{ transform: 'translateX(0)' }, { transform: `translateX(${lean}px)` }, { transform: 'translateX(0)' }], { duration: 1300, easing: 'ease-in-out', iterations: Infinity }) ?? null;
      if (sheen && sweeping?.playState !== 'running') sweeping = sheen.animate(SHEEN, { duration: 1100, delay: 150, easing: 'cubic-bezier(.4, 0, .2, 1)' });
    };
    const leave = () => {
      settle(sway, swaying);
      settle(nudge, nudging);
      swaying = nudging = null; // the sheen finishes its sweep on its own
    };
    root.addEventListener('pointerenter', enter);
    root.addEventListener('pointerleave', leave);
    return () => {
      root.removeEventListener('pointerenter', enter);
      root.removeEventListener('pointerleave', leave);
      swaying?.cancel(); nudging?.cancel(); sweeping?.cancel();
    };
  }, []);

  return <button ref={button} type="button" className="edge-toggle" onClick={onToggle} aria-label={label} title={label} aria-expanded={!collapsed}>
    <span className="et-ribbon" aria-hidden="true"><span className="et-sway">
      <svg className="et-layer et-lift" viewBox="0 0 26 58"><path d={SHAPE} fill="#1e2a50" /></svg>
      {/* deep blue duchess satin: sheen runs along its length, gold piping on both edges, a tuck shadow where it passes under the sidebar */}
      <svg className="et-layer et-satin" viewBox="0 0 26 58">
        <defs>
          <linearGradient id="etBody" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1f449a" /><stop offset=".14" stopColor="#5c88e2" /><stop offset=".28" stopColor="#86a9ef" /><stop offset=".44" stopColor="#3f6dd2" /><stop offset=".6" stopColor="#22489f" /><stop offset=".78" stopColor="#4d7bd9" /><stop offset=".9" stopColor="#3360c2" /><stop offset="1" stopColor="#1b3d8c" /></linearGradient>
          <linearGradient id="etGold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#f6e3a4" /><stop offset=".5" stopColor="#c9a44c" /><stop offset="1" stopColor="#8f6e27" /></linearGradient>
          <linearGradient id="etTuck" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#0b1430" stopOpacity=".38" /><stop offset="1" stopColor="#0b1430" stopOpacity="0" /></linearGradient>
          <clipPath id="etClip"><path d={SHAPE} /></clipPath>
        </defs>
        <path d={SHAPE} fill="url(#etBody)" />
        <g clipPath="url(#etClip)">
          <rect x="0" y="0" width="26" height="2.4" fill="url(#etGold)" />
          <rect x="0" y="55.6" width="26" height="2.4" fill="url(#etGold)" />
          <rect x="0" y="0" width="4" height="58" fill="url(#etTuck)" />
        </g>
      </svg>
      <span className="et-sheen-clip"><span className="et-sheen" /></span>
      <span className="et-nudge"><svg className="et-layer et-chev" viewBox="0 0 26 58"><path d="M12.9 25l-4.8 4 4.8 4" fill="none" stroke="#f3dc96" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg></span>
    </span></span>
  </button>;
}
