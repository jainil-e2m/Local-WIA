/* ────────────────────────────────────────────────────────────────
   What happens after approval — the onboarding journey.

   WHY THIS PAGE EXISTS. The console modelled ONE row of the onboarding:
   the ClickUp lists. Everything Whitney actually described on 2 September —
   the welcome email, the Drive folder, the Slack brief, the LeadLock
   sub-account, two kickoff calls running in parallel, the build-and-review
   loop, the launch gate — was either invisible or buried in a table on the
   review screen, where it competed with the task list for attention.

   It is a MAP, not a mockup. Nothing on it is wired, and it says so once
   rather than on every card. The point is to show that the sequence is
   understood and sequenced, and to make the two-track shape legible: the
   ads track and the LeadLock track run at the same time, and they converge
   at a single gate that today is somebody remembering to tell Carmen and
   Jacqueline.

   Everything below is from the 2 September walkthrough (@20:59 → @40:36).
   ──────────────────────────────────────────────────────────────── */

import { ArrowLeft, Check, RotateCw } from "lucide-react";

type Maturity = "built" | "phase1" | "later" | "manual";

const MATURITY: Record<Maturity, { label: string; dot: string; chip: string }> = {
  built: {
    label: "Demoed here",
    dot: "bg-emerald-500",
    chip: "border-emerald-200 bg-emerald-50 text-emerald-800",
  },
  phase1: {
    label: "Phase 1",
    dot: "bg-brand-primary",
    chip: "border-brand-primary/25 bg-brand-primary/10 text-brand-primary",
  },
  later: {
    label: "Phase 2–3",
    dot: "bg-amber-400",
    chip: "border-amber-200 bg-amber-50 text-amber-800",
  },
  manual: {
    label: "Stays manual",
    dot: "bg-brand-stone",
    chip: "border-brand-stone bg-white text-brand-secondary",
  },
};

type Step = {
  title: string;
  owner: string;
  systems: string[];
  maturity: Maturity;
  note?: string;
};

type Stage = {
  id: string;
  kicker: string;
  title: string;
  when: string;
  steps: Step[];
};

/* ── Before the tracks split ─────────────────────────────────── */
const SIGNATURE: Stage = {
  id: "signature",
  kicker: "Trigger",
  title: "Signed and paid",
  when: "Dubsado alert pair lands in hello@",
  steps: [
    {
      title: "Create the ClickUp lists",
      owner: "Gisselle",
      systems: ["ClickUp"],
      maturity: "built",
      note: "One list per signed offer, owners resolved, dates from each call",
    },
    {
      title: "Welcome email",
      owner: "Gisselle",
      systems: ["Gmail", "Dubsado"],
      maturity: "phase1",
      note: "Countersigned contract, kickoff booking link, questionnaire",
    },
    {
      title: "Client folder in Drive",
      owner: "Gisselle",
      systems: ["Drive"],
      maturity: "phase1",
      note: "Sales-call recording, contract, questionnaire filed in",
    },
    {
      title: "Slack channel + team brief",
      owner: "Gisselle",
      systems: ["Slack"],
      maturity: "phase1",
      note: "Who signed, which offers, links to the questionnaire",
    },
    {
      title: "LeadLock sub-account",
      owner: "Danielle",
      systems: ["HighLevel"],
      maturity: "manual",
      note: "Billing-bearing — raised as a task, created by a person",
    },
  ],
};

/* ── The two tracks, running at the same time ────────────────── */
const ADS_TRACK: Stage[] = [
  {
    id: "ads-kickoff",
    kicker: "Call 1",
    title: "Ads kickoff",
    when: "Client books it from the welcome email",
    steps: [
      {
        title: "Expectations and education",
        owner: "Whitney",
        systems: ["Zoom"],
        maturity: "manual",
      },
      {
        title: "Account access by screen-share",
        owner: "Whitney",
        systems: ["Google Ads", "Meta", "GA4"],
        maturity: "manual",
        note: "Every self-serve variant has been tried; clients get stuck",
      },
      {
        title: "Recording and summary filed",
        owner: "Gisselle",
        systems: ["Zoom", "Drive"],
        maturity: "phase1",
      },
    ],
  },
  {
    id: "positioning",
    kicker: "Call 2",
    title: "Messaging & positioning",
    when: "Booked separately with Whitney",
    steps: [
      {
        title: "Transcript into the client knowledge base",
        owner: "Gisselle",
        systems: ["Knowledge base"],
        maturity: "later",
        note: "Replaces the per-client ChatGPT project, and keeps it current",
      },
      {
        title: "Draft Google and Meta strategy",
        owner: "Carmen · Jacqueline",
        systems: ["Knowledge base"],
        maturity: "later",
        note: "First drafts for the team to react to",
      },
    ],
  },
  {
    id: "strategy",
    kicker: "Call 3",
    title: "Ad strategy presentation",
    when: "Shortly after positioning",
    steps: [
      {
        title: "Keyword plan approved on the call",
        owner: "Carmen",
        systems: ["Google Ads"],
        maturity: "manual",
      },
      {
        title: "Location targeting agreed",
        owner: "Whitney · Carmen",
        systems: ["Google Ads"],
        maturity: "manual",
      },
    ],
  },
  {
    id: "ads-build",
    kicker: "Build",
    title: "Campaigns built and approved",
    when: "Review loop per campaign set",
    steps: [
      {
        title: "Google Search campaign + Loom walkthrough",
        owner: "Carmen",
        systems: ["Google Ads", "Gmail"],
        maturity: "manual",
      },
      {
        title: "Client-attraction, conversion, retargeting ads",
        owner: "Jacqueline · Ivy",
        systems: ["Meta"],
        maturity: "manual",
        note: "Each set emailed for review, approved, then launched",
      },
      {
        title: "Approval chased and confirmed",
        owner: "Gisselle",
        systems: ["Gmail", "Slack"],
        maturity: "phase1",
      },
    ],
  },
];

const LEADLOCK_TRACK: Stage[] = [
  {
    id: "ll-kickoff",
    kicker: "Call 1",
    title: "LeadLock kickoff",
    when: "Runs in parallel, not after",
    steps: [
      {
        title: "Scope the automations",
        owner: "Danielle",
        systems: ["HighLevel"],
        maturity: "manual",
        note: "Inquiry, pre-tour and post-tour workflows",
      },
      {
        title: "User, email, calendar, phone number",
        owner: "Danielle",
        systems: ["HighLevel"],
        maturity: "manual",
      },
      {
        title: "DNS access captured",
        owner: "Danielle",
        systems: ["DNS"],
        maturity: "manual",
      },
    ],
  },
  {
    id: "ll-build",
    kicker: "Build",
    title: "Pages, copy and registration",
    when: "Tina and Danielle in parallel",
    steps: [
      {
        title: "Landing pages and privacy policy",
        owner: "Tina",
        systems: ["HighLevel"],
        maturity: "manual",
      },
      {
        title: "Email and SMS nurture copy",
        owner: "Tina",
        systems: ["HighLevel"],
        maturity: "later",
        note: "First drafts from the knowledge base — FF-02",
      },
      {
        title: "A2P registration",
        owner: "Danielle",
        systems: ["HighLevel", "DNS"],
        maturity: "manual",
      },
    ],
  },
  {
    id: "ll-review",
    kicker: "Review",
    title: "Client review and testing",
    when: "Edits, then internal and client tests",
    steps: [
      {
        title: "Build emailed over for review",
        owner: "Tina · Gisselle",
        systems: ["Gmail"],
        maturity: "phase1",
      },
      {
        title: "Internal and client testing",
        owner: "Danielle",
        systems: ["HighLevel"],
        maturity: "manual",
      },
      {
        title: "Official LeadLock onboarding call",
        owner: "Danielle",
        systems: ["Zoom"],
        maturity: "manual",
        note: "Approved — leads start flowing",
      },
    ],
  },
];

const GATE: Stage = {
  id: "gate",
  kicker: "Gate",
  title: "Cross-track launch",
  when: "LeadLock live and the page approved",
  steps: [
    {
      title: "Switch the campaign URLs to the LeadLock page",
      owner: "Carmen · Jacqueline",
      systems: ["Google Ads", "Meta"],
      maturity: "later",
      note: "Today this is somebody remembering to tell them — ON-05",
    },
  ],
};

const RECURRING: Stage = {
  id: "recurring",
  kicker: "Handoff",
  title: "Fully onboarded",
  when: "Every campaign launched",
  steps: [
    {
      title: "Recurring 30-minute strategy call booked",
      owner: "Whitney",
      systems: ["Zoom"],
      maturity: "manual",
    },
    {
      title: "Monthly client report pack",
      owner: "Tina",
      systems: ["Google Ads", "Meta", "LeadLock"],
      maturity: "later",
      note: "The first three days of every month today — PM-03",
    },
  ],
};

/* ── Presentation ─────────────────────────────────────────────── */

function StepRow({ step }: { step: Step }) {
  const m = MATURITY[step.maturity];
  return (
    <li className="flex items-start gap-2.5 py-1.5">
      <span className={`mt-[7px] h-1.5 w-1.5 flex-none rounded-full ${m.dot}`} aria-hidden />
      <span className="min-w-0 flex-1">
        <span className="block text-[12.5px] font-semibold leading-snug text-brand-ink">
          {step.title}
        </span>
        {step.note && (
          <span className="mt-0.5 block text-[11px] leading-snug text-brand-gray">
            {step.note}
          </span>
        )}
        <span className="mt-1 flex flex-wrap items-center gap-1">
          <span className="rounded bg-brand-mist/70 px-1.5 py-px text-[10px] font-semibold text-brand-secondary">
            {step.owner}
          </span>
          {step.systems.map((sys) => (
            <span
              key={sys}
              className="rounded border border-brand-mist px-1.5 py-px text-[10px] text-brand-gray"
            >
              {sys}
            </span>
          ))}
        </span>
      </span>
    </li>
  );
}

function StageCard({
  stage,
  accent = "border-brand-mist",
  index,
}: {
  stage: Stage;
  accent?: string;
  index?: number;
}) {
  return (
    <article className={`rounded-xl border bg-white p-4 ${accent}`}>
      <div className="flex items-start gap-3">
        {index !== undefined && (
          <span className="grid h-6 w-6 flex-none place-items-center rounded-full bg-brand-ink text-[11px] font-bold text-white">
            {index}
          </span>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-brand-slate">
            {stage.kicker}
          </p>
          <h4 className="text-[14px] font-semibold leading-tight text-brand-ink">
            {stage.title}
          </h4>
          <p className="mt-0.5 text-[11px] text-brand-gray">{stage.when}</p>
        </div>
      </div>
      <ul className="mt-2.5 divide-y divide-brand-mist/60 border-t border-brand-mist/60 pt-1">
        {stage.steps.map((s) => (
          <StepRow key={s.title} step={s} />
        ))}
      </ul>
    </article>
  );
}

/** A vertical rail segment, so the two tracks read as flowing downward. */
function Rail({ label, tone }: { label: string; tone: string }) {
  return (
    <div className="flex items-center gap-2 py-1.5" aria-hidden>
      <span className={`h-6 w-px flex-none ${tone}`} />
      <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-brand-slate">
        {label}
      </span>
    </div>
  );
}

export function OnboardingJourney({
  projectName,
  taskCount,
  listCount,
  onBack,
  onRestart,
}: {
  projectName: string;
  taskCount: number;
  listCount: number;
  onBack: () => void;
  onRestart: () => void;
}) {
  return (
    <div className="space-y-6">
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-sm text-brand-gray transition-colors hover:text-brand-primary"
      >
        <ArrowLeft className="h-4 w-4" /> Back to the board
      </button>

      {/* Confirmation, then straight into the map. */}
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <h2 className="flex items-center gap-2 text-base font-semibold text-emerald-900">
          <span className="grid h-6 w-6 place-items-center rounded-full bg-emerald-600">
            <Check className="h-3.5 w-3.5 text-white" />
          </span>
          {projectName} approved
        </h2>
        <p className="mt-1 text-xs text-emerald-900">
          {taskCount} tasks across {listCount} list{listCount === 1 ? "" : "s"}, recorded
          against this client. No ClickUp write is issued in this build.
        </p>
      </div>

      <div>
        <h3 className="text-xl font-semibold text-brand-ink">What happens next</h3>
        <p className="mt-1 max-w-3xl text-sm text-brand-gray">
          The rest of the onboarding, as Whitney described it. Two tracks run at the same
          time and converge at one gate.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          {(Object.keys(MATURITY) as Maturity[]).map((k) => (
            <span key={k} className="inline-flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${MATURITY[k].dot}`} aria-hidden />
              <span className="text-[11px] font-medium text-brand-secondary">
                {MATURITY[k].label}
              </span>
            </span>
          ))}
        </div>
      </div>

      {/* Stage 1 — before the split */}
      <StageCard stage={SIGNATURE} index={1} accent="border-emerald-200" />

      {/* The split */}
      <div className="flex items-center gap-3">
        <span className="h-px flex-1 bg-brand-mist" aria-hidden />
        <span className="rounded-full border border-brand-mist bg-white px-3 py-1 text-[11px] font-semibold text-brand-secondary">
          Two tracks, in parallel
        </span>
        <span className="h-px flex-1 bg-brand-mist" aria-hidden />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-brand-primary" aria-hidden />
            <h4 className="text-[13px] font-bold uppercase tracking-[0.08em] text-brand-ink">
              Ads track
            </h4>
            <span className="text-[11px] text-brand-gray">Whitney · Carmen · Jacqueline · Ivy</span>
          </div>
          <div className="space-y-0">
            {ADS_TRACK.map((stage, i) => (
              <div key={stage.id}>
                <StageCard stage={stage} index={i + 2} />
                {i < ADS_TRACK.length - 1 && <Rail label="then" tone="bg-brand-primary/40" />}
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-brand-teal" aria-hidden />
            <h4 className="text-[13px] font-bold uppercase tracking-[0.08em] text-brand-ink">
              LeadLock track
            </h4>
            <span className="text-[11px] text-brand-gray">Danielle · Tina</span>
          </div>
          <div className="space-y-0">
            {LEADLOCK_TRACK.map((stage, i) => (
              <div key={stage.id}>
                <StageCard stage={stage} index={i + 2} />
                {i < LEADLOCK_TRACK.length - 1 && <Rail label="then" tone="bg-brand-teal/50" />}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Convergence */}
      <div className="flex items-center gap-3">
        <span className="h-px flex-1 bg-brand-mist" aria-hidden />
        <span className="rounded-full bg-brand-ink px-3 py-1 text-[11px] font-semibold text-white">
          Both tracks meet here
        </span>
        <span className="h-px flex-1 bg-brand-mist" aria-hidden />
      </div>

      <StageCard stage={GATE} accent="border-amber-200" />
      <StageCard stage={RECURRING} accent="border-brand-stone" />

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-brand-mist bg-brand-surface p-4">
        <p className="min-w-0 flex-1 text-xs text-brand-gray">
          This map is the sequence, not a working build. Only the ClickUp step is
          demoable today.
        </p>
        <button
          onClick={onRestart}
          className="inline-flex items-center gap-1.5 rounded-lg border border-brand-primary px-3 py-2 text-xs font-semibold text-brand-primary"
        >
          <RotateCw className="h-3.5 w-3.5" /> Run the walkthrough again
        </button>
        <button
          onClick={onBack}
          className="rounded-lg bg-brand-ink px-3 py-2 text-xs font-semibold text-white"
        >
          Back to the board
        </button>
      </div>
    </div>
  );
}
