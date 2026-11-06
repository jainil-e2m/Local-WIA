import { memo, useEffect, useRef } from "react";
import { useFrameLoop, useStage } from "./stage";
import { useLowPower } from "./perf";

/* ────────────────────────────────────────────────────────────────
   A flat white on its saucer, still warm.

   The steam is a small particle system: soft puffs leave the surface,
   rise and slow, spread as they cool, and curl on a shared breeze so
   neighbouring puffs line up into wisps instead of reading as dots.
   Each puff is drawn twice — a faint cool halo, then a white core — so
   it stays visible against the pale wall as well as the blue behind it.
   ──────────────────────────────────────────────────────────────── */

const CUP = { left: 612, top: 438, w: 238, h: 170 };
const STEAM = { w: 190, h: 250 };

interface Puff {
  x: number;
  y: number;
  vy: number;
  age: number;
  life: number;
  s0: number;
  s1: number;
  seed: number;
  a: number;
}

function sprite(color: string) {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d")!;
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, color.replace("ALPHA", "1"));
  grad.addColorStop(0.45, color.replace("ALPHA", "0.55"));
  grad.addColorStop(1, color.replace("ALPHA", "0"));
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  return c;
}

function Steam() {
  const { scale, still } = useStage();
  const ref = useRef<HTMLCanvasElement>(null);
  const state = useRef<{ puffs: Puff[]; acc: number; core?: HTMLCanvasElement; halo?: HTMLCanvasElement; ratio: number }>({
    puffs: [],
    acc: 0,
    ratio: 1,
  });

  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 2) * scale;
    c.width = Math.round(STEAM.w * ratio);
    c.height = Math.round(STEAM.h * ratio);
    state.current.ratio = ratio;
    state.current.core ??= sprite("rgba(255,255,255,ALPHA)");
    state.current.halo ??= sprite("rgba(138,153,180,ALPHA)");
  }, [scale]);

  const lowPower = useLowPower();
  useFrameLoop((t, dt) => {
    const c = ref.current;
    const s = state.current;
    if (!c || !s.core || !s.halo) return;
    const g = c.getContext("2d");
    if (!g) return;

    // In still mode, pre-age a plume so the frame shows steam, not an empty cup.
    const steps = still ? 90 : 1;
    const step = still ? 1 / 30 : dt;
    for (let k = 0; k < steps; k++) {
      const time = still ? k * step : t;
      s.acc += step * 15;
      while (s.acc >= 1) {
        s.acc -= 1;
        const seed = Math.random() * 1000;
        s.puffs.push({
          x: STEAM.w / 2 + (Math.random() - 0.5) * 46,
          y: STEAM.h - 8 - Math.random() * 6,
          vy: -(20 + Math.random() * 12),
          age: 0,
          life: 3.6 + Math.random() * 2.2,
          s0: 9 + Math.random() * 8,
          s1: 46 + Math.random() * 30,
          seed,
          a: 0.55 + Math.random() * 0.45,
        });
      }
      const breeze = Math.sin(time * 0.31) * 6 + Math.sin(time * 0.13 + 1.2) * 4;
      for (const p of s.puffs) {
        p.age += step;
        const k01 = p.age / p.life;
        p.vy *= 1 - step * 0.18;
        p.y += p.vy * step;
        // a shared curl: puffs at the same height share most of their sway
        const curl = Math.sin(p.y * 0.045 + time * 1.15) * 13 + Math.sin(p.y * 0.021 - time * 0.6 + p.seed * 0.002) * 7;
        p.x += (curl * (0.35 + k01) + breeze * k01) * step;
      }
      s.puffs = s.puffs.filter((p) => p.age < p.life && p.y > -40);
    }

    const r = s.ratio;
    g.setTransform(r, 0, 0, r, 0, 0);
    g.clearRect(0, 0, STEAM.w, STEAM.h);
    for (const p of s.puffs) {
      const k01 = p.age / p.life;
      const fadeIn = Math.min(1, k01 / 0.14);
      const fadeOut = 1 - Math.pow(Math.max(0, (k01 - 0.25) / 0.75), 1.4);
      const alpha = fadeIn * fadeOut * p.a;
      const size = p.s0 + (p.s1 - p.s0) * Math.pow(k01, 0.75);
      g.globalAlpha = alpha * 0.055;
      g.drawImage(s.halo, p.x - size * 0.62, p.y - size * 0.62, size * 1.24, size * 1.24);
      g.globalAlpha = alpha * 0.2;
      g.drawImage(s.core, p.x - size / 2, p.y - size / 2, size, size);
    }
    g.globalAlpha = 1;
  }, !lowPower, 30);

  return (
    <canvas
      ref={ref}
      className="v1-steam"
      style={{
        left: CUP.left + CUP.w / 2 - STEAM.w / 2 - 6,
        top: CUP.top + 58 - STEAM.h,
        width: STEAM.w,
        height: STEAM.h,
      }}
      aria-hidden
    />
  );
}

const Cup = memo(function Cup() {
  return (
    <svg className="v1-cup" viewBox="0 0 210 150" style={{ left: CUP.left, top: CUP.top, width: CUP.w, height: CUP.h }} aria-hidden>
      <defs>
        <radialGradient id="v1-saucer" cx="0.42" cy="0.35" r="0.75">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="0.6" stopColor="#f3f4f6" />
          <stop offset="1" stopColor="#d9dde3" />
        </radialGradient>
        <radialGradient id="v1-well" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#e6e9ee" />
          <stop offset="1" stopColor="#f7f8fa" />
        </radialGradient>
        <linearGradient id="v1-porcelain" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#f6f7f9" />
          <stop offset="0.16" stopColor="#ffffff" />
          <stop offset="0.45" stopColor="#f5f6f8" />
          <stop offset="0.8" stopColor="#dde1e7" />
          <stop offset="1" stopColor="#c6ccd4" />
        </linearGradient>
        <radialGradient id="v1-coffee" cx="0.5" cy="0.45" r="0.55">
          <stop offset="0" stopColor="#ecd6b5" />
          <stop offset="0.55" stopColor="#d0a777" />
          <stop offset="0.85" stopColor="#9c6a42" />
          <stop offset="1" stopColor="#6e4527" />
        </radialGradient>
        <filter id="v1-soft" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="5" />
        </filter>
        <clipPath id="v1-surface">
          <ellipse cx="105" cy="54" rx="40" ry="9.6" />
        </clipPath>
      </defs>

      {/* contact shadow */}
      <ellipse cx="112" cy="128" rx="88" ry="17" fill="#2b3550" opacity="0.18" filter="url(#v1-soft)" />
      {/* saucer */}
      <ellipse cx="105" cy="118" rx="88" ry="24" fill="url(#v1-saucer)" />
      <ellipse cx="105" cy="116" rx="88" ry="23" fill="none" stroke="#ffffff" strokeWidth="1.2" />
      <ellipse cx="105" cy="113" rx="52" ry="13" fill="url(#v1-well)" />
      <path d="M22,121 Q105,150 188,121" stroke="#c4cad2" strokeWidth="1" fill="none" opacity="0.7" />
      {/* cup shadow in the well */}
      <ellipse cx="114" cy="113" rx="42" ry="9" fill="#97a1b2" opacity="0.28" filter="url(#v1-soft)" />

      {/* handle, behind the body on its right */}
      <path d="M146,62 C172,56 178,90 150,96" stroke="#e1e5ea" strokeWidth="8" fill="none" strokeLinecap="round" />
      <path d="M147,63 C168,59 173,88 150,93" stroke="#c4cbd3" strokeWidth="2" fill="none" opacity="0.6" />
      <path d="M146,60 C170,55 176,86 152,95" stroke="#ffffff" strokeWidth="1.2" fill="none" opacity="0.8" />

      {/* body */}
      <path d="M59,52 C60,84 66,104 76,111 Q105,121 134,111 C144,104 150,84 151,52 Z" fill="url(#v1-porcelain)" />
      <rect x="70" y="58" width="7" height="44" rx="3.5" fill="#fff" opacity="0.9" filter="url(#v1-soft)" />
      {/* rim + coffee */}
      <ellipse cx="105" cy="52" rx="46" ry="12.2" fill="#fbfbfc" />
      <ellipse cx="105" cy="53.4" rx="41.6" ry="10.4" fill="#d9dde3" />
      <ellipse cx="105" cy="54" rx="40" ry="9.6" fill="url(#v1-coffee)" />
      <g clipPath="url(#v1-surface)">
        <g transform="translate(105 54) scale(1 0.24)">
          <g className="v1-latte">
            {/* a three-tier tulip poured into the crema */}
            <path d="M0,-30 C-14,-30 -20,-16 -12,-6 C-6,1 0,4 0,4 C0,4 6,1 12,-6 C20,-16 14,-30 0,-30 Z" fill="#f7efe3" opacity="0.95" transform="translate(0 -4)" />
            <path d="M0,-8 C-15,-8 -22,4 -14,13 C-7,20 0,22 0,22 C0,22 7,20 14,13 C22,4 15,-8 0,-8 Z" fill="#f4eadb" opacity="0.92" transform="translate(0 6)" />
            <path d="M0,14 C-11,14 -16,22 -10,28 C-5,32 0,33 0,33 C0,33 5,32 10,28 C16,22 11,14 0,14 Z" fill="#f2e6d4" opacity="0.9" transform="translate(0 6)" />
            <path d="M0,-36 L0,40" stroke="#c99f72" strokeWidth="2.4" opacity="0.6" />
          </g>
        </g>
        <ellipse className="v1-coffee-glint" cx="92" cy="50" rx="12" ry="2" fill="#fff" opacity="0.32" />
      </g>
      <ellipse cx="105" cy="52" rx="46" ry="12.2" fill="none" stroke="#ffffff" strokeWidth="1.4" />
    </svg>
  );
});

/* A silver pen beside the saucer. */
const Pen = memo(function Pen() {
  return (
    <svg className="v1-pen" viewBox="0 0 140 30" aria-hidden>
      <defs>
        <linearGradient id="v1-pen-metal" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f4f5f7" />
          <stop offset="0.5" stopColor="#b9bec6" />
          <stop offset="1" stopColor="#8c929c" />
        </linearGradient>
      </defs>
      <ellipse cx="72" cy="22" rx="62" ry="3.2" fill="#2b3550" opacity="0.12" />
      <g transform="rotate(14 70 12)">
        <rect x="10" y="9" width="112" height="5.2" rx="2.6" fill="url(#v1-pen-metal)" />
        <path d="M122,9 L134,11.6 L122,14.2 Z" fill="#9ca2ab" />
        <rect x="24" y="7.6" width="34" height="1.6" rx="0.8" fill="#c7cbd1" />
        <rect x="56" y="9" width="2" height="5.2" fill="#d7b46a" />
      </g>
    </svg>
  );
});

export function CoffeeCup() {
  return (
    <div className="v1-coffee" aria-hidden>
      <Pen />
      <Cup />
      <Steam />
    </div>
  );
}
