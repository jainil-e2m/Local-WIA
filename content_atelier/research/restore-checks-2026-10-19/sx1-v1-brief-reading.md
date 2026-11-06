# S.X1: the team's reading of the two v1 briefs (19 October 2026)

Read by the implementing engineer under D12 (R55: a delegated review, not WIA's label), against brief standard 2.4a and the
contract of section 4.5. The briefs are the developer's two real v1 runs, restored from the handover: Week 1
(`brief_f4778b68…`, "Give distinct wedding markets distinct landing-page context", run `brief_run_76d191eb…`) and Week 2
(`brief_2ff7b35b…`, "Reviews and buying research answer different questions", run `brief_run_c9d93e21…`). Their exports are
in the handover's artifacts (`brief-runs/<run>/exports/`). Brief v2 (E.B15) and writer v3 (E.B22) were built before this
reading, so the findings feed what is still open: brief contract v3 (E.B23), stance and experience (E.B26) and the
knowledge base's shape (E.B25).

## Against standard 2.4a

| Item | Week 1 | Week 2 |
| --- | --- | --- |
| (a) Refine, don't replace | Met: argument, audience, reader decision and CTA are the approved card's (the deterministic check agrees). | Met, except "Reader decision: Not supplied", which the card lacked too. |
| (b) WIA perspective first | **Not met.** The scene is WIA's Google Ads lead (Carmen) asking a client whether to focus on Orlando first, which is WIA's working judgement; the brief retells it as the client's report and teaches generic "page context" with no "we". | **Partly.** Whitney's own proposal (post-booking buying-research surveys) is the subject, but it is handled as a third party's uncleared words ("the transcript-labelled Whitney"), so WIA's founder cannot say it in her own voice. |
| (c) One complete argument | Partly: hook, problem, main point and decision are directed; the transformation is "a clearer scope decision"; the approved CTA ("Match the landing page per venue…") belongs to a different argument, so the brief needs a "venue bridge" and labels it untested everywhere. | Partly: the argument is clear; no reader decision; the transformation is "clearer understanding". |
| (d) Every format in the channel set | **Not met.** Email, an 8-slide carousel and three Reels are directions, not copy; no caption, no Reel cover text. | **Not met**, the same. |
| (e) Distinct openings and CTAs | Openings differ across the Reels; one CTA everywhere (the approved one, a person's choice). | Same. |
| (f) Credit and grounding | **Not met.** Carmen's question is credited to the client; beliefs cite no knowledge-base document. | Partly: Whitney is credited, but as "transcript-labelled"; a former employee's agreement (C4) is used as support. |
| (g) Clean public copy | **Not met.** Caveats sit inside every deliverable: "untested", "conditional inference", "keep the venue-level caveat adjacent to the exact CTA in every standalone deliverable". | **Not met**: "potentially useful", "remain unestablished", "only after clearance" run through the email, carousel and Reels. |
| (h) No one named who shouldn't be | Met in the public directions (names and markets excluded). | **At risk**: claim C4 names a former staff member (Fallon, who left on 14 August 2026, section 1.8 X6); a writer building copy from the claims could name her. |

Overall (engineer's 2.4a score, delegated): Week 1 **2 of 5**, Week 2 **2 of 5**. Neither is publishable without rewriting:
the useful, specific substance (the Ads lead's scope question; a founder's buying-research proposal) is buried under evidence
handling, and the deliverables are instructions to a writer.

## Against the contract (section 4.5)

- **Rigour inside the copy.** v1 has no ledger beside the copy: qualifications, consent and permission notes are written
  into the claims, the narrative and every format's direction. R54 (rigour beside the copy) and writer v3 answer it for v2;
  E.B23's separate ledger step should finish it.
- **Statuses carry handling notes.** "reported; private; excluded from public deliverables", "Planned proposal; public
  reuse not cleared": the claim status mixes what the source supports with what may be published. The six-value status
  (S.B4) and the ledger's separate handling field are the right split; keep them apart in contract v3.
- **WIA's own people treated as uncleared sources.** A WIA team member's words from WIA's own call (Whitney's proposal,
  Carmen's question) were handled with the same public-use clearance as a client's. Their attributed first-person
  experience is WIA's to say: E.B26's rule (attributed experience, never a prevalence claim) should cover the brief writer
  and its verifier as well as the strategist.
- **No caption, no cover text, no anchor piece.** The format plan needs pieces with a job and finished copy (E.B23: anchor
  piece, caption body, piece keys).
- **Distinctiveness came too late.** Week 2's own similarity review says it repeats the prior buying-research angle and
  WIA's 10 June email at the argument level, after the brief was paid for. The check belongs before Gate 1 on twelve months
  of published central points (E.B25 f, 3.B5).

## What carries into the open items

1. E.B23: claims ledger in its own step; `evidence_ids` off the copy pieces; caption body and cover text; reader decision
   optional; repair may never add qualifiers to copy.
2. E.B26: a WIA team member's attributed observation is experience, not an unverified claim, for writer and verifier too.
3. E.B25 (f): the distinctiveness check must see the 10 June email before a card is approved.
4. E.B24 already blocks former staff in public copy (2.4a h); claims should also stop citing former staff as support for a
   current position.
