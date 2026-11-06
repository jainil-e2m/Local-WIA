import { useMemo, useRef, useState } from "react";
import {
  motion,
  useInView,
  useMotionValue,
  useSpring,
  useReducedMotion,
  type Variants,
} from "framer-motion";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, LayoutDashboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Magnetic } from "@/components/Magnetic";
import { HeroVisual } from "@/components/HeroVisual";
import { BirdsSky } from "@/components/BirdsSky";
import { AutomationsModal } from "@/components/AutomationsModal";
import { RotatingDestination } from "@/components/RotatingDestination";
import { greeting } from "@/lib/greeting";
import { useCountUp } from "@/hooks/useCountUp";
import { resolveTimelineView } from "@/data/timeline";
import { accountName } from "@/data/user";
import { useAuth } from "@/context/auth";

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


export function Hero() {
  // Greet the signed-in user by first name. Signed out — or while the session
  // is still resolving — the greeting stands alone with no name appended, so a
  // visitor is never addressed by a placeholder that isn't them.
  const { status, user } = useAuth();
  const reduce = useReducedMotion();
  const [launcherOpen, setLauncherOpen] = useState(false);

  // Cursor-driven background spotlight (content itself never moves)
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const spotX = useSpring(mx, { stiffness: 120, damping: 25 });
  const spotY = useSpring(my, { stiffness: 120, damping: 25 });

  /* THREE LANDINGS OFF ONE COMPONENT, chosen by `?variant=`:

       classic   sky loop + the bouquet asset in a right column, copy
                 left-aligned. Was the default; a bare `/` now renders
                 MarbleHero instead (App.tsx routes these variants here).
       sky       sky loop, NO orbital asset, copy centred in a single column.
       gradient  the original gradient/grid/orb hero, kept reachable rather
                 than deleted so it is still the fallback if the loop ever has
                 to come out.

     `birds` is tested as `!== "gradient"` rather than `=== "birds"` so old
     `?variant=birds` links keep working and `sky` inherits the loop for free:
     anything that is not an explicit opt-out gets the sky.

     `centered` is what `sky` actually buys. Dropping the asset leaves the
     right-hand grid column empty, and left-aligned copy against 700px of dead
     space reads as a broken layout rather than a deliberate one — so the grid
     collapses to one column and every block centres with it. */
  const [searchParams] = useSearchParams();
  const variant = searchParams.get("variant");
  const birds = variant !== "gradient";
  const centered = variant === "sky";

  function onMouseMove(e: React.MouseEvent<HTMLElement>) {
    if (reduce) return;
    const { innerWidth, innerHeight } = window;
    mx.set(e.clientX - innerWidth / 2);
    my.set(e.clientY - innerHeight / 2);
  }

  const particles = useMemo(
    () =>
      Array.from({ length: 18 }, (_, i) => ({
        id: i,
        left: (i * 53) % 100,
        top: (i * 37) % 100,
        size: 2 + ((i * 7) % 5),
        delay: (i % 6) * 0.8,
        duration: 7 + ((i * 3) % 8),
      })),
    [],
  );

  /* Counters track the build timeline — which is the Blueprint roadmap, row
     for row (see data/timeline.ts) — not this app's tool catalogue. The row
     advances by itself as the plan progresses.

     THE LABELS ARE DELIBERATE. Nothing in this engagement is running in
     production yet, so the delivered tally is labelled "Demoed at review"
     rather than the old "Live now": the three pinned rows are consoles walked
     through at the blueprint review, and calling them live would be a claim
     this hub cannot support. "Consoles built" is the fourth figure — it counts
     the mock surfaces in this app, including the AI Operations Hub, which is not
     an automation and so is excluded from `total` above.

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
    <section
      id="top"
      onMouseMove={onMouseMove}
      className="bg-hero relative flex min-h-[100svh] items-center overflow-hidden px-6 pb-4 pt-[112px] text-black"
    >
      {/* ── Background layers ─────────────────────────────── */}
      <div className="pointer-events-none absolute inset-0" aria-hidden>
        {/* sky loop — first child so every other layer paints above it, and
            those layers are gated off below so nothing draws on the clouds */}
        {birds && <BirdsSky />}

        {/* fading grid */}
        {!birds && <div className="hero-grid absolute inset-0" />}

        {/* Orbs, particles and the cursor spotlight are all tints over the
            gradient. Over the sky loop they would colour the clouds, so the
            default drops them wholesale rather than dimming them. They return
            with `?variant=gradient`. */}
        {!birds && (
          <>
            {/* aurora orbs */}
            <motion.div
              className="absolute -right-32 -top-40 h-[560px] w-[560px] rounded-full blur-[70px]"
              style={{ background: "radial-gradient(circle, #8da1fd, transparent 65%)", opacity: 0.3 }}
              animate={reduce ? undefined : { x: [0, -70, 0], y: [0, 60, 0], scale: [1, 1.12, 1] }}
              transition={{ duration: 17, repeat: Infinity, ease: "easeInOut" }}
            />
            <motion.div
              className="absolute -bottom-44 -left-36 h-[480px] w-[480px] rounded-full blur-[70px]"
              style={{ background: "radial-gradient(circle, #c39878, transparent 65%)", opacity: 0.24 }}
              animate={reduce ? undefined : { x: [0, 80, 0], y: [0, -50, 0], scale: [1, 1.08, 1] }}
              transition={{ duration: 21, repeat: Infinity, ease: "easeInOut" }}
            />
            <motion.div
              className="absolute left-[54%] top-[30%] h-[320px] w-[320px] rounded-full blur-[64px]"
              style={{
                background: "radial-gradient(circle, rgba(80,112,255,0.5), transparent 68%)",
                opacity: 0.14,
              }}
              animate={reduce ? undefined : { x: [0, -60, 0], y: [0, -70, 0], scale: [1, 1.16, 1] }}
              transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
            />

            {/* floating particles */}
            {particles.map((p) => (
              <motion.span
                key={p.id}
                className="absolute rounded-full bg-brand-slate/45"
                style={{ left: `${p.left}%`, top: `${p.top}%`, width: p.size, height: p.size }}
                animate={reduce ? { opacity: 0.25 } : { y: [0, -34, 0], opacity: [0, 0.8, 0] }}
                transition={{
                  duration: p.duration,
                  delay: p.delay,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
              />
            ))}

            {/* cursor spotlight */}
            <motion.div
              className="absolute left-1/2 top-1/2 h-[640px] w-[640px] rounded-full blur-2xl"
              style={{
                x: spotX,
                y: spotY,
                translateX: "-50%",
                translateY: "-50%",
                background: "radial-gradient(circle, rgba(80,112,255,0.1), transparent 60%)",
              }}
            />
          </>
        )}
      </div>

      {/* ── Content ───────────────────────────────────────── */}
      <div
        className={cn(
          "container relative z-10 grid items-center gap-12",
          !centered &&
            "lg:grid-cols-[minmax(0,1fr)_minmax(0,440px)] xl:grid-cols-[minmax(0,1fr)_minmax(0,560px)]",
        )}
      >
        <div className={cn(centered && "mx-auto max-w-3xl text-center")}>
          {/* eyebrow — name comes from the logged-in user placeholder.
              data-hero-band-start: the bookmarks island sizes itself to the
              band between this line and the KPI row (data-hero-band-end). */}
          <motion.p
            data-hero-band-start
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

          {/* AI Operations Hub — centred under the two actions above, because it
              is a third KIND of destination rather than a third option of the
              same kind: not a tool launcher and not an external link, but a
              whole console. Internal route, so it uses Link rather than the
              external-link treatment RotatingDestination carries. */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 1.45 }}
            className={cn(
              "mt-6 flex max-w-xl flex-col items-center gap-2",
              centered && "mx-auto",
            )}
          >
            <Magnetic strength={0.2}>
              <Button asChild variant="solid" size="lg">
                <Link to="/ops-hub">
                  <LayoutDashboard className="h-[18px] w-[18px]" />
                  AI Operations Hub
                </Link>
              </Button>
            </Magnetic>
            <p className="text-[12px] text-brand-gray">
              Attention, context and approval across every connected source
            </p>
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
      data-hero-band-end
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
