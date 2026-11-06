# N8: evidence and account memory (25 October 2026)

This records Phase N8, done unattended on the owner's instruction (full permissions from the WIA team; decisions under
the delegation, D12, D21, R55). Times are UTC. Every review and reading here was made by the implementing agent under
delegation; none is WIA's.

**Run authority (the owner).** Production go-ahead for merging, deployments, `settings apply`, the identity and
classification changes, the standing caps and the extraction of the internal meetings; self-merge after CI; the OpenRouter
limit is what both keys had left (Client USD 5.44, internal USD 1.45 until Monday's renewal). No Railway billing change.

## What was built

| Item | What | Commits |
| --- | --- | --- |
| 1.B12 (extension) | Identities: people and accounts with every spelling the records use (a meeting handle, a nickname, a device label, a mis-heard transcription), pronouns from evidence, a former team member's leaving date, and two flags no consent overrides (never name; never link to a named piece of published work, with its markers). `storage_cli identities import / apply / show`; a client or prospect identity takes the call's role. Strategist v8 reads the identities frozen with its cycle, writer v5.2 those frozen with its brief; the card, brief and pack checks block a never-named identity, or a never-link marker in copy that names the identity or is built on its calls, and warn on a wrong pronoun beside a named person | `ff29b40`, `f762030`, `95f1370` |
| 1.B13 (extension) | Internal meetings as team practice (D24): `documents team-practice` admits the internal meetings excluded only for being internal; their scenes are team practice (`key_moments.evidence_class`); scene profile v4 records how the team works (the `team_practice` type, no client contribution, client names and figures only where the scene needs them); strategist v8 gives them their own handling line; the checks block a client name or figure only an internal meeting carries | `ff29b40`, `f762030`, `95f4977` |
| 3.B17 | Account memory (D25): an account's dated timeline from its calls, its internal meetings, published content and WIA's sent emails in the context store, never a model's memory (`accounts.py`). Gate 1 and Gate 2 show the account beside a client story card (naming, calls on record, the last call, what happened after the card's call, internal remarks apart); writer v5.2 gets "what happened next" as evidence items the claim ledger binds, each flagged for the client's okay | `f762030`, `0125d99` |
| L.B13 | Founder notes (D29): a seed of kind `founder_note` linked to its call (migration 010), entered in the seed form with the call chosen from the last three weeks; strategist v8 reads it with the call named as the scenes name it; the cycle's selection and the week's review document show each note used in a card, paired, or unanswered | `ff29b40`, `f762030`, `0125d99`, `95f1370` |
| 1.B11 | The Zoom transcripts dated: the backfill's week folders (filed by recording time) are a window; a spoken cue of the day or a recording-list event unique in that week dates the call, otherwise it is dated to its week, with what supports each date in `transcripts.date_evidence` | `e7a2390` (subagent) |
| 2.B11 | The Funktastic chain: its golden scenes (`research/golden-scenes/funktastic-chain.json`) marked from the published pieces, recall measured per extractor and search by paraphrase (`golden_search.py`) | `95f4977` |

## The reviewed identities (`identities.json`)

Drafted by a subagent from the transcripts, the Week 2 research notes and the Slack-derived notes, every identity with its
evidence, then reviewed (delegated, D21): 30 accounts (24 active, 2 former, 4 prospect-only), 61 client, prospect and outside
people (43 with pronouns, each from a quote), and staff dates and pronouns for four roster members (Fallon Looney left on
14 August 2026). The review's own changes:

- A device label more than one person speaks through ("judy", "Scott & Krista", "The Organic Moment Photo + Video", "Dos
  Palomas Ranch", "The Weinberg At Wixon Valley") names the account, never a person.
- Aliases that collide or are other people's names were left out ("Jill" on two people, "Brittany" on Brittanie Pate,
  "Katie", "Matt", "Mike", "Jen" and similar), so a label never resolves to the wrong person.
- An outside person who works with an account (Brooke Jenkins of Sage Haus) is not tied to it; Tirzah Caffee, already on the
  roster, gets the transcripts' device label added to her roster row.
- Carroll Hall and Erin Smith: never named, and never linked to the anonymised $22K-to-$70K Accelerator case study
  (markers: its figures and phrases). Noam Wolf is she/her. "aliepler", "Allie" and "Ali" are Ali Epler of Diamond A
  Ranch; "iver" is Ivor; Felipe Cortes is kept apart from the earlier Felipe Luna.
- Two calls the review found are not WIA's work were excluded as `other` (delegated, D21): the 14 October call in Carmen's
  series with a Reno esthetics studio (facials and waxing throughout; the rest of the series was already excluded) and a
  call with a freelance media buyer about her own e-commerce client.

## Copy C: production's dump on migration 010 (the free-model shakedown)

Production's database was dumped at 07:34 (52.7 MB) through a temporary TCP proxy, deleted straight after, and restored
twice: copy C (`atelier_np_c`, free models) and copy D (`atelier_np_d`, the paid proofs). Both migrated to 010 cleanly.

| Step | Result |
| --- | --- |
| Identities | 30 accounts and 61 people created, one roster row updated, four staff rows; `identities apply` re-normalised 114 documents with no model call (25 seconds): 75 calls now tied to their account, 1,371 of 1,862 current scenes carry their client, and consent follows the account (anonymise) |
| Dating | All 164 Zoom transcripts dated: 63 to the day (59 from Zoom's recording list, 4 from a calendar export, all applied on production before N8) and 101 to their week folder, each with its window in `date_evidence`. The hello@ account's list dated one more call (1 October, unique in its week) |
| Team practice | 63 internal meetings admitted; 16 exclusions kept with their reasons (a non-wedding business, personal chatter, a partner's debrief, a test call) |
| Scene profile v4 (free model) | Four internal meetings extracted: their scenes are team practice; the Week 2 meeting's new survey service and its test of the chat widget on WIA's own account came through as `team_practice` scenes |
| Week 2 cycle, strategist v8 (free model) | Ten calls (the eleventh, 135,642 characters, timed out on the free endpoint), 87 scenes sent, two cards; the account panel beside the client story card (Sunny Entertainment: anonymise, two calls, 22 entries after the card's call); the stand-in founder note on the Diamond A call shown unanswered |

### Found and fixed on the way (each with a test that fails without the fix)

1. **A weekly run's partial failure marked every document failed** (`95f4977`): one free model's timeout on one call marked
   all eleven calls of the week failed, though ten had their scenes saved. Now a saved document stays `completed`.
2. **A card still on an internal-only scene after its one repair failed the whole cycle** (`95f4977`): under strategist v8
   such a card becomes an internal insight, recorded as `demoted_internal_cards`; v7 is unchanged.
3. **A founder note named its call by the document's title** (`95f1370`): the free strategist read it as another call. The
   note now names its call exactly as the scenes name their recording.
4. **A wrong pronoun went unnoticed** (`95f1370`): the free strategist wrote "him" for a prospect recorded as she/her, in a
   card's guardrail the writer reads. A sentence naming a person with recorded pronouns and using another set is now a check
   on the card and a warning in public copy ("they" is never flagged).

Not a defect: the free endpoint's 504 on a 135,642-character call (free-tier artefact, K70).
5. **Account memory's later records made a brief's research request too large** (`01fba86`, copy D, paid): every context
   passage of twelve later scenes (182 evidence items) went over the 120,000-character preflight. What happened next is now at
   most eight later records, what was built or measured first, each by its anchor passages.
6. **A week-dated account entry showed the day before its folder week** (`d96e919`): the window's start, converted to UTC.
7. **An internal meeting's scene was not linked to its account** (`7814344`, copy D): scene profile v4 keeps client names
   out of the record (D24), so the record alone linked one of twenty-five meetings. The scene's anchor passages are read,
   a scene naming another account as well is not linked, and short first names ("Ali") are not used.

## Copy D: the paid proofs (the Client key; production's models)

Copy D carried the same identities, dates, exclusions and team-practice admission as copy C, the candidate configuration
(`candidate-settings.json`: strategist v8, scene profile v4, writer v5.2, internal meetings included), the re-headed chunks
re-embedded (2,305 chunks, USD 0.03), and copy D's caps raised for the proofs.

**The Week 2 cycle under strategist v8** (11 calls with the six internal meetings; scene profile v4 on Luna, USD 0.15;
strategist 0.61; card verification 0.25): 174 verified scenes, five cards. Reading (delegated, R55): **pass.**

| Card | What it shows |
| --- | --- |
| 1. How we use the time before a venue tour | The Diamond A story (Week 2's venue account). Its account panel at Gate 1: Diamond A Ranch, anonymise, two calls on record, the last in the week of 31 August, 18 records after the card's call. The guardrail anonymises the venue and owner and keeps "the video idea came from her". The stand-in founder note on that call was paired with three of its scenes ("rank 1 develops that moment") |
| 2. How we decide whether a new AI tool belongs in our work | A team-practice card from the Week 2 internal meeting about the chat widget (WIA's own account tried first). Guardrail: "From an internal meeting: show the practice, no client detail or internal quotations" |
| 3. How we learn what already works before planning your ads | A prospect call; "anonymise the owner and use no guessed pronouns" (the identity records hold none for him) |
| 4. How we decide what counts as follow-up progress | A second team-practice card; held by the point test (a tactic) |
| 5. How local knowledge shapes our keyword research | The Penny's call; its account panel (four calls, 34 later records); "credit our team rather than Whitney or a former team member as current" |

The account review and the survey service of the Week 2 internal meetings reached the strategist as team-practice scenes
(internal insights cite "the account-review excerpts"). No card names Carroll Hall or Erin, and the review document of the
week carries the founder-note line: "in 'How we use the time before a venue tour'" (`proof/d-week2-review.md`).

**Writer v5.2 on card 1** (`proof/d-brief-v52.json`, then `d-brief-v52-second.json` after the internal meetings that discuss
the account were extracted, USD 0.31): the brief is ready for Gate 2 with only Gate 2's own steps as blockers. The venue
owner is anonymised and "she"; the former strategist on the June call is credited as "our team"; the later records reached
the writer as evidence with their dates and sources, and the brief keeps the story at recommendation stage because, as its
before-publishing item says, "the later records do not establish that this proposed email was built or produced results".
That is right on the database's evidence: the record that shows the June recommendation built (the 9 September internal
meeting in the Week 2 research notes) is not in the corpus. Reading: **pass**, with that remainder for 3.B17.

**The Funktastic chain (2.B11)** on copy D: the golden scenes' recall per extractor (`proof/funktastic-recall-copy-d.json`):
scenes v1 4 of 5, v2 4 of 5, v4 3 of 5; the fifth (Whitney's summary of the system working end to end) is not a scene in any
extraction, though v2 records the same beat in the client's words. Search by paraphrase (`proof/funktastic-search-copy-d.json`):
across the whole archive only the 17-to-90 result ranks in the top 25; filtered to the Funktastic account, which only the
N8 identities make possible, four of five rank in the top 10 (the Instagram line does not).

The screens on copy D (signed in through a development Command Center): the account panel at Gate 1 at 1024 px and at a
375 px phone width (no horizontal scroll); the founder-note kind in the seed form is unit-tested.

## Production (25 October)

PR #26 merged at `cb3ecc9`; the newest deployment of all seven services approved (the api first, so migration 010 ran
before the others); every service SUCCESS. Then, through a temporary TCP proxy with production's variables minus every
`ATELIER_ALLOW_*` switch (a switch passed for one command only where it queued paid work), in this order:

| Step | Result |
| --- | --- |
| Identities | `identities import`: 30 accounts, 61 people, one roster row updated, four staff rows. `identities apply` over the proxy ran one document a minute or more (every query a round trip), so after 10 documents the rest went to production's workers: `documents normalise --ids` for the 97 its estimate showed with no classification call (done in about five minutes), and the 7 a queued job would have asked the classification model about through `identities apply`'s path (their call types kept). A second dry run lists nothing left. 75 calls tied to their account; 1,354 of 1,827 current scenes carry their client |
| Two calls excluded | The Reno esthetics call and the media buyer's call, `other` and excluded with the review's reasons (delegated, D21) |
| Dating | `documents dates --zoom-listing ... --apply`: one more call dated to the day (1 October); all 164 Zoom transcripts dated, 63 to the day and 101 to their week folder (`date_evidence`); the 29 Fathom calls and the one file were already dated |
| Configuration | `settings apply --file deploy/production-settings.json`: exactly five rows changed (strategist v8, scene profile v4 for both keys, writer v5.2, `internal` in the included call types); 25 unchanged |
| Team practice | 63 internal meetings admitted (814 chunks added); 18 stay excluded with their reasons (16 earlier, the two above) |
| Re-embedding | 2,305 re-headed chunks queued live (estimate USD 0.03; spent USD 0.031 on the embedding cap); 21 jobs done by production's workers |
| Extraction | The 63 internal meetings and the Funktastic call under scene profile v4 (estimate USD 0.31), the extraction cap raised for it from USD 0.4 to 1.2 and restored after. Production's bulk worker and five inline workers sharing its queue (the claim takes a row lock and a lease) finished all 64 in about an hour: USD 0.68 on the internal key. 930 current scenes on 59 meetings (four gave none), every one team practice (`evidence_class`), 655 of the `team_practice` type |
| Account panels | `repository.review`, what the API serves at Gate 1, for weeks `week_2026-10-20` and `week_2026-10-12` (`proof/production-account-panels.json`): every client story card shows its account (The Brightside, The Penny, Press Record Co., Ridgefield, Carroll Hall), its naming, calls on record, the last call and what happened after the card's call (26 later records for the Brightside card of 15 October) |
| Funktastic recall (2.B11) | `proof/funktastic-recall-production.json`: scenes v1, v2 and v4 each find 4 of 5; the fifth (Whitney's summary relay) is missed by all three |
| Funktastic search (2.B11) | Across the archive, 1 of 5 in the top 25 (the 17-to-90 line, rank 2; `proof/funktastic-search-production.json`); within the Funktastic account, 4 of 5 in the top 10 (ranks 1, 1, 5 and 8; the Instagram line is not; `proof/funktastic-search-production-account.json`). `golden_search.py` takes the account as its fourth argument |

**Found on production and fixed (`records/N8-production`):** a card of 15 October, written before the identities existed,
is about Carroll Hall's search terms and credits "Erin" (never to be named) in its WIA-in-action line and guardrail; its
approved brief of 24 October credits "Erin, a member of the client's team" in the supporting example. None of its three
packs names her in their copy (only an internal before-publishing note does), but the pack checks would not have caught it:
they ran the identity checks only from a writer v5.2 brief's frozen records, and reported only what the pack raised beyond
its brief's approved copy. Now a pack run freezes the identity records when it is queued (`packs.checks.pack_identities`, in
both queues), a run queued earlier reads the current ones, and the never-name and never-link check runs on the pack's own
copy, the brief's included, with no consent, clearance or approval overriding it (`identity_findings`;
`test_n8_units.py::test_a_pack_blocks_a_never_named_person_even_when_its_approved_brief_carried_the_name`, which fails
without the fix). The card and brief themselves stay as approved records; a new cycle or brief on that account is held to
the identities.

**Cost on production for N8:** USD 0.71 on the internal key (extraction 0.68, embedding 0.03, five query embeddings), inside
the standing caps; nothing on the Client key. No Railway billing change; no password set or entered.
