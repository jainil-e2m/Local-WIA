import { useEffect, useRef, useState, type MutableRefObject } from "react";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { ActionLink } from "../ActionLink";
import { ORBIT_CARDS, type OrbitGlyph } from "../destinations";
import { useFrameLoop, useStage } from "./stage";

/* ────────────────────────────────────────────────────────────────
   The gold orbit and the cards that ride it.

   The cards sit ON the main ring and travel round it, clockwise, one turn
   every ORBIT_PERIOD seconds — slow enough to read and to click. Pointing
   at or focusing any card eases the whole orbit to a stop (and eases it
   back up on leave), so nothing slides out from under the cursor. The
   gold beads travel with them; the outer arcs and the comet run on their
   own clocks so the gold is never entirely still.
   ──────────────────────────────────────────────────────────────── */

// The larger orbit frames the whole still life. Cards, beads and comets share
// this radius so they stay on the ring as it turns.
export const ORBIT = { cx: 450, cy: 404, r: 400 };
const INNER_RADIUS = ORBIT.r - 56;
const OUTER_RADIUS = ORBIT.r + 54;
const OUTER_CENTER = { cx: ORBIT.cx + 30, cy: ORBIT.cy + 12 };
const ORBIT_PERIOD = 150; // seconds per turn
const CARD_W = 252;
const CARD_H = 64;
const CARD_PADDING = 26; // breathing room around the moving cards, px
// Include cards and outer arcs when fitting the scene to its column.
export const ORBIT_BOUNDS = {
  width: 2 * (ORBIT.r + CARD_W / 2 + CARD_PADDING),
  height: 2 * (OUTER_RADIUS + 12 + 12),
};
const BEADS = [266, 40, 186]; // degrees, between cards

export interface OrbitClock {
  /** Degrees the orbit has turned since mount. */
  turn: number;
  /** 0 = stopped, 1 = cruising. */
  speed: number;
  /** Cards currently hovered or focused. */
  holds: number;
}

const rad = (deg: number) => (deg * Math.PI) / 180;

export function OrbitRings({ clock }: { clock: MutableRefObject<OrbitClock> }) {
  const beadRefs = useRef<(SVGGElement | null)[]>([]);
  const { cx, cy, r } = ORBIT;

  useFrameLoop(() => {
    const turn = clock.current.turn;
    BEADS.forEach((a, i) => {
      const el = beadRefs.current[i];
      if (!el) return;
      const t = rad(a + turn);
      el.setAttribute("transform", `translate(${cx + r * Math.cos(t)} ${cy + r * Math.sin(t)})`);
    });
  });

  return (
    <svg className="v1-rings" viewBox="0 0 900 820" aria-hidden>
      <defs>
        <linearGradient id="v1-gold" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#efdcab" />
          <stop offset="0.35" stopColor="#c9a24c" />
          <stop offset="0.62" stopColor="#ead39b" />
          <stop offset="1" stopColor="#b48a38" />
        </linearGradient>
        <linearGradient id="v1-gold-soft" x1="1" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#e6cf97" stopOpacity="0.9" />
          <stop offset="1" stopColor="#c8a14d" stopOpacity="0.55" />
        </linearGradient>
        <radialGradient id="v1-bead">
          <stop offset="0" stopColor="#fff6dc" />
          <stop offset="0.45" stopColor="#e2bd68" />
          <stop offset="1" stopColor="#b88a2e" />
        </radialGradient>
        <radialGradient id="v1-bead-halo">
          <stop offset="0" stopColor="#e9c977" stopOpacity="0.55" />
          <stop offset="1" stopColor="#e9c977" stopOpacity="0" />
        </radialGradient>
        <filter id="v1-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2.2" />
        </filter>
      </defs>

      {/* inner dotted ring, drifting */}
      <g className="v1-ring-spin is-slow">
        <circle
          cx={cx}
          cy={cy}
          r={INNER_RADIUS}
          fill="none"
          stroke="#c9a24c"
          strokeOpacity="0.38"
          strokeWidth="1"
          strokeDasharray="1.5 7"
          strokeLinecap="round"
        />
      </g>

      {/* outer arcs, counter-rotating, carrying two fixed nodes */}
      <g className="v1-ring-spin is-reverse" style={{ transformOrigin: `${OUTER_CENTER.cx}px ${OUTER_CENTER.cy}px` }}>
        <circle
          className="v1-ring-draw is-late"
          cx={OUTER_CENTER.cx}
          cy={OUTER_CENTER.cy}
          r={OUTER_RADIUS}
          fill="none"
          stroke="url(#v1-gold-soft)"
          strokeWidth="1"
          pathLength={1000}
          strokeDasharray="210 70 120 140 260 200"
        />
        {[18, 214].map((a) => {
          const t = rad(a);
          return (
            <g key={a} transform={`translate(${OUTER_CENTER.cx + OUTER_RADIUS * Math.cos(t)} ${OUTER_CENTER.cy + OUTER_RADIUS * Math.sin(t)})`}>
              <circle r="9" fill="url(#v1-bead-halo)" />
              <circle r="3.4" fill="url(#v1-bead)" />
            </g>
          );
        })}
      </g>

      {/* the orbit itself */}
      <circle
        className="v1-ring-draw"
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke="url(#v1-gold)"
        strokeWidth="1.2"
        pathLength={1000}
      />
      {/* comets: short bright runs that lap the orbit */}
      <circle
        className="v1-comet"
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke="#e3bd62"
        strokeWidth="2.4"
        strokeLinecap="round"
        pathLength={1000}
        strokeDasharray="46 954"
        filter="url(#v1-glow)"
      />
      <circle
        className="v1-comet is-core"
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke="#fff3cf"
        strokeWidth="1.2"
        strokeLinecap="round"
        pathLength={1000}
        strokeDasharray="22 978"
      />

      {BEADS.map((a, i) => (
        <g key={a} ref={(el) => (beadRefs.current[i] = el)} className="v1-bead">
          <circle r="11" fill="url(#v1-bead-halo)" />
          <circle r="3.8" fill="url(#v1-bead)" />
        </g>
      ))}
    </svg>
  );
}

export function OrbitCards({ clock }: { clock: MutableRefObject<OrbitClock> }) {
  const { still } = useStage();
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);
  const { cx, cy, r } = ORBIT;

  useFrameLoop((t, dt) => {
    const c = clock.current;
    const target = c.holds > 0 ? 0 : 1;
    c.speed += (target - c.speed) * Math.min(1, dt * (target ? 1.4 : 5));
    if (!still) c.turn = (c.turn + (360 / ORBIT_PERIOD) * c.speed * dt) % 360;

    ORBIT_CARDS.forEach((card, i) => {
      const el = cardRefs.current[i];
      if (!el) return;
      const a = rad(card.angle + c.turn);
      const bob = still ? 0 : Math.sin(t * 0.7 + i * 1.7) * 3.2;
      const x = cx + r * Math.cos(a) - CARD_W / 2;
      const y = cy + r * Math.sin(a) - CARD_H / 2 + bob;
      el.style.transform = `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0)`;
    });
  });

  return (
    <div className="v1-cards">
      {ORBIT_CARDS.map((card, i) => (
        <div
          key={card.id}
          ref={(el) => (cardRefs.current[i] = el)}
          className="v1-card-slot"
          style={{
            width: CARD_W,
            height: CARD_H,
            transform: `translate3d(${cx + r * Math.cos(rad(card.angle)) - CARD_W / 2}px, ${
              cy + r * Math.sin(rad(card.angle)) - CARD_H / 2
            }px, 0)`,
          }}
        >
          <OrbitCard index={i} clock={clock} />
        </div>
      ))}
    </div>
  );
}

function OrbitCard({ index, clock }: { index: number; clock: MutableRefObject<OrbitClock> }) {
  const card = ORBIT_CARDS[index];
  const [hover, setHover] = useState(false);
  const [focus, setFocus] = useState(false);
  const held = hover || focus;

  /* Hover and focus are tracked apart so that leaving with the mouse does not
     restart the orbit under a card that still has keyboard focus. */
  useEffect(() => {
    if (!held) return undefined;
    const c = clock.current;
    c.holds += 1;
    return () => {
      c.holds -= 1;
    };
  }, [held, clock]);

  return (
    <motion.div
      className="h-full w-full"
      initial={{ opacity: 0, scale: 0.9, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.9, delay: 1.5 + index * 0.12, ease: [0.22, 1, 0.36, 1] }}
    >
      <ActionLink
        action={card.action}
        className="v1-card"
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        onFocus={() => setFocus(true)}
        onBlur={() => setFocus(false)}
      >
        <span className="v1-card-glyph" aria-hidden>
          <Glyph kind={card.glyph} />
        </span>
        <span className="v1-card-title">{card.title}</span>
        <ArrowRight className="v1-card-arrow" strokeWidth={1.6} aria-hidden />
      </ActionLink>
    </motion.div>
  );
}

/* Filled glyphs, drawn to match the design rather than taken from the outline
   icon set the rest of the page uses. */
function Glyph({ kind }: { kind: OrbitGlyph }) {
  switch (kind) {
    case "folder":
      return (
        <svg viewBox="0 0 24 24" className="h-[22px] w-[22px]">
          <path
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
            d="M2.8 6.6c0-1 .8-1.8 1.8-1.8h4.6l2 2.3h8.2c1 0 1.8.8 1.8 1.8v9.5c0 1-.8 1.8-1.8 1.8H4.6c-1 0-1.8-.8-1.8-1.8V6.6Z"
          />
          <path fill="none" stroke="currentColor" strokeWidth="1.6" d="M2.8 10.2h18.4" />
        </svg>
      );
    case "lock":
      return (
        <svg viewBox="0 0 24 24" className="h-[22px] w-[22px]">
          <rect x="4.2" y="10.4" width="15.6" height="11" rx="2.6" fill="currentColor" />
          <path fill="none" stroke="currentColor" strokeWidth="1.9" d="M7.9 10.4V7.6a4.1 4.1 0 0 1 8.2 0v2.8" />
          <circle cx="12" cy="15.3" r="1.5" fill="#fff" />
          <path stroke="#fff" strokeWidth="1.4" strokeLinecap="round" d="M12 16.4v1.9" />
        </svg>
      );
    case "globe":
      return (
        <svg viewBox="0 0 24 24" className="h-[22px] w-[22px]">
          <g fill="none" stroke="currentColor" strokeWidth="1.6">
            <circle cx="12" cy="12" r="9.2" />
            <ellipse cx="12" cy="12" rx="4" ry="9.2" />
            <path d="M3 9.2h18M3 14.8h18" />
          </g>
        </svg>
      );
  }
}
