// Test helpers for the Content Atelier's launch link (lib/atelierLaunch.ts).
// A launch entry must be a full-page navigation to a server route, never an
// in-app route, so these render under a router with a probe that shows where
// the router is, and check that clicking the entry leaves it there.
import { createElement, type ReactNode } from "react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect } from "vitest";
import { ATELIER_LAUNCH_PATH } from "@/lib/atelierLaunch";

function RouterLocation() {
  const { pathname, search } = useLocation();
  return createElement("output", { "data-testid": "router-location" }, pathname + search);
}

/** Renders `ui` in a memory router at `path`, beside the location probe. */
export function renderInRouter(ui: ReactNode, path = "/") {
  return render(
    createElement(MemoryRouter, { initialEntries: [path] }, ui, createElement(RouterLocation)),
  );
}

/** A same-tab anchor to the launch route that the router does not intercept.
    A router <Link> would render the same href but move the probe on click. */
export async function expectFullPageLaunch(link: HTMLElement) {
  expect(link.tagName).toBe("A");
  expect(link).toHaveAttribute("href", ATELIER_LAUNCH_PATH);
  expect(link).not.toHaveAttribute("target");
  const before = screen.getByTestId("router-location").textContent;
  // jsdom cannot navigate, so cancel the default action once React has seen the
  // click: on the render container, whose React listener was added first. Not on
  // document, which a stopPropagation in a drawer or dialog would keep it from.
  let root: HTMLElement = link;
  while (root.parentElement && root.parentElement !== document.body) root = root.parentElement;
  const cancel = (event: Event) => event.preventDefault();
  root.addEventListener("click", cancel);
  try {
    await userEvent.click(link);
  } finally {
    root.removeEventListener("click", cancel);
  }
  expect(screen.getByTestId("router-location").textContent).toBe(before);
}
