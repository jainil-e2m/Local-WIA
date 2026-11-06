# Content packs stage: repository survey (read-only, 24 October 2026)

Repository: `C:\Users\KENIL\Desktop\wedding_industry_ads\WIA-Content-Atelier` at `03a3c98` (main). No file in the repository was changed. Paths below are relative to the repository root; `bp/` means `backend/backend_pipeline/`.

## 0. Key findings first

1. **The old `packs/` module cannot read a v4 brief.** It reads v1 document fields directly (`document["email"]["reader_job"]`, `document["carousel_reader_job"]`, `document["reels"][n]["reader_job"]`, `brief["claims"][*]["qualifications"]`, `brief["sources"]`, `brief["carousel"]`), refuses any v2/v3/v4 brief by name (`bp/packs/workflow.py:35-39`, code `brief_v2_unmapped`), and requires exactly five slots `email, carousel, reel_1, reel_2, reel_3` (`bp/packs/contracts.py:9`, `bp/packs/service.py:50-51`). **All three N2 v4 briefs have two Reels** (story and b-roll; D30 allows two), so even a mapped v1 design would block on the slot check.
2. **Its model re-writes copy the brief already carries.** Each slot is one `pack_write` call that writes a new email/carousel/reel from the brief's directions; v4 briefs already hold finished copy (R56: "After Gate 2, copy is edited by hand and kept verbatim"). The v1 pack contracts (`Email.subject/preview_text/body`, `Reel.spoken_script/visual_directions`, `Slide.headline/body`) do not match v4's shapes (send header, `on_screen_hook`, `screens`, per-asset caption with hook/body/ending, carousel title).
3. **The hand-off view is the right input and already works for v4.** `GET /storage/briefs/{id}/handoff` (`bp/briefs/handoff.py:304-341`) returns `brief_handoff_v1`: pieces keyed `reel_1..n`, `carousel`, `email` (then `caption`, `stories`), each with `copy` and `direction`, the anchor, the message spine, claims, before-publishing items, evidence with consent, and `can_consume`. Checked on all three N2 briefs (`research/n2-delivery-2026-10/readings.md:203`); all returned `can_consume: false` because none is Gate-2-approved yet.
4. **The database tables are reusable as they are.** `content_packs`, `content_assets`, `calendar_entries` (migration 001, extended by 004) have no v1-specific columns; `slot_key` is free text, the unique indexes are `(pack_id, slot_key)` and `(pack_id, ordinal)`, and the table comment says "no fixed asset-count cap". Migration 004 is applied wherever 005+ is (production is at 008).
5. **No standing budget covers pack stages.** `bp/llm/standing.py:27` lists six purposes; line 30 says "Pack stages are out of this phase (R31): no standing budget covers them." A paid pack call in production (no `ATELIER_RUN_PLAN_ID`) is refused by `StandingPlanStore.plan_for` (`standing.py:166-180`). Also: a standing plan's `stages` list is frozen when the week's row is created (`ensure`, `standing.py:100-117`, `ON CONFLICT DO NOTHING`), and `run_plans.py:107` refuses a stage not in it. **A new stage mapped to an existing purpose (for example `briefs`) is refused for the rest of the current budget week**; a new purpose gets a fresh row that includes it.
6. **Gate 2 approval queues nothing today.** `gate_two.decide` (`bp/briefs/gate_two.py:421-437`) records the decision, emits `gate_two_approved` with "no production jobs queued" and closes the brief run. Gate 1 shows the pattern for auto-queueing in the approving transaction (`bp/gate_one.py:385-388` calling `briefs/workflow.queue_in_transaction` with a savepoint).
7. **The pack-shaped rendering already exists.** `bp/briefs/review_document.py` renders the week in the "# Pack N" layout WIA reviewed (content angle, brief, Email with send header, each Reel, Carousel slide by slide, "Before you publish Pack N"), served at `GET /storage/weeks/{id}/review.md`. `render_v4.asset_lines` and the frontend `BriefBodyV4View` render the same assets.
8. **Pack-level checks exist and are deterministic.** `first_touch_findings`, `asset_findings`, `week_findings` (`bp/briefs/first_touch.py`, `bp/briefs/asset_checks.py`) take a v4 writer body; `bp/briefs/pack_markdown.py` + `backend/scripts/pack_checks.py` run them over a hand-built pack document. They already run inside `checks_v4` at Gate 2.
9. **The real frontend has v1 pack screens behind `flags.packs`.** `StoredPacks.tsx` (v1 asset fields), routes `/studio/packs`, `/packs`, `/studio/scheduled`, and a "Generate saved content pack" button in `SQLBriefs.tsx` shown only when `packMapped(brief)` (schema v1). The mock's richer pack view (tabs Email / Carousel / Reel 1-3, labelled sections, Copy and Copy all, "Approve Content Pack & Schedule") lives only in `frontend/src/mock/`.
10. **Learning capture under-reads v4.** `knowledge/capture.brief_copy` (`bp/knowledge/capture.py:59-100`) takes a v4 b-roll Reel's text as cover + beats (no screens, no caption), the carousel as slides only (no title or caption), and returns None for channel `caption` (v4 has no `format_plan.caption`; captions live on each Reel and the carousel). A pack's piece keys could fix the mapping.

---

## 1. The `packs/` module

### 1.1 Files

| File | Lines | What it holds |
| --- | --- | --- |
| `bp/packs/contracts.py` | 71 | `VERSION="production_pack_v1"` (l.8); `SLOTS=("email","carousel","reel_1","reel_2","reel_3")` (l.9); `STAGES = pack_prepare, pack_<slot> x5, pack_validation, pack_assembly` (l.10); models `Claim`, `Copy`, `Email`, `Slide`, `Carousel`, `Reel`, `Review`, `Generate`, `Decision`; `schema(slot)` (l.70) |
| `bp/packs/runtime.py` | 99 | `execution_contract` (l.21-38), `check_dependencies` (l.46-56), cost `record` (l.59-76), `_flow` (l.79-83, budget 8 chat calls per run), `call` (l.86-99) |
| `bp/packs/service.py` | 199 | `authorize` (l.9-11), `assets`, `manifest` (l.18-36), `blockers` (l.39-73), `locked` (l.76-86), `detail` (l.89-114), `listing` (l.117-134), `decide` (l.137-180), `audit` (l.183-199) |
| `bp/packs/workflow.py` | 284 | `queue` (l.12-127), `execute` (l.130-251), `written` (l.254-268), `validate_copy` (l.271-284) |

### 1.2 Contracts (v1 copy shapes)

| Model | Fields | Limits |
| --- | --- | --- |
| `Copy` (base) | `title`, `claims: [Claim{text, brief_claim_ids, qualifications}]`, `evidence_ids`, `cta: dict` | |
| `Email` | + `subject_lines`, `subject`, `preview_text`, `body` | 1 to 5 subject lines |
| `Carousel` | + `slides: [Slide{number, headline, body, direction}]`, `caption: str` | 1 to 30 slides |
| `Reel` | + `spoken_script`, `caption: str`, `visual_directions` | |
| `Review` | `preserves_approved_direction`, `grounded`, `distinct_contributions`, `findings` | |
| `Generate` (mutation) | `request_id`, `expected_brief_hash`, `mode: replay/live`, `supersedes_id` | |
| `Decision` (mutation) | `request_id`, `expected_manifest_hash`, `decision: approved/rejected`, `note` | |

`Mutation` (`bp/calendar/contracts.py:13-14`) carries `request_id`; receipts make every write idempotent (`bp/production_common.py:18-27`, table `mutation_receipts` from migration 004).

### 1.3 Trigger and job graph

- **Trigger:** manual only. `POST /storage/briefs/{brief_id}/pack` (`bp/production_api.py:66-68`) calls `workflow.queue`. Nothing calls it on Gate 2 approval.
- **Guards in `queue`:** `edit_packs` capability; `features.packs`; live needs `generation_enabled and pack_live_enabled` (env `ATELIER_ALLOW_PACK_GENERATION`, `bp/storage_config.py:92`); receipt replay; brief row locked `FOR UPDATE`, hash equals `expected_brief_hash`, approved, `gate_two.blockers` empty; **refuses v2/v3/v4** (l.35-39); reads the brand bundle from the brief's origin run (v1 only; v2+ use the knowledge base, `briefs/workflow.py:155-158`).
- **Run key:** `intent = canonical_hash([brief_id, content_hash, contract, mode, supersedes_id])`; run `pack_run_<intent24>`, pack `pack_<intent24>` (l.54-59). Settings snapshot added via `snapshot_refs("pack", ...)` (l.56-58), kept out of the intent.
- **Rows written:** one `pipeline_runs` (`run_scope="pack_generation"`), one `content_packs` row, and 8 `pipeline_jobs` with `pack_id` set and dependencies in `progress_details.dependencies` (l.99-125): `pack_prepare` → 5 slot jobs in parallel → `pack_validation` (depends on all slots) → `pack_assembly`.
- **Supersession:** `supersedes_id` must share the governing `angle_id` and have no other replacement (l.62-72).

### 1.4 Execution (`workflow.execute`)

| Stage | What it does | v4 problem |
| --- | --- | --- |
| `pack_prepare` | Inserts 5 `content_assets` rows (`status='planned'`, `reader_contribution` from v1 `reader_job` fields, l.145-164) | v4 has no `reader_job`; the equivalent is each piece's `direction.job` |
| `pack_<slot>` | One `pack_write` call with `{slot, approved_brief, evidence, brand}`, `validate_copy`, writes envelope `{version, slot, document, brief_id, brief_hash}` to `pack-runs/<run>/<slot>.json` (l.166-193) | Re-writes copy; v4 already has it |
| `pack_validation` | Re-validates every slot, one `pack_review` call; blocks unless grounded, preserves direction and distinct contributions; writes `validation.json` (l.194-222) | Review prompt asserts "email, carousel and three reels" |
| `pack_assembly` | Locks pack and assets, checks validation artifact hashes, writes `content_body`, `content_hash`, `status='generated'`, computes `manifest_hash` (l.223-249) | Reusable as a pattern |

`validate_copy` (l.271-284) checks the CTA equals `brief["cta"]`, evidence ids are a subset of `brief["sources"]`, every claim cites approved `claim_id`s and keeps their `qualifications`, and the carousel keeps slide numbers: all v1 shapes. A v4 brief has `header.cta` / `body.cta`, ledger claims with `status` and `field` (no `qualifications`), and evidence in `body.evidence` + `selected_evidence`.

### 1.5 Runtime

- `execution_contract` requires `pack_writer_model` and `pack_review_model` when not synthetic (l.26-27) and hashes the two prompts and four schemas. **It includes `max_tokens`** and `check_dependencies` compares the whole dict exactly (l.48): raising `models.completion_tokens` mid-run voids a pack run. Briefs fixed this in N2 (`briefs/runtime.stable_contract`, `bp/briefs/runtime.py:47-58`, drops `max_tokens`).
- `check_dependencies` re-reads the brief on every call: same hash, still approved, no Gate 2 blocker.
- The call goes through `llm.workflow.chat` with `Flow(name="pack", cache="pack-cache", attempts="pack-attempts", budget=8, live_enabled=pack_live_enabled)` (l.79-83): response cache, recovery of an earlier attempt's answer, one repair, `llm_runs` row. Cost summaries go to `pack-runs/<run>/cost_summary.json` (`record`, l.59-76), read by `GET /packs/{id}/production`.

### 1.6 Service: status, manifest, approval

- **Statuses:** `content_packs.approval_status` `pending/approved/rejected`; `content_assets.status` `planned/generated` (any text is allowed by the DDL; only these two are written).
- **Manifest** (`service.manifest`, l.18-36): canonical hash of version, brief id and hash, ordered assets (id, slot, type, ordinal, content hash) and the validation result.
- **Blockers** (l.39-73): provenance version, governing brief still approved at the same hash with no Gate 2 blocker, no replacement pack, the five slots in order, asset lineage and hashes, the stored body validates against the slot schema, validation passed, manifest current; with `approved=True` also bound approval (for scheduling).
- **Decision** (`decide`, l.137-180): approver capability, receipt, lock order brief → pack → assets (`locked`, l.76-86), stale-manifest check, rejection needs a note, `pack_approved/pack_rejected` event on the production run. The DB constraint `pack_approval_is_bound` enforces `approved_hash = manifest_hash` with actor and time.
- **Roles:** `edit_packs`, `approve_packs`, `schedule` (`bp/gates/roles.py:103-108`). With a `users` row (production) editor generates and schedules, approver approves (l.161); without one, the lists `ATELIER_PACK_EDITORS`, `ATELIER_PACK_APPROVERS`, `ATELIER_CALENDAR_SCHEDULERS` apply (l.172-174). `GET /storage/me` exposes `generate_packs`, `approve_packs`, `schedule_calendar` (l.120-127). Job retry of a `pack_generation` run checks pack authority (`bp/repository.py:450-452`).

### 1.7 Tables (migrations)

| Table | Created | Pack-relevant columns and constraints |
| --- | --- | --- |
| `content_packs` | `backend/migrations/001_approved_schema.sql:125-141`; 004 adds `source_brief_id`, `source_brief_hash`, `production_run_id`, `contract_version` (`004_packs_calendar.sql:2-5`) | `pack_id`, `week_id`, `supersedes_id`, `title`, `manifest_hash`, `validation_result`, approval columns, `review_note`; check `pack_approval_is_bound` |
| `content_assets` | `001:143-163` | `pack_id`, `brief_id`, `brief_input_hash`, `supersedes_id`, `slot_key`, `ordinal`, `asset_type`, `reader_contribution NOT NULL`, `status`, `content_body`, `content_hash`, `validation_result`; checks: ordinal > 0, body iff hash, generated needs body; unique `(pack_id, slot_key)` and `(pack_id, ordinal)` (l.246-248); comment (l.288-290): "no fixed asset-count cap" |
| `calendar_entries` | `001:165-179`; 004 adds `revision`, `pack_manifest_hash`, `display_timezone`, `created_by`, `updated_by`, status check, unique active `(asset_id, channel)` | schedules one exact asset content hash |
| `mutation_receipts` | `004:14-21` | idempotent writes |
| `pipeline_jobs.pack_id`, `.asset_id` | `001:189-190`, FK l.348-350; check `job_has_at_most_one_target` | a pack job targets the pack |

`bp/database.py:49-57,94-98` detects 004 by `mutation_receipts`; every database at 005 or later has it.

### 1.8 API, CLI, settings, prompts, tests

- **Routes** (`bp/production_api.py`, installed from `bp/storage_api.py:446-447` under `/storage`): `GET /packs` (l.35-44), `GET /packs/{id}` (l.46-49), `GET /packs/{id}/production` (jobs and costs, l.51-64), `POST /briefs/{id}/pack` (l.66-68, 202), `POST /packs/{id}/decision` (l.70-73), `POST /packs/{id}/schedule` (l.75-77), plus calendar routes (l.21-33, 79-85). Every pack read answers 503 `packs_disabled` when the flag is off (l.17-19).
- **Response models** (`bp/api_models.py:998-1060`): `PackDocument` is the v1 asset shape (`subject`, `preview_text`, `body`, `spoken_script`, `slides[{number, headline, body, direction}]`, `caption: str`, `visual_directions`, `cta`, `claims`, `evidence_ids`); `StoredAsset.asset_type: Literal['email','carousel','reel']`.
- **CLI:** none. `storage_cli` has no pack command (`grep` over `bp/storage_cli.py`, `bp/cli.py`).
- **Settings:** `features.packs` (`bp/settings_store.py:312-319`, env `ATELIER_PACKS_ENABLED`, default false), `models.pack_writer`, `models.pack_review` (l.208-211), `models.reasoning_effort.pack_writer|pack_review` (l.217-221, scope `pack`), `briefs.max_characters` is scoped to `brief` and `pack` (l.280). `pack_live_enabled` is env-only (`ATELIER_ALLOW_PACK_GENERATION`), not a table key.
- **Prompts:** `bp/prompt_templates/pack_write.v1.md` (10 lines: write one slot from the approved brief, cite claim ids, keep qualifications) and `pack_review.v1.md` (8 lines: review all five assets). Both generic, no knowledge base, no first-touch rules.
- **Tests:** `bp/tests/test_calendar.py` (7 tests; `PackProvider` fakes `pack_write`/`pack_review`; fixture `produced` approves a v1 brief, queues a synthetic pack, drains, approves it), `test_calendar_contracts.py` (5), `test_brief_v2_db.py::test_packs_stay_off_by_flag_and_refuse_an_approved_v2_brief_without_breaking_it` (l.217), `test_jobs_db.py` (`queue_for("pack_writing")` is interactive, l.80; `pack-cache` replay, l.244), `test_roles.py`, `test_users_db.py`, `test_openapi.py`, `test_sql_storage.py`/`test_briefs.py` (assert zero packs created).

---

## 2. The hand-off view

### 2.1 Where

| Piece | Location |
| --- | --- |
| Derivation | `bp/briefs/handoff.py` (341 lines; module docstring l.1-25 is the spec) |
| Entry point | `gate_two.handoff` (`bp/briefs/gate_two.py:192-196`): `view(conn, _get(...))`, so `blockers` and `can_consume` come from `_get` (l.166-190; `can_consume` at l.181) |
| Route | `GET /storage/briefs/{brief_id}/handoff` (`bp/storage_api.py:367-370`, `decider` dependency) |
| Response model | `BriefHandoff` (`bp/api_models.py:~898-930`), `HandoffPiece`, `MessageSpine`, `HandoffAnchor`, `HandoffEvidence`, `HandoffClaim`, `HandoffItem`, `PublishingOrder`, `HandoffTopic` |
| Relay | allowlisted GET in `frontend/server/allowlist.mjs:15`; `server/routes.test.mjs:101-105` |

Nothing is stored except a person's anchor choice in `content_body.review.anchor`; no model call.

### 2.2 Output schema (`view`, `handoff.py:304-341`)

| Field | Meaning |
| --- | --- |
| `handoff_version` | `"brief_handoff_v1"` |
| `brief_id`, `schema_version`, `content_hash`, `approval_status`, `approved_hash`, `approved_by`, `approved_at` | identity and approval |
| `can_consume`, `blockers` | approved and no blocker (computed on read) |
| `week_id`, `angle_id`, `title`, `core_perspective`, `audience`, `purpose`, `content_type`, `point_of_view`, `wia_perspective` | meta (v2+: from header and `approved_angle`) |
| `cta` | v2+: `header.cta` `{choice, track, action, offer_connection, chosen_by}` |
| `message_spine` | `{text, source: sharpened_point / approved_angle / core_insight, supporting[]}` (l.183-195) |
| `anchor` | `{key, chosen_by: rule/person, actor, at, rule, note}` (l.136-148) |
| `pieces[]` | `{key, channel, platform, label, copy, direction, evidence_ids, anchor}` (l.80-124) |
| `channels`, `channels_without_piece` | confirmed channel set; v4 counts `caption` present when any piece has a caption (l.326-329) |
| `series`, `publishing_order` | `{rank, position, of, held, known}` from the strategist run's `publishing_order` (l.287-301) |
| `topic`, `topics` | active registry topics of the card's moments (l.279-284) |
| `claims[]` | `{claim_id, text, kind, status, evidence_ids, quote, public_quote, numeric_facts, notes}` (l.209-220) |
| `before_publishing[]` | `{id: P1.., text, kind, required, answer}` (l.223-233) |
| `evidence[]` | per selected evidence item: `cited`, role, title, speaker, `start_ms`, quote, `moment_ids`, `consent_status` (most restrictive of linked moments: do_not_use > internal_only > anonymise > cleared, else unknown; `not_applicable` for external framing), `client_consent` (no_use > anonymise_only > may_name, else the call's client, else unknown), `consent_basis`, `sensitivity`, `public_use`, `attribution_verified`, `permission_recorded` (a Gate 2 clearance), `attribution_reference` (l.241-276) |

**Piece keys** depend only on the plan: `reel_1..n` in order, then `carousel`, `email`, `caption`, `stories`; named after the old pack SLOTS (docstring l.7-10). **Copy vs direction** by contract (l.70-77):

| Contract | Reel copy | Reel direction | Email copy | Email direction | Carousel |
| --- | --- | --- | --- | --- | --- |
| v4 | cover_text, on_screen_hook, spoken_opening, script, screens, caption | kind, job, register, beats, personal_lines, read_time_seconds, source, offer_descriptor | subject_options, preview, opening, body, ending | job, register, send_header, offer_descriptor | copy: title, slides[{number,text}], caption; direction: job, slides[{number,job}], register, offer_descriptor |
| v3 | cover_text, spoken_opening, script | job, beats, read_time_seconds, source | subject_options, preview, opening, body, ending | none | copy: slides text; direction: job, slide jobs |
| v1 | none (directions only) | reader_job, direction, outline | none | reader_job, direction, outline | direction only |

**Anchor rule:** first Reel, else carousel, else email, else caption, else stories (`ANCHOR_RULE`, l.38). A person chooses another at Gate 2 with `PATCH /briefs/{id}` `changes: {"anchor": "<key>"}` (`gate_two.edit_v2`, l.306-307; `handoff.choose_anchor`, l.151-164); it is outside the reviewed hash, so no new claims check.

### 2.3 Example: computed from `research/n2-delivery-2026-10/brief-1.json`

Computed offline with `handoff.pieces`, `anchor_of`, `message_spine` (the DB parts, evidence consent, topics and publishing order, need a connection). Text truncated.

```json
{"key":"reel_1","channel":"reel","platform":"instagram","label":"Reel 1","anchor":true,
 "copy":{"cover_text":"Our landing page wasn't an automatic replacement","on_screen_hook":"We built a page. We didn't switch all the ad traffic.",
         "spoken_opening":"We built a landing page for a client, ...","script":"We built a landing page ...","screens":null,
         "caption":{"hook":"Hiring an ads team doesn't mean ...","body":"...","ending":"-Whitney"}},
 "direction":{"kind":"story","job":"Face-to-camera account ...","register":"spoken","beats":["..."],"personal_lines":["..."],
              "read_time_seconds":86,"source":"new_script","offer_descriptor":null},
 "evidence_ids":[]}
{"key":"reel_2", ... "copy":{"cover_text":"A landing page has to earn the switch","script":null,"screens":["...","...","..."],"caption":{...}},
 "direction":{"kind":"broll_text","register":"on_screen","read_time_seconds":19, ...}}
{"key":"carousel", ... "copy":{"title":"A page we build should face the same scrutiny ...","slides":[{"number":1,"text":"..."}, "...(7)"],"caption":{...}},
 "direction":{"job":"Seven-slide written treatment ...","slides":[{"number":1,"job":"..."}],"register":"written","offer_descriptor":null}}
{"key":"email","platform":"email", "copy":{"subject_options":["A new landing page still has something to prove","Does your current ad page need replacing?"],
 "preview":"...","opening":"Hi {{contact.first_name}},\n\n...","body":"...","ending":"Reply to this email, ..."},
 "direction":{"job":"Standalone Tuesday broadcast ...","register":"written",
   "send_header":{"date":"Tuesday, 27 October 2026, proposed; ...","send_time":"11:00 a.m. Central, proposed ...","recipients":"WIA main email list, proposed; ..."},
   "offer_descriptor":"our full-service advertising management program"}}
anchor: {"key":"reel_1","chosen_by":"rule","note":null}
message_spine: {"text":"We make a page we've built earn its place ...","source":"approved_angle","supporting":["...","...","..."]}
cta: {"choice":"explicit","track":"email_reply","action":"Reply to this email, ...","chosen_by":"writer", ...}
before_publishing[0]: {"id":"P1","kind":"permission","required":true,"answer":null,"text":"Confirm Whitney's attribution ... Hold all story assets until cleared."}
```

All three N2 briefs: WARM, channels `reel, carousel, email, caption`, Reels `[story, broll_text]`, carousel 7/7/9 slides, 2/2/3 subject lines, 49/41/67 ledger claims, 5 before-publishing items each. No saved hand-off JSON exists in `research/` (only the readings note).

**Observations for a pack stage:** v3/v4 pieces carry `evidence_ids: []` (the ledger binds copy to evidence; claims carry `field` paths like `format_plan.reels[1].cover_text`, so per-piece claims can be derived by path prefix). The `caption` channel has no piece of its own in v4. The CTA in N2 briefs is still `chosen_by: writer` until Gate 2 confirms it.

### 2.4 Tests

`bp/tests/test_brief_handoff.py` (9 tests: stable keys and anchor, fallback order, person's choice, copy/direction marks, v2 and v1 mapping, spine, writer request unchanged, series and publishing order); `test_brief_v4.py::test_the_hand_off_view_gives_each_v4_piece_its_copy_and_direction` (l.221); `test_brief_v4_db.py::test_the_v4_brief_renders_in_the_hand_off_the_export_and_the_review_document` (l.148; asserts keys `reel_1, reel_2, reel_3, carousel, email`, empty `channels_without_piece`); `test_brief_v3_db.py` (7 refs), `test_brief_v2_db.py`, `test_users_db.py`, `test_phase_s.py`.

---

## 3. Brief v4, its rendering and checks, and the stage pattern to copy

### 3.1 `bp/briefs/contracts_v4.py` (asset fields and limits)

| Model | Fields (COPY = audience-facing; DIRECTION = note to maker) | Limits |
| --- | --- | --- |
| `ReelPlanV4` (l.72-93) | kind (story/stance/broll_text), job, register (spoken/on_screen), cover_text, on_screen_hook, spoken_opening (null for b-roll), script (null for b-roll and existing clip), screens (b-roll only), beats, personal_lines, read_time_seconds, source (existing_clip/new_script), caption (`CaptionPlanV3{hook, body, ending}`), offer_descriptor | screens <= 3, beats 1-8, personal_lines <= 3, read time 5-180 s |
| `CarouselPlanV4` (l.96-102) | job, register=written, title, slides (`SlideV3{number, job, text}`), caption, offer_descriptor | 7-12 slides (number 1-12) |
| `SendHeader` (l.105-109) | date, send_time, recipients ("proposed for WIA to confirm; scheduling is downstream") | |
| `EmailPlanV4` (l.112-123) | job, register=written, send_header, subject_options, preview, opening, body, ending, offer_descriptor | 2-4 subjects |
| `FormatPlanV4` (l.126-130) | reels, carousel, email, stories (`StoriesPlan{frames}`) | reels <= 3; frames 1-8 |
| `BriefWriteV4` (l.133-149) | approved_angle, sharpened_point, central_point, strategic_purpose, intended_shift, audience, point_of_view, wia_perspective, supporting_example, narrative_outline, cta, cta_why, before_publishing (<= 5), format_plan | |
| `BriefBodyV4` / `BriefHeaderV4` / `BriefDocumentV4` (l.174-195) | body adds `evidence[]`, `claims[]` (ledger, status bound/supported/unsupported/unchecked/kept_by_person/attested, `field`); header has schema_version, angle hash, purpose, audience, cta, channels, pinned_inputs | |

`EDITABLE_V4` = every writer field except `approved_angle` and `cta` (l.199-200). `writer_schema_v4(channels)` nulls formats outside the channel set (l.203-217). `copy_fields_v4` lists every copy line with its ledger field (l.236-276).

### 3.2 Renderers and checks a pack stage can reuse

| Function | File | Consumes | Notes |
| --- | --- | --- | --- |
| `markdown_v4`, `asset_lines(plan)` | `bp/briefs/render_v4.py:19-107` | v4 row / format_plan | Email with DATE/SEND TIME/RECIPIENTS/SUBJECT/OTHER SUBJECTS/PREVIEW, each Reel, carousel, Stories; serves `GET /briefs/{id}/export.md` via `gate_two.markdown` (l.551-554) |
| `render`, `render_week`, `assets` | `bp/briefs/review_document.py:322-370, 423-477` | week material (cards + current brief per card, v1-v4) | "# Pack N · PILLAR", "## Content angle", "## Content brief", assets, "## Before you publish Pack N", "# Content bank"; label by maker (R58). Served at `GET /storage/weeks/{id}/review.md` (`bp/cycle/api.py:194-199`) and `storage_cli review-document` |
| `first_touch.assets(body)` | `bp/briefs/first_touch.py:93-124` | v4 writer body | Asset list keyed `reel_<n>`, `carousel`, `email` (the hand-off keys), with first-touch lines, parts and paths |
| `first_touch_findings` | `first_touch.py:374` | body, insider terms, attested facts, evidence, roster | 5 first-touch rules (insider terms blocking) |
| `asset_findings` | `bp/briefs/asset_checks.py:415-427` | body, pillar, channels, evidence, roster, attested, offers, `anchor_key="reel_1"` | outcome verbs and hook fidelity blocking; the rest warnings |
| `week_findings`, `week_siblings` | `asset_checks.py:439-475` | body + the week's other current briefs | one offer CTA a week on Instagram; covers distinct across the week |
| `checks_v4` | `bp/briefs/validation_v4.py:60-117` | v4 document, dossier, provenance (pinned insider terms and offers) | Runs all of the above at Gate 2 |
| `parse_packs`, `check_packs` | `bp/briefs/pack_markdown.py:99-145` | a hand-built pack Markdown | Turns each "# Pack N" into a v4 body with placeholders, then runs the three check sets |
| `scripts/pack_checks.py` | `backend/scripts/pack_checks.py` (50 lines) | pack Markdown + `--attest N TEXT` | Prints findings by pack; `--json`. No model call |

### 3.3 Paths, locks and versions

- `bp/briefs/paths.py`: dotted paths with 0-based indexes (`format_plan.reels[1].cover_text`); `apply` (l.123), `merge_locks` (l.148), `restore` (l.167), `revision_locks` (l.184), `locked_values` (l.196), `leaves` (l.103). A person's edit locks only the line; a refresh restores locked lines verbatim.
- Every Gate 2 change is a new `content_briefs` row (`gate_two.replace`, l.248-258) with `content_body.change = {kind, fields, by, at}`; `versions` (l.198-212) walks the `supersedes_id` chain; `locked` (l.66-72) refuses a stale hash or a superseded version.
- **Gate 2 approval** (`decide`, l.421-437): approver role; pending only; blockers must be empty; sets `approved_hash = content_hash`, actor, time; `record_decision` writes a `decisions` row (l.409-419); event `gate_two_approved` "no production jobs queued"; brief run closed "production remains separate".

### 3.4 The workflow pattern to copy (`bp/briefs/workflow.py`)

1. **Queue inside the caller's transaction.** `queue_in_transaction` (l.16-29) wraps `_queue` in a savepoint; a failure is recorded as a failed run (`record_failure`, l.38-49) so the approval still commits. Gate 1 calls it from `decide` (`bp/gate_one.py:385-388`) with `develop_mode(settings)` (l.31-36: synthetic on a test DB, live when switched on, else replay).
2. **Run key.** `intent = canonical_hash([WORKFLOW, angle_id, approved_hash, ...(+mode if live)])`, `run_id = 'brief_run_' + intent[:24]`; an existing run is returned (l.75-81). Same approval in the same mode is one run.
3. **Pinned inputs.** `input_refs` = packet, brand source, mode, synthetic, queued_by, revision and context items, `settings_snapshot` from `snapshot_refs('brief', ...)` (l.101), schema version, channels and writer (l.102-104).
4. **Rows.** One `pipeline_runs` row (`run_scope`), one `pipeline_jobs` row per stage with `idempotency_key = run_id:stage`, `input_hash`, and `progress_details.dependencies` (l.108-117). `repository.insert` adds `executor='rq'` and the queue from `jobs/policy.placement` (`bp/repository.py:98-110`).
5. **Dispatch.** The API middleware kicks dispatch after any successful POST/PATCH (`bp/api.py:39-44`, `jobs/dispatch.kick`, `bp/jobs/dispatch.py:88-100`); the scheduler's reconcile pass re-dispatches any ready row every 30 s (`bp/jobs/scheduler.py`). `READY_SQL` and `repository.claim` (l.332-357) skip jobs whose dependencies are not completed.
6. **Queues.** `jobs/policy.queue_for` (`bp/jobs/policy.py:61-73`): brief stages, anything starting `pack_`, and `card_refresh` go to `interactive`; timeouts in `TIMEOUTS` (default 1800 s).
7. **Worker routing.** `SQLWorker.execute` (`bp/sql_pipeline.py:201-236`): any stage starting `pack_` goes to `packs.workflow.execute` (l.228-231). `run_claimed` (l.79-104) sets the budget purpose from the run scope (`standing.purpose_for_job`), and a `BudgetExhausted` refusal makes the job wait (`standing.wait_for_budget`) instead of failing; other errors fail with a plain message (`llm/failures.message`).
8. **Frozen execution contract.** At the first stage the contract (models, prompts, schemas, knowledge base) is written into `input_refs`; later stages fail with `CONTEXT_CHANGED_MESSAGE` if `stable_contract` differs (`briefs/workflow.py:349-358`). `max_tokens` is excluded.
9. **Artifacts.** `save` writes `brief-runs/<run>/<stage>/<hash>.json` and finishes the job with `{artifact, hash}`; `output` re-reads and checks the hash (l.227-250).
10. **The call.** `briefs/runtime.call` (`bp/briefs/runtime.py:246-266`) → `llm.workflow.chat(Flow, ...)` (`bp/llm/workflow.py`): cache by fingerprint, recover an earlier attempt, live gate (`mode == live and generation_enabled and flow.live_enabled`), per-run chat budget, one repair, `llm_runs` row; replay mode answers only from saved responses.
11. **Retry and regenerate.** `POST /jobs/{id}/retry` re-queues a failed/waiting job (`repository.py:~440-460`); `regenerate` (l.188-220) makes a new run key when the pinned context changed.

A smaller single-call model is `bp/cycle/refresh.py` (Gate 1 refresh): `SCOPE = STAGE = "card_refresh"`, one job with `**placement(STAGE)`, its own `Flow`, `plain_reason` for refusals, `status_for` for the screen, and `standing.purpose("refreshes")`.

### 3.5 Standing budgets (`bp/llm/standing.py`)

- `PURPOSES = ("cycle","briefs","refreshes","embedding","extraction","context_mining")` (l.27); `STAGE_PURPOSE` maps call stages (l.33-35); `SCOPE_PURPOSE` maps run scopes: `brief_generation → briefs`, `brief_revision → refreshes`, `card_refresh → refreshes` (l.64-65). No `pack_generation`, no pack stage.
- Caps come from settings `budgets.weekly_usd.<purpose>` and `budgets.weekly_calls.<purpose>` (`bp/settings_store.py:410-422`, `BUDGET_DEFAULTS`; a new purpose needs an entry here). Production runs USD 5.00 a week (briefs at D42's 2.70).
- `ensure` creates the week's plan once with `stages = ALL_STAGES` at that moment (l.100-117); `run_plans.py:107` refuses any stage outside it. `storage_cli budgets show|set|renew` manage it; `GET /storage/budgets` shows it (`bp/cycle/api.py:185-192`).

---

## 4. The `calendar/` package

- **What it is:** scheduling of exact pack assets, built for the 004 release. `bp/calendar/contracts.py` (80 lines): `Schedule{expected_pack_manifest_hash, whole_pack, items[1..5]{asset_id, expected_asset_hash, entry_id, expected_revision, scheduled_for (with offset), display_timezone}}`, `Reschedule`, `Cancel`. `bp/calendar/service.py` (259 lines): `authorize` (flag `features.calendar` + `schedule`, l.11-15), `config` (l.18-32: worker readiness, timezone, pack flags), `entry_view` (l.39-63: warnings when the asset or manifest changed; `needs_review`), `schedule` (l.66-...: only an approved pack whose `blockers(approved=True)` are empty; one active entry per asset and channel; a published asset needs a new version), `reschedule` (l.164), `cancel` (l.192), `listing` (l.239).
- **Channel:** `email` for email assets, `instagram` otherwise (l.35-36). Status `draft/scheduled/needs_review/cancelled/published`; "published" needs a confirmation time, and nothing in the code sets it (no publishing integration).
- **Relation to packs:** it depends on `packs.service` (`blockers`, `locked`, `assets`, `audit`), so it inherits the v1 slot assumption through `blockers`. `publications.confirmed` (`bp/publications.py:4-21`) reads published calendar entries joined to `content_assets` and `content_briefs` for prior coverage (used in `gate_two.prior_state`, l.90).
- **State:** off (`features.calendar=false`); `Calendar-Deployment.md` was corrected on 23 October (S.B15). The v4 email's `send_header` and the hand-off's `publishing_order` are the inputs a placement step would use. Per plan section 6 and D43, calendar and a third gate are in scope only if D43 says so.

---

## 5. Frontend

### 5.1 Mode and wiring

- `frontend/src/App.tsx:13-15`: `VITE_ATELIER_MODE === 'backend'` renders `AppRoutes`, else `MockStudioApp`. The Dockerfile passes `backend` (7.F2); production runs backend mode since N3.
- Feature flags come from `GET /storage/flags` (`bp/storage_api.py:209-214`: `briefs, packs, calendar, context`) through `useFeatureFlagState`.

### 5.2 The real app

| Item | Where | State |
| --- | --- | --- |
| v4 reader | `BriefBodyV4View`, `BriefReaderV4` (`frontend/src/components/BriefReaderV4.tsx:44-103`) | Read-only v4 body: brief sections, Email (send header, all subjects, preview, opening/body/ending), Reels (kind, cover, hook, screens, script or opening, personal lines, caption, offer descriptor), Carousel (title, slides, caption) |
| Gate 2 | `BriefGateV4` (l.107-110) wraps `BriefReaderV2` panels (edit by path from `briefFields.ts`, refresh, versions, context, blockers, CTA, answers, decision) | Live |
| Brief page | `SQLBriefs.tsx` | `packMapped = schema_version === 'brief_document_v1'` (l.47); `handoffNote` (l.49-53) tells a v2-v4 reader "Content packs are made from version 1 briefs only"; `generatePack` posts `/briefs/{id}/pack` and navigates to `/studio/packs/{pack_id}` (l.117-124); the "Generate saved content pack" panel shows only for `can_consume && packMapped && productionConfig.can_generate` (l.132-137); `PublishedCapture` when `can_record_published` (l.176) |
| Pack screens | `StoredPacks.tsx` (652 lines): `StoredPacks` list (l.561-), `StoredPackDetail` (l.250-) reads `/packs/{id}`, `/packs/{id}/production`, `/calendar/config`; `AssetCopy` (l.186-248) renders v1 fields (subject, preview_text, body, spoken_script, slides headline/body/direction, caption string, visual_directions, CTA, claims with qualifications); "Approve exact pack" / "Reject pack" (l.385-424); `SchedulePicker` (l.23-) | Behind `flags.packs`; no test file |
| Routes | `frontend/src/app/routes.ts:18-22` (`studioPacks`, `studioPack`, `scheduled`, `packs`, `pack`); `AppRoutes.tsx:41-42, 60-67` (`FlagGate allow={PACKS}`); `BackendStudio.tsx:6-14` adds the "Content Packs" tab when `flags.packs`, "Scheduled Content" when packs and calendar; `viewRegistry.ts:22-24` lists them as `backend` views |
| Calendar | `BackendCalendar.tsx` (65 lines, reuses `SchedulePicker`), Home page | Behind `flags.calendar` |

### 5.3 The mock demo's pack screens (20 October)

- **Flow:** `frontend/src/mock/App.tsx` (633 lines) with gates `gate1_angle → gate2_brief → gate3_pack → approved_for_giselle`. In `mock/components/IdeaDetailModal.tsx`: tabs Content Angle / Content Brief / Content Pack / Schedule (l.155); the brief tab's button "Approve Brief & Generate Content Pack" sets a spinner ("Generating content pack…") and moves to `gate3_pack` (`handleApproveBriefWithPackGeneration`, l.107-114, l.310); "View content pack →" (l.312).
- **Pack tab** (l.318-410): a sticky tablist "Content pack deliverables" with Email, Carousel, Reel 1, Reel 2, Reel 3 (keyboard arrows); each piece is a card with an order badge (01-05), kind icon (Mail/Layers/Video), meta line ("Carousel · N slides", "Reel 1 · face to camera (story)"), title, and a per-piece **Copy** button; below, labelled sections (Email: Date, Send time, Recipients in a 3-column grid, then Subject/Preview/Email body; Reels: Cover, On-screen hook, Script or On-screen text, Caption). Empty state: "Five contents land after the brief is approved".
- **Footer** (l.482-488): "Approve Content Pack & Schedule" (then "Go to Schedule" / "View Schedule") and **"Copy all Content"** (`draftPackToText`: "CONTENT SUITE: <title>" then each piece).
- **Data:** `frontend/src/data/fathomContentPacks.ts` (401 lines, three hand-built packs, anonymised by S.B15), `ContentPack` type (`frontend/src/types/atelier.ts:56-83`: `suppliedCopy{email, carousel, reels[3]}` verbatim text, plus structured email/carousel/reels, captions, `ruleChecks`); `stages/ideaStages.ts:249-281` (`selectDraftContents` parses `suppliedCopy` into labelled sections; `draftPieceToText`, `draftPackToText`).
- **Grid:** `components/ContentPacksView.tsx` ("Content Packs & Deliverable Scripts", packs grouped by month, CTA track badge, Scheduled / To be scheduled) is a `fixture` view (`viewRegistry.ts:36, 43-47`, "Sample: content packs").
- R58 applies: the mock's packs are hand-built references and must never be shown as system output.

### 5.4 Allowlist (`frontend/server/allowlist.mjs`)

Already relayed: `GET packs`, `packs/{id}`, `packs/{id}/production`, `calendar`, `calendar/config` (l.17), `GET briefs/{id}/handoff` (l.15); `POST packs/{id}/decision|schedule`, `briefs/{id}/pack`, `calendar/{id}/cancel` (l.43); `PATCH (angles|briefs)/{id}` only (l.46): no `PATCH packs/...`. Query rule for `/packs`: `week_id`, `status`, paging (l.89). `allowlist.test.mjs` scans the app source and fails when a called route is missing; `server/calendar.test.mjs` and `routes.test.mjs` cover the pack and hand-off relays.

### 5.5 Wiring a new screen

1. Backend route + response model in `bp/api_models.py`; `python -m backend_pipeline.openapi --write` (`bp/openapi.py`, CI runs `--check`).
2. `npm run api:types` (`frontend/tools/api-types/generate.mjs`) regenerates `src/api/schema.d.ts`; `src/api/types.ts` re-exports names.
3. Add the path to `allowlist.mjs` (GET/POST/PATCH arrays, query rules, long-read list if it is an export) and a server test.
4. Add the path to `app/routes.ts`, a `<Route>` in `AppRoutes.tsx` (with `FlagGate`), the tab in `BackendStudio.tsx`, and a `backend` entry in `viewRegistry.ts`.
5. Use `useApiQuery` / `apiPost` / `useGuardedAction` / `ConflictNotice` / `StageProgress` (`components/shared/`), `requestId()` for idempotent mutations (`utils/production.ts`).

---

## 6. Learning and published capture

- **L.B9** is `bp/knowledge/capture.py`: `POST /storage/briefs/{id}/published` and `GET .../published` (`bp/storage_api.py:431-438`), UI `frontend/src/components/PublishedCapture.tsx` (channels email, reel, carousel, caption, stories; piece number). `record` (l.213-264) stores a confirmed `published_content` row (migration 006, `006_context_store.sql:54-79`, `source_kind='approved_brief'`, `source_ref = capture:<brief_id>:<channel>:<piece>`, `sibling_group = brief_id`), a `decisions` row, optional metrics, an optional embedding, and **`details.edit`** = the difference between `brief_copy(brief, channel, piece)` and the final (`difference`, l.108-121; field `published_<channel>`).
- **How it feeds learning:** `knowledge/mining.edit_diffs` (`bp/knowledge/mining.py:175-205`) reads Gate 2 field diffs between brief versions plus every `published_content.details.edit`, so the weekly learning loop categorises them (L.B6) and repeated corrections become rule candidates (L.B14, `knowledge/repeats.py`). The strategist's situational block reads published rows ("do not repeat a central point").
- **Gap for v4:** `brief_copy` (l.59-100) predates v4. For a Reel it takes `cover_text + script`, or `cover_text + spoken_opening + beats` without a script, so a b-roll Reel's `screens` and every per-asset caption are missed; the carousel is slides only; `caption` returns None. A pack stage that stores per-piece copy keyed `reel_1`, `carousel`, `email` can give capture an exact "what we handed over" text per piece, and a hand edit made in the pack (R56) can be recorded as an authored edit the same way.
- **Two publication records exist side by side:** `calendar_entries.status='published'` (read by `publications.confirmed` for prior coverage) and `published_content` (read by the learning loop and the strategist). Neither links to the other.

---

## 7. Settings and deploy

- **`backend/deploy/production-settings.json`** keys: strategist v7 profile, models (default and extraction Luna, angles Sol, card verification and context mining Sonnet 5.5, brief Sol, brief review Sonnet 5.5), scene profile v3, card verification v4, `prompts.profile.brief = brief_document_v4`, writer `v5`, `models.completion_tokens 32000` (+ extraction 32000), `features.briefs true`, `features.context true`, `context.schedule.mining_live true`. **No pack key** (`features.packs`, `models.pack_writer`, `models.pack_review` absent).
- **`settings_store.py`**: `features.packs/calendar` (l.312-319), pack models (l.208-211), pack effort (l.217-221), snapshot scope `pack` (`P = ("pack",)`, l.186; `keys_for`, l.457; `snapshot_refs`, l.877), budgets (l.410-422).
- **`DEPLOYMENT.md`**: editorial worker runs "brief and pack stages" on `interactive,default` (l.68); `ATELIER_PACKS_ENABLED`, `ATELIER_CALENDAR_ENABLED` "Out of scope; see backend/docs/Calendar-Deployment.md" (l.119); setting table rows for `models.pack_writer`, `models.pack_review`, effort, `features.packs` (l.191-201, 229); packs and calendar keep their own role lists when there is no `users` row (l.528); `/me` capabilities (l.540). `research/production-2026-10/README.md:53`: production has `ATELIER_ALLOW_GENERATION`, `_ENCODING`, `_REFINEMENT`, `_BRIEF_GENERATION` on; `ATELIER_ALLOW_PACK_GENERATION` is not mentioned (so off).
- **`backend/docs/Calendar-Deployment.md`**: the 004 pack and calendar runbook (flags, role lists, exact pack models, both generation switches, the five-asset workflow).

---

## 8. Tests

- **Backend:** 159 files in `bp/tests/`, 58 of them `*_db.py`. Files touching packs: about 25 (most only assert no pack exists); substantive: `test_calendar.py` (7, end-to-end v1 pack + schedule), `test_calendar_contracts.py` (5), `test_brief_v2_db.py` (refusal test), `test_jobs_db.py`, `test_roles.py`. Hand-off: `test_brief_handoff.py` (9) plus v2/v3/v4 suites.
- **DB suite pattern:** a test skips unless `ATELIER_TEST_DATABASE_URL` points at an isolated database; `platform_db.platform_url` recreates `atelier_test_platform_test` once per session and migrates to the latest (`bp/tests/platform_db.py:22-28`); `platform_setup` truncates every table and admits two synthetic weeks. CI runs the suite twice: without a database (DB tests skip) and with one (`.github/workflows/ci.yml:44, 94`).
- **M1 exit model** (`bp/tests/test_m1_exit_db.py`, 498 lines): fixture `live` (l.164-231) applies `production-settings.json` as settings rows, switches live mode with standing budgets and no run-plan variable, patches `httpx.HTTPTransport.handle_request` to `FakeOpenRouter` (l.126-162) so every call goes through the real `LiveProvider` (run plan reservation, routing, `llm_runs`, settlement), caches model routes, embeds the chunks, and drives everything through `TestClient(router(s))` with approver headers. Helpers `worker`/`run` drain jobs as production does (l.233-243); `settle_gate_two` (l.372-407) resolves each named blocker as the screen does. Failure tests: 402 refusal (l.422), budget cap and release (l.443), worker killed mid-brief (l.470). A pack exit test would extend `settle_gate_two` with the decision, then assert the pack queues on approval (or on request), runs under its budget, renders each piece, and survives 402 / cap / kill.
- **Frontend:** `ContentPacksView.test.tsx` (3), `PackSchedulePopover.test.tsx` (4), `ScopeFlags.test.tsx` (7; `handoffNote`, `packMapped`), `BackendCalendar.test.tsx` (5), `mock/mockFlow.test.tsx` (1), `server/calendar.test.mjs`, `server/routes.test.mjs` (hand-off relay), `server/allowlist.test.mjs`. `StoredPacks.tsx` has no test.

---

## 9. Reuse / replace / build new (for a v4-based pack stage)

| Part | Verdict | Why |
| --- | --- | --- |
| Tables `content_packs`, `content_assets`, `calendar_entries`, `mutation_receipts` | **Reuse** | Generic columns; free-text `slot_key`; no asset-count cap; already migrated in production. `reader_contribution` can take the piece's `direction.job` |
| Hand-off view (`briefs/handoff.py`, `GET /briefs/{id}/handoff`) | **Reuse as the only input** (R56) | Version-independent pieces, keys, anchor, spine, consent, `can_consume`. Possible small additions: per-piece claim lists by `field` prefix, a hash of the view |
| `packs/service.py`: `manifest`, `locked`, `decide`, `detail`, `listing`, `audit`, receipt pattern | **Reuse with edits** | Replace the fixed `SLOTS` check in `blockers` with "the pieces of the hand-off view, in order"; validate bodies against a v4 piece schema; keep lineage, manifest and bound approval |
| `packs/contracts.py` (`Email`, `Carousel`, `Reel`, `Claim`, `SLOTS`, `STAGES`) | **Replace** | v1 shapes; v4 pieces carry the copy (send header, on-screen hook, screens, captions, title) |
| `packs/workflow.py` `queue` | **Replace** (keep its skeleton) | Remove the `is_v2` refusal and brand-bundle read; read the hand-off view; run key on `brief_id + approved_hash (+ mode)`; build jobs from the view's pieces |
| `packs/workflow.py` `execute`, `validate_copy`, per-slot `pack_write` | **Replace** | Writing copy again contradicts R56; any model step (if D43 wants one, for example a caption pass or a pack review) needs its own contract and prompt |
| `packs/runtime.py` | **Reuse the pattern, fix** | Use `stable_contract` (drop `max_tokens`), add the knowledge base if a model call reads it, and a budget purpose |
| Prompts `pack_write.v1.md`, `pack_review.v1.md` | **Replace or drop** | Generic, five-slot, no first-touch or 4.3 rules |
| `first_touch_findings`, `asset_findings`, `week_findings`, `checks_v4`, `pack_markdown`, `scripts/pack_checks.py` | **Reuse** | Deterministic pack-level checks over a v4 body; re-run on hand edits |
| `render_v4.asset_lines`, `review_document.render`/`assets` | **Reuse** | Already the pack layout WIA reviewed; a per-pack Markdown export can call them |
| `production_api.py` routes | **Reuse, extend** | Keep `/packs`, `/packs/{id}`, `/production`, `/decision`; `POST /briefs/{id}/pack` keeps its path; add a piece edit route if D43 wants hand edits in the pack |
| `api_models.py` `PackDocument`, `StoredAsset` | **Replace** | v1 field set and `asset_type` literal |
| Calendar (`calendar/`) | **Reuse only if D43 includes scheduling** | Works on any approved pack once `blockers` is fixed; 5 items per request limit |
| Standing budget for packs | **Build new** (if any paid call) | New purpose (`packs`) in `PURPOSES`, `LABELS`, `SCOPE_PURPOSE`, `STAGE_PURPOSE`, `BUDGET_DEFAULTS`; or map to `briefs` only after the week renews |
| Gate 2 auto-trigger | **Build new** (if D43 says packs start on approval) | Same savepoint pattern as Gate 1 |
| Frontend v4 pack view | **Build new**, reusing `BriefBodyV4View` pieces and the mock's layout | `StoredPacks.AssetCopy` is v1; the mock's tabbed piece view, per-piece Copy and Copy all are the reviewed target |
| `SQLBriefs.packMapped`/`handoffNote` | **Replace** | They refuse non-v1 briefs |
| `capture.brief_copy` for v4 | **Fix** (small) | Screens, captions, carousel title missing; could read the pack's per-piece copy |
| Pack exit test | **Build new**, modelled on `test_m1_exit_db.py` | Reuse `live`, `FakeOpenRouter`, `settle_gate_two`; replace `test_calendar.py`'s v1 fixture |

---

## 10. Concrete integration points

| # | Hook | File and function | What to do |
| --- | --- | --- | --- |
| 1 | Trigger on Gate 2 approval | `bp/briefs/gate_two.py` `decide` (l.421-437), after `record_decision` and before the run is closed | `if decision=='approved' and repo.settings.packs_enabled:` call a new `packs.workflow.queue_in_transaction(repo, conn, brief_id, actor, mode)` inside `with conn.transaction():` (savepoint), recording a failed `pack_generation` run on error, exactly as `gate_one.decide` does at `bp/gate_one.py:385-388`. Change the event text "no production jobs queued" |
| 2 | Manual trigger and retry | `bp/production_api.py` `generate` (l.66-68) → `bp/packs/workflow.py` `queue` (l.12-127) | Read `gate_two.handoff(repo, brief_id, actor)`; require `can_consume`; drop l.35-48 (v1 refusal, brand bundle); key on the approved hash |
| 3 | Input | `bp/briefs/handoff.py` `view` (l.304-341), `pieces` (l.85-124) | Pieces become `content_assets` rows: `slot_key = piece.key`, `ordinal` in plan order (or anchor first), `asset_type = piece.channel`, `reader_contribution = piece.direction.job`, `content_body = {copy, direction, ...}` |
| 4 | Job type and queue | `bp/jobs/policy.py` `queue_for` (l.69), `TIMEOUTS` (l.22-42) | Keep the `pack_` prefix so pack jobs go to `interactive`; add timeouts for any model stage |
| 5 | Worker routing | `bp/sql_pipeline.py` `SQLWorker.execute` (l.228-231) | `pack_*` stages already route to `packs.workflow.execute`; replace its stage table |
| 6 | Budget purpose | `bp/llm/standing.py` `PURPOSES` (l.27), `LABELS` (l.28-29), `STAGE_PURPOSE` (l.33-35), `SCOPE_PURPOSE` (l.64-65); `bp/settings_store.py` `BUDGET_DEFAULTS` (l.410-411) | Add `packs` (or map `pack_generation` to `briefs`); remember `run_plans.py:107` and `ensure` (l.100-117) freeze the week's stage list |
| 7 | Frozen contract and snapshot | `bp/packs/runtime.py` `execution_contract`/`check_dependencies` (l.21-56); `bp/settings_store.py` `snapshot_refs("pack", ...)` (l.877) | Compare with a `stable_contract` (drop `max_tokens`); keep the settings snapshot in `input_refs` |
| 8 | Checks | `bp/briefs/asset_checks.py` `asset_findings` (l.415), `week_findings` (l.439), `week_siblings` (l.464); `bp/briefs/first_touch.py` `first_touch_findings` (l.374); `bp/briefs/validation_v4.py` `checks_v4` (l.60) | Run on the pack's assembled body at assembly and after every hand edit; `anchor_key` from the hand-off anchor; siblings = the week's other packs |
| 9 | Pack status and approval | `bp/packs/service.py` `blockers` (l.39-73), `manifest` (l.18-36), `decide` (l.137-180) | Replace the `SLOTS` check (l.50-51) and slot schema validation (l.58-61); keep lineage, manifest and bound approval |
| 10 | API routes | `bp/production_api.py` `install` (l.16-85); `bp/api_models.py` (l.998-1060) | v4 `PackDocument`/`StoredAsset`; optional `PATCH /packs/{id}/assets/{asset_id}` (hand edit by path, reusing `briefs/paths.py`) and `GET /packs/{id}/export.md` (reusing `render_v4.asset_lines`) |
| 11 | Settings and deploy | `backend/deploy/production-settings.json`; `bp/settings_store.py` (l.312-319); env `ATELIER_ALLOW_PACK_GENERATION` (`bp/storage_config.py:92`) | Add `features.packs: true` (and pack models only if a model step exists) via `storage_cli settings apply`; document in `DEPLOYMENT.md` l.119 and `Calendar-Deployment.md` |
| 12 | Relay allowlist | `frontend/server/allowlist.mjs` GET (l.17), POST (l.43), PATCH (l.46), `LONG_READS` (l.151-156) | Existing pack routes are listed; add any new route (edit, export) and its server test |
| 13 | Brief page | `frontend/src/components/SQLBriefs.tsx` `packMapped` (l.47), `handoffNote` (l.49-53), generate panel (l.132-137) | Show the pack state for any `can_consume` brief; link to the pack; drop the v1-only message |
| 14 | Pack screen | `frontend/src/components/StoredPacks.tsx` `AssetCopy` (l.186-248), `StoredPackDetail` (l.250-) | Render v4 pieces (reuse `BriefReaderV4.tsx` Reel/Caption/Email blocks); port the mock's tabbed layout, per-piece Copy and Copy all (`mock/components/IdeaDetailModal.tsx:318-410, 482-488`; `stages/ideaStages.ts:274-281`) |
| 15 | Routes, tabs, registry | `frontend/src/app/routes.ts:18-22`; `AppRoutes.tsx:41-42, 60-67`; `BackendStudio.tsx:6-14`; `viewRegistry.ts:22-24` | Already present behind `flags.packs`; keep or rename |
| 16 | Learning | `bp/knowledge/capture.py` `brief_copy` (l.59-100), `record` (l.213-264); `bp/knowledge/mining.py` `edit_diffs` (l.175-205) | Read v4 screens and captions (or the pack's per-piece copy) so published finals diff correctly; record pack hand edits as authored edits |
| 17 | Tests | New `bp/tests/test_packs_v4_db.py` and a pack exit test on `test_m1_exit_db.py`'s `live` fixture; update `test_brief_v2_db.py:217`, `test_calendar.py` (`produced`), `ScopeFlags.test.tsx` | Cover: queue on approval, idempotent run key, two-Reel brief, stale brief after approval, budget wait, 402, killed worker, hand edit re-check, export |
