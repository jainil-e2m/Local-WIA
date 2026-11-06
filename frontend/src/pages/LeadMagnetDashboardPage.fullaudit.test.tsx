/* The FULL AUDIT cell's three states, and what clicking the third one does.

   The bug this covers: the cell used to be a binary — completed, or "Run full
   audit" — so a lead whose audit was actually in flight advertised a button that
   started another one. Closing the progress console dropped every trace of the
   run, which is when an operator would see it. */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import type { Lead, LeadType } from "@/services/api/leadMagnet";

const listLeads = vi.fn();
const startFullAudit = vi.fn();
const pollFullAudit = vi.fn();

vi.mock("@/services/api/leadMagnet", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/services/api/leadMagnet")>()),
  listLeads: (...a: unknown[]) => listLeads(...a),
  deleteLead: vi.fn(),
  createLead: vi.fn(),
  updateLead: vi.fn(),
  startFullAudit: (...a: unknown[]) => startFullAudit(...a),
  pollFullAudit: (...a: unknown[]) => pollFullAudit(...a),
}));

vi.mock("framer-motion", () => ({
  AnimatePresence: ({ children }: { children?: React.ReactNode }) => children,
  motion: new Proxy(
    {},
    {
      get:
        (_t, tag: string) =>
        ({ children, ...rest }: Record<string, unknown> & { children?: React.ReactNode }) => {
          const Tag = tag as unknown as React.ElementType;
          const clean = Object.fromEntries(
            Object.entries(rest).filter(
              ([k]) => !["initial", "animate", "exit", "transition", "variants"].includes(k),
            ),
          );
          return <Tag {...clean}>{children}</Tag>;
        },
    },
  ),
}));

import LeadMagnetDashboardPage from "./LeadMagnetDashboardPage";

/* Marks a run as one this console started. Without it the lead describes a
   funnel-pushed audit id, which is deliberately NOT a full run in flight — see
   isFullAuditRunning. Every in-flight fixture below must carry it. */
const STARTED = "2026-09-07T12:00:00.000Z";

function lead(over: Partial<Lead> & { type: LeadType }): Lead {
  return {
    id: over.id ?? "lead-1",
    seq: 1,
    name: over.name ?? "Jamison Probst",
    email: over.email ?? "jamison@hickory.com",
    timestamp: "2026-09-01T21:39:00.000Z",
    domainUrl: over.domainUrl ?? "hickory.com",
    ...over,
  };
}

const renderPage = () =>
  render(
    <MemoryRouter>
      <LeadMagnetDashboardPage />
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.clearAllMocks();
  // Never resolves: the console opens and stays on its first tick, which is the
  // state under test. A resolved poll would race the assertions.
  pollFullAudit.mockReturnValue(new Promise(() => {}));
});

describe("full-audit cell states", () => {
  it('offers "Run full audit" for a lead that has never been audited', async () => {
    listLeads.mockResolvedValue([lead({ type: "technical_seo" })]);
    renderPage();
    expect(await screen.findByRole("button", { name: /run full audit/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /watch the full audit/i })).toBeNull();
  });

  it("shows the Running control instead once a run is in flight", async () => {
    listLeads.mockResolvedValue([
      lead({ type: "technical_seo", auditId: "audit-1", auditStatus: "running", fullAuditStartedAt: STARTED }),
    ]);
    renderPage();
    expect(
      await screen.findByRole("button", { name: /watch the full audit in progress/i }),
    ).toBeInTheDocument();
    // The whole point: no control that would start a second run.
    expect(screen.queryByRole("button", { name: /^run full audit$/i })).toBeNull();
  });

  it("shows Running for a queued run too, not just a started one", async () => {
    listLeads.mockResolvedValue([
      lead({ type: "technical_seo", auditId: "audit-1", auditStatus: "queued", fullAuditStartedAt: STARTED }),
    ]);
    renderPage();
    expect(
      await screen.findByRole("button", { name: /watch the full audit in progress/i }),
    ).toBeInTheDocument();
  });

  it("goes back to the completed state once the run reaches a terminal status", async () => {
    listLeads.mockResolvedValue([
      lead({
        type: "technical_seo",
        auditId: "audit-1",
        auditStatus: "completed",
        details: { scheduler_cron: "FULL_AUDIT_COMPLETED" },
      }),
    ]);
    renderPage();
    expect(
      await screen.findByRole("button", { name: /re-run the full audit/i }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /watch the full audit/i })).toBeNull();
  });

  it("prefers Running over the completed block while a re-run is in flight", async () => {
    listLeads.mockResolvedValue([
      lead({
        type: "technical_seo",
        auditId: "audit-2",
        auditStatus: "running",
        fullAuditStartedAt: STARTED,
        details: { scheduler_cron: "FULL_AUDIT_COMPLETED" },
      }),
    ]);
    renderPage();
    expect(
      await screen.findByRole("button", { name: /watch the full audit in progress/i }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /re-run the full audit/i })).toBeNull();
  });
});

describe("clicking the Running control", () => {
  it("attaches to the existing run and opens the console", async () => {
    listLeads.mockResolvedValue([
      lead({ type: "technical_seo", auditId: "audit-1", auditStatus: "running", fullAuditStartedAt: STARTED }),
    ]);
    startFullAudit.mockResolvedValue({
      auditId: "audit-1",
      toolId: "technical-seo",
      attached: true,
    });
    renderPage();

    await userEvent.click(
      await screen.findByRole("button", { name: /watch the full audit in progress/i }),
    );

    expect(
      await screen.findByRole("dialog", { name: /deep-dive audit console/i }),
    ).toBeInTheDocument();
    // Attach, not re-submit: the server dedupes, and the console says so.
    await waitFor(() => expect(startFullAudit).toHaveBeenCalledTimes(1));
    expect(startFullAudit).toHaveBeenCalledWith("lead-1", {});
    expect(await screen.findByText(/re-attaching to the full/i)).toBeInTheDocument();
  });

  it("does NOT re-ask an AI SEO lead for its country and state", async () => {
    // The old path sent every AI SEO click through the identity modal, so
    // watching a run already going meant re-entering identity it already had.
    listLeads.mockResolvedValue([
      lead({ type: "ai_seo", auditId: "audit-1", auditStatus: "running", fullAuditStartedAt: STARTED }),
    ]);
    startFullAudit.mockResolvedValue({ auditId: "audit-1", toolId: "ai-seo", attached: true });
    renderPage();

    await userEvent.click(
      await screen.findByRole("button", { name: /watch the full audit in progress/i }),
    );

    expect(
      await screen.findByRole("dialog", { name: /deep-dive audit console/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/additional required intake fields/i)).toBeNull();
  });

  it("keeps showing Running after the console is closed, and reopens the same run", async () => {
    listLeads.mockResolvedValue([
      lead({ type: "technical_seo", auditId: "audit-1", auditStatus: "running", fullAuditStartedAt: STARTED }),
    ]);
    startFullAudit.mockResolvedValue({
      auditId: "audit-1",
      toolId: "technical-seo",
      attached: true,
    });
    renderPage();

    const watch = await screen.findByRole("button", { name: /watch the full audit in progress/i });
    await userEvent.click(watch);
    const dialog = await screen.findByRole("dialog", { name: /deep-dive audit console/i });

    await userEvent.click(within_(dialog).closeButton());
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: /deep-dive audit console/i })).toBeNull(),
    );

    // The row must still say Running — this is the reported bug.
    const again = await screen.findByRole("button", { name: /watch the full audit in progress/i });
    await userEvent.click(again);
    expect(
      await screen.findByRole("dialog", { name: /deep-dive audit console/i }),
    ).toBeInTheDocument();

    // Re-opening a watch this tab already holds must not hit the API again.
    expect(startFullAudit).toHaveBeenCalledTimes(1);
  });
});

describe("reconciling a run nobody is watching", () => {
  /* The reported failure: a full audit was started from the console, the
     operator closed it (a real run takes ~17 minutes), and the audit finished
     upstream — but the row still offered "Run full audit" and never a report.

     The cause is that GET /full-audit is the ONLY thing that writes a terminal
     auditStatus onto a lead, and nothing was calling it once the console was
     closed. These prove the row now settles on its own, with no click. */

  it("flips to the completed state without any interaction", async () => {
    const running = lead({ type: "technical_seo", auditId: "audit-1", auditStatus: "running", fullAuditStartedAt: STARTED });
    const finished = lead({
      type: "technical_seo",
      auditId: "audit-1",
      auditStatus: "completed",
      fullAuditStartedAt: STARTED,
      auditReportUrl: "https://reports.example.com/audit-1.pdf",
      details: { scheduler_cron: "FULL_AUDIT_COMPLETED", last_audit_time: "2026-09-02T18:20:00Z" },
    });

    let current = [running];
    listLeads.mockImplementation(async () => current);
    // The sweep is what reaches the status route; the route is what writes the
    // terminal status, which the next list read then returns.
    pollFullAudit.mockImplementation(async () => {
      current = [finished];
      return {
        state: "completed",
        auditId: "audit-1",
        toolId: "technical-seo",
        auditStatus: "completed",
      };
    });

    renderPage();

    expect(await screen.findByRole("link", { name: /report/i })).toHaveAttribute(
      "href",
      "https://reports.example.com/audit-1.pdf",
    );
    expect(screen.getByRole("button", { name: /re-run the full audit/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /watch the full audit/i })).toBeNull();
    // Nobody clicked anything: no start request was ever made.
    expect(startFullAudit).not.toHaveBeenCalled();
    expect(pollFullAudit).toHaveBeenCalledWith("lead-1");
  });

  it("leaves the row on Running when the run has not finished yet", async () => {
    listLeads.mockResolvedValue([
      lead({ type: "technical_seo", auditId: "audit-1", auditStatus: "running", fullAuditStartedAt: STARTED }),
    ]);
    pollFullAudit.mockResolvedValue({ state: "running", auditId: "audit-1", percent: 40 });

    renderPage();

    expect(
      await screen.findByRole("button", { name: /watch the full audit in progress/i }),
    ).toBeInTheDocument();
    await waitFor(() => expect(pollFullAudit).toHaveBeenCalled());
    expect(screen.getByRole("button", { name: /watch the full audit in progress/i })).toBeInTheDocument();
  });

  it("does not poll a lead that has no run in flight", async () => {
    listLeads.mockResolvedValue([
      lead({
        type: "technical_seo",
        auditId: "audit-1",
        auditStatus: "completed",
        details: { scheduler_cron: "FULL_AUDIT_COMPLETED" },
      }),
    ]);
    renderPage();

    await screen.findByRole("button", { name: /re-run the full audit/i });
    // Every sweep is a real call through to a paid audit backend.
    expect(pollFullAudit).not.toHaveBeenCalled();
  });
});

describe("a funnel-pushed audit id is not a full run", () => {
  /* Reproduces the exact production rows. Every ai_seo lead carried
     audit_id + audit_status "complete" — the funnel's own quick audit, run on a
     deployment this dashboard has no address for, pushed in by the summary
     webhook. Nothing distinguished it from a full run, so the row claimed to be
     running and POST /full-audit attached to it instead of submitting: no AI SEO
     full audit was ever created, and no intake form was ever shown. */
  const funnelLead = (type: LeadType = "ai_seo") =>
    lead({
      type,
      auditId: "a08617af-3811-4788-9883-86623360982f",
      auditStatus: "complete", // AI SEO's own word, never translated on the way in
      details: { score: 85 },
      // no fullAuditStartedAt — the webhook never sets one
    });

  it("offers Run full audit, not Running", async () => {
    listLeads.mockResolvedValue([funnelLead()]);
    renderPage();

    expect(await screen.findByRole("button", { name: /run full audit/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /watch the full audit/i })).toBeNull();
  });

  it("is never polled, because its id belongs to another service", async () => {
    listLeads.mockResolvedValue([funnelLead()]);
    renderPage();

    await screen.findByRole("button", { name: /run full audit/i });
    // The reconciler asking our AI SEO service about a funnel id can only 404,
    // forever, every 15 seconds.
    expect(pollFullAudit).not.toHaveBeenCalled();
  });

  it("asks for country and state instead of silently attaching", async () => {
    listLeads.mockResolvedValue([funnelLead("ai_seo")]);
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: /run full audit/i }));

    // The intake the operator never saw.
    expect(await screen.findByText(/additional required intake fields/i)).toBeInTheDocument();
    // And nothing was submitted before the identity was collected.
    expect(startFullAudit).not.toHaveBeenCalled();
  });

  it("submits to the real service once the intake is filled", async () => {
    listLeads.mockResolvedValue([funnelLead("ai_seo")]);
    startFullAudit.mockResolvedValue({ auditId: "new-1", toolId: "ai-seo", attached: false });
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: /run full audit/i }));
    await screen.findByText(/additional required intake fields/i);

    /* fireEvent.change, not userEvent.type: the location comboboxes re-render on
       every keystroke as their suggestion list recomputes, and per-character
       typing loses all but the first. One change event is what a paste does. */
    fireEvent.change(screen.getByPlaceholderText("Wahha Design"), {
      target: { value: "Hickory Dental Care" },
    });
    fireEvent.change(screen.getByPlaceholderText("United States"), {
      target: { value: "United States" },
    });
    fireEvent.change(screen.getByPlaceholderText("North Carolina"), {
      target: { value: "North Carolina" },
    });
    const submit = screen
      .getAllByRole("button", { name: /run full audit/i })
      .find((b) => b.getAttribute("type") === "submit")!;
    await userEvent.click(submit);

    await waitFor(() => expect(startFullAudit).toHaveBeenCalledTimes(1));
    const [leadId, identity] = startFullAudit.mock.calls[0];
    expect(leadId).toBe("lead-1");
    // attached:false — a real submission, which is what reaches AI_SEO_AUDIT_URL.
    expect(identity).toMatchObject({
      businessName: "Hickory Dental Care",
      country: "United States",
      state: "North Carolina",
    });
  });

  it("re-opens the intake when the server answers 422 identity_required", async () => {
    // The server owns the real requirement; a 422 must become a prompt, not a
    // dead end, or any drift between the two lists strands the operator.
    listLeads.mockResolvedValue([funnelLead("technical_seo")]);
    startFullAudit.mockRejectedValue({
      response: { status: 422, data: { error: "identity_required", missing: ["country", "state"] } },
    });
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: /run full audit/i }));

    expect(await screen.findByText(/additional required intake fields/i)).toBeInTheDocument();
  });
});

/** The console's footer "Close" button, scoped to the dialog. */
function within_(dialog: HTMLElement) {
  return {
    closeButton: () => {
      const buttons = Array.from(dialog.querySelectorAll("button")).filter(
        (b) => b.textContent?.trim().toLowerCase() === "close",
      );
      expect(buttons.length).toBeGreaterThan(0);
      return buttons[0];
    },
  };
}
