# Email corpus — findings

Superseded as a listing by [`FETCHED.md`](./FETCHED.md), which is generated.
This file holds what the corpus *means* for generation.

**126 sent campaigns**, April 2024 → September 2026, pulled from LeadLock via
the Private Integration Token on 21 September 2026. Not the six preview URLs
the handover supplied — the API had everything.

---

## The corpus is two different eras

Splitting matters more than the raw count. Do not train a founder-voice model
on all 126.

| Era | Sends | Character |
|---|---|---|
| 2024 (15) | Apr–Dec 2024 | Promotional. Flash sales, `$300 off`, `LAST CHANCE!!!`, `[TIME SENSITIVE]`, summit invitations |
| 2025 (71) | Jan–Dec 2025 | Mixed. Webinar and lead-magnet pushes, Meta Ads Immersive Experience, Foolproof Follow-Up |
| **2026 (40)** | Jan–Sep 2026 | **The founder-voice motion.** Client stories, teaching, reply-bait |

The exemplar set for `prompts/marketing-email.md` is **2026 only**, and
arguably only the six from June onward, which is where the
`{subject} {date} | {CTA} CTA` naming convention starts and the repurposing
motion is visible. The 2024–25 material is useful as *negative* reference —
what the voice moved away from.

---

## Confirmed against real bodies

**The campaign name really is the log.** `{subject} {date} | {CTA} CTA` parses
cleanly, and `cta_from_name` is populated in every 2026 file.

**Her stated CTA rule holds.** Teaching content → Accelerator sales page.
Client result → ELEVATE waitlist. Everything else → Reply, which is the single
most-used CTA.

**Subject lines are frequently the client's own words, in quote marks.**
`"I honestly have no idea if this is working."` ·
`"It feels like our sales are on autopilot."` The API confirms the quotation
marks are part of the subject — they were invisible in the campaign list.
So the accepted candidate quote is a **subject-line candidate**, not just body
material.

**List size ~800–840** and growing slowly: 803 in June, 840 in September.
Delivery is consistently 99%+.

---

## Two corrections to earlier assumptions

**Emoji are in use.** The 20 August subject is
`She didn't post on Instagram for 10 weeks 😱`. Reading the campaign list alone
suggested she never used emoji — the list was truncating them. Negative-space
rules derived from titles are unreliable; derive them from bodies.

**Merge tags are live and must be preserved in generated copy.**

```
{{contact.first_name}}   118 emails
{{location.name}}         75
{{location.email}}        75
{{right_now.year}}        75
```

`{{contact.first_name}}` appears mid-sentence, not as a greeting —
*"What would happen to your wedding business if you didn't post on Instagram
for 10 weeks, {{contact.first_name}}?"* Generated copy should place it the same
way rather than opening with `Hi {{contact.first_name}}`.

---

## Footer chrome

Every extracted body carries the same tail — signature block, copyright line,
mailing address, unsubscribe. It is template-level, not written per email, and
should be stripped before the bodies go into a prompt as exemplars. It is left
in deliberately so the boundary is visible and can be cut in one place.

---

## Still outstanding, and not obtainable from the API

`source_session` and `instagram_sibling` are blank in all 126 files. The API
gives subjects, bodies, dates, recipients and CTAs; it cannot say that
*"She didn't post on Instagram for 10 weeks"* came from that planner call, or
which reel it was repurposed from.

Only Whitney or Giselle can supply that mapping, and it is what turns 126
emails from a style sample into input/output pairs. The six from June 2026
onward are the ones worth asking about — that is a short, specific question
rather than an open-ended request.
