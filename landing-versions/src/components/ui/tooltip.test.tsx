import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, render, screen, fireEvent } from "@testing-library/react";
import { Tooltip } from "./tooltip";

/** Advance past the open delay. */
const settle = () => act(() => void vi.advanceTimersByTime(200));

describe("<Tooltip />", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("stays hidden until hovered", () => {
    render(
      <Tooltip content="Technical SEO">
        <span>bar</span>
      </Tooltip>,
    );
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("opens on hover after the delay and closes on leave", () => {
    render(
      <Tooltip content="Technical SEO">
        <span>bar</span>
      </Tooltip>,
    );
    const trigger = screen.getByText("bar").parentElement!;

    fireEvent.pointerEnter(trigger);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument(); // still within the delay
    settle();
    expect(screen.getByRole("tooltip")).toHaveTextContent("Technical SEO");

    fireEvent.pointerLeave(trigger);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("opens on keyboard focus and closes on blur", () => {
    render(
      <Tooltip content="Technical SEO">
        <span>bar</span>
      </Tooltip>,
    );
    const trigger = screen.getByText("bar").parentElement!;

    fireEvent.focus(trigger);
    settle();
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    fireEvent.blur(trigger);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("wires aria-describedby to the bubble while open", () => {
    render(
      <Tooltip content="Technical SEO">
        <span>bar</span>
      </Tooltip>,
    );
    const trigger = screen.getByText("bar").parentElement!;
    expect(trigger).not.toHaveAttribute("aria-describedby");

    fireEvent.pointerEnter(trigger);
    settle();
    expect(trigger.getAttribute("aria-describedby")).toBe(screen.getByRole("tooltip").id);
  });

  it("closes on pointerdown so it never fights a drag", () => {
    render(
      <Tooltip content="Technical SEO">
        <span>bar</span>
      </Tooltip>,
    );
    const trigger = screen.getByText("bar").parentElement!;
    fireEvent.pointerEnter(trigger);
    settle();
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    fireEvent.pointerDown(trigger);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("closes on Escape", () => {
    render(
      <Tooltip content="Technical SEO">
        <span>bar</span>
      </Tooltip>,
    );
    fireEvent.pointerEnter(screen.getByText("bar").parentElement!);
    settle();
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("renders no tooltip (and is not focusable) without content", () => {
    render(
      <Tooltip>
        <span>bar</span>
      </Tooltip>,
    );
    const trigger = screen.getByText("bar").parentElement!;
    expect(trigger).not.toHaveAttribute("tabindex");

    fireEvent.pointerEnter(trigger);
    settle();
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("keeps an opaque surface (guards the dropped-opacity-class bug)", () => {
    // `bg-[#141a45]/97` silently produced NO background: Tailwind's opacity
    // scale stops at 95/100, so the class never generated. Pin the explicit rgba.
    render(
      <Tooltip content="x">
        <span>bar</span>
      </Tooltip>,
    );
    fireEvent.pointerEnter(screen.getByText("bar").parentElement!);
    settle();
    expect(screen.getByRole("tooltip").className).toContain("bg-[rgba(20,26,69,0.97)]");
  });

  it("passes className and style through to the trigger", () => {
    render(
      <Tooltip content="x" className="absolute rounded-full" style={{ width: "40%" }}>
        <span>bar</span>
      </Tooltip>,
    );
    const trigger = screen.getByText("bar").parentElement!;
    expect(trigger).toHaveClass("absolute", "rounded-full");
    expect(trigger).toHaveStyle({ width: "40%" });
  });
});
