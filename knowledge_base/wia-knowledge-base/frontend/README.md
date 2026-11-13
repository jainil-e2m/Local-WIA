# WIA Client Knowledge Base — frontend preview

A standalone React + TypeScript + Vite mock of the maintained client record. It uses Playfair Display/Poppins typography, porcelain surfaces, navy and blue accents, gold details, rounded cards, WIA branding, and floral sidebar.

## Run locally

Use Node.js 20.19+ or 22.12+ (the Vite runtime requirement).

```powershell
cd "C:\Users\Jainil Trivedi\Desktop\Wedding_Industry_Ads\knowledge_base\wia-knowledge-base\frontend"
npm ci
npm run dev
```

Open **http://localhost:3001**. The server is bound to the local computer and uses a strict port so it cannot silently open on another port.

The optional **http://localhost:3001/?variant=blue** palette replaces gold accents with blue, including the sidebar floral treatment, buttons, badges, and calendar highlights. It stays active while navigating. The default URL retains the gold theme. This variant applies only to the Client Knowledge Base.

Install dependencies with `npm ci` before starting the development server.

```powershell
npm run typecheck
npm run build
npm run preview
```

Stop the development server before using `preview`, since both use port 3001. The production build is generated in `dist/`.

## Shareable HTML exports

```powershell
npm run export        # exports/client-portfolio.html (sample data, safe to share)
npm run export:live   # exports/client-portfolio.local.html (real GHL/Dubsado finance data, local only)
```

- `npm run export` builds a single self-contained HTML file with fonts and images inlined. It opens in the **blue** palette by default (`?variant=gold` switches back) and stores action edits under its own browser key, separate from the dev server.
- `npm run export:live` bundles real finance data from `src/finance-live.local.json` and `src/dubsado-live.local.json` (both gitignored; built by the scripts in `../verification/`). **Never share `client-portfolio.local.html`.** Every other build uses the empty stubs.

## UI feedback with Agentation

The development preview includes [Agentation](https://www.agentation.com/install), matching Content Atelier's local copy/paste workflow. Open the floating toolbar, select an element, write the requested change, save the note, then use **Copy** and paste the feedback into this chat.

- Feedback identifies **WIA Client Knowledge Base** and includes the element context.
- Notes are stored in this browser and separated by hash route, including individual client tabs. Copy notes from each route you want to discuss. Gold and blue palette variants share notes; mention the palette when relevant.
- The toolbar follows open dialogs and drawers so their contents can be annotated too.
- No MCP endpoint, webhook or automatic submission is configured, just as in Content Atelier.
- The toolbar is loaded by `npm run dev` and by `npm run export`, which rebuilds `exports/client-portfolio.html` (via `dist-export/`) with the toolbar included. It stays out of `npm run build` and `npm run preview`.
- In the exported HTML, notes are stored per browser and per page address, so notes made on the `file://` copy are separate from notes made on localhost.

The [content agenda](docs/content-agenda.md) maps the intended purpose of each screen, the client-record sections and gaps between the preview and agreed requirements.

## Explore the mock

Client record headers now follow the architectural cover design, with a 12-image library behind **Edit cover**. Each client's selection persists locally in the browser. **Edit cover** and the portfolio card's ⋯ → **Edit client details** open one client editor (name, aliases, category, location, logo upload/size/background, cover); see [client details editor](docs/client-details-editor.md). See [client record design](docs/client-record-design.md) for layout decisions, image sources, provenance, and the live `coverId` integration contract. Run `node scripts/verify-client-covers.mjs` after exporting to verify all covers are embedded and preferences remain independent between clients (Node 24+).

Several sections have a second layout under review. They sit next to the original in the sidebar, marked with a small badge, and share the same records, so a change in one shows in the other.

| Sidebar item (hash) | What is present |
| --- | --- |
| Overview (`#dashboard`) | Daily call queue, next-call brief, open loops, client attention and portfolio snapshot. |
| Client portfolio (`#clients`) | Large heading; My clients / All clients; service, stage, owner and health filters; logo cards (extracted logo or *Logo pending*, owner, engagements, open and overdue actions, health category) and a list view. |
| Call preparation (`#calls`) | Calendar-linked briefs, call objectives, agenda, client asks, source context and outstanding commitments; copy or download Markdown. |
| Call preparation · **v2** (`#calls-v2`) | Meetings board/list; a one-minute Overview per brief (goal, account pulse, what to settle, changes, talking points, a watch-out, gaps) with the rest in sub-tabs; regenerate with a custom prompt. |
| Action register (`#actions`) | Six clickable summary tiles; Register / Needs review / Programme ops; My actions / All clients; grouping by **Team** (admins only), **Client** (what clients owe) or Due date; Slack notify; action drawer. |
| Action register · **Revised** (`#actions-v2`) | Four buckets by who has the next move (My / Team / Client pending, Completed) as a **board or list**; priority; due-date range; programme ops in the same list; reopen; deadline-change requests that admins approve; admin-only Needs review; last-sync pill. |
| Action register · **v2 · Teams** (`#actions-v3`) | The revised layout with per-client visibility from account teams (`src/teams.ts`). |
| Health & sentiment (`#health`) | Qualitative relationship signals, the underlying client words and a next step; clearly marked interpretations. |
| Health & sentiment · **v2** (`#health-v2`) | "Whose move is it?": client mood and WIA delivery kept as separate measures, a relationship map, and tabs for this week, our side, client voice, movement, lead results and the Monday review. |
| Client 360 (`#assistant`) | The only chatbot entry point: conversations, scope bar, cited answers, pinned answers. No header button, shortcut or per-page *Ask about this* links. |
| Invoices & contracts (`#money`, admins only) | Three sub-views: Today (chases, missing invoices, new deals, renewals, unmatched alerts), Invoices (ledger with trust badges and timeline), Clients & contracts. |
| Source library (`#sources`) | Searchable original excerpts with dates, authors and source locators. |
| Connections (`#settings`) | Sample connector coverage, missing-source explanations, illustrative preference controls and preview reset. |

Each client record has **Now, Profile, History, Handover brief, Commitments, Meetings, Health, Support, Accounts & sources**, plus **Invoices & terms** for admins and **Attendance** for accelerator accounts. Invoices & terms is condensed to a standing line (up to date, overdue with Chase, missing invoice, or *Can't confirm yet*), invoices beside agreements, and one filterable activity timeline.

**Preview accounts.** The signed-in person is chosen from the account menu at the bottom of the sidebar (Carmen, Jacqueline, Gisselle, Whitney Hodges). The preview opens as Whitney. Each page follows that person's defaults: admins (Whitney, Gisselle) land on everyone's work and see finance and Needs review; managers land on their own work. The bell opens **Notifications** (overdue items, and deadline-change requests for admins).

Engagement history supports a multi-lane spine and chronological feed. The history boundary and missing evidence stay visible. Call briefs vary by call purpose; invoice reminders are shown before any follow-up could be prepared.

## Preview behaviour and boundaries

- All names, communications, source excerpts, invoices and indicators are fictional. The sample reference date is October 9, 2026; displayed call times are IST.
- Action edits persist in browser local storage and update the other views. Use **Connections → Reset preview changes** to restore the sample. If storage is unavailable, the current session still works.
- Search opens from the header or **Ctrl/⌘ K**. Client 360 is reached from the sidebar only. Dialogs support Escape; the mobile menu supports keyboard focus and Escape. Reduced-motion preferences are respected.
- Connector cards and preference switches illustrate the intended connection/settings UI. They do not authenticate, sync, generate briefs, or run jobs.
- No backend, live AI, client messaging, payment processing, real integrations, or authentication is implemented. Client logos are fictional drawings (`src/logos.tsx`); the intended extraction reads the Drive brand folder, then the contact's email signature, never the client's website.
- Google Fonts supplies Playfair Display and Poppins when available; Georgia and system sans-serif fallbacks keep the interface usable offline.

## Code map

- `src/data.ts` — the sample dataset and record helpers; `src/records.ts`, `src/finance.ts`, `src/health.ts` / `src/health-v2.ts`, `src/calls.ts`, `src/teams.ts` and `src/logos.tsx` hold the per-area samples.
- `src/financeLive.ts` — replaces the finance sample with real data in the local live export only.
- `src/types.ts` — client, action, evidence, call and invoice contracts.
- `src/App.tsx` — hash navigation, shared action state, global search and dialogs.
- `src/views/` — the main sections, their revised variants (`*Revised.tsx`, `*V2.tsx`, `ActionsTeams.tsx`) and the client record views.
- `src/components/` — sidebar, evidence drawer and shared controls.
- `src/styles.css` — WIA theme, responsive layouts and accessibility states.

## Validation

TypeScript checks and the export build pass (last checked 26 October 2026). Browser checks covered all main sections and client tabs, source and invoice drawers, search, action creation/editing/completion/verification, reload persistence, reset, brief copy/download and mobile navigation. At a 390px viewport, the reviewed main pages had no document-level horizontal overflow.
