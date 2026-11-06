import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

/* Zero-dependency static server for the timeline page.
   Nothing to npm-install, so the image builds in seconds and there is no
   dependency tree to keep patched. Only ./public is ever served — the
   Dockerfile, package.json and this file sit outside it and are not
   reachable over HTTP. */

const PORT = Number(process.env.PORT) || 8080;
const ROOT = resolve(fileURLToPath(new URL("./public", import.meta.url)));

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8",
};

async function send(req, res, filePath, status) {
  const body = await readFile(filePath);
  const ext = extname(filePath).toLowerCase();
  res.writeHead(status, {
    "Content-Type": TYPES[ext] ?? "application/octet-stream",
    "Content-Length": body.length,
    /* The page itself is never cached: a redeploy has to show up on the next
       reload rather than whenever the browser decides to revalidate. */
    "Cache-Control":
      ext === ".html" ? "no-cache" : "public, max-age=31536000, immutable",
    "X-Content-Type-Options": "nosniff",
  });
  res.end(req.method === "HEAD" ? undefined : body);
}

const server = createServer(async (req, res) => {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405, { Allow: "GET, HEAD" }).end();
    return;
  }

  let pathname;
  try {
    pathname = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
  } catch {
    res.writeHead(400).end("Bad request");
    return;
  }

  // Railway's healthcheckPath. Answered before any disk access so it stays
  // green even if the page itself were missing.
  if (pathname === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(req.method === "HEAD" ? undefined : '{"status":"ok"}');
    return;
  }

  const target = resolve(join(ROOT, pathname.endsWith("/") ? pathname + "index.html" : pathname));

  // Traversal guard: anything resolving outside ./public is refused.
  if (target !== ROOT && !target.startsWith(ROOT + sep)) {
    res.writeHead(403).end("Forbidden");
    return;
  }

  try {
    await send(req, res, target, 200);
  } catch {
    /* A path with no file extension is a route, not a missing asset, so it
       falls through to the page. A missing .png stays a genuine 404. */
    if (extname(pathname)) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end(req.method === "HEAD" ? undefined : "Not found");
      return;
    }
    try {
      await send(req, res, join(ROOT, "index.html"), 200);
    } catch {
      res.writeHead(500).end("Server error");
    }
  }
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`timeline listening on :${PORT}`);
});

// Railway sends SIGTERM on redeploy; close cleanly rather than being killed.
for (const signal of ["SIGTERM", "SIGINT"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
