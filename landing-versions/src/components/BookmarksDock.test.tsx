import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BookmarksDock } from "./BookmarksDock";
import type { BookmarksState } from "@/services/api/bookmarks";

/* The dock talks to the server on mount; stub that surface so these tests are
   about the island's own behaviour (search, labels, layers). */
vi.mock("@/services/api/bookmarks", async () => {
  const actual =
    await vi.importActual<typeof import("@/services/api/bookmarks")>(
      "@/services/api/bookmarks",
    );
  return {
    ...actual, // keep the real normalizeUrlInput / hostLabel helpers
    fetchBookmarks: vi.fn(),
    createBookmark: vi.fn(),
    updateBookmark: vi.fn(),
    deleteBookmark: vi.fn(),
  };
});

const api = await import("@/services/api/bookmarks");

const state: BookmarksState = {
  groups: [],
  bookmarks: [
    { id: "1", url: "https://github.com/", name: "GitHub", groupId: null, order: 0, createdAt: 1 },
    { id: "2", url: "https://figma.com/", name: "Figma", groupId: null, order: 1, createdAt: 2 },
    // name deliberately unlike the host, to prove the URL is searched too
    { id: "3", url: "https://notion.so/", name: "Docs", groupId: null, order: 2, createdAt: 3 },
  ],
};

beforeEach(() => {
  vi.mocked(api.fetchBookmarks).mockResolvedValue(state);
});

const openDock = async () => {
  render(<BookmarksDock open onClose={vi.fn()} />);
  await waitFor(() => expect(screen.getAllByRole("link")).toHaveLength(3));
};

describe("<BookmarksDock /> search", () => {
  it("shows a search affordance at rest, not a 'Saved' label", async () => {
    await openDock();
    expect(screen.getByRole("button", { name: "Search bookmarks" })).toBeInTheDocument();
    expect(screen.queryByText(/saved/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("reveals a focused input when the search icon is clicked", async () => {
    const user = userEvent.setup();
    await openDock();

    await user.click(screen.getByRole("button", { name: "Search bookmarks" }));
    const input = screen.getByRole("textbox", { name: "Search bookmarks" });
    expect(input).toBeInTheDocument();
    expect(input).toHaveFocus();
  });

  it("filters the column by name as you type", async () => {
    const user = userEvent.setup();
    await openDock();
    await user.click(screen.getByRole("button", { name: "Search bookmarks" }));

    await user.type(screen.getByRole("textbox", { name: "Search bookmarks" }), "fig");
    await waitFor(() => expect(screen.getAllByRole("link")).toHaveLength(1));
    expect(screen.getByText("Figma")).toBeInTheDocument();
  });

  it("also matches the URL, so a differently-named bookmark is findable", async () => {
    const user = userEvent.setup();
    await openDock();
    await user.click(screen.getByRole("button", { name: "Search bookmarks" }));

    // "notion" appears only in the URL of the bookmark named "Docs"
    await user.type(screen.getByRole("textbox", { name: "Search bookmarks" }), "notion");
    await waitFor(() => expect(screen.getAllByRole("link")).toHaveLength(1));
    expect(screen.getByText("Docs")).toBeInTheDocument();
  });

  it("is case-insensitive", async () => {
    const user = userEvent.setup();
    await openDock();
    await user.click(screen.getByRole("button", { name: "Search bookmarks" }));

    await user.type(screen.getByRole("textbox", { name: "Search bookmarks" }), "GITHUB");
    await waitFor(() => expect(screen.getAllByRole("link")).toHaveLength(1));
  });

  it("reports no matches rather than showing an empty column", async () => {
    const user = userEvent.setup();
    await openDock();
    await user.click(screen.getByRole("button", { name: "Search bookmarks" }));

    await user.type(screen.getByRole("textbox", { name: "Search bookmarks" }), "zzzz");
    await waitFor(() => expect(screen.getByText("No matches.")).toBeInTheDocument());
    expect(screen.queryAllByRole("link")).toHaveLength(0);
  });

  it("shows names beside favicons only while expanded", async () => {
    const user = userEvent.setup();
    await openDock();
    // collapsed rail: names live in tooltips, not in the column
    expect(screen.queryByText("GitHub")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Search bookmarks" }));
    expect(screen.getByText("GitHub")).toBeInTheDocument();
    expect(screen.getByText("github.com")).toBeInTheDocument();
  });

  it("closing search restores the rail and clears the filter", async () => {
    const user = userEvent.setup();
    await openDock();
    await user.click(screen.getByRole("button", { name: "Search bookmarks" }));
    await user.type(screen.getByRole("textbox", { name: "Search bookmarks" }), "fig");
    await waitFor(() => expect(screen.getAllByRole("link")).toHaveLength(1));

    await user.click(screen.getByRole("button", { name: "Close search" }));
    await waitFor(() => expect(screen.getAllByRole("link")).toHaveLength(3));
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("Escape exits search before it closes the island", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<BookmarksDock open onClose={onClose} />);
    await waitFor(() => expect(screen.getAllByRole("link")).toHaveLength(3));

    await user.click(screen.getByRole("button", { name: "Search bookmarks" }));
    await user.keyboard("{Escape}");

    // first Escape unwinds search only
    await waitFor(() => expect(screen.queryByRole("textbox")).not.toBeInTheDocument());
    expect(onClose).not.toHaveBeenCalled();

    // a second Escape then closes the island
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  it("keeps every bookmark link a safe new-tab link", async () => {
    await openDock();
    for (const link of screen.getAllByRole("link")) {
      expect(link).toHaveAttribute("target", "_blank");
      expect(link.getAttribute("rel")).toContain("noopener");
      expect(link.getAttribute("rel")).toContain("noreferrer");
    }
  });
});
