/* Inbox re-triage and the ONE work lifecycle.

   These tests exist for one reason: the queue badges, the Home KPIs, the Ops
   Watch risk count and the Client Hub commitment ledger are all DERIVED from
   the same readers. A regression that reads `Email.queue` directly, or that
   treats an approval as a completion again, would not crash — it would just
   make two numbers on screen quietly disagree, which is the failure mode the
   hub's own comments call out. So the assertions are about the derivation,
   not about the widgets.

   THE BEHAVIOUR THESE ASSERT WAS DELIBERATELY CHANGED. Approving a draft used
   to mark a row completed and drop it out of every count, and posting a nudge
   used to clear an Ops Watch risk. Both were wrong: a draft is not a sent
   email and a chase is not an acknowledgement. */

import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useOpsHub } from "./useOpsHub";

/* Seed layout the assertions below lean on: e1/e2/e3 in Needs Whitney,
   e4/e5/e6 in Ready for Gisselle. */
const NEEDS_WHITNEY = 3;
const READY_GISSELLE = 3;

describe("emailQueue — re-triage overrides the seed queue", () => {
  it("starts from the queue in the seed data", () => {
    const { result } = renderHook(() => useOpsHub());
    expect(result.current.emailQueue("e1")).toBe("needs_whitney");
    expect(result.current.queueOpen("needs_whitney")).toBe(NEEDS_WHITNEY);
  });

  it("moves a row between queues and rebalances BOTH counts in one tick", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.moveEmail("e1", "ready_gisselle"));

    expect(result.current.emailQueue("e1")).toBe("ready_gisselle");
    expect(result.current.queueOpen("needs_whitney")).toBe(NEEDS_WHITNEY - 1);
    expect(result.current.queueOpen("ready_gisselle")).toBe(READY_GISSELLE + 1);
  });

  it("drops a moved row out of the source queue's list", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.moveEmail("e1", "no_action"));

    expect(result.current.queueEmails("needs_whitney").map((e) => e.id)).not.toContain(
      "e1",
    );
    expect(result.current.queueEmails("no_action").map((e) => e.id)).toContain("e1");
  });

  it("leaves the total inbox count unchanged — a move is not a completion", () => {
    const { result } = renderHook(() => useOpsHub());
    const before = result.current.counts.inboxOpen;

    act(() => result.current.moveEmail("e1", "finance_followup"));

    expect(result.current.counts.inboxOpen).toBe(before);
  });

  it("does not resurrect a completed row when it is moved", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.setEmailStage("e1", "completed"));
    act(() => result.current.moveEmail("e1", "ready_gisselle"));

    expect(result.current.isEmailOpen("e1")).toBe(false);
    expect(result.current.queueOpen("ready_gisselle")).toBe(READY_GISSELLE);
  });
});

describe("the lifecycle — a draft is not a sent email", () => {
  it("reads unread while nothing has happened", () => {
    const { result } = renderHook(() => useOpsHub());
    expect(result.current.emailStage("e2")).toBe("review_pending");
    expect(result.current.isEmailOpen("e2")).toBe(true);
  });

  it("approving creates a DRAFT and leaves the row open", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.setEmailStatus("e1", "approved", "ok", "draft"));

    expect(result.current.emailStage("e1")).toBe("draft_created");
    /* The correction. Previously this asserted `completed` and a falling
       queue count, which is exactly the claim the hub could not support. */
    expect(result.current.isEmailOpen("e1")).toBe(true);
    expect(result.current.queueOpen("needs_whitney")).toBe(NEEDS_WHITNEY);
  });

  it("only recording the send, then completion, closes the row", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.setEmailStatus("e1", "approved", "ok", "draft"));
    act(() => result.current.setEmailStage("e1", "sent"));
    expect(result.current.isEmailOpen("e1")).toBe(true);

    act(() => result.current.setEmailStage("e1", "completed"));
    expect(result.current.isEmailOpen("e1")).toBe(false);
    expect(result.current.queueOpen("needs_whitney")).toBe(NEEDS_WHITNEY - 1);
  });

  it("maps the softer dispositions rather than calling them done", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.setEmailStatus("e1", "kept", "ok"));
    expect(result.current.emailStage("e1")).toBe("noted");

    act(() => result.current.setEmailStatus("e2", "snoozed", "ok"));
    expect(result.current.emailStage("e2")).toBe("waiting_reply");

    /* Neither is finished, so neither leaves the queue. */
    expect(result.current.queueOpen("needs_whitney")).toBe(NEEDS_WHITNEY);
  });

  it("brings a snoozed row back to the top of the lifecycle when it expires", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.setEmailStatus("e2", "snoozed", "ok"));
    act(() => result.current.setEmailStatus("e2", "open", "back"));

    expect(result.current.emailStatus("e2")).toBe("open");
    expect(result.current.isEmailOpen("e2")).toBe(true);
  });

  it("keeps an in-progress row in the queue", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.setEmailStage("e1", "in_progress"));

    expect(result.current.isEmailOpen("e1")).toBe(true);
    expect(result.current.queueOpen("needs_whitney")).toBe(NEEDS_WHITNEY);
  });

  it("closes a row marked completed by hand, with no approval involved", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.setEmailStage("e1", "completed"));

    expect(result.current.emailStatus("e1")).toBe("open"); // disposition untouched
    expect(result.current.queueOpen("needs_whitney")).toBe(NEEDS_WHITNEY - 1);
  });

  it("lets an action overwrite a stale hand-picked stage", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.setEmailStage("e1", "in_progress"));
    act(() => result.current.setEmailStatus("e1", "approved", "ok", "draft"));

    expect(result.current.emailStage("e1")).toBe("draft_created");
  });
});

describe("a nudge is an event, not a resolution", () => {
  it("does not clear the Ops Watch risk when the nudge is posted", () => {
    const { result } = renderHook(() => useOpsHub());
    const before = result.current.counts.teamRisk;

    act(() => result.current.nudge("ack-carmen", "Carmen"));

    expect(result.current.counts.teamRisk).toBe(before);
    expect(result.current.eventsFor("ob-rosewood-reply")).toHaveLength(1);
  });

  it("records every chase rather than overwriting the first", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.nudge("ack-carmen", "Carmen"));
    act(() => result.current.nudge("ack-carmen", "Carmen"));

    expect(result.current.eventsFor("ob-rosewood-reply")).toHaveLength(2);
    expect(result.current.eventsFor("ob-rosewood-reply")[1].text).toContain("chase 2");
  });

  it("clears the risk only on an acknowledgement", () => {
    const { result } = renderHook(() => useOpsHub());
    const before = result.current.counts.teamRisk;

    act(() => result.current.acknowledge("ack-carmen", "reaction"));

    expect(result.current.counts.teamRisk).toBe(before - 1);
    expect(result.current.teamActionAcked("ack-carmen")).toBe(true);
  });

  it("approving the inbox nudge moves the SAME work item Ops Watch shows", () => {
    const { result } = renderHook(() => useOpsHub());
    const before = result.current.counts.teamRisk;

    act(() => result.current.setEmailStatus("e7", "nudged", "nudge posted"));

    /* One obligation, two screens: the inbox row records the nudge and the
       Ops Watch risk stays up, because nobody has replied. */
    expect(result.current.emailStage("e7")).toBe("waiting_ack");
    expect(result.current.counts.teamRisk).toBe(before);
    expect(result.current.teamActionAcked("ack-carmen")).toBe(false);
  });
});

describe("one obligation, four screens", () => {
  it("shows the parent's own stage while it is still running", () => {
    const { result } = renderHook(() => useOpsHub());

    /* The delivery is in progress; approving one of its emails is not
       progress on the delivery, so the parent does not move. */
    expect(result.current.stageOf("ob-bloom-lp")).toBe("in_progress");

    act(() => result.current.setEmailStatus("e1", "approved", "ok", "draft"));
    expect(result.current.stageOf("ob-bloom-lp")).toBe("in_progress");
  });

  it("refuses to read delivered while the client handoff is still a draft", () => {
    const { result } = renderHook(() => useOpsHub());

    /* Jacqueline finishes the page and marks the delivery complete… */
    act(() =>
      result.current.advance("ob-bloom-lp", "completed", {
        actor: "Jacqueline",
        text: "Page signed off",
        where: "clickup",
      }),
    );
    act(() => result.current.setEmailStage("e1", "completed"));
    act(() => result.current.setEmailStatus("e6", "approved", "ok", "draft"));

    /* …but the email carrying the link has not been sent, so the account
       overview must not say the client has it. The parent names the step
       that is holding it up rather than claiming closure. */
    expect(result.current.stageOf("ob-bloom-lp")).toBe("draft_created");

    act(() => result.current.setEmailStage("e6", "completed"));
    expect(result.current.stageOf("ob-bloom-lp")).toBe("completed");
  });

  it("blocks the completion update until what it claims is actually done", () => {
    const { result } = renderHook(() => useOpsHub());

    expect(result.current.completionBlockers("ob-bloom-completion")).toContain(
      "ob-bloom-lp",
    );

    act(() => result.current.setEmailStage("e1", "completed"));
    act(() => result.current.setEmailStage("e6", "completed"));
    act(() =>
      result.current.advance("ob-bloom-lp", "completed", {
        actor: "Jacqueline",
        text: "Delivered",
        where: "clickup",
      }),
    );

    expect(result.current.completionBlockers("ob-bloom-completion")).toHaveLength(0);
  });

  it("moves the account overview when a commitment is completed elsewhere", () => {
    const { result } = renderHook(() => useOpsHub());

    const before = result.current.flagsFor("bloom").map((f) => f.text);
    expect(before.join(" ")).toContain("unacknowledged");

    act(() => result.current.acknowledge("ack-jacqueline", "reaction"));

    const after = result.current.flagsFor("bloom").map((f) => f.text);
    expect(after.join(" ")).not.toContain("unacknowledged");
  });
});

describe("the reviewer's own queue", () => {
  it("counts only the lanes that reviewer owns", () => {
    const { result } = renderHook(() => useOpsHub());

    const whitney = result.current.counts.myOpen;
    expect(whitney).toBe(
      result.current.queueOpen("needs_whitney") +
        result.current.queueOpen("sales_followup"),
    );

    act(() => result.current.toggleUser());

    expect(result.current.state.user).toBe("Gisselle");
    expect(result.current.counts.myOpen).not.toBe(whitney);
    /* Switching persona lands on that persona's own first lane. */
    expect(result.current.state.inboxQueue).toBe("ready_gisselle");
  });
});

describe("meeting packs release per output", () => {
  it("fails one output, retries it, and does not re-release the rest", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.releasePack("bloom-strategy", "released"));

    expect(result.current.outputState("bloom-strategy", "o-slack")).toBe("failed");
    expect(result.current.outputState("bloom-strategy", "o-tasks")).toBe("released");

    act(() => result.current.retryOutput("bloom-strategy", "o-slack", "retried"));

    expect(result.current.outputState("bloom-strategy", "o-slack")).toBe("released");
  });

  it("holds back an output the reviewer excluded", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.toggleOutputHold("bloom-strategy", "o-recap"));
    act(() => result.current.releasePack("bloom-strategy", "released"));

    expect(result.current.outputState("bloom-strategy", "o-recap")).toBe("held");
  });

  it("keeps a returned pack visibly awaiting revision", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.sendPackBack("bloom-strategy", "back"));
    expect(result.current.packStatus("bloom-strategy")).toBe("revision");

    act(() => result.current.reopenPack("bloom-strategy", "reopened"));
    expect(result.current.packStatus("bloom-strategy")).toBe("needs_review");
  });
});

describe("resetDemo clears every axis", () => {
  it("returns a moved, completed row to its seed queue and stage", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.moveEmail("e1", "no_action"));
    act(() => result.current.setEmailStage("e1", "completed"));
    act(() => result.current.resetDemo());

    expect(result.current.emailQueue("e1")).toBe("needs_whitney");
    expect(result.current.emailStage("e1")).toBe("review_pending");
    expect(result.current.queueOpen("needs_whitney")).toBe(NEEDS_WHITNEY);
  });

  it("clears nudge history and released outputs", () => {
    const { result } = renderHook(() => useOpsHub());

    act(() => result.current.nudge("ack-carmen", "Carmen"));
    act(() => result.current.releasePack("bloom-strategy", "released"));
    act(() => result.current.resetDemo());

    expect(result.current.eventsFor("ob-rosewood-reply")).toHaveLength(0);
    expect(result.current.outputState("bloom-strategy", "o-slack")).toBe("pending");
  });
});
