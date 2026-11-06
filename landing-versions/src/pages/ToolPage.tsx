import { useEffect } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowUpRight, Lock } from "lucide-react";
import { tools } from "@/data/tools";
import { AuditPanel } from "@/components/AuditPanel";

/**
 * Dedicated page for a single automation (/automations/:toolId).
 * Placeholder layout until each tool's real dashboard is wired in — the
 * "Run Audit" CTA uses tool.url from src/data/tools.ts once it's set.
 */
export default function ToolPage() {
  const { toolId } = useParams();
  const tool = tools.find((t) => t.id === toolId);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [toolId]);

  if (!tool) return <Navigate to="/" replace />;
  // A tool with its own page (e.g. Lead Magnet) must not also render this
  // generic stub — send a direct hit on /automations/<id> to the real page,
  // but only while it is unlocked, so the redirect can't bypass the flag.
  if (tool.route && tool.status === "live") return <Navigate to={tool.route} replace />;

  const live = tool.status === "live";
  const runnable = live && tool.url !== "";
  const Icon = tool.icon;

  return (
    <div className="bg-hero relative min-h-[100svh] overflow-hidden text-white">
      {/* subtle backdrop orbs to match the hero */}
      <div className="pointer-events-none absolute inset-0" aria-hidden>
        <div className="hero-grid absolute inset-0" />
        <div
          className="absolute -right-32 -top-40 h-[560px] w-[560px] rounded-full blur-[70px] opacity-40"
          style={{ background: `radial-gradient(circle, ${tool.from}, transparent 65%)` }}
        />
        <div
          className="absolute -bottom-44 -left-36 h-[480px] w-[480px] rounded-full blur-[70px] opacity-35"
          style={{ background: `radial-gradient(circle, ${tool.to}, transparent 65%)` }}
        />
      </div>

      <div className="container relative z-10 flex min-h-[100svh] flex-col pb-16 pt-8">
        {/* top bar */}
        <motion.div
          initial={{ opacity: 0, y: -14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex items-center justify-between"
        >
          <Link to="/" aria-label="Back to the Automation Hub">
            <img src="/logo-white.svg" alt="Wahha Design" className="h-8 w-auto md:h-9" />
          </Link>
          <Link
            to="/"
            className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.07] px-4 py-2 text-[12.5px] font-bold uppercase tracking-[0.14em] text-white/80 transition-colors hover:bg-white/[0.14] hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to hub
          </Link>
        </motion.div>

        {/* tool identity — icon and name read as one unit on the left; the status
            badge sits at the container's right edge, the same edge as the
            dashboard panel below it */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.12 }}
          className="mt-14 flex flex-wrap items-center justify-between gap-4"
        >
          <div className="flex min-w-0 items-center gap-4 sm:gap-6">
            <span
              className="grid h-20 w-20 shrink-0 place-items-center rounded-3xl text-white shadow-[0_18px_40px_-12px_rgba(0,0,0,0.55)]"
              style={{ background: `linear-gradient(135deg, ${tool.from}, ${tool.to})` }}
              aria-hidden
            >
              <Icon className="h-9 w-9" />
            </span>
            {/* Same treatment as the hero headline's second line: the brand ramp
                clipped to the glyphs, over-sized to 200% so `animate-shimmer` has
                somewhere to pan. The hero applies it per word (each one carries the
                full ramp); a title reads better as one continuous sweep.
                pb-[0.12em] keeps descenders — the "y" in "Crawlability" — off the
                clipping edge, as the hero does for the same reason. */}
            <h1 className="text-gradient-brand animate-shimmer pb-[0.12em] text-4xl font-extrabold tracking-tight sm:text-5xl">
              {tool.name}
            </h1>
          </div>
          {live ? (
            <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-brand-teal/15 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.14em] text-brand-teal">
              <span
                className="h-1.5 w-1.5 rounded-full bg-brand-teal animate-pulse-ring"
                aria-hidden
              />
              Live
            </span>
          ) : (
            <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-white/[0.1] px-3 py-1 text-[11px] font-bold uppercase tracking-[0.14em] text-white/55">
              <Lock className="h-3 w-3" aria-hidden />
              In development
            </span>
          )}
        </motion.div>

        {/* run CTA — external dashboards only; audit tools run inline below */}
        {!tool.auditType && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.25 }}
            className="mt-10"
          >
            {runnable ? (
              <a
                href={tool.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2.5 rounded-full bg-brand-orange px-8 py-4 text-[13.5px] font-bold uppercase tracking-[0.16em] text-white shadow-[0_16px_40px_-10px_rgba(246,157,47,0.55)] transition-transform hover:scale-[1.03]"
              >
                Run Audit
                <ArrowUpRight className="h-[18px] w-[18px]" />
              </a>
            ) : (
              <div className="flex flex-wrap items-center gap-4">
                <span
                  aria-disabled
                  className="inline-flex cursor-not-allowed items-center gap-2.5 rounded-full bg-white/[0.08] px-8 py-4 text-[13.5px] font-bold uppercase tracking-[0.16em] text-white/40"
                >
                  Run Audit
                  <Lock className="h-4 w-4" />
                </span>
                <span className="text-sm text-white/50">
                  {live
                    ? "Connect the dashboard URL to enable."
                    : "Your Wahha team is building this right now."}
                </span>
              </div>
            )}
          </motion.div>
        )}

        {/* dashboard area — audit runner for audit tools, placeholder otherwise */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.38 }}
          className={`mt-12 flex min-h-[320px] flex-1 items-center justify-center rounded-3xl bg-white/[0.04] ${
            tool.auditType ? "border border-white/15" : "border border-dashed border-white/15"
          }`}
        >
          {tool.auditType ? (
            <AuditPanel tool={tool} auditType={tool.auditType} />
          ) : (
            <div className="px-6 py-14 text-center">
              <span
                className="mx-auto grid h-12 w-12 place-items-center rounded-2xl opacity-80"
                style={{ background: `linear-gradient(135deg, ${tool.from}, ${tool.to})` }}
                aria-hidden
              >
                <Icon className="h-6 w-6 text-white" />
              </span>
              <p className="mt-5 text-[15px] font-semibold text-white/70">
                The {tool.name} dashboard will live here.
              </p>
              <p className="mt-1.5 text-sm text-white/45">
                Wire it up by setting{" "}
                <code className="rounded bg-white/10 px-1.5 py-0.5 text-[12px]">url</code> in
                src/data/tools.ts
              </p>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
