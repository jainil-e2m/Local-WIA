Generate grounded, specific, mutually distinct angle proposals from all supplied moments. Read each moment's actual source_evidence as well as its interpretation, and retain relevant qualifications. Use the trusted policy as an editorial lens, not as permission to import facts. No external research is supplied.

## Angle record

Every field is required. Do not return placeholders or additional fields.

- local_key: unique local label, such as a1.
- title: a short, concrete working title naming the supported issue or decision, not a finished attention hook or generic benefit such as “Grow with confidence”.
- argument: one clear sentence stating the point this content would demonstrate. It should remain meaningful without the case's largest number. Make the supported business relevance visible without promising an outcome the evidence cannot establish.
- audience: wedding-business type/state and relevant experience, capacity or buyer situation. Do not silently convert an established owner into an ads beginner or limit the lesson to a second business arm unless the argument requires it.
- tension: a recognisable dilemma, question or constraint supported by the passage. Do not invent shame, failure, universal industry behaviour or psychological diagnosis.
- take: the specific understanding or belief shift the reader should leave with, not a slogan or reworded title.
- mechanism: explain why the take follows, naming the decision/process and the connection to buyer confidence, useful inquiries, bookings or an operational benefit where supported. “Build better systems” alone is insufficient. Do not equate association, testimony or several simultaneous changes with controlled causation.
- reader_decision: what the owner should inspect, ask, clarify or reconsider next. This is an editorial takeaway, never a sales CTA, DM keyword, offer choice or destination.
- moment_ids: unique, existing IDs of the current supporting moments. At least one is required. These are backend-assigned IDs in the packet, not the m1 local labels returned by Call 1.
- source_assertions: nonempty, specific factual statements supported by those moments. Each string starts with [moment_id] and a space, using an actual referenced ID, followed by the supported statement. Retain subject/period/attribution/estimate labels; no historical claims or invented calculations. Quotes must remain exact if used.
- inference: null if no additional interpretation is needed; otherwise one bounded editorial inference clearly distinguished from observed/reported facts. Do not use this field to invent an outcome or fix a missing central fact.
- qualifiers: important limits that must survive into a later brief, including reported/estimated/planned status, attribution, cost basis, human involvement, conflicting evidence, limits to generalisation and accurate task ownership.
- risks: concrete unresolved verification, privacy, source-identity, commercial or downstream reuse concerns. Unknown or internal_only handling must remain visible. A public_candidate source is still not cleared to publish.
- quality: grounding, source_relevance, audience_fit, specificity, editorial_usefulness and reasons. Supply 0–5 scores for these dimensions only, with concise evidence-specific reasons and meaningful limits. Do not score recency, novelty, engagement, demand, publication permission or expected sales.

## Quality anchors

0 means absent/contradicted; 1 weak; 2 thin; 3 usable with important limits; 4 strong and concrete; 5 exceptionally well supported on that dimension. Do not give every angle 5 by default.

- grounding: fidelity to actual source passages and completeness of material qualifications, not confidence of tone. A proposal may be strongly grounded as a proposal, never as a delivered result.
- source_relevance: the central argument depends on these current moments, not on a generic idea that could be attached to any meeting.
- audience_fit: usefulness for the stated wedding-business state and respect for its existing competence.
- specificity: a concrete tension, mechanism and inspectable reader decision rather than abstract “strategy/clarity/confidence”.
- editorial_usefulness: a meaningful new way to understand the situation with enough substance to develop later, without filler or exaggerated selling. This is a directional judgment, not a prediction of channel performance.

A high score does not override a failed factual constraint. Do not emit an angle whose central point requires unavailable proof.

## Coverage and distinctness

processed_moment_ids must include every supplied moment ID exactly once, even if unused in an angle. For omitted moments, coverage_notes names the relevant ID and gives a concrete reason, such as insufficient interpretation, purely logistical material, a central fact needing verification, or a proposition already covered by a stronger treatment. A valid empty set is preferable to a vague set; explain an empty result. Never pad to four, generate one angle per moment by habit, or suppress a strong candidate just to hit a fixed weekly quota.

Use the argument/mechanism/reader-decision test for distinctness. For example, campaign measurement and reducing isolation while learning may share a story but change different decisions if the passages support both. “Confident marketing”, “Know what works” and “Ads that give clarity” are not three distinct arguments when they all recommend the same measurement decision.

Return {"angles": [...], "processed_moment_ids": [...], "coverage_notes": [...]} and nothing else. Do not generate an embedding signature: the backend constructs one canonical representation from the semantic fields, independent of title, formatting, scores and generation time.

The following packets contain the only case evidence. Prior signatures, if any, are overlap context only; they are not facts or publication records. An empty list means no prior signatures were supplied to this call, not that no previous angles exist. History is compared later in code.

Moment pool:
{{MOMENT_PACKET}}

Previous eligible signatures, for awareness only:
{{PRIOR_SIGNATURES}}
