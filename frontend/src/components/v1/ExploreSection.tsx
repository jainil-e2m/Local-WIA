import { useCallback, useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowUpRight, Search, X } from "lucide-react";
import { useDismiss } from "@/hooks/useDismiss";
import { deployedAtelierUrl } from "@/lib/atelierLaunch";
import { EXTERNAL } from "./destinations";
import { WiaMark } from "./WiaMark";
import { LIBRARY, type LibraryItem } from "./library/automations";
import { Tile } from "./library/Tile";
import { LibraryOrbits } from "./library/Orbits";

/* ────────────────────────────────────────────────────────────────
   Below the hero — the automation library, laid out as a gallery.

   The automations in a grid of three: ivory cards, each with a collage of
   what it does, its status (live or coming soon) and the way in. The
   chips filter by area and the search box by anything on the card.
   ──────────────────────────────────────────────────────────────── */

const EASE = [0.22, 1, 0.36, 1] as const;

/* Each tile rises into place as it scrolls into view, staggered across
   its row of three. */
const tileIn = {
  hidden: { opacity: 0, y: 70, rotateX: 12 },
  show: (col: number) => ({ opacity: 1, y: 0, rotateX: 0, transition: { duration: 1.1, delay: col * 0.1, ease: EASE } }),
};

const lineIn = {
  hidden: { y: "105%" },
  show: (i: number) => ({ y: "0%", transition: { duration: 1.05, delay: 0.1 + i * 0.12, ease: EASE } }),
};

export function ExploreSection() {
  const items = LIBRARY;
  const atelierUrl = deployedAtelierUrl();

  return (
    <section id="v1-explore" className="v1-lib" aria-labelledby="v1-explore-title">
      <div className="v1-lib-backdrop" aria-hidden>
        <LibraryOrbits />
      </div>

      <header className="v1-lib-head">
        <motion.p
          className="v1-lib-eyebrow"
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.6 }}
          transition={{ duration: 0.9, ease: EASE }}
        >
          <span className="v1-greeting-dot" aria-hidden />
          Inside the Command Center
        </motion.p>
        <div className="v1-lib-titlebar">
          <motion.h2
            id="v1-explore-title"
            className="v1-lib-title"
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.5 }}
          >
            <span className="v1-lib-line">
              <motion.em custom={0} variants={lineIn}>
                Automation Library
              </motion.em>
            </span>
          </motion.h2>
          <InfoTip label="About the Automation Library">
            Plug in proven automations to save time, delight clients, and grow your business — all built for the wedding
            industry.
          </InfoTip>
        </div>
      </header>

      <Gallery items={items} atelierUrl={atelierUrl} />

      <footer className="v1-footer">
        <div className="v1-footer-inner">
          <WiaMark className="h-12 w-12 text-[#1b2540]" title="Wedding Industry Ads" />
          <p className="v1-footer-line">
            <span className="v1-tagline-rule" aria-hidden />
            Building a stronger wedding industry
          </p>
          <nav className="v1-footer-links" aria-label="Elsewhere">
            {EXTERNAL.map((e) => (
              <a key={e.id} href={e.href} target="_blank" rel="noopener noreferrer">
                {e.label}
                <ArrowUpRight className="h-[12px] w-[12px]" strokeWidth={1.8} aria-hidden />
              </a>
            ))}
          </nav>
        </div>
      </footer>
    </section>
  );
}

const ALL = "All";

/** The filter chips and the search, then the grid of cards. */
function Gallery({ items, atelierUrl }: { items: readonly LibraryItem[]; atelierUrl?: string }) {
  const reduce = useReducedMotion() ?? false;
  const tileRefs = useRef(new Map<string, HTMLLIElement>());
  const [filter, setFilter] = useState(ALL);
  const [query, setQuery] = useState("");
  const [seen, setSeen] = useState<ReadonlySet<string>>(new Set());
  const [observing, setObserving] = useState(false);
  const categories = useMemo(() => [ALL, ...new Set(items.map((i) => i.category))], [items]);
  const q = query.trim().toLowerCase();
  const shown = items.filter(
    (i) =>
      (filter === ALL || i.category === filter) &&
      (!q || [i.name, i.description, i.category, i.status].some((t) => t.toLowerCase().includes(q))),
  );

  /* Each card's collage assembles the first time most of it is on screen.
     Until something is watching, the cards simply show finished. */
  useEffect(() => {
    if (reduce || typeof IntersectionObserver === "undefined") return undefined;
    setObserving(true);
    const io = new IntersectionObserver(
      (entries) => {
        const ids = entries.filter((e) => e.isIntersecting).map((e) => (e.target as HTMLElement).dataset.id ?? "");
        if (ids.length) setSeen((prev) => new Set([...prev, ...ids]));
      },
      { threshold: 0.45 },
    );
    tileRefs.current.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [shown.length, filter, q, reduce]);

  return (
    <div className={`v1-shelf${observing ? " is-staged" : ""}`} role="group" aria-label="Automations">
      <div className="v1-shelf-bar">
        <div className="v1-shelf-chips" aria-label="Filter automations">
          {categories.map((c) => (
            <button
              key={c}
              type="button"
              className={`v1-chip${c === filter ? " is-on" : ""}`}
              aria-pressed={c === filter}
              onClick={() => setFilter(c)}
            >
              {c}
            </button>
          ))}
        </div>
        <span className="v1-shelf-rule" aria-hidden />
        <label className="v1-search">
          <Search aria-hidden strokeWidth={1.9} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search automations..."
            aria-label="Search automations"
          />
        </label>
      </div>

      {shown.length === 0 && (
        <p className="v1-shelf-empty" role="status">
          No automations match{q ? <> &ldquo;{query.trim()}&rdquo;</> : null}.
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setFilter(ALL);
            }}
          >
            <X aria-hidden strokeWidth={1.8} />
            Clear
          </button>
        </p>
      )}

      <motion.ol className="v1-shelf-grid" layout={!reduce}>
        <AnimatePresence initial={false}>
          {shown.map((item, i) => (
            <motion.li
              key={item.id}
              ref={(el) => {
                if (el) tileRefs.current.set(item.id, el);
                else tileRefs.current.delete(item.id);
              }}
              data-id={item.id}
              className="v1-shelf-item"
              layout={!reduce}
              custom={i % 3}
              variants={tileIn}
              initial={reduce ? false : "hidden"}
              whileInView="show"
              viewport={{ once: true, amount: 0.25 }}
              exit={{ opacity: 0, scale: 0.94, transition: { duration: 0.25 } }}
            >
              <Tile item={item} index={items.indexOf(item)} playing={seen.has(item.id)} atelierUrl={atelierUrl} />
            </motion.li>
          ))}
        </AnimatePresence>
      </motion.ol>
    </div>
  );
}

/** A navy "i" beside a heading whose note shows on hover or focus, and on a
    tap for touch screens. The note is the button's description, so it is
    read out whether or not it is showing. */
function InfoTip({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  const rootRef = useDismiss<HTMLSpanElement>(open, close);
  const tipId = useId();
  return (
    <span ref={rootRef} className={`v1-infotip${open ? " is-open" : ""}`}>
      <button
        type="button"
        className="v1-infotip-button"
        aria-label={label}
        aria-describedby={tipId}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span aria-hidden>i</span>
      </button>
      <span id={tipId} role="tooltip" className="v1-infotip-note">
        {children}
      </span>
    </span>
  );
}
