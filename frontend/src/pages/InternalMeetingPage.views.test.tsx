import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import InternalMeetingPage from "./InternalMeetingPage";
import { DEMO_TRANSCRIPT } from "@/data/internalMeetingTranscript";
import { deriveCitation, detectSource, normalizeTranscript } from "@/lib/internalMeeting";

/* The stage walk is driven by setTimeout, so the review is reached by running
   the timers rather than by waiting ~9s of real holds. */
async function reachReview() {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
  render(
    <MemoryRouter>
      <InternalMeetingPage />
    </MemoryRouter>,
  );

  const textarea = screen.getByRole("textbox");
  /* paste, not type: 43k characters through a keyboard simulator is minutes. */
  await user.click(textarea);
  await user.paste(DEMO_TRANSCRIPT);

  await user.click(screen.getByRole("button", { name: /Read this transcript/ }));
  vi.advanceTimersByTime(12_000);
  await waitFor(() => expect(screen.getByText(/waiting on you/)).toBeInTheDocument());

  /* A fresh user bound to real timers. The one above is wired to
     advanceTimersByTime and throws the moment the fakes are torn down. */
  vi.useRealTimers();
  return userEvent.setup();
}

beforeEach(() => {
  vi.useRealTimers();
});

/** A kanban column, addressed by its heading rather than by loose text — the
    drag hint repeats "Waiting on you" in prose. */
const column = (name: string) =>
  screen.getByRole("heading", { name }).closest("section")!;

describe("source detection", () => {
  it("recognises the Fathom clipboard header without a call url", () => {
    /* The demo paste opens with "VIEW RECORDING - 48 mins" and carries no
       fathom.video link, so it is known to be Fathom AND cannot deep-link. */
    const t = normalizeTranscript(DEMO_TRANSCRIPT);
    expect(t.sourceKind).toBe("fathom");
    expect(t.fathomCallId).toBeNull();
    expect(t.canDeepLink).toBe(false);
  });

  it("does not assert a source it cannot see", () => {
    expect(detectSource("0:01 - Someone\n  Just some text.")).toBe("unknown");
    expect(detectSource("https://fathom.video/calls/12345")).toBe("fathom");
    expect(detectSource("https://zoom.us/rec/share/abc")).toBe("zoom");
  });

  it("anchors a citation to the turn that contains it", () => {
    const t = normalizeTranscript(DEMO_TRANSCRIPT);
    const quote = "So we need to add you to ClickUp, our GHL, and then";
    const cite = deriveCitation(t, quote);
    expect(cite.verified).toBe(true);
    expect(cite.turnIndex).toBeGreaterThanOrEqual(0);
    /* The modal reads the turn off this index, so it must be the turn whose
       text actually contains the quote — not merely a valid index. */
    expect(t.turns[cite.turnIndex].text).toContain(quote);
    expect(cite.display).toBe(t.turns[cite.turnIndex].display);
  });
});

describe("the three views", () => {
  it("defaults to the list and offers Board and Table", async () => {
    await reachReview();
    expect(screen.getByRole("button", { name: /List/, pressed: true })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Board/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Table/ })).toBeInTheDocument();
    expect(screen.getByText(/Already in the ledger/)).toBeInTheDocument();
  });

  it("shows the kanban columns with every decidable row waiting", async () => {
    const user = await reachReview();
    await user.click(screen.getByRole("button", { name: /Board/ }));

    for (const column of ["Waiting on you", "Recorded", "Closed by you", "Not an item", "Snoozed"])
      expect(screen.getByRole("heading", { name: column })).toBeInTheDocument();

    /* 10 decidable rows, all undecided on arrival. */
    const waiting = column("Waiting on you");
    expect(within(waiting).getByText("10")).toBeInTheDocument();
  });

  it("moves a card between columns when it is decided", async () => {
    const user = await reachReview();
    await user.click(screen.getByRole("button", { name: /Board/ }));

    const waiting = column("Waiting on you");
    const card = within(waiting)
      .getByText("Grant ai@ access to ClickUp, GHL and the Members Portal")
      .closest("article")!;
    await user.click(within(card).getByRole("button", { name: "Recorded" }));

    const recorded = column("Recorded");
    expect(
      within(recorded).getByText("Grant ai@ access to ClickUp, GHL and the Members Portal"),
    ).toBeInTheDocument();
    expect(within(waiting).getByText("9")).toBeInTheDocument();
  });

  it("renders the table with sortable headers and every row", async () => {
    const user = await reachReview();
    await user.click(screen.getByRole("button", { name: /Table/ }));

    const table = screen.getByRole("table");
    /* 14 rows: 10 decidable + 4 not-proposed, which the table includes so its
       counts cannot disagree with the list. */
    expect(within(table).getAllByRole("row")).toHaveLength(15); // + header
    expect(within(table).getByRole("button", { name: /Owner/ })).toBeInTheDocument();
    expect(within(table).getByRole("button", { name: /Due/ })).toBeInTheDocument();
  });

  it("keeps one decision state across all three views", async () => {
    const user = await reachReview();
    await user.click(screen.getByRole("button", { name: /Board/ }));

    const card = within(column("Waiting on you"))
      .getByText("Send E2M a couple of the office-hours transcripts")
      .closest("article")!;
    await user.click(within(card).getByRole("button", { name: "Recorded" }));

    await user.click(screen.getByRole("button", { name: /Table/ }));
    const row = screen
      .getByText("Send E2M a couple of the office-hours transcripts")
      .closest("tr")!;
    /* Two "Recorded" in the cell: the decision pill and the toggle that set
       it. The pill is the assertion — it is what a reader sees. */
    expect(within(row).getAllByText("Recorded").length).toBeGreaterThan(0);
    expect(within(row).getByText("Recorded", { selector: "span" })).toBeInTheDocument();
  });
});

describe("source logo opens the evidence modal", () => {
  it("shows the quote, the timestamp and the surrounding turns", async () => {
    const user = await reachReview();

    /* A chip for THIS run's transcript — the prior-run chip also carries an
       @mm:ss and sits earlier in the DOM. */
    const chip = screen
      .getAllByRole("button", { name: /@\d+:\d+/ })
      .find((el) => !/run #/.test(el.textContent ?? ""))!;
    await user.click(chip);

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("The words this came from")).toBeInTheDocument();
    expect(within(dialog).getByText("In context")).toBeInTheDocument();
    /* Source asserted from the paste, and the deep-link caveat stated. */
    expect(within(dialog).getAllByText(/Fathom/).length).toBeGreaterThan(0);
    expect(within(dialog).getByText(/no call id/)).toBeInTheDocument();
  });

  it("labels prior-run evidence as a different file and does not re-check it", async () => {
    const user = await reachReview();
    await user.click(screen.getByRole("button", { name: /run #23 · @40:33/ }));

    const dialog = await screen.findByRole("dialog");
    expect(
      within(dialog).getByText(/came out of the run #23 transcript, not the/),
    ).toBeInTheDocument();
    expect(within(dialog).queryByText("In context")).toBeNull();
  });

  it("leaves a failed verification open rather than behind a click", async () => {
    await reachReview();
    /* The deliberately broken row keeps its always-visible red block — it is
       the only on-screen proof the substring check runs. */
    expect(screen.getByText("Quote failed verification")).toBeInTheDocument();
    expect(
      screen.getByText("These words do not appear in the pasted transcript."),
    ).toBeInTheDocument();
  });
});

describe("removed copy", () => {
  it("no longer pitches the run against Fathom", async () => {
    await reachReview();
    expect(screen.queryByText(/nothing you have today does/)).toBeNull();
    expect(screen.queryByText(/is not a Fathom export/)).toBeNull();
    expect(screen.queryByText(/Nothing else you have keeps this list/)).toBeNull();
    expect(screen.queryByText(/which is what makes the carry-over below real/)).toBeNull();
  });

  it("keeps the factual disclosures and the capability statement", async () => {
    await reachReview();
    expect(
      screen.getByText(/This is the E2M weekly sync, not a Monday team meeting/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Speaker labels in this file are unreliable/)).toBeInTheDocument();
    /* The capability disclosure, not its exact old wording. It was reworded
       and de-emphasised so it stopped outweighing the value line above it,
       but it must still be on the page. */
    expect(
      screen.getByText(/No connection to ClickUp, Slack or Drive/),
    ).toBeInTheDocument();
  });
});
