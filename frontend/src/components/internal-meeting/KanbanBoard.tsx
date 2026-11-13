/* Kanban view — the review as a board.

   THE COLUMNS ARE DECISIONS, NOT CATEGORIES. A board split by row kind (new /
   sighting / abstain) would be a re-render of the list with worse density:
   nothing ever moves, because kind is fixed by the extraction. Split by
   decision, every card starts in "Waiting on you" and the board drains as the
   review progresses, which is the one thing the list view cannot show — its
   only progress signal is a counter in the sticky bar.

   DRAG IS NATIVE HTML5, NOT A LIBRARY. Five columns and fourteen cards do not
   justify a dependency, and the click path still works: the decision buttons
   are on every card, so the board is fully usable without ever dragging.

   A DROP IS A DECISION, AND SO IT OBEYS THE SAME RULES. `decisionBlockedReason`
   gates the drop exactly as it gates the buttons — the unverified row cannot be
   dragged into Recorded any more than it can be clicked into it, and a closure
   candidate has no Not-an-item column to land in. Refusals say why rather than
   silently snapping back, because a card that returns home with no explanation
   reads as a broken drag. */

import { useState } from "react";
import { Ban, Check, CheckCircle2, Clock, Inbox } from "lucide-react";
import {
  decisionBlockedReason,
  type Decision,
  type ResolvedRow,
} from "@/hooks/useInternalMeetingRun";
import type { NormalizedTranscript } from "@/lib/internalMeeting";
import {
  DecisionButtons,
  EvidenceChip,
  OwnerPicker,
  Pill,
  RowBadges,
  type EvidencePayload,
} from "./parts";

/** `null` is the undecided column — see `undecide` in the run hook. */
type ColumnKey = Decision | "undecided";

const COLUMNS: {
  key: ColumnKey;
  label: string;
  icon: typeof Check;
  accent: string;
}[] = [
  { key: "undecided", label: "Waiting on you", icon: Inbox, accent: "border-t-brand-primary" },
  { key: "record", label: "Recorded", icon: Check, accent: "border-t-emerald-500" },
  { key: "closed", label: "Closed by you", icon: CheckCircle2, accent: "border-t-brand-sky" },
  { key: "not_an_item", label: "Not an item", icon: Ban, accent: "border-t-brand-stone" },
  { key: "snooze", label: "Snoozed", icon: Clock, accent: "border-t-amber-400" },
];

export function KanbanBoard({
  rows,
  decided,
  transcript,
  onDecide,
  onUndecide,
  onChooseOwner,
  onOpenEvidence,
}: {
  rows: ResolvedRow[];
  decided: boolean;
  transcript: NormalizedTranscript | null;
  onDecide: (id: string, decision: Decision) => void;
  onUndecide: (id: string) => void;
  onChooseOwner: (id: string, owner: string) => void;
  onOpenEvidence: (payload: EvidencePayload) => void;
}) {
  const [dragId, setDragId] = useState<string | null>(null);
  const [over, setOver] = useState<ColumnKey | null>(null);
  const [refusal, setRefusal] = useState<string | null>(null);

  const dragged = rows.find((row) => row.id === dragId) ?? null;

  const canDrop = (row: ResolvedRow | null, column: ColumnKey): string | null => {
    if (!row) return "No card in hand";
    if (column === "undecided") return null;
    return decisionBlockedReason(row, column);
  };

  const drop = (column: ColumnKey) => {
    const row = dragged;
    setOver(null);
    setDragId(null);
    if (!row) return;
    const blocked = canDrop(row, column);
    if (blocked) {
      setRefusal(blocked);
      window.setTimeout(() => setRefusal(null), 3200);
      return;
    }
    if (column === "undecided") onUndecide(row.id);
    else onDecide(row.id, column);
  };

  return (
    <div>
      {refusal && (
        <p
          role="status"
          className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900"
        >
          {refusal}
        </p>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {COLUMNS.map((column) => {
          const cards = rows.filter((row) =>
            column.key === "undecided" ? !row.decision : row.decision === column.key,
          );
          const blocked = dragged ? canDrop(dragged, column.key) : null;
          const isOver = over === column.key;
          const Icon = column.icon;

          return (
            <section
              key={column.key}
              onDragOver={(event) => {
                if (decided) return;
                /* preventDefault is what marks this a valid drop target;
                   without it the browser refuses the drop silently. */
                event.preventDefault();
                setOver(column.key);
              }}
              onDragLeave={() => setOver((prev) => (prev === column.key ? null : prev))}
              onDrop={(event) => {
                event.preventDefault();
                drop(column.key);
              }}
              className={`flex min-h-[140px] flex-col rounded-xl border border-t-2 bg-brand-mist/20 p-2.5 transition-colors ${column.accent} ${
                isOver && !blocked
                  ? "border-brand-primary bg-brand-primary/5"
                  : isOver && blocked
                    ? "border-amber-300 bg-amber-50/60"
                    : "border-brand-mist"
              }`}
            >
              <header className="mb-2 flex items-center gap-1.5 px-1">
                <Icon className="h-3.5 w-3.5 text-brand-slate" />
                <h3 className="text-[11px] font-semibold uppercase tracking-wide text-brand-secondary">
                  {column.label}
                </h3>
                <span className="ml-auto rounded bg-white px-1.5 py-px text-[11px] font-bold tabular-nums text-brand-gray">
                  {cards.length}
                </span>
              </header>

              {/* The refusal reason on the column itself, while a card is in
                  hand — better than finding out after the drop. */}
              {isOver && blocked && (
                <p className="mb-2 rounded-md bg-amber-100/70 px-2 py-1 text-[10.5px] leading-snug text-amber-900">
                  {blocked}
                </p>
              )}

              <div className="space-y-2">
                {cards.map((row) => (
                  <KanbanCard
                    key={row.id}
                    row={row}
                    decided={decided}
                    transcript={transcript}
                    dragging={dragId === row.id}
                    onDragStart={() => setDragId(row.id)}
                    onDragEnd={() => {
                      setDragId(null);
                      setOver(null);
                    }}
                    onDecide={(decision) => onDecide(row.id, decision)}
                    onChooseOwner={(owner) => onChooseOwner(row.id, owner)}
                    onOpenEvidence={onOpenEvidence}
                  />
                ))}
                {cards.length === 0 && (
                  <p className="rounded-lg border border-dashed border-brand-mist px-2 py-4 text-center text-[11px] text-brand-slate">
                    {column.key === "undecided" ? "All decided" : "Nothing here"}
                  </p>
                )}
              </div>
            </section>
          );
        })}
      </div>

      {!decided && (
        <p className="mt-3 text-[11px] text-brand-gray">
          Drag a card to a column to decide it, or use the buttons on the card.
          Dragging back to <strong>Waiting on you</strong> undoes a decision.
        </p>
      )}
    </div>
  );
}

function KanbanCard({
  row,
  decided,
  transcript,
  dragging,
  onDragStart,
  onDragEnd,
  onDecide,
  onChooseOwner,
  onOpenEvidence,
}: {
  row: ResolvedRow;
  decided: boolean;
  transcript: NormalizedTranscript | null;
  dragging: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  onDecide: (decision: Decision) => void;
  onChooseOwner: (owner: string) => void;
  onOpenEvidence: (payload: EvidencePayload) => void;
}) {
  const needsOwner = row.kind === "abstain" && !row.chosenOwner && !decided;

  return (
    <article
      draggable={!decided}
      onDragStart={(event) => {
        /* Some browsers refuse to start a drag with no payload set. */
        event.dataTransfer.setData("text/plain", row.id);
        event.dataTransfer.effectAllowed = "move";
        onDragStart();
      }}
      onDragEnd={onDragEnd}
      className={`rounded-lg border border-brand-mist bg-white p-2.5 ${
        decided ? "" : "cursor-grab active:cursor-grabbing"
      } ${dragging ? "opacity-40" : ""}`}
    >
      <div className="mb-1 flex flex-wrap items-center gap-1">
        <RowBadges row={row} />
      </div>

      <h4 className="text-[12.5px] font-semibold leading-snug text-brand-ink">
        {row.title}
      </h4>

      <p className="mt-1 text-[11px] text-brand-gray">
        {row.chosenOwner ?? row.owner ?? "No owner yet"} · {row.due ?? "no date"}
      </p>

      {!row.verified && (
        <p className="mt-1.5 rounded bg-red-50 px-2 py-1 text-[10.5px] font-medium text-red-800">
          Quote failed verification — cannot be recorded
        </p>
      )}

      {row.question && (
        <p className="mt-1.5 rounded bg-brand-mist/40 px-2 py-1 text-[10.5px] leading-snug text-brand-secondary">
          {row.question}
        </p>
      )}

      <div className="mt-2 flex flex-wrap gap-1.5">
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

      {needsOwner && (
        <div className="mt-2 border-t border-brand-mist pt-2">
          <OwnerPicker row={row} onChooseOwner={onChooseOwner} />
        </div>
      )}

      {!decided && (
        <div className="mt-2 flex flex-wrap gap-1.5 border-t border-brand-mist pt-2">
          <DecisionButtons row={row} onDecide={onDecide} compact />
        </div>
      )}

      {decided && row.decision && (
        <div className="mt-2">
          <Pill className="border-emerald-200 bg-emerald-50 text-emerald-700">
            <Check className="h-3 w-3" /> decided
          </Pill>
        </div>
      )}
    </article>
  );
}
