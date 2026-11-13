# Build order

What to do, in order, before continuing the KB implementation. Tick each step off as it's done.

---

## Step 1: Install Ponytail in Claude Code (do this first)

Ponytail is a Claude Code plugin. Once installed, it adds its active rule set before every Claude turn, and passes the same rules to any sub-agents Claude starts. Delegated or parallel work therefore follows the same minimalism rules as the main session.

**⚠️ Use `DietrichGebert/ponytail`, not `dietrichayala/ponytail`.** The install snippet shared on 6 Nov names `dietrichayala/ponytail`, but that repo doesn't exist. There's no GitHub user `dietrichayala` at all. Every Ponytail port credits `DietrichGebert/ponytail` as the original. Never install from the misspelled name: anyone could register it later, and plugin hooks run on every turn.

**Reviewed 6 Nov 2026 (`DietrichGebert/ponytail`, plugin v5.3.3, MIT licence):**

| What | Finding |
|---|---|
| Hooks | Three Node hooks, at session start, sub-agent start and each prompt. They add Ponytail's rules, pass them to sub-agents, and track its on/off mode |
| Commands it runs | `git ls-files` and `git rev-parse` (to map the repo), and its own scripts |
| Files it writes | Mode flags and config, plus a per-project "task board" CSV (cost, turns, tokens, tests per task) in `~/.config/ponytail/band/`. The CSV is on by default; turn it off with the `ledger` option |
| Network | None by default. The only network call is an optional task-board webhook (`webhookUrl`), which is empty unless someone sets it. Leave it empty: it would send task names and costs off the machine |
| Extras | Slash commands `/ponytail`, `/ponytail-review`, `/ponytail-audit`, `/ponytail-debt`, `/ponytail-gain`, `/ponytail-help` |

**Install. Choose either option. Both install at project scope**, so Ponytail applies to Claude sessions run in this workspace (`Wedding_Industry_Ads`), not to every project on the machine:

*Option A: inside a `claude` session in a terminal, started in `Wedding_Industry_Ads`:*

```text
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```

When it asks for a scope, choose **project**.

*Option B: PowerShell, in `Wedding_Industry_Ads`, using the Claude Code copy bundled with the desktop app (the `claude` command isn't on PATH on this machine):*

```powershell
& "$env:APPDATA\Claude\claude-code\2.1.317\a33aa5518497\claude.exe" plugin marketplace add DietrichGebert/ponytail --scope project
& "$env:APPDATA\Claude\claude-code\2.1.317\a33aa5518497\claude.exe" plugin install ponytail@ponytail --scope project
```

The version folder (`2.1.317\a33aa5518497`) changes when the app updates. Use the newest folder under `%APPDATA%\Claude\claude-code\`.

**Notes:**
- Project scope writes `enabledPlugins` (and the marketplace) to `Wedding_Industry_Ads\.claude\settings.json`. That file doesn't exist yet; the existing `settings.local.json` and `launch.json` aren't touched.
- Ponytail runs Node.js hooks, so Node.js must be installed. The frontend already needs it.
- **Check it worked:** run `/plugin` (or `claude plugin list`) and confirm `ponytail` shows as installed and enabled. Then start a new session so its hooks load.
- **To remove it:** `/plugin uninstall ponytail@ponytail`.

- [x] Ponytail installed and enabled (verified 6 Nov 2026: `ponytail@ponytail` v5.3.3, project scope, enabled, from `DietrichGebert/ponytail`; its skills load in new sessions)

---

## Step 2: Then continue the implementation

Pending from the 5–6 Nov work on Connections (details in `backend/README.md`, under "Mapping sub-accounts to clients"):

- [x] **Resume reading on reactivate and link** (6 Nov: the scheduler sweep in the worker, streams switched on after the first copy, the resumable path for every copy, reactivation re-checks, LeadLock every 6 h; see `backend/docs/production-readiness.md` BF-4 and the Scheduler row. Email, calendar and Fathom still need P-02 below.)
  - Reactivating a client, or linking a source, should switch on its sync stream and queue a resume for each of its sources:
    - Slack, ClickUp and Drive continue from their saved positions.
    - LeadLock re-reads the whole sub-account.
    - Email, calendar and Fathom need the P-02 catch-up for the paused weeks.
  - Set a sensible update interval per source (hours for LeadLock, not 5 minutes).
- [x] **Leads tab keeps showing history after an unlink.** (6 Nov) Show "Not collected since …" instead of "No LeadLock sub-account mapped".
- [x] **P-02 catch-up for late contacts.** (6 Nov: `qualify.recheck`; Calendar and Fathom now keep pointers too) When a contact is approved, re-check the mail, calendar events and Fathom meetings already read, so they attach.
- [x] **Snapshot tabs.** (6 Nov: production reads the live portfolio build, `GET /api/v1/portfolio`, rebuilt after each copy and mapping change) Every tab except Leads and Connections reads `frontend/src/kb-live.local.json`. Make those tabs read live, or rebuild the snapshot automatically after any mapping change.
- [ ] **Production blockers** (see the Connections write-up):
  - production's own LeadLock install, redirect URI and webhook URL (the agency refresh token can't be shared with local development);
  - admin login (S10) before the Connections, Leads and add-client endpoints leave local-only mode; (interim 6 Nov: the shared team password; named sign-in still to come)
  - spending cap and pause on the AI extraction queue before switching it on. (built 6 Nov: `AI_MODE` and `AI_MONTHLY_BUDGET_USD`; the AI stays off)
- [ ] **Deploy to Railway** with the AI off and backfills on command: runbook in `backend/README.md`, "Deploying to Railway".
