# E.B24's warnings decided (Phase N6, 25 October 2026)

Plan section 5.0b asks, for every E.B24 check that still only warns: block, on evidence, or stay a warning by decision,
recorded per check. There are no WIA live weeks yet; the evidence is WIA's own corrections (13 and 20 October, plan section
3.2) and her reactions in her ChatGPT work. Decided by the implementing agent under the delegation (D12, R55).

The rule used: a check blocks when it is one of WIA's house rules, stated as a pattern that needs no reading (so a
blocking finding is never a false alarm a person has to argue with), or when she gave the same correction twice. A blocking
finding at Gate 2 asks the reviewer to fix the line before approving; in a pack it goes to the finisher's repair, like
every blocking finding, so the system fixes it by itself. Everything that needs a person's reading stays a warning.

| Check | Decision | Why |
| --- | --- | --- |
| `first_touch.subject` | **Blocks** on the subject sent first; warns on the other options | W3 ("not a subject line that I would use") repeats her 13 October note; the first option is the one sent |
| `first_touch.specific` (covers, on-screen hooks, the first b-roll screen) | **Blocks** | W5, W7 and W8 in one review: "make it more about ads", "did I set my ads up wrong?" |
| `first_touch.slide_one` | **Blocks** on a bare quote or a slide 1 that drops the title's subject; warns on the good-news order | W4 ("slide one is so ambiguous") repeats 13 October ("punchier slide 1") |
| `first_touch.insider_term`, not explained | Warning | Whether a sentence explains a term is a reading. The term in first-touch text and more than once in a body already block |
| `format.email_bullets` | **Blocks** | Her email standard: short flowing paragraphs, no bullet list |
| `format.caption_signoff` | **Blocks** | "-Whitney" on every first-person caption |
| `format.offer_descriptor` (an offer named without its approved descriptor on a CONVERT asset) | **Blocks**; an empty or unknown `offer_descriptor` field stays a warning | Offers are always named with their approved descriptors (section 4.3) |
| `copy.never_used_cta` | **Blocks** | A CTA pattern she never uses ("follow along") |
| `format.send_header` | Warning | A proposal WIA confirms when scheduling |
| `format.carousel_cta` (both readers) | Warning | Matching a paraphrase of the two readers is a reading |
| `format.register`, `format.reels` | Warning | Register is a reading; a two-Reel brief is allowed (D30) |
| `copy.self_audit`, `copy.takeaway`, `copy.diy_drift`, `copy.kicker`, `copy.detail_density`, `copy.sibling_overlap` | Warning | Each needs a reading; the finisher and the reviewer act on them |
| `copy.hook_fidelity`, how much of a call something took | Warning | A person checks it against the call (the tool and who-decided mismatches already block) |
| `week.offer_cta`, `week.covers` | Warning | Across the week's briefs; the week's plan resolves them |
| Pack: `pack.format`, `pack.us_spelling`, `pack.client_quote_listed`, `week.offer_cta`, `week.distinct`, `week.emoji`, `week.central_point` | Warning | Format counts and week-level variety are readings or notes; the client-quote list is a note, never a gate |
| Pack: `pack.quote_exact`, `pack.quote_attributed`, `pack.new_number`, `pack.new_name` on a line a person wrote | Warning | A person's own line is checked by that person (they block on system lines) |
| Validation: caveat language, knowledge-base rules marked as flags, a wrong pronoun beside a named person | Warning | Readings; "they" is never flagged |

Code: `backend_pipeline/briefs/first_touch.py`, `backend_pipeline/briefs/asset_checks.py`; tests:
`test_first_touch.py::test_e_b24_decided_the_subject_the_cover_and_slide_one_block_where_wia_corrected_them_twice`,
`test_asset_checks.py::test_e_b24_decided_the_house_rules_block_and_the_readings_stay_warnings`.
