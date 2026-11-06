# mvp — deployed client portfolio

Static deployment of the single-file client portfolio. No build step: `index.html` is self-contained (fonts and images are inlined as data URIs).

## Files

- `real_index.html` — **the deployed page** (served at `/`): `index.html` with its sample data swapped for the 4 pilot clients' real data. Generated; never edit it by hand. Rebuild with `python -I backend/.local/raw_pull/scripts/build_real_index.py` from the repo root.
- `index.html` — the sample-data source. Edit this file for UI changes (logged in `readme_changes.md`), then rebuild `real_index.html`. Not served.
- `Caddyfile.template` — Railpack's default static-site Caddyfile with three changes: `/` serves `real_index.html`, `index.html` and the repo notes return 404, and an `X-Robots-Tag: noindex` header.
- `railway.json` — Railway config-as-code (Railpack builder).

## Source

`index.html` is a copy of `frontend/exports/client-portfolio.html`, which `npm run export` (in `frontend/`) regenerates and overwrites. Never edit the export for deployment; edit the copy here.

Copied 2026-11-02 from the working-tree export built 2026-10-30 (uncommitted on top of `1326db9`), sha256 `0bd862f58e7862abc8a87e249029ab073218cc7c010f1472c63ce1ac0122d0f5`.

`index.html` is the stub-data build (`npm run export`). Since 2026-11-03 the deployed page is `real_index.html`, real data for the 4 pilot clients (Jainil's decision). Finance documents stay hidden in it (F2). Still never copy `client-portfolio-wia.html` or `client-portfolio.local.html` here.

## Re-syncing after a new export

1. In `frontend/`, run `npm run export`.
2. Copy `frontend/exports/client-portfolio.html` over `mvp/index.html`.
3. Reapply the deployment-only edits listed below.
4. Update the copy date and sha256 above.

## Deployment-only edits

Changes made to `index.html` that are not in the export (keep this list current so a re-sync can reapply them):

- All MVP review edits, listed with reapply notes in `readme_changes.md`.

The `agentation` annotation toolbar stays in `index.html` for review rounds. The build strips it from `real_index.html` automatically (`readme_changes.md` technical note 31's two edits), so the deployed page never has it. For feedback rounds, use the review copy `backend/.local/raw_pull/real/real_index.html` (gitignored), which keeps the toolbar.

## Deploying (Railway)

Create a Railway service from this GitHub repo, then in the service settings:

- **Root Directory:** `/mvp`
- **Config file path:** `/mvp/railway.json` (Railway does not look for the config file inside the Root Directory on its own)
- **Networking:** generate a public domain

Railpack sees `index.html` at the root, treats this folder as a static site, and uses `Caddyfile.template` from it instead of its default Caddyfile; there is no build step. Only `real_index.html` is served (at `/` and `/real_index.html`); `index.html`, this README, `readme_changes.md`, `railway.json` and the Caddyfile return 404. **The domain is public to anyone with the URL and has no login**, so the real client data on it is readable by anyone who has the link. Any new file added here is served unless it's added to the `hide` list in `Caddyfile.template`.

## Local preview

From the repo root:

`npx serve mvp` serves the folder without the Caddyfile (so `/` is the sample `index.html`); open `/real_index.html` for the deployed page. To test the Caddy rules exactly, run `caddy:2` in Docker with `{{.StaticFileRoot}}` replaced by `.`.
