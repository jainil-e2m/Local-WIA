# Can Be Built

A running backlog of ideas that came up during the build journey and were **deliberately kept out of scope**.

This is not a wish list. Every entry here was considered against a specific automation, judged sound, and deferred for a stated reason. Each one records what it depends on and the moment it becomes cheap to build — so when that moment arrives, nobody has to reconstruct the thinking.

Grouped by the automation it relates to. Add new entries under the relevant automation; create a new heading if the automation isn't listed yet.

**Entry format**

- **Idea** — one line, what it is
- **Relates to** — the automation ID it hangs off
- **Why deferred** — the actual reason, not "no time"
- **Depends on** — what has to exist first
- **Becomes cheap when** — the trigger to revisit
- **Raised** — date and context

---

## FF-01 · Maintained Client Knowledge Base

### Ad performance as an intake source for the engagement record

- **Idea** — Read Google Ads and Meta Ads monthly performance (spend, leads, CPL, conversions) into the per-client engagement record as timeline events, alongside emails, meetings, commitments and invoices.
- **Relates to** — FF-01 (Maintained Client Knowledge Base) · consumes PM-01 / PM-02 / PM-03 infrastructure
- **Why deferred** — FF-01's scope is being held to the operational engagement record: onboarding → today, assembled from the seven already-connected sources (Gmail, Slack, ClickUp, Zoom, Fathom, Drive, HighLevel). Ad performance is a different data class with its own access chain, its own metric definitions and its own review gate, and folding it in now widens FF-01 before its core shape is settled.
- **Depends on** — `A-00` (Google Ads MCP + Meta Ads MCP servers deployed and connected, W2) · PM-01 and PM-02 metric definitions agreed · FF-01's event model and persisted store in place
- **Becomes cheap when** — PM-01/PM-02 are live and the FF-01 event store exists. At that point the connector is already built and already authorised; the work is a reader that emits performance events into the record, not a new integration.
- **Why it is worth revisiting** — An engagement record that carries every email, meeting and invoice but not what happened in the ad account is missing the actual work product. It is also the only thing that lets the record answer the question that matters at renewal: *did this engagement work?* The two streams are being built in the same engagement and never connected, which is the specific kind of gap that is cheap now and expensive in a year.
- **Raised** — 2026-09-16, during FF-01 scope definition

---

## Content Atelier · Later scope

### Maintained client history → transformation stories and case studies

- **Idea** — Feed Content Atelier with a client's full history from the maintained client knowledge base, so it can draft transformation stories and case studies using the starting situation, work delivered, and evidenced outcomes across the engagement.
- **Relates to** — Content Atelier / Marketing & Content Engine, especially MC-04 (Case-Study Extraction); consumes FF-01's maintained client record.
- **Why deferred** — User clarification on 2026-10-09: keep this integration in Content Atelier's scope to be built later. It is not a current knowledge-base delivery requirement or a current Content Atelier build requirement.
- **Depends on** — A maintained client record with source citations and a defined handoff to Content Atelier.
- **Becomes cheap when** — The maintained client knowledge base exists and this later Content Atelier integration is selected for implementation.
- **Raised** — Whitney described the idea in the 2026-09-22 knowledge-base scoping call; the user assigned it to later Content Atelier scope on 2026-10-09.

---

## Notes on using this file

- An entry graduating out of here should be **deleted**, not ticked — it lives in the scope document once it is real.
- If an idea is rejected outright rather than deferred, say so and keep it. A recorded "no, because…" stops the same idea being re-proposed every quarter.
