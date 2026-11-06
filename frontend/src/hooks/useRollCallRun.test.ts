/* Roll call — the four corrections to the exception model.

   The screen already SAID that transcript speech is only a fallback and that
   a silent attendee is scored absent. It then gave the reviewer no way to
   correct any of it, which makes the warning a disclaimer rather than a
   control. These assert that the corrections actually change the recorded
   answer, because a confirmation that does not move the attendance number is
   worse than no confirmation at all. */

import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useRollCallRun } from "./useRollCallRun";
import { DEMO_TRANSCRIPT } from "@/data/rollCallTranscript";
import { META_TRANSCRIPT } from "@/data/rollCallMetaTranscript";
import { buildGrid } from "@/lib/rollCall";
import { ROSTER, SEEDED_SESSIONS } from "@/data/rollCall";

describe("session selection", () => {
  it("starts on the Google session but can move to Meta", () => {
    const { result } = renderHook(() => useRollCallRun());
    expect(result.current.runTrack).toBe("google");

    act(() => result.current.chooseTrack("meta"));

    expect(result.current.runTrack).toBe("meta");
    /* Lands on that track's newest unread, uncancelled Thursday. */
    expect(result.current.runSession?.track).toBe("meta");
    expect(result.current.runSession?.cancelled).toBeFalsy();
    expect(result.current.runSession?.recorded).toBe(false);
  });

  it("offers the cancelled week and marks it unselectable", () => {
    const { result } = renderHook(() => useRollCallRun());
    act(() => result.current.chooseTrack("meta"));

    const cancelled = result.current.selectableSessions.find((s) => s.cancelled);
    expect(cancelled).toBeDefined();
    expect(cancelled?.cancelledReason).toMatch(/cancelled/i);
  });
});

describe("a cancelled week is not a miss", () => {
  it("does not count towards a member's consecutive misses", () => {
    const grid = buildGrid("meta", ROSTER, SEEDED_SESSIONS, null);
    const marcus = grid.find((r) => r.member.accountName === "Marcus Hale")!;

    /* Marcus attended 15 Jan only. Without the cancelled-week rule the
       29 Jan column would be a third miss and push him over a threshold he
       never earned. */
    const cells = marcus.cells.filter((c) => c.session.cancelled);
    expect(cells).toHaveLength(1);
    expect(cells[0].state).toBe("no_session");
  });
});

describe("a late enrolment is not an absence", () => {
  it("reads not_enrolled for sessions before the membership started", () => {
    const grid = buildGrid("meta", ROSTER, SEEDED_SESSIONS, null);
    const rosa = grid.find((r) => r.member.accountName === "Rosa Delgado")!;

    const january = rosa.cells.filter((c) => c.session.date < "2026-02-05");
    expect(january.length).toBeGreaterThan(0);
    expect(january.every((c) => c.state !== "missed")).toBe(true);
    /* And so she carries no flag on her first tracked month. */
    expect(rosa.flag).toBe("none");
  });
});

describe("human corrections change the recorded attendance", () => {
  const run = (track: "google" | "meta" = "google") => {
    const hook = renderHook(() => useRollCallRun());
    act(() => hook.result.current.chooseTrack(track));
    act(() =>
      hook.result.current.start(track === "meta" ? META_TRANSCRIPT : DEMO_TRANSCRIPT),
    );
    return hook;
  };

  it("a confirmed short attendance counts as present", () => {
    /* The real Google transcript has no below-floor speaker — everyone who
       turned up had a consultation. The Meta fixture exists to carry that
       case rather than have it inserted into a real record. */
    const { result } = run("meta");

    const short = result.current.attendees.find(
      (a) => a.observed.belowThreshold && a.match.member,
    );
    /* The fixture must keep at least one below-floor speaker, or this
       correction has nothing to demonstrate. */
    expect(short).toBeDefined();
    const name = short!.match.member!.accountName;
    expect(result.current.presentAccounts).not.toContain(name);

    act(() => result.current.confirmShort(short!.observed.label));

    expect(result.current.presentAccounts).toContain(name);
    expect(
      result.current.presentPreview.find((r) => r.accountName === name)?.reason,
    ).toMatch(/confirmed present by a human/);
  });

  it("a silent attendee can be added from the roster", () => {
    const { result } = run();

    const silent = result.current.silentCandidates[0];
    expect(silent).toBeDefined();
    expect(result.current.presentAccounts).not.toContain(silent.accountName);

    act(() => result.current.addPresent(silent.memberId));

    expect(result.current.presentAccounts).toContain(silent.accountName);
    expect(
      result.current.presentPreview.find((r) => r.accountName === silent.accountName)
        ?.reason,
    ).toMatch(/without speaking/);
  });

  it("carries the correction through to the recorded session", () => {
    const { result } = run("meta");
    const silent = result.current.silentCandidates.find(
      (m) => m.accountName === "Rosa Delgado",
    )!;
    expect(silent).toBeDefined();

    act(() => result.current.addPresent(silent.memberId));
    act(() => {
      result.current.confirm();
    });

    const row = result.current.grids.meta.find(
      (r) => r.member.memberId === silent.memberId,
    );
    /* If the member is on this track, the newest column must read attended
       rather than missed — the whole point of the correction. */
    if (row) {
      expect(row.cells[row.cells.length - 1].state).toBe("attended");
      expect(row.consecutiveMisses).toBe(0);
    }
  });
});

describe("follow-up history is per member, track and session", () => {
  it("does not let a Google DM satisfy a Meta thread", () => {
    const { result } = renderHook(() => useRollCallRun());

    act(() =>
      result.current.markSent("M-105", "portal_dm", {
        track: "google",
        tier: "two_week",
        accountName: "Nora Chen",
      }),
    );

    expect(result.current.sentFor("M-105", "google")).toHaveLength(1);
    expect(result.current.sentFor("M-105", "meta")).toHaveLength(0);
  });

  it("records the ClickUp monitoring task the client creates by hand today", () => {
    const { result } = renderHook(() => useRollCallRun());

    act(() =>
      result.current.markSent("M-106", "email", {
        track: "google",
        tier: "four_week",
        accountName: "Tobias Wren",
      }),
    );

    const [record] = result.current.sentFor("M-106", "google");
    expect(record.monitorTask).toContain("Tobias Wren");
    expect(record.monitorTask).toContain("Google");
    expect(record.sessionId).toBe(result.current.runSessionId);
  });
});
