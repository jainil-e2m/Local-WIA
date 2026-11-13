import { useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  ClipboardCopy,
  Columns3,
  Copy,
  Download,
  FileText,
  LayoutList,
  Loader2,
  RotateCw,
  ShieldCheck,
  Sparkles,
  Table2,
  X,
  type LucideIcon,
} from "lucide-react";
import { STAGES, type LedgerItem } from "@/data/internalMeeting";
import { formatDuration } from "@/lib/internalMeeting";
import {
  toClickUpManifest,
  toLedgerExport,
  toMarkdown,
  toSlackDigest,
  useInternalMeetingRun,
} from "@/hooks/useInternalMeetingRun";
import {
  EvidenceModal,
  Pill,
  RowCard,
  type EvidencePayload,
} from "@/components/internal-meeting/parts";
import { KanbanBoard } from "@/components/internal-meeting/KanbanBoard";
import { TableView } from "@/components/internal-meeting/TableView";

/* ────────────────────────────────────────────────────────────────
   Internal Meeting + Action Items — paste a transcript, get a decidable
   action list, record it in this card's own ledger.

   THE FLOW STOPS AT THE LEDGER. There is no ClickUp, Slack or Drive
   integration in this feature, so no wording on this page may imply an
   external write. Three rules are enforced in the copy throughout:

     · No completed external verbs. Never "created", "assigned", "posted",
       "sent". A destination is a NOUN with a not-connected marker.
     · The non-delivery line is CAPABILITY-negative and present tense —
       "this card cannot send anything anywhere" — not "nothing was sent",
       which is a report about one run and implies the next might.
     · The primary action is "Record in ledger", not "Approve". In every
       adjacent tool Whitney uses — Dubsado proposals, GHL workflows, ad
       approvals — Approve means it goes out now.

   Three things here are load-bearing rather than decorative:

   1. THE CARRY-OVER. Fathom already turns one transcript into action items
      with deep links, free. What it cannot do is remember. The two ledger
      rows — one second sighting, one closure candidate — are the only output
      on this page that is not a commodity, which is why they sit ABOVE the
      new items rather than below them.

   2. THE AGING VIEW. Open ledger items this transcript never mentioned. Four
      of six on the demo run. Without it the register silently accumulates and
      "it always feels like we're like chasing the team" (26 Aug @16:54) stays
      unanswerable.

   3. THE FAILED QUOTE. One row's quote is genuinely not in the transcript, so
      the substring check genuinely fails and its quotation marks come off. It
      is the only thing on screen proving the verification runs rather than
      being asserted — and Whitney has the transcript, so it is checkable.
   ──────────────────────────────────────────────────────────────── */

/* ── View switch ──────────────────────────────────────────────────
   Three shapes over ONE row set and one decision state — nothing is
   duplicated per view, so a decision made on the board is already made in the
   table. The view is the only thing that changes.

   List is the default because it is the only one that shows the grouping the
   extraction produced — already in the ledger, new, needs a call — and that
   grouping is the argument for the card. The board and the table are for
   working through the pile, which is the second visit, not the first. */

type ViewMode = "list" | "board" | "table";

const VIEWS: { id: ViewMode; label: string; icon: LucideIcon }[] = [
  { id: "list", label: "List", icon: LayoutList },
  { id: "board", label: "Board", icon: Columns3 },
  { id: "table", label: "Table", icon: Table2 },
];

function ViewSwitch({
  value,
  onChange,
}: {
  value: ViewMode;
  onChange: (next: ViewMode) => void;
}) {
  return (
    <div
      role="group"
      aria-label="View"
      className="inline-flex items-center gap-1 rounded-lg border border-brand-mist bg-white p-1"
    >
      {VIEWS.map(({ id, label, icon: Icon }) => {
        const on = value === id;
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            aria-pressed={on}
            className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors ${
              on
                ? "bg-brand-primary text-white"
                : "text-brand-secondary hover:bg-brand-mist/50"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        );
      })}
    </div>
  );
}

function Section({
  title,
  count,
  hint,
  children,
}: {
  title: string;
  count: number;
  hint?: string;
  children: React.ReactNode;
}) {
  if (count === 0) return null;
  return (
    <section>
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-brand-secondary">
        {title} · {count}
      </h3>
      {hint && <p className="mb-3 max-w-3xl text-xs leading-relaxed text-brand-gray">{hint}</p>}
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function AgingView({ items }: { items: LedgerItem[] }) {
  if (!items.length) return null;
  return (
    <section>
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-brand-secondary">
        Open in the ledger, not mentioned this run · {items.length}
      </h3>
      <p className="mb-3 max-w-3xl text-xs leading-relaxed text-brand-gray">
        Recorded on an earlier run and still open, whether or not today&rsquo;s meeting
        touched it.
      </p>
      <div className="rounded-xl border border-brand-mist bg-white divide-y divide-brand-mist">
        {items.map((item) => (
          <div key={item.ledgerId} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5">
            <span className="font-mono text-[11px] text-brand-slate">{item.ledgerId}</span>
            <span className="min-w-0 flex-1 text-sm text-brand-ink">{item.canonicalText}</span>
            <span className="text-xs text-brand-gray">{item.owner ?? "unassigned"}</span>
            <Pill className="border-brand-mist bg-brand-mist/40 text-brand-gray">
              open {item.ageDays}d
            </Pill>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function InternalMeetingPage() {
  const run = useInternalMeetingRun();
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<ViewMode>("list");
  /* One modal for the whole page rather than per-chip open state: the old
     inline expander could leave a dozen quotes open at once, which is how the
     list stopped being scannable at exactly the moment you were comparing
     rows. */
  const [evidence, setEvidence] = useState<EvidencePayload | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [toast, setToast] = useState<{
    recorded: number;
    sightings: number;
    closed: number;
    dismissed: number;
    snoozed: number;
  } | null>(null);

  /* Dynamic import so ~48KB of transcript never lands in the main bundle,
     and so the demo needs no network in the room. */
  const loadDemo = async () => {
    setLoading(true);
    const mod = await import("@/data/internalMeetingTranscript");
    run.setText(mod.DEMO_TRANSCRIPT);
    setLoading(false);
  };

  const copy = async (label: string, value: string) => {
    await navigator.clipboard.writeText(value);
    setCopied(label);
    window.setTimeout(() => setCopied(null), 1800);
  };

  const download = (name: string, value: string) => {
    const url = URL.createObjectURL(new Blob([value], { type: "application/json" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = name;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const decided = run.state === "decided";
  const t = run.transcript;

  return (
    <div className="bg-hero min-h-[100svh]">
      <div className="container py-10">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-brand-gray transition-colors hover:text-brand-primary"
        >
          <ArrowLeft className="h-4 w-4" /> Command Center
        </Link>

        <header className="mt-4 mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold text-brand-ink">Internal Meeting + Action Items</h1>
            <p className="mt-1 max-w-2xl text-sm leading-relaxed text-brand-gray">
              Action items with owners, dates and the words they came from — checked against what was open last time.
            </p>
            {/* MATURITY, STATED. The candidate rows are PREPARED for the
                supplied sample, not extracted live: `DEMO_ROWS` is a fixed
                set. What runs for real against whatever you paste is the
                citation check — every quote below is located in your text or
                marked as unverified — and the carry-over match against the
                ledger. Saying "paste a transcript and get the action items"
                implied arbitrary extraction, which is designed and not yet
                built. */}
            <p className="mt-2 max-w-2xl text-xs leading-relaxed text-amber-800">
              Citation checks run on whatever you paste. The candidate items are prepared for the sample.
            </p>
            {/* Capability-negative, present tense. Not "nothing was sent".

                Weighted BELOW the value line rather than above it. At
                `text-sm font-medium` this caveat was the boldest thing on the
                page and read as the headline, so the first thing a client saw
                about the console was what it cannot do. It still says so,
                plainly, in the register the other supporting lines use. */}
            <p className="mt-2 max-w-2xl text-xs leading-relaxed text-brand-gray">
              No connection to ClickUp, Slack or Drive. Every decision terminates in the
              ledger on this page.
            </p>
            {/* WHY THIS IS NOT THE OPERATIONS HUB'S MEETINGS SCREEN. The Hub
                shows an execution pack per meeting, including internal ones, and
                a reader moving between the two should not have to guess which
                one wins. This console owns the LEDGER — the memory of what was
                still open last week — which is the one thing a per-meeting pack
                structurally cannot hold. It ships first, on its own, as MK-01. */}
            <p className="mt-2 max-w-2xl text-xs leading-relaxed text-brand-gray">
              MK-01. The Hub shows an execution pack per meeting; the carry-over ledger
              lives here.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Pill className="border-amber-200 bg-amber-50 text-amber-800">
              <FileText className="h-3 w-3" /> paste intake · ledger only
            </Pill>
            {run.state !== "idle" && (
              <button
                onClick={run.reset}
                className="rounded-lg border border-brand-mist bg-white p-2 text-brand-gray transition-colors hover:border-brand-stone"
                aria-label="Start over"
              >
                <RotateCw className="h-4 w-4" />
              </button>
            )}
          </div>
        </header>

        {/* ── INTAKE ───────────────────────────────────────────── */}
        {run.state === "idle" && (
          <div className="rounded-xl border border-brand-mist bg-white p-5">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-semibold text-brand-ink">Upload transcript</h2>
              <button
                onClick={() => void loadDemo()}
                disabled={loading}
                className="inline-flex items-center gap-1.5 rounded-lg border border-brand-primary px-3 py-1.5 text-xs font-semibold text-brand-primary disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" />
                )}
                Load demo transcript
              </button>
            </div>
            <textarea
              value={run.text}
              onChange={(event) => run.setText(event.target.value)}
              placeholder="Paste a Fathom copy or a Zoom .txt — both come out as “MM:SS - Speaker Name” with indented body text, so either works."
              rows={10}
              className="w-full rounded-lg border border-brand-mist px-3 py-2.5 font-mono text-xs leading-relaxed focus:border-brand-primary focus:outline-none"
            />
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button
                onClick={() => run.start(run.text)}
                disabled={run.text.trim().length < 200}
                className="inline-flex items-center gap-2 rounded-lg bg-brand-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
              >
                <Check className="h-4 w-4" /> Read this transcript
              </button>
              <span className="text-xs text-brand-gray">
                {run.text.trim() ? `${run.text.length.toLocaleString()} characters pasted` : "Nothing pasted yet"}
              </span>
            </div>
          </div>
        )}

        {/* ── PROCESSING ───────────────────────────────────────── */}
        {run.state === "running" && (
          <div className="rounded-xl border border-brand-mist bg-white p-6">
            <h2 className="text-sm font-semibold text-brand-ink">Reading run #{run.runNumber}</h2>
            <ol className="mt-4 space-y-3">
              {STAGES.map((stage, index) => {
                const done = index < run.stageIndex;
                const active = index === run.stageIndex;
                return (
                  <li key={stage.id} className="flex items-start gap-3">
                    <span className="mt-0.5">
                      {done ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      ) : active ? (
                        <Loader2 className="h-4 w-4 animate-spin text-brand-primary" />
                      ) : (
                        <span className="block h-4 w-4 rounded-full border border-brand-mist" />
                      )}
                    </span>
                    <div className="min-w-0">
                      <p
                        className={`text-sm ${done || active ? "text-brand-ink" : "text-brand-slate"}`}
                      >
                        {stage.label}
                        {!stage.real && (
                          <Pill className="ml-2 border-amber-200 bg-amber-50 text-amber-800">
                            pre-computed for this run
                          </Pill>
                        )}
                      </p>
                      {/* Real stages report real numbers off the parsed text. */}
                      {done && stage.id === "read" && t && (
                        <p className="mt-0.5 text-xs text-brand-gray">
                          {t.turns.length} turns · {t.speakers.length} speakers ·{" "}
                          {formatDuration(t.durationSeconds)} · {t.firstDisplay}–{t.lastDisplay}
                        </p>
                      )}
                      {/* Counts QUOTES, not rows — one item carries two. Saying
                          "quotes" while counting rows is the small kind of wrong
                          that costs more than it saves when someone checks. */}
                      {done && stage.id === "verify" && (
                        <p className="mt-0.5 text-xs text-brand-gray">
                          {run.rows.reduce(
                            (n, r) => n + r.citations.filter((c) => c.verified).length,
                            0,
                          )}{" "}
                          of {run.rows.reduce((n, r) => n + r.citations.length, 0)} quotes found
                          word-for-word ·{" "}
                          {run.rows.reduce(
                            (n, r) => n + r.citations.filter((c) => !c.verified).length,
                            0,
                          )}{" "}
                          failed
                        </p>
                      )}
                      {done && stage.id === "ledger" && (
                        <p className="mt-0.5 text-xs text-brand-gray">
                          {run.ledger.length} open items checked ·{" "}
                          {run.rows.filter((r) => r.match).length} matched
                        </p>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>
        )}

        {/* ── REVIEW / DECIDED ─────────────────────────────────── */}
        {(run.state === "review" || decided) && t && (
          <div /* pb-28 reserves clearance for the sticky action bar below, which is
                 the last child: without it the bar lands on top of the final
                 section at full scroll and that content is unreachable. */
            className="space-y-8 pb-28">
            <div className="rounded-xl border border-brand-mist bg-white p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <h2 className="text-lg font-semibold text-brand-ink">
                  Run #{run.runNumber} · E2M weekly sync, 2 Sep 2026
                </h2>
                {decided ? (
                  <Pill className="border-emerald-200 bg-emerald-50 text-emerald-700">
                    <ShieldCheck className="h-3 w-3" /> Decided by Gisselle · ledger v
                    {run.priorRun} → v{run.ledgerVersion}
                  </Pill>
                ) : (
                  <Pill className="border-brand-primary/30 bg-brand-primary/5 text-brand-primary">
                    {run.undecided.length} waiting on you
                  </Pill>
                )}
              </div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-brand-gray">
                <span>{t.charCount.toLocaleString()} characters</span>
                <span>{t.turns.length} turns</span>
                <span>
                  {t.speakers.map((s) => `${s.label}${s.org === "wia" ? "" : " (outside)"}`).join(" · ")}
                </span>
                <span>
                  {t.canDeepLink
                    ? "deep links available"
                    : "quote-only citations — no Fathom call id in this paste, so no deep links"}
                </span>
              </div>
              {/* Counted off the parsed speaker set, never asserted — a
                  hardcoded headcount is wrong the moment the paste changes.
                  The sentence justifying the choice of fixture was removed:
                  it explained the demo to the reader rather than telling them
                  anything about their own meeting. */}
              <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900">
                <strong>This is the E2M weekly sync, not a Monday team meeting.</strong>{" "}
                {t.speakers.filter((s) => s.org === "external").length} of {t.speakers.length}{" "}
                people who spoke are from E2M, so some owners land outside your team and are marked
                that way.
              </p>
              <p className="mt-2 rounded-lg bg-brand-mist/40 px-3 py-2 text-xs leading-relaxed text-brand-secondary">
                Speaker labels in this file are unreliable. Owners are resolved from what was
                committed, never from the label.
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3">
              <ViewSwitch value={view} onChange={setView} />
              <span className="text-xs text-brand-gray">
                {run.decidable.length} decidable · {run.undecided.length} still waiting
              </span>
            </div>

            {view === "list" && (
              <>
                <Section
                  title="Already in the ledger"
                  count={run.groups.sightings.length + run.groups.closure.length}
                  hint="Recorded on an earlier run and raised again today. These update the existing entry rather than adding a second one."
                >
                  {[...run.groups.sightings, ...run.groups.closure].map((row) => (
                    <RowCard
                      key={row.id}
                      row={row}
                      decided={decided}
                      transcript={t}
                      onDecide={(d) => run.decide(row.id, d)}
                      onChooseOwner={(owner) => run.chooseOwner(row.id, owner)}
                      onOpenEvidence={setEvidence}
                    />
                  ))}
                </Section>

                <Section title="New this run" count={run.groups.new.length}>
                  {run.groups.new.map((row) => (
                    <RowCard
                      key={row.id}
                      row={row}
                      decided={decided}
                      transcript={t}
                      onDecide={(d) => run.decide(row.id, d)}
                      onChooseOwner={(owner) => run.chooseOwner(row.id, owner)}
                      onOpenEvidence={setEvidence}
                    />
                  ))}
                </Section>

                <Section
                  title="Needs you to decide"
                  count={run.groups.abstains.length + run.groups.unverified.length}
                  hint="Where the extraction was not confident enough to call it, it asks instead of guessing."
                >
                  {[...run.groups.abstains, ...run.groups.unverified].map((row) => (
                    <RowCard
                      key={row.id}
                      row={row}
                      decided={decided}
                      transcript={t}
                      onDecide={(d) => run.decide(row.id, d)}
                      onChooseOwner={(owner) => run.chooseOwner(row.id, owner)}
                      onOpenEvidence={setEvidence}
                    />
                  ))}
                </Section>
              </>
            )}

            {/* The board carries only decidable rows: a not-proposed row has
                no decision to make, so it has no column to sit in. It stays
                in its own disclosure below, in every view. */}
            {view === "board" && (
              <KanbanBoard
                rows={run.decidable}
                decided={decided}
                transcript={t}
                onDecide={run.decide}
                onUndecide={run.undecide}
                onChooseOwner={run.chooseOwner}
                onOpenEvidence={setEvidence}
              />
            )}

            {/* The table shows everything INCLUDING not-proposed rows, because
                its job is the whole picture on one screen and a hidden four
                would make the counts disagree with the list. */}
            {view === "table" && (
              <TableView
                rows={run.rows}
                decided={decided}
                transcript={t}
                onDecide={run.decide}
                onChooseOwner={run.chooseOwner}
                onOpenEvidence={setEvidence}
              />
            )}

            <AgingView items={run.groups.untouched} />

            {view !== "table" && (
              <details className="rounded-xl border border-brand-mist bg-white">
                <summary className="cursor-pointer px-4 py-3 text-xs font-semibold uppercase tracking-wide text-brand-secondary">
                  Not proposed, and why · {run.groups.notProposed.length}
                </summary>
                <div className="space-y-3 border-t border-brand-mist p-4">
                  {run.groups.notProposed.map((row) => (
                    <RowCard
                      key={row.id}
                      row={row}
                      decided
                      transcript={t}
                      onDecide={() => undefined}
                      onChooseOwner={() => undefined}
                      onOpenEvidence={setEvidence}
                    />
                  ))}
                </div>
              </details>
            )}

            {!decided ? (
              /* A sticky bar floats OVER whatever is behind it, so it has to
                 look like it is floating. With `shadow-sm` and a flat white
                 fill it read as a panel that had collided with the table
                 underneath and clipped a row in half. The lift, the ring and
                 the blur are what make it legible as an action bar. */
              <div className="sticky bottom-4 z-20 flex flex-wrap items-center gap-3 rounded-xl border border-brand-mist bg-white/95 p-4 shadow-lg ring-1 ring-brand-ink/5 backdrop-blur-md">
                <button
                  onClick={() => setToast(run.record())}
                  disabled={run.undecided.length > 0}
                  className="inline-flex items-center gap-2 rounded-lg bg-brand-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
                >
                  <ShieldCheck className="h-4 w-4" />
                  Finish review
                  {run.undecided.length > 0 && ` · ${run.undecided.length} undecided`}
                </button>
                <span className="text-xs text-brand-gray">
                  Records your decisions in this card&rsquo;s ledger. No external request is made.
                </span>
              </div>
            ) : (
              <div className="rounded-xl border border-brand-mist bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-brand-secondary">
                  What she does next
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {[
                    ["ClickUp manifest", toClickUpManifest(run.rows), ClipboardCopy],
                    ["Slack digest", toSlackDigest(run.rows, run.reviewDate), Copy],
                    ["Markdown", toMarkdown(run.rows, run.reviewDate), FileText],
                  ].map(([label, value, Icon]) => {
                    const IconComponent = Icon as typeof Copy;
                    return (
                      <button
                        key={label as string}
                        onClick={() => void copy(label as string, value as string)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-brand-mist px-3 py-2 text-xs font-medium text-brand-secondary transition-colors hover:border-brand-stone"
                      >
                        <IconComponent className="h-3.5 w-3.5" />
                        {copied === label ? "Copied" : `Copy ${label}`}
                      </button>
                    );
                  })}
                  <button
                    onClick={() => download("wia-ledger-v24.json", toLedgerExport(run.ledger))}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-brand-mist px-3 py-2 text-xs font-medium text-brand-secondary transition-colors hover:border-brand-stone"
                  >
                    <Download className="h-3.5 w-3.5" /> Export ledger
                  </button>
                </div>
                <p className="mt-3 text-xs leading-relaxed text-brand-gray">
                  Tab-delimited for ClickUp&rsquo;s bulk paste. The ledger export is yours and
                  portable.
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* One evidence modal for the page. Rendered outside the scroll
          container so its overlay is never clipped by it. */}
      <EvidenceModal payload={evidence} onClose={() => setEvidence(null)} />

      {/* Persistent decision receipt — stays until dismissed, because the
          decision is the terminal event of this flow. */}
      <AnimatePresence>
        {toast && (
          <motion.div
            key="internal-meeting-decision-toast"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            className="fixed bottom-6 right-6 z-50 max-w-sm rounded-xl border border-brand-mist bg-white p-4 shadow-lg"
            role="status"
          >
            <div className="flex items-start gap-3">
              <div className="rounded-full bg-emerald-50 p-1.5">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-brand-ink">
                  Run #{run.runNumber} decided
                </p>
                <p className="mt-0.5 text-xs leading-relaxed text-brand-gray">
                  {toast.recorded} recorded ({toast.sightings} as sightings on existing items),{" "}
                  {toast.closed} closed by you, {toast.dismissed} marked not an item,{" "}
                  {toast.snoozed} snoozed. Recorded in this card&rsquo;s ledger (v{run.priorRun} → v
                  {run.ledgerVersion}).{" "}
                  <strong>This card cannot send to ClickUp, Slack or Drive.</strong>
                </p>
              </div>
              <button
                onClick={() => setToast(null)}
                aria-label="Dismiss notification"
                className="rounded p-1 text-brand-slate transition-colors hover:bg-brand-mist/50 hover:text-brand-ink"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
