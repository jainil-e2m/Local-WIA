import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowUpRight, Globe, Library, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

/* The three places the team actually works. One pill cycles through them
   rather than spending three buttons of hero real estate. */
const DESTINATIONS = [
  { label: "Website", href: "https://weddingindustryads.com", Icon: Globe },
  { label: "LeadLock", href: "https://app.leadlockpro.com/", Icon: Zap },
  /* lucide's `Vault` is the semantically obvious choice and the wrong one
     visually: it packs 10 child elements (a rect, five circles, four paths)
     into an 18px box at 2px stroke and renders as indistinct mush. Globe has
     3, Zap has 1. `Library` reads cleanly at this size and is apt anyway —
     the Vault is their members resource portal. */
  { label: "The Vault", href: "https://members.weddingindustryads.com/", Icon: Library },
] as const;

const ROTATE_MS = 3000;

/**
 * A pill that cycles through DESTINATIONS, with dots to jump straight to one.
 *
 * ── WHY IT IS NOT THE `ghost` BUTTON VARIANT ──────────────────────────────
 * It was, and it looked wrong: `ghost` is a bare outline built for a static
 * secondary CTA, and the shared button base applies uppercase with 0.14em
 * tracking. On a short word inside a pill whose width is pinned to the longest
 * label, that reads as a few sparse letters floating in an empty capsule. This
 * is a different KIND of control — a switcher, not a call to action — so it
 * gets a real surface, sentence-case type, an icon that identifies the
 * destination, and a glyph saying it leaves the app.
 *
 * ── WHY THE DOTS ARE CLICKABLE ────────────────────────────────────────────
 * A link whose target changes on a timer is hostile: you reach for one thing
 * and press another. Hover and focus pause the timer, and the dots let you go
 * straight to the destination you want instead of waiting for it to come
 * round. That turns it from something that happens TO you into a control.
 *
 * ── WHY THERE IS NO EXIT ANIMATION ────────────────────────────────────────
 * An earlier version used AnimatePresence with mode="wait", which keeps the
 * OUTGOING label mounted until its exit finishes while the href updates
 * immediately — measured live as label "Website" over href app.leadlockpro.com.
 * In a tab whose rAF is throttled the exit never completes and the label sticks
 * permanently out of sync. The swap is enter-only, so label, icon and href all
 * change in one React commit and can never disagree.
 */
/**
 * `tone` picks the surface. `default` is the white pill the sky hero uses;
 * `vault` is the marble landing's ivory pill with the metallic gold rim
 * (`.lux-cream` in index.css), bronze type and gold dots — the same control,
 * dressed for the navy-and-gold buttons it sits beside.
 */
export function RotatingDestination({ tone = "default" }: { tone?: "default" | "vault" }) {
  const vault = tone === "vault";
  const reduceMotion = useReducedMotion();
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  /* Bumped on every manual pick so the effect re-runs and the countdown starts
     over. Without it a tap lands with whatever was left on the clock: choose
     The Vault 200ms before a tick and it moves straight off again. A mouse is
     incidentally protected because hovering to click fires mouseenter and
     pauses — a touch user gets no hover, and would be overridden. */
  const [restartAt, setRestartAt] = useState(0);

  useEffect(() => {
    if (paused) return undefined;
    const id = window.setInterval(() => setIndex((i) => (i + 1) % DESTINATIONS.length), ROTATE_MS);
    return () => window.clearInterval(id);
  }, [paused, restartAt]);

  const pick = (i: number) => {
    setIndex(i);
    setRestartAt((n) => n + 1);
  };

  const current = DESTINATIONS[index];
  const { Icon } = current;

  /* Enter-only. Reduced motion crossfades rather than travelling. */
  const enter = reduceMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 } }
    : { initial: { y: 14, opacity: 0 }, animate: { y: 0, opacity: 1 } };

  return (
    <div
      /* `relative` with the dots taken out of flow below: the row this sits in
         is items-center, so a taller stack would push the pill above the
         primary CTA's centre line instead of sitting level with it. */
      className="relative inline-flex flex-col items-center"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <a
        href={current.href}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={`Open ${current.label} in a new tab`}
        className={cn(
          "group inline-flex items-center rounded-full transition-all duration-300 hover:-translate-y-0.5",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-2",
          vault
            ? "lux-cream h-[46px] gap-2 pl-[20px] pr-[18px]"
            : cn(
                "h-14 gap-3 border-2 border-brand-mist bg-white pl-6 pr-5 shadow-[0_10px_30px_-16px_rgba(34,30,23,0.28)]",
                "hover:border-brand-stone hover:shadow-[0_16px_36px_-16px_rgba(34,30,23,0.34)]",
              ),
        )}
      >
        {/* Grid-stacks every label so the pill sizes to the LONGEST one and
            never resizes mid-rotation. Hidden copies lay out but are not
            announced.

            The consequence, and why the label is centred: the cell is as wide
            as "LeadLock" / "The Vault", so a shorter label like "Website"
            leaves slack. Left-aligned, all of that slack piled up after the
            text and opened a gap before the arrow. `flex-1 text-center` on the
            label spreads it evenly instead, so the word sits centred between
            the destination icon and the arrow at every width. */}
        <span className="grid flex-1">
          {DESTINATIONS.map((d) => (
            <span
              key={d.label}
              className={cn(
                "invisible col-start-1 row-start-1 flex items-center",
                vault ? "gap-2.5 text-[13px] font-medium" : "gap-3 text-[15px] font-semibold",
              )}
              aria-hidden
            >
              <d.Icon
                className={cn("shrink-0", vault ? "h-[15px] w-[15px]" : "h-[18px] w-[18px]")}
              />
              <span className="flex-1 text-center">{d.label}</span>
            </span>
          ))}
          <motion.span
            /* Keying on the index remounts the row, replaying the entrance.
               Nothing outlives the state change it belongs to. */
            key={index}
            className={cn(
              "col-start-1 row-start-1 flex items-center",
              vault
                ? "gap-2.5 text-[13px] font-medium text-[#9a6a2c]"
                : "gap-3 text-[15px] font-semibold text-brand-ink",
            )}
            initial={enter.initial}
            animate={enter.animate}
            transition={{ duration: 0.34, ease: [0.22, 1, 0.36, 1] }}
          >
            <Icon
              className={cn(
                "shrink-0",
                vault ? "h-[15px] w-[15px] text-[#b8955c]" : "h-[18px] w-[18px] text-brand-primary",
              )}
              strokeWidth={vault ? 1.6 : 2}
              aria-hidden
            />
            <span className="flex-1 text-center">{current.label}</span>
          </motion.span>
        </span>

        <ArrowUpRight
          className={cn(
            "shrink-0 transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5",
            vault
              ? "ml-0.5 h-3 w-3 text-[#b8955c] group-hover:text-[#9a6a2c]"
              : "h-4 w-4 text-brand-slate group-hover:text-brand-primary",
          )}
          strokeWidth={vault ? 1.8 : 2}
          aria-hidden
        />
      </a>

      {/* Jump straight to a destination instead of waiting for it. */}
      <div
        className={cn("absolute flex items-center gap-1.5", vault ? "-bottom-[11px]" : "-bottom-4")}
      >
        {DESTINATIONS.map((d, i) => (
          <button
            key={d.label}
            type="button"
            onClick={() => pick(i)}
            aria-label={`Show ${d.label}`}
            aria-current={i === index}
            className={cn(
              "rounded-full transition-all duration-300",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-2",
              vault
                ? i === index
                  ? "h-1 w-4 bg-[#c9a15e]"
                  : "h-1 w-1 bg-[#e3d2b2] hover:bg-[#c9a15e]"
                : i === index
                  ? "h-1.5 w-6 bg-brand-primary"
                  : "h-1.5 w-1.5 bg-brand-stone hover:bg-brand-secondary",
            )}
          />
        ))}
      </div>
    </div>
  );
}
