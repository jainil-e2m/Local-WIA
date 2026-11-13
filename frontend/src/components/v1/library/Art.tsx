import { useEffect, useRef, useState, type ComponentType, type CSSProperties, type ReactNode, type RefObject } from "react";
import { AnimatePresence, motion, useInView, useReducedMotion } from "framer-motion";
import {
  ArrowUp,
  Briefcase,
  CalendarCheck,
  ChevronLeft,
  ChevronRight,
  Folder,
  Globe,
  ListChecks,
  MessageCircle,
  PhoneCall,
  Play,
  Sparkles,
} from "lucide-react";

/* ────────────────────────────────────────────────────────────────
   The collage at the top of each library card: photographs from the
   terrace, a little white UI panel or two, and the flowers.

   Every piece is placed in the card's own container units (1cqi = 1% of
   the card's width, measured off the reference at a 351px card), so the
   collage keeps its proportions at any column width. --z is how far a
   piece drifts with the pointer (its depth) and --d its delay when the
   card first comes into view; both are read by v1.css.
   ──────────────────────────────────────────────────────────────── */

interface PieceProps {
  className: string;
  /** left, top, width, height in cqi; rotation in degrees; depth; entrance delay (s). */
  at: [number, number, number, number, number?, number?, number?];
  children?: ReactNode;
  style?: CSSProperties;
}

function Piece({ className, at: [l, t, w, h, r = 0, z = 2, d = 0], children, style }: PieceProps) {
  const vars = { "--l": l, "--t": t, "--w": w, "--h": h, "--r": `${r}deg`, "--z": z, "--d": `${d}s`, ...style } as CSSProperties;
  return (
    <div className={`v1-piece ${className}`} style={vars}>
      {children}
    </div>
  );
}

const v = (vars: Record<string, string | number>) => vars as CSSProperties;

/* Simplified marks for where the content goes out: Instagram, Facebook,
   Gmail. Each takes its own gradient id, so two Instagram marks on a page
   never share one. */
function InstagramMark({ id }: { id: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden>
      <defs>
        <linearGradient id={id} x1="0" y1="1" x2="1" y2="0">
          <stop offset="0" stopColor="#feda75" />
          <stop offset="0.45" stopColor="#d62976" />
          <stop offset="1" stopColor="#4f5bd5" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="20" height="20" rx="6" fill={`url(#${id})`} />
      <rect x="6.5" y="6.5" width="11" height="11" rx="3.4" fill="none" stroke="#fff" strokeWidth="1.6" />
      <circle cx="12" cy="12" r="2.7" fill="none" stroke="#fff" strokeWidth="1.6" />
      <circle cx="16.1" cy="7.9" r="0.9" fill="#fff" />
    </svg>
  );
}

function FacebookMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden>
      <circle cx="12" cy="12" r="10.5" fill="#1877f2" />
      <path d="M13.3 22.4v-7.3h2.4l.4-2.9h-2.8v-1.8c0-.8.3-1.4 1.4-1.4h1.5V6.4c-.3 0-1.2-.1-2.2-.1-2.2 0-3.6 1.3-3.6 3.7v2.2H8v2.9h2.4v7.3" fill="#fff" />
    </svg>
  );
}

function GmailMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden>
      <circle cx="12" cy="12" r="10.5" fill="#fff" stroke="#e3e6ed" strokeWidth="0.8" />
      <path d="M6.4 16.4V9.4" stroke="#4285f4" strokeWidth="2.3" strokeLinecap="round" />
      <path d="M17.6 16.4V9.4" stroke="#34a853" strokeWidth="2.3" strokeLinecap="round" />
      <path d="M6.4 9.4 12 13.5l5.6-4.1" fill="none" stroke="#ea4335" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="6.4" cy="9.4" r="1.15" fill="#c5221f" />
      <circle cx="17.6" cy="9.4" r="1.15" fill="#fbbc04" />
    </svg>
  );
}

/**
 * Steps through a loop of timed phases while `ref` is on screen, holding
 * still with motion reduced. Returns how many phases have passed.
 */
function useLoop(durations: readonly number[], ref: RefObject<Element>) {
  const reduce = useReducedMotion() ?? false;
  const inView = useInView(ref, { amount: 0.4 });
  const [step, setStep] = useState(0);
  useEffect(() => {
    if (reduce || !inView) return undefined;
    const id = window.setTimeout(() => setStep((n) => n + 1), durations[step % durations.length]);
    return () => window.clearTimeout(id);
  }, [step, inView, reduce, durations]);
  return step;
}

const SWAP = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] } },
  exit: { opacity: 0, y: -6, transition: { duration: 0.25, ease: [0.4, 0, 1, 1] } },
} as const;

/* Content Atelier turns out one piece after another: a reel, a carousel,
   an email. The channel it is going to lights up in the strip beside it. */
const FORMATS = [
  { id: "reel", label: "Reel", channel: "instagram", tag: "0:15" },
  { id: "carousel", label: "Carousel", channel: "instagram", tag: "1 / 5" },
  { id: "email", label: "Email", channel: "gmail", tag: "Draft" },
] as const;
const FORMAT_MS = [3400, 3400, 3400] as const;

function FormatBody({ id }: { id: (typeof FORMATS)[number]["id"] }) {
  const lines = (widths: string[]) => (
    <span className="v1-art-lines">
      {widths.map((w, i) => (
        <i key={i} style={v({ "--w": w, "--d": `${0.2 + i * 0.1}s` })} />
      ))}
    </span>
  );
  if (id === "reel")
    return (
      <>
        <p>A love story, a beautiful venue, and a day to remember. ✨</p>
        {lines(["80%", "70%", "52%"])}
      </>
    );
  if (id === "carousel")
    return (
      <>
        <span className="v1-art-slides">
          <i className="is-a" />
          <i className="is-b" />
          <i className="is-c" />
        </span>
        <p>Swipe through the day, moment by moment. 🤍</p>
        <span className="v1-art-dots">
          <i className="is-on" />
          <i />
          <i />
          <i />
          <i />
        </span>
      </>
    );
  return (
    <>
      <p className="v1-art-mail">
        <small>To: Hannah &amp; James</small>
        <span>Your venue tour is confirmed 💍</span>
      </p>
      {lines(["86%", "74%", "58%"])}
    </>
  );
}

function AtelierArt() {
  const swapRef = useRef<HTMLDivElement>(null);
  const format = FORMATS[useLoop(FORMAT_MS, swapRef) % FORMATS.length];
  return (
    <>
      <span className="v1-art-orbit" style={v({ "--l": 2, "--t": -6, "--s": 88 })} />
      <Piece className="v1-art-photo is-sea" at={[47.6, 2.6, 45, 57, 3.5, 2.2, 0.05]} />
      <Piece className="v1-art-panel v1-art-caption" at={[16.2, 5.4, 49.9, 49.3, -4, 3.4, 0.2]}>
        <div ref={swapRef} className="v1-art-swap">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div key={format.id} {...SWAP}>
              <b className="v1-art-format">
                {format.channel === "gmail" ? <GmailMark /> : <InstagramMark id="v1-ig-format" />}
                {format.label}
                <small>
                  {format.id === "reel" && <Play strokeWidth={0} fill="currentColor" />}
                  {format.tag}
                </small>
              </b>
              <FormatBody id={format.id} />
            </motion.div>
          </AnimatePresence>
        </div>
        <em className="v1-art-approve">
          <Sparkles strokeWidth={1.8} />
          Approve
        </em>
      </Piece>
      <Piece className="v1-art-panel v1-art-social" at={[5.7, 24.8, 12, 29, 0, 4.4, 0.35]}>
        <span className={format.channel === "instagram" ? "is-on" : undefined}>
          <InstagramMark id="v1-ig-strip" />
        </span>
        <span>
          <FacebookMark />
        </span>
        <span className={format.channel === "gmail" ? "is-on" : undefined}>
          <GmailMark />
        </span>
      </Piece>
    </>
  );
}

/* The knowledge base opens one client after another: the list, the pick,
   then that client's record. */
const CLIENTS = ["Miss Lyss Planning", "Dogwood Reserve", "The Elia"] as const;
const RECORD = [
  [Briefcase, "Client portfolio"],
  [PhoneCall, "Call Preparation"],
  [ListChecks, "Action Items"],
] as const;
const KNOWLEDGE_MS = [2400, 900, 3600] as const; // list, a client picked, its record

function KnowledgeArt() {
  const swapRef = useRef<HTMLDivElement>(null);
  const step = useLoop(KNOWLEDGE_MS, swapRef);
  const phase = step % 3;
  const client = Math.floor(step / 3) % CLIENTS.length;
  const open = phase === 2;
  return (
    <>
      <span className="v1-art-orbit" style={v({ "--l": 10, "--t": -4, "--s": 84 })} />
      <Piece className="v1-art-photo is-columns" at={[12.8, 2.6, 30.2, 23.6, -3, 2, 0.05]} />
      <Piece className="v1-art-panel v1-art-list" at={[24.2, 8.3, 64.7, 48.4, 0, 2.8, 0.15]}>
        <div ref={swapRef} className="v1-art-swap">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div key={open ? `record-${client}` : "clients"} className={`v1-art-view${open ? " is-record" : ""}`} {...SWAP}>
              {open ? (
                <>
                  <b>
                    <ChevronLeft className="v1-art-back" strokeWidth={2} />
                    {CLIENTS[client]}
                  </b>
                  {RECORD.map(([Icon, label], i) => (
                    <span key={label} className="v1-art-row" style={v({ "--d": `${0.08 + i * 0.08}s` })}>
                      <Icon strokeWidth={1.6} />
                      {label}
                      <ChevronRight className="v1-art-chev" strokeWidth={1.8} />
                    </span>
                  ))}
                </>
              ) : (
                <>
                  <b>
                    <i className="v1-art-glyph" />
                    Clients
                  </b>
                  {CLIENTS.map((name, i) => (
                    <span
                      key={name}
                      className={`v1-art-row${phase === 1 && i === client ? " is-picked" : ""}`}
                      style={v({ "--d": `${0.08 + i * 0.08}s` })}
                    >
                      <Folder strokeWidth={1.6} />
                      {name}
                      <ChevronRight className="v1-art-chev" strokeWidth={1.8} />
                    </span>
                  ))}
                </>
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </Piece>
      <Piece className="v1-art-note" at={[4.3, 26.2, 22, 31.3, -6, 3.8, 0.3]}>
        Client insights at your fingertips.
      </Piece>
    </>
  );
}

const BARS = [22, 30, 37, 50, 58, 74];
const LINE = [
  [30, 66],
  [54, 58],
  [78, 54],
  [102, 40],
  [126, 32],
  [150, 18],
  [168, 26],
  [182, 12],
  [194, 4],
];

function ReportingArt() {
  return (
    <>
      <span className="v1-art-orbit" style={v({ "--l": 4, "--t": -2, "--s": 92 })} />
      <Piece className="v1-art-flowers is-tall" at={[0.6, 4.8, 14, 58, 0, 1.2, 0]} />
      <Piece className="v1-art-flowers is-crown" at={[73.5, 6.3, 22, 21, 0, 1.2, 0.05]} />
      <Piece className="v1-art-panel v1-art-chart" at={[13.4, 6.3, 59.8, 41.3, 0, 2.4, 0.12]}>
        <b>
          <i className="v1-art-glyph" />
          Campaign Performance
        </b>
        <svg viewBox="0 0 200 104" aria-hidden>
          <defs>
            <linearGradient id="v1-bar" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#4d6cf5" />
              <stop offset="1" stopColor="#bccaff" stopOpacity="0.6" />
            </linearGradient>
          </defs>
          {["600", "500", "400", "300", "200", "100", "0"].map((label, i) => (
            <text key={label} x="2" y={14 + i * 13.4} className="v1-art-axis">
              {label}
            </text>
          ))}
          {BARS.map((h, i) => (
            <rect
              key={i}
              x={26 + i * 24}
              y={94 - h}
              width="9"
              height={h}
              rx="2"
              fill="url(#v1-bar)"
              className="v1-art-bar"
              style={v({ "--d": `${0.35 + i * 0.07}s` })}
            />
          ))}
          <polyline points={LINE.map((p) => p.join(",")).join(" ")} className="v1-art-trend" />
          {LINE.map(([x, y]) => (
            <circle key={x} cx={x} cy={y} r="2.3" className="v1-art-dot" />
          ))}
          {["Jan", "Feb", "Mar", "Apr", "May", "Jun"].map((m, i) => (
            <text key={m} x={30.5 + i * 24} y="102" className="v1-art-axis is-x">
              {m}
            </text>
          ))}
        </svg>
      </Piece>
      <Piece className="v1-art-flowers is-low" at={[10, 47, 38.5, 17, 0, 1.6, 0.1]} />
      <Piece className="v1-art-panel v1-art-roas" at={[47.6, 26.2, 44.7, 42.7, 0, 3.6, 0.28]}>
        <span className="v1-art-gauge">
          <svg viewBox="0 0 60 60" aria-hidden>
            <defs>
              <linearGradient id="v1-gauge" x1="0" y1="1" x2="1" y2="0">
                <stop offset="0" stopColor="#2f55f0" />
                <stop offset="1" stopColor="#b8c6ff" />
              </linearGradient>
            </defs>
            <circle cx="30" cy="30" r="24" className="v1-art-track" />
            <circle cx="30" cy="30" r="24" className="v1-art-arc" />
            <text x="30" y="27" className="v1-art-gauge-label">
              ROAS
            </text>
            <text x="30" y="39.5" className="v1-art-gauge-value">
              4.8x
            </text>
          </svg>
        </span>
        <ArrowUp className="v1-art-up" strokeWidth={2.2} />
        <ul>
          {(
            [
              [Globe, "Website Visits", "+42%"],
              [MessageCircle, "Inquiries", "+28%"],
              [CalendarCheck, "Bookings", "+18%"],
            ] as const
          ).map(([Icon, label, value], i) => (
            <li key={label} style={v({ "--d": `${0.75 + i * 0.1}s` })}>
              <Icon strokeWidth={1.7} />
              {label}
              <b>{value}</b>
            </li>
          ))}
        </ul>
      </Piece>
    </>
  );
}

const ART: Record<string, ComponentType> = {
  "content-atelier": AtelierArt,
  "client-knowledge-base": KnowledgeArt,
  "paid-media-reporting": ReportingArt,
};

export function CardArt({ id }: { id: string }) {
  const Art = ART[id];
  return (
    <div className="v1-auto-art" aria-hidden>
      {Art ? <Art /> : <span className="v1-art-orbit" style={v({ "--l": 8, "--t": -4, "--s": 84 })} />}
    </div>
  );
}
