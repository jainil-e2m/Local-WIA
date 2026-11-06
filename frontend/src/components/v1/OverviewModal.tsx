import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowRight, ChevronLeft, ChevronRight, Pause, Play, RotateCcw, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/auth";
import { toolsForRole } from "@/data/tools";
import { ROADMAP_PHASES, resolveTimelineView } from "@/data/timeline";
import { SOURCE_META, SOURCE_ORDER } from "@/lib/opsHub";
import { useV1Action } from "./useV1Action";

/* ────────────────────────────────────────────────────────────────
   "Watch overview" — a short film about the hub, made of the hub.

   Five chapters, played like video: a segmented scrubber, play/pause,
   chapter skipping (←/→, space, esc). Every figure and name in it is
   read live from the same sources as the page — the roadmap, the
   consoles the viewer's role can open, the Ops Hub's source list — so
   the film can't drift out of date the way a recorded one would.
   ──────────────────────────────────────────────────────────────── */

const CHAPTERS = [
  { id: "intro", title: "The Command Center", seconds: 6.5 },
  { id: "roadmap", title: "The roadmap", seconds: 7.5 },
  { id: "consoles", title: "Live consoles", seconds: 7 },
  { id: "sources", title: "One hub, every source", seconds: 7.5 },
  { id: "ready", title: "Ready when you are", seconds: 6 },
] as const;

const ease = [0.22, 1, 0.36, 1] as const;

export function OverviewModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <AnimatePresence>
      {open && <Player onClose={onClose} />}
    </AnimatePresence>
  );
}

function Player({ onClose }: { onClose: () => void }) {
  const reduce = useReducedMotion() ?? false;
  const [chapter, setChapter] = useState(0);
  const [playing, setPlaying] = useState(!reduce);
  const [progress, setProgress] = useState(0); // 0..1 within the chapter
  const progressRef = useRef(0);
  const last = chapter === CHAPTERS.length - 1;
  const ended = last && progress >= 1;

  const go = useCallback((i: number) => {
    const next = Math.max(0, Math.min(CHAPTERS.length - 1, i));
    progressRef.current = 0;
    setProgress(0);
    setChapter(next);
  }, []);

  // The clock: advances the scrubber, rolls into the next chapter.
  useEffect(() => {
    if (!playing) return undefined;
    let raf = 0;
    let prev = performance.now();
    const tick = (now: number) => {
      const dt = Math.min(0.1, (now - prev) / 1000);
      prev = now;
      const p = Math.min(1, progressRef.current + dt / CHAPTERS[chapter].seconds);
      progressRef.current = p;
      setProgress(p);
      if (p >= 1) {
        if (chapter < CHAPTERS.length - 1) go(chapter + 1);
        else setPlaying(false);
        return;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, chapter, go]);

  const toggle = useCallback(() => {
    if (ended) {
      go(0);
      setPlaying(true);
    } else setPlaying((p) => !p);
  }, [ended, go]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") go(chapter + 1);
      else if (e.key === "ArrowLeft") go(chapter - 1);
      else if (e.key === " " && !(e.target instanceof HTMLButtonElement)) {
        e.preventDefault();
        toggle();
      }
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [chapter, go, toggle, onClose]);

  return (
    <motion.div
      className="v1-overlay is-film"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35 }}
      onMouseDown={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Command Center overview"
    >
      <motion.div
        className="v1-film"
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 16, scale: 0.98 }}
        transition={{ duration: 0.5, ease }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <button type="button" className="v1-film-close" onClick={onClose} aria-label="Close overview">
          <X className="h-[18px] w-[18px]" strokeWidth={1.6} />
        </button>

        <div className="v1-film-screen" onClick={toggle}>
          <div className="v1-film-grain" aria-hidden />
          <AnimatePresence mode="wait">
            <motion.div
              key={chapter}
              className="v1-film-chapter"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, transition: { duration: 0.3 } }}
              transition={{ duration: 0.5 }}
            >
              <Chapter id={CHAPTERS[chapter].id} onClose={onClose} />
            </motion.div>
          </AnimatePresence>
          {!playing && !ended && (
            <span className="v1-film-paused" aria-hidden>
              <Play className="h-6 w-6" fill="currentColor" strokeWidth={0} />
            </span>
          )}
        </div>

        <div className="v1-film-bar">
          <button type="button" className="v1-film-btn" onClick={toggle} aria-label={ended ? "Replay" : playing ? "Pause" : "Play"}>
            {ended ? (
              <RotateCcw className="h-[16px] w-[16px]" strokeWidth={1.8} />
            ) : playing ? (
              <Pause className="h-[16px] w-[16px]" fill="currentColor" strokeWidth={0} />
            ) : (
              <Play className="h-[16px] w-[16px] translate-x-[1px]" fill="currentColor" strokeWidth={0} />
            )}
          </button>
          <button type="button" className="v1-film-btn is-ghost" onClick={() => go(chapter - 1)} disabled={chapter === 0} aria-label="Previous chapter">
            <ChevronLeft className="h-[16px] w-[16px]" strokeWidth={1.8} />
          </button>
          <button type="button" className="v1-film-btn is-ghost" onClick={() => go(chapter + 1)} disabled={last} aria-label="Next chapter">
            <ChevronRight className="h-[16px] w-[16px]" strokeWidth={1.8} />
          </button>

          <div className="v1-film-track" role="group" aria-label="Chapters">
            {CHAPTERS.map((c, i) => (
              <button
                key={c.id}
                type="button"
                className="v1-film-seg"
                onClick={() => go(i)}
                aria-label={`Chapter ${i + 1}: ${c.title}`}
                aria-current={i === chapter}
              >
                <span
                  className="v1-film-seg-fill"
                  style={{ transform: `scaleX(${i < chapter ? 1 : i === chapter ? progress : 0})` }}
                />
              </button>
            ))}
          </div>

          <p className="v1-film-label" aria-live="polite">
            <span>{String(chapter + 1).padStart(2, "0")}</span>
            {CHAPTERS[chapter].title}
          </p>
        </div>
      </motion.div>
    </motion.div>
  );
}

/* ── Chapters ───────────────────────────────────────────────────── */

function Chapter({ id, onClose }: { id: (typeof CHAPTERS)[number]["id"]; onClose: () => void }) {
  switch (id) {
    case "intro":
      return <Intro />;
    case "roadmap":
      return <Roadmap />;
    case "consoles":
      return <Consoles />;
    case "sources":
      return <Sources />;
    case "ready":
      return <Ready onClose={onClose} />;
  }
}

const up = (delay: number) => ({
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.9, delay, ease },
});

function Intro() {
  return (
    <div className="v1-ch v1-ch-center">
      <svg viewBox="0 0 120 120" className="v1-ch-mark" aria-hidden>
        <motion.circle
          cx="60"
          cy="60"
          r="56"
          fill="none"
          stroke="url(#v1-film-gold)"
          strokeWidth="1.4"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 2, ease: [0.65, 0, 0.35, 1] }}
        />
        <defs>
          <linearGradient id="v1-film-gold" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#f1dfb0" />
            <stop offset="0.5" stopColor="#c9a24c" />
            <stop offset="1" stopColor="#ecd59f" />
          </linearGradient>
        </defs>
        <motion.text
          x="60"
          y="62"
          textAnchor="middle"
          dominantBaseline="central"
          fill="#fff"
          className="v1-ch-mark-text"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.2, delay: 0.9 }}
        >
          WIA
        </motion.text>
      </svg>
      <motion.p {...up(1.3)} className="v1-ch-eyebrow">
        Wedding Industry Ads · Command Center
      </motion.p>
      <motion.h3 {...up(1.6)} className="v1-ch-title">
        Your wedding business, <em>Automated &amp; simplified</em> for growth.
      </motion.h3>
    </div>
  );
}

function Roadmap() {
  const view = useMemo(() => resolveTimelineView(), []);
  const ids = new Set(view.items.map((i) => i.id));
  const phases = ROADMAP_PHASES.map((p) => ({ ...p, items: p.items.filter((i) => ids.has(i.id)) }));
  const max = Math.max(...phases.map((p) => p.items.length), 1);

  return (
    <div className="v1-ch">
      <motion.p {...up(0.1)} className="v1-ch-eyebrow">
        The Blueprint roadmap
      </motion.p>
      <motion.h3 {...up(0.25)} className="v1-ch-title is-left">
        <span className="v1-ch-num">{view.tally.total}</span> automations, in three phases.
      </motion.h3>
      <div className="v1-ch-phases">
        {phases.map((p, i) => (
          <motion.div key={p.id} {...up(0.6 + i * 0.25)} className="v1-ch-phase">
            <p className="v1-ch-phase-name">
              <span>Phase {i + 1}</span>
              {p.title}
            </p>
            <div className="v1-ch-phase-track">
              <motion.span
                className="v1-ch-phase-bar"
                initial={{ width: 0 }}
                animate={{ width: `${(p.items.length / max) * 100}%` }}
                transition={{ duration: 1.4, delay: 0.9 + i * 0.25, ease }}
              />
            </div>
            <p className="v1-ch-phase-count">{p.items.length}</p>
          </motion.div>
        ))}
      </div>
      <motion.p {...up(1.8)} className="v1-ch-foot">
        <span className="v1-ch-dot" /> {view.tally.delivered} demoed at review · {view.tally.inDevelopment} in development
      </motion.p>
    </div>
  );
}

function Consoles() {
  const { user } = useAuth();
  const live = toolsForRole(user?.role).filter((t) => t.status === "live");
  return (
    <div className="v1-ch">
      <motion.p {...up(0.1)} className="v1-ch-eyebrow">
        Open today
      </motion.p>
      <motion.h3 {...up(0.25)} className="v1-ch-title is-left">
        {live.length} consoles, live in the hub.
      </motion.h3>
      <div className="v1-ch-consoles">
        {live.map((t, i) => (
          <motion.div key={t.id} {...up(0.7 + i * 0.22)} className="v1-ch-console">
            <span className="v1-ch-console-icon" style={{ background: `linear-gradient(140deg, ${t.from}, ${t.to})` }}>
              <t.icon className="h-[18px] w-[18px]" strokeWidth={1.7} />
            </span>
            <span className="v1-ch-console-name">{t.name}</span>
            <span className="v1-ch-console-tags">{t.tags.join(" · ")}</span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function Sources() {
  const n = SOURCE_ORDER.length;
  return (
    <div className="v1-ch v1-ch-split">
      <div>
        <motion.p {...up(0.1)} className="v1-ch-eyebrow">
          AI Operations Hub · walkthrough
        </motion.p>
        <motion.h3 {...up(0.25)} className="v1-ch-title is-left">
          Seven sources. One place to decide.
        </motion.h3>
        <motion.p {...up(0.5)} className="v1-ch-copy">
          What needs a decision today, the context behind it, and an approval gate in front of anything that
          leaves the building.
        </motion.p>
      </div>
      <div className="v1-ch-orbit" aria-hidden>
        <motion.span
          className="v1-ch-orbit-ring"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.2, ease }}
        />
        <motion.span className="v1-ch-orbit-core" {...up(0.4)}>
          AI Ops
        </motion.span>
        <div className="v1-ch-orbit-spin">
          {SOURCE_ORDER.map((key, i) => {
            const meta = SOURCE_META[key];
            const a = (i / n) * Math.PI * 2 - Math.PI / 2;
            return (
              <motion.span
                key={key}
                className="v1-ch-orbit-node"
                style={{ left: `${50 + Math.cos(a) * 42}%`, top: `${50 + Math.sin(a) * 42}%` }}
                initial={{ opacity: 0, scale: 0.4 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.7, delay: 0.6 + i * 0.12, ease }}
              >
                {/* counter-rotates so each logo stays upright as the ring turns */}
                <span className="v1-ch-orbit-face">
                  {meta.logo ? <img src={meta.logo} alt="" /> : meta.label.slice(0, 2)}
                </span>
              </motion.span>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Ready({ onClose }: { onClose: () => void }) {
  const run = useV1Action();
  return (
    <div className="v1-ch v1-ch-center">
      <motion.p {...up(0.1)} className="v1-ch-eyebrow">
        Ready when you are
      </motion.p>
      <motion.h3 {...up(0.3)} className="v1-ch-title">
        Your wedding growth engine, <em>in one place.</em>
      </motion.h3>
      <motion.div {...up(0.7)} className={cn("v1-ch-ctas")} onClick={(e) => e.stopPropagation()}>
        <Link to="/ops-hub" className="v1-cta is-light" onClick={onClose}>
          <span>Enter Command Center</span>
          <ArrowRight className="v1-cta-arrow" strokeWidth={1.6} aria-hidden />
        </Link>
        <button
          type="button"
          className="v1-film-text-btn"
          onClick={() => {
            onClose();
            run({ kind: "automations" });
          }}
        >
          View automations
        </button>
      </motion.div>
    </div>
  );
}
