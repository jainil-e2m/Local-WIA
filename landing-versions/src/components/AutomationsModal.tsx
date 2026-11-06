import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUpRight, ChevronLeft, ChevronRight, Lock, X } from "lucide-react";
import { toolsForRole, toolRoute } from "@/data/tools";
import { useAuth } from "@/context/auth";

interface AutomationsModalProps {
  open: boolean;
  onClose: () => void;
}

/* Fan geometry — the fan is FIXED, symmetric around the middle (a hand of
   cards). Hover/pagination only raise a card out of the fan, in place. */
const ROTATE_STEP = 14; // deg per step away from the fan's center
const X_STEP = 122; // px per step away from the fan's center
const Y_DROP = 30; // px sink per step away from center (bottom edges form an arc)
const HOVER_SPREAD = 1.12; // fan opens slightly wider while hovered

/**
 * Launcher overlay — opens on "View automations".
 * Cards fan out in an arc (card-fan carousel): hovering a card raises and
 * straightens it, arrows/dots cycle the focused card, live card opens its
 * dashboard.
 */
export function AutomationsModal({ open, onClose }: AutomationsModalProps) {
  const { user } = useAuth();
  const tools = toolsForRole(user?.role);
  // null = resting fan, nothing raised (the default look)
  const [active, setActive] = useState<number | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const [fanHovered, setFanHovered] = useState(false);

  const n = tools.length;
  const CENTER = (n - 1) / 2; // fan pivot — fixed, never moves

  // Esc to close + lock page scroll while open
  useEffect(() => {
    if (!open) return;
    setActive(null);
    setHovered(null);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") setActive((a) => (a === null ? 0 : (a + 1) % n));
      if (e.key === "ArrowLeft") setActive((a) => (a === null ? n - 1 : (a - 1 + n) % n));
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose, n]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          /* Scrim is the brand's warm ink rather than the hub's navy. It stays
             dark on purpose: the page underneath is white now, and a light
             scrim over a light page gives the fan nothing to sit against. */
          className="fixed inset-0 z-[80] flex flex-col items-center justify-center overflow-hidden bg-[#221e17]/60 px-4 backdrop-blur-xl"
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-label="Choose an automation"
        >
          {/* close */}
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ delay: 0.25 }}
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="absolute right-6 top-6 z-10 grid h-10 w-10 place-items-center rounded-full border border-white/15 bg-white/[0.06] text-white/60 transition-colors hover:bg-white/[0.14] hover:text-white"
          >
            <X className="h-[18px] w-[18px]" />
          </motion.button>

          {/* heading */}
          <motion.div
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.45, delay: 0.1 }}
            className="pointer-events-none mb-2 text-center"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="text-[11.5px] font-bold uppercase tracking-[0.3em] text-brand-orange">
              Command Center
            </p>
            <h2 className="mt-2 text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
              Choose an automation
            </h2>
          </motion.div>

          {/* fan */}
          <div
            className="relative flex h-[430px] w-full max-w-4xl scale-[0.62] items-center justify-center sm:scale-90 lg:scale-100"
            onClick={(e) => e.stopPropagation()}
            onMouseEnter={() => setFanHovered(true)}
            onMouseOver={(e) => {
              // pointer over a gap between cards → nothing is hovered
              if (e.target === e.currentTarget) setHovered(null);
            }}
            onMouseLeave={() => {
              setFanHovered(false);
              setHovered(null);
            }}
          >
            {tools.map((tool, i) => {
              /* Geometry is anchored on the FIXED fan center — hover and
                 pagination never re-center the fan, they only raise a card
                 out of it in place. Cards can't slide out from under the
                 cursor. */
              const offset = i - CENTER;
              const spread = fanHovered ? HOVER_SPREAD : 1;
              const isHovered = hovered === i;
              const isActiveRaised = hovered === null && i === active;
              const raised = isHovered || isActiveRaised;
              const live = tool.status === "live";
              const Icon = tool.icon;
              const ctaLabel = tool.ctaLabel ?? "Run Audit";

              const card = (
                <motion.div
                  initial={{ opacity: 0, y: 120, rotate: 0, scale: 0.7 }}
                  animate={{
                    opacity: 1,
                    x: offset * X_STEP * spread,
                    y: Math.abs(offset) * Y_DROP + (raised ? -34 : 0),
                    /* hover keeps most of the tilt so the hit-box stays under
                       the cursor; only a pagination raise straightens fully */
                    rotate: isActiveRaised
                      ? 0
                      : offset * ROTATE_STEP * spread * (isHovered ? 0.85 : 1),
                    scale: raised ? 1.07 : 1 - Math.abs(offset) * 0.04,
                  }}
                  exit={{ opacity: 0, y: 110, scale: 0.8, transition: { duration: 0.28 } }}
                  transition={{
                    type: "spring",
                    stiffness: 240,
                    damping: 19,
                    mass: 0.9,
                    delay: open ? undefined : 0,
                  }}
                  className="pointer-events-auto"
                  style={{ transformOrigin: "50% 100%" }}
                  onMouseEnter={() => setHovered(i)}
                >
                  <div
                    className={[
                      /* items-center centers the icon, name and CTA on the cross
                         axis; the status chip opts out with self-end so it stays
                         pinned to the card's top-right corner. */
                      "relative flex h-[340px] w-[235px] flex-col items-center overflow-hidden rounded-[26px] border p-6 text-center shadow-[0_30px_70px_-18px_rgba(34,30,23,0.6)] transition-colors duration-300",
                      // Edges are the brand's slate at low alpha rather than two
                      // hand-picked greys — still no bright white rim, and hover
                      // keeps a slightly lighter step.
                      raised ? "border-brand-slate/55" : "border-brand-slate/25",
                      live ? "cursor-pointer" : "cursor-default",
                    ].join(" ")}
                    style={{
                      background: `linear-gradient(160deg, ${tool.from} 0%, ${tool.to} 120%)`,
                    }}
                  >
                    {/* soft inner glow */}
                    <div
                      className="pointer-events-none absolute inset-0 opacity-60"
                      style={{
                        background:
                          "radial-gradient(120% 70% at 80% -10%, rgba(255,255,255,0.28), transparent 55%)",
                      }}
                      aria-hidden
                    />

                    {/* status chip — the one element that opts out of centering */}
                    {live ? (
                      <span className="relative z-10 inline-flex w-fit self-end items-center gap-1.5 rounded-full bg-white/20 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-white backdrop-blur-sm">
                        {/* Periwinkle, not the old teal: there is no green in
                            the extracted palette, and brand-teal now resolves
                            to the brand's mocha, which does not read as live. */}
                        <span className="h-1.5 w-1.5 rounded-full bg-brand-sky" aria-hidden />
                        {/* See the note in ToolCard: these are demos, not
                            production automations. */}
                        Demo
                      </span>
                    ) : (
                      <span className="relative z-10 inline-flex w-fit self-end items-center gap-1.5 rounded-full bg-black/25 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-white/75 backdrop-blur-sm">
                        <Lock className="h-2.5 w-2.5" aria-hidden />
                        Coming soon
                      </span>
                    )}

                    {/* icon */}
                    <span className="relative z-10 mt-7 grid h-14 w-14 place-items-center rounded-2xl bg-white/15 text-white backdrop-blur-sm">
                      <Icon className="h-7 w-7" />
                    </span>

                    {/* name — the tag line was dropped; the tool page carries the
                        detail, and the fan reads better as name + CTA alone */}
                    <h3 className="relative z-10 mt-5 text-[21px] font-extrabold leading-tight text-white">
                      {tool.name}
                    </h3>

                    {/* CTA button (whole card navigates; this is the visual cue).
                        Coming-soon tools: unclickable until wired up. Label comes
                        from tool.ctaLabel — Lead Magnet reads "View Console"
                        since it's a records list, not an audit runner. */}
                    <div className="relative z-10 mt-auto">
                      {live ? (
                        <span className="inline-flex items-center gap-2 rounded-full border border-white/30 bg-white/15 px-4 py-2.5 text-[12px] font-bold uppercase tracking-[0.14em] text-white backdrop-blur-sm transition-colors duration-300 hover:bg-white/25">
                          {ctaLabel}
                          <ArrowUpRight className="h-4 w-4" />
                        </span>
                      ) : (
                        <span
                          aria-disabled
                          className="inline-flex cursor-not-allowed items-center gap-2 rounded-full border border-white/15 bg-white/[0.08] px-4 py-2.5 text-[12px] font-bold uppercase tracking-[0.14em] text-white/40 backdrop-blur-sm"
                        >
                          {ctaLabel}
                          <Lock className="h-3.5 w-3.5" />
                        </span>
                      )}
                    </div>
                  </div>
                </motion.div>
              );

              // fractional offsets (±0.5, ±1.5) → double to get integer z steps
              /* Wrappers are untransformed boxes stacked at the fan center —
                 they must NOT be hit targets (pointer-events-none), or they
                 swallow hovers meant for the visually-transformed cards.
                 The motion.div re-enables pointer events, so the hit area is
                 exactly the rotated, rounded card you see. */
              const z = raised ? 10 : 8 - Math.round(Math.abs(offset) * 2);

              /* Locked tools render as a plain (unlinked) card, so the whole
                 card — not just its CTA — is inert. `live` comes from the
                 tool's resolved status, which its VITE_TOOL_<ID>_ENABLED flag
                 can override; see data/toolFlags.ts. */
              if (!live) {
                return (
                  <div key={tool.id} className="pointer-events-none absolute" style={{ zIndex: z }}>
                    {card}
                  </div>
                );
              }

              return (
                <Link
                  key={tool.id}
                  to={toolRoute(tool)}
                  aria-label={`Open ${tool.name}`}
                  className="pointer-events-none absolute"
                  style={{ zIndex: z }}
                >
                  {card}
                </Link>
              );
            })}
          </div>

          {/* pagination */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.45, delay: 0.35 }}
            className="relative z-20 mt-2 flex items-center gap-5"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              aria-label="Previous automation"
              onClick={() => setActive((a) => (a === null ? n - 1 : (a - 1 + n) % n))}
              className="grid h-10 w-10 place-items-center rounded-full border border-white/15 bg-white/[0.06] text-white/70 transition-colors hover:bg-white/[0.14] hover:text-white"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-2.5">
              {tools.map((t, i) => (
                <button
                  key={t.id}
                  type="button"
                  aria-label={`Focus ${t.name}`}
                  onClick={() => setActive(i)}
                  className={[
                    "h-2 rounded-full transition-all duration-300",
                    i === active ? "w-6 bg-brand-orange" : "w-2 bg-white/25 hover:bg-white/45",
                  ].join(" ")}
                />
              ))}
            </div>

            <button
              type="button"
              aria-label="Next automation"
              onClick={() => setActive((a) => (a === null ? 0 : (a + 1) % n))}
              className="grid h-10 w-10 place-items-center rounded-full border border-white/15 bg-white/[0.06] text-white/70 transition-colors hover:bg-white/[0.14] hover:text-white"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
