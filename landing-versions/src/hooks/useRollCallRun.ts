import { useCallback, useMemo, useRef, useState } from "react";
import { normalizeTranscript, type NormalizedTranscript } from "@/lib/internalMeeting";
import {
  buildGrid,
  deriveAttendance,
  matchToRoster,
  TRACKS,
  type MessageChannel,
  type GridRow,
  type Member,
  type ObservedSpeaker,
  type RosterMatch,
  type Session,
  type TrackId,
} from "@/lib/rollCall";
import {
  DEMO_SESSION_ID,
  ROSTER,
  SEEDED_SESSIONS,
  STAGES,
  type StageSpec,
} from "@/data/rollCall";

/* ────────────────────────────────────────────────────────────────
   Roll call run state.

   TERMINATES AT A HUMAN PRESSING SEND. Confirming a run writes attendance into
   this card's own session store and raises flags, each carrying the finished
   message for that member. A person then reads it and sends it, per the audit
   sheet: "Just needs to flag, we will manually follow up."

   `markSent` records that decision and nothing more — there is no mail or
   portal client in this build, so no request leaves the browser. The channel
   is stored per member because the two tiers use different ones (a portal DM
   at two weeks, email at four) and because the four-week email opens by
   referring to the two-week DM, so it needs to know whether that ever went.

   ── FOUR CORRECTIONS THE WARNING DID NOT COVER ────────────────────────
   The screen said plainly that transcript speech is only a fallback, and
   then gave the reviewer no controls to correct it. Saying a source is
   unreliable while offering no way to fix a wrong answer is not honesty, it
   is a disclaimer. So:

   1. THE SESSION IS CHOSEN, NOT FIXED. Track and date are selected before a
      paste, so a Meta session, a cancelled week and a re-read of an earlier
      Thursday are all reachable without editing code.

   2. A SILENT ATTENDEE CAN BE ADDED. They have no observed-speaker row to
      correct — that is the whole failure mode — so presence is added from
      the roster instead.

   3. A SHORT ATTENDANCE CAN BE CONFIRMED. Selecting a roster member used to
      leave `belowThreshold` in force, so a human decision could still be
      overruled by a word count. Confirming now overrides the floor.

   4. FOLLOW-UP IS PER MEMBER, TRACK, THRESHOLD AND SESSION. It was keyed on
      the member alone, so a Google DM in January made a Meta email in
      February think the DM had already gone.
   ──────────────────────────────────────────────────────────────── */

export type RunState = "idle" | "running" | "review" | "recorded";

/** One recorded follow-up. Keyed by member AND track AND session, because
    "have we already DM'd them?" is a different question per track. */
export interface SentRecord {
  memberId: string;
  track: TrackId;
  sessionId: string;
  channel: MessageChannel;
  tier: "two_week" | "four_week";
  /** The ClickUp task Gisselle creates today to monitor that it went
      (26 Aug @14:47). Recorded, not created — no write leaves the browser. */
  monitorTask: string;
}

/** One speaker, resolved against the roster. */
export interface ResolvedAttendee {
  observed: ObservedSpeaker;
  match: RosterMatch;
  /** Matched a member who is NOT in this session's channel. */
  crossTrack: boolean;
  /** A human confirmed the brief attendance counts, overriding the floor. */
  shortConfirmed: boolean;
  /** Needs a human: ambiguous name, unknown speaker, or below the floor. */
  needsDecision: boolean;
  /** Set by the reviewer when the match was ambiguous. */
  chosenMemberId?: string;
  /** Reviewer marked this speaker as not a member (a guest, a staff alias). */
  dismissed?: boolean;
}

export function useRollCallRun() {
  const [state, setState] = useState<RunState>("idle");
  const [text, setText] = useState("");
  const [transcript, setTranscript] = useState<NormalizedTranscript | null>(null);
  const [stageIndex, setStageIndex] = useState(-1);
  const [sessions, setSessions] = useState<Session[]>(SEEDED_SESSIONS);
  const [chosen, setChosen] = useState<Record<string, string>>({});
  const [dismissed, setDismissed] = useState<Record<string, boolean>>({});
  const [tab, setTab] = useState<TrackId>("google");
  /* Which members have had a message sent this run, and on which channel.
     Keyed per member so a row cannot be sent twice by accident, and so the
     4-week email can tell whether the 2-week DM ever actually went. */
  const [sentLog, setSentLog] = useState<SentRecord[]>([]);
  /* Reviewer overrides on the observed speakers: a short attendance the
     human has confirmed, and roster members added who never spoke at all. */
  const [confirmedShort, setConfirmedShort] = useState<Record<string, boolean>>({});
  const [manualPresent, setManualPresent] = useState<Record<string, boolean>>({});
  const timers = useRef<number[]>([]);

  /* WHICH SESSION IS BEING READ. Chosen, not fixed — the console previously
     hard-coded Google / 12 Feb, so a Meta session could not be processed at
     all and the two-track description had no demonstrable half. */
  const [runTrack, setRunTrack] = useState<TrackId>("google");
  const [runSessionId, setRunSessionId] = useState<string>(DEMO_SESSION_ID);

  const clearTimers = () => {
    timers.current.forEach((id) => window.clearTimeout(id));
    timers.current = [];
  };

  const start = useCallback((raw: string) => {
    clearTimers();
    setTranscript(normalizeTranscript(raw));
    setState("running");
    setStageIndex(0);
    let elapsed = 0;
    STAGES.forEach((stage: StageSpec, index: number) => {
      elapsed += stage.holdMs;
      timers.current.push(
        window.setTimeout(() => {
          if (index === STAGES.length - 1) {
            setStageIndex(STAGES.length);
            setState("review");
          } else {
            setStageIndex(index + 1);
          }
        }, elapsed),
      );
    });
  }, []);

  const reset = useCallback(() => {
    clearTimers();
    setState("idle");
    setText("");
    setTranscript(null);
    setStageIndex(-1);
    setSessions(SEEDED_SESSIONS);
    setChosen({});
    setDismissed({});
    setConfirmedShort({});
    setManualPresent({});
    setTab("google");
    setRunTrack("google");
    setRunSessionId(DEMO_SESSION_ID);
    setSentLog([]);
  }, []);

  /** Sessions a reviewer may read, per track. A cancelled week is offered
      and refused rather than hidden, so the rule is visible. */
  const selectableSessions = useMemo(
    () => sessions.filter((s) => s.track === runTrack).sort((a, b) => a.date.localeCompare(b.date)),
    [sessions, runTrack],
  );

  const runSession = useMemo(
    () => sessions.find((s) => s.sessionId === runSessionId) ?? null,
    [sessions, runSessionId],
  );

  /** Picking a track moves the chosen session to that track's newest
      unrecorded, uncancelled Thursday. */
  const chooseTrack = useCallback(
    (track: TrackId) => {
      setRunTrack(track);
      setTab(track);
      const candidates = SEEDED_SESSIONS.filter(
        (s) => s.track === track && !s.cancelled,
      ).sort((a, b) => a.date.localeCompare(b.date));
      const next = candidates.find((s) => !s.recorded) ?? candidates[candidates.length - 1];
      if (next) setRunSessionId(next.sessionId);
    },
    [],
  );

  /* Attendance and roster matching are computed from the PARSED transcript, so
     pasting different text changes the result. Nothing is hard-coded. */
  const attendees = useMemo<ResolvedAttendee[]>(() => {
    if (!transcript) return [];
    return deriveAttendance(transcript).map((observed) => {
      const match = matchToRoster(observed.label, ROSTER);
      const resolvedId = chosen[observed.label];
      const resolved = resolvedId
        ? (ROSTER.find((m) => m.memberId === resolvedId) ?? null)
        : match.member;
      const crossTrack = Boolean(resolved && !resolved.tracks.includes(runTrack));
      /* THE OVERRIDE. Selecting a roster member used to leave the engagement
         floor in force, so a human saying "yes, they were here" could still
         be overruled by a word count and the member scored absent. */
      const shortConfirmed = Boolean(confirmedShort[observed.label]);
      return {
        observed,
        match: resolvedId ? { ...match, member: resolved, method: "alias" } : match,
        crossTrack,
        shortConfirmed,
        needsDecision:
          !resolvedId &&
          (match.method === "ambiguous" ||
            match.method === "unknown" ||
            (observed.belowThreshold && !shortConfirmed)),
        chosenMemberId: resolvedId,
        dismissed: dismissed[observed.label],
      };
    });
  }, [transcript, chosen, dismissed, confirmedShort, runTrack]);

  const undecided = attendees.filter((a) => a.needsDecision && !a.dismissed);

  /** Roster members on this track who were NOT observed speaking — the
      cohort the method is blind to, offered so a human can add them. */
  const silentCandidates = useMemo(() => {
    const observedIds = new Set(
      attendees
        .filter((a) => !a.dismissed && a.match.member)
        .map((a) => a.match.member!.memberId),
    );
    return ROSTER.filter(
      (m) =>
        m.tracks.includes(runTrack) &&
        !observedIds.has(m.memberId) &&
        (!m.enrolledFrom || !runSession || runSession.date >= m.enrolledFrom),
    );
  }, [attendees, runTrack, runSession]);

  /** THE FINAL PREVIEW. Exactly who this run will mark present, and why —
      shown before the confirm rather than discovered in the grid after. */
  const presentPreview = useMemo(() => {
    const rows: { accountName: string; reason: string }[] = [];
    for (const a of attendees) {
      if (a.dismissed || !a.match.member) continue;
      if (a.observed.belowThreshold && !a.shortConfirmed) continue;
      rows.push({
        accountName: a.match.member.accountName,
        reason: a.observed.belowThreshold
          ? `spoke briefly (${a.observed.turns} turns, ${a.observed.words} words) — confirmed present by a human`
          : `spoke ${a.observed.turns} times, ${a.observed.words} words`,
      });
    }
    for (const m of ROSTER) {
      if (!manualPresent[m.memberId]) continue;
      if (rows.some((r) => r.accountName === m.accountName)) continue;
      rows.push({
        accountName: m.accountName,
        reason: "added by hand — attended without speaking",
      });
    }
    return rows;
  }, [attendees, manualPresent]);

  const presentAccounts = useMemo(
    () => presentPreview.map((r) => r.accountName),
    [presentPreview],
  );

  /* The grid is rebuilt from sessions on every render, so confirming a run
     moves the numbers in front of the reviewer rather than after a reload. */
  const grids = useMemo(() => {
    const latest = state === "recorded" ? runSessionId : null;
    return {
      google: buildGrid("google", ROSTER, sessions, latest),
      meta: buildGrid("meta", ROSTER, sessions, latest),
    } as Record<TrackId, GridRow[]>;
  }, [sessions, state, runSessionId]);

  /** Flags that this run newly raised — never the whole standing list. */
  const newFlags = useMemo(
    () => grids[runTrack].filter((row) => row.crossedThisRun),
    [grids, runTrack],
  );

  /** Already over a threshold before this run. Shown, but not re-raised. */
  const standingFlags = useMemo(
    () => grids[runTrack].filter((row) => row.flag !== "none" && !row.crossedThisRun),
    [grids, runTrack],
  );

  /** Records that a human sent the message. No request leaves the browser. */
  const markSent = useCallback(
    (
      memberId: string,
      channel: MessageChannel,
      opts?: { track?: TrackId; tier?: "two_week" | "four_week"; accountName?: string },
    ) => {
      const track = opts?.track ?? runTrack;
      const tier = opts?.tier ?? (channel === "email" ? "four_week" : "two_week");
      setSentLog((prev) => [
        ...prev,
        {
          memberId,
          track,
          sessionId: runSessionId,
          channel,
          tier,
          monitorTask: `Monitor ${tier === "four_week" ? "email" : "DM"} follow-up · ${
            opts?.accountName ?? memberId
          } · ${TRACKS[track].label}`,
        },
      ]);
    },
    [runTrack, runSessionId],
  );

  /** Has this member already been contacted ON THIS TRACK? The four-week
      email opens by referring to the two-week DM, so it has to know. */
  const sentFor = useCallback(
    (memberId: string, track: TrackId = runTrack) =>
      sentLog.filter((r) => r.memberId === memberId && r.track === track),
    [sentLog, runTrack],
  );

  /** Back-compat shape for the composer: latest channel per member, per track. */
  const sent = useMemo(() => {
    const map: Record<string, MessageChannel> = {};
    for (const r of sentLog) if (r.track === runTrack) map[r.memberId] = r.channel;
    return map;
  }, [sentLog, runTrack]);

  /** The most recent session actually READ for a track. Anchors {{DATE}}. */
  const lastRecordedDate = useCallback(
    (track: TrackId) =>
      sessions
        .filter((s) => s.track === track && s.recorded && !s.cancelled)
        .map((s) => s.date)
        .sort()
        .pop() ?? "2026-02-12",
    [sessions],
  );

  const chooseMember = useCallback((label: string, memberId: string) => {
    setChosen((prev) => ({ ...prev, [label]: memberId }));
  }, []);

  const dismiss = useCallback((label: string) => {
    setDismissed((prev) => ({ ...prev, [label]: true }));
  }, []);

  /** A human confirms a brief attendance counts. Overrides the word floor. */
  const confirmShort = useCallback((label: string) => {
    setConfirmedShort((prev) => ({ ...prev, [label]: true }));
  }, []);

  /** A human adds someone who attended without speaking. */
  const addPresent = useCallback((memberId: string) => {
    setManualPresent((prev) => ({ ...prev, [memberId]: true }));
  }, []);

  const removePresent = useCallback((memberId: string) => {
    setManualPresent((prev) => {
      const next = { ...prev };
      delete next[memberId];
      return next;
    });
  }, []);

  /**
   * The terminal action. Writes attendance into this card's own session store
   * and nowhere else, then lets the grid and the flags recompute.
   */
  const confirm = useCallback(() => {
    const present = presentAccounts;

    setSessions((prev) =>
      prev.map((session) =>
        session.sessionId === runSessionId
          ? { ...session, recorded: true, attended: present }
          : session,
      ),
    );
    setState("recorded");
    return { present: present.length };
  }, [presentAccounts, runSessionId]);

  return {
    state,
    text,
    runSession,
    runSessionId,
    setRunSessionId,
    selectableSessions,
    chooseTrack,
    silentCandidates,
    manualPresent,
    addPresent,
    removePresent,
    confirmShort,
    presentPreview,
    sentLog,
    sentFor,
    setText,
    transcript,
    stageIndex,
    attendees,
    undecided,
    presentAccounts,
    grids,
    sessions,
    newFlags,
    standingFlags,
    tab,
    setTab,
    sent,
    markSent,
    lastRecordedDate,
    runTrack,
    track: TRACKS[runTrack],
    roster: ROSTER,
    start,
    reset,
    chooseMember,
    dismiss,
    confirm,
  };
}

/* ── Exports ──────────────────────────────────────────────────────
   What Gisselle does in the two minutes AFTER this screen: paste the week's
   column into her sheet, and DM or email whoever crossed. Both are copyable
   so stopping short of a write layer reads as deliberate. */

export function toSheetColumn(grid: GridRow[], sessionDate: string): string {
  const header = ["Member", "Consecutive misses", "Last attended", "2-week", "4-week"].join("\t");
  const rows = grid.map((row) =>
    [
      row.member.accountName,
      String(row.consecutiveMisses),
      row.lastAttended ?? "never",
      row.flag === "two_week" || row.flag === "four_week" ? "YES" : "",
      row.flag === "four_week" ? "YES" : "",
    ].join("\t"),
  );
  return [`Roll call — session ${sessionDate}`, header, ...rows].join("\n");
}

export function toFollowUpList(newFlags: GridRow[], owner: string): string {
  if (!newFlags.length) return "No new flags this run.";
  const dm = newFlags.filter((r) => r.flag === "two_week");
  const email = newFlags.filter((r) => r.flag === "four_week");
  const block = (label: string, rows: GridRow[]) =>
    rows.length
      ? [
          `${label} — owner: ${owner}`,
          ...rows.map(
            (r) =>
              `• ${r.member.accountName} (${r.member.business}) — ${r.consecutiveMisses} consecutive misses, last attended ${r.lastAttended ?? "never"}`,
          ),
        ].join("\n")
      : "";
  return [block("PORTAL DM (2 weeks missed)", dm), block("EMAIL (4 weeks missed)", email)]
    .filter(Boolean)
    .join("\n\n");
}

export const memberById = (id: string): Member | undefined =>
  ROSTER.find((m) => m.memberId === id);
