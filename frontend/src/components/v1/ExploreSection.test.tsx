import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { TIMELINE_URL } from "./destinations";
import { ExploreSection } from "./ExploreSection";
import { V1ActionContext } from "./useV1Action";

beforeEach(() => {
  vi.stubGlobal("IntersectionObserver", class {
    observe() {}
    unobserve() {}
    disconnect() {}
  });
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

const renderSection = (run = vi.fn()) =>
  render(
    <MemoryRouter>
      <V1ActionContext.Provider value={run}>
        <ExploreSection />
      </V1ActionContext.Provider>
    </MemoryRouter>,
  );

describe("Content Atelier destination", () => {
  it("opens the authenticated server handoff when a deployed app is configured", () => {
    vi.stubEnv("VITE_CONTENT_ATELIER_URL", "https://atelier.example.com/workspace?source=command-center");
    renderSection();
    expect(screen.getByRole("link", { name: "View Content Atelier" })).toHaveAttribute(
      "href", "/api/auth/content-atelier/launch",
    );
    expect(screen.queryByRole("button", { name: "View Here" })).not.toBeInTheDocument();
    expect(screen.getByText("Live")).toBeInTheDocument();
    expect(screen.queryByText("In development")).not.toBeInTheDocument();
  });

  it.each(["", "not-a-url", "javascript:alert(1)"])("stays unavailable for an unconfigured or invalid destination: %s", (url) => {
    vi.stubEnv("VITE_CONTENT_ATELIER_URL", url);
    renderSection();
    expect(screen.getByRole("button", { name: "View Here" })).toBeDisabled();
    expect(screen.queryByRole("link", { name: "View Content Atelier" })).not.toBeInTheDocument();
  });
});

describe("Automation library", () => {
  it("shows the Atelier live and the two roadmap builds coming soon, in that order", () => {
    renderSection();
    expect(screen.getAllByRole("article").map((a) => a.getAttribute("aria-labelledby"))).toEqual([
      "v1-tile-content-atelier",
      "v1-tile-client-knowledge-base",
      "v1-tile-paid-media-reporting",
    ]);
    expect(within(screen.getByRole("article", { name: "Content Atelier" })).getByText("Live")).toBeInTheDocument();
    for (const name of ["Client Knowledge Base", "Paid Media Reporting"]) {
      const tile = screen.getByRole("article", { name });
      expect(within(tile).getByText("Coming soon")).toBeInTheDocument();
    }
  });

  it("opens the deployed build timeline in a new tab from a card that is coming soon", () => {
    renderSection();
    for (const name of ["Client Knowledge Base", "Paid Media Reporting"]) {
      const link = within(screen.getByRole("article", { name })).getByRole("link", { name: /View timeline/ });
      expect(link).toHaveAttribute("href", TIMELINE_URL);
      expect(link).toHaveAttribute("target", "_blank");
    }
  });

  it("keeps the library's introduction behind the info button, as its description", () => {
    renderSection();
    const info = screen.getByRole("button", { name: "About the Automation Library" });
    expect(info).toHaveAccessibleDescription(/Plug in proven automations/);
    fireEvent.click(info);
    expect(info).toHaveAttribute("aria-expanded", "true");
  });

  it("narrows the cards by search and by area, and says when nothing matches", async () => {
    renderSection();
    const ids = () => screen.queryAllByRole("article").map((a) => a.getAttribute("aria-labelledby"));
    const search = screen.getByRole("searchbox", { name: "Search automations" });
    fireEvent.change(search, { target: { value: "benchmarks" } });
    await waitFor(() => expect(ids()).toEqual(["v1-tile-paid-media-reporting"]));
    fireEvent.change(search, { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Knowledge" }));
    await waitFor(() => expect(ids()).toEqual(["v1-tile-client-knowledge-base"]));
    fireEvent.change(search, { target: { value: "caption" } });
    await waitFor(() => expect(ids()).toEqual([]));
    expect(screen.getByRole("status")).toHaveTextContent("No automations match");
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    await waitFor(() => expect(ids()).toHaveLength(3));
  });
});
