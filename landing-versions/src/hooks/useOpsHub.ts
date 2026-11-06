/* ────────────────────────────────────────────────────────────────
   useOpsHub — the whole hub's state machine.

   One reducer-shaped hook rather than per-screen state, for one reason: the
   counts are cross-screen. Approving an email on Inbox has to move the Home
   KPI, the nav badge, the Ops Watch chase and the Client Hub commitment in
   the same render. Splitting state per screen would make that a
   synchronisation problem instead of a derivation.

   ONE LIFECYCLE, NOT FOUR. Every screen reads `stageOf(obligationId)` (see
   data/obligations.ts and WORK_STAGES in lib/opsHub.ts). The corrections that
   model exists for:

     · approving a draft produces `draft_created`, NOT completed — a draft is
       not a sent email, so the row stays open until somebody records the send
     · posting a nudge is an EVENT on an open obligation, not its resolution;
       the unacknowledged count only falls on an actual acknowledgement
     · a parent obligation may not claim closure while one of its steps is
       open, so a delivery cannot look done while its client handoff sits in
       drafts — it names the step holding it up instead
     · the Client Hub commitment ledger and the account attention flags are
       derived from the same stages, so they move with everything else

   NOTHING HERE WRITES ANYWHERE. Every action mutates local state and raises
   a toast that says "simulated". There is no fetch, no /api call, no
   connector. That is the boundary of this build and it is deliberate — the
   same boundary the onboarding console draws at approval.
   ──────────────────────────────────────────────────────────────── */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  CLIENTS,
  EMAILS,
  accountFlags,
  accountNeedsAttention,
  INVALID_EMAILS,
  INVOICES,
  MEETINGS,
  OVERDUE_TASKS,
  QUEUES,
  TEAM_ACTIONS,
  packOutputs,
  type Meeting,
} from "@/data/opsHub";
import { OPEN_SIGNALS } from "@/data/contentAtelier";
import {
  CHILDREN_OF,
  COMPLETION_UPDATE_SCOPE,
  OBLIGATION_BY_COMMITMENT,
  OBLIGATION_BY_EMAIL,
  OBLIGATION_BY_INVOICE,
  OBLIGATION_BY_TEAM_ACTION,
  OBLIGATION_META,
  OBLIGATIONS,
} from "@/data/obligations";
import {
  DISPOSITION_STAGE,
  INITIAL_STATE,
  RESETTABLE,
  STAGE_META,
  STAGE_RANK,
  isAcknowledged,
  isOpenWork,
  type DrawerPayload,
  type EmailStatus,
  type MsgModalPayload,
  type ObligationEvent,
  type OpsHubState,
  type ScreenId,
  type WorkStage,
} from "@/lib/opsHub";

const PACK_IDS = ["bloom-strategy", "monday-team", "magnolia-sales"];

/* Which queues each reviewer owns. F03: switching the persona has to produce
   a distinct owned-work queue, not just a different name in the corner.
   Grounded in D1 @24:00–25:38 — Whitney stars and decides, Gisselle drafts,
   files and monitors team replies. */
export const REVIEWER_QUEUES: Record<"Whitney" | "Gisselle", string[]> = {
  Whitney: ["needs_whitney", "sales_followup"],
  Gisselle: [
    "ready_gisselle",
    "team_reply_due",
    "waiting_client",
    "finance_followup",
    "no_action",
  ],
};

export type OpsHubCounts = {
  needsReview: number;
  needsReviewSub: string;
  /** Per-destination breakdown so a KPI can open exactly what it counted. */
  needsReviewParts: { label: string; value: number; screen: ScreenId; extra?: Record<string, unknown> }[];
  clientComm: number;
  clientCommSub: string;
  clientCommParts: { label: string; value: number; screen: ScreenId; extra?: Record<string, unknown> }[];
  teamRisk: number;
  teamRiskSub: string;
  unacked: number;
  overdueTasks: number;
  inboxOpen: number;
  opsOpen: number;
  packsNeedingReview: number;
  invoicesOpen: number;
  invalidOpen: number;
  clientAttention: number;
  contentSignals: number;
  /** Everything the CURRENT reviewer still owes, across every queue. */
  myOpen: number;
};

export function useOpsHub() {
  const [state, setState] = useState<OpsHubState>(INITIAL_STATE);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* ── toast ─────────────────────────────────────────────────── */
  const toast = useCallback((msg: string) => {
    setState((s) => ({ ...s, toast: msg }));
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(
      () => setState((s) => ({ ...s, toast: null })),
      3200,
    );
  }, []);

  useEffect(() => {
    return () => {
      if (toastTimer.current) clearTimeout(toastTimer.current);
    };
  }, []);

  /* ── navigation ────────────────────────────────────────────── */
  const go = useCallback((screen: ScreenId, extra?: Record<string, unknown>) => {
    setState((s) => ({
      ...s,
      screen,
      paletteOpen: false,
      drawer: null,
      ...(screen === "clients" && !extra?.clientId ? { clientId: null } : {}),
      ...(screen === "meetings" && extra?.meetingId === undefined
        ? { meetingId: null }
        : {}),
      ...(extra as Partial<OpsHubState>),
    }));
  }, []);

  const patch = useCallback((next: Partial<OpsHubState>) => {
    setState((s) => ({ ...s, ...next }));
  }, []);

  /* ⌘K opens the palette; Escape closes every overlay. Bound at window
     level because the palette must be reachable from any screen without
     focus being inside a particular panel. */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setState((s) => ({ ...s, paletteOpen: !s.paletteOpen, paletteQ: "" }));
      }
      if (e.key === "Escape") {
        setState((s) => ({
          ...s,
          paletteOpen: false,
          drawer: null,
          msgModal: null,
          invoiceId: null,
        }));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  /* ── the lifecycle reader every screen goes through ────────── */

  const emailStatus = useCallback(
    (id: string): EmailStatus => state.emailState[id] ?? "open",
    [state.emailState],
  );

  /** One obligation's own stage, before any parent roll-up.

      Order of precedence: an explicit stage written by an action wins; then
      the stage implied by its email's disposition; then the seed. */
  const ownStage = useCallback(
    (obligationId: string): WorkStage => {
      const explicit = state.stages[obligationId];
      if (explicit) return explicit;
      const ob = OBLIGATION_META[obligationId];
      if (!ob) return "unread";
      const emailId = ob.links.emails?.[0];
      if (emailId && state.emailState[emailId]) {
        return DISPOSITION_STAGE[state.emailState[emailId]];
      }
      return ob.seed;
    },
    [state.stages, state.emailState],
  );

  /** The stage a screen shows.

      A parent normally reads its OWN stage — "is the delivery in progress?"
      is a fact about the delivery, not about its emails. The one thing it may
      not do is claim CLOSURE while a step is still open: a landing page is
      not delivered while the email carrying its link sits unsent in drafts.
      In that case the parent falls back to its least advanced open step, so
      the screen names the thing that is actually holding it up. */
  const stageOf = useCallback(
    (obligationId: string): WorkStage => {
      const mine = ownStage(obligationId);
      const kids = CHILDREN_OF[obligationId];
      if (!kids?.length) return mine;
      if (!STAGE_META[mine].closed) return mine;
      const openKids = kids.map(ownStage).filter((k) => !STAGE_META[k].closed);
      if (!openKids.length) return mine;
      return openKids.reduce((a, b) => (STAGE_RANK[a] <= STAGE_RANK[b] ? a : b));
    },
    [ownStage],
  );

  const obligationOfEmail = useCallback(
    (emailId: string) => OBLIGATION_BY_EMAIL[emailId] ?? "",
    [],
  );

  const emailStage = useCallback(
    (id: string): WorkStage => {
      const ob = OBLIGATION_BY_EMAIL[id];
      /* The email row shows its OWN step, not the parent roll-up: a reviewer
         acting on one message needs to see that message's state. The parent
         is shown beside it as context. */
      return ob ? ownStage(ob) : "unread";
    },
    [ownStage],
  );

  const eventsFor = useCallback(
    (obligationId: string): ObligationEvent[] => state.events[obligationId] ?? [],
    [state.events],
  );

  /* Which queue a row is in RIGHT NOW. `Email.queue` is only the seed value —
     once someone re-triages a row by hand the override is the truth. */
  const emailQueue = useCallback(
    (id: string) =>
      state.emailQueue[id] ?? EMAILS.find((e) => e.id === id)?.queue ?? "",
    [state.emailQueue],
  );

  const queueEmails = useCallback(
    (q: string) => EMAILS.filter((e) => emailQueue(e.id) === q),
    [emailQueue],
  );

  const isEmailOpen = useCallback(
    (id: string) => isOpenWork(emailStage(id)),
    [emailStage],
  );

  const queueOpen = useCallback(
    (q: string) => queueEmails(q).filter((e) => isEmailOpen(e.id)).length,
    [queueEmails, isEmailOpen],
  );

  /** The reviewer's own open work, across every queue they own. Home's
      "you are finished" message is allowed to appear only when this is 0. */
  const reviewerOpen = useCallback(
    (who: "Whitney" | "Gisselle") =>
      REVIEWER_QUEUES[who].reduce((n, q) => n + queueOpen(q), 0),
    [queueOpen],
  );

  /* ── meeting packs ─────────────────────────────────────────── */

  const packStatus = useCallback(
    (id: string) => state.packState[id] ?? "needs_review",
    [state.packState],
  );

  const meetingPackStatus = useCallback(
    (m: Meeting): "needs_source" | "executed" | "needs_review" | "approved" | "revision" => {
      if (m.exceptions && !state.packExceptions.transcript) return "needs_source";
      if (m.processed) return "executed";
      return packStatus(m.id);
    },
    [state.packExceptions, packStatus],
  );

  /** Per-output result. `pending` until the pack is released; then each
      output carries its OWN outcome, because a pack in which every dispatch
      always succeeds teaches nobody what a failed Slack post looks like. */
  const outputState = useCallback(
    (meetingId: string, outputId: string) =>
      state.outputState[`${meetingId}:${outputId}`] ?? "pending",
    [state.outputState],
  );

  const outputHeld = useCallback(
    (meetingId: string, outputId: string) =>
      Boolean(state.outputHeld[`${meetingId}:${outputId}`]),
    [state.outputHeld],
  );

  /* ── counts ────────────────────────────────────────────────── */

  const teamActionAcked = useCallback(
    (actionId: string) => {
      const ob = OBLIGATION_BY_TEAM_ACTION[actionId];
      return ob ? isAcknowledged(stageOf(ob)) : false;
    },
    [stageOf],
  );

  const commitmentStage = useCallback(
    (commitmentId: string): WorkStage | null => {
      const ob = OBLIGATION_BY_COMMITMENT[commitmentId];
      return ob ? stageOf(ob) : null;
    },
    [stageOf],
  );

  /** The obligations a completion update claims are finished, and which of
      them are not. Rendered next to the approve button rather than
      discovered after the client has been told. */
  const completionBlockers = useCallback(
    (obligationId: string) =>
      (COMPLETION_UPDATE_SCOPE[obligationId] ?? []).filter(
        (id) => !STAGE_META[stageOf(id)].closed,
      ),
    [stageOf],
  );

  const counts = useMemo<OpsHubCounts>(() => {
    const nw = queueOpen("needs_whitney");
    const packs = PACK_IDS.filter((id) => packStatus(id) === "needs_review").length;
    const invoicesOpen = INVOICES.filter(
      (i) => (state.invoiceState[i.id] ?? "overdue") !== "handled",
    ).length;
    const invalidOpen = INVALID_EMAILS.filter((i) => !state.invalidState[i.id]).length;

    /* DERIVED, not `2 + …`. The two structurally-overdue rows are data now
       (OVERDUE_TASKS), so the number on Home and the rows on Ops Watch cannot
       disagree — and posting a nudge no longer moves either, because
       `teamActionAcked` asks the lifecycle whether anybody acknowledged. */
    const unacked = TEAM_ACTIONS.filter((a) => !teamActionAcked(a.id)).length;
    const overdueTasks = OVERDUE_TASKS.length;
    const teamRisk = overdueTasks + unacked;

    const teamReplies = queueOpen("team_reply_due");
    const waiting = queueOpen("waiting_client");

    const needsReviewParts = [
      {
        label: "email drafts for Whitney",
        value: nw,
        screen: "inbox" as ScreenId,
        extra: { inboxQueue: "needs_whitney" },
      },
      {
        label: "meeting execution packs",
        value: packs,
        screen: "meetings" as ScreenId,
        extra: { meetingFilter: "needs_review" },
      },
      {
        label: "finance follow-ups",
        value: invoicesOpen,
        screen: "ops" as ScreenId,
        extra: { opsTab: "finance" },
      },
    ];

    const clientCommParts = [
      {
        label: "team replies past the expectation",
        value: teamReplies,
        screen: "inbox" as ScreenId,
        extra: { inboxQueue: "team_reply_due" },
      },
      {
        label: "clients we are waiting on",
        value: waiting,
        screen: "inbox" as ScreenId,
        extra: { inboxQueue: "waiting_client" },
      },
      {
        label: "invoice follow-ups",
        value: invoicesOpen,
        screen: "ops" as ScreenId,
        extra: { opsTab: "finance" },
      },
    ];

    return {
      needsReview: nw + packs + invoicesOpen,
      needsReviewSub: needsReviewParts
        .map((p) => `${p.value} ${p.label}`)
        .join(" · "),
      needsReviewParts,
      clientComm: waiting + teamReplies + invoicesOpen,
      clientCommSub: clientCommParts.map((p) => `${p.value} ${p.label}`).join(" · "),
      clientCommParts,
      teamRisk,
      teamRiskSub: `${overdueTasks} overdue · ${unacked} unacknowledged`,
      unacked,
      overdueTasks,
      inboxOpen: EMAILS.filter((e) => isEmailOpen(e.id)).length,
      opsOpen: teamRisk + invoicesOpen + invalidOpen,
      packsNeedingReview: packs,
      invoicesOpen,
      invalidOpen,
      clientAttention: CLIENTS.filter((c) => accountNeedsAttention(c.id, stageOf))
        .length,
      /* What is WAITING ON A PERSON, not how many moments exist. Three of
         the six in the queue are blocked on a transcript nobody can produce
         yet, and badging those as review work would put a number on the nav
         that no amount of reviewing can clear. */
      contentSignals: OPEN_SIGNALS,
      myOpen: reviewerOpen(state.user),
    };
  }, [
    queueOpen,
    isEmailOpen,
    packStatus,
    teamActionAcked,
    stageOf,
    reviewerOpen,
    state.invoiceState,
    state.invalidState,
    state.user,
  ]);

  /** Attention flags for one account, computed against LIVE stages. */
  const flagsFor = useCallback(
    (clientId: string) => accountFlags(clientId, stageOf),
    [stageOf],
  );

  /* ── actions ───────────────────────────────────────────────── */

  /** Move an obligation and record why. Every lifecycle change goes through
      here so the trail and the stage can never disagree. */
  const advance = useCallback(
    (
      obligationId: string,
      stage: WorkStage,
      event: { actor: string; text: string; where: ObligationEvent["where"] },
      msg?: string,
    ) => {
      setState((s) => ({
        ...s,
        stages: { ...s.stages, [obligationId]: stage },
        events: {
          ...s.events,
          [obligationId]: [
            ...(s.events[obligationId] ?? []),
            { at: "just now", ...event },
          ],
        },
      }));
      if (msg) toast(msg);
    },
    [toast],
  );

  /** An event with NO stage change. This is what a nudge is: it proves
      somebody chased, and it leaves the obligation exactly as open as it was. */
  const record = useCallback(
    (
      obligationId: string,
      event: { actor: string; text: string; where: ObligationEvent["where"] },
      msg?: string,
    ) => {
      setState((s) => ({
        ...s,
        events: {
          ...s.events,
          [obligationId]: [
            ...(s.events[obligationId] ?? []),
            { at: "just now", ...event },
          ],
        },
      }));
      if (msg) toast(msg);
    },
    [toast],
  );

  const setEmailStatus = useCallback(
    (id: string, status: EmailStatus, msg: string, kind?: string) => {
      const obligationId = OBLIGATION_BY_EMAIL[id] ?? "";
      const nextStage = DISPOSITION_STAGE[status];
      setState((s) => {
        const stages = { ...s.stages };
        const events = { ...s.events };
        if (obligationId) {
          /* A nudge does NOT overwrite an obligation that is already further
             along; it is an event on it. Everything else writes its stage. */
          if (status === "nudged") {
            const current = s.stages[obligationId] ?? OBLIGATION_META[obligationId]?.seed;
            stages[obligationId] =
              current && STAGE_RANK[current] > STAGE_RANK.waiting_ack
                ? current
                : "waiting_ack";
          } else {
            stages[obligationId] = nextStage;
          }
          events[obligationId] = [
            ...(s.events[obligationId] ?? []),
            {
              at: "just now",
              actor: s.user,
              text: msg.replace(/ — simulated$/, ""),
              where: status === "nudged" ? ("slack" as const) : ("gmail" as const),
            },
          ];
        }
        return {
          ...s,
          emailState: { ...s.emailState, [id]: status },
          stages,
          events,
          /* Approving the finance follow-up is what makes the invoice row read
             "draft ready" over on Ops Watch — one action, two screens. */
          invoiceState:
            kind === "finance"
              ? { ...s.invoiceState, "INV-204": "draft_ready" }
              : s.invoiceState,
        };
      });
      toast(msg);
    },
    [toast],
  );

  /* Re-triage. The row keeps its disposition and its stage — only the lane
     changes — so moving a completed row does not resurrect it. */
  const moveEmail = useCallback(
    (id: string, queue: string) => {
      setState((s) => ({ ...s, emailQueue: { ...s.emailQueue, [id]: queue } }));
      toast(
        `Moved to ${QUEUES.find((q) => q.id === queue)?.label ?? queue} — simulated`,
      );
    },
    [toast],
  );

  /** Hand-set the stage of the obligation behind an email row. */
  const setEmailStage = useCallback(
    (id: string, stage: WorkStage) => {
      const ob = OBLIGATION_BY_EMAIL[id];
      if (!ob) return;
      advance(
        ob,
        stage,
        { actor: "reviewer", text: `Stage set to ${STAGE_META[stage].label}`, where: "aihq" },
        `Stage set to ${STAGE_META[stage].label} — simulated`,
      );
    },
    [advance],
  );

  /** The reviewer's edit to a prepared draft. Held locally; approving uses
      the edited text, which is what makes "you can correct it" true. */
  const editDraft = useCallback((emailId: string, text: string) => {
    setState((s) => ({ ...s, draftEdits: { ...s.draftEdits, [emailId]: text } }));
  }, []);

  const clearDraftEdit = useCallback((emailId: string) => {
    setState((s) => {
      const draftEdits = { ...s.draftEdits };
      delete draftEdits[emailId];
      return { ...s, draftEdits };
    });
  }, []);

  /* ── meeting pack actions ──────────────────────────────────── */

  /** Release the outputs a reviewer selected. One of them fails on purpose:
      a pack in which every dispatch succeeds is not a demonstration of a
      review layer, it is a demonstration of a happy path. */
  const releasePack = useCallback(
    (meetingId: string, msg: string) => {
      const outputs = packOutputs(MEETINGS.find((m) => m.id === meetingId)!);
      setState((s) => {
        const next = { ...s.outputState };
        for (const o of outputs) {
          const key = `${meetingId}:${o.id}`;
          if (s.outputHeld[key]) {
            next[key] = "held";
            continue;
          }
          if (s.outputState[key] === "released") continue;
          next[key] = o.failsFirstAttempt && !s.outputRetried[key] ? "failed" : "released";
        }
        return { ...s, outputState: next, packState: { ...s.packState, [meetingId]: "approved" } };
      });
      toast(msg);
    },
    [toast],
  );

  const retryOutput = useCallback(
    (meetingId: string, outputId: string, msg: string) => {
      const key = `${meetingId}:${outputId}`;
      setState((s) => ({
        ...s,
        outputRetried: { ...s.outputRetried, [key]: true },
        outputState: { ...s.outputState, [key]: "released" },
      }));
      toast(msg);
    },
    [toast],
  );

  const assignOutputManually = useCallback(
    (meetingId: string, outputId: string, owner: string) => {
      const key = `${meetingId}:${outputId}`;
      setState((s) => ({
        ...s,
        outputState: { ...s.outputState, [key]: "manual" },
        outputOwner: { ...s.outputOwner, [key]: owner },
      }));
      toast(`Handed to ${owner} to do by hand — the pack stays open until it is done`);
    },
    [toast],
  );

  const toggleOutputHold = useCallback((meetingId: string, outputId: string) => {
    const key = `${meetingId}:${outputId}`;
    setState((s) => ({
      ...s,
      outputHeld: { ...s.outputHeld, [key]: !s.outputHeld[key] },
    }));
  }, []);

  /** Send a pack back for revision. A visible state, not a toast that
      evaporates: the pack stays on the list reading "awaiting revision". */
  const sendPackBack = useCallback(
    (id: string, msg: string) => {
      setState((s) => ({ ...s, packState: { ...s.packState, [id]: "revision" } }));
      toast(msg);
    },
    [toast],
  );

  const reopenPack = useCallback(
    (id: string, msg: string) => {
      setState((s) => ({ ...s, packState: { ...s.packState, [id]: "needs_review" } }));
      toast(msg);
    },
    [toast],
  );

  const fixException = useCallback(
    (key: string, msg: string) => {
      setState((s) => ({
        ...s,
        packExceptions: { ...s.packExceptions, [key]: true },
      }));
      toast(msg);
    },
    [toast],
  );

  /* ── Ops Watch actions ─────────────────────────────────────── */

  /** Post a nudge. Records the chase; the risk count does not move. */
  const nudge = useCallback(
    (actionId: string, owner: string) => {
      const ob = OBLIGATION_BY_TEAM_ACTION[actionId];
      if (!ob) return;
      const priorNudges = (state.events[ob] ?? []).filter((e) =>
        e.text.startsWith("Nudge posted"),
      ).length;
      record(
        ob,
        {
          actor: "Gisselle",
          text: `Nudge posted to ${owner} in Slack${priorNudges ? ` (chase ${priorNudges + 1})` : ""}`,
          where: "slack",
        },
        "Nudge posted to Slack — still unacknowledged, so the risk count is unchanged",
      );
    },
    [record, state.events],
  );

  /** The four acknowledgement paths, spelled out in ACK_PATHS on screen. */
  const acknowledge = useCallback(
    (actionId: string, how: string) => {
      const ob = OBLIGATION_BY_TEAM_ACTION[actionId];
      if (!ob) return;
      advance(
        ob,
        "in_progress",
        { actor: OBLIGATION_META[ob]?.owner ?? "owner", text: `Acknowledged · ${how}`, where: "slack" },
        `Acknowledged (${how}) — the risk clears and the work is now in progress`,
      );
    },
    [advance],
  );

  const setDigest = useCallback(
    (value: "ready" | "posted", msg: string) => {
      setState((s) => ({ ...s, digestState: value }));
      toast(msg);
    },
    [toast],
  );

  const setInvoice = useCallback(
    (id: string, value: "overdue" | "draft_ready" | "handled", msg: string) => {
      const ob = OBLIGATION_BY_INVOICE[id];
      setState((s) => ({
        ...s,
        invoiceState: { ...s.invoiceState, [id]: value },
        ...(ob && value === "handled"
          ? { stages: { ...s.stages, [ob]: "completed" as WorkStage } }
          : {}),
      }));
      toast(msg);
    },
    [toast],
  );

  const resolveInvalid = useCallback(
    (id: string, msg: string) => {
      setState((s) => ({ ...s, invalidState: { ...s.invalidState, [id]: true } }));
      toast(msg);
    },
    [toast],
  );

  /* ── Content Atelier ───────────────────────────────────────── */

  const stageContent = useCallback(
    (key: string, value: string, msg: string) => {
      setState((s) => ({ ...s, contentStage: { ...s.contentStage, [key]: value } }));
      toast(msg);
    },
    [toast],
  );

  const setCandidate = useCallback(
    (id: string, value: "accepted" | "rejected", msg: string) => {
      setState((s) => ({ ...s, candidateState: { ...s.candidateState, [id]: value } }));
      toast(msg);
    },
    [toast],
  );

  const setSteer = useCallback(
    (id: string, text: string) => {
      setState((s) => ({ ...s, steerDraft: { ...s.steerDraft, [id]: text } }));
    },
    [],
  );

  const setScript = useCallback(
    (id: string, value: "draft" | "approved", msg: string) => {
      setState((s) => ({ ...s, scriptState: { ...s.scriptState, [id]: value } }));
      toast(msg);
    },
    [toast],
  );

  const setClearance = useCallback(
    (id: string, value: boolean) => {
      setState((s) => ({ ...s, clearance: { ...s.clearance, [id]: value } }));
    },
    [],
  );

  /** The CTA. Set by a person, never inferred — and clearing it back to
      empty is a real move, because "I have not decided yet" is a state the
      pack has to be able to return to. */
  const setCta = useCallback(
    (momentId: string, cta: string, msg?: string) => {
      setState((s) => ({ ...s, contentCta: { ...s.contentCta, [momentId]: cta } }));
      if (msg) toast(msg);
    },
    [toast],
  );

  /** Which asset the rest of the pack derives from. Changing it after the
      lead was approved withdraws that approval: the derived formats were
      written from the old lead and cannot silently re-point at a new one. */
  const setLeadAsset = useCallback(
    (momentId: string, assetId: string, msg?: string) => {
      setState((s) => ({
        ...s,
        leadAsset: { ...s.leadAsset, [momentId]: assetId },
        scriptState: { ...s.scriptState, [momentId]: "draft" },
      }));
      if (msg) toast(msg);
    },
    [toast],
  );

  /* ── overlays ──────────────────────────────────────────────── */

  const openDrawer = useCallback((payload: DrawerPayload) => {
    setState((s) => ({ ...s, drawer: payload }));
  }, []);

  const openMsgModal = useCallback((payload: MsgModalPayload) => {
    setState((s) => ({ ...s, msgModal: payload }));
  }, []);

  const toggleUser = useCallback(() => {
    setState((s) => {
      const user = s.user === "Whitney" ? "Gisselle" : "Whitney";
      /* Switching reviewer has to land on that reviewer's own work, or the
         persona is decoration. */
      return { ...s, user, inboxQueue: REVIEWER_QUEUES[user][0], emailId: "" };
    });
  }, []);

  const resetDemo = useCallback(() => {
    setState((s) => ({ ...s, ...RESETTABLE }));
    toast("Demo state reset — every count and status is back to the starting point");
  }, [toast]);

  return {
    state,
    counts,
    /* readers */
    emailStatus,
    emailQueue,
    emailStage,
    stageOf,
    ownStage,
    eventsFor,
    obligationOfEmail,
    isEmailOpen,
    queueEmails,
    queueOpen,
    reviewerOpen,
    packStatus,
    meetingPackStatus,
    outputState,
    outputHeld,
    teamActionAcked,
    commitmentStage,
    completionBlockers,
    flagsFor,
    /* navigation */
    go,
    patch,
    /* actions */
    toast,
    advance,
    record,
    setEmailStatus,
    moveEmail,
    setEmailStage,
    editDraft,
    clearDraftEdit,
    releasePack,
    retryOutput,
    assignOutputManually,
    toggleOutputHold,
    sendPackBack,
    reopenPack,
    fixException,
    nudge,
    acknowledge,
    setDigest,
    setInvoice,
    resolveInvalid,
    stageContent,
    setCandidate,
    setSteer,
    setScript,
    setClearance,
    setCta,
    setLeadAsset,
    openDrawer,
    openMsgModal,
    toggleUser,
    resetDemo,
  };
}

export type OpsHub = ReturnType<typeof useOpsHub>;

export const ALL_MEETINGS = MEETINGS;
export { OBLIGATIONS };
