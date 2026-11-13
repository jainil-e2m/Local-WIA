# Stage 3: People and roster. Implementation plan

Written 30 Oct 2026 for an AI coding agent to build end to end. Read the whole plan before changing anything.

> **Privacy rule.** This repo is pushed to GitHub.
> - **Code, tests and example files:** no real names, email addresses, Slack IDs or ClickUp IDs at all. Tests use invented people at `example.com`, `example.org` and `example.net`.
> - **Docs:** may name WIA team members and WIA's own shared role inboxes (hello@, support@) where needed to explain the design, as this plan does. They must never contain personal email addresses or provider IDs.
> - **Real roster data** lives only in `backend/.local/`, which is git-ignored.

---

## 1. Goal

"Who said it" and "who owns it" must resolve to **one person** across Slack, ClickUp, Gmail, Calendar, Drive and Fathom. Later stages build on this:

| Later stage | Needs from S3 |
|---|---|
| S8 Action Register | Action owners; whether WIA or the client owes an action |
| S9 Read models | "Awaiting our reply"; "My clients" |
| S10 Access | Per-client visibility by account team |
| S13 Admin page | Roster, unknown-people queue, account teams |

**In scope:** people, their identities, shared mailboxes, linking every stored provider identity to a person or a "party", the unknown-people queue, account teams (owner plus roles), and making the "is this internal?" check roster-aware.

**Out of scope:**
- KB user accounts, login and sessions (S10).
- Any UI (S13).
- Any outbound writes (S12).
- Any LLM work.
- Changing how records are associated with clients. That stays contact- and scope-based, as built in S2. S3 only adds who the people are.

---

## 2. Decisions this plan relies on

| Date | Decision |
|---|---|
| 29 Oct | Admins manage mapping in the UI. Every command lives in one service called by both the CLI and the later API, writes an audit event, and checks `expected_revision`. |
| 30 Oct | **Partners** (agencies, consultants, vendors that serve several clients) are never client contacts. A partner may stay *linked* to one client (e.g. a consultant linked to the venue they work for) but never decides association. This is already built in S2 as `sender_rules` plus `scoping.live_contacts`. |
| 30 Oct | Team members' personal and other-business addresses were filed as `sender_rules` of kind `team` as a stop-gap. **S3 replaces this with the roster.** Team rules keep working: they are read alongside the roster, never deleted automatically. |
| 30 Oct | Shared inboxes (`hello@`, `support@` and similar) are **roles, not people**. A message from one resolves to the shared mailbox, plus the person who held it at that time when known. |
| 30 Oct | Prospects and accelerator members are in scope for the KB. Model them as people of kind `prospect` / `programme_member` if they appear. No special logic yet. |
| 30 Oct | No email bodies are stored. This doesn't affect S3, which works only on identities. |

---

## 3. Current state (read these files first)

| Area | File | What it does today |
|---|---|---|
| Identities | `backend/models/db/sources.py`: `ProviderIdentity` | One row per (connector account, `external_key`), with `display_name`, `email` and `is_internal`. `person_id` is a bare UUID column with **no FK and no table behind it**. |
| Identity writes | `backend/services/intake/persist.py`: `IdentityCache.resolve()` | Upserts a `ProviderIdentity` for every unit author and record participant. Sets `is_internal` from `shared.emails.is_internal(email)`, which knows domains only, so it misses team members' personal addresses. |
| Unit authors | `backend/models/db/sources.py`: `ContentUnit.author_identity_id` | FK to `provider_identities`. |
| External keys by provider | `backend/services/intake/adapters/*.py` | Slack: user ID (`U…`), and `bot:B…` for bots. ClickUp: numeric user ID, with email when present. Gmail, Calendar, Drive: lowercased email. Fathom: email, or `speaker:<display name>` when the speaker has no email. |
| ClickUp assignees | `adapters/clickup.py` `_normalise()` | `attributes["assignee_ids"]` on each task version (ClickUp user IDs). Assignees and the creator are also `participants`. |
| Internal check | `backend/services/shared/emails.py` | `INTERNAL_DOMAINS` plus subdomains, `is_internal()`, `is_automated_sender()`, `within()`. Pure functions, no DB. |
| Client registry | `backend/models/db/registry.py` | `Business`, `BusinessAlias`, `Contact` (an email *or* a domain per client; status candidate/approved/rejected; `revision`), `ClientSourceDecision`, `SenderRule` (team/partner/blocked). |
| Mapping commands | `backend/services/clients/mapping.py` | All S2 admin commands: `MappingError`, `RevisionConflict`, `_audit`, `_check`, `SenderRules`, `contact_conflicts`, `partner_links`, `coverage`. **Copy its style** for the new people service. |
| Live contacts | `backend/services/intake/scoping.py`: `live_contacts()` | Approved contacts of active clients, minus any address covered by a sender rule. |
| Discovery filter | `backend/services/intake/discovery.py`: `filter_contacts()`, `_never_client()` | Drops internal, platform, automated and sender-rule addresses before proposing client contacts. |
| CLI | `backend/scripts/kb.py` | argparse subcommands; mapping commands use `actor="cli"`. |
| Migrations | `backend/sql/migrations/versions/` | Chain: `18e642a0961c` → `b05a20261028` → `c02a20261029` → **`c03a20261030` (head)**. Use `op.f("ck_<table>_<name>")` for check constraint names; the naming convention is in `models/db/base.py`. |
| Tests | `backend/tests/` | `conftest.py` recreates `kb_test` and truncates all tables after each test. Examples to copy: `tests/services/test_client_mapping.py` and `tests/services/test_discovery_filters.py`. 110 tests pass today. |
| Real roster draft | `backend/.local/roster.draft.yaml` (git-ignored) | Built 30 Oct from Slack, ClickUp and Fathom: 9 current people, 14 former, 5 shared mailboxes, and account-team suggestions. **Not** in the loader's final format (§6.1). Convert it. |

The local dev DB holds 24 active clients, approved scopes and contacts, and identities from an earlier 30-day test backfill of 4 clients. Use it for the dry-run checks in §9.

---

## 4. Data model: new migration `c04a20261030_people_roster.py`

`down_revision = "c03a20261030"`. Add the models to `backend/models/db/people.py` (new file) and export them from `backend/models/db/__init__.py`.

### 4.1 `people`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | `IdMixin` |
| name | String(200) | Display name |
| kind | String(20) | `staff`, `contractor`, `former`, `shared_mailbox`, `service_account`, `client_contact`, `partner`, `prospect`, `programme_member`, `unknown` (check constraint) |
| business_id | UUID FK → businesses, nullable | Set for `client_contact` (their client) |
| functions | JSONB list | Internal people only, e.g. `["ads_google","ads_meta"]`. Values: `leadership`, `operations`, `support`, `client_communication`, `review`, `ads_google`, `ads_meta`, `landing_page_feedback`, `leadlock_copy`, `leadlock_technical`, `creative` |
| status | String(20) | `confirmed` or `pending` (pending = from the draft, not yet confirmed by WIA) |
| merged_into_id | UUID FK → people, nullable | Duplicates are merged, never deleted |
| notes | String(500), nullable | |
| revision | Integer default 1 | Admin edits use `expected_revision` |
| created_at / updated_at | | `TimestampMixin` |

Helper property: **internal kinds** = `staff`, `contractor`, `former`, `shared_mailbox`, `service_account`.

### 4.2 `person_addresses`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| person_id | UUID FK → people, indexed | |
| kind | String(20) | `email`, `slack_user`, `clickup_user`, `fathom_email`, `display_name` (the last only for Fathom `speaker:` keys) |
| value | String(320) | Lowercased for `email`/`fathom_email`; raw ID otherwise |
| source | String(30) | `roster`, `admin`, `client_contact` |
| created_at | | |

Unique `(kind, value)`: one address belongs to one person.

### 4.3 `mailbox_holders` (who covers a shared mailbox, over time)
`id`, `mailbox_person_id` (FK people, must be kind `shared_mailbox`), `holder_person_id` (FK people), `valid_from` (Date, nullable), `valid_to` (Date, nullable), `note`. The current holder has `valid_to` null.

### 4.4 Changes to `provider_identities`
Add:
- a real FK on `person_id` → people;
- `party` String(20), nullable: `internal`, `shared_mailbox`, `client`, `partner`, `automated`, `bot`, `unknown`;
- `party_business_id` FK → businesses, nullable (set when the party is `client`);
- `resolution_basis` String(30), nullable: `provider_id`, `email`, `client_contact`, `client_domain`, `partner_rule`, `automated`, `display_name`, `admin`;
- `resolved_at` timestamptz, nullable.

Keep `is_internal`, but derive it from `party` (§5.3).

### 4.5 `account_team_members`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| business_id | FK businesses, indexed | |
| person_id | FK people | Internal kinds only (enforced in the service) |
| role | String(30) | `owner`, `ads_google`, `ads_meta`, `copy`, `technical`, `creative`, `operations` |
| status | String(20) | `suggested`, `confirmed`, `ended` |
| source | String(30) | `clickup_assignments`, `admin`, `roster_file` |
| evidence | JSONB | e.g. `{"clickup_tasks_120d": 28}` |
| started_on / ended_on | Date, nullable | |
| confirmed_by / confirmed_at | | |
| revision | Integer default 1 | |
| created_at / updated_at | | |

Partial unique indexes:
- one row per `(business_id, role, person_id)` where status is not `ended`;
- **one `confirmed` owner per business** where `role='owner' AND status='confirmed'`.

Write the migration by hand in the style of `c03a20261030_sender_rules.py`. Keep `downgrade()` working for the new tables. Add a SQL backfill that sets `party='internal'` where `is_internal` is true (§5.3 recomputes everything anyway).

---

## 5. Services

### 5.1 `backend/services/people/__init__.py` (empty) and `backend/services/people/roster.py`: people commands
Follow `services/clients/mapping.py`: session-taking functions, `actor` argument, `_audit()` events, `expected_revision` checks, and a `PeopleError(ValueError)` exception (reuse `RevisionConflict` from mapping).

- `create_person(s, *, name, kind, functions=(), business_id=None, status="confirmed", actor) -> Person`
- `update_person(s, person_id, *, expected_revision, actor, name=None, kind=None, functions=None, status=None)`
- `add_address(s, person_id, kind, value, *, actor, source="admin")`. Lowercases emails. Raises when the address belongs to someone else, or is a public-domain *domain*. Addresses are always exact.
- `remove_address(...)`
- `merge_people(s, keep_id, merge_id, *, actor)`. Moves addresses, identities and team rows to `keep_id`, then sets `merge_id.merged_into_id`. Never deletes.
- `set_mailbox_holder(s, mailbox_id, holder_id, *, valid_from=None, actor)`. Closes the previous open holder row and adds the new one.
- `load_roster(path, actor="cli") -> dict`. Idempotent YAML loader (§6.1), matched on name plus kind. Re-running changes nothing.
- `internal_addresses(s) -> set[str]`. Every `email`/`fathom_email` of people with internal kinds, **plus** `sender_rules` of kind `team` (backward compatible).
- `internal_ids(s) -> dict[str, set[str]]`. `{"slack_user": {...}, "clickup_user": {...}}` for internal kinds.

### 5.2 `backend/services/people/resolve.py`: identity → person/party
`resolve_identity(s, identity: ProviderIdentity, ctx: Resolver) -> None` sets `person_id`, `party`, `party_business_id`, `resolution_basis` and `resolved_at`. `Resolver` is built once per run with every lookup preloaded: addresses, live contacts, sender rules, provider of each connector account. Rules, **first match wins**:

1. `external_key` starts with `bot:` → `party=bot`.
2. Provider-native ID: Slack `external_key` matches a `slack_user` address, or ClickUp matches `clickup_user` → that person (`basis=provider_id`).
3. The identity's email (or an email-shaped `external_key`) matches an `email`/`fathom_email` address → that person (`basis=email`).
4. Fathom `speaker:<name>`: an exact case- and accent-insensitive match on the full name of one internal person, or on a `display_name` address → that person (`basis=display_name`). Never match client names this way.
5. Email is an approved **client contact address**, i.e. `Contact.email`. Find or create a `client_contact` person for that contact's business, with the email as an address (`basis=client_contact`), and set `party=client` and `party_business_id`.
6. Email's domain matches an approved client **domain** contact → `party=client` with `party_business_id`, **no person** (`basis=client_domain`). A person is created only when an admin asks.
7. Email matches a `partner` sender rule → `party=partner` (`basis=partner_rule`). For partners linked to one client (`mapping.partner_links`), also set `party_business_id`.
8. Email is internal by domain (`shared.emails.is_internal`) or matches a `team` sender rule → `party=internal`, no person yet (`basis=email`). These go to the unknown queue as "internal, not on roster".
9. `shared.emails.is_automated_sender(email)` → `party=automated`.
10. Anything else → `party=unknown`.

**Party from person kind:**
- `staff`, `contractor`, `former`, `service_account` → `internal`
- `shared_mailbox` → `shared_mailbox`
- `client_contact` → `client`, with that business
- `partner` → `partner`
- `prospect`, `programme_member` → `unknown`, with the person set (they are known people, but neither WIA nor a client)

Also in this file:
- `resolve_all(s, only_unresolved=False) -> dict[str, int]` returns counts per party. Must be **idempotent**: a second run changes nothing.
- `mailbox_holder_at(s, mailbox_person_id, when: date) -> Person | None`

### 5.3 Wire resolution into intake
- **`persist.py` `IdentityCache`:** after the upsert, resolve the identity using a per-publish `Resolver`. Build it lazily once per `IdentityCache`, not per identity. Set `is_internal = party in ("internal", "shared_mailbox")`. Keep the upsert's conflict update from wiping `person_id`, `party` or `resolution_basis` set earlier. Only re-resolve when `person_id` is null, or when `party` is `unknown`/null.
- **Performance:** a publish page can touch hundreds of identities. Load the lookups in a handful of queries, never one query per identity.

### 5.4 Make S2 filters roster-aware
- `services/intake/discovery.py` `_never_client()`: also drop any candidate whose email is in `people.roster.internal_addresses()`. Load it once in `run_discovery()` and pass it in alongside the sender rules.
- `services/intake/scoping.py` `live_contacts()`: also exclude any approved contact whose email belongs to an internal person.
- `services/clients/mapping.py` `contact_conflicts()`: flag approved contacts whose email belongs to an internal person, with reason `"team member (roster)"`.
- The adapters' discovery calls `is_internal(addr)` (calendar, fathom, gmail) and stays as it is. Roster filtering happens centrally in `filter_contacts`.

### 5.5 `backend/services/people/teams.py`: account teams
- `suggest_teams(s, days=120) -> int`:
  - Look at task versions of ClickUp records associated with each business (`record_associations`, status `associated`) whose `provider_updated_at` falls within `days`.
  - Count `attributes["assignee_ids"]`, mapped through `clickup_user` addresses to people.
  - Map each person to roles from their `functions`: `ads_google`/`ads_meta` → the same role; `leadlock_copy` → `copy`; `leadlock_technical` → `technical`; `creative` → `creative`; `operations`/`support` → `operations`.
  - Upsert `suggested` rows with the counts in `evidence`. Never touch `confirmed` or `ended` rows. Skip people of kind `former` (report them instead, §6.2).
- `set_team_member(s, business_id, role, person_id, *, actor, started_on=None) -> AccountTeamMember`: creates or confirms. For `owner`, end any other confirmed owner first.
- `end_team_member(s, member_id, *, expected_revision, actor, ended_on=None)`
- `team_for(s, business_id) -> list[...]`
- `clients_for_person(s, person_id) -> list[business_id]` (confirmed rows only). S10 visibility and "My clients" will call this.

---

## 6. Files outside the services

### 6.1 Roster file format
New `backend/roster.example.yaml` (tracked, **invented data only**), and the real `backend/.local/roster.yaml` (git-ignored), converted by hand from `backend/.local/roster.draft.yaml`:

```yaml
people:
  - name: Alex Example
    kind: staff                      # staff | contractor | former | service_account | partner | prospect | programme_member
    status: confirmed                # or pending (default for anything WIA hasn't confirmed)
    functions: [ads_google, ads_meta]
    emails: [alex@example.com]
    slack: [U000EXAMPLE1]
    clickup: ["10000001"]
    fathom: [alex@example.com]
    display_names: ["Alex E."]       # only for Fathom speakers without email
    notes: optional
shared_mailboxes:
  - name: Example main inbox
    email: hello@example.com
    holders: [{person: Alex Example, from: 2026-01-01}]
  - name: Example support inbox
    email: support@example.org
    holders: [{person: Sam Sample, to: 2026-02-28}, {person: Riley Placeholder, from: 2026-03-01}]
account_teams:                       # optional: confirmed rows WIA has given us
  example-client-slug:
    owner: Alex Example
    ads_google: Alex Example
```

Conversion notes for the real file:
- Whitney's two ClickUp user IDs both belong to her person.
- `hello@weddingindustryads.com` is a **shared mailbox** held by Whitney. It is not her personal address, even though her ClickUp owner account and Fathom use it.
- `support@weddingindustryads.com` is the shared mailbox behind ClickUp "WIA Support". Put the ClickUp user ID of "WIA Support" on the **shared mailbox person**, not on Gisselle, with Gisselle as holder.
- `support@leadlockpro.com` is a shared mailbox: Danielle now, and Christina Hill earlier in 2026 (no exact dates; leave them null).
- `ai@weddingindustryads.com` (Slack "AI Dev", ClickUp "E2M AI") is a `service_account`.
- Everyone marked `unknown` in the draft (Crystal Chantel, Courtney Donilon) goes in with `status: pending`. Choose `contractor` for Crystal and `former` for Courtney, and note why.
- Account-team suggestions in the draft are **not** loaded from YAML. They are recomputed by `suggest_teams()` from the DB.

### 6.2 CLI: `backend/scripts/kb.py`
Add subcommands, keeping the existing style:
- `kb roster load backend/.local/roster.yaml`
- `kb people list [--kind K]`
- `kb people unknown [--limit N]`: unresolved identities, most frequent first. Columns: provider, external key, display name, email, party, unit count.
- `kb people link <identity-id> <person-name-or-id>`: admin resolution. Adds the matching address so future identities resolve automatically.
- `kb people resolve [--all]`: runs `resolve_all` and prints counts per party.
- `kb team suggest [--days 120]`
- `kb team set <client-slug> <role> <person-name>` and `kb team end <member-id>`
- `kb team list [<client-slug>]`: shows confirmed and suggested rows. Flags clients with no confirmed owner, and former people still holding work (e.g. ClickUp tasks assigned to someone of kind `former`).

### 6.3 `backend/scripts/export_frontend_snapshot.py`
Where it reads `identities[first.author_identity_id]` (around line 259), show the **person's** name when `person_id` is set, and fall back to the identity's display name. No other change.

### 6.4 Docs
- Update `backend/before_production.md`: mark G-01 (contractor domains) as addressed by S3.
- Add a short "People and roster" section to `backend/README.md` with the CLI commands.

---

## 7. Tests: `backend/tests/services/test_people.py` (new)
Use only invented `example.*` data. Cover:
1. `load_roster` creates people, addresses, shared mailboxes and holders. A second load changes nothing (counts and revisions equal).
2. An address can't belong to two people (`PeopleError`). Emails are lowercased.
3. Resolution order, one test per rule in §5.2: bot; Slack ID; ClickUp ID; email; Fathom speaker name (internal only, not a client); client contact address (creates the `client_contact` person once); client domain (no person); partner rule, including a partner linked to one client; internal domain not on roster (→ internal, and appears in the unknown queue); automated; unknown.
4. A shared mailbox identity → `party=shared_mailbox`. `mailbox_holder_at()` returns the right holder before and after a holder change.
5. `IdentityCache.resolve()` during a publish sets party and person, and a second publish of the same identity doesn't overwrite an admin `link`. Use the `FakeAdapter` pattern from `tests/integration/test_pipeline.py`.
6. `resolve_all` is idempotent.
7. `merge_people` moves addresses, identities and team rows, and sets `merged_into_id`.
8. Discovery: a roster email is never proposed as a client contact (`filter_contacts`). `live_contacts` excludes an approved contact that is on the roster. `contact_conflicts` flags it.
9. `suggest_teams` builds suggested rows from ClickUp task versions with `assignee_ids`. It never overwrites confirmed rows and skips former people.
10. Owner uniqueness: confirming a second owner ends the first. A direct DB insert of two confirmed owners fails on the partial unique index.
11. `clients_for_person` returns confirmed clients only.
12. Revision conflicts on `update_person` and `end_team_member`.

Run: `backend/.venv/Scripts/python -m pytest backend/tests -q --basetemp=<a writable temp dir>`, from the repository root `knowledge_base/wia-knowledge-base`. A bare `--basetemp` is needed on this machine, because the default pytest temp folder is permission-blocked.

---

## 8. Build order
1. Models and migration (§4). Run `alembic upgrade head` on the dev DB and check that `alembic downgrade -1` then `upgrade head` works on an empty DB.
2. `people/roster.py` and the roster loader, with tests 1–2 and 7.
3. `people/resolve.py`, with tests 3–6.
4. Intake wiring (§5.3) and S2 filter changes (§5.4), with test 8. The full suite must still pass.
5. `people/teams.py`, with tests 9–12.
6. CLI (§6.2), export tweak (§6.3), docs (§6.4).
7. Convert the draft to `backend/.local/roster.yaml`, load it on the dev DB, run `kb people resolve --all`, `kb team suggest` and `kb team list`, and record the numbers (§9).

Don't commit or push unless the repo owner asks. Never stage anything under `backend/.local/`.

---

## 9. Done when (S3 success criteria)

**Code**
- [ ] Migration `c04a20261030` applies on the dev DB and on a fresh DB; downgrade works on an empty DB.
- [ ] Every existing test passes (110), plus the new tests in §7.
- [ ] `git diff` adds no personal email addresses, Slack IDs or ClickUp IDs anywhere, and no real names in code, tests or `roster.example.yaml`.

**On the dev DB (after loading `.local/roster.yaml`)**
- [ ] Every current team member, former member, shared mailbox and the service account exist as people with the right kind. Re-loading changes nothing.
- [ ] `kb people resolve --all` classifies **every** `provider_identity`: no null `party`.
- [ ] **Every Slack human user in the workspace and every ClickUp member resolves to a person.** Zero team members end up `unknown`.
- [ ] Contractors on their own domains or personal addresses resolve as `internal` (G-01 fixed).
- [ ] The remaining `unknown` identities are listed by `kb people unknown`. Each is a genuine outsider (prospect, vendor, one-off sender), not a team member or an approved client contact.
- [ ] Re-running resolution changes nothing.
- [ ] `kb team suggest` creates suggested rows for every active client that has ClickUp work in the last 120 days. `kb team list` shows them, plus the clients with no confirmed owner (expected: all of them, until WIA answers) and former people still assigned (expected: Fallon on Press Record).
- [ ] Re-running `kb discover` proposes no roster address as a client contact, and `kb mapping` is unchanged from before S3.

**Needs WIA before S3 is fully closed** (questions in `kb_tab_scope/tobeaskedinnextcall.md` §8)
- [ ] Roles confirmed, and pending people resolved (Crystal Chantel, Courtney Donilon).
- [ ] One confirmed **owner** per active client, and the per-account ads split, entered with `kb team set`.
- [ ] A new owner for work still assigned to former team members.

---

## 10. Pitfalls
- **Never resolve by display name for clients.** Names collide: two clients both have a "Brittany". Display-name matching (§5.2 rule 4) is only for Fathom speakers and only against internal people.
- **Shared mailboxes are not people.** Never attach `hello@weddingindustryads.com` to Whitney's person as a personal address, or every client email to hello@ will look as if Whitney wrote it.
- **ClickUp "WIA Support" is a shared login.** Its user ID belongs to the shared mailbox person.
- **Don't let the identity upsert in `persist.py` reset `person_id`** on conflict. The existing `on_conflict_do_update` sets only `display_name`, `email` and `is_internal`; keep it that way and resolve afterwards.
- **Team sender rules stay valid.** `internal_addresses()` unions them with the roster. Don't delete them in the migration.
- **Respect archived clients:** `live_contacts()` already skips inactive businesses. Resolution may still label a contact of an archived client as `client`, which is fine because history is kept.
