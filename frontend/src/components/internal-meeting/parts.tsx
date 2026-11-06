/* Shared row parts for Internal Meeting + Action Items.

   Extracted from the page because three views now render the same row — the
   list, the kanban card and the table — and the owner/date/evidence rules
   have to read identically in all three. The decision rules themselves live
   in `useInternalMeetingRun` (allowedDecisions / decisionBlockedReason) for
   the same reason. */

import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  Ban,
  CalendarClock,
  Check,
  CheckCircle2,
  Clock,
  FileText,
  HelpCircle,
  Layers,
  Quote,
  X,
} from "lucide-react";
import {
  DUE_BASIS_LABEL,
  OWNER_BASIS_LABEL,
  type LedgerItem,
} from "@/data/internalMeeting";
import {
  SOURCE_KIND_META,
  WIA_ROSTER,
  type NormalizedTranscript,
} from "@/lib/internalMeeting";
import {
  allowedDecisions,
  decisionBlockedReason,
  type Decision,
  type ResolvedRow,
} from "@/hooks/useInternalMeetingRun";
import { DECISION_LABEL } from "./labels";

export const Pill = ({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) => (
  <span
    className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${className}`}
  >
    {children}
  </span>
);

/* ── The evidence modal ───────────────────────────────────────────
   What the source logo opens. It carries the four things that make a quote
   checkable and nothing else:

     · the tool that produced the paste, asserted only when the text says so
     · the derived MM:SS, with the segment caveat when the turn is long
     · the verbatim quote
     · the turn it sits inside, plus the turns either side

   THE SURROUNDING TURNS ARE THE POINT. A quote read alone is how "we totally
   can" becomes a commitment; read with the question that preceded it, it is
   plainly conditional. Whitney sat in these meetings, so context is what lets
   her overrule the extraction rather than just trust it. */

export interface EvidencePayload {
  title: string;
  quote: string;
  speaker: string | null;
  display: string | null;
  segment: boolean;
  deepLink: string | null;
  turnIndex: number;
  /** Absent for prior-run evidence: it came out of a different file. */
  transcript: NormalizedTranscript | null;
  /** Set when the evidence is a ledger item's first sighting. */
  priorRun?: { run: number; label: string };
}

export function EvidenceModal({
  payload,
  onClose,
}: {
  payload: EvidencePayload | null;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!payload) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [payload, onClose]);

  const source = payload?.transcript
    ? SOURCE_KIND_META[payload.transcript.sourceKind]
    : SOURCE_KIND_META.unknown;

  /* One turn either side. Enough to see what was being answered, short
     enough that the quote itself stays the thing you read first. */
  const turns = payload?.transcript?.turns ?? [];
  const context =
    payload && payload.turnIndex >= 0
      ? turns.slice(Math.max(0, payload.turnIndex - 1), payload.turnIndex + 2)
      : [];

  return (
    <AnimatePresence>
      {payload && (
        <motion.div
          key="evidence-modal"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-label="Source evidence"
          className="fixed inset-0 z-[80] flex items-start justify-center overflow-y-auto bg-brand-ink/40 px-4 py-10 backdrop-blur-sm"
        >
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.99 }}
            onClick={(event) => event.stopPropagation()}
            className="w-full max-w-2xl rounded-2xl border border-brand-mist bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-3 border-b border-brand-mist px-5 py-4">
              <div className="flex min-w-0 items-start gap-3">
                <SourceMark kind={payload.transcript?.sourceKind ?? "unknown"} size="lg" />
                <div className="min-w-0">
                  <p className="text-sm font-semibold leading-snug text-brand-ink">
                    {payload.title}
                  </p>
                  <p className="mt-0.5 text-[11px] text-brand-gray">
                    {payload.priorRun
                      ? `Run #${payload.priorRun.run} transcript · ${payload.priorRun.label}`
                      : source.label}
                    {payload.display &&
                      ` · ${payload.segment ? `in the segment starting @${payload.display}` : `@${payload.display}`}`}
                    {payload.speaker && ` · ${payload.speaker}`}
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                aria-label="Close"
                className="rounded p-1 text-brand-slate transition-colors hover:bg-brand-mist/50 hover:text-brand-ink"
              >
                <X className="h-4 w-4" />
              </button>
            </header>

            <div className="space-y-4 px-5 py-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-secondary">
                  The words this came from
                </p>
                <blockquote className="mt-1.5 border-l-2 border-brand-primary/40 bg-brand-mist/20 py-2 pl-3 text-sm leading-relaxed text-brand-ink">
                  “{payload.quote}”
                </blockquote>
              </div>

              {payload.priorRun ? (
                <p className="rounded-lg bg-brand-mist/40 px-3 py-2 text-[11px] leading-relaxed text-brand-secondary">
                  This came out of the run #{payload.priorRun.run} transcript, not the
                  one pasted today, so it is shown as recorded and is not re-checked
                  against this file.
                </p>
              ) : (
                context.length > 0 && (
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-secondary">
                      In context
                    </p>
                    <div className="mt-1.5 space-y-2.5">
                      {context.map((turn, index) => {
                        const isQuoteTurn =
                          payload.turnIndex >= 0 &&
                          turns[payload.turnIndex] === turn;
                        return (
                          <div
                            key={`${turn.display}-${index}`}
                            className={`rounded-lg px-3 py-2 text-xs leading-relaxed ${
                              isQuoteTurn
                                ? "bg-brand-primary/5 text-brand-ink"
                                : "text-brand-gray"
                            }`}
                          >
                            <p className="mb-0.5 text-[11px] font-semibold text-brand-slate">
                              {turn.display} · {turn.speaker}
                              {isQuoteTurn && " · contains the quote"}
                            </p>
                            <p>{turn.text}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )
              )}

              <div className="flex flex-wrap items-center gap-2 border-t border-brand-mist pt-3">
                {payload.deepLink ? (
                  <a
                    href={payload.deepLink}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 rounded-lg border border-brand-mist px-3 py-1.5 text-xs font-medium text-brand-secondary hover:border-brand-stone"
                  >
                    Open at this moment in {source.label}
                  </a>
                ) : (
                  <p className="text-[11px] leading-relaxed text-brand-gray">
                    {payload.priorRun
                      ? "No deep link — the prior run was pasted as text too."
                      : `Recognised as a ${source.label} copy, but the paste carries no call id, so there is no moment to link to. The timestamp is derived from the turn that contains the quote.`}
                  </p>
                )}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* Static, not `h-${size}`: Tailwind scans source text for whole class names,
   so an interpolated one is never generated and the mark renders unsized. */
const MARK_BOX = {
  sm: "h-4 w-4",
  lg: "h-9 w-9",
} as const;

/** The tool logo, or a document glyph when provenance is not asserted. */
export function SourceMark({
  kind,
  size = "sm",
}: {
  kind: "fathom" | "zoom" | "unknown";
  size?: keyof typeof MARK_BOX;
}) {
  const meta = SOURCE_KIND_META[kind];
  const box = MARK_BOX[size];
  if (!meta.logo)
    return (
      <span
        className={`grid ${box} flex-none place-items-center rounded-md border border-brand-mist bg-brand-mist/40 text-brand-gray`}
        title={meta.label}
      >
        <FileText className={size === "lg" ? "h-4 w-4" : "h-2.5 w-2.5"} />
      </span>
    );
  return (
    <img
      src={meta.logo}
      alt={meta.label}
      title={meta.label}
      className={`${box} flex-none rounded-md border border-brand-mist bg-white object-contain p-0.5`}
    />
  );
}

/* ── The evidence chip ────────────────────────────────────────────
   Replaces the old inline expander. The logo is the affordance and the
   timestamp is the label, so the chip says where the words came from and when
   before you click it.

   A FAILED VERIFICATION IS NOT A CHIP. It stays an always-open red block: the
   whole reason that state exists is to be impossible to miss, and putting it
   behind a click would hide the one thing on the page that proves the
   substring check runs. */

export function EvidenceChip({
  row,
  index,
  transcript,
  onOpen,
}: {
  row: ResolvedRow;
  index: number;
  transcript: NormalizedTranscript | null;
  onOpen: (payload: EvidencePayload) => void;
}) {
  const citation = row.citations[index];
  const quote = row.quotes[index];

  if (!citation?.verified) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2">
        <p className="flex items-center gap-1.5 text-[11px] font-semibold text-red-800">
          <AlertTriangle className="h-3 w-3" /> Quote failed verification
        </p>
        {/* Quotation marks deliberately removed: the words could not be found
            in the transcript, so presenting them as a quote would be the exact
            thing this check exists to stop. */}
        <p className="mt-1 text-xs italic leading-relaxed text-red-700">{quote}</p>
        <p className="mt-1 text-[11px] text-red-700">
          These words do not appear in the pasted transcript.
        </p>
      </div>
    );
  }

  return (
    <button
      onClick={() =>
        onOpen({
          title: row.title,
          quote,
          speaker: citation.speaker,
          display: citation.display,
          segment: citation.segment,
          deepLink: citation.deepLink,
          turnIndex: citation.turnIndex,
          transcript,
        })
      }
      className="inline-flex items-center gap-1.5 rounded-md border border-brand-mist bg-white px-1.5 py-1 text-[11px] font-medium text-brand-gray transition-colors hover:border-brand-stone hover:text-brand-ink"
    >
      <SourceMark kind={transcript?.sourceKind ?? "unknown"} />
      <Quote className="h-3 w-3" />
      {citation.segment
        ? `in the segment starting @${citation.display}`
        : `@${citation.display}`}
    </button>
  );
}

/** The ledger item's first sighting — a different file, so labelled as one. */
export function PriorEvidenceChip({
  item,
  onOpen,
}: {
  item: LedgerItem;
  onOpen: (payload: EvidencePayload) => void;
}) {
  return (
    <button
      onClick={() =>
        onOpen({
          title: item.canonicalText,
          quote: item.firstSeenQuote,
          speaker: null,
          display: item.firstSeenDisplay,
          segment: false,
          deepLink: null,
          turnIndex: -1,
          transcript: null,
          priorRun: { run: item.firstSeenRun, label: item.firstSeenLabel },
        })
      }
      className="inline-flex items-center gap-1.5 rounded-md border border-brand-mist bg-white px-1.5 py-1 text-[11px] font-medium text-brand-gray transition-colors hover:border-brand-stone hover:text-brand-ink"
    >
      <SourceMark kind="unknown" />
      run #{item.firstSeenRun} · @{item.firstSeenDisplay}
    </button>
  );
}

export function OwnerLine({ row }: { row: ResolvedRow }) {
  const name = row.chosenOwner ?? row.owner;
  const external = row.ownerBasis === "unmapped_external";
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <span className="text-sm font-medium text-brand-ink">{name ?? "No owner yet"}</span>
      <Pill
        className={
          external
            ? "border-amber-200 bg-amber-50 text-amber-800"
            : "border-brand-mist bg-brand-mist/40 text-brand-gray"
        }
      >
        {OWNER_BASIS_LABEL[row.ownerBasis]}
      </Pill>
      {row.ownerWas && (
        <Pill className="border-brand-mist bg-white text-brand-gray">
          was {row.ownerWas}
        </Pill>
      )}
    </span>
  );
}

export function DueLine({ row }: { row: ResolvedRow }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <CalendarClock className="h-3.5 w-3.5 text-brand-slate" />
      <span className="text-sm text-brand-secondary">{row.due ?? "No date"}</span>
      {/* A default date must never render as though somebody said it. */}
      <Pill
        className={
          row.dueBasis === "default"
            ? "border-brand-mist bg-brand-mist/40 text-brand-gray"
            : "border-brand-sky/40 bg-brand-sky/10 text-brand-secondary"
        }
      >
        {DUE_BASIS_LABEL[row.dueBasis]}
      </Pill>
      {row.duePast && (
        <Pill className="border-amber-200 bg-amber-50 text-amber-800">
          already past as of this review
        </Pill>
      )}
    </span>
  );
}

/** The kind badges, shared so a kanban card and a list card read the same. */
export function RowBadges({ row }: { row: ResolvedRow }) {
  return (
    <>
      {row.ledgerId && (
        <Pill className="border-brand-primary/30 bg-brand-primary/5 text-brand-primary">
          <Layers className="h-3 w-3" /> {row.ledgerId} · this card&rsquo;s own id
        </Pill>
      )}
      {row.kind === "sighting" && row.match && (
        <Pill className="border-emerald-200 bg-emerald-50 text-emerald-700">
          sighting {row.match.item.sightings + 1} · matched, not duplicated
        </Pill>
      )}
      {row.kind === "closure_candidate" && (
        <Pill className="border-brand-sky/40 bg-brand-sky/10 text-brand-secondary">
          <HelpCircle className="h-3 w-3" /> possible closure
        </Pill>
      )}
      {row.quotes.length > 1 && (
        <Pill className="border-brand-mist bg-brand-mist/40 text-brand-gray">
          said {row.quotes.length}× in this meeting · collapsed to one item
        </Pill>
      )}
    </>
  );
}

const DECISION_ICON: Record<Decision, typeof Check> = {
  record: Check,
  not_an_item: Ban,
  closed: CheckCircle2,
  snooze: Clock,
};

const DECISION_BUTTON_LABEL: Record<Decision, string> = {
  record: "Record in ledger",
  not_an_item: "Not an item",
  closed: "Yes, I know this is closed",
  snooze: "Snooze to next run",
};

/* The closure candidate's "record" reads as a rejection of closure, not as a
   plain record, so it gets its own wording in that one context. */
const closureLabel = (row: ResolvedRow, decision: Decision) =>
  row.kind === "closure_candidate" && decision === "record"
    ? "No, still open — log the sighting"
    : DECISION_BUTTON_LABEL[decision];

export function DecisionButtons({
  row,
  onDecide,
  compact = false,
}: {
  row: ResolvedRow;
  onDecide: (decision: Decision) => void;
  compact?: boolean;
}) {
  return (
    <>
      {allowedDecisions(row).map((decision) => {
        const blocked = decisionBlockedReason(row, decision);
        const Icon = DECISION_ICON[decision];
        const on = row.decision === decision;
        const primary = decision === "record" || decision === "closed";
        return (
          <button
            key={decision}
            onClick={() => onDecide(decision)}
            disabled={Boolean(blocked)}
            aria-pressed={on}
            title={blocked ?? undefined}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 font-medium disabled:cursor-not-allowed disabled:opacity-40 ${
              compact ? "text-[11px]" : "text-xs"
            } ${
              on
                ? "border-brand-primary bg-brand-primary/10 font-semibold text-brand-primary"
                : primary
                  ? "border-transparent bg-brand-primary text-white"
                  : "border-brand-mist text-brand-secondary hover:border-brand-stone"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {compact ? DECISION_LABEL[decision] : closureLabel(row, decision)}
          </button>
        );
      })}
    </>
  );
}

export function OwnerPicker({
  row,
  onChooseOwner,
}: {
  row: ResolvedRow;
  onChooseOwner: (owner: string) => void;
}) {
  /* Where the extraction narrowed it to two, offer those two. Otherwise the
     roster, because an abstain with no reachable owner can only ever be
     dismissed, which is not the same as deciding it. */
  const options = row.ownerCandidates ?? [...WIA_ROSTER];
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-brand-gray">
        {row.ownerCandidates ? "Owner:" : "Assign to:"}
      </span>
      {options.map((candidate) => (
        <button
          key={candidate}
          onClick={() => onChooseOwner(candidate)}
          className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
            row.chosenOwner === candidate
              ? "border-brand-primary bg-brand-primary/10 text-brand-primary"
              : "border-brand-mist text-brand-secondary hover:border-brand-stone"
          }`}
        >
          {candidate}
        </button>
      ))}
    </div>
  );
}

export function RowCard({
  row,
  decided,
  transcript,
  onDecide,
  onChooseOwner,
  onOpenEvidence,
}: {
  row: ResolvedRow;
  decided: boolean;
  transcript: NormalizedTranscript | null;
  onDecide: (decision: Decision) => void;
  onChooseOwner: (owner: string) => void;
  onOpenEvidence: (payload: EvidencePayload) => void;
}) {
  const showOwnerPicker = row.kind === "abstain" && !decided;

  return (
    <article className="rounded-xl border border-brand-mist bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex flex-wrap items-center gap-1.5">
            <RowBadges row={row} />
          </div>
          <h4 className="text-sm font-semibold leading-snug text-brand-ink">{row.title}</h4>
          {row.reason && (
            <p className="mt-1.5 text-xs leading-relaxed text-brand-gray">{row.reason}</p>
          )}
          {row.question && (
            <p className="mt-1.5 rounded-lg bg-brand-mist/40 px-2.5 py-1.5 text-xs leading-relaxed text-brand-secondary">
              {row.question}
            </p>
          )}
          {row.dueNote && (
            <p className="mt-1 text-[11px] leading-relaxed text-brand-gray">{row.dueNote}</p>
          )}
        </div>
        {/* Shown as soon as the row is decided, NOT only once the whole run
            is. Without this a reviewer working through ten rows has no
            per-row feedback and the only signal is the counter in the
            header — which is how you lose your place and decide one twice. */}
        {row.decision && (
          <Pill className="border-emerald-200 bg-emerald-50 text-emerald-700">
            <Check className="h-3 w-3" /> {DECISION_LABEL[row.decision]}
          </Pill>
        )}
      </div>

      {row.kind !== "not_proposed" && (
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
          <OwnerLine row={row} />
          <DueLine row={row} />
        </div>
      )}

      {/* Prior-run evidence is shown as-is and NEVER substring-checked against
          today's paste: it came out of a different transcript. */}
      {row.match && (
        <div className="mt-3 rounded-lg border border-brand-mist bg-brand-mist/20 px-3 py-2">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-secondary">
            First recorded — run #{row.match.item.firstSeenRun}, {row.match.item.firstSeenLabel}
          </p>
          <div className="mt-1.5">
            <PriorEvidenceChip item={row.match.item} onOpen={onOpenEvidence} />
          </div>
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {row.quotes.map((_, index) => (
          <EvidenceChip
            key={index}
            row={row}
            index={index}
            transcript={transcript}
            onOpen={onOpenEvidence}
          />
        ))}
      </div>

      {showOwnerPicker && (
        <div className="mt-3">
          <OwnerPicker row={row} onChooseOwner={onChooseOwner} />
        </div>
      )}

      {!decided && row.kind !== "not_proposed" && (
        <div className="mt-3 flex flex-wrap gap-2 border-t border-brand-mist pt-3">
          <DecisionButtons row={row} onDecide={onDecide} />
        </div>
      )}
    </article>
  );
}
