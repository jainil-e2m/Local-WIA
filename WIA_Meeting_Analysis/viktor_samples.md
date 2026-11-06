# Viktor samples to gather

Purpose: see how WIA asks Viktor for things, what it sends back, and what happens next, for each use in [`viktor_at_wia.md`](viktor_at_wia.md). Started 2026-09-24.

## For every sample, capture
- **Input:** the question word for word, or the scheduled task's instructions
- **Viktor's questions back**, if it asked any before answering
- **Output:** the full reply as posted. Take a screenshot if it has tables, colours or attachments, and keep the text too
- **What it used:** the data and date range it cites
- **Context:** date, channel or DM, client, who asked
- **Outcome:** what happened next (acted on? by whom? when?) and the user's one-word verdict: useful / noisy / wrong

**Where to find them.** Where "Get it from" says **Slack**, `AI@` can find the sample in the client channels it has been in since Sep 21. Search `from:@Viktor` for its posts and `@Viktor` for the questions people asked it. Everything else is a DM or an admin screen that only WIA can share.

**Pulling them with the Content Atelier app** (checked Sep 24)
- **What it can do:** the app's bot token can read full history, threads and files, but only in channels the bot is in. Today that's `#wia-ai-team-testing` only, and every client channel is private.
- **Before any pull:** get WIA's OK to invite the bot to the 11 `c_*` client channels and wherever the Monday snapshot is posted. The app was approved for three content channels, and each invite shows a notice in the channel.
- **The code change:** add a Viktor-only filter to `frontend/corpus/fetch-slack.mjs`. Keep only threads where Viktor (`U0BPF0MBD45`) posted or was mentioned.
- **What it can't reach:** DMs, search, and Viktor's own admin screens. The app covers the same 9 Slack items, not the other 23.

**Don't @-mention Viktor ourselves.**
- It spends WIA's credits.
- Its connections are shared across the workspace, so it could answer from Whitney's inbox on our behalf.

**Storage.** Store samples in `received/YYYY-MM-DD_viktor-samples/`. They contain client performance data and email content, so keep them internal.

## Samples

### 1. Call preparation
| # | Sample | How many | Get it from | Status |
|---|--------|----------|-------------|--------|
| 1.1a | Daily call prep: the scheduled task's instructions and schedule | 1 | Whitney (Viktor admin) | Not collected |
| 1.1b | Morning briefs, one per call type: sales call, ads kickoff, messaging & positioning interview, ads strategy call, monthly strategy call | 5 | Whitney (wherever she receives them) | Not collected |
| 1.1c | A follow-up where she dug deeper into a brief | 1–2 | Whitney | Not collected |
| 1.1d | A brief that recommended something unnecessary (the call-type problem) | 1 | Whitney | Not collected |
| 1.2 | Gap check before the interview: her prompt, the questionnaire, website and question list she gave it, and Viktor's answer | 1–2 | Whitney | Not collected |
| 1.3 | Danielle brief: Whitney's prompt, the brief, and where it was sent | 1 | Whitney / Danielle | Not collected |

### 2. Client status on demand
| # | Sample | How many | Get it from | Status |
|---|--------|----------|-------------|--------|
| 2.1 | "How are things going with…?" threads, for clients with different setups (e.g. full-service Elevate, LeadLock-only, the Shopify client) | 3–5 | Whitney; Slack for any in client channels | Not collected |
| 2.2 | "Where does this stand?" / "remind me" threads, including one wrong or incomplete answer | 2–3 | Whitney | Not collected |

### 3. Monitoring and alerts
| # | Sample | How many | Get it from | Status |
|---|--------|----------|-------------|--------|
| 3.1a | Unprompted recommendations, across Google, Meta and GHL | 5 | Slack | Not collected |
| 3.1b | What happened to each of those (fixed? when?), to measure the 1–1.5-week lag | same 5 | Carmen / ClickUp | Not collected |
| 3.2a | Anomaly alerts, including "zero leads over the past three days" and any false alarm | 2–3 | Slack / Whitney | Not collected |
| 3.2b | What triggers alerts (a scheduled check or Viktor's own initiative), and any thresholds | 1 | Whitney / Gisselle (admin) | Not collected |
| 3.3a | Monday snapshots, complete, from 2–3 consecutive weeks | 2–3 | Whitney (where it's posted is unknown) | Not collected |
| 3.3b | The snapshot's instructions and its green/yellow/red rules | 1 | Whitney / Gisselle (admin or memory) | Not collected |

### 4. Support for the ads managers
| # | Sample | How many | Get it from | Status |
|---|--------|----------|-------------|--------|
| 4.1 | Carmen's recap requests and Viktor's recaps, on different accounts | 3 | Slack; otherwise Carmen | Not collected |
| 4.2 | Fix checks: Carmen reports a fix done, and Viktor confirms it (or says it didn't stick) | 2 | Slack; otherwise Carmen | Not collected |

### 5. Team follow-through
| # | Sample | How many | Get it from | Status |
|---|--------|----------|-------------|--------|
| 5.1a | Open loops: the task's instructions | 1 | Gisselle | Not collected |
| 5.1b | Open loops: outputs from consecutive days, and which loops got closed | 3–5 | Gisselle | Not collected |
| 5.2a | ClickUp digest: its instructions, and whether it still runs (and uses credits) | 1 | Gisselle | Not collected |
| 5.2b | ClickUp digest: old outputs, plus Gisselle's own ClickUp filter to compare against | 1–2 + filter | Gisselle | Not collected |

### 6. Audits, SOPs and QA
| # | Sample | How many | Get it from | Status |
|---|--------|----------|-------------|--------|
| 6.1 | UTM: the thread where Viktor spotted it, its explanation, the final SOP, and the old and new UTM strings | 1 set | Slack / Whitney; the SOP from Drive or ClickUp | Not collected |
| 6.2 | GHL forms: the same set | 1 set | Slack / Whitney | Not collected |
| 6.3 | Page checks: threads where someone tagged @Viktor to check a domain (e.g. Ridgefield or The Penny, around Aug 21) | 1–2 | Slack | Not collected |

### 7. Client onboarding
| # | Sample | How many | Get it from | Status |
|---|--------|----------|-------------|--------|
| 7.1a | One recent client channel, from its creation: Viktor's first posts, and anything it did without being asked | 1 channel | Slack | Not collected |
| 7.1b | The per-client setup: adding Viktor to that client's Meta ad account and LeadLock sub-account (this isn't in the ClickUp templates) | 1 | Whitney | Not collected |

### 8. How Viktor is set up (admin screens)
| # | Sample | How many | Get it from | Status |
|---|--------|----------|-------------|--------|
| 8.1 | All scheduled tasks: instructions, schedule, where each posts, active or paused, including any Viktor proposed | full list | Whitney / Gisselle | Not collected |
| 8.2 | What it's been taught: memory entries and "skills" | full list | Whitney | Not collected |
| 8.3 | Connected tools: which accounts, who connected each, and whether it's shared with the team or personal | full list | Whitney | Not collected |
| 8.4 | The channels Viktor is in | list | Slack / Gisselle | Not collected |
| 8.5 | Plan, monthly credits, and usage by task | 1 | Whitney | Not collected |
| 8.6 | Anything it built outside Slack: PDFs, Pages, Spaces | all | Whitney | Not collected |
| 8.7 | Standing instructions on tone or length, if any | all | Whitney | Not collected |

**32 items.** We can start on 9 of them ourselves (the rows that start with "Slack"). The rest need WIA.

## If WIA can only give a few
1. Call-prep briefs, one per call type (1.1b), with the task's instructions (1.1a)
2. Two or three Monday snapshots and their colour rules (3.3)
3. The scheduled-task list (8.1)
4. Three of Carmen's recaps (4.1)

These map directly to knowledge base Phase 1 (call prep + top opportunities) and to reporting.

## Fastest way to get the WIA-only items
A 30-minute recorded screen-share:
- **Whitney and Gisselle** walk through the Viktor admin screens (8.1–8.7) and pull up their DMs (sections 1, 2, 3.3 and 5).
- **Carmen** joins for 10 minutes (section 4).

Zoom keeps the transcript, so the session itself becomes a source.

## Change log
| Date | Change |
|------|--------|
| 2026-09-24 | Checklist created; nothing collected yet |
