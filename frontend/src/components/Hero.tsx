import { useEffect, useRef, useState } from "react";
import {
  motion,
  useInView,
  useReducedMotion,
  type Variants,
} from "framer-motion";
import {
  ArrowRight,
  ArrowUpRight,
  Globe,
  Library,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Magnetic } from "@/components/Magnetic";
import { HeroVisual } from "@/components/HeroVisual";
import { HeroMarble } from "@/components/HeroMarble";
import { AutomationsModal } from "@/components/AutomationsModal";
import { useCountUp } from "@/hooks/useCountUp";
import { resolveTimelineView } from "@/data/timeline";
import { accountName } from "@/data/user";
import { useAuth } from "@/context/auth";

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
function RotatingDestination() {
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
    const id = window.setInterval(
      () => setIndex((i) => (i + 1) % DESTINATIONS.length),
      ROTATE_MS,
    );
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
          "group inline-flex h-14 items-center gap-3 rounded-full border-2 border-brand-mist",
          "bg-white pl-6 pr-5 shadow-[0_10px_30px_-16px_rgba(34,30,23,0.28)]",
          "transition-all duration-300 hover:-translate-y-0.5 hover:border-brand-stone",
          "hover:shadow-[0_16px_36px_-16px_rgba(34,30,23,0.34)]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-2",
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
              className="invisible col-start-1 row-start-1 flex items-center gap-3 text-[15px] font-semibold"
              aria-hidden
            >
              <d.Icon className="h-[18px] w-[18px] shrink-0" />
              <span className="flex-1 text-center">{d.label}</span>
            </span>
          ))}
          <motion.span
            /* Keying on the index remounts the row, replaying the entrance.
               Nothing outlives the state change it belongs to. */
            key={index}
            className="col-start-1 row-start-1 flex items-center gap-3 text-[15px] font-semibold text-brand-ink"
            initial={enter.initial}
            animate={enter.animate}
            transition={{ duration: 0.34, ease: [0.22, 1, 0.36, 1] }}
          >
            <Icon className="h-[18px] w-[18px] shrink-0 text-brand-primary" aria-hidden />
            <span className="flex-1 text-center">{current.label}</span>
          </motion.span>
        </span>

        <ArrowUpRight
          className="h-4 w-4 shrink-0 text-brand-slate transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-brand-primary"
          aria-hidden
        />
      </a>

      {/* Jump straight to a destination instead of waiting for it. */}
      <div className="absolute -bottom-4 flex items-center gap-1.5">
        {DESTINATIONS.map((d, i) => (
          <button
            key={d.label}
            type="button"
            onClick={() => pick(i)}
            aria-label={`Show ${d.label}`}
            aria-current={i === index}
            className={cn(
              "h-1.5 rounded-full transition-all duration-300",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-2",
              i === index
                ? "w-6 bg-brand-primary"
                : "w-1.5 bg-brand-stone hover:bg-brand-secondary",
            )}
          />
        ))}
      </div>
    </div>
  );
}


const LINE_1 = "Your growth stack,".split(" ");
const LINE_2 = "ONE SINGLE HUB".split(" ");

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.5 } },
};
const word: Variants = {
  hidden: { y: "115%" },
  show: { y: 0, transition: { duration: 0.85, ease: [0.22, 1, 0.36, 1] } },
};

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export function Hero() {
  // Greet the signed-in user by first name. Signed out — or while the session
  // is still resolving — the greeting stands alone with no name appended, so a
  // visitor is never addressed by a placeholder that isn't them.
  const { status, user } = useAuth();
  const [launcherOpen, setLauncherOpen] = useState(false);
  const centered = false;

  /* Counters track the build timeline — which is the Blueprint roadmap, row
     for row (see data/timeline.ts) — not this app's tool catalogue. The row
     advances by itself as the plan progresses.

     THE LABELS ARE DELIBERATE. Nothing in this engagement is running in
     production yet, so the delivered tally is labelled "Demoed at review"
     rather than the old "Live now": the three pinned rows are consoles walked
     through at the blueprint review, and calling them live would be a claim
     this hub cannot support. "Consoles built" includes the AI Operations Hub
     walkthrough from the blueprint review.

     Still read through resolveTimelineView rather than counting anything
     locally. The timeline board is no longer reachable from the hero, but the
     resolver remains the single source for these tallies. */
  const { total, delivered, inDevelopment } = resolveTimelineView().tally;
  const stats = [
    { label: "Roadmap automations", value: total },
    { label: "Demoed at review", value: delivered },
    { label: "In the build queue", value: inDevelopment },
    { label: "Consoles built", text: "4" },
  ];

  return (
    <section id="top" className="bg-hero relative flex min-h-[100svh] items-center overflow-hidden px-6 pb-4 pt-[112px] text-black">
      {/* ── Background layers ─────────────────────────────── */}
      <HeroMarble />

      {/* ── Content ───────────────────────────────────────── */}
      <div className="container relative z-10 grid items-center gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,440px)] xl:grid-cols-[minmax(0,1fr)_minmax(0,560px)]">
        <div>
          {/* eyebrow — name comes from the logged-in user placeholder. */}
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.35 }}
            className={cn(
              "mb-2 flex items-center gap-4 text-[13px] font-bold uppercase tracking-[0.32em] text-brand-secondary",
              centered && "justify-center",
            )}
          >
            {/* The rule grows from its left edge, which only reads correctly
                against left-aligned copy. Centred, it would need a mirrored
                twin to look intentional, so it is dropped instead. */}
            {!centered && (
              <motion.span
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: 0.7, delay: 0.6, ease: [0.22, 1, 0.36, 1] }}
                className="hidden h-0.5 w-12 origin-left bg-brand-primary sm:block"
              />
            )}
            {greeting()}
            {status === "authenticated" && user?.name ? ` · ${accountName(user.name)}` : null}
          </motion.p>

          {/* date, moved here from the header */}
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.5 }}
            className={cn(
              "mb-[52px] text-sm font-medium text-brand-gray",
              /* The indent aligns this under the eyebrow's text, clearing the
                 rule. No rule when centred, so no indent. */
              !centered && "sm:pl-16",
            )}
          >
            {new Date().toLocaleDateString("en-US", {
              weekday: "long",
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </motion.p>

          {/* headline */}
          <motion.h1
            variants={container}
            initial="hidden"
            animate="show"
            className={cn(
              "text-[clamp(2.9rem,7.2vw,5.75rem)] font-extrabold leading-[1.02] tracking-[-0.02em] lg:text-[clamp(2.5rem,3.9vw,3.9rem)]",
              centered ? "mx-auto max-w-[24ch]" : "max-w-[16ch] xl:max-w-none",
            )}
          >
            <span className={cn("flex flex-wrap", centered && "justify-center")}>
              {LINE_1.map((w, i) => (
                <span key={i} className="mr-[0.26em] inline-block overflow-hidden pb-[0.12em]">
                  <motion.span variants={word} className="inline-block">
                    {w}
                  </motion.span>
                </span>
              ))}
            </span>
            <span className={cn("flex flex-wrap", centered && "justify-center")}>
              {LINE_2.map((w, i) => (
                <span key={i} className="mr-[0.26em] inline-block overflow-hidden pb-[0.12em]">
                  <motion.span
                    variants={word}
                    className="text-gradient-brand inline-block animate-shimmer"
                  >
                    {w}
                  </motion.span>
                </span>
              ))}
            </span>
          </motion.h1>

          {/* subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 1.15 }}
            className={cn("mt-8 max-w-xl text-lg text-brand-secondary", centered && "mx-auto")}
          >
            Every automation on your roadmap lives here — the consoles we&rsquo;ve built,
            and what is queued behind them.
          </motion.p>

          {/* actions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 1.3 }}
            className={cn(
              "mt-11 flex flex-wrap items-center gap-4",
              centered && "justify-center",
            )}
          >
            <Magnetic>
              <Button variant="primary" size="lg" onClick={() => setLauncherOpen(true)}>
                View automations
                <ArrowRight className="h-[18px] w-[18px]" />
              </Button>
            </Magnetic>
            <Magnetic strength={0.2}>
              <RotatingDestination />
            </Magnetic>
          </motion.div>

          {/* stats */}
          <StatsRow stats={stats} centered={centered} />
        </div>

        {/* orbital asset — own column on the right, no text overlaps it.
            Omitted entirely on `?variant=sky`: that variant exists to drop it,
            and rendering an empty grid cell would reintroduce the offset the
            centring is there to remove. */}
        {!centered && (
          <div className="hidden lg:block">
            <HeroVisual />
          </div>
        )}
      </div>

      {/* bottom fade */}
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 h-36 bg-gradient-to-b from-transparent to-[#e0dfe2]"
        aria-hidden
      />

      {/* automation launcher overlay */}
      <AutomationsModal open={launcherOpen} onClose={() => setLauncherOpen(false)} />
    </section>
  );
}

function StatsRow({
  stats,
  centered = false,
}: {
  stats: Array<{ label: string; value?: number; text?: string }>;
  centered?: boolean;
}) {
  const ref = useRef<HTMLDListElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.6 });

  return (
    <motion.dl
      ref={ref}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 1.45 }}
      className={cn(
        "mt-28 grid grid-cols-2 gap-x-6 gap-y-8 border-t border-brand-mist pt-9",
        centered
          ? /* Four even columns rather than the default's `justify-between`:
               spread apart across a centred measure the figures stop reading
               as one row. */
            "sm:grid-cols-4 justify-items-center"
          : "md:grid-cols-[auto_auto_auto_auto] md:justify-between lg:grid-cols-2 lg:justify-normal xl:grid-cols-[auto_auto_auto_auto] xl:justify-between",
      )}
    >
      {stats.map((s) => (
        <div key={s.label}>
          <dt className="mb-1.5 whitespace-nowrap text-[12.5px] font-semibold uppercase tracking-[0.2em] text-brand-gray">
            {s.label}
          </dt>
          <dd className="text-4xl font-extrabold tabular-nums text-brand-accent md:text-[40px]">
            {s.text ?? <Counter target={s.value ?? 0} active={inView} />}
          </dd>
        </div>
      ))}
    </motion.dl>
  );
}

function Counter({ target, active }: { target: number; active: boolean }) {
  return <>{useCountUp(target, active)}</>;
}
