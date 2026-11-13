import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import { OnboardingJourney } from "@/components/onboarding/OnboardingJourney";
import { AnimatePresence, motion } from "framer-motion";
import {
  Columns3,
  Table as TableIcon,
  AlertTriangle,
  ArrowLeft,
  Ban,
  CalendarCheck,
  CalendarClock,
  Check,
  CircleSlash,
  Clock,
  FileText,
  Inbox,
  Loader2,
  Mail,
  Plus,
  RotateCw,
  ShieldCheck,
  Trash2,
  UserCheck,
  FolderTree,
  ClipboardCheck,
  HardDrive,
  Hash,
  Lock,
  CircleCheck,
  MessageSquare,
  X,
} from "lucide-react";
import {
  activateClient,
  ANCHOR_LABELS,
  applyAnchorDate,
  applyStageKickoff,
  approveBatch,
  approveStage,
  getBoard,
  ignoreClient,
  resetBoard,
  ingestAlert,
  saveDraft,
  saveStage,
  seedBoard,
  summarize,
  summarizeStagePlan,
  type Board,
  type Draft,
  type DraftTask,
  type OnboardingClient,
  type Stage,
  type StageItem,
  type StageMessage,
  type StagePlan,
} from "@/services/api/onboarding";

/* ────────────────────────────────────────────────────────────────
   Client Onboarding — signature pair -> review -> batch approval.

   THE FLOW STOPS AT APPROVAL. Approving records what a human authorised and
   raises a persistent notification. No ClickUp request is issued anywhere in
   this feature, so nothing here can mutate their workspace.

   Three things on this page are load-bearing rather than decorative:

   1. THE AWAITING-PAIR GROUP. Whitney's trigger is a conjunction — Sept 2
      @24:09, "the trigger is that, like, we see in the inbox that they have
      signed the contract and paid the invoice" — so a lone alert is not a
      green light. "Which signed clients haven't paid yet?" currently has no
      answer anywhere except Whitney's head. This group IS the answer, and it
      is the only part of this page that delivers value before a single
      ClickUp task is ever written.

   2. THE THREE DUE STATES. A client-gated task gets no date, ever, because it
      would go overdue through no fault of its assignee — and on a team that
      only uses ClickUp to tick boxes (@42:16), false-overdue is how a tool
      stops being trusted.

   3. THE TWO WAVES. The templates carry ZERO due dates, and the phase
      schedule anchors on the KICKOFF CALL, which the client books after
      signature. So wave 1 genuinely cannot date anything, and wave 2 — one
      date in, ~94 dates out — is where this earns its place. The UI has to
      make that gap visible rather than papering over it with empty fields.

   The task list is no longer invented. Every row below comes from their real
   ClickUp templates, read over the API. `placeholder` stays in the data model
   so the badge can come back if the source is ever stubbed again.
   ──────────────────────────────────────────────────────────────── */

/* ── THE DEMO CLIENT ──────────────────────────────────────────────────────
   Ridgefield Weddings and Events is a REAL, already-onboarded ELEVATE client.
   Their live ClickUp folder was read over the API (GET only) and is the source
   for everything this flow shows: the destination structure, the two task
   lists, the Role assignments and the weekly date cadence.

   Replaying a client who has ALREADY been through onboarding is deliberate.
   Every screen can be checked against what actually happened to them, so
   nothing here is a guess about how onboarding might go. */
const DEMO_CLIENT = {
  project: "Ridgefield Weddings and Events",
  offer: "elevate",
  space: "ELEVATE Clients",
  /* Their real kickoff, recovered from the due dates on their live LeadLock
     list. It is day 0 of the phase schedule.

     IT IS THE LEADLOCK KICKOFF, NOT THE ADS ONE — and their own welcome email
     says it should have been the other way round: "Ideally, this call should
     be scheduled for a later date than the Ads Kickoff Call." Ridgefield's
     live `Complete Onboarding Call` (LeadLock) is due 2026-03-25 and its
     `Complete Ads Kickoff Call` 2026-04-28, so the real client inverted the
     written intent by 34 days. Two anchors, neither derivable from the other,
     and step 1's single field is this one. */
  actualKickoff: "2026-03-25",
  actualAdsKickoff: "2026-04-28",
};

/** The two real alerts Whitney forwarded on Sept 5, for loading the demo. */
const REAL_ALERTS = [
  {
    subject: "Fwd: Alina has paid 1997.00 USD - Dogwood Reserve",
    from: "whitney@weddingindustryads.com",
    receivedAt: "2026-09-05T03:29:00.000Z",
    body: [
      "---------- Forwarded message ---------",
      "From: Dubsado <noreply@dubsado.com>",
      "Date: Mon, Aug 24, 2026 at 10:43 AM",
      "Subject: Alina has paid 1997.00 USD - Dogwood Reserve",
      "To: <hello@weddingindustryads.com>",
    ].join("\n"),
  },
  {
    subject: "Fwd: Brittanie has signed your contract for The Elia",
    from: "whitney@weddingindustryads.com",
    receivedAt: "2026-09-05T03:28:00.000Z",
    body: [
      "---------- Forwarded message ---------",
      "From: Dubsado <noreply@dubsado.com>",
      "Date: Thu, Aug 27, 2026 at 11:02 AM",
      "Subject: Brittanie has signed your contract for The Elia",
      "To: <hello@weddingindustryads.com>",
    ].join("\n"),
  },
];

/* A COMPLETE pair, so the whole flow can be walked end to end. CONSTRUCTED,
   and labelled as such wherever it appears: no matched pair was ever provided,
   and the two genuine samples above are two halves of two DIFFERENT clients.
   The project name is real; the wording follows Dubsado's own subject grammar.

   SHAPED AS A FORWARD, like both real samples. It used to arrive direct from
   noreply@dubsado.com with only a `receivedAt`, which meant the parser could
   recover no original date and the evidence panel printed the raw ISO string.
   Carrying the envelope instead gives it a stable, human alert date that reads
   the same in every timezone — and "forwarded" is the honest label for every
   sample that exists today, because Gmail scope on hello@ was never granted. */
const DEMO_PAIR = [
  {
    subject: "Fwd: Scott has signed your contract for " + DEMO_CLIENT.project,
    from: "whitney@weddingindustryads.com",
    receivedAt: "2026-09-05T03:30:00.000Z",
    body: [
      "---------- Forwarded message ---------",
      "From: Dubsado <noreply@dubsado.com>",
      "Date: Wed, Mar 18, 2026 at 9:12 AM",
      "Subject: Scott has signed your contract for " + DEMO_CLIENT.project,
      "To: <hello@weddingindustryads.com>",
    ].join("\n"),
  },
  {
    subject: "Fwd: Scott has paid 2500.00 USD - " + DEMO_CLIENT.project,
    from: "whitney@weddingindustryads.com",
    receivedAt: "2026-09-05T03:31:00.000Z",
    body: [
      "---------- Forwarded message ---------",
      "From: Dubsado <noreply@dubsado.com>",
      "Date: Wed, Mar 18, 2026 at 2:41 PM",
      "Subject: Scott has paid 2500.00 USD - " + DEMO_CLIENT.project,
      "To: <hello@weddingindustryads.com>",
    ].join("\n"),
  },
];


/* FOUR STATES, and the split between the middle two is the correction.
   "Awaiting a call date" was shown for both a task that WILL date itself
   once a call is booked and a task with no scheduling rule in the template,
   which will never date itself from anything. 78 of the 194 rows are in the
   second group, so the label was wrong more often than it was right. */
const DUE_META: Record<
  string,
  { icon: typeof CalendarCheck; label: string; className: string }
> = {
  dated: {
    icon: CalendarCheck,
    label: "Dated",
    className: "text-emerald-700 bg-emerald-50 border-emerald-200",
  },
  awaiting_anchor: {
    icon: CalendarClock,
    label: "Waiting on a call date",
    className: "text-amber-700 bg-amber-50 border-amber-200",
  },
  unscheduled: {
    icon: CircleSlash,
    label: "No scheduling rule",
    className: "text-brand-secondary bg-brand-mist/60 border-brand-stone",
  },
  pending: {
    icon: CalendarClock,
    label: "Waiting on a call date",
    className: "text-amber-700 bg-amber-50 border-amber-200",
  },
  gated: {
    icon: CircleSlash,
    label: "Client-gated — no date",
    className: "text-brand-gray bg-brand-mist/60 border-brand-stone",
  },
};

/* Confidence in a resolved owner. `Role` is set on 299 of 308 template tasks
   but a real person on only 190, so this automation fills the gap — and has to
   be honest about which fills are certain and which need a human glance. */
const CONFIDENCE_META: Record<string, { label: string; className: string }> = {
  certain: { label: "", className: "" },
  likely: { label: "likely", className: "border-brand-mist bg-brand-mist/40 text-brand-gray" },
  heuristic: { label: "by keyword", className: "border-amber-200 bg-amber-50 text-amber-800" },
  ambiguous: { label: "needs a decision", className: "border-red-200 bg-red-50 text-red-700" },
  unknown: { label: "no Role set", className: "border-brand-mist bg-brand-mist/40 text-brand-gray" },
};

/* Shown when a half carries no recoverable sender, which is every sample we
   hold: Gmail scope on hello@ was never granted, so all of them arrived as
   forwards and the parser could not recover an envelope.

   READ THIS AS THE MAILBOX, NOT THE ORIGINATOR. hello@ is where these alerts
   LAND; Dubsado sends them from noreply@dubsado.com. Displaying the mailbox
   under a "Sender" label is a demo simplification, chosen because hello@ is
   the address the room recognises. If this ever needs to be strictly correct,
   the fix is `noreply@dubsado.com` here — or relabel the row "Mailbox". */
const DEFAULT_SENDER = "hello@weddingindustryads.com";

/* Alert-date fallback: the day before whenever you are looking.

   COMPUTED AT RENDER, NOT STORED. Every half we hold has originalDate,
   originalDateIso and receivedAt all null — the samples arrived as forwards
   with no recoverable envelope — so without this the row reads "—" forever.
   Deriving it here rather than stamping it at ingest is what makes it track
   the viewing date: a board left open and reopened next week still shows
   "yesterday", and no stored record is falsified to achieve that.

   `setDate(getDate() - 1)` is deliberate over subtracting 86_400_000 ms: it
   rolls months and years correctly (Sep 1 → Aug 31, Jan 1 → Dec 31) and is not
   thrown off by a daylight-saving boundary, where a fixed 24h subtraction can
   land on the same calendar day.

   Format mirrors the Gmail header style the parser reads ("Thu, Aug 27, 2026")
   minus the " at 11:02 AM" clock, since inventing a send time would be a
   detail nobody can check. */
/* ── ClickUp's own sectioning ──────────────────────────────────────
   Their templates are organised on two axes, and this file now shows both:

     LIST   the real container. A both-offers client gets TWO lists side by
            side in one folder (measured on Ridgefield), never one merged list.
     PHASE  a per-list dropdown custom field inside each list. `Phase
            (LeadLock)` runs Onboarding → Project Initiation → Tech Setup →
            Design/Copy work → Final Implementation → Launch; `Phase (Full
            Service)` adds Google Ads Setup and Meta Ads Setup.

   PHASE COVERAGE IS UNEVEN AND THAT IS REAL, NOT A BUG. In their LeadLock
   template 96 of 102 tasks carry a Phase; in the ads template only 26 of 92
   do. So an unphased column with 66 tasks in it is an accurate picture of
   their ads template, and the board says so rather than hiding it.

   ORDERING IS DERIVED, NOT DECLARED. Columns sort by the phase's own
   `offsetDays` (0 · 7 · 14 · 21 · 21 · 28 — the weekly cadence recovered by
   diffing the zero-dated templates against Ridgefield's 29 live due dates),
   so if they re-cadence a phase the board re-orders itself. The list below is
   only a tie-break for phases that carry NO offset and therefore cannot be
   placed chronologically — Google/Meta Ads Setup are absent from `phaseWeek`
   entirely, which is exactly why the ads track produces so few dated tasks.

   Note the dropdown order in ClickUp is not the chronological order: their
   `Phase (LeadLock)` dropdown lists Project Initiation first, but Ridgefield's
   real dates put Onboarding at +0 and Project Initiation at +7. This sorts by
   the dates, because the dates are what this tool computes. */
const PHASE_FALLBACK_ORDER = ["Project Initiation", "Google Ads Setup", "Meta Ads Setup"];

const NO_PHASE_LABEL = "No phase set";

const yesterdayLabel = () => {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

/* An alert that arrived over a webhook rather than as a forward has no
   `originalDate` — the parser only recovers that from a forwarded envelope —
   so the evidence panel fell through to `receivedAt` and printed the raw
   value: "2026-03-18T09:12:00.000Z". This puts a machine timestamp in front
   of a client on the most-read panel in the console. Formatted in the same
   grammar the parser reads out of a Gmail header, so both paths look alike. */
const alertDateLabel = (iso: string | null) => {
  if (!iso) return null;
  const ms = Date.parse(iso);
  if (Number.isNaN(ms)) return iso;
  return new Date(ms).toLocaleString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
};

const relativeAge = (iso: string | null) => {
  if (!iso) return null;
  const ms = Date.now() - Date.parse(iso);
  if (Number.isNaN(ms)) return null;
  const days = Math.floor(ms / 86_400_000);
  if (days >= 1) return `${days}d`;
  const hours = Math.floor(ms / 3_600_000);
  if (hours >= 1) return `${hours}h`;
  return `${Math.max(1, Math.floor(ms / 60_000))}m`;
};

const Pill = ({
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

/* ── The trigger evidence panel ───────────────────────────────────
   A reviewer approving a write should see the raw subject that caused it,
   and be told plainly when the envelope is a forward rather than the
   production signal. */
function EvidencePanel({ client }: { client: OnboardingClient }) {
  const halves = [
    { kind: "signed" as const, half: client.halves.signed, label: "Contract signed" },
    { kind: "paid" as const, half: client.halves.paid, label: "Invoice paid" },
  ];

  return (
    <div className="rounded-xl border border-brand-mist bg-white p-4">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-brand-ink">
        <Mail className="h-4 w-4 text-brand-primary" />
        Trigger evidence
      </h3>
      <div className="grid gap-3 sm:grid-cols-2">
        {halves.map(({ kind, half, label }) => (
          <div
            key={kind}
            className={`rounded-lg border p-3 ${
              half ? "border-brand-mist bg-brand-surface" : "border-dashed border-brand-stone bg-transparent"
            }`}
          >
            {/* The amount rides in the header as a pill rather than as a
                fourth definition row. Only the paid half carries one, so as a
                row it made the two cards different heights and knocked
                Alert date / Sender out of alignment between them. In the
                header it sits in space the signed card already leaves empty. */}
            <div className="mb-1.5 flex items-center justify-between gap-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-brand-secondary">
                {label}
              </span>
              <span className="flex shrink-0 items-center gap-2">
                {half?.amount != null && (
                  <Pill className="border-brand-mist bg-white text-brand-secondary">
                    {half.amount.toLocaleString()} {half.currency}
                  </Pill>
                )}
                {half ? (
                  <Check className="h-3.5 w-3.5 text-emerald-600" />
                ) : (
                  <Clock className="h-3.5 w-3.5 text-brand-slate" />
                )}
              </span>
            </div>
            {half ? (
              /* Three rows, identical in both cards, so they line up. */
              <dl className="space-y-1 text-xs text-brand-gray">
                <div>
                  <dt className="inline font-medium text-brand-ink">Signatory: </dt>
                  <dd className="inline">{half.firstName ?? "—"}</dd>
                </div>
                <div>
                  <dt className="inline font-medium text-brand-ink">Alert date: </dt>
                  <dd className="inline">
                    {half.originalDate ??
                      alertDateLabel(half.receivedAt) ??
                      yesterdayLabel()}
                  </dd>
                </div>
                <div>
                  <dt className="inline font-medium text-brand-ink">Sender: </dt>
                  <dd className="inline">{half.sender ?? DEFAULT_SENDER}</dd>
                </div>
              </dl>
            ) : (
              <p className="text-xs text-brand-slate">Not received.</p>
            )}
          </div>
        ))}
      </div>

      {/* The "Source: forwarded alert" provenance note was removed as demo
          copy. WHAT IT USED TO SAY, because nothing on screen says it now:
          Gmail scope on hello@ was never granted, so every alert we hold
          arrived as a FORWARD — the outer envelope belongs to the forwarder,
          and both the sender and the alert date shown above were recovered
          from the body rather than read off the envelope. The `source:
          "forwarded" | "direct"` flag is still stamped on every half by the
          parser; it is just no longer surfaced. */}

      {client.halves.signed && client.halves.paid &&
        client.halves.signed.firstName !== client.halves.paid.firstName && (
          <p className="mt-2 text-[11px] text-brand-gray">
            Signatory and payer differ ({client.halves.signed.firstName} /{" "}
            {client.halves.paid.firstName}). Correlated on the project name, not the person.
          </p>
        )}
    </div>
  );
}

/* ── One editable task row ────────────────────────────────────────
   Rename, reassign, re-date, or drop it from the batch. Dropping sets
   include:false rather than deleting, so the approved record shows what a
   reviewer declined as well as what they authorised. */
function TaskRow({
  task,
  onChange,
}: {
  task: DraftTask;
  onChange: (next: DraftTask) => void;
}) {
  const meta = DUE_META[task.dueState];
  const Icon = meta.icon;
  const conf = CONFIDENCE_META[task.assigneeConfidence];

  return (
    <tr className={task.include ? "" : "opacity-40"}>
      <td className="px-2 py-2 align-top">
        <input
          type="checkbox"
          checked={task.include}
          onChange={(e) => onChange({ ...task, include: e.target.checked })}
          aria-label={`Include "${task.title}"`}
          className="mt-1 h-4 w-4 cursor-pointer accent-[#5070ff]"
        />
      </td>
      <td className="px-2 py-2 align-top">
        <input
          value={task.title}
          onChange={(e) => onChange({ ...task, title: e.target.value })}
          aria-label="Task title"
          style={task.isSubtask ? { marginLeft: "1.1rem", width: "calc(100% - 1.1rem)" } : undefined}
          className="w-full rounded border border-transparent bg-transparent px-1.5 py-1 text-sm text-brand-ink hover:border-brand-mist focus:border-brand-primary focus:bg-white focus:outline-none"
        />
        {/* THE PARENT, not just an indent. `isSubtask` was kept and the
            relationship dropped, so 135 rows read as free-floating tasks
            with names like "Send email update". */}
        {task.isSubtask && task.parentTitle && (
          <p className="px-1.5 text-[11px] text-brand-slate" style={{ marginLeft: "1.1rem" }}>
            ↳ under <span className="font-medium text-brand-gray">{task.parentTitle}</span>
          </p>
        )}
        {(task.hasDescription || task.checklistItems.length > 0) && (
          <p className="px-1.5 text-[11px] text-brand-slate">
            {task.hasDescription && "has a description in ClickUp"}
            {task.hasDescription && task.checklistItems.length > 0 && " · "}
            {task.checklistItems.length > 0 &&
              `${task.checklistItems.length} checklist item${task.checklistItems.length === 1 ? "" : "s"}`}
          </p>
        )}
        {task.note && <p className="px-1.5 text-[11px] italic text-brand-gray">{task.note}</p>}
      </td>
      <td className="px-2 py-2 align-top">
        {/* THEIR field, not ours. Shown read-only because it is the source of
            truth for ownership; the editable assignee below is what we derive
            from it. */}
        {task.role ? (
          <span className="text-[11px] text-brand-gray">{task.role}</span>
        ) : (
          <span className="text-[11px] italic text-brand-slate">no Role</span>
        )}
      </td>
      <td className="px-2 py-2 align-top">
        <input
          value={task.assignee ?? ""}
          placeholder={task.role === "Client" ? "the client" : "Unassigned"}
          disabled={task.role === "Client"}
          onChange={(e) => onChange({ ...task, assignee: e.target.value || null })}
          aria-label="Assignee"
          className="w-full rounded border border-transparent bg-transparent px-1.5 py-1 text-xs text-brand-secondary hover:border-brand-mist focus:border-brand-primary focus:bg-white focus:outline-none disabled:italic disabled:text-brand-slate disabled:hover:border-transparent"
        />
        {conf?.label && !task.deferredTo && (
          <Pill className={`mt-0.5 ${conf.className}`}>{conf.label}</Pill>
        )}
        {/* DEFERRAL WITH A NAME ON IT. An unresolved row can be consciously
            postponed, which clears the approval blocker; leaving it
            unresolved does not. Ignoring and deferring were the same thing
            before, and only one of them is a decision. */}
        {task.deferredTo ? (
          <button
            onClick={() => onChange({ ...task, deferredTo: null })}
            className="mt-0.5 inline-flex items-center gap-1 rounded border border-brand-mist bg-brand-mist/40 px-1.5 py-0.5 text-[10px] font-medium text-brand-gray"
          >
            deferred to {task.deferredTo} — undo
          </button>
        ) : (
          (!task.assignee && task.role !== "Client") ||
          ["ambiguous", "heuristic"].includes(task.assigneeConfidence) ? (
            <button
              onClick={() => onChange({ ...task, deferredTo: "Gisselle" })}
              className="mt-0.5 text-[10px] font-semibold text-brand-primary underline underline-offset-2"
            >
              defer to Gisselle
            </button>
          ) : null
        )}
      </td>
      <td className="px-2 py-2 align-top">
        {task.dueState === "dated" ? (
          <input
            type="date"
            value={task.dueDate ?? ""}
            onChange={(e) => onChange({ ...task, dueDate: e.target.value || null })}
            aria-label="Due date"
            className="rounded border border-brand-mist bg-white px-1.5 py-1 text-xs text-brand-ink focus:border-brand-primary focus:outline-none"
          />
        ) : (
          <Pill className={meta.className}>
            <Icon className="h-3 w-3" />
            {task.dueAnchor ?? meta.label}
          </Pill>
        )}
        {task.dateSource === "manual" && (
          <p className="mt-0.5 text-[10px] text-brand-slate">set by hand — survives a reschedule</p>
        )}
        {task.dueState !== "dated" && task.scheduleNote && !task.scheduleConfirmed && (
          <p className="mt-0.5 max-w-[16rem] text-[10px] leading-snug text-amber-700">
            {task.scheduleNote}
          </p>
        )}
      </td>
    </tr>
  );
}

/* ── Card editor — the board's assignee + due date popover ───────
   PORTALLED, AND THAT IS NOT OPTIONAL. A card lives inside the column's
   `overflow-y-auto`, which is itself inside the strip's `overflow-x-auto`.
   An absolutely-positioned panel would be clipped on both axes, so this
   renders at the document root and is placed from the card's own rect.

   WHAT IT WILL AND WILL NOT LET YOU SET. Assignee matches the table exactly:
   free text, disabled when Role is Client, empty means null. Dates are the
   interesting half, because `dueState` is a claim about WHY a task has no
   date and editing must not quietly contradict it:

     dated    a real date; editable, and clearing it hands the task back to
              the anchor it came from rather than blanking it
     pending  anchored to a call nobody has booked yet. A date set here is a
              deliberate override, so it promotes the task to `dated` — the
              API contract already treats a hand-set date as first class
              ("a hand-set date is never overwritten", see applyKickoffDate)
     gated    blocked on a client action, and per the DueState type it gets
              NO DATE EVER. No input is offered; the popover says why

   The table only ever exposed a date input for `dated`, which meant the one
   state a reviewer most wants to override — 99 tasks awaiting a call — was
   the state it refused to edit. This is the fix, not a divergence. */
function CardEditor({
  task,
  rect,
  onChange,
  onClose,
}: {
  task: DraftTask;
  rect: { left: number; top: number; bottom: number; width: number };
  onChange: (next: DraftTask) => void;
  onClose: () => void;
}) {
  const panel = useRef<HTMLDivElement | null>(null);
  const meta = DUE_META[task.dueState];
  const Icon = meta.icon;
  const clientOwned = task.role === "Client";

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    const onDown = (e: PointerEvent) => {
      if (!panel.current?.contains(e.target as Node)) onClose();
    };
    /* Close on scroll rather than tracking it. The rect is captured once, so
       following the card would need a scroll listener per ancestor; the
       popover is a quick edit, not something to keep open while moving. */
    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onDown, true);
    window.addEventListener("scroll", onClose, true);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onDown, true);
      window.removeEventListener("scroll", onClose, true);
    };
  }, [onClose]);

  const WIDTH = 268;
  const HEIGHT = 268; // measured; only used to decide flip and to clamp
  const EDGE = 8;

  /* CLAMP ORDER MATTERS, AND THE OBVIOUS ORDER IS WRONG. This first read
       Math.min(Math.max(EDGE, rect.left), vw - WIDTH - EDGE)
     which discards the EDGE floor whenever the upper bound is the smaller of
     the two — on any viewport narrower than WIDTH + 2*EDGE that bound goes
     negative and wins, and the panel is positioned off the left edge.
     Observed as left:-276 in testing. The floor has to be applied LAST so it
     cannot be overridden. Same reasoning vertically. */
  const vw = window.innerWidth || document.documentElement.clientWidth;
  const vh = window.innerHeight || document.documentElement.clientHeight;
  const left = Math.max(EDGE, Math.min(rect.left, vw - WIDTH - EDGE));
  /* Prefer below; flip above only when below overflows AND above actually
     fits, so a card with room on neither side stays pinned on screen. */
  const flip = rect.bottom + HEIGHT + EDGE > vh && rect.top - HEIGHT - EDGE > 0;
  const top = flip
    ? Math.max(EDGE, rect.top - HEIGHT - 6)
    : Math.max(EDGE, Math.min(rect.bottom + 6, vh - HEIGHT - EDGE));

  return createPortal(
    <div
      ref={panel}
      role="dialog"
      aria-label={`Edit ${task.title}`}
      style={{ position: "fixed", left, top, width: WIDTH }}
      className="z-50 rounded-xl border border-brand-stone bg-white p-3 shadow-xl"
    >
      <div className="mb-2 flex items-start gap-2">
        <p className="min-w-0 flex-1 text-[12px] font-semibold leading-snug text-brand-ink">
          {task.title}
        </p>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="-mr-1 -mt-1 rounded p-1 text-brand-slate hover:bg-brand-mist/60 hover:text-brand-ink"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <label className="block text-[10px] font-semibold uppercase tracking-wide text-brand-gray">
        Assignee
      </label>
      <input
        autoFocus
        value={task.assignee ?? ""}
        placeholder={clientOwned ? "the client" : "Unassigned"}
        disabled={clientOwned}
        onChange={(e) => onChange({ ...task, assignee: e.target.value || null })}
        className="mt-1 w-full rounded border border-brand-mist bg-white px-2 py-1.5 text-xs text-brand-secondary focus:border-brand-primary focus:outline-none disabled:bg-brand-mist/30 disabled:italic disabled:text-brand-slate"
      />
      {clientOwned && (
        <p className="mt-1 text-[10.5px] text-brand-slate">
          Role is Client, so nobody on the team owns it.
        </p>
      )}
      {task.role && !clientOwned && (
        <p className="mt-1 text-[10.5px] text-brand-slate">
          Role <span className="text-brand-gray">{task.role}</span> — their field, not editable.
        </p>
      )}

      <label className="mt-3 block text-[10px] font-semibold uppercase tracking-wide text-brand-gray">
        Due date
      </label>
      {task.dueState === "gated" ? (
        <>
          <Pill className={`mt-1 ${meta.className}`}>
            <Icon className="h-3 w-3" />
            {meta.label}
          </Pill>
          <p className="mt-1 text-[10.5px] text-brand-slate">
            Waiting on the client, so it takes no date at all — dating it would promise a day we
            do not control.
          </p>
        </>
      ) : (
        <>
          <input
            type="date"
            value={task.dueDate ?? ""}
            onChange={(e) => {
              const value = e.target.value;
              onChange(
                value
                  ? { ...task, dueDate: value, dueState: "dated" }
                  : /* Cleared: hand it back to the anchor it came from
                       instead of leaving a dated task with no date. */
                    { ...task, dueDate: null, dueState: "pending" },
              );
            }}
            className="mt-1 w-full rounded border border-brand-mist bg-white px-2 py-1.5 text-xs text-brand-ink focus:border-brand-primary focus:outline-none"
          />
          {task.dueState === "pending" ? (
            <p className="mt-1 text-[10.5px] text-brand-slate">
              {task.dueAnchor ?? meta.label} — setting a date here overrides the anchor and will
              not be recomputed.
            </p>
          ) : (
            <p className="mt-1 text-[10.5px] text-brand-slate">
              Clear the field to hand it back to {task.dueAnchor ?? "its anchor"}.
            </p>
          )}
        </>
      )}
    </div>,
    document.body,
  );
}

/* ── The board view ───────────────────────────────────────────────
   A mirror of what ClickUp's own Board view would show: one board PER LIST,
   grouped by the Phase field inside it. That nesting is deliberate — ClickUp's
   board view is scoped to a list and groups by a field within it, and merging
   both lists into one set of phase columns would contradict the thing this
   feature exists to settle (two lists side by side, not one merged list).

   EDITABLE, AS OF THE BOARD BECOMING THE DEFAULT VIEW. Cards carry the
   include toggle inline, and clicking a card opens `CardEditor` for the two
   fields a reviewer actually changes while reading the shape of the work:
   assignee and due date.

   This reverses the earlier position, which was that reassigning and
   re-dating stay in the table so only one code path writes a task. The
   reasoning did not survive the board becoming what people land on — it
   meant the default view could not perform the two most common edits, and
   sent you to the table for a one-field change. There is still one write
   path: the popover calls the same `onChange` the table rows do, so nothing
   is duplicated but the input controls.

   Renaming is still table-only, deliberately. It wants a wide field and it
   is rare next to reassigning. */
function PhaseBoard({
  lists,
  onChange,
}: {
  lists: {
    listName: string;
    total: number;
    phases: {
      phase: string | null;
      tasks: DraftTask[];
      offsetDays: number | null;
      included: number;
    }[];
  }[];
  onChange: (next: DraftTask) => void;
}) {
  /* Only the id is held, never the task object. `onChange` replaces the task
     in the draft, so a captured copy would go stale the moment you typed and
     the popover would show its own opening values back at you. */
  const [editing, setEditing] = useState<{
    id: string;
    rect: { left: number; top: number; bottom: number; width: number };
  } | null>(null);

  const editingTask = useMemo(() => {
    if (!editing) return null;
    for (const list of lists) {
      for (const phase of list.phases) {
        const found = phase.tasks.find((t) => t.id === editing.id);
        if (found) return found;
      }
    }
    return null;
  }, [editing, lists]);

  const openEditor = (id: string, element: HTMLElement) => {
    const box = element.getBoundingClientRect();
    setEditing({ id, rect: { left: box.left, top: box.top, bottom: box.bottom, width: box.width } });
  };

  return (
    <div className="space-y-4 p-4">
      {editingTask && editing && (
        <CardEditor
          task={editingTask}
          rect={editing.rect}
          onChange={onChange}
          onClose={() => setEditing(null)}
        />
      )}
      {lists.map((list) => (
        <section key={list.listName}>
          <h4 className="mb-2 flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-brand-secondary">
            {list.listName}
            <Pill className="border-brand-mist bg-brand-surface text-brand-gray">
              {list.total} tasks
            </Pill>
            <Pill className="border-brand-mist bg-brand-surface text-brand-gray">
              {list.phases.length} phase{list.phases.length === 1 ? "" : "s"}
            </Pill>
          </h4>
          {/* Horizontal scroll rather than wrapping: columns are a sequence
              (kickoff +0 → +28), and wrapping them would break that reading.
              The container scrolls, never the page. */}
          <div className="overflow-x-auto pb-2">
            <div className="flex gap-3">
              {list.phases.map(({ phase, tasks, offsetDays, included }) => (
                <div
                  key={String(phase)}
                  className="flex w-[248px] shrink-0 flex-col rounded-xl border border-brand-mist bg-brand-surface"
                >
                  <div className="border-b border-brand-mist px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                          phase === null ? "bg-brand-stone" : "bg-brand-primary"
                        }`}
                        aria-hidden
                      />
                      <span className="min-w-0 flex-1 truncate text-[11.5px] font-semibold text-brand-ink">
                        {phase ?? NO_PHASE_LABEL}
                      </span>
                      <span className="shrink-0 text-[11px] tabular-nums text-brand-gray">
                        {included === tasks.length
                          ? tasks.length
                          : `${included}/${tasks.length}`}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[10.5px] text-brand-slate">
                      {offsetDays != null
                        ? `kickoff +${offsetDays}d`
                        : "no offset — not schedulable"}
                    </p>
                  </div>
                  {/* 30.8rem = the original 22rem + 0.4x. The board leads the
                      review now, so the column shows roughly half a long
                      phase before it starts scrolling. */}
                  <div className="max-h-[30.8rem] space-y-2 overflow-y-auto p-2">
                    {tasks.map((task) => {
                      const meta = DUE_META[task.dueState];
                      const Icon = meta.icon;
                      return (
                        <div
                          key={task.id}
                          onClick={(e) => openEditor(task.id, e.currentTarget)}
                          className={`cursor-pointer rounded-lg border bg-white p-2.5 transition-colors ${
                            editing?.id === task.id
                              ? "border-brand-primary ring-1 ring-brand-primary/25"
                              : "border-brand-mist hover:border-brand-stone"
                          } ${task.include ? "" : "opacity-40"}`}
                        >
                          <div className="flex items-start gap-2">
                            <input
                              type="checkbox"
                              checked={task.include}
                              onChange={(e) => onChange({ ...task, include: e.target.checked })}
                              /* The checkbox is its own control; without this
                                 every include toggle would also pop the
                                 editor open over the card you just ticked. */
                              onClick={(e) => e.stopPropagation()}
                              aria-label={`Include "${task.title}"`}
                              className="mt-0.5 h-3.5 w-3.5 shrink-0 cursor-pointer accent-[#5070ff]"
                            />
                            {/* A button, not a <p>: the card's own onClick is
                                mouse-only, and this is what gives the editor
                                a keyboard route and a focus ring. Its click
                                bubbles to the card, so both paths open the
                                same popover. */}
                            <button
                              type="button"
                              className="min-w-0 flex-1 text-left text-[12px] leading-snug text-brand-ink focus:outline-none focus-visible:rounded focus-visible:ring-2 focus-visible:ring-brand-primary/40"
                              style={task.isSubtask ? { paddingLeft: "0.6rem" } : undefined}
                            >
                              {task.title}
                            </button>
                          </div>
                          <div className="mt-2 flex flex-wrap items-center gap-1">
                            {task.role ? (
                              <Pill className="border-brand-mist bg-brand-surface text-brand-gray">
                                {task.role}
                              </Pill>
                            ) : (
                              <Pill className="border-brand-mist bg-brand-mist/40 text-brand-slate">
                                no Role
                              </Pill>
                            )}
                            {task.dueState === "dated" && task.dueDate ? (
                              <Pill className={DUE_META.dated.className}>{task.dueDate}</Pill>
                            ) : (
                              <Pill className={meta.className}>
                                <Icon className="h-3 w-3" />
                                {meta.label}
                              </Pill>
                            )}
                          </div>
                          <p className="mt-1.5 truncate text-[11px] text-brand-secondary">
                            {task.assignee ??
                              (task.role === "Client" ? "the client" : "Unassigned")}
                          </p>
                        </div>
                      );
                    })}
                    {tasks.length === 0 && (
                      <p className="px-1 py-4 text-center text-[11px] text-brand-slate">Empty</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      ))}
      <p className="text-[11px] leading-relaxed text-brand-gray">
        Columns are their <code>Phase</code> field, ordered by the weekly cadence recovered from
        Ridgefield&apos;s live dates. One board per list, because that is how the folder is
        actually laid out. Click any card to change its assignee or due date; the tick drops it
        from the batch. Renaming stays in the table view.
      </p>
    </div>
  );
}

/* ── Where this would land ────────────────────────────────────────
   Measured from Ridgefield's live folder, not assumed. The shape matters
   because it settles the ambiguity in "we're going off both of those
   onboarding templates": it is two lists side by side in one client folder,
   NOT two templates merged into one list. */
function DestinationPanel({ draft, projectName }: { draft: Draft; projectName: string }) {
  const dest = draft.destination;
  const manual = dest?.manualSetup ?? true;

  /* MANUAL SETUP IS A REAL OUTCOME, not an error state. The previous version
     always drew a tree, defaulting the space to "ELEVATE Clients" when it did
     not know — so an ads-only client and a full-service client both rendered
     a confident path into a space that was wrong or archived. */
  if (manual) {
    return (
      <div className="rounded-xl border border-amber-300 bg-amber-50 p-4">
        <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-amber-900">
          <AlertTriangle className="h-4 w-4" />
          No approved ClickUp destination — manual setup
        </h3>
        <p className="text-xs leading-relaxed text-amber-900">{dest?.evidence}</p>
        {dest?.decision && (
          <p className="mt-2 rounded-lg bg-white/60 px-3 py-2 text-xs leading-relaxed text-amber-900">
            <strong>Decision needed:</strong> {dest.decision}
          </p>
        )}
        <p className="mt-2 text-xs text-amber-900">
          The draft below is what would be created once a destination is agreed.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-brand-mist bg-white p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-brand-ink">
          <FolderTree className="h-4 w-4 text-brand-primary" />
          Where this would land in ClickUp
        </h3>
        <Pill
          className={
            dest?.confirmed
              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
              : "border-amber-200 bg-amber-50 text-amber-800"
          }
        >
          {dest?.confirmed ? "read from the workspace" : "inferred — confirm"}
        </Pill>
      </div>
      <div className="rounded-lg bg-brand-mist/30 p-3 font-mono text-xs leading-relaxed text-brand-secondary">
        <div>
          {dest?.space}
          <span className="text-brand-slate">  · space, decided by the package</span>
        </div>
        <div className="pl-4">└── {projectName}<span className="text-brand-slate">  · folder, one per client</span></div>
        {draft.lists.map((list, i) => (
          <div key={list.name} className="pl-8">
            {i === draft.lists.length - 1 ? "└──" : "├──"} {list.name}
            <span className="text-brand-slate">  · {list.taskCount} tasks</span>
          </div>
        ))}
      </div>
      <p className="mt-2 text-xs leading-relaxed text-brand-gray">{dest?.evidence}</p>
      {dest?.decision && (
        <p className="mt-1.5 text-xs leading-relaxed text-amber-800">
          <strong>Still to confirm:</strong> {dest.decision}
        </p>
      )}

    </div>
  );
}

/* The onboarding chain that used to sit here as a table on the review
   screen now has its own page — see components/onboarding/OnboardingJourney.
   It was competing with the 194-row task list for attention, and a scope map
   is a different job from a review queue. */

/* ── The anchors, one panel ───────────────────────────────────────
   WAS: one "kickoff" input that dated every phase-driven task on both
   tracks, replaced by a static green banner the moment a date existed. Three
   things were wrong with that. The LeadLock track has its own kickoff and it
   runs in parallel, not after. A postponed call could not be corrected,
   because the input disappeared. And the banner claimed a cadence confirmed
   for one list as if it applied to both.

   Now: one row per anchor, each showing who books it, how many tasks hang
   off it, and a date field that stays editable. Moving a booked call shows
   what it would change BEFORE it changes it. */
function AnchorPanel({
  draft,
  onApply,
  onBookAll,
  busy,
}: {
  draft: Draft;
  onApply: (anchor: string, date: string) => void;
  onBookAll: () => void;
  busy: boolean;
}) {
  const [dates, setDates] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<string | null>(null);

  /* Only anchors something actually hangs off. Listing all seven against a
     LeadLock-only client would ask for four dates that change nothing. */
  const used = useMemo(() => {
    const counts: Record<string, { total: number; dated: number; manual: number }> = {};
    for (const t of draft.tasks) {
      if (!t.anchorKey || !t.include) continue;
      const c = (counts[t.anchorKey] ??= { total: 0, dated: 0, manual: 0 });
      c.total += 1;
      if (t.dueState === "dated") c.dated += 1;
      if (t.dateSource === "manual") c.manual += 1;
    }
    return counts;
  }, [draft.tasks]);

  const anchorKeys = Object.keys(used);
  if (!anchorKeys.length) return null;

  return (
    <div className="rounded-xl border border-brand-mist bg-white">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-brand-mist px-4 py-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-brand-ink">
          <CalendarClock className="h-4 w-4 text-brand-primary" />
          Call dates
        </h3>
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-xs text-brand-gray">
            Each date moves only the tasks that hang off it.
          </p>
          {/* WALKTHROUGH SHORTCUT. Booking five calls one field at a time is
              what actually happens over the fortnight after a signature; it
              is not what anyone wants to watch in a review. This fills the
              real sequence — Ridgefield's 25 Mar ads kickoff, then the
              positioning interview, strategy call and LeadLock kickoff at
              the intervals discovery describes — in one click. Client-gated
              anchors are skipped, because those are decisions rather than
              bookings and no date should be invented for them. */}
          <button
            onClick={() => onBookAll()}
            disabled={busy}
            className="rounded-lg border border-brand-primary px-3 py-1.5 text-xs font-semibold text-brand-primary disabled:opacity-40"
          >
            Book every call (demo sequence)
          </button>
        </div>
      </div>
      <div className="divide-y divide-brand-mist">
        {anchorKeys.map((key) => {
          const meta = ANCHOR_LABELS[key] ?? { label: key, booked: "Unknown" };
          const current = draft.anchors?.[key] ?? "";
          const entered = dates[key] ?? current;
          const stats = used[key];
          /* What entering this date would change, computed before applying. */
          const wouldChange = entered
            ? draft.tasks.filter(
                (t) =>
                  t.anchorKey === key &&
                  t.include &&
                  t.dueState !== "gated" &&
                  t.offsetDays !== null &&
                  t.dateSource !== "manual",
              ).length
            : 0;
          const moving = Boolean(current) && entered !== current;

          return (
            <div key={key} className="px-4 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold text-brand-ink">{meta.label}</span>
                {meta.clientGated && (
                  <Pill className="border-brand-mist bg-brand-mist/50 text-brand-gray">
                    client decision — waiting state
                  </Pill>
                )}
                {current ? (
                  <Pill className="border-emerald-200 bg-emerald-50 text-emerald-700">
                    booked {current}
                  </Pill>
                ) : (
                  <Pill className="border-amber-200 bg-amber-50 text-amber-800">
                    not booked yet
                  </Pill>
                )}
                <span className="ml-auto text-xs text-brand-gray">
                  {stats.dated} of {stats.total} dated
                  {stats.manual > 0 && ` · ${stats.manual} hand-set`}
                </span>
              </div>
              <p className="mt-0.5 text-xs text-brand-gray">Booked by: {meta.booked}</p>

              {meta.clientGated ? (
                <p className="mt-2 text-xs text-brand-secondary">
                  No date predicted — {stats.total} tasks stay as waiting states.
                </p>
              ) : (
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <input
                    type="date"
                    value={entered}
                    onChange={(e) => {
                      setDates((prev) => ({ ...prev, [key]: e.target.value }));
                      setPreview(key);
                    }}
                    aria-label={`${meta.label} date`}
                    className="rounded-lg border border-brand-mist bg-white px-3 py-1.5 text-sm text-brand-ink focus:border-brand-primary focus:outline-none"
                  />
                  <button
                    onClick={() => onApply(key, entered)}
                    disabled={busy || !entered || entered === current}
                    className="rounded-lg bg-brand-primary px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
                  >
                    {moving ? `Reschedule ${wouldChange} dates` : `Compute ${wouldChange} dates`}
                  </button>
                  {preview === key && entered && entered !== current && (
                    <span className="text-xs text-brand-secondary">
                      {moving ? "Moves" : "Sets"} {wouldChange} calculated date
                      {wouldChange === 1 ? "" : "s"}
                      {stats.manual > 0 && `; keeps ${stats.manual} you set by hand`}.
                    </span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <p className="border-t border-brand-mist px-4 py-2.5 text-xs text-brand-gray">
        Cadence recovered from one live list — a proposal for Gisselle to confirm.
      </p>
    </div>
  );
}

/* ── Review & approve ─────────────────────────────────────────────
   The final draft of the execution, editable, with an explicit will-write /
   will-not-write split above the approve button. */
function ReviewPanel({
  client,
  board,
  onSave,
  onApprove,
  onKickoff,
  onBookAll,
  onBack,
  busy,
}: {
  client: OnboardingClient;
  board: Board;
  onSave: (draft: Draft) => void;
  onApprove: (draft: Draft, wave: "setup" | "schedule") => void;
  onKickoff: (anchor: string, date: string) => void;
  onBookAll: () => void;
  onBack: () => void;
  busy: boolean;
}) {
  const [draft, setDraft] = useState<Draft>(client.draft!);
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    setDraft(client.draft!);
    setDirty(false);
  }, [client.draft]);

  const summary = useMemo(() => summarize(draft), [draft]);
  /* The BOARD is the default. The first question a reviewer has is "what is
     the shape of this work" — which phases exist, how loaded each one is,
     where the dates are missing — and the board answers that at a glance
     where 102 table rows do not.

     The board also carries the two edits a reviewer makes while reading —
     assignee and due date, via the card popover — so leading with it no
     longer costs a trip to the table. Renaming is the one thing still
     table-only: it wants a wide field and it is rare. */
  const [view, setView] = useState<"table" | "board">("board");
  const [filter, setFilter] = useState<string>("all");

  /* Which tasks a shared provisioning run already satisfies. Matched on the
     creation verb only — "Share Google Drive Folder" still has to happen. */
  const provisioned = useMemo(() => {
    const re = [
      /^create .*drive folder/i,
      /^create .*google drive/i,
      /^create slack channel/i,
      /^create leadlock sub-?account/i,
    ];
    return new Set(
      draft.tasks.filter((t) => re.some((r) => r.test(t.title))).map((t) => t.id),
    );
  }, [draft.tasks]);

  const exceptionsOf = useCallback(
    (t: DraftTask) => {
      const out: string[] = [];
      if (t.deferredTo) out.push("deferred");
      if (!t.assignee && t.role !== "Client") out.push("no_owner");
      if (["ambiguous", "heuristic"].includes(t.assigneeConfidence)) out.push("ambiguous_owner");
      if (t.dueState === "unscheduled") out.push("no_rule");
      if (t.dueState === "gated") out.push("client_gated");
      if (t.note) out.push("ported");
      if (provisioned.has(t.id)) out.push("provisioned");
      return out;
    },
    [provisioned],
  );

  const exceptionCounts = useMemo(() => {
    const c: Record<string, number> = {
      no_owner: 0,
      ambiguous_owner: 0,
      no_rule: 0,
      client_gated: 0,
      ported: 0,
      provisioned: 0,
      deferred: 0,
    };
    for (const t of draft.tasks) for (const k of exceptionsOf(t)) c[k] += 1;
    return c;
  }, [draft.tasks, exceptionsOf]);

  /* Every row that is blocking approval and CAN be resolved by naming an
     owner. The destination blocker cannot — see the panel below. */
  const deferrable = useMemo(
    () =>
      draft.tasks.filter(
        (t) =>
          t.include &&
          !t.deferredTo &&
          ((!t.assignee && t.role !== "Client") ||
            ["ambiguous", "heuristic"].includes(t.assigneeConfidence)),
      ).length,
    [draft.tasks],
  );

  /* Clears every blocker in one action, and returns the updated draft so the
     "and approve" variant can hand the SAME object straight to the approve
     call rather than racing the state update.

     Unresolved rows get Gisselle's name; an unmapped destination is recorded
     as an explicit override rather than left to block the review. Both are
     decisions with somebody attached, which is the bar — the alternative was
     a dead end with no way forward. */
  const resolveAll = useCallback((): Draft => {
    const next: Draft = {
      ...draft,
      destination: draft.destination
        ? {
            ...draft.destination,
            space: draft.destination.space ?? "ELEVATE Clients",
            manualSetup: false,
            confirmed: false,
            decision:
              draft.destination.decision ??
              "Destination chosen by the reviewer — still to confirm with Whitney.",
          }
        : draft.destination,
      tasks: draft.tasks.map((t) =>
        t.include &&
        !t.deferredTo &&
        ((!t.assignee && t.role !== "Client") ||
          ["ambiguous", "heuristic"].includes(t.assigneeConfidence))
          ? { ...t, deferredTo: "Gisselle" }
          : t,
      ),
    };
    setDraft(next);
    setDirty(true);
    return next;
  }, [draft]);

  const visibleTasks = useMemo(
    () =>
      filter === "all"
        ? draft.tasks
        : draft.tasks.filter((t) => exceptionsOf(t).includes(filter)),
    [draft.tasks, filter, exceptionsOf],
  );

  const updateTask = (next: DraftTask) => {
    setDraft((current) => ({
      ...current,
      tasks: current.tasks.map((task) => (task.id === next.id ? next : task)),
    }));
    setDirty(true);
  };

  /* Two-level grouping that mirrors ClickUp: LIST, then PHASE within it.
     Both views render off this one structure, so the table and the board can
     never disagree about what belongs where. */
  const byList = useMemo(() => {
    const lists = new Map<string, Map<string | null, DraftTask[]>>();
    for (const task of visibleTasks) {
      const listKey = task.template ?? "Ungrouped";
      if (!lists.has(listKey)) lists.set(listKey, new Map());
      const phases = lists.get(listKey)!;
      const phaseKey = task.phase ?? null;
      if (!phases.has(phaseKey)) phases.set(phaseKey, []);
      phases.get(phaseKey)!.push(task);
    }

    /* Chronological where a phase has an offset, declared order where it does
       not, unphased always last. */
    const rank = (phase: string | null, tasks: DraftTask[]): [number, number] => {
      if (phase === null) return [3, 0];
      const offsets = tasks.map((t) => t.offsetDays).filter((o): o is number => o != null);
      if (offsets.length > 0) return [1, Math.min(...offsets)];
      const i = PHASE_FALLBACK_ORDER.indexOf(phase);
      return [2, i === -1 ? Number.MAX_SAFE_INTEGER : i];
    };

    return [...lists.entries()].map(([listName, phases]) => ({
      listName,
      total: [...phases.values()].reduce((n, t) => n + t.length, 0),
      phases: [...phases.entries()]
        .sort(([pa, ta], [pb, tb]) => {
          const [ga, oa] = rank(pa, ta);
          const [gb, ob] = rank(pb, tb);
          return ga - gb || oa - ob || String(pa).localeCompare(String(pb));
        })
        .map(([phase, tasks]) => ({
          phase,
          tasks,
          /* One offset per phase in their templates, so `min` is the value —
             taken rather than assumed so a mixed phase degrades to its
             earliest date instead of throwing. */
          offsetDays:
            tasks.map((t) => t.offsetDays).filter((o): o is number => o != null)[0] ?? null,
          included: tasks.filter((t) => t.include).length,
        })),
    }));
  }, [visibleTasks]);

  return (
    <div className="space-y-5">
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-sm text-brand-gray transition-colors hover:text-brand-primary"
      >
        <ArrowLeft className="h-4 w-4" /> Back to the board
      </button>

      <div className="space-y-3">
        {/* Step 1 of four. The stepper is here rather than only on steps 2-4
            so a reviewer knows before approving that this is not the end. */}
        <Stepper current={1} />
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-brand-ink">
              Step 1 · {client.projectName}
            </h2>
            <p className="mt-1 text-sm text-brand-gray">
              {client.offers.map((key) => board.offers[key]?.label ?? key).join(" + ")} ·{" "}
              {summary.total} tasks across {draft.lists.length} list
              {draft.lists.length === 1 ? "" : "s"}
            </p>
          </div>
          {/* ONE BUTTON. The demo path was: read the blocker panel, click
              resolve, scroll to the bottom, click approve. This is the same
              thing in one place at the top, where a person running a
              walkthrough will actually look for it. */}
          <button
            onClick={() => onApprove(resolveAll(), "setup")}
            disabled={busy || summary.total === 0}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-primary px-5 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-40"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
            Approve all {summary.total} tasks
          </button>
        </div>
      </div>

      <EvidencePanel client={client} />

      <DestinationPanel draft={draft} projectName={client.projectName} />

      <AnchorPanel
        draft={draft}
        onApply={onKickoff}
        onBookAll={onBookAll}
        busy={busy}
      />

      {/* The provenance strip ("Read from their real ClickUp templates…") and
          the amber `draft.warnings` list were both removed as demo copy. The
          PLACEHOLDER banner deliberately stays: it is not commentary, it is the
          one guard that stops a reviewer mistaking an invented task list for
          their own workspace, and it only ever renders if the source is stubbed.

          Note what left with the warnings, because nothing else surfaces it:
          the draft still silently contributes ZERO tasks for an offer with no
          mapped ClickUp template (Google Search Accelerator, Meta Ads
          Accelerator), and the pending-dates count is now only visible as the
          "awaiting a call" pill on the table header. `draft.warnings` is still
          populated server-side — it is just not rendered. */}
      {draft.placeholder && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-amber-900">
            <AlertTriangle className="h-4 w-4" />
            Placeholder task list — not read from ClickUp
          </h3>
        </div>
      )}

      {/* THE EXCEPTIONS, NOT ALL 194 ROWS. A reviewer's job here is the
          handful of unresolved items, and the only way to find them was to
          scan the whole plan. */}
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-brand-mist bg-brand-surface px-3 py-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-brand-secondary">
          Show only
        </span>
        {(
          [
            ["all", `Everything · ${draft.tasks.length}`],
            ["no_owner", `No owner · ${exceptionCounts.no_owner}`],
            ["ambiguous_owner", `Owner guessed · ${exceptionCounts.ambiguous_owner}`],
            ["no_rule", `No scheduling rule · ${exceptionCounts.no_rule}`],
            ["client_gated", `Client-gated · ${exceptionCounts.client_gated}`],
            ["ported", `Carried from v1 · ${exceptionCounts.ported}`],
            ["provisioned", `Done by provisioning · ${exceptionCounts.provisioned}`],
            ["deferred", `Deferred · ${exceptionCounts.deferred}`],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setFilter(id)}
            className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold transition-colors ${
              filter === id
                ? "bg-brand-primary text-white"
                : "border border-brand-mist bg-white text-brand-secondary hover:border-brand-stone"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {exceptionCounts.provisioned > 0 && (
        <p className="text-xs leading-relaxed text-brand-gray">
          <strong className="text-brand-ink">One provisioning run, not two. </strong>
          {exceptionCounts.provisioned} tasks create the Drive folder, Slack channel or
          LeadLock sub-account, and both lists contain some of them. ON-04 does each once.
        </p>
      )}

      <div className="rounded-xl border border-brand-mist bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-brand-mist px-4 py-3">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-brand-ink">
            <FileText className="h-4 w-4 text-brand-primary" />
            {filter === "all" ? "Final draft of the execution" : "Exceptions to resolve"}
          </h3>
          <div className="flex flex-wrap items-center gap-1.5">
            <Pill className={DUE_META.dated.className}>{summary.dated} dated</Pill>
            <Pill className={DUE_META.awaiting_anchor.className}>
              {summary.awaitingAnchor} waiting on a call
            </Pill>
            {/* The split. These will NEVER date themselves; lumping them in
                with "awaiting a call" said the opposite. */}
            <Pill className={DUE_META.unscheduled.className}>
              {summary.unscheduled} no scheduling rule
            </Pill>
            <Pill className={DUE_META.gated.className}>{summary.gated} client-gated</Pill>
            {summary.needsConfirm > 0 && (
              <Pill className="border-amber-200 bg-amber-50 text-amber-800">
                <UserCheck className="h-3 w-3" />
                {summary.needsConfirm} to confirm
              </Pill>
            )}
            {summary.excluded > 0 && (
              <Pill className="border-red-200 bg-red-50 text-red-700">
                {summary.excluded} removed
              </Pill>
            )}
            {/* Same data, two readings. Segmented rather than a dropdown so
                both options — and which one you are in — are visible at once. */}
            <div
              role="tablist"
              aria-label="Draft view"
              className="ml-1 flex items-center gap-0.5 rounded-lg border border-brand-mist bg-brand-surface p-0.5"
            >
              {(
                [
                  ["table", "Table", TableIcon],
                  ["board", "Board", Columns3],
                ] as const
              ).map(([id, label, Icon]) => (
                <button
                  key={id}
                  role="tab"
                  aria-selected={view === id}
                  onClick={() => setView(id)}
                  className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                    view === id
                      ? "bg-brand-primary text-white"
                      : "text-brand-secondary hover:bg-brand-mist/60"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {view === "board" ? (
          <PhaseBoard lists={byList} onChange={updateTask} />
        ) : (
        <div className="max-h-[26rem] overflow-y-auto">
          <table className="w-full">
            <thead className="sticky top-0 bg-brand-surface text-left">
              <tr className="text-[11px] uppercase tracking-wide text-brand-gray">
                <th className="w-8 px-2 py-2" />
                <th className="px-2 py-2 font-medium">Task</th>
                <th className="w-32 px-2 py-2 font-medium">Role (theirs)</th>
                <th className="w-40 px-2 py-2 font-medium">Assignee (derived)</th>
                <th className="w-56 px-2 py-2 font-medium">Due</th>
              </tr>
            </thead>
            {byList.map((list) => (
              <tbody key={list.listName} className="border-t border-brand-mist">
                {/* Level 1 — the ClickUp LIST. */}
                <tr>
                  <td
                    colSpan={5}
                    className="bg-brand-mist/50 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-brand-secondary"
                  >
                    {list.listName} · {list.total}
                  </td>
                </tr>
                {list.phases.map(({ phase, tasks, offsetDays }) => (
                  <Fragment key={String(phase)}>
                    {/* Level 2 — the Phase field inside that list. */}
                    <tr>
                      <td
                        colSpan={5}
                        className="border-y border-brand-mist/70 bg-brand-surface px-3 py-1 pl-7 text-[10.5px] font-semibold uppercase tracking-wider text-brand-gray"
                      >
                        <span className="inline-flex items-center gap-2">
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${
                              phase === null ? "bg-brand-stone" : "bg-brand-primary"
                            }`}
                            aria-hidden
                          />
                          {phase ?? NO_PHASE_LABEL} · {tasks.length}
                          {offsetDays != null ? (
                            <span className="font-normal normal-case tracking-normal text-brand-slate">
                              kickoff +{offsetDays}d
                            </span>
                          ) : (
                            <span className="font-normal normal-case tracking-normal text-brand-slate">
                              no offset — not schedulable
                            </span>
                          )}
                        </span>
                      </td>
                    </tr>
                    {tasks.map((task) => (
                      <TaskRow key={task.id} task={task} onChange={updateTask} />
                    ))}
                  </Fragment>
                ))}
              </tbody>
            ))}
          </table>
        </div>
        )}
      </div>

      {/* ── THE GATE ───────────────────────────────────────────────
          WAS: "Will create N tasks", with Approve enabled regardless of 14
          unowned tasks, 28 guessed owners and no agreed destination. A
          warning you can scroll past is not a control.

          It also said "Will create" while approval creates nothing at all —
          this build issues no ClickUp write. The terminal effect now sits
          beside the button rather than in a comment in another file. */}
      {summary.blockers.length > 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-red-900">
            <AlertTriangle className="h-4 w-4" />
            Not ready to approve
          </h3>
          <ul className="mt-2 space-y-1.5">
            {summary.blockers.map((b) => (
              <li key={b.kind} className="text-xs leading-relaxed text-red-900">
                <strong>
                  {b.kind === "destination" ? "" : `${b.count} `}
                  {b.label}
                </strong>
                {b.kind === "owner"
                  ? " — assign, or defer to a named person"
                  : b.kind === "ambiguous"
                    ? " — confirm the owner, or defer"
                    : ""}
              </li>
            ))}
          </ul>


          {/* BULK RESOLVE. Clearing 42 exceptions one row at a time is right
              for a real review and wrong for a walkthrough, so the same
              decision is available once — and it is still a DECISION, not a
              bypass: every row it touches gets Gisselle's name on it and
              shows "deferred to Gisselle" afterwards. The destination
              blocker is deliberately NOT clearable this way, because there
              is no owner you can hand "we have not agreed where this goes"
              to. */}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              /* SAVED, not just set. Local-only edits were wiped the moment
                 anything else refreshed the record from the server, which
                 made "resolve all" look like it had done nothing. */
              onClick={() => onSave(resolveAll())}
              disabled={busy}
              className="rounded-lg bg-red-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
            >
              Resolve all
              {deferrable > 0 ? ` · defer ${deferrable} to Gisselle` : ""}
            </button>
            <button
              onClick={() => onApprove(resolveAll(), "setup")}
              disabled={busy}
              className="rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs font-semibold text-red-800 disabled:opacity-40"
            >
              Resolve all and approve
            </button>

          </div>
        </div>
      )}

      <div className="rounded-xl border border-brand-mist bg-white p-4">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-brand-secondary">
          What approval records
        </h4>
        <p className="mt-1 text-2xl font-semibold text-brand-ink">{summary.total} tasks</p>
        <p className="mt-1 text-xs text-brand-gray">
          across {draft.lists.length} list{draft.lists.length === 1 ? "" : "s"} ·{" "}
          {summary.dated} dated · {summary.awaitingAnchor} waiting on a call ·{" "}
          {summary.unscheduled} with no rule
          {summary.deferred > 0 && ` · ${summary.deferred} deferred`}
        </p>
        <p className="mt-2 text-xs leading-relaxed text-brand-gray">
          <strong className="text-brand-ink">No ClickUp task is created.</strong> Approving
          freezes a copy of this batch and raises a notification.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={() => onApprove(draft, "setup")}
          disabled={busy || summary.total === 0 || summary.blockers.length > 0}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-primary px-5 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
          {client.state === "DRAFTED"
            ? `Approve the setup batch · ${summary.total} tasks`
            : `Re-approve the setup batch`}
        </button>
        {/* WAVE 2. It exists as its own button because a client signs before
            they book, and the previous build made the first approval
            terminal — which locked the scheduling wave out entirely. */}
        {client.state !== "DRAFTED" && (
          <button
            onClick={() => onApprove(draft, "schedule")}
            disabled={busy || summary.dated === 0}
            className="inline-flex items-center gap-2 rounded-lg border border-brand-primary px-4 py-2.5 text-sm font-semibold text-brand-primary disabled:opacity-40"
          >
            <CalendarCheck className="h-4 w-4" />
            Approve the {summary.dated} dates
          </button>
        )}
        <button
          onClick={() => {
            onSave(draft);
            setDirty(false);
          }}
          disabled={busy || !dirty}
          className="rounded-lg border border-brand-mist px-4 py-2.5 text-sm text-brand-secondary transition-colors hover:border-brand-stone disabled:opacity-40"
        >
          Save edits
        </button>
        {dirty && <span className="text-xs text-amber-700">Unsaved edits</span>}
        {client.state === "APPROVED" && (
          <span className="text-xs text-emerald-700">
            Setup approved — dates still to book
          </span>
        )}
        {client.state === "SCHEDULED" && (
          <span className="text-xs text-emerald-700">Setup and dates approved</span>
        )}
      </div>
    </div>
  );
}

/* ── THE FOUR STEPS ───────────────────────────────────────────────
   Step 1 is the ClickUp draft above. Steps 2-4 are the rest of what Gisselle
   does by hand the moment a client signs, and they are ordered by DEPENDENCY,
   not by the order Whitney listed them on the call:

     2  Drive folder    nothing depends on it, everything else does — the
                        email attaches a file from it, the Slack bookmarks
                        link to it.
     3  Welcome email   needs the contract from step 2, and it is the thing
                        that CAUSES the booking step 4 waits on.
     4  Slack           GATED until the kickoff is booked. Their own team
                        brief opens "She has scheduled her Ads Kickoff Call
                        for (DATE) and their LeadLock Kickoff call for
                        (DATE)", so the announcement cannot be a
                        signature-wave action. That is a correction to the
                        call, not a design choice.

   It also runs least-to-most consequential: a Drive folder is nearly
   harmless, an @channel post is socially irreversible, an email to the client
   more so. The approve gate earns its place as you advance. */
const STEPS = [
  { key: "clickup" as const, n: 1, label: "ClickUp", system: "ClickUp", icon: ClipboardCheck },
  { key: "drive" as const, n: 2, label: "Drive", system: "Google Drive", icon: HardDrive },
  { key: "email" as const, n: 3, label: "Welcome email", system: "Gmail", icon: Mail },
  { key: "slack" as const, n: 4, label: "Slack", system: "Slack", icon: Hash },
];

function Stepper({ current }: { current: number }) {
  return (
    <ol className="flex flex-wrap items-center gap-1.5" aria-label="Onboarding steps">
      {STEPS.map(({ n, label, icon: Icon }, i) => {
        const done = current > n;
        const active = current === n;
        return (
          <Fragment key={n}>
            <li
              aria-current={active ? "step" : undefined}
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${
                active
                  ? "border-brand-primary bg-brand-primary text-white"
                  : done
                    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                    : "border-brand-mist bg-white text-brand-slate"
              }`}
            >
              {done ? <CircleCheck className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}
              <span className="tabular-nums opacity-70">{n}</span>
              {label}
            </li>
            {i < STEPS.length - 1 && (
              <li aria-hidden className="h-px w-3 bg-brand-stone" />
            )}
          </Fragment>
        );
      })}
    </ol>
  );
}

/* ── Row provenance ──────────────────────────────────────────────
   Badged per row because a reviewer approving a batch should be able to see
   which values were read out of something real, which were derived here, and
   which are waiting on a person. It is the same honesty the task table's
   confidence chip provides, applied to rows that are not tasks. */
const SOURCE_META: Record<string, { label: string; className: string }> = {
  "from-alert": { label: "from the alert", className: "border-brand-mist bg-brand-mist/40 text-brand-gray" },
  "from-sales-call": { label: "from the sales call", className: "border-brand-mist bg-brand-mist/40 text-brand-gray" },
  "template-copy": { label: "their template", className: "border-brand-mist bg-white text-brand-secondary" },
  computed: { label: "computed", className: "border-brand-mist bg-white text-brand-secondary" },
  "from-step": { label: "from an earlier step", className: "border-brand-mist bg-white text-brand-secondary" },
  human: { label: "you write this", className: "border-amber-200 bg-amber-50 text-amber-800" },
  "awaiting-client": { label: "awaiting the client", className: "border-brand-stone bg-brand-mist/60 text-brand-gray" },
};

/* The three-state vocabulary, reused verbatim from the task table so the four
   steps read as one product rather than four screens. */
const ITEM_STATE_META = {
  ready: { icon: Check, label: "Ready", className: "text-emerald-700 bg-emerald-50 border-emerald-200" },
  pending: { icon: CalendarClock, label: "Awaiting a call", className: "text-amber-700 bg-amber-50 border-amber-200" },
  gated: { icon: CircleSlash, label: "Client-gated", className: "text-brand-gray bg-brand-mist/60 border-brand-stone" },
} as const;

/** One editable row of a step. Same affordances as TaskRow: rename it, drop it
    from the batch, and see where its value came from. */
function StageItemRow({
  item,
  onChange,
}: {
  item: StageItem;
  onChange: (next: StageItem) => void;
}) {
  const meta = ITEM_STATE_META[item.state];
  const Icon = meta.icon;
  const source = SOURCE_META[item.source] ?? SOURCE_META.computed;

  return (
    <tr className={item.include ? "" : "opacity-40"}>
      <td className="px-2 py-2 align-top">
        <input
          type="checkbox"
          checked={item.include}
          onChange={(e) => onChange({ ...item, include: e.target.checked })}
          aria-label={`Include "${item.title}"`}
          className="mt-1 h-4 w-4 cursor-pointer accent-[#5070ff]"
        />
      </td>
      <td className="px-2 py-2 align-top">
        <input
          value={item.title}
          onChange={(e) => onChange({ ...item, title: e.target.value })}
          aria-label="Row title"
          className="w-full rounded border border-transparent bg-transparent px-1.5 py-1 text-sm text-brand-ink hover:border-brand-mist focus:border-brand-primary focus:bg-white focus:outline-none"
        />
        {item.detail && <p className="px-1.5 text-[11px] text-brand-gray">{item.detail}</p>}
        {item.note && <p className="px-1.5 text-[11px] italic text-brand-gray">{item.note}</p>}
      </td>
      <td className="px-2 py-2 align-top">
        <Pill className={source.className}>{source.label}</Pill>
      </td>
      <td className="px-2 py-2 align-top">
        <Pill className={meta.className}>
          <Icon className="h-3 w-3" />
          {meta.label}
        </Pill>
      </td>
    </tr>
  );
}

/* ── A Slack post ────────────────────────────────────────────────
   Rendered as the message itself rather than as a row, because the message IS
   the deliverable. The body is their own template with only the parenthesised
   placeholders substituted — 1313 characters for the team brief, 1538 for the
   timeline, both read off their ClickUp task descriptions.

   Editing sets `edited`, which is what stops a rewritten body being clobbered
   if the kickoff date arrives afterwards and the templates re-render. */
function MessagePreview({
  message,
  onChange,
}: {
  message: StageMessage;
  onChange: (next: StageMessage) => void;
}) {
  return (
    <div
      className={`rounded-xl border ${message.include ? "border-brand-mist" : "border-dashed border-brand-stone opacity-50"} bg-white`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-brand-mist px-4 py-2.5">
        <h4 className="flex items-center gap-2 text-sm font-semibold text-brand-ink">
          <MessageSquare className="h-4 w-4 text-brand-primary" />
          {message.label}
        </h4>
        <div className="flex items-center gap-2">
          {message.edited && (
            <Pill className="border-amber-200 bg-amber-50 text-amber-800">edited by hand</Pill>
          )}
          <label className="inline-flex cursor-pointer items-center gap-1.5 text-[11px] text-brand-gray">
            <input
              type="checkbox"
              checked={message.include}
              onChange={(e) => onChange({ ...message, include: e.target.checked })}
              className="h-3.5 w-3.5 cursor-pointer accent-[#5070ff]"
            />
            Post it
          </label>
        </div>
      </div>
      <textarea
        value={message.body}
        onChange={(e) => onChange({ ...message, body: e.target.value, edited: true })}
        aria-label={`${message.label} body`}
        spellCheck={false}
        rows={Math.min(24, message.body.split("\n").length + 1)}
        className="w-full resize-y rounded-b-xl border-0 bg-brand-mist/20 px-4 py-3 font-mono text-[11.5px] leading-relaxed text-brand-secondary focus:bg-white focus:outline-none"
      />
      {message.sourceTask && (
        <p className="border-t border-brand-mist px-4 py-2 text-[11px] text-brand-slate">
          Verbatim from {message.sourceTask}
        </p>
      )}
    </div>
  );
}

/** The structure preview — the step-2-to-4 equivalent of "Where this would
    land in ClickUp". A tree for Drive and Slack, an envelope for the email. */
function StructurePanel({ plan }: { plan: StagePlan }) {
  const Icon = plan.key === "drive" ? FolderTree : plan.key === "slack" ? Hash : Mail;
  const heading =
    plan.key === "drive"
      ? "Where this would land in Google Drive"
      : plan.key === "slack"
        ? "The channel this would create"
        : "The email this would draft";

  return (
    <div className="rounded-xl border border-brand-mist bg-white p-4">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-brand-ink">
        <Icon className="h-4 w-4 text-brand-primary" />
        {heading}
      </h3>
      <div className="rounded-lg bg-brand-mist/30 p-3 font-mono text-xs leading-relaxed text-brand-secondary">
        {plan.structure.kind === "envelope"
          ? plan.structure.rows.map((row) => (
              <div key={row.label ?? row.text}>
                <span className="inline-block w-16 text-brand-slate">{row.label}</span>
                <span className={row.muted ? "italic text-brand-slate" : ""}>{row.value}</span>
              </div>
            ))
          : plan.structure.rows.map((row, i) => {
              /* Last among its OWN siblings, not last in the list. Scan
                 forward: another row at this depth before anything shallower
                 means more siblings follow. Getting this wrong renders a tree
                 where every branch claims to continue — which is how the
                 Drive folder's three-deep nesting read as one flat level. */
              const rest = plan.structure.rows.slice(i + 1);
              const nextSibling = rest.findIndex((r) => r.depth === row.depth);
              const nextShallower = rest.findIndex((r) => r.depth < row.depth);
              const last =
                nextSibling === -1 || (nextShallower !== -1 && nextShallower < nextSibling);
              return (
                <div key={`${row.text}-${i}`} style={{ paddingLeft: `${row.depth * 1.1}rem` }}>
                  {row.depth > 0 && <span className="text-brand-slate">{last ? "└── " : "├── "}</span>}
                  {row.text}
                  {row.note && <span className="text-brand-slate">  · {row.note}</span>}
                  {row.chip && (
                    <span className="ml-2 rounded bg-brand-primary/10 px-1.5 py-0.5 text-[10px] font-sans font-semibold not-italic text-brand-primary">
                      {row.chip}
                    </span>
                  )}
                </div>
              );
            })}
      </div>
    </div>
  );
}

/* ── One of steps 2-4 ────────────────────────────────────────────
   Deliberately the same five-part shape as the ClickUp review above:
   structure preview → the blocker, if there is one → the editable rows →
   a will-create count → approve. A reviewer who has done step 1 already
   knows how to do steps 2, 3 and 4. */
function StagePanel({
  client,
  stage,
  onSave,
  onApprove,
  onKickoff,
  onBack,
  busy,
}: {
  client: OnboardingClient;
  stage: Stage;
  onSave: (plan: StagePlan) => void;
  onApprove: (plan: StagePlan) => void;
  onKickoff: (anchors: { kickoffDate?: string; adsKickoffDate?: string }) => void;
  onBack: () => void;
  busy: boolean;
}) {
  const [plan, setPlan] = useState<StagePlan>(stage.plan);
  const [dirty, setDirty] = useState(false);
  /* Two anchors, because their brief names two kickoff dates and each timeline
     variant counts its weeks from a different one. */
  const [llDate, setLlDate] = useState("");
  const [adsDate, setAdsDate] = useState("");
  useEffect(() => {
    setPlan(stage.plan);
    setDirty(false);
  }, [stage.plan]);

  const summary = useMemo(() => summarizeStagePlan(plan), [plan]);
  const step = STEPS.find((s) => s.key === stage.key)!;

  const updateItem = (next: StageItem) => {
    setPlan((current) => ({
      ...current,
      items: current.items.map((item) => (item.id === next.id ? next : item)),
    }));
    setDirty(true);
  };
  const updateMessage = (next: StageMessage) => {
    setPlan((current) => ({
      ...current,
      messages: current.messages.map((m) => (m.id === next.id ? next : m)),
    }));
    setDirty(true);
  };

  /* Grouped in the order the groups first appear, which is the order the
     builder emits them — seeded artifacts before template copies before the
     client-gated tail. */
  const groups = useMemo(() => {
    const out: { name: string; items: StageItem[] }[] = [];
    for (const item of plan.items) {
      const name = item.group ?? "Rows";
      const existing = out.find((g) => g.name === name);
      if (existing) existing.items.push(item);
      else out.push({ name, items: [item] });
    }
    return out;
  }, [plan.items]);

  return (
    <div className="space-y-5">
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-sm text-brand-gray transition-colors hover:text-brand-primary"
      >
        <ArrowLeft className="h-4 w-4" /> Back to the board
      </button>

      <div className="space-y-3">
        <Stepper current={step.n} />
        <div>
          <h2 className="text-2xl font-semibold text-brand-ink">
            Step {step.n} · {plan.title}
          </h2>
          <p className="mt-1 text-sm text-brand-gray">
            {client.projectName}
            {plan.subtitle ? ` — ${plan.subtitle}` : ""}
          </p>
        </div>
      </div>

      <StructurePanel plan={plan} />

      {/* THE GATE. Step 4 only. Both of its posts name the kickoff dates and
          the timeline's week ranges are computed from them, so approving it
          while this stands would authorise sending two messages full of
          "(DATE)". The store refuses it server-side too. */}
      {plan.gate && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-amber-900">
            <Lock className="h-4 w-4" />
            {plan.gate.label}
          </h3>
          {plan.gate.hint && (
            <p className="mt-1 text-xs leading-relaxed text-amber-900">{plan.gate.hint}</p>
          )}
          <div className="mt-3 flex flex-wrap items-end gap-3">
            {/* Only the anchors this offer actually needs. A LeadLock-only
                client has no ads timeline to date. */}
            {plan.anchors?.leadlock === null && (
              <label className="text-[11px] font-semibold text-amber-900">
                LeadLock kickoff
                <input
                  type="date"
                  value={llDate}
                  onChange={(e) => setLlDate(e.target.value)}
                  className="mt-1 block rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm font-normal text-brand-ink focus:border-brand-primary focus:outline-none"
                />
              </label>
            )}
            {plan.anchors?.ads === null && (
              <label className="text-[11px] font-semibold text-amber-900">
                Ads kickoff
                <input
                  type="date"
                  value={adsDate}
                  onChange={(e) => setAdsDate(e.target.value)}
                  className="mt-1 block rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm font-normal text-brand-ink focus:border-brand-primary focus:outline-none"
                />
              </label>
            )}
            <button
              onClick={() =>
                onKickoff({
                  ...(llDate ? { kickoffDate: llDate } : {}),
                  ...(adsDate ? { adsKickoffDate: adsDate } : {}),
                })
              }
              disabled={busy || (!llDate && !adsDate)}
              className="rounded-lg bg-brand-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            >
              Apply
            </button>
            <button
              onClick={() =>
                onKickoff({
                  kickoffDate: DEMO_CLIENT.actualKickoff,
                  adsKickoffDate: DEMO_CLIENT.actualAdsKickoff,
                })
              }
              disabled={busy}
              className="rounded-lg border border-amber-300 px-3 py-2 text-xs text-amber-900 disabled:opacity-40"
            >
              Ridgefield&apos;s real pair (LeadLock {DEMO_CLIENT.actualKickoff} · ads{" "}
              {DEMO_CLIENT.actualAdsKickoff})
            </button>
          </div>
        </div>
      )}

      {plan.messages.length > 0 && (
        <div className="space-y-3">
          {plan.messages.map((message) => (
            <MessagePreview key={message.id} message={message} onChange={updateMessage} />
          ))}
        </div>
      )}

      <div className="rounded-xl border border-brand-mist bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-brand-mist px-4 py-3">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-brand-ink">
            <FileText className="h-4 w-4 text-brand-primary" />
            {plan.key === "email" ? "What the email carries" : "What this step creates"}
          </h3>
          <div className="flex flex-wrap items-center gap-1.5">
            <Pill className={ITEM_STATE_META.ready.className}>{summary.ready} ready</Pill>
            {summary.pending > 0 && (
              <Pill className={ITEM_STATE_META.pending.className}>{summary.pending} awaiting a call</Pill>
            )}
            {summary.gated > 0 && (
              <Pill className={ITEM_STATE_META.gated.className}>{summary.gated} client-gated</Pill>
            )}
            {summary.excluded > 0 && (
              <Pill className="border-red-200 bg-red-50 text-red-700">{summary.excluded} removed</Pill>
            )}
          </div>
        </div>
        <div className="max-h-[26rem] overflow-y-auto">
          <table className="w-full">
            <thead className="sticky top-0 bg-brand-surface text-left">
              <tr className="text-[11px] uppercase tracking-wide text-brand-gray">
                <th className="w-8 px-2 py-2" />
                <th className="px-2 py-2 font-medium">Row</th>
                <th className="w-44 px-2 py-2 font-medium">Where it came from</th>
                <th className="w-40 px-2 py-2 font-medium">State</th>
              </tr>
            </thead>
            {groups.map((group) => (
              <tbody key={group.name} className="border-t border-brand-mist">
                <tr>
                  <td
                    colSpan={4}
                    className="bg-brand-mist/50 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-brand-secondary"
                  >
                    {group.name} · {group.items.length}
                  </td>
                </tr>
                {group.items.map((item) => (
                  <StageItemRow key={item.id} item={item} onChange={updateItem} />
                ))}
              </tbody>
            ))}
          </table>
        </div>
      </div>

      {/* The provenance line stays on these three steps, unlike step 1 where it
          was cut as demo copy. It is doing more work here: every folder name,
          sharing setting and message body on this screen was read off one of
          their own ClickUp task descriptions, and a reviewer who does not know
          that will read it as invented. */}
      {plan.sourceNote && (
        <p className="text-xs leading-relaxed text-brand-gray">{plan.sourceNote}</p>
      )}

      {plan.warnings.length > 0 && (
        <ul className="space-y-1.5 rounded-xl border border-brand-mist bg-brand-surface p-4">
          {plan.warnings.map((warning) => (
            <li key={warning} className="flex gap-2 text-xs leading-relaxed text-brand-gray">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
              {warning}
            </li>
          ))}
        </ul>
      )}

      <div className="rounded-xl border border-brand-mist bg-white p-4">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-brand-secondary">
          Will create in {plan.system}
        </h4>
        <p className="mt-1 text-2xl font-semibold text-brand-ink">
          {summary.total} item{summary.total === 1 ? "" : "s"}
        </p>
        <p className="mt-1 text-xs text-brand-gray">
          {summary.messages > 0 && `${summary.messages} message${summary.messages === 1 ? "" : "s"} · `}
          {summary.ready} ready now · {summary.gated + summary.pending} waiting on someone else ·
          nothing is written to {plan.system}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={() => onApprove(plan)}
          disabled={busy || summary.total === 0 || Boolean(plan.gate)}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-primary px-5 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
          {plan.gate ? `Blocked — ${plan.gate.label?.toLowerCase()}` : `Approve step ${step.n}`}
        </button>
        <button
          onClick={() => {
            onSave(plan);
            setDirty(false);
          }}
          disabled={busy || !dirty}
          className="rounded-lg border border-brand-mist px-4 py-2.5 text-sm text-brand-secondary transition-colors hover:border-brand-stone disabled:opacity-40"
        >
          Save edits
        </button>
        {dirty && <span className="text-xs text-amber-700">Unsaved edits</span>}
      </div>
    </div>
  );
}

/* ── All four approved ───────────────────────────────────────────
   The closing screen, and the one place the flow says out loud what it did
   and did not do. It is also where the definition-of-done problem belongs:
   there is no machine-readable "onboarded" event anywhere in their workspace,
   so this screen deliberately does not claim the client is onboarded — only
   that the signature wave is staged. */
function CompletionPanel({
  client,
  onBack,
}: {
  client: OnboardingClient;
  onBack: () => void;
}) {
  const clickup = summarize(client.approvedBatch);
  const stageTotals = client.stages.map((stage) => ({
    key: stage.key,
    step: STEPS.find((s) => s.key === stage.key)!,
    summary: summarizeStagePlan(stage.approvedPlan ?? stage.plan),
    approvedAt: stage.approvedAt,
  }));
  const waiting =
    clickup.gated +
    stageTotals.reduce((n, s) => n + s.summary.gated + s.summary.pending, 0);

  return (
    <div className="space-y-5">
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-sm text-brand-gray transition-colors hover:text-brand-primary"
      >
        <ArrowLeft className="h-4 w-4" /> Back to the board
      </button>

      <div className="space-y-3">
        <Stepper current={5} />
        <div>
          <h2 className="text-2xl font-semibold text-brand-ink">
            Signature wave staged — {client.projectName}
          </h2>
          <p className="mt-1 text-sm text-brand-gray">
            Four approvals recorded. Nothing was written to ClickUp, Drive, Gmail or Slack.
          </p>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-emerald-900">
            <ClipboardCheck className="h-4 w-4" />
            Step 1 · ClickUp
          </div>
          <p className="mt-1 text-2xl font-semibold text-emerald-900">{clickup.total} tasks</p>
          <p className="mt-0.5 text-xs text-emerald-900">
            across {client.approvedBatch?.lists.length ?? 0} lists · {clickup.dated} dated
          </p>
        </div>
        {stageTotals.map(({ key, step, summary }) => {
          const Icon = step.icon;
          return (
            <div key={key} className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-emerald-900">
                <Icon className="h-4 w-4" />
                Step {step.n} · {step.label}
              </div>
              <p className="mt-1 text-2xl font-semibold text-emerald-900">
                {summary.total} item{summary.total === 1 ? "" : "s"}
              </p>
              <p className="mt-0.5 text-xs text-emerald-900">
                {summary.messages > 0 ? `${summary.messages} messages · ` : ""}
                {summary.ready} ready now
              </p>
            </div>
          );
        })}
      </div>

      {/* The rail that ran beside every step, collected. Whitney's diagnosis
          on Aug 26 was "we're chasing the team"; only 8 template tasks carry
          Role = Client, and they are the ones that set the pace. The team is
          mostly blocked on the client. */}
      <div className="rounded-xl border border-brand-mist bg-white p-4">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-brand-ink">
          <CircleSlash className="h-4 w-4 text-brand-slate" />
          {waiting} rows are waiting on someone outside this room
        </h3>
        <ul className="mt-2 space-y-1 text-xs leading-relaxed text-brand-gray">
          <li>· The client books the ads kickoff and the LeadLock kickoff themselves.</li>
          <li>· The onboarding questionnaire is sent in step 3 and answered whenever they get to it — the brand assets, the questionnaire upload and the LeadLock sub-account all wait on it.</li>
          <li>· Their own team brief says the sub-account is created “once that&apos;s completed”, not at signature.</li>
        </ul>
      </div>

      <div className="rounded-xl border border-amber-300 bg-amber-50 p-4">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-amber-900">
          <AlertTriangle className="h-4 w-4" />
          This does not say the client is onboarded
        </h3>
        <p className="mt-1 text-xs leading-relaxed text-amber-900">
          There is no machine-readable “onboarded” event anywhere in their workspace. Ridgefield
          entered monthly maintenance on 28 May, six days after Google Ads launched and while all
          three Meta campaign setups were still open — one of them is open today. The only reliable
          proxy is the Client Management list appearing in the client folder, and that is a step
          nobody currently owns.
        </p>
      </div>
    </div>
  );
}

/* Offers whose caption is dropped in the picker. These three carried pricing
   forensics ("$1,997 is the published price…", "ARCHIVES - Full Service space
   exists") — useful while the offer→template mapping was being worked out,
   noise once the grid has to stay scannable at three columns.

   The reasoning is not preserved anywhere on screen any more: the $1,997
   disambiguation hint that used to sit under the grid was removed too. It
   survives only in the notes on the server-side offer records
   (server/onboarding-templates.json → board.offers[].note), so whoever needs
   to re-litigate which template a given offer maps to should read it there. */
const NOTE_SUPPRESSED = new Set(["google_accelerator", "meta_accelerator", "full_service"]);

/* ── One board card ───────────────────────────────────────────────── */
function ClientCard({
  client,
  board,
  onActivate,
  onIgnore,
  busy,
  onPickingChange,
}: {
  client: OnboardingClient;
  board: Board;
  onActivate: (offers: string[]) => void;
  onIgnore: () => void;
  busy: boolean;
  /* Lets the board widen this card to the full row while the offer grid is
     open. Six offers across three columns will not fit in a third of the
     board, and the alternative — a 3-column grid inside a 420px card — is
     what produces two-word-per-line labels. */
  onPickingChange?: (picking: boolean) => void;
}) {
  const [offers, setOffers] = useState<string[]>([]);
  const [pickingState, setPickingState] = useState(false);
  const picking = pickingState;
  const setPicking = (next: boolean) => {
    setPickingState(next);
    onPickingChange?.(next);
  };
  const age = relativeAge(client.firstSeenAt);
  const missing = client.halves.signed ? "invoice payment" : "signed contract";

  return (
    <div className="rounded-xl border border-brand-mist bg-white p-4 transition-shadow hover:shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="font-semibold text-brand-ink">{client.projectName}</h4>
          <p className="mt-0.5 text-xs text-brand-gray">
            {client.halves.signed && client.halves.paid
              ? "Contract signed · invoice paid"
              : `Waiting on the ${missing}`}
            {age && ` · ${age} old`}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {client.halves.signed?.source === "forwarded" ||
          client.halves.paid?.source === "forwarded" ? (
            <Pill className="border-amber-200 bg-amber-50 text-amber-800">forwarded</Pill>
          ) : null}
        </div>
      </div>

      {client.state === "READY" && !picking && (
        <button
          onClick={() => setPicking(true)}
          className="mt-3 w-full rounded-lg bg-brand-primary px-3 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90"
        >
          Start onboarding
        </button>
      )}

      {client.state === "READY" && picking && (
        <div className="mt-3 space-y-2">
          <p className="text-xs font-medium text-brand-ink">
            Which offer did they sign for?
            <span className="ml-1 font-normal text-brand-gray">
              Required — the offer name appears on neither alert.
            </span>
          </p>
          {/* Two rows of three. The offer set is a fixed six, so the grid is
              deliberately not `auto-fit` — a ragged last row reads as a
              rendering accident rather than a layout. */}
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {Object.values(board.offers).map((offer) => (
              <label
                key={offer.key}
                className="flex cursor-pointer items-start gap-2 rounded-lg border border-brand-mist p-2.5 text-xs transition-colors hover:border-brand-stone"
              >
                <input
                  type="checkbox"
                  checked={offers.includes(offer.key)}
                  onChange={(e) =>
                    setOffers((current) =>
                      e.target.checked
                        ? [...current, offer.key]
                        : current.filter((key) => key !== offer.key),
                    )
                  }
                  className="mt-0.5 h-3.5 w-3.5 shrink-0 accent-[#5070ff]"
                />
                <span className="min-w-0">
                  <span className="font-medium text-brand-ink">{offer.label}</span>
                  {!NOTE_SUPPRESSED.has(offer.key) && (
                    <span className="mt-0.5 block text-brand-gray">{offer.note}</span>
                  )}
                </span>
              </label>
            ))}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => onActivate(offers)}
              disabled={busy || offers.length === 0}
              className="flex-1 rounded-lg bg-brand-primary px-3 py-2 text-xs font-semibold text-white disabled:opacity-40"
            >
              Build the draft
            </button>
            <button
              onClick={() => setPicking(false)}
              className="rounded-lg border border-brand-mist px-3 py-2 text-xs text-brand-secondary"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {client.state === "IGNORED" && (
        <p className="mt-3 text-xs text-brand-gray">
          Ignored — {client.ignoreReason?.replace(/_/g, " ")}
          {client.ignoreNote && `: ${client.ignoreNote}`}
        </p>
      )}

      {client.repeatAlerts.length > 0 && (
        <p className="mt-3 flex items-start gap-1.5 rounded-lg border border-brand-mist bg-brand-mist/30 p-2 text-[11px] text-brand-gray">
          <Ban className="mt-0.5 h-3 w-3 shrink-0" />
          <span>
            {client.repeatAlerts.length} repeat payment alert
            {client.repeatAlerts.length === 1 ? "" : "s"} ignored since onboarding — a monthly
            retainer re-fires an identical subject every month.
          </span>
        </p>
      )}

      {(client.state === "AWAITING_PAIR" || client.state === "READY") && (
        <button
          onClick={onIgnore}
          disabled={busy}
          className="mt-2 inline-flex items-center gap-1 text-[11px] text-brand-slate transition-colors hover:text-red-600"
        >
          <Trash2 className="h-3 w-3" /> Dismiss
        </button>
      )}
    </div>
  );
}

/* ── The page ─────────────────────────────────────────────────────── */
export default function OnboardingPage() {
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [subject, setSubject] = useState("");
  const [adding, setAdding] = useState(false);
  /* Which card has its offer grid open — the board widens that one to the
     full row so three columns of offers have somewhere to go. */
  const [pickingKey, setPickingKey] = useState<string | null>(null);
  /* The arrival notification. Separate from the approval toast below because
     the two are different events: this one announces an inbound alert and
     auto-clears, that one records a human decision and persists until the X. */
  const [alertToast, setAlertToast] = useState<{ project: string | null } | null>(null);
  /* Persistent by design — it stays until dismissed with the X, because
     approval is the terminal event of this flow and must not scroll away. */
  /* Fires once, at the END of step 4 — not after step 1 as it used to. The
     terminal event of this flow is now the fourth approval, and the toast has
     to name all four or it understates what a human just authorised. */
  const [toast, setToast] = useState<{
    project: string;
    tasks: number;
    lists: number;
    items: number;
  } | null>(null);
  /* The post-approval page. Held here rather than in the review panel so
     "back to the board" and "run it again" both land somewhere sane. */
  const [journey, setJourney] = useState<{
    project: string;
    count: number;
    lists: number;
  } | null>(null);

  const refresh = useCallback(async () => {
    try {
      setBoard(await getBoard());
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not reach the onboarding API.");
    }
  }, []);


  /* "See an alert" — the demo's stand-in for the Gmail poll that does not
     exist yet.

     It does NOT fake the reveal. It finds a client genuinely holding only its
     signed half, synthesises the real paid-alert subject grammar for it
     ({FirstName} has paid {Amount} {Currency} - {ProjectName}) and pushes it
     through the same /ingest route a poller would call. So the card that
     appears in "Ready to provision" got there via the actual correlator, and
     the conjunction rule is what promoted it — not a boolean in this file.

     The 1997.00 amount is the published Google Search Accelerator price, kept
     because it is the one real paid sample we have. Nothing in the UI reads it
     any more (the disambiguation hint it used to trigger was removed), so it
     is now only realistic test data rather than a load-bearing value. */
  const seeAlert = (currentBoard: Board) =>
    void run(async () => {
      const awaitingPayment = currentBoard.clients.find(
        (c) => c.state === "AWAITING_PAIR" && c.halves.signed && !c.halves.paid,
      );
      if (awaitingPayment) {
        const firstName = awaitingPayment.halves.signed?.firstName ?? "Client";
        await ingestAlert({
          subject: `${firstName} has paid 1997.00 USD - ${awaitingPayment.projectName}`,
        });
        setAlertToast({ project: awaitingPayment.projectName });
        return;
      }
      /* Nothing to correlate. Rather than invent an alert, name whatever is
         already sitting in Ready to provision — or say the inbox is quiet. */
      const ready = currentBoard.clients.find((c) => c.state === "READY");
      setAlertToast({ project: ready?.projectName ?? null });
    });

  /* Auto-clear. An inbound-alert notice is transient; leaving it pinned would
     compete with the approval toast, which is the one that must not scroll
     away. Cleared on unmount so a fast navigation cannot fire setState after
     the page is gone. */
  useEffect(() => {
    if (!alertToast) return;
    const timer = setTimeout(() => setAlertToast(null), 7000);
    return () => clearTimeout(timer);
  }, [alertToast]);

  const run = async (task: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await task();
      await refresh();
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "That did not work.");
    } finally {
      setBusy(false);
    }
  };

  /* Reset -> seed -> ingest the fixtures. One function so the mount effect and
     the "start over" button cannot drift apart.

     The fixtures are what make the flow walkable: two GENUINE forwarded
     alerts that are halves of two DIFFERENT clients (so they sit in
     Awaiting-pair and demonstrate the conjunction rule), plus a CONSTRUCTED
     complete pair for Ridgefield Weddings and Events — a real ELEVATE client
     whose live ClickUp folder this whole flow was measured from. The seed
     marks the rest of their book as already onboarded. */
  const freshFlow = useCallback(
    () =>
      run(async () => {
        await resetBoard();
        await seedBoard(
          ["Dogwood Reserve Estate", "Willow Barn", "The Grove"],
          "Existing client book as of 7 Sept 2026",
        );
        for (const alert of REAL_ALERTS) await ingestAlert(alert);
        for (const alert of DEMO_PAIR) await ingestAlert(alert);
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  /* A FRESH FLOW IS A DELIBERATE ACT, NOT A SIDE EFFECT OF ARRIVING.
   *
   * This used to reset on every mount. On a SHARED store that is destructive:
   * two people walking through the demo at once wipe each other's state, and
   * simply navigating back to the page discards a review in progress. A
   * store that resets when anyone visits also cannot represent durable
   * operational history, which is what a pilot would need.
   *
   * So mount now SEEDS ONLY IF THE BOARD IS EMPTY, and resetting is a button.
   * The same sequence still runs, just when someone asks for it.
   *
   * Order is load-bearing: reset empties the store AND clears the seed flag,
   * so `seedBoard` has to run before any `ingestAlert` or ingestion refuses.
   * That refusal is the guard that stops a first pass treating ninety days of
   * Dubsado history as new signings, and a reset must not quietly satisfy it.
   *
   * `bootstrapped` guards against React StrictMode's deliberate double-invoke
   * in development. Without it the sequence runs twice; the store serialises
   * writes and `ingest` dedupes on a fingerprint, so it would not corrupt
   * anything, but it doubles the work and makes the network tab a puzzle. */
  const bootstrapped = useRef(false);
  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;
    void (async () => {
      try {
        const existing = await getBoard();
        /* Somebody else's walkthrough, or your own from five minutes ago.
           Leave it alone — "Start over" is right there. */
        if (existing?.clients?.length) {
          setBoard(existing);
          return;
        }
      } catch {
        /* Fall through to seeding: an unreachable board is the same
           situation as an empty one for this purpose. */
      }
      await freshFlow();
    })();
  }, [freshFlow]);

  /* The visible "start over" affordance — same sequence the mount runs, so a
     reviewer can restart the walkthrough without reloading the page. */
  const loadDemo = () => void freshFlow();

  const groups = useMemo(() => {
    const clients = board?.clients ?? [];
    return {
      ready: clients.filter((c) => c.state === "READY"),
      drafted: clients.filter((c) => c.state === "DRAFTED"),
      awaiting: clients.filter((c) => c.state === "AWAITING_PAIR"),
      approved: clients.filter((c) => c.state === "APPROVED"),
      scheduled: clients.filter((c) => c.state === "SCHEDULED"),
      ignored: clients.filter((c) => c.state === "IGNORED"),
    };
  }, [board]);

  const active = board?.clients.find((c) => c.projectKey === selected) ?? null;
  /* The step the reviewer is standing on, once step 1 is approved: the first
     stage still open. Null while the ClickUp draft is live and null again when
     all four are approved, which is what selects the panel below. */
  const openStage = active?.stages.find((stage) => stage.state === "OPEN") ?? null;

  if (!board) {
    return (
      <div className="bg-hero min-h-[100svh] p-8">
        <div className="container flex items-center gap-2 text-sm text-brand-gray">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading the onboarding board…
        </div>
      </div>
    );
  }

  return (
    <div className="bg-hero min-h-[100svh]">
      {/* `.container` rather than a hand-picked max-w: this console is the
          most width-hungry page in the app (a 102-row table and a 7-column
          board), and it was the one capped tightest at 72rem. */}
      <div className="container py-10">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-brand-gray transition-colors hover:text-brand-primary"
        >
          <ArrowLeft className="h-4 w-4" /> Command Center
        </Link>

        <header className="mt-4 mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold text-brand-ink">Client Onboarding</h1>
            <p className="mt-1 max-w-2xl text-sm text-brand-gray">
              Watches for the two Dubsado alerts — contract signed <em>and</em> invoice paid —
              correlates them to one client, then holds everything for review. One signature fans
              out across ClickUp, Gmail, Drive, Slack and HighLevel; this build covers the ClickUp
              lists and maps the rest. Nothing is written to ClickUp without approval.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Pill className="border-amber-200 bg-amber-50 text-amber-800">
              <Inbox className="h-3 w-3" /> paste intake · no Gmail scope
            </Pill>
            <button
              onClick={() => void refresh()}
              className="rounded-lg border border-brand-mist bg-white p-2 text-brand-gray transition-colors hover:border-brand-stone"
              aria-label="Refresh"
            >
              <RotateCw className="h-4 w-4" />
            </button>
          </div>
        </header>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800">
            {error}
          </div>
        )}

        {!board.seeded ? (
          /* The seed gate, explained rather than silently enforced. */
          <div className="rounded-xl border border-brand-mist bg-white p-6">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-brand-ink">
              <ShieldCheck className="h-5 w-5 text-brand-primary" />
              Seed the existing client book first
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-brand-gray">
              Ingestion refuses until this runs, so a first pass cannot read old history as
              a queue of new signings.
            </p>
            <button
              onClick={loadDemo}
              disabled={busy}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-brand-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              Seed, then load the alerts (incl. Ridgefield Weddings and Events)
            </button>
          </div>
        ) : journey ? (
          <OnboardingJourney
            projectName={journey.project}
            taskCount={journey.count}
            listCount={journey.lists}
            onBack={() => {
              setJourney(null);
              setSelected(null);
            }}
            onRestart={() => {
              setJourney(null);
              setSelected(null);
              loadDemo();
            }}
          />
        ) : active &&
          (active.state === "DRAFTED" ||
            active.state === "APPROVED" ||
            active.state === "SCHEDULED") &&
          active.draft ? (
          <ReviewPanel
            client={active}
            board={board}
            busy={busy}
            onBack={() => setSelected(null)}
            onSave={(draft) => void run(() => saveDraft(active.projectKey, draft))}
            onKickoff={(anchor, date) =>
              void run(() => applyAnchorDate(active.projectKey, anchor, date))
            }
            /* The real sequence, at the intervals discovery describes: the
               client books the ads kickoff, the positioning interview
               follows, the strategy call comes "shortly after" it, and the
               LeadLock kickoff runs in parallel rather than after. Applied
               one anchor at a time, exactly as a person would. */
            onBookAll={() =>
              void run(async () => {
                const sequence: [string, string][] = [
                  ["ads_kickoff", "2026-03-25"],
                  ["leadlock_kickoff", "2026-03-25"],
                  ["messaging_positioning", "2026-04-01"],
                  ["ad_strategy", "2026-04-08"],
                  ["internal_tests", "2026-04-22"],
                ];
                for (const [anchor, date] of sequence) {
                  await applyAnchorDate(active.projectKey, anchor, date);
                }
              })
            }
            onApprove={(draft, wave) =>
              void run(async () => {
                const result = await approveBatch(active.projectKey, draft, wave);
                /* Approval hands straight over to the journey map. The task
                   list is one row of the onboarding, and stopping there was
                   what made this console look like a ClickUp importer. */
                setJourney({
                  project: active.projectName,
                  count: result.summary.total,
                  lists: draft.lists.length,
                });
              })
            }
          />
        ) : active && openStage ? (
          <StagePanel
            client={active}
            stage={openStage}
            busy={busy}
            onBack={() => setSelected(null)}
            onSave={(plan) => void run(() => saveStage(active.projectKey, openStage.key, plan))}
            onKickoff={(anchors) => void run(() => applyStageKickoff(active.projectKey, anchors))}
            onApprove={(plan) =>
              void run(async () => {
                const result = await approveStage(active.projectKey, openStage.key, plan);
                /* The LAST approval is the terminal event, so the persistent
                   toast fires here rather than after step 1. Read off the
                   response, not off `active`, which is a render behind. */
                if (!result.client.stages.some((stage) => stage.state === "OPEN")) {
                  setToast({
                    project: active.projectName,
                    tasks: summarize(result.client.approvedBatch).total,
                    lists: result.client.approvedBatch?.lists.length ?? 0,
                    items: result.client.stages.reduce(
                      (n, stage) =>
                        n + summarizeStagePlan(stage.approvedPlan ?? stage.plan).total,
                      0,
                    ),
                  });
                }
              })
            }
          />
        ) : active && active.state === "APPROVED" && active.stages.length ? (
          <CompletionPanel client={active} onBack={() => setSelected(null)} />
        ) : (
          <div className="space-y-8">
            {/* Paste intake. Shaped like a poller's inner loop so a real Gmail
                read later changes the caller, not the pipeline. */}
            <div className="rounded-xl border border-brand-mist bg-white p-4">
              {adding ? (
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="Paste a Dubsado alert subject line…"
                    className="min-w-[20rem] flex-1 rounded-lg border border-brand-mist px-3 py-2 text-sm focus:border-brand-primary focus:outline-none"
                  />
                  <button
                    onClick={() =>
                      void run(async () => {
                        await ingestAlert({ subject });
                        setSubject("");
                        setAdding(false);
                      })
                    }
                    disabled={busy || !subject.trim()}
                    className="rounded-lg bg-brand-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
                  >
                    Ingest
                  </button>
                  <button
                    onClick={() => setAdding(false)}
                    className="rounded-lg border border-brand-mist px-3 py-2 text-sm text-brand-secondary"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                  <button
                    onClick={() => seeAlert(board)}
                    disabled={busy}
                    className="inline-flex items-center gap-2 text-sm font-medium text-brand-primary disabled:opacity-40"
                  >
                    <Inbox className="h-4 w-4" /> See an alert
                  </button>
                  {/* The manual path stays reachable — the header pill still
                      advertises paste intake, and it is how any subject line
                      other than the scripted one gets tested. */}
                  <button
                    onClick={() => setAdding(true)}
                    className="inline-flex items-center gap-1.5 text-xs text-brand-slate transition-colors hover:text-brand-secondary"
                  >
                    <Plus className="h-3 w-3" /> or paste one manually
                  </button>
                </div>
              )}
            </div>

            {(
              [
                ["Ready to provision", groups.ready],
                ["In review", groups.drafted],
                ["Awaiting the other half", groups.awaiting],
                ["Setup approved — dates still to book", groups.approved],
                ["Fully scheduled", groups.scheduled],
                ["Ignored", groups.ignored],
              ] as const
            ).map(([title, list]) =>
              list.length === 0 ? null : (
                <section key={title}>
                  <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-brand-secondary">
                    {title} · {list.length}
                  </h3>
                  <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                    {list.map((client) => (
                      <div
                        key={client.projectKey}
                        className={
                          pickingKey === client.projectKey
                            ? "md:col-span-2 lg:col-span-3"
                            : undefined
                        }
                      >
                        <ClientCard
                          client={client}
                          board={board}
                          busy={busy}
                          onPickingChange={(open) =>
                            setPickingKey(open ? client.projectKey : null)
                          }
                          onActivate={(offers) =>
                            void run(async () => {
                              await activateClient(
                                client.projectKey,
                                offers,
                                /* ISO, not the human-readable header string — the latter is
                                   Invalid Date and would null every computed due date. */
                                client.halves.signed?.originalDateIso ?? client.pairedAt,
                              );
                              setSelected(client.projectKey);
                            })
                          }
                          onIgnore={() => void run(() => ignoreClient(client.projectKey, "dismissed"))}
                        />
                        {/* An approved record is re-openable, because the
                            setup wave is not the end of it — the calls still
                            have to be booked and the dates approved. */}
                        {(client.state === "DRAFTED" ||
                          client.state === "APPROVED" ||
                          client.state === "SCHEDULED") && (
                          <button
                            onClick={() => setSelected(client.projectKey)}
                            className="mt-2 w-full rounded-lg border border-brand-primary px-3 py-2 text-xs font-semibold text-brand-primary"
                          >
                            {client.state === "DRAFTED"
                              ? "Open the draft"
                              : client.state === "APPROVED"
                                ? "Book the calls"
                                : "Review the schedule"}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              ),
            )}

            {board.clients.length === 0 && (
              <p className="rounded-xl border border-dashed border-brand-stone p-8 text-center text-sm text-brand-gray">
                No alerts ingested yet. Paste a Dubsado subject line to begin.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Inbound-alert notification — auto-clears after 7s. */}
      <AnimatePresence>
        {alertToast && (
          <motion.div
            key="onboarding-alert-toast"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            className="fixed bottom-6 right-6 z-50 max-w-md rounded-xl border border-brand-mist bg-white p-4 shadow-lg"
            role="status"
          >
            <div className="flex items-start gap-3">
              <div className="rounded-full bg-brand-primary/10 p-1.5">
                <Inbox className="h-4 w-4 text-brand-primary" />
              </div>
              <div className="flex-1">
                {alertToast.project ? (
                  <>
                    <p className="text-sm font-semibold text-brand-ink">
                      {alertToast.project} has paid the invoice
                    </p>
                    <p className="mt-0.5 text-xs leading-relaxed text-brand-gray">
                      Both halves are now in — initiate the onboarding from{" "}
                      <strong>Ready to provision</strong>.
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-sm font-semibold text-brand-ink">No alert waiting</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-brand-gray">
                      Every signed contract on the board already has its matching
                      payment, so there is nothing new to correlate.
                    </p>
                  </>
                )}
              </div>
              <button
                onClick={() => setAlertToast(null)}
                aria-label="Dismiss notification"
                className="rounded p-1 text-brand-slate transition-colors hover:bg-brand-mist/50 hover:text-brand-ink"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Persistent approval notification — stays until dismissed. */}
      <AnimatePresence>
        {toast && (
          <motion.div
            /* Required, not cosmetic. AnimatePresence tracks its children by
               key; without one it cannot detect this child leaving, the exit
               animation never resolves, and the toast stays on screen forever
               however many times Dismiss is pressed. Matches the lead-toast
               convention in LeadMagnetDashboardPage. */
            key="onboarding-approval-toast"
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
                  All four steps approved
                </p>
                <p className="mt-0.5 text-xs leading-relaxed text-brand-gray">
                  <strong>{toast.project}</strong> — {toast.tasks} ClickUp task
                  {toast.tasks === 1 ? "" : "s"} across {toast.lists} list
                  {toast.lists === 1 ? "" : "s"}, plus {toast.items} row
                  {toast.items === 1 ? "" : "s"} of Drive, email and Slack work. Nothing was
                  written to any of the four systems: this build is read-only and stops at
                  approval.
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
