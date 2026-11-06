# Content Atelier — Postgres, pgvector, and knowledge-storage design

Prepared: 7 October 2026.

Status: reasoned design specification for review, not an implemented schema or an instruction to deploy infrastructure. This document consolidates the supplied solution architecture, the corpus/editorial review, and the user's subsequent storage decisions. It does not modify the supplied architecture or authorise new connectors, automatic learning, or publishing.

## 1. The decision and the answer to “anything else?”

Yes. Historical meeting/Slack chunks and generated angles are necessary, but insufficient to produce grounded content in Whitney's voice. We also need structured moments, scoped claims, canonical topics, prior published content, brief/asset history, curated positive and negative editorial examples, and current policy/offer records. Some need embeddings; others must be retrieved deterministically.

The governing distinction is:

**Store the records needed to explain and reproduce an editorial decision. Embed only representations that benefit from semantic retrieval.**

Confirmed by the user:

- One Postgres database with pgvector, not an additional vector database.
- Separate logical collections/search targets for historical source evidence and generated-angle memory.
- Retain all generated angles, not only the four selected for a weekly portfolio, and consult that history when proposing new angles.
- Initial bounded batch ingestion; four distinct weekly angles; three approval gates before production handoff.
- The current task is to document storage and its clarifications, not implement the backend.

Recommended additions below are explicitly design recommendations. Physical table/schema names, source permissions, retention periods, and production quantities still require implementation choices or user confirmation.

The supplied architecture already supports one database, three knowledge tiers, source segments, moments, topics, angle embeddings, brief/asset versions, published history, and decisions. The principal additions are stronger claim/provenance contracts, pre-generation memory retrieval, explicit candidate persistence, source revisions/snapshots, curated correction handling, and permission-aware invalidation. [Supplied architecture, §§0, 3, 7, 10][architecture] [Reconciled architecture review][architecture-review]

## 2. What “vector database” and “collection” mean here

Postgres is the authoritative database. pgvector adds vector storage and similarity search to it. The application still uses ordinary text, numeric, relational, JSON, and audit records alongside vectors.

A “collection” means a logical group with a clear purpose, eligibility rules, and retrieval interface. It can be implemented using typed tables and, optionally, PostgreSQL schemas. It is not a separately deployed database or a new service. Schemas organise related database objects; access still depends on privileges. [PostgreSQL schemas][pg-schemas]

Keep the original three knowledge concerns:

1. **Editorial policy:** how Whitney wants content written, the current strategy, offer boundaries, format rules, and deliberately chosen CTAs.
2. **Source evidence:** what people actually said or reported, its context, and the propositions it can support.
3. **Content memory:** what has been proposed, reviewed, generated, scheduled, and actually published.

Operational/audit tables support these concerns but are not a fourth semantic corpus. External research is a separately labelled evidence subtype, not an equal-authority replacement for WIA's internal proof.

Use illustrative table families such as `evidence_*`, `memory_*`, and `policy_*`, or equivalent schemas. The final naming is an engineering choice. Do not create one table per client, Slack channel, week, or file. Related call and Slack chunks can share a typed `segments` table, distinguished through source metadata.

Avoid one generic `documents(text, embedding, metadata)` table for everything. It becomes too easy to retrieve an obsolete offer, rejected draft, or generated claim as if it were verified source evidence. A shared search service is useful; a shared authority level is not.

## 3. Complete storage inventory

“Core” means the responsibility is needed as the corresponding pipeline stage is implemented, not that every component must be built before ingestion. “Optional embedding” does not mean optional record retention.

| Knowledge category | Authoritative record | Embed? | Why it belongs |
|---|---|---|---|
| Meeting, Slack, workshop, and approved corpus sources | Logical source plus exact source revisions; private raw-object references | Source metadata: no. Searchable segments: yes | Preserve underlying context and evidence |
| Screenshot/image-derived text | Attachment identity, original-file reference, extraction revision and linked segments | Yes, for eligible extracted text/descriptions | Make otherwise inaccessible evidence searchable without pretending OCR is exact |
| Content-worthy moments | Structured insight and links to supporting source spans | Yes | Find reusable questions, results, stories, teaching, objections, and recurring concerns |
| Scoped public claims | Structured proposition, qualifiers, measurements, evidence and exclusions | Optional initially; yes if claim retrieval becomes useful | Prevent a relevant passage from becoming an inaccurately worded factual claim |
| Canonical topics | Name, description, aliases, hierarchy if needed, moment links | Yes | Connect discussions expressed differently over time |
| Every generated/manual angle | Angle identity, immutable revisions, semantic signature, status and decisions | Yes | Historical novelty search and proposal recall |
| Briefs and generated assets | Exact versions, governing angle/brief/plan, claim links and locks | Embed brief spines and meaningful asset messages where useful | Avoid duplicate work and compare actual arguments across formats |
| Prior published content | Publication record plus the exact published or archived representation | Yes, for key messages and useful content sections | Check audience-facing repetition, including pre-Atelier history |
| Curated editorial exemplars | References to approved/published assets or reviewed source excerpts | Yes, optionally with format-specific projections | Retrieve examples of a suitable execution, not only a similar subject |
| Founder corrections and negative examples | Before/after spans, actor confidence, scope, rationale, approval and supersession | Optional retrieval of reviewed correction cases | Retain what Whitney rejected without teaching the writer to copy it |
| Active voice, strategy, offer, CTA and format policy | Versioned, reviewed records selected by exact policy/offer/format identity | Not required for enforcement; optional archive search | Essential rules and current product truth must not depend on a similarity ranking |
| External research and SEO results | Cited findings, provider/query metadata, dates, cache and dossier links | Optional, separately targeted | Add dated public context without laundering it into WIA proof |
| Permissions, people, clients, publication events, approvals, locks and dependency links | Relational records and constrained structured fields | No | Exact identities, decisions, dates and rights are not similarity questions |
| Snapshots, jobs, retrieval logs, evaluations and cost records | Durable state, manifests and bounded diagnostic records | No by default | Reproduce decisions, detect omissions, recover work, and evaluate quality |

There is no need to embed every paragraph of every asset revision on day one. Start with source segments, moments, topics, angle signatures, and historical published key messages. Expand projections when a concrete retrieval or repetition problem warrants it.

The inventory extends the original architecture, not replaces it: moments/topics and published memory are already there; claims and precise revision/permission contracts strengthen the earlier design. [Supplied architecture, §§3.3, 7.1, 10][architecture]

## 4. Authority boundaries: similar does not mean true, approved, or current

Every retrievable item needs an explicit kind and authority. Useful categories include `source_span`, `extracted_moment`, `reported_claim`, `generated_angle`, `draft_asset`, `published_asset`, `reviewed_exemplar`, `founder_correction`, and `external_finding`. These categories describe different responsibilities; they are not a single ladder of truth.

Three independent dimensions matter:

- **Factual authority:** does the underlying record support this proposition, with the correct speaker, period, attribution, and qualifiers?
- **Editorial authority:** is this a current founder instruction, an approved example, a consultant proposal, or an unapproved draft?
- **Workflow authority:** was this exact revision actually approved, scheduled, or published?

Publication establishes that a message reached an audience when adequately evidenced. It does not independently establish that its numerical claim was correctly scoped or that its source may be reused now. An angle generated from a transcript is not a second independent corroborating source. A human-approved brief is an editorial contract, not a new measurement of client performance.

Content returned from Slack, transcripts, chats, or public research remains source data. Instructions found inside it must not override pipeline rules, trigger tools, change access, or approve artifacts. Reviewed founder corrections become active policy only through an explicit policy-release process. The rest of the corpus remains untrusted as operational instructions.

These boundaries are particularly important for this corpus: surviving assistant drafts can still be rejected, `user` chat roles do not always establish Whitney as the author, and published history/media coverage is incomplete. [Corpus authority and limitations review][taste-review]

## 5. Historical source evidence

### 5.1 Preserve source identity and exact revisions

Separate a logical source from its content revisions:

- A meeting has a stable conversation identity, even if Zoom and Fathom both captured it.
- A Slack parent/reply retains its upstream identity, channel, author and timestamps.
- A changed transcript, edited message, or new reply creates a new source representation/revision rather than silently overwriting the version behind an approval.
- Imported HTML and Markdown versions of the same email are alternative representations, not independent examples or independent proof.

Minimum source metadata: source system/type, upstream ID, canonical event ID, purpose, occurred time, observed time, available upstream revision time, host/channel/client/participants, original link or protected recording locator, content hash, raw-object pointer, parser version, inclusion/access status, and completeness state.

Use a `source_revision` identity plus a normalisation/segmentation version to identify derived chunks. A record can be retained for audit while being excluded from current generation. Do not describe “immutable revisions” as permission to retain sensitive material indefinitely after withdrawal.

### 5.2 Chunking is source-aware

Retain the supplied starting approach:

- **Meetings:** consecutive speaker turns, approximately 200–400 tokens, normally overlap one turn. Preserve timestamps and speaker identity/role. Prefer meaningful conversational boundaries over mechanical fixed-length cuts.
- **Slack:** parent message plus contextual replies, split when long. Preserve individual message IDs/authors; do not flatten the thread into a single anonymous speaker.
- **Screenshots:** preserve the original attachment reference, extracted text, visual description, extraction confidence and provenance as distinct fields.
- **Published carousels:** preserve post identity, slide number/order and caption boundaries. A caption is not another slide, and a transcribed visual description is not a verified original image.
- **Chat conversations:** preserve turn order, role, author confidence, supplied draft, correction and subsequent response boundaries. Do not chunk across a correction in a way that loses which text was criticised.

The original's 200–400 tokens and 1–2 minutes are rough starting estimates, not simultaneously guaranteed constraints. Tune to source structure and measured retrieval quality. A large uninterrupted speaker turn may require a controlled split. [Supplied architecture, §3.3][architecture]

Minimum segment fields: ID, source revision, sequence, source-unit/message IDs, source-span offsets, timestamps where applicable, raw text, normalised text, context header, speaker/role references, parser/segmenter versions, retrieval eligibility, full-text representation, and embedding metadata.

Headers should describe context rather than assert conclusions. Keep original text available for verification. Glossary corrections belong in normalised search text; ambiguous corrections remain hints for review, not rewritten “verbatim” quotes.

Neighbour expansion must use the same source revision and reapply access checks. A retrieved chunk without its preceding qualifier can invert the meaning of a result or quote.

### 5.3 Source inclusion: purpose before “internal versus external”

The original excludes internal/vendor calls by default. The corpus review showed why this is too broad: useful WIA operational discussions can contain editorially relevant decisions, client requests, and constraints.

Recommended purpose-aware scope:

| Source purpose | Recommended treatment, subject to access approval |
|---|---|
| Client calls, office hours, workshops | Include configured sources; retain source and permission boundaries |
| WIA client-performance/editorial/operations discussions | Include configured useful discussions; staff reports remain staff reports |
| Engineering/vendor/product-build syncs | Exclude from editorial generation by default |
| Prospect/sales calls | Include only if specifically authorised, with restricted/anonymised handling |
| Scheduling, billing, account/security and private personal material | Exclude from writing retrieval unless an explicitly permitted editorial purpose exists; protect sensitive fields |

Storage inclusion, extraction inclusion, internal research access, and public-use permission are different decisions. Someone discussing a client result internally does not create permission for a public testimonial.

### 5.4 Slack triage must not silently destroy context

The architecture clearly says only messages with a content signal proceed to moment extraction. It does not clearly specify whether triage-negative chunks remain stored/searchable.

Recommended contract: within an approved channel and retention scope, retain authorised source records even when no moment is extracted. Store the triage verdict/version/reason. Exclude operational noise from default writing retrieval, but permit controlled archive/context retrieval for authorised users. Sensitive or out-of-scope messages should not be embedded simply because they are technically readable.

This allows a brief researcher to recover a clarification in a seemingly uninteresting reply. Conversely, “archive retention” must not become “everything enters every model prompt.” Confirm this treatment and retention scope before import.

Track individual reply identities and refresh relevant threads, including old parents receiving new replies. The original fourteen-day parent rescan is not a general solution to old-thread activity. Slack exposes threaded-message retrieval; the connector must reconcile parent/reply coverage deliberately. [Slack thread API][slack-replies]

### 5.5 Raw files and missing media

Raw exports, original screenshots, and authorised document/media bytes belong in private object storage. Postgres contains their identity, hash, access metadata, and locators. Do not embed binary VTT/JSON exports or pretend a link contains the missing media itself.

The corpus review identified missing Slack attachment files and incomplete reel/slide media. Store explicit availability states such as `available`, `metadata_only`, `pending`, or `unavailable`. Only index content actually obtained and extracted through an authorised path. A referenced reel can be a production lead without being verified searchable footage.

## 6. Moments, scoped claims, and topics

### 6.1 Moments: the editorial discovery unit

Keep all valid candidate moments with their extraction status, not only top-ranked ones. Record type, title, summary, source spans, quotes, speaker/role, client, direct-quote versus staff-report/OCR evidence kind, content relevance, strength rationale, sensitivity and permissions.

Embed a compact projection containing moment type, title, useful summary and eligible supporting text. Store the projection/version separately from original evidence. An extracted summary must not replace the source passage for verification.

Moment extraction can read the complete included call, using bounded structured processing if it exceeds the chosen model's safe input budget. Chunk search serves later discovery and research; it is not a requirement to extract insights only from the nearest few chunks. “No moment found” should be an auditable result, not loss of the underlying source.

### 6.2 Claims: the missing precision layer

A moment identifies an interesting event. A claim identifies a proposition that public copy may safely state. One moment can support several claims; one claim can require multiple source spans.

Store at least:

- Subject/client/account, relevant period and comparison period.
- Metric, value, unit, baseline and denominator, where applicable.
- Attribution boundary and costs included/excluded.
- Reported, measured, estimated, derived, hypothetical, or planned status.
- Supporting spans, qualifying/counterevidence spans, and any calculation/assumptions.
- Permitted wording, required qualifiers and explicitly prohibited interpretations.
- Independent checks for text presence, speaker, context, measurement and public-use eligibility.

Worked corpus example: approximately $70,000 in ad-attributable new bookings is not total business revenue, profit, or proof that a prior agency produced no results. A previous fee-inclusive spend and a later media-only spend are not an automatically fair total-cost comparison. Save these restrictions with the claim, not only in a long research paragraph. [Attribution case analysis][taste-review]

Claim embeddings are optional initially. Structured retrieval through topic/moment links is enough to enforce approved claims. If embedded later, include the scope and qualifiers in the projection so a headline-sized vector does not erase what makes the claim defensible.

Do not collapse all verification into `verified = true`. Quote matching checks text location, not necessarily speaker, interpretation, consent, or causality. Failed matching does not make an unsupported paraphrase safe.

### 6.3 Topics: recall, not a ban on revisiting a subject

Store canonical topic identity, name, description, aliases, current/merged/blocked status and links to moments/claims/angles/published messages. Embed topic name and description.

Topic linking makes “the same concern discussed across three months” discoverable even when speakers use different words. Preserve assignment confidence and allow reviewed merges; changing an active topic mapping should not rewrite the historical rationale behind an approval.

A shared topic is not a duplicate angle. It helps retrieve evidence and nominate overlap comparisons; the reader decision, mechanism, claim and editorial contribution determine whether an argument genuinely repeats.

## 7. Content-angle memory and generation-time retrieval

### 7.1 Persist every generated candidate

Create a stable angle identity with exact revisions. Retain generated candidates that are selected, unselected, filtered as duplicates, below the quality floor, passed, snoozed, expired, approved, or later withdrawn. Keep valid manual ideas in the same memory contract.

Store cycle/run ID, origin, audience, statement, hooks, topic links, source/claim dependencies, generation/policy versions, score/reasons, novelty matches, selection status, human decision scope, CTA/steer, and timestamps. Invalid model output belongs in a bounded error/attempt record; do not invent a valid angle simply to populate memory.

Persist candidates before filtering/selection can discard them. Embedding/search readiness must be explicit. A run is not memory-complete until its valid candidates are durably recorded and searchable through the approved profile, or an honest incomplete-memory state is shown. Nightly refresh can recompute cooldowns; it must not be the sole path making new candidates searchable.

### 7.2 Store a semantic signature, not only a title

The original signature is `topic · take · core claim`. Extend the structured angle representation with audience/state, tension, belief shift, mechanism, primary case/proof, reader decision, and editorial job where available.

Embed a concise signature derived from these fields. Keep its text and signature version. Search can then recognise the same argument under a different hook, while distinguishing a shared topic that serves a different useful decision.

Preserve individual revisions but avoid counting five edits to one angle as five independent historical ideas. Default novelty search should use a representative/current relevant revision per angle, with access to earlier revisions for audit or changed arguments.

### 7.3 Retrieve before generation and validate after it

The original makes its post-generation memory filter clearer than its pre-generation retrieval. The strengthened contract is:

1. Build candidate themes from eligible weekly moments plus permitted historical/backlog context.
2. Retrieve relevant prior angle signatures and published key messages for each direction.
3. Give the generator a bounded prior-coverage summary: what the argument was, its status, why it was passed or used, and what would have to be new.
4. Generate grounded candidates; persist them and their signatures.
5. Check candidates against history and against one another in the current generation set.
6. Save matched IDs, pairwise assessment, policy action and explanation.
7. Select the four-angle portfolio, or return a shortage instead of filler.

Exclude a candidate's own revision from its history comparison. Handle the same logical angle's earlier revisions explicitly. Compare the new set pairwise so the first newly stored candidate does not accidentally make every subsequent candidate a historical repeat.

### 7.4 Memory status determines the response

Retaining an angle is not the same as permanently prohibiting it:

- An unselected idea may remain valuable backlog.
- An active approved workstream is a reservation against duplicate effort.
- A “weak proof” decision can be revisited when suitable evidence arrives.
- A local off-brand treatment does not necessarily ban the whole topic.
- A published message creates audience-exposure history.
- A discarded pack releases its work reservation; it does not invent publication.

Store reason scope, expiry/revisit conditions, and links to prior work. If Whitney says “done before” without an available publication record, retain that assertion with its provenance/uncertainty instead of manufacturing a publication date.

Similarity thresholds nominate pairs for assessment; they do not certify sameness. Keep the original numerical thresholds as uncalibrated proposal defaults, not agreed production settings. Use a calibrated pairwise similarity/meaning judgement, and distinguish its raw cosine score from a hybrid-search rank-fusion score.

## 8. Published content, brief/asset memory, and editorial examples

### 8.1 Import history before the first meaningful novelty run

Include authorised historical emails, carousels, captions, reel scripts/transcripts and available published representations. Keep channel, date, URL/source identity, format, text, key message, topics, related campaign/suite, availability and publication-confidence fields.

Do not reset this memory each week. Distinguish `reported_published`, `confirmed_published`, `scheduled`, and `draft` when the import's evidence warrants that distinction. A manual authorised publication record is acceptable; not every historical piece requires an API integration.

Archive coverage must be visible by channel/time range. “No match found” means no match in the available archive, not proof Whitney has never covered the subject.

### 8.2 Store actual brief and asset revisions

Keep briefs and assets as exact versioned content, including message spine, allowed/excluded claim IDs, audience, POV, chosen CTA, format, asset contribution, source handling, locked fields, approval records and governing pack plan.

Embeddings can project the brief spine and the asset's main claim/message. Their purpose is work recall and overlap review, not proof. Store published wording separately when it differs from approved copy.

Approved, produced, scheduled, and published are separate events with separate dates. A pack approval should not start a publication cooldown as if the audience had already seen it. Four angle approvals must not automatically create four complete packs; the explicit asset allocation remains a separate production decision.

### 8.3 Curated exemplars: relevant execution, not indiscriminate imitation

An exemplar is a reviewed reference to an existing asset or source excerpt, with format, editorial job, audience, reason it is useful, approval/author confidence, applicable policy version and obsolescence restrictions.

Retrieve a small appropriate set: an education caption should not inherit a historic launch-reminder voice merely because both mention Meta ads. The same published item can serve novelty memory and exemplar retrieval using different projections; it need not be copied into disconnected authoritative stores.

Exemplars teach execution. Their names, numerical results, deadlines, availability, and offer promises are not portable facts for a new story. Revalidate a reused factual case against eligible underlying evidence.

### 8.4 Chat histories and corrections need deliberate curation

Treat chats as a record of process, not a uniformly approved copy library. Preserve author/role confidence, turn order, proposed copy, exact correction, correction category, scope, resulting revision, and whether approval is actually evidenced.

The existing chat index describes surviving branches, but surviving branches still include assistant drafts criticised by the next prompt. Some user-role material is team-authored. Missing canvases/attachments are not available approved outcomes. [Chat export index][chat-index] [Corpus review][taste-review]

Recommended reviewed correction record:

- The offending span and the exact founder correction.
- Verified/uncertain author and date.
- Factual, audience, mechanism, offer, voice, CTA, or edit-scope category.
- Local edit versus reusable rule; affected format and audience.
- Accepted replacement if actually available.
- Supporting/conflicting examples and supersession relationship.

Negative examples remain excluded from positive exemplar retrieval. They can appear in a labelled review/critique context. Store later live corrections immediately, but do not silently promote each edit into a global voice rule or automatically fine-tune/update prompts.

The September caption corrections, for example, should govern applicable captions without automatically banning every short carousel headline. Current reviewed rules take precedence over the quantity of older examples in the archive. [Policy authority review][taste-review] [Caption conversation][caption-chat]

## 9. Editorial policy, offer truth, and CTA records

Store founder voice principles, current strategy/pillars, glossary, banned patterns, format specifications, pack templates, reviewed correction rules and prompt versions as versioned policy records.

Select the active policy bundle deterministically for the stage and format. An essential rule must not disappear because its embedding ranks twenty-first. Optional search can locate examples or explain historical changes; it cannot choose which rules are authoritative.

Recommended policy fields: stable identity, revision, author/approver, effective dates, source reference, scope, status, superseded revision, compiled-bundle hash and rationale. Keep an explicit policy release, rather than assuming the most recently ingested document is automatically current.

The original “load the brand kit whole” is best interpreted as loading the complete applicable **curated active rules**, plus a bounded exemplar set. It should not mean inserting every historical email, chat draft and strategy note into every prompt. If the bundle exceeds a model budget, visibly resolve/split the stage or curate the policy; do not silently truncate essential rules.

Offer records need separate exact facts: offer identity/aliases, current availability, audience, what WIA does, what the client does, prerequisites, supported deliverables, excluded promises, approved destinations and effective version. Preserve old versions for interpretation of historical content, but exclude them from current sales assertions.

Examples from the corpus justify this separation: a past ELEVATE waitlist is not a current availability statement; a discussion of a planned capability is not proof of an existing deliverable; LeadLock appearing in a success story does not establish that it caused the entire result. [Offer/causality findings][taste-review]

Store CTA options and an explicit chosen action bound to the approved angle/brief revision. Suggestions are not choices. Support reply/DM/resource/offer invitations and deliberate no-explicit-ask modes where approved. Do not infer destinations from a semantically similar old post or preselect a CTA on Whitney's behalf.

## 10. External research and research dossiers

Store external research when the post-angle research stage is implemented. Keep it separately labelled from internal source proof, even if both reside in the evidence table family.

Required finding metadata: provider, sanitised query, URL, publisher/title, relevant excerpt or permitted response representation, retrieval time, published/event time when known, topic, reliability/limitations, expiry/cache identity, and dossier links. Structured SEO data should retain market/language, metric meaning, period and provider units. It does not need an embedding merely because it is research.

Optional embeddings can make retained public findings reusable, but use a distinct search target and authority label. A platform announcement can explain “why now”; it cannot establish a specific WIA client's result. An external spike should not automatically refresh an unchanged internal claim.

Keep substantive enrichment after Gate 1 for the initial agreed flow. DataForSEO remains optional/off initially unless chosen. Use only approved public-topic queries outside the private model context; do not send client names, quotes, private source bodies or token-bearing URLs to a public search provider. Provider retention/routing requirements must be assessed independently of database storage location.

A dossier is the exact research record used for a brief, not just a list of URLs. Save queries, filters, source/claim revision IDs, selected and rejected hits, retrieval/reranking versions, graded evidence, conflicting information, unresolved gaps, coverage/truncation, and external findings. It should be possible to tell whether a weak brief came from poor retrieval or poor interpretation.

The original proposes a bounded multi-query loop with topic expansion and at most two follow-up rounds. Keep those as starting budgets, with visible exhaustion. Searching the whole eligible archive does not promise every relevant item can fit into a finite dossier. [Supplied architecture, §3.6][architecture]

## 11. Relational control records that must accompany vectors

The following records belong in Postgres but generally do not need vectors:

- **People/clients/accounts:** stable identities, aliases, roles and source-system mappings. Names in an embedding do not establish identity or permission.
- **Permissions:** permitted uses, handling requirements, authority, scope, effective/expiry/revocation dates and events.
- **Source and derived-object dependencies:** exact links from source revisions/spans to moments, claims, dossiers, angles, briefs, assets, caches and handoffs.
- **Snapshots and coverage:** which source revisions and completed derived representations were eligible for each run, which hosts/channels/time ranges were missing, and who accepted partial coverage.
- **Decisions:** exact object revision, actor, authority, action, reason scope, time and request identity. An approval score is not an approval record.
- **Locks:** exact accepted text/field and the version to preserve. A semantic vector cannot enforce “keep this opening unchanged.”
- **Publication events:** channel, actual date, published representation/URL or authorised manual evidence, and withdrawal/amendment information.
- **Work and processing attempts:** input fingerprints, leases/status, errors, checkpoints, processing versions and output pointers.
- **Retrieval/evaluation runs:** search configuration, ordered hit IDs/scores, selection decisions, policy/profile versions and expected outcomes.

Keep critical identities, states, dates and relationships in typed constrained columns. JSON is appropriate for rich editorial bodies and provider payloads, not as the only unvalidated home for approval/permission semantics.

Do not embed credentials, access tokens, queue messages, job stack traces, raw payment/account identifiers, or arbitrary telemetry. Diagnostic storage should use IDs/fingerprints and redacted error categories by default, not private prompt/source bodies.

## 12. Embedding and full-text contracts

### 12.1 A vector is a derived representation

For every embedded item, retain:

- Exact authoritative entity/revision and semantic projection text or reconstructable projection.
- Projection/input hash and projection-builder version.
- Embedding-space/profile identity, pinned model/configuration, dimensions and document/query encoding conventions.
- Text normalisation/context-header version, requested distance metric and generation time.
- Readiness/error state and active/retired representation status.

The proposed initial implementation can place vectors on typed domain tables or typed embedding side tables with enforceable revision references. Do not require a generic polymorphic record that cannot guarantee its target exists. If all profiles cannot fit one fixed vector-column definition/index, use an explicit compatible versioned representation rather than mixing incompatible rows.

Equal dimensions do not imply equal embedding spaces. Query and document vectors must use the compatible active profile and the appropriate encoding convention. Stage-specific projections also need versioning and evaluation, even when they share the same underlying space.

### 12.2 Representation by purpose

| Retrieval purpose | Suggested projection |
|---|---|
| Recover source language | Context header plus normalised segment text, with original text retrievable |
| Discover moments | Moment type, title, scoped summary and eligible supporting quote |
| Link topics | Canonical name, description and reviewed aliases |
| Compare angles | Audience/tension/take/mechanism/core claim/reader decision signature |
| Check prior published arguments | Published key message plus meaningful contribution and relevant context |
| Select execution examples | Reviewed excerpt tagged by format/editorial job and why it is useful |
| Retrieve claims, if needed | Proposition with subject/period/units/attribution/qualifiers |

Do not use a compressed key-message vector as the only way to recover a detailed quote. Do not use an entire long email vector as the only representation of its argument. Preserve authoritative content and choose a projection suited to the question.

### 12.3 Full-text and exact metadata remain first-class

Use semantic search for meaning, full-text search for wording, and relational filters/joins for exact identities, dates, states, permissions and claim fields. A number appearing in a semantically nearby passage is not a verified numerical claim.

The original hybrid approach can fuse independently ranked semantic/keyword lists and optionally rerank the shortlist. Record component scores and final ordering separately. PostgreSQL documents GIN as the preferred full-text index type; use the appropriate `tsvector` representation and verify query behaviour for this corpus. [PostgreSQL full-text indexes][pg-textsearch]

For novelty judgements, never apply a raw cosine threshold to a fused rank score. pgvector's cosine operator returns distance; cosine similarity is `1 - distance`. [pgvector querying][pgvector]

### 12.4 Re-embedding and projection changes

Build a shadow representation for a new embedding space or projection. Evaluate retrieval/novelty against held-out cases before switching the active profile. Record the profile switch, preserve prior profile IDs in historical runs, and retain old vectors only as retention permits.

A new model must not silently query old vectors, and a partial migration must not imply full coverage. Missing embeddings should be visible; an allowed keyword-only fallback can be labelled, while novelty generation should wait or explicitly disclose incomplete memory if semantic checking is essential.

Source/permission changes can invalidate vectors independently of model changes. Re-embedding revoked text would simply recreate the privacy problem; eligibility must be checked before processing as well as before search.

## 13. Retrieval targets, filters, and index strategy

### 13.1 Distinct targets behind one service

Retain a shared retrieval interface, but make intent explicit. Suggested targets include source segments, moments, topics, angle memory, published memory, reviewed exemplars, and optional claims/external findings. Mandatory policy loading uses exact policy identities instead of ranked search.

An evidence request should not silently fall back to a generated angle when no proof is found. An exemplar request should not return an unlabeled rejected draft. A published-memory request should not count an unshipped mock pack as audience exposure.

Minimum request context: authenticated principal/processing authority, purpose/stage, query, target, source/history snapshot, policy/profile versions, allowed source kinds, time/topic/client/role filters, status restrictions and result budget. Set these on the server; do not let a model widen its own access through arbitrary filters.

### 13.2 Returned evidence must be inspectable

Each hit should expose entity/revision, kind/authority, eligible excerpt, source locator, speaker/role confidence, occurred date, claim qualifiers if applicable, handling requirements, component scores and match rationale. Neighbour expansion and reranking must retain these boundaries.

Deduplicate evidence by underlying event/client provenance rather than merely chunk ID. Two overlapping chunks from one meeting, two exports of one meeting, and a Slack repost of one screenshot must not become three independent testimonials. Conversely, independent client concerns should not disappear merely because their wording is similar.

### 13.3 Eligibility before expensive processing, and recheck before handoff

Logical retrieval eligibility must be enforced before any source is supplied to an embedding/reranking/writing provider. Apply access, source-purpose, current-revision, snapshot and withdrawal conditions consistently to semantic, keyword, topic expansion, neighbours and caches. Check public-use handling again for the actual drafted asset and at final handoff.

This does not mean every private item must be excluded from authorised internal research. Internal research eligibility and public disclosure eligibility are distinct, explicit uses.

### 13.4 Start with measured exact search; add ANN when justified

pgvector supports exact search and approximate HNSW/IVFFlat indexes; approximate search trades recall for speed. Its documentation warns that filters applied after approximate index scans can reduce returned matches and describes iterative scans. [pgvector indexing and filtering][pgvector]

For this corpus, benchmark exact search on eligible rows with ordinary metadata indexes first. Add an appropriate ANN index only when measured latency/volume justifies it. Test restrictive filters against an exact baseline; consider supported iterative scans or suitably scoped indexes where needed. Validate the installed PostgreSQL/extension versions rather than copying settings from a different image.

The original 100,000-row cutoff is a heuristic, not a guarantee. Relevant measures include filtered latency, recall, result completeness, memory use, update cost and index size. There is no current reason to introduce a separate vector service or a partition per client/week.

Independent target-specific indexes and projections prevent a much larger evidence archive from crowding out angle-memory results. Do not compare scores across unrelated targets as if they were calibrated on one universal scale.

## 14. How storage supports the weekly pipeline

| Stage | Reads | Writes / freezes | Important boundary |
|---|---|---|---|
| Batch ingestion | Approved source registry, cursors/access and source identities | Connector runs, raw references, source revisions, coverage and manifest | No silent claim of complete coverage |
| Normalisation/indexing | Exact source revisions, speaker/glossary policy | Versioned segments, triage, full-text data, embedding readiness | Original evidence remains traceable |
| Moment/claim extraction | Included complete source context and verification policy | Candidate moments, scoped claims, topic links and checks | Extraction is not blanket public-use approval |
| Candidate angles | Weekly signals, permitted historical evidence/backlog, policy and prior angle/published memory | Every valid angle candidate and novelty assessment | Retrieve memory before drafting; check afterwards |
| Four-angle selection / Gate 1 | Grounding, overlap explanations, candidate set and offer definitions | Selected portfolio, reservations and exact angle/CTA decisions | Four distinct directions or visible shortage |
| Research | Approved angle, eligible historical evidence, prior coverage and optional public findings | Exact dossier revision, hits, grades and gaps | Relevant historical evidence may be months old |
| Brief / Gate 2 | Dossier, policy, claims, current offers and approved CTA | Brief revision, allowed/excluded claims, locks and asset allocation | Approval binds the exact editorial contract |
| Asset generation/checks | Approved brief/plan, claim set, policy and curated exemplars | Asset revisions, factual/style/set checks and dependencies | Assets are generated independently from the shared contract |
| Pack approval / Gate 3 | Exact eligible assets and their current checks | Pack manifest and decision bound to exact revisions | Hard factual/privacy failures cannot become ordinary warnings |
| Production/publication recording | Approved manifest and handling instructions | Handoff state; later separate publication/amendment events | Copy approval and staging are not publication |

### 14.1 Freeze weekly signals without losing historical recall

Do not use a weekly-only filter for every retrieval request. Distinguish:

- **Weekly signal manifest:** exact source revisions representing new/late-arriving evidence considered for this cycle.
- **Historical research snapshot:** eligible archive revisions available at the research cutoff, including older calls and messages.
- **Content-memory as-of view:** prior proposals, reservations and publications visible when selection was made.
- **Policy/profile versions:** the exact rule and retrieval configuration used.

A historical source imported today is not a meeting that happened this week. Preserve occurred, observed, source-revision and editorial-cutoff times independently. A late transcript can enter a later run or an explicitly reopened snapshot; it must not silently rewrite an already approved argument.

The research snapshot can be established after Gate 1. Newly available material is recorded in that dossier version; if it materially changes the approved direction or claim boundaries, reopen the affected gate. Permissions remain current even when an as-of evidence snapshot is used.

### 14.2 Search readiness is part of run completeness

Keep separate fetch, normalisation, extraction and embedding readiness states. A successful connector response is not proof that all transcripts/attachments were readable or indexed. Source gaps, embedding failures and stale representations should be visible by host/channel/time range.

Persist outputs and their dependencies atomically where practical; stage expensive embedding work through durable intent. Reprocessing keys should include source revision, representation/projection version and profile. Workers must not replace current output with a result computed from stale input.

An explicit partial result may be useful, but it must identify missing coverage and receive the required acceptance. Do not generate a confidently novel portfolio when relevant prior memory silently failed to load.

## 15. Permissions, edits, deletion, and dependency invalidation

### 15.1 Permission is multi-dimensional

Record naming, verbatim quotation, results/metrics, screenshot reuse, visual identity, training excerpts and applicable destinations/audiences independently where needed. Include authority, scope, expiry and revocation. Record handling separately: anonymise, omit, paraphrase, blur, aggregate or use a labelled illustration.

Anonymisation is not an automatic safe-use flag: a story, screenshot or combination of details may still identify someone. A public post does not by itself establish permission for every reuse. A staff report is not a direct client quote. The actual asset's usage must be checked against its requirements.

Store permission on authoritative records/relations, not only copied metadata inside an embedding row. If eligibility flags are cached for speed, keep them synchronised with policy events and fail safely while invalidation is incomplete.

### 15.2 Source edits are not silent evidence substitutions

Create new source/derived revisions when upstream text changes. New processing may supersede an active source representation, but earlier approvals retain their exact historical dependencies and are flagged if their factual basis changed.

For changed claims, speakers, permission, central audience, offers or CTA, invalidate/reopen affected downstream approvals. A spelling fix may be local, but the changed asset still has its applicable review boundary. Store the reason and affected field scope rather than blindly regenerating every accepted paragraph.

### 15.3 Withdrawal must propagate through every representation

On a confirmed deletion/removal request or permission revocation:

1. Immediately remove the material from eligible search and pending public handoff.
2. Identify dependent segments, vectors, moments, claims, dossiers, briefs, assets, exemplars, caches and model-context copies.
3. Purge/redact/restrict according to the approved retention policy; flag dependent content and invalidate approvals as necessary.
4. Retain only permitted minimal audit/tombstone information needed to prevent accidental reimport.
5. Reapply withdrawals when restoring backups or reprocessing old exports.

The “retain every angle” requirement operates within privacy/retention constraints. A sensitive angle signature may itself need redaction or removal, while a minimal non-sensitive workflow fact remains. Merely deleting the transcript and leaving its quote in angle memory or a cached dossier is incomplete.

Do not infer confirmed deletion from a failed/incomplete connector poll. Unavailable, inaccessible and deleted are different states. Restrict uncertain evidence appropriately and reconcile with an authoritative source path.

Backup retention and purge timing remain to be chosen. There is no promise here that historical backup copies can be edited immediately. A restore procedure must prevent revoked material from becoming searchable again before withdrawal reconciliation.

### 15.4 Access and provider boundaries

Use the existing authenticated application boundary; do not introduce a replacement login merely for vector search. Scope backend reads/writes and raw-file access to authorised principals/stages. Avoid logs and model contexts containing secrets or token-bearing URLs.

Database privileges are mandatory. If row-level security is used as defence in depth, test the actual runtime role: PostgreSQL documents owner/superuser/bypass-role exceptions. A policy does not protect a connection that bypasses it. [PostgreSQL row security][pg-rls]

Embeddings and extracted summaries are sensitive derived data, not guaranteed anonymised representations. Sending text to an embedding or reranking provider is a disclosure/processing step that needs approved routing. Keeping the vectors in Railway does not mean all processing stayed in Railway.

## 16. Clarification register

This register records both the earlier clarifications and additional storage decisions. “Recommended” is not approval to broaden access or production scope.

| Item | Current position / recommendation | Status / decision needed |
|---|---|---|
| Physical datastore | One Postgres database with pgvector; separate logical evidence/memory targets | User confirmed |
| All angle retention | Retain all valid generated/manual candidates and status/reasons, not only selected four | User requested; exact privacy/retention policy remains open |
| Collection implementation | Typed table families; optional schemas, not one universal authority-free index | Design recommendation; final naming/migrations pending |
| Pre-generation memory | Retrieve relevant prior angles/published arguments into bounded generation context, then validate candidates afterwards | Strengthening of original post-generation filter |
| Candidate persistence timing | Save before filtering; make search readiness visible before later runs | Design contract to implement/test |
| Source purpose | Include configured useful WIA internal discussions; exclude engineering/vendor noise separately | Recommendation; exact hosts/series/channels need confirmation |
| Slack triage-negative retention | Retain authorised archive context, skip moment extraction, exclude noise from default writing search | Recommendation; storage/search/retention scope needs confirmation |
| Source changes | Immutable normal-processing revisions, active/superseded states and dependency invalidation | Required precision missing from original indicative schema |
| Old Slack threads | Parent/reply reconciliation beyond a fixed recent-parent window | Connector contract/test pending; access must be verified |
| Permissions | Independent use dimensions and current eligibility; internal research differs from public reuse | WIA permission policy and authority need confirmation |
| Raw data/withdrawals | Private raw objects; explicit tombstones and purge/redaction across derived copies | Retention durations and backup handling need confirmation |
| Current policy | Exact active reviewed bundles, not semantic winner-takes-all retrieval | Recommendation consistent with fixed versioned prompts |
| Offer truth and CTA | Versioned current offer facts; deliberate founder CTA; historic examples cannot supply current promises | Current offer facts/destinations need confirmation |
| Publication status | Separate approved, produced, scheduled and actual published events; manual import acceptable | Recommendation correcting original approval/publication conflation |
| Archive coverage | Visible source/channel/date/media availability; missing match is not proof of no prior coverage | Coverage audit/import mapping pending |
| Weekly boundary | Explicit occurred/observed/revision/cutoff clocks and late-arrival policy | WIA timezone/cutoff to confirm; operator timezone is not evidence |
| Final production volume | Explicit pack plan across four angles; do not multiply full packs automatically | Weekly allocation versus per-angle bundles still open |
| Embedding/index choices | Compatible pinned profiles; benchmark exact retrieval and add ANN only if justified | Model/profile/version/latency targets to evaluate |
| External research | Separately labelled, sanitised, optional enrichment after angle approval | No expansion of provider scope authorised by this document |
| Chat/correction curation | Explicit approval/author labels; negative examples isolated; no automatic policy learning | Human-reviewed curation required before positive use |

The architecture can proceed through evidence/angle milestones without resolving every later format quantity. Source scope, access/permissions, temporal semantics and privacy handling cannot be postponed until public handoff.

## 17. Corpus import and minimum initial dataset

Classify imports before embedding:

| Available material | Destination / treatment |
|---|---|
| Meeting/Slack source material | Evidence sources/revisions/segments; extract eligible moments/claims/topics |
| Founder voice and strategy documents | Provenance-preserved policy archive; reviewed active rules and curated examples |
| Historical emails/carousels/captions | Published-history records where evidenced; format-aware exemplars after review |
| Reels/scripts/transcript screenshots | Store the representation actually available; distinguish script from confirmed published footage |
| Chat transcripts | Process/correction archive; only reviewed examples/rules promoted into writing inputs |
| Current weekly briefs | Versioned work-in-progress artifacts, not automatically published content or independent factual evidence |
| Analyst summaries/research reports | Supporting analysis with authorship, not original client/source facts |
| Frontend mock packs | Test/demo fixtures, excluded from source proof, positive exemplars and publication memory |

Do not trust copied index counts as an ingestion manifest. Record source IDs, representation relationships, extraction completeness and missing attachments. Preserve speaker/author uncertainty. An import should report actual files/records read and the resulting eligible/indexed counts.

The corpus has useful positive and negative examples, but it does not contain complete publication history or complete playable reels. A new complete-content-history claim cannot be inferred from the existing folder. [Corpus inventory/limitations][taste-review]

Minimum through the first four-angle milestone:

1. Approved source registry and permissions; raw/source revision retention contract.
2. Versioned chunks with full-text and compatible embeddings.
3. Moments, topics, scoped claim links and verification dimensions.
4. Relevant historical published messages plus every generated angle/status.
5. Current reviewed policy/offer bundle and enough curated examples to evaluate taste.
6. Frozen manifests, search readiness, coverage, decisions and novelty explanations.

Dossier/brief/asset memory grows as those stages are implemented. Broad external-search embedding, full paragraph-level embeddings of all asset revisions, multimodal image/video embeddings and an automated learning loop are not prerequisites.

## 18. Acceptance tests and operational checks

### 18.1 Retrieval and authority tests

- Search the ten-week-without-posting case by exact phrase and paraphrase; recover supporting context, not an invented percentage lift.
- Retrieve a claim's qualifiers: ad-attributable bookings must not become all revenue or profit; fee-inclusive and media-only cost scopes remain distinct.
- Two chunks/exports of the same meeting count as one underlying event; separate clients with similar concerns remain distinct evidence.
- A source edit creates new representations and flags affected work instead of rewriting approved dependencies.
- A Slack reply on an old parent becomes discoverable; partial pagination is not mistaken for deletion.
- Relevant triage-negative context is available through authorised archive research without flooding default candidate selection.
- Restrictive client/role/date/permission filters return eligible evidence; neighbour expansion and reranking cannot bypass them.
- Rejected assistant wording is excluded from positive exemplars; a newer scoped caption rule is not defeated by many older examples.
- An old waitlist/deadline or planned service cannot become a current offer fact.

### 18.2 Memory and workflow tests

- Every valid generated candidate remains stored after rejection/filtering/selection and is searchable before the next run.
- New candidates see meaningful history before drafting and are checked against history and their current set afterwards.
- Self-matches and repeated revisions do not inflate historical coverage.
- A changed hook with the same argument is detected; a genuinely different reader decision on one topic is not automatically banned.
- An active reservation, an approved unshipped pack and an actual publication lead to distinct policy responses.
- Incomplete archive/embedding coverage produces an honest limitation, not a fake novelty pass.
- A brief/claim/permission change invalidates the correct downstream approvals; unrelated locked wording remains preserved.
- Withdrawal removes eligible derived representations/caches and blocks reimport and public handoff.

### 18.3 Profile, evaluation, and recovery tests

- A query from an incompatible embedding space is rejected, not compared because dimensions happen to match.
- Shadow-profile migration is evaluated before activation; partial readiness is visible.
- When ANN is introduced, compare restrictive-filter recall against exact retrieval before release.
- Historical evaluations use evidence/content history available as of the simulated date. Future publication records and desired answers must not leak into the test setup.
- Demo/generated artifacts do not become positive gold labels or fake published examples.
- Restore testing verifies relational records, raw-object references, extension compatibility, selected embedding profiles and withdrawal reconciliation.

Monitor eligible/indexed counts by target, pending/failed representations, source/media coverage, query latency, zero/short-result rates, exact-baseline recall where sampled, duplicate decisions, unsupported-claim failures and founder correction effort. Do not interpret scraped likes or email delivery counts as a verified “winning content” score.

Set measured targets with a representative corpus before launch; this document does not invent an SLA or claim an evaluation has passed. Keep backups and object storage under an approved recovery policy. Embeddings are rebuildable from retained eligible text; approvals, source provenance, publication events, locks and withdrawals are not disposable cache data.

## 19. Crosswalk to the supplied architecture

| Responsibility | Already present in supplied document | Strengthening here |
|---|---|---|
| One database / tiers | §§0, 3.1–3.2 | Clarify logical collections, typed ownership and different authority |
| Source chunks and indexing | §§3.3–3.4, 4.1–4.2, 10 | Source revisions, thread/author boundaries, eligibility and readiness |
| Moments/topics | §§4.3–4.4 | Scoped claim ledger, independent verification dimensions and provenance deduplication |
| Angle history | §§3.1, 4.5, 7, 10 | Pre-generation retrieval, immediate candidate retention, self/revision handling |
| Brief/asset/published memory | §§3.1, 7.1, 10 | Separate reservation, approval, actual publication and semantic contribution |
| Brand kit | §§1.2, 3.1, 8.4 | Reviewed active policy, current offers, scoped corrections and bounded exemplars |
| Research dossiers | §§3.6, 4.6, 5 | Exact eligible source revisions, gaps/counterevidence and external authority boundary |
| Consent/deletion | §§4.3, 12 | Multi-dimensional use permissions, dependencies, tombstones and restore handling |
| Evaluation/rebuildability | §§3.7, 11 | Compatible profile migrations, as-of evaluations and no mock/exemplar leakage |

Where this document differs, it is a proposed refinement aligned to user-confirmed decisions and corpus findings, not a claim that the original already specified every detail. The original file remains unchanged.

## 20. Implementation handoff checklist

Before writing migrations, agree source registry, scope/permissions, temporal/retention contracts, required record identities and the first retrieval/novelty fixtures. Then implement the smallest typed schema that meets these responsibilities.

Prioritise source identity/revisions and manifests, segments/full-text/profiles, moments/claims/topics, historical publication memory, and every generated angle with its decisions. Add dossier/brief/asset contracts as their gates are implemented. Capture correction/publication events from the beginning, without building automatic learning or publishing.

The final design principle is:

**Evidence tells us what we can responsibly say. Policy tells us how Whitney wants it expressed. Memory tells us what we have already proposed or said. Relational state tells us whether this exact version is eligible, approved, and ready for handoff.**

## Sources and verification boundaries

Local editorial/design sources:

- [Supplied solution architecture, 4 October 2026][architecture]: principally §§0, 3, 4, 7, 10–12.
- [Corpus taste and pipeline review, 7 October 2026][taste-review]: source inventory, authority, claim hazards and editorial preferences.
- [Architecture comparison and reconciled design, 7 October 2026][architecture-review]: revisions, claims, permissions, gates and durability.
- [Chat export index][chat-index] and [September caption conversation][caption-chat]: process-history and scoped correction examples.

Primary technical documentation checked on 7 October 2026: [pgvector][pgvector], [PostgreSQL schemas][pg-schemas], [PostgreSQL full-text indexes][pg-textsearch], [PostgreSQL row security][pg-rls], and [Slack threaded replies][slack-replies]. These establish cited capabilities/constraints, not the actual installed environment or permissions. No database, provider account, migration or application implementation was created or tested by this document.

[architecture]: <C:/Users/Jainil Trivedi/Downloads/Content-Atelier-Solution-Architecture.md>
[taste-review]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/research/whitney-taste-and-editorial-pipeline.md>
[architecture-review]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/research/architecture-comparison-and-reconciled-design.md>
[chat-index]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/chatgpt/_INDEX.md>
[caption-chat]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/corpus/chatgpt/caption-strategy-summary.md>
[pgvector]: https://github.com/pgvector/pgvector
[pg-schemas]: https://www.postgresql.org/docs/current/ddl-schemas.html
[pg-textsearch]: https://www.postgresql.org/docs/current/textsearch-indexes.html
[pg-rls]: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
[slack-replies]: https://docs.slack.dev/reference/methods/conversations.replies/

