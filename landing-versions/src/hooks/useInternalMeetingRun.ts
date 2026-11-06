import { useCallback, useMemo, useRef, useState } from "react";
import {
  deriveCitation,
  fingerprint,
  normalizeTranscript,
  similarity,
  type Citation,
  type NormalizedTranscript,
} from "@/lib/internalMeeting";
import {
  DEMO_ROWS,
  PRIOR_RUN_NUMBER,
  REVIEW_DATE,
  RUN_NUMBER,
  SEEDED_LEDGER,
  STAGES,
  TOUCHED_LEDGER_IDS,
  type ExtractedRow,
  type LedgerItem,
} from "@/data/internalMeeting";

/* ────────────────────────────────────────────────────────────────
   The run state machine.

   TERMINATES AT THE REVIEW. `decided` is the last state there is: recording a
   decision writes to this card's own ledger and nothing else. There is no
   commit stage, no queue and no pending write, which is why none of the
   failure modes that come with external writes — partial batches, retries,
   idempotency, token expiry — exist anywhere in this file.
   ──────────────────────────────────────────────────────────────── */

export type RunState = "idle" | "running" | "review" | "decided";

/** What a human can say about one row. `undefined` = not yet decided. */
export type Decision = "record" | "not_an_item" | "closed" | "snooze";

export interface ResolvedRow extends ExtractedRow {
  /** One citation per quote, each verified live against the paste. */
  citations: Citation[];
  /** Every quote survived the literal-substring check. */
  verified: boolean;
  /** Ledger row this matched, with the similarity that matched it. */
  match: { item: LedgerItem; score: number } | null;
  decision?: Decision;
  /** Owner chosen by the reviewer on an abstain. */
  chosenOwner?: string;
}

const DECIDABLE = new Set(["new", "sighting", "closure_candidate", "abstain", "unverified"]);

/* ── One rulebook for what a row may be decided as ────────────────
   Exported because three surfaces now offer decisions — the list card, the
   kanban drop target and the table row — and a rule that lives in the JSX of
   one of them is a rule the other two can contradict. The closure candidate
   is the case that matters: it may only be closed or logged as a sighting,
   never dismissed, and a board that let you drop it into "Not an item" would
   quietly invent a fourth option the list view refuses to show. */
export function allowedDecisions(row: ResolvedRow): Decision[] {
  if (row.kind === "not_proposed") return [];
  if (row.kind === "closure_candidate") return ["closed", "record"];
  return ["record", "not_an_item", "snooze"];
}

/** Why this decision is unavailable, or null when it is allowed. */
export function decisionBlockedReason(
  row: ResolvedRow,
  decision: Decision,
): string | null {
  if (!allowedDecisions(row).includes(decision))
    return `A ${row.kind.replace(/_/g, " ")} row cannot be ${decision.replace(/_/g, " ")}`;
  if (decision !== "record") return null;
  if (!row.verified)
    return "Fix the quote first — it could not be verified against the transcript";
  if (row.kind === "abstain" && !row.chosenOwner) return "Choose an owner first";
  return null;
}

export function useInternalMeetingRun() {
  const [state, setState] = useState<RunState>("idle");
  const [text, setText] = useState("");
  const [transcript, setTranscript] = useState<NormalizedTranscript | null>(null);
  const [stageIndex, setStageIndex] = useState(-1);
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const [owners, setOwners] = useState<Record<string, string>>({});
  const [ledger, setLedger] = useState<LedgerItem[]>(SEEDED_LEDGER);
  const [ledgerVersion, setLedgerVersion] = useState(23);
  const timers = useRef<number[]>([]);

  const clearTimers = () => {
    timers.current.forEach((id) => window.clearTimeout(id));
    timers.current = [];
  };

  /** Parse, verify and match — all of it real — then walk the stage display. */
  const start = useCallback(
    (raw: string) => {
      clearTimers();
      const normalized = normalizeTranscript(raw);
      setTranscript(normalized);
      setState("running");
      setStageIndex(0);

      let elapsed = 0;
      STAGES.forEach((stage, index) => {
        elapsed += stage.holdMs;
        timers.current.push(
          window.setTimeout(() => {
            if (index === STAGES.length - 1) {
              setStageIndex(STAGES.length);
              setState("review");
            } else {
              setStageIndex(index + 1);
            }
          }, elapsed),
        );
      });
    },
    [],
  );

  const reset = useCallback(() => {
    clearTimers();
    setState("idle");
    setText("");
    setTranscript(null);
    setStageIndex(-1);
    setDecisions({});
    setOwners({});
    setLedger(SEEDED_LEDGER);
    setLedgerVersion(23);
  }, []);

  /* Citations and ledger matches are computed from the PARSED transcript, so
     they change if the pasted text changes. Nothing here is hard-coded. */
  const rows = useMemo<ResolvedRow[]>(() => {
    if (!transcript) return [];
    return DEMO_ROWS.map((row) => {
      const citations = row.quotes.map((quote) => deriveCitation(transcript, quote));
      const seeded = row.ledgerId
        ? (SEEDED_LEDGER.find((item) => item.ledgerId === row.ledgerId) ?? null)
        : null;
      return {
        ...row,
        citations,
        verified: citations.every((citation) => citation.verified),
        match: seeded
          ? { item: seeded, score: similarity(fingerprint(seeded.canonicalText), fingerprint(row.title)) }
          : null,
        decision: decisions[row.id],
        chosenOwner: owners[row.id],
      };
    });
  }, [transcript, decisions, owners]);

  const groups = useMemo(() => {
    const by = (kind: string) => rows.filter((row) => row.kind === kind);
    return {
      sightings: by("sighting"),
      closure: by("closure_candidate"),
      new: by("new"),
      abstains: by("abstain"),
      unverified: by("unverified"),
      notProposed: by("not_proposed"),
      /* The aging view: open ledger items this transcript never mentioned.
         Without it the register silently accumulates, and "what has been
         hanging around for three weeks" stays unanswerable.

         Both exclusions are needed. Dropping only the matched ids leaves the
         rows minted BY this run — they carry ids nothing has matched yet — so
         after Finish review the list would claim the items just recorded were
         never mentioned. */
      untouched: ledger.filter(
        (item) =>
          !TOUCHED_LEDGER_IDS.includes(item.ledgerId) && item.firstSeenRun !== RUN_NUMBER,
      ),
    };
  }, [rows, ledger]);

  const decidable = rows.filter((row) => DECIDABLE.has(row.kind));
  const undecided = decidable.filter((row) => !row.decision);

  const decide = useCallback((id: string, decision: Decision) => {
    setDecisions((prev) => ({ ...prev, [id]: decision }));
  }, []);

  /* Dragging a card back to "Waiting on you" is an undo, and it has to clear
     the key rather than store a fifth decision value — `undecided` is derived
     from the absence of one, so writing a sentinel here would leave the
     Finish-review counter permanently satisfied. */
  const undecide = useCallback((id: string) => {
    setDecisions((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }, []);

  const chooseOwner = useCallback((id: string, owner: string) => {
    setOwners((prev) => ({ ...prev, [id]: owner }));
  }, []);

  /**
   * The terminal action. Writes to this card's ledger and nowhere else.
   *
   * Returns the receipt the toast reads, so the caller never has to recompute
   * what happened.
   */
  const record = useCallback(() => {
    const recorded = decidable.filter((row) => row.decision === "record");
    const closed = decidable.filter((row) => row.decision === "closed");
    const dismissed = decidable.filter((row) => row.decision === "not_an_item");
    const snoozed = decidable.filter((row) => row.decision === "snooze");

    setLedger((prev) => {
      const next = [...prev];
      let seq = prev.length;
      for (const row of recorded) {
        const existing = row.ledgerId
          ? next.findIndex((item) => item.ledgerId === row.ledgerId)
          : -1;
        if (existing >= 0) {
          /* A sighting appends to the existing row. It never mints a second
             one — this is the whole point of the card. */
          next[existing] = {
            ...next[existing],
            sightings: next[existing].sightings + 1,
            owner: row.chosenOwner ?? row.owner ?? next[existing].owner,
          };
        } else {
          seq += 1;
          next.push({
            ledgerId: `LGR-${String(seq).padStart(4, "0")}`,
            canonicalText: row.title,
            owner: row.chosenOwner ?? row.owner,
            ownerBasis: row.ownerBasis,
            firstSeenRun: RUN_NUMBER,
            firstSeenLabel: "2 Sep",
            firstSeenDisplay: row.citations[0]?.display ?? "—",
            firstSeenQuote: row.quotes[0],
            sightings: 1,
            ageDays: 0,
          });
        }
      }
      for (const row of closed) {
        const at = next.findIndex((item) => item.ledgerId === row.ledgerId);
        if (at >= 0) next.splice(at, 1);
      }
      return next;
    });
    setLedgerVersion(24);
    setState("decided");

    return {
      recorded: recorded.length,
      sightings: recorded.filter((row) => row.ledgerId).length,
      closed: closed.length,
      dismissed: dismissed.length,
      snoozed: snoozed.length,
    };
  }, [decidable]);

  return {
    state,
    text,
    setText,
    transcript,
    stageIndex,
    rows,
    groups,
    decidable,
    undecided,
    ledger,
    ledgerVersion,
    priorRun: PRIOR_RUN_NUMBER,
    runNumber: RUN_NUMBER,
    reviewDate: REVIEW_DATE,
    start,
    reset,
    decide,
    undecide,
    chooseOwner,
    record,
  };
}

/* ── Exports ──────────────────────────────────────────────────────
   The two that matter are the ClickUp manifest and the Slack digest, because
   they are what the reviewer does in the ninety seconds AFTER this screen —
   retype the tasks and paste a digest. Copying them is what makes stopping
   short of a write layer feel deliberate rather than unfinished. */

const owner = (row: ResolvedRow) => row.chosenOwner ?? row.owner ?? "unassigned";

/** Tab-delimited, in the shape ClickUp's bulk paste accepts. */
export function toClickUpManifest(rows: ResolvedRow[]): string {
  const lines = rows
    .filter((row) => row.decision === "record")
    .map((row) => [row.title, owner(row), row.due ?? ""].join("\t"));
  return ["Task Name\tAssignee\tDue Date", ...lines].join("\n");
}

/** Grouped by person, because that is how the digest is read. */
export function toSlackDigest(rows: ResolvedRow[], reviewDate: string): string {
  const recorded = rows.filter((row) => row.decision === "record");
  const byOwner = new Map<string, ResolvedRow[]>();
  for (const row of recorded) {
    const key = owner(row);
    byOwner.set(key, [...(byOwner.get(key) ?? []), row]);
  }
  const blocks = [...byOwner.entries()].map(([person, items]) =>
    [
      `*${person}*`,
      ...items.map((row) => {
        const when = row.due ? ` — due ${row.due}` : "";
        return `• ${row.title}${when}`;
      }),
    ].join("\n"),
  );
  return [
    `*Monday recap — reviewed ${reviewDate}*`,
    ...blocks,
    "",
    "_Recorded from the meeting transcript and reviewed before posting._",
  ].join("\n\n");
}

export function toMarkdown(rows: ResolvedRow[], reviewDate: string): string {
  const section = (title: string, list: ResolvedRow[]) =>
    list.length
      ? [
          `## ${title}`,
          "",
          ...list.map((row) => {
            const cite = row.citations[0];
            const stamp = cite?.display
              ? cite.segment
                ? ` _(in the segment starting @${cite.display})_`
                : ` _(@${cite.display})_`
              : "";
            const due = row.due ? ` · due ${row.due}` : "";
            return `- **${row.title}** — ${owner(row)}${due}${stamp}\n  > ${row.quotes[0]}`;
          }),
          "",
        ].join("\n")
      : "";

  return [
    `# Internal Meeting + Action Items — reviewed ${reviewDate}`,
    "",
    "Recorded in this card's own ledger. Nothing was sent to ClickUp, Slack or Drive.",
    "",
    section("Recorded", rows.filter((r) => r.decision === "record")),
    section("Closed by a human", rows.filter((r) => r.decision === "closed")),
    section("Not an item", rows.filter((r) => r.decision === "not_an_item")),
  ]
    .filter(Boolean)
    .join("\n");
}

export function toLedgerExport(ledger: LedgerItem[]): string {
  return JSON.stringify({ version: 24, exportedFor: "Wedding Industry Ads", items: ledger }, null, 2);
}
