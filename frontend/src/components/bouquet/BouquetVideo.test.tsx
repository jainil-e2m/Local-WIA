import { describe, it, expect, vi, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { BouquetVideo } from "./BouquetVideo";

/** jsdom has no matchMedia: answer the width query and the motion query. */
function mockMedia({ wide, reduce = false }: { wide: boolean; reduce?: boolean }) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      matches: query.includes("reduced-motion") ? reduce : wide,
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

describe("BouquetVideo", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("renders nothing below 1100px, where the florals are dropped", () => {
    mockMedia({ wide: false });
    const { container } = render(<BouquetVideo />);
    expect(container.firstChild).toBeNull();
  });

  it("shows only the still bouquet under reduced motion, and never loads the video", () => {
    mockMedia({ wide: true, reduce: true });
    const createElement = vi.spyOn(document, "createElement");
    const { container } = render(<BouquetVideo />);
    expect(container.querySelector("img")).toHaveAttribute("src", "/landing/bouquet-still.webp");
    expect(container.querySelector("canvas")).toBeNull();
    expect(createElement).not.toHaveBeenCalledWith("video");
  });

  it("keeps the still bouquet when WebGL is unavailable", () => {
    mockMedia({ wide: true });
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    const { container } = render(<BouquetVideo />);
    expect(container.querySelector("img")).toHaveAttribute("src", "/landing/bouquet-still.webp");
    expect(container.querySelector("canvas")).toBeNull();
  });
});
