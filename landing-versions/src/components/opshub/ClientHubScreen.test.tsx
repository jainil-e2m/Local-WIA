import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useOpsHub } from "@/hooks/useOpsHub";
import { ClientHubScreen } from "./screens/ClientHubScreen";
import {
  CLIENTS,
  CLIENT_INVOICES,
  COMMITMENTS,
  INVOICES,
  accountNeedsAttention,
  clientTabs,
} from "@/data/opsHub";
import { DEMO_NOW_MS, ENGAGEMENTS, LANES } from "@/data/engagement";

/* The screen takes the whole hub, so the harness is the real hook. That is
   deliberate: the tab set, the counts and the ask answers are all derived,
   and a stubbed hub would only prove the JSX compiles. */
function Harness() {
  const hub = useOpsHub();
  return <ClientHubScreen hub={hub} />;
}

const openAccount = async (name: string) => {
  const user = userEvent.setup();
  render(<Harness />);
  await user.click(screen.getByText(name));
  return user;
};

describe("Client Hub — account grid", () => {
  it("lists every account with its shape", () => {
    render(<Harness />);
    for (const c of CLIENTS) expect(screen.getByText(c.name)).toBeInTheDocument();
    expect(screen.getByText("Prospect")).toBeInTheDocument();
    expect(screen.getAllByText("Accelerator member")).toHaveLength(2);
    expect(screen.getAllByText("Retainer")).toHaveLength(3);
  });
});

describe("Client Hub — shape-aware tabs", () => {
  it("gives every account the three readings, then a retainer Money and Meetings", async () => {
    await openAccount("Bloom Manor");
    const labels = clientTabs(CLIENTS[0]).map(([, l]) => l);
    expect(labels).toEqual([
      "Spine",
      "Now",
      "Brief",
      "Commitments",
      "Timeline",
      "Meetings",
      "Money",
    ]);
    expect(screen.getByRole("tab", { name: /Money/ })).toBeInTheDocument();
  });

  it("opens on Spine, not on Now — history first, today second", async () => {
    await openAccount("Bloom Manor");
    expect(screen.getByRole("tab", { name: /Spine/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("tab", { name: /^Now/ })).toHaveAttribute(
      "aria-selected",
      "false",
    );
  });

  it("swaps Meetings for Attendance on an Accelerator member", async () => {
    await openAccount("Willow & Pine");
    expect(screen.getByRole("tab", { name: /Attendance/ })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /^Meetings/ })).toBeNull();
  });

  it("hides Money for a prospect", async () => {
    await openAccount("Magnolia House");
    expect(screen.queryByRole("tab", { name: /Money/ })).toBeNull();
    expect(screen.getByRole("tab", { name: /Commitments/ })).toBeInTheDocument();
  });
});

describe("Client Hub — Now tab", () => {
  it("derives its counts from the commitment ledger", async () => {
    const user = await openAccount("Bloom Manor");
    await user.click(screen.getByRole("tab", { name: /^Now/ }));
    const open = COMMITMENTS.filter(
      (c) => c.clientId === "bloom" && c.state !== "done",
    );
    const late = open.filter((c) => c.state === "overdue");

    const tile = (label: string) => screen.getByText(label).closest("div")!;
    expect(
      within(tile("Open commitments")).getByText(String(open.length)),
    ).toBeInTheDocument();
    expect(
      within(tile("Overdue")).getByText(String(late.length)),
    ).toBeInTheDocument();
  });

  it("shows the invoice standing empty state for a prospect", async () => {
    const user = await openAccount("Magnolia House");
    await user.click(screen.getByRole("tab", { name: /^Now/ }));
    expect(screen.getByText(/Nothing billed yet/)).toBeInTheDocument();
  });

  it("checks cadence per lane rather than per client", async () => {
    const user = await openAccount("Rosewood Venue");
    await user.click(screen.getByRole("tab", { name: /^Now/ }));

    /* Meetings expect every 35 days; the last call was 46 days before the
       frozen clock, so this lane is aging and the strip has to say so. */
    const row = screen.getByText("Calls & recordings").closest("button")!;
    expect(within(row).getByText(/expects every 35d/)).toBeInTheDocument();
  });
});

describe("Client Hub — Commitments tab", () => {
  it("splits the ledger by side and filters to overdue", async () => {
    const user = await openAccount("Rosewood Venue");
    await user.click(screen.getByRole("tab", { name: /Commitments/ }));

    const all = COMMITMENTS.filter((c) => c.clientId === "rosewood");
    expect(
      screen.getByText(`${all.length} of ${all.length} commitments`),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Overdue", pressed: false }));
    const late = all.filter((c) => c.state === "overdue");
    expect(
      screen.getByText(`${late.length} of ${all.length} commitments`),
    ).toBeInTheDocument();
  });

  it("says so when an account has no transcript timestamps", async () => {
    const user = await openAccount("Harbor House");
    await user.click(screen.getByRole("tab", { name: /Commitments/ }));
    expect(screen.getByText(/No transcript timestamps/)).toBeInTheDocument();
  });

  it("cites the transcript second when there is one", async () => {
    const user = await openAccount("Bloom Manor");
    await user.click(screen.getByRole("tab", { name: /Commitments/ }));
    expect(screen.getByText(/Said Sep 2 at 24:18/)).toBeInTheDocument();
  });
});

describe("Client Hub — Timeline tab", () => {
  it("filters the merged feed by source", async () => {
    const user = await openAccount("Bloom Manor");
    await user.click(screen.getByRole("tab", { name: /Timeline/ }));

    expect(screen.getByText("Client requested landing-page update")).toBeInTheDocument();
    expect(screen.getByText("Monthly Strategy Call")).toBeInTheDocument();

    /* Gmail only — the Zoom row must drop out. */
    await user.click(screen.getByRole("button", { name: /^Gmail/ }));
    expect(screen.getByText("Client requested landing-page update")).toBeInTheDocument();
    expect(screen.queryByText("Monthly Strategy Call")).toBeNull();
  });
});

describe("Client Hub — Money tab", () => {
  it("totals the ledger and shows the reminder trail", async () => {
    const user = await openAccount("Rosewood Venue");
    await user.click(screen.getByRole("tab", { name: /Money/ }));

    expect(screen.getByText("INV-204 · $1,850")).toBeInTheDocument();
    expect(screen.getByText(/Personal Gmail follow-up drafted/)).toBeInTheDocument();

    const paid = CLIENT_INVOICES.rosewood.filter((i) => i.state === "paid");
    const collected = paid.reduce((t, i) => t + i.amount, 0);
    const tile = screen.getByText("Collected").closest("div")!;
    expect(
      within(tile).getByText(`$${collected.toLocaleString("en-US")}`),
    ).toBeInTheDocument();
  });
});

describe("Client Hub — Attendance tab", () => {
  it("keeps the unmatched participant provisional rather than asserting it", async () => {
    const user = await openAccount("Willow & Pine");
    await user.click(screen.getByRole("tab", { name: /Attendance/ }));

    const row = screen
      .getByText(/91% similarity to Maya Stone/)
      .closest("button")!;
    expect(within(row).getByText("Needs match")).toBeInTheDocument();
    expect(
      screen.getByText(/miss count below is provisional/),
    ).toBeInTheDocument();
  });
});

describe("Client Hub — the asks route instead of generating", () => {
  it("answers from the loaded record and lands on the filtered tab", async () => {
    const user = await openAccount("Bloom Manor");
    await user.click(screen.getByText("What is overdue?"));

    /* One overdue commitment, no overdue invoice on this account. */
    expect(screen.getByText("1 commitment overdue.")).toBeInTheDocument();
    expect(screen.getByText(/no model call/)).toBeInTheDocument();

    /* It routed to Commitments with the overdue filter already applied. */
    const all = COMMITMENTS.filter((c) => c.clientId === "bloom");
    expect(screen.getByText(`1 of ${all.length} commitments`)).toBeInTheDocument();
  });

  it("counts both ledgers when money is also late", async () => {
    const user = await openAccount("Rosewood Venue");
    await user.click(screen.getByText("What is overdue?"));
    expect(
      screen.getByText("2 commitments and 1 invoice ($1,850) overdue."),
    ).toBeInTheDocument();
  });

  it("names the client contact when asked what we are waiting on", async () => {
    const user = await openAccount("Rosewood Venue");
    await user.click(screen.getByText("What are we waiting on?"));
    expect(
      screen.getByText("1 item outstanding from Dana Whitfield · 1 past the agreed date."),
    ).toBeInTheDocument();
  });
});

describe("Client Hub — derived cross-screen data", () => {
  it("derives the Ops Watch finance queue from the per-client ledger", () => {
    /* One list, not two: INVOICES is every overdue row in CLIENT_INVOICES. */
    expect(INVOICES.map((i) => i.id)).toEqual(["INV-204", "INV-198"]);
    expect(INVOICES[0]).toMatchObject({
      client: "Rosewood Venue",
      amount: "$1,850",
      age: "5d",
      due: "Aug 30",
      contact: "Dana Whitfield · dana@rosewoodvenue.com",
    });
  });

  it("flags only the accounts where something actually slipped", () => {
    const flagged = CLIENTS.filter((c) => accountNeedsAttention(c.id)).map((c) => c.id);
    /* Magnolia's proposal is due today but nothing is late yet. */
    expect(flagged).not.toContain("magnolia");
    expect(flagged).toEqual(["bloom", "rosewood", "everly", "willow", "harbor"]);
  });
});

/* ── Spine ──────────────────────────────────────────────────────── */

describe("Client Hub — Spine", () => {
  it("puts every lane of the engagement on one axis", async () => {
    await openAccount("Bloom Manor");
    expect(screen.getByText("Engagement spine")).toBeInTheDocument();
    for (const lane of LANES) {
      expect(screen.getAllByText(lane.short).length).toBeGreaterThan(0);
    }
  });

  it("narrows the window without changing the record", async () => {
    const user = await openAccount("Bloom Manor");
    const total = ENGAGEMENTS.bloom.events.length;
    expect(
      screen.getByText(new RegExp(`${total} of ${total} events in view`)),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "30 days" }));
    const cutoff = DEMO_NOW_MS - 30 * 86_400_000;
    const recent = ENGAGEMENTS.bloom.events.filter(
      (e) => new Date(e.occurredAt).getTime() >= cutoff,
    ).length;

    expect(recent).toBeLessThan(total);
    expect(
      screen.getByText(new RegExp(`${recent} of ${total} events in view`)),
    ).toBeInTheDocument();
  });

  it("declares which source went blind, and when", async () => {
    /* The most important thing on this screen. An incomplete record that does
       not say so is indistinguishable from a complete one. */
    await openAccount("Harbor House");
    /* Two sources went blind on the same day — the recorder changed and took
       both the Fathom key and the Drive filing with them. */
    expect(screen.getAllByText(/Blind from 14 Apr/)).toHaveLength(2);
    expect(screen.getByText(/Fathom keys are user-level/)).toBeInTheDocument();
    expect(
      screen.getByText(/mapping for Harbor House is unresolved/),
    ).toBeInTheDocument();
  });

  it("says a fact is uncitable rather than deriving a citation for it", async () => {
    const user = await openAccount("Harbor House");
    await user.click(screen.getByText("Rebuild the enquiry form"));
    expect(screen.getByText("Selected event")).toBeInTheDocument();
    /* The dash appears on every uncitable row in the list as well as on the
       selected event, which is the point — it is not a special case. */
    expect(screen.getAllByText("— not citable").length).toBeGreaterThan(1);
    expect(
      screen.getByText(/a fabricated citation is worse than an admitted gap/),
    ).toBeInTheDocument();
  });

  it("shows a prospect as a prospect rather than an empty client", async () => {
    await openAccount("Magnolia House");
    expect(screen.getByText("No engagement yet", { exact: false })).toBeInTheDocument();
    const tile = screen.getByText("Engagement age").closest("div")!;
    expect(within(tile).getByText("Not started")).toBeInTheDocument();
  });
});

/* ── Brief ──────────────────────────────────────────────────────── */

describe("Client Hub — Brief", () => {
  it("assembles a handover from the record, not from authored prose", async () => {
    const user = await openAccount("Bloom Manor");
    await user.click(screen.getByRole("tab", { name: /Brief/ }));
    expect(screen.getByText("Handover brief")).toBeInTheDocument();
    expect(screen.getByText(/18 months · since 14 Mar 2025/)).toBeInTheDocument();
  });

  it("lists the asset that is live, not the one it replaced", async () => {
    const user = await openAccount("Bloom Manor");
    await user.click(screen.getByRole("tab", { name: /Brief/ }));
    expect(
      screen.getByText("Enquiry landing page v2 — tour-first CTA"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Enquiry landing page v1")).toBeNull();
  });

  it("names its own holes instead of reading as complete", async () => {
    const user = await openAccount("Harbor House");
    await user.click(screen.getByRole("tab", { name: /Brief/ }));
    expect(screen.getByText("What this record cannot tell you")).toBeInTheDocument();
    expect(screen.getByText(/fathom unreachable from 14 Apr/i)).toBeInTheDocument();
  });

  it("raises the renewal that passed undecided", async () => {
    const user = await openAccount("Harbor House");
    await user.click(screen.getByRole("tab", { name: /Brief/ }));
    expect(
      screen.getByText(/Renewal date passed on 2 Sep 2026 with no decision recorded/),
    ).toBeInTheDocument();
  });

  it("keeps a departed contact on the record with the dates they were valid", async () => {
    /* Rosewood's positioning document was written for a contact who left in
       July 2025. Overwriting her would make every 2024 event look like it was
       agreed with someone who had not arrived yet. */
    const user = await openAccount("Rosewood Venue");
    await user.click(screen.getByRole("tab", { name: /Brief/ }));
    const row = screen.getByText("Priya Raman").closest("li")!;
    expect(within(row).getByText("Former")).toBeInTheDocument();
    expect(within(row).getByText(/15 Oct 2024 → 31 Jul 2025/)).toBeInTheDocument();
  });
});
