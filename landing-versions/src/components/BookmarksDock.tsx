import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { isAxiosError } from "axios";
import { AlertCircle, Copy, ExternalLink, Pencil, Plus, Search, Trash2, X } from "lucide-react";
import { BookmarkIcon } from "@/components/BookmarkIcon";
import { Tooltip } from "@/components/ui/tooltip";
import {
  createBookmark,
  deleteBookmark,
  fetchBookmarks,
  hostLabel,
  normalizeUrlInput,
  updateBookmark,
  type Bookmark,
  type BookmarksState,
} from "@/services/api/bookmarks";

interface BookmarksDockProps {
  open: boolean;
  onClose: () => void;
  /**
   * Called when the user interacts inside the island. Lets a hover-revealed
   * ("peek") island become sticky, so opening the centred add/edit dialog —
   * which draws the cursor away from the edge — can't make it vanish mid-task.
   */
  onPin?: () => void;
}

/* ── Island chrome ────────────────────────────────
   The surfaces are `chrome-island`, `chrome-panel` and `chrome-pill` in
   index.css: a chrome finish on the hero object's own sampled hues, over a
   #2c3fc4 blue ground. They live in CSS because the effect is a four-layer
   background stack with per-layer blend modes and a keyframed sheen, none of
   which Tailwind arbitrary values express without becoming unreadable.

   Those classes own `background` and `box-shadow`, so nothing here should
   add a bg-* or shadow-* utility to the same element.

   Only the hairlines stay here. White rather than a blue hex: on a polished
   surface the rim and the dividers read as a reflection, not a drawn line.
   Moving off near-black also cost the muted text its headroom, so every
   text-white/NN in this file sits a step brighter than the navy version —
   white/40 was 3.84:1 there and would be 2.56:1 here. */
const EDGE = "border-white/25";

/* The island is an icon rail at rest; searching needs a real text field, so it
   expands leftward (its right edge is anchored) to make room — the same trick
   the dynamic island itself uses. */
const RAIL_WIDTH = 92;
const SEARCH_WIDTH = 256;

type Draft = { mode: "create" } | { mode: "edit"; bookmark: Bookmark };
type Menu = { x: number; y: number; bookmark: Bookmark };

const errorText = (error: unknown, fallback: string) => {
  if (isAxiosError(error) && error.response) {
    const body = error.response.data as { message?: string; error?: string } | undefined;
    return body?.message ?? body?.error ?? fallback;
  }
  return "Can't reach the server.";
};

/**
 * The island's default height is the hero's content band: top edge level with
 * the "GOOD MORNING · <NAME>" eyebrow, bottom edge level with the 24/7 KPI
 * row. Those two elements carry data anchors in Hero.tsx; measuring them keeps
 * the alignment exact on every viewport instead of guessing a percentage.
 * Falls back to a centred 63svh column when the hero isn't on screen.
 */
function measureHeroBand(): { top: number; height: number } | null {
  const start = document.querySelector("[data-hero-band-start]");
  const end = document.querySelector("[data-hero-band-end]");
  if (!start || !end) return null;
  const MARGIN = 16;
  const top = Math.max(MARGIN, start.getBoundingClientRect().top);
  const bottom = Math.min(window.innerHeight - MARGIN, end.getBoundingClientRect().bottom);
  if (bottom - top < 260) return null; // scrolled away / degenerate — use the fallback
  return { top, height: bottom - top };
}

/**
 * Bookmarks dock — a dynamic-island-style shelf pinned to the right edge:
 * one scrollable column of favicon tiles at a fixed height that mirrors the
 * hero's content band (eyebrow at the top ↔ the 24/7 KPI at the bottom).
 *
 * No scrim, no blur: the dashboard stays fully visible; clicking anywhere
 * outside the island closes it. Left-click opens the URL in a new tab,
 * right-click opens a context menu, hover reveals name + host.
 */
export function BookmarksDock({ open, onClose, onPin }: BookmarksDockProps) {
  const [state, setState] = useState<BookmarksState>({ groups: [], bookmarks: [] });
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [menu, setMenu] = useState<Menu | null>(null);
  const [banner, setBanner] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [query, setQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);

  const dockRef = useRef<HTMLElement>(null);
  const [band, setBand] = useState<{ top: number; height: number } | null>(null);

  // Size the island to the hero band while open, tracking scroll and resize.
  useEffect(() => {
    if (!open) return;
    const update = () => setBand(measureHeroBand());
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open]);

  const load = useCallback(async () => {
    setLoadState("loading");
    try {
      setState(await fetchBookmarks());
      setLoadState("ready");
    } catch {
      setLoadState("error");
    }
  }, []);

  // Read latest layer state inside global handlers without re-binding them.
  const menuRef = useRef<Menu | null>(null);
  const draftRef = useRef<Draft | null>(null);
  const searchingRef = useRef(searching);
  menuRef.current = menu;
  draftRef.current = draft;
  searchingRef.current = searching;

  const exitSearch = useCallback(() => {
    setSearching(false);
    setQuery("");
  }, []);

  useEffect(() => {
    if (!open) return;
    setDraft(null);
    setMenu(null);
    setBanner(null);
    setSearching(false);
    setQuery("");
    void load();

    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      // Esc unwinds the innermost layer first
      if (menuRef.current) setMenu(null);
      else if (draftRef.current) setDraft(null);
      else if (searchingRef.current) exitSearch();
      else onClose();
    };

    // No scrim — the island closes when a click lands outside it and outside
    // any of its portalled layers (context menu, add/edit form).
    const onDown = (e: PointerEvent) => {
      const target = e.target as Element | null;
      if (!target) return;
      if (dockRef.current?.contains(target)) return;
      if (target.closest("[data-bookmarks-ui]")) return;
      if (menuRef.current || draftRef.current) return; // inner layers close themselves first
      onClose();
    };

    window.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [open, onClose, load, exitSearch]);

  // Focus the field as it appears so search is type-ready in one click.
  useEffect(() => {
    if (searching) searchInputRef.current?.focus();
  }, [searching]);

  const mutate = async (action: () => Promise<BookmarksState>, fallback: string) => {
    try {
      setState(await action());
      setBanner(null);
      return true;
    } catch (error) {
      setBanner(errorText(error, fallback));
      return false;
    }
  };

  /* Grouping is parked for now — the island shows one flat, ordered column.
     (The server still stores groupId, so nothing is lost if it returns.)
     Search matches the name and the URL, so "git" finds a bookmark named
     "Repos" pointing at github.com. */
  const items = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return state.bookmarks;
    return state.bookmarks.filter(
      (b) =>
        b.name.toLowerCase().includes(needle) || b.url.toLowerCase().includes(needle),
    );
  }, [state, query]);

  const filtering = query.trim().length > 0;
  const isEmpty = loadState === "ready" && items.length === 0;

  /* Portalled to <body> deliberately. The header this is mounted from carries a
     framer transform, and a transformed ancestor becomes the containing block
     for position:fixed descendants — the island would otherwise be measured
     against the 76px header strip instead of the viewport. */
  return createPortal(
    <AnimatePresence>
      {open && (
        <>
          {/* Positioning wrapper is static so the slide-in transform can't
              fight the positioning offsets. Its box IS the hero content band
              (eyebrow → 24/7 KPI), measured live; centred fallback otherwise. */}
          <div
            className="pointer-events-none fixed right-4 z-[85]"
            style={
              band
                ? { top: band.top, height: band.height }
                : { top: "50%", height: "63svh", transform: "translateY(-50%)" }
            }
          >
            <motion.aside
              ref={dockRef}
              initial={{ x: 130, opacity: 0 }}
              animate={{ x: 0, opacity: 1, width: searching ? SEARCH_WIDTH : RAIL_WIDTH }}
              exit={{ x: 130, opacity: 0, transition: { duration: 0.2 } }}
              transition={{ type: "spring", stiffness: 300, damping: 30, mass: 0.9 }}
              role="dialog"
              aria-label="Bookmarks"
              onPointerDownCapture={onPin}
              className={`pointer-events-auto flex h-full flex-col overflow-hidden rounded-[30px] chrome-island`}
            >
              {/* header — a search affordance at rest, a real field once active */}
              <div className={`flex items-center gap-2 border-b ${EDGE} px-3 py-3 ${
                searching ? "bg-[#141c66]/90" : ""
              }`}>
                {searching ? (
                  <>
                    <Search className="h-[15px] w-[15px] shrink-0 text-white/70" aria-hidden />
                    <input
                      ref={searchInputRef}
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Search"
                      aria-label="Search bookmarks"
                      className="min-w-0 flex-1 bg-transparent text-[13px] font-medium text-white placeholder:text-white/60 outline-none"
                    />
                    <button
                      type="button"
                      onClick={exitSearch}
                      aria-label="Close search"
                      className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-white/25 bg-white/[0.06] text-white/85 transition-colors hover:bg-white/[0.14] hover:text-white"
                    >
                      <X className="h-[13px] w-[13px]" />
                    </button>
                  </>
                ) : (
                  <div className="flex w-full items-center justify-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => setSearching(true)}
                      aria-label="Search bookmarks"
                      className="grid h-7 w-7 place-items-center rounded-full border border-white/25 bg-white/[0.06] text-white/85 transition-colors hover:bg-white/[0.14] hover:text-white"
                    >
                      <Search className="h-[13px] w-[13px]" />
                    </button>
                    <button
                      type="button"
                      onClick={onClose}
                      aria-label="Close bookmarks"
                      className="grid h-7 w-7 place-items-center rounded-full border border-white/25 bg-white/[0.06] text-white/85 transition-colors hover:bg-white/[0.14] hover:text-white"
                    >
                      <X className="h-[13px] w-[13px]" />
                    </button>
                  </div>
                )}
              </div>

              {/* the column */}
              <div
                className={`scrollbar-themed flex-1 overflow-y-auto overscroll-contain px-3 py-3 ${
                  isEmpty || loadState !== "ready" ? "grid place-items-center" : ""
                }`}
              >
                {loadState === "loading" && (
                  <p className="rounded-xl bg-[#141c66]/85 px-2.5 py-1.5 text-center text-[10px] text-white">
                    Loading…
                  </p>
                )}

                {loadState === "error" && (
                  <button
                    type="button"
                    onClick={() => void load()}
                    className="rounded-full border border-[#6478e6] bg-white/[0.05] px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-white/85 transition-colors hover:bg-white/[0.12] hover:text-white"
                  >
                    Retry
                  </button>
                )}

                {isEmpty && (
                  <p className="rounded-xl bg-[#141c66]/85 px-2.5 py-2 text-center text-[10px] leading-relaxed text-white">
                    {filtering ? "No matches." : "No bookmarks yet — add one below."}
                  </p>
                )}

                {loadState === "ready" && !isEmpty && (
                  <div className={`flex flex-col gap-2.5 ${searching ? "" : "items-center"}`}>
                    {items.map((bookmark) => (
                      <BookmarkRow
                        key={bookmark.id}
                        bookmark={bookmark}
                        /* Room for labels once expanded — far easier to scan
                           search results by name than by favicon alone. */
                        showLabel={searching}
                        onContextMenu={(x, y) => setMenu({ x, y, bookmark })}
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* footer — the one action that matters */}
              <div className={`flex justify-center border-t ${EDGE} px-3 py-3`}>
                <Tooltip
                  focusable={false}
                  content="Add bookmark"
                  className="flex"
                  label="Add bookmark"
                >
                  <button
                    type="button"
                    onClick={() => setDraft({ mode: "create" })}
                    aria-label="Add bookmark"
                    className="grid h-10 w-10 place-items-center rounded-full chrome-pill text-brand-primary transition-transform duration-200 hover:scale-105"
                  >
                    <Plus className="h-[18px] w-[18px]" aria-hidden />
                  </button>
                </Tooltip>
              </div>
            </motion.aside>
          </div>

          {banner && (
            <div
              role="alert"
              className="fixed bottom-6 left-1/2 z-[96] flex max-w-md -translate-x-1/2 items-start gap-2.5 rounded-2xl border border-[#f2756b]/35 bg-[#151d4b]/95 px-4 py-3 text-[13px] font-medium text-[#f6a49d] shadow-[0_24px_60px_-16px_rgba(0,0,0,0.7)]"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              {banner}
            </div>
          )}

          {menu && (
            <ContextMenu
              menu={menu}
              onClose={() => setMenu(null)}
              onEdit={(bookmark) => setDraft({ mode: "edit", bookmark })}
              onDelete={(bookmark) =>
                void mutate(() => deleteBookmark(bookmark.id), "Couldn't delete the bookmark.")
              }
            />
          )}

          {draft && (
            <BookmarkDialog
              draft={draft}
              onCancel={() => setDraft(null)}
              onSubmit={async (values) => {
                const ok =
                  draft.mode === "create"
                    ? await mutate(() => createBookmark(values), "Couldn't add the bookmark.")
                    : await mutate(
                        () => updateBookmark(draft.bookmark.id, values),
                        "Couldn't update the bookmark.",
                      );
                if (ok) setDraft(null);
                return ok;
              }}
            />
          )}
        </>
      )}
    </AnimatePresence>,
    document.body,
  );
}

/**
 * One row of the column. The Tooltip wrapper carries the sizing so it has a
 * real layout box to anchor against — `display: contents` would generate no
 * box and the bubble would land in the page corner.
 */
function BookmarkRow({
  bookmark,
  showLabel = false,
  onContextMenu,
}: {
  bookmark: Bookmark;
  showLabel?: boolean;
  onContextMenu: (x: number, y: number) => void;
}) {
  const onContext = (e: React.MouseEvent) => {
    e.preventDefault(); // our menu replaces the browser's
    onContextMenu(e.clientX, e.clientY);
  };

  // Expanded: a full-width row with the name beside the favicon. The tooltip is
  // redundant here, so it is dropped rather than duplicating visible text.
  if (showLabel) {
    return (
      <a
        href={bookmark.url}
        target="_blank"
        rel="noopener noreferrer"
        onContextMenu={onContext}
        className="flex w-full items-center gap-2.5 rounded-[14px] border border-white/20 bg-[#141c66]/90 p-2 outline-none transition-colors hover:border-white/30 hover:bg-white/[0.09] focus-visible:ring-2 focus-visible:ring-white/50"
      >
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-[11px] border border-white/20 bg-white/95">
          <BookmarkIcon url={bookmark.url} name={bookmark.name} className="h-5 w-5" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[12.5px] font-semibold text-white/95">
            {bookmark.name}
          </span>
          <span className="block truncate text-[10.5px] text-white/70">
            {hostLabel(bookmark.url)}
          </span>
        </span>
      </a>
    );
  }

  return (
    <Tooltip
      focusable={false}
      className="flex h-12 w-12"
      label={`${bookmark.name} — ${hostLabel(bookmark.url)}`}
      content={
        <span className="flex flex-col gap-0.5">
          <span className="font-semibold">{bookmark.name}</span>
          <span className="text-white/75">{hostLabel(bookmark.url)}</span>
        </span>
      }
    >
      <a
        href={bookmark.url}
        target="_blank"
        rel="noopener noreferrer"
        onContextMenu={onContext}
        className="grid h-full w-full place-items-center rounded-[14px] border border-white/20 bg-white/95 outline-none transition-transform duration-200 hover:scale-[1.08] focus-visible:ring-2 focus-visible:ring-white/60"
      >
        <BookmarkIcon url={bookmark.url} name={bookmark.name} className="h-7 w-7" />
      </a>
    </Tooltip>
  );
}

function ContextMenu({
  menu,
  onClose,
  onEdit,
  onDelete,
}: {
  menu: Menu;
  onClose: () => void;
  onEdit: (bookmark: Bookmark) => void;
  onDelete: (bookmark: Bookmark) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ left: menu.x, top: menu.y });

  // Keep the menu on screen when opened near an edge (the island hugs the right).
  useEffect(() => {
    const box = ref.current?.getBoundingClientRect();
    if (!box) return;
    setPos({
      left: Math.max(8, Math.min(menu.x, window.innerWidth - box.width - 8)),
      top: Math.max(8, Math.min(menu.y, window.innerHeight - box.height - 8)),
    });
  }, [menu.x, menu.y]);

  useEffect(() => {
    const onDown = (e: PointerEvent) => {
      if (!ref.current?.contains(e.target as Node)) onClose();
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [onClose]);

  const item =
    "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-[13px] font-medium text-white/95 transition-colors hover:bg-white/[0.1] hover:text-white";

  return createPortal(
    <div
      ref={ref}
      role="menu"
      data-bookmarks-ui
      style={{ left: pos.left, top: pos.top }}
      className={`fixed z-[100] w-52 rounded-2xl border ${EDGE} chrome-panel p-1.5 drop-shadow-[0_24px_60px_rgba(6,9,34,0.65)]`}
    >
      <p className="truncate px-3 pb-1.5 pt-1 text-[11px] font-bold uppercase tracking-[0.14em] text-white/70">
        {menu.bookmark.name}
      </p>
      <a
        href={menu.bookmark.url}
        target="_blank"
        rel="noopener noreferrer"
        role="menuitem"
        onClick={onClose}
        className={item}
      >
        <ExternalLink className="h-[15px] w-[15px] text-white/75" aria-hidden />
        Open in new tab
      </a>
      <button
        type="button"
        role="menuitem"
        onClick={() => {
          void navigator.clipboard?.writeText(menu.bookmark.url);
          onClose();
        }}
        className={item}
      >
        <Copy className="h-[15px] w-[15px] text-white/75" aria-hidden />
        Copy link
      </button>
      <button
        type="button"
        role="menuitem"
        onClick={() => {
          onEdit(menu.bookmark);
          onClose();
        }}
        className={item}
      >
        <Pencil className="h-[15px] w-[15px] text-white/75" aria-hidden />
        Edit
      </button>
      <div className="mx-2 my-1 h-px bg-white/10" aria-hidden />
      <button
        type="button"
        role="menuitem"
        onClick={() => {
          onDelete(menu.bookmark);
          onClose();
        }}
        className={`${item} text-[#ffd0cb] hover:bg-[#f2756b]/25 hover:text-white`}
      >
        <Trash2 className="h-[15px] w-[15px]" aria-hidden />
        Delete
      </button>
    </div>,
    document.body,
  );
}

function BookmarkDialog({
  draft,
  onCancel,
  onSubmit,
}: {
  draft: Draft;
  onCancel: () => void;
  onSubmit: (values: { url: string; name?: string }) => Promise<boolean>;
}) {
  const editing = draft.mode === "edit";
  const [url, setUrl] = useState(editing ? draft.bookmark.url : "");
  const [name, setName] = useState(editing ? draft.bookmark.name : "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const field =
    "w-full rounded-2xl border border-[#6478e6] bg-white/[0.05] px-4 py-2.5 text-[14px] font-medium text-white placeholder:text-white/60 outline-none transition-colors focus:border-white";
  const label =
    "mb-1.5 block text-[11.5px] font-semibold uppercase tracking-[0.16em] text-white/85";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const normalized = normalizeUrlInput(url);
    if (!normalized) {
      setError("Enter a valid web address, e.g. web.telegram.org");
      return;
    }
    setError(null);
    setSaving(true);
    await onSubmit({ url: normalized, name: name.trim() });
    setSaving(false);
  }

  return createPortal(
    <div
      data-bookmarks-ui
      className="fixed inset-0 z-[95] grid place-items-center bg-[#0a0f26]/70 px-4 backdrop-blur-sm"
      onClick={onCancel}
    >
      <form
        onSubmit={submit}
        onClick={(e) => e.stopPropagation()}
        aria-label={editing ? "Edit bookmark" : "Add bookmark"}
        className={`w-full max-w-[420px] rounded-[24px] border ${EDGE} chrome-panel p-6 drop-shadow-[0_40px_110px_rgba(6,9,34,0.6)]`}
      >
        <h3 className="text-[18px] font-extrabold text-white">
          {editing ? "Edit bookmark" : "Add bookmark"}
        </h3>

        <div className="mt-5 space-y-3.5">
          <div>
            <label htmlFor="bookmark-url" className={label}>
              Web address
            </label>
            {/* autofocus is correct here: the dialog exists to capture this field */}
            <input
              id="bookmark-url"
              autoFocus
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="web.telegram.org"
              aria-invalid={Boolean(error)}
              className={field}
            />
          </div>
          <div>
            <label htmlFor="bookmark-name" className={label}>
              Name <span className="font-medium normal-case text-white/60">(optional)</span>
            </label>
            <input
              id="bookmark-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Defaults to the site’s domain"
              className={field}
            />
          </div>
        </div>

        {error && (
          <p role="alert" className="mt-3 text-[13px] font-medium text-[#f6a49d]">
            {error}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-2.5">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-full px-4 py-2 text-[12px] font-bold uppercase tracking-[0.14em] text-white/80 transition-colors hover:text-white"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="rounded-full chrome-pill px-5 py-2 text-[12px] font-bold uppercase tracking-[0.14em] text-[#2c3fc4] transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Saving…" : editing ? "Save" : "Add"}
          </button>
        </div>
      </form>
    </div>,
    document.body,
  );
}
