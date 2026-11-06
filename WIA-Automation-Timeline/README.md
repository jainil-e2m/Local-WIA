# Automation Timeline — Wedding Industry Ads

The automation engagement build timeline, as a standalone page.

## Layout

```
public/index.html   the page — everything is in this one file
server.mjs          zero-dependency static server (serves ./public, /health)
Dockerfile          what Railway builds
railway.json        builder + healthcheck config
```

There is nothing to install and nothing to compile. `public/index.html` is
self-contained: all CSS and JS are inline, and the only external request is
the Inter webfont from Google Fonts.

## Run locally

```bash
node server.mjs
```

Then open http://localhost:8080. Set `PORT` to use another port.

To edit the page, open `public/index.html` directly in a browser — no server
needed. The plan lives in the `PHASES` array near the top of its `<script>`
block, and `KICKOFF` (one line above it) sets the start date the whole board
is scheduled from.

## Deploy to Railway

1. In Railway: **New Project → Deploy from GitHub repo**, pick this repo.
2. Deploy. Everything sits at the repo root, so there is no **Root Directory**
   to set. Railway reads `railway.json`, builds the `Dockerfile`, and waits for
   `/health` to return 200 before routing traffic.
3. **Settings → Networking → Generate Domain** for a public URL.

No environment variables are required. Railway injects `PORT` and the server
binds to it; `8080` is only the local fallback.
