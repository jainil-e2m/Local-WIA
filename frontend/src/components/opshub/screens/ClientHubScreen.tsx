/* Client Hub — the operational record per client.

   It is not a CRM and does not try to be: no pipeline, no deal stages, no
   contact management. It is the record Inbox, Meetings and Ops Watch read
   from, gathered per account.

   THREE READINGS, THEN THE LEDGERS. Spine is the whole engagement on a time
   axis, Now is this week, Brief is what you hand the next account manager.
   All three are projections over ONE event log (data/engagement) — which is
   what makes the record connected rather than five lists drawn side by side.
   The ledgers underneath them (Commitments, Timeline, Meetings, Money,
   Attendance) are the same joins they always were, reached as drill-downs.

   NOT ONE OF THEM CALLS A MODEL. Every count, date, duration, gap and brief
   line is arithmetic over rows already in memory. The ask panel routes rather
   than generates. So the cost of this screen is the cost of the API polls
   behind it, and looking at an account twice costs the same as looking at it
   once — see the header of the Client Hub section in `data/opsHub` for why
   that is the whole design.

   TIME IS COMPUTED, NEVER STORED. The Ops Hub corpus carries display strings
   ("Today", "2d ago"), which is why staleness could not be computed from it
   and why a timeline could not be drawn. The engagement record carries real
   ISO timestamps and everything temporal is derived against a frozen
   DEMO_NOW — see the header of data/engagement for why the clock is frozen.

   THE TAB SET IS DERIVED FROM ACCOUNT SHAPE. `clientTabs` gives a prospect
   no Money tab and an Accelerator member Attendance in place of Meetings,
   because a fixed bar hands a third of the book empty screens.

   WHAT REPLACED WHAT. Overview restated the header, and Activity /
   Communication / Tasks rendered the same unfiltered timeline three times —
   four tabs, two views. Now answers "what is the state of this account",
   Timeline carries the source filter those three labels only implied, and
   Commitments surfaces the promise ledger that existed in the data model and
   was visible nowhere per-account. */

import { useMemo } from "react";
import { ArrowLeft, ArrowRight, ExternalLink, Sparkles } from "lucide-react";
import { engagementFor, type EngagementRecord } from "@/data/engagement";
import {
  HEALTH_META,
  currentPhase,
  engagementAgeDays,
  fmtDuration,
  fmtRel,
  laneHealth,
  activityBuckets,
} from "@/lib/engagement";
import { SpineView } from "../clienthub/SpineView";
import { BriefView } from "../clienthub/BriefView";
import {
  ACK_META,
  ASK_ROUTES,
  ATTENDANCE_STATE_META,
  CLIENTS,
  CLIENT_ATTENDANCE,
  CLIENT_INVOICES,
  CLIENT_TIMELINES,
  COMMITMENTS,
  COMMITMENT_STATE_META,
  EMAILS,
  INVOICE_STATE_META,
  MEETINGS,
  RECENT_WHEN,
  liveCommitment,
  clientShape,
  clientTabs,
  money,
  type Client,
  type Commitment,
  type TimelineRow,
} from "@/data/opsHub";
import { SOURCE_META, SOURCE_ORDER } from "@/lib/opsHub";
import type { OpsHub } from "@/hooks/useOpsHub";
import {
  Card,
  Empty,
  Facts,
  Panel,
  Pill,
  SectionLabel,
  SourceDot,
  Stat,
  Tabs,
} from "../primitives";

const SHAPE_LABEL = {
  retainer: "Retainer",
  accelerator: "Accelerator member",
  prospect: "Prospect",
} as const;

export function ClientHubScreen({ hub }: { hub: OpsHub }) {
  const { state, patch } = hub;
  /* Flags read LIVE stages now. Acknowledging a chase on Ops Watch or
     completing a delivery in Meetings changes these pills in the same tick —
     they were computed from static data and moved for nothing. */

  if (state.clientId) {
    const c = CLIENTS.find((x) => x.id === state.clientId);
    if (c) return <ClientDetail hub={hub} client={c} />;
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {CLIENTS.map((c) => {
          const flags = hub.flagsFor(c.id);
          const rec = engagementFor(c.id);
          return (
            <Card
              key={c.id}
              onClick={() =>
                patch({
                  clientId: c.id,
                  clientTab: "spine",
                  spineZoom: "all",
                  spineLane: "all",
                  spineEventId: null,
                  askAnswer: null,
                  timelineSource: "all",
                  commitSide: "all",
                  commitState: "all",
                })
              }
            >
              <div className="flex flex-wrap items-center gap-2">
                <Pill tone={c.status === "prospect" ? "violet" : "slate"}>
                  {c.service}
                </Pill>
                <Pill tone="outline">{SHAPE_LABEL[clientShape(c)]}</Pill>
              </div>
              <p className="mt-2.5 text-[15px] font-bold leading-tight text-brand-ink">
                {c.name}
              </p>
              <p className="mt-0.5 text-[12px] text-brand-gray">
                {c.contact} · {c.email}
              </p>
              <p className="mt-2.5 text-[12.5px] font-bold text-brand-secondary">
                {c.opStatus}
              </p>
              {rec && <CardSpark rec={rec} client={c} />}
              {flags.length > 0 ? (
                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  {flags.map((f) => (
                    <Pill key={f.text} tone={f.tone}>
                      {f.text}
                    </Pill>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-[11.5px] text-console-good">
                  Nothing slipped · next {c.next.toLowerCase()}
                </p>
              )}
              <p className="mt-3 inline-flex items-center gap-1.5 text-[12px] font-bold text-brand-primary">
                Open client <ArrowRight className="h-3.5 w-3.5" />
              </p>
            </Card>
          );
        })}
      </div>
      <p className="text-[11.5px] leading-snug text-brand-gray">
        Six accounts, three shapes — retainer, Accelerator member and prospect —
        because the tab set each one gets is derived from that shape. The bar under
        each card is twelve months of event density off its engagement record, so a
        book that has gone quiet looks quiet before you open anything. Synthetic:
        the real book lives in ClickUp and HighLevel and is deliberately not loaded
        into a demo environment.
      </p>
    </div>
  );
}

/* ── Detail ───────────────────────────────────────────────────── */

function ClientDetail({ hub, client: c }: { hub: OpsHub; client: Client }) {
  const { state, patch } = hub;

  /* Every tab reads from these four slices. Memoised per account rather than
     per tab so switching tabs re-filters in memory and touches nothing. */
  const data = useMemo(() => {
    const commitments = COMMITMENTS.filter((x) => x.clientId === c.id).map((x) =>
      liveCommitment(x, hub.stageOf),
    );
    const timeline = CLIENT_TIMELINES[c.id] ?? [];
    const invoices = CLIENT_INVOICES[c.id] ?? [];
    const meetings = MEETINGS.filter((m) => m.clientId === c.id);
    const attendance = CLIENT_ATTENDANCE[c.id] ?? [];
    const emails = EMAILS.filter((e) => e.clientId === c.id);
    return { commitments, timeline, invoices, meetings, attendance, emails };
  }, [c.id, hub.stageOf]);

  const rec = engagementFor(c.id);

  const tabs = clientTabs(c);
  /* A tab left over from another account's shape would render nothing. */
  const activeTab = tabs.some(([id]) => id === state.clientTab)
    ? state.clientTab
    : "spine";

  const openCommits = data.commitments.filter((x) => x.state !== "done");
  const tabCounts: Record<string, number> = {
    spine: rec ? rec.events.length : 0,
    commitments: openCommits.length,
    timeline: data.timeline.length,
    meetings: data.meetings.length,
    money: data.invoices.filter((i) => i.state !== "paid").length,
    attendance: data.attendance.filter((a) => a.state !== "attended").length,
  };

  const phase = rec ? currentPhase(rec) : null;
  const age = rec ? engagementAgeDays(rec) : null;

  return (
    <div className="space-y-5">
      <button
        type="button"
        onClick={() => patch({ clientId: null, askAnswer: null })}
        className="inline-flex items-center gap-2 text-[12px] font-bold uppercase tracking-[0.1em] text-brand-gray transition-colors hover:text-brand-ink"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All clients
      </button>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-[28px] font-bold leading-none tracking-[-0.03em] text-brand-ink">
            {c.name}
          </h2>
          <p className="mt-1.5 text-[13px] text-brand-secondary">
            {c.contact} · {c.email} · {c.service}
          </p>
          {rec && (
            <p className="mt-1 text-[12px] text-brand-gray">
              {age === null
                ? `Prospect since ${fmtRel(rec.backfill.beginsAt)} — no contract signed`
                : `Client for ${fmtDuration(age)} · record begins ${fmtRel(rec.backfill.beginsAt)}`}
              {rec.backfill.unreachable.length > 0 &&
                ` · ${rec.backfill.unreachable.length} source${rec.backfill.unreachable.length === 1 ? "" : "s"} unreachable`}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Pill tone="outline">{SHAPE_LABEL[clientShape(c)]}</Pill>
          {phase && (
            <span
              className="inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-bold"
              style={{ background: `${phase.color}1a`, color: phase.color }}
            >
              {phase.label}
            </span>
          )}
          <Pill tone={hub.flagsFor(c.id).length ? "red" : "green"}>{c.opStatus}</Pill>
        </div>
      </div>

      <AskPanel hub={hub} client={c} data={data} />

      <Tabs
        tabs={tabs}
        active={activeTab}
        counts={tabCounts}
        onSelect={(id) => patch({ clientTab: id })}
      />

      {activeTab === "spine" &&
        (rec ? (
          <SpineView hub={hub} rec={rec} />
        ) : (
          <Empty>No engagement record connected for this account.</Empty>
        ))}
      {activeTab === "brief" &&
        (rec ? (
          <BriefView hub={hub} rec={rec} client={c} />
        ) : (
          <Empty>No engagement record connected for this account.</Empty>
        ))}
      {activeTab === "now" && <NowTab hub={hub} client={c} data={data} rec={rec} />}
      {activeTab === "commitments" && (
        <CommitmentsTab hub={hub} client={c} rows={data.commitments} />
      )}
      {activeTab === "timeline" && (
        <TimelineTab hub={hub} client={c} rows={data.timeline} />
      )}
      {activeTab === "meetings" && <MeetingsTab hub={hub} meetings={data.meetings} />}
      {activeTab === "money" && <MoneyTab client={c} rows={data.invoices} />}
      {activeTab === "attendance" && (
        <AttendanceTab hub={hub} client={c} rows={data.attendance} />
      )}
    </div>
  );
}

type ClientData = {
  commitments: Commitment[];
  timeline: TimelineRow[];
  invoices: (typeof CLIENT_INVOICES)[string];
  meetings: typeof MEETINGS;
  attendance: (typeof CLIENT_ATTENDANCE)[string];
  emails: typeof EMAILS;
};

/* ── Ask panel — routing, not generation ──────────────────────────
   Each button computes one line from the rows already in memory and jumps to
   the tab holding the evidence, with that tab pre-filtered. The source pills
   stayed: they were the trust device when the answer was prose, and they are
   the destination now. */

function AskPanel({
  hub,
  client: c,
  data,
}: {
  hub: OpsHub;
  client: Client;
  data: ClientData;
}) {
  const { state, patch } = hub;
  const active = ASK_ROUTES.find((a) => a.q === state.askAnswer);
  const ctx = {
    client: c,
    commitments: data.commitments,
    timeline: data.timeline,
    invoices: data.invoices,
    meetings: data.meetings,
  };

  return (
    <Panel
      title="Ask about this account"
      subtitle="The questions that get asked out loud — answered from the record, then it takes you there"
      right={<Sparkles className="h-4 w-4 text-brand-primary" />}
    >
      <div className="flex flex-wrap gap-2">
        {ASK_ROUTES.map((a) => {
          const on = state.askAnswer === a.q;
          return (
            <button
              key={a.q}
              type="button"
              onClick={() =>
                patch({
                  askAnswer: a.q,
                  clientTab: a.tab,
                  timelineSource: "all",
                  commitSide: "all",
                  commitState: "all",
                  ...a.patch,
                })
              }
              className={
                "rounded-lg border px-3 py-2 text-left text-[12px] transition-colors " +
                (on
                  ? "border-brand-primary bg-brand-primary/10 font-bold text-brand-primary"
                  : "border-brand-mist bg-white text-brand-secondary hover:border-brand-stone")
              }
            >
              {a.q}
            </button>
          );
        })}
      </div>

      {active && (
        <div className="mt-4 rounded-xl border border-brand-mist bg-brand-surface p-4">
          <p className="text-[13px] font-bold leading-relaxed text-brand-ink">
            {active.answer(ctx)}
          </p>
          <p className="mt-1.5 text-[11.5px] text-brand-gray">
            Counted from the loaded record — no model call, so it cannot be stale.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-1.5">
            <SectionLabel>Sources</SectionLabel>
            {active.sources.map((s) => (
              <Pill key={s} tone="outline">
                {s}
              </Pill>
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}

/* ── Now ──────────────────────────────────────────────────────────
   Fully derived: it authors nothing. Every row is a join across the
   commitment ledger, the invoice ledger, the Inbox queues and the account
   record — which is why it is also the proof that the tab costs nothing. */

function NowTab({
  hub,
  client: c,
  data,
  rec,
}: {
  hub: OpsHub;
  client: Client;
  data: ClientData;
  rec: EngagementRecord | null;
}) {
  const { patch, go } = hub;
  const flags = hub.flagsFor(c.id);
  const open = data.commitments.filter((x) => x.state !== "done");
  const late = open.filter((x) => x.state === "overdue");
  const silent = open.filter((x) => x.side === "wia" && x.ack === "none");
  const theirs = open.filter((x) => x.side === "client");
  const lateBills = data.invoices.filter((i) => i.state === "overdue");
  const openBills = data.invoices.filter((i) => i.state === "open");
  const slaRows = data.emails.filter((e) => e.kind === "sla");

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-4">
        <Stat label="Open commitments" value={open.length} />
        <Stat label="Overdue" value={late.length} />
        <Stat label="Unacknowledged" value={silent.length} />
        <Stat label="Waiting on client" value={theirs.length} />
      </div>

      <Panel
        title="What needs attention"
        subtitle="Derived from the ledgers below — nothing here is written by hand"
      >
        {flags.length === 0 ? (
          <Empty>Nothing has slipped on this account.</Empty>
        ) : (
          /* Each flag is the link to the thing that clears it — F12. A pill
             that only names a problem leaves the reader hunting for it. */
          <div className="flex flex-wrap gap-1.5">
            {flags.map((f) =>
              f.screen ? (
                <button
                  key={f.text}
                  type="button"
                  onClick={() => go(f.screen!, f.extra)}
                  className="rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary/60"
                >
                  <Pill tone={f.tone}>
                    {f.text}
                    <ArrowRight className="ml-1 h-3 w-3" aria-hidden />
                  </Pill>
                </button>
              ) : (
                <Pill key={f.text} tone={f.tone}>
                  {f.text}
                </Pill>
              ),
            )}
          </div>
        )}
      </Panel>

      {rec && <StalenessStrip hub={hub} rec={rec} />}

      {slaRows.length > 0 && (
        <Panel
          title="Reply clock"
          subtitle="The 24–48 business-hour expectation, measured per open thread"
          bodyClassName="px-2 py-2"
        >
          <ul className="divide-y divide-brand-mist/60">
            {slaRows.map((e) => (
              <li key={e.id} className="flex flex-wrap items-center gap-3 px-3 py-2.5">
                <SourceDot source="gmail" />
                <span className="min-w-0 flex-1">
                  <span className="block text-[12.5px] font-bold text-brand-ink">
                    {e.subject}
                  </span>
                  <span className="block text-[11.5px] text-brand-gray">
                    Owner {e.owner} · {e.age}
                  </span>
                </span>
                <Pill tone={e.classification.includes("breach") ? "red" : "amber"}>
                  {e.classification}
                </Pill>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Account record">
          <Facts
            facts={[
              ["Service", c.service],
              ["Primary contact", `${c.contact} · ${c.email}`],
              ["Last communication", c.lastComm],
              ["Next scheduled", c.next],
              [
                "Waiting on",
                theirs.length
                  ? theirs.map((x) => x.text).join(" · ")
                  : "Nothing outstanding",
              ],
              [
                "Meetings on record",
                data.meetings.length ? `${data.meetings.length} processed` : "None",
              ],
            ]}
          />
        </Panel>

        <Panel title="Invoice standing" subtitle="HighLevel · read-only">
          {data.invoices.length === 0 ? (
            <Empty>Nothing billed yet — this account is a prospect.</Empty>
          ) : (
            <div className="space-y-2.5">
              {lateBills.length === 0 && openBills.length === 0 && (
                <p className="text-[12.5px] text-console-good">
                  All invoices settled. Nothing outstanding.
                </p>
              )}
              {[...lateBills, ...openBills].map((i) => (
                <div
                  key={i.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-brand-mist px-3 py-2.5"
                >
                  <span>
                    <span className="text-[12.5px] font-bold text-brand-ink">
                      {i.id} · {money(i.amount)}
                    </span>
                    <span className="block text-[11.5px] text-brand-gray">
                      Due {i.due}
                      {i.state === "overdue" ? ` · ${i.overdueDays} days past` : ""}
                    </span>
                  </span>
                  <Pill tone={INVOICE_STATE_META[i.state].tone}>
                    {INVOICE_STATE_META[i.state].label}
                  </Pill>
                </div>
              ))}
              <button
                type="button"
                onClick={() => patch({ clientTab: "money", askAnswer: null })}
                className="inline-flex items-center gap-1.5 text-[12px] font-bold text-brand-primary transition-colors hover:text-brand-ink"
              >
                Full ledger and reminder trail <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}

/* ── Commitments ──────────────────────────────────────────────────
   The promise ledger. `ts` is the transcript second where it was said, which
   is what turns a claim into a citation — and its absence on Harbor House is
   stated rather than hidden, because that transcript never came back. */

const SIDE_TABS: [string, string][] = [
  ["all", "Both sides"],
  ["wia", "We owe them"],
  ["client", "They owe us"],
];

const STATE_TABS: [string, string][] = [
  ["all", "All"],
  ["overdue", "Overdue"],
  ["unacked", "Unacknowledged"],
  ["done", "Delivered"],
];

/* Not the `Tabs` primitive, despite looking like it. These narrow a list in
   place; they do not switch panels, and stacking two more tablists next to
   the real one would announce three sets of tabs on a screen that has one.
   Toggle buttons in a labelled group say what these actually are. */
function FilterRow({
  label,
  options,
  active,
  onSelect,
}: {
  label: string;
  options: [string, string][];
  active: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className="flex flex-wrap items-center gap-1.5 rounded-xl border border-brand-mist bg-white p-1.5"
    >
      {options.map(([id, text]) => {
        const on = active === id;
        return (
          <button
            key={id}
            type="button"
            aria-pressed={on}
            onClick={() => onSelect(id)}
            className={
              "rounded-lg px-3 py-1.5 text-[12.5px] transition-colors " +
              (on
                ? "bg-brand-primary font-bold text-white"
                : "font-medium text-brand-secondary hover:bg-brand-mist/50")
            }
          >
            {text}
          </button>
        );
      })}
    </div>
  );
}

function CommitmentsTab({
  hub,
  client: c,
  rows,
}: {
  hub: OpsHub;
  client: Client;
  rows: Commitment[];
}) {
  const { state, patch, openDrawer } = hub;
  const side = state.commitSide;
  const filter = state.commitState;

  const shown = rows.filter((r) => {
    if (side !== "all" && r.side !== side) return false;
    if (filter === "overdue") return r.state === "overdue";
    if (filter === "done") return r.state === "done";
    if (filter === "unacked") return r.state !== "done" && r.ack === "none";
    return true;
  });

  const noTranscript = rows.length > 0 && rows.every((r) => r.ts === "—");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <FilterRow
          label="Filter commitments by side"
          options={SIDE_TABS}
          active={side}
          onSelect={(id) => patch({ commitSide: id as typeof side })}
        />
        <FilterRow
          label="Filter commitments by status"
          options={STATE_TABS}
          active={filter}
          onSelect={(id) => patch({ commitState: id })}
        />
      </div>

      {noTranscript && (
        <p className="rounded-xl border border-console-warn/30 bg-console-warn/5 px-4 py-3 text-[11.5px] leading-snug text-console-warn">
          No transcript timestamps — the Sep 3 meeting was never shared, so
          these came from the summary alone.
        </p>
      )}

      <Panel
        title={`${shown.length} of ${rows.length} commitments`}
        subtitle="Every promise, its owner, its current status and where it was said"
        bodyClassName="px-2 py-2"
      >
        {shown.length === 0 ? (
          <Empty>No commitments match this filter.</Empty>
        ) : (
          <ul className="divide-y divide-brand-mist/60">
            {shown.map((r) => {
              const meta = COMMITMENT_STATE_META[r.state];
              const ack = ACK_META[r.ack];
              return (
                <li key={r.id}>
                  <button
                    type="button"
                    onClick={() =>
                      openDrawer({
                        title: r.text,
                        source: r.meetingId
                          ? (MEETINGS.find((m) => m.id === r.meetingId)?.source ??
                            "clickup")
                          : "clickup",
                        label: `${r.side === "wia" ? "WIA committed" : "Client committed"} · ${r.madeOn}`,
                        excerpt: `${r.text}\n\nOwner ${r.owner} · due ${r.due}\nClickUp: ${r.clickup}\n${ack.label}: ${r.ackDetail}${
                          r.ts !== "—" ? `\n\nHeard at ${r.ts} in the ${r.madeOn} recording.` : "\n\nNo transcript returned for this meeting."
                        }`,
                        time: r.ts !== "—" ? r.ts : r.madeOn,
                        client: c.name,
                      })
                    }
                    className="w-full rounded-lg px-3 py-3 text-left transition-colors hover:bg-brand-mist/40"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Pill tone={r.side === "wia" ? "navy" : "violet"}>
                        {r.side === "wia" ? "We owe them" : "They owe us"}
                      </Pill>
                      <Pill tone={meta.tone}>{meta.label}</Pill>
                      {r.side === "wia" && (
                        <Pill tone={ack.tone}>{ack.label}</Pill>
                      )}
                    </div>
                    <p className="mt-2 text-[13px] font-bold leading-snug text-brand-ink">
                      {r.text}
                    </p>
                    <p className="mt-1 text-[11.5px] text-brand-secondary">
                      {r.owner} · due {r.due} · {r.clickup}
                    </p>
                    <p className="mt-1 text-[11.5px] text-brand-gray">
                      Said {r.madeOn}
                      {r.ts !== "—" ? ` at ${r.ts}` : " · no transcript timestamp"} ·{" "}
                      {r.ackDetail}
                    </p>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </Panel>
    </div>
  );
}

/* ── Timeline ─────────────────────────────────────────────────────
   The one merged feed, with the source filter the three old tabs implied but
   never delivered. Chips are built from the rows present, so a source this
   account has no events on never appears as a dead filter. */

function TimelineTab({
  hub,
  client: c,
  rows,
}: {
  hub: OpsHub;
  client: Client;
  rows: TimelineRow[];
}) {
  const { state, patch, openDrawer } = hub;
  const active = state.timelineSource;

  const present = SOURCE_ORDER.filter((s) => rows.some((r) => r.s === s));
  const shown = active === "all" ? rows : rows.filter((r) => r.s === active);
  const recent = rows.filter((r) => RECENT_WHEN.includes(r.when)).length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-brand-mist bg-white p-1.5">
        <button
          type="button"
          onClick={() => patch({ timelineSource: "all" })}
          className={
            "rounded-lg px-3 py-1.5 text-[12.5px] transition-colors " +
            (active === "all"
              ? "bg-brand-primary font-bold text-white"
              : "font-medium text-brand-secondary hover:bg-brand-mist/50")
          }
        >
          All sources
          <span className="ml-2 rounded bg-brand-mist/80 px-1.5 py-px text-[10.5px] font-bold tabular-nums text-brand-gray">
            {rows.length}
          </span>
        </button>
        {present.map((s) => {
          const n = rows.filter((r) => r.s === s).length;
          const on = active === s;
          return (
            <button
              key={s}
              type="button"
              onClick={() => patch({ timelineSource: s })}
              className={
                "inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-[12.5px] transition-colors " +
                (on
                  ? "bg-brand-primary font-bold text-white"
                  : "font-medium text-brand-secondary hover:bg-brand-mist/50")
              }
            >
              <SourceDot source={s} />
              {SOURCE_META[s].label}
              <span
                className={
                  "rounded px-1.5 py-px text-[10.5px] font-bold tabular-nums " +
                  (on ? "bg-white/20 text-white" : "bg-brand-mist/80 text-brand-gray")
                }
              >
                {n}
              </span>
            </button>
          );
        })}
      </div>

      <Panel
        title="Cross-source timeline"
        subtitle={`One record assembled from ${present.length} connected systems · ${recent} events since the last call`}
        bodyClassName="px-2 py-2"
      >
        {shown.length === 0 ? (
          <Empty>No activity from this source on this account.</Empty>
        ) : (
          <ul className="divide-y divide-brand-mist/60">
            {shown.map((r) => (
              <li key={r.when + r.text}>
                <button
                  type="button"
                  onClick={() =>
                    openDrawer({
                      title: r.text,
                      source: r.s,
                      label: r.meta,
                      excerpt: `${r.text}\n\n${r.meta}`,
                      time: r.when,
                      client: c.name,
                    })
                  }
                  className="flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-brand-mist/40"
                >
                  <span className="w-[62px] flex-none pt-px text-[11px] text-brand-slate">
                    {r.when}
                  </span>
                  <span className="mt-[7px]">
                    <SourceDot source={r.s} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[12.5px] font-bold text-brand-ink">
                      {r.text}
                    </span>
                    <span className="block text-[11.5px] text-brand-gray">{r.meta}</span>
                  </span>
                  <Pill tone={r.tone}>{r.status}</Pill>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}

/* ── Meetings ─────────────────────────────────────────────────────
   Absorbs the old Files tab: every asset it listed came from these meetings,
   so it was a subset of this view standing next to it. */

function MeetingsTab({ hub, meetings }: { hub: OpsHub; meetings: typeof MEETINGS }) {
  if (meetings.length === 0)
    return (
      <Panel title="Meetings on record">
        <Empty>
          No meetings recorded against this account yet.
        </Empty>
      </Panel>
    );

  return (
    <div className="space-y-4">
      {meetings.map((m) => {
        const unmapped = m.fileDest.startsWith("No mapped");
        return (
          <Panel
            key={m.id}
            title={m.title}
            subtitle={`${m.date} · ${m.duration} · host ${m.host} · ${SOURCE_META[m.source].label}`}
            right={
              <button
                type="button"
                onClick={() => hub.go("meetings", { meetingId: m.id })}
                className="inline-flex items-center gap-1.5 rounded-lg bg-brand-primary/10 px-3 py-2 text-[12px] font-bold text-brand-primary transition-colors hover:bg-brand-primary/20"
              >
                Execution pack <ExternalLink className="h-3.5 w-3.5" />
              </button>
            }
          >
            <div className="grid gap-4 sm:grid-cols-3">
              <Stat label="Decisions" value={m.decisions.length} />
              <Stat label="Actions" value={m.tasks.length} />
              <Stat label="Files filed" value={m.files.length} />
            </div>

            <div className="mt-4 space-y-3">
              <div>
                <SectionLabel>Filed to</SectionLabel>
                <p
                  className={
                    "mt-1 text-[12px] " +
                    (unmapped ? "text-console-warn" : "text-brand-secondary")
                  }
                >
                  {unmapped
                    ? `${m.fileDest} — filing was skipped rather than a folder invented`
                    : m.fileDest}
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {m.files.map(([name]) => (
                    <Pill key={name} tone="outline">
                      {name}
                    </Pill>
                  ))}
                </div>
              </div>

              {m.moments.length > 0 && (
                <div>
                  <SectionLabel>Cited moments</SectionLabel>
                  <ul className="mt-1.5 space-y-1.5">
                    {m.moments.map((mo) => (
                      <li key={mo.ts} className="flex items-start gap-2.5">
                        <span className="w-[46px] flex-none text-[11px] tabular-nums text-brand-slate">
                          {mo.ts}
                        </span>
                        <Pill tone="neutral">{mo.tag}</Pill>
                        <span className="min-w-0 flex-1 text-[12px] leading-snug text-brand-secondary">
                          {mo.text}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {m.moments.length === 0 && (
                <p className="text-[11.5px] text-console-warn">
                  No moments extracted — the transcript for this meeting was never
                  returned.
                </p>
              )}
            </div>
          </Panel>
        );
      })}
    </div>
  );
}

/* ── Money ────────────────────────────────────────────────────────
   HighLevel invoice events. The reminder trail is the point: "overdue" reads
   very differently once you know three automatic reminders already went out
   under WIA's name, which is the difference between a chase and an apology. */

function MoneyTab({
  client: c,
  rows,
}: {
  client: Client;
  rows: (typeof CLIENT_INVOICES)[string];
}) {
  if (rows.length === 0)
    return (
      <Panel title="Invoices">
        <Empty>Nothing billed yet — {c.name} is a prospect.</Empty>
      </Panel>
    );

  const paid = rows.filter((i) => i.state === "paid");
  const outstanding = rows.filter((i) => i.state !== "paid");
  const collected = paid.reduce((t, i) => t + i.amount, 0);
  const owed = outstanding.reduce((t, i) => t + i.amount, 0);
  const avgDays = paid.length
    ? Math.round(paid.reduce((t, i) => t + i.daysToPay, 0) / paid.length)
    : 0;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-4">
        <Stat label="Collected" value={money(collected)} />
        <Stat label="Outstanding" value={money(owed)} />
        <Stat label="Avg days to pay" value={paid.length ? avgDays : "—"} />
        <Stat label="Invoices" value={rows.length} />
      </div>

      {avgDays > 14 && (
        <p className="rounded-xl border border-console-warn/30 bg-console-warn/5 px-4 py-3 text-[11.5px] leading-snug text-console-warn">
          This account averages {avgDays} days to pay across {paid.length} settled
          invoices. That is the number a balance cannot show you — the account pays,
          but late enough that every cycle needs chasing.
        </p>
      )}

      <Panel
        title="Invoice ledger"
        subtitle="Issued, settled and outstanding — with every reminder that went out"
        bodyClassName="px-2 py-2"
      >
        <ul className="divide-y divide-brand-mist/60">
          {rows.map((i) => {
            const meta = INVOICE_STATE_META[i.state];
            return (
              <li key={i.id} className="px-3 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <SourceDot source="highlevel" />
                    <span className="text-[13px] font-bold text-brand-ink">
                      {i.id} · {money(i.amount)}
                    </span>
                    <Pill tone={meta.tone}>{meta.label}</Pill>
                  </div>
                  <span className="text-[11.5px] text-brand-gray">
                    Issued {i.issued} · due {i.due}
                    {i.state === "paid" && ` · paid ${i.paidOn} (${i.daysToPay}d)`}
                    {i.state === "overdue" && ` · ${i.overdueDays} days past due`}
                  </span>
                </div>

                {i.reminders.length > 0 && (
                  <ul className="mt-2.5 space-y-1">
                    {i.reminders.map((r) => (
                      <li
                        key={r.when + r.detail}
                        className="flex items-start gap-2.5 text-[11.5px]"
                      >
                        <span className="w-[52px] flex-none text-brand-slate">
                          {r.when}
                        </span>
                        <Pill tone={r.kind === "personal" ? "blue" : "neutral"}>
                          {r.kind === "personal" ? "Personal" : "Automatic"}
                        </Pill>
                        <span className="min-w-0 flex-1 text-brand-secondary">
                          {r.detail}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}

                {i.state !== "paid" && (
                  <p className="mt-2.5 inline-flex items-center gap-1.5 text-[11.5px] text-brand-gray">
                    <ExternalLink className="h-3 w-3" />
                    {i.payUrl}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      </Panel>

      <p className="text-[11.5px] leading-snug text-brand-gray">
        Read-only. The hub prepares a personal follow-up for approval; it never
        touches an invoice.
      </p>
    </div>
  );
}

/* ── Attendance ───────────────────────────────────────────────────
   Accelerator members in place of Meetings, because their sessions are the
   group Office Hours and the replay lives on the row.

   The unmatched row is the one worth reading twice. A participant called
   "Maya" joined the Sep 3 Meta session at 91% similarity to Maya Stone, and
   the matcher will not assert it — so the fourth consecutive miss driving the
   re-engagement case is provisional, and the screen says so. */

function AttendanceTab({
  hub,
  client: c,
  rows,
}: {
  hub: OpsHub;
  client: Client;
  rows: (typeof CLIENT_ATTENDANCE)[string];
}) {
  const { openDrawer } = hub;

  if (rows.length === 0)
    return (
      <Panel title="Office Hours attendance">
        <Empty>No sessions on record for this member.</Empty>
      </Panel>
    );

  const attended = rows.filter((r) => r.state === "attended").length;
  const missed = rows.filter((r) => r.state === "missed").length;
  const unmatched = rows.filter((r) => r.state === "unmatched").length;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-4">
        <Stat label="Sessions" value={rows.length} />
        <Stat label="Attended" value={attended} />
        <Stat label="Missed" value={missed} />
        <Stat label="Needs match" value={unmatched} />
      </div>

      {unmatched > 0 && (
        <p className="rounded-xl border border-console-bad/30 bg-console-bad/5 px-4 py-3 text-[11.5px] leading-snug text-console-bad">
          One session is unmatched, so the miss count below is provisional. The
          matcher abstains rather than guessing.
        </p>
      )}

      {/* WHERE THE COUNTERS ACTUALLY LIVE. This tab is a read of one member's
          history; the consecutive-miss counters, the two-week / four-week
          thresholds and the flags themselves are owned by the Roll Call console
          (MP-01), which keeps a counter per track. Saying so here is what stops
          two screens quietly disagreeing about how many sessions someone has
          missed. */}
      <p className="rounded-xl border border-brand-mist bg-brand-mist/30 px-4 py-2.5 text-[11.5px] leading-snug text-brand-gray">
        Read-only view. The miss counters and the 2-week / 4-week flags are kept
        by the <span className="font-semibold text-brand-ink">Roll Call console
        (MP-01)</span>, one counter per track — this tab shows what it recorded
        for this member.
      </p>

      <Panel
        title="Office Hours attendance"
        subtitle="Matched from the Zoom participant report against the HighLevel member record"
        bodyClassName="px-2 py-2"
      >
        <ul className="divide-y divide-brand-mist/60">
          {rows.map((r) => {
            const meta = ATTENDANCE_STATE_META[r.state];
            return (
              <li key={r.date}>
                <button
                  type="button"
                  onClick={() =>
                    openDrawer({
                      title: `${r.session} · ${r.date}`,
                      source: r.state === "missed" ? "highlevel" : "zoom",
                      label: meta.label,
                      excerpt: `${r.detail}\n\nReplay: ${r.replay}`,
                      time: r.date,
                      client: c.name,
                    })
                  }
                  className="flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-brand-mist/40"
                >
                  <span className="w-[52px] flex-none pt-px text-[11px] text-brand-slate">
                    {r.date}
                  </span>
                  <span className="mt-[7px]">
                    <SourceDot source={r.state === "missed" ? "highlevel" : "zoom"} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[12.5px] font-bold text-brand-ink">
                      {r.session}
                    </span>
                    <span className="block text-[11.5px] text-brand-gray">
                      {r.detail}
                    </span>
                    <span className="mt-0.5 block text-[11px] text-brand-slate">
                      Replay · {r.replay}
                    </span>
                  </span>
                  <Pill tone={meta.tone}>{meta.label}</Pill>
                </button>
              </li>
            );
          })}
        </ul>
      </Panel>
    </div>
  );
}

/* ── Card sparkline ───────────────────────────────────────────────
   Twelve monthly buckets of event count, drawn as bars. It is on the index
   card rather than inside an account because the question it answers —
   "which of these has gone quiet" — is a question about the BOOK, and
   answering it by opening six accounts in turn is the thing this screen
   exists to stop. */

function CardSpark({ rec, client: c }: { rec: EngagementRecord; client: Client }) {
  const buckets = activityBuckets(rec);
  const peak = Math.max(1, ...buckets);
  const health = laneHealth(rec);
  const comms = health.find((h) => h.lane === "comms")!;
  const age = engagementAgeDays(rec);

  /* An Accelerator member has no one-to-one calls — their contact is the group
     office hours, which land on the engagement lane. Reading them against the
     meetings lane printed "last call never" on a member who had attended
     eleven sessions, which is true of the lane and false about the account. */
  const accelerator = clientShape(c) === "accelerator";
  const cadence = health.find((h) => h.lane === (accelerator ? "engagement" : "meetings"))!;

  return (
    <div className="mt-3">
      <div className="flex items-end gap-[3px]" aria-hidden>
        {buckets.map((n, i) => (
          <span
            key={i}
            className="flex-1 rounded-sm"
            style={{
              /* Square-rooted, not linear. One onboarding burst or a heavy
                 review month peaks at 15+ against a normal month's 1-3, and a
                 linear scale flattens every ordinary month to a 2px stub —
                 which is exactly the shape this bar exists to show. */
              height:
                n === 0 ? 2 : Math.max(5, Math.round((Math.sqrt(n) / Math.sqrt(peak)) * 22)),
              background: n === 0 ? "#e0dfe2" : "#5070ff",
              opacity: n === 0 ? 1 : 0.4 + (Math.sqrt(n) / Math.sqrt(peak)) * 0.6,
            }}
          />
        ))}
      </div>
      <p className="mt-1.5 text-[11px] leading-snug text-brand-gray">
        {age === null ? "Prospect" : fmtDuration(age)} · last contact{" "}
        <span
          className={
            comms.state === "stale" || comms.state === "silent"
              ? "font-bold text-console-bad"
              : comms.state === "aging"
                ? "font-bold text-console-warn"
                : ""
          }
        >
          {comms.lastAt ? fmtRel(comms.lastAt) : "never"}
        </span>
        {accelerator ? " · last session " : " · last call "}
        <span
          className={
            cadence.state === "stale" || cadence.state === "silent"
              ? "font-bold text-console-bad"
              : cadence.state === "aging"
                ? "font-bold text-console-warn"
                : ""
          }
        >
          {cadence.lastAt ? fmtRel(cadence.lastAt) : "never"}
        </span>
      </p>
    </div>
  );
}

/* ── Staleness strip ──────────────────────────────────────────────
   Per LANE, not per client. "This client is stale" is not actionable;
   "nobody has spoken to them in six weeks while the invoice ledger is
   current" tells you which person to go and find. Clicking a lane takes you
   to the spine filtered to it, so the strip is a route as well as a reading. */

function StalenessStrip({ hub, rec }: { hub: OpsHub; rec: EngagementRecord }) {
  const health = laneHealth(rec).filter((h) => h.expectDays !== null);
  const worst = health.filter((h) => h.state === "stale" || h.state === "silent");

  return (
    <Panel
      title="Cadence check"
      subtitle={
        worst.length
          ? `${worst.length} lane${worst.length === 1 ? "" : "s"} past twice the expected interval — click one to see it on the spine`
          : "Every lane is inside the interval it is supposed to keep"
      }
    >
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {health.map((h) => (
          <button
            key={h.lane}
            type="button"
            onClick={() =>
              hub.patch({
                clientTab: "spine",
                spineLane: h.lane,
                spineZoom: "all",
                spineEventId: null,
                askAnswer: null,
              })
            }
            className="flex items-center gap-2.5 rounded-xl border border-brand-mist bg-brand-surface px-3 py-2.5 text-left transition-colors hover:border-brand-stone"
          >
            <span
              className="h-7 w-[3px] flex-none rounded-full"
              style={{ background: h.color }}
              aria-hidden
            />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[12px] font-bold text-brand-ink">
                {h.label}
              </span>
              <span className="block text-[11px] text-brand-gray">
                {h.lastAt ? fmtRel(h.lastAt) : "never"} · expects every {h.expectDays}d
              </span>
            </span>
            <Pill tone={HEALTH_META[h.state].tone}>{HEALTH_META[h.state].label}</Pill>
          </button>
        ))}
      </div>
    </Panel>
  );
}
