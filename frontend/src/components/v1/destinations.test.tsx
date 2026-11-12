import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuthContext, type AuthContextValue } from "@/context/auth";
import { expectFullPageLaunch, renderInRouter } from "@/test/launchLink";
import { CommandPalette } from "./CommandPalette";
import { NAV, ORBIT_CARDS } from "./destinations";
import { MobileNav, Sidebar } from "./Sidebar";

/* "Campaigns" is the Content Atelier. It used to deep-link an Ops Hub screen;
   the Atelier is its own app now, so the destination is its launch link. */

const auth: AuthContextValue = {
  status: "authenticated",
  user: { email: "team@example.com", name: "Team", role: "team" },
  login: vi.fn(),
  logout: vi.fn(),
};

const renderNav = () =>
  renderInRouter(
    <>
      <Sidebar />
      <MobileNav open onClose={() => {}} />
    </>,
  );

const renderPalette = () =>
  render(
    <AuthContext.Provider value={auth}>
      <CommandPalette open onClose={() => {}} />
    </AuthContext.Provider>,
  );

afterEach(() => {
  vi.unstubAllEnvs();
});

/* jsdom has no layout, so no scrollIntoView; the palette keeps its active row in view. */
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});
afterAll(() => {
  delete (Element.prototype as Partial<Element>).scrollIntoView;
});

describe("Campaigns destination", () => {
  /* The orbit carries only the three external sites now, so Campaigns is on the rail alone. */
  it("is the Atelier launch on the rail, and no destination opens a content screen", () => {
    const campaigns = [...NAV, ...ORBIT_CARDS].filter((d) => d.id === "campaigns");
    expect(campaigns).toHaveLength(1);
    for (const d of campaigns) expect(d.action).toEqual({ kind: "atelier" });
    for (const d of [...NAV, ...ORBIT_CARDS]) {
      if (d.action.kind === "route") expect(d.action.to).not.toContain("screen=content");
    }
  });

  it("launches the Atelier from the rail and the drawer when it is configured", async () => {
    vi.stubEnv("VITE_CONTENT_ATELIER_URL", "https://atelier.example.com/workspace");
    renderNav();
    const links = screen.getAllByRole("link", { name: "Campaigns" });
    expect(links).toHaveLength(2);
    for (const link of links) await expectFullPageLaunch(link);
  });

  it.each(["", "not-a-url", "javascript:alert(1)"])(
    "is disabled on the rail and the drawer without a configured Atelier: %s",
    (url) => {
      vi.stubEnv("VITE_CONTENT_ATELIER_URL", url);
      renderNav();
      const buttons = screen.getAllByRole("button", { name: "Campaigns" });
      expect(buttons).toHaveLength(2);
      for (const button of buttons) expect(button).toBeDisabled();
      expect(screen.queryByRole("link", { name: "Campaigns" })).not.toBeInTheDocument();
    },
  );

  it("is offered by the palette only when the Atelier is configured", () => {
    vi.stubEnv("VITE_CONTENT_ATELIER_URL", "https://atelier.example.com/");
    const { unmount } = renderPalette();
    expect(screen.getByRole("option", { name: /^Campaigns/ })).toBeInTheDocument();
    unmount();

    vi.stubEnv("VITE_CONTENT_ATELIER_URL", "");
    renderPalette();
    expect(screen.getByRole("option", { name: /^Resources/ })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /^(Leads|Insights|Settings)\b/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /^Campaigns/ })).not.toBeInTheDocument();
  });
});
