Review the complete supplied packet and return useful evidence moments under the trusted policy. This packet may contain several transcripts. Respect source_id boundaries and chronological ordinal order within each transcript.

## Moment record

Every field is required. Do not use placeholders as values.

- local_key: unique local label, such as m1. Never invent a permanent source or moment ID.
- anchor_span_ids: existing IDs for the central proposition, unique and in chronological order, all from one source.
- context_span_ids: existing IDs for a contiguous chronological interval in that same source, including every anchor and the setup, resolution and relevant correction/qualification. Choose the smallest sufficient interval, not an arbitrary fixed window or the whole meeting by default.
- quote: an exact, nonempty substring of one anchor's text. Do not fix grammar, paraphrase, add ellipses or stitch separate turns. Put interpretation in separate fields. Additional anchors can support the proposition but do not turn the quote into a fabricated composite.
- context_summary: a compact factual orientation, usually 2–4 sentences, keeping the relevant sequence and what was not established. Speaker labels are labels, not verified founder identity.
- moment_type: one of result, objection, decision, tension, mechanism, observation or story.
- proposition: a bounded statement of what this evidence supports. Preserve proposal/report/estimate status in the wording. Avoid making a broader persuasive claim than the source.
- audience_relevance: identify the recognisable wedding-business state and decision this could help, without assuming all readers are beginners or negligent.
- qualifications: concrete limitations needed downstream. For numbers retain subject, period, measure/unit, denominator or comparison, cost inclusion, attribution and reported versus estimated status where supplied. State meaningful missing information, multiple interventions, human involvement, contradictory evidence, unknown identities/attachments or planned service ownership. Do not infer missing values.
- claim_status: reported, measured, estimated, planned, hypothetical or inferred. A speaker saying “we measured this” without the measurement record is reported. An explicitly hypothetical or planned proposition must not become a result.
- sensitivity: internal_only for explicitly restricted/private-use material, unknown where permissions/handling are absent, or public_candidate only where the packet explicitly supports candidacy. None of these labels is publication approval. Do not reproduce credentials or unnecessary personal details in paraphrases.
- strength: 0–5 for interpretable source substance and editorial usefulness, not expected engagement, revenue potential or founder approval. 0–1 is weak/unresolved, 2 is thin, 3 is usable but limited, 4 is concrete and useful, 5 is unusually clear and rich. Do not retain an uninterpretable central claim merely to meet a count.
- reasons: short, specific explanations of why this is worth considering and what decision-level substance it offers. Do not output hidden reasoning.

## Coverage and exclusions

processed_span_ids must list every supplied span ID exactly once, including greetings and discarded material. It is a coverage acknowledgement, not the selected anchors. coverage_notes records actual exclusions, unresolved meaning, missing referenced attachments or limitations; give source/span references where useful. If moments is empty, explain the absence of usable evidence. Do not add invented IDs, and do not silently return a partial packet as complete.

Return {"moments": [...], "processed_span_ids": [...], "coverage_notes": [...]} and nothing else. The API schema defines the nested field types.

## Calibration illustrations, not current evidence

- A discussion says past spend included agency fees and results could not be attributed. Keep “results unknown”, not “zero bookings” or “wasted spend”. A later attributable-booking figure is not total revenue or profit; preserve each cost basis.
- A capable owner pauses organic posting while paid visibility continues. Keep the earlier competence and remaining system, not “she stopped all marketing” or “never post again”.
- A team plans to add a research service. Extract a planned process decision if useful; do not say the service is already delivered.
- A testimonial says sales feel automatic, then mentions consultations and several interventions. Keep those surrounding qualifications; do not credit one automation with all growth.

These illustrations contain no permissible new facts, quotes or IDs. The only extractable evidence follows.

Source packet:
{{SOURCE_PACKET}}
