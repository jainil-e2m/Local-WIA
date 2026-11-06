import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  createBookmarksStore,
  normalizeUrl,
  defaultNameFor,
  BookmarksError,
  LIMITS,
} from "./bookmarks-store.mjs";

let dir;
let file;
let opened;

beforeEach(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "wahha-bookmarks-"));
  file = path.join(dir, "nested", "bookmarks.json");
  opened = [];
});

afterEach(async () => {
  // Let queued writes land before the directory disappears, otherwise an
  // in-flight rename races teardown and logs a spurious ENOENT.
  await Promise.all(opened.map((store) => store.flush().catch(() => {})));
  fs.rmSync(dir, { recursive: true, force: true });
});

const open = () => {
  const store = createBookmarksStore(file, { now: () => 1_700_000_000_000 });
  opened.push(store);
  return store;
};

/** Write a store document straight to disk, bypassing the write queue. */
const seedFile = (bookmarks, groups = []) => {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify({ version: 1, groups, bookmarks }), "utf8");
};

describe("normalizeUrl (security boundary)", () => {
  it("assumes https for a bare hostname", () => {
    expect(normalizeUrl("web.telegram.org")).toBe("https://web.telegram.org/");
    expect(normalizeUrl("  example.com/path  ")).toBe("https://example.com/path");
  });

  it("keeps an explicit http(s) scheme", () => {
    expect(normalizeUrl("http://intranet.local/x")).toBe("http://intranet.local/x");
    expect(normalizeUrl("https://a.co/b?c=1#d")).toBe("https://a.co/b?c=1#d");
  });

  it("REJECTS script-bearing schemes (these become stored XSS in an href)", () => {
    expect(normalizeUrl("javascript:alert(1)")).toBeNull();
    expect(normalizeUrl("JavaScript:alert(1)")).toBeNull();
    expect(normalizeUrl("data:text/html,<script>alert(1)</script>")).toBeNull();
    expect(normalizeUrl("vbscript:msgbox(1)")).toBeNull();
    expect(normalizeUrl("file:///etc/passwd")).toBeNull();
  });

  it("rejects junk, empties and over-long input", () => {
    expect(normalizeUrl("")).toBeNull();
    expect(normalizeUrl("   ")).toBeNull();
    expect(normalizeUrl(undefined)).toBeNull();
    expect(normalizeUrl(42)).toBeNull();
    expect(normalizeUrl(`https://e.com/${"x".repeat(LIMITS.urlLength)}`)).toBeNull();
  });
});

describe("defaultNameFor", () => {
  it("uses the hostname without www", () => {
    expect(defaultNameFor("https://www.telegram.org/a")).toBe("telegram.org");
    expect(defaultNameFor("https://mail.google.com/")).toBe("mail.google.com");
  });
});

describe("bookmarks store", () => {
  it("starts empty and creates the file (and its directory) on first write", async () => {
    const store = open();
    expect(store.read()).toEqual({ groups: [], bookmarks: [] });
    expect(fs.existsSync(file)).toBe(false);

    await store.addBookmark({ url: "example.com" });
    expect(fs.existsSync(file)).toBe(true);
    expect(JSON.parse(fs.readFileSync(file, "utf8")).bookmarks).toHaveLength(1);
  });

  it("derives a name from the URL when none is given, and trims one that is", async () => {
    const store = open();
    const auto = await store.addBookmark({ url: "https://www.telegram.org" });
    expect(auto.name).toBe("telegram.org");
    const named = await store.addBookmark({ url: "a.com", name: "  My Site  " });
    expect(named.name).toBe("My Site");
  });

  it("rejects an invalid URL without mutating state", async () => {
    const store = open();
    await expect(store.addBookmark({ url: "javascript:alert(1)" })).rejects.toBeInstanceOf(
      BookmarksError,
    );
    expect(store.read().bookmarks).toHaveLength(0);
  });

  it("persists across reopen (the file is the source of truth)", async () => {
    const first = open();
    const group = await first.addGroup({ name: "Work" });
    await first.addBookmark({ url: "telegram.org", name: "Telegram", groupId: group.id });
    await first.flush();

    const second = open();
    const state = second.read();
    expect(state.groups.map((g) => g.name)).toEqual(["Work"]);
    expect(state.bookmarks[0]).toMatchObject({ name: "Telegram", groupId: group.id });
  });

  it("updates name, url and group", async () => {
    const store = open();
    const group = await store.addGroup({ name: "Tools" });
    const bookmark = await store.addBookmark({ url: "a.com" });

    await store.updateBookmark(bookmark.id, { name: "Renamed", groupId: group.id });
    expect(store.read().bookmarks[0]).toMatchObject({ name: "Renamed", groupId: group.id });

    await store.updateBookmark(bookmark.id, { url: "b.com", groupId: null });
    expect(store.read().bookmarks[0]).toMatchObject({
      url: "https://b.com/",
      groupId: null,
    });
  });

  it("deletes a bookmark, and 404s on an unknown id", async () => {
    const store = open();
    const bookmark = await store.addBookmark({ url: "a.com" });
    await store.removeBookmark(bookmark.id);
    expect(store.read().bookmarks).toHaveLength(0);
    await expect(store.removeBookmark(bookmark.id)).rejects.toMatchObject({ status: 404 });
  });

  it("keeps bookmarks when their group is deleted (they fall back to Ungrouped)", async () => {
    const store = open();
    const group = await store.addGroup({ name: "Temp" });
    await store.addBookmark({ url: "a.com", groupId: group.id });

    await store.removeGroup(group.id);
    const state = store.read();
    expect(state.groups).toHaveLength(0);
    expect(state.bookmarks).toHaveLength(1);
    expect(state.bookmarks[0].groupId).toBeNull();
  });

  it("refuses a bookmark pointed at a group that does not exist", async () => {
    const store = open();
    await expect(store.addBookmark({ url: "a.com", groupId: "nope" })).rejects.toMatchObject({
      status: 404,
    });
  });

  it("enforces the bookmark ceiling so the file stays bounded", async () => {
    // Seeded on disk rather than via 500 awaited writes — same invariant, and
    // it doesn't spend seconds of I/O to reach the boundary.
    seedFile(
      Array.from({ length: LIMITS.bookmarks }, (_, i) => ({
        id: `seed-${i}`,
        url: `https://site${i}.com/`,
        name: `site${i}.com`,
        groupId: null,
        order: i,
        createdAt: 1,
      })),
    );
    const store = open();
    expect(store.read().bookmarks).toHaveLength(LIMITS.bookmarks);

    await expect(store.addBookmark({ url: "one-too-many.com" })).rejects.toMatchObject({
      code: "limit_reached",
    });
  });

  it("caps absurdly long names", async () => {
    const store = open();
    const b = await store.addBookmark({ url: "a.com", name: "z".repeat(500) });
    expect(b.name).toHaveLength(LIMITS.nameLength);
  });

  it("survives a corrupt file instead of crashing, leaving it in place", () => {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, "{ this is not json", "utf8");

    const store = open();
    expect(store.read()).toEqual({ groups: [], bookmarks: [] });
    expect(store.status().loadError).toBeTruthy();
    expect(fs.readFileSync(file, "utf8")).toContain("not json"); // untouched
  });

  it("drops hand-edited entries that break the rules", () => {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(
      file,
      JSON.stringify({
        version: 1,
        groups: [{ id: "g1", name: "Kept" }],
        bookmarks: [
          { id: "b1", url: "https://ok.com/", name: "Fine", groupId: "g1" },
          { id: "b2", url: "javascript:alert(1)", name: "Evil" }, // unsafe scheme
          { id: "b3", url: "https://orphan.com/", groupId: "ghost-group" }, // dead group ref
          { url: "https://no-id.com/" }, // missing id
        ],
      }),
      "utf8",
    );

    const state = open().read();
    expect(state.bookmarks.map((b) => b.name)).toEqual(["Fine", "orphan.com"]);
    expect(state.bookmarks.find((b) => b.name === "orphan.com").groupId).toBeNull();
  });

  it("serializes concurrent writes without corrupting the document", async () => {
    const store = open();
    await Promise.all(
      Array.from({ length: 25 }, (_, i) => store.addBookmark({ url: `concurrent${i}.com` })),
    );
    await store.flush();

    const onDisk = JSON.parse(fs.readFileSync(file, "utf8"));
    expect(onDisk.bookmarks).toHaveLength(25);
    expect(new Set(onDisk.bookmarks.map((b) => b.id)).size).toBe(25);
    // no temp files left behind
    expect(fs.readdirSync(path.dirname(file)).filter((f) => f.endsWith(".tmp"))).toEqual([]);
  });
});
