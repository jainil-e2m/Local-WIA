/* Home — the Operations Overview screen.
   Every KPI, queue row and pulse card is a click-through into the screen
   that owns it. The review cards are CONDITIONAL: handle an item anywhere
   in the hub and its card disappears from here. That is what makes the
   number at the top mean something. */

import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import {
  COVERAGE_STRIP,
  DEMO_DATE,
  OPERATING_QUEUE,
  QUEUES,
  TEAM_PULSE,
} from "@/data/opsHub";
import { MOMENTS, UNREADABLE } from "@/data/contentAtelier";
import type { ScreenId } from "@/lib/opsHub";
import { REVIEWER_QUEUES, type OpsHub } from "@/hooks/useOpsHub";
import {
  AutoBadge,
  Card,
  Glyph,
  Panel,
  Pill,
  SourceDot,
  SectionLabel,
} from "../primitives";

export function HomeScreen({ hub }: { hub: OpsHub }) {
  const { state, counts, go, emailQueue, isEmailOpen, packStatus, queueOpen } = hub;
  const me = state.user;

  /* KPIs. Each one now carries its PARTS, so the tile can open exactly what
     it counted instead of guessing a single destination — F03. The old
     "Communication At Risk" tile summed three things and opened one of
     them. */
  const kpis = [
    {
      label: "Needs Review",
      value: counts.needsReview,
      parts: counts.needsReviewParts,
      trend: "Approval queue",
      accent: "#5070ff",
    },
    {
      label: "Communication At Risk",
      value: counts.clientComm,
      parts: counts.clientCommParts,
      trend: "Gmail + rules",
      accent: "#7d4a0f",
    },
    {
      label: "Team Actions At Risk",
      value: counts.teamRisk,
      parts: [
        {
          label: "overdue in ClickUp",
          value: counts.overdueTasks,
          screen: "ops" as ScreenId,
          extra: { opsTab: "team" },
        },
        {
          label: "dispatched, not acknowledged",
          value: counts.unacked,
          screen: "ops" as ScreenId,
          extra: { opsTab: "team" },
        },
      ],
      trend: "ClickUp + Slack",
      accent: "#a83323",
    },
  ];

  /* THE REVIEWER'S OWN QUEUE. Switching persona used to change a name in the
     corner and nothing else. This is the answer to "where do I start?" and
     to "have I finished?", and the two are the same list. */
  const myLanes = REVIEWER_QUEUES[me]
    .map((id) => ({
      id,
      label: QUEUES.find((q) => q.id === id)?.label ?? id,
      open: queueOpen(id),
    }))
    .filter((l) => l.open > 0);

  /* Conditional review cards. Each predicate reads the same state the rest
     of the hub writes, so this list shrinks as work gets done. */
  const reviewCards: {
    kind: string;
    tone: "blue" | "red" | "amber";
    auto: "ai_hq" | "highlevel";
    time: string;
    title: string;
    detail: string;
    outputs: string[];
    cta: string;
    screen: ScreenId;
    owner: "Whitney" | "Gisselle";
    extra?: Record<string, unknown>;
  }[] = [];

  if (packStatus("bloom-strategy") === "needs_review")
    reviewCards.push({
      kind: "Execution Pack Ready",
      tone: "blue",
      auto: "ai_hq",
      time: "Sep 2 call",
      title: "Bloom Manor strategy call",
      detail:
        "Meeting intelligence, ClickUp actions, Slack dispatch, client recap and Drive filing — reviewable one output at a time.",
      outputs: ["3 ClickUp tasks", "1 Slack dispatch", "1 Gmail recap", "4 Drive files"],
      cta: "Review execution pack",
      screen: "meetings",
      owner: "Whitney",
      extra: { meetingId: "bloom-strategy" },
    });

  if ((state.invoiceState["INV-204"] ?? "overdue") !== "handled")
    reviewCards.push({
      kind: "5 days overdue",
      tone: "red",
      auto: "ai_hq",
      time: "INV-204",
      title: "Rosewood invoice",
      detail:
        "Standard HighLevel reminder already sent from the WIA account. A personal Gmail follow-up is prepared.",
      outputs: ["$1,850 outstanding", "Personal draft"],
      cta: "Review personal reminder",
      screen: "ops",
      owner: "Gisselle",
      extra: { opsTab: "finance", invoiceId: "INV-204" },
    });

  if (isEmailOpen("e7"))
    reviewCards.push({
      kind: "Client email waiting 29 business hours",
      tone: "red",
      auto: "ai_hq",
      time: "Rosewood Venue",
      title: "Team reply at risk",
      detail:
        "Carmen owns the thread and no reply has been detected. Internal nudge ready for review.",
      outputs: ["Owner: Carmen", "Slack nudge"],
      cta: "Review owner",
      screen: "inbox",
      owner: "Gisselle",
      extra: { inboxQueue: emailQueue("e7"), emailId: "e7" },
    });

  const mine = reviewCards.filter((r) => r.owner === me);
  const theirs = reviewCards.filter((r) => r.owner !== me);

  return (
    <div className="space-y-5">
      {/* greeting */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-[34px] font-bold leading-none tracking-[-0.03em] text-brand-ink">
            Good morning, {state.user}
          </h2>
          <p className="mt-2 text-[13.5px] text-brand-secondary">
            Here’s what needs attention across WIA today.
          </p>
        </div>
        <div className="text-right">
          <p className="text-[12.5px] font-bold text-brand-ink">{DEMO_DATE}</p>
          <p className="mt-0.5 text-[11.5px] text-brand-gray">
            Last sync across 7 sources · 2 min ago
          </p>
        </div>
      </div>

      {/* KPIs. Each part is its own link, so the number, the label and the
          destination describe the same set of work. */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {kpis.map((k) => (
          <div
            key={k.label}
            className="flex flex-col rounded-2xl border border-brand-mist bg-white p-4"
            style={{ boxShadow: `inset 3px 0 0 ${k.accent}` }}
          >
            <SectionLabel>{k.label}</SectionLabel>
            <div className="mt-2 flex items-center gap-2.5">
              <span className="text-[38px] font-bold leading-none tracking-[-0.04em] text-brand-ink">
                {k.value}
              </span>
              <Pill tone="outline">{k.trend}</Pill>
            </div>
            <ul className="mt-2.5 space-y-1">
              {k.parts.map((p) => (
                <li key={p.label}>
                  <button
                    type="button"
                    disabled={p.value === 0}
                    onClick={() => go(p.screen, p.extra)}
                    className={
                      "flex w-full items-center gap-2 rounded-lg px-1.5 py-1 text-left text-[11.5px] leading-snug transition-colors " +
                      (p.value === 0
                        ? "cursor-default text-brand-slate"
                        : "text-brand-gray hover:bg-brand-mist/50 hover:text-brand-ink")
                    }
                  >
                    <span className="w-4 flex-none text-right font-bold tabular-nums text-brand-ink">
                      {p.value}
                    </span>
                    <span className="min-w-0 flex-1">{p.label}</span>
                    {p.value > 0 && (
                      <ArrowRight className="h-3 w-3 flex-none" aria-hidden />
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* WHERE DO I START. The reviewer's own lanes, and nothing else. */}
      <Panel
        title={`${me}’s queue`}
        subtitle={
          counts.myOpen === 0
            ? "Every lane you own is clear"
            : `${counts.myOpen} open across the lanes you own`
        }
        right={
          <Pill tone={counts.myOpen === 0 ? "green" : "blue"}>
            {counts.myOpen} open
          </Pill>
        }
      >
        {myLanes.length === 0 ? (
          <p className="rounded-xl border border-dashed border-console-good/40 bg-console-good/[0.05] px-4 py-6 text-center text-[12.5px] text-brand-secondary">
            Nothing open in any lane {me} owns.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {myLanes.map((l) => (
              <button
                key={l.id}
                type="button"
                onClick={() => go("inbox", { inboxQueue: l.id, emailId: "" })}
                className="inline-flex items-center gap-2 rounded-xl border border-brand-mist bg-white px-3.5 py-2 text-[12.5px] font-bold text-brand-ink transition-colors hover:border-brand-stone"
              >
                {l.label}
                <span className="rounded bg-brand-primary/10 px-1.5 py-px text-[10.5px] font-bold tabular-nums text-brand-primary">
                  {l.open}
                </span>
              </button>
            ))}
          </div>
        )}
      </Panel>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* operating queue */}
        <Panel
          title="Today’s operating queue"
          subtitle="What already ran, and what is scheduled next. ✓ completed · ● needs review · ○ scheduled · ⚠ exception"
          right={<AutoBadge system="ai_hq" />}
          bodyClassName="px-2 py-2"
        >
          <ul className="divide-y divide-brand-mist/60">
            {OPERATING_QUEUE.map((r) => {
              const clickable = !!r.screen;
              return (
                <li key={r.time + r.label}>
                  <button
                    type="button"
                    disabled={!clickable}
                    onClick={() =>
                      r.screen && go(r.screen, r.extra)
                    }
                    className={
                      "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors " +
                      (clickable ? "hover:bg-brand-mist/40" : "cursor-default")
                    }
                  >
                    <span className="w-[38px] flex-none text-[11px] tabular-nums text-brand-slate">
                      {r.time}
                    </span>
                    <Glyph icon={r.icon} tone={r.tone} />
                    <span className="min-w-0 flex-1 truncate text-[12.5px] text-brand-ink">
                      {r.label}
                    </span>
                    <Pill tone={r.tone === "neutral" ? "outline" : r.tone}>
                      {r.status}
                    </Pill>
                  </button>
                </li>
              );
            })}
          </ul>
        </Panel>

        {/* needs your review */}
        <Panel
          title={`Prepared for ${me}`}
          subtitle="The hub has prepared these — you decide"
          right={
            <span className="text-[11px] font-bold uppercase tracking-[0.08em] text-console-good">
              Nothing is sent without approval
            </span>
          }
        >
          <div className="space-y-3">
            {/* "NOTHING WAITING" IS NOW AN HONEST CLAIM. It used to appear
                once three selected cards had been cleared, while other review
                work was still open elsewhere. It now requires the reviewer's
                ENTIRE owned queue to be clear as well. */}
            {mine.length === 0 && (
              <p className="rounded-xl border border-dashed border-brand-mist bg-brand-surface px-4 py-6 text-center text-[12.5px] text-brand-gray">
                {counts.myOpen > 0 ? (
                  <>
                    Nothing prepared —{" "}
                    <button
                      type="button"
                      onClick={() => go("inbox", { inboxQueue: REVIEWER_QUEUES[me][0] })}
                      className="font-bold text-brand-primary underline underline-offset-2"
                    >
                      {counts.myOpen} still open
                    </button>{" "}
                    in your lanes.
                  </>
                ) : (
                  <>
                    All clear. Reset the demo in Source Coverage to refill.
                  </>
                )}
              </p>
            )}
            {mine.map((r) => (
              <Card key={r.title} onClick={() => go(r.screen, r.extra)}>
                <div className="flex flex-wrap items-center gap-2">
                  <Pill tone={r.tone}>{r.kind}</Pill>
                  <AutoBadge system={r.auto} />
                  <span className="ml-auto text-[11px] text-brand-slate">{r.time}</span>
                </div>
                <p className="mt-2.5 text-[14px] font-bold text-brand-ink">{r.title}</p>
                <p className="mt-1 text-[12.5px] leading-snug text-brand-secondary">
                  {r.detail}
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  {r.outputs.map((o) => (
                    <Pill key={o} tone="outline">
                      {o}
                    </Pill>
                  ))}
                </div>
                <p className="mt-3 inline-flex items-center gap-1.5 text-[12px] font-bold text-brand-primary">
                  {r.cta}
                  <ArrowRight className="h-3.5 w-3.5" />
                </p>
              </Card>
            ))}

            {theirs.length > 0 && (
              <div className="rounded-xl border border-brand-mist bg-brand-surface p-3.5">
                <SectionLabel>
                  Prepared for {me === "Whitney" ? "Gisselle" : "Whitney"}
                </SectionLabel>
                <ul className="mt-2 space-y-1.5">
                  {theirs.map((r) => (
                    <li key={r.title}>
                      <button
                        type="button"
                        onClick={() => go(r.screen, r.extra)}
                        className="flex w-full items-center gap-2 text-left text-[12px] text-brand-secondary transition-colors hover:text-brand-ink"
                      >
                        <span
                          className="h-1.5 w-1.5 flex-none rounded-full bg-brand-stone"
                          aria-hidden
                        />
                        <span className="min-w-0 flex-1 truncate">{r.title}</span>
                        <ArrowRight className="h-3 w-3 flex-none" aria-hidden />
                      </button>
                    </li>
                  ))}
                </ul>

              </div>
            )}
          </div>
        </Panel>
      </div>

      {/* Team pulse runs full width: it lost the panel that used to sit
          beside it, and a lone child in a 2-col grid is a half-empty row. */}
      <div>
        {/* team pulse */}
        <Panel
          title="Team pulse"
          right={
            <>
              <Pill tone="red">2 overdue</Pill>
              <Pill tone="amber">{counts.teamRisk - 2} unacknowledged</Pill>
            </>
          }
        >
          <ul className="space-y-2.5">
            {TEAM_PULSE.map((t) => (
              <li key={t.title} className="flex items-center gap-3">
                <span className="grid h-7 w-7 flex-none place-items-center rounded-full bg-brand-mist/70 text-[11px] font-bold text-brand-secondary">
                  {t.initial}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[12.5px] font-bold text-brand-ink">
                    {t.title}
                  </p>
                  <p className="truncate text-[11.5px] text-brand-gray">
                    {t.who} · {t.meta}
                  </p>
                </div>
                <Pill tone={t.tone}>{t.status}</Pill>
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() => go("ops", { opsTab: "team" })}
            className="mt-4 inline-flex items-center gap-1.5 text-[12px] font-bold text-brand-primary"
          >
            Open Ops Watch <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </Panel>

      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* source coverage */}
        <Panel
          title="Source coverage"
          right={
            <span className="text-[11px] uppercase tracking-[0.08em] text-brand-slate">
              Demo sources · what the hub can actually reach
            </span>
          }
        >
          <div className="grid gap-2.5 sm:grid-cols-2">
            {COVERAGE_STRIP.map(([key, label, tone]) => (
              <div key={key} className="flex items-center gap-2">
                <SourceDot source={key} />
                <span className="flex-1 text-[12.5px] font-bold text-brand-ink">
                  {key === "highlevel"
                    ? "HighLevel"
                    : key.charAt(0).toUpperCase() + key.slice(1)}
                </span>
                <Pill tone={tone}>{label}</Pill>
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={() => go("settings")}
            className="mt-4 inline-flex items-center gap-1.5 text-[12px] font-bold text-brand-primary"
          >
            Review source coverage <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </Panel>

        {/* Content Atelier teaser. The corpus is no longer one transcript, so
            the honest headline is no longer "one moment" — it is the split
            between what can be read and what is sitting in Drive as video.
            Both numbers derive from the corpus. */}
        <Panel>
          <SectionLabel>Content Atelier · Phase 2</SectionLabel>
          <p className="mt-2 text-[20px] font-bold leading-tight tracking-[-0.02em] text-brand-ink">
            {MOMENTS.filter((m) => m.state !== "blocked").length} of{" "}
            {MOMENTS.length} moments workable
          </p>
          <p className="mt-1.5 text-[12.5px] text-brand-secondary">
            {MOMENTS.filter((m) => m.state === "blocked").length} blocked ·{" "}
            {UNREADABLE} recordings held as video with no transcript
          </p>
          <p className="mt-3 text-[11.5px] leading-snug text-brand-gray">
            WIA’s own marketing. Client calls are archived out of Zoom into
            Drive, so the sessions carrying the results are the ones the engine
            cannot read.
          </p>
          <button
            type="button"
            onClick={() => go("content")}
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-brand-primary px-4 py-2.5 text-[12.5px] font-bold text-white transition-colors hover:bg-brand-accent"
          >
            Review signals <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </Panel>
      </div>

      {/* THE STANDALONE CONSOLES, REACHABLE FROM HERE — F03.

          They were reachable only by going back to the launcher, whose link
          was confusingly called "Back to hub". Each entry states which
          workflow it owns, so a reader knows why it is a separate screen
          rather than a tab. */}
      <Panel
        title="The standalone consoles"
        subtitle="Three workflows keep their own system of record"
      >
        <div className="grid gap-3 sm:grid-cols-3">
          {[
            {
              to: "/roll-call",
              name: "Roll Call",
              initiative: "MP-01",
              holds: "Miss counters and the 2 / 4-week flags, per track",
            },
            {
              to: "/internal-meeting",
              name: "Internal Meeting",
              initiative: "MK-01",
              holds: "The carry-over ledger, week to week",
            },
            {
              to: "/onboarding",
              name: "Client Onboarding",
              initiative: "ON-01 / ON-02",
              holds: "The signed-and-paid pair and the task draft",
            },
          ].map((c) => (
            <Link
              key={c.to}
              to={c.to}
              className="rounded-xl border border-brand-mist bg-white p-4 transition-colors hover:border-brand-stone"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[13px] font-bold text-brand-ink">{c.name}</span>
                <Pill tone="outline">{c.initiative}</Pill>
              </div>
              <p className="mt-1.5 text-[11.5px] leading-snug text-brand-gray">
                {c.holds}
              </p>
              <p className="mt-2.5 inline-flex items-center gap-1.5 text-[12px] font-bold text-brand-primary">
                Open console <ArrowRight className="h-3.5 w-3.5" />
              </p>
            </Link>
          ))}
        </div>
      </Panel>
    </div>
  );
}