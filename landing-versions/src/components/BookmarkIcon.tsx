import { useMemo, useState } from "react";

/* ────────────────────────────────────────────────────────────────
   Favicon rendering. The hard part — working out which URL actually
   holds a site's icon — happens on the server (see
   server/favicon-resolver.mjs), because:

     • the /favicon.ico convention is often stale, and only the page's
       declared <link rel="icon"> is authoritative
     • a browser cannot read another origin's HTML to find that link
     • an <img> fires `load` even for a 404 whose body happens to
       decode, so a client-side fallback chain cannot tell a real icon
       from a placeholder

   So this component just asks our own origin for the icon and falls
   back to a lettered monogram if there genuinely isn't one.
   ──────────────────────────────────────────────────────────────── */

/** Deterministic tint per host, so monograms look intentional rather than random. */
const MONOGRAM_TINTS = [
  "from-brand-primary to-brand-secondary",
  "from-brand-secondary to-brand-accent",
  "from-brand-accent to-brand-sky",
  "from-brand-teal to-brand-sky",
  "from-brand-orange to-brand-teal",
];

function tintFor(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  return MONOGRAM_TINTS[Math.abs(hash) % MONOGRAM_TINTS.length];
}

function initialsFor(name: string): string {
  const words = name.trim().split(/[\s.\-_/]+/).filter(Boolean);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return (words[0]?.slice(0, 2) ?? "?").toUpperCase();
}

export function BookmarkIcon({
  url,
  name,
  className = "h-8 w-8",
}: {
  url: string;
  name: string;
  className?: string;
}) {
  const src = useMemo(
    () => `/api/bookmarks/icon?url=${encodeURIComponent(url)}`,
    [url],
  );

  // Keyed by url so switching bookmarks retries rather than inheriting a
  // previous item's failed state.
  const [failed, setFailed] = useState(false);
  const [failedFor, setFailedFor] = useState(url);
  if (failedFor !== url) {
    setFailedFor(url);
    setFailed(false);
  }

  if (failed) {
    return (
      <span
        aria-hidden
        className={`grid shrink-0 place-items-center rounded-[9px] bg-gradient-to-br text-[11px] font-extrabold text-white ${tintFor(url)} ${className}`}
      >
        {initialsFor(name)}
      </span>
    );
  }

  return (
    <img
      src={src}
      alt=""
      aria-hidden
      loading="lazy"
      onError={() => setFailed(true)}
      className={`shrink-0 rounded-[9px] object-contain ${className}`}
    />
  );
}
