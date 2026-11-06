/* Ops Watch — exceptions and recurring routines.

   FLAGS FLAG; THEY DO NOT CHASE. Every action on this screen produces a
   nudge, a draft or a correction for a human to send. Nothing contacts a
   client and nothing contacts a team member without an approval click.

   A NUDGE IS AN EVENT, NOT A RESOLUTION. Posting one used to flip the row to
   "Nudge posted" and drop the risk count — so Whitney could watch the number
   fall without anybody having replied. The count now asks the shared
   lifecycle whether the owner ACKNOWLEDGED (one of the four paths below);
   chasing is recorded on the item and changes nothing else.

   TWO TABS CARRY MOST OF THE ARGUMENT. `Data Quality` shows an automation
   ABSTAINING — one address has a high-confidence fix, the other has none and
   says so. And `Routines` is the native-vs-AI inventory, with each row
   carrying its trigger, queue, reviewer, destination, failure owner and
   completion signal so an efficiency output cannot be listed without a home. */

import { AlertTriangle, CheckCircle2 } from "lucide-react";
import {
  ACK_PATHS,
  CLIENTS,
  DIGEST_PREVIEW,
  INVALID_EMAILS,
  INVOICES,
  OPS_TABS,
  OVERDUE_TASKS,
  ROUTINES,
  TEAM_ACTIONS,
} from "@/data/opsHub";
import { OBLIGATION_BY_TEAM_ACTION, OBLIGATION_META } from "@/data/obligations";
import { STAGE_META, isAcknowledged } from "@/lib/opsHub";
import type { OpsHub } from "@/hooks/useOpsHub";
import { Actions, AutoBadge, Facts, Panel, Pill, SectionLabel, Stat, Tabs } from "../primitives";

export function OpsWatchScreen({ hub }: { hub: OpsHub }) {
  const {
    state,
    patch,
    counts,
    queueEmails,
    isEmailOpen,
    nudge,
    acknowledge,
    stageOf,
    eventsFor,
    setInvoice,
    resolveInvalid,
    openDrawer,
    toast,
  } = hub;

  /* DERIVED. The subtitle used to read "six of nine" against a table of ten
     rows — the kind of stale literal the hub's own comments warn about. */
  const nativeCount = ROUTINES.filter((r) =>
    ["clickup", "highlevel", "gmail", "zoom", "gmail_filter", "native_highlevel_ai"].includes(
      r.system,
    ),
  ).length;

  const tabCounts = {
    team: counts.teamRisk,
    waiting: queueEmails("waiting_client").filter((e) => isEmailOpen(e.id))
      .length,
    finance: counts.invoicesOpen,
    data: counts.invalidOpen,
    routines: 0,
  };

  return (
    <div className="space-y-5">
      <Tabs
        tabs={OPS_TABS}
        active={state.opsTab}
        counts={tabCounts}
        onSelect={(id) => patch({ opsTab: id })}
      />

      {/* ── team ───────────────────────────────────────────────── */}
      {state.opsTab === "team" && (
        <div className="space-y-5">
          <Panel
            title="Unacknowledged team actions"
            subtitle="Assigned, delivered, not yet picked up"
            right={<AutoBadge system="ai_hq" />}
          >
            <div className="space-y-3">
              {TEAM_ACTIONS.map((a) => {
                const obligationId = OBLIGATION_BY_TEAM_ACTION[a.id];
                const ob = obligationId ? OBLIGATION_META[obligationId] : null;
                const stage = obligationId ? stageOf(obligationId) : "unread";
                const acked = isAcknowledged(stage);
                const events = obligationId ? eventsFor(obligationId) : [];
                const chases = events.filter((e) => e.text.startsWith("Nudge posted"));
                return (
                  <div
                    key={a.id}
                    className="rounded-xl border border-brand-mist bg-white p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[13.5px] font-bold text-brand-ink">
                        {a.task}
                      </span>
                      <Pill tone="outline">{a.client}</Pill>
                      <Pill tone="slate">{a.owner}</Pill>
                      <Pill tone={STAGE_META[stage].tone} className="ml-auto">
                        {STAGE_META[stage].label}
                      </Pill>
                    </div>
                    <p className="mt-1.5 text-[12px] text-console-bad">{a.since}</p>
                    {ob && (
                      <p className="mt-1 truncate text-[11.5px] text-brand-gray">
                        {ob.title}
                      </p>
                    )}
                    <div className="mt-3">
                      <Facts facts={a.facts} />
                    </div>

                    {chases.length > 0 && (
                      <div className="mt-3 rounded-lg border border-brand-mist bg-brand-surface px-3 py-2">
                        <SectionLabel>Chase history</SectionLabel>
                        <ul className="mt-1.5 space-y-1">
                          {chases.map((e, i) => (
                            <li
                              key={i}
                              className="text-[11.5px] leading-snug text-brand-secondary"
                            >
                              {e.text} · {e.at}
                            </li>
                          ))}
                        </ul>
                        {!acked && (
                          <p className="mt-1.5 text-[11.5px] text-console-warn">
                            Still unacknowledged
                          </p>
                        )}
                      </div>
                    )}

                    <div className="mt-3">
                      {acked ? (
                        <div className="flex flex-wrap items-center gap-2">
                          <Pill tone="green">
                            <CheckCircle2 className="h-3 w-3" /> Acknowledged
                          </Pill>
                          <Actions
                            actions={[
                              {
                                label: "Owner marked it done",
                                variant: "ghost",
                                onClick: () =>
                                  obligationId &&
                                  hub.advance(
                                    obligationId,
                                    "completed",
                                    {
                                      actor: a.owner,
                                      text: "ClickUp task moved to Complete",
                                      where: "clickup",
                                    },
                                    "Completed — the commitment ledger and the account overview move with it",
                                  ),
                              },
                            ]}
                          />
                        </div>
                      ) : (
                        <Actions
                          actions={[
                            {
                              label: chases.length
                                ? `Chase again (${chases.length} sent)`
                                : "Preview & approve nudge",
                              variant: "primary",
                              onClick: () => nudge(a.id, a.owner),
                            },
                            {
                              label: "Owner reacted 👀",
                              variant: "secondary",
                              onClick: () => acknowledge(a.id, "reaction"),
                            },
                            {
                              label: "ClickUp status moved",
                              variant: "secondary",
                              onClick: () => acknowledge(a.id, "status moved"),
                            },
                            {
                              label: "Mark acknowledged by hand",
                              variant: "ghost",
                              onClick: () => acknowledge(a.id, "by hand"),
                            },
                          ]}
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="mt-4 text-[11.5px] text-brand-gray">
              A nudge is recorded on the item. Only an acknowledgement clears it.
            </p>
          </Panel>

          {/* The two rows behind Home's "overdue" figure. They were a literal
              `2` inside the count and appeared nowhere on this screen. */}
          <Panel
            title="Overdue in ClickUp"
            subtitle="The other half of Team Actions At Risk"
            right={<Pill tone="red">{OVERDUE_TASKS.length} overdue</Pill>}
          >
            <ul className="divide-y divide-brand-mist/70 overflow-hidden rounded-xl border border-brand-mist">
              {OVERDUE_TASKS.map((t) => (
                <li key={t.id} className="flex flex-wrap items-center gap-3 px-3.5 py-2.5">
                  <span className="min-w-0 flex-1 text-[12.5px] font-bold text-brand-ink">
                    {t.task}
                  </span>
                  <Pill tone="outline">{t.client}</Pill>
                  <Pill tone="slate">{t.owner}</Pill>
                  <Pill tone="red">{t.overdueBy}</Pill>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-[11.5px] text-brand-gray">
              Read from ClickUp. Execution stays there.
            </p>
          </Panel>

          <Panel
            title="What counts as acknowledged"
            subtitle="Four paths, because “acknowledged” is otherwise the vaguest word in the product"
          >
            <ul className="space-y-1.5">
              {ACK_PATHS.map((p) => (
                <li
                  key={p}
                  className="flex items-start gap-2 text-[12.5px] leading-snug text-brand-secondary"
                >
                  <span
                    className="mt-[6px] h-1.5 w-1.5 flex-none rounded-full bg-brand-primary"
                    aria-hidden
                  />
                  {p}
                </li>
              ))}
            </ul>
          </Panel>

          <Panel
            title="Monday overdue digest"
            subtitle="Deterministic ClickUp query. AI only groups and shortens it."
            right={<AutoBadge system="ai_hq" />}
          >
            <div className="grid gap-4 sm:grid-cols-3">
              <Stat label="Overdue tasks" value={6} />
              <Stat label="Team members" value={3} />
              <Stat label="Client accounts" value={4} />
            </div>
            <div className="mt-4">
              <Actions
                actions={[
                  {
                    label: "Preview Slack digest",
                    variant: "primary",
                    onClick: () =>
                      openDrawer({
                        title: "Monday overdue digest — Slack preview",
                        source: "slack",
                        label: "#team-ops",
                        excerpt: DIGEST_PREVIEW,
                        time: "Monday · 08:30",
                        client: "Internal",
                      }),
                  },
                ]}
              />
            </div>
          </Panel>
        </div>
      )}

      {/* ── waiting ────────────────────────────────────────────── */}
      {state.opsTab === "waiting" && (
        <Panel
          title="Waiting on clients"
          subtitle="Work that cannot progress until the client acts"
          right={<AutoBadge system="ai_hq" />}
        >
          <ul className="space-y-2.5">
            {queueEmails("waiting_client").map((e) => {
              const handled = !isEmailOpen(e.id);
              const c = CLIENTS.find((x) => x.id === e.clientId);
              return (
                <li
                  key={e.id}
                  className="flex flex-wrap items-center gap-3 rounded-xl border border-brand-mist bg-white px-4 py-3"
                >
                  <span className="min-w-[160px] flex-1 text-[12.5px] font-bold text-brand-ink">
                    {c?.name ?? e.sender}
                  </span>
                  <span className="min-w-[200px] flex-1 text-[12px] text-brand-secondary">
                    {e.subject}
                  </span>
                  <Pill tone={e.priority === "high" ? "red" : "amber"}>{e.age}</Pill>
                  {handled ? (
                    <Pill tone="green">Follow-up drafted</Pill>
                  ) : (
                    <Actions
                      actions={[
                        {
                          label: "Open in Inbox",
                          variant: "ghost",
                          onClick: () =>
                            hub.go("inbox", {
                              inboxQueue: "waiting_client",
                              emailId: e.id,
                            }),
                        },
                      ]}
                    />
                  )}
                </li>
              );
            })}
          </ul>
          <p className="mt-4 text-[11.5px] leading-snug text-brand-gray">
            Nobody owns the waiting. Aging it in one place is most of the fix.
          </p>
        </Panel>
      )}

      {/* ── finance ────────────────────────────────────────────── */}
      {state.opsTab === "finance" && (
        <Panel
          title="Overdue invoices · Wedding Industry Ads account"
          subtitle="The automated reminder already went out. This is the personal follow-up that actually lands."
          right={<AutoBadge system="native_highlevel_ai" />}
        >
          <p className="mb-3 text-[11.5px] text-brand-gray">
            WIA account only — LeadLock Pro takes no payments.
          </p>
          <div className="space-y-3">
            {INVOICES.map((inv) => {
              const st = state.invoiceState[inv.id] ?? "overdue";
              return (
                <div
                  key={inv.id}
                  className={
                    "rounded-xl border bg-white p-4 " +
                    (state.invoiceId === inv.id
                      ? "border-brand-primary ring-1 ring-brand-primary/25"
                      : "border-brand-mist")
                  }
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[13.5px] font-bold text-brand-ink">
                      {inv.id}
                    </span>
                    <Pill tone="outline">{inv.client}</Pill>
                    <span className="text-[15px] font-bold tracking-[-0.02em] text-brand-ink">
                      {inv.amount}
                    </span>
                    <Pill
                      tone={
                        st === "handled" ? "green" : st === "draft_ready" ? "blue" : "red"
                      }
                      className="ml-auto"
                    >
                      {st === "handled"
                        ? "Handled"
                        : st === "draft_ready"
                          ? "Personal draft ready"
                          : `${inv.age} overdue`}
                    </Pill>
                  </div>
                  <div className="mt-3">
                    <Facts
                      facts={[
                        ["Due", inv.due],
                        ["Contact", inv.contact],
                        ["Standard reminder", "Sent automatically by HighLevel"],
                        ["Payment link", "Available on the invoice record"],
                      ]}
                    />
                  </div>
                  <div className="mt-3">
                    {st === "handled" ? (
                      <Pill tone="green">
                        <CheckCircle2 className="h-3 w-3" /> Closed
                      </Pill>
                    ) : (
                      <Actions
                        actions={[
                          {
                            label:
                              st === "draft_ready"
                                ? "Open draft in Inbox"
                                : "Prepare personal follow-up",
                            variant: "primary",
                            onClick: () =>
                              st === "draft_ready"
                                ? hub.go("inbox", {
                                    inboxQueue: "finance_followup",
                                    emailId: "e12",
                                  })
                                : setInvoice(
                                    inv.id,
                                    "draft_ready",
                                    "Personal Gmail follow-up prepared — simulated",
                                  ),
                          },
                          {
                            label: "Mark handled",
                            variant: "ghost",
                            onClick: () =>
                              setInvoice(
                                inv.id,
                                "handled",
                                `${inv.id} marked handled — counts updated`,
                              ),
                          },
                        ]}
                      />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          <p className="mt-4 text-[11.5px] leading-snug text-brand-gray">
            Automated dues land in spam. This drafts the personal note that works.
          </p>
        </Panel>
      )}

      {/* ── data quality ───────────────────────────────────────── */}
      {state.opsTab === "data" && (
        <Panel
          title="Invalid lead emails"
          subtitle="Both HighLevel accounts. Native verification branches these to human review."
          right={<AutoBadge system="highlevel" />}
        >
          <p className="mb-3 text-[11.5px] text-brand-gray">
            Runs in both accounts. Correcting the address is half the job — the
            contact also re-enters the workflow.
          </p>
          <div className="space-y-3">
            {INVALID_EMAILS.map((q) => {
              const resolved = !!state.invalidState[q.id];
              return (
                <div
                  key={q.id}
                  className="rounded-xl border border-brand-mist bg-white p-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[13.5px] font-bold text-brand-ink">
                      {q.name}
                    </span>
                    {/* The tenant, on the row. Two HighLevel accounts run
                        this check and their rows are otherwise identical —
                        which is how half the work goes missing. */}
                    <Pill tone="slate">{q.tenant}</Pill>
                    <Pill tone={q.lowConfidence ? "red" : "amber"}>{q.validity}</Pill>
                    <Pill tone={resolved ? "green" : "outline"} className="ml-auto">
                      {resolved ? "Resolved" : q.when}
                    </Pill>
                  </div>
                  <p className="mt-1 text-[12px] text-brand-gray">{q.role}</p>
                  <div className="mt-3">
                    <Facts
                      facts={[
                        ["Entered", q.entered],
                        ["Suggested", q.suggestion],
                        ["Confidence", q.confidence],
                      ]}
                    />
                  </div>

                  {q.lowConfidence && !resolved && (
                    <p className="mt-3 flex items-start gap-2 rounded-lg border border-console-warn/30 bg-console-warn/[0.07] p-3 text-[12px] leading-snug text-console-warn">
                      <AlertTriangle className="mt-px h-4 w-4 flex-none" />
                      <span>
                        No safe correction exists for <code>@rmail</code>, so none
                        is offered. Guessing here would silently rewrite a real
                        lead’s address — the one failure that makes the whole
                        queue untrustworthy.
                      </span>
                    </p>
                  )}

                  <div className="mt-3">
                    {resolved ? (
                      <Pill tone="green">
                        <CheckCircle2 className="h-3 w-3" /> Handled
                      </Pill>
                    ) : (
                      <Actions
                        actions={
                          q.lowConfidence
                            ? [
                                {
                                  label: "Ask the lead to re-enter",
                                  variant: "primary",
                                  onClick: () =>
                                    resolveInvalid(
                                      q.id,
                                      "Re-entry request drafted — no address was rewritten",
                                    ),
                                },
                                {
                                  label: "Leave for review",
                                  variant: "ghost",
                                  onClick: () =>
                                    toast("Left in the queue for a human"),
                                },
                              ]
                            : [
                                {
                                  label: `Apply ${q.suggestion}`,
                                  variant: "primary",
                                  onClick: () =>
                                    resolveInvalid(
                                      q.id,
                                      `Corrected to ${q.suggestion} — simulated`,
                                    ),
                                },
                                {
                                  label: "Reject suggestion",
                                  variant: "ghost",
                                  onClick: () =>
                                    toast("Suggestion rejected — left unresolved"),
                                },
                              ]
                        }
                      />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      )}

      {/* ── routines ───────────────────────────────────────────── */}
      {state.opsTab === "routines" && (
        <Panel
          title="Recurring routines"
          subtitle={`${nativeCount} of ${ROUTINES.length} are platform behaviour we are not rebuilding`}
        >
          <div className="space-y-2.5">
            {ROUTINES.map((r) => (
              <div
                key={r.title}
                className="rounded-xl border border-brand-mist bg-white p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[13px] font-bold text-brand-ink">
                    {r.title}
                  </span>
                  <AutoBadge system={r.system} />
                  <Pill tone="outline">{r.initiative}</Pill>
                  <Pill
                    tone={
                      r.status === "Needs review"
                        ? "amber"
                        : r.status === "Not automated"
                          ? "red"
                          : "green"
                    }
                    className="ml-auto"
                  >
                    {r.status}
                  </Pill>
                </div>
                <p className="mt-1.5 text-[11.5px] text-brand-gray">{r.cadence}</p>
                {r.checklist.length > 0 && (
                  <div className="mt-2.5 flex flex-wrap gap-1.5">
                    {r.checklist.map((c) => (
                      <Pill key={c} tone="outline">
                        {c}
                      </Pill>
                    ))}
                  </div>
                )}
                <p className="mt-2.5 text-[11.5px] leading-snug text-brand-secondary">
                  {r.note}
                </p>

                {/* Trigger → queue → reviewer → destination → failure owner →
                    completion. The six answers that turn "we automate this"
                    into something a person can actually follow. */}
                {/* Six answers as chips rather than a six-row table under
                    every routine — ten of those stacked read as a document. */}
                <div className="mt-2.5 flex flex-wrap gap-1.5">
                  <Pill tone="outline">Review · {r.reviewer.split(/[—,.]/)[0].trim()}</Pill>
                  <Pill tone="outline">Lands in · {r.destination.split(/[—(]/)[0].trim()}</Pill>
                  <Pill tone="outline">
                    If it fails · {r.failureOwner.split(/[—,.;]/)[0].trim()}
                  </Pill>
                </div>
                {r.missingInput && (
                  <p className="mt-2 flex items-start gap-1.5 text-[11.5px] leading-snug text-console-warn">
                    <AlertTriangle className="mt-px h-3.5 w-3.5 flex-none" />
                    {r.missingInput.split(/(?<=\.)\s/)[0]}
                  </p>
                )}
              </div>
            ))}
          </div>
          <p className="mt-4 text-[11.5px] text-brand-gray">
            Native means configuration, not a build. Exceptions land in the
            queues above.
          </p>
        </Panel>
      )}
    </div>
  );
}
