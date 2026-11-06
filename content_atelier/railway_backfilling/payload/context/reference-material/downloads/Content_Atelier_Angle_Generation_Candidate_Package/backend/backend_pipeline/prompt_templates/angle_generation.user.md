Generate evidence-grounded strategic editorial opportunities from the supplied current moments. Re-examine the original passages before adopting any upstream proposition or discovery label. Identify the strongest supported interpretation of each useful exchange, not simply the easiest tactical lesson to extract from it. Some moments may yield internal intelligence, a bounded research hypothesis, or no worthwhile public direction.

## Public opportunity record

For each angle draft under the active response contract, supply ALL required keys with their exact types and allowed values. Required nullable keys must appear as null when not supported. The angle fields are a compact editorial proposal, not a finished brief.

First reconstruct the source interaction and ask what was actually revealed: the business/buyer issue, the WIA question or analysis, the client's own contribution, the decision or trade-off, and why this could matter beyond that conversation. Compare at least a literal educational treatment with any credible broader process, positioning, authority, audience-insight or service-value treatment. Select the perspective with the strongest evidence and audience stake; do not force a wider treatment when it would erase the actual case. Preserve multiple treatments only if their central ideas or evidenced contributions materially differ.

- `local_key`: a unique short local identifier within the current response, not a permanent database ID.
- `title`: a clear working description of this particular editorial opportunity; not a polished hook or an instructional heading by default.
- `content_opportunity`: the specific broader idea worth exploring, including what the underlying exchange uniquely illuminates.
- `strategic_purpose`: exactly `ATTRACT`, `WARM` or `CONVERT`. Choose the primary intended strategic role, without a quota.
- `content_type`: exactly one of `opinion`, `founder_forward`, `campaign_breakdown`, `trend`, `uvp`, `thought_shift`, `process`, `behind_the_scenes`, `education`, `founder_story`, `solution_selling`, `social_proof`. The source must support the type, especially trend, founder claims and social proof.
- `strategic_rationale`: why communicating this perspective would help WIA reach suitable owners, earn their trust or make its relevant value understandable. Do not assume every candidate must sell.
- `audience`: which wedding-business owners would care, and about what. The recorded client's profession is not automatically the intended audience; generalize only a transferable issue, not an unproven case claim.
- `core_perspective`: one precise belief, interpretation or demonstrated principle to explore. Do not split the old Argument and Take into redundant statements.
- `tension`: required, nonblank honest reason this matters now to the intended audience: a decision, question, contrast, desire, obstacle, trade-off or uncertainty. It need not be a problem or failure; do not manufacture a crisis.
- `wia_expertise_in_action`: specific evidenced WIA reasoning, question, diagnostic step, recommendation, collaboration or actual work; null where the supplied source does not establish it. Credit the correct team member and the client's contribution. Do not imply completed work from a proposal.
- `service_relevance`: narrowly explain an evidenced WIA service/product connection if useful; otherwise null. Do not invent current scope, features, prices or delivery ownership.
- `reader_decision`: normally null; use a concise actual decision only if it naturally follows from the chosen opportunity. Never invent an immediate action or CTA as a condition of being selected.
- `evidence_readiness`: exactly `supported` or `research_required`. `supported` means the proposed central perspective can be fairly developed with current evidence; it does NOT certify publication approval or an outcome. `research_required` means a substantive source-grounded opportunity is blocked by a specific knowable missing fact.
- `research_questions`: array of exact follow-up questions linked to the missing underlying evidence; use [] when not needed. For `research_required`, supply at least one nonblank question identifying what source, capability, period, outcome, contributor or context must be checked. Do not use this status for a hollow speculation.
- `selection_reason`: the concrete editorial reason to retain this rather than a merely true or relevant topic. Identify the distinctive reasoning, scene, stake, contrast or view into WIA's work, not a predicted engagement score.
- `moment_ids`: nonempty array of unique IDs that exist in this current moment pool and actually substantiate the treatment; do not copy local extraction keys or archived moment IDs.
- `source_assertions`: nonempty array of precise factual statements. EVERY string must begin EXACTLY `[<referenced current moment_id>] ` with the ID belonging to this angle's `moment_ids`, including the trailing space after `]`. Describe who said/did what and the factual status; separate proposed/estimated/reported/measured claims. Do not cite history or trusted policy as current-call evidence, and do not count on the SQL citation adapter to repair default-path output.
- `inference`: null or a carefully bounded editorial interpretation beyond literal facts, clearly distinguished from the source assertions. Missing product capabilities or unobserved results must never be asserted as inference.
- `qualifiers`: array of material limits, missing context, chronology, attribution, estimates, differing interpretations, claim status and implementation boundaries; [] when none. Carry forward all relevant upstream qualifications.
- `risks`: array of concrete privacy, client-identification, consent, evidence, sensitivity and commercial-scope checks; [] if none apparent. An `internal_only` source or unidentified speaker merits careful handling; neither a candidate label nor an anonymized version grants publication permission.
- `quality`: object with numeric `grounding`, `strategic_fit`, `distinctiveness`, `audience_resonance`, `source_strength` and nonempty `reasons`. All scores must be finite values between 0 and 5 inclusive.

## Quality anchors

0 = absent or contradicted; 1 = weak; 2 = thin; 3 = meaningfully useful but limited; 4 = strong; 5 = exceptionally compelling and substantiated for that dimension. Score each dimension independently, with specific reasons; do not inflate scores to pass the later bottleneck or cutoff. A strong supported process/decision can score well without performance metrics; a missing outcome lowers strength only when the angle claims or depends on that outcome.

- `grounding`: precision of alignment with the actual context and the claim's key boundaries.
- `strategic_fit`: credible service of WIA's stated content/business strategy, not merely topic relevance.
- `distinctiveness`: meaningful perspective, particular source scene or actual demonstrated method; not cosmetic phrasing, purpose-label variation or unverified historical novelty.
- `audience_resonance`: a specific credible reason the intended wedding-business owner would care, without assuming incompetence or predicting views.
- `source_strength`: sufficiency, interpretability and qualifications of original source support for the treatment as stated, not generic confidence in the model.

Check cross-angle duplication by comparing central perspective, audience concern, underlying stake and WIA contribution. Merge equivalent treatments; multiple angles may share source moments only when there is a substantive reason. If history is unavailable or the previous-signature list is empty in the rendered request, do not assert historical novelty.

## Internal intelligence

For initial angle generation, return `internal_insights` for useful but not necessarily public intelligence from actual current source moments. Every entry has `moment_ids` (nonempty, unique IDs from this pool), `insight` (what the evidence reveals), `strategic_use` (how WIA could investigate or apply it internally) and `research_questions` (specific open questions or []). Keep product praise separate from affordability objections and do not invent missing praised features. One moment may support both internal intelligence and a distinct supported public treatment when warranted.

For the initial response, return exactly these top-level keys: `angles`, `internal_insights`, `processed_moment_ids`, `coverage_notes`. `angles` and `internal_insights` may be empty. `processed_moment_ids` must list every current supplied `moment_id` exactly once, even if unused in an angle. Use `coverage_notes` (array of nonblank strings, possibly empty) to document meaningful exclusions, incomplete or partial moment pools, limits, research gaps and why apparently similar candidates were merged. If public angles and internal insights are both empty, provide a concrete nonempty coverage explanation. Coverage acknowledgement does not prove that any upstream omitted moments were examined.

Do not generate permanent IDs, novelty scores, embedding calculations, a selected CTA, approval flags, rankings, new response keys, or a different handbook/legacy envelope. Historical signatures are overlap context only, never authority or current source evidence. The response must match the active backend `StrategicAngleResponse` JSON contract exactly, without Markdown, prose or private reasoning.

Moment pool:
{{MOMENT_PACKET}}

Previous eligible signatures, for awareness only:
{{PRIOR_SIGNATURES}}
