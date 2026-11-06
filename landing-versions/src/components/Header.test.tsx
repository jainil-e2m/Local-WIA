import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Header } from "./Header";
import { AuthContext, type AuthContextValue } from "@/context/auth";

/** Header uses <Link> + useAuth, so it needs a router and an auth context. */
function renderHeader(auth: Partial<AuthContextValue> = {}) {
  const value: AuthContextValue = {
    status: "authenticated",
    user: { email: "team@wahha.design", name: "Wahha Design", role: "team" },
    login: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    ...auth,
  };
  render(
    <MemoryRouter>
      <AuthContext.Provider value={value}>
        <Header />
      </AuthContext.Provider>
    </MemoryRouter>,
  );
  return value;
}

describe("<Header />", () => {
  it("renders the Wedding Industry Ads logo", () => {
    renderHeader();
    expect(screen.getByAltText("Wedding Industry Ads")).toBeInTheDocument();
  });

  /* History was deliberately removed from the Command Center. The /history
     route still resolves if typed — only the entry point is gone — so this
     guards the header, not the router. */
  it("does not link to the audit history page from anywhere in the header", () => {
    renderHeader();
    expect(screen.queryByRole("link", { name: /history/i })).not.toBeInTheDocument();
    for (const link of screen.queryAllByRole("link")) {
      expect(link.getAttribute("href")).not.toBe("/history");
    }
  });

  it("opens the bookmarks board from the header", async () => {
    const user = userEvent.setup();
    renderHeader();
    expect(screen.queryByRole("dialog", { name: /bookmarks/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /bookmarks/i }));
    expect(await screen.findByRole("dialog", { name: /bookmarks/i })).toBeInTheDocument();
  });

  it("gives the Bookmarks pill the primary-CTA fill while the island is showing", async () => {
    const user = userEvent.setup();
    renderHeader();
    const pill = screen.getByRole("button", { name: /bookmarks/i });

    expect(pill).toHaveAttribute("aria-expanded", "false");
    expect(pill.className).not.toContain("bg-brand-primary");

    await user.click(pill);
    expect(pill).toHaveAttribute("aria-expanded", "true");
    // Same treatment as the hero's "View automations" button. That CTA is the
    // brand primary since the Wedding Industry Ads re-theme — it used to be
    // the hub's orange, which is not in their palette.
    expect(pill.className).toContain("bg-brand-primary");
    expect(pill.className).toContain("border-brand-primary");
    expect(pill.className).toContain("rgba(80,112,255,0.45)");
  });

  it("leaves Bookmarks as the only quick link, ahead of the user pill", () => {
    renderHeader();
    const bookmarks = screen.getByRole("button", { name: /bookmarks/i });
    const user = screen.getByRole("button", { name: /signed in as/i });
    // DOCUMENT_POSITION_FOLLOWING === 4 → the user pill comes after Bookmarks
    expect(bookmarks.compareDocumentPosition(user) & 4).toBeTruthy();
  });

  it("shows the user pill with a logout dropdown when signed in", async () => {
    const user = userEvent.setup();
    const auth = renderHeader();

    const pill = screen.getByRole("button", { name: /signed in as wahha design/i });
    await user.click(pill);

    const logoutItem = await screen.findByRole("menuitem", { name: /log out/i });
    expect(screen.getByText("team@wahha.design")).toBeInTheDocument();

    await user.click(logoutItem);
    expect(auth.logout).toHaveBeenCalledOnce();
  });

  it("shows a sign-in link instead of the pill when signed out", () => {
    renderHeader({ status: "unauthenticated", user: null });
    expect(screen.getByRole("link", { name: /sign in/i })).toHaveAttribute("href", "/login");
    expect(screen.queryByRole("button", { name: /signed in as/i })).not.toBeInTheDocument();
  });
});
