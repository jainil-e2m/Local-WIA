# Scene profile v2: a person's read of 10 documents (2.B11, D21)

Read on 19 October 2026 by the implementing engineer, under D21 (recorded as delegated, R55), on the restored working copy
(stamp `kenil-2026-10-19b`, run `docext_665ba0687c44bfa2d90d57c0`). Each document was read against its transcript: every
scene's quote, setup, proposition (the WIA moves and the client's contribution), qualifications, speaker and consent.

## The documents

Chosen to probe the likely weak spots (sparse, dense, short, long, every call type), not the golden documents.

| Document | Call type | Characters | Scenes (verified) | Read |
|---|---|---|---|---|
| `transcript_3627bcca0f0c045eeca4a2db` | client 1:1 (a rescheduled demo) | 3,771 | 2 (2) | full |
| `transcript_54a846b353fbfcbab21dd6f2` | client 1:1 (account access) | 12,548 | 2 (2) | full |
| `transcript_85e5d10cbfd86810ee8c6f45` | client 1:1 (check-in) | 21,048 | 21 (20) | full |
| `transcript_277479bc9ea2cdac3a218e55` | client 1:1 (monthly strategy) | 33,393 | 8 (8) | full |
| `transcript_4d21ee64c0f57b78e0a7b1a1` | office hours | 35,076 | 11 (11) | scenes, figures checked against the text |
| `transcript_cd7d2add20a12a234b883e14` | prospect | 39,364 | 13 (13) | scenes, closing turns |
| `transcript_c328d038511e56ca517e9724` | workshop (WIA's UVP method) | 28,280 | 14 (11) | scenes, unverified quotes traced |
| `transcript_9143cef8d30d0b34d5458ed1` | workshop with an outside presenter | 106,247 | 13 (13) | scenes, coverage by position |
| `transcript_d4b98119727bd29437c8e71a` | prospect | 65,377 | 33 (28) | scenes |
| `transcript_e55fb5bf35dc6e9b7292b0fa` | client 1:1 and a staff working session | 135,642 | 16 (16) | scenes, the two largest gaps sampled |

## Verdict

**Faithful; fit to be the per-document default.** No invented fact, outcome or attribution was found. Propositions keep a
WIA person's moves apart from the client's contribution, and the qualifications say when a figure is an estimate, a
recommendation or a characterisation. Speakers are right even where the source's diarisation is wrong (the check-in labels
several of Whitney's lines as the client's, and the scenes attribute them correctly). Consent follows the call type: every
prospect scene and every client figure is `internal_only`. Sparse documents are sparse for a reason (an account-access
call, a rescheduled demo); the long gaps are screen-share clicking or an outside presenter's talk.

## Defects found

1. **Private talk recorded as a scene.** The rescheduled demo's first scene is Whitney speaking to her child before the client
   joined, recorded as a staff `tension`. A scene profile should skip personal and household talk that is not part of the call.
2. **The client's line chosen as the quote where WIA's line carries the substance** (the access call; the check-in's local
   families). This is the v3 recommendation already in E.B12: prefer WIA's line, anchor both turns.
3. **A quote stitched across two consecutive turns of one speaker stays unverified** (the workshop's "if this would make sense
   on 100 competitors' websites, then it's too generic", split by the source as "So, if." / "this would make sense…"). This is
   golden scene g01's failure; a repair that binds a quote across adjacent turns of the same speaker would recover it.
4. **Short quotes stay unverified by design.** A quote under six words (`REBIND_MIN_WORDS`) is not re-anchored even when it is
   verbatim in one turn ("Thankfully, August picked up."). Kept: short generic lines are where a wrong rebind is likeliest.
5. **The stored ledger predates the current repair rules.** Replaying all 91 saved responses under today's code (no provider
   call) binds 1,605 of 1,669 scenes (96.2%) against the 1,571 stored (94.1%), across 27 documents; the 27 documents were
   re-partitioned from the saved responses on 20 October (USD 0): 1,605 verified, 64 unverified records, recall unchanged.
6. **One duplicated scene** (the same prospect question recorded twice, consecutive scenes).
7. **The number check confirms a figure is present, not that it is right.** Whitney's "70% decrease" for a cost per lead that
   fell from about $70 to $27 (61%) passes; the scene is `internal_only`, so it cannot reach public copy, and the brief's
   verifier still checks figures. Most of the 31 number-check failures are figures from the scene's context rather than its
   anchor, or transcription slips the extractor normalised ("$19.97" for $1,997): flagged, as designed.
8. **No slot for an outside presenter.** A guest's teaching appears only in the setup, so about 40% of the guest workshop yields
   no scene. Accepted: it is not WIA's thinking and must not be attributed to WIA.

## For a scene profile v3 (with E.B12's recommendations)

Skip personal talk; prefer WIA's line as the quote and anchor both turns; allow a quote across adjacent turns of one speaker;
one scene per exchange (no duplicates); keep the reason a WIA person gave; a move for WIA challenging a client's assumption.
