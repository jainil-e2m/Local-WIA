# WIA — Resource Mapping

What has actually been collected, what access exists behind it, and what is
still missing. Generated **25 September 2026** against the working tree.

This is a ledger, not a plan. Everything below was verified by reading the
files, not by trusting a filename — the Zoom set in particular arrived with
sixty files sharing one generic name, and the classification here comes from
the words inside them.

Two consumers share this corpus:

- **Content Atelier** — turns sessions WIA has already had into drafted
  marketing copy. Spec in [`Content_Atelier.md`](Content_Atelier.md).
- **Maintained Client Knowledge Base** — the running record of what has been
  discussed, decided and delivered per client.

They draw on overlapping sources, so the ledger is organised by source rather
than by consumer, with a column saying which one each serves.

---

## 1. The directory

```
corpus/                        94 MB total, git-ignored except tooling and notes
├── docs/                      6 files · 3.0 MB    voice + strategy documents
├── emails/                    127 files · 2.6 MB  GHL marketing sends
│   └── raw/                   126 files · 2.0 MB  original HTML bodies
├── instagram/                 1 file · 116 KB     carousel corpus
├── slack/                     8 files · 70 MB     6 channels + _INDEX.md
│   ├── files/                 210 files · 63 MB   attachments under 25 MB
│   └── raw/                   7 files · 5.9 MB    untouched API payloads
├── webhooks/                  3 files · 40 KB     captured test deliveries
├── zoom/                      2 files · 11 MB     parsed index + normalised JSON
└── zoom_transcripts/          150 files · 7.6 MB  raw WEBVTT, as downloaded
```

`.gitignore` inverts `corpus/` deliberately: the default is *ignore*, and the
exceptions are tooling (`*.mjs`, `*.js`), notes (`*.md`) and `*.tsv`. Any new
fetcher's output is ignored the moment it is created, without an edit.

Outside `corpus/`:

| Path | What it is |
|---|---|
| `Content_Atelier.md` | The component spec — operating rules, inputs, outputs, pipeline |
| `prompts/marketing-email.md` | Source layers, corpus-study checklist, voice card, generation prompt |
| `src/data/contentAtelier.ts` | The app's fixture data — corpus rows, moments, coverage |
| `.env` | Live credentials. Never committed |
| `.env.example` | The credential contract, with the caveats recorded inline |

---

## 2. Collected — what is on disk

| Source | Volume | Serves | State |
|---|---|---|---|
| **Zoom transcripts** | **150 files · 803,947 words** | Both | ✅ indexed |
| **GHL marketing emails** | **126 emails**, Apr 2024 → Sep 2026 | Atelier | ✅ complete |
| **Instagram carousels** | **18 carousels · 159 slides** | Atelier | ✅ 12 months |
| **Voice + strategy docs** | 3 documents, converted to markdown | Atelier | ✅ complete |
| **Slack** | **6 channels · 1,070 msgs · 1,594 replies** | Both | ✅ complete |
| **Fathom** | 3 test deliveries, own account | Both | ⚠️ proven, no WIA data |

### 2.1 Zoom transcripts — the moment corpus

150 WEBVTT files downloaded from Zoom's Transcript Management, parsed by
`corpus/index-zoom.mjs` into `corpus/zoom/transcripts.json`.

| Classification | Files | Notes |
|---|---|---|
| **Client calls** | **78** | 498,208 words — the material the qualifying signals live in |
| Workshops & Q&A | 4 | Drive lists 6; two are missing |
| Internal | 61 | Check-ins, LeadLock, planning — triaged out before extraction |
| Fragments | 7 | Under 50 words. Recording started, meeting did not |
| **Extractable** | **143** | |

Named chains present:

| Chain | Transcripts | Why it matters |
|---|---|---|
| **Funktastic** | 13 | The only chain where source transcript *and* published output both survive. The acceptance test for MC-02/03 |
| **Press Record** | 22 | Back-to-back record months — the strongest results material in the corpus |
| Dogwood Reserve | 14 | Also has a Slack client channel |
| Carroll Hall | 5 | |
| Miss Lyss (Alyssa) | 4 | Produced the only finished case study |

Verified unique by content, not filename: all pairs compared on exact hash,
timestamp-stripped hash, and Jaccard similarity over utterance sets. One
byte-identical duplicate was found and removed. No partial overlaps — nothing
is a truncated re-download of something else.

**Attribution caveat.** Every record carries `attribution: "name-only"`. A Zoom
VTT gives a display name and nothing more, so "this speaker is a client" is an
*inference* from who they appear alongside — not a fact. Anything quoting a
named client from this source needs its timecode checked before it ships.

Team roster is derived from speaker frequency (9+ meetings) and seeded with
known staff, because Danielle appears in only three calls while Accelerator
members Erin Smith and Shannon Lee appear in eight. Frequency alone gets one
of those wrong whichever threshold is chosen.

### 2.2 GHL marketing emails — the voice corpus

126 sends pulled via `corpus/fetch-emails.mjs`, one markdown file each plus the
original HTML in `raw/`.

- Date range **4 Apr 2024 → 16 Sep 2026**
- Subject line, preview text, body, CTA label and destination per email
- Delivery counts (`recipients`, `delivered`, `failed`) captured per campaign
- Offer map built from the **editor payload**, not the rendered HTML — both
  rendered variants route every link through `link.msgsndr.com/email-tracking`,
  so real destinations only exist upstream

Real CTA destinations recovered: `/accelerate`,
`/full-service-ads-management-waitlist`, `/google-search-accelerator`,
`/premiumleadgeneration-workshop`.

Not captured: open and click rates. `emails/stats.readonly` returns 401 despite
being selected on the token — see §3.

### 2.3 Instagram carousels

`corpus/instagram/wia_carousels.md` — every carousel published between
23 Sep 2025 and 23 Sep 2026, slide by slide, captions verbatim.

**18 carousels · 159 slides · 6,328 words of slide copy · 3,775 words of
caption**, with a ledger mapping each to its voice register, CTA and email
sibling where one exists.

### 2.4 Voice and strategy documents

| File | Source |
|---|---|
| `founder-voice-guide.md` | Whitney \| Founder Voice Guide |
| `founder-voice-knowledge-base.md` | Whitney Founder Voice \| Knowledge Base |
| `strategy-wlf-savannah.md` | Strategy from WLF Savannah |

Originals retained as `.docx` alongside. The overlap between the two voice
documents has not been reconciled — `Content_Atelier.md` §3.3 flags this.

### 2.5 Slack — collected 25 September 2026

**All six client and signal channels fetched.** 1,070 parent messages, 1,594
thread replies, 209 files, one markdown file per channel with permalinks on
every message.

| Channel | Messages | Replies | Files | Covers |
|---|---:|---:|---:|---|
| `#metaadsaccelerator` | 347 | 514 | 60 (+37 skipped) | 2024-11-22 → 2026-09-24 |
| `#c_funktasticproductions_djhybrid` | 248 | 371 | 43 | 2025-05-05 → 2026-09-24 |
| `#cfpfu_luxurytravelboutique` | 188 | 245 | 32 | 2025-05-14 → 2026-09-04 |
| `#googlesearchaccelerator` | 152 | 221 | 21 (+26 skipped) | 2025-10-24 → 2026-09-24 |
| `#c_dogwoodreserve` | 103 | 208 | 21 | 2026-05-07 → 2026-09-24 |
| `#social-proof-and-results` | 32 | 35 | 32 | 2025-06-11 → 2026-08-14 |

Attribution here is **resolved**, not inferred — Slack gives a real user id per
message, so unlike the Zoom VTTs (§2.1) a name is fact rather than a guess from
who else was present. Permalinks make each quote checkable.

**This was caught with one day to spare.** Free-plan retention truncates history
to 90 days; measured against a 2026-06-27 cutoff, **2,072 of the 2,664 messages
— 78% — sit outside that window** and would have been deleted by Slack, not
merely unfetched. `#metaadsaccelerator` alone reaches back twenty-two months.

Two exclusions, both deliberate and both recorded rather than dropped:

- **63 files over the 25 MB cap** (12.2 GB, almost all office-hours recordings).
  Name, size and authenticated URL are in each channel's markdown. The Atelier
  reads transcripts, and 150 of those already came from Zoom (§2.1).
- **2 Google Docs linked rather than uploaded** — *Dogwood Inquiry Sequences*
  and *Dogwood Reserve | Landing Page Copy*. The bytes live on
  `docs.google.com`, so no Slack scope reaches them. These need the Drive OAuth
  app, and they are named individually because landing-page copy is precisely
  what the Atelier exists to work from.

The scratch channel `#wia-ai-team-testing` is excluded from both the fetch and
the index. It holds messages we wrote to prove the pipeline, including an
invented client success story that is well-formed enough to extract cleanly as
a testimonial — see §6.

### 2.6 Fathom — proven, not populated

Three webhook deliveries captured from a personal test account, including one
duplicate pair that exposed two production traps (§6). No WIA meeting data yet.

---

## 3. Access ledger

### 3.1 Credentials held

| Credential | `.env` key | State | Reaches |
|---|---|---|---|
| GHL Private Integration Token | `GHL_PIT` | ✅ live | 126 emails, builder, schedule, contacts |
| GHL location id | `GHL_LOCATION_ID` | ✅ live | `Xi40zxmRvW8Pbyk5DYHp` |
| Slack bot token | `SLACK_BOT_TOKEN` | ✅ live | 7 channels, 7 read-only scopes proven |
| Fathom API key | `FATHOM_API_KEY` | ✅ live | Own account only — keys are per person |
| Fathom webhook secret | `FATHOM_WEBHOOK_SECRET` | ✅ live | Signature verification, confirmed against real signing |
| Instagram Graph token | `IG_TOKEN` / `IG_USER_ID` | ⬜ declared, empty | — |
| Canva Connect | `CANVA_*` | ⬜ declared, empty | — |
| Zoom S2S OAuth | — | ❌ not created | Blocked: `ai@` role lacks app-creation privilege |

### 3.2 Platform coverage

| Platform | State | Granted | Gap |
|---|---|---|---|
| **Gmail** `ai@` | ✅ Connected | Account + LastPass credentials | — |
| **OpenRouter** | ✅ Connected | Account on `ai@`, key shared | No spend cap recorded |
| **Google Drive** | ✅ Connected | Shared drive + Results Social Proof folders | Recordings are video; OAuth app not yet built |
| **GoHighLevel** | ✅ Connected | PIT with 6 working scopes | `emails/campaigns` + `emails/stats` return 401 |
| **Slack** | ✅ Connected | Bot in 7 channels, 6 fetched | 2 linked Google Docs |
| **Zoom** | ⚠️ Partial | `ai@` user with recordings + transcripts role | No API. 150 transcripts pulled by hand from the UI |
| **Fathom** | ⚠️ Partial | Own key proven end to end | WIA team keys in progress |
| **ChatGPT** | ⚠️ Partial | Account credentials + shared chat links | No data export |
| **Instagram** | ⚠️ Partial | Carousels scraped from the logged-in profile | No Business Suite / Graph token |
| **Canva** | ❌ Not granted | — | Carousel slide copy as text |
| **Descript** | ❌ Out of scope | — | Published reel scripts have no text precedent |
| **Speech-to-text** | ❌ Not needed *(revised)* | — | The Zoom transcript pull largely retired this |

### 3.3 Slack channel membership

Bot `content_atelier` (`U0C3KNA5SU9`), **7 channels, all private**:

| Channel | Role |
|---|---|
| `googlesearchaccelerator` | Signal — Carmen's Google Ads office hours |
| `metaadsaccelerator` | Signal — Jacqueline's Meta office hours |
| `social-proof-and-results` | Signal — client email screenshots, relayed praise |
| `c_funktasticproductions_djhybrid` | Client KB — **the benchmark chain** |
| `cfpfu_luxurytravelboutique` | Client KB |
| `c_dogwoodreserve` | Client KB — also 14 Zoom transcripts |
| `wia-ai-team-testing` | Scratch |

Scopes, all read-only and all proven live: `channels:history`, `channels:read`,
`groups:history`, `groups:read`, `files:read`, `reactions:read`,
`users:read`.

Not added, deliberately: `#social-media` (output destination — its role as an
input is undecided) and the remaining `c_*` client channels (pending Whitney's
approval).

---

## 4. Tooling

Every script is read-only against the source platform unless noted.

| File | Does |
|---|---|
| `corpus/probe-ghl.mjs` | Tests 9 GHL endpoints, reports status and shape |
| `corpus/probe-ghl-body.mjs` | Dumps one full schedule record, follows URL fields |
| `corpus/fetch-emails.mjs` | Pulls campaigns with bodies, builds the offer map |
| `corpus/capture-ghl-scopes.js` | Browser console script — captured all 162 scopes |
| `corpus/probe-slack.mjs` | Proves channel reach, files, reactions, threads |
| `corpus/fetch-slack.mjs` | Paginated history + thread walking + file download |
| `corpus/probe-fathom.mjs` | Key reach, speaker labels; `--register` creates one webhook |
| `corpus/webhook-receiver.mjs` | Local receiver for Fathom **and** Zoom, signature-verified |
| `corpus/index-zoom.mjs` | Parses VTT → common shape, classifies, builds the index |
| `corpus/probe-instagram.mjs` · `fetch-instagram.mjs` | Graph API, pending a token |

Reference notes: `slack-app-setup.md`, `ghl-scopes.md` + `.tsv` (160 scopes),
`instagram-app-setup.md`, `canva-descript-access.md`.

---

## 5. Outstanding

Ordered by whether anyone else is required.

### Unblocked — ours to do

| Item | Note |
|---|---|
| ~~Run the Slack fetch~~ | **Done 25 Sep**, one day before the retention cliff. 78% of what was captured sits outside the 90-day window and is now unrecoverable from Slack — see §2.5 |
| Google Drive OAuth app | Can be created without WIA. For a one-off backfill, Testing mode avoids `drive.readonly` verification entirely. Now also the only route to the two Dogwood copy docs linked in Slack (§2.5) |
| Two missing workshops | Drive lists 6, transcripts cover 4. Search `workshop` in the Zoom UI |

### Blocked on WIA

| Item | Who | Note |
|---|---|---|
| Zoom Server-to-Server OAuth app | Whitney / account owner | `ai@` role lacks Marketplace privilege. Now **backfill-only** — the 150 transcripts cover the immediate need |
| Fathom team API keys | Gisselle — in progress | Per person; one key per recorder |
| Client channel approval | Whitney | For the wider Client KB |
| ChatGPT data export | Whitney | Prefer export over share links — sharing publishes a public URL |
| `source_session` / `instagram_sibling` | Whitney / Giselle | Blank in all 126 emails; only they can supply |

### Known API gaps

- `emails/campaigns.readonly` and `emails/stats.readonly` return **401** despite
  appearing selected. Campaigns is redundant — `/emails/schedule` already gave
  everything. Stats costs open and click rates, recoverable by hand from the
  LeadLock Statistics tab.

---

## 6. Findings worth not rediscovering

Each of these cost time to find and fails silently if forgotten.

**Fathom `is_test_event` is absent on real deliveries, not `false`.** The
obvious filter `=== false` matches nothing and drops every genuine event. The
test event also arrives *first* after registration, so deduping on
`recording_id` keeping the earliest keeps the test and discards the real one.

**Fathom webhook payloads are byte-identical to the API.** Verified by pulling
the same meetings both ways. No reconciliation layer is needed — but the API
returns meetings that predate the webhook, so the poll is the backfill path.

**Fathom `matched_calendar_invitee_email` resolves only for calendar invitees.**
Across two real meetings, 1 of 3 speakers matched. Impromptu meetings match
nothing. Attribution must be treated as a bonus, per speaker, not a guarantee.

**Speaker diarisation is visibly wrong in sample data.** Both Fathom and Zoom
misattribute lines. A misattributed quote *is* in the transcript, so the "no
quote without a transcript" rule does not catch it. Every candidate quote needs
a deep link to its moment before a named client's words ship.

**GHL `nonTrackingDownloadUrl` does not preserve real destination URLs.** Both
rendered variants route through `link.msgsndr.com/email-tracking`. Real
destinations live only in `templateDataDownloadUrl`.

**`conversations.history` omits thread replies.** In 25 messages across two
Slack channels, 58 replies were invisible to it. The fetcher walks threads via
`conversations.replies` — same scopes, second endpoint.

**Slack file downloads return a login page with a 200** when the auth header is
missing. Content-type must be verified or HTML gets written into a `.webp`.

**An externally-linked file looks identical to that failure.** A Google Doc
shared into a channel is a file object with a `url_private` pointing at
`docs.google.com`, where the Slack token means nothing — so Google answers with
*its* login page at 200 and the content-type check reports "download failed".
It never was a download. `is_external` / `mode: "external"` must be tested
first, or a permanent gap gets logged as a transient error nobody chases.

**Slack bot authors do not resolve through `users.info`.** An app posts with a
`bot_id`, the lookup fails, and the raw `B09ANRU4AUW` lands in the corpus as the
author. The readable name is already on the message as `username` — no extra
call, no extra scope. It matters because the bot in these channels announces new
signups, which is a client-acquisition timeline that reads as machine noise when
it is attributed to an opaque id.

**The sandbox channel contains an invented client success story.** Written to
prove the pipeline, it is well-formed enough to extract cleanly as a testimonial
and would ship with a working permalink that appears to corroborate it.
`#wia-ai-team-testing` is excluded from both the fetch and the index for this
reason. Any future test channel needs the same treatment — synthetic content in
a corpus that generates marketing copy is not neutral filler.

**A per-channel re-run rebuilt the index from only that channel**, silently
dropping five others while reporting success. The index is now derived from
every `raw/*.json` on disk rather than from the current run's results, so
fixing one channel cannot delete the record of the rest.

---

## 7. Known staleness

`src/data/contentAtelier.ts` `COVERAGE` **predates most of this work** and still
reports HighLevel as "Not granted", Instagram as "Not granted", Slack as
"Membership, not an integration", and Fathom as having no API key. All four have
since changed — Slack most of all, which is now six fetched channels rather than
bare membership. The Operations Hub UI therefore shows an access picture that is
several days out of date.

`Content_Atelier.md` §11 still lists **"Fetch the three Slack channels"** as the
top item to make the Atelier real. It was six channels, not three, and it is
done. §8's coverage table records Slack as connected-but-unfetched.

`corpus/slack-app-setup.md` still names the app `Content Atelier` in five places,
including `/invite @Content Atelier`, which will be wrong once the rename to
**WIA AI BOT** completes.

`Content_Atelier.md` — **brought current 25 September.** §8 was rewritten (the
speech-to-text blocker is retired), §5 gained the ingest and triage stages, §5.1
gained the attribution rule, §10 closed the offer/CTA question and opened two
Slack ones, §11 marks Slack as the last uncollected source, and §12's transcript
question is answered.
