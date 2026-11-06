import { describe, it, expect, vi, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { MarbleVeins } from "./MarbleVeins";

/** jsdom has no matchMedia; answer every query with `matches`. */
function mockMatchMedia(matches: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  );
}

describe("MarbleVeins", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("renders nothing below 1100px, where the copy fills the width", () => {
    mockMatchMedia(false);
    const { container } = render(<MarbleVeins />);
    expect(container.querySelector("canvas")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
  });

  it("falls back to the still marble when WebGL is unavailable", () => {
    mockMatchMedia(true);
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    const { container } = render(<MarbleVeins />);
    expect(container.querySelector("canvas")).toBeNull();
    expect(container.querySelector("img")).toHaveAttribute("src", "/landing/marble-a.webp");
  });
});
