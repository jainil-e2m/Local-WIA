import { useRef, useState } from "react";
import { motion, useInView, type Variants } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Magnetic } from "@/components/Magnetic";
import { AutomationsModal } from "@/components/AutomationsModal";
import { RotatingDestination } from "@/components/RotatingDestination";
import { MarbleVeins } from "@/components/marble/MarbleVeins";
import { BouquetVideo } from "@/components/bouquet/BouquetVideo";
import { greeting } from "@/lib/greeting";
import { useCountUp } from "@/hooks/useCountUp";
import { resolveTimelineView } from "@/data/timeline";
import { accountName } from "@/data/user";
import { useAuth } from "@/context/auth";

/**
 * The marble landing — the DEFAULT hero at a bare `/`.
 *
 * A translation of the delivered design (white ground, cobalt-veined marble
 * on the right, a tied bouquet over it, a blurred fern in the corner,
 * navy-and-gold buttons). The design's round posy in the centre was removed
 * at the owner's request, and the still bouquet was replaced by a turning
 * one with falling petals (bouquet/BouquetVideo.tsx). Positions and type
 * sizes are the design's, measured at its 1566px capture width; the florals
 * are placed off the viewport centre, which is what keeps them clear of the
 * copy column at every width the 1220px shell is centred.
 *
 * The marble lives only in the right-hand region the owner marked out — from
 * 46% of the hero's width to its right edge, top to bottom — and dissolves in
 * from that region's left edge without ever crossing it. Its veins are live
 * (marble/MarbleVeins.tsx). Below 1100px the copy spans the whole width, so the
 * marble and the florals are both dropped rather than run behind the text.
 *
 * The previous heroes are still reachable through `?variant=` (see App.tsx).
 */

const LINE_1 = "Your growth stack,".split(" ");
const LINE_2 = "ONE SINGLE HUB".split(" ");

const headline: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.45 } },
};
const word: Variants = {
  hidden: { y: "110%" },
  show: { y: 0, transition: { duration: 0.85, ease: [0.22, 1, 0.36, 1] } },
};

const rise = (delay: number) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.75, delay, ease: [0.22, 1, 0.36, 1] as const },
});

function Marble() {
  return (
    <div className="landing-marble" aria-hidden>
      <MarbleVeins />
    </div>
  );
}

const PETALS = [
  { left: "calc(50% + 172px)", top: 452, w: 18, h: 12, r: -30 },
  { left: "calc(50% + 512px)", top: 586, w: 14, h: 10, r: 20 },
  { left: "calc(50% + 556px)", top: 655, w: 28, h: 18, r: -15 },
  { left: "calc(50% + 712px)", top: 372, w: 12, h: 9, r: 40 },
  { left: "calc(50% + 400px)", top: 630, w: 8, h: 6, r: 0 },
];

function Florals() {
  return (
    <div
      className="pointer-events-none absolute inset-0 z-[1] hidden min-[1100px]:block"
      aria-hidden
    >
      <img src="/landing/fern.webp" alt="" decoding="async" className="landing-fern-far" />
      <motion.div
        className="landing-bouquet"
        initial={{ opacity: 0, y: 22, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 1.2, delay: 0.85, ease: [0.22, 1, 0.36, 1] }}
      >
        <BouquetVideo />
      </motion.div>
      <img src="/landing/fern.webp" alt="" decoding="async" className="landing-fern-near" />
      {PETALS.map((p, i) => (
        <motion.span
          key={i}
          className="landing-petal"
          style={{ left: p.left, top: p.top, width: p.w, height: p.h, rotate: p.r }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 1.3 + i * 0.08 }}
        />
      ))}
    </div>
  );
}

export function MarbleHero() {
  // Greet the signed-in user by name. Signed out — or while the session is
  // still resolving — the greeting stands alone, so a visitor is never
  // addressed by a placeholder that isn't them.
  const { status, user } = useAuth();
  const [launcherOpen, setLauncherOpen] = useState(false);

  /* Counters track the build timeline (the Blueprint roadmap), read through
     resolveTimelineView exactly as the previous hero did — see the label
     rationale there. "Consoles built" counts the mock surfaces in this app. */
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
      className="relative isolate min-h-[max(100svh,775px)] overflow-hidden bg-[#f5f7fb] text-[#1d1f2b]"
    >
      <Marble />
      <Florals />

      {/* 52px clears the fixed header, which shares this shell. */}
      <div className="landing-shell relative z-[2] pb-16 pt-[52px]">
        <motion.p
          {...rise(0.3)}
          className="mt-[66px] flex items-center gap-[14px] text-[11px] font-medium uppercase leading-[14px] tracking-[0.32em] text-[#23252f]"
        >
          <motion.span
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.7, delay: 0.55, ease: [0.22, 1, 0.36, 1] }}
            className="h-[1.2px] w-[38px] shrink-0 origin-left bg-[#23252f]"
          />
          <span>
            {greeting()}
            {status === "authenticated" && user?.name ? ` · ${accountName(user.name)}` : null}
          </span>
        </motion.p>

        <motion.p
          {...rise(0.42)}
          className="ml-[52px] mt-[10px] text-[12.5px] leading-[16px] text-[#5c6baf]"
        >
          {new Date().toLocaleDateString("en-US", {
            weekday: "long",
            month: "long",
            day: "numeric",
            year: "numeric",
          })}
        </motion.p>

        <motion.h1
          variants={headline}
          initial="hidden"
          animate="show"
          className="mt-[38px] text-[clamp(2.25rem,7vw,51px)] font-bold leading-[1.12] tracking-[-0.016em] text-[#5b78f6]"
        >
          {[LINE_1, LINE_2].map((line, li) => (
            <span key={li} className="flex flex-wrap">
              {line.map((w, i) => (
                /* The overflow mask is what the words rise out of. Its padding
                   keeps descenders unclipped; the matching negative margin
                   keeps the line box at exactly 1.1. */
                <span
                  key={i}
                  className="-mb-[0.12em] mr-[0.25em] inline-block overflow-hidden pb-[0.12em] last:mr-0"
                >
                  <motion.span variants={word} className="inline-block">
                    {w}
                  </motion.span>
                </span>
              ))}
            </span>
          ))}
        </motion.h1>

        <motion.p
          {...rise(1.05)}
          className="mt-[30px] max-w-[440px] text-[14.75px] leading-[1.54] text-[#34363f]"
        >
          Every automation on your roadmap lives here — the consoles we&rsquo;ve built, and what is
          queued behind them.
        </motion.p>

        <motion.div {...rise(1.2)} className="mt-[38px] w-full max-w-[466px]">
          <div className="flex flex-wrap items-center gap-[14px]">
            <Magnetic strength={0.2}>
              <button
                type="button"
                onClick={() => setLauncherOpen(true)}
                className="lux-navy gap-3 px-[30px]"
              >
                View automations
                <ArrowRight className="h-[15px] w-[15px]" strokeWidth={2} aria-hidden />
              </button>
            </Magnetic>
            <Magnetic strength={0.2}>
              <RotatingDestination tone="vault" />
            </Magnetic>
          </div>
        </motion.div>

        <StatsRow stats={stats} />
      </div>

      <AutomationsModal open={launcherOpen} onClose={() => setLauncherOpen(false)} />
    </section>
  );
}

function StatsRow({ stats }: { stats: Array<{ label: string; value?: number; text?: string }> }) {
  const ref = useRef<HTMLDListElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.6 });

  return (
    <motion.dl
      ref={ref}
      {...rise(1.35)}
      className={cn(
        "mt-[90px] grid w-full max-w-[726px] grid-cols-2 gap-x-6 gap-y-7 border-t border-[#dfe0ea] pt-[30px]",
        "md:flex md:justify-between",
      )}
    >
      {stats.map((s) => (
        <div key={s.label}>
          <dt className="whitespace-nowrap text-[11px] font-medium uppercase leading-[14px] tracking-[0.13em] text-[#6f7fe0]">
            {s.label}
          </dt>
          <dd className="mt-[6px] text-[34px] font-bold leading-[1.1] tabular-nums text-[#5b73ec]">
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
