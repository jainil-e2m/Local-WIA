# WIA Access Ledger

Every access E2M has received from Wedding Industry Ads: what it reaches, where its credential is kept, and how to undo it.
**As of 2026-09-24.** Built from:
- two written requests and WIA's replies: the Sep 3 feasibility request, and the ~Sep 15–17 requirements doc answered by the **Sep 21 handover**
- the meeting analyses (M00–M05)
- `frontend/Content_Atelier.md` §8
- `.clickup-snapshot/` and the `frontend/corpus/` fetch logs
- the git remotes, and the *names* of configured variables in `frontend/.env*`

> **No secrets in this file.** Never paste passwords, tokens, API keys or 2FA codes here. Record *where* each one lives: a LastPass entry, or a `.env` variable name.
> **Share links that open for anyone who holds them** (Fathom, ChatGPT, Canva edit links, GHL email previews) are treated the same way. Record where the link lives, not the URL. The raw messages are kept locally, marked sensitive, under [`received/`](received/).
> `frontend/.env` and `.env.local` are git-ignored and have never been committed (checked 2026-09-24).

**Status key**
- **Active:** verified in use
- **Partial:** works, but doesn't reach what we need
- **Unconfirmed:** granted, not yet verified
- **Pending:** requested, not received
- **Not requested:** needed, never asked for

Fields marked *TBD* are waiting on details you'll supply.

---

## Requests log

### Request 1 · 2026-09-03: technical-feasibility request (Jainil → Whitney, Gisselle; E2M Slack thread)
This is the "list of items needed for technical feasibility" promised in M01 and M02; it went out the day after M02.

**Replies:**
- **Fri Sep 4** (inferred from "have a great weekend"): Gisselle's first batch
- **Sep 4–7:** Jainil's reply: accepting the invites and "will confirm the permission levels"; the Zoom `.txt` preferred; a ChatGPT fallback
- **Tue Sep 8** (inferred from "out yesterday for Labor Day"): Gisselle's second batch

| # | Asked for | What came back | When | Status |
|---|-----------|----------------|------|--------|
| 1.1 | `AI@` account. E2M changed its password at first sign-in and shared the new one via LastPass to `whitney@whitneyhodges.com` and `gisselle@dotandcompany.co` | n/a (E2M → WIA) | Sep 3 | Done (#1) |
| 1.2 | **ClickUp: a Member seat, not Guest** (guests can't open templates) | Invite | Sep 4 | **Done.** Member confirmed: templates read Sep 8 (#4) |
| 1.3 | **GoHighLevel: Agency Admin** (should cover LeadLock Pro too) | Invite | Sep 4 | Received. **Level: TBD** (#5) |
| 1.4 | **Members portal:** Google Search Accelerator, Meta Ads Accelerator and Announcements channels | Invite | Sep 4 | Unconfirmed (#16) |
| 1.5 | **Slack:** the workspace and the client channels | Invite; channels "once invite is accepted" | Sep 4 | ✔ Workspace; **all client channels ✔ (Sep 21)** (#7) |
| 1.6 | **Dubsado:** "contract signed" and "invoice paid" emails as attachments, plus **one completed onboarding questionnaire** | "Forwarded dubsado emails" | Sep 4 | Emails ✔. **Questionnaire not sent: TBD** |
| 1.7 | **Fathom:** 2 office-hours transcripts + 1 client meeting, **exported** (to test whether attendee names come through as data) | 2 Fathom **share links** (Google Ads office hours, Meta Ads office hours) | Sep 4 | **Partial.** Not exports, so **the attendee-data test hasn't been possible** (#15) |
| 1.7b | The client meeting | Whitney uses Zoom → Jainil asked for the `.txt` → **Zoom `.txt` of an onboarding call** (Drive link) | Sep 4 → Sep 8 | ✔ |
| 1.8 | **Drive:** one onboarded client's folder, and whether folders live in someone's own Drive or a **Shared Drive** | **Ridgefield's** folder, plus an **invite to WIA's whole Shared Drive**. `wia+ridgefield` is the client-shared sub-folder | Sep 4 | ✔ Answer: **Shared Drive** (#3) |
| 1.9 | **Monthly reporting:** one complete report, **plus its walkthrough video** | A client report (Canva edit link) + the report template (Canva link) | Sep 4 | **Partial. No video** |
| 1.10 | **Email templates:** recap, welcome, invoice nudge, campaign review | "Full service email templates" Drive folder | Sep 4 | Received. **Which of the four: TBD** |
| 1.11 | **ChatGPT:** one client's whole Project | Blocked ("will remove all files from the project"). Fallback, Sep 8: **1 shared chat + the custom instructions + 3 WIA playbooks**; "all uploads are from the client folder" | Sep 4 → Sep 8 | ✔ [`received/2026-09-08_chatgpt-project/`](received/2026-09-08_chatgpt-project/) (#12) |

### Request 2 · ~2026-09-15 → 17: Client Requirements doc for the content engine (prepared by Jainil) → reply **Sep 21** (the access handover)
- **Sent:** a first version ~Sep 15 (M04: "from Asha probably yesterday"), updated after the M04 scoping call.
- **Records:** [`requirements-doc.md`](received/2026-09-21_access-handover/requirements-doc.md) and WIA's [`reply.md`](received/2026-09-21_access-handover/reply.md) (verbatim, sensitive).
- **Why the reply is dated Sep 21:** its contents match the "21 September handover" state in `Content_Atelier.md` §8.

| # | Asked for | What came back (Sep 21) | Status |
|---|-----------|-------------------------|--------|
| 2.1 | **Central Google account** `AI@` ("created by WIA, managed by E2M") | Credentials shared via LastPass to **`jainil.trivedi@e2m.solutions`** | ✔ (#1) |
| 2.2 | **OpenRouter** (pay per execution; "1st recharge $20") | Account created on the `AI@` Gmail; credentials via LastPass | ✔ **$20 top-up done? TBD** (#10) |
| 2.3 | **Railway** ($5/month) | "Railway / Github: account was **already created** but I wasn't sure if it had been created by E2M. **Password was reset** and shared through LastPass" | Received. **Who created it, and did the reset break anything? TBD** (#11, #17) |
| 2.4 | **Zoom call recordings, past 3 months** | `AI@` Zoom user + a role for recordings and transcripts. "We delete client meetings to save Zoom storage"; they're filed in client folders in the Shared Drive. Also: the **WIA \| Marketing › Results Social Proof › Call with Clients** folder | ✔ Recordings deleted from Zoom; **transcripts kept (M05)** (#9, #3) |
| 2.5 | **Fathom / AI-notetaker meeting links** | "Whitney is only using Zoom. The team has Fathom mainly for internal meetings and Office Hours." Seven office-hours recordings: **4 Google Ads (Jul 9, Aug 13, Aug 20, Aug 27) as Drive `.mp4`**, **1 Meta Ads (Aug 27) as a Fathom link**, **2 "Impromptu Zoom Meeting" `.mp4`s** (Jun 11, Aug 20) | **Partial**: 6 of 7 are video only (#15) |
| 2.6 | **Founder-voice document** | **Two:** "Founder voice guide" and "Whitney Founder Voice Knowledge Base" | ✔ |
| 2.7 | **Marketing strategy document** (outside consultant) | "Strategy from WLF" | ✔ |
| 2.8 | **Historic monthly workshops, past 3 months** | **Six** workshop files in Drive (UVP; inquiry-funnel audit; ads-traffic landing pages; Messaging & Positioning Questionnaire; brand & lead generation with Emily Foster; market research). "Transcripts and summaries can be found in zoom account by looking up 'workshop'" | ✔ |
| 2.9 | **ChatGPT account access (`hello@`)**, "to review existing chat history… via LastPass" | "Access shared through LastPass", plus one chat ("Podcast Reel Scripts generation"). **2FA then blocked the login**, which led to M05's +91 phone on `hello@` | ✔ Then widened (#12, #13) |
| 2.10 | **Slack: `#social-proof-and-results`** | "Added to **all client channels** and social-proof-and-results" | ✔ More than asked (#7) |
| (extra) | Not requested | **"Additional Source Content": five source → output chains** (see *Files handed over*) | ✔ The calibration material for the content engine |

**What Request 2 didn't cover, and how each was handled:**
- **GHL API:** not in the doc, but **access is in place** (the Private Integration Token; confirmed by Jainil, Sep 24). Not a gap.
- **Instagram and Canva:** asked for separately, through **access guides shared with WIA** (Request 3).
- **Still never requested:** a Fathom API or Team plan, and speech-to-text (which is E2M's to provision). Descript too, unless it went with the Canva guide.

### Request 3 · Instagram and Canva access guides (Jainil → WIA, shared for review)
The guides were written **Sep 22** (file dates). The date they were shared with WIA, and the channel, are *TBD*. **Status: waiting on WIA.**

| Guide | What WIA has to do | Then E2M does | Status |
|-------|-------------------|---------------|--------|
| [`frontend/corpus/instagram-app-setup.md`](../frontend/corpus/instagram-app-setup.md): Instagram Graph API | **Confirm `@weddingindustryads` is a Business or Creator account.** If it's Personal, the whole route is blocked. Create the Meta app (the guide suggests doing it on `AI@`, so WIA is the admin) | Add the Instagram product; generate a long-lived token; record `IG_TOKEN` + `IG_USER_ID` in `.env` | Waiting on WIA |
| [`frontend/corpus/canva-descript-access.md`](../frontend/corpus/canva-descript-access.md) §1: Canva Connect | **Confirm the Canva plan allows private integrations** (Canva Free is a real fork). A **WIA team admin** creates the integration and passes the client ID and secret to E2M | Complete OAuth; store the refresh token. Read-only; the route is export to PPTX, then extract the text | Waiting on WIA |
| Same doc, §2: Descript | Add `AI@` to the Descript workspace (viewer or editor), or Gisselle exports the transcripts herself | Export each reel's transcript | **Confirm this part went with the Canva guide** |

---

## At a glance

| # | Access | Identity / credential | Type | Status | Received | Used by |
|---|--------|----------------------|------|--------|----------|---------|
| 1 | Google Workspace user | `AI@weddingindustryads.com` | Account | **Active** | by Sep 3 | Everything |
| 2 | Gmail | `AI@` inbox | Account | **Active** | by Sep 21 | A |
| 3 | Google Drive: **WIA's Shared Drive** (all files) | shared to `AI@` | Shared Drive member | **Active** | Sep 4 | A, C |
| 4 | ClickUp | `AI@` **Member** seat + `CLICKUP_TOKEN` (+ team / templates-space IDs) in `.env.local` | Seat + personal API token | **Active** | Sep 4 / by Sep 8 | Onboarding MVP; C |
| 5 | LeadLock / GHL web app | `AI@` user (Agency Admin requested) | User seat | **Active**, level TBD | Sep 4 | A, B, C |
| 6 | LeadLock / GHL API | `GHL_PIT` + `GHL_LOCATION_ID` in `.env` | Private Integration Token | **Active** | Sep 21–22 | A |
| 7 | Slack workspace member | `AI@` person, in **all client channels** + `#social-proof-and-results` | Workspace member | **Active** | Sep 4 / Sep 21 | A, C |
| 8 | Slack bot (Content Atelier app) | `SLACK_BOT_TOKEN` in `.env` | Bot token | **Partial** | Sep 22 | A (C later) |
| 9 | Zoom | `AI@` user with a custom role (recordings, transcripts, summaries) | Account role | **Partial** | Sep 21 | A, C |
| 10 | OpenRouter | account on `AI@`; credentials via LastPass | Account + API key | **Active** | Sep 21 | A, B, C |
| 11 | Railway | account on `AI@` (**already existed**; WIA reset the password) | Account | **Received**, creator TBD | Sep 21 | Hosting |
| 12 | ChatGPT (shared account) | 1 chat + instructions (Sep 8); login via LastPass + 10 chats (Sep 21); `hello@` 2FA (Sep 22) | Share links → login | **Partial / Unconfirmed** | Sep 8 / 21 / 22 | A, C |
| 13 | **`hello@` Google account** | password via LastPass + **E2M +91 phone as 2nd 2FA** | Full account | **Unconfirmed** (test was due Sep 23) | Sep 22 | Calendar, ChatGPT |
| 14 | Whitney's Google Calendar | through `hello@` | Account (via #13) | **Unconfirmed** | Sep 22 | A, C |
| 15 | Fathom | **2 share links** in total: Google Ads office hours (Sep 4) and Meta Ads office hours Aug 27 (Sep 4, re-sent Sep 21) | Share links | **Partial** | Sep 4 / 21 | A |
| 16 | Members portal (GHL Communities) | `AI@` invited to 3 channels | Portal member | **Unconfirmed** | Sep 4 | Portal posts (not picked) |
| 17 | **GitHub** | account on `AI@` (**already existed**; WIA reset the password with Railway's) | Account | **Received**, creator TBD | Sep 21 | Repo ownership at handover |

*Streams:* **A** Marketing & Content Engine · **B** Paid Media Reporting · **C** Maintained Client Knowledge Base

---

## Details

### 1. `AI@weddingindustryads.com`: the white-label identity
- **Status:** Active
- **Why it exists:** in M02, E2M asked for one white-label identity so that all access is scoped to it and can be revoked in one place.
- **Received:**
  - WIA created it before Sep 3.
  - **Sep 3:** at first sign-in E2M changed the password and shared it via LastPass to Whitney and Gisselle.
  - **Sep 21:** WIA shared the credentials via LastPass to **`jainil.trivedi@e2m.solutions`**. The E2M holder is Jainil, not Minu as M02 had planned.
- **LastPass entry name:** *TBD*
- **WIA holders:** Whitney (`whitneyhodges.com`) and Gisselle (`dotandcompany.co`). **Neither is a WIA-domain account.** If either person leaves, their share has to be removed. This is the same key-person risk as M00.
- **Reaches:** Gmail (#2), Drive (#3), ClickUp (#4), GHL (#5), Slack (#7), Zoom (#9), OpenRouter (#10), Railway (#11), the members portal (#16), GitHub (#17).
- **Limits:** 2FA blocked E2M from Whitney's calendar and from ChatGPT, which is why the `hello@` route was used (M05).
- **Revoke:** ⚠ **Don't delete `AI@`.** WIA's own assets live under it. To remove E2M, rotate its password and 2FA and remove E2M from the LastPass share.

### 2. Gmail (`AI@` inbox)
- **Status:** Active (Sep 21). This is the white-label inbox only, *not* `hello@` (for that, see #13).

### 3. Google Drive: WIA's Shared Drive
- **Status:** Active
- **Received (Sep 4):** an **invite to WIA's whole Shared Drive** ("where we keep all of our files") and **Ridgefield's** client folder.
- **Structure:**
  - Client folders are grouped **by offer**. Each has a **"call recordings and transcripts"** folder (M05).
  - **The `wia+<client>` sub-folders (e.g. `wia+ridgefield`) are shared with the client.** ⚠ Never write internal material into them.
- **Named locations (Sep 21):**
  - **WIA | Marketing › Results Social Proof › Call with Clients**, the curated client calls for marketing, and the best source for the content engine
  - office-hours `.mp4`s
  - the six workshop files
  - the founder-voice and WLF strategy docs
- **Permission level:** *TBD*
- **Revoke:** remove `AI@` from the Shared Drive's members.

### 4. ClickUp
- **Status:** Active
- **Seat:** **Member** (the Sep 3 request specified "not Guest"). Confirmed because templates could be read on Sep 8.
- **Credential:** `CLICKUP_TOKEN`, `CLICKUP_TEAM_ID` and `CLICKUP_TEMPLATES_SPACE_ID` in `frontend/.env.local`
- **Pulled Sep 8–9:** templates, fields, a client list, and 103 task descriptions (`.clickup-snapshot/`)
- **Token:** a personal token, probably the `AI@` member's *(TBD)*. **It has every permission that member has, so there's no read-only mode.** So far it has only been used to read.
- **Revoke:** regenerate the token, then remove the member.

### 5. LeadLock / GHL web app
- **Status:** Active; level TBD
- **Requested (Sep 3):** **Agency Admin**, which should also cover LeadLock Pro. Invite Sep 4.
- **Level actually granted:** *TBD*. It decides whether we can reach **client sub-accounts** (streams B and C).
- **Revoke:** remove the user from the agency team.

### 6. LeadLock / GHL Private Integration Token
- **Status:** Active
- **Credential:** `GHL_PIT` and `GHL_LOCATION_ID` in `frontend/.env`. Location = WIA's own sub-account `Xi40zxmRvW8Pbyk5DYHp`, **not the client sub-accounts.**
- **Scopes:** meant to be read-only (`corpus/ghl-scopes.md`). *Confirm the actual token's scopes: TBD*
- **Received:** Sep 21–22. It wasn't on either written request, but it's in place (**confirmed by Jainil, Sep 24**). Used on **Sep 22 to pull 126 sent campaigns**.
- **Stored at:** LastPass. Entry: *TBD*
- **Revoke:** delete it under Settings → Private Integrations.

### 7. Slack: `AI@` as a workspace member
- **Status:** Active
- **Received:** workspace invite Sep 4. On **Sep 21** it was added to **all client channels** and `#social-proof-and-results` (Request 2 asked only for the latter). The Sep 21 notes also list `#google-search-accelerator` and `#meta-ads-accelerator`.
- **Revoke:** deactivate the member.

### 8. Slack bot (Content Atelier app)
- **Status:** Partial
- **Credential:** `SLACK_BOT_TOKEN` in `frontend/.env`. Read-only scopes.
- **Received:** Sep 22. The only pull so far is the private test channel `#wia-ai-team-testing` (`C0C3FT6DZAS`).
- **Gap:** **the bot isn't in the content channels** (a bot token sees nothing until the bot is invited).
- **Checked Sep 24 (read-only, metadata only):**
  - The bot is still in `#wia-ai-team-testing` only.
  - `#general` is the only public channel. **Every client channel is private**, so each one needs an `/invite`.
  - Viktor's bot user is `U0BPF0MBD45`. The directory also shows a ChatGPT app, Zapier, LeadConnector, ClickUp, Google Drive and Google Calendar.
  - Reading client channels (e.g. for Viktor samples) is **a new scope** beyond the three content channels the app was approved for. **Get WIA's OK first** (`viktor_samples.md`).
- **Revoke:** uninstall the app.

### 9. Zoom
- **Status:** Partial
- **Received (Sep 21):** an `AI@` Zoom user, plus "a role… so the account has access to recordings and transcripts". Gisselle showed it in M05.
- **Retention:**
  - WIA "delete[s] client meetings to save Zoom storage". The *recordings* go into client Drive folders.
  - Gisselle in M05: **transcripts and summaries aren't deleted.**
  - Workshop transcripts and summaries can be found by searching "workshop".
- **Check:** Zoom Admin → Transcripts for recent client calls, before provisioning speech-to-text. `Content_Atelier.md` §8 (edited Sep 23) still says client calls are video only.
- **Already done:** **two workshop recordings were transcribed locally on Sep 9** (`transcripts/`): "Building a Brand That Supports Premium Lead Generation" and "Real-World Ads Traffic Landing Page Examples". The local pipeline works on this material.
- **Revoke:** remove the role or the user.

### 10. OpenRouter
- **Status:** Active
- **Received (Sep 21):** an account on the `AI@` Gmail; credentials via LastPass. WIA owns it and pays.
- **Cost as written (Request 2):** "Pay per execution. 1st Recharge 20$." Was the $20 top-up made? *TBD*
- **API key stored at:** *TBD* (not in `frontend/.env`)
- **Gaps:** **no spend cap**; no transcription model selected
- **Revoke:** rotate or delete the key.

### 11. Railway
- **Status:** Received; the creator is unknown
- **Asked for:** in Request 2 ("$5/month"; access guide provided)
- **Received (Sep 21):** "Railway / Github: account was **already created** but I wasn't sure if it had been created by E2M. **Password was reset** and shared through LastPass."
- **To settle:**
  - Who created it? Probably E2M, during the prototype work *(confirm)*.
  - Are the deployed apps (Command Center, timeline app) under this account or a personal one? *TBD*
  - Did the password reset cut off any deploy integration? OAuth-linked GitHub deploys usually survive a password change, but check. *TBD*
- **Revoke:** remove E2M from the Railway project or team.

### 12. ChatGPT (the shared account)
- **Status:** Partial / Unconfirmed
- **Received:**
  - **Sep 8:** one shared chat, the Project's **custom instructions** and **3 playbooks** ([`received/2026-09-08_chatgpt-project/`](received/2026-09-08_chatgpt-project/))
  - **Sep 21:** "access shared through LastPass" (the `hello@` login), plus **10 unique shared chats**. Eleven links were listed, but one appears twice (see *Files handed over*).
  - **Sep 22:** 2FA blocked the login, so an E2M phone was added to `hello@` (#13)
- **Account:** paid, ~$20/month
- **Revoke:** covered by #13. Then sign out all sessions.

### 13. `hello@weddingindustryads.com`: the main company Google account
- **Status:** Unconfirmed (test was due Sep 23). *Result: TBD*
- **In writing (Request 2):** access to the **ChatGPT** account on `hello@`, "to review existing chat history, founder-voice context, and prior conversations", shared via LastPass.
- **What was actually granted (M05, Sep 22):**
  - the **`hello@` password**
  - an **E2M +91 phone as a secondary 2-step-verification method**
  - **Whitney's calendar** added verbally
- **So the reach is wider than the written purpose.** The whole Google account: the company inbox with all client communication, its Calendar and Drive, and any "Sign in with Google" service.
- **Holder of the +91 number:** *TBD*
- **End date:** *TBD*
- **Revoke:**
  1. Remove the +91 phone from 2-Step Verification
  2. Rotate the password
  3. Sign out all sessions
  4. Review third-party access
- **Lighter replacements:** share the calendar with `AI@`; the ChatGPT data export.

### 14. Whitney's Google Calendar
- **Status:** Unconfirmed (reached through #13). Needed to find calls calendar-first (M05).
- **Recommended instead:** calendar sharing to `AI@`.

### 15. Fathom
- **Status:** Partial
- **Received:** **two unique share links in total**
  - Google Ads office hours (Sep 4)
  - Meta Ads office hours, Aug 27 (Sep 4, re-sent Sep 21)
  - Other Google Ads office hours came as **Drive `.mp4`s** (Sep 21).
- **Usage:** "The team has Fathom mainly for internal meetings and Office Hours"; Whitney uses only Zoom.
- **Gaps:**
  - no export (so the attendee-data test hasn't been run)
  - no API key; the accounts are individual and probably free
  - `FATHOM_API_KEY` is empty
- **Next:** decide on a Fathom Team account after the Zoom review.

### 16. Members portal (GHL Communities)
- **Status:** Unconfirmed. Invited Sep 4 to Google Search Accelerator, Meta Ads Accelerator and Announcements. *Membership confirmed: TBD*

### 17. GitHub (`AI@` account)
- **Status:** Received; the creator is unknown
- **Received (Sep 21):** bundled with Railway. An account existed on `AI@`; **WIA reset the password** and shared it via LastPass.
- **Why it matters:** M03 told WIA "the entire code and the repo… tied to the AI at wedding email address". **Today the repos are under an E2M engineer's account** (see *Held by E2M on WIA's behalf*). This `AI@` GitHub is where they should end up.
- **Revoke:** rotate the password and 2FA; remove E2M collaborators. **Don't delete it**; it will own WIA's code.

---

## Files handed over (data, not access)
| Item | From | When | Where it is |
|------|------|------|-------------|
| Task-audit sheet (12 rows) | Gisselle | Aug 25–26 | M01 |
| "A few documents" | Gisselle | before Sep 2 | M02 |
| Dubsado notification emails ("contract signed", "invoice paid") | Gisselle | Sep 4 | `AI@` inbox |
| Ridgefield client folder (incl. the client-shared `wia+ridgefield`) | Gisselle | Sep 4 | Shared Drive |
| A client monthly report + report template | Gisselle | Sep 4 | Canva (links in the Slack thread). *No walkthrough video* |
| "Full service email templates" | Gisselle | Sep 4 | Drive folder |
| Zoom `.txt` of a client onboarding call | Gisselle | Sep 8 | Drive link (Slack thread) |
| ChatGPT custom instructions (v1) + 3 WIA playbooks + 1 shared chat | Gisselle | Sep 8 | [`received/2026-09-08_chatgpt-project/`](received/2026-09-08_chatgpt-project/) |
| **Founder voice guide** + **Whitney Founder Voice Knowledge Base** + **Strategy from WLF** | WIA | Sep 21 | Google Docs |
| **Six workshop recordings** (+ transcripts in Zoom, searchable by "workshop") | WIA | Sep 21 | Drive |
| **Seven office-hours recordings** (6 `.mp4`, 1 Fathom) | WIA | Sep 21 | Drive / Fathom |
| **Five source → output chains** ("Additional Source Content"): the calibration material | WIA | Sep 21 | [`reply.md`](received/2026-09-21_access-handover/reply.md) |
| 5 Instagram posts; 6 GHL email previews; 10 unique ChatGPT chats (all inside the chains above) | WIA | Sep 21 | same |
| Requirements-tracker documents; knowledge-base documents | Gisselle | by Sep 22 | M05 |
| *E2M-made:* local transcripts of 2 workshops | E2M | Sep 9 | `transcripts/` |

**The five chains** (source → what WIA made from it):
| Chain | Source | Outputs | Notes |
|-------|--------|---------|-------|
| **Defining your UVP** (workshop) | Drive video | 3 ChatGPT chats (reel scripts, workshop planning, marketing email) | Also a "WIA Marketing week of 9.14.26" chat |
| **Miss Lyss** (planning check-in call) | Drive video | ChatGPT email chat → 1 GHL email → 2 IG posts → **a case-study doc** | |
| **Carroll Hall** (Whitney's monthly Q&A) | Drive video **+ transcript** | 2 GHL emails; ChatGPT marketing chat; **a case-study chat** | ⚠ Its "marketing generation" chat link is the **same link** as Miss Lyss's. One of the two is wrong |
| **Funktastic** (strategy call results) | *no source link given* | 2 IG reels; 2 GHL emails; ChatGPT content chat | `Content_Atelier.md` treats this as *the* benchmark chain |
| **Market Research** (workshop) | Drive video | 1 GHL email; 1 IG post; 2 ChatGPT chats | |

- **Carroll Hall is a second chain that can be scored.** It has a transcript and outputs, so Funktastic isn't the only one, as `Content_Atelier.md` says. *Check this.*
- **Two chains end in a case study** (Miss Lyss, Carroll Hall). That's evidence WIA really does make case studies, which bears on the open "is the case study a fifth format?" decision.

---

## Requested or needed, not yet received
| Access / item | Needed for | Asked | Next step |
|---------------|-----------|-------|-----------|
| **Completed Dubsado onboarding questionnaire** | Onboarding; C | Request 1 | Not sent. The Sep 21 "Messaging & Positioning Questionnaire" is listed as a workshop. Check whether it's the questionnaire; either way it isn't a *completed* one |
| **Monthly report walkthrough video** | B | Request 1 | Re-ask |
| **Fathom exports** (not share links) | Roll-call feasibility; A | Request 1 | Re-ask, or settle through the Fathom Team / API decision |
| **Confirmation of permission levels** (GHL Agency Admin especially) | B, C | E2M promised (Sep 4–7) | Check and record in #5 |
| Which of the 4 email template types are in the folder | Drafting | Request 1 | Check the folder |
| **OpenRouter $20 top-up** | A, B, C | Request 2 | Confirm |
| **Railway / GitHub: who created them; did the reset break any deploy link** | Hosting, repo transfer | Request 2 reply | Confirm (#11, #17) |
| **Funktastic chain: the source recording or transcript** | A (the acceptance test) | — | Not in the Sep 21 list. Locate it |
| **Carroll Hall vs Miss Lyss: the duplicated ChatGPT link** | A | — | Ask which chat belongs to which |
| Slack bot invited to the content channels | A | Setup doc Sep 21–22 | `/invite` the bot |
| Instagram Graph API (`IG_TOKEN`, `IG_USER_ID`) | A | **Request 3**: access guide shared with WIA | Waiting on WIA: confirm Business/Creator; create the Meta app (on `AI@`) |
| Canva Connect (private integration) | A | **Request 3**: access guide shared with WIA | Waiting on WIA: confirm the plan allows private integrations; a WIA team admin creates it |
| Descript workspace seat | A | In the same Canva/Descript guide | Confirm the Descript part was shared too |
| Fathom Team / API keys | A, C | M02, M04, M05 (**not in Request 2**) | After the Zoom review |
| LeadLock kickoff recordings (Danielle) | C, A | M05 | Widen access, or Danielle uses a team Fathom |
| **Google Ads MCC; Meta ad accounts; client LeadLock sub-accounts** | B, C | Not yet requested | Needs its own requirements doc for B/C |
| Shopify (one client); feedback surveys; LeadLock tickets | C | Raised M05 | Not requested |
| Speech-to-text *(E2M-side)* | A, C | — | Only for gaps. The local pipeline is already proven here (Sep 9) |
| **Replacements for `hello@`**: calendar share to `AI@`, ChatGPT export | A, C | Recommended | Propose with the SOW |

---

## Held by E2M on WIA's behalf
| Item | Where | Status |
|------|-------|--------|
| **Code repos** | `github.com/jainil-e2m/WIA-Command-Center` and `github.com/jainil-e2m/WIA-Automation-Timeline` (from the git remotes, Sep 24) | ⚠ **On an E2M engineer's account.** M03 promised the repo "tied to the AI@ email". Transfer to the `AI@` GitHub (#17), or add it as owner, before handover |
| `AI@` password (changed at first sign-in) | LastPass → Whitney, Gisselle (Sep 3) | Done |
| Command Center prototype login | `CLIENT_EMAIL` / `CLIENT_PASSWORD_HASH` in `frontend/.env`; sent via LastPass after M03 | Unconfirmed |
| Timeline / progress link | `WIA-Automation-Timeline/` on Railway (whose account? #11) | Shared (M05) |

---

## Revocation checklist (at a pause or at the end)
1. **Transfer first.** Move the repos to the `AI@` GitHub. Confirm the Railway projects sit under the `AI@` Railway account.
2. **`hello@`:**
   - remove the E2M +91 phone from 2-Step Verification
   - rotate the password
   - sign out all sessions
   - review third-party access
3. **`AI@` (and its GitHub and Railway):** rotate the passwords and 2FA, and remove E2M from the LastPass shares. **Keep the accounts**: they own WIA's assets. Also review WIA's own LastPass holders (non-WIA addresses).
4. **Tokens:**
   - delete the GHL Private Integration
   - uninstall the Slack app
   - regenerate the ClickUp token
   - rotate the OpenRouter key
5. **Seats and roles:** remove `AI@` from the Shared Drive, ClickUp, GHL, the members portal, Slack and the Zoom role, and disable the Fathom share links.
6. **Local copies:**
   - purge `frontend/.env*`
   - delete or return `frontend/corpus/`, `transcripts/` and `received/`, as agreed
7. Record every step in the change log below.

---

## Change log
| Date | Change | Source |
|------|--------|--------|
| 2026-09-03 | Request 1 sent. `AI@` password changed by E2M at first sign-in and shared back to Whitney and Gisselle | Slack thread |
| 2026-09-04 | Invites: ClickUp, HighLevel, members portal, Slack, **WIA Shared Drive**. Samples: Ridgefield folder, Dubsado emails, 2 Fathom links, Canva report + template, email templates. ChatGPT Project sharing blocked | Slack thread |
| 2026-09-04–07 | Jainil: accepting invites; will confirm levels; Zoom `.txt` preferred; ChatGPT fallback | Slack thread |
| 2026-09-08 | Zoom `.txt` of an onboarding call. ChatGPT chat + custom instructions + 3 playbooks. ClickUp API pull (proves the Member seat) | Slack thread; `.clickup-snapshot/` |
| 2026-09-09 | E2M transcribed 2 workshop recordings locally | `transcripts/` |
| ~2026-09-15 → 17 | Request 2 (Client Requirements doc for the content engine) sent, then updated after M04 | `received/2026-09-21_access-handover/requirements-doc.md` |
| 2026-09-21 | **Access handover** (the reply to Request 2):<br>• Gmail credentials → Jainil<br>• OpenRouter created<br>• Railway/GitHub: already existed, password reset<br>• Zoom user + role<br>• voice and strategy docs; 6 workshops; 7 office hours<br>• Slack: all client channels<br>• ChatGPT access + 10 chats<br>• 5 source→output chains | `received/2026-09-21_access-handover/reply.md` |
| 2026-09-21–22 | GHL PIT created and used (126 campaigns). Slack bot token live (test channel) | `corpus/` |
| 2026-09-22 | Zoom role shown. **`hello@` password via LastPass + E2M +91 2FA phone added** | M05 |
| 2026-09-23 | E2M to test `hello@` access. *Result: TBD* | M05 |
| 2026-09-24 | Ledger created, then updated with Request 1 (Sep 3–8) and Request 2 (the Sep 21 handover). Repo ownership gap found | — |
| 2026-09-24 | Jainil confirms **GHL API access is in place**, and that the **Instagram and Canva access guides were shared with WIA** (Request 3; share date TBD) | Jainil |
