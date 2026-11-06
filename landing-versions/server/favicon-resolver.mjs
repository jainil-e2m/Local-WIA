/* ────────────────────────────────────────────────────────────────
   Favicon resolution, server-side.

   Why not just <img src="{origin}/favicon.ico">: that convention is
   frequently stale. app.clickup.com serves a legacy icon there while
   its pages declare the real brand mark via
   <link rel="icon" href="assets/favicons/favicon-32x32.png">. The
   browser tab shows the declared one; /favicon.ico shows the wrong
   one. Only reading the HTML gets this right, and a browser cannot
   read another origin's HTML (CORS).

   Doing it here also lets us judge success honestly: an <img> fires
   `load` even for a 404 whose body happens to be a valid image, so a
   client-side fallback chain cannot tell a real icon from a
   placeholder. A fetch can check the status.

   Because this fetches a user-supplied URL from our own network, it
   is SSRF-guarded: http(s) only, no credentials, and the resolved IP
   must be publicly routable.
   ──────────────────────────────────────────────────────────────── */

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import dns from "node:dns/promises";

export const LIMITS = {
  htmlBytes: 512 * 1024,
  iconBytes: 256 * 1024,
  redirects: 3,
  timeoutMs: 6000,
  /** Re-check a cached icon after this long. */
  ttlMs: 30 * 24 * 60 * 60 * 1000,
};

const IMAGE_TYPES = /^image\/(png|x-icon|vnd\.microsoft\.icon|jpeg|gif|webp|svg\+xml|avif)/i;

/** Reject anything that is not a public host — the SSRF boundary. */
export function isPrivateAddress(address) {
  if (typeof address !== "string") return true;
  /* Fail closed on anything that is not recognisably an address. "" is a
     string, contains no ".", and matched none of the v6 literals below — so it
     fell through to `return false` and was treated as PUBLIC. An empty or junk
     answer from DNS must never open the fetch. */
  const trimmed = address.trim();
  if (!trimmed) return true;
  if (!trimmed.includes(".") && !trimmed.includes(":")) return true;
  const v4 = trimmed.includes(".") ? trimmed.replace(/^::ffff:/i, "") : null;
  if (v4 && /^\d+\.\d+\.\d+\.\d+$/.test(v4)) {
    const [a, b] = v4.split(".").map(Number);
    if (a === 0 || a === 10 || a === 127) return true; // this-host, private, loopback
    if (a === 169 && b === 254) return true; // link-local
    if (a === 172 && b >= 16 && b <= 31) return true; // private
    if (a === 192 && b === 168) return true; // private
    if (a === 100 && b >= 64 && b <= 127) return true; // CGNAT
    if (a === 198 && (b === 18 || b === 19)) return true; // benchmarking
    if (a >= 224) return true; // multicast / reserved
    return false;
  }
  const v6 = trimmed.toLowerCase();
  if (v6 === "::" || v6 === "::1") return true;
  if (/^f[cd][0-9a-f]{2}:/.test(v6)) return true; // unique-local fc00::/7
  if (/^fe[89ab][0-9a-f]:/.test(v6)) return true; // link-local fe80::/10
  return false;
}

/**
 * Validate a URL for outbound fetching.
 *
 * NB: this resolves DNS and checks the answer, which closes the common case.
 * It cannot close a DNS-rebinding race (the fetch resolves again), which would
 * need a pinned-IP agent — out of proportion for an authenticated internal
 * dashboard where the URL comes from a signed-in operator.
 */
export async function assertFetchableUrl(raw, { lookup = dns.lookup } = {}) {
  let url;
  try {
    url = new URL(raw);
  } catch {
    throw new Error("invalid_url");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") throw new Error("unsupported_scheme");
  if (url.username || url.password) throw new Error("credentials_in_url");
  if (!url.hostname) throw new Error("invalid_url");
  if (/^(localhost|.*\.local|.*\.internal|.*\.localhost)$/i.test(url.hostname)) {
    throw new Error("private_host");
  }
  const answers = await lookup(url.hostname, { all: true }).catch(() => []);
  if (!answers.length) throw new Error("dns_failed");
  if (answers.some((a) => isPrivateAddress(a.address))) throw new Error("private_host");
  return url;
}

/** Fetch with a timeout and a hard byte cap. */
async function fetchCapped(url, maxBytes, accept) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), LIMITS.timeoutMs);
  try {
    const res = await fetch(url, {
      redirect: "follow",
      signal: controller.signal,
      headers: {
        Accept: accept,
        // Some CDNs serve a stripped page to unknown agents.
        "User-Agent": "Mozilla/5.0 (compatible; CommandCenterBookmarks/1.0)",
      },
    });
    if (!res.ok) return { ok: false, status: res.status };
    const buffer = Buffer.from(await res.arrayBuffer());
    if (buffer.length > maxBytes) return { ok: false, status: 413 };
    return {
      ok: true,
      status: res.status,
      buffer,
      contentType: res.headers.get("content-type") ?? "",
      finalUrl: res.url || String(url),
    };
  } catch {
    return { ok: false, status: 0 };
  } finally {
    clearTimeout(timer);
  }
}

/** Largest declared side length, or a sensible default per rel type. */
function declaredSize(tag, rel) {
  const sizes = /sizes=["']?([^"'\s>]+)/i.exec(tag)?.[1];
  if (sizes) {
    const best = [...sizes.matchAll(/(\d+)\s*x\s*(\d+)/gi)].map((m) => Number(m[1]));
    if (best.length) return Math.max(...best);
    if (/any/i.test(sizes)) return 512; // SVG
  }
  // apple-touch-icon is conventionally 180 and usually the crispest asset
  return /apple-touch-icon/i.test(rel) ? 180 : 16;
}

/**
 * Choose the best icon a page declares.
 *
 * Prefers the largest asset that is still icon-shaped — we render at ~40px on
 * 2x displays, so a 180-192px apple-touch-icon is ideal, while a 512px+ PWA
 * asset is wasted bytes.
 */
export function pickDeclaredIcon(html, pageUrl) {
  const candidates = [];
  for (const match of html.matchAll(/<link\b[^>]*>/gi)) {
    const tag = match[0];
    const rel = /rel=["']?([^"'>]*)/i.exec(tag)?.[1] ?? "";
    if (!/(^|\s)(icon|shortcut\s+icon|apple-touch-icon(-precomposed)?)(\s|$)/i.test(rel.trim())) {
      continue;
    }
    const href = /href=["']?([^"'\s>]+)/i.exec(tag)?.[1];
    if (!href) continue;
    let resolved;
    try {
      resolved = new URL(href, pageUrl).toString(); // handles relative hrefs
    } catch {
      continue;
    }
    candidates.push({ url: resolved, size: declaredSize(tag, rel) });
  }
  if (!candidates.length) return null;
  candidates.sort((a, b) => {
    /* Penalise oversized 1:1 rather than by a hundredth. The old divisor scored
       a 1024px PWA asset at 248 — still ahead of a 192px icon at 192 — so the
       "wasted bytes" the doc comment above promises to avoid were downloaded
       every time a site declared both. Clamped at 0 so an oversized asset is
       still chosen when it is the only thing on offer. */
    const score = (s) => (s > 256 ? Math.max(0, 256 - (s - 256)) : s);
    return score(b.size) - score(a.size);
  });
  return candidates[0].url;
}

/** Disk-backed icon cache: one small JSON per host. */
export function createFaviconCache(dir, { now = () => Date.now() } = {}) {
  const fileFor = (key) =>
    path.join(dir, `${crypto.createHash("sha1").update(key).digest("hex")}.json`);

  return {
    read(key) {
      try {
        const raw = fs.readFileSync(fileFor(key), "utf8");
        const entry = JSON.parse(raw);
        if (!entry || typeof entry.base64 !== "string") return null;
        if (now() - (entry.fetchedAt ?? 0) > LIMITS.ttlMs) return null;
        return { contentType: entry.contentType, buffer: Buffer.from(entry.base64, "base64") };
      } catch {
        return null;
      }
    },
    async write(key, { contentType, buffer }) {
      try {
        await fsp.mkdir(dir, { recursive: true });
        const target = fileFor(key);
        const tmp = `${target}.${crypto.randomUUID()}.tmp`;
        await fsp.writeFile(
          tmp,
          JSON.stringify({ contentType, base64: buffer.toString("base64"), fetchedAt: now() }),
          "utf8",
        );
        await fsp.rename(tmp, target); // atomic
      } catch {
        /* cache is best-effort — a failure here must not fail the request */
      }
    },
  };
}

/**
 * Resolve the icon for a page: read what it declares, then fall back to the
 * /favicon.ico convention. Returns { contentType, buffer } or null.
 */
export async function fetchFavicon(pageUrl, { deps = {} } = {}) {
  const url = await assertFetchableUrl(pageUrl, deps);

  const attempts = [];
  const page = await fetchCapped(url, LIMITS.htmlBytes, "text/html,*/*");
  if (page.ok && /text\/html/i.test(page.contentType)) {
    const declared = pickDeclaredIcon(page.buffer.toString("utf8"), page.finalUrl);
    if (declared) attempts.push(declared);
  }
  attempts.push(new URL("/favicon.ico", url).toString());

  for (const candidate of attempts) {
    // Each candidate is re-validated: a declared href can point anywhere.
    const safe = await assertFetchableUrl(candidate, deps).catch(() => null);
    if (!safe) continue;
    const icon = await fetchCapped(safe, LIMITS.iconBytes, "image/*");
    if (!icon.ok || !icon.buffer.length) continue;
    if (!IMAGE_TYPES.test(icon.contentType)) continue;
    return { contentType: icon.contentType.split(";")[0].trim(), buffer: icon.buffer };
  }
  return null;
}
