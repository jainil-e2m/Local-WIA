/* ────────────────────────────────────────────────────────────────
   Spine — the engagement on a time axis.

   WHY A TIME AXIS AND NOT A FEED. A feed is what WIA already has: seven
   systems each showing their own most-recent rows. Putting those rows in one
   list makes them co-located, not connected. What makes an engagement legible
   is the SHAPE of it over time — when the cadence broke, how long the client
   went quiet before the invoice slipped, whether the contact change and the
   missing transcripts are the same event wearing two hats. None of that is
   visible in a list sorted by date.

   THREE THINGS ARE DRAWN THAT A FEED CANNOT SHOW.

     1. GAPS. A lane that stops is drawn as a hatched block, sized to the
        silence. A feed renders a quiet quarter as "nothing between these two
        rows", which looks identical to a busy quarter once you scroll.

     2. THE RECORD BOUNDARY. A dashed edge where history actually begins.
        Without it an incomplete record is indistinguishable from a complete
        one, which is the single most dangerous failure mode of this screen.

     3. CAUSE vs COVERAGE. A gap the backfill declaration explains — an
        unreachable Fathom key, an expired Zoom recording — is hatched in the
        source's own colour and says so on hover. "They went quiet" and "we
        stopped being able to see" need opposite responses and must never
        look the same.

   UNCITABLE EVENTS ARE HOLLOW, NOT MISSING. Harbor House is the case that
   forced this: its calls did not stop in April, its TRANSCRIPTS did. Drawing
   that as a silence would be a lie — the meetings lane is busy. So an event
   with no citation renders as a ring rather than a filled mark: the thing
   happened, the evidence for it did not survive. A lane of rings is a
   coverage failure; a lane of nothing is a relationship failure.

   EVERYTHING IS DERIVED. No position, duration or count below is authored;
   all of it is arithmetic over data/engagement against the frozen DEMO_NOW.
   ──────────────────────────────────────────────────────────────── */

import { useMemo } from "react";
import { ArrowRight, FileCheck2, Layers } from "lucide-react";
import {
  ASSET_KIND_LABEL,
  LANES,
  LANE_META,
  type EngagementEvent,
  type EngagementRecord,
} from "@/data/engagement";
import {
  HEALTH_META,
  ZOOMS,
  citationCoverage,
  engagementAgeDays,
  fmtDate,
  fmtDuration,
  fmtMonth,
  fmtRel,
  fmtShort,
  fmtTime,
  gapsFor,
  inSpan,
  laneHealth,
  liveAssets,
  ms,
  pctOf,
  resolvedPhases,
  spanFor,
  supersededAssets,
  ticksFor,
  type SpineZoom,
} from "@/lib/engagement";
import { DEMO_NOW_MS } from "@/data/engagement";
import { SOURCE_META } from "@/lib/opsHub";
import type { OpsHub } from "@/hooks/useOpsHub";
import { Empty, Panel, Pill, SectionLabel, SourceDot, Stat } from "../primitives";

const LANE_RAIL = 132;
const LANE_H = 38;

export function SpineView({ hub, rec }: { hub: OpsHub; rec: EngagementRecord }) {
  const { state, patch } = hub;
  const zoom = (ZOOMS.some((z) => z.id === state.spineZoom)
    ? state.spineZoom
    : "all") as SpineZoom;
  const laneFilter = state.spineLane;

  const span = useMemo(() => spanFor(rec, zoom), [rec, zoom]);
  const ticks = useMemo(() => ticksFor(span), [span]);
  const phases = useMemo(() => resolvedPhases(rec), [rec]);
  const health = useMemo(() => laneHealth(rec), [rec]);
  const coverage = useMemo(() => citationCoverage(rec), [rec]);

  const lanes = laneFilter === "all" ? LANES : LANES.filter((l) => l.key === laneFilter);

  const visible = useMemo(
    () =>
      rec.events
        .filter((e) => inSpan(e, span))
        .filter((e) => laneFilter === "all" || e.lane === laneFilter),
    [rec.events, span, laneFilter],
  );

  const selected = rec.events.find((e) => e.id === state.spineEventId) ?? null;
  const age = engagementAgeDays(rec);

  /* Wide enough that a two-year engagement does not compress into mush, and
     scrollable rather than squeezed. 1.6px per day is the point where a
     monthly cadence still reads as regular dots. */
  const innerWidth = Math.max(920, Math.round(span.days * 1.6));
  const beginsPct = pctOf(ms(rec.backfill.beginsAt), span);
  const todayPct = pctOf(DEMO_NOW_MS, span);

  return (
    <div className="space-y-5">
      {/* ── record summary ─────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Engagement age"
          value={age === null ? "Not started" : fmtDuration(age)}
        />
        <Stat label="Events on record" value={rec.events.length} />
        <Stat label="Record begins" value={fmtShort(rec.backfill.beginsAt)} />
        {/* "0%" would claim nothing is cited; an account with no meetings or
            commitments has nothing to cite, which is not the same thing. */}
        <Stat
          label="Citable"
          value={coverage.total === 0 ? "—" : `${coverage.pct}%`}
        />
      </div>

      {/* ── controls ───────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-brand-mist bg-white p-2">
        <div className="flex flex-wrap items-center gap-1">
          <span className="px-1.5 text-[10.5px] font-bold uppercase tracking-[0.1em] text-brand-slate">
            Zoom
          </span>
          {ZOOMS.map((z) => {
            const on = z.id === zoom;
            return (
              <button
                key={z.id}
                type="button"
                onClick={() => patch({ spineZoom: z.id, spineEventId: null })}
                className={
                  "rounded-lg px-2.5 py-1.5 text-[12px] transition-colors " +
                  (on
                    ? "bg-brand-primary font-bold text-white"
                    : "font-medium text-brand-secondary hover:bg-brand-mist/50")
                }
              >
                {z.label}
              </button>
            );
          })}
        </div>
        <span className="hidden h-5 w-px bg-brand-mist sm:block" />
        <div className="flex flex-wrap items-center gap-1">
          <span className="px-1.5 text-[10.5px] font-bold uppercase tracking-[0.1em] text-brand-slate">
            Lane
          </span>
          <button
            type="button"
            onClick={() => patch({ spineLane: "all" })}
            className={
              "rounded-lg px-2.5 py-1.5 text-[12px] transition-colors " +
              (laneFilter === "all"
                ? "bg-brand-ink font-bold text-white"
                : "font-medium text-brand-secondary hover:bg-brand-mist/50")
            }
          >
            All
          </button>
          {LANES.map((l) => {
            const on = laneFilter === l.key;
            const n = rec.events.filter((e) => e.lane === l.key).length;
            return (
              <button
                key={l.key}
                type="button"
                onClick={() => patch({ spineLane: on ? "all" : l.key, spineEventId: null })}
                title={l.question}
                className={
                  "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[12px] transition-colors " +
                  (on
                    ? "bg-brand-ink font-bold text-white"
                    : "font-medium text-brand-secondary hover:bg-brand-mist/50")
                }
              >
                <span
                  className="h-[7px] w-[7px] flex-none rounded-full"
                  style={{ background: l.color }}
                  aria-hidden
                />
                {l.short}
                <span className="tabular-nums opacity-60">{n}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── the spine ──────────────────────────────────────────── */}
      <Panel
        title="Engagement spine"
        subtitle={`${fmtDate(rec.backfill.beginsAt)} to today · ${visible.length} of ${rec.events.length} events in view · hollow marks happened but cannot be cited`}
        bodyClassName="p-0"
      >
        <div className="overflow-x-auto">
          <div style={{ minWidth: innerWidth }} className="relative p-4 pt-3">
            {/* tick rail */}
            <div className="relative mb-1 h-5" style={{ marginLeft: LANE_RAIL }}>
              {ticks.map((t) => (
                <span
                  key={t.ms}
                  className={
                    "absolute top-0 -translate-x-1/2 whitespace-nowrap text-[10px] tabular-nums " +
                    (t.major ? "font-bold text-brand-secondary" : "text-brand-gray")
                  }
                  style={{ left: `${pctOf(t.ms, span)}%` }}
                >
                  {t.label}
                </span>
              ))}
            </div>

            {/* phase band */}
            <div
              className="relative mb-2 h-[22px] overflow-hidden rounded-md border border-brand-mist bg-brand-mist/20"
              style={{ marginLeft: LANE_RAIL }}
            >
              {phases.map((p) => {
                const from = Math.max(pctOf(ms(p.startsAt), span), 0);
                const to = Math.min(
                  p.endsAt ? pctOf(ms(p.endsAt), span) : 100,
                  100,
                );
                const w = to - from;
                if (w <= 0) return null;
                return (
                  <span
                    key={p.key + p.startsAt}
                    title={`${p.label} — from ${fmtDate(p.startsAt)}. ${p.note}`}
                    className="absolute inset-y-0 flex items-center overflow-hidden whitespace-nowrap px-2 text-[10px] font-bold"
                    style={{
                      left: `${from}%`,
                      width: `${w}%`,
                      background: `${p.color}22`,
                      borderLeft: `2px solid ${p.color}`,
                      color: p.color,
                    }}
                  >
                    {w > 7 ? p.label : ""}
                  </span>
                );
              })}
            </div>

            {/* lanes */}
            <div className="relative">
              {/* today line, drawn over every lane */}
              {todayPct >= 0 && todayPct <= 100 && (
                <span
                  className="pointer-events-none absolute top-0 z-20 w-px bg-brand-primary"
                  style={{
                    left: `calc(${LANE_RAIL}px + (100% - ${LANE_RAIL}px) * ${todayPct / 100})`,
                    height: lanes.length * LANE_H,
                  }}
                  aria-hidden
                />
              )}
              {/* record boundary */}
              {beginsPct >= 0 && beginsPct <= 100 && (
                <span
                  className="pointer-events-none absolute top-0 z-20 w-px"
                  style={{
                    left: `calc(${LANE_RAIL}px + (100% - ${LANE_RAIL}px) * ${beginsPct / 100})`,
                    height: lanes.length * LANE_H,
                    background:
                      "repeating-linear-gradient(to bottom,#a83323 0 4px,transparent 4px 8px)",
                  }}
                  aria-hidden
                />
              )}

              {lanes.map((l) => {
                const h = health.find((x) => x.lane === l.key)!;
                const rows = rec.events.filter(
                  (e) => e.lane === l.key && inSpan(e, span),
                );
                const gaps = gapsFor(rec, l.key, span);
                return (
                  <div
                    key={l.key}
                    className="flex items-stretch border-t border-brand-mist/70"
                    style={{ height: LANE_H }}
                  >
                    <button
                      type="button"
                      onClick={() =>
                        patch({
                          spineLane: laneFilter === l.key ? "all" : l.key,
                          spineEventId: null,
                        })
                      }
                      title={l.question}
                      className="flex flex-none items-center gap-2 pr-3 text-left"
                      style={{ width: LANE_RAIL }}
                    >
                      <span
                        className="h-4 w-[3px] flex-none rounded-full"
                        style={{ background: l.color }}
                        aria-hidden
                      />
                      <span className="min-w-0">
                        <span className="block truncate text-[11.5px] font-bold text-brand-ink">
                          {l.short}
                        </span>
                        <span
                          className={
                            "block truncate text-[10px] " +
                            (h.state === "stale" || h.state === "silent"
                              ? "text-console-bad"
                              : h.state === "aging"
                                ? "text-console-warn"
                                : "text-brand-gray")
                          }
                        >
                          {h.days === null ? "never" : fmtRel(h.lastAt!)}
                        </span>
                      </span>
                    </button>

                    <div className="relative flex-1 border-l border-brand-mist/70">
                      {/* tick gridlines */}
                      {ticks.map((t) => (
                        <span
                          key={t.ms}
                          className="absolute inset-y-0 w-px bg-brand-mist/50"
                          style={{ left: `${pctOf(t.ms, span)}%` }}
                          aria-hidden
                        />
                      ))}

                      {/* gaps */}
                      {gaps.map((g) => {
                        const from = Math.max(pctOf(g.fromMs, span), 0);
                        const to = Math.min(pctOf(g.toMs, span), 100);
                        const w = to - from;
                        if (w <= 0.3) return null;
                        const colour = g.explainedBy
                          ? SOURCE_META[g.explainedBy].color
                          : "#9da2b1";
                        return (
                          <span
                            key={`${g.fromMs}-${g.toMs}`}
                            title={
                              g.explainedBy
                                ? `${g.days} days with no ${l.short.toLowerCase()} activity — explained by coverage. ${g.why}`
                                : `${g.days} days of silence on ${l.label.toLowerCase()}.`
                            }
                            className="absolute inset-y-[7px] rounded-[3px]"
                            style={{
                              left: `${from}%`,
                              width: `${w}%`,
                              background: `repeating-linear-gradient(135deg,${colour}33 0 5px,transparent 5px 10px)`,
                              border: `1px dashed ${colour}66`,
                            }}
                          />
                        );
                      })}

                      {/* events */}
                      {rows.map((e) => {
                        const size =
                          e.weight === "major" ? 11 : e.weight === "normal" ? 8 : 5;
                        const on = selected?.id === e.id;
                        /* Hollow = on the record, not checkable. See the
                           header: a ring is a coverage failure, an empty
                           stretch of lane is a relationship failure, and
                           collapsing the two would hide the difference that
                           decides what you do about it. */
                        const hollow = e.citation === null;
                        return (
                          <button
                            key={e.id}
                            type="button"
                            onClick={() =>
                              patch({ spineEventId: on ? null : e.id })
                            }
                            title={`${fmtShort(e.occurredAt)} · ${e.title}${e.detail ? ` — ${e.detail}` : ""}${hollow ? " · no citation" : ""}`}
                            aria-label={`${fmtDate(e.occurredAt)}: ${e.title}${hollow ? " (not citable)" : ""}`}
                            className="absolute top-1/2 z-10 -translate-x-1/2 -translate-y-1/2 rounded-full transition-transform hover:scale-150"
                            style={{
                              left: `${pctOf(ms(e.occurredAt), span)}%`,
                              width: size,
                              height: size,
                              background: hollow ? "transparent" : l.color,
                              border: hollow
                                ? `${e.weight === "minor" ? 1 : 2}px solid ${l.color}`
                                : "none",
                              opacity: e.weight === "minor" ? 0.55 : 0.9,
                              outline: on ? "2px solid #221e17" : "none",
                              outlineOffset: 2,
                            }}
                          />
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* legend */}
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-brand-mist pt-2.5 text-[10.5px] text-brand-gray">
              <span className="inline-flex items-center gap-1.5">
                <span className="h-[11px] w-[11px] rounded-full bg-brand-ink/80" /> major
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-[8px] w-[8px] rounded-full bg-brand-ink/70" /> event
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-[5px] w-[5px] rounded-full bg-brand-ink/50" /> minor
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-[9px] w-[9px] rounded-full border-2 border-brand-ink/70" />
                no citation
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span
                  className="h-[10px] w-6 rounded-[3px] border border-dashed border-brand-slate"
                  style={{
                    background:
                      "repeating-linear-gradient(135deg,#9da2b133 0 5px,transparent 5px 10px)",
                  }}
                />
                silence
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span
                  className="h-3 w-px"
                  style={{
                    background:
                      "repeating-linear-gradient(to bottom,#a83323 0 3px,transparent 3px 6px)",
                  }}
                />
                record begins
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-3 w-px bg-brand-primary" /> today
              </span>
            </div>
          </div>
        </div>
      </Panel>

      {/* ── record boundary declaration ────────────────────────── */}
      <Panel
        title="Where this record starts, and what it cannot see"
        subtitle="Declared per source. A gap you can explain is a different problem from a client who went quiet."
      >
        <div className="rounded-xl border border-brand-mist bg-brand-surface p-3.5">
          <p className="text-[12.5px] font-bold text-brand-ink">
            {fmtDate(rec.backfill.beginsAt)} ·{" "}
            {rec.backfill.mode === "backfilled"
              ? "Backfilled"
              : rec.backfill.mode === "from-connection"
                ? "From connection"
                : "No engagement yet"}
          </p>
          <p className="mt-1 text-[12px] leading-relaxed text-brand-secondary">
            {rec.backfill.summary}
          </p>
          <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
            <SectionLabel>Reached</SectionLabel>
            {rec.backfill.reachable.map((s) => (
              <Pill key={s} tone="green">
                {SOURCE_META[s].label}
              </Pill>
            ))}
          </div>
        </div>

        {rec.backfill.unreachable.length > 0 && (
          <ul className="mt-3 space-y-2">
            {rec.backfill.unreachable.map((u) => (
              <li
                key={u.source + (u.from ?? "")}
                className="rounded-xl border border-console-bad/25 bg-console-bad/[0.04] p-3.5"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <SourceDot source={u.source} />
                  <span className="text-[12.5px] font-bold text-brand-ink">
                    {SOURCE_META[u.source].label}
                  </span>
                  <Pill tone="red">
                    {u.from ? `Blind from ${fmtShort(u.from)}` : "No data"}
                  </Pill>
                </div>
                <p className="mt-1.5 text-[12px] leading-relaxed text-brand-secondary">
                  {u.why}
                </p>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      {/* ── selected event ─────────────────────────────────────── */}
      {selected && <EventDetail event={selected} onClose={() => patch({ spineEventId: null })} />}

      {/* ── lane health ────────────────────────────────────────── */}
      <Panel
        title="Lane health"
        subtitle="Silence measured against the cadence each lane is supposed to keep"
        bodyClassName="px-2 py-2"
      >
        <ul className="divide-y divide-brand-mist/60">
          {health.map((h) => (
            <li key={h.lane} className="flex flex-wrap items-center gap-3 px-3 py-2.5">
              <span
                className="h-4 w-[3px] flex-none rounded-full"
                style={{ background: h.color }}
                aria-hidden
              />
              <span className="min-w-0 flex-1">
                <span className="block text-[12.5px] font-bold text-brand-ink">
                  {h.label}
                  <span className="ml-2 font-medium text-brand-gray">
                    {h.count} event{h.count === 1 ? "" : "s"}
                  </span>
                </span>
                <span className="block text-[11.5px] leading-snug text-brand-gray">
                  {h.note}
                </span>
              </span>
              <span className="text-[11.5px] tabular-nums text-brand-secondary">
                {h.lastAt ? fmtShort(h.lastAt) : "—"}
              </span>
              <Pill tone={HEALTH_META[h.state].tone}>{HEALTH_META[h.state].label}</Pill>
            </li>
          ))}
        </ul>
      </Panel>

      {/* ── assets ─────────────────────────────────────────────── */}
      <AssetsPanel rec={rec} />

      {/* ── the events themselves ──────────────────────────────── */}
      <EventList
        events={visible}
        selectedId={selected?.id ?? null}
        onSelect={(id) => patch({ spineEventId: id === selected?.id ? null : id })}
      />
    </div>
  );
}

/* ── Event detail ─────────────────────────────────────────────── */

function EventDetail({
  event: e,
  onClose,
}: {
  event: EngagementEvent;
  onClose: () => void;
}) {
  const lane = LANE_META[e.lane];
  return (
    <Panel
      title="Selected event"
      right={
        <button
          type="button"
          onClick={onClose}
          className="text-[11.5px] font-bold uppercase tracking-[0.1em] text-brand-gray hover:text-brand-ink"
        >
          Clear
        </button>
      }
    >
      <div className="flex flex-wrap items-center gap-2">
        <Pill tone="navy">{fmtDate(e.occurredAt)}</Pill>
        <Pill tone="outline">{fmtTime(e.occurredAt)}</Pill>
        <span
          className="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-bold"
          style={{ background: `${lane.color}1a`, color: lane.color }}
        >
          {lane.label}
        </span>
        <span className="inline-flex items-center gap-1.5 text-[11.5px] text-brand-gray">
          <SourceDot source={e.source} />
          {SOURCE_META[e.source].label}
        </span>
      </div>
      <p className="mt-3 text-[15px] font-bold leading-snug text-brand-ink">{e.title}</p>
      {e.detail && (
        <p className="mt-1.5 text-[12.5px] leading-relaxed text-brand-secondary">
          {e.detail}
        </p>
      )}
      <dl className="mt-3.5 grid gap-x-6 gap-y-2 sm:grid-cols-3">
        <div>
          <dt className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-brand-slate">
            Actor
          </dt>
          <dd className="mt-0.5 text-[12.5px] text-brand-secondary">
            {e.actor} ·{" "}
            {e.side === "wia" ? "our side" : e.side === "client" ? "client side" : "system"}
          </dd>
        </div>
        <div>
          <dt className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-brand-slate">
            Citation
          </dt>
          <dd
            className={
              "mt-0.5 text-[12.5px] " +
              (e.citation ? "text-brand-secondary" : "font-bold text-console-bad")
            }
          >
            {e.citation ?? "— not citable"}
          </dd>
        </div>
        <div>
          <dt className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-brand-slate">
            Source record
          </dt>
          <dd className="mt-0.5 text-[12.5px] text-brand-secondary">
            {e.sourceRef ?? "No record to open"}
          </dd>
        </div>
      </dl>
      {!e.citation && (
        <p className="mt-3 rounded-lg border border-console-bad/25 bg-console-bad/[0.05] px-3 py-2 text-[11.5px] leading-relaxed text-brand-secondary">
          This event is on the record but cannot be checked against a source. It is
          shown with an explicit dash rather than a derived timestamp — a fabricated
          citation is worse than an admitted gap.
        </p>
      )}
    </Panel>
  );
}

/* ── Event list ───────────────────────────────────────────────── */

function EventList({
  events,
  selectedId,
  onSelect,
}: {
  events: EngagementEvent[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  /* Newest first, grouped by month. The spine answers "what shape is this
     engagement"; this answers "what exactly happened", and they have to agree
     because they read the same array. */
  const groups = useMemo(() => {
    const out: { label: string; rows: EngagementEvent[] }[] = [];
    for (const e of [...events].sort((a, b) => b.occurredAt.localeCompare(a.occurredAt))) {
      const label = fmtMonth(new Date(e.occurredAt));
      const last = out[out.length - 1];
      if (last && last.label === label) last.rows.push(e);
      else out.push({ label, rows: [e] });
    }
    return out;
  }, [events]);

  return (
    <Panel
      title="Every event in view"
      subtitle={`${events.length} row${events.length === 1 ? "" : "s"}, newest first — the same array the spine above is drawn from`}
      bodyClassName="px-2 py-2"
    >
      {events.length === 0 ? (
        <Empty>Nothing on this lane inside the selected window.</Empty>
      ) : (
        <div className="max-h-[520px] overflow-y-auto">
          {groups.map((g) => (
            <div key={g.label}>
              <p className="sticky top-0 z-10 bg-white/95 px-3 py-1.5 text-[10.5px] font-bold uppercase tracking-[0.12em] text-brand-slate backdrop-blur">
                {g.label}
              </p>
              <ul className="divide-y divide-brand-mist/60">
                {g.rows.map((e) => {
                  const lane = LANE_META[e.lane];
                  const on = e.id === selectedId;
                  return (
                    <li key={e.id}>
                      <button
                        type="button"
                        onClick={() => onSelect(e.id)}
                        className={
                          "flex w-full flex-wrap items-start gap-3 px-3 py-2.5 text-left transition-colors " +
                          (on ? "bg-brand-primary/[0.06]" : "hover:bg-brand-mist/30")
                        }
                      >
                        <span className="w-[76px] flex-none pt-px text-[11.5px] tabular-nums text-brand-gray">
                          {fmtShort(e.occurredAt)}
                        </span>
                        <span
                          className="mt-[5px] h-2 w-2 flex-none rounded-full"
                          style={{ background: lane.color }}
                          aria-hidden
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block text-[12.5px] font-bold leading-snug text-brand-ink">
                            {e.title}
                          </span>
                          {e.detail && (
                            <span className="mt-0.5 block text-[11.5px] leading-snug text-brand-gray">
                              {e.detail}
                            </span>
                          )}
                          <span className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-brand-gray">
                            <span className="inline-flex items-center gap-1.5">
                              <SourceDot source={e.source} />
                              {SOURCE_META[e.source].label}
                            </span>
                            <span>·</span>
                            <span>{e.actor}</span>
                            <span>·</span>
                            <span
                              className={e.citation ? "" : "font-bold text-console-bad"}
                            >
                              {e.citation ? `cite ${e.citation}` : "— not citable"}
                            </span>
                          </span>
                        </span>
                        <span className="flex-none text-[11px] text-brand-slate">
                          {lane.short}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

/* ── Assets ───────────────────────────────────────────────────── */

function AssetsPanel({ rec }: { rec: EngagementRecord }) {
  const live = liveAssets(rec);
  const old = supersededAssets(rec);

  return (
    <Panel
      title="Approved work on record"
      subtitle="What is live today, and what it replaced — the chain is why 'which landing page is current' is answerable without opening Drive"
      right={<Layers className="h-4 w-4 text-brand-slate" />}
    >
      {live.length === 0 ? (
        <Empty>Nothing approved on this account yet.</Empty>
      ) : (
        <ul className="space-y-2">
          {live.map((a) => (
            <li
              key={a.id}
              className="rounded-xl border border-brand-mist bg-brand-surface px-3.5 py-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <FileCheck2 className="h-3.5 w-3.5 flex-none text-console-good" />
                <span className="text-[12.5px] font-bold text-brand-ink">{a.title}</span>
                <Pill tone="green">Live</Pill>
                <Pill tone="outline">{ASSET_KIND_LABEL[a.kind]}</Pill>
              </div>
              <p className="mt-1 text-[11.5px] text-brand-gray">
                Approved {fmtDate(a.approvedAt)} by {a.approvedBy} · {fmtRel(a.approvedAt)}{" "}
                · {a.sourceRef}
              </p>
              {a.note && (
                <p className="mt-1 text-[11.5px] leading-snug text-brand-secondary">
                  {a.note}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}

      {old.length > 0 && (
        <>
          <div className="mt-4">
            <SectionLabel>Superseded — kept on the record, not live</SectionLabel>
          </div>
          <ul className="mt-2 space-y-1.5">
            {old.map((a) => (
              <li
                key={a.id}
                className="flex flex-wrap items-center gap-2 rounded-lg border border-brand-mist/70 px-3 py-2 text-[11.5px] text-brand-gray"
              >
                <span className="font-bold text-brand-secondary">{a.title}</span>
                <ArrowRight className="h-3 w-3 text-brand-slate" />
                <span>
                  replaced by{" "}
                  {rec.assets.find((x) => x.supersedes === a.id)?.title ?? "a later version"}
                </span>
                <span className="ml-auto tabular-nums">{fmtShort(a.approvedAt)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </Panel>
  );
}
