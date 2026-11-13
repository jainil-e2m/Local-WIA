import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useQueryReview } from "./useQueryReview";
import * as aiPresence from "@/services/api/aiPresence";

vi.mock("@/services/api/aiPresence", () => ({
  getAuditQueries: vi.fn(),
  confirmAuditQueries: vi.fn(),
}));

/** A realistic slice of GET /audits/:id/queries. */
const backendQueries = [
  {
    query_number: 1,
    query_text: "What does Schein Dental do?",
    is_branded: true,
    category_name: "Brand & Entity Recognition",
    aspect_key: "brand_entity_recognition",
  },
  {
    query_number: 2,
    query_text: "who provides family dental care",
    is_branded: false,
    category_name: "Core Solution & Keyword",
    aspect_key: "core_solution_keyword",
  },
  {
    query_number: 3,
    query_text: "dental cleaning and checkup near me",
    is_branded: false,
    category_name: "Local & Geographic",
    aspect_key: "local_geographic",
  },
];

beforeEach(() => {
  vi.mocked(aiPresence.getAuditQueries).mockReset();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("useQueryReview fetch", () => {
  it("loads the generated set into sections and reports done", async () => {
    // Resolves on a later tick, like a real request — the response must survive
    // whatever re-renders happen while it is in flight.
    vi.mocked(aiPresence.getAuditQueries).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(backendQueries), 10)),
    );

    const { result } = renderHook(() =>
      useQueryReview({ auditId: "audit-1", active: true, onConfirmed: vi.fn() }),
    );

    await waitFor(() => expect(result.current.fetchStatus).toBe("done"));
    expect(result.current.total).toBe(3);
    expect(aiPresence.getAuditQueries).toHaveBeenCalledTimes(1);
  });

  it("does not fetch until the run is actually awaiting review", async () => {
    vi.mocked(aiPresence.getAuditQueries).mockResolvedValue(backendQueries);

    const { result, rerender } = renderHook(
      ({ active }: { active: boolean }) =>
        useQueryReview({ auditId: "audit-1", active, onConfirmed: vi.fn() }),
      { initialProps: { active: false } },
    );

    await new Promise((r) => setTimeout(r, 20));
    expect(aiPresence.getAuditQueries).not.toHaveBeenCalled();

    rerender({ active: true });
    await waitFor(() => expect(result.current.fetchStatus).toBe("done"));
    expect(result.current.total).toBe(3);
  });

  it("fetches once, not once per re-render, while awaiting review", async () => {
    vi.mocked(aiPresence.getAuditQueries).mockResolvedValue(backendQueries);

    const { result, rerender } = renderHook(() =>
      useQueryReview({ auditId: "audit-1", active: true, onConfirmed: vi.fn() }),
    );

    await waitFor(() => expect(result.current.fetchStatus).toBe("done"));
    // The panel re-renders on every 8s status poll; none of that may refetch.
    rerender();
    rerender();
    await new Promise((r) => setTimeout(r, 20));
    expect(aiPresence.getAuditQueries).toHaveBeenCalledTimes(1);
  });

  it("surfaces a failure as retryable, and retry refetches", async () => {
    vi.mocked(aiPresence.getAuditQueries).mockRejectedValueOnce(new Error("409"));

    const { result } = renderHook(() =>
      useQueryReview({ auditId: "audit-1", active: true, onConfirmed: vi.fn() }),
    );

    await waitFor(() => expect(result.current.fetchStatus).toBe("error"));
    expect(result.current.error).toBeTruthy();

    vi.mocked(aiPresence.getAuditQueries).mockResolvedValue(backendQueries);
    result.current.retry();

    await waitFor(() => expect(result.current.fetchStatus).toBe("done"));
    expect(result.current.total).toBe(3);
  });

  it("never shows a previous run's queries after the id changes", async () => {
    vi.mocked(aiPresence.getAuditQueries).mockResolvedValue(backendQueries);

    const { result, rerender } = renderHook(
      ({ auditId }: { auditId: string }) =>
        useQueryReview({ auditId, active: true, onConfirmed: vi.fn() }),
      { initialProps: { auditId: "audit-1" } },
    );

    await waitFor(() => expect(result.current.total).toBe(3));

    vi.mocked(aiPresence.getAuditQueries).mockResolvedValue([backendQueries[0]]);
    rerender({ auditId: "audit-2" });

    await waitFor(() => expect(result.current.total).toBe(1));
  });
});
