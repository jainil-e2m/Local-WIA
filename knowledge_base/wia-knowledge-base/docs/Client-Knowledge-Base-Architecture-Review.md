# Client Knowledge Base: Solution Architecture Review

**Date:** 26 October 2026 · **Baseline reviewed:** commit `a788ab7` (23 October 2026)
**Type:** Independent architecture validation · **Audience:** E2M engineering and WIA decision-makers
**Status:** Findings and recommendations for decision. This review changes no existing document, design or code.

---

## Documents and abbreviations

| Abbreviation | Document | Date |
|---|---|---|
| **SA** | [Solution Architecture](Client-Knowledge-Base-Solution-Architecture.md) | 20–21 Oct |
| **FR** | [Functional Requirements](functional_requirements.md) | 21 Oct |
| **FS** | [Feasibility Study](Client-Knowledge-Base-Feasibility-Study.md) | 20 Oct |
| **DR** | [Architecture Discovery and decision register (ARCH-Q01–Q23)](Client-Knowledge-Base-Architecture-Discovery.md) | 20 Oct |
| **GA** | [Technical Gap Analysis (TG-01–TG-22)](Client-Knowledge-Base-Architecture-Technical-Gap-Analysis.md) | 20 Oct |
| **CB** | [Chatbot scope](chatbot_KB.md) | 20–22 Oct |
| **TS-01…06** | Tab scopes in [`kb_tab_scope/`](../kb_tab_scope/): [Action Register](../kb_tab_scope/01-action-register.md), [Client Portfolio](../kb_tab_scope/02-client-portfolio.md), [Invoices & Contracts](../kb_tab_scope/03-invoices-contracts.md), [Health & Sentiment](../kb_tab_scope/04-health-sentiment.md), [Call Preparation](../kb_tab_scope/05-call-preparation.md), [Client 360](../kb_tab_scope/06-chatbot.md) | 22 Oct |
| **FE** | Frontend prototype in [`frontend/src`](../frontend/src) | 21–23 Oct |
| **CC** | WIA Command Center authentication code (`../WIA-Command-Center/server/`), inspected read-only because SA depends on it | — |

References use `DOC §section (Lnnn)`, where `Lnnn` is the line number in the reviewed commit.

### How to read the findings

**Priority**

- **Critical:** resolve before backend implementation starts. Building without resolving it produces rework or the wrong system.
- **High:** resolve before the affected capability is built or before Stage 1 launch.
- **Medium:** materially improves cost, risk or maintainability. Schedule during Stage 1.
- **Low:** hygiene or later-stage concerns.

**Type**

- **Flaw:** the design as specified will not work, or works against its own invariants.
- **Gap:** a capability that agreed or decided functionality needs and the architecture does not specify.
- **Inconsistency:** documents or code contradict each other.
- **Overengineering:** more mechanism than the requirement or scale justifies.
- **Risk:** the design may be right, but an unvalidated dependency or assumption could defeat it.
- **Insufficient information:** the documentation does not support a conclusion either way.

An unimplemented feature is not treated as a gap. No backend exists yet, and the frontend is an agreed mock. A finding is raised only when the *planning* is missing, contradictory or unsound.

---

## 1. Executive summary

### Verdict

**The core architecture is sound and well matched to the product. The documented architecture is not yet a safe basis for implementation.**

The foundational choices are correct for an internal system with about ten users serving 15–40 client businesses:

- a modular FastAPI monolith with PostgreSQL as the single system of record;
- evidence and provenance as first-class data;
- source observations kept separate from reviewed values;
- deterministic code for counts, states and money;
- LLMs confined to interpretation, with backend validation;
- permission filtering applied before retrieval and before any model context;
- idempotent at-least-once processing with a transactional outbox.

Rejecting a separate vector database, microservices and agent frameworks is the right call. Many of the domain invariants are exactly what this product needs and are often missed elsewhere: unknown is not zero, Done is not Verified, a date-only deadline is not an instant, and coverage is not completeness. These should be kept.

Four problems stand between the documents and a buildable system:

1. **The architecture is out of date (AR-01).** On 22–23 October the tab scopes and mockups decided about fifteen product behaviours that change architectural assumptions. They include:
   - outbound Slack and Gmail messaging;
   - WIA's own GoHighLevel (GHL) account as the finance ledger;
   - finance hidden from non-admins across every module;
   - owner-approved narratives;
   - admin-editable brief templates;
   - free-text "regenerate with instructions";
   - an extended action lifecycle;
   - a chatbot UI that removes the context entry points the cost model relied on.

   SA (21 October) reflects none of these. A developer building from SA would build the wrong system, and one building from the tab scopes would have no mechanisms.
2. **There is no minimum viable slice, and the dates are not achievable as specified (AR-02).** SA specifies the final state at uniform depth. That includes semantic intent routing, embedding reuse, HMAC cache manifests, fencing tokens, a global policy lock and evaluation regimes for an unscheduled chatbot. Today is 26 October. The development target of 6 November is 11 days away, and no backend code exists.
3. **An unresolved design fork sits on the critical path (AR-03).** "Hybrid versus Viktor-led" is evaluated *before* the Stage 1 screens are built (SA §14, L1491). The Viktor-led candidate conflicts with SA's own invariants: quote verification against the transient original, cursor checkpoints and coverage manifests. SA §4.9 already specifies direct connectors for all eight sources.
4. **The identity dependency does not exist (AR-04).** SA assumes a central provisioning and introspection API (SA §12.5). Inspection of Command Center shows:
   - users are configured through environment variables (at most 20 extra accounts);
   - the only roles are `team` and `client`;
   - there are no stable user IDs;
   - session revocation is held in memory;
   - there is no provisioning API.

   ARCH-Q04 therefore implies rebuilding another product's identity store on Stage 1's critical path.

The High findings concentrate on a few themes:

- the facts/excerpts-only retention decision has consequences the decision did not account for (AR-10);
- KB edits to ClickUp-mapped tasks will permanently diverge from ClickUp (AR-09);
- the module-level permission model cannot express the decided finance restrictions (AR-07);
- the human review load created by full historical backfill is unsized and may become the real bottleneck (AR-12);
- real client personal data is committed to the GitHub repository (AR-13).

### Readiness by dimension

| Dimension | Assessment | Key findings |
|---|---|---|
| Core data and evidence model | **Strong.** Correct separation of observations, reviewed values, evidence and lifecycle events | AR-08, AR-19 (extensions needed) |
| Processing, reliability and recovery | **Strong but over-built** for the scale | AR-15, AR-16 |
| Security and access policy | **Strong principles; gaps in the model's expressiveness and in dependencies** | AR-04, AR-07, AR-13, AR-21, AR-23 |
| AI and retrieval strategy | **Sound principles; one structural fork unresolved; chat over-specified** | AR-03, AR-10, AR-17 |
| Alignment with current product decisions | **Weak.** Material drift after 21 October | AR-01, AR-05, AR-06, AR-11 |
| Delivery feasibility | **Weak.** No Stage 1 cut; backfill and review load unsized | AR-02, AR-12 |
| Documentation as a development guide | **Weak.** Authoritative decision register missing from the repo, heavy repetition, 75 broken links | AR-14 |

### Before writing backend code

1. **Run a one-time reconciliation:** convert every 22–23 October decision into a decision record, and update SA where its mechanisms change (AR-01, §5.14).
2. **Decide that the KB owns retrieval for all eight sources.** Reframe the Viktor question as "which interpreter for which task", then remove it from the Stage 1 critical path (AR-03, §5.2).
3. **Choose a Stage 1 identity approach that needs no Command Center rebuild:** reuse the existing sign-in hand-off and provision manually (AR-04, §5.3).
4. **Approve a Stage 1 architecture slice and re-baseline the dates** after a no-LLM source inventory (AR-02, AR-12, §5.1, §5.10).
5. **Revalidate three decisions whose consequences are now visible:**
   - evidence retention (AR-10);
   - who is authoritative for ClickUp-mapped task fields (AR-09);
   - Slack and Gmail sending in Stage 1 (AR-05).
6. **Remove real client data from the GitHub repository** and add a root `.gitignore` (AR-13).

---

## 2. What is being built

This section summarises the understanding the review is based on, so that disagreements can be traced to their premise.

| Aspect | Understanding |
|---|---|
| **Purpose** | An owned, evidence-backed, maintained record of each WIA client business and its service engagements, plus an accountable register of what WIA and each client owe. It replaces repeated reconstruction across Slack, Gmail, ClickUp, Fathom/Zoom, Drive, Calendar and LeadLock, and much of today's ad-hoc use of Viktor in Slack |
| **Users** | About ten WIA team members, all potentially concurrent: founder/admin, operations coordinator, ads/account managers, the LeadLock specialist. Internal only; no client portal |
| **Scale** | 15–20 active clients, growing to 30–40. 59 LeadLock sub-accounts discovered. Source volumes are unknown |
| **Activation** | Stage 1: Action Register and Client Portfolio. Stage 2: Call Preparation. Stage 3: Health & Sentiment, Invoices & Contracts and Overview. Chatbot ("Client 360") is unsequenced (FR §2) |
| **Data obligation** | All obtainable history from all eight approved sources, for all active clients, processed before first launch, including data for later-stage features (FR-INT-02) |
| **Key invariants** | Unknown owner or date is never filled in. Assignment is not acknowledgement. Done is not Verified. A meeting commitment beats a ClickUp due date. Reviewed corrections survive re-extraction. Per-user read state is separate from resolution. Last successful sync never advances on failure. Permissions apply to every derived output |
| **Proposed stack** | React/Vite frontend (existing); FastAPI with synchronous SQLAlchemy 2, psycopg 3 and Alembic; PostgreSQL; Redis/RQ workers; OpenRouter and Viktor adapters; a dedicated Railway project |
| **Current state** | Documentation, a fictional-data frontend prototype with several design variants, and bounded live source probes (GET only). No backend, connector, schema or auth integration exists |

---

## 3. Architecture assessment

### 3.1 Strengths to preserve

| Design element | Why it is right | Reference |
|---|---|---|
| Modular monolith with separate worker processes | The right granularity for one team and about ten users. Avoids distributed-system overhead while isolating slow work | SA §2.3, §9.1 |
| PostgreSQL as the only store; no vector database until retrieval evaluation shows a benefit | Identity, access, lifecycle and money need relational integrity. Semantic search cannot count or establish current state | SA §3.2, FS §4 |
| Observation versus reviewed value versus read state | Prevents the most common failure of "AI knowledge bases": re-extraction silently overwriting human corrections | DR §5.3, SA §4.10 |
| Pure reducer with an explicit field-authority matrix | Testable, deterministic conflict handling. Avoids "newest wins" | SA §4.10 (L469–480) |
| Typed deadlines (`unknown` / `date` / `instant`) with no default midnight | Removes a whole class of false-overdue bugs | SA §4.8, §10.1 (L1247) |
| Separate progress, review, acknowledgement and verification dimensions | Correctly decomposes a concept the mock flattens into one status | SA §4.5, §6.6 |
| Permission filtering inside candidate queries, before ranking and before model context | Post-hoc filtering leaks and hurts recall. This is the correct order | SA §3.4, §3.8 |
| Withholding mixed-client content rather than trusting the LLM to redact it | Correct for shared programme channels and calls | SA §3.3, §3.8 (L264) |
| Transactional outbox, idempotency keys, `expected_revision`, crash-boundary matrix | Gives at-least-once delivery with idempotent effects; no exactly-once promises | SA §9.2, §9.6 |
| "Exactly-once database effects do not imply exactly-once provider billing" | Rarely understood; correctly handled through stored run references | SA §9.6 (L1101) |
| Synchronous SQLAlchemy, a single origin for SPA and API, Alembic as sole schema owner | Simple, conventional and low-risk | SA §2.5 |
| Exact money (`numeric` plus currency), no cross-currency sums, notification time distinct from transaction time | Correct finance hygiene | SA §10.3 (L1303), §4.18 |
| `404` for out-of-scope entities, `403` for denied operations on visible ones | Avoids existence leaks | SA §4.11 (L513) |
| Discipline about status: "verified" versus "proposed" versus "agreed" | Honest, and avoids promoting probes into capabilities | All documents |
| Tab scopes grounded in actual WIA workflows | Strong product thinking. The GHL-ledger discovery (TS-03 §2) is a genuine correction the architecture missed | TS-01…06 |
| FR catalogue with stable IDs | Excellent for traceability into tasks and acceptance tests | FR §17 |

### 3.2 Principal weaknesses

1. **Alignment:** the mechanisms in SA predate the product decisions they must support (AR-01, AR-05–AR-08, AR-11).
2. **Proportion:** the chatbot, cache, permission locking and ingestion are specified for a larger, more adversarial system than ten trusted internal users (AR-15–AR-18). Meanwhile the parts that decide whether Stage 1 succeeds are thin: backfill sizing, review load, ClickUp authority and identity.
3. **Decision hygiene:** two foundational forks remain open while dependent work is specified in detail: the background AI route, and chat Mode A versus Mode B. One agreed decision (Q3, excerpts only) undermines several later decisions (AR-10).
4. **Documentation as a tool:** the authoritative decision register (KB-CH-01…69), the FastAPI SOP and all source-scope files are referenced but absent from the repository. The same decisions are restated in five documents, and drift has already occurred (AR-14).

### 3.3 Assessment by dimension

**Overall design suitability: good.** The layered model (intake → identity → maintained records → interpretation → permissioned delivery → recovery, DR §1) maps cleanly onto services. The main suitability issue is the AI route fork (AR-03).

**Completeness against requirements: partial.**

- FR is well covered for the FR-ACT, FR-POR, FR-REV, FR-ADM and FR-INT series.
- Stage 2 and 3 decisions taken after FR are not covered: outbound messaging, the GHL ledger, narrative approval, templates, reply detection, health snapshots and the after-call loop.
- FR-OPS-03 (controlled reprocessing) conflicts with excerpts-only retention (AR-10).

**Component responsibilities and boundaries: mostly clear.** The service folders in SA Appendix A.1 are reasonable. There are three missing components:

- outbound communications (AR-05);
- generated-artifact lifecycle (AR-11);
- connector credential management (AR-21).

One boundary is unclear: who owns the truth for ClickUp-mapped fields (AR-09).

**Data architecture: strong core, incomplete extensions.** The SA §10 core tables are well designed. Decided features need entities that do not exist yet (AR-19). Business events, facts and artifacts need a data-domain classification to make finance restriction enforceable (AR-07).

**Data flows and integration: sound but heavy.** The intake contracts (SA §4.8) and per-source procedures (SA §4.9) are good. Webhooks as the primary path add infrastructure that the architecture's own five-minute reconciliation loop already makes redundant (AR-15). A new source domain, WIA's GHL billing, is not designed (AR-06).

**Scalability and performance: not a concern at runtime; a concern for backfill.**

- Ten users and 40 clients fit comfortably in one PostgreSQL instance and one API process.
- The binding constraints are backfill throughput (one `bulk` worker executing one job at a time, SA §2.5 L163), provider rate limits and human review capacity (AR-12).

**Reliability: well designed.** Outbox, leases, sweeps, idempotency and recovery runbooks are appropriate. They are over-engineered in one place: the dual queue (AR-16).

**Maintainability: at risk.** The cause is documentation structure and frontend variant sprawl, not code (AR-14, AR-20). The specification sets a high bar: every cache hit validates collection revisions, clock boundaries and policy fingerprints. That raises the cost of every feature. Phase it in only where it is needed.

**Security and privacy: strong policy; specific gaps.**

- Revocation, private chat, metadata-only admin views and webhook verification are well thought through.
- The gaps are:
  - expressiveness of the domain-level permission model (AR-07);
  - the outbound leakage surface (AR-05);
  - prompt-injection surfaces from templates and user instructions (AR-11);
  - credential ownership (AR-21);
  - LLM provider data handling (AR-23);
  - personal data already committed to the repository (AR-13).

**Extensibility: good.** Adapter protocols, typed contracts and the artifact/dependency model extend naturally to Stage 2 and 3, provided the artifact lifecycle is generalised (AR-11).

**Alignment with the existing implementation: weak, but expected for a mock.** The FE types, statuses and permission rules diverge from SA *and* from the tab scopes. Three Action Register variants coexist (AR-20).

---

## 4. Detailed findings

### Finding index

| ID | Title | Priority | Type |
|---|---|---|---|
| AR-01 | Architecture does not reflect the 22–23 October product decisions | Critical | Inconsistency / Gap |
| AR-02 | No Stage 1 architecture slice; full-depth specification against an 11-day development target | Critical | Risk / Gap |
| AR-03 | Background AI route left open on the critical path; Viktor-led retrieval conflicts with core invariants | Critical | Flaw |
| AR-04 | Central identity and provisioning dependency does not exist in Command Center | Critical | Risk (verified) |
| AR-05 | Outbound communications decided in tab scopes with no architecture | High (Critical if D8 is approved) | Gap |
| AR-06 | Finance source of truth moved to WIA's GHL account; not designed | High | Gap / Inconsistency |
| AR-07 | Module-level visibility cannot express decided finance restrictions; client-visibility model undecided | High | Flaw |
| AR-08 | Action domain model does not match agreed register behaviour | High | Gap |
| AR-09 | Read-only ClickUp plus editable KB causes permanent divergence for mapped tasks | High | Flaw |
| AR-10 | Excerpts-only retention conflicts with decided features and with "process everything now" | High | Risk / decision conflict |
| AR-11 | Generated-content lifecycle is unmodelled; template governance conflicts with Q19; new injection surfaces | High | Gap / Inconsistency |
| AR-12 | Backfill volume, throughput and human review load are unsized | High | Risk |
| AR-13 | Real client personal data is committed to the GitHub repository | High | Security |
| AR-14 | Authoritative decision register and SOP missing from the repo; drift-prone document structure | High | Documentation |
| AR-15 | Webhook-first ingestion is heavier than the freshness target requires | Medium | Overengineering |
| AR-16 | Two work-queue systems (PostgreSQL work/outbox plus Redis/RQ) | Medium | Overengineering |
| AR-17 | Chatbot specification depth does not fit its unsequenced status; cost model assumes removed UI | Medium | Overengineering / Inconsistency |
| AR-18 | Permission and locking machinery heavier than ten users require | Medium | Overengineering |
| AR-19 | Domain model gaps for decided Stage 1–3 features | Medium | Gap |
| AR-20 | Frontend is a design prototype; variant sprawl and business rules in components | Medium | Risk |
| AR-21 | Connector credential ownership and lifecycle unspecified | Medium | Risk |
| AR-22 | Client lifecycle behaviour undefined while lifecycle stage ships in Stage 1 | Medium | Gap |
| AR-23 | LLM and agent provider data governance unspecified | Medium | Gap |
| AR-24 | Observability tooling unspecified | Low | Insufficient information |
| AR-25 | Recovery depends on an unverified provider feature and one failure domain | Low | Risk |
| AR-26 | Repository hygiene | Low | Maintainability |

---

### AR-01 — Architecture does not reflect the 22–23 October product decisions

**Priority:** Critical · **Type:** Inconsistency / Gap

**Evidence.** SA was last revised on 21 October. The tab scopes (22 October) and FE commits (22–23 October) introduced decisions that change SA's mechanisms:

| Decision (source) | What SA says instead |
|---|---|
| D8: Slack notifications proposed for release 1, "changing KB-CH-38" (TS-01 §5a L156–180, L236) | "No register command in the first release writes a ClickUp task or sends a message" (SA §4.16 L635). "No business notification jobs are introduced" (SA §9.6 L1120) |
| F3/F4/C3/C4: Gmail chase drafts, daily overdue nudge, morning prep digest, agenda-to-client, follow-up emails (TS-03 L178–183, L205; TS-05 L83, L101, L133) | No outbound path exists in any section |
| F1: WIA's GHL location is the invoice/payment ledger (TS-03 L79, L256) | "HighLevel/LeadLock is not the established financial authority… This design does not silently add a new Dubsado API integration" (SA §4.18 L671–675) |
| F2: finance visible to admins only and hidden inside History, Profile, Handover, Call Prep and chat (TS-03 L190–197) | Client/module visibility only. Individual-field visibility is later scope (FR-ADM-03, L332) |
| P2: KB drafts the narrative and the account owner approves (TS-02 L122–127) | "Narrative lifecycle… remains intentionally deferred" (SA §1.4 L90, §4.14 L595) |
| C2: admin-editable call-type templates (TS-05 L47, L137) | Q19: prompts, skills and routing are version-controlled and evaluated; "Admins do not directly edit/activate them" (SA §8.4 L1015) |
| C7: "Regenerate with instructions", free text, versioned and carried into rebuilds (TS-05 L105–122) | Not specified |
| H2/H5: worst-signal category rule; AI "why" auto-published (TS-04 L70–80, L139–143) | Category rules and publication policy "require definition" (SA §4.17 L654) |
| Action statuses Open/In progress/Blocked/Done/Verified/Cancelled, Snoozed, verification only for flagged types (TS-01 L93, L111, L149) | `unknown | open | in_progress | done`; Verified for any action (SA §6.6 L867) |
| N2/N4: chatbot is one sidebar tab with no context buttons or suggested questions (TS-06 L35–45, L190–194; CB L120) | "No Chatbot entry exists in `ViewId`" (SA §4.19 L679, §4.12 L531). Context input with `view_key` and `displayed_snapshot_token` (L693) |
| Per-client visibility derived from ClickUp account teams (FE `ActionsTeams.tsx` L17–19) | Admin-configured client/module grants (SA §6.3) |

**Impact.** Neither document can be implemented alone:

- SA's mechanisms are missing whole subsystems (outbound messaging, GHL, artifact approval).
- The tab scopes have no mechanisms.

Inconsistent assumptions will be baked into the schema in the first migration, which is the most expensive place to fix them.

**Recommendation.**

1. Run one reconciliation pass now. Record each tab-scope "Decided" item as a decision record (ADR) with its SA impact, and update the affected SA sections. The designs in §5 of this review are proposed starting points.
2. Set a rule: tab scopes are authoritative for UX and business rules, and SA is authoritative for mechanisms. Any tab-scope decision that changes a mechanism must update SA in the same change.
3. Separate proposals from decisions. Several tab-scope items marked "Proposed" (D8, Escalation, Snooze) are already implemented in the mock, which blurs the difference.

---

### AR-02 — No Stage 1 architecture slice; full-depth specification against an 11-day development target

**Priority:** Critical · **Type:** Risk / Gap

**Evidence.**

- The targets are development on 6 November and launch on 26 November (FS L28; DR L51; SA §14 L1498). All three documents call them "not validated estimates". From today that is 11 and 31 days.
- GA classifies 17 of its 22 specification areas as P0 "needed for first-release correctness" (GA §4).
- SA specifies, at implementation depth, mechanisms that Stage 1 does not need:
  - cache manifests with HMAC keys, fencing and coalescing (SA §7.6);
  - evidence and query embedding reuse plus a semantic intent router (SA §7.7);
  - R0/R1/R2 evaluation (CB §13.15);
  - a global policy guard lock order (SA §6.6 L865);
  - row-level security for chat (SA §12.5 L1432).
- Stage 1 scope is growing in the tab scopes:
  - P4 adds Support, Accounts & sources, lifecycle and onboarding progress (TS-02 L273);
  - D5 leaves Register additions open;
  - P2 puts LLM-drafted, owner-approved narratives on the Stage 1 "Now" sub-tab.
- The build plan puts "Candidate evaluation" before "Portfolio/Actions" (SA §14 L1491).

**Impact.** With uniform depth and no cut line, engineering will either build infrastructure for Stage 3 and the chatbot before any Stage 1 screen works, or improvise the cut under deadline pressure. Neither the 6 November nor the 26 November target is credible for the specified scope: six or more connectors, central auth integration, extraction, reducer, review UI, frontend data layer and a full historical backfill with WIA sign-off.

**Recommendation.**

- Approve an explicit Stage 1 slice. Each mechanism should be marked *build now*, *build simplified* or *defer until measured need* (§5.1).
- Re-baseline the dates after the Phase 0 inventory (§5.10, §8).
- Keep every invariant, but defer the machinery that exists only for the chatbot, caching or Stage 3.
- Consider moving narrative drafting (P2) to Stage 2, where the brief-generation infrastructure is built anyway. Stage 1 "Now" would then use structured facts: latest client ask, blocked items and the commitments snapshot.

---

### AR-03 — Background AI route left open on the critical path; Viktor-led retrieval conflicts with core invariants

**Priority:** Critical · **Type:** Flaw

**Evidence.**

- Two candidates are retained: selective hybrid, and Viktor-led, in which "Viktor orchestration obtains/interprets the assigned material" (SA §8.2 L995–1001; FS §9 L333).
- SA's own invariants assume the KB holds the source material:
  - "Before retaining an excerpt, verify its quotation against the transient source" (SA §4.8 L444);
  - cursor and checkpoint advancement rules (L440);
  - backfill manifests with discovered, obtained, parsed and extracted counts (SA §4.10 L484);
  - "A provider adapter must expose what source/field coverage it actually obtained" (DR §4 L85).
- SA §4.9 already specifies direct synchronisation procedures for all eight sources. Original hydration (SA §3.8) and deletion detection also need KB-owned connectors.
- Viktor's workspace permissions do not map to KB permissions, and prompting is not isolation (SA §5.4 L805; CB §10 L265–271).
- Evaluation sits before the Stage 1 UI build (SA §14 L1491).

**Impact.** If Viktor retrieves the sources:

- the KB cannot verify quotes;
- it cannot account for coverage or advance cursors safely;
- it cannot detect deletions;
- it cannot re-fetch originals.

It would either need Viktor to return full originals, at which point Viktor is just an expensive connector proxy, or abandon those invariants. Meanwhile the KB must build direct connectors anyway for change detection, reconciliation and original fetch. Keeping the fork open also blocks the extraction contract, prompt work and cost model, all of which Stage 1 needs.

**Recommendation.**

1. **Decide now that the KB owns retrieval for all eight sources** through direct, read-only connectors. This is the "selective hybrid" baseline, and it is what SA §4.9 already designs.
2. **Reframe the remaining question as per-task interpreter selection.** For each LLM task (action extraction, profile facts, call brief, health "why"), which engine gives the best accepted output per unit of cost? Stage 1 can start with OpenRouter for extraction. Viktor skills can be evaluated for Stage 2 call preparation, where WIA reports real value (FS L32). This is a bounded A/B test on identical KB-supplied context, not an architecture fork (§5.2).
3. **Keep existing Viktor posts as attributed evidence,** as already agreed. Keep Viktor's ad monitoring outside the KB, as already agreed.
4. **Trade-off:** this narrows a user-retained option, so it needs WIA's explicit agreement (KB-CH-41). The rationale is structural, not cost-based.

---

### AR-04 — Central identity and provisioning dependency does not exist in Command Center

**Priority:** Critical · **Type:** Risk (verified by code inspection)

**Evidence.**

- ARCH-Q01/Q04 reuse Command Center authentication, and have KB admins provision central accounts through an API (DR L95, L98).
- SA §12.5 (L1434–1443) proposes `users:resolve`, `users` (create/link) and `sessions:introspect`, explicitly as "proposed required interfaces, not observed".
- Command Center today (`WIA-Command-Center/server/`):

| Aspect | What exists | Location |
|---|---|---|
| Accounts | One team account, one optional client account, and up to 20 extra accounts from `USER_n_*` environment variables. Adding a user means editing deployment variables and redeploying | `auth-core.mjs` L18, L34–42 |
| Roles | `["team", "client"]` only | `auth-core.mjs` L13 |
| Identity key | Email in an HMAC-signed token. No stable user ID | `auth-core.mjs` L152–166 |
| Revocation | In-memory list, lost on restart | `auth-core.mjs` L288 |
| Cross-app sign-in | Existing PKCE hand-off for Content Atelier with one-time, process-local codes. The downstream app holds the same session token and re-checks `/api/auth/session` | `atelier-sso.mjs` L27–32 |
| Session lifetime | Seven days | `index.mjs` L205 |

**Impact.**

- API provisioning requires Command Center to gain a persistent user store, stable subject IDs, a provisioning API with service authentication, durable revocation and a migration away from environment-variable accounts. That is a cross-product project with its own testing, owned outside the KB, on Stage 1's critical path.
- Email as the only identity key makes membership fragile if an address changes.
- A KB that trusts a seven-day Command Center token without introspection cannot honour central disabling promptly.

**Recommendation (§5.3).**

- For Stage 1, reuse the existing Atelier hand-off pattern unchanged. The KB issues its own short-lived session, re-validates against Command Center `/api/auth/session` on a short interval, and keeps its own membership and grants keyed by normalised email plus a KB user ID.
- Provision central accounts manually through Command Center's existing environment-variable process. With about ten users this is a small operational task. The KB "Add user" screen records membership as *pending central account* until the first successful sign-in.
- Schedule the Command Center identity store and provisioning API as a separate project, and update ARCH-Q04 to "target state".
- **Alternative to note, not recommend:** WIA appears to run Google Workspace (`hello@weddingindustryads.com`). Google OIDC would give stable subject IDs and Workspace-managed off-boarding at no build cost, but ARCH-Q01 explicitly did not select it. Revisit only if the Command Center work stalls.

---

### AR-05 — Outbound communications decided in tab scopes with no architecture

**Priority:** High (Critical if D8 is approved for Stage 1) · **Type:** Gap

**Evidence.**

| Outbound capability | Proposed or decided in |
|---|---|
| Slack posts to client channels, DMs to owners and an admin summary, from four entry points | TS-01 §5a, D8 |
| Handover brief "Send on Slack" | TS-02 L170 |
| Chase email drafts, optionally as Gmail drafts (needs the `compose` scope) | TS-03 F3/F7, L178–183, L262 |
| Daily overdue nudge | TS-03 F4, L205 |
| Monday review posted to Slack; "Notify owner" | TS-04 L101, L114 |
| Morning prep digest, agenda to client, follow-up email, team recap | TS-05 C3/C4, L83, L101, L133–134 |
| What it needs | Slack `chat:write` and `im:write`, which are "new write permission beyond the current read-only Slack access" (TS-01 L180) |

SA has no write connectors, no message entity, no send workflow and no staging rule beyond "never… trigger source writes" (SA §2.3 L142).

**Impact.** Outbound messaging is the highest-consequence capability in the product, because a mistake reaches a client. The specific risks are:

- **Client-visible channels:** a Slack Connect channel exposes internal wording such as "overdue" or "not acknowledged" to the client (D9, still open).
- **Cross-client leakage:** shared programme channels (`#meta-accelerator`) mix clients.
- **Finance leakage:** finance content can reach non-admin destinations.
- **LLM drafting errors:** a drafted client email may include another client's facts.
- **Duplicate sends:** retries can double-send, and Slack's `chat.postMessage` has no idempotency key.
- **Staging sends:** a test environment can message real clients.
- **Missing audit:** sends may not be logged on the action history.

**Recommendation.** Design a small, explicit outbound subsystem before any send feature is built (§5.6). Its core elements are:

- outbound messages as KB records with a draft → approved → sent lifecycle;
- deterministic content-scope checks before the Send button is enabled;
- a send outbox with uncertain-outcome reconciliation;
- a staging sink and a global kill switch;
- separate operation rights for sending.

Resolve D9 first. Prefer Gmail *drafts* over sends.

---

### AR-06 — Finance source of truth moved to WIA's GHL account; not designed

**Priority:** High · **Type:** Gap / Inconsistency

**Evidence.**

- TS-03 §2 (L18–38) establishes from the 2 September ops call that ongoing invoices, recurring payments and reminders live in **WIA's own GHL location**. Dubsado covers only signing and first payments.
- F1 decides that GHL is the ledger and requests invoice, payment and subscription read scopes (L79, L256).
- SA §4.18 (L671–675) treats Dubsado-through-Gmail as the only approved route and HighLevel as non-authoritative.
- The approved source list names "LeadLock/GHL" as client sub-account data (FR L362). WIA's own billing location is a different account, with a different authority and module, and with scopes that are currently denied (TS-03 L246).

**Impact.** Without this connector, Invoices & Contracts can never show overdue invoices, which is its primary daily use (TS-03 §7.1). Several things are undefined:

- the reconciliation between Dubsado and GHL (F5: is anyone billed in both?);
- billing plans and subscriptions, and missing-invoice detection;
- how the WIA billing location stays separate from LeadLock client locations, so the agency token cannot mix client lead data with WIA finance.

**Recommendation.**

- Record F1 as an approved source extension through an ADR. The data domain is new even if the vendor is not.
- Model a distinct `connector_account` for WIA billing (domain = finance) alongside LeadLock client locations (domain = leads).
- Add `subscriptions` and `billing_plans`, and reconciliation keys between Dubsado project/invoice identities and GHL invoices.
- Reuse SA's per-record `events_only | reconciled_ledger` basis, which fits this well.
- Request the scopes now, so their availability is known before Stage 3 planning.
- Bundle the LeadLock location-access request (H6) into the same request.

---

### AR-07 — Module-level visibility cannot express decided finance restrictions; client-visibility model undecided

**Priority:** High · **Type:** Flaw

**Evidence.**

- FR-ADM-03 (L332) offers client and whole module/section visibility, with field-level visibility as later scope.
- F2 hides the finance tab and the client sub-tab, **and** removes finance-derived content from the History Commercial lane, Profile signing dates, Handover lines, Call Prep and chat answers (TS-03 L190–197). TS-03 L197 notes that the mock leaks these today.
- SA tags evidence excerpts with a `module_key` (L1210). `business_events` (L1294), `fact_values` and `artifacts` (L1301) carry none, and artifacts are unique per target, kind and input signature.
- The FE v3 register derives per-client visibility from ClickUp account teams (`ActionsTeams.tsx` L17–19).
- TS-02 makes the account owner and "My clients" a release-1 feature (L48, L61).
- SA's model is explicit admin grants, with "one configured primary role per membership" (L1249).

**Impact.** If "module" means a UI tab, the finance restriction cannot be enforced. Finance facts appear on non-finance tabs, and a handover or brief generated once and shared across users will either leak finance lines or omit them for admins. Separately, if per-user client grants have to be maintained by hand, ten users across 40 clients means 400 grant decisions to keep current. A team-derived model is implied by the mock but has not been decided.

**Recommendation (§5.5).**

- Redefine "module" as a **data domain**: actions, communications, meetings, profile, support, programme, leads, health, finance, chat. Screens compose domains.
- Tag every business-content row (events, facts, excerpts, artifact sections) with its domain.
- Compose generated artifacts from domain-scoped sections, so a viewer sees only the sections their grants allow.
- Make the **account team** a first-class KB entity, edited in the KB and suggested from ClickUp. Derive default client visibility from team membership plus an "all clients" flag.
- Keep the agreed role and per-user Inherit/Allow/Deny model for *operations*.
- This stays within FR-ADM-03 (no per-field administration UI) while making F2 enforceable.

---

### AR-08 — Action domain model does not match agreed register behaviour

**Priority:** High · **Type:** Gap

**Evidence.** TS-01 and the FE use behaviours that SA §6.6 and §10.1 do not model:

| Behaviour | Where | SA coverage |
|---|---|---|
| Blocked, Cancelled statuses | TS-01 L93; FE `types.ts` L61 | Progress is `unknown | open | in_progress | done` (SA L867) |
| Snooze with reason, excluded from counts | TS-01 L111 | None |
| Verification only for flagged action types (D3) | TS-01 L149; FE `verifyRequired`, `actionType` | Verified is a universal dimension; no action type |
| Third-party side; "several people" as owner | TS-01 L91–92 | Single `owner_person_id`; no responsibility enum in schema |
| Programme-ops bucket excluded from client counts (D4) | TS-01 L48 | None |
| Internal notes | TS-01 L108 | None (user-generated content with retention implications) |
| Reassign all, bulk with re-acknowledgement | TS-01 L133 | Single-field corrections only |
| Deadline-change requests approved by admins | FE `ActionsRevised.tsx` L11–13; `types.ts` L86 | Correction proposals (equivalent concept, different shape) |
| Dismissed review items never recreated | TS-01 L127 | Principle stated (SA §6.5); no dismissed state or suppression key |
| Priority | FE `types.ts` L84 | TS-01 L198 says "skip for now" |

**Impact.** The action table is the first and most-used schema. Retrofitting states and dimensions after the reducer, counts and projections exist is expensive, and changes every count predicate shared across the Register, Portfolio, Overview and briefs.

**Recommendation.** Adopt the reconciled model in §5.4. In summary:

- add `blocked` and `cancelled` progress;
- add a candidate / active / dismissed / archived lifecycle;
- treat snooze as an overlay;
- derive `verification_required` from action type;
- one accountable owner plus optional collaborators;
- a `classification` field for programme ops;
- deadline-change requests implemented as correction proposals;
- bulk reassignment as one batched command.

Decide snooze-versus-overdue semantics, multi-owner and priority explicitly.

---

### AR-09 — Read-only ClickUp plus editable KB causes permanent divergence for mapped tasks

**Priority:** High · **Type:** Flaw

**Evidence.**

- "Audited KB correction changes the maintained KB view, not the underlying provider record" (SA §6.5 L841).
- Users can edit owner and deadline, mark Done, and Block or Unblock from the drawer (TS-01 L109–110).
- ClickUp creation is "later" (FR L84), and no field write-back is planned.
- WIA's team works in ClickUp daily (TS-01 L16: the ops coordinator's own ClickUp filter).
- The reducer keeps reviewed corrections over later source changes and raises conflicts (SA §4.10).

**Impact.**

- Every KB edit to a mapped task creates a lasting difference from ClickUp.
- Every later ClickUp change to that field creates a new conflict.
- Users must update two tools, and the KB stops being trusted.
- For progress the semantics are undefined. If the KB marks a task Done and ClickUp keeps it open, Q23's reopening rule does not fire, because there is no transition. The two systems simply disagree indefinitely.

**Recommendation.** Decide field authority for mapped tasks explicitly. Options:

| Option | Behaviour | Trade-off |
|---|---|---|
| **A (recommended for Stage 1)** | ClickUp is authoritative for owner, due date and status of mapped tasks. The KB drawer shows "Edit in ClickUp" (deep link) for these fields. KB-only fields (acknowledgement, verification, notes, snooze, client-side responsibility) stay editable. The meeting-beats-ClickUp deadline rule shows as a conflict badge | Simplest. No write scopes. One source of truth. A slightly worse UX for mapped tasks |
| B | Field write-back to ClickUp (owner, due, status) through the outbound subsystem (§5.6), with review | Best UX. Brings ClickUp write scopes and failure handling into Stage 1 |
| C | Status quo (KB corrections persist, conflicts accumulate) | Divergence and double entry. Not recommended |

KB-originated actions (from Slack, Gmail or meetings) remain fully editable in the KB under every option.

---

### AR-10 — Excerpts-only retention conflicts with decided features and with "process everything now"

**Priority:** High · **Type:** Risk / decision conflict (an agreed decision whose consequences need revalidation)

**Evidence.**

- ARCH-Q03 (DR L103, §5.2 L134–143) retains extracted facts, supporting excerpts and metadata only, and fetches originals on demand.
- These later decisions need broader text or metadata:

| Need | Why excerpts are insufficient | Reference |
|---|---|---|
| "What was discussed in the last call?" | Recall needs the transcript, not only the extracted commitments. Under Mode A it is answerable only from excerpts | CB §3 L61; SA §3.6 |
| Client voice feed: every client statement classified | Retaining every client statement as an "excerpt" is close to retaining the message corpus | TS-04 L127–128 |
| "Waiting on us" reply detection | Needs per-message sender, thread and time for all client threads | TS-04 L169 |
| "Include everything Sarah said about pricing since August" | Free-text research over the full corpus | TS-05 L110 |
| Controlled reprocessing when extractors change | Every reprocessing re-fetches history from eight providers, some of it deleted or unavailable | FR-OPS-03 L373 |
| Full-text search | Finds only what an extractor chose to keep | FR-EVI-02 |
| Prelaunch processing for Stage 2–3 features whose definitions are not agreed | Extraction contracts for health, leads and finance will change after definitions land. Without retained text, the whole history must be re-fetched from providers | FR-INT-02 L350; FR §18 L385–398 |

**Impact.** The decision trades storage and privacy minimisation for permanent dependence on eight provider APIs, for reprocessing, recall and new features. The last row is the sharpest: "process all history before launch for later features", combined with "retain only what today's extractor selects" and "later definitions not yet agreed", guarantees a second full-history fetch. It also weakens chatbot Mode A before it is tested.

**Recommendation.** Ask WIA to revalidate Q3 with the consequences above (§5.9). The lowest-friction resolution uses the already agreed Q16 mechanism: add a **retained normalised text** category per source type (transcripts, client communications, documents) with an admin-configured duration. A duration of zero is equivalent to today's decision, and a long duration removes most re-fetching. At minimum, retain message-level metadata (sender, thread, timestamps, hash) for all in-scope messages to support reply detection and coverage. If Q3 stands unchanged, limit prelaunch processing for Stage 2–3 features to *inventory and coverage*, and defer their extraction until their contracts are final.

---

### AR-11 — Generated-content lifecycle is unmodelled; template governance conflicts with Q19; new injection surfaces

**Priority:** High · **Type:** Gap / Inconsistency

**Evidence.**

| Behaviour | Source |
|---|---|
| Narrative drafts: draft → owner approves, edits or discards → stale when newer evidence arrives; the next draft starts from the approved text | TS-02 P2, L122–127 |
| Health "why" summaries auto-published, labelled, with a flag-and-regenerate loop | TS-04 H5, L139–143 |
| Call-brief versions with user instructions; a "current" version; rebuilds keep the instructions | TS-05 C7, L105–122 |
| Admin-editable call-type templates (sections, agenda skeleton, leave-out list, detection patterns, length) | TS-05 C2, L137–138 |
| Pinned chat answers that show when their sources change | TS-06 N4, L164 |

- SA's `artifacts` table (L1301) has kind, payload, versions and an input manifest, but no lifecycle states, approver, lineage, current pointer, instructions or per-scope sections.
- SA §8.4 (L1015) says business text fields must not become "an arbitrary prompt/tool injection mechanism".

**Impact.**

- Without a shared artifact lifecycle, each tab invents its own draft and staleness logic.
- Admin templates and user instructions are new prompt-injection and scope-widening surfaces. For example, "check their website" or "include invoice status" from a non-admin. TS-05 requires refusal, but no mechanism enforces it.
- Q19 and C2 contradict each other unless templates are defined as structured configuration rather than prompt text.

**Recommendation (§5.7).**

- Generalise `artifacts` with a state machine (building, draft, published, approved, stale, superseded, rejected, failed) and a per-kind approval policy: auto-publish, owner approval or on demand.
- Add lineage, a current pointer, stored instructions and domain-scoped sections.
- Define templates as **schema-validated configuration** from fixed catalogues: section toggles, an agenda skeleton of short items, leave-out options, a length setting. The template is rendered as delimited data into a code-owned, version-controlled prompt. Template changes publish through a preview on fixtures.
- Map user instructions to typed retrieval parameters, validated against permissions. Free text may affect tone and emphasis only.

---

### AR-12 — Backfill volume, throughput and human review load are unsized

**Priority:** High · **Type:** Risk

**Evidence.**

- Full history for all active clients across eight sources is a launch condition (FR-INT-02 L350; FS §5 L239–251).
- Volumes are unknown, and "backfill cost and duration require actual… totals" (FS L440).
- Samples: 2,664 Slack messages in six channels (FS L114), 338 ClickUp tasks in five lists (L116), and 245–700 transcript segments per Fathom meeting (FS Appendix A).
- Runtime: one `bulk` worker process, where "an RQ worker executes one job at a time" (SA §2.5 L163, A.4 L1726), with one extraction window per job and a 240-second timeout (SA §9.6 L1107, L1116).
- D2 expects "a large first-day triage queue" and plans a bulk dismiss pass (TS-01 L151). The mock has no bulk triage (TS-01 L248).
- There is one named operations reviewer, and named reviewers are still open (D6).

**Impact.** An illustrative calculation follows. The assumptions are stated and are not measurements.

| Assumption | Value |
|---|---|
| Active clients | 30 |
| Recorded calls per client per month | 2 |
| History | 18 months |
| Tokens per transcript | ~20k |
| Extraction windows per transcript | ~4 (6k-token windows) |
| LLM latency per window | ~30 s |

| Result | Value |
|---|---|
| Transcripts | ~1,080 |
| Windows | ~4,300 |
| Serial time on one bulk worker, meetings only | ~36 hours, before Slack, Gmail, Drive and ClickUp |
| Input tokens | ~22M |
| LLM cost at the FS reference rate ($3/M input) | ~$65–100 |

The conclusion holds across reasonable assumptions: **LLM cost is unlikely to be the constraint. Throughput, provider rate limits and especially human review volume are.** The design routes every ambiguity to review: identity in shared programme channels, stale asks, conflicts, AI proposals, mapping suggestions and unmatched finance events. A review backlog in the thousands at launch would make the Register unusable. This is the failure mode TS-01 §1 names explicitly: "If the register shows everything ever mentioned, nobody will use it."

**Recommendation (§5.10).**

1. Run a **no-LLM inventory** across all sources (counts, date ranges, token estimates) in Phase 0.
2. Run a **two-to-three-client dry run** through extraction, including one client in a shared programme channel. Measure review items per client per source.
3. Set an explicit **historical-action policy:** only open ClickUp tasks and asks with activity in the last 30 days (D2) become action candidates. Older unresolved asks become *history events*, not review items. This matches FS L146: "absence of closure alone does not establish current open work".
4. Run backfill extraction with bounded parallelism (N bulk processes or async batching) within provider limits.
5. Build bulk review tools in Stage 1.

---

### AR-13 — Real client personal data is committed to the GitHub repository

**Priority:** High · **Type:** Security / privacy

**Evidence.**

- `verification/**/*.json` (about 3.5 MB) contains raw live-probe responses. For example, `verification/calendar/live_probe.json` holds calendar event samples (up to 200 events per sampled calendar) with about 169 distinct email addresses.
- `calendar/followup_probe.json` has about 81, `google/followup_probe.json` about 24 and `gmail/live_probe.json` about 16. The Fathom and Drive probes contain more.
- The repository has an `origin` at `github.com/kenil-e2m/wia-knowledge-base`, and these files are in its history.
- No credentials were found: the token fields in the probe outputs are booleans.
- There is no root `.gitignore`. Only `frontend/.gitignore` exists, and it excludes neither `.env` nor `.data`.

**Impact.** Client and contact personal data sits outside WIA's systems, in a repository whose access is controlled by an individual account, and it stays in git history even if the files are deleted. This contradicts the KB's own data principles: no raw JSON bodies retained (DR §5.2 L137), controlled staging data (ARCH-Q14) and category retention. The backend will add `.env` files with connector secrets, and nothing currently prevents committing them.

**Recommendation.** This is the repository owner's decision. It involves rewriting shared history, so it is not done as part of this review.

1. Confirm the repository's visibility and collaborators.
2. Move the probe outputs to restricted storage, and purge them from history (for example `git filter-repo`), coordinating with everyone who has a clone.
3. Keep only redacted summaries (counts, shapes, status codes) in git.
4. Add a root `.gitignore` covering `.env*`, `.data/`, probe output folders and `dist*`.
5. Adopt a rule that future verification scripts write raw responses outside the repository.

---

### AR-14 — Authoritative decision register and SOP missing from the repo; drift-prone document structure

**Priority:** High · **Type:** Documentation

**Evidence.**

- **75 broken relative links to 19 distinct targets** across the docs. They include:
  - `knowledgebase_changes.md` (13 links): the KB-CH-01…69 decision register that every document cites as authoritative;
  - `backend_build.md` (5 links): the FastAPI SOP that defines the required backend layout (SA A.1);
  - `tobeverified_knowledgebase.md`, `tobeclarified.md` and `tobeverified.md`: the verification and clarification registers;
  - all seven `*_scope.md` source files;
  - `knowledge_base_viktor_llm_comparison.md` and `MAINTAINED_CLIENT_KNOWLEDGE_BASE_ARCHITECTURE.md`.
- `chatbot_KB.md` is linked as `../../../chatbot_KB.md` (12 links), although it lives in `docs/`.
- The ARCH-Q01–Q23 decisions are restated in DR, FS, SA, CB and FR. Drift has followed: CB records the 22 October chatbot change (L120) and SA does not.
- GA §8 says TG-01–22 are covered, but several promised artifacts are absent:
  - TG-05 per-source sequence diagrams;
  - TG-11 sign-in and Add-user sequence diagrams and failure table;
  - most of the TG-20 dashboards.
- SA mixes requirement, decision, proposal and caveat in nearly every paragraph. For example, "proposed", "not verified" and "remains to configure" each appear dozens of times. That makes the implementable specification hard to extract.
- The frontend README's run path points to another machine (`C:\Users\Jainil Trivedi\…`).

**Impact.**

- Developers cannot verify a decision's wording or date.
- New team members cannot find the SOP that the layout depends on.
- Every future decision must be edited in five places, which guarantees more drift.

**Recommendation (§5.14).**

- Import the decision register, SOP, verification registers and source-scope files into the repository, and fix the links.
- Move to a single ADR log, with documents linking to decision IDs instead of restating them.
- Split SA into a concise mechanism specification (what to build) and a status annex (what is unverified).
- Correct GA §8's coverage claims.

---

### AR-15 — Webhook-first ingestion is heavier than the freshness target requires

**Priority:** Medium · **Type:** Overengineering

**Evidence.**

- SA §4.9 specifies push mechanisms as the primary path:
  - Gmail watch through Cloud Pub/Sub;
  - Drive and Calendar notification channels with renewal;
  - Slack Events;
  - ClickUp and Fathom signed webhooks;
  - public `/hooks/{provider}/{connection}` endpoints with two-second acknowledgement.
- SA *also* schedules "missed-change reconciliation every five minutes per eligible source scope" (L1120), and allocates five minutes of the fifteen-minute budget to detection (L1126).

**Impact.** A five-minute incremental poll meets the freshness budget by itself. Webhooks add:

- a Google Cloud Pub/Sub project and IAM;
- channel renewal jobs;
- five signature-verification implementations;
- public attack surface;
- deduplication between signal and poll;
- harder local development and staging isolation (watch identities must not collide, per SA §2.3).

At 40 clients the API cost of polling is negligible.

**Recommendation.** Make **polling incremental sync the Stage 1 mechanism** for every source, using each provider's native cursor (§5.8). Add a webhook only where a measured latency need appears, for example Fathom for the after-call loop, or Slack Events for near-real-time reaction acknowledgement.

Verify Slack rate limits early. In 2025 Slack reduced `conversations.history` and `conversations.replies` limits for commercially distributed non-Marketplace apps. Internal customer-built apps are described as unaffected, but the treatment of internal apps created after 29 May 2025 is worded inconsistently ([Slack rate limits](https://docs.slack.dev/apis/web-api/rate-limits), [2025 changelog](https://api.slack.com/changelog/2025-05-terms-rate-limit-update-and-faq), [clarification](https://docs.slack.dev/changelog/2025/06/03/rate-limits-clarity)). Create the KB app as an internal app in WIA's workspace and confirm its limits before relying on history polling.

---

### AR-16 — Two work-queue systems (PostgreSQL work/outbox plus Redis/RQ)

**Priority:** Medium · **Type:** Overengineering

**Evidence.** SA §9.6 (L1095–1101) persists `work_items` with leases, attempts, fencing tokens and `next_run_at`. A dispatcher claims outbox rows with `FOR UPDATE SKIP LOCKED`, enqueues IDs into RQ, and a sweep rediscovers work lost in Redis. Workers then re-claim in PostgreSQL before executing. All correctness lives in PostgreSQL. RQ adds dispatch, one-job-per-process execution and a second failure domain. RQ also does not run natively on Windows, which the team uses (SA A.4 L1807 acknowledges this with Linux Docker workers).

**Impact.** Two queue systems mean double the failure modes (lost dispatch, duplicate enqueue, sweep races), the dispatcher and sweep code, and Redis as a required service. In return there is no capability PostgreSQL does not already provide at this scale.

**Recommendation.**

- **Preferred:** a PostgreSQL-only worker loop. Workers claim due `work_items` with `SKIP LOCKED` and run them in per-lane process pools, using the leases and fencing SA already specifies. Redis becomes optional; nothing else in Stage 1 needs it once answer caches are deferred (AR-17). This deviates from the SOP's Redis/RQ pattern and needs the SOP owner's approval.
- **If the SOP is binding:** keep RQ as best-effort transport, with the PostgreSQL sweep as the source of truth, and drop dispatch-receipt bookkeeping.

---

### AR-17 — Chatbot specification depth does not fit its unsequenced status; cost model assumes removed UI

**Priority:** Medium · **Type:** Overengineering / Inconsistency

**Evidence.**

- The chatbot has no delivery position (FR §10).
- SA §7.6–7.7 and CB §13.11–13.15 nonetheless specify:
  - HMAC cache manifests, in-flight coalescing and fencing;
  - versioned evidence and query embedding reuse;
  - a calibrated semantic intent router;
  - a three-variant evaluation.
- The cheapest path assumed "contextual buttons/suggested questions can send an approved intent… avoiding model interpretation entirely" (CB §13.2 L335). N2 removed the context buttons and N4 removed personalised suggested questions (TS-06 L190–194). SA §4.19 (L693) still specifies context input with `view_key` and `displayed_snapshot_token`, which the UI no longer produces.

**Impact.** The cost case for answer caching is weak at this scale. SA's own workload assumption is 2,200 questions a month (SA §15.4). At the FS reference rate (about $0.05 per 10k-in/1k-out call), that is roughly **$110–$220 a month** in generation. A plausible 20–30% valid reuse saves tens of dollars a month. Against that sits the implementation and QA cost of dependency-validated answer caching, which SA itself shows must handle collection revisions, clock boundaries, permissions, private context and restores.

**Recommendation.** When chat is scheduled, build it in this order:

1. Typed read tools over the same query services as the screens.
2. One bounded tool-calling LLM loop.
3. Deterministic definitions.
4. Backend citation validation.
5. **No answer cache, no embeddings and no semantic router** until retrieval QA and measured volume justify them.

KB-CH-68 remains the agreed future method, and A.4 already disables it by default. This only makes the order explicit. Pinned answers (N4) need only "cited record revisions changed?" checks, not collection-level manifests. Update SA §4.19 for N2 and N4.

---

### AR-18 — Permission and locking machinery heavier than ten users require

**Priority:** Medium · **Type:** Overengineering (keep the agreed semantics, simplify the mechanism)

**Evidence.**

- Every content mutation takes a shared global policy guard, and every grant change takes it exclusively (`policy_epoch`, SA §6.6 L865, §10.1 L1219, §12.5 L1432).
- Row-level security for chat tables is recommended, with transaction-local actor context.
- Membership revisions invalidate caches.
- The user base is about ten people with two admins. Grant changes happen a few times a month.

**Impact.** The extra lock in every mutation adds lock-ordering rules that every developer must follow. Row-level security with a pooled connection needs careful session handling. Both are sources of subtle bugs that buy little at this scale.

**Recommendation.**

- Implement effective permissions as one pure, heavily tested function.
- Inside mutation transactions, re-read the actor's membership and grant revision (`SELECT … FOR SHARE` on the membership row) instead of taking a global guard.
- Make row-level security an optional hardening step after Stage 1.
- Keep the agreed Inherit/Allow/Deny precedence and the self-verification checks exactly as specified.

---

### AR-19 — Domain model gaps for decided Stage 1–3 features

**Priority:** Medium · **Type:** Gap

The SA §10 tables need these additions. Items covered by AR-06, AR-08 and AR-11 are not repeated.

| Feature | Missing entity or field | Stage |
|---|---|---|
| "My clients", account owner, handover trigger (TS-02 P4) | `account_team_members(business_id, user_id, role, is_owner)` | 1 |
| Lifecycle stage and onboarding phase (TS-02 L60, L118) | `businesses.lifecycle_stage`, onboarding phase/steps projection from ClickUp | 1 |
| "My actions", acknowledgement, self-verification | `kb_users.person_id` link (KB user ↔ person ↔ provider identities). SA compares "mapped person ID" (L1430) but defines no link | 1 |
| Accounts & sources sub-tab, mapping suggestions (TS-02 B9) | `mapping_suggestions` (candidate resource, suggested business, evidence, decision) | 1 |
| Quick links | Covered by `business_account_links` (SA L1290) | — |
| "Waiting on us", last contact (TS-02 L64, TS-04 L169) | `conversation_threads` (business, channel, last client message, last WIA reply, state) from message metadata | 1 (last contact) / 3 |
| Client voice feed (TS-04 E) | `client_statements` (excerpt, speaker person, class: praise/concern/question/request/decision) | 3 |
| Health grid, trend, "changed this week" (TS-04 B, L99, L115) | `health_dimension_states` and immutable weekly `assessment_snapshots` | 3 |
| Call-type templates, brief versions, after-call recap (TS-05) | `brief_templates` (versioned), artifact lineage (AR-11), `call_recaps` | 2 |
| Pinned answers (TS-06 N4) | `chat_pins(thread, message, cited_revisions)` | Chat |
| Programme ops tasks (D4) | `actions.classification` (AR-08) | 1 |
| Support issue ↔ fixing action link (TS-02 B10) | `support_issue_actions` link | 1 |
| Outbound messages (AR-05) | `outbound_messages`, `outbound_batches` | per D8 |

---

### AR-20 — Frontend is a design prototype; variant sprawl and business rules in components

**Priority:** Medium · **Type:** Risk

**Evidence.**

- Three Action Register variants (`actions`, `actions-v2`, `actions-v3`) and two Call Prep variants (`calls`, `calls-v2`) are routed and appear in the sidebar together (`App.tsx` L26; `Sidebar.tsx` L12–15).
- The variants use different rules:
  - v1 has snooze;
  - v2 replaces snooze with admin-approved deadline requests (`ActionsRevised.tsx` L11–13);
  - v3 adds team-derived visibility (`ActionsTeams.tsx` L17–19);
  - Call Prep v2 builds "2 hours before each call" (`CallPrepV2.tsx` L33), while TS-05 says "evening before, refreshed 2 hours before" (L149–150).
- TS-01 describes v1.
- Business rules live in TypeScript:
  - `isOverdue` uses a demo date (`data.ts` L138);
  - the worst-signal health rule (`health.ts` L2);
  - finance totals and the self-verification rule (`Actions.tsx` L438).
- All state is in one `App` component, with hash routing and `localStorage` persistence (`App.tsx` L25, L39–45, L63).
- Comments are stale: `types.ts` L3–4 and L169–170 still describe "Ask about this" buttons and a side panel that N2 removed.

**Impact.** "Retain the existing React frontend" (DR L35) is reasonable for components, styling and UX, but the application architecture (data, routing, auth, errors, permissions) must be rebuilt. SA §14 step 6 treats "Replace mock data/mutations" as one step, which underestimates it. Unresolved variants are unresolved product decisions in disguise.

**Recommendation (§5.13).**

1. Choose one canonical variant per tab and record the rule differences as decisions.
2. Add a typed API client generated from FastAPI's OpenAPI schema, a server-state library (for example TanStack Query) and a real router.
3. Gate stages and features from `GET /session`.
4. Render from `allowed_actions`.
5. Move every business rule to the backend.
6. Keep the design system and components.

---

### AR-21 — Connector credential ownership and lifecycle unspecified

**Priority:** Medium · **Type:** Risk

**Evidence.**

- The probes use `CLICKUP_TOKEN` (typically a personal token), a per-user `FATHOM_API_KEY`, user-consented Google OAuth refresh tokens for the shared mailbox (`verification/google/oauth_store.mjs`), GHL agency and location PITs, and a Slack bot token.
- The Fathom key-confusion incident (FS L15; SA §1.2 L67) shows the identity risk.
- SA keeps secrets server-side and validates connector identity (SA §5.2, §12.4), which is good. It does not cover:
  - credential ownership;
  - rotation;
  - expiry monitoring;
  - what happens when the person whose token is used leaves WIA.

**Impact.** Personal tokens tie the KB to an individual's account. Off-boarding that person silently stops ingestion, or, worse, keeps a departed person's access alive. This sits awkwardly with the product's turnover-proofing goal.

**Recommendation.**

- Add a connector registry (`connector_accounts`) with provider account identity, credential type, owning person, scopes, created and expiry dates, and last verification.
- Prefer service identities: a dedicated ClickUp integration user; for Google, a dedicated integration account or domain-wide delegation limited to read-only scopes (trade-off: delegation needs Workspace admin setup and is powerful); the Slack bot token installed in WIA's workspace.
- Add an expiry and rotation runbook, plus an off-boarding checklist step.

---

### AR-22 — Client lifecycle behaviour undefined while lifecycle stage ships in Stage 1

**Priority:** Medium · **Type:** Gap

**Evidence.**

- FR §18 (L397) lists "Behaviour when a client/engagement becomes inactive, including future ingestion and retained history" as open.
- TS-02 puts Onboarding, Active, Paused and Offboarding into release 1 (L60, P4), with stage names still open (P6).
- Former-client retention is a category (SA §7.5), and former-client archive intake is out of scope.

**Impact.** Ingestion, counts, visibility, review routing and retention all depend on lifecycle. Without rules, paused clients keep generating review items, and offboarded clients' data has no defined end.

**Recommendation.** Define a simple rule set in an ADR. A proposal:

| Stage | Behaviour |
|---|---|
| Onboarding, Active, Paused | Ingest normally. Paused clients are excluded from overdue escalation |
| Offboarding | Ingest until a set end date, then freeze |
| Former | Read-only. No ingestion. The retention category applies. Excluded from default lists |

Engagement-level status is independent of business-level status.

---

### AR-23 — LLM and agent provider data governance unspecified

**Priority:** Medium · **Type:** Gap

**Evidence.**

- "Provider data-routing settings… remain to configure" (SA §12.4 L1426).
- OpenRouter routes requests to many underlying providers with different retention and training policies.
- Viktor's workspace, memory and connections can retain the context the KB sends it (CB §10 L267).
- Client communications, finance (admin-only) and personal data would all flow to these providers.

**Impact.** Without an explicit policy, client data may be retained or used by third parties in ways WIA has not agreed. This is also a client-trust risk for an agency.

**Recommendation.**

- Decide a provider policy before the first extraction run: restrict OpenRouter routing to providers with no training and zero or minimal retention, using account and per-request provider preferences, and pin model endpoints.
- Keep finance data out of LLM context unless a feature needs it.
- Document what Viktor retains.
- Check the agreements WIA has with clients for any restrictions on processors.

---

### AR-24 — Observability tooling unspecified

**Priority:** Low · **Type:** Insufficient information

SA §9.4 lists the right metrics: lag, coverage, queue age, review age, cost per accepted output. It names no tooling. Recommendation:

- structured JSON logs with PII redaction at the logger;
- an error tracker with body scrubbing;
- an in-app operations page, which also serves FR-OPS-01 and FR-ADM-09;
- an external uptime check.

Decide during scaffold.

---

### AR-25 — Recovery depends on an unverified provider feature and one failure domain

**Priority:** Low · **Type:** Risk

The one-hour and four-hour targets depend on Railway PostgreSQL point-in-time recovery (SA §9.5 L1087), which has not been verified for WIA's plan. All copies sit with one provider. Recommendation:

- verify PITR on the actual plan in Phase 1;
- add a daily logical dump to object storage outside Railway, to cover account or provider loss;
- run one restore drill before launch, as SA already proposes.

---

### AR-26 — Repository hygiene

**Priority:** Low · **Type:** Maintainability

- `frontend/exports/` commits built HTML (5,655, 8,189 and 2,237 lines) and `_backup-2026-10-22/` copies of source files.
- The export build bundles the Agentation dev toolbar.
- There is no root `.gitignore` (see AR-13).

Recommendation: produce exports in CI or locally and publish them as artifacts rather than source; delete the backup copies (git history is the backup); add a root `.gitignore`.

---

## 5. Recommended resolutions

This section holds the concrete design proposals the findings refer to. Each is a starting point for an ADR, not a final specification.

### 5.1 Stage 1 architecture slice (AR-02)

| Area | Build now | Build simplified | Defer until needed |
|---|---|---|---|
| **Data** | Registry (businesses, engagements, people, identity links, account teams); source records and versions; evidence excerpts with scope and domain links; observations and fact values; actions with events, acknowledgements and verifications; corrections, reviews and changes with read state; memberships, roles, overrides and grants; work items; audit; coverage windows | — | Commercial, health, attendance and lead tables beyond what backfill inventory needs; chat tables |
| **Connectors** | ClickUp, Slack, Gmail, Fathom (action sources); Drive (questionnaires, transcript archives); Calendar (next call on cards); historical Zoom archive (one-off) | **Polling** incremental sync (§5.8) | Webhooks; GHL billing (Stage 3, but request scopes now); LeadLock outcomes (blocked on access) |
| **AI** | Action and profile-fact extraction through one OpenRouter endpoint; versioned prompts in the repo; span validation; one bounded repair | Single interpreter, no candidate routing | Viktor skills (Stage 2 evaluation); embeddings; semantic search; narrative drafts (consider Stage 2) |
| **Domain logic** | Reducer, field authority, action state machine (§5.4), review queue with **bulk** actions, per-user read state | Mapped-task authority option A (AR-09) | — |
| **Access** | Command Center hand-off, KB session and membership; effective-permission function; domain-based visibility (§5.5) | Manual central provisioning (§5.3) | Central provisioning API; row-level security |
| **Execution** | Durable `work_items` with leases and fencing; per-lane workers | **PostgreSQL-only queue** (AR-16) | Redis; answer caches; coalescing |
| **API and frontend** | Session, clients and record sections, actions, corrections and reviews, changes and read state, citations, full-text search, coverage | Generated TypeScript client; canonical variants | Overview (Stage 3); chat |
| **Operations** | Staging environment, structured logs, error tracking, PITR check, daily external dump, one restore drill | — | Monthly drills, dashboards beyond the operations page |
| **Outbound** | Nothing, unless D8 is approved. If it is, the minimal §5.6 design for Slack only | — | Gmail drafts (Stage 3), digests (Stage 2) |

### 5.2 Retrieval ownership and interpreter selection (AR-03)

```text
Sources --(KB-owned read-only connectors: cursors, coverage, versions, originals)--> KB
KB --(bounded, permission-filtered context package)--> Interpreter
Interpreter = OpenRouter model  |  Viktor skill (per-task, if evaluated better)
Interpreter --(typed AnalysisResult, backend-issued span IDs only)--> KB validation --> ledger
```

- The `AnalysisAdapter` protocol (SA A.2) stays. Only the retrieval half of "Viktor-led" is dropped.
- Evaluate per task with the same context packages, on cost per *accepted* output and on reviewer correction rate:
  - action extraction (Stage 1, OpenRouter baseline);
  - call brief (Stage 2: OpenRouter against a Viktor preparation skill);
  - health "why" (Stage 3).
- Viktor runs for restricted-user features stay ineligible unless isolation is demonstrated (SA §5.4). Background extraction runs under system authority, so isolation matters less there than provenance, which this design keeps.

### 5.3 Stage 1 identity integration (AR-04)

```text
Browser -> KB /auth/start -> Command Center /login?next=... (existing PKCE hand-off, as for Content Atelier)
Command Center -> KB /auth/callback?code -> KB backend exchanges code server-side
KB backend: resolve email -> kb_users (+ membership state) -> issue KB session cookie (HttpOnly, Secure, SameSite=Lax, CSRF token)
Every N minutes (e.g. 5) and on sensitive operations: re-validate via Command Center /api/auth/session; fail closed if invalid
```

- `kb_users(id, email_normalised, central_subject = email for now, person_id, membership_state)`. Keep a column for a future stable central subject.
- Add user: an admin creates a KB membership in state `pending_central_account`, and the Command Center account is added through its existing configuration. Membership activates on first successful sign-in. Partial provisioning stays visible, as ARCH-Q04 requires, without a central API.
- KB-only revocation (Q11) works unchanged: the KB checks its own membership on every request.
- Central disabling takes effect within the re-validation interval. State this explicitly as a known bound.
- Ask Command Center for one small change with high value: persist session revocations (today they are in memory), so a central sign-out survives restarts.

### 5.4 Reconciled action model (AR-08, AR-09)

| Dimension | Values | Notes |
|---|---|---|
| `lifecycle` | `candidate` (in review) · `active` · `dismissed` · `archived` | `dismissed` stores a suppression fingerprint (source span plus obligation key), so re-extraction never recreates the item (TS-01 L127) |
| `progress` | `open` · `in_progress` · `blocked` · `done` · `cancelled` | `cancelled` carries a reason: cancelled, replaced or not applicable. ClickUp statuses map once at setup (TS-01 §5). Unmapped statuses go to review rather than `unknown` |
| `verification_required` | boolean, defaulted from `action_type` (D3), overridable with audit | |
| verification | `not_required` · `awaiting` · `verified` (active event) · `superseded` | Display "Verified" only for done plus active verification (SA L867) |
| acknowledgement | events per (owner person, obligation version) | Owner change requires a new acknowledgement (agreed) |
| `responsibility` | `wia` · `client` · `third_party` | |
| owner | one accountable `owner_person_id` (nullable) plus `action_collaborators` | Multi-owner acknowledgement semantics are avoided. Confirm with WIA |
| `classification` | `client_obligation` · `programme_ops` · `internal` | D4: programme ops excluded from client counts |
| snooze overlay | `snoozed_until`, `snooze_reason`, actor | **Decide:** excluded from default counts; still marked overdue in the drawer and visible under an "include snoozed" filter |
| notes | `action_notes` (author, text, time) | Domain `actions`; retention category "team notes" |
| authority (mapped tasks) | ClickUp-authoritative fields: owner, due, status (option A) | KB-only fields always editable |

Commands:

- **Deadline-change request** (FE v2) = correction proposal on `deadline`, with admins as resolvers. This gives one mechanism instead of two.
- **Reassign all** = one batched command that creates per-action owner changes under a `batch_id` in one transaction. Each resets acknowledgement. For mapped tasks under option A it produces a ClickUp to-do list instead.
- **Priority:** omit (TS-01 L198) or decide.

### 5.5 Data-domain visibility (AR-07)

**Domains:** `registry`, `actions`, `communications`, `meetings`, `profile`, `support`, `programme`, `leads`, `health`, `finance`, `chat` (private).

Rules:

1. Every business-content row carries `domain`. This covers excerpts, events, fact values, artifact sections and review items. Finance review items go to a finance-only queue (TS-03 F4, L149).
2. A screen is a composition of domains. A History lane or Profile field from the finance domain is omitted for viewers without the finance grant. This is enforced in the query service, not the frontend.
3. **Artifacts are composed of sections, each with one domain.** Section generation receives inputs only from its own domain and the shared non-sensitive domains. Viewers receive the sections they may see. Copy, export and Slack recheck at delivery.
4. Chat retrieval, tools and refusals use the same domain filter.
5. **Client visibility:** `all_clients` flag (admins and operations) OR membership of the client's account team. Admins can add explicit extra client grants. ClickUp assignees *suggest* team membership; they never grant it automatically.
6. **Operation rights:** agreed roles plus per-user Inherit/Allow/Deny (Q8–Q13), unchanged.

### 5.6 Outbound communications subsystem (AR-05)

```text
compose (template / LLM draft) -> outbound_message[draft]
  -> deterministic checks (must all pass before Send is enabled):
       target scope: every referenced record belongs to the target business (or the DM recipient's permitted scope)
       domain: finance content only to finance-permitted internal DMs
       channel class: Slack Connect / shared channel (conversations.info is_ext_shared) -> internal wording blocked
       programme channel: off by default (TS-01 L172)
  -> human edits and presses Send (records approver) -> [approved] -> outbox (same transaction)
  -> sender worker: claim -> provider call -> [sent | failed | uncertain]
       uncertain: reconcile by searching the target conversation for the embedded message marker before any retry
  -> log on action / invoice history; provider message ID stored
```

- `outbound_messages(id, kind: slack_channel | slack_dm | gmail_draft, target, business_id, domains, body, source_artifact_version, state, approver, idempotency_key, provider_message_id, error, timestamps)`.
- Separate operation right `send_notifications`, plus a global kill switch.
- Staging uses a **sink adapter** that never contacts providers.
- Prefer Gmail **drafts** (`gmail.compose`) to sending. A person sends from Gmail, and the sent mail is detected through normal intake (TS-03 L183).
- Scheduled digests (C4, F4) are just scheduled *compositions* that still require Send, unless WIA explicitly approves auto-send for internal DMs only.

### 5.7 Generated content lifecycle (AR-11)

| Element | Proposal |
|---|---|
| States | `building` → `draft` → (`approved` \| `published`) → `stale` → `superseded`; plus `rejected` and `failed` |
| Policy per kind | Narrative: owner approval (P2). Health "why": auto-publish plus flag (H5). Call brief: published on build, versioned (C7). Handover: on demand |
| Lineage | `base_version_id`. Human edits create a human-authored version; the next draft starts from the latest approved version (P2) |
| Current pointer | One `is_current` per (target, kind, domain-set). Copy, export and send use it (C7) |
| Instructions | `instructions{chips[], free_text, author}` stored per version and reused by automatic rebuilds (C7) |
| Staleness | From the dependency manifest (SA §10.3). The prior version stays visible and labelled |
| Templates (C2) | `brief_templates(version)` holding detection patterns, section toggles from a fixed catalogue, agenda skeleton (short items), leave-out options and length. Inserted into a **code-owned prompt as delimited data**. Change flow: edit → preview on fixtures → publish. Treat as business configuration under Q19; confirm through an ADR |
| User instructions | Chips map to typed retrieval parameters (period, sections, focus domain), validated against permissions. Free text may change tone and emphasis only. Requests for unapproved sources or domains are refused deterministically before generation |
| Injection hygiene | Source content, templates and instructions are passed as data and never as tool instructions. Tools are read-only and allowlisted (SA §8.5) |

### 5.8 Polling-first incremental sync (AR-15)

| Source | Cursor and mechanism | Suggested interval | Notes |
|---|---|---|---|
| Gmail | `users.history.list` from the stored `historyId`; full resync through `messages.list` if history expires | 2–5 min | One shared mailbox; client boundary from contact mapping |
| Calendar | `events.list` with `syncToken` per calendar; on `410`, full resync | 5 min | Occurrence identity per SA §10.3 |
| Drive | `changes.list` with a page token; filter to approved folder descendants | 5 min | Maintain a folder-membership map; removal is not deletion |
| Slack | `conversations.history` from the last `ts` per channel; `conversations.replies` for threads whose `latest_reply` changed; re-scan a rolling 7-day window for edits, deletes and reactions | 5 min | Verify the rate tier first (AR-15) |
| ClickUp | Team tasks filtered by `date_updated_gt`, including closed tasks and subtasks | 5 min | Refetch on ordering ambiguity (SA L879) |
| Fathom | List recent meetings; re-poll until the transcript is present | 5–10 min | Webhook later for the after-call loop |
| Zoom archive | One-off backfill (Drive archive / cloud recordings) | — | No ongoing sync |
| GHL / LeadLock | `updated since` queries once scopes exist | 15 min | Stage 3 |

### 5.9 Evidence retention options (AR-10)

| Option | What is retained | Enables | Cost |
|---|---|---|---|
| A: Q3 as agreed | Facts, excerpts, metadata | Minimal footprint | Re-fetch for every reprocess and recall; weaker Mode A; second full-history fetch for Stage 2–3 extraction |
| **B: retained normalised text category (recommended)** | A, plus normalised text per source type under a Q16 category, with admin-set duration (can be 0) | Local reprocessing, recall, client voice, search; WIA controls the trade-off | Storage (small at this scale); a larger privacy surface, governed by retention |
| C: metadata-only extension | A, plus per-message metadata (sender, thread, time, hash) for all in-scope messages | Reply detection, last contact, coverage | Does not fix recall or reprocessing |

If A stands: limit prelaunch processing for Stage 2–3 to inventory and coverage, and state the re-fetch dependency in the launch gap report.

### 5.10 Backfill and review-load plan (AR-12)

1. **Inventory (no LLM):** per source and client, record counts, date ranges, token estimates and inaccessible items, and write the first gap report.
2. **Dry run:** two or three clients, including a shared programme-channel client, through extraction and reconciliation. Measure review items by reason, extraction cost and windows per hour.
3. **Policy:** apply the historical-action rule (AR-12, recommendation 3). Clear deterministic identity matches (explicit channel, list and folder mappings) are auto-accepted and do not need review.
4. **Capacity:** size bulk parallelism to provider limits and the measured rate. Reserve current-intake lanes, as SA intends.
5. **Review tooling:** bulk accept, dismiss and merge, grouped by reason and source, with keyboard flow.
6. **Re-baseline:** set dates from measured throughput and review volume (FS §10 already requires this).

### 5.11 Work execution (AR-16)

PostgreSQL-only loop: `claim due work_items (SKIP LOCKED) → set lease and token → commit → execute outside the transaction → final commit checks the token and input versions`. Lanes are separate process pools (`sync`, `analysis`, `bulk`, `outbound`), each with configured concurrency. The sweep, retries, crash matrix and fencing follow SA §9.6 unchanged, minus the RQ dispatch steps.

### 5.12 Minimal viable chat (AR-17)

```text
question + explicit scope bar (client, period, domains)
  -> deterministic definition match? -> answer (no model)
  -> LLM tool loop (max 4 typed read tools, same query services, permission filter inside tools)
  -> backend citation validation (span IDs issued by tools only) -> answer card with status
```

No answer cache, embeddings or router in v1. Measure question mix, cost and latency for a month, then decide on KB-CH-68 components with data.

### 5.13 Frontend production path (AR-20)

1. Choose canonical variants (Register, Call Prep) and delete the others.
2. Generate TypeScript types and a client from FastAPI's OpenAPI. Add contract tests in CI.
3. Introduce a router (deep links already exist as hashes) and a server-state cache with invalidation on mutation responses.
4. Add a session provider driven by `GET /session`: feature and stage flags ("Coming soon"), domains and `allowed_actions`.
5. Replace mock rules with server fields (`display_status`, counts, `is_overdue`, health category). Keep only presentation logic.
6. Add explicit loading, stale, partial and unavailable components, as specified in SA §4.12.

### 5.14 Documentation structure (AR-14)

```text
docs/
  decisions/            ADR-0001… (imported KB-CH-01…69, ARCH-Q01…23, tab-scope decisions)
  requirements/         functional_requirements.md (links to ADR IDs)
  architecture/         concise mechanism spec, one file per area (data, intake, actions, access, AI, ops)
  product/              kb_tab_scope/* (UX and business rules)
  status/               verification and clarification registers, source scopes, open questions
  reviews/              this document
```

One statement per decision, linked everywhere else. Each architecture section answers GA §5's eight questions without repeating status caveats inline. A dated status annex holds those.

---

## 6. Prioritisation

| Priority | Findings | Blocks |
|---|---|---|
| **Critical** | AR-01 drift · AR-02 Stage 1 slice and dates · AR-03 retrieval ownership · AR-04 identity | Any backend scaffold and schema work |
| **High** | AR-05 outbound · AR-06 GHL ledger · AR-07 domain visibility · AR-08 action model · AR-09 ClickUp authority · AR-10 retention · AR-11 artifact lifecycle · AR-12 backfill and review load · AR-13 PII in repo · AR-14 documentation | The first migration (AR-07, AR-08, AR-09, AR-10); Stage 1 launch (AR-12); repository access now (AR-13); Stage 2–3 build (AR-05, AR-06, AR-11) |
| **Medium** | AR-15 polling · AR-16 queue · AR-17 chat order · AR-18 permission mechanism · AR-19 model gaps · AR-20 frontend · AR-21 credentials · AR-22 lifecycle · AR-23 provider data | Efficiency and risk during Stage 1 |
| **Low** | AR-24 observability · AR-25 recovery · AR-26 hygiene | — |

**Fix first (cheapest relative to impact):**

- AR-13 (hours);
- AR-14 link and import fix (hours);
- AR-03 and AR-04 decisions (one meeting);
- AR-09 option A (one decision);
- AR-15 and AR-16 (they remove work).

---

## 7. Open questions and assumptions

### 7.1 Decisions needed

| # | Question | Why it matters | Blocks | Owner |
|---|---|---|---|---|
| Q-1 | Approve D8 (Slack sends in Stage 1)? Resolve D9: are client channels shared with clients (Slack Connect)? | Brings write scopes and the outbound subsystem into Stage 1; client-visible wording risk | §5.6 scope | WIA |
| Q-2 | Agree that the KB owns retrieval for all eight sources, and that Viktor is a per-task interpreter only? | Removes the critical-path fork | Extraction design | WIA + E2M |
| Q-3 | Accept manual central provisioning for Stage 1, with ARCH-Q04's API as a later Command Center project? | Avoids a cross-product rebuild before launch | Auth build | WIA + Command Center owner |
| Q-4 | Revalidate Q3 retention: option A, B or C (§5.9)? | Reprocessing, recall, client voice, re-fetch of history | First migration | WIA |
| Q-5 | Mapped ClickUp tasks: option A, B or C (AR-09)? | Divergence, write scopes | Action model | WIA |
| Q-6 | Client visibility from account teams plus an "all clients" flag, and finance as a data domain (§5.5)? | Permission schema | First migration | WIA |
| Q-7 | Approve F1 as a source extension, request GHL billing and LeadLock location scopes now, and confirm F5 (dual billing)? | Stage 3 feasibility | Stage 3 plan | WIA |
| Q-8 | Stage 1 boundary: narrative drafts (P2) in Stage 1 or 2? Which P4 and D5 additions? | Scope and dates | Stage 1 slice | WIA |
| Q-9 | Prelaunch processing for Stage 2–3 features: full extraction, or inventory and coverage only? | Rework and cost (AR-10) | Backfill plan | WIA |
| Q-10 | Re-baselined dates and named staffing after the Phase 0 inventory | Credible plan | Everything | WIA + E2M |
| Q-11 | Canonical frontend variants (Register v1/v2/v3; Call Prep v1/v2) and their rule differences | Snooze versus deadline requests; team visibility; brief timing | Frontend and model | WIA |
| Q-12 | Templates (C2) as business configuration rather than prompts under Q19? | Governance consistency | Stage 2 | WIA |
| Q-13 | Snooze semantics, single versus multiple owners, priority | Action model | First migration | WIA |
| Q-14 | Lifecycle stages and ingestion rules (AR-22, P6) | Ingestion, counts, retention | Stage 1 | WIA |
| Q-15 | Repository visibility and handling of committed probe data | Privacy | Now | Repository owner |
| Q-16 | LLM provider data policy (no training, retention), and whether finance may go to an LLM | Third-party processing | First extraction run | WIA |
| Q-17 | Named reviewers and acceptable review backlog and turnaround | Review-load design | Launch readiness | WIA |
| Q-18 | Chat delivery position | Whether any chat machinery belongs in the next six weeks | Planning | WIA |

### 7.2 Where the documentation cannot support a conclusion

- **Source volumes and growth:** needed for throughput, cost and storage (AR-12).
- **Exact wording of KB-CH-01…69:** not in the repository. This review relied on how the decisions are restated in DR, FS, SA and FR.
- **The FastAPI SOP's binding constraints:** not in the repository. AR-16's preferred option may conflict with it.
- **Viktor API access and isolation for WIA:** untested. The relevance to AR-03 is unchanged either way.
- **Railway PITR availability on the actual plan** (AR-25).

### 7.3 Assumptions made by this review

- The product stays a single-tenant internal tool for WIA, with about 10–20 users and no client portal.
- The users are trusted employees. The access model protects against accidental exposure and role boundaries (finance), not against hostile insiders with database access (SA §12.5 says the same).
- The Stage 1–3 sequence (KB-CH-69) stands.
- The command-center auth code inspected in the sibling `WIA-Command-Center` folder is what production runs.
- The illustrative volumes in AR-12 and costs in AR-17 are for sensitivity only. Their direction of effect, not their values, supports the conclusions.

---

## 8. Suggested next steps

### Phase 0: Decide and reconcile (this week)

| Step | Output | Exit criterion |
|---|---|---|
| Purge and secure probe data; add root `.gitignore` (AR-13, AR-26) | Clean repository | No raw provider responses in tree or history |
| Import the decision register, SOP, registers and scopes; fix the 75 links (AR-14) | Self-contained documentation | Zero broken internal links |
| Decision meeting on Q-1 to Q-9 and Q-13 | ADRs | Each recorded with its SA impact |
| SA reconciliation update (AR-01) using §5.1–5.9 | SA revision | SA and tab scopes agree; GA §8 corrected |
| No-LLM source inventory (§5.10 step 1) | Volume table and first gap report | Every active client and source has counts and ranges |
| Stage 1 slice and re-baselined dates (AR-02) | Plan | Approved by WIA |

### Phase 1: Stage 1 foundation

- Scaffold under the SOP; Alembic; staging and production environments; logging and error tracking; PITR check and external dump.
- Schema for §5.1 "build now", including the action model (§5.4), domains (§5.5) and the retention choice (§5.9).
- Command Center hand-off, KB sessions, membership and grants admin (§5.3); the effective-permission function and its tests.
- ClickUp and Slack polling connectors first (largest action sources); then Gmail and Fathom.
- Extraction contract plus validators; reducer; review queue with bulk tools.
- **Exit:** dry run on two or three clients (§5.10 step 2) with measured review volume, cost and throughput; ClickUp authority behaviour demonstrated; revocation and denied-operation tests pass.

### Phase 2: Stage 1 completion and launch readiness

- Drive, Calendar and the Zoom archive; full backfill with bounded parallelism; gap report and WIA sign-off.
- Frontend production path (§5.13) for the Register, Portfolio, record, review and evidence views.
- Ten-user mixed-load test; restore drill; device matrix.
- **Exit:** FS §10 launch checklist and SA §11.5 gates for Stage 1.

### Phase 3: Stage 2 (Call Preparation)

- Artifact lifecycle (§5.7), templates as configuration, brief build and versions; per-task interpreter evaluation (OpenRouter against a Viktor skill) on identical context (§5.2).
- After-call loop. Outbound subsystem (§5.6) if digests or agenda sending are approved. Narrative drafts if they were deferred from Stage 1.

### Phase 4: Stage 3 and chat

- GHL billing connector and reconciliation (AR-06); health dimensions and snapshots; Overview.
- Chat per §5.12 when sequenced; add KB-CH-68 components only on measured need.

### Throughout

- Every tab-scope decision updates the ADR log and SA in the same change (AR-01).
- Measure cost per accepted output, review backlog age and freshness per source from the first dry run onwards.

---

## Appendix A: Inconsistency register

| # | Topic | Statement A | Statement B |
|---|---|---|---|
| 1 | External notifications | Coming soon in release 1 (FR L84; SA §4.16 L635; FS L157) | Slack notifications in release 1 (TS-01 D8); digests, nudges and drafts (TS-03, TS-04, TS-05) |
| 2 | Finance authority | Dubsado through Gmail only; HighLevel not authoritative (SA §4.18 L671–675) | GHL is the ledger (TS-03 F1) |
| 3 | Finance visibility | Client and module grants; field-level later (FR-ADM-03) | Finance hidden inside History, Profile, Handover and chat (TS-03 F2) |
| 4 | Narrative lifecycle | Deferred (SA L90, L595; FR §5.1) | Draft and owner approval (TS-02 P2) |
| 5 | Prompt and template governance | Admins do not edit or activate prompts (SA L1015, Q19) | Admin-editable call-type templates (TS-05 C2) |
| 6 | Action statuses | `unknown/open/in_progress/done` (SA L867) | Open, In progress, Blocked, Done, Verified, Cancelled, Snoozed (TS-01 L93, L111); FE without Cancelled (`types.ts` L61) |
| 7 | Verification scope | All actions eligible; "awaiting verification" universal (SA §4.16) | Only flagged types (TS-01 D3) |
| 8 | Chatbot existence | No route or screen (SA L531, L679; FR §2 L27) | Client 360 tab implemented in the mock (`App.tsx` L26; TS-06) |
| 9 | Chat entry points | Contextual entry points and snapshot tokens (SA L693; CB §5) | Single sidebar tab only (CB L120; TS-06 N2) |
| 10 | Chat cost path | Context buttons avoid model calls (CB L335) | Buttons and suggested questions removed (TS-06 N2, N4) |
| 11 | Deadline changes | Correction proposals (SA §6.6) | Snooze (TS-01 §4.4) and admin-approved deadline requests (FE v2) |
| 12 | Client visibility | Admin grants (SA §6.3) | Derived from ClickUp account teams (FE v3) |
| 13 | Brief build timing | Evening before, plus refresh 2 hours before (TS-05 L149–150) | 2 hours before with the default skill (`CallPrepV2.tsx` L33) |
| 14 | Priority | Skip for now (TS-01 L198) | Priority on actions (FE `types.ts` L84) |
| 15 | Paid-media figures | Paid media deferred; Viktor rating attributed only (TS-04 H3) | Spend and lead figures shown in Call Prep v2 (`performance.ts`), attributed to Viktor |
| 16 | GA coverage | TG-05, TG-11 and TG-20 artifacts "added" (GA §8) | Sequence diagrams, failure table and dashboards absent from SA |
| 17 | `chatbot_KB.md` location | Linked at `../../../chatbot_KB.md` | File is `docs/chatbot_KB.md` |
| 18 | Landing page | Use an activated module before Overview is enabled (FR §9; SA §13.2) | Mock lands on Overview (`App.tsx` route default) |
| 19 | Call times | WIA works in US time (TS-05 L188) | Mock displays IST (FE README) |

## Appendix B: Method and evidence

- **Read in full:** all six `docs/` files, all six `kb_tab_scope/` files, the frontend README and content agenda.
- **Inspected:** frontend `App.tsx`, `types.ts`, `data.ts`, `records.ts`, `teams.ts`, `performance.ts`, `finance.ts`, `health.ts`, sidebar, and view headers for all variants; the verification scripts and probe structure (field names and shapes only, no content reproduced); git history; the remote configuration.
- **Outside the repository, read-only:** `WIA-Command-Center/server/auth-core.mjs`, `atelier-sso.mjs` and the session settings in `index.mjs`, because SA's authentication design depends on them.
- **External sources:** Slack's rate-limit documentation and changelog ([1](https://docs.slack.dev/apis/web-api/rate-limits), [2](https://api.slack.com/changelog/2025-05-terms-rate-limit-update-and-faq), [3](https://docs.slack.dev/changelog/2025/06/03/rate-limits-clarity)). Cost figures reuse the rates published in FS §11.
- **Not done:** no code was run against providers, no backend was built, no load or restore test was performed, and no existing document or code was modified. The 75 broken links were found by resolving every relative Markdown link in `docs/`, `kb_tab_scope/` and `frontend/` against the working tree.
