# MVP 1 — Client Onboarding

**Handoff document.** Everything built, every file, every measured fact, and what is still open.
Written to be read cold by a session with no prior context.

- **Engagement:** E2M Solutions × Wedding Industry Ads, LLC (dba LeadLock / LeadLock Pro)
- **Blueprint Review:** Thursday 10 September 2026
- **Repo:** `C:\Users\Jainil Trivedi\Desktop\Wedding_Industry_Ads` (not a git repo)
- **App:** `frontend/` — `wahha-automation-hub`, Vite 6 + React 18 + Tailwind + framer-motion,
  with an Express BFF in `frontend/server/`
- **Status:** working vertical slice on localhost, running on their real ClickUp data
- **Prior context:** [`Conversation summary.md`](Conversation%20summary.md) — Session 1 (scoping
  and brand re-theme) and Session 2 (the build, turn by turn)

---

## 1. What this is, and the one boundary that matters

Watches for the two Dubsado alerts that mean a client has signed → correlates them to one
client → surfaces it on the Command Center → a human activates it and walks **four steps**,
editing and approving each: the ClickUp workspace, the Google Drive client folder, the welcome
email, and the Slack channel with its two posts.

> ### EVERY STEP TERMINATES AT APPROVAL.
> **No write is issued to ClickUp, Drive, Gmail or Slack anywhere in this feature.** There is no
> client library for any of the four systems in this codebase. Each approval records what a
> human authorised and stops; the fourth raises a persistent toast.
>
> `APPROVED` is still the terminal *record* state, and step 1 still owns it — see §5.1 for why
> steps 2-4 are a separate progression rather than four more states.

Every ClickUp call in the codebase is a hard-coded `GET`. Verify with:

```bash
cd frontend && grep -rniE "method:\s*[\"'](POST|PUT|PATCH|DELETE)" server/clickup-*.mjs server/onboarding-*.mjs
```

That should return nothing.

### Where it is in the product

Card 1 of the five-MVP portfolio in `automation_scope.md`. **It is not a standalone MVP** — it
is the *signature branch* of **MVP 1 — The Handoff**, which has two triggers: a call ending
(transcript → recap/action items) and a signature (this). Only the signature branch is built.

---

## 2. File map

### Runtime — the feature

| File | Lines | What it does |
|---|---|---|
| [`server/onboarding-alert-parser.mjs`](frontend/server/onboarding-alert-parser.mjs) | 296 | One Dubsado email → typed half-signal, or `null`. No I/O. |
| [`server/onboarding-store.mjs`](frontend/server/onboarding-store.mjs) | 809 | Correlator + state machine + durability. The heart of it. |
| [`server/onboarding-plan.mjs`](frontend/server/onboarding-plan.mjs) | 282 | Offer set → editable task draft. Role→person, Phase→date. |
| [`server/onboarding-stages.mjs`](frontend/server/onboarding-stages.mjs) | 640 | **Steps 2-4.** Drive / email / Slack plans, built from their real task descriptions. |
| [`server/onboarding-templates.json`](frontend/server/onboarding-templates.json) | 3214 | **Generated.** Their real templates. Never hand-edit. |
| [`src/services/api/onboarding.ts`](frontend/src/services/api/onboarding.ts) | 238 | Typed client for `/api/onboarding/*`. |
| [`src/pages/OnboardingPage.tsx`](frontend/src/pages/OnboardingPage.tsx) | 1125 | The console at `/onboarding`. |

### Tests

| File | Lines | Tests |
|---|---|---|
| [`server/onboarding-alert-parser.test.mjs`](frontend/server/onboarding-alert-parser.test.mjs) | 428 | 49 |
| [`server/onboarding-store.test.mjs`](frontend/server/onboarding-store.test.mjs) | 861 | 63 |
| | | **112 total** |

### ClickUp integration — READ ONLY

| File | Lines | What it does |
|---|---|---|
| [`server/clickup-templates-fetch.mjs`](frontend/server/clickup-templates-fetch.mjs) | 180 | Reads the six template lists + all tasks → `clickup-templates.json` |
| [`server/clickup-fields-fetch.mjs`](frontend/server/clickup-fields-fetch.mjs) | 101 | Reads custom-field **definitions** so dropdown indexes resolve to labels → `clickup-fields.json` |
| [`server/clickup-client-fetch.mjs`](frontend/server/clickup-client-fetch.mjs) | 166 | Reads a live client's folder by name → `clickup-client.json` |
| [`server/onboarding-templates-generate.mjs`](frontend/server/onboarding-templates-generate.mjs) | 232 | **Codegen.** Snapshots → `onboarding-templates.json` |

Each of the three fetchers hard-codes `method: "GET"` in a single `request()` helper and has no
other call path. That is deliberate: `CLICKUP_TOKEN` is a **personal** `pk_` token carrying the
full permissions of the account that minted it — ClickUp has no read-only personal token — so
read-only has to be a property of the *code*, not the credential. **Do not add a write path to
these files.** A provisioning writer, if ever built, belongs in its own module behind its own
approval gate.

### Snapshots — `.clickup-snapshot/` at the repo root (NOT inside `frontend/`)

| File | Size | Contents |
|---|---|---|
| `clickup-templates.json` | 264 KB | 6 template lists, 308 tasks, 9 spaces |
| `clickup-fields.json` | 20 KB | Custom-field definitions with dropdown option labels |
| `clickup-client.json` | 88 KB | Ridgefield Weddings and Events' three live lists, 183 tasks |
| `clickup-descriptions.json` | 60 KB | **Task description TEXT, checklists and hyperlink targets** — 103 tasks. The three files above carry `descriptionLength` only; this one carries the actual content, and it is what made steps 2-4 buildable. |

### Modified elsewhere

| File | Change |
|---|---|
| `server/index.mjs` | 3 imports, 9 `/api/onboarding/*` routes, `AUTH_DISABLED` bypass + `demoUserFor` |
| `src/main.tsx` | Lazy `OnboardingPage`, route `/onboarding` behind `RequireAuth` |
| `src/data/tools.ts` | Card 1 → `route: "/onboarding"`, `ctaLabel: "Open Console"`, icon `ClipboardCheck` |
| `src/components/RequireAuth.tsx` | Env-gated dev bypass |
| `src/pages/LoginPage.tsx` | Light-theme fix (was white-on-white), Wahha → WIA |
| `src/components/Hero.tsx` | `RotatingDestination` — the 3-destination switcher pill |
| `.env.local` | ClickUp token + team/space IDs, auth bypass flags |
| `vite.config.ts` | Dev proxy target reads `API_PORT` (default 8787) so two sessions can each run their own vite+BFF pair. 8787 is a single global slot: a second BFF silently fails to bind, and your server changes are then simply not loaded. |

---

## 3. Running it

```bash
cd frontend && npm run dev:api
```
```bash
cd frontend && npm run dev
```

Then **http://localhost:5173/onboarding**.

The BFF must be on **:8787** — `vite.config.ts` proxies `/api` there, and `.env.local` pins
`PORT=8787`. If `npm run dev:api` exits with `EADDRINUSE`, an older BFF is still holding the
port and **your code changes will not be loaded** — this cost a debugging round already. Kill it
by PID:

```bash
netstat -ano | grep ":8787" | grep LISTENING
```

To reset the board to a clean seed gate: stop the BFF, `rm frontend/.data/onboarding.json`,
restart. Deleting the file while the BFF runs does nothing — state is in memory and gets
re-persisted.

### Re-reading ClickUp after they edit a template

```bash
cd frontend && node --env-file-if-exists=.env --env-file-if-exists=.env.local server/clickup-templates-fetch.mjs
```
```bash
cd frontend && node --env-file-if-exists=.env --env-file-if-exists=.env.local server/clickup-fields-fetch.mjs
```
```bash
cd frontend && node server/onboarding-templates-generate.mjs
```

To inspect a different live client: `node ... server/clickup-client-fetch.mjs "Client Name"`.

---

## 4. The trigger

Whitney's gate is a **conjunction**, stated twice on 2 Sept:

> @23:38 — "we get alerts in the Gmail inbox when they have signed the contract **and** have paid the invoice"
> @24:09 — "the trigger is that, like, we see in the inbox that they have signed the contract and paid the invoice"

Two subject grammars, verified against two real alerts Whitney forwarded on 5 Sept:

```
paid    {FirstName} has paid {Amount} {Currency} - {ProjectName}
signed  {FirstName} has signed your contract for {ProjectName}
```

Both are **subject-line-only** as signals; the bodies carry a greeting and a link.

### Things the parser gets right that are easy to get wrong

- **Identity is the PROJECT, never the person.** "Alina / Dogwood Reserve", "Brittanie / The
  Elia" — the person is the signatory, the project is the venue, and the payer and signer can
  differ. Correlating on first name would strand both halves forever.
- **Forwarded envelopes.** Gmail scope on `hello@` was never granted, so every sample is a
  forward sitting in an engineer's mailbox. The real sender and date are recovered from the
  body; the outer envelope belongs to Whitney. `source: "forwarded" | "direct"` is stamped on
  every record and rendered on the review card.
- **`originalDateIso`.** Gmail writes `"Thu, Aug 27, 2026 at 11:02 AM"` — that ` at ` makes it
  `Invalid Date`. Un-normalised, every signature-anchored date silently computed to `null`.
- **Sender matching is not enough.** Every Dubsado notification shares `noreply@dubsado.com` —
  form submissions, proposal views, receipts, reminders. The subject is the real filter.
- **The name class excludes a colon.** Without it, `"Receipt: Alina has paid 1997.00 USD -
  Dogwood Reserve"` parses as a payment for a client named "Receipt: Alina".

### The evidence gap

**No matched pair was ever provided.** Dogwood Reserve has only a *paid* alert; The Elia only a
*signed* one — two halves of two different clients. Every pair in the demo is constructed and
labelled as such in the UI.

---

## 5. The store — three corrections to the obvious design

1. **"Already onboarded" cannot be binary.** Three outcomes: already provisioned → ignore;
   half-pair pending → attach and re-check; never seen → open a pending record.
2. **The recurring-payment trap.** Elevate is a monthly retainer, so month 2's payment fires a
   subject *identical in shape* to month 1's. Nothing in the alert distinguishes them — only
   this store's own record does. `fingerprintAlert` deliberately includes the alert's original
   date and amount so month 2 does not look like a duplicate and get silently swallowed.
3. **Seed before the first poll.** `ingest` refuses until `seed()` runs. A first pass against an
   empty store would read 90 days of Dubsado history as a queue of new signings. A corrupt file
   starts empty → unseeded → refuses, rather than re-onboarding the whole client book.

**Source of truth is our own store, not ClickUp.** A ClickUp name lookup belongs on the card as
a *soft warning*, never as the dedupe key — fuzzy name matching must not be load-bearing on the
one decision that cannot be wrong.

### States

`PRE_EXISTING → AWAITING_PAIR → READY → DRAFTED → APPROVED` plus `IGNORED` (with a reason).

### 5.1 Why steps 2-4 are not four more states

Step 1's `approve()` is what sets `provisioned`, and `provisioned` is the single flag that makes
month 2 of a retainer inert (§5.2 above). Folding three more approvals into the same state
machine would put that flag behind three more gates and re-open the recurring-payment trap.

So `approve()` keeps its exact meaning — *a human authorised this onboarding* — and steps 2-4
hang off the record as a separate `stages[]` progression, each entry `OPEN → APPROVED` with its
own frozen `approvedPlan`. A record therefore reaches `APPROVED` with three steps still open,
which is accurate: approving the ClickUp batch **is** the commitment, and the Drive folder and
the Slack posts follow it.

`initStages` is idempotent, because the approve route calls it on every approval and an approval
can be retried — a second call finds stages already there and leaves a reviewer's edits alone.

### TWO ANCHORS, NOT ONE — the correction that matters most

Step 1 collects **one** kickoff date, and its phase cadence (+0/+7/+14/+21/+28) was recovered
from Ridgefield's **LeadLock** list. So that single field is the LeadLock kickoff. Their ads
track has its own:

| | Ridgefield's live task | Due |
|---|---|---|
| LeadLock kickoff | `Complete Onboarding Call` | **2026-03-25** |
| Ads kickoff | `Complete Ads Kickoff Call` | **2026-04-28** |

**34 days apart** — and their own welcome email asks for the *opposite* order: *"Ideally, this
call [LeadLock] should be scheduled for a later date than the Ads Kickoff Call."* Their project-
timeline post agrees, putting the LeadLock kickoff in week 2. The one live client inverted the
written intent by a month.

Consequences:

- **Step 4 asks for both dates and derives neither.** An earlier pass derived the LeadLock date
  as ads +7 from their timeline's week-2 mention; against Ridgefield that is wrong in magnitude
  *and* direction. The gate now clears progressively — both missing → "waiting on the LeadLock
  kickoff and the ads kickoff", one in → "waiting on the ads kickoff".
- **Step 1 still applies its single anchor to both lists**, so a both-offers client necessarily
  mis-dates one track. Not fixed here: the cadence reproduces Ridgefield exactly, and changing
  it would break the one property the demo leans on. It is question 1 for Gisselle.

### The step-4 gate

Their own team brief opens *"She has scheduled her Ads Kickoff Call for (DATE) and their LeadLock
Kickoff call for (DATE)"*, and the timeline post's six week ranges are computed off the same
anchor. **So the Slack announcement cannot be a signature-wave action at all** — it presupposes
a booking that does not exist yet. That is a correction to the call: Whitney narrated Slack as a
day-0 step (Sept 2) and her own templates disagree.

`approveStage` refuses any plan still carrying a `gate`, server-side, so a reviewer cannot
authorise posting two messages full of `(DATE)`. `recordKickoff` is the way through it — the
same arithmetic as `applyKickoffDate` but legal on an `APPROVED` record, after which the route
re-renders the two posts via `rehydrateSlackStage`, preserving any body a reviewer edited.

> **One bug worth remembering.** `approve()` assigns the *same object* to both `draft` and
> `approvedBatch`, so `recordKickoff` walking `[draft, approvedBatch]` counted every date twice
> — and the `/2` that "fixed" it then halved the count on records where they genuinely are two
> objects. It dedupes by identity now (`new Set`), and a test pins `computed` to the actual
> dated-task count.

### Store API

`read` · `status` · `seed` · `ingest` · `activate` · `updateDraft` · `applyKickoffDate` ·
`approve` · `initStages` · `updateStage` · `approveStage` · `recordKickoff` · `ignore` ·
`expireStalePairs` · `flush` · `reset`

All three mutators (`activate`, `updateDraft`, `approve`) take **options objects**. They did not,
and the inconsistency silently broke a call site.

Durability matches `leads-store.mjs`: in-memory, mirrored to disk with atomic temp-file+rename
serialized through one promise chain. `ONBOARDING_FILE` points it at a volume.

### Routes — all behind `requireSession`

| Method | Path |
|---|---|
| GET | `/api/onboarding` |
| POST | `/api/onboarding/seed` |
| POST | `/api/onboarding/ingest` |
| POST | `/api/onboarding/:projectKey/activate` |
| POST | `/api/onboarding/:projectKey/kickoff` |
| PUT | `/api/onboarding/:projectKey/draft` |
| POST | `/api/onboarding/:projectKey/approve` |
| POST | `/api/onboarding/:projectKey/ignore` |
| POST | `/api/onboarding/expire` |
| PUT | `/api/onboarding/:projectKey/stage/:stage` |
| POST | `/api/onboarding/:projectKey/stage/:stage/approve` |
| POST | `/api/onboarding/:projectKey/stage-kickoff` |

The seven write routes also share `onboardingJson` (`express.json({limit:"256kb"})`) and map
`OnboardingError` through `sendOnboardingError`. The GET takes neither — no body, no failure path.

---

## 6. What reading their ClickUp actually established

This section is the highest-value part of the document. All of it was **measured**, not inferred
from the call transcripts, and several items **contradict** `automation_scope.md`.

### The six template lists — `Templates` space (`90110419120`) → folder `Onboarding Templates`

| List | ID | Tasks | Assignees | **Due dates** |
|---|---|---|---|---|
| Client Management | `901101886878` | 4 | 0% | **0** |
| Google + Meta Onboarding *(v1, stale)* | `901113178693` | 72 | 33% | **0** |
| **Google + Meta Onboarding (version 2)** | `901114303479` | 89 | 62% | **0** |
| **LeadLock Onboarding** | `901112080381` | 102 | 95% | **0** |
| Google Ads VIP Day | `901112430846` | 23 | 0% | **0** |
| Ads Traffic Landing Page | `901113739811` | 18 | 78% | **0** |

> **0 of 308 tasks carries a due date.** The templates contain no relative offsets whatsoever.
> Sidebar counts (24, 34…) are *top-level only*; the numbers above include subtasks.

**`Client Management` is not an onboarding template** — it is the recurring maintenance block
(Monthly Reporting, Daily Ad Check, Weekly Check-in, Bi-weekly Lead Funnel Monitoring).

**v2 supersedes v1.** 23 of 24 top-level tasks shared; v1 uniquely has "Send Referral Fee (If
Applicable)", v2 uniquely adds "Create custom GPT for the client" — the step Whitney described
as newly added on 2 Sept. Provisioning reads **v2**.

### Two custom fields the transcripts never mentioned

**`Role`** — set on **299 of 308** tasks, against only **190** with a real assignee. It is the
better source of ownership, and closing that 109-task gap is this automation's actual contribution.

| Role | Tasks | Resolves to |
|---|---|---|
| Assistant | 98 | Gisselle (her ClickUp account is **"WIA Support"**) |
| **Ads Manager** | 86 | **75 unassigned** — Carmen (Google) *or* Jacqueline (Meta) |
| GHL Specialist | 66 | Danielle McGinnis — 66/66, unambiguous |
| LeadLock Designer | 26 | Tina Henares |
| CEO | 11 | Whitney Hodges |
| **Client** | 8 | **nobody — their own marker for client-gated work** |
| Marketing Assistant | 3 | Ivy Ayala |

Jacqueline is not missing from the templates: **Ads Manager work is role-tagged but
person-unassigned on 75 of 86 tasks.**

**`Phase`** — a per-template dropdown encoding the sequencing:

- `Phase (LeadLock)` — Project Initiation → Onboarding → Tech Setup → Design/Copy work → Final Implementation → Launch. Populated on **96 of 102**.
- `Phase (Full Service)` — Project Initiation → Onboarding → Google Ads Setup → Meta Ads Setup. Populated on only **25 of 89** in the ads template.
- `Phase (Google Ads VIP Day)` — Project Initiation → VIP Day Call 1 → VIP Day Call 2 → Post-VIP Day.

**The two templates are at very different maturity.** LeadLock is 95% assigned and 94% phased;
the ads template is 62% assigned and 28% phased. The automation earns its place on the ads side.

### The destination — measured from a live client

```
ELEVATE Clients                        · space, chosen by offer
  └── Ridgefield Weddings and Events   · folder, one per client
        ├── LeadLock Onboarding        · list from template
        ├── Google + Meta Onboarding   · list from template
        └── Client Management          · recurring, NOT onboarding
```

**Two lists side by side, not one merged list.** This resolves Whitney's ambiguous "we're going
off both of those onboarding templates" (@19:59). Consequence: the eight task names appearing in
both templates need **no de-duplication** — they land in different lists.

Spaces are organised **by offer**:

| Space | ID |
|---|---|
| Templates | `90110419120` |
| ELEVATE Clients | `90110423738` |
| Foolproof Follow-Up Advantage | `90113946116` |
| Google Search Accelerator | `90113970636` |
| Meta Ads Accelerator | `90113807797` |
| VIP Days | `90113826595` |
| ARCHIVES - Full Service | `90113970808` |
| COMPLETED - VIP Days | `90113974164` |
| WIA Internal | `90113826619` |

### The date rule, recovered by diffing

Templates carry 0 due dates. **Ridgefield's live LeadLock list carries 29.** Diffing them
recovers the rule Gisselle applies by hand — a weekly cadence anchored on the **kickoff call**:

| Phase | Offset | Ridgefield's actual |
|---|---|---|
| Onboarding | +0 | 2026-03-25 ✓ |
| Project Initiation | +7 | 2026-04-01 ✓ |
| Tech Setup | +14 | 2026-04-08 ✓ |
| Design/Copy work | +21 | 2026-04-15 ✓ |
| Final Implementation | +21 | 2026-04-15 ✓ |
| Launch | +28 | 2026-04-22 ✓ |

> **Caveat that must travel with this number: n = 1.** It reproduces Ridgefield exactly, but it
> is one client. It is a proposal to put in front of Gisselle, not an established rule. The ads
> list does **not** follow it cleanly — offsets run +0,+2,+3,+6,+7,+14,+17,+21,+24,+28,+30,+35
> then a tail at **+69, +71, +73**. That tail is Whitney's "chasing" problem, visible as data.

### Why there are two waves

The kickoff is booked **by the client**, via the link in the welcome email (@27:38). So at
signature the anchor does not exist and **no phase-driven date is computable**.

- **Wave 1, at signature** — create the lists, resolve owners from `Role`, mark every
  phase-driven task as awaiting the anchor.
- **Wave 2, on booking** — one date entered → **111 due dates compute themselves.**

Wave 2 is the valuable part, and it is exactly the "return visit days later" that makes this
"2 hours, depending" rather than one sitting — the shape of work a person forgets.

### The referral-fee gap — worth raising with them

The **only** written referral-fee procedure in the workspace is a 337-character description on
"Send Referral Fee (If Applicable)", which lives in the **stale v1** template. **v2 deleted it.**
LeadLock's "Check if referral fee is needed" has an *empty* description. The codegen ports the
three v1-only tasks into the generated ads template so it is not lost:

- Send Referral Fee (If Applicable)
- Share Google Drive Folder (add client email address)
- Review Sales Call

---

## 7. Corrections to `automation_scope.md`

Things this work established that the scope document gets wrong. **Fix these before Thursday.**

1. **`automation_scope.md:346` — "the alert survives the migration" is wrong in detail.** The
   *surface* survives; the *alert* is a Dubsado artifact and dies with Dubsado. Whitney says
   Foolproof Follow-Up Advantage **has already moved to GHL** (@24:09: "we've done that for just
   one offer"; @23:29: "majority of our contracts are in Dubsado", not all). FFA is precisely the
   `{LeadLock}`-only case, so that branch may already be unreachable from the Dubsado subject
   patterns. They are on the **top-tier GHL agency SaaS plan** (@13:21), so the post-migration
   signal can be a webhook rather than an email parse. **Unverified and load-bearing.**

2. **The MVP renumbering collision, still unfixed.** Part 5 renumbered; Part 1.3, Part 6.1, the
   status rows and Appendix A did not. Confirmed live in the file: §1.3 reads `MVP2 · Page Check`
   and `MVP3 · Nobody starts from a blank page`, while Part 5 has MVP 2 as the office-hours engine
   and MVP 3 *as* Page Check. Literal contradictions at `:1136`, `:192`, `:1816`.

3. **MVP 2's Effort section sums to 5.25 days** by double-counting the spine. Part 7 has it right
   at exactly 4.00.

4. **`automation_scope.md:91` frames the questionnaire as a missing sample.** The sharper problem
   is sequencing: it is *sent* in the welcome email, so it is unanswered at signature — yet it is
   the payload of the Drive upload, the Slack announcement and the ChatGPT Project seed. Those
   three cannot fire in the signature wave.

5. **Client Onboarding is not a standalone MVP** — it is the signature branch of MVP 1.

---

## 8. Other findings from the transcripts

- **Dubsado mail is deprioritised in Gmail.** Gisselle calls the "tools" label contents "usually
  not priority" (Aug 26 @29:56–30:15), and existing automations tag mail automatically. The
  signal that starts every onboarding arrives pre-sorted into the bucket she reads last. A
  latency explanation, and possibly a usable pre-filter. *(Inference: that transactional alerts
  inherit the same label as the newsletters. Testable in one look.)*
- **Nobody had seen the ClickUp template before this work.** Whitney offered the walkthrough
  @19:59 and it never happened; Minu confirms @40:36. Across the entire 21-minute onboarding
  segment **Gisselle's only contribution was spelling "Dubsado"** — the flow was narrated by the
  person who does not perform it.
- **~17 client-gated steps**, not the ~11 previously counted. Whitney's "chasing the team"
  diagnosis is largely a misattribution: the team is blocked on the *client*.
- **A third unused Dubsado event exists** — proposal acceptance. It fires before the pair and is
  the moment the offer is definitively known.
- **Transcript diarization is unreliable.** Labels drift by a turn in both directions (@39:36
  "Minu" says "I am not tied to the labeling system at all"; @12:24 "Whitney" asks "we usually
  have an AI notetaker present?"). Attribute by content, never by label.

---

## 9. UI

`/onboarding`, lazy-loaded behind `RequireAuth`. Board → activate → **four steps, each
editable then approved** → persistent toast on the fourth.

### The four steps, and why in this order

A stepper sits above every panel (`1 ClickUp · 2 Drive · 3 Welcome email · 4 Slack`) so a
reviewer knows before approving step 1 that it is not the end. Ordered by **dependency**, not by
the order Whitney listed them:

| Step | Why here | Approve gate |
|---|---|---|
| **1 · ClickUp** | 194 tasks across 2 lists — the commitment | 194 tasks |
| **2 · Drive** | Nothing depends on it, everything else does — step 3 attaches a file from it, step 4 bookmarks it | 11 rows |
| **3 · Welcome email** | Needs the contract from step 2, and it *causes* the booking step 4 waits on | 5 rows |
| **4 · Slack** | **Gated** on the kickoff booking (see §5) | 16 rows incl. 2 posts |

It also runs least-to-most consequential — a Drive folder is nearly harmless, an `@channel` post
is socially irreversible, an email to the client more so — so the gate earns its place as you
advance.

**The best beat in the demo** is step 4's gate: it sits locked, one click on Ridgefield's real
kickoff (`2026-03-25`) unlocks it, and 111 due dates plus six week ranges plus two full messages
populate at once. One input, two steps light up.

### What steps 2-4 reuse from step 1

Deliberately the same five-part shape — structure preview → blocker → editable rows →
will-create count → approve — plus the same vocabularies: the three states (`ready` / `pending` /
`gated`) and the confidence chip. A reviewer who has done step 1 already knows how to do 2, 3
and 4. New to these steps is a **provenance badge** per row (`from the alert` · `from the sales
call` · `their template` · `computed` · `from an earlier step` · `you write this` · `awaiting the
client`), because a row that is not a task needs to say where its value came from.

### The content is theirs, verbatim

Everything on steps 2-4 was read off their own ClickUp task descriptions:

- **Drive** — the two-folder structure from `Create Google Drive Client Folder` (409 chars): an
  internal folder named for the company, and a `WIA + <Company>` subfolder set to *Anyone with
  the link · Viewer* which is the only client-facing surface. Note step 1 must **not** dedupe the
  contract and sales-recording tasks (two lists, two tasks) while step 2 **must** (one file each);
  Drive is the one place the two-list model collapses.
- **Slack** — both posts are the real templates: the team brief (`Share details with team in
  Slack`, 1313 chars, byte-identical in v1 and v2) and the timeline (`Share project timeline`,
  1538 chars ads / 648 LeadLock), with only their parenthesised placeholders substituted.
  `Things to note` is left **blank on purpose** — in their template it is a hand-written
  observation about a client mid-transition from another agency, so a blank box with a cursor is
  the honest rendering and the human-in-the-loop point made concretely.
- **Email** — **their real per-offer welcome templates**, supplied 2026-09-09 and no longer a
  gap. `WELCOME_BY_OFFER` maps offer → template: ELEVATE (two booking links), Foolproof
  Follow-Up Advantage (one link, questionnaire bundled into the booking flow), and the
  accelerator/VIP variants, which carry **no booking link at all** — they propose a date in
  prose and name the expert, so those offers have no client-booked anchor to wait on. Only the
  client's first name is substituted; their own `(INSERT ONBOARDING QUESTIONNAIRE)` marker is
  left in place and counted as unresolved rather than filled.

  Three things the templates settled that the transcripts could not: the ELEVATE email carries
  **two** booking links (an earlier pass concluded from Whitney's call description that it
  carried one); the intended call order is **ads first**; and FFA's questionnaire cannot go
  unanswered while the call proceeds, because it is part of booking. They also surfaced a
  **second questionnaire** — the *Messaging & Positioning Questionnaire*, a Google Doc sent
  after the kickoff and reviewed together on the M&P call, which appears in real sent mail and
  in **no** ClickUp template.

> **A pronoun decision.** Their team brief hardcodes *"She has scheduled her…"*. The alert gives
> us a first name and nothing else, so guessing would misgender a real client on a message going
> to the whole team. These render neutrally and a warning tells them the template wants a pronoun
> field.

### The closing screen

`CompletionPanel` — four summary cards, the collected "waiting on someone outside this room"
rail, and an amber panel that **refuses to claim the client is onboarded**: there is no
machine-readable onboarded event in their workspace, Ridgefield entered monthly maintenance six
days after Google Ads launched with all three Meta setups still open, and the only reliable proxy
is the `Client Management` list appearing in the folder — a step nobody currently owns.

### Step 1's panels

- **Awaiting-pair group** — the only part that delivers value before a ClickUp task is ever
  written. "Which signed clients haven't paid yet?" currently has no answer outside Whitney's head.
- **Destination panel** — renders the space → folder → lists tree.
- **Kickoff panel (wave 2)** — enter a date, or one click for Ridgefield's real `2026-03-25`.
- **Task table** — grouped by destination list, showing `Role (theirs)` beside
  `Assignee (derived)` with a confidence chip: `certain` / `likely` / `heuristic` / `ambiguous`.
- **Three due states** — `dated` / `pending` / `gated`. A `Role = Client` task **never** gets a
  date: it would go overdue through no fault of the assignee, and on a team that only ticks boxes
  in ClickUp (@42:16) false-overdue is how the tool stops being trusted.
- **Will-write / will-not-write** split above the approve button; excluded rows survive into
  `approvedBatch` so the record answers what a human *authorised*, not what the planner proposed.

### Demo numbers — Ridgefield as Elevate

194 tasks across 2 lists. Wave 1: **0 dated / 189 pending / 5 gated**. After wave 2:
**111 dated / 78 pending / 5 gated**, with **28 flagged to confirm** (the Ads Manager split).

---

## 10. Current environment state — READ THIS

### Auth is disabled

`frontend/.env.local` has `VITE_AUTH_DISABLED=1` and `AUTH_DISABLED=1`. Both are needed — the
React route guard and the API gate are separate boundaries. **`AUTH_DISABLED` also makes
`/api/auth/login` accept any email and any password**, minting a real session and deriving a
display name (`whitney.hodges@…` → "Whitney Hodges").

**Delete those two lines to restore real auth.** Verified: with the flag off, wrong passwords
401, protected routes 401, and no bypass warning appears in the boot log. If it is ever set
alongside `NODE_ENV=production` the server prints a large banner at boot.

### The ClickUp token must be revoked

`frontend/.env.local` contains `CLICKUP_TOKEN=pk_87472224_…`, supplied as **temporary** and
**pasted into a chat transcript**. It is a personal token with full account permissions.

> **Action: revoke it in ClickUp and delete the line.** Nothing in the running app reads it — only
> the three fetch scripts do, and only when re-reading templates. The generated
> `onboarding-templates.json` and the `.clickup-snapshot/` files are all committed data; the
> feature runs fine with no token at all.

Also in `.env.local`: `CLICKUP_TEAM_ID=9011165651`, `CLICKUP_TEMPLATES_SPACE_ID=90110419120`.

### Test baseline

**699 of 701 pass.** The 2 failures are **pre-existing and unrelated** — `server/favicon-resolver.test.mjs`
(SSRF boundary, PWA icon picking), documented in Session 1 and untouched by any of this work.
Lint: 2 pre-existing warnings in `AuditPanel.tsx`, 0 errors. Type-check clean.

---

## 11. Open questions, in priority order

0. **THE PHASE INVERSION — one line of config, ~26 of the 111 dated rows in the wrong order.**
   `PHASE_WEEK` maps `Onboarding` → +0 and `Project Initiation` → +7, so the entire *signature*
   wave is dated a week **after** the entire *kickoff* wave. The clearest instance: `Send
   Onboarding Email with call links` lands at +7 while `Complete Ads Kickoff Call` lands at +0 —
   the email carrying the booking link is dated a week after the call it books. Also
   `Countersign Contract` +7, `Google Drive Client Folder` +7, `Create Slack Channel` +7 and
   `Create LeadLock Subaccount` +7 against `Connect Google account to LeadLock Subaccount` +0;
   and on the LeadLock side `Add LeadLock Kickoff Call Worksheet` +7 (prep dated after the call
   it prepares).

   **It is not a bug in the derivation.** The cadence reproduces Ridgefield exactly, and
   Ridgefield's lists were bulk-created the day of / the day before their own kickoff — so
   *their* dates are inverted, and ours faithfully copy them. Do not "fix" it silently; it is
   the first thing to put to Gisselle, because the answer also settles whether a signature wave
   exists at all.

0b. **Which call anchors which list** (see §5). Two anchors, 34 days apart on the one live
   client, in the opposite order to their own written intent.

1. **The `Ads Manager` split rule.** 28 tasks need a real rule from them; the current
   Google-vs-Meta split is a keyword heuristic, flagged per row in the UI.
2. **Confirm the phase→week cadence with Gisselle.** It reproduces Ridgefield exactly but n=1.
   Also worth asking why `Phase` is fully populated on LeadLock and mostly empty on the ads template.
3. **Which of the two `Google + Meta Onboarding` lists is live?** Evidence says v2; get it stated.
4. **The referral-fee procedure v2 dropped** (§6).
5. **The FFA/GHL migration hole in the trigger** (§7.1) — the single biggest correctness risk.
6. **Gmail scope on `hello@weddingindustryads.com`.** Never requested. Converts the trigger from a
   paste into the real thing and unblocks TASK-04's triage half.
7. **A matched pair and one raw, non-forwarded alert.** The parser was built against forwards and
   a transcription, never real envelope headers.
8. **Onboarding volume per month.** The one place an hours claim would be defensible — `2 hrs × N`
   — and N has never been given.
9. **Confirm "WIA Support" is Gisselle's account** (84 tasks assigned to it).
10. **Why 75 of 86 Ads Manager tasks are unassigned** in the templates.

## 12. Natural next steps

- Map the two accelerator offers to their real templates (`Google Ads VIP Day`,
  `Ads Traffic Landing Page`) — currently declared but unmapped, so they contribute no tasks and
  the UI says so.
- Decide whether `Client Management` should be provisioned alongside onboarding (Ridgefield has
  it) or treated as a separate monthly-maintenance step.
- If a real write path is ever wanted: new module, own approval gate, and the ClickUp seat must
  be **Member not Guest** — Guests cannot read templates at all.

---

## 13. Known rough edges

- **`/history` is broken the same way `/login` was** — hardcoded white-alpha text on the now-white
  ground, renders almost blank. `ToolPage.tsx` (10 occurrences) and `LeadMagnetDashboardPage.tsx`
  (30) are very likely the same. Not fixed: Session 1 notes those routes may be removed. Note that
  `AutomationsModal.tsx`'s `text-white` is *correct* — it sits on dark card gradients.
- **Hero counters read 0.** They read `resolveTimelineView().tally` — the Wahha *build timeline*,
  not the tool catalogue. `src/data/timeline.ts` was last modified 31 Aug, before any of this work.
  Arguably content that should not be on a WIA dashboard at all.
- **`package.json` is still named `wahha-automation-hub`** — ties into the repo URL and Docker
  config, so it was left alone deliberately.
- **The persistent toast's dismiss could not be verified visually.** The React state goes to
  `null` correctly (read off the fiber), but the Browser pane stays `visibilityState: "hidden"`,
  so `requestAnimationFrame` never fires and framer's exit animation cannot complete. A hidden-tab
  artifact, not app behaviour — but worth one eyeball.
