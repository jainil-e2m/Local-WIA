# Canva and Descript — access

The two tools that hold **carousel copy** and **reel scripts as text**.

Both were named on the 16 September call as part of how content actually gets
made. Neither was put on the access list, because at the time they read as
*design and editing tools* — places where WIA's output goes, not places it comes
from. That is exactly backwards for a voice corpus.

---

## Why these two, and not Instagram

The three things we want to learn Whitney's voice from store differently, and
only one of them is text on Instagram.

| Asset | On Instagram | As text, natively |
|---|---|---|
| Captions | Text | Instagram ✅ |
| **Carousel slide copy** | Burned into the JPEG | **Canva** |
| **Reel scripts** | Spoken audio in an MP4 | **Descript** |

Going after carousels and reels through Instagram means OCR on every slide and
a speech-to-text provider — and speech-to-text is the component's open blocker,
the same one holding 17 Drive recordings. It would be strange to take on that
dependency to recover text that already exists as text, two tools over.

There is a second payoff. `corpus/emails/FETCHED.md` records that
`source_session` and `instagram_sibling` are blank in all 126 email files, and
that the mapping cannot be derived from the GHL API — *"only Whitney or Giselle
know which call each email came from, and that mapping is what turns this from a
style sample into input/output pairs."* Canva design dates and Descript project
dates are the closest thing to that mapping anyone can recover without asking a
person, because a carousel and its email were made in the same week from the
same source.

---

# 1 · Canva — carousel copy

## What we want

The text of the published carousels, per slide, in slide order. Whitney writes
the copy; Giselle pastes it into the brand templates — *"we have the carousel
templates in there"* — so Canva holds the approved final wording as live text.

Seven to ten slides per carousel, deliberately text-heavy and *"not surface
level."* That structure is most of what a carousel prompt has to learn, and it
is invisible in a caption.

## The route

Canva **Connect APIs**, as a **private integration** — usable only by members
of the team that created it, and it needs no marketplace review.

| Step | Who |
|---|---|
| 1 · Confirm the Canva plan supports private integrations | **WIA** |
| 2 · Create the integration | **WIA team admin** |
| 3 · Set scopes, generate client id and secret | **WIA admin → E2M** |
| 4 · Complete the OAuth flow, store the refresh token | **E2M** |

**Step 1 is the one that can stop this.** Private integrations are a Canva
Teams / Enterprise capability, and on some plans the team owner has to enable
them before they appear. If WIA is on Canva Free, that is a real fork — either a
plan change, or fall back to the manual export below.

**Developer Portal:** <https://www.canva.com/developers/> → **Your
integrations** → **Create an integration** → **Private**.

Scopes:

| Scope | Why |
|---|---|
| `design:meta:read` | List designs and read their titles and dates — how we find the carousels |
| `design:content:read` | Required to export a design's content |
| `folder:read` | Navigate the brand folder structure rather than listing every design in the account |
| `asset:read` | Only if we later want the slide images alongside the text |

No write scopes. Nothing in the Atelier creates or edits a Canva design —
placing copy into templates is Giselle's job and stays that way.

## Getting text out, honestly

There is no endpoint that hands back a design's text layers as JSON. The route
that works is **export, then extract**:

1. `GET /v1/designs` — list, filter to the carousel templates
2. `POST /v1/exports` with `format: pptx` — returns a job id
3. `GET /v1/exports/{exportId}` — poll until the download URL appears
4. Extract text per slide from the PPTX

**PPTX, not PDF.** Both carry extractable text, but a PPTX slide maps 1:1 to a
carousel slide, so slide order and slide boundaries survive without inference.
In a PDF they have to be reconstructed, and slide boundaries are the structure
we are trying to learn.

## The fallback, if private integrations are not available

Giselle opens each published carousel → **Share → Download → PPTX** → drops
them in a Drive folder we already have access to. Slower, no worse as data, and
it needs no plan change or developer portal at all. Roughly a minute per
carousel.

## What to send back

```
CANVA_CLIENT_ID=
CANVA_CLIENT_SECRET=
CANVA_REFRESH_TOKEN=
```

---

# 2 · Descript — reel scripts

## What we want

The transcript of every reel WIA has published. Not five — all of them.

Whitney's process, in her words: *"I'll record the reels on my phone and either
upload them into Descript or give them to Giselle to upload into Descript. And
then she'll trim or edit from there."*

Descript transcribes what it edits. That is its core function, not a feature
anyone has to switch on. So every reel that has ever been cut in Descript
**already has its script sitting there as text**, whether or not anyone thought
of it as a transcript. This is the single largest untapped body of Whitney's
spoken voice in the whole engagement, and it costs nothing to read.

It is also the closest match to what the Atelier actually produces. The pack
calls for three reel scripts per moment; the drafts in
`src/data/contentAtelier.ts` are timecoded with hooks, b-roll notes and
on-screen text. Descript transcripts are the only corpus that shows what her
*delivered* scripts sound like, as opposed to what a written script looks like.

## The route — a workspace seat, not an API

This is a deliberate departure from how the other sources were done, and it is
worth stating plainly rather than discovering later:

**Descript's public API is not a dependable integration surface for bulk
transcript export.** Unlike Slack, GHL and Meta — each of which has a documented,
stable read API that `corpus/` already uses — Descript's programmatic access has
been limited and inconsistently available. Building a fetcher against it is a
gamble; the export path is not.

So the ask is smaller and more certain:

| Step | Who |
|---|---|
| 1 · Add `ai@weddingindustryads.com` to the Descript workspace, viewer or editor | **WIA — Whitney or Giselle** |
| 2 · Export transcripts from each reel project | **E2M** |

In Descript, per composition: **File → Export → Transcript**, as `.txt` or
`.docx`. Plain text is preferred and sufficient — the corpus wants the words,
not the timing.

If a seat is not possible, the alternative is Giselle running the same export
and dropping the files into Drive. Same data, one more person's afternoon.

## What to ask for alongside the seat

Worth requesting in the same message, because it costs nothing extra and
answers a question the corpus will otherwise raise:

- **Which reels went out**, so an unused draft in the workspace is not mistaken
  for approved voice. A cut that never shipped is not precedent.
- **Roughly when**, so a script can be paired with its caption and its email.

---

## What this unlocks, once both land

| Corpus | Source | State |
|---|---|---|
| 126 marketing emails | GHL, via PIT | **Held** |
| Slack channel history | Bot token | **Held** — test channel proven |
| Captions | Instagram Graph API | See `instagram-app-setup.md` |
| **Carousel copy, per slide** | Canva | This document |
| **Reel scripts** | Descript | This document |

At which point every format in the pack — email, reel, carousel, caption — has
a corpus of approved, published precedent behind it, and the voice card in
`prompts/marketing-email.md` §3 can be filled from data rather than intuition
for all four rather than just the email.

The transcription blocker still stands, and still blocks the 17 Drive
recordings. Nothing here fixes that. What it does is stop that blocker from
also costing us the voice corpus, which it does not need to.
