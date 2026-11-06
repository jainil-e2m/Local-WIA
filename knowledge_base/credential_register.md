# WIA Client Knowledge Base: Credential Register

Private. **No secret values go in this file**, only what each credential is, who owns it, where it's stored and how to revoke it. The values live in `.env` files locally, and later in Railway's variables.

This file sits outside the `wia-knowledge-base` git repo on purpose. Don't move it inside.

Last checked: 29 Oct 2026 (Jainil)

## When to use it

- Something breaks, for example an expired token: find whose account needs fixing.
- Someone on the WIA or E2M team changes.
- WIA asks what access E2M has, and how to cut it off.

## Credentials used by the KB

| # | Credential | Belongs to | Stored in | Access | Expires | Revoke / rotate |
|---|---|---|---|---|---|---|
| 1 | Slack bot token (`SLACK_BOT_TOKEN`) | WIA Slack workspace; app **WIA AI BOT** (renamed Content Atelier), app id `A0C3CRX098D` | `wia-knowledge-base/backend/.env`; the same token is also in `frontend/.env` | 11 scopes: channels:history, channels:read, groups:history, groups:read, files:read, reactions:read, users:read, users:read.email, im:read, chat:write, im:write. The bot is in 4 client channels plus #wia-ai-team-testing | Never | **Rotate:** api.slack.com → the app → OAuth & Permissions → revoke the token and reinstall, then update both `.env` files. **Cut off:** a WIA Slack admin removes the app under Workspace settings → Manage apps |
| 2 | ClickUp personal API token (`CLICKUP_TOKEN`, a `pk_` token) + `CLICKUP_TEAM_ID` | **E2M AI** user, `ai@weddingindustryads.com`, Member role in the WIA workspace | `wia-knowledge-base/backend/.env` | Everything the E2M AI member can see and do. Used **read-only** by the KB (sync); never used for write-back | Never | **Rotate:** log in as E2M AI → ClickUp Settings → Apps → API Token → Regenerate. **Cut off:** a WIA Owner/Admin deactivates or removes the E2M AI member |
| 3 | ClickUp OAuth app "WIA Knowledge Base" (`CLICKUP_OAUTH_CLIENT_ID`, `CLICKUP_OAUTH_CLIENT_SECRET`, `CLICKUP_OAUTH_REDIRECT_URI`) | WIA ClickUp workspace; created 2 Nov 2026 by Jainil via the hello@ login (Option A, approved by Gisselle for Whitney) | `wia-knowledge-base/backend/.env` | Lets each KB user connect their own ClickUp account; redirect is local only for now | Never (app); per-user tokens until revoked | **Rotate:** ClickUp Settings > ClickUp API Settings > the app > regenerate secret, update `.env`. **Cut off:** delete the app there (every connection stops) |
| 4 | ClickUp per-user tokens (future, S10/S12) | Each KB user's own ClickUp account | KB database, encrypted (not built yet) | Owner, due date and status edits on mapped tasks, as that user | ClickUp-defined | The user disconnects it in the KB or revokes it in ClickUp; the KB then blocks their ClickUp edits (no fallback) |
| 5 | Google OAuth client (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) | GCP project **Client Knowledge Base** (868273890431), weddingindustryads.com org. Audience **Internal**. Project Owner: hello@ (Whitney Hodges, Org Administrator) | `wia-knowledge-base/backend/.env`; the same values are in `frontend/.env` (with `GOOGLE_REDIRECT_URI`) | Lets weddingindustryads.com accounts grant the scopes in row 6 | Never | **Rotate the secret:** GCP → Google Auth Platform → Clients → add a secret, update `.env`, delete the old one. **Cut off:** delete the client in GCP (this also kills row 6) |
| 6 | Google refresh token (`GOOGLE_REFRESH_TOKEN`) | Granted by **hello@weddingindustryads.com** | `wia-knowledge-base/backend/.env`; a duplicate is in `frontend/.data/knowledge-base-google/oauth-tokens.json` (git-ignored) | gmail.readonly, drive.readonly, calendar.events.readonly, calendar.calendarlist.readonly | No 7-day limit (Internal app). Dies if hello@ revokes it, its password changes with Gmail scopes, or it goes unused for 6 months | **Cut off:** hello@ → myaccount.google.com/permissions → remove the app. **Re-issue:** run the consent flow as hello@ again and update `.env` |
| 7 | Fathom API key (`FATHOM_API_KEY`) | WIA's Fathom **Team plan** key (shared team key, confirmed 30 Oct), created by a WIA admin | `wia-knowledge-base/backend/.env`; the same key is in `frontend/.env` | Read meetings, transcripts, summaries and action items visible to that account | Never | **Rotate / cut off:** that admin → Fathom Settings → API access → revoke and create a new key, then update both `.env` files |
| 8 | LeadLock Marketplace app "WIA Client Knowledge Base" (`LEADLOCK_APP_CLIENT_ID`, `LEADLOCK_APP_CLIENT_SECRET`, `LEADLOCK_APP_ID`, `LEADLOCK_COMPANY_ID`) | HighLevel developer account (marketplace.gohighlevel.com) **[record which login]**; private app created 4 Nov 2026 by Jainil. Agency: LeadLock (`LEADLOCK_COMPANY_ID`) | `wia-knowledge-base/backend/.env` (client keys added 4 Nov; installed on the LeadLock agency 4 Nov: all 59 sub-accounts, auto-install for new ones on) | 19 read-only scopes (contacts, opportunities, conversations, calendars, forms, surveys, custom fields, invoices, payments, products, locations) + `oauth.readonly/write` to mint per-sub-account tokens. Target user Sub-Account, Agency-only install | Never (app); agency token ~24 h, refresh token rotates on every use | **Rotate:** the app → Manage → Secrets → new client key, update `.env`, delete the old key. **Cut off:** an agency admin uninstalls the app (every sub-account token stops), or delete the app in the developer portal |
| 9 | LeadLock agency grant + sub-account tokens (from row 8's install) | The LeadLock agency, granted by the agency admin who installs the app | KB database, encrypted with `KB_SECRET_KEY` (`leadlock_installations`, `leadlock_locations`) | What row 8's scopes allow, per installed sub-account | Agency token refreshed by the KB; sub-account tokens re-minted daily | Uninstall the app from the agency (KB revokes on the uninstall webhook). If a refresh is ever rejected, the KB revokes the grant and the app must be reinstalled |
| 10 | GHL private integration tokens (`GHL_AGENCY_PIT`, `GHL_FINANCE_PIT`, `GHL_PIT`, with `GHL_LOCATION_ID`) | `GHL_AGENCY_PIT`: agency integration "Client Knowledge Base" (19 Oct, created by E2M AI). `GHL_FINANCE_PIT` and `GHL_PIT`: WIA's own sub-account | `frontend/.env` only | Agency PIT: companies, locations, users (read). Finance PIT: WIA's own contacts, campaigns, invoices, schedules, transactions, subscriptions, orders (read). **`GHL_PIT` is invalid since ~4 Nov** | Never (until deleted) | LeadLock Settings → Private Integrations (agency view, or WIA's sub-account) → ⋮ → Delete. Once row 8 works, delete `GHL_PIT` and review whether the others are still needed |

## Internal to E2M (not WIA credentials)

Also: `KB_SECRET_KEY` in `backend/.env` encrypts the stored per-person ClickUp tokens (row 4) and the LeadLock agency and sub-account tokens (row 9). Losing it means everyone reconnects; leaking it exposes stored tokens. Rotate by generating a new key and asking everyone to reconnect.


| Credential | Stored in | Notes |
|---|---|---|
| `DATABASE_URL` | `wia-knowledge-base/backend/.env` | Local Postgres (port 5440). Becomes a Railway variable at deploy |
| `OPS_TOKEN` | `wia-knowledge-base/backend/.env` | Guards the ops API until real auth (S10). Generated by E2M; rotate by changing the value |

## Human logins E2M holds (not used by the KB code)

| Login | Since | Notes |
|---|---|---|
| hello@weddingindustryads.com password + an E2M +91 phone as a second 2-step-verification method | 22 Sep 2026 | No written scope or end date. **Revoking this properly means:** remove the +91 phone from 2-Step Verification, rotate the password, sign out all sessions, and review third-party app grants. A password reset alone leaves the phone in place |
| E2M AI ClickUp login (ai@weddingindustryads.com) | — | The account behind row 2 |

## Open items

- Row 3: created 2 Nov. Add the production redirect URL at deploy.
- Row 8: record which login owns the HighLevel developer account (it should be WIA-owned: ai@ or hello@). At deploy, add the production redirect URL and the webhook URL (`/api/v1/leadlock/webhooks`).
- Row 7: record which WIA admin created the team key, and that it can see every team member's recorded meetings.
- Row 1: record who the Slack app's owner and collaborators are (api.slack.com → the app → Collaborators).
- At deploy, move every value into Railway variables and update the "Stored in" column.
