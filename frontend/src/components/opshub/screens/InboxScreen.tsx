/* Inbox — context-aware triage.

   THE POINT OF THIS SCREEN IS THE MIDDLE COLUMN, NOT THE DRAFT. Any tool can
   generate a reply. What makes the reply trustworthy is the evidence stack
   beside it — the Gmail thread, the Slack message, the ClickUp task, the
   transcript timestamp where the promise was actually made. `contextFor`
   assembles that per email kind.

   NOTHING AUTO-SENDS. Every primary action produces a DRAFT and says so in
   the toast. `noaction` items can be filed, and the ambiguous one refuses to
   recommend filing at all.

   TRIAGE IS TWO CONTROLS, AND THEY ARE DIFFERENT AXES. "Change category"
   moves a row between queues — it says WHO OWNS IT. "Status" says HOW FAR
   ALONG IT IS. Both live in the detail header because both are per-email
   decisions, and both route through the hub's readers so the queue badges,
   the Home KPIs and Ops Watch move in the same tick. */

import { useMemo, useState } from "react";
import { AlertTriangle, Clock, Link2, User } from "lucide-react";
import {
  AUTHORITY_META,
  AXIS_META,
  CLIENTS,
  EMAILS,
  DONE_LABEL,
  DRAFTS,
  EMAIL_ACTIONS,
  ENVELOPES,
  NUDGES,
  QUEUES,
  QUEUE_AXIS,
  type Email,
} from "@/data/opsHub";
import { OBLIGATION_META } from "@/data/obligations";
import {
  STAGE_META,
  WORK_STAGES,
  type AutoSystem,
  type SourceKey,
  type Tone,
  type WorkStage,
} from "@/lib/opsHub";
import type { OpsHub } from "@/hooks/useOpsHub";
import { cn } from "@/lib/utils";
import {
  Actions,
  AutoBadge,
  DraftBlock,
  Empty,
  EvidenceRow,
  Facts,
  Menu,
  Panel,
  Pill,
  SectionLabel,
} from "../primitives";

type Evidence = { s: SourceKey; label: string; excerpt: string; time: string };

function clientName(id: string) {
  return CLIENTS.find((c) => c.id === id)?.name ?? "";
}

/* The evidence stack, by email kind. Written per-kind rather than generated,
   because the *shape* of the proof differs: an SLA breach is proved by an
   absence (no reply, no acknowledgement, no task), while a commitment is
   proved by a timestamp. */
function contextFor(e: Email): Evidence[] {
  if (e.id === "e1" || e.id === "e6")
    return [
      {
        s: "gmail",
        label: "Current client thread",
        excerpt: "Sarah Mitchell · 3 messages · last reply from Whitney Sep 2",
        time: "2h ago",
      },
      {
        s: "slack",
        label: "#client-bloom-manor",
        excerpt: "Jacqueline: Final QA is done; handing off tomorrow.",
        time: "4h ago",
      },
      {
        s: "clickup",
        label: "Landing Page QA · In Progress",
        excerpt: "Owner Jacqueline · Due tomorrow",
        time: "Yesterday",
      },
      {
        s: "zoom",
        label: "Sep 2 Strategy Call · 24:18",
        excerpt:
          "Whitney told the client the revised page would be delivered this week.",
        time: "Sep 2",
      },
      {
        s: "drive",
        label: "Latest landing-page review file",
        excerpt: "Clients / Bloom Manor / Meetings / 2026-09-02 Strategy",
        time: "Sep 2",
      },
    ];

  if (e.id === "e3")
    return [
      {
        s: "clickup",
        label: "4 / 4 client-facing actions complete",
        excerpt: "LP handoff · keyword review · testimonial creative · recap sent",
        time: "Today",
      },
      {
        s: "slack",
        label: "#client-bloom-manor",
        excerpt: "Jacqueline reacted 👀 then marked complete",
        time: "Today",
      },
      {
        s: "zoom",
        label: "Sep 2 Strategy Call",
        excerpt: "Commitments made on the call are the source of this update.",
        time: "Sep 2",
      },
      {
        s: "gmail",
        label: "Last client email",
        excerpt: "Whitney · Sep 2 · recap of the strategy call",
        time: "Sep 2",
      },
    ];

  if (e.kind === "sla")
    return [
      {
        s: "gmail",
        label: "Client thread — no reply detected",
        excerpt: `${e.sender} asked a question ${e.age} ago`,
        time: e.age,
      },
      {
        s: "slack",
        label: "Owner channel",
        excerpt: `No acknowledgement from ${e.owner} on the thread`,
        time: "Today",
      },
      {
        s: "clickup",
        label: "No task created for this reply",
        excerpt: "Reply SLA expectation: 24–48 business hours",
        time: "—",
      },
    ];

  if (e.kind === "waiting")
    return [
      {
        s: "gmail",
        label: "Original request",
        excerpt: "Assets requested by Gisselle · no client reply since",
        time: e.age,
      },
      {
        s: "clickup",
        label: `${clientName(e.clientId)} creative build · Blocked`,
        excerpt: "Cannot progress without client assets",
        time: "Today",
      },
      {
        s: "slack",
        label: `#client-${e.clientId || "account"}`,
        excerpt: "Team confirmed everything else on the recap is complete",
        time: "Yesterday",
      },
      {
        s: "zoom",
        label: "Last call commitment",
        excerpt: "Client agreed to send the gallery after the call",
        time: "Sep 2",
      },
    ];

  if (e.kind === "sales")
    return [
      {
        s: "zoom",
        label: "Sep 3 sales call · 34 min",
        excerpt: "Prospect asked about Elevate scope and timeline",
        time: "Yesterday",
      },
      {
        s: "highlevel",
        label: "Contact record",
        excerpt: "Magnolia House · Tessa Ruiz · lead source: referral",
        time: "Aug 24",
      },
      {
        s: "clickup",
        label: "Send Elevate proposal",
        excerpt: "Owner Whitney · Due today",
        time: "Today",
      },
    ];

  if (e.kind === "finance")
    return [
      {
        s: "highlevel",
        label: "INV-204 · unpaid",
        excerpt: "Due Aug 30 · amount due $1,850 · not void",
        time: "5d overdue",
      },
      {
        s: "highlevel",
        label: "Standard reminder already sent",
        excerpt: "Automated invoice reminder · Sep 1",
        time: "Sep 1",
      },
      {
        s: "gmail",
        label: "Last client email",
        excerpt: "Dana Whitfield · Sep 1 · unrelated thread",
        time: "Sep 2",
      },
    ];

  if (e.kind === "noaction")
    return [
      {
        s: "gmail",
        label: "Message read, no reply detected",
        excerpt: e.rec,
        time: e.age,
      },
      {
        s: "clickup",
        label: "No linked task",
        excerpt: "No action item references this message",
        time: "—",
      },
      {
        s: "slack",
        label: "No related discussion",
        excerpt: "Nothing referencing this thread in the last 7 days",
        time: "—",
      },
    ];

  return [
    { s: "gmail", label: "Current thread", excerpt: e.subject, time: e.age },
    {
      s: "slack",
      label: "Related channel context",
      excerpt: `Team discussion linked to ${clientName(e.clientId) || "this thread"}`,
      time: "Today",
    },
    {
      s: "clickup",
      label: "Linked task",
      excerpt: "Operational task · In progress",
      time: "Yesterday",
    },
  ];
}

function badgeFor(e: Email): AutoSystem {
  if (e.kind === "noaction") return "gmail_filter";
  if (e.kind === "sla" || e.kind === "waiting") return "ai_hq";
  if (e.kind === "finance") return "native_highlevel_ai";
  return "ai_assisted";
}

const PRIORITY_TONE = { high: "red", medium: "amber", low: "outline" } as const;

/* Priority moves to a dot in the list so the status pill can have the row's
   only pill slot. It stays a full pill in the detail header, where there is
   room for the word. */
const PRIORITY_DOT = {
  high: "bg-console-bad",
  medium: "bg-console-warn",
  low: "bg-brand-stone",
} as const;

/* Solid fills for the status dot on the menu trigger. TONE_CLASS is a
   background/text pair at ~10% alpha, which disappears at 8px. */
const STATUS_DOT: Partial<Record<Tone, string>> = {
  outline: "bg-brand-stone",
  blue: "bg-brand-primary",
  slate: "bg-brand-slate",
  amber: "bg-console-warn",
  green: "bg-console-good",
};

const STATUS_OPTIONS = WORK_STAGES.map((w) => ({
  value: w.id,
  label: `${w.label}`,
  hint: `${w.group} · ${w.hint}`,
  tone: w.tone,
}));

/* Who the artifact needs, by email kind. Reads out of the one matrix in
   data/opsHub.ts so Inbox, Meetings and Source Coverage cannot disagree. */
const AUTHORITY_FOR: Record<string, keyof typeof AUTHORITY_META> = {
  draft: "whitney",
  waiting: "whitney",
  sales: "whitney",
  finance: "whitney",
  sla: "gisselle",
  noaction: "gisselle",
};

/* ── detail column ────────────────────────────────────────────── */

/** The obligation strip. One work item, and every system it touches — the
    thing F02 asked for and the reason Ops Watch and Client Hub can no longer
    disagree with this screen about whether something is done. */
function ObligationStrip({ hub, obligationId }: { hub: OpsHub; obligationId: string }) {
  const ob = OBLIGATION_META[obligationId];
  if (!ob) return null;
  const parent = ob.partOf ? OBLIGATION_META[ob.partOf] : null;
  const stage = hub.stageOf(obligationId);
  const parentStage = ob.partOf ? hub.stageOf(ob.partOf) : null;
  const events = hub.eventsFor(obligationId);

  const links: [string, string][] = [
    ...(ob.links.emails?.length ? [["Gmail", `${ob.links.emails.length} thread${ob.links.emails.length === 1 ? "" : "s"}`] as [string, string]] : []),
    ...(ob.links.slack ? [["Slack", ob.links.slack] as [string, string]] : []),
    ...(ob.links.clickup ? [["ClickUp", ob.links.clickup] as [string, string]] : []),
    ...(ob.links.meetingTasks?.length ? [["Meeting", ob.links.meetingTasks[0].split(":")[0]] as [string, string]] : []),
    ...(ob.links.invoices?.length ? [["HighLevel", ob.links.invoices.join(", ")] as [string, string]] : []),
    ...(ob.clientId ? [["Account", clientName(ob.clientId)] as [string, string]] : []),
  ];

  return (
    <Panel
      title="Work item"
      subtitle="Shared across Inbox, Meetings, Ops Watch and Client Hub"
      right={<Pill tone={STAGE_META[stage].tone}>{STAGE_META[stage].label}</Pill>}
    >
      <p className="text-[13px] font-bold text-brand-ink">{ob.title}</p>
      <p className="mt-1 truncate text-[11.5px] text-brand-gray">{ob.origin}</p>
      {parent && parentStage && (
        <p className="mt-2 inline-flex flex-wrap items-center gap-1.5 rounded-lg bg-brand-mist/50 px-2.5 py-1.5 text-[11.5px] text-brand-secondary">
          <Link2 className="h-3 w-3 flex-none" aria-hidden />
          Step of <span className="font-bold text-brand-ink">{parent.title}</span>
          <Pill tone={STAGE_META[parentStage].tone}>{STAGE_META[parentStage].label}</Pill>
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {links.map(([k, v]) => (
          <Pill key={k} tone="outline">
            <span className="font-bold">{k}</span> · {v}
          </Pill>
        ))}
        <Pill tone="outline">Owner · {ob.owner}</Pill>
      </div>
      {events.length > 0 && (
        <>
          <SectionLabel className="mt-4">Activity</SectionLabel>
          <ul className="mt-2 space-y-1.5">
            {events.map((ev, i) => (
              <li
                key={`${ev.text}-${i}`}
                className="flex items-start gap-2 text-[12px] leading-snug text-brand-secondary"
              >
                <span
                  className="mt-[6px] h-1.5 w-1.5 flex-none rounded-full bg-brand-primary"
                  aria-hidden
                />
                <span>
                  <span className="font-bold text-brand-ink">{ev.actor}</span> · {ev.text}{" "}
                  <span className="text-brand-slate">({ev.at})</span>
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </Panel>
  );
}

/* ── detail ───────────────────────────────────────────────────── */

function EmailDetail({ email, hub }: { email: Email; hub: OpsHub }) {
  const {
    state,
    emailStatus,
    emailQueue,
    emailStage,
    stageOf,
    queueOpen,
    moveEmail,
    setEmailStage,
    setEmailStatus,
    editDraft,
    clearDraftEdit,
    completionBlockers,
    openDrawer,
  } = hub;

  const status = emailStatus(email.id);
  const stage = emailStage(email.id);
  const stageMeta = STAGE_META[stage];
  const evidence = contextFor(email);
  const obligationId = hub.obligationOfEmail(email.id);
  const envelope = ENVELOPES[email.id];
  const seedDraft = DRAFTS[email.id] ?? NUDGES[email.id] ?? "";
  const draft = state.draftEdits[email.id] ?? seedDraft;
  const edited = state.draftEdits[email.id] !== undefined && state.draftEdits[email.id] !== seedDraft;
  const isNudge = email.kind === "sla";
  const authority = AUTHORITY_META[AUTHORITY_FOR[email.kind] ?? "gisselle"];

  /* Local editor toggle. The reviewer can correct the exact text that
     approval will use — the previous build put "Edit" behind a toast saying
     inline editing was out of scope, which made the approve button a claim
     about content nobody could change. */
  const [editing, setEditing] = useState(false);

  const [actionLabel, nextStatus, actionToast] = EMAIL_ACTIONS[email.kind];

  /* Blockers on a completion update: it tells the client everything is done,
     so it cannot be approved while one of the things it names is open. */
  const blockers = obligationId ? completionBlockers(obligationId) : [];

  const queueOptions = useMemo(
    () =>
      QUEUES.map((q) => ({
        value: q.id,
        label: q.label,
        hint: `Lane ${AXIS_META[QUEUE_AXIS[q.id]].label}`,
        count: queueOpen(q.id),
      })),
    [queueOpen],
  );

  const primaryAction = {
    label: actionLabel,
    variant: "primary" as const,
    disabled: blockers.length > 0,
    onClick: () => {
      if (blockers.length) return;
      setEmailStatus(email.id, nextStatus, actionToast, email.kind);
      setEditing(false);
    },
  };

  /* What approval actually produced, and what a person must still do. */
  const terminalNote = isNudge
    ? "Posts to Slack. Stays open until the owner acknowledges."
    : "Creates a Gmail draft under hello@. Stays open until a send is recorded.";

  return (
    <div className="space-y-5">
      <Panel
        title={email.subject}
        subtitle={`${email.sender} · ${email.email}`}
        right={
          <>
            <Menu
              ariaLabel="Change lane"
              trigger="Change lane"
              value={emailQueue(email.id)}
              options={queueOptions}
              onChange={(q) => moveEmail(email.id, q)}
            />
            <Menu
              ariaLabel="Set stage"
              trigger={
                <>
                  <span
                    className={cn(
                      "h-2 w-2 flex-none rounded-full",
                      STATUS_DOT[stageMeta.tone] ?? "bg-brand-stone",
                    )}
                    aria-hidden
                  />
                  <span className="font-medium text-brand-gray">Stage</span>
                  {stageMeta.short}
                </>
              }
              value={stage}
              options={STATUS_OPTIONS}
              onChange={(w) => setEmailStage(email.id, w as WorkStage)}
            />
          </>
        }
      >
        <div className="flex flex-wrap items-center gap-2">
          <Pill tone={stageMeta.tone}>{stageMeta.label}</Pill>
          <Pill tone="slate">{email.classification}</Pill>
          <Pill tone={PRIORITY_TONE[email.priority]}>
            {email.priority} priority
          </Pill>
          <Pill tone="outline">
            <User className="h-3 w-3" /> {email.owner}
          </Pill>
          <Pill tone="outline">Trigger: {email.trigger}</Pill>
          {email.dest && <Pill tone="outline">Files to: {email.dest}</Pill>}
          <AutoBadge system={badgeFor(email)} />
        </div>

        <p className="mt-3.5 rounded-xl border border-brand-primary/25 bg-brand-primary/[0.06] p-3.5 text-[12.5px] leading-snug text-brand-secondary">
          <span className="font-bold text-brand-primary">Recommendation · </span>
          {email.rec}
        </p>

        {email.ambiguous && (
          <p className="mt-3 flex items-start gap-2 rounded-xl border border-console-warn/30 bg-console-warn/[0.07] p-3.5 text-[12px] leading-snug text-console-warn">
            <AlertTriangle className="mt-px h-4 w-4 flex-none" />
            <span>
              Not confident enough to file a client-facing thread, so it
              abstains and asks.
            </span>
          </p>
        )}
      </Panel>

      {obligationId && <ObligationStrip hub={hub} obligationId={obligationId} />}

      {/* THE ORIGINAL, VERBATIM. Not a summary of it — a reviewer correcting
          a reply has to be able to read what was actually asked. */}
      {envelope?.original && (
        <Panel
          title="The message being answered"
          subtitle="Verbatim, as it arrived"
          right={<AutoBadge system="gmail" />}
        >
          <div className="rounded-xl border border-brand-mist bg-white p-4">
            <p className="text-[11.5px] text-brand-gray">
              <span className="font-bold text-brand-ink">{envelope.original.from}</span>
              {" · "}
              {envelope.original.when}
            </p>
            <p className="mt-1 text-[12.5px] font-bold text-brand-ink">
              {envelope.original.subject}
            </p>
            <p className="mt-2 whitespace-pre-wrap text-[12.5px] leading-relaxed text-brand-secondary">
              {envelope.original.body}
            </p>
          </div>
        </Panel>
      )}

      {/* evidence */}
      <Panel
        title="Why this recommendation"
        subtitle="Every line is a source a reviewer can check"
        bodyClassName="px-2 py-2"
      >
        <div className="divide-y divide-brand-mist/60">
          {evidence.map((ev) => (
            <EvidenceRow
              key={ev.label}
              source={ev.s}
              label={ev.label}
              excerpt={ev.excerpt}
              time={ev.time}
              onClick={() =>
                openDrawer({
                  title: ev.label,
                  source: ev.s,
                  label: ev.label,
                  excerpt: ev.excerpt,
                  time: ev.time,
                  client: clientName(email.clientId) || "Internal",
                })
              }
            />
          ))}
        </div>
      </Panel>

      {/* draft */}
      {draft && (
        <Panel
          title={isNudge ? "Internal nudge — not sent to the client" : "The exact draft"}
          subtitle={
            isNudge
              ? "Goes to the owner in Slack. The client sees nothing."
              : "Everything approval will create"
          }
          right={<Pill tone={authority.tone}>{authority.label}</Pill>}
        >
          {/* PADDED. `Facts` is a bare grid — it carries no padding of its own,
              because every other caller puts it inside a Panel that supplies
              it. Dropping it into a bordered box with none clipped the first
              column against the left edge. */}
          {envelope && (
            <div className="mb-3 rounded-xl border border-brand-mist bg-brand-surface px-4 py-3.5">
              <Facts
                facts={[
                  ["From", envelope.from],
                  ["To", envelope.to],
                  ...(envelope.cc ? ([["Cc", envelope.cc]] as [string, string][]) : []),
                  ["Subject", envelope.subject],
                  [
                    "Attachments",
                    envelope.attachments?.length
                      ? envelope.attachments.join(", ")
                      : "None",
                  ],
                ]}
              />
            </div>
          )}
          {isNudge && (
            <p className="mb-3 text-[11.5px] text-brand-gray">
              Slack DM to {email.owner}
            </p>
          )}

          {editing ? (
            <>
              <label className="sr-only" htmlFor={`draft-${email.id}`}>
                Edit the draft body
              </label>
              <textarea
                id={`draft-${email.id}`}
                value={draft}
                onChange={(e) => editDraft(email.id, e.target.value)}
                rows={Math.min(20, draft.split("\n").length + 3)}
                className="w-full rounded-xl border border-brand-primary/40 bg-white p-4 text-[12.5px] leading-relaxed text-brand-ink focus:border-brand-primary focus:outline-none"
              />
              <p className="mt-2 text-[11.5px] text-brand-gray">
                Your edits are what approval uses.
              </p>
            </>
          ) : (
            <DraftBlock text={draft} />
          )}

          {edited && !editing && (
            <p className="mt-2 inline-flex items-center gap-2 text-[11.5px] font-bold text-brand-primary">
              Edited by the reviewer
              <button
                type="button"
                onClick={() => clearDraftEdit(email.id)}
                className="font-medium text-brand-gray underline underline-offset-2"
              >
                revert to the prepared version
              </button>
            </p>
          )}

          {blockers.length > 0 && (
            <p className="mt-3 flex items-start gap-2 rounded-xl border border-console-bad/30 bg-console-bad/[0.05] p-3.5 text-[12px] leading-snug text-console-bad">
              <AlertTriangle className="mt-px h-4 w-4 flex-none" />
              <span>
                This says everything from the Sep 2 call is done.{" "}
                {blockers.length === 1 ? "One item is" : `${blockers.length} items are`} still
                open:{" "}
                <span className="font-bold">
                  {blockers.map((b) => OBLIGATION_META[b]?.title ?? b).join("; ")}
                </span>
                .
              </span>
            </p>
          )}

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            {status === "open" ? (
              <Actions
                actions={[
                  primaryAction,
                  {
                    label: editing ? "Done editing" : "Edit",
                    variant: "secondary",
                    onClick: () => setEditing((v) => !v),
                  },
                  {
                    label: "Keep in Inbox",
                    variant: "ghost",
                    onClick: () =>
                      setEmailStatus(
                        email.id,
                        "kept",
                        "Kept in Inbox — noted, still open",
                      ),
                  },
                  {
                    label: "Snooze 4h",
                    variant: "ghost",
                    onClick: () =>
                      setEmailStatus(
                        email.id,
                        "snoozed",
                        "Snoozed until 14:00 — it returns to this queue, it does not disappear",
                      ),
                  },
                ]}
              />
            ) : (
              <div className="flex flex-wrap items-center gap-2">
                <Pill tone="green">{DONE_LABEL[status] ?? "Handled"}</Pill>
                {/* THE RETURN LOOP. Keep and snooze used to be one-way: the
                    disposition moved off `open` and the review actions
                    vanished, so a deferred email could not come back. */}
                {(status === "kept" || status === "snoozed") && (
                  <Actions
                    actions={[
                      {
                        label:
                          status === "snoozed"
                            ? "Snooze expired — return to review"
                            : "Return to review",
                        variant: "secondary",
                        onClick: () =>
                          setEmailStatus(
                            email.id,
                            "open",
                            "Back in the review queue with its original actions",
                          ),
                      },
                    ]}
                  />
                )}
                {(status === "approved" || status === "nudged") && (
                  <Actions
                    actions={[
                      {
                        label: isNudge ? "Owner acknowledged" : "Record the send",
                        variant: "secondary",
                        onClick: () =>
                          setEmailStage(email.id, isNudge ? "in_progress" : "sent"),
                      },
                      {
                        label: "Mark completed",
                        variant: "ghost",
                        onClick: () => setEmailStage(email.id, "completed"),
                      },
                    ]}
                  />
                )}
              </div>
            )}
            <SectionLabel>Nothing sends without approval</SectionLabel>
          </div>

          {/* THE TERMINAL EFFECT, BESIDE THE BUTTON. Not in a footnote, not on
              another screen — F11. */}
          <p className="mt-3 text-[11.5px] leading-snug text-brand-gray">
            <span className="font-bold text-brand-ink">Approving · </span>
            {terminalNote} Simulated in this build.
          </p>
        </Panel>
      )}

      {!draft && (
        <Panel title="No draft prepared">
          <p className="text-[12.5px] text-brand-secondary">{email.rec}</p>
          <div className="mt-4">
            {status === "open" ? (
              <Actions
                actions={[
                  primaryAction,
                  {
                    label: "Keep in Inbox",
                    variant: "ghost",
                    onClick: () =>
                      setEmailStatus(
                        email.id,
                        "kept",
                        "Kept in Inbox — noted, still open",
                      ),
                  },
                ]}
              />
            ) : (
              <div className="flex flex-wrap items-center gap-2">
                <Pill tone="green">{DONE_LABEL[status] ?? "Handled"}</Pill>
                {(status === "kept" || status === "filed") && (
                  <Actions
                    actions={[
                      {
                        label: "Return to review",
                        variant: "secondary",
                        onClick: () =>
                          setEmailStatus(email.id, "open", "Back in the review queue"),
                      },
                    ]}
                  />
                )}
              </div>
            )}
          </div>
          {email.kind === "noaction" && (
            <p className="mt-3 text-[11.5px] leading-snug text-brand-gray">
              Filed only once Whitney has read it and taken no action — never on
              arrival.
            </p>
          )}
        </Panel>
      )}
    </div>
  );
}

/* ── screen ───────────────────────────────────────────────────── */

export function InboxScreen({ hub }: { hub: OpsHub }) {
  const { state, patch, emailStage, queueEmails, queueOpen } = hub;

  /* THREE CONTROLS ON THREE AXES — F03.

     The seven lanes are the client's own vocabulary and they stay. What they
     could not do is answer "what do *I* still owe?" or "what is still open?",
     because two lanes are about owners, two about state and three about
     subject. Owner and state are now their own filters and they cut across
     lanes; "All lanes" makes that visible rather than theoretical. */
  const lane = state.inboxQueue;
  const owner = state.inboxOwner;
  const stateFilter = state.inboxStateFilter;

  const base = useMemo(
    () => (lane === "all" ? [...EMAILS] : queueEmails(lane)),
    [lane, queueEmails],
  );

  const list = useMemo(
    () =>
      base.filter((e) => {
        if (owner !== "all" && e.owner !== owner) return false;
        if (stateFilter === "open" && !hub.isEmailOpen(e.id)) return false;
        if (stateFilter === "closed" && hub.isEmailOpen(e.id)) return false;
        if (stateFilter === "waiting") {
          const st = emailStage(e.id);
          if (st !== "waiting_ack" && st !== "waiting_reply") return false;
        }
        return true;
      }),
    [base, owner, stateFilter, emailStage, hub],
  );

  const owners = useMemo(
    () => [...new Set(EMAILS.map((e) => e.owner))].filter((o) => o && o !== "—"),
    [],
  );

  const selected = list.find((e) => e.id === state.emailId) ?? list[0] ?? null;
  const laneLabel =
    lane === "all" ? "All lanes" : (QUEUES.find((q) => q.id === lane)?.label ?? "");
  const openInView = list.filter((e) => hub.isEmailOpen(e.id)).length;

  return (
    <div className="space-y-5">
      {/* lane rail — the client's own categories, each declaring its axis */}
      <div className="flex flex-wrap gap-1.5 rounded-xl border border-brand-mist bg-white p-1.5">
        <button
          type="button"
          onClick={() => patch({ inboxQueue: "all", emailId: "" })}
          className={cn(
            "inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-[12.5px] transition-colors",
            lane === "all"
              ? "bg-brand-ink font-bold text-white"
              : "font-medium text-brand-secondary hover:bg-brand-mist/50",
          )}
        >
          All lanes
          <span
            className={cn(
              "rounded px-1.5 py-px text-[10.5px] font-bold tabular-nums",
              lane === "all" ? "bg-white/20 text-white" : "bg-brand-mist/80 text-brand-gray",
            )}
          >
            {EMAILS.filter((e) => hub.isEmailOpen(e.id)).length}
          </span>
        </button>
        {QUEUES.map((q) => {
          const open = queueOpen(q.id);
          const on = lane === q.id;
          return (
            <button
              key={q.id}
              type="button"
              onClick={() => patch({ inboxQueue: q.id, emailId: "" })}
              title={`Lane ${AXIS_META[QUEUE_AXIS[q.id]].label}`}
              className={cn(
                "inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-[12.5px] transition-colors",
                on
                  ? "bg-brand-primary font-bold text-white"
                  : "font-medium text-brand-secondary hover:bg-brand-mist/50",
              )}
            >
              {q.label}
              <span
                className={cn(
                  "rounded px-1.5 py-px text-[10.5px] font-bold tabular-nums",
                  on ? "bg-white/20 text-white" : "bg-brand-mist/80 text-brand-gray",
                )}
              >
                {open}
              </span>
            </button>
          );
        })}
      </div>

      {/* the two axes the lanes could not express */}
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-brand-mist bg-brand-surface px-3 py-2">
        <SectionLabel>Across lanes</SectionLabel>
        <Menu
          ariaLabel="Filter by owner"
          trigger={<>Owner · {owner === "all" ? "Anyone" : owner}</>}
          value={owner}
          options={[
            { value: "all", label: "Anyone" },
            ...owners.map((o) => ({ value: o, label: o })),
          ]}
          onChange={(v) => patch({ inboxOwner: v, emailId: "" })}
        />
        <Menu
          ariaLabel="Filter by lifecycle state"
          trigger={
            <>
              State ·{" "}
              {stateFilter === "all"
                ? "Any"
                : stateFilter === "open"
                  ? "Still open"
                  : stateFilter === "waiting"
                    ? "Waiting on someone"
                    : "Closed"}
            </>
          }
          value={stateFilter}
          options={[
            { value: "all", label: "Any state" },
            { value: "open", label: "Still open", hint: "Somebody still owes this" },
            {
              value: "waiting",
              label: "Waiting on someone",
              hint: "Waiting for an acknowledgement or a reply",
            },
            { value: "closed", label: "Closed", hint: "Completed or client informed" },
          ]}
          onChange={(v) => patch({ inboxStateFilter: v, emailId: "" })}
        />
        {(owner !== "all" || stateFilter !== "all" || lane === "all") && (
          <button
            type="button"
            onClick={() =>
              patch({
                inboxQueue: "needs_whitney",
                inboxOwner: "all",
                inboxStateFilter: "all",
                emailId: "",
              })
            }
            className="text-[11.5px] font-bold text-brand-primary underline underline-offset-2"
          >
            Clear
          </button>
        )}

      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
        {/* list */}
        <Panel
          title={laneLabel}
          subtitle={`${list.length} shown · ${openInView} open`}
          bodyClassName="px-2 py-2"
        >
          {list.length === 0 && <Empty>Nothing matches these filters.</Empty>}
          <ul className="space-y-1">
            {list.map((e) => {
              const meta = STAGE_META[emailStage(e.id)];
              const on = e.id === selected?.id;
              return (
                <li key={e.id}>
                  <button
                    type="button"
                    onClick={() => patch({ emailId: e.id })}
                    className={cn(
                      "w-full rounded-xl px-3 py-2.5 text-left transition-colors",
                      on
                        ? "bg-brand-primary/10 ring-1 ring-brand-primary/30"
                        : "hover:bg-brand-mist/40",
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        role="img"
                        aria-label={`${e.priority} priority`}
                        className={cn(
                          "h-1.5 w-1.5 flex-none rounded-full",
                          PRIORITY_DOT[e.priority],
                        )}
                      />
                      <span className="min-w-0 flex-1 truncate text-[12.5px] font-bold text-brand-ink">
                        {e.sender}
                      </span>
                      <Pill tone={meta.tone}>{meta.short}</Pill>
                    </div>
                    <p className="mt-0.5 truncate text-[12px] text-brand-secondary">
                      {e.subject}
                    </p>
                    <p className="mt-1 flex items-center gap-1.5 text-[11px] text-brand-gray">
                      <Clock className="h-3 w-3" />
                      {e.age}
                      {lane === "all" && (
                        <span className="ml-1 truncate text-brand-slate">
                          {QUEUES.find((q) => q.id === hub.emailQueue(e.id))?.label}
                        </span>
                      )}
                      {e.ambiguous && (
                        <span className="ml-1 inline-flex items-center gap-1 text-console-warn">
                          <AlertTriangle className="h-3 w-3" />
                          ambiguous
                        </span>
                      )}
                    </p>
                  </button>
                </li>
              );
            })}
          </ul>
        </Panel>

        {/* detail */}
        {selected ? (
          <EmailDetail key={selected.id} email={selected} hub={hub} />
        ) : (
          <Panel
            title="Nothing here"
            subtitle="No thread matches the current filters"
          >
            <p className="text-[12.5px] text-brand-secondary">
              Pick another lane, or clear the filters above.
            </p>
          </Panel>
        )}
      </div>
    </div>
  );
}
