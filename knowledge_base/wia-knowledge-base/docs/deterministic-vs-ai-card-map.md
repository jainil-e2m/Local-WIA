# What the deployed MVP can show without AI

Written 4 Nov 2026. It covers every card and field of the deployed page (`mvp/real_index.html`) **except the Action Hub**, and sorts each one by what it needs:
- a fixed rule over stored records (deterministic);
- AI (an LLM call by the KB);
- a human decision.

It's checked against the backfilled data for the 4 pilot clients.

Companion to `docs/mvp-card-to-data-map.md`. That doc maps each element to a source and a stage; this one asks a narrower question: **can it be built without an LLM, and how?**

> Repo file: no client or staff names. The pilot clients are **A–D**. Real figures come from the local learning-run dump in `backend/.local/raw_pull/`. The Gmail backfill was paused at about 55% of hello@, newest first, so recent weeks are complete and older mail is not.

---

## 1. The categories

| Label | Meaning | Example |
|---|---|---|
| **DET** | Deterministic. A query, join, count or fixed rule over stored records. The same input always gives the same output. No LLM. | Open actions, next call, last email from the client |
| **PROV** | The provider made the text, including with its own AI. **The KB makes no LLM call** and just shows it, labelled with its source. | Fathom's own meeting summary and action items |
| **HUMAN** | A person sets or confirms the value once (WIA or an admin), then it's stored. | Account owner, service type mapping, contact roles |
| **AI** | Needs the KB's own LLM: reading free text and producing a fact, summary, classification or judgment. | Profile facts, decisions, curated history, sentiment |
| **BLOCKED** | No usable source today. | Lead outcomes (GHL 401), LeadLock support mail |

"DET with a human gate" means the rule is deterministic, but a value only shows as confirmed after a person approves it once. Example: account teams are suggested from ClickUp assignees, then WIA confirms them.

---

## 2. What the backfill actually holds (pilot clients)

| | A | B | C | D |
|---|---|---|---|---|
| Approved contacts (with a display name) | 13 (10) | 3 (3) | 7 (6) | 3 (2) |
| Past calendar events with a client attendee | 6 | 13 | 29 | 8 |
| …of which have a conference link | 4 | 5 | 7 | 5 |
| Upcoming calendar events | 0 | 8 | 8 | 0 |
| Fathom recordings (all have Fathom's summary) | 1 | 1 | 3 | 0 |
| Fathom action items | 6 | 6 | 4 | 0 |
| **Drive "Call Recordings" folder:** dated meeting videos | 7 | 9 | 11 | 8 |
| …transcript files (Zoom `.txt`, parsed) | 1 | 0 | 1 | 3 |
| …summary docs (Google Docs, parsed) | 2 | 1 | 6 + 2 notes | 2 |
| Meeting dates with a video that are also on the calendar | 4 of 7 | 7 of 9 | 9 of 11 | 5 of 8 |
| Last client meeting before 4 Nov | 2 Oct | 7 Oct | 28 Oct | 22 Sep |
| Gmail messages since that meeting (client / WIA) | 12 / 12 | 6 / 8 | 3 / 3 | 29 / 25 |
| Slack messages since that meeting | 55 | 56 | 15 | 121 |
| Gmail threads whose latest message is from the client (since 1 Oct) | 5 (2) | 14 (2) | 23 (4) | 18 (6) |
| ClickUp tasks / ClickUp `Role` field set | 211 / 197 | 141 / 91 | 127 / 23 | 199 / 191 |
| Account-team suggestions (none confirmed) | 5 | 2 | 2 | 0 |

**Five facts from this table shape everything below:**
1. **Meetings come from three places, and Fathom is only the newest.** WIA moved to the Fathom team plan only recently, so Fathom holds just 5 recordings. Older calls were recorded on **Zoom**:
   - The **videos** were saved to each client's Drive **"Call Recordings"** folder: 35 dated videos across the 4 clients, from Apr 2025 to Oct 2026. The backfill already holds them, as metadata only.
   - **Transcripts** stay in Zoom. Only 5 were exported to Drive as `.txt`, and those are parsed.
   - **11 summary docs** sit in the same folders, also parsed.
   - Calendar is the list of meetings that were *scheduled*. Drive videos, Zoom and Fathom are what was *recorded*.
   - Video file names start with the meeting date (`YYYY-MM-DD - <title> - Recording`). That date joins them to the calendar by rule; 25 of 35 match a calendar date exactly.
   - **The transcript gap is a connection gap, not missing data.** Connecting Zoom cloud recordings brings the transcripts in. The Drive videos could also be transcribed locally as a fallback (speech-to-text, not an LLM).
2. **Slack is internal-only.** Every Slack message is from WIA staff or a bot, none from the client. Slack counts as *the team talking about the client*, never as client contact.
3. **Gmail direction can be decided by rule.** The sender is either an approved client contact or client domain, or WIA (internal, or the shared mailbox).
4. **Provider-written summaries are already stored, in two fixed formats.** They can be shown with no KB AI:
   - Fathom's summary and action items, as `provider_summary` and `provider_action_item` units.
   - Summary docs saved next to the videos in Drive. **Zoom AI Companion** docs use the headings "Quick recap", "Next steps" (grouped per person) and "Summary". **Fathom exports** use "Meeting Purpose", "Key Takeaways", "Next Steps" and "Action Items".

   Because the headings are fixed, recap, next steps and action items can be **cut out by rule**. Zoom transcripts are speaker-labelled (`Name: text`), so speakers map to people by rule as well.
5. **The ClickUp `Role` and `Phase` custom fields are well filled** for 3 of 4 clients. They give the action side (we owe / client owes) and the onboarding phase without AI.

---

## 3. Summary: page by page

| Page / tab | DET + PROV | HUMAN | AI | BLOCKED / soon |
|---|---|---|---|---|
| Client Portfolio (cards, list) | almost all | owner, service type, lifecycle rule | — | health (soon) |
| Record header and strip | all | client since (WIA's definition) | — | — |
| **Now tab** | Next meeting (header), Last meeting (header + Fathom summary), Action items, **Communication since last call** | — | meeting decisions, call brief, sentiment | sentiment (soon) |
| **Profile tab** | **People card**, Engagements panel, LeadLock account link | contact roles, team confirmation | the 6 profile sections (marketing profile facts) | lead outcomes |
| Commitments tab | same as the Action Hub (out of scope) | — | commitments said in calls, Slack and email | — |
| **Meetings tab** | list (calendar + Fathom + Drive videos), schedule, attendees, recording/transcript state, provider summaries and next steps (Fathom, Zoom AI Companion), upcoming agenda | — | decisions, linking next steps to actions, call brief | Zoom transcripts (not connected yet) |
| History tab | lanes, timeline, counts, period filter, raw event list, Commercial lane | — | curated milestones, one-line titles, evidence tags | — |
| Handover brief | 4 of 7 sections | — | 3 of 7 sections | — |
| Support tab | — | — | issues read out of conversations | LeadLock mailbox |
| Accounts & sources | all | — | — | — |
| Health, Invoices & terms, Call prep | (invoices are DET, admin-only) | — | health, sentiment, call briefs, agreement terms | soon |

**Bottom line:** apart from the Action Hub, these can go live with no LLM:
- the Portfolio;
- the record header;
- most of the Now tab;
- the People and Engagements panels;
- the whole Meetings list;
- the History timeline;
- Accounts & sources;
- most of the Handover brief.

AI is needed for:
- the marketing profile;
- meeting decisions (summaries and next steps come from Fathom and Zoom where they exist; most older calls need Zoom connected first);
- commitments not in ClickUp;
- curated milestones;
- support issues;
- sentiment and health;
- call briefs.

---

## 4. Client Portfolio (provisional design)

| Element | Class | Rule / source | Caveat |
|---|---|---|---|
| Name, initials, aliases | DET | `businesses`, `business_aliases` | Former names should be added as aliases so old records match |
| Logo | HUMAN (once) | Drive logo file or upload, stored as a client asset | Pick once, never at runtime |
| Location | DET | GHL LeadLock sub-account profile (address) | Service area is wider than the address and needs AI |
| Category (venue, DJ…) | HUMAN | A registry field set when the client is added | Could be inferred, but a one-time admin field is cheaper and certain |
| Service chips / engagement count | DET with a human gate | Map raw labels (GHL invoice titles, Dubsado labels, ClickUp space, LeadLock active) through a **fixed lookup table** to Elevate / LeadLock / Google Search Accelerator / Meta Ads Accelerator | WIA confirms the table once |
| Lifecycle (Active, Onboarding…) | DET with a human gate | Which ClickUp space the client folder sits in, plus the `Phase` field | WIA's own lifecycle rule is still open (AR-22) |
| Owner | DET with a human gate | `account_team_members`, suggested from ClickUp assignee counts | **None are confirmed; D has no suggestion.** "My clients" stays empty until WIA confirms |
| Open / Overdue counts | DET | Actions read model | Exclude archived onboarding-template tasks (O-8). Most open tasks have no due date, so overdue is understated by design |
| Next call | DET | Earliest future calendar event with a client attendee | A and D have none booked; the card says so |
| Pin, archive | DET (UI state) | A per-user pin table, plus admin archive (see the archive mismatch in the map doc §6) | Not data, so no AI question |
| Health | Soon | — | AI or a WIA rule later |

---

## 5. Record header and strip

| Element | Class | Rule / source |
|---|---|---|
| Client since | DET with a human gate | Earliest commercial evidence: first Dubsado signing, first GHL invoice, or LeadLock sub-account creation. WIA may define it differently |
| Earliest evidence / Processed through | DET | Minimum `occurred_at` across the client's records / the last successful sync (`coverage_windows`, `sync_streams`) |
| Account owner | DET with a human gate | as above |
| Quick links (Slack, Drive, ClickUp, LeadLock) | DET | Approved scopes, plus the GHL location ID |
| Related business (partner) | HUMAN | Partner sender rules and the registry |
| Cover image | UI | — |
| "Prepare for the call" | AI | Opens the call brief (Call prep is a Soon page) |

---

## 6. Now tab

### 6.1 Next meeting: DET for the header, AI for the brief

- **DET:**
  - date, time (in the viewer's timezone), duration, title, host (organizer) and attendees, from the calendar event;
  - "In N days";
  - "No meeting booked" with the date of the last one.
- **DET objective:** the event description (`event_description` units), when the invite has one (14 of 37 events for C). Otherwise show the title.
- **AI:** "From the brief · to raise", the brief itself, and "Generate brief". In this version, hide the brief block or show it as Soon, instead of a fake generator.

### 6.2 Last meeting: DET plus Fathom summary (PROV), AI for decisions

- **DET:** the most recent past client meeting (calendar ∪ Fathom, joined by date and time). Title, type, attendees, "N days ago".
- **PROV:** show the provider's summary, labelled with its source. Check these in order:
  1. Fathom recording;
  2. a Drive summary doc dated that day (Zoom AI Companion "Quick recap", or a Fathom export's "Meeting Purpose" / "Key Takeaways");
  3. once Zoom is connected, Zoom's own meeting summary.

  Today that covers 5 Fathom recordings plus 11 Drive summaries. Otherwise show: "Recorded (video in Drive), no summary yet" when a video exists, or "No recording found" when it doesn't.
- **DET:** "Previous call with a summary": the latest earlier meeting that has any provider summary.
- **PROV (rule-cut) / AI:** "Decided / next steps":
  - Show the provider's **"Next steps" / "Action Items" / "Key Takeaways"** sections, cut out by heading.
  - Real *decisions* with evidence quotes need AI.
- **AI:** "N actions created · N done". Linking a meeting to the ClickUp tasks that came out of it is a fuzzy match. Fathom's own action items aren't ClickUp tasks.

### 6.3 Action items: DET

- Open actions for the client, sorted overdue first and then by due date; the first 3, plus "+N more".
- **Side (we owe / client owes):** the ClickUp `Role` custom field (Role = Client → client owes). It's set on 197 of 211 tasks for A, 91 of 141 for B and 191 of 199 for D, but only **23 of 127 for C**. Unset tasks default to "we owe", or show as unassigned side. Inferring the side from the task text would be AI.

### 6.4 Communication since the last call: DET (proposed rework of "Communication this week")

**Why the change works:** "this week" is an arbitrary window. "Since the last call" answers what an account manager actually asks before the next call. The data supports it: every pilot client has a last client meeting, between 22 Sep and 28 Oct.

**Window**
- **Start** = the most recent past client meeting from the same union the Meetings tab uses: calendar (client attendee, not cancelled), Fathom recording, or a dated Drive recording. **End** = the day of viewing.
- **No past meeting:** fall back to the last 30 days, labelled as such.
- **Long windows** (D: 6 weeks, 54 emails, 121 Slack messages): group by week and show the latest 10 items, with "Show all".
- **The eyebrow** reads "SINCE THE 22 SEP CALL · 43 DAYS". A meeting that happens today resets the window, so the card says "Last call was today".

**Counts and rows (all DET)**

| Element | Rule |
|---|---|
| From client | Gmail messages whose `from` is an approved client contact or client domain |
| From WIA | Gmail messages from an internal address or the shared mailbox (hello@) |
| Calls | Client meetings inside the window, from the calendar |
| Channel split | Gmail n · Calls n. **Slack is shown apart as "Team discussion n"**, because it's internal-only (§2) |
| Client last wrote / We last wrote | Latest message date per direction |
| Row text | Email **subject line**, sender display name and direction. For a call: the event title |
| Awaiting our reply | A thread whose **latest message is from the client** and has no later WIA message. Business days since that message |

**Known limits of the deterministic rules**
1. **"Awaiting our reply" over-flags.** "Thanks!" closers and FYI emails end threads too. C has 23 threads ending with the client, 4 of them since 1 Oct. Cheap rules that keep it deterministic:
   - only threads inside the window;
   - only messages with more than ~25 authored words or a `?`;
   - no reply-all from WIA within 1 business day.

   Deciding whether a message actually needs a reply is the AI version.
2. **Staff replies from personal mailboxes are invisible.** Only hello@ is connected. A reply a team member sent from their own mailbox looks like no reply. Show the badge as "No reply from hello@", not as a fact about the team.
3. **No one-line summary of each email.** That's AI. The subject line is the deterministic stand-in.
4. **Storage interplay with BF-2 (email as pointers):**
   - This card needs only subject, from, to, cc, date and thread ID, all of which pointer storage keeps.
   - The word-count and `?` rules need the body, or a stored Gmail snippet (Gmail's own ~200-character preview).
   - **Decide whether the snippet is part of the pointer.**
5. **The Gmail backfill is incomplete for older mail**, which this card doesn't need. Live sync (S6) is what keeps it current.

### 6.5 Client sentiment: AI (Soon)

---

## 7. Profile tab

### 7.1 Marketing profile sections (Who they are, Offer, Ideal client, Differentiators, Voice, Goals): AI

- All 12 narrative fields and about 6 standard facts per client were **hand-written** in the overlays. They come from questionnaires (Drive) and calls.
- **DET fallback, flagged "Unreviewed questionnaire answer":** show the questionnaire's question and answer pairs verbatim, from Drive sheet rows and doc tables. G-15 warns that PDF form exports run optional answers together, so this only works for Sheets/Docs questionnaires. Sensitive questions (tax, credentials, banking) must be dropped by a fixed exclusion list (G-14).
- **DET/HUMAN:** "How WIA will judge it". The benchmark thresholds are fixed numbers in WIA's playbooks, so they're a lookup by service. Only a per-client target needs AI or WIA.
- **HUMAN:** "Propose a correction" stays a person-to-resolver flow.

### 7.2 People card: DET, with roles from a human

**Client side (DET)**

| Field | Rule |
|---|---|
| Name and email | Approved `contacts`. The name comes from the Gmail `From` display name or the contact's `display_name` (A: 10 of 13 named) |
| Last contact / message count | Latest Gmail message from or to that address, and how many, within the record |
| On calls | Calendar attendee matches; Fathom speaker matches where recorded |
| Exclusions | Hide domain-only contacts and automated or `reply.` addresses (C has `reply.` domains among its contacts). They're qualification rules, not people |
| Role (owner, planner, coordinator) | **HUMAN** (admin sets it once) or **AI** (from email signatures and call introductions). Until then: "Role not recorded" |

**WIA team (DET with a human gate)**

| Field | Rule |
|---|---|
| Members and roles | `account_team_members`. Suggested by S3 from ClickUp assignee counts (for example "ads_meta"); **confirmed by WIA** |
| Activity | ClickUp tasks assigned, plus Gmail messages sent to the client, per person |
| State today | Suggestions only. D has none, so the card shows "Not confirmed" rather than guessing |

### 7.3 Engagements panel: DET

- Engagement type: from the service lookup (§4).
- Since: the earliest commercial evidence.
- **Phase:** the ClickUp `Phase (LeadLock)`, `Phase (Full Service)` and `Phase (Ads Traffic)` fields on the onboarding lists. The latest phase with incomplete tasks is the current phase.
- Signed date: Dubsado or a Drive contract (admins only).
- The onboarding checklist progress ("2/48 tasks done") is also DET from the same lists. Client-side steps use `Role` = Client.

### 7.4 LeadLock account: DET for the link, BLOCKED for lead outcomes (GHL 401)

---

## 8. Meetings tab: DET for the list, PROV/AI for content

| Element | Class | Rule |
|---|---|---|
| Meeting list (past + scheduled) | DET | Union of: calendar events with a client attendee (not cancelled), Fathom recordings, and Drive "Call Recordings" videos. Joined on date: the Fathom recording time, or the `YYYY-MM-DD` prefix of the video file name; 25 of 35 videos match a calendar date. Recordings with no calendar match still count as meetings (some are older than the calendar history or were booked on another calendar). Scheduled first, then past, newest first |
| Title, date, time, duration | DET | Calendar `summary`, `start`/`end` with the event's timezone |
| Type filter (Monthly, Onboarding, Demo…) | DET | Recurring series (`recurring_event_id`) gives "recurring", plus keyword rules on the title. Unmatched titles go under "Other" |
| Attendees | DET | Attendee emails resolved to people (S3): client contacts and WIA staff by name, the rest as email |
| Host | DET | Organizer |
| Recording / transcript state | DET | Fathom or a Zoom/Drive transcript → "Transcript available"; Drive video only → "Video in Drive · transcript in Zoom (not connected)"; neither → "No recording found" |
| Watch recording | DET | Link to the Drive video or the Fathom share URL |
| "What the meeting was about" | PROV | Fathom summary; Drive summary doc (Zoom AI Companion "Quick recap" / Fathom "Meeting Purpose"); later Zoom's own summary. Today 16 of 35+ recorded meetings have one |
| Next steps / action items | PROV (rule-cut) | "Next steps" (Zoom, per person) or "Action Items" (Fathom), cut out by heading. **Linking them to Action Hub items is AI** (or a manual "link to action") |
| Decisions | AI | See §6.2 |
| Transcript & source link | DET | Fathom `transcript_segment` units, or Zoom transcript lines (`Name: text`, speakers resolved to people) |
| Upcoming: "What this meeting is for" | DET | Event description, if any |
| Upcoming: Agenda | DET | Description lines, or the open items with a due date before the meeting |
| Upcoming: What to settle, Opportunity | AI | That's the call brief |

**How to close the transcript gap.** Most meetings *were* recorded; the transcripts just aren't connected. In order of preference:
1. **Connect Zoom cloud recordings** (read-only) as a new source. It brings transcripts and Zoom AI summaries, matched to meetings by start time. `zoom` is already in the backend's provider list, but there's no adapter yet.
   - WIA's process: after each client call, the ops lead files the video and transcript to Drive and deletes the *recording* from Zoom. **Transcripts and summaries stay in Zoom** (Sep 22 call). About 508 sat in Transcript Management in September, with no auto-delete.
   - **Blocker:** the AI account's Zoom role can't create an API app. A Zoom admin must create a read-only Server-to-Server OAuth app. Until then, transcripts can only be exported by hand, as Content Atelier did for 150.
2. **Ingest the transcript and summary files** WIA already saves next to the videos in Drive. This is already working: 5 transcripts and 11 summaries are parsed today.
3. **Transcribe the Drive videos** with local speech-to-text, for meetings whose Zoom transcript has expired or was never made. That's a speech model, not an LLM, so the transcript stays reproducible; summarising it is still AI. **Not approved today:** the KB decision log rules out new transcription and OCR (KB-CH-26/32), so this needs WIA's go-ahead.

"Historical Zoom" is already one of the 8 approved KB intake sources (`knowledgebase_changes.md`).

**What already exists outside the KB** (from Content Atelier):
- **164 Zoom transcripts, 1 Jun – 18 Oct 2026, hand-exported from Zoom's Transcript Management.** They're in `content_atelier/backend/zoom_backfill_meetings/week1–20/` and in the Atelier database. About 78 of the first 150 are client calls; the Atelier has tied 75 calls to client accounts.
  - **Dates are weak.** Zoom transcript files carry no date, meeting ID or emails. 63 are dated to the day and 101 only to the week. Matching them to calendar events or Drive videos by rule is reliable only for the day-dated ones.
  - The rest need a Zoom recording-list export (Atelier's `documents dates --zoom-listing`), or the API.
- **393 older Fathom recordings (Sep 2021 – Mar 2026)** are visible to the `hello@` key, private to that recorder. They include named client onboarding, kickoff and strategy calls. Most show `transcript_language: unknown`, so whether they have transcripts is **unverified**.
  - The KB's Fathom adapter admits a recording only when an invitee is an approved contact. That likely explains why the KB backfill kept just 5.
  - Re-check them with a transcript fetch before counting them as coverage.

**Coverage message:** show "N client meetings · N recorded · N with transcript". Hosts should know an empty summary means "transcript not connected", not "no meeting".

---

## 9. History tab: DET skeleton, AI curation

| Element | Class | Rule |
|---|---|---|
| Lanes and the spine timeline | DET | Each record mapped to a lane by source and kind: Gmail → Communication; calendar and Fathom → Meetings; ClickUp tasks → Commitments; onboarding lists → Onboarding; Drive files → Work delivered; Dubsado and GHL → Commercial (admins only) |
| Period filter, "Since last call" | DET | Date filters |
| Event list with titles | DET (raw) | Email subject, task name, file name, meeting title. Correct, but noisy: C has 911 communication events |
| Bursts ("12 messages in 3 days about …") | DET for the count, AI for the "about" | Group by thread or task and day; the topic line needs AI |
| **"Moments that shaped the account"** (14–18 curated per client) | AI | Hand-written in the overlays today. Choosing what mattered is judgment |
| Evidence tags (Decision, Client signal, Commitment, Delivery) | AI | Classification of a quote |

**Deterministic option for this version:** show the lane timeline plus a **deduplicated** event list (one row per thread, task or file per day). Label it "All activity", and keep "Moments" as the AI layer later.

---

## 10. Handover brief: 4 of 7 sections DET

| Section | Class | Source |
|---|---|---|
| Who they are | AI | Profile facts |
| Where things stand | AI | Narrative (picture, focus, trigger) |
| What's owed | DET | Open actions with side, owner and due |
| Key decisions | AI (PROV fallback) | Meeting decisions; until then, Fathom summaries with dates |
| People & how to work with them | DET (+ HUMAN roles) | People card (§7.2). "How to work with them" is AI |
| Watch-outs | DET (partly) | Overdue actions, deadline conflicts, and unanswered client threads (§6.4). Support issues are AI |
| What this record can't tell you | DET | Source states and coverage dates |

"Regenerate" for the DET sections is just a re-query, with no LLM. The stamp means "assembled from the record at …".

---

## 11. Other tabs

- **Support:** AI. Issues are read out of conversations. Partly BLOCKED: LeadLock support goes to a mailbox that isn't connected (O-11). Show the coverage banner and an empty state; don't list guesses.
- **Accounts & sources:** DET. Approved scopes, state, last sync, history-from date, item counts; plus mapping suggestions from discovery, which are rule-based.
- **Commitments:** shares the Action Hub's records (out of scope here). Commitments that exist only in calls, Slack or email are AI (S7 `action_candidate`).
- **Invoices & terms (Soon):** invoices, payments, plans and signed agreements are DET (GHL, Dubsado, Drive contract files), admins only. Agreement terms (fee, term, notice) need AI.
- **Health & sentiment, Call prep, Client 360, Overview (Soon):** AI or WIA-defined rules. Out of this version.

---

## 12. What this means for the build

1. **A deterministic phase is possible before any S7 work.** The read models (S9) and API (S11) for these cards need no extraction contracts:
   - Portfolio
   - header
   - Next and Last meeting headers
   - Action items
   - Communication since last call
   - People
   - Engagements and phase
   - Meetings list
   - History timeline
   - Accounts & sources
   - the DET brief sections

   That replaces the snapshot plus overlays for everything except the AI fields.
2. **The cards above need these stored fields:**
   - Gmail: subject, from, to, cc, date, thread, labels, plus possibly the snippet;
   - Calendar: everything already stored;
   - Fathom: summary, action items and transcript units (PROV);
   - ClickUp: status, due, assignees, `Role` and `Phase` fields;
   - Drive: file metadata;
   - registry, contacts and account teams.

   Only §6.4's reply heuristic and §7.1's questionnaire fallback read body text.
3. **Human gates come before AI.** Most "unknowns" in the deterministic cards are WIA decisions, not AI work:
   - account owners and teams;
   - the service lookup table;
   - the lifecycle rule;
   - contact roles;
   - "client since".
4. **AI work concentrates in a few contracts:**
   - `profile_fact`;
   - `meeting_summary` / decisions (only where there's a transcript);
   - `action_candidate`;
   - `milestone`;
   - `evidence_classification`;
   - support issues;
   - call briefs.
5. **Label provider-made text.** Fathom and Zoom AI Companion summaries are AI output, but not the KB's. Show them as "Summary by Fathom" or "Summary by Zoom" so nobody mistakes them for reviewed KB facts.
6. **Connecting Zoom is the biggest gain in meeting coverage.** Most past client calls were Zoom calls whose videos are in Drive and whose transcripts are in Zoom (§8).

## 13. Decisions needed

- ~~**Rename the card** to "Communication since the last call", with the 30-day fallback~~ **Done 13 Nov.** The window starts on the day of the last client call (calendar or Fathom, not cancelled), or covers the last 30 days with no call. It shows the latest 10 rows with "Show all", and the counts cover the whole window. Slack stays as "team threads" (§6.4).
- **Choose the "awaiting our reply" rule:** plain (latest message is from the client) or filtered (words or `?`). Decide the badge wording given that staff mailboxes aren't connected.
- **Gmail snippet in the pointer** (BF-2): yes or no.
- **Show Fathom summaries as-is** (labelled) in the Last meeting card and the Meetings tab.
- **Contact roles:** admin-entered, or wait for AI.
- **History:** ship "All activity" (DET) now, with "Moments" later.
