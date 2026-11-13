/* Settings — source coverage and the boundary of the build.

   THIS IS THE MOST HONEST SCREEN AND IT SHOULD STAY THAT WAY. Every `note`
   under a source is a real production constraint: Gmail watches expire in
   seven days, Slack visibility is scope- and membership-dependent, Zoom's
   participant API needs Pro or higher, Fathom keys are per-user so an admin
   key unlocks nothing, one Drive mapping is unresolved, and HighLevel's
   recurring Community behaviour has never been validated in the WIA tenant.

   The out-of-scope list is deliberately first-class. "No onboarding
   orchestration" leads it because that workstream already exists as its own
   console at /onboarding — duplicating it here would create two disagreeing
   sources of truth for the one decision that cannot be wrong.

   FOUR TABLES WERE ADDED HERE RATHER THAN INVENTED ELSEWHERE, because this is
   the screen a reader already comes to for "what is actually true":

     · the CAPABILITY REGISTER, replacing blanket "API access required"
       language with four honest states and the test that moves each row
     · the ACCOUNT TOPOLOGY, because two HighLevel accounts and one shared
       mailbox is the real shape and the hub previously described one
     · the REVIEWER MATRIX, one agreed answer to who may approve what
     · the DATA INVENTORY, because "synthetic demo data" was not a true
       description of every dataset in this repository */

import { ExternalLink, RotateCcw, ShieldCheck } from "lucide-react";
import {
  AUTHORITY_META,
  CAPABILITY_META,
  CAPABILITY_REGISTER,
  DATA_INVENTORY,
  DATA_ORIGIN_META,
  EMAIL_POLICY,
  IDENTITY_ACCESS,
  OUT_OF_SCOPE,
  REVIEWER_MATRIX,
  SOURCE_SETTINGS,
  TENANTS,
} from "@/data/opsHub";
import type { OpsHub } from "@/hooks/useOpsHub";
import { Actions, Panel, Pill, SectionLabel, SourceChip } from "../primitives";

export function SettingsScreen({ hub }: { hub: OpsHub }) {
  const { resetDemo } = hub;

  return (
    <div className="space-y-5">
      <Panel
        title="Connected sources"
        subtitle="What it can read, what it can write, and what has not been verified"
        right={<Pill tone="amber">Demo environment</Pill>}
      >
        <div className="space-y-3">
          {SOURCE_SETTINGS.map((s) => (
            <div key={s.key} className="rounded-xl border border-brand-mist bg-white p-4">
              <div className="flex flex-wrap items-center gap-2">
                <SourceChip source={s.key} />
                <span className="text-[12.5px] text-brand-secondary">{s.role}</span>
                <Pill tone={s.tone} className="ml-auto">
                  {s.status}
                </Pill>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {s.caps.map((c) => (
                  <Pill key={c} tone="outline">
                    {c}
                  </Pill>
                ))}
              </div>
              <p className="mt-3 border-l-2 border-console-warn/40 pl-3 text-[11.5px] leading-snug text-console-warn">
                {s.note}
              </p>
            </div>
          ))}
        </div>
      </Panel>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel
          title="Identity and access"
          subtitle="One service account, four systems"
          right={<ShieldCheck className="h-4 w-4 text-console-good" />}
        >
          <p className="text-[12.5px] text-brand-secondary">
            The hub acts as a single named account —{" "}
            <span className="font-bold text-brand-ink">
              ai@weddingindustryads.com
            </span>{" "}
            — so every write is attributable to it. It is credentials, not
            access: each grant is separate, and the two HighLevel accounts are
            two grants.
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {IDENTITY_ACCESS.map((l) => (
              <Pill key={l} tone="slate">
                {l}
              </Pill>
            ))}
          </div>
          <p className="mt-3 text-[11.5px] leading-snug text-brand-gray">
            The ClickUp seat must be a Member, not a Guest — Guests cannot read
            templates.
          </p>
        </Panel>

        <Panel title="Deliberately out of scope" subtitle="Each one says where it lives instead">
          {/* Paired rather than a pill cloud: a bare "No client performance
              reporting" reads as an omission, and that one is the largest
              single cost in discovery. The right-hand column is the answer to
              "then who does it?" — every line lands on a named initiative in
              the Blueprint roadmap. */}
          <ul className="space-y-1.5">
            {OUT_OF_SCOPE.map(([claim, where]) => (
              <li
                key={claim}
                className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-brand-mist/70 pb-1.5 last:border-0"
              >
                <Pill tone="outline">{claim}</Pill>
                <span className="text-[11px] text-brand-gray">{where}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[11.5px] leading-snug text-brand-gray">
            Each belongs to a different build or to a person by design.
          </p>
        </Panel>
      </div>

      {/* ── THE CAPABILITY REGISTER — F10 ─────────────────────── */}
      <Panel
        title="Capability register"
        subtitle="What is proven, what needs setting up, and what is still untested"
        right={
          <div className="flex flex-wrap gap-1.5">
            {(
              ["confirmed", "configure", "untested", "fallback"] as const
            ).map((k) => (
              <Pill key={k} tone={CAPABILITY_META[k].tone}>
                {CAPABILITY_META[k].label}
              </Pill>
            ))}
          </div>
        }
      >
        <div className="space-y-3">
          {CAPABILITY_REGISTER.map((c) => (
            <div key={c.area} className="rounded-xl border border-brand-mist bg-white p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[13px] font-bold text-brand-ink">{c.area}</span>
                <Pill tone="outline">{c.initiative}</Pill>
                <Pill tone={CAPABILITY_META[c.state].tone} className="ml-auto">
                  {CAPABILITY_META[c.state].label}
                </Pill>
              </div>
              <p className="mt-1.5 text-[12px] leading-snug text-brand-secondary">
                {c.position}
              </p>
              <p className="mt-1.5 text-[11.5px] leading-snug text-brand-gray">
                <span className="font-bold text-brand-ink">Next · </span>
                {c.validation}
                {c.reference && (
                  <a
                    href={c.reference}
                    target="_blank"
                    rel="noreferrer"
                    className="ml-1.5 inline-flex items-center gap-1 font-bold text-brand-primary"
                  >
                    docs
                    <ExternalLink className="h-3 w-3" aria-hidden />
                  </a>
                )}
              </p>
            </div>
          ))}
        </div>
      </Panel>

      {/* ── ACCOUNT AND MAILBOX TOPOLOGY — F09 ────────────────── */}
      <Panel
        title="Accounts, mailboxes and identities"
        subtitle="Two HighLevel accounts, one shared mailbox, one integration identity"
      >
        <div className="grid gap-3 md:grid-cols-2">
          {TENANTS.map((t) => (
            <div key={t.id} className="rounded-xl border border-brand-mist bg-white p-4">
              <p className="text-[13px] font-bold text-brand-ink">{t.name}</p>
              <p className="mt-0.5 text-[11.5px] text-brand-gray">
                {t.system} · {t.purpose}
              </p>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {t.sourceOf.map((x) => (
                  <Pill key={x} tone="green">
                    {x}
                  </Pill>
                ))}
                {t.notSourceOf.map((x) => (
                  <Pill key={x} tone="outline">
                    not {x.toLowerCase()}
                  </Pill>
                ))}
              </div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[11.5px] text-brand-gray">
          Every record carries its tenant. Location ids to be recorded on access.
        </p>
      </Panel>

      {/* ── REVIEWER MATRIX — F04 ─────────────────────────────── */}
      <Panel
        title="Who may approve what"
        subtitle="Applied on every screen. Amber rows are still open decisions."
      >
        <ul className="divide-y divide-brand-mist/70 overflow-hidden rounded-xl border border-brand-mist">
          {REVIEWER_MATRIX.map((r) => {
            const a = AUTHORITY_META[r.authority];
            return (
              <li key={r.artifact} className="px-3.5 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[12.5px] font-bold text-brand-ink">
                    {r.artifact}
                  </span>
                  <Pill tone="outline">{r.initiative}</Pill>
                  <Pill tone={a.tone} className="ml-auto">
                    {a.label}
                  </Pill>
                  {!a.confirmed && <Pill tone="amber">To agree</Pill>}
                </div>
                <p className="mt-1 text-[11.5px] leading-snug text-brand-gray">
                  Sends: {r.sends}
                </p>
              </li>
            );
          })}
        </ul>
      </Panel>

      {/* ── EMAIL POLICY — F14 ────────────────────────────────── */}
      <Panel
        title="Inbox policy"
        subtitle="The rules triage applies. Amber rows are our proposal, not theirs."
      >
        <ul className="divide-y divide-brand-mist/70 overflow-hidden rounded-xl border border-brand-mist">
          {EMAIL_POLICY.map((r) => (
            <li key={r.situation} className="px-3.5 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[12.5px] font-bold text-brand-ink">
                  {r.situation}
                </span>
                <Pill tone={r.agreed ? "green" : "amber"} className="ml-auto">
                  {r.agreed ? "From discovery" : "To agree"}
                </Pill>
              </div>
              <p className="mt-1 text-[12px] leading-snug text-brand-secondary">
                {r.rule}{" "}
                <span className="text-brand-slate">· {r.basis}</span>
              </p>
            </li>
          ))}
        </ul>
      </Panel>

      {/* ── DATA INVENTORY — F17 ──────────────────────────────── */}
      <Panel
        title="What each dataset actually is"
        subtitle="The hub is synthetic. Not everything in this build is."
        right={
          <div className="flex flex-wrap gap-1.5">
            {(["synthetic", "derived", "real"] as const).map((k) => (
              <Pill key={k} tone={DATA_ORIGIN_META[k].tone}>
                {DATA_ORIGIN_META[k].label}
              </Pill>
            ))}
          </div>
        }
      >
        <ul className="divide-y divide-brand-mist/70 overflow-hidden rounded-xl border border-brand-mist">
          {DATA_INVENTORY.map((d) => (
            <li key={d.what} className="px-3.5 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="min-w-0 flex-1 text-[12.5px] font-bold text-brand-ink">
                  {d.what}
                </span>
                <Pill tone={DATA_ORIGIN_META[d.origin].tone}>
                  {DATA_ORIGIN_META[d.origin].label}
                </Pill>
              </div>
              <p className="mt-0.5 text-[11px] text-brand-gray">
                {d.shareable}
                <span className="ml-1.5 font-mono text-brand-slate">{d.where}</span>
              </p>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-[11.5px] text-console-warn">
          An unlisted URL is not an access boundary. Check this before sharing.
        </p>
      </Panel>

      <Panel
        title="Demo controls"
        subtitle="Every count, status and queue returns to its starting point"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Actions
            actions={[
              {
                label: "Reset demo state",
                variant: "primary",
                onClick: resetDemo,
              },
            ]}
          />
          <p className="flex items-center gap-1.5 text-[11.5px] text-brand-gray">
            <RotateCcw className="h-3.5 w-3.5" />
            Nothing here has ever written to a real system.
          </p>
        </div>
      </Panel>

      <Panel title="What this environment is not">
        {/* THESE LINES MUST STAY TRUE. An earlier pass left two entries here
            describing defects that had already been fixed in the same pass —
            a missing roster and an invented service tier — so the demo was
            telling the client it was broken in ways it no longer was. Every
            line below is checkable against the data: if one stops being true,
            delete it rather than leaving it to read as a live defect. */}
        <ul className="space-y-1.5 text-[12.5px] leading-snug text-brand-secondary">
          {[
            "No connector is live. Every source above is synthetic and every action is simulated.",
            "No client data is loaded into this hub. Other parts of this build do carry real material — see the dataset table above.",
            "Three coverage gaps are real and shown above: two private Slack channels, one unmapped Drive folder, and HighLevel's recurring Community series.",
            "Onboarding, roll call and internal meetings keep their own consoles. This hub reads them.",
          ].map((l) => (
            <li key={l} className="flex items-start gap-2">
              <span
                className="mt-[6px] h-1.5 w-1.5 flex-none rounded-full bg-console-warn"
                aria-hidden
              />
              {l}
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
