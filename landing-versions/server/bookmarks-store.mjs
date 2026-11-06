/* ────────────────────────────────────────────────────────────────
   Bookmarks store — a single JSON document on disk.

   Deliberately not a database: the whole dataset is a few dozen KB
   (~200 bytes per bookmark), so a Postgres service would cost real
   money in RAM to hold what fits in a file. Point BOOKMARKS_FILE at a
   mounted volume to make it survive redeploys; without one the server
   still works, it just resets when the container is replaced (the same
   contract SESSION_SECRET has).

   Writes are atomic (temp file + rename) and serialized through one
   promise chain, so a crash or two concurrent requests can never leave
   a half-written document behind.
   ──────────────────────────────────────────────────────────────── */

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";

export const LIMITS = {
  bookmarks: 500, // bounds the file at ~100 KB
  groups: 40,
  nameLength: 60,
  urlLength: 2048,
};

const emptyState = () => ({ version: 1, groups: [], bookmarks: [] });

/**
 * Normalize a user-supplied URL, or return null if it isn't usable.
 *
 * Only http(s) is allowed. This is a security boundary, not tidiness: these
 * URLs are rendered straight into an `href`, so a stored `javascript:` or
 * `data:` URL would be persistent XSS against every user of the dashboard.
 */
export function normalizeUrl(raw) {
  if (typeof raw !== "string") return null;
  const trimmed = raw.trim();
  if (!trimmed || trimmed.length > LIMITS.urlLength) return null;
  // bare "example.com" is a URL the user means; assume https
  const hasScheme = /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(trimmed);
  let url;
  try {
    url = new URL(hasScheme ? trimmed : `https://${trimmed}`);
  } catch {
    return null;
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") return null;
  if (!url.hostname) return null;
  return url.toString();
}

/** Human label to fall back on when the user doesn't name a bookmark. */
export function defaultNameFor(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "Bookmark";
  }
}

const cleanLabel = (raw, fallback) => {
  const value = typeof raw === "string" ? raw.trim().slice(0, LIMITS.nameLength) : "";
  return value || fallback;
};

/** Drop anything malformed rather than trusting a hand-edited file. */
function sanitizeState(parsed) {
  if (!parsed || typeof parsed !== "object") return emptyState();
  const groups = Array.isArray(parsed.groups) ? parsed.groups : [];
  const bookmarks = Array.isArray(parsed.bookmarks) ? parsed.bookmarks : [];

  const cleanGroups = groups
    .filter((g) => g && typeof g.id === "string")
    .slice(0, LIMITS.groups)
    .map((g, i) => ({
      id: g.id,
      name: cleanLabel(g.name, "Group"),
      order: Number.isFinite(g.order) ? g.order : i,
    }));
  const groupIds = new Set(cleanGroups.map((g) => g.id));

  const cleanBookmarks = bookmarks
    .filter((b) => b && typeof b.id === "string")
    .map((b, i) => {
      const url = normalizeUrl(b.url);
      if (!url) return null;
      return {
        id: b.id,
        url,
        name: cleanLabel(b.name, defaultNameFor(url)),
        // a bookmark pointing at a deleted group falls back to Ungrouped
        groupId: typeof b.groupId === "string" && groupIds.has(b.groupId) ? b.groupId : null,
        order: Number.isFinite(b.order) ? b.order : i,
        createdAt: Number.isFinite(b.createdAt) ? b.createdAt : 0,
      };
    })
    .filter(Boolean)
    .slice(0, LIMITS.bookmarks);

  return { version: 1, groups: cleanGroups, bookmarks: cleanBookmarks };
}

export class BookmarksError extends Error {
  constructor(code, message, status = 400) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

/**
 * Open (or create) the store at `filePath`.
 *
 * State is held in memory and mirrored to disk on every mutation, so reads are
 * synchronous and free while the file stays the durable source of truth.
 */
export function createBookmarksStore(filePath, { now = () => Date.now() } = {}) {
  let state = emptyState();
  let durable = true;
  let loadError = null;

  try {
    if (fs.existsSync(filePath)) {
      state = sanitizeState(JSON.parse(fs.readFileSync(filePath, "utf8")));
    }
  } catch (error) {
    // A corrupt file must not take the whole server down — start empty and
    // surface it, leaving the bad file untouched for inspection.
    loadError = error instanceof Error ? error.message : String(error);
  }

  let writes = Promise.resolve();
  const persist = () => {
    const snapshot = JSON.stringify(state, null, 2);
    writes = writes.then(async () => {
      const tmp = `${filePath}.${crypto.randomUUID()}.tmp`;
      try {
        await fsp.mkdir(path.dirname(filePath), { recursive: true });
        await fsp.writeFile(tmp, snapshot, "utf8");
        await fsp.rename(tmp, filePath); // atomic swap
        durable = true;
      } catch (error) {
        durable = false;
        await fsp.rm(tmp, { force: true }).catch(() => {});
        console.error(
          JSON.stringify({
            event: "bookmarks_persist_failed",
            path: filePath,
            error: error instanceof Error ? error.message : String(error),
          }),
        );
      }
    });
    return writes;
  };

  const findBookmark = (id) => state.bookmarks.find((b) => b.id === id);
  const findGroup = (id) => state.groups.find((g) => g.id === id);
  const nextOrder = (items) => items.reduce((max, i) => Math.max(max, i.order + 1), 0);

  return {
    /** Everything the client needs, ordered for display. */
    read() {
      return {
        groups: [...state.groups].sort((a, b) => a.order - b.order),
        bookmarks: [...state.bookmarks].sort((a, b) => a.order - b.order),
      };
    },

    /** Diagnostics for the boot log / health surface. */
    status() {
      return {
        path: filePath,
        durable,
        loadError,
        counts: { bookmarks: state.bookmarks.length, groups: state.groups.length },
      };
    },

    async addBookmark({ url, name, groupId }) {
      if (state.bookmarks.length >= LIMITS.bookmarks) {
        throw new BookmarksError("limit_reached", `At most ${LIMITS.bookmarks} bookmarks.`, 409);
      }
      const normalized = normalizeUrl(url);
      if (!normalized) {
        throw new BookmarksError("invalid_url", "Enter a valid http(s) web address.");
      }
      if (groupId != null && !findGroup(groupId)) {
        throw new BookmarksError("unknown_group", "That group no longer exists.", 404);
      }
      const bookmark = {
        id: crypto.randomUUID(),
        url: normalized,
        name: cleanLabel(name, defaultNameFor(normalized)),
        groupId: groupId ?? null,
        order: nextOrder(state.bookmarks),
        createdAt: now(),
      };
      state.bookmarks.push(bookmark);
      await persist();
      return bookmark;
    },

    async updateBookmark(id, patch) {
      const bookmark = findBookmark(id);
      if (!bookmark) throw new BookmarksError("not_found", "Bookmark not found.", 404);
      if (patch.url !== undefined) {
        const normalized = normalizeUrl(patch.url);
        if (!normalized) throw new BookmarksError("invalid_url", "Enter a valid http(s) address.");
        bookmark.url = normalized;
      }
      if (patch.name !== undefined) {
        bookmark.name = cleanLabel(patch.name, defaultNameFor(bookmark.url));
      }
      if (patch.groupId !== undefined) {
        if (patch.groupId != null && !findGroup(patch.groupId)) {
          throw new BookmarksError("unknown_group", "That group no longer exists.", 404);
        }
        bookmark.groupId = patch.groupId ?? null;
      }
      await persist();
      return bookmark;
    },

    async removeBookmark(id) {
      const index = state.bookmarks.findIndex((b) => b.id === id);
      if (index === -1) throw new BookmarksError("not_found", "Bookmark not found.", 404);
      const [removed] = state.bookmarks.splice(index, 1);
      await persist();
      return removed;
    },

    async addGroup({ name }) {
      if (state.groups.length >= LIMITS.groups) {
        throw new BookmarksError("limit_reached", `At most ${LIMITS.groups} groups.`, 409);
      }
      const group = {
        id: crypto.randomUUID(),
        name: cleanLabel(name, "Group"),
        order: nextOrder(state.groups),
      };
      state.groups.push(group);
      await persist();
      return group;
    },

    async updateGroup(id, patch) {
      const group = findGroup(id);
      if (!group) throw new BookmarksError("not_found", "Group not found.", 404);
      if (patch.name !== undefined) group.name = cleanLabel(patch.name, group.name);
      await persist();
      return group;
    },

    /** Deleting a group keeps its bookmarks — they fall back to Ungrouped. */
    async removeGroup(id) {
      const index = state.groups.findIndex((g) => g.id === id);
      if (index === -1) throw new BookmarksError("not_found", "Group not found.", 404);
      state.groups.splice(index, 1);
      for (const bookmark of state.bookmarks) {
        if (bookmark.groupId === id) bookmark.groupId = null;
      }
      await persist();
    },

    /** Test hook — resolves once queued writes have hit disk. */
    flush() {
      return writes;
    },
  };
}
