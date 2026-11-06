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
| **Reel scripts** | Spoken audio in an MP4 | **nowhere** — not authored as text, see §2 |

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

# 2 · Descript — WITHDRAWN

> **Corrected 28 September.** This section asked for a Descript seat on the
> grounds that it holds WIA's reel scripts. **It does not, and the ask is
> withdrawn.** WIA uses Descript to edit recorded video — trimming clips and
> merging them into a finished reel. Scripts are not written there.
>
> The paragraphs below are kept because the reasoning error is easy to repeat.

## What the argument got wrong

The original case ran: Descript transcribes what it edits, therefore every reel
"already has its script sitting there as text."

The first half is true — transcript-based editing is Descript's core mechanic,
not an opt-in. The conclusion does not follow. What that produces is a record
of **what Whitney said**, generated after filming. An authored script is
something written *before* it, and WIA does not write one.

Those are different artefacts, and only the second is what §4 of the spec asks
the Atelier to produce: timecoded, hook, b-roll notes, on-screen text, three
per pack on three different claims.

So the value of a Descript seat collapses to spoken-voice material — which is
the one thing the corpus is least short of. There are **803,947 words** of Zoom
transcript already on disk, 498,208 of them from client calls. Another few
thousand words of delivered reel audio adds very little, and does not add the
thing that was missing.

## Where the reel format actually has to come from

Nowhere, currently. This is the only one of §4's four outputs with no example
of a real WIA instance, and that is worth stating plainly rather than
discovering at draft time.

Two routes, in order of preference:

1. **The ChatGPT chats.** Generation happened there, so a reel script that was
   ever written down is likelier to sit in a chat than in an editing tool. This
   is now the main reason those chats matter.
2. **Treat §4 as the specification.** The format is defined in the spec; the
   first packs set the precedent instead of inheriting one. Legitimate, but it
   should be a decision taken deliberately.

The drafts in `src/data/contentAtelier.ts` are **fixture data written for the
mock UI**. They are not WIA output and must not be mistaken for precedent.

## No ask goes to WIA for this

The seat request that stood here — add `ai@weddingindustryads.com` to the
Descript workspace, export transcripts per composition — has been removed
rather than struck through, because a withdrawn ask that still reads as a
checklist is one someone actions by mistake.

**Nothing about Descript needs to reach Whitney or Giselle.**

---

## Where the four pack formats actually stand

*Updated 28 September. This table previously read "what this unlocks, once both
land" and claimed all four formats would end up with published precedent behind
them. Three do. The fourth does not, and neither of the two tools in this
document's title was ever going to supply it.*

| Pack format | Precedent held | Source |
|---|---|---|
| **Marketing email** | **126 sends**, Apr 2024 → Sep 2026 | GHL, via PIT |
| **Carousel, per slide** | **18 carousels · 159 slides · 6,328 words** | Instagram scrape |
| **Captions** | **3,775 words**, verbatim | Instagram scrape |
| **Reel scripts** | **none** | No source exists — see §2 |

So the voice card in `prompts/marketing-email.md` §3 can be filled from data for
three of the four. The reel format has to be specified rather than inferred, or
recovered from the ChatGPT chats if it was ever written down there.

Two blockers this document used to name are gone, and neither was resolved by
the route it proposed:

- **Carousel copy** was recovered by transcribing the published slides, so the
  Canva ask in §1 is no longer load-bearing either.
- **Speech-to-text** is no longer the critical dependency. Zoom stores
  transcripts separately from recordings, and 150 of them — 803,947 words —
  are on disk. See `Content_Atelier.md` §8.1.
