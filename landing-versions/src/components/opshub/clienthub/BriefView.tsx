/* ────────────────────────────────────────────────────────────────
   Brief — the handover reading of the engagement record.

   WHAT IT IS FOR. Whitney's stated reason for buying any of this was not
   saving time: it was getting institutional knowledge out of individual
   contractors' heads, so the next account manager "is just a person who is
   kind of like running it." This screen is that artefact. It is what someone
   taking an account over on a Monday reads before their first call.

   IT IS ASSEMBLED, NOT WRITTEN. Every fact is computed in lib/engagement
   from the record and the ledgers. There is no authored prose per client
   anywhere in this build, which is the only way a brief stays true — a
   hand-written one is accurate on the day it is written and wrong by the
   following quarter, which is the exact failure mode of the ChatGPT projects
   this is meant to replace.

   THE LAST SECTION IS THE POINT. "What this record cannot tell you" lists
   the holes: where backfill stops, which source went blind and when, which
   lanes have gone stale. A handover that hides its own gaps is worse than no
   handover, because it teaches the reader to trust it everywhere.
   ──────────────────────────────────────────────────────────────── */

import { useMemo } from "react";
import { ClipboardCopy, UserRound } from "lucide-react";
import type { EngagementRecord } from "@/data/engagement";
import {
  buildBrief,
  currentPhase,
  engagementAgeDays,
  engagementStart,
  fmtDate,
  fmtDuration,
  watchList,
} from "@/lib/engagement";
import type { Client } from "@/data/opsHub";
import type { OpsHub } from "@/hooks/useOpsHub";
import { Empty, Panel, Pill, SectionLabel } from "../primitives";

export function BriefView({
  hub,
  rec,
  client,
}: {
  hub: OpsHub;
  rec: EngagementRecord;
  client: Client;
}) {
  const { patch, toast } = hub;
  const sections = useMemo(() => buildBrief(rec, client), [rec, client]);
  const watch = useMemo(() => watchList(rec, client), [rec, client]);
  const phase = currentPhase(rec);
  const age = engagementAgeDays(rec);
  const start = engagementStart(rec);

  return (
    <div className="space-y-5">
      {/* ── header ─────────────────────────────────────────────── */}
      <Panel
        title="Handover brief"
        subtitle="Assembled from the record on every render. Nothing here is authored per client, so it cannot go stale between readings."
        right={
          <button
            type="button"
            onClick={() =>
              toast(
                "Simulated — a real build would put the brief on the clipboard as Markdown.",
              )
            }
            className="inline-flex items-center gap-1.5 rounded-lg border border-brand-mist px-2.5 py-1.5 text-[11.5px] font-bold text-brand-secondary transition-colors hover:border-brand-stone"
          >
            <ClipboardCopy className="h-3.5 w-3.5" />
            Copy brief
          </button>
        }
      >
        <p className="text-[13px] leading-relaxed text-brand-secondary">
          <span className="font-bold text-brand-ink">{client.name}</span> has been{" "}
          {age === null ? (
            <>a prospect since {fmtDate(rec.backfill.beginsAt)}, with no contract signed.</>
          ) : (
            <>
              a client for {fmtDuration(age)}, since {fmtDate(start!)}.
            </>
          )}{" "}
          {phase && (
            <>
              The engagement is currently in{" "}
              <span className="font-bold" style={{ color: phase.color }}>
                {phase.label.toLowerCase()}
              </span>
              {" — "}
              {/* The note keeps its own casing. Lowercasing it to fit the
                  sentence turned "due 2 Sep" into "due 2 sep" on the one
                  account where the date is the whole point. */}
              {phase.note}.
            </>
          )}
        </p>
      </Panel>

      {/* ── what to watch, first ───────────────────────────────── */}
      <Panel
        title="What to watch"
        subtitle="The only judgement on this page. Each line routes to the ledger that proves it."
      >
        {watch.length === 0 ? (
          <Empty>Nothing outstanding.</Empty>
        ) : (
          <ul className="space-y-2">
            {watch.map((w, i) => (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => patch({ clientTab: w.tab, askAnswer: null })}
                  className="flex w-full items-start gap-3 rounded-xl border border-brand-mist bg-brand-surface px-3.5 py-2.5 text-left transition-colors hover:border-brand-stone"
                >
                  <Pill tone={w.tone}>
                    {w.tone === "red"
                      ? "Act"
                      : w.tone === "amber"
                        ? "Watch"
                        : w.tone === "green"
                          ? "Clear"
                          : "Note"}
                  </Pill>
                  <span className="min-w-0 flex-1 text-[12.5px] leading-snug text-brand-secondary">
                    {w.text}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      {/* ── the sections ───────────────────────────────────────── */}
      {sections.map((s) => (
        <Panel key={s.key} title={s.title} subtitle={s.blurb}>
          <dl className="divide-y divide-brand-mist/60">
            {s.facts.map((f, i) => (
              <div
                key={`${f.label}-${i}`}
                className="grid gap-1 py-2.5 sm:grid-cols-[180px_1fr] sm:gap-4"
              >
                <dt className="text-[11.5px] font-bold uppercase tracking-[0.06em] text-brand-slate">
                  {f.label}
                </dt>
                <dd className="min-w-0">
                  <span className="flex flex-wrap items-baseline gap-2">
                    <span className="text-[12.5px] leading-relaxed text-brand-secondary">
                      {f.value}
                    </span>
                    {f.tone && f.tone !== "neutral" && (
                      <Pill tone={f.tone}>
                        {f.tone === "red"
                          ? "attention"
                          : f.tone === "amber"
                            ? "watch"
                            : f.tone === "green"
                              ? "ok"
                              : "note"}
                      </Pill>
                    )}
                  </span>
                  {f.cite && (
                    <span className="mt-0.5 block text-[11px] text-brand-gray">
                      source · {f.cite}
                    </span>
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </Panel>
      ))}

      {/* ── people, with validity ──────────────────────────────── */}
      <Panel
        title="Who has been on this account"
        subtitle="Both sides, with the dates they were valid — so a 2025 event is not signed by someone who arrived in 2026"
        right={<UserRound className="h-4 w-4 text-brand-slate" />}
        bodyClassName="px-2 py-2"
      >
        <ul className="divide-y divide-brand-mist/60">
          {rec.people.map((p) => (
            <li
              key={`${p.name}-${p.validFrom}`}
              className="flex flex-wrap items-center gap-3 px-3 py-2.5"
            >
              <span className="min-w-0 flex-1">
                <span className="block text-[12.5px] font-bold text-brand-ink">
                  {p.name}
                  <span className="ml-2 font-medium text-brand-gray">{p.role}</span>
                </span>
                <span className="block text-[11.5px] text-brand-gray">{p.email}</span>
              </span>
              <span className="text-[11.5px] tabular-nums text-brand-secondary">
                {fmtDate(p.validFrom)} →{" "}
                {p.validTo ? fmtDate(p.validTo) : "present"}
              </span>
              <Pill tone={p.validTo ? "outline" : p.side === "client" ? "blue" : "slate"}>
                {p.validTo ? "Former" : p.side === "client" ? "Client" : "WIA"}
              </Pill>
            </li>
          ))}
        </ul>
      </Panel>

      <div className="rounded-xl border border-brand-mist bg-brand-mist/20 px-4 py-3">
        <SectionLabel>How this page is built</SectionLabel>
        <p className="mt-1.5 text-[11.5px] leading-relaxed text-brand-gray">
          Every line above is computed from the engagement record and the ledgers at
          render time — there is no stored summary and no model call. That is what
          makes it safe to read cold: a brief that is assembled cannot disagree with
          the record it was assembled from.
        </p>
      </div>
    </div>
  );
}
