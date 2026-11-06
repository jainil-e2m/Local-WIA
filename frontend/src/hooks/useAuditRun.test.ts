import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAuditRun } from "./useAuditRun";
import * as audits from "@/services/api/audits";

vi.mock("@/services/api/audits", () => ({
  startAudit: vi.fn(),
  openAuditProgress: vi.fn(),
  getAuditStatus: vi.fn(),
  TERMINAL_AUDIT_STATUSES: new Set([
    "completed",
    "completed_partial",
    "failed",
    "cancelled",
    "interrupted",
  ]),
}));

/** Minimal stand-in for the SSE stream the hook wires handlers onto. */
function fakeEventSource() {
  return {
    close: vi.fn(),
    onmessage: null as ((event: { data: string }) => void) | null,
    onerror: null as (() => void) | null,
  };
}

function terminalDetail(status: "completed" | "completed_partial" | "failed" | "cancelled") {
  return {
    audit_id: "audit-1",
    status,
    failure_reason: status === "failed" ? "Worker failed" : null,
    outputs: { client_pdf_download_url: "https://reports.example/audit-1.pdf" },
  };
}

afterEach(() => {
  vi.clearAllMocks();
  vi.useRealTimers();
});

describe("useAuditRun", () => {
  it("starts an audit through the selected service and retains its id", async () => {
    const stream = fakeEventSource();
    vi.mocked(audits.startAudit).mockResolvedValue({ auditId: "audit-1" });
    vi.mocked(audits.openAuditProgress).mockReturnValue(stream as unknown as EventSource);
    const { result } = renderHook(() => useAuditRun("technical"));

    await act(() => result.current.run("Wahha Design", "https://wahhadesign.com"));

    expect(result.current.phase).toBe("running");
    expect(result.current.auditId).toBe("audit-1");
    expect(audits.startAudit).toHaveBeenCalledWith("technical", {
      businessName: "Wahha Design",
      businessUrl: "https://wahhadesign.com",
    });
    expect(audits.openAuditProgress).toHaveBeenCalledWith("technical", "audit-1");
  });

  it("uses persisted status to show a completed audit after an SSE terminal event", async () => {
    const stream = fakeEventSource();
    vi.mocked(audits.startAudit).mockResolvedValue({ auditId: "audit-1" });
    vi.mocked(audits.openAuditProgress).mockReturnValue(stream as unknown as EventSource);
    vi.mocked(audits.getAuditStatus).mockResolvedValue(terminalDetail("completed"));
    const { result } = renderHook(() => useAuditRun("technical"));

    await act(() => result.current.run("Wahha Design", "https://wahhadesign.com"));
    await act(async () => {
      stream.onmessage?.({
        data: JSON.stringify({ percent: 100, stage: "Completed", done: true }),
      });
      await Promise.resolve();
    });

    expect(result.current.phase).toBe("completed");
    expect(result.current.detail?.outputs?.client_pdf_download_url).toContain("audit-1.pdf");
    expect(stream.close).toHaveBeenCalled();
  });

  it("never converts a failed terminal event into a successful completion", async () => {
    const stream = fakeEventSource();
    vi.mocked(audits.startAudit).mockResolvedValue({ auditId: "audit-1" });
    vi.mocked(audits.openAuditProgress).mockReturnValue(stream as unknown as EventSource);
    vi.mocked(audits.getAuditStatus).mockResolvedValue(terminalDetail("failed"));
    const { result } = renderHook(() => useAuditRun("technical"));

    await act(() => result.current.run("Wahha Design", "https://wahhadesign.com"));
    await act(async () => {
      stream.onmessage?.({
        data: JSON.stringify({ percent: 100, stage: "Failed", done: true, status: "failed" }),
      });
      await Promise.resolve();
    });

    expect(result.current.phase).toBe("failed");
    expect(result.current.stage).toBe("Failed");
    expect(result.current.detail?.failure_reason).toBe("Worker failed");
  });

  it("uses polling to recover a dropped SSE stream", async () => {
    vi.useFakeTimers();
    const stream = fakeEventSource();
    vi.mocked(audits.startAudit).mockResolvedValue({ auditId: "audit-1" });
    vi.mocked(audits.openAuditProgress).mockReturnValue(stream as unknown as EventSource);
    vi.mocked(audits.getAuditStatus).mockResolvedValue(terminalDetail("cancelled"));
    const { result } = renderHook(() => useAuditRun("technical"));

    await act(() => result.current.run("Wahha Design", "https://wahhadesign.com"));
    await act(async () => {
      stream.onerror?.();
      await Promise.resolve();
    });

    expect(audits.getAuditStatus).toHaveBeenCalledWith("technical", "audit-1");
    expect(result.current.phase).toBe("failed");
    expect(result.current.stage).toBe("Cancelled");
  });

  it("shows the service's own stage while polling, with nothing about the transport", async () => {
    vi.useFakeTimers();
    const stream = fakeEventSource();
    vi.mocked(audits.startAudit).mockResolvedValue({ auditId: "audit-1" });
    vi.mocked(audits.openAuditProgress).mockReturnValue(stream as unknown as EventSource);
    vi.mocked(audits.getAuditStatus).mockResolvedValue({
      audit_id: "audit-1",
      status: "running",
      progress_percent: 67,
      progress_stage: "Running checks (18 / 33 complete)",
    });
    const { result } = renderHook(() => useAuditRun("on-page"));

    await act(() => result.current.run("Wahha Design", "https://wahhadesign.com"));
    await act(async () => {
      stream.onerror?.();
      await Promise.resolve();
    });

    expect(result.current.phase).toBe("running");
    expect(result.current.percent).toBe(67);
    expect(result.current.stage).toBe("Running checks (18 / 33 complete)");
  });

  it("advances the stage across polls as the run moves between stages", async () => {
    vi.useFakeTimers();
    const stream = fakeEventSource();
    vi.mocked(audits.startAudit).mockResolvedValue({ auditId: "audit-1" });
    vi.mocked(audits.openAuditProgress).mockReturnValue(stream as unknown as EventSource);
    vi.mocked(audits.getAuditStatus)
      .mockResolvedValueOnce({
        audit_id: "audit-1",
        status: "running",
        progress_percent: 22,
        progress_stage: "Crawling pages (128 / 340 crawled)",
      })
      .mockResolvedValueOnce({
        audit_id: "audit-1",
        status: "running",
        progress_percent: 42,
        progress_stage: "Classifying pages",
      });
    const { result } = renderHook(() => useAuditRun("on-page"));

    await act(() => result.current.run("Wahha Design", "https://wahhadesign.com"));
    await act(async () => {
      stream.onerror?.();
      await Promise.resolve();
    });
    expect(result.current.stage).toBe("Crawling pages (128 / 340 crawled)");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(8_000);
    });
    expect(result.current.stage).toBe("Classifying pages");
    expect(result.current.percent).toBe(42);
  });

  it("keeps the last known stage until the first poll answers", async () => {
    vi.useFakeTimers();
    const stream = fakeEventSource();
    vi.mocked(audits.startAudit).mockResolvedValue({ auditId: "audit-1" });
    vi.mocked(audits.openAuditProgress).mockReturnValue(stream as unknown as EventSource);
    // A poll that never settles: the stage on screen has to be the streamed one,
    // not a placeholder describing the switch to polling.
    vi.mocked(audits.getAuditStatus).mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useAuditRun("on-page"));

    await act(() => result.current.run("Wahha Design", "https://wahhadesign.com"));
    await act(async () => {
      stream.onmessage?.({
        data: JSON.stringify({ percent: 46, stage: "Rendering pages" }),
      });
      await Promise.resolve();
    });
    await act(async () => {
      stream.onerror?.();
      await Promise.resolve();
    });

    expect(result.current.stage).toBe("Rendering pages");
  });

  it("falls back to the status when a service reports no stage", async () => {
    vi.useFakeTimers();
    const stream = fakeEventSource();
    vi.mocked(audits.startAudit).mockResolvedValue({ auditId: "audit-1" });
    vi.mocked(audits.openAuditProgress).mockReturnValue(stream as unknown as EventSource);
    vi.mocked(audits.getAuditStatus).mockResolvedValue({
      audit_id: "audit-1",
      status: "queued",
    });
    const { result } = renderHook(() => useAuditRun("on-page"));

    await act(() => result.current.run("Wahha Design", "https://wahhadesign.com"));
    await act(async () => {
      stream.onerror?.();
      await Promise.resolve();
    });

    expect(result.current.stage).toBe("Queued");
  });

  /**
   * The nine labels On-Page's DASHBOARD_STAGE_LABELS reports, in pipeline
   * order. The signed-off progress copy: the tool page renders `stage` verbatim,
   * so each of these reaches a client exactly as written. Pinned on this side
   * too because the backend suite can only prove the service EMITS them — this
   * proves the dashboard does not decorate, truncate or rewrite them on the way
   * to the screen, which is the specific regression that shipped before (a
   * "live stream unavailable; polling" suffix appended to every one of them).
   */
  const APPROVED_ON_PAGE_STAGES = [
    "Queued",
    "Preparing the run",
    "Crawling pages",
    "Extracting content",
    "Classifying pages",
    "Planning checks",
    "Rendering pages",
    "Running checks",
    "Building the report",
    // The two banded stages carry their counters once the service has them.
    "Crawling pages (128 / 340 crawled)",
    "Running checks (18 / 33 complete)",
  ];

  it.each(APPROVED_ON_PAGE_STAGES)(
    "shows the stage %j exactly as the service reports it",
    async (progress_stage) => {
      vi.useFakeTimers();
      const stream = fakeEventSource();
      vi.mocked(audits.startAudit).mockResolvedValue({ auditId: "audit-1" });
      vi.mocked(audits.openAuditProgress).mockReturnValue(stream as unknown as EventSource);
      vi.mocked(audits.getAuditStatus).mockResolvedValue({
        audit_id: "audit-1",
        status: "running",
        progress_percent: 42,
        progress_stage,
      });
      const { result } = renderHook(() => useAuditRun("on-page"));

      await act(() => result.current.run("Wahha Design", "https://wahhadesign.com"));
      await act(async () => {
        stream.onerror?.();
        await Promise.resolve();
      });

      expect(result.current.stage).toBe(progress_stage);
    },
  );

  it("moves to error when the start request fails", async () => {
    vi.mocked(audits.startAudit).mockRejectedValue(new Error("no backend"));
    const { result } = renderHook(() => useAuditRun("technical"));

    await act(() => result.current.run("Wahha Design", "https://wahhadesign.com"));

    expect(result.current.phase).toBe("error");
    expect(audits.openAuditProgress).not.toHaveBeenCalled();
  });
});
