# Phases N6, N10, N7 and N11 (25 October 2026)

The record of the run, done on the owner's instruction of 25 October 2026 (decisions in `DECISIONS.md`; the benchmark's
design in `BENCHMARK.md`; E.B24's warnings decided in `EB24-decisions.md`). Every reading here is the implementing agent's,
recorded as delegated (D12, R55); none is WIA's. Times are UTC.

## The N11 benchmark (copy D, the Client key)

Copy D is production's database of 25 October (restored, migrated), so a cycle reads production's identities,
team-practice scenes, account memory, published log and earlier cards. Week 1 is the week of 1 June 2026 (nine calls),
Week 2 the week of 8 June (eleven calls, six of them internal meetings). Neither week's text is in any prompt (D28).

### Week 1, strategist v8 (`proof/week1-v8.*`, USD 0.71)

| Card | Reading |
| --- | --- |
| 1. How we keep ads useful after an inquiry | Whitney's own explanation of why campaign layers carry different creative; her alternative E ("explaining the work beyond attractive ads") at a narrower point. Pass |
| 2. What we want couples to know before a venue tour | A LeadLock recommendation (introduce the person giving the tour before the visit). Pass |
| 3. How we keep a photographer's promise accurate | Her alternative B (accurate messaging as valuable work), credited to the photographer and Carmen as the call shows. Pass |
| 4. How we decide where LeadLock belongs | Close to her alternative F, turned from the objection she rejected to LeadLock's place beside the owner's CRM. Pass |
| 5. How we hand a Google campaign over to its owner | CONVERT for the Accelerators, from the launch call. Pass |

Of Whitney's six Week 1 alternatives, two are cards (B, E), one is close (F), and two are considered ideas with their
reason (A, the owner's market knowledge, lost the one-card-per-conversation choice to card 5 from the same call; D, the
venue's value positioning, would repeat September's published UVP point); C (keyword decisions) has no scene in this
window's calls. Her verdict on the October batch was 1 of 5; this slate is her method's output, and every card passes the
five tests. **Reading: pass.**

### Week 2, strategist v8 (N8's sample, `research/n8-2026-10/proof/d-week2-v8.*`) and v9 (`proof/week2-v9.*`)

The two samples agree on four of five moments: the owner's own infrastructure respected (a prospect), the venue tour
conversation (pre-tour wait in v8, post-tour readiness in v9), the owner's local keyword knowledge, and WIA testing a new
sales tool on its own account first. Both file the hand-built v2 ideas WIA saw on 20 October differently: the budget
decision on the venue call loses the one-card-per-conversation choice to the tour moment of the same call (it stays an
internal insight), the AI-assisted account story stays internal because the fact Whitney attested is in no record, and
"what strategy calls cover" has no card in either sample. The ChatGPT angles WIA's own process found for this week (A02
the tour decision, A07 the owner's knowledge, the AI widget reserve) are all cards.

Strategist v9 adds one section ("Decisions and stakes belong in public"). Its effect shows in the guardrails: v9's tour
card tells the writer which stakes it may state in the call's own terms ("some couples had booked tours without
responding"; "the owner distinguished first tours from last tours"), where v8's guardrails listed only what to keep out.
The card verifier caught one overclaim in v9's slate (card 2's point said WIA builds readiness-based follow-up; the call
shows Whitney asking about readiness), which the delegated Gate 1 reframed before developing it. **Reading: pass; v9
replaces v8 in production** (the switch-back is v8).

### Week 2 through Gate 2 and the packs (copy D, USD 2.46; the run's benchmark total USD 6.64)

Two of v9's cards were developed at the delegated Gate 1 (`proof/week2-v9-gate1-*.json`) and taken through Gate 2 and the
packs as the WIA team would (`gate2-benchmark.json`, `refresh-tour-brief.txt`, `pack-edits*.json`; final copy in
`proof/week2-v9-packs.md`). The brief writer was interrupted once by the pause; the run stopped with an unsettled paid call,
which the system does not resend by itself, and was retried explicitly (`POST /jobs/{id}/retry`), as the alert would ask.

| Piece | Reading |
| --- | --- |
| Brief, the keyword review (WARM) | True to the call, credits exact ("our team": the strategist has left), anonymity kept (no term, market or name), no explicit ask (R-9). Its weakness was WIA's expertise: the copy said the client helped without saying why a local name matters to search. The team added one line at Gate 2 (couples who say the name may search with it; a list built from outside the market can miss it), as reasoning, not a result; no refresh needed. Approved |
| Brief, the post-tour follow-up (CONVERT) | Two blockers (a client quotation her call does not clear; beats that "credit" her with more than the call shows) and abstract, repetitive copy. One refresh with the team's notes (`refresh-tour-brief.txt`): reported speech only, the stake in the call's terms (more tours, more couples going quiet), her within-a-week practice as the reason follow-up differs, short concrete lines. The refreshed brief fixed every point. Approved after two "Whitney asked/agreed" lines became "we" in WIA's carousel voice |
| Pack, the keyword review | Publishable after light edits (rubric 3). Hooks name the subject; siblings open differently; no overclaim (P4 held in every piece); the carousel caption's opener ("Being asked to approve a Google keyword list is different from being invited to add to it") is the best line. Still more measured than Whitney's register in the email's middle. Edits: the team's own Gate 2 line had become the same sentence in three pieces (the pack step flagged it), "travelling", the email's second retelling, two shared sentences |
| Pack, the post-tour follow-up | Publishable as is after light edits (rubric 4): it opens on the concrete situation ("she was booking more tours, but more of those couples were going quiet afterwards"), keeps one distinction, tells her practice in reported speech, gives every sibling its own hook and wording, and keeps the offer to what the offer sheet says (WIA sets it up; the owner runs it). Edits: slide 1 leads with the problem (the check's warning), the shared fact worded differently across siblings. The pack step listed the figures it left out (her tours with no response) under "Stronger with permission" instead of using them |

**Defect found and fixed (one re-test).** Both packs were blocked by `first_touch.who_did_what`, which a reviewer cannot
attest, on lines that were not story beats: the close for both offers ("Others want us to launch their campaigns and guide
them while they run them"; the fixture's own "Whether you'd like our team to manage your ads" fails the same way) and the
offer described to the reader ("Inside it, we set up The Foolproof Follow-Up Advantage ... around your own conversations",
which is what the offer sheet says). The check now leaves out a clause that says what a reader may want, a "they" that
follows a general group, and, in the copy only, a clause addressed to the reader; the story's own third-person beats are
read as before (`f9f50cf`, `ee68cdf`, tests). Re-test: both packs' findings recomputed through the fixed checks have no
blocker (before: one each); copy D was rebuilt on the fixed code and both packs were marked ready there.

### E.X8: the packs beside Whitney's finished pieces

No judge (the owner's ruling); the reading uses the moves her six chains show (`backend/knowledge_base/19-transformations.md`)
and her published pieces (`15-exemplars.md`) as the checklist. It cannot be blind for the agent that ran it, and says so.

| Her move | The keyword pack | The post-tour pack |
| --- | --- | --- |
| The concrete situation leads, so a cold viewer knows the subject in one line (chain 2) | Yes ("A venue client gave our team another phrase to investigate for her Google Ads") | Yes, and the stake leads |
| One principle, said plainly (chain 1: running ads against building a system) | Yes, softer ("your knowledge belongs in the keyword conversation") | Yes ("a finished tour isn't a decision") |
| Who did what stays exact (chain 3) | Yes ("our team"; the client suggested, the team agreed to look) | Yes (Whitney asked and agreed; the client's practice is hers) |
| Every claim the offer can keep (chain 5) | No offer | Yes (the offer sheet's own words) |
| Invite, never warn or shame (chains 4, 6) | Yes | Yes (no blame on the couples, the ads or the automation) |
| Each sibling its own hook (chain 2) | Yes | Yes |
| No em dashes (chain 4) | None | None |
| Her pieces carry the client's own line and a figure (17 to 90 events; 10 weeks) | Not possible: no clearance, and the term stays anonymous | Not used: her quotation needs her okay; the figure is outside the approved example (listed under "Stronger with permission") |

**Reading:** the post-tour pack would sit beside her published pieces; the keyword pack is publishable but plainer, because
the one concrete detail that would carry it (the local name) must stay out. The gap to her finished pieces is the client's
own words and a figure, which is a permission question for WIA (the pack lists it), not a writing defect. No prompt
change: the writer and finisher did what the brief and the guardrails allowed.

## Production (25 October, evening)

**Deployed:** PR #28 (`4c082f4`: N6, N10, N7, N11 code; migration 011 ran on `api`), #29 (`45731a7`: the upkeep waits for a
used-up budget; a missed hour clears itself), #30 (`fafec9e`: Home's summary, alerts and costs, the schedule in the app,
archived weeks, the browser test), #31 (`bc38a32`: the upkeep retries its own interrupted scene jobs). Settings applied
(strategist v9, the Sunday schedule, the approver releases tone changes); `ATELIER_ALLOW_INTAKE_ENCODING=true` on
`scheduler` and `intake-worker`. **Key:** the owner's budget for this task is the two keys' credits of 25 October only, so
production was switched to the Client key (`OPENROUTER_API_KEY`, `EMBEDDING_API_KEY`) before any production call; the
internal key was not used. **Next run:** Sunday 1 November 2026, 04:00 America/Chicago (`/schedule` and Home both say so),
window 25 October 04:00 CDT to 1 November 04:00 CST.

**Last week regenerated** (`week_2026-10-18`, cycle `run_c33de7caf2cd43da8c91c9ab07895e20`, window 18 October 09:00 UTC to
25 October 09:00 UTC; eight calls: four internal meetings on 19 October, the LeadLock sync and a prospect consult on 21
October, a new client's kickoff on 22 October, a client strategy call on 23 October; the tax call excluded as WIA's private
matter). Five cards; the delegated Gate 1 (`proof/prod/gate1-*.json`):

| Card | Decision |
| --- | --- |
| WARM, an owner's judgment in keyword decisions (a venue strategy call) | Developed after a reframe answering the verifier's overclaim flag: Carmen paused a routine exclusion list ("cheap", "inexpensive", "low cost") over the venue's own "affordable" |
| CONVERT, a venue's in-house ads handoff (a prospect consult) | Developed after two edits answering three flags (his part-time role, no season, no invented reason) |
| WARM, carrying feedback into the next campaign (internal) | Skipped, evidence (a blocking flag: the owner's feedback is not in the scene) |
| ATTRACT, AI guidance (internal) | Skipped, evidence (two blocking flags) |
| WARM, an owner's sales conversations (a photographer's kickoff) | Skipped, distinctiveness (a plan, not a practice; the surprise test fails) |

Both briefs had a blocking finding (a direct quotation, the owner's in one and Whitney's own in the other, from calls not
cleared for public use) and the same repetition as the benchmark's; one refresh each with the team's notes
(`refresh-prod-*.txt`) fixed both, with the advertising reason stated once (an exclusion list decides which searches the
ads never show for) and seven-slide carousels. Gate 2 through the API (`gate2_api.py`; the database route over a proxy timed
out on its settings read and was stopped before it wrote anything), then the packs:

| Pack | Reading |
| --- | --- |
| Affordable without being cheap (WARM, `pack_aa3440be`) | Rubric 4: Whitney's register ("A little backstory for you", "honestly, that's the part I love"), the exclusion list explained in plain words, the three words named, no outcome claimed. Edits: Reel 3's cover names Google Ads (the first-touch check), three sentences the siblings shared said differently, one clipped closing line. Ready to publish |
| The in-house handoff (CONVERT, `pack_c2b0eb5b`) | Rubric 4: the in-house question leads, his role exact, the offer as the offer sheet words it (six months of guided support). Edits: a frequency claim the call does not show ("every day"), two shared lines. Ready to publish; Reel 1 still shares a few phrases with its siblings (warnings) |

Proofs: `proof/prod/week-2026-10-18.*`, `proof/prod/week-2026-10-18-packs.md`. `week_2026-10-20` (N5's three cards of 21 to
23 October, before v9) is archived.

**The drills (6.X4)**, all during the regeneration:

| Drill | What happened |
| --- | --- |
| Redis flushed (18:51:14) while the cycle's extraction ran and three jobs waited | The extraction finished at 18:55:09 and the strategist step was dispatched at 18:55:10 from the database; nothing lost, no person |
| `editorial-worker` restarted (19:11:16) mid-brief | Card 2's research step had a paid call in flight: the job failed with "the worker stopped ... a model call whose answer was not saved ... not run again by itself" and a `job_failed` alert; card 1's writing finished on the restarted worker. One explicit retry; the alert cleared |
| A cap below the next call | Card 1's brief check and the upkeep's extraction waited on their caps (`budget_refused` alerts, warnings); raising the caps released both within a minute and the alerts cleared by themselves |
| No web provider is wired (`briefs/external.py` unused) | Not applicable |

**Found on production and fixed the same evening:** the hourly upkeep treated a used-up weekly budget as a failed hour (an
error alert every pass; #29), and a deploy's restart left the upkeep's embedding job waiting for a person (#31); a
transient provider failure on one brief check was retried by hand (it is a person's run, so the system does not resend it).

**Spend:** production USD 5.34 tonight (the cycle and card checks about 1.0, two briefs with their retry about 1.6, two
refreshes about 0.8, two packs about 1.3, the upkeep's extraction and embedding about 0.1); with the benchmark's USD 6.64,
USD 11.97 of the Client key's USD 16.17. Left: Client USD 4.20, internal USD 0.74 (untouched). The standing caps from 26
October total USD 4.20 so the Sunday run and the upkeep always fit (DEPLOYMENT.md, "What is deployed today").

## The screens, realigned with the mockup (the owner, 25 October; PRs #32, #33)

The owner found the app "leaps and bounds different from the mockup UI we presented to the client" and overloaded with
technical detail. The reference is the demo build WIA was walked through on 20 October (`b02c54d`, served locally beside the
real app); both were screenshotted at 1440 px and compared screen by screen (desktop only, the owner's instruction). The
realignment reuses the mockup's own components (`frontend/src/mock/`):

| Screen | Before | After |
| --- | --- | --- |
| Navigation | Seven items in one list; `/` opened the Weekly Studio | The mockup's four (Home, Weekly Studio, Previous Concepts, Content Packs); Sources, Moments, Knowledge and Settings in a quiet Administration group; `/` opens Home |
| Home | A plain list | "Good morning, {name}", the gold line, Flag idea, the week's summary in plain lines with links; the calendar when switched on (left off: nothing places pack pieces on it yet) |
| Weekly Studio | Three tabs, then cycles, budgets in USD, scene counts and every card field stacked (an 18,500 px page) | The mockup's header with one Download review control, the four-step stepper, Awaiting approval and Approved as two-column cards with the topic and editorial rationale panel, Review angle (the full card screen in the mockup's dialog) and Approve & create brief; cycles, budgets, Run cycle and seeds folded into Cycle details |
| Content Briefing | The full Gate 2 form | The mockup's brief cards; Read full brief opens the whole Gate 2 screen; Approve & generate pack only when nothing blocks |
| Content Packs | "No open findings · 5 before-publishing notes open · 0/5 published" | "Content Packs & Deliverable Scripts", plain status words; model, profile and run ids under Details for approvers and admins |
| Previous Concepts | (none) | Earlier weeks ("October · Week 2") in the same cards |

Every function stays reachable; the checks pass (483 unit, 85 server, Playwright on the new flow). Left as is: text the model
wrote into stored records still carries a few internal labels ("rank 4", "B5") inside folded sections.

### Older content on production

| Week | What | Decision |
| --- | --- | --- |
| `week_2026-10-12` (calls of 12 to 18 October) | 10 cards, 4 briefs approved under delegation, 4 packs in review | **Kept.** Every pack is publishable after a light edit (rubric 3): plain titles, first-touch lines that name their subject, no insider terms, the right CTAs. Notes for WIA's review: Pack 2's email closes a paragraph on "Both can be true in the same conversation" (a kicker); Pack 3's b-roll screen names Whitney in the third person |
| `week_2026-06-01`, `week_2026-06-08` | Diagnostic cards of 8 to 13 October (before strategist v7) | **Archived** (`weeks archive`): the batch WIA rated 1 of 5, kept as the record and out of the app's lists |
| `week_2026-10-20` | Three cards from the calls of 21 to 23 October (N5's cycle) | **Archived** (25 October), replaced by `week_2026-10-18` |

### 2.B11's remainder: archive-wide search by paraphrase (copy D)

N8 measured the Funktastic chain's search on production, where no scene had ever been embedded: across the archive only one
of five golden scenes ranked in the top 25. Embedding every current scene on copy D (2,383 of 2,479, USD 0.01; the rest have
no searchable text) and searching again (`proof/funktastic-search-copy-d-embedded*.json`):

| Search | Before (N8, copy D) | After |
| --- | --- | --- |
| Across the archive, top 10 | 1 of 5 | 2 of 5 (f01 and f03 at rank 1, both as scenes found by meaning) |
| Within the account, top 10 | 4 of 5 (production) | 3 of 5 (f05 moved to rank 16 as scenes join the fused list) |

The hourly upkeep now embeds every new scene (`upkeep.py`), and production's archive is embedded on deployment. The fifth
golden scene (Whitney's summary of the system working end to end) is still not a scene in any extraction: an extraction
limit, recorded, not a search defect.

### E.B18: what the strategist reads (no paid run)

The question was whether the strategist should read whole calls or per-call summaries beside the scenes, measured against
the moments Whitney's ChatGPT work found for Week 2. Only nine of its eighteen catalogued moments survive (as fragments,
`research/week2-packs-rebuild-2026-10-21/notes/chatgpt_export_week2_findings.md`, A.3). Against strategist v9's Week 2
output (cards, considered ideas and internal insights, `proof/week2-v9.week.json`), every one of the nine reached the
strategist and was placed in a lane:

| ChatGPT's moment | Where v9 put it |
| --- | --- |
| Helping owners decide what kind of support they need | Considered (held: it would argue against the audits being delivered) |
| The market-research survey idea | Internal insight (the tool was still being explored) and a considered idea |
| The route someone takes after clicking an ad | Considered (a routine check; fails the surprise test) |
| Campaign activity against booking progress | Internal insight (v8 made it a card) |
| Working through problems in office hours | Internal (the office-hours account is never named, N8) |
| The venue conversation about what happens after an inquiry | Card 2 (v8: card 1) |
| The prospect whose ads work but wants a partner | Considered (the same audit reason) |
| The channel comparison whose numbers need checking | Internal insight (estimates, not measurements) |
| The AI widget discussion | Card 4 |

Nine of nine: the verified scenes of the whole calls carry what a person found. **Decision: the strategist keeps reading
scenes**; whole calls or summaries would add tokens for no recall.

### The rest of N11, decided

| Item | Decision |
| --- | --- |
| Re-extraction of Weeks 1 and 2; strategist smoke runs; the full gate (E.X4) | Replaced by this benchmark (the owner's smaller option): both weeks extracted under scene profile v4, cycles under v8 and v9 |
| Benchmark v2 rebuilt with the October packet | Not needed: the October weeks are live production weeks, read as such (`week_2026-10-12` above, last week below) |
| E.X8, blind comparison with Whitney's finished pieces | Done as the agent's reading (above); no judge |
| E.B3's paid judge run, the E.B3 and E.X7 extensions (a judge scoring packs on anchors), E.B24's caption-framework model check | Dropped: the owner ruled out any LLM judge (25 October). The anchors (Whitney's 13 October lines) are the reading's checklist instead |
| L.B2's extension (the ChatGPT export read again), 6.B16, 6.B17 | Out: calls only (the owner, 25 October) |
| E.B5 and 3.B4 (a separate scoring call) | Closed: R43 adopts it only on evidence that it predicts WIA's choices, and there are no live dispositions to test it on |
| E.B8 (model choices on held-out data) | Recorded on the evidence already held: extraction on Luna (N1, N2, N8 shakedowns and readings), the strategist and writer on Sol (benchmark v1, N2, N8, this benchmark), card verification, brief review and the pack check on Sonnet (another family than the writer, R42), the pack finisher on Opus (the packs plan's probe, NP). No change |
| 6.C4 | Done (Command Center PR #5) |
