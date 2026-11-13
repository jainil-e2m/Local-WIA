# Marketing email — generation spec

The first of four asset prompts for the Content Atelier, written when it was planned as a Command Center
screen. The Atelier is its own app now and owns its corpus; this is the original spec, kept for reference.

One marketing email per accepted moment. Destination is GHL. The LLM writes the
copy and nothing else — no send, no schedule, no template rendering.

**Read §6 before using the prompt.** The voice card it depends on is not filled
in yet, because the six published emails sit behind LeadConnector preview URLs
we cannot read at volume. Any voice rule stated below without a citation is
inferred from the 16 September transcript, not derived from her actual sends.

---

## 1. Three source layers

The mistake to avoid is treating "sources" as one list. They do three different
jobs and they fail in three different ways.

| Layer | Question it answers | Fails as |
|---|---|---|
| **Shape** | What does a WIA marketing email look like? | Generic AI email voice |
| **Substance** | What is *this* email about? | Plausible-sounding invention |
| **Constraint** | What may this email not do? | Something that cannot be sent |

### 1.1 Shape — the exemplar corpus

What teaches the model the form. Ranked by how much signal each carries.

| Source | Signal | Held? |
|---|---|---|
| **6 published GHL emails** | The form itself — subject, structure, length, register, CTA placement | URLs only |
| **ChatGPT email-generation chats** | Her *editorial deltas* — what she asked to change between draft and send. Often worth more than the finished email | 4 chats |
| **The subject/date/CTA log** | Which CTA she chose for which source type, over time | **Found** — it is the LeadLock campaign naming convention |
| **Founder voice guide** | Stated voice rules | Held |
| **Founder Voice Knowledge Base** | Second voice doc, overlap unreconciled | Held |
| **Published IG captions** | Same voice, compressed. Useful for tone, not structure | 5 posts |

The four paired chains are the few-shot gold, because they show input *and*
output:

| Chain | Source readable? | Emails |
|---|---|---|
| **Funktastic** | Yes — transcript held | 2 |
| **Carroll Hall** | Yes — transcript held | 2 |
| Miss Lyss | No — video only | 1 |
| Market research workshop | No — video only | 1 |

Only Funktastic and Carroll Hall can be used as full few-shot examples. The
other two can teach form but not the transformation.

### 1.2 Substance — this email's content

| Source | Role |
|---|---|
| **The accepted candidate** | The soundbite or result, with its timecode |
| **Surrounding transcript** | Context the quote sits in. The claim alone is not enough |
| **Whitney's steer** | The angle. **This outranks the transcript** |
| **The CTA** | Set by her, never chosen by the model |
| **The approved lead asset** | Only when the email is derived rather than leading |
| **Slack screenshot / thread** | Where the moment came from Slack rather than a call |

On the steer outranking the transcript — this is the thing most likely to be
built wrong:

> "The transcript normally sparks the idea, but then we're taking that and
> running with it. It's not like the context of the call is what gets turned into
> the content — it's an idea that then gets built upon."

A model that faithfully summarises the call has failed at this task.

### 1.3 Constraint

| Source | Constraint |
|---|---|
| **Content framework** | Hook → problem → solution → transformation → how we can help → CTA |
| **Voice-switch rule** | First person for her own experience or a 1:1 client conversation; "we"/team when general |
| **Clearance rule** | No identifiable client, no legible analytics, every claim traced to a timecode |
| **Coherence rule** | Shares threads with the rest of the pack without being redundant, and never reads as a filled-in template |
| **Repurpose framing** | The email is a repurpose, not a sales push. Do not write it as a conversion asset |

---

## 2. What to study before writing the prompt

This is the work that has to happen against the six emails. The output is a
**voice card** (§3) that gets injected into every generation.

### 2.1 Structure

- Subject line: character length range · question vs statement · curiosity vs
  specificity · does it name a number?
- Preview text: present? Does it extend the subject or repeat it?
- Opening move: story first, claim first, or question first?
- Body length: word count range across the six
- Paragraph rhythm: single-line paragraphs, or blocks? Average sentence length
- Is there a numbered or listed section, and where does it sit?
- The "tie back to how we can help" transition — where in the body, and how
  hard is the turn?
- CTA: button, inline link, or plain ask? How many per email?
- P.S.: used? What goes in it?
- Sign-off form

### 2.2 Voice

- First person vs "we" — confirm the trigger she described, and find the
  exceptions
- Contraction density
- Punctuation habits — em-dashes, ellipses, sentence fragments
- Jargon level: "CPL" or "cost per lead"? "creative" or "the ad"?
- Number handling: exact, rounded, or hedged ("just under 5%")
- Client reference: named, anonymised, or described ("a venue in Texas")
- Second person — does she address the reader as "you" throughout?

### 2.3 Strategy

- Teaching-to-pitching ratio by word count
- How the client story is framed: direct quote, paraphrase, or scene
- CTA ↔ source-type correlation — does the workshop → Accelerator, 1:1 result →
  Elevate rule actually hold across the six?
- What the email keeps, drops and **adds** relative to the Instagram content it
  repurposes. This is the derivation rule, and it can only be read off
  Funktastic and Miss Lyss

### 2.4 Negative space

Equally important and usually skipped. What does she **never** do?

- Emoji? Urgency or scarcity language? Discount framing?
- `Hi {{first_name}}` merge-tag openers?
- Exclamation marks?
- Length she never exceeds
- Claims she never makes without a hedge

### 2.5 Mechanical

- GHL merge tags in use
- Link structure and any tracking convention
- Footer and compliance block — is it template-level or in the body?

---

## 3. The voice card

The artifact §2 produces. Injected into every email generation. Fill from the
six emails; do not fill from intuition.

```yaml
voice_card:
  subject:
    length_chars: [TBD, TBD]
    forms: [TBD]              # question / statement / number-led
    never: [TBD]
  preview_text:
    used: TBD
    relationship_to_subject: TBD
  body:
    word_count: [TBD, TBD]
    opening_move: TBD
    paragraph_style: TBD
    avg_sentence_words: TBD
    list_section: TBD
  cta:
    form: TBD                 # button / inline / plain ask
    count_per_email: TBD
    placement: TBD
  ps:
    used: TBD
    contains: TBD
  signoff: "— Whitney"        # observed in the one long-form draft we hold
  voice:
    person_rule: >
      First person when the source is Whitney's own experience or a 1:1 client
      conversation. "We" / the team when the piece is general.   # stated 27:09
    contractions: TBD
    jargon_level: TBD
    number_style: TBD
    client_reference: TBD
  never:
    - TBD
```

---

## 4. The prompt

Two variants, because the email is sometimes the lead asset and sometimes
derived from an approved reel. Same scaffold, one conditional block.

### 4.1 System

```
You are a copywriter embedded at Wedding Industry Ads, a Google and Meta ads
agency for wedding businesses. You write marketing emails in Whitney Hodges'
voice for WIA's own list.

You write copy. You do not design, schedule, send, or render anything.

HARD RULES — a violation makes the output unusable, not merely worse:

1. Never quote a person unless the exact words appear in SOURCE EXCERPTS below.
   Paraphrase supplied as context is not a quote and may not be presented as one.
2. Never state a figure that is not in SOURCE EXCERPTS. Every figure you use
   must be listed in `claims` with the timecode it came from.
3. Never choose a call to action. Use the one supplied in CTA. If its
   destination URL is empty, write the literal token {{CTA_URL}} and add a line
   to `handling_notes`.
4. Never name or make identifiable a client, venue, or business unless
   CLEARANCE says named clients are permitted for this moment.
5. Never invent a result, testimonial, statistic, or customer.
6. If SOURCE EXCERPTS is insufficient to support the angle in STEER, say so in
   `blockers` and return no body. Do not fill the gap.
```

### 4.2 Voice conditioning

```
VOICE CARD
<the §3 YAML, filled>

REFERENCE EMAILS — these are real, approved, and went out. Match their form,
not their content.
<2–3 full emails from the corpus, chosen to match the source type of the
current moment — workshop exemplar for a workshop, client-result exemplar for
a client result>

EDITORIAL NOTES — changes Whitney asked for between draft and send on past
emails.
<extracted from the ChatGPT generation chats>
```

### 4.3 Task input

```
MOMENT
  client:       {{client}}
  session:      {{session_title}}
  type:         {{workshop | client_call | office_hours | slack}}
  date:         {{date}}
  source:       {{platform}} · {{holding}}

SOURCE EXCERPTS — the only material you may quote or cite.
  [{{timecode}}] {{verbatim excerpt}}
  [{{timecode}}] {{verbatim excerpt}}
  ...

STEER — Whitney's angle. This outranks the transcript. The transcript is the
seed; the steer is the idea it grew into. Do not summarise the session.
  {{steer_text}}

CTA
  label:        {{cta_label}}
  track:        {{cta_track}}
  destination:  {{cta_url_or_empty}}

CLEARANCE
  named_clients_permitted: {{true | false}}
  analytics_on_screen:     {{true | false}}
```

### 4.4 The conditional block

**When the email leads:**

```
This email is the LEAD asset. Everything else in the pack — three reel scripts,
a carousel and captions — will be written from it afterwards. Make the central
argument explicit and self-contained.
```

**When the email is derived:**

```
This email is DERIVED from a reel script Whitney has already approved.

APPROVED LEAD
<full text of the approved reel script>

Carry its argument and its language. Somebody who watched the reel and then
opened this email should recognise the same idea in the same words in the same
places — and should still find something here the reel did not give them.

Do not restate the reel. Email affords length the reel did not: the detail that
was cut for time, the second example, the caveat. Use that affordance.
```

That second paragraph is the coherence rule made operational. Her wording:

> "Somewhat saying the same things, using the same language in the same places,
> but it wouldn't be like somebody consuming all three of those things feels like
> it's super redundant either."

### 4.5 Output contract

```
Return JSON. No prose outside it.

{
  "subject_primary": "",
  "subject_alternates": ["", "", ""],
  "preview_text": "",
  "body": "",
  "cta_button": "",
  "ps": "",
  "person": "first_person | team",
  "person_rationale": "",
  "claims": [
    { "text": "", "timecode": "", "source": "" }
  ],
  "handling_notes": [],
  "blockers": []
}
```

`claims` is what makes the clearance gate machine-checkable instead of a human
eyeballing a wall of text. Any figure in `body` that is not in `claims` is a
hallucination, and that is a cheap automated test.

### 4.6 Self-check

Appended to the prompt. Cheaper than a second model call and catches most of it.

```
Before returning, verify:
- Every figure in body appears in claims with a timecode.
- Every quoted sentence appears verbatim in SOURCE EXCERPTS.
- The CTA matches the supplied one in intent and destination.
- The person choice matches the voice card rule, and person_rationale says why.
- Body length is inside the voice card range.
- If derived: the email is not a restatement of the lead, and adds at least one
  thing the lead does not contain.
- No client is identifiable unless clearance permits it.
```

---

## 5. How we know it worked

**Funktastic is the benchmark.** It is the only chain where the source
transcript and the published emails both survive, so it is the only case where
output can be scored rather than admired.

The test: run this prompt on the Funktastic transcript with a steer
reconstructed from the ChatGPT chat, and compare against the two emails that
actually went out.

What to measure:
- Did it pick the same angle?
- Subject line in the same register?
- Same CTA track?
- Length inside the observed range?
- Any claim not in the transcript? (automatic fail)

Carroll Hall is the second pass, for the harder question — **two emails from one
session without the second reading as a repeat.** She solved that by hand; it is
the clearest worked example of the coherence rule in the corpus.

---

## 6. What blocks this today

| Blocker | Effect |
|---|---|
| **No GHL private integration token** | The six emails are preview URLs. No programmatic read, no drafting back into the account |
| ~~Subject/date/CTA log not supplied~~ **RESOLVED 21 Sep** | The log is the LeadLock campaign naming convention: `{subject} {date} \| {CTA} CTA`. See [`corpus/emails/_INDEX.md`](../corpus/emails/_INDEX.md) |
| **n = 6** | Six emails, not consecutive. She sends ~weekly; three months would be ~12. Thin for deriving a voice card, though the ChatGPT chats partly compensate |
| **No destination URLs** | Every generated CTA carries `{{CTA_URL}}` until the offer map arrives. The CTA button settings in LeadLock hold them |
| **Two voice documents, unreconciled** | Unclear which wins where they disagree |
| **One ChatGPT chat is a duplicate URL** | Miss Lyss and Carroll Hall "marketing generation" point at the same chat. One label is wrong and a chat may be missing |

None of these block writing the prompt. All of them block filling the voice
card, which is the part that decides whether the output sounds like her.
