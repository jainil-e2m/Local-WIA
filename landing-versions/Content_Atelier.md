# Content Atelier

The Content Atelier is the Operations Hub component that turns sessions WIA has
already had — client calls, Vault workshops, office hours, Slack chatter — into
drafted marketing copy for WIA's own channels.

It maps to **MC-01 → MC-04** on the Blueprint timeline (Phase 2, Jan–Apr 2027)
and lives under SECONDARY in the hub nav, because client fulfilment outranks
WIA's own marketing every time. It is there because it is the one item tied
directly to revenue — "we need more leads, we need more sales" — not because it
is urgent.

*An atelier is a workshop where a small number of pieces are made properly, by
hand, from good material. That is the argument this component makes against
pushing three scripts at an already-inundated founder, and it is the word the
wedding industry already uses for exactly that kind of workshop.*

Source of record for everything below: the **16 September 2026 working session**
with Whitney Hodges, plus the **21 September access handover**.

---

## 1. The three operating rules

Everything in this document follows from these. If a future change breaks one of
them, the change is wrong.

**1 · Whitney is the selector.** The Atelier surfaces moments; it does not push
content. Her words: *"That's what I'm really flagging for Giselle saying, this
is worthy of turning into content. It's not necessarily going to happen from
every conversation I have."* An engine that drafts a pack from every call has
misunderstood the job.

**2 · Nothing is drafted from a source we cannot read.** A `.mp4` in Drive is a
recording, not a transcript. The LLM does not get to infer what was probably
said. A moment whose source is unreadable stays blocked and says why.

**3 · Every claim traces to a timestamp.** Results, percentages and client
quotes carry the source and the timecode they came from, so a case study or a
carousel can be checked against what was actually said.

---

## 2. Scope boundary — what the LLM does, and does not, produce

**The LLM produces text. Only text.**

This is the single most important boundary in the component, and it is Whitney's
own call, not a technical limitation:

> "I don't know at this point that I'm necessarily looking for the marketing and
> content engine to actually design any of the actual content, like in Canva or
> anything like that. But just having the framework, having the captions, having
> the scripts is already going to be such a huge lift."

And on why:

> "I can kind of tell when stuff like that has been AI generated. And I know that
> I think our clients can too. So taking a couple extra minutes to just copy and
> paste in Canva is okay at this point."

### The LLM DOES produce

| | |
|---|---|
| Reel scripts | Timecoded, with hooks, alternate hooks, b-roll notes, on-screen text callouts and production notes |
| Carousel copy | Per-slide text plus design notes for whoever builds it |
| Email copy | Subject line plus alternates, preview text, body, CTA button label, P.S. |
| Captions | Long form, plus a short variant, hashtags and alt text |
| Handling notes | What must be blurred, anonymised or withheld before anything leaves |

### The LLM does NOT produce

- **No rendered graphics.** No Canva slides, no generated images. Copy goes to
  Giselle, who places it into the existing brand templates.
- **No video.** Reels are filmed by Whitney on her phone and cut in Descript.
- **No voice.** An AI voice clone reading her scripts was discussed internally
  and explicitly deferred — *"you're such a face for your company that we
  wouldn't want to go down that phase two until we are very confident."*
- **No publishing.** Nothing auto-sends and nothing auto-posts. There is no
  publish path in this component at all.
- **No CTA invention.** See §6.
- **No workshop topic suggestions.** Asked directly, Whitney declined: *"I think
  I have kind of just a bank in my mind right now of stuff I want to be doing."*

Design stays with Giselle. On-camera stays with Whitney.

---

## 3. Input sources

### 3.1 Primary — session transcripts

| Source | System | What is extracted | Qualifying rule |
|---|---|---|---|
| Client calls | Zoom | Soundbites, results claims, praise | **Not every call.** See the signal list below |
| Monthly Vault workshop | Zoom | The session topic and its teaching content | Every session qualifies |
| Google Ads office hours | Zoom → Drive | Member questions, results shared on the call | Carmen hosts |
| Meta Ads office hours | Fathom | Same | Jacqueline hosts |
| Historic calls | Zoom / Drive | Context only — see below | Trailing **3 months**, capped deliberately |

**The qualifying signals for a client call**, in her words:

- The client is praising the work — *"praising us up and down, thanking us so
  much for our work"*
- Results talk, from the work or from the ad spend specifically
- A soundbite she can *"grab onto and take it and run with it"* — her worked
  example being the planner who had not posted organically in ten weeks all
  summer because the ads were running and the leads did not stop
- Milestone claims — business doubled, best month ever, too busy from sales

**On the three-month window.** The cap is not a storage decision. The historic
calls are there so the engine can see *the source call and what was made from
it* — a paired training set, not a corpus dump. *"Probably no longer than three
months. That's going to give it a really good example of what the source call
was and how you took that and transformed it into content."*

**Critical caveat.** The transcript, in her words, *"sparks the idea but then
we're taking that and running with it. It's not like the context of the call is
what gets turned into the content — it's an idea that then gets built upon."*
The Atelier is not a summarisation tool. The transcript is the seed, and the
steer (§5.3) is where the actual angle comes from.

### 3.2 Slack — three channels

`Google Search Accelerator` · `Meta Ads Accelerator` · `Social Proof and Results`

Two distinct things arrive here:

- **Screenshots of good client emails** that Whitney drops in herself. These are
  dual-purpose — an idea trigger *and* an asset that gets embedded in the
  finished reel or Instagram story.
- **Relayed feedback** from Jacqueline and Carmen after their office hours.

### 3.3 Knowledge base — voice and strategy

Read 23 September; originals and markdown copies in `corpus/docs/`.

| Document | Role |
|---|---|
| Founder voice guide (v2.0) | **How she thinks and writes — the rules.** Positioning, core beliefs, thinking style, hook types, vocabulary to use and avoid, sentence rhythm, an AI style guide |
| Whitney Founder Voice Knowledge Base | **What she has written — the examples.** Her own curation: 4 reels (two timestamped spoken transcripts, one full script, one summary, with captions) and 17 emails, Jul 2025 → Jul 2026, all of them in `corpus/emails/`. Not a second rulebook, so no overlap to reconcile — where an example breaks a v2.0 rule (the Q4 2025 emails use “skyrocket” and “magic”), the guide wins |
| Strategy from WLF (Savannah) | **What to make — the strategy.** A funnel of Attract → Warm → Convert with 12 content pillars, a CTA type per stage, a social-proof structure, a verbatim idea bank and six priority series. The guide itself says Savannah sets the framework and Whitney's voice sets the execution |
| Content framework | Savannah's: **Hook → Problems / Desires / Symptoms → Main Point → Transformation → CTA** — follow/comment/engage at Attract and Warm, DM/inquire/book at Convert. The version heard on the 16 September call is a paraphrase of this |

Whitney flagged there may be more: *"resources from different marketing programs
we've been in, in terms of what makes really great, strong content."* Not yet
supplied.

### 3.4 Approved existing marketing — the voice corpus

This is how the LLM learns the voice, and it matters more than any style
description of it.

- **GHL marketing emails** — the weekly sends, plus the log of subject line,
  date sent and CTA used. That log is a ready-made training set for how she
  chooses a call to action.
- **Instagram** — carousels, reels and their captions.

### 3.5 ChatGPT history

The accumulated working knowledge on the existing account. Two things to carry
forward into the build:

- She gets **better output from a brand-new chat than from a Project or Custom
  GPT**. *"If I start a new chat versus going into a project or a custom GPT,
  the output is better."* The Atelier should not replicate a siloed-memory
  pattern that narrows the search space.
- Giselle's ChatGPT work is **client fulfilment, not marketing** — out of scope.

### 3.6 Google Drive

Both voice documents, the WLF strategy, the Miss Lyss case study, and the
archive of session recordings. *"Any documents living there which could be
relevant."*

### 3.7 Human inputs

Easy to miss as "sources," and load-bearing:

- **The flag** — Whitney marking a moment as worth working.
- **The steer** — the angle. *"Hey, this came up on a call, what do you think
  about turning this into content, what angles, how would you spin it?"*
- **The CTA** — see §6.

### 3.8 Not input sources

- **ClickUp** — *"I don't think it would be ClickUp."*
- **OpenRouter / Railway / `ai@weddingindustryads.com`** — infrastructure, not
  content. OpenRouter is the model-selection layer; Railway hosts the solution.

---

## 4. Output — the pack

One pack per accepted moment. The spec is Whitney's, stated directly:

> "It would be ideal if the sourced content that we're using could be turned into
> **one marketing email, three reel scripts, and one carousel**. That would be my
> ideal. And then of course **captions to go along with all of that**."

| Asset | Count | Specification |
|---|---|---|
| **Marketing email** | 1 | Subject + alternates, preview text, body, CTA button, P.S. Destination is GHL. ~weekly cadence |
| **Reel scripts** | Up to 3 | Timecoded, each on a **different claim** from the same session — three angles, not three rewrites of one script. When a call supports fewer, write fewer: one complete, valuable reel beats three thin ones (§12) |
| **Carousel** | 1 | **7–10 slides.** Per-slide copy plus design notes. High-value and text-heavy — *"not surface level"* |
| **Captions** | for all | Long form, plus short variant, hashtags, alt text |

### Per-asset rules

**Reel scripts.** Whitney starts from *either* a reel script or the email —
*"either have it give me a script for reels first, or we work on a marketing
email first"* — then shifts to the other, then the carousel. The lead asset is
therefore a **choice**, not a fixed order, and everything else derives from
whichever she approved. *Superseded 23 September (§12): every piece is now
written independently from the approved gist.*

**Carousel.** Runs the framework, always ties back to how WIA can help, and
closes on a CTA. Giselle copy-pastes the finished copy into the existing Canva
templates, which is why slide count and copy length have to fit those templates.

**Captions.** Voice switches by source type:
- **First person** when it is Whitney's own experience or a 1:1 client conversation
- **"We" / the team** when the piece is general

Imagery varies too — sometimes Whitney, sometimes Danielle, sometimes both.

**Email.** Purpose is explicitly **repurposing, not a sales channel**. Settled on
the call with Asha: *"We're not making sales directly from emails at this point…
but if we're already spending the time generating the content for Instagram,
it's fairly low-lift to repurpose that into an email and send it out."* Do not
build an email-first strategy on top of this.

**Instagram Stories.** Named twice as an output surface — caption scripts for
stories, and the destination for the Slack screenshots. Less formalised than the
other four; see Open Decisions.

### 4.1 The coherence rule

A constraint on the **set**, not on any one asset, and the hardest thing here to
get right:

> "It should maintain your brand, your voice, how you usually do things, but it
> shouldn't look like a fixed template which is just copy-pasting or replacing
> elements within it."

> "Somewhat saying the same things, using the same language in the same places,
> but it wouldn't be like somebody consuming all three of those things feels like
> it's super redundant either."

Mechanically: **whatever is approved first becomes context for everything drafted
after it.** *"What's one thing is approved, that should be being used as part of
the knowledge of what else is created."* That is why the pipeline has a lead
asset and a derivation step rather than generating seven things in parallel.

> **Mechanism superseded 23 September (§12).** The goal above still stands, but
> every piece is now written independently from the approved gist — none is
> derived from another. The gist is the only thing the pieces share, so it
> carries the pack's consistency.

---

## 5. The pipeline

> **Revised 23 September — see §12.** The engine now runs as a nightly batch
> over the day's calls, and steps 4–6 (flag, steer, set CTA) become one step:
> Whitney approves or edits a gist the engine writes, on the Content Atelier
> screen. Steps 7–9 (draft lead, approve lead, derive) become one too: the
> engine writes every piece of the pack independently from the approved gist.

Twelve steps. Note which are LLM, which are human, and which are neither.

| # | Step | Who | Notes |
|---|---|---|---|
| 1 | **Ingest** | Deterministic | Webhook on session-end, plus a reconciliation poll. See §5.3 |
| 2 | **Normalise** | Deterministic | Two sources, one transcript shape: speaker, timecode, text |
| 2b | **Pre-filter** | Deterministic | Internal vs external, from calendar invitees or the speaker roster. Costs no tokens and is more reliable than asking a model |
| 3 | **Extract candidates** | LLM | Sentiment and soundbite detection across the transcript; ranked, with a one-line reason each |
| 3b | **Triage** | LLM | §12's worthiness judgment. *Not worth it* is returned with a reason and the call is **set aside**, never binned. See §5.4 |
| 4 | **Flag** | Whitney | Accept or reject each candidate. Nothing proceeds without this |
| 5 | **Steer** | Whitney | The angle, supplied as text or a transcribed voice note |
| 6 | **Set CTA** | Whitney | See §6. Blocks staging while empty |
| 7 | **Draft lead asset** | LLM | Reel script or email, her choice |
| 8 | **Approve lead** | Whitney | Unlocks derivation |
| 9 | **Derive the pack** | LLM | Conditioned on the approved lead, the steer, the CTA and the voice corpus |
| 10 | **Clear** | Whitney | Named-client / legible-analytics / claim-traceability check per asset |
| 11 | **Stage** | Deterministic | Hand off. Nothing publishes |

Step 3 is the automation that starts the whole thing, and it is what replaces the
current manual step — *"as soon as you finish a call, they paste the transcript
into ChatGPT."* The point, in Minu's words, is that Whitney is *"brought in only
when a human in the loop is required."*

### 5.1 LLM grounding rules

Applied at every generation step:

1. **No quote without a transcript.** Paraphrase in a handover note is not a
   quotable source. Drafting a result post from a paraphrase puts words in a
   named client's mouth.
2. **No figure without a timecode.** Every number carries where it came from.
3. **Voice conditioning is corpus-first.** Published emails and captions outrank
   any prose description of the voice.
4. **The three reel angles must be genuinely distinct** — three different claims
   from the session, not one claim rewritten three ways.
5. **Handling notes are part of the output**, not an afterthought. If the source
   is a paid members' session walking client analytics on screen, the script says
   what to blur.
6. **Speaker attribution is a claim, not a fact, until the timecode is checked.**
   Added 25 September, after observing both sources misattribute lines in sample
   data — Fathom assigned an answer to the person who asked the question, and a
   Zoom VTT carries a display name with nothing behind it. A misattributed quote
   *is* in the transcript, so rule 1 does not catch it. Every candidate quote
   therefore carries a deep link to its moment, and clearing a named-client quote
   means watching those seconds. See §8.2.

### 5.2 Model selection

All model calls route through **OpenRouter** on the `ai@weddingindustryads.com`
account, so different models can be tested per step without switching providers.
Extraction (step 3) and drafting (steps 7, 9) have different cost and quality
profiles and should not be assumed to want the same model.

### 5.3 Ingest — webhook and poll

Added 25 September, once both sources were proven end to end.

**Webhook first.** Fathom fires `new-meeting-content-ready` with the transcript
**inside the payload** — no second fetch, no expiring token. Zoom fires
`recording.transcript_completed` with a `download_token` valid 24 hours. Both
require a public HTTPS endpoint; `corpus/webhook-receiver.mjs` answers both,
including Zoom's `endpoint.url_validation` challenge.

**Poll second, and it is not optional.** Zoom stops delivering permanently after
three failed retries (5 min, 20, 60) and revalidates the URL every 72 hours. A
deploy during a delivery window silently costs a session. A daily reconciliation
pass over each API catches what the webhook dropped, and is also the only route
to anything recorded *before* the webhook existed.

Four rules the implementation must not lose, each learned from a real payload:

1. **Answer before you work.** Return 200, then process. An inline model call
   blows the timeout and costs the meeting.
2. **Store the raw body before parsing it.** If the parse throws or the prompt
   changes, the original is still on disk.
3. **Dedupe on the recording id, not the delivery id.** Fathom's `webhook-id` is
   unique per send; the same meeting arrives more than once.
4. **Drop test events first.** Fathom marks them `is_test_event: true` and
   **omits the field entirely on real deliveries** — it is never `false`. The
   test event also arrives *first* after registration, so first-wins deduping
   keeps the test and discards the real one. Both failures are silent.

### 5.4 Triage and the set-aside

Added 25 September. This extends §12's worthiness judgment; it does not replace
it. The bar stays strict and *not worth it* stays a frequent answer.

**A rejected call is set aside, never binned.** It appears in its own section of
the Content Atelier screen with the one-line reason attached, and Whitney can
open it.

**The reason has to be arguable.** "Not relevant" tells her nothing and she will
stop opening the section within a fortnight. The rejection states what was
looked for and what was found instead, with timecodes — *"no results or ad-spend
discussion; closest was a scheduling change at 12:04; the client spoke positively
about response times at 31:47 but named no outcome."* Negative evidence cited the
way positive evidence is.

**She can push back, and the engine must be able to hold its ground.** If she
writes *"there is something here about retention,"* that is a **search
instruction, not a conclusion**. A model asked to find retention will find it
whether or not it is there, and a fabricated candidate carrying a named client's
words is the worst output this system can produce. The re-run must be able to
return *"searched for retention; the call mentions renewal once at 08:12 with no
detail, and nothing else."*

**Her overrides do not change the engine.** §12 is explicit that there is no
learning loop after launch: her steer shapes that pack and nothing else. An
override that reveals a *missing qualifying signal* is a reason to edit the
prompt file deliberately, which is a decision, not an automatic update.

**One consequence to accept.** If triage is badly calibrated early, the set-aside
section fills and she stops reading it — the noisy-alert-channel failure. Bias
the first month toward surfacing rather than hiding, and tighten by editing the
prompt once there is evidence of what she actually rejects.

---

## 6. The CTA

Its own section because it is Whitney's single most specific instruction, and
because the LLM is explicitly **not** allowed to decide it:

> "I don't know if we even want there to be a way where, based on the source
> material — at least in the beginning, it doesn't have to come up with what the
> CTA is going to be. It can ask me, if it needs questions or clarifications."

**The engine asks. It never guesses. Staging is blocked while the CTA is unset.**

Two tracks, and the source type suggests which:

| Source type | Track |
|---|---|
| Workshop / teaching content | **Ads Accelerators** — learn more, apply |
| 1:1 client results | **Elevate** (full-service done-for-you) — waitlist signup |

Within email she tests variants: point to a sales page, or ask for a reply
(*"does this resonate with you?"*, *"what's your biggest challenge right now?"*).

**Outstanding:** the offer/CTA map with live destination URLs has not been
supplied. Without it the engine can name a CTA but cannot link it.

---

## 7. Where output goes

**Today:** Whitney → Slack → Giselle → Canva → Slack back to Whitney. Reels are
filmed on her phone, uploaded to Descript by either of them, trimmed there.
Whitney's own assessment: *"It's not very organised."*

**Asked for:** a **calendar view** so it is mapped out, and **links to the
content living in Google Drive**.

**`#social-media`** — noted 22 September, and not mentioned on the 16 September
call. Generated content accumulates in this Slack channel *alongside* the
Atelier view in the Command Center. So the team already has a habit and a place
for finished content, and the Atelier is a second surface onto the same thing
rather than a replacement for it.

Three consequences worth holding on to:

- It is a strong candidate answer to **open question #3** — where finished
  drafts live — because it is where they already live.
- It is where `chat:write` would eventually post, which makes **open question
  #4** concrete: auto-handoff means posting a finished pack here.
- It is also an **input**. A channel of content that actually went out is a
  record of what survived review, which is exactly the published-precedent
  signal the Atelier values — and unlike Instagram, it is reachable on scopes
  we already hold.

Not yet connected. The bot is not in it and it is not in the fetcher's default
channel list, both deliberate until its role is decided.

**Final destinations:** Instagram (feed, reels, stories), GHL (email).

---

## 8. Source coverage

> **Rewritten 25 September.** The section this replaces called speech-to-text
> the blocking dependency and the 17 Drive recordings unreadable. Both were
> overtaken by events: Zoom's Transcript Management holds transcripts that
> survived the recordings being deleted, and 150 of them have been pulled.

Full ledger, including what is on disk rather than only what is granted, is in
[`wia_resource_mapping.md`](wia_resource_mapping.md). Summary:

| System | State | Reaches | Gap |
|---|---|---|---|
| Gmail (`ai@`) | Connected | The white-label identity | — |
| OpenRouter | Connected | All text models behind one key | No spend cap recorded |
| Drive | Connected | Voice docs, WLF strategy, case study, recordings | OAuth app not yet built — see §5.3 of the mapping |
| **GHL** | **Connected** | **126 emails with bodies**, Apr 2024 → Sep 2026, plus the offer map | `emails/stats` 401s — open and click rates missing |
| **Slack** | **Connected** | Bot in 7 private channels, all 7 read-only scopes proven | **History not yet fetched** |
| **Zoom** | Partial | **150 transcripts · 803,947 words**, pulled by hand from the UI | No API — the `ai@` role cannot create the app |
| **Fathom** | Partial | Webhook + API proven end to end on a test account | Keys are per person; WIA team keys in progress |
| Instagram | Partial | **18 carousels · 159 slides**, scraped from the profile | No Graph token; reel scripts have no text source |
| ChatGPT | Partial | Account credentials plus shared chat links | No data export |
| Canva · Descript | Not granted | — | Carousel copy and reel scripts as text |
| Speech-to-text | **No longer blocking** | — | Still needed for any recording with no transcript upstream |

### 8.1 What changed

**The transcripts outlived the recordings.** WIA deletes client meetings from
Zoom to save storage, so the assumption was that the calls carrying results were
gone. They are not — Zoom stores transcripts separately from recordings, and
508 of them were sitting in Transcript Management with no auto-delete set.

150 were downloaded and parsed by `corpus/index-zoom.mjs`:

| | |
|---|---|
| **Client calls** | **78** — 498,208 words |
| Workshops & Q&A | 4 (Drive lists 6; two still missing) |
| Internal, triaged out | 61 |
| Fragments | 7 |
| **Extractable** | **143** |

Funktastic appears in 13, Press Record in 22, Miss Lyss in 4, Carroll Hall in 5.
One of the 17 supposedly unreadable Drive videos — the Emily Foster brand
workshop — is confirmed present as a 15,245-word transcript.

Verified unique by content rather than filename: exact hash, timestamp-stripped
hash, and Jaccard similarity across every pair. Sixty files share one generic
Zoom-assigned name, so the filenames prove nothing.

### 8.2 Attribution is weaker in Zoom than in Fathom

A Zoom VTT carries a display name and nothing else, so "this speaker is a
client" is inferred from who they appear alongside. Fathom resolves speakers to
calendar invitees by **email** and marks each `is_external`, which is fact
rather than inference — but only for people on the invite. Across two real
meetings, 1 of 3 speakers resolved; impromptu meetings resolve nobody.

Every normalised record therefore carries `attribution: "email-matched"` or
`"name-only"`, per speaker. A pipeline that forgets the difference will
eventually put a quote in the wrong client's mouth. See grounding rule 6.

### The one calibration asset

**Funktastic** is the only chain where the source *transcript* and the published
output both survive: transcript in, two Instagram reels and two marketing emails
out. That makes it the only case where the engine can be **scored** rather than
imitated. It is the acceptance test for MC-02 and MC-03.

---

## 9. Out of scope for Phase 1

Confirmed on the call, recorded here so nothing drifts back in:

- Designing the carousel graphics — Canva stays manual
- Generating the reel videos
- An AI voice clone reading the scripts
- Suggesting topics for the monthly workshop
- ClickUp as an input source
- Scaling email beyond roughly one repurposed send a week
- Any publishing path at all

---

## 10. Open decisions

| # | Question | Why it matters |
|---|---|---|
| 1 | How does Whitney flag a moment? | **Resolved 23 Sep (§12):** she approves, edits or rejects the engine's gists on the Content Atelier screen. Nothing generates until she approves |
| 2 | Where does the engine ask her questions? | **Resolved 23 Sep (§12):** the Content Atelier screen. What the engine needs from her lives in the gist — the CTA field is hers to set |
| 3 | Where do finished drafts live? | Drive folder per pack plus a calendar view, or ClickUp |
| 4 | Auto-handoff to Giselle, or approval-gated? | **Resolved 23 Sep (§12):** approval-gated at both ends — nothing is written without an approved gist, and nothing reaches Giselle until Whitney accepts the pack |
| 5 | Named-client consent | Four of five published chains name the client. Standing permission, or per-post judgement? |
| 6 | Is the **case study** a fifth format? | MC-04 exists on the timeline and the Miss Lyss case study exists, but this spec is not in the 16 September ideal |
| 7 | Is **Instagram Stories** a formal pack asset? | Named twice on the call, not in the stated four |
| 8 | The offer/CTA map | **Resolved 25 Sep:** recovered from the 126 fetched emails. `/accelerate`, `/full-service-ads-management-waitlist`, `/google-search-accelerator`, `/premiumleadgeneration-workshop`. Note the destinations had to come from the **editor payload** — both rendered variants route every link through `link.msgsndr.com/email-tracking` |
| 9 | Are the remaining `c_*` client channels in scope? | Bot is in three. Approval for the rest is with Whitney |
| 10 | Is `#social-media` an input as well as an output? | It is where finished content already accumulates, which makes it a record of what survived review — see §7 |

---

## 11. Current state — mock vs target

The component is currently an MVP running on fixture data.

**Implemented and real:** the queue with honest per-moment states
(`pack drafted` / `ready` / `blocked`), provenance chips per source, the
candidate → steer → CTA → lead → pack gate sequence, the published-precedent
view with Funktastic marked as the benchmark, and the corpus-and-access view.

**Still fixture:** every generated artifact. The production drafts for the Vault
landing-pages moment are real copy written against a real transcript, but they
were written by hand, not by the engine. No model call happens anywhere in this
build. No connector is wired. Every action mutates local state and raises a
toast that says so.

**To make it real, in order** *(revised 25 September — the first three are now
done, and speech-to-text left the list entirely)*:

1. ~~Provision speech-to-text and backfill the 17 Drive recordings~~ — **retired.**
   150 Zoom transcripts cover the material, §8.1
2. ~~Slack app install with a bot token~~ — **done.** Bot in 7 private channels
3. ~~GHL private integration token~~ — **done.** 126 emails with bodies
4. **Fetch the three Slack channels.** The only unblocked source still
   uncollected, and the only one with a deadline — free-plan retention truncates
   history to 90 days once the Pro trial lapses
5. Ingest pipeline → worthiness and gist (§5.3, §12)
6. Generation from the approved gist, against the voice corpus
7. Score the whole chain against Funktastic

**The corpus as it stands:** 150 Zoom transcripts (803,947 words), 126 marketing
emails, 18 carousels with 159 slides, three voice documents. The voice corpus is
in good shape; the moment corpus went from empty to 78 client calls on
25 September. Slack is the one hole left in it.

### Where it lives

| Path | Contents |
|---|---|
| `prompts/marketing-email.md` | Source layers, corpus-study checklist, voice card and the generation prompt for the email |
| `src/data/contentAtelier.ts` | Corpus, moments, candidates, steers, pack, precedent chains, coverage |
| `src/components/opshub/screens/ContentAtelierScreen.tsx` | The three views and the gate sequence |
| `src/hooks/useOpsHub.ts` | `setCandidate`, `setSteer`, `setCta`, `setLeadAsset`, `setScript`, `setClearance`, `stageContent` |
| `src/lib/opsHub.ts` | `atelierView`, `contentId`, `contentTab`, `contentCta`, `leadAsset` state |

---

## 12. The engine — decisions of 23 September

Settled in the working session of 23 September 2026. Where this conflicts with
§4, §5 or §10, this section wins.

### What it does

1. **Nightly batch.** At the end of each day the engine takes that day's call
   transcripts. Mostly client-facing calls reach it — which calls are fed in is
   an ingestion concern, handled in the implementation, not in the prompt.
2. **Worthiness, per call.** For each call it decides whether there is content
   worth making. *Not worth it* is a normal, frequent answer, returned with a
   one-line reason — this judgment is the only thing controlling how many gists
   Whitney sees, so the bar is strict.
3. **A gist per worthy call** — the direction the content would take (below).
4. **Whitney decides.** Every gist appears on the Content Atelier screen. She
   approves, edits or rejects each one. No cap, no ranking cut-off.
5. **An approved gist becomes a pack**, in her voice: 1 marketing email, 1
   carousel of 7–10 slides, up to 3 reel scripts, and captions — each piece
   written independently from the gist (below). Her edits to the gist are the
   steer for that pack.
6. **Whitney accepts the pack before it moves.** Nothing reaches Giselle until
   she does. Then carousel copy goes to Giselle for Canva, scripts go to Whitney
   to film, and the email goes to GHL as a draft. Nothing publishes (§2, §7).

### Worthiness — three tests

- **A spark** — praise, a result with a number, a milestone, a quotable line, or
  a teaching moment. Her own signals from 16 September (§3.1).
- **Enough for a pack** — distinct points for the reels, a story that fills 7–10
  slides, a lesson for the email.
- **Something new** — not an angle published recently, checked against
  `corpus/instagram/wia_carousels.md` and `corpus/emails/`.

The transcript is the spark, not the content (§3.1): the gist says what idea the
moment grows into, rather than summarising the call.

### Reels — up to three

Three reel scripts is the target, each on a different point. When a call
supports fewer, the engine writes fewer, and the gist says how many. One
complete, valuable reel beats three thin ones.

### Every piece is written independently

The email, the carousel, each reel script and the captions are each written from
the approved gist on its own. No piece is written from another, and whether they
are generated at once or one at a time doesn't matter. This replaces the
lead-asset step of §4.1 and §5.

The gist is therefore the only thing the pieces share. Its main argument and key
lines are what keep the pack consistent — the same idea in the same language,
without the pieces repeating each other (§4.1's goal) — so they deserve weight
when the gist fields are refined in testing.

### The gist

- The quote, with its timestamp and the call it came from
- Why it's worth using
- The direction — client story, teaching, reframe or offer: the four kinds in
  the published record
- The main argument it grows into, and the reel angles (one to three)
- First person or team voice, and which offer it points to
- Warnings — is the client identifiable, are there numbers on screen, is any
  figure an estimate stated as fact (#3's “$90,000” in the carousel ledger —
  9 bookings × a ~$10K average, published as booked revenue — is the worked
  example)
- The CTA — left for Whitney. §6 still holds: the engine never picks one

The fields will be refined in testing.

### Static prompts

The worthiness-and-gist prompt and the generation prompts are fixed, versioned
files in the backend, sent to the model as they are. **There is no learning loop
after launch.** Whitney's edits shape the pack they belong to and nothing else;
changing how the engine judges or writes is a deliberate edit to a prompt file.

That puts all the calibration before launch. Testing runs the prompt against
past calls with known outcomes — the Funktastic and Carroll Hall calls became
content (§8, `prompts/marketing-email.md` §5) — plus a few that didn't.

### Still open

- **Transcript access — largely solved, 25 September.** Two things landed. The
  back catalogue came from Zoom's Transcript Management, which keeps transcripts
  *separately from recordings* and so survived the deletion policy: 150 pulled,
  78 of them client calls (§8.1). Going forward, Fathom's webhook and API are
  proven end to end and free on every plan, so a call it records never depends on
  Zoom storage again — the remaining step is WIA team members generating their
  own keys, since a Fathom key reaches only its owner's meetings. Speech-to-text
  is no longer on the critical path; it is needed only for a recording whose
  transcript never existed upstream.
- **Captions — to clarify with Whitney.** §4 asks for hashtags and alt text;
  none of the 18 published carousels in the ledger uses either. Her answer
  decides whether the engine produces them.

### Next

1. Supporting documents — the founder voice guide, the voice knowledge base, the
   WLF strategy and the rest — to design the worthiness-and-gist prompt.
2. Reel scripts from Descript (`corpus/canva-descript-access.md`) — the one
   asset with no published corpus yet.
