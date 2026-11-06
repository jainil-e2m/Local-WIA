import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useEdgeReveal } from "./useEdgeReveal";

/** jsdom reports clientWidth 0, so pin a known layout width for the maths. */
const VIEWPORT = 1000;

beforeEach(() => {
  vi.useFakeTimers();
  Object.defineProperty(document.documentElement, "clientWidth", {
    value: VIEWPORT,
    configurable: true,
  });
});

afterEach(() => {
  vi.useRealTimers();
});

/** Move the mouse to `distance` px from the right edge. */
const moveTo = (distance: number, pointerType = "mouse") =>
  act(() => {
    document.dispatchEvent(
      new PointerEvent("pointermove", {
        clientX: VIEWPORT - distance,
        pointerType,
        bubbles: true,
      }),
    );
  });

const advance = (ms: number) => act(() => void vi.advanceTimersByTime(ms));

describe("useEdgeReveal", () => {
  it("starts closed", () => {
    const { result } = renderHook(() => useEdgeReveal());
    expect(result.current.mode).toBe("closed");
    expect(result.current.isOpen).toBe(false);
  });

  it("peeks open once the cursor lingers at the right edge", () => {
    const { result } = renderHook(() => useEdgeReveal());
    moveTo(2);
    expect(result.current.mode).toBe("closed"); // dwell not yet elapsed
    advance(150);
    expect(result.current.mode).toBe("peek");
    expect(result.current.isOpen).toBe(true);
  });

  it("does NOT open on a quick brush past the edge (dwell guard)", () => {
    const { result } = renderHook(() => useEdgeReveal());
    moveTo(2);
    advance(60); // still inside the dwell window
    moveTo(400); // moved away again
    advance(500);
    expect(result.current.mode).toBe("closed");
  });

  it("auto-dismisses a peek once the cursor moves well away", () => {
    const { result } = renderHook(() => useEdgeReveal());
    moveTo(2);
    advance(150);
    expect(result.current.mode).toBe("peek");

    moveTo(400);
    expect(result.current.mode).toBe("peek"); // grace period still running
    advance(300);
    expect(result.current.mode).toBe("closed");
  });

  it("keeps a peek open while the cursor is over the island itself", () => {
    const { result } = renderHook(() => useEdgeReveal());
    moveTo(2);
    advance(150);

    moveTo(60); // island footprint is ~16-108px from the edge
    advance(500);
    expect(result.current.mode).toBe("peek");
  });

  it("returning to the edge cancels a pending dismissal", () => {
    const { result } = renderHook(() => useEdgeReveal());
    moveTo(2);
    advance(150);

    moveTo(400); // starts the grace timer
    advance(100);
    moveTo(2); // back before it expires
    advance(500);
    expect(result.current.mode).toBe("peek");
  });

  it("ignores touch pointers — the edge must not become a dead zone", () => {
    const { result } = renderHook(() => useEdgeReveal());
    moveTo(2, "touch");
    advance(500);
    expect(result.current.mode).toBe("closed");
  });

  it("a pinned island is never dismissed by cursor movement", () => {
    const { result } = renderHook(() => useEdgeReveal());
    act(() => result.current.pin());
    expect(result.current.mode).toBe("pinned");

    moveTo(900);
    advance(1000);
    expect(result.current.mode).toBe("pinned");
  });

  it("pin promotes a peek so interacting inside can't dismiss it", () => {
    const { result } = renderHook(() => useEdgeReveal());
    moveTo(2);
    advance(150);
    expect(result.current.mode).toBe("peek");

    act(() => result.current.pin());
    moveTo(900); // e.g. cursor travels to the centred add dialog
    advance(1000);
    expect(result.current.mode).toBe("pinned");
  });

  it("toggle pins from closed and closes from either open mode", () => {
    const { result } = renderHook(() => useEdgeReveal());
    act(() => result.current.toggle());
    expect(result.current.mode).toBe("pinned");

    act(() => result.current.toggle());
    expect(result.current.mode).toBe("closed");

    // a peek counts as open, so the button closes rather than re-opening
    moveTo(2);
    advance(150);
    expect(result.current.mode).toBe("peek");
    act(() => result.current.toggle());
    expect(result.current.mode).toBe("closed");
  });

  it("dismisses a peek when the pointer leaves the document", () => {
    const { result } = renderHook(() => useEdgeReveal());
    moveTo(2);
    advance(150);

    act(() => void document.dispatchEvent(new PointerEvent("pointerleave", { bubbles: true })));
    advance(300);
    expect(result.current.mode).toBe("closed");
  });

  it("close() drops out of a peek immediately", () => {
    const { result } = renderHook(() => useEdgeReveal());
    moveTo(2);
    advance(150);
    act(() => result.current.close());
    expect(result.current.mode).toBe("closed");
  });
});
