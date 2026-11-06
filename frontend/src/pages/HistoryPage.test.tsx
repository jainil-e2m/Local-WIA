import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import HistoryPage from "./HistoryPage";
import * as audits from "@/services/api/audits";

/**
 * The report follow-up poll: AI Presence finalizes a run and only then queues
 * its PDF, so a finished row legitimately has `report_ready` with no download
 * URL for a while. These cover the poll itself and — more importantly — the two
 * guards that keep it from running away: other services must never be polled,
 * and neither must a run old enough that its PDF is never coming.
 *
 * `clientPdfDownloadUrl` must be in this mock. HistoryPage calls it
 * unconditionally, unlike useAuditRun, whose own mock omits it and survives only
 * because a `report_ready` check short-circuits first.
 */
vi.mock("@/services/api/audits", () => ({
  listAudits: vi.fn(),
  getAuditStatus: vi.fn(),
  openAuditProgress: vi.fn(),
  LISTABLE_AUDIT_TYPES: ["technical", "ai-presence"],
  clientPdfDownloadUrl: (source: { outputs?: { client_pdf_download_url?: string | null } | null; client_pdf_download_url?: string | null } | null | undefined) =>
    source?.outputs?.client_pdf_download_url ?? source?.client_pdf_download_url ?? undefined,
}));

const PDF_URL = "https://drive.google.com/uc?export=download&id=abc";

function presenceRow(overrides: Partial<audits.AuditSummary> = {}): audits.AuditSummary {
  return {
    audit_id: "presence-1",
    status: "completed",
    dashboard_status: "completed",
    business_name: "Arbor Dental",
    seed_urls: ["https://arbordental.example"],
    submitted_at: new Date().toISOString(),
    started_at: new Date().toISOString(),
    report_ready: true,
    client_pdf_download_url: null,
    ...overrides,
  };
}

function renderHistory() {
  return render(
    <MemoryRouter>
      <HistoryPage />
    </MemoryRouter>,
  );
}

/** Resolve the list call per audit type so only AI Presence returns rows. */
function listReturns(rows: Partial<Record<string, audits.AuditSummary[]>>) {
  vi.mocked(audits.listAudits).mockImplementation(async (type) =>
    (rows[type as string] ?? []) as audits.AuditSummary[],
  );
}

beforeEach(() => {
  vi.mocked(audits.openAuditProgress).mockReturnValue({
    close: vi.fn(),
    onmessage: null,
    onerror: null,
  } as unknown as EventSource);
});

afterEach(() => {
  vi.clearAllMocks();
  vi.useRealTimers();
});

describe("HistoryPage — client PDF follow-up poll", () => {
  it("shows Preparing, then picks up a PDF that lands after the run went terminal", async () => {
    listReturns({ "ai-presence": [presenceRow()] });
    vi.mocked(audits.getAuditStatus).mockResolvedValue({
      audit_id: "presence-1",
      status: "completed",
      report_ready: true,
      outputs: { client_pdf_download_url: PDF_URL },
    } as unknown as audits.AuditStatusDetail);

    renderHistory();

    // Before any poll: the honest waiting state, not a Download that lies.
    expect(await screen.findAllByText("Preparing")).not.toHaveLength(0);
    expect(screen.queryByRole("link", { name: /download/i })).toBeNull();

    await waitFor(
      () => expect(audits.getAuditStatus).toHaveBeenCalledWith("ai-presence", "presence-1"),
      { timeout: 15_000 },
    );
    await waitFor(() => {
      const link = screen.getAllByRole("link", { name: /download/i })[0];
      expect(link).toHaveAttribute("href", PDF_URL);
    });
  }, 20_000);

  it("never polls a finished Technical SEO row that has no report", async () => {
    // No report_ready on this row — the field is AI Presence's alone.
    listReturns({
      technical: [
        {
          audit_id: "tech-1",
          status: "completed",
          seed_urls: ["https://example.com"],
          submitted_at: new Date().toISOString(),
          started_at: new Date().toISOString(),
          client_pdf_download_url: null,
        } as audits.AuditSummary,
      ],
    });

    renderHistory();
    // findAll, not find: the host renders as both the row title and its subline.
    await screen.findAllByText(/example\.com/i);

    await new Promise((resolve) => setTimeout(resolve, 500));
    expect(audits.getAuditStatus).not.toHaveBeenCalled();
    expect(screen.queryByText("Preparing")).toBeNull();
  });

  it("does not wait on a report-ready run old enough that its PDF is never coming", async () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    listReturns({
      "ai-presence": [presenceRow({ submitted_at: twoHoursAgo, started_at: twoHoursAgo })],
    });

    renderHistory();
    await screen.findByText(/arbordental\.example/i);

    await new Promise((resolve) => setTimeout(resolve, 500));
    expect(audits.getAuditStatus).not.toHaveBeenCalled();
    expect(screen.queryByText("Preparing")).toBeNull();
  });

  it("keeps showing a PDF the list already carried, without polling for it", async () => {
    listReturns({
      "ai-presence": [presenceRow({ client_pdf_download_url: PDF_URL })],
    });

    renderHistory();

    const link = (await screen.findAllByRole("link", { name: /download/i }))[0];
    expect(link).toHaveAttribute("href", PDF_URL);
    expect(screen.queryByText("Preparing")).toBeNull();
    expect(audits.getAuditStatus).not.toHaveBeenCalled();
  });
});
