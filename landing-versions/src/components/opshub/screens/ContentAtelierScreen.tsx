/* ────────────────────────────────────────────────────────────────
   Content Atelier — WIA's own marketing.

   THE NAME. An atelier is a workshop where a small number of pieces are
   made properly, by hand, from good material — which is the argument this
   screen makes against pushing three scripts per call at a founder. It is
   also the word the wedding industry already uses for exactly that, so it
   arrives in the client's own vocabulary rather than in ours.

   SECONDARY BY DESIGN. This sits under SECONDARY in the nav because client
   fulfilment outranks WIA's own marketing every time. It is here because it
   is the one item tied directly to revenue — "we need more leads, we need
   more sales" — not because it is urgent.

   WHAT THE 21 SEPTEMBER HANDOVER CHANGED. The previous screen was built for
   a workspace holding one transcript: one moment, four candidate quotes,
   five drafts behind five tabs. The handover delivered roughly forty
   artifacts across seven platforms, including five chains where a source, the
   ChatGPT reasoning that shaped it and the published email or Instagram post
   all survive. Three things follow, and they are the three things this
   screen now does that the old one could not:

     1  A QUEUE WITH STATES, NOT A CARD GRID. Six moments, four of which
        cannot be worked at all — client calls are deleted out of Zoom and
        archived to Drive as VIDEO. A blocked row says what is missing and
        what would unblock it instead of sitting in the queue looking ready.

     2  PUBLISHED PRECEDENT AS ITS OWN VIEW. Five worked examples that
        already went out. One of them — Funktastic — is the only chain where
        the source TRANSCRIPT and the published output both survive, which
        makes it the one case the engine can be scored against rather than
        imitate. That is a benchmark, and it had nowhere to live before.

     3  CORPUS AND ACCESS, ON THE SCREEN THAT DEPENDS ON IT. A content engine
        blocked on speech-to-text is not a content problem, and the queue
        cannot explain itself without showing what access actually reaches.

   THE LOOP IS STILL THE PRODUCT. Whitney remains the selector: the hub
   surfaces moments, it does not push three scripts per call at an already
   inundated founder. The gates are unchanged in spirit and corrected in two
   places —

     · THE CTA IS HERS. "It doesn't have to come up with what the CTA is
       going to be — it can ask me." It was buried inside the draft text
       before; it is now a field a person sets, the engine never picks one,
       and nothing stages while it is empty.

     · EITHER FORMAT MAY LEAD. The old screen hard-wired the reel as the
       thing that unlocks everything else. Her process: "either have it give
       me a script for reels first, or we work on a marketing email first."
       So the lead is a choice, and the rest derive from whichever she
       approved.

   And the pack is the pack she asked for — one email, THREE reel scripts,
   one carousel, captions for all of it — not one draft per format behind a
   row of tabs, which is a different deliverable.
   ──────────────────────────────────────────────────────────────── */

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Lock, Mic, Quote } from "lucide-react";
import {
  ACCESS_META,
  ASSET_META,
  CANDIDATES,
  CHAT_COUNT,
  CLEARANCE_QUESTION,
  CORPUS_ORDER,
  COVERAGE,
  CTA_OPTIONS,
  HOLDING_META,
  MOMENTS,
  PACK_SPEC,
  PLATFORM_META,
  PRECEDENT,
  QUEUE_META,
  READABLE,
  STEERS,
  TRANSCRIPTION_GAP,
  UNREADABLE,
  alternatesOf,
  assetById,
  corpusFor,
  derivedOf,
  leadCandidates,
  momentById,
  packOf,
  type Moment,
  type PackAsset,
  type PlatformKey,
} from "@/data/contentAtelier";
import type { OpsHub } from "@/hooks/useOpsHub";
import { cn } from "@/lib/utils";
import type { ActionSpec } from "../primitives";
import {
  Actions,
  AutoBadge,
  DraftBlock,
  Empty,
  Panel,
  Pill,
  SectionLabel,
  Tabs,
} from "../primitives";

const VIEWS: [string, string][] = [
  ["queue", "Queue"],
  ["precedent", "Published precedent"],
  ["corpus", "Corpus & access"],
];

/* ── Local bits ───────────────────────────────────────────────────
   SourceChip in primitives only speaks SourceKey, and this screen carries
   four platforms that key does not cover — ChatGPT, Instagram, OpenRouter
   and the transcription capability nobody has bought. Same visual grammar,
   wider vocabulary. */

function PlatformChip({
  platform,
  label,
  className,
}: {
  platform: PlatformKey;
  label?: string;
  className?: string;
}) {
  const meta = PLATFORM_META[platform];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border border-brand-mist bg-white px-2 py-[3px] text-[10.5px] font-bold uppercase tracking-[0.06em]",
        className,
      )}
      style={{ color: meta.color }}
    >
      <span
        className="h-[5px] w-[5px] flex-none rounded-full"
        style={{ background: meta.color }}
        aria-hidden
      />
      {label ?? meta.label}
    </span>
  );
}

/* ════════════════════════════════════════════════════════════════
   THE SCREEN
   ════════════════════════════════════════════════════════════════ */

export function ContentAtelierScreen({ hub }: { hub: OpsHub }) {
  const { state, patch } = hub;

  return (
    <div className="space-y-5">
      <Tabs
        tabs={VIEWS}
        active={state.atelierView}
        onSelect={(id) => patch({ atelierView: id })}
      />
      {state.atelierView === "precedent" ? (
        <PrecedentView />
      ) : state.atelierView === "corpus" ? (
        <CorpusView />
      ) : (
        <QueueView hub={hub} />
      )}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   QUEUE
   ════════════════════════════════════════════════════════════════ */

function QueueView({ hub }: { hub: OpsHub }) {
  const { state, patch } = hub;
  const selected = momentById(state.contentId);
  const blocked = MOMENTS.filter((m) => m.state === "blocked").length;

  return (
    <>
      {/* WHAT LIMITS THIS QUEUE, ABOVE THE QUEUE. Not a KPI row — the
          numbers are a constraint, not a scoreboard, so they read as a
          sentence with the figures set in the queue's own type. */}
      <Panel>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <SectionLabel>What the engine can read</SectionLabel>
            <p className="mt-2 max-w-[60ch] text-[13px] leading-relaxed text-brand-secondary">
              <span className="font-bold text-brand-ink">{READABLE}</span> sources
              are text the engine can work on today — two voice documents, the WLF
              strategy, the workshop transcripts, the Miss Lyss case study and{" "}
              {CHAT_COUNT} ChatGPT chats.{" "}
              <span className="font-bold text-console-warn">{UNREADABLE}</span> more
              are video sitting in Drive with nothing beside them.
            </p>
            <p className="mt-2.5 max-w-[60ch] text-[11.5px] leading-snug text-brand-gray">
              {TRANSCRIPTION_GAP}
            </p>
          </div>
          <div className="flex flex-none flex-col items-end gap-2">
            <Pill tone={blocked ? "amber" : "green"}>
              {blocked} of {MOMENTS.length} blocked
            </Pill>
            <PlatformChip platform="stt" label="Transcription · not granted" />
          </div>
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-[330px_minmax(0,1fr)]">
        {/* ── the queue itself ─────────────────────────────────── */}
        <div className="space-y-2.5 lg:sticky lg:top-4 lg:self-start">
          {MOMENTS.map((m) => {
            const on = m.id === selected.id;
            const meta = QUEUE_META[m.state];
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => patch({ contentId: m.id })}
                className={cn(
                  "w-full rounded-xl border p-3.5 text-left transition-colors",
                  on
                    ? "border-brand-primary bg-brand-primary/[0.06] ring-1 ring-brand-primary/25"
                    : m.state === "blocked"
                      ? "border-brand-mist bg-brand-surface hover:border-brand-stone"
                      : "border-brand-mist bg-white hover:border-brand-stone",
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[12.5px] font-bold text-brand-ink">
                    {m.client}
                  </span>
                  <Pill tone={meta.tone} className="ml-auto">
                    {meta.label}
                  </Pill>
                </div>
                <p className="mt-0.5 text-[11.5px] leading-snug text-brand-gray">
                  {m.kind} · {m.meeting}
                </p>
                <div className="mt-2.5 flex flex-wrap gap-1.5">
                  {m.origin.map((o) => (
                    <PlatformChip
                      key={`${m.id}-${o.platform}-${o.label}`}
                      platform={o.platform}
                      label={`${PLATFORM_META[o.platform].label} · ${HOLDING_META[o.held].label}`}
                    />
                  ))}
                </div>
              </button>
            );
          })}
        </div>

        {/* ── the working pane ─────────────────────────────────── */}
        <div className="space-y-5">
          <MomentSource moment={selected} />
          {selected.state === "blocked" ? (
            <BlockedPane moment={selected} />
          ) : selected.state === "ready" ? (
            <ReadyPane moment={selected} />
          ) : (
            <WorkPane hub={hub} moment={selected} />
          )}
        </div>
      </div>
    </>
  );
}

/* ── What we hold, before anything is claimed about it ──────────── */

function MomentSource({ moment }: { moment: Moment }) {
  return (
    <Panel
      title={moment.meeting}
      subtitle={`${moment.client} · ${moment.when}`}
      right={<Pill tone={QUEUE_META[moment.state].tone}>{QUEUE_META[moment.state].label}</Pill>}
    >
      <div className="flex flex-wrap gap-1.5">
        {moment.origin.map((o) => (
          <PlatformChip
            key={`${o.platform}-${o.label}`}
            platform={o.platform}
            label={`${PLATFORM_META[o.platform].label} · ${o.label}`}
          />
        ))}
        <Pill tone={moment.claimSourced ? "green" : "amber"}>
          {moment.claimSourced ? "Quotable — text held" : "Paraphrase — not quotable"}
        </Pill>
      </div>

      <p className="mt-3 flex gap-2 text-[13px] italic leading-snug text-brand-secondary">
        <Quote className="mt-1 h-3.5 w-3.5 flex-none text-brand-slate" aria-hidden />
        <span>
          {moment.claim}
          {moment.ts && (
            <span className="ml-2 rounded bg-brand-ink px-1.5 py-0.5 align-middle text-[10px] font-bold not-italic tabular-nums text-white">
              {moment.ts}
            </span>
          )}
        </span>
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {moment.signals.map((s) => (
          <Pill key={s} tone="violet">
            {s}
          </Pill>
        ))}
        <span className="ml-auto text-[11px] text-brand-gray">
          Suggests · {moment.suggests}
        </span>
      </div>
    </Panel>
  );
}

/* ── Blocked: name the missing thing, not the status ────────────── */

function BlockedPane({ moment }: { moment: Moment }) {
  return (
    <Panel
      title="Nothing is drafted from this"
      subtitle="And nothing will be, until the source can be read"
      right={<Pill tone="amber">Blocked</Pill>}
    >
      <p className="flex items-start gap-2.5 rounded-xl border border-console-warn/30 bg-console-warn/[0.06] p-4 text-[12.5px] leading-snug text-brand-secondary">
        <AlertTriangle className="mt-px h-4 w-4 flex-none text-console-warn" aria-hidden />
        <span>{moment.blockedBy}</span>
      </p>

      <SectionLabel className="mt-4">What would unblock it</SectionLabel>
      <ul className="mt-2 space-y-1.5">
        {[
          "A speech-to-text provider on the account — the one capability the access handover did not cover.",
          moment.origin.some((o) => o.platform === "fathom")
            ? "A Fathom API key, or the same session exported to Drive alongside the Google Ads recordings."
            : "Or the Zoom-side transcript, if Carmen's cloud recording kept one before the client meeting was deleted.",
        ].map((t) => (
          <li
            key={t}
            className="flex items-start gap-2 text-[12.5px] leading-snug text-brand-secondary"
          >
            <span
              className="mt-[7px] h-1.5 w-1.5 flex-none rounded-full bg-console-warn"
              aria-hidden
            />
            {t}
          </li>
        ))}
      </ul>

      <p className="mt-4 text-[11.5px] leading-snug text-brand-gray">
        The claim on this card is the handover note's own wording, not the
        client's. Drafting a result post from a paraphrase puts words in a named
        client's mouth, which is the one failure mode this queue exists to
        prevent.
      </p>
    </Panel>
  );
}

/* ── Ready: readable, and deliberately not drafted yet ──────────── */

function ReadyPane({ moment }: { moment: Moment }) {
  return (
    <Panel
      title="Readable, not yet drafted"
      subtitle="The transcript is held — this one is a scheduling decision, not a blocker"
      right={<Pill tone="green">Ready</Pill>}
    >
      <p className="rounded-xl border border-brand-mist bg-brand-surface p-4 text-[12.5px] leading-snug text-brand-secondary">
        Two marketing emails already went out from this session, so the voice
        work is done and the angle is proven. What has never been made from it
        is a reel, a carousel or a caption set — which is the whole argument for
        the pack: the same source, worked into the formats nobody had time for.
      </p>
      <p className="mt-3 text-[11.5px] leading-snug text-brand-gray">
        Nothing is drafted here on purpose. Accepting a candidate from{" "}
        {moment.client} would put a second pack in front of Whitney before the
        first has been through her, and the queue is meant to surface one
        decision at a time.
      </p>
    </Panel>
  );
}

/* ════════════════════════════════════════════════════════════════
   THE WORKING LOOP — candidates → steer + CTA → lead → pack
   ════════════════════════════════════════════════════════════════ */

function WorkPane({ hub, moment }: { hub: OpsHub; moment: Moment }) {
  const {
    state,
    setCandidate,
    setSteer,
    setScript,
    setCta,
    setLeadAsset,
    setClearance,
    stageContent,
    toast,
  } = hub;

  const candidates = CANDIDATES[moment.id] ?? [];
  const drafted = candidates.find((c) => c.isDrafted);
  const acceptedDrafted =
    drafted && state.candidateState[drafted.id] === "accepted";

  const steerSpec = STEERS[moment.id];
  const steer = state.steerDraft[moment.id] ?? steerSpec?.transcript ?? "";
  const cta = state.contentCta[moment.id] ?? "";
  const ctaOption = CTA_OPTIONS.find((c) => c.id === cta);

  const pack = packOf(moment.id);
  const leadId = state.leadAsset[moment.id] ?? pack.find((a) => a.canLead)?.id ?? "";
  const lead = assetById(moment.id, leadId);
  const leadApproved = state.scriptState[moment.id] === "approved";

  const open = assetById(moment.id, state.contentTab) ?? lead;
  const isLead = open?.id === leadId;
  const isAlternate =
    !!open && !isLead && !!lead && open.kind === lead.kind;
  const locked = !leadApproved && !isLead && !isAlternate;

  const cleared = Boolean(state.clearance[`${moment.id}:${open?.id}`]);
  const staged = state.contentStage[`${moment.id}:${open?.id}`];

  /* Copy is the only action here that does real work — every other button in
     this screen is a demo no-op, so this one has to actually succeed or
     actually say why it did not. */
  const [copied, setCopied] = useState(false);
  const copyTimer = useRef<number | null>(null);

  useEffect(() => {
    setCopied(false);
    return () => {
      if (copyTimer.current !== null) window.clearTimeout(copyTimer.current);
    };
  }, [moment.id, state.contentTab]);

  const copyDraft = async () => {
    try {
      await navigator.clipboard.writeText(open?.body ?? "");
    } catch {
      toast("Clipboard blocked by the browser — select the draft and copy manually");
      return;
    }
    setCopied(true);
    if (copyTimer.current !== null) window.clearTimeout(copyTimer.current);
    copyTimer.current = window.setTimeout(() => setCopied(false), 1800);
  };

  const copyAction: ActionSpec = {
    label: copied ? "Copied" : "Copy draft",
    variant: copied ? "done" : "secondary",
    onClick: () => void copyDraft(),
  };

  return (
    <>
      {/* ── GATE 1 · CANDIDATES (MC-01) ─────────────────────────── */}
      <Panel
        title="Candidates in this transcript"
        subtitle="Accept or reject each one"
        right={<AutoBadge system="human" />}
      >
        <div className="space-y-2.5">
          {candidates.map((c) => {
            const decision = state.candidateState[c.id];
            return (
              <div
                key={c.id}
                className={cn(
                  "rounded-xl border p-3.5",
                  decision === "accepted"
                    ? "border-console-good/40 bg-console-good/[0.05]"
                    : decision === "rejected"
                      ? "border-brand-mist bg-brand-mist/25 opacity-60"
                      : "border-brand-mist bg-white",
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded bg-brand-ink px-1.5 py-0.5 text-[10px] font-bold tabular-nums text-white">
                    {c.ts}
                  </span>
                  {c.isDrafted && <Pill tone="blue">Pack drafted from this</Pill>}
                  {decision && (
                    <Pill
                      tone={decision === "accepted" ? "green" : "slate"}
                      className="ml-auto"
                    >
                      {decision === "accepted" ? "Accepted" : "Rejected"}
                    </Pill>
                  )}
                </div>
                <p className="mt-2 text-[12.5px] italic leading-snug text-brand-secondary">
                  {c.quote}
                </p>
                <p className="mt-1 text-[11.5px] leading-snug text-brand-gray">{c.why}</p>
                {!decision && (
                  <div className="mt-2.5">
                    <Actions
                      actions={[
                        {
                          label: "Accept",
                          variant: "primary",
                          onClick: () =>
                            setCandidate(
                              c.id,
                              "accepted",
                              c.isDrafted
                                ? "Accepted — the steer is now editable"
                                : "Accepted. No pack drafted for this moment yet.",
                            ),
                        },
                        {
                          label: "Reject",
                          variant: "ghost",
                          onClick: () =>
                            setCandidate(c.id, "rejected", "Rejected — nothing is drafted from it"),
                        },
                      ]}
                    />
                  </div>
                )}
                {decision && (
                  <button
                    type="button"
                    onClick={() =>
                      setCandidate(
                        c.id,
                        decision === "accepted" ? "rejected" : "accepted",
                        "Decision changed",
                      )
                    }
                    className="mt-2 text-[11.5px] font-bold text-brand-primary underline underline-offset-2"
                  >
                    Change decision
                  </button>
                )}
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-[11.5px] leading-snug text-brand-gray">
          Four moments out of one session. The other five sessions in the queue
          produce no candidates at all, because a candidate is a quote and a
          quote needs text.
        </p>
      </Panel>

      {/* ── GATE 2 · THE STEER AND THE CTA (MC-02) ──────────────── */}
      {steerSpec && (
        <Panel
          title="Whitney's steer"
          subtitle="The angle and the call to action, both supplied by a person"
          right={<AutoBadge system="human" />}
        >
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone="blue">
              <Mic className="mr-1 inline h-3 w-3" aria-hidden />
              {steerSpec.captured}
            </Pill>
            {/* PROVENANCE, STATED. Still no recording or transcription of one
                anywhere in the workspace, including in the 21 September
                handover — so this stays illustrative and says so. */}
            <Pill tone={steerSpec.sourced ? "green" : "amber"}>
              {steerSpec.sourced
                ? "Transcribed from the recording"
                : "Illustrative — no recording supplied"}
            </Pill>
          </div>

          {!acceptedDrafted ? (
            <p className="mt-3 flex items-start gap-2 rounded-xl border border-brand-mist bg-brand-surface p-3.5 text-[12px] leading-snug text-brand-gray">
              <Lock className="mt-px h-4 w-4 flex-none" aria-hidden />
              Accept the {drafted?.ts} candidate above to open the steer.
            </p>
          ) : (
            <>
              <label className="sr-only" htmlFor="steer">
                Steer for this moment
              </label>
              <textarea
                id="steer"
                value={steer}
                onChange={(e) => setSteer(moment.id, e.target.value)}
                rows={6}
                className="mt-3 w-full rounded-xl border border-brand-mist bg-white p-3.5 text-[12.5px] leading-relaxed text-brand-ink focus:border-brand-primary focus:outline-none"
              />
              <p className="mt-2 text-[11.5px] text-brand-gray">
                In production this field is filled by transcribing a voice note.
              </p>

              {/* THE CTA. Her one explicit instruction on 16 September, and
                  the thing the old screen buried inside the email body. */}
              <SectionLabel className="mt-5">
                Call to action — the engine will not choose one
              </SectionLabel>
              <div className="mt-2 flex flex-wrap gap-2">
                {CTA_OPTIONS.map((o) => {
                  const on = o.id === cta;
                  return (
                    <button
                      key={o.id}
                      type="button"
                      onClick={() =>
                        setCta(
                          moment.id,
                          on ? "" : o.id,
                          on ? "CTA cleared — the pack cannot stage without one" : `CTA set · ${o.label}`,
                        )
                      }
                      className={cn(
                        "rounded-lg border px-3 py-2 text-left text-[12px] transition-colors",
                        on
                          ? "border-brand-primary bg-brand-primary/[0.08] font-bold text-brand-primary"
                          : "border-brand-mist bg-white font-medium text-brand-secondary hover:border-brand-stone",
                      )}
                    >
                      {o.label}
                      <span className="mt-0.5 block text-[10.5px] font-medium uppercase tracking-[0.06em] text-brand-slate">
                        {o.track}
                      </span>
                    </button>
                  );
                })}
              </div>
              {ctaOption ? (
                <p className="mt-2.5 text-[11.5px] leading-snug text-brand-gray">
                  {ctaOption.destination ? (
                    <>Destination · {ctaOption.destination}</>
                  ) : (
                    <span className="text-console-warn">
                      No destination URL supplied for this offer. The link is an
                      outstanding ask, not something the engine can fill in.
                    </span>
                  )}
                </p>
              ) : (
                <p className="mt-2.5 text-[11.5px] leading-snug text-console-warn">
                  Not set. Every draft below stays unstageable until a person
                  picks one.
                </p>
              )}

              <SectionLabel className="mt-5">Applied to the drafts</SectionLabel>
              <ul className="mt-2 space-y-1">
                {steerSpec.applied.map((a) => (
                  <li
                    key={a}
                    className="flex items-start gap-2 text-[12.5px] leading-snug text-brand-secondary"
                  >
                    <span
                      className="mt-[6px] h-1.5 w-1.5 flex-none rounded-full bg-brand-primary"
                      aria-hidden
                    />
                    {a}
                  </li>
                ))}
              </ul>
              <div className="mt-4">
                <Actions
                  actions={[
                    {
                      label: "Re-draft from this steer",
                      variant: "secondary",
                      onClick: () => toast("Re-drafting is not implemented in this build"),
                    },
                  ]}
                />
              </div>
            </>
          )}
        </Panel>
      )}

      {/* ── GATE 3 · THE LEAD ASSET ─────────────────────────────── */}
      {acceptedDrafted && lead && (
        <Panel
          title="The lead asset"
          subtitle="Whichever one she starts from. Approving it unlocks the rest"
          right={
            <Pill tone={leadApproved ? "green" : "amber"}>
              {leadApproved ? "Approved" : "Awaiting approval"}
            </Pill>
          }
        >
          <div className="flex flex-wrap gap-2">
            {leadCandidates(moment.id).map((a) => {
              const on = a.id === leadId;
              return (
                <button
                  key={a.id}
                  type="button"
                  onClick={() =>
                    !on &&
                    setLeadAsset(
                      moment.id,
                      a.id,
                      `Lead set to ${a.label} — approval resets, because the rest derive from it`,
                    )
                  }
                  className={cn(
                    "rounded-lg border px-3 py-2 text-left text-[12px] transition-colors",
                    on
                      ? "border-brand-primary bg-brand-primary/[0.08] font-bold text-brand-primary"
                      : "border-brand-mist bg-white font-medium text-brand-secondary hover:border-brand-stone",
                  )}
                >
                  {a.label}
                  {a.angle && (
                    <span className="mt-0.5 block text-[10.5px] font-medium normal-case text-brand-slate">
                      {a.angle}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="mt-4">
            <Actions
              actions={
                leadApproved
                  ? [
                      {
                        label: "Withdraw approval",
                        variant: "ghost",
                        onClick: () =>
                          setScript(moment.id, "draft", "Approval withdrawn — derived formats lock again"),
                      },
                    ]
                  : [
                      {
                        label: `Approve ${lead.label}`,
                        variant: "primary",
                        onClick: () =>
                          setScript(
                            moment.id,
                            "approved",
                            `${lead.label} approved — the derived formats unlock`,
                          ),
                      },
                    ]
              }
            />
          </div>

          <p className="mt-3 text-[11.5px] leading-snug text-brand-gray">
            Three reel scripts is the spec, not three attempts at one script —
            each takes a different claim from the same session, so picking one
            is a choice about angle rather than about quality.
          </p>
        </Panel>
      )}

      {/* ── GATE 4 · THE PACK (MC-03 / MC-04) ───────────────────── */}
      {acceptedDrafted && lead && (
        <Panel
          title="The pack"
          subtitle={PACK_SPEC}
          right={
            <Pill tone={leadApproved ? "blue" : "slate"}>
              {leadApproved ? "Open" : "Derived formats locked"}
            </Pill>
          }
          bodyClassName="px-5 py-4"
        >
          <PackStrip
            hub={hub}
            moment={moment}
            pack={pack}
            leadId={leadId}
            leadApproved={leadApproved}
            openId={open?.id ?? ""}
          />

          {locked ? (
            <p className="mt-4 flex items-start gap-2 rounded-xl border border-brand-mist bg-brand-surface p-4 text-[12.5px] leading-snug text-brand-secondary">
              <Lock className="mt-px h-4 w-4 flex-none text-brand-slate" aria-hidden />
              <span>
                Written from the approved {lead.label}. Approve the lead above
                to open this one.
              </span>
            </p>
          ) : open ? (
            <div className="mt-4">
              <div className="mb-2.5 flex flex-wrap items-center gap-2">
                <Pill tone={ASSET_META[open.kind].tone}>{ASSET_META[open.kind].label}</Pill>
                {isLead && <Pill tone="navy">Lead</Pill>}
                {isAlternate && <Pill tone="slate">Alternate angle</Pill>}
                {!isLead && !isAlternate && (
                  <Pill tone="violet">Derived from {lead.label}</Pill>
                )}
                {open.angle && (
                  <span className="text-[11.5px] text-brand-gray">{open.angle}</span>
                )}
                <AutoBadge system="ai_assisted" />
              </div>

              <DraftBlock text={open.body} />

              {open.handling && (
                <p className="mt-3 flex items-start gap-2 text-[11.5px] leading-snug text-console-warn">
                  <AlertTriangle className="mt-px h-3.5 w-3.5 flex-none" aria-hidden />
                  {open.handling}
                </p>
              )}

              {/* PUBLICATION PERMISSION, AT THE HANDOFF. The Vault session
                  walks real client analytics on screen, so clearance is a gate
                  on every format leaving here, not a footnote on the case
                  study. */}
              <label className="mt-4 flex cursor-pointer items-start gap-2.5 rounded-xl border border-console-warn/30 bg-console-warn/[0.06] p-3.5">
                <input
                  type="checkbox"
                  id={`clearance-${moment.id}-${open.id}`}
                  checked={cleared}
                  onChange={(e) => setClearance(`${moment.id}:${open.id}`, e.target.checked)}
                  className="mt-0.5 h-4 w-4 flex-none accent-[#5070ff]"
                />
                <span className="text-[11.5px] leading-snug text-console-warn">
                  <span className="font-bold">Clearance · </span>
                  No client named or identifiable, no legible analytics, every
                  claim traced to a timestamp.
                </span>
              </label>

              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  {staged && <Pill tone="green">Staged for review</Pill>}
                  <Actions
                    actions={
                      staged
                        ? [copyAction]
                        : [
                            {
                              label: "Stage for review",
                              variant: "primary",
                              disabled: !cleared || !cta,
                              onClick: () =>
                                cleared &&
                                cta &&
                                stageContent(
                                  `${moment.id}:${open.id}`,
                                  "staged",
                                  "Staged for Whitney’s review — nothing is published",
                                ),
                            },
                            copyAction,
                            {
                              label: "Regenerate",
                              variant: "secondary",
                              onClick: () => toast("Regeneration is out of scope for this demo"),
                            },
                          ]
                    }
                  />
                  {!staged && (!cleared || !cta) && (
                    <span className="text-[11.5px] text-console-warn">
                      {!cta && !cleared
                        ? "Needs a CTA and clearance"
                        : !cta
                          ? "Needs a CTA"
                          : "Needs clearance"}
                    </span>
                  )}
                </div>
                <SectionLabel>No publish path exists in this build</SectionLabel>
              </div>
            </div>
          ) : (
            <Empty>No draft for this format.</Empty>
          )}

          <p className="mt-4 text-[11.5px] leading-snug text-brand-gray">
            Copy only — no Canva render, no narration, no generated likeness.
            Design stays with Ivy, on-camera with Whitney and Tina.{" "}
            {CLEARANCE_QUESTION}
          </p>
        </Panel>
      )}
    </>
  );
}

/* ── The pack at a glance ─────────────────────────────────────────
   The spec is 1 + 3 + 1 + captions, and a row of five equal tabs hid that
   shape entirely. This strip groups by format and carries each asset's own
   state, so the deliverable is legible before anything is opened. */

function PackStrip({
  hub,
  moment,
  pack,
  leadId,
  leadApproved,
  openId,
}: {
  hub: OpsHub;
  moment: Moment;
  pack: PackAsset[];
  leadId: string;
  leadApproved: boolean;
  openId: string;
}) {
  const { state, patch } = hub;
  const alternates = alternatesOf(moment.id, leadId).map((a) => a.id);
  const derived = derivedOf(moment.id, leadId).map((a) => a.id);

  return (
    <div className="flex flex-wrap gap-1.5">
      {pack.map((a) => {
        const on = a.id === openId;
        const isLead = a.id === leadId;
        const isAlt = alternates.includes(a.id);
        const isLocked = !leadApproved && derived.includes(a.id);
        const staged = Boolean(state.contentStage[`${moment.id}:${a.id}`]);
        return (
          <button
            key={a.id}
            type="button"
            onClick={() => patch({ contentTab: a.id })}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11.5px] font-bold transition-colors",
              on
                ? "border-brand-primary bg-brand-primary text-white"
                : isLocked
                  ? "border-brand-mist bg-brand-surface text-brand-gray hover:border-brand-stone"
                  : "border-brand-mist bg-white text-brand-secondary hover:border-brand-stone",
            )}
          >
            {isLocked && <Lock className="h-3 w-3 flex-none" aria-hidden />}
            {staged && (
              <CheckCircle2
                className={cn("h-3 w-3 flex-none", on ? "text-white" : "text-console-good")}
                aria-hidden
              />
            )}
            {a.label}
            {isLead && (
              <span
                className={cn(
                  "rounded px-1 py-px text-[9.5px] uppercase tracking-[0.06em]",
                  on ? "bg-white/25 text-white" : "bg-brand-ink text-white",
                )}
              >
                Lead
              </span>
            )}
            {isAlt && !on && (
              <span className="rounded bg-brand-mist px-1 py-px text-[9.5px] uppercase tracking-[0.06em] text-brand-gray">
                Alt
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   PUBLISHED PRECEDENT
   ════════════════════════════════════════════════════════════════ */

function PrecedentView() {
  const benchmark = PRECEDENT.filter((p) => p.benchmark);
  const rest = PRECEDENT.filter((p) => !p.benchmark);

  return (
    <div className="space-y-5">
      <Panel>
        <SectionLabel>Why these are on screen</SectionLabel>
        <p className="mt-2 max-w-[68ch] text-[13px] leading-relaxed text-brand-secondary">
          Five chains that already went out, each with the source it came from
          and the ChatGPT conversation that shaped it. They are the voice
          reference — not a style guide describing the voice, but the voice
          doing the job, with the reasoning attached.
        </p>
        <p className="mt-2 max-w-[68ch] text-[12px] leading-snug text-brand-gray">
          One of them is different in kind. Read on.
        </p>
      </Panel>

      {benchmark.map((p) => (
        <ChainCard key={p.id} chain={p} />
      ))}

      <SectionLabel>The other four — voice reference</SectionLabel>
      <div className="grid gap-4 xl:grid-cols-2">
        {rest.map((p) => (
          <ChainCard key={p.id} chain={p} />
        ))}
      </div>
    </div>
  );
}

function ChainCard({ chain }: { chain: (typeof PRECEDENT)[number] }) {
  return (
    <Panel
      title={chain.title}
      subtitle={chain.client}
      right={
        chain.benchmark ? (
          <Pill tone="navy">Benchmark — scorable</Pill>
        ) : (
          <Pill tone="slate">{chain.published.length} published</Pill>
        )
      }
      className={chain.benchmark ? "ring-1 ring-brand-primary/25" : undefined}
    >
      <p className="text-[12.5px] leading-snug text-brand-secondary">{chain.teaches}</p>

      <div className="mt-4 space-y-3">
        {(
          [
            ["Source", chain.source.map((s) => ({ platform: s.platform, label: `${s.label} · ${HOLDING_META[s.held].label}` }))],
            ["Reasoning", chain.reasoning.map((r) => ({ platform: "chatgpt" as PlatformKey, label: r.label }))],
            ["Published", chain.published.map((p) => ({ platform: p.platform, label: p.label }))],
          ] as const
        ).map(([label, items]) => (
          <div key={label}>
            <SectionLabel>{label}</SectionLabel>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {items.length ? (
                items.map((i) => (
                  <PlatformChip
                    key={`${label}-${i.label}`}
                    platform={i.platform}
                    label={i.label}
                  />
                ))
              ) : (
                <span className="text-[11.5px] text-brand-gray">Nothing supplied</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {chain.caveat && (
        <p className="mt-4 flex items-start gap-2 rounded-xl border border-console-warn/30 bg-console-warn/[0.06] p-3 text-[11.5px] leading-snug text-console-warn">
          <AlertTriangle className="mt-px h-3.5 w-3.5 flex-none" aria-hidden />
          {chain.caveat}
        </p>
      )}

      {chain.benchmark && (
        <p className="mt-4 rounded-xl border border-brand-primary/25 bg-brand-primary/[0.05] p-3.5 text-[12px] leading-snug text-brand-secondary">
          <span className="font-bold text-brand-ink">Use it as a test, not a sample. </span>
          Run the engine on the transcript, compare what comes out against the
          four assets that actually went out, and the difference is a measurement
          rather than an opinion. It is the only chain in the corpus where that
          is possible, which makes it the acceptance test for MC-02 and MC-03.
        </p>
      )}
    </Panel>
  );
}

/* ════════════════════════════════════════════════════════════════
   CORPUS & ACCESS
   ════════════════════════════════════════════════════════════════ */

function CorpusView() {
  return (
    <div className="space-y-5">
      <Panel
        title="What the access handover reaches"
        subtitle="Grouped by the platform it lives on, because that is how access is granted and how it breaks"
        right={<AutoBadge system="validation" />}
      >
        <div className="space-y-2.5">
          {COVERAGE.map((row) => {
            const meta = ACCESS_META[row.state];
            return (
              <div
                key={row.platform}
                className={cn(
                  "rounded-xl border p-3.5",
                  row.state === "missing"
                    ? "border-console-bad/30 bg-console-bad/[0.04]"
                    : row.state === "partial"
                      ? "border-console-warn/30 bg-console-warn/[0.04]"
                      : "border-brand-mist bg-white",
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <PlatformChip platform={row.platform} />
                  <Pill tone={meta.tone} className="ml-auto">
                    {meta.label}
                  </Pill>
                </div>
                <p className="mt-2 text-[12.5px] leading-snug text-brand-ink">
                  <span className="font-bold">Granted · </span>
                  {row.granted}
                </p>
                <p className="mt-1 text-[12px] leading-snug text-brand-secondary">
                  <span className="font-bold">Reaches · </span>
                  {row.reaches}
                </p>
                {row.gap && (
                  <p className="mt-1.5 flex items-start gap-1.5 text-[11.5px] leading-snug text-console-warn">
                    <AlertTriangle className="mt-px h-3.5 w-3.5 flex-none" aria-hidden />
                    {row.gap}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel
        title="The corpus"
        subtitle={`${READABLE} sources the engine can read · ${UNREADABLE} it cannot`}
      >
        <div className="space-y-5">
          {CORPUS_ORDER.map((platform) => {
            const items = corpusFor(platform);
            if (!items.length) return null;
            return (
              <div key={platform}>
                <div className="flex items-center gap-2 border-b border-brand-mist pb-2">
                  <PlatformChip platform={platform} />
                  <span className="text-[11px] tabular-nums text-brand-gray">
                    {items.length} {items.length === 1 ? "item" : "items"}
                  </span>
                </div>
                <ul className="mt-1">
                  {items.map((c) => (
                    <li
                      key={c.id}
                      className="flex flex-wrap items-baseline gap-x-2 gap-y-1 border-b border-brand-mist/60 py-2 last:border-b-0"
                    >
                      <span className="text-[12.5px] font-medium text-brand-ink">
                        {c.title}
                      </span>
                      {c.when && (
                        <span className="text-[11px] tabular-nums text-brand-gray">
                          {c.when}
                        </span>
                      )}
                      <Pill tone={HOLDING_META[c.held].tone} className="ml-auto">
                        {HOLDING_META[c.held].label}
                      </Pill>
                      {c.note && (
                        <p className="w-full text-[11.5px] leading-snug text-brand-gray">
                          {c.note}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      </Panel>
    </div>
  );
}
