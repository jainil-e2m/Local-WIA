/* Renders the console with a stubbed lead feed to prove the dedup UI actually
   reaches the DOM: repeats collapse into one row, the flag marker appears, and
   the expanded panel explains why. The page is session-gated in the browser,
   so this is where the rendering gets verified. */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import type { Lead, LeadType } from "@/services/api/leadMagnet";

const listLeads = vi.fn();
const deleteLead = vi.fn().mockResolvedValue(undefined);

/* Spreads the real module rather than replacing it: only the four network
   calls need stubbing, and the pure helpers the page also imports (currently
   isFullAuditRunning and FULL_AUDIT_IDENTITY_FIELDS) must keep working. An
   exhaustive hand-written mock breaks the moment the page imports one more
   helper, which is exactly what happened. */
vi.mock("@/services/api/leadMagnet", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/services/api/leadMagnet")>()),
  listLeads: (...a: unknown[]) => listLeads(...a),
  deleteLead: (...a: unknown[]) => deleteLead(...a),
  createLead: vi.fn(),
  updateLead: vi.fn(),
  startFullAudit: vi.fn(),
  pollFullAudit: vi.fn(),
}));

// framer-motion's animated wrappers add nothing to assert on here.
vi.mock("framer-motion", () => ({
  AnimatePresence: ({ children }: { children?: React.ReactNode }) => children,
  motion: new Proxy(
    {},
    {
      get: (_t, tag: string) =>
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

let n = 0;
function lead(over: Partial<Lead> & { email: string; type: LeadType }): Lead {
  n += 1;
  return {
    id: over.id ?? `id-${n}`,
    seq: over.seq ?? n,
    name: over.name ?? `Person ${n}`,
    email: over.email,
    type: over.type,
    timestamp: over.timestamp ?? new Date(Date.UTC(2026, 0, n)).toISOString(),
    domainUrl: over.domainUrl,
    details: over.details,
  };
}

const renderPage = () =>
  render(
    <MemoryRouter>
      <LeadMagnetDashboardPage />
    </MemoryRouter>,
  );

beforeEach(() => {
  listLeads.mockReset();
  deleteLead.mockClear();
});

describe("console dedup UI", () => {
  it("collapses repeat submissions into a single row", async () => {
    listLeads.mockResolvedValue([
      lead({ id: "a1", email: "jai@x.com", name: "Jai", type: "ai_seo" }),
      lead({ id: "a2", email: "JAI@x.com", name: "Jai", type: "ai_seo" }),
      lead({ id: "b1", email: "other@x.com", name: "Other", type: "ai_seo" }),
    ]);
    renderPage();

    expect(await screen.findByText("Jai")).toBeInTheDocument();
    // Two captures from Jai, but only one row bearing that name.
    expect(screen.getAllByText("Jai")).toHaveLength(1);
    expect(screen.getByText("Other")).toBeInTheDocument();
    // The collapse is signalled by the flag marker and the caption above the
    // table — the row itself carries no count badge.
    expect(screen.getAllByRole("button", { name: /flag.*on this lead/i })).toHaveLength(1);
    expect(screen.getByText(/3 captures shown as 2 leads/i)).toBeInTheDocument();
  });

  it("explains the capture-vs-row gap above the table", async () => {
    listLeads.mockResolvedValue([
      lead({ id: "a1", email: "jai@x.com", type: "technical_seo" }),
      lead({ id: "a2", email: "jai@x.com", type: "technical_seo" }),
    ]);
    renderPage();
    expect(await screen.findByText(/2 captures shown as 1 leads/i)).toBeInTheDocument();
    expect(screen.getByText(/1 repeat submission folded in/i)).toBeInTheDocument();
  });

  it("shows a flag marker only on flagged rows", async () => {
    listLeads.mockResolvedValue([
      lead({ id: "a1", email: "jai@x.com", name: "Jai", type: "ai_seo" }),
      lead({ id: "a2", email: "jai@x.com", name: "Jai", type: "ai_seo" }),
      lead({ id: "b1", email: "clean@x.com", name: "Clean", type: "ai_seo" }),
    ]);
    renderPage();
    // 3 captures collapse to 2 rows, and only the repeat row is flagged.
    expect(await screen.findByText(/3 captures shown as 2 leads/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /flag.*on this lead/i })).toHaveLength(1);
  });

  it("opens the row from the flag marker and names the reason", async () => {
    const user = userEvent.setup();
    listLeads.mockResolvedValue([
      // seq is pinned: leadDisplayId renders lead_<seq>, so the ids asserted
      // below have to be chosen here rather than left to the factory counter.
      lead({ id: "a1", seq: 11, email: "jai@x.com", name: "Jai", type: "ai_seo" }),
      lead({ id: "a2", seq: 12, email: "jai@x.com", name: "Jai", type: "ai_seo" }),
    ]);
    renderPage();
    await screen.findByText("Jai");

    await user.click(screen.getByRole("button", { name: /flag.*on this lead/i }));

    expect(screen.getByText(/2 submissions of the same audit/i)).toBeInTheDocument();
    expect(
      screen.getByText(/submitted AI Crawlability Readiness Checker 2 times/i),
    ).toBeInTheDocument();
    // Both submissions are itemised so the collapse hides nothing. Scoped to
    // the history list: the representative's id also appears in Lead Details.
    const history = screen.getByRole("list", { name: /submission history/i });
    expect(within(history).getByText("lead_11")).toBeInTheDocument();
    expect(within(history).getByText("lead_12")).toBeInTheDocument();
    expect(within(history).getByText(/shown above/i)).toBeInTheDocument();
  });

  it("flags a domain audited by several different people, keeping the rows separate", async () => {
    const user = userEvent.setup();
    listLeads.mockResolvedValue([
      lead({ id: "1", email: "a@x.com", name: "Aaa", type: "ai_seo", domainUrl: "https://shared.com" }),
      lead({ id: "2", email: "b@x.com", name: "Bbb", type: "ai_seo", domainUrl: "http://www.shared.com/" }),
      lead({ id: "3", email: "c@x.com", name: "Ccc", type: "ai_seo", domainUrl: "shared.com" }),
    ]);
    renderPage();
    await screen.findByText("Aaa");

    // Three distinct people => three rows, each flagged.
    expect(screen.getByText("Bbb")).toBeInTheDocument();
    expect(screen.getByText("Ccc")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /flag.*on this lead/i })).toHaveLength(3);

    await user.click(screen.getAllByRole("button", { name: /flag.*on this lead/i })[0]);
    expect(
      screen.getByText(/shared\.com audited by 3 different people/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/3 audits have been run on shared\.com/i)).toBeInTheDocument();
  });

  it("does not flag one person auditing their own domain repeatedly", async () => {
    listLeads.mockResolvedValue([
      lead({ id: "1", email: "solo@x.com", name: "Solo", type: "technical_seo", domainUrl: "https://solo.com" }),
      lead({ id: "2", email: "solo@x.com", name: "Solo", type: "onpage_seo", domainUrl: "https://solo.com" }),
      lead({ id: "3", email: "solo@x.com", name: "Solo", type: "ai_seo", domainUrl: "https://solo.com" }),
    ]);
    renderPage();
    // Three different audit types => three separate rows, none flagged:
    // 3 audits on the host but only one person behind them.
    expect(await screen.findAllByText("Solo")).toHaveLength(3);
    expect(screen.queryAllByRole("button", { name: /flag.*on this lead/i })).toHaveLength(0);
  });

  it("deleting a collapsed row warns that every submission goes", async () => {
    const user = userEvent.setup();
    listLeads.mockResolvedValue([
      lead({ id: "a1", email: "jai@x.com", name: "Jai", type: "technical_seo" }),
      lead({ id: "a2", email: "jai@x.com", name: "Jai", type: "technical_seo" }),
    ]);
    renderPage();
    await screen.findByText("Jai");

    await user.click(screen.getByRole("button", { name: /delete lead jai/i }));
    const dialog = await screen.findByText(/delete all 2 submissions\?/i);
    expect(dialog).toBeInTheDocument();
    expect(screen.getByText(/All 2 stored submissions will be removed/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^delete lead$/i }));
    // Both stored ids removed, not just the representative.
    expect(deleteLead).toHaveBeenCalledTimes(2);
    expect(deleteLead.mock.calls.flat()).toEqual(expect.arrayContaining(["a1", "a2"]));
  });

  it("searching an older submission still shows its row", async () => {
    const user = userEvent.setup();
    listLeads.mockResolvedValue([
      // Timestamps pinned so "Newer" really is the representative — the
      // factory's auto-increment would otherwise make the second one newest.
      lead({
        id: "new",
        email: "jai@x.com",
        name: "Newer",
        type: "ai_seo",
        timestamp: "2026-06-01T00:00:00Z",
      }),
      lead({
        id: "old",
        email: "jai@x.com",
        name: "Older",
        type: "ai_seo",
        timestamp: "2026-01-01T00:00:00Z",
      }),
    ]);
    renderPage();
    expect(await screen.findByText("Newer")).toBeInTheDocument();

    await user.type(screen.getByLabelText(/search leads/i), "Older");
    // The row displays the newest submission, but a match on the collapsed
    // one must not make the row disappear.
    expect(screen.getByText("Newer")).toBeInTheDocument();
  });

  it("shows nothing unusual when there are no duplicates", async () => {
    listLeads.mockResolvedValue([
      lead({ id: "1", email: "a@x.com", name: "Aaa", type: "ai_seo" }),
      lead({ id: "2", email: "b@x.com", name: "Bbb", type: "technical_seo" }),
    ]);
    renderPage();
    await screen.findByText("Aaa");
    expect(screen.queryByRole("button", { name: /flag.*on this lead/i })).toBeNull();
    expect(screen.queryByText(/captures shown as/i)).toBeNull();
  });
});
