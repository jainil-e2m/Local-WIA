import axios from "axios";

/**
 * Bookmarks live on the dashboard's own origin (the Express server that serves
 * this bundle) behind the session cookie — same shape as the auth client.
 * The server is authoritative for validation; the checks mirrored here are for
 * fast feedback in the form, not for safety.
 */
const bookmarksApi = axios.create({
  baseURL: "",
  timeout: 10_000,
  headers: { "Content-Type": "application/json" },
});

export interface BookmarkGroup {
  id: string;
  name: string;
  order: number;
}

export interface Bookmark {
  id: string;
  url: string;
  name: string;
  /** null = the implicit "Ungrouped" bucket. */
  groupId: string | null;
  order: number;
  createdAt: number;
}

export interface BookmarksState {
  groups: BookmarkGroup[];
  bookmarks: Bookmark[];
}

/** Mirrors the server's rule: only http(s) may ever reach an `href`. */
export function normalizeUrlInput(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const hasScheme = /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(trimmed);
  try {
    const url = new URL(hasScheme ? trimmed : `https://${trimmed}`);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    if (!url.hostname) return null;
    return url.toString();
  } catch {
    return null;
  }
}

/** "https://www.telegram.org/a" → "telegram.org" */
export function hostLabel(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export async function fetchBookmarks(): Promise<BookmarksState> {
  const { data } = await bookmarksApi.get<BookmarksState>("/api/bookmarks");
  return data;
}

export async function createBookmark(input: {
  url: string;
  name?: string;
  groupId?: string | null;
}): Promise<BookmarksState> {
  const { data } = await bookmarksApi.post<BookmarksState>("/api/bookmarks", input);
  return data;
}

export async function updateBookmark(
  id: string,
  patch: { url?: string; name?: string; groupId?: string | null },
): Promise<BookmarksState> {
  const { data } = await bookmarksApi.patch<BookmarksState>(`/api/bookmarks/${id}`, patch);
  return data;
}

export async function deleteBookmark(id: string): Promise<BookmarksState> {
  const { data } = await bookmarksApi.delete<BookmarksState>(`/api/bookmarks/${id}`);
  return data;
}

export async function createGroup(name: string): Promise<BookmarksState> {
  const { data } = await bookmarksApi.post<BookmarksState>("/api/bookmarks/groups", { name });
  return data;
}

export async function renameGroup(id: string, name: string): Promise<BookmarksState> {
  const { data } = await bookmarksApi.patch<BookmarksState>(`/api/bookmarks/groups/${id}`, {
    name,
  });
  return data;
}

export async function deleteGroup(id: string): Promise<BookmarksState> {
  const { data } = await bookmarksApi.delete<BookmarksState>(`/api/bookmarks/groups/${id}`);
  return data;
}
