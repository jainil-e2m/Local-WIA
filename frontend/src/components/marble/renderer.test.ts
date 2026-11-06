import { describe, it, expect, vi, afterEach } from "vitest";
import { createMarbleRenderer, cycleClock, renderScale, MAX_PIXELS } from "./renderer";

describe("renderScale", () => {
  it("uses the device pixel ratio when the canvas is small", () => {
    expect(renderScale(800, 700, 2)).toBe(2);
    expect(renderScale(800, 700, 1)).toBe(1);
  });

  it("never renders above 2x, even on 3x displays", () => {
    expect(renderScale(400, 400, 3)).toBe(2);
  });

  it("never renders below 1x on a low-density display", () => {
    expect(renderScale(400, 400, 0.5)).toBe(1);
  });

  it("caps the backing store so a large retina window stays affordable", () => {
    const r = renderScale(1380, 1440, 2);
    expect(r).toBeLessThan(2);
    expect(1380 * 1440 * r * r).toBeLessThanOrEqual(MAX_PIXELS + 1);
  });
});

describe("cycleClock", () => {
  it("counts cycles of the given period", () => {
    expect(cycleClock(0, 13)).toBe(0);
    expect(cycleClock(26, 13)).toBeCloseTo(2);
    expect(cycleClock(19.5, 13)).toBeCloseTo(1.5);
  });

  it("wraps after 97 cycles, the period the shader's vein picker repeats on", () => {
    expect(cycleClock(97 * 13, 13)).toBeCloseTo(0);
    expect(cycleClock(98.25 * 13, 13)).toBeCloseTo(1.25);
  });
});

describe("createMarbleRenderer", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns null when the browser has no WebGL, so the caller can fall back", () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    expect(createMarbleRenderer(document.createElement("canvas"))).toBeNull();
  });
});
