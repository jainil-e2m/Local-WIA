import { memo, useEffect, useState, type CSSProperties } from "react";
import { CoastStatic } from "./Coast";
import { useStage } from "./stage";

/* ────────────────────────────────────────────────────────────────
   What lies flat on the table, and the light falling across it.

   Each item is laid into the table plane with its own perspective tilt,
   so the prints, the notebook and the phone foreshorten the way they do
   in the photograph. The prints were dealt onto the table and never quite
   stop settling; the phone wakes now and then with something from the
   Command Center; leaf shadows from a window out of frame move over all
   of it.
   ──────────────────────────────────────────────────────────────── */

const TILT = 54; // degrees the table is laid back from the viewer

function flat(left: number, top: number, w: number, h: number, rot: number, extra?: CSSProperties): CSSProperties {
  return {
    left,
    top,
    width: w,
    height: h,
    ["--rot" as string]: `${rot}deg`,
    ["--tilt" as string]: `${TILT}deg`,
    ...extra,
  } as CSSProperties;
}

const SWATCHES = ["#a8bba3", "#e9c9c3", "#dcc6a7", "#9eaab6", "#ccaaa4", "#efe8dc", "#c99482", "#aebdcc", "#e6d4b5"];

const NOTICES = [
  { app: "Client Onboarding", text: "Checklist ready for review" },
  { app: "Roll Call", text: "Office hours attendance logged" },
  { app: "AI Operations", text: "3 drafts waiting for approval" },
];

/* The phone wakes every so often with something from the hub. */
function Phone() {
  const { active, still } = useStage();
  const [n, setN] = useState(-1);

  useEffect(() => {
    if (still || !active) return undefined;
    let i = 0;
    let off: number | undefined;
    const wake = () => {
      setN(i++ % NOTICES.length);
      off = window.setTimeout(() => setN(-1), 4200);
    };
    const first = window.setTimeout(wake, 3200);
    const every = window.setInterval(wake, 9500);
    return () => {
      window.clearTimeout(first);
      window.clearInterval(every);
      if (off) window.clearTimeout(off);
    };
  }, [active, still]);

  const notice = n >= 0 ? NOTICES[n] : null;
  return (
    <div className={`v1-phone${notice ? " is-awake" : ""}`}>
      <div className="v1-phone-screen">
        <span className="v1-phone-time">9:41</span>
        <span className="v1-phone-date">Monday</span>
        <span className="v1-phone-note" key={n}>
          <b>{notice?.app ?? ""}</b>
          {notice?.text ?? ""}
        </span>
      </div>
      <span className="v1-phone-glare" />
    </div>
  );
}

const Napkin = memo(function Napkin() {
  return (
    <svg viewBox="0 0 240 160" className="h-full w-full" aria-hidden>
      <defs>
        <linearGradient id="v1-linen" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="0.6" stopColor="#f3f4f6" />
          <stop offset="1" stopColor="#e3e6ea" />
        </linearGradient>
        <linearGradient id="v1-fold" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#d9dde3" stopOpacity="0" />
          <stop offset="0.5" stopColor="#cfd4db" stopOpacity="0.8" />
          <stop offset="1" stopColor="#d9dde3" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d="M14,22 C70,8 160,4 236,18 L240,150 C170,160 80,158 6,146 C10,110 8,60 14,22 Z" fill="url(#v1-linen)" />
      <path d="M60,16 C66,60 62,110 70,152" stroke="url(#v1-fold)" strokeWidth="9" fill="none" opacity="0.7" />
      <path d="M150,10 C144,58 152,104 146,156" stroke="url(#v1-fold)" strokeWidth="12" fill="none" opacity="0.55" />
      <path d="M14,22 C70,8 160,4 236,18" stroke="#ffffff" strokeWidth="2" fill="none" />
      <path d="M20,30 C80,18 160,14 232,26" stroke="#dfe2e7" strokeWidth="0.8" strokeDasharray="2 3" fill="none" />
    </svg>
  );
});

export function TableSurface() {
  return (
    <div className="v1-table" aria-hidden>
      <div className="v1-table-floor" />
      <div className="v1-leaf-shadow">
        <img src="/variant-1/fern.webp" alt="" decoding="async" />
      </div>
      <div className="v1-vase-shadow" />
      <div className="v1-flat v1-napkin" style={flat(674, 528, 250, 168, -6)}>
        <Napkin />
      </div>
    </div>
  );
}

export function TableItems() {
  return (
    <div className="v1-table v1-table-items" aria-hidden>
      <div className="v1-flat v1-notebook" style={flat(450, 560, 252, 176, -9)}>
        <span className="v1-notebook-mark">
          <svg viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="28" fill="none" stroke="currentColor" strokeWidth="1.4" />
            <text x="32" y="33" textAnchor="middle" dominantBaseline="central" fill="currentColor">
              WIA
            </text>
          </svg>
        </span>
        <span className="v1-notebook-band" />
      </div>
      <div className="v1-flat v1-phone-wrap" style={flat(556, 548, 80, 160, -74)}>
        <Phone />
      </div>
      <div className="v1-flat v1-print is-swatch" style={flat(388, 640, 178, 150, 7, { animationDelay: "0.25s" })}>
        <span className="v1-print-inner">
          <span className="v1-swatches">
            {SWATCHES.map((c) => (
              <i key={c} style={{ background: c }} />
            ))}
          </span>
        </span>
      </div>
      <div className="v1-flat v1-print is-marble" style={flat(500, 690, 156, 128, -5, { animationDelay: "0.4s" })}>
        <span className="v1-print-inner">
          <CoastStatic viewBox="48 92 205 174" detail="low" className="h-full w-full" />
        </span>
      </div>
      <div className="v1-flat v1-print is-coast" style={flat(262, 666, 186, 168, -9, { animationDelay: "0.1s" })}>
        <span className="v1-print-inner">
          <CoastStatic viewBox="0 150 290 250" detail="low" className="h-full w-full" />
        </span>
      </div>
    </div>
  );
}
