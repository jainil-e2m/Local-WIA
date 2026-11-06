import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ExploreSection } from "./ExploreSection";

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

describe("Content Atelier destination", () => {
  it("opens the configured deployed app, including its path", () => {
    vi.stubEnv("VITE_CONTENT_ATELIER_URL", "https://atelier.example.com/workspace?source=command-center");
    render(<ExploreSection />);
    expect(screen.getByRole("link", { name: "View Content Atelier" })).toHaveAttribute(
      "href", "https://atelier.example.com/workspace?source=command-center",
    );
    expect(screen.queryByRole("button", { name: "View Here" })).not.toBeInTheDocument();
  });

  it.each(["", "not-a-url", "javascript:alert(1)"])("stays unavailable for an unconfigured or invalid destination: %s", (url) => {
    vi.stubEnv("VITE_CONTENT_ATELIER_URL", url);
    render(<ExploreSection />);
    expect(screen.getByRole("button", { name: "View Here" })).toBeDisabled();
    expect(screen.getByText("In development")).toBeInTheDocument();
    expect(screen.getAllByText("Coming soon")).toHaveLength(2);
    expect(screen.queryByRole("link", { name: "View Content Atelier" })).not.toBeInTheDocument();
  });
});
