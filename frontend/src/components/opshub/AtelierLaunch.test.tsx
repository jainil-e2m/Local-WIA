import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useOpsHub } from "@/hooks/useOpsHub";
import { PALETTE_DEFS } from "@/data/opsHub";
import { INITIAL_STATE, PAGE_META, SCREEN_IDS, isScreenId } from "@/lib/opsHub";
import OpsHubPage from "@/pages/OpsHubPage";
import { expectFullPageLaunch, renderInRouter } from "@/test/launchLink";
import { OpsHubShell } from "./OpsHubShell";
import { HomeScreen } from "./screens/HomeScreen";

/* The Content Atelier left the hub for its own app. Every entry that used to
   open its screen is now the launch link: a full-page navigation through the
   sign-on hand-off where the Atelier is configured, disabled (or, in the
   palette, absent) where it is not. */

const PALETTE_QUESTION = "Which client-call moments could become WIA content?";

function Hub() {
  const hub = useOpsHub();
  return (
    <OpsHubShell hub={hub}>
      <HomeScreen hub={hub} />
    </OpsHubShell>
  );
}

const openPalette = () =>
  userEvent.click(screen.getByText("Ask a question about your operations…"));

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("Ops Hub — Content Atelier entries with the Atelier configured", () => {
  it("launches the Atelier from the sidebar, the mobile nav and the Home card", async () => {
    vi.stubEnv("VITE_CONTENT_ATELIER_URL", "https://atelier.example.com/workspace");
    renderInRouter(<Hub />, "/ops-hub");
    await expectFullPageLaunch(screen.getByRole("link", { name: "Content Atelier" }));
    await expectFullPageLaunch(screen.getByRole("link", { name: "Atelier" }));
    await expectFullPageLaunch(screen.getByRole("link", { name: "Open Content Atelier" }));
    expect(screen.queryByRole("button", { name: /atelier/i })).not.toBeInTheDocument();
  });

  it("answers the palette's content question with the launch link", async () => {
    vi.stubEnv("VITE_CONTENT_ATELIER_URL", "https://atelier.example.com/");
    renderInRouter(<Hub />, "/ops-hub");
    await openPalette();
    const dialog = screen.getByRole("dialog", { name: "Ask a question about your operations" });
    await expectFullPageLaunch(within(dialog).getByRole("link", { name: new RegExp(PALETTE_QUESTION) }));
  });
});

describe("Ops Hub — Content Atelier entries without the Atelier configured", () => {
  it.each(["", "not-a-url", "javascript:alert(1)"])(
    "disables the sidebar, mobile nav and Home entries: %s",
    (url) => {
      vi.stubEnv("VITE_CONTENT_ATELIER_URL", url);
      renderInRouter(<Hub />, "/ops-hub");
      for (const name of ["Content Atelier", "Atelier", "Open Content Atelier"]) {
        expect(screen.getByRole("button", { name })).toBeDisabled();
      }
      expect(screen.queryByRole("link", { name: /atelier/i })).not.toBeInTheDocument();
    },
  );

  it("leaves the content question out of the palette", async () => {
    vi.stubEnv("VITE_CONTENT_ATELIER_URL", "");
    renderInRouter(<Hub />, "/ops-hub");
    await openPalette();
    expect(screen.getByText("What needs my review today?")).toBeInTheDocument();
    expect(screen.queryByText(PALETTE_QUESTION)).not.toBeInTheDocument();
  });
});

describe("Ops Hub — no Content Atelier screen", () => {
  it("has no content screen id, page meta, palette target or state", () => {
    expect(SCREEN_IDS).not.toContain("content");
    expect(isScreenId("content")).toBe(false);
    expect(Object.keys(PAGE_META).sort()).toEqual([...SCREEN_IDS].sort());
    for (const def of PALETTE_DEFS) {
      if ("screen" in def) expect(SCREEN_IDS).toContain(def.screen);
    }
    expect(PALETTE_DEFS.filter((def) => "launch" in def).map((def) => def.dest)).toEqual([
      "Content Atelier",
    ]);
    expect(Object.keys(INITIAL_STATE).filter((key) => /^(content|atelier)/i.test(key))).toEqual(
      [],
    );
  });

  it("opens Home for an old ?screen=content link instead of an empty shell", async () => {
    vi.stubEnv("VITE_CONTENT_ATELIER_URL", "");
    renderInRouter(<OpsHubPage />, "/ops-hub?screen=content&signal=x&format=y");
    expect(screen.getByRole("heading", { level: 1, name: "Operations Overview" })).toBeInTheDocument();
    /* The address bar follows the state, so the dead keys drop out of it. */
    const location = screen.getByTestId("router-location");
    await waitFor(() => expect(location.textContent).toMatch(/[?&]screen=home(&|$)/));
    expect(location.textContent).not.toMatch(/content|signal=|format=/);
  });
});
