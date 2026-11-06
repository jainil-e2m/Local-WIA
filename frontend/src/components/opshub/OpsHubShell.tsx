/* ────────────────────────────────────────────────────────────────
   Ops Hub shell — sidebar, topbar, and the four global overlays.

   Re-skin decisions worth stating, because they are the whole reason this
   file exists rather than the mock's markup:

   1. THE SIDEBAR IS `brand-ink`, NOT NAVY. #221e17 is the WIA extraction's
      warm near-black — the same value `.bg-ink` already uses on the landing
      page. A dark rail is what gives a six-screen app its structure, so
      the structure is kept and only the hue is corrected onto the brand.

   2. NUMERALS ARE INTER, TIGHTLY TRACKED. The mock set every figure in DM
      Serif Display. The hub ships Inter alone, so display weight comes from
      size and negative tracking instead of a second family. Adding a serif
      would mean loading a face the rest of the app does not use.

   3. THE ACTIVE STATE IS `brand-primary`, and counts sit in a translucent
      chip rather than a mono font, for the same reason.
   ──────────────────────────────────────────────────────────────── */

import { useMemo, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowLeftRight, ArrowUpRight, Bell, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { ATELIER_UNAVAILABLE, atelierLaunchHref } from "@/lib/atelierLaunch";
import { PAGE_META, SOURCE_META, SOURCE_ORDER, type ScreenId } from "@/lib/opsHub";
import { Tooltip } from "@/components/ui/tooltip";
import { DEMO_DATE, PALETTE_DEFS } from "@/data/opsHub";
import { TEAM } from "@/data/opsHub";
import type { OpsHub } from "@/hooks/useOpsHub";
import { Pill, SourceChip } from "./primitives";

const NAV_MAIN: { id: ScreenId; label: string }[] = [
  { id: "home", label: "Home" },
  { id: "inbox", label: "AI Inbox" },
  { id: "meetings", label: "Meetings" },
  { id: "ops", label: "Ops Watch" },
  { id: "clients", label: "Client Hub" },
];

/* The mobile nav's tab chip — the sidebar is desktop-only. */
const mobileTabClass = (active: boolean) =>
  cn(
    "flex-none rounded-lg px-3 py-1.5 text-[12px] transition-colors",
    active
      ? "bg-brand-primary font-bold text-white"
      : "font-medium text-brand-secondary hover:bg-brand-mist/60",
  );

export function OpsHubShell({ hub, children }: { hub: OpsHub; children: ReactNode }) {
  const { state, counts, go } = hub;
  const meta = PAGE_META[state.screen];
  /* The Content Atelier is its own app, not a hub screen: its entries are a
     full-page launch through the sign-on hand-off, disabled where the
     Atelier is not configured. */
  const atelierHref = atelierLaunchHref();

  const navCount = (id: ScreenId): number => {
    switch (id) {
      case "home":
        return counts.needsReview;
      case "inbox":
        return counts.inboxOpen;
      case "meetings":
        return counts.packsNeedingReview;
      case "ops":
        return counts.opsOpen;
      case "clients":
        return counts.clientAttention;
      default:
        return 0;
    }
  };

  return (
    <div className="bg-hero min-h-[100svh]">
      <div className="flex min-h-[100svh]">
        {/* ── sidebar ──────────────────────────────────────────── */}
        <aside className="bg-ink sticky top-0 hidden h-[100svh] w-[236px] flex-none flex-col overflow-y-auto lg:flex">
          <div className="px-5 pb-4 pt-6">
            <Link
              to="/"
              className="mb-5 inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.12em] text-white/45 transition-colors hover:text-white"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              {/* "Back to hub" pointed AWAY from the hub — this screen is the
                  hub. The launcher is the Command Center. */}
              Back to Command Center
            </Link>
            <div className="flex items-center gap-2.5">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-primary text-[13px] font-bold text-white">
                W
              </span>
              <div className="min-w-0">
                <p className="text-[14px] font-bold leading-tight text-white">
                  AI Operations Hub
                </p>
                <p className="text-[10.5px] leading-tight text-white/45">
                  Your operations, connected.
                </p>
              </div>
            </div>
          </div>

          <nav className="flex-1 px-3">
            <NavGroup label="Operate">
              {NAV_MAIN.map((d) => (
                <NavItem
                  key={d.id}
                  label={d.label}
                  count={navCount(d.id)}
                  active={state.screen === d.id}
                  onClick={() => go(d.id)}
                />
              ))}
            </NavGroup>
            <NavGroup label="Secondary">
              <AtelierNavItem href={atelierHref} />
            </NavGroup>
            <NavGroup label="System">
              <NavItem
                label="Source Coverage"
                count={0}
                active={state.screen === "settings"}
                onClick={() => go("settings")}
              />
            </NavGroup>
          </nav>

          <div className="mt-4 border-t border-white/10 px-4 py-4">
            <p className="mb-2.5 text-[10px] font-bold uppercase tracking-[0.12em] text-white/35">
              Connected sources
            </p>
            {/* Marks rather than wordmarks: seven text pills wrapped to three
                rows and read as a paragraph. The icons are recognised at a
                glance and fit one row, and the Tooltip carries the name — the
                native `title` attribute was doing that job invisibly on touch
                and after a ~1s OS delay. */}
            <div className="flex flex-wrap gap-1.5">
              {SOURCE_ORDER.map((s) => {
                const meta = SOURCE_META[s];
                return (
                  <Tooltip
                    key={s}
                    content={`${meta.label} — connected (demo)`}
                    className="grid h-8 w-8 place-items-center rounded-lg bg-white/[0.07] ring-1 ring-white/10 transition-colors hover:bg-white/[0.16] hover:ring-white/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-sky/70"
                  >
                    {meta.logo ? (
                      <img
                        src={meta.logo}
                        // The tooltip is the accessible name; a duplicate alt
                        // would have a screen reader announce every source twice.
                        alt=""
                        aria-hidden
                        width={22}
                        height={22}
                        loading="lazy"
                        decoding="async"
                        className="h-[22px] w-[22px] object-contain"
                      />
                    ) : (
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{ background: meta.color }}
                        aria-hidden
                      />
                    )}
                  </Tooltip>
                );
              })}
            </div>
            <p className="mt-3 flex items-center gap-1.5 text-[10px] text-white/35">
              <span
                className="h-1.5 w-1.5 rounded-full bg-brand-orange"
                aria-hidden
              />
              Demo environment · see Source Coverage for what each dataset is
            </p>
          </div>

          <button
            type="button"
            onClick={hub.toggleUser}
            aria-label={`Signed in as ${state.user}. Switch user.`}
            className="m-3 flex items-center gap-2.5 rounded-xl bg-white/[0.06] px-3 py-2.5 text-left transition-colors hover:bg-white/[0.11]"
          >
            <span className="grid h-8 w-8 flex-none place-items-center rounded-full bg-brand-primary text-[12px] font-bold text-white">
              {TEAM[state.user] ?? "W"}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[12.5px] font-bold text-white">
                {state.user}
              </span>
              <span className="block truncate text-[10.5px] text-white/45">
                {state.user === "Whitney" ? "Founder · approver" : "Operations lead"}
              </span>
            </span>
            {/* An icon, not the word "Switch": at 236px the word left ~84px
                for the role line, which clipped "Founder · approver" to
                "Founder · app…". The button already carries the accessible
                name, so the glyph loses nothing. */}
            <ArrowLeftRight
              className="h-3.5 w-3.5 flex-none text-white/45"
              aria-hidden
            />
          </button>
        </aside>

        {/* ── main column ──────────────────────────────────────── */}
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex flex-wrap items-center gap-3 border-b border-brand-mist/80 bg-white/85 px-5 py-3 backdrop-blur-md sm:px-7">
            <div className="min-w-[150px] flex-1">
              <h1 className="text-[16.5px] font-bold leading-tight tracking-[-0.01em] text-brand-ink">
                {meta.title}
              </h1>
              <p className="mt-0.5 text-[12px] text-brand-gray">{meta.subtitle}</p>
            </div>

            <button
              type="button"
              onClick={() => hub.patch({ paletteOpen: true, paletteQ: "" })}
              className="hidden min-w-[260px] flex-1 items-center gap-2.5 rounded-xl border border-brand-mist bg-white px-3.5 py-2.5 text-left text-[12.5px] text-brand-gray transition-colors hover:border-brand-stone md:flex"
            >
              <Search className="h-4 w-4 flex-none text-brand-slate" />
              <span className="flex-1 truncate">Ask a question about your operations…</span>
              <kbd className="flex-none rounded border border-brand-mist bg-brand-surface px-1.5 py-0.5 text-[10px] font-bold text-brand-gray">
                ⌘K
              </kbd>
            </button>

            <div className="flex flex-none items-center gap-2.5">
              <button
                type="button"
                onClick={() => go("ops")}
                aria-label={`${counts.opsOpen} open exceptions`}
                className="relative grid h-9 w-9 place-items-center rounded-xl border border-brand-mist bg-white transition-colors hover:border-brand-stone"
              >
                <Bell className="h-4 w-4 text-brand-secondary" />
                {counts.opsOpen > 0 && (
                  <span className="absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full bg-console-bad px-1 text-[9.5px] font-bold text-white">
                    {counts.opsOpen}
                  </span>
                )}
              </button>
              <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-ink text-[12px] font-bold text-white">
                {TEAM[state.user] ?? "W"}
              </span>
            </div>
          </header>

          {/* mobile nav — the sidebar is desktop-only */}
          <div className="flex gap-1.5 overflow-x-auto border-b border-brand-mist/70 bg-white/70 px-4 py-2 lg:hidden">
            {NAV_MAIN.map((d) => (
              <button
                key={d.id}
                type="button"
                onClick={() => go(d.id)}
                className={mobileTabClass(state.screen === d.id)}
              >
                {d.label}
              </button>
            ))}
            {atelierHref ? (
              <a href={atelierHref} className={mobileTabClass(false)}>
                Atelier
              </a>
            ) : (
              <button
                type="button"
                disabled
                title={ATELIER_UNAVAILABLE}
                className={cn(mobileTabClass(false), "cursor-not-allowed opacity-50 hover:bg-transparent")}
              >
                Atelier
              </button>
            )}
            <button
              type="button"
              onClick={() => go("settings")}
              className={mobileTabClass(state.screen === "settings")}
            >
              Sources
            </button>
          </div>

          <main className="flex-1 px-5 py-6 sm:px-7">
            {/* Wider than the page container's 1920 would imply, because the
                236px sidebar is outside this box — at 1920 the content area is
                ~1684, so a 1180 cap wasted 500px. Still capped: the screens
                are card grids, and past ~1600 a four-up row starts reading as
                unrelated columns. */}
            <div className="mx-auto w-full max-w-[1600px]">{children}</div>
          </main>
        </div>
      </div>

      <CommandPalette hub={hub} />
      <EvidenceDrawer hub={hub} />
      <MessageModal hub={hub} />
      <Toast message={state.toast} />
    </div>
  );
}

/* ── sidebar bits ─────────────────────────────────────────────── */

function NavGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="mb-5">
      <p className="mb-1.5 px-3 text-[9.5px] font-bold uppercase tracking-[0.14em] text-white/30">
        {label}
      </p>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function NavItem({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-[10px] px-3 py-2 text-left text-[13px] transition-colors",
        active
          ? "bg-brand-primary/25 font-bold text-white"
          : "font-medium text-[#B9C3E8] hover:bg-white/[0.06] hover:text-white",
      )}
    >
      <span
        className={cn(
          "h-[5px] w-[5px] flex-none rounded-full",
          active ? "bg-brand-primary" : "bg-white/25",
        )}
        aria-hidden
      />
      <span className="flex-1 truncate">{label}</span>
      {count > 0 && (
        <span
          className={cn(
            "flex-none rounded px-1.5 py-px text-[10.5px] font-bold tabular-nums",
            active ? "bg-white/20 text-white" : "text-white/40",
          )}
        >
          {count}
        </span>
      )}
    </button>
  );
}

/** The sidebar's Content Atelier entry. It leaves the hub for another app, so
    it is a plain anchor (a full-page navigation through the sign-on
    hand-off), never active, and a disabled button where the launch link is
    not available. */
function AtelierNavItem({ href }: { href: string | undefined }) {
  const className =
    "flex w-full items-center gap-2.5 rounded-[10px] px-3 py-2 text-left text-[13px] font-medium text-[#B9C3E8] transition-colors";
  const content = (
    <>
      <span className="h-[5px] w-[5px] flex-none rounded-full bg-white/25" aria-hidden />
      <span className="flex-1 truncate">Content Atelier</span>
      <ArrowUpRight className="h-3.5 w-3.5 flex-none text-white/40" aria-hidden />
    </>
  );
  return href ? (
    <a href={href} className={cn(className, "hover:bg-white/[0.06] hover:text-white")}>
      {content}
    </a>
  ) : (
    <button
      type="button"
      disabled
      title={ATELIER_UNAVAILABLE}
      className={cn(className, "cursor-not-allowed opacity-50")}
    >
      {content}
    </button>
  );
}

/* ── command palette ──────────────────────────────────────────── */

function CommandPalette({ hub }: { hub: OpsHub }) {
  const { state, patch, go } = hub;
  const atelierHref = atelierLaunchHref();
  const results = useMemo(() => {
    const q = state.paletteQ.trim().toLowerCase();
    /* A launch row with nowhere to launch is left out rather than shown dead. */
    const defs = PALETTE_DEFS.filter((d) => !("launch" in d) || atelierHref);
    if (!q) return defs;
    return defs.filter(
      (d) =>
        d.label.toLowerCase().includes(q) ||
        d.tag.toLowerCase().includes(q) ||
        d.dest.toLowerCase().includes(q),
    );
  }, [state.paletteQ, atelierHref]);

  return (
    <AnimatePresence>
      {state.paletteOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.14 }}
          className="fixed inset-0 z-50 flex items-start justify-center bg-brand-ink/45 p-4 pt-[12vh] backdrop-blur-sm"
          onClick={() => patch({ paletteOpen: false })}
        >
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.16 }}
            role="dialog"
            aria-label="Ask a question about your operations"
            className="w-full max-w-[620px] overflow-hidden rounded-2xl border border-brand-mist bg-white shadow-[0_30px_80px_-24px_rgba(34,30,23,0.45)]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-brand-mist px-4 py-3.5">
              <Search className="h-4 w-4 flex-none text-brand-slate" />
              <input
                autoFocus
                value={state.paletteQ}
                onChange={(e) => patch({ paletteQ: e.target.value })}
                placeholder="Ask a question about your operations…"
                className="flex-1 bg-transparent text-[14px] text-brand-ink outline-none placeholder:text-brand-slate"
              />
              <kbd className="flex-none rounded border border-brand-mist bg-brand-surface px-1.5 py-0.5 text-[10px] font-bold text-brand-gray">
                Esc
              </kbd>
            </div>
            <div className="max-h-[46vh] overflow-y-auto p-2">
              {results.length === 0 && (
                <p className="px-3 py-6 text-center text-[12.5px] text-brand-gray">
                  No operator question matches that. Try “waiting”, “overdue” or
                  “attendance”.
                </p>
              )}
              {results.map((d) => {
                const row = (
                  <>
                    <Pill tone="outline" className="flex-none">
                      {d.tag}
                    </Pill>
                    <span className="min-w-0 flex-1 truncate text-[13px] text-brand-ink">
                      {d.label}
                    </span>
                    <span className="flex-none text-[11px] font-bold uppercase tracking-[0.08em] text-brand-slate">
                      {d.dest}
                    </span>
                  </>
                );
                const className =
                  "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-brand-mist/50";
                return "launch" in d ? (
                  <a key={d.label} href={atelierHref} className={className}>
                    {row}
                  </a>
                ) : (
                  <button
                    key={d.label}
                    type="button"
                    onClick={() => go(d.screen, d.extra)}
                    className={className}
                  >
                    {row}
                  </button>
                );
              })}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* ── evidence drawer ──────────────────────────────────────────── */

function EvidenceDrawer({ hub }: { hub: OpsHub }) {
  const { state, patch } = hub;
  const d = state.drawer;
  return (
    <AnimatePresence>
      {d && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.14 }}
          className="fixed inset-0 z-50 flex justify-end bg-brand-ink/35 backdrop-blur-sm"
          onClick={() => patch({ drawer: null })}
        >
          <motion.aside
            initial={{ x: 40, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 30, opacity: 0 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            role="dialog"
            aria-label={d.title}
            className="flex h-full w-full max-w-[440px] flex-col border-l border-brand-mist bg-white"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-start justify-between gap-3 border-b border-brand-mist px-5 py-4">
              <div className="min-w-0">
                <p className="text-[10.5px] font-bold uppercase tracking-[0.12em] text-brand-slate">
                  Evidence
                </p>
                <h2 className="mt-1 text-[15px] font-bold leading-tight text-brand-ink">
                  {d.title}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => patch({ drawer: null })}
                aria-label="Close evidence"
                className="grid h-8 w-8 flex-none place-items-center rounded-lg border border-brand-mist transition-colors hover:bg-brand-mist/50"
              >
                <X className="h-4 w-4 text-brand-secondary" />
              </button>
            </header>
            <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
              <div className="flex flex-wrap items-center gap-2">
                <SourceChip source={d.source} />
                <Pill tone="outline">{d.client}</Pill>
                <span className="text-[11px] text-brand-gray">{d.time}</span>
              </div>
              <p className="text-[13px] font-bold text-brand-ink">{d.label}</p>
              <p className="whitespace-pre-wrap rounded-xl border border-brand-mist bg-brand-surface p-4 text-[12.5px] leading-relaxed text-brand-secondary">
                {d.excerpt}
              </p>
              <p className="text-[11.5px] leading-snug text-brand-gray">
                Evidence is shown so a reviewer can check the claim against its
                source. In production every line here would carry a deep link back
                into the system it came from.
              </p>
            </div>
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* ── suggested-message modal ──────────────────────────────────── */

function MessageModal({ hub }: { hub: OpsHub }) {
  const { state, patch, toast } = hub;
  const m = state.msgModal;
  return (
    <AnimatePresence>
      {m && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.14 }}
          className="fixed inset-0 z-50 grid place-items-center bg-brand-ink/45 p-4 backdrop-blur-sm"
          onClick={() => patch({ msgModal: null })}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.16 }}
            role="dialog"
            aria-label={m.title}
            className="w-full max-w-[520px] overflow-hidden rounded-2xl border border-brand-mist bg-white shadow-[0_30px_80px_-24px_rgba(34,30,23,0.45)]"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-start justify-between gap-3 border-b border-brand-mist px-5 py-4">
              <div>
                <p className="text-[10.5px] font-bold uppercase tracking-[0.12em] text-brand-slate">
                  {m.member}
                </p>
                <h2 className="mt-1 text-[15px] font-bold text-brand-ink">{m.title}</h2>
              </div>
              <button
                type="button"
                onClick={() => patch({ msgModal: null })}
                aria-label="Close"
                className="grid h-8 w-8 flex-none place-items-center rounded-lg border border-brand-mist transition-colors hover:bg-brand-mist/50"
              >
                <X className="h-4 w-4 text-brand-secondary" />
              </button>
            </header>
            <div className="space-y-3 px-5 py-4">
              <p className="whitespace-pre-wrap rounded-xl border border-brand-mist bg-brand-surface p-4 text-[12.5px] leading-relaxed text-brand-secondary">
                {m.body}
              </p>
              <p className="text-[11.5px] leading-snug text-console-warn">{m.note}</p>
            </div>
            <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-brand-mist bg-brand-surface px-5 py-3.5">
              <button
                type="button"
                onClick={() => {
                  toast("Copied to clipboard — demo");
                  patch({ msgModal: null });
                }}
                className="rounded-lg bg-brand-mist/60 px-3 py-2 text-[12px] font-bold text-brand-secondary transition-colors hover:bg-brand-mist"
              >
                Copy
              </button>
              <button
                type="button"
                onClick={() => patch({ msgModal: null })}
                className="rounded-lg bg-brand-ink px-3 py-2 text-[12px] font-bold text-white transition-colors hover:bg-brand-secondary"
              >
                Close
              </button>
            </footer>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* ── toast ────────────────────────────────────────────────────── */

function Toast({ message }: { message: string | null }) {
  return (
    <AnimatePresence>
      {message && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 10 }}
          transition={{ duration: 0.18 }}
          role="status"
          aria-live="polite"
          className="fixed bottom-6 left-1/2 z-50 max-w-[92vw] -translate-x-1/2 rounded-xl bg-brand-ink px-4 py-3 text-[12.5px] font-medium text-white shadow-[0_20px_50px_-18px_rgba(34,30,23,0.6)]"
        >
          {message}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export { DEMO_DATE };
