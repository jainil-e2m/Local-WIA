Review the complete supplied packet through the trusted WIA strategy. Return source-bound moments with provisional discovery metadata. Several transcripts may be present; preserve source boundaries and chronological order.

## Moment record

Every schema field is required; nullable fields must use null when unavailable.

- local_key: unique response-local label, not a permanent source ID.
- anchor_span_ids: actual, unique, ordered IDs for the central exchange in one source.
- context_span_ids: the smallest sufficient contiguous interval in that source, including all anchors, relevant setup, WIA response, client contribution and qualifications.
- quote: a brief exact substring of ONE anchor. Preserve spelling, capitalization and punctuation. Do not paraphrase, splice turns, add ellipses or correct transcription.
- context_summary: factual orientation to what was asked, explained or proposed, by whom according to the labels, and what remains unresolved. Do not rewrite the exchange as a generic lesson.
- moment_type: result, objection, decision, tension, mechanism, observation or story. Use the closest source-event category; multiple strategic lenses belong in discovery.
- proposition: a bounded statement of what happened or was expressed. Keep reported/proposed status; distinguish it from the broader interpretation.
- audience_relevance: who could care about the transferable concern and why. This is provisional and can be broader than the recorded client. No required next decision or CTA.
- discovery.lenses: one or more unique labels: audience_insight, wia_expertise, service_value, broader_principle. Attention worthiness is assessed separately in attention_reason.
- discovery.destination: public_opportunity, internal_intelligence or research_needed. One exchange may later support several uses; choose its strongest provisional destination without discarding other lenses.
- discovery.wia_contribution: the concrete question, reasoning, recommendation, collaboration or capability visible here; null if this is only audience research. Preserve the client's contribution.
- discovery.attention_reason: the specific stake, question, misconception, contrast or view into work that makes this material worth investigating. Relevance alone is insufficient.
- discovery.research_questions: specific missing details and where to look in supplied context; [] if none. research_needed requires at least one question.
- qualifications: material evidence limitations, including subject, period, units, attribution, estimates, human involvement, proposed implementation, unknown identity and unavailable attachments. Preserve conflicts rather than choose a convenient interpretation.
- claim_status: reported, measured, estimated, planned, hypothetical or inferred. A spoken metric without the underlying measurement is reported.
- sensitivity: internal_only if explicitly restricted, otherwise unknown unless candidacy is explicitly established. It is independent of discovery.destination and never publication approval.
- strength: 0–5 for interpretable source substance and strategic research usefulness, not predicted engagement or human approval. A clear objection can have high research strength even with low public potential.
- reasons: concise source-specific reasons for selection; show the strategic opportunity or research use and its relevant limit.

## Coverage

processed_span_ids must acknowledge every supplied span once, including omitted material. coverage_notes explains significant excluded opportunities, unavailable context or weak interpretations, using valid references. Do not equate delivery coverage with exhaustive strategic recall. An empty moments list requires an explanation. Do not pad to a count or assume one moment per meeting.

Return {"moments": [...], "processed_span_ids": [...], "coverage_notes": [...]} matching the complete supplied schema. The lossless weekly supplement, when present, replaces the span acknowledgement and context-list representation with meeting bounds and context_first_span_id/context_last_span_id.

Source packet:
{{SOURCE_PACKET}}
