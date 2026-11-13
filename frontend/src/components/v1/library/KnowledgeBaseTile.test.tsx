import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { LIBRARY } from "./automations";
import { Tile } from "./Tile";

/* The Client Knowledge Base tile: live with "View Here" through the sign-on hand-off where the KB is deployed,
   on the roadmap where it isn't. */

const kb = LIBRARY.find((item) => item.id === "client-knowledge-base")!;

// The card's artwork only animates while on screen; jsdom has no IntersectionObserver.
vi.stubGlobal("IntersectionObserver", class { observe() {} unobserve() {} disconnect() {} });
afterEach(() => vi.unstubAllEnvs());

describe("Client Knowledge Base tile", () => {
  it("launches the Knowledge Base through the hand-off where it is deployed", () => {
    vi.stubEnv("VITE_KNOWLEDGE_BASE_URL", "https://kb.example.com/");
    render(<Tile item={kb} index={1} playing={false} />);
    expect(screen.getByRole("link", { name: "View Client Knowledge Base" })).toHaveAttribute("href", "/api/auth/knowledge-base/launch");
    expect(screen.getByText("Live")).toBeInTheDocument();
  });

  it("stays on the roadmap where it isn't configured", () => {
    vi.stubEnv("VITE_KNOWLEDGE_BASE_URL", "");
    render(<Tile item={kb} index={1} playing={false} />);
    expect(screen.queryByRole("link", { name: "View Client Knowledge Base" })).toBeNull();
    expect(screen.getByText("Coming soon")).toBeInTheDocument();
  });
});
