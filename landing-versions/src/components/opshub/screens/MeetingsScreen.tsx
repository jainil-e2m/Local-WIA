/* Meetings — one reviewable execution pack per meeting.

   THREE STATUSES, NOT TWO. `needs_review` can be approved. `executed` is
   done. `needs_source` CANNOT be approved at all — the pack is blocked on a
   connector, and offering an approve button there would be a lie. The Harbor
   House pack exists purely to show that state, because a demo in which every
   integration succeeds teaches nobody what Thursday morning actually looks
   like when a Fathom key is user-scoped and the recorder never shared the
   meeting. */

import { useMemo } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Clock,
  Users,
} from "lucide-react";
import {
  AUTHORITY_META,
  MEETINGS,
  MEETING_FILTERS,
  PACK_EXCEPTIONS,
  packOutputs,
  type Meeting,
  type PackOutput,
} from "@/data/opsHub";
import { OBLIGATION_META } from "@/data/obligations";
import { STAGE_META } from "@/lib/opsHub";
import type { OpsHub } from "@/hooks/useOpsHub";
import { cn } from "@/lib/utils";
import {
  Actions,
  AutoBadge,
  Card,
  DraftBlock,
  Empty,
  Facts,
  Panel,
  Pill,
  SectionLabel,
  SourceChip,
} from "../primitives";

const STATUS_META: Record<
  string,
  { label: string; tone: "blue" | "green" | "red" | "amber" }
> = {
  needs_review: { label: "Needs review", tone: "blue" },
  approved: { label: "Released", tone: "green" },
  executed: { label: "Executed", tone: "green" },
  needs_source: { label: "Blocked · source", tone: "red" },
  /* A real state, not a toast. Sending a pack back used to raise a message
     that evaporated, leaving the pack sitting in "Needs review" as though
     nothing had been rejected. */
  revision: { label: "Awaiting revision", tone: "amber" },
};

const OUTPUT_RESULT: Record<
  string,
  { label: string; tone: "outline" | "green" | "red" | "amber" | "slate" }
> = {
  pending: { label: "Not released", tone: "outline" },
  released: { label: "Released", tone: "green" },
  failed: { label: "Failed", tone: "red" },
  held: { label: "Held back", tone: "slate" },
  manual: { label: "Handed to a person", tone: "amber" },
};

const TYPE_LABEL: Record<string, string> = {
  client: "Client call",
  internal: "Internal",
  sales: "Sales",
  office_hours: "Office Hours",
};

/* Router-shaped, and deliberately hook-free: the list and the detail hold
   their own hooks, so switching between them cannot change hook order. */
export function MeetingsScreen({ hub }: { hub: OpsHub }) {
  const detail = hub.state.meetingId
    ? MEETINGS.find((x) => x.id === hub.state.meetingId)
    : undefined;

  return detail ? (
    <MeetingDetail hub={hub} meeting={detail} />
  ) : (
    <MeetingList hub={hub} />
  );
}

function MeetingList({ hub }: { hub: OpsHub }) {
  const { state, patch, meetingPackStatus } = hub;

  const list = useMemo(
    () =>
      MEETINGS.filter((m) => {
        const s = meetingPackStatus(m);
        const f = state.meetingFilter;
        if (f === "needs_review") return s === "needs_review";
        if (f === "exceptions") return s === "needs_source";
        if (f === "processed") return s === "approved" || s === "executed";
        return m.type === f;
      }),
    [state.meetingFilter, meetingPackStatus],
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-1.5 rounded-xl border border-brand-mist bg-white p-1.5">
        {MEETING_FILTERS.map((f) => {
          const on = state.meetingFilter === f.id;
          return (
            <button
              key={f.id}
              type="button"
              onClick={() => patch({ meetingFilter: f.id })}
              className={cn(
                "rounded-lg px-3 py-1.5 text-[12.5px] transition-colors",
                on
                  ? "bg-brand-primary font-bold text-white"
                  : "font-medium text-brand-secondary hover:bg-brand-mist/50",
              )}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {/* WHICH BUILD OWNS WHAT. A client call's execution pack is this screen's
          job (MK-01 → MK-03, CC-04). The two reads that overlap another build
          say so rather than competing with it: an Internal pack is the same
          extraction the Internal Meeting console runs, and only that console
          keeps the carry-over ledger that remembers an item across weeks; an
          Office Hours pack carries the session recap, and the attendance
          counters behind it belong to the Roll Call console. */}
      <p className="text-[11.5px] leading-snug text-brand-gray">
        Client and sales packs are built here. Internal and Office Hours mirror their own consoles.
      </p>

      {list.length === 0 && (
        <Empty>No meetings match this filter right now.</Empty>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {list.map((m) => {
          const s = meetingPackStatus(m);
          const meta = STATUS_META[s];
          return (
            <Card key={m.id} onClick={() => patch({ meetingId: m.id })}>
              <div className="flex flex-wrap items-center gap-2">
                <SourceChip source={m.source} />
                <Pill tone="outline">{TYPE_LABEL[m.type]}</Pill>
                <Pill tone={meta.tone} className="ml-auto">
                  {meta.label}
                </Pill>
              </div>
              <p className="mt-2.5 text-[15px] font-bold leading-tight text-brand-ink">
                {m.title}
              </p>
              <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11.5px] text-brand-gray">
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {m.date} · {m.duration}
                </span>
                <span className="inline-flex items-center gap-1">
                  <Users className="h-3 w-3" />
                  Host {m.host}
                </span>
                <span>{m.channel}</span>
              </p>
              {/* Every pack in the corpus carries exactly one risk, so the
                  unpluralised form was the one a client actually saw: "1
                  risks", three times on one screen. */}
              <div className="mt-3 flex flex-wrap items-center gap-1.5">
                <Pill tone="outline">
                  {m.tasks.length} {m.tasks.length === 1 ? "action" : "actions"}
                </Pill>
                <Pill tone="outline">
                  {m.decisions.length}{" "}
                  {m.decisions.length === 1 ? "decision" : "decisions"}
                </Pill>
                {m.risks.length > 0 && (
                  <Pill tone="amber">
                    {m.risks.length} {m.risks.length === 1 ? "risk" : "risks"}
                  </Pill>
                )}
              </div>
              <p className="mt-3 inline-flex items-center gap-1.5 text-[12px] font-bold text-brand-primary">
                Open execution pack <ArrowRight className="h-3.5 w-3.5" />
              </p>
            </Card>
          );
        })}
      </div>

      <p className="text-[11.5px] leading-snug text-brand-gray">
        Intake is a human paste, not an automatic pull. The source label says
        which system the transcript came from.
      </p>
    </div>
  );
}

/* ── detail ───────────────────────────────────────────────────── */

function MeetingDetail({ hub, meeting: m }: { hub: OpsHub; meeting: Meeting }) {
  const { state, patch, meetingPackStatus, releasePack, sendPackBack, reopenPack, fixException, toast } =
    hub;
  const status = meetingPackStatus(m);
  const blocked = status === "needs_source";
  const done = status === "approved" || status === "executed";
  const outputs = useMemo(() => packOutputs(m), [m]);
  const releasable = outputs.filter(
    (o) => !hub.outputHeld(m.id, o.id) && hub.outputState(m.id, o.id) === "pending",
  ).length;
  const failedCount = outputs.filter((o) => hub.outputState(m.id, o.id) === "failed").length;
  const heldCount = outputs.filter((o) => hub.outputState(m.id, o.id) === "held").length;

  return (
    <div className="space-y-5">
      <button
        type="button"
        onClick={() => patch({ meetingId: null })}
        className="inline-flex items-center gap-2 text-[12px] font-bold uppercase tracking-[0.1em] text-brand-gray transition-colors hover:text-brand-ink"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All meetings
      </button>

      <Panel
        title={m.title}
        subtitle={`${m.date} · ${m.duration} · host ${m.host} · ${m.channel}`}
        right={
          <>
            <SourceChip source={m.source} />
            <Pill tone={STATUS_META[status].tone}>{STATUS_META[status].label}</Pill>
          </>
        }
      >
        <Facts
          facts={[
            ["Type", TYPE_LABEL[m.type]],
            ["Filing destination", m.fileDest],
          ]}
        />
      </Panel>

      {/* exceptions first — you cannot review a pack whose source failed */}
      {m.exceptions && (
        <Panel
          title="Exceptions"
          subtitle="Each one is resolvable here"
          right={<AutoBadge system="validation" />}
        >
          <div className="space-y-3">
            {PACK_EXCEPTIONS.map((d) => {
              const resolved = !!state.packExceptions[d.key];
              return (
                <div
                  key={d.key}
                  className={cn(
                    "rounded-xl border p-4",
                    resolved
                      ? "border-console-good/30 bg-console-good/[0.05]"
                      : "border-console-bad/30 bg-console-bad/[0.04]",
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <SourceChip source={d.system} />
                    <Pill tone={resolved ? "green" : "red"}>
                      {resolved ? "RESOLVED" : d.code}
                    </Pill>
                  </div>
                  <p className="mt-2 text-[13px] font-bold text-brand-ink">
                    {resolved ? `${d.message} — resolved` : d.message}
                  </p>
                  <p className="mt-1 text-[12px] leading-snug text-brand-secondary">
                    {resolved
                      ? "Resolved in this demo session. Reset the demo in Settings to see the exception again."
                      : d.recovery}
                  </p>
                  <div className="mt-3">
                    {resolved ? (
                      <Pill tone="green">
                        <CheckCircle2 className="h-3 w-3" /> Resolved
                      </Pill>
                    ) : (
                      <Actions
                        actions={d.buttons.map((b, i) => ({
                          label: b[0],
                          variant: b[1] === "primary" ? "primary" : "ghost",
                          onClick: () =>
                            i === 0
                              ? fixException(
                                  d.key,
                                  `${d.message} — resolved (simulated)`,
                                )
                              : toast(`${b[0]} — demo action, nothing is written`),
                        }))}
                      />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        {/* intelligence */}
        <Panel title="Meeting intelligence" subtitle="Extracted, then attributed">
          <div className="space-y-4">
            <Block label="Decisions" items={m.decisions} />
            <Block label="WIA committed to" items={m.wiaCommitments} />
            <Block
              label="Client committed to"
              items={m.clientCommitments}
              empty="Nothing committed by the client on this call."
            />
            <Block label="Risks" items={m.risks} tone="amber" />
          </div>
        </Panel>

        {/* moments */}
        <Panel
          title="Source moments"
          subtitle="Each action below traces to one of these timestamps"
        >
          {m.moments.length === 0 ? (
            <Empty>
              No transcript was returned for this meeting.
            </Empty>
          ) : (
            <ul className="space-y-2.5">
              {m.moments.map((mo) => (
                <li
                  key={mo.ts + mo.tag}
                  className="rounded-xl border border-brand-mist bg-brand-surface p-3.5"
                >
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-brand-ink px-1.5 py-0.5 text-[10.5px] font-bold tabular-nums text-white">
                      {mo.ts}
                    </span>
                    <Pill tone="outline">{mo.tag}</Pill>
                  </div>
                  <p className="mt-2 text-[12.5px] italic leading-snug text-brand-secondary">
                    {mo.text}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      {/* THE PACK, AS SEPARATE OUTPUTS — F04 and F02.

          Was one list and one "Approve pack" button. That hid two things: a
          reviewer could not see or correct the exact Slack and client
          messages being approved, and a whole-pack approval said nothing
          about which authority applied to three internal ClickUp tasks
          versus one client-facing email. Each output now carries its own
          content, its own approver, its own release decision and its own
          RESULT — because a pack is several dispatches and they do not all
          succeed together. */}
      <Panel
        title="Execution pack"
        subtitle="Approve each output on its own"
        right={<AutoBadge system="ai_hq" />}
      >
        <div className="space-y-3">
          {outputs.map((o) => (
            <OutputCard key={o.id} hub={hub} meeting={m} output={o} locked={blocked} />
          ))}
        </div>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-brand-mist pt-4">
          {blocked ? (
            <div>
              <Pill tone="red">Cannot approve — source unavailable</Pill>
              <p className="mt-2 max-w-[520px] text-[11.5px] leading-snug text-brand-gray">
                No transcript arrived, so these actions came from the invite and
                the Slack thread. Resolve the exception first.
              </p>
            </div>
          ) : status === "revision" ? (
            <div>
              <Pill tone="amber">Awaiting revision</Pill>
              <p className="mt-2 max-w-[520px] text-[11.5px] leading-snug text-brand-gray">
                Sent back. Stays unreleased until somebody re-opens it.
              </p>
              <div className="mt-3">
                <Actions
                  actions={[
                    {
                      label: "Re-open for review",
                      variant: "secondary",
                      onClick: () =>
                        reopenPack(m.id, "Back in the review queue — simulated"),
                    },
                  ]}
                />
              </div>
            </div>
          ) : done ? (
            <div>
              <Pill tone="green">
                <CheckCircle2 className="h-3 w-3" />
                {status === "executed" ? "Executed" : "Released"}
              </Pill>
              {failedCount > 0 && (
                <p className="mt-2 flex items-start gap-2 text-[11.5px] leading-snug text-console-bad">
                  <AlertTriangle className="mt-px h-3.5 w-3.5 flex-none" />
                  {failedCount} failed — retry or hand to a person.
                </p>
              )}
              {heldCount > 0 && (
                <p className="mt-1 text-[11.5px] text-brand-gray">
                  {heldCount} held back
                </p>
              )}
            </div>
          ) : (
            <Actions
              actions={[
                {
                  label: `Release ${releasable} of ${outputs.length} outputs`,
                  variant: "primary",
                  disabled: releasable === 0,
                  onClick: () =>
                    releasePack(
                      m.id,
                      `${releasable} output${releasable === 1 ? "" : "s"} released — simulated. Held items were not dispatched.`,
                    ),
                },
                {
                  label: "Send back for revision",
                  variant: "ghost",
                  onClick: () =>
                    sendPackBack(
                      m.id,
                      "Returned for edits — the pack now reads “awaiting revision”",
                    ),
                },
              ]}
            />
          )}
          <SectionLabel>Per output, not per pack</SectionLabel>
        </div>

        <p className="mt-3 text-[11.5px] leading-snug text-brand-gray">
          Creates tasks, files to Drive, posts internally. Client email stays a
          Gmail draft. Simulated in this build.
        </p>
      </Panel>
    </div>
  );
}

/* ── one output ───────────────────────────────────────────────── */

function OutputCard({
  hub,
  meeting,
  output: o,
  locked,
}: {
  hub: OpsHub;
  meeting: Meeting;
  output: PackOutput;
  locked: boolean;
}) {
  const { outputState, outputHeld, toggleOutputHold, retryOutput, assignOutputManually, stageOf } =
    hub;
  const result = outputState(meeting.id, o.id);
  const held = outputHeld(meeting.id, o.id);
  const authority = AUTHORITY_META[o.authority];
  const owner = hub.state.outputOwner[`${meeting.id}:${o.id}`];
  const linked = o.obligationId ? OBLIGATION_META[o.obligationId] : null;

  return (
    <div
      className={cn(
        "rounded-xl border p-4",
        result === "failed"
          ? "border-console-bad/40 bg-console-bad/[0.04]"
          : result === "released"
            ? "border-console-good/30 bg-console-good/[0.04]"
            : held
              ? "border-brand-stone bg-brand-mist/25"
              : "border-brand-mist bg-white",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <SourceChip source={o.source} />
        <span className="text-[13px] font-bold text-brand-ink">{o.label}</span>
        <Pill tone={o.clientFacing ? "red" : "slate"}>
          {o.clientFacing ? "Client-facing" : "Internal"}
        </Pill>
        <Pill tone={authority.tone}>{authority.label}</Pill>
        <Pill tone={OUTPUT_RESULT[result].tone} className="ml-auto">
          {OUTPUT_RESULT[result].label}
        </Pill>
      </div>
      <p className="mt-1.5 text-[11.5px] text-brand-gray">{o.destination}</p>

      {o.body && (
        <div className="mt-3">
          <DraftBlock text={o.body} label="Exactly what gets created" />
        </div>
      )}

      {linked && (
        <p className="mt-2 truncate text-[11.5px] text-brand-gray">
          {linked.title} · {STAGE_META[stageOf(o.obligationId!)].label.toLowerCase()}
        </p>
      )}

      {result === "failed" && (
        <div className="mt-3 rounded-lg border border-console-bad/30 bg-white p-3">
          <p className="text-[12px] font-bold text-console-bad">
            {o.failureReason}
          </p>
          <div className="mt-2.5">
            <Actions
              actions={[
                {
                  label: "Retry",
                  variant: "primary",
                  onClick: () =>
                    retryOutput(
                      meeting.id,
                      o.id,
                      "Retried and posted — no duplicates",
                    ),
                },
                {
                  label: `Hand to ${o.manualOwner ?? "a person"}`,
                  variant: "ghost",
                  onClick: () =>
                    assignOutputManually(meeting.id, o.id, o.manualOwner ?? "Gisselle"),
                },
              ]}
            />
          </div>
        </div>
      )}

      {result === "manual" && owner && (
        <p className="mt-2 text-[11.5px] font-bold text-console-warn">
          {owner} is posting this by hand
        </p>
      )}

      {!locked && result === "pending" && (
        <label className="mt-3 inline-flex cursor-pointer items-center gap-2 text-[11.5px] text-brand-secondary">
          <input
            type="checkbox"
            checked={held}
            onChange={() => toggleOutputHold(meeting.id, o.id)}
            className="h-3.5 w-3.5 accent-[#5070ff]"
          />
          Hold back
        </label>
      )}
    </div>
  );
}

function Block({
  label,
  items,
  tone,
  empty,
}: {
  label: string;
  items: string[];
  tone?: "amber";
  empty?: string;
}) {
  return (
    <div>
      <SectionLabel>{label}</SectionLabel>
      {items.length === 0 ? (
        <p className="mt-1.5 text-[12px] text-brand-gray">{empty ?? "None."}</p>
      ) : (
        <ul className="mt-1.5 space-y-1">
          {items.map((i) => (
            <li
              key={i}
              className={cn(
                "flex items-start gap-2 text-[12.5px] leading-snug",
                tone === "amber" ? "text-console-warn" : "text-brand-secondary",
              )}
            >
              <span
                className={cn(
                  "mt-[6px] h-1.5 w-1.5 flex-none rounded-full",
                  tone === "amber" ? "bg-console-warn" : "bg-brand-primary",
                )}
                aria-hidden
              />
              {i}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
