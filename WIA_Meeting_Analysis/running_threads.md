# Running Threads: across all E2M × WIA meetings

Updated after each meeting's analysis. Newest changes on top within each section.
Last updated: after Meeting 05 (2026-09-22, knowledge base scoping).

**Current build (M04–M05 + `WIA-Automation-Timeline/`, kickoff Sep 15):**
| Stream | Build | Plan window (timeline app) | Status |
|--------|-------|----------------------------|--------|
| A. Marketing & Content Engine | 5–6 wks | Sep 15 → Oct 22 | **In execution since Sep 21** |
| B. Paid Media Reporting | 4 wks | Oct 19 → Nov 13 | Requirements not gathered. Whitney calls it "the third phase" (M05) |
| C. Maintained Client Knowledge Base | 5–6 wks | Nov 11 → Dec 15 | "Queued for November". **Backend starting early** (M05). Scoped in M05 |

- The windows assume **every step hits its minimum**. If every step takes its maximum, the chain ends **Jan 12, 2027**.
- **The order of B and C is unresolved.** Asha opened M05 with "which to pick up next"; it was never answered.

## Open commitments
| Owner | Commitment | Raised in | Due | Status |
|-------|------------|-----------|-----|--------|
| **E2M + WIA** | **Written scope, end date and revocation for the `hello@` access** (remove the +91 2FA phone, rotate the password, sign out sessions, review grants) | M05 (recommended) | Now | **Not raised on the call** |
| E2M (Minu / Nandini) | Test `hello@` access after the 2FA delay | M05 | Sep 23 | Open |
| E2M (Jainil) | **Gather Viktor samples:** pull the 9 channel-side items with the Content Atelier app, **once WIA okays inviting it to the private client channels** (it's in the test channel only today); ask WIA for the DMs and admin screens (a recorded screen-share is fastest) | Internal (Sep 24) | Before the KB Phase 1 spec | Open. `viktor_samples.md` |
| E2M | Confirm the permission levels that came through (GHL Agency Admin especially), as promised in the Sep 4–7 reply | Sep 3 request | ASAP | Open. `access_wia.md` #5 |
| WIA | Outstanding from the Sep 3 request: the completed Dubsado onboarding questionnaire; the monthly-report **walkthrough video**; Fathom **exports** (not share links) | Sep 3 request | — | Open. `access_wia.md` requests log |
| WIA (Gisselle) | `hello@` password via LastPass | M05 | Sep 22–23 | Presumed done |
| E2M | **Check Zoom Admin for retained client-call transcripts**; correct `Content_Atelier.md` §8; limit speech-to-text to the gaps | M05 | ASAP | Open |
| E2M | Review Zoom settings → recommend on a Fathom team account | M05 | After access | Open |
| E2M | Knowledge base recommendations "once sources are locked"; phased functional requirements (Phase 1: call prep + top opportunities) | M05 | Before build | Open |
| WIA (Gisselle / Danielle) | LeadLock kickoff recordings: widen access or use a team Fathom | M05 | TBD | Open |
| E2M | **Show content-engine output** (promised M04 as "what we have done so far") | M04 | ~Sep 22 | **Partly.** Timeline shown, no output |
| WIA | Content inputs: GHL token, Instagram access, Slack bot, Fathom, ChatGPT export | M04 | Before build | **GHL token ✔ (Sep 21–22); Slack: all client channels ✔ (Sep 21).** Still open: **Instagram and Canva** (requested through access guides shared with WIA, **waiting on WIA**), the bot in the content channels, Fathom API. GHL API confirmed in place (Sep 24) |
| E2M | **Repos are on `github.com/jainil-e2m`, not the `AI@` GitHub** (M03 promised "tied to the AI@ email"). Confirm who created the `AI@` Railway/GitHub accounts WIA reset on Sep 21, and whether the reset broke any deploy link | M03 / Sep 21 | Before handover | Open. `access_wia.md` #11, #17 |
| WIA (Whitney) | Offer/CTA map with live links | M04 | Before drafting goes live | Open |
| E2M (Asha) | New-card payment link / charge | M04 | Sep 17 | Unknown |
| E2M (Asha) | **Dedicated SOW** (plus in/out scope, running cost, accuracy, handover, **access scope**) | M03 | Before execution | **Still not mentioned (M04, M05)** |
| E2M | Handover docs, technical docs, Looms at pause/end; maintenance plans | M03 | Pause / end | Open |
| E2M | Role-based logins if needed | M03 | Build | Open. The knowledge base will have team users (M05) |
| E2M | Running cost estimate + spend cap (OpenRouter, Railway) | M00 → M04 | Post-build | **Partly.** The requirements doc gives unit costs (OpenRouter pay-per-execution, $20 first top-up; Railway $5/mo). No monthly estimate or cap |
| E2M | Audit deliverables: accuracy ✗, API/running cost ✗ | M00 | — | Carry into the SOW |
| E2M | Try options inside tools WIA already uses before going custom | M00 | Build | Open |
| — | Mobile homepage CTA → 404; Aug 25 Claude recording; Command Center credentials; GHL Communities check | M01–M03 | — | Unknown / low priority |

*Closed / lapsed:*
- M05: progress link ✔ (timeline app); delivery team named ✔
- M04:
  - Tue/Thu slot ✔ (M05 on a Tuesday)
  - updated API/access list ✔ (Sep 21 handover)
  - OpenRouter ✔
- M03:
  - WIA pick ✔ (three priorities)
  - timeline ✔
  - card consent ✔
  - blueprint link ✔
- M02: feasibility request ✔ (Jainil, Sep 3); `AI@` ✔; access invites ✔ (Sep 4); office-hour transcripts ✔ (2 Fathom links, Sep 4); blueprint ✔; ClickUp review ✔; Asha's sync ✔
- M01: fulfilment ideas ✔ (M03); Slack group superseded; onboarding walkthrough **partly**
- M00: audit link ✔; decision ✔; $499 credit ✔

## Decisions log
| Decision | Meeting | Notes |
|----------|---------|-------|
| Delivery team: **Nandini Vithlani** (lead AI executor), **Jainil** (associate) | M05 | Direct Slack contact with WIA |
| **E2M gets `hello@` credentials plus an E2M +91 phone as secondary 2FA** | M05 | Done live. **Reverses M02's scoped `AI@` design.** No written scope or end date |
| **Knowledge base rule: meeting statements beat ClickUp dates; answers cite sources** | M05 | Settles half of FF-01's gate. Approved document vs later call is still open |
| Knowledge base built in phases, in parallel: **Phase 1 = call prep + top opportunities**; then sentiment, health, to-dos | M05 | Needs a written Phase 1 cut |
| Knowledge base users = Whitney + team; no client exclusions | M05 | Role-based logins needed |
| Find source calls through the calendar (scan the calendar → fetch transcripts) | M05 | Whitney's idea, adopted |
| Knowledge base backend starts before its November slot, justified by the "Q1 2027 scale-up" | M05 | **Premise unconfirmed on the record** |
| Fathom team account: deferred until the Zoom review | M05 | |
| Three priorities: Content Engine → (Reporting / KB, order unresolved) | M04 | All Phase 2–3 in the blueprint |
| Content engine Phase 1 scope (Whitney chooses; 1 email + 3 reels + 1 carousel + captions; engine asks for the CTA; text only) | M04 | |
| Email = weekly repurposing, not a sales channel | M04 | |
| Model = OpenRouter; hosting = Railway, both on `AI@` | M04 | WIA pays |
| Weekly sync moves to Tuesdays | M04 → M05 | ✔ |
| Pick → feasibility → milestone chart → **SOW** → execution | M03 | SOW skipped in practice |
| WIA owns the build (repo + Railway on `AI@`) | M03 | "Ultimately I want it to be something that we own" (M05). **Today the repos are on `jainil-e2m`. An `AI@` GitHub exists (Sep 21), so transfer before handover** |
| ClickUp stays the system of record ~1 quarter | M03 | Whitney would drop it (M03); Viktor's ClickUp digest was noise (M05) |
| Pricing: $499 credited → $9,000 upfront or $3,000 + $3,499 + $3,499 | M03 | |
| Access via `AI@`, credentials via LastPass → Minu | M02 | **Extended to `hello@` in M05** |
| Ad-account access collection stays manual | M02 | |
| Human review before any client send | M00–M05 | |
| Client relationship contact stays human | M00 | |
| Phase 2 (marketing, sales, bookkeeping) needs its own audit | M00 (Daniela) | Marketing scoped without her (M04) |

## Open questions
| Question | First raised | Still open as of |
|----------|--------------|------------------|
| **Are client-call transcripts retained in Zoom Admin?** If so, speech-to-text is only for gaps (Fathom office hours, LeadLock kickoffs, older calls) | M05 (Gisselle, 7:07) | **Open. Verify now.** `Content_Atelier.md` still says video-only |
| **Which stream is next: KB or reporting?** When do the shared ad connectors (MCC, Meta, GHL, Shopify) land? | M05 | Open |
| **Primary surface for the knowledge base:** dashboard (Whitney), ChatGPT (Minu), Slack (the team today)? | M05 | Open |
| **Viktor:** coexist or retire? How does E2M's build beat it (organised, owned, follows through, concise, knows the call type)? | M00 → M05 | Open. **Not positioned by E2M.** Most of WIA's complaints can be fixed inside Viktor, so ownership is the real differentiator. Also ask for its plan/spend and output samples (`viktor_at_wia.md`) |
| **Q1 2027 scale-up:** a real plan? | M03 | M05: attributed to Whitney by Minu; never stated by her on the record |
| **`hello@` access:** scope, holder of the number, end date, revocation | M05 | Open |
| Knowledge base Phase 1 spec: call-prep format (short), call-type templates, what counts as a "top" opportunity | M05 | Open |
| FF-01: approved document vs later call, which wins? | Internal | M05: meeting > ClickUp settled; this part open |
| Fathom team account; Meta office hours and LeadLock kickoff capture | M02 → M05 | Open (after the Zoom review) |
| How does Whitney flag a moment? Where does the engine ask? Where do drafts live? Approval before handoff? | M04 | Open |
| Client consent to quote and name clients | M04 | Open. Also relevant to "transformation" stories built from KB history (M05) |
| Offer/CTA map; case study and Stories in the pack | M04 | Open. **Evidence for case studies:** two of the five Sep 21 chains (Miss Lyss, Carroll Hall) end in a case study |
| Running cost + spend cap | M00 → M04 | Open |
| Timeline realism (fits 3 months only at minimums) | M04 | Open |
| Reporting discovery (Tina's hours, number of clients, contents) | M02 | Open. M05: "with every new client… more and more hours" |
| Gisselle's load under the content engine | M04 | Open |
| Daniela's involvement (absent M01–M05) | M01 | Open |
| Upfront or monthly payment? | M04 | Open |
| Template residue ("Explore Media") in the shared blueprint | M03 | Open |

*Answered:*
- **What counts as "acknowledged" (M03)?** The practical definition from Viktor's "open loops" (M05) is an ask in Slack that got a response
- **Knowledge base date conflicts (internal)**: the meeting wins over ClickUp; cite the source (M05)
- **Brand voice document (M01)**: exists (M04)
- **Picks and 3-month scope (M03)**: M04
- **Hosting (M00)**: Railway (M03)
- **$3,499 (M00)**: the Apollo monthly instalment (M03)
- **"How is it all connected?" (M01)**: M03
- **Daniela's fulfilment question (M00)**: M02
- **Notetaker (M01)**: M02; retention detail in M05

## Scope traceability (need → meeting → blueprint item → picked?)
| Need | Raised | Blueprint item (phase) | Picked |
|------|--------|------------------------|--------|
| Content from calls; "more leads, more sales"; transformation stories from full client history | M00, **M01**, M03, M04, M05 | MC-01…04 (P2) | **Yes: stream A (in execution)** |
| Client intelligence: call prep, performance, sentiment, opportunities, weekly focus, health, team Q&A, dashboard | M00 ("agency brain"), M02, **M05** | FF-01 (P3) + PM-01/02 overlap | **Yes: stream C (scoped M05)** |
| Reporting → exec summary; weekly RAG snapshot (Viktor does it today) | M00, M02, M03, M05 | PM-01/02 (P1), PM-03 (P2) | **Yes: stream B** (requirements not gathered) |
| Follow-through: chasing, open loops, overdue, missed onboarding deadlines | M00, M01, M02, **M05** | OP-01/02 (P1–2), MK-01 | Not a stream. **Re-entering through KB features** |
| Overdue invoices / invalid emails | M02 | OP-03 | Not a stream (partly KB FF-01d) |
| Onboarding admin / trigger | M01, M02, M05 (strain) | ON-01…05 | No |
| Inbox triage; roll call; portal posts; briefs / landing-page QA | M01, M02 | CC-*, MP-*, FF-02/03 | No |

## Corrected assumptions
| Was believed | Actually | Corrected in |
|--------------|----------|--------------|
| (M00–M05 notes) "Victor" | **Viktor** ([viktor.com](https://viktor.com/)), a commercial Slack "AI employee" by ZETA AI, Inc. (launched Feb 2026), not a custom bot. viktor.ai is a different company. The full use inventory is in `viktor_at_wia.md` | User, Sep 24 |
| (M00 Khushbu) Viktor "works great at a personal level", but not across a team | It's built and sold as **one shared agent for the whole workspace**. WIA uses it that way (Whitney, Carmen, Gisselle; added to every client channel during onboarding) | `viktor_at_wia.md` |
| (M03) The repo is "tied to the AI@ email" | The repos are on `github.com/jainil-e2m` (git remotes, Sep 24). An `AI@` GitHub account exists (WIA reset its password Sep 21) | `access_wia.md` #17 |
| (M05 analysis) The `hello@` access had no written basis | The requirements doc asked in writing for `hello@` **ChatGPT** access (chat history). M05 widened it to the calendar and, through 2FA, the whole account | Requirements doc |
| (`Content_Atelier.md`) Funktastic is the only chain with a surviving source transcript | The Sep 21 handover lists a **Carroll Hall transcript** next to its outputs. Funktastic's own source isn't in that list | Sep 21 handover |
| (Sep 21 notes) Speech-to-text is a blocker nobody has solved | E2M already transcribed 2 workshop recordings locally on Sep 9 (`transcripts/`) | Local files |
| (M02 analysis) The feasibility/access list "slipped a week" | **Jainil sent it Sep 3**, the day after M02. Invites and samples followed Sep 4 and Sep 8 | Slack thread (`access_wia.md`) |
| (Sep 21 notes) One Fathom share link | **Two**: Google Ads and Meta Ads office hours (Sep 4) | Slack thread |
| (M05) Drive access = client folders | **WIA's whole Shared Drive** (Sep 4). The `wia+<client>` sub-folders are shared with clients, so never write internal material there | Slack thread |
| (Sep 21 notes / M04 hindsight) Client calls reach E2M only as video; speech-to-text is the blocker | **Only recordings are deleted from Zoom; transcripts and summaries are retained** (Admin view through the new role). Client Drive folders hold "call recordings and transcripts" | **M05 (Gisselle, 7:07). Verify** |
| (M02) E2M works only through the scoped `AI@` identity | E2M also holds `hello@` + a 2FA phone | M05 |
| (M00) The team is at "square one" with AI | Carmen uses Viktor daily; Gisselle configured its digests; Whitney runs daily call prep through it | M05 |
| (M00 Khushbu) "Why would you want to pay for Viktor?" | Viktor is embedded (call prep, open loops, RAG snapshots, SOPs), and it's the incumbent the KB must beat | M05 |
| (memory + Sep 15 xlsx) Picked = Reporting / Ops / KB | Content Engine → Reporting / KB. Ops isn't a stream | M04 |
| (M04) Fathom is a simple connection | Individual free accounts; one share link, no API | Sep 21 / M05 |
| (M01) Unknown whether a voice doc exists | Founder-voice + consultant strategy docs exist | M04 |
| (M00) Custom work "on your AWS" | Railway on `AI@` | M03 |
| (M00) Apollo = one full-time-equivalent engineer | Two developers, two in parallel; named team = Nandini + Jainil | M03, M05 |
| (M03 demo) Onboarding "creates tasks in ClickUp"; roll call knows "who was present" | Stops at approval; sees only who spoke | Internal |
| (M02 log) Onboarding walkthrough done | Narrated only; template pulled through the API | M03 |
| (M00) Every touchpoint fully personalised | Templated framework, personalised copy | M02 |
| (M00) ClickUp is how the team works | Checklist only; Slack is where work happens | M02 |
| (M01) Dubsado is just a "tool" | Contracts + first invoices; the signed/paid trigger; FFA on GHL | M02 |
| (M00) Scope = Gisselle's admin | Reporting and content turned out to be the priorities | M02, M04 |
| (M00) Processes documented step-by-step | Mostly no SOPs | M01 |
| "LeadLog" / "lead block" | **LeadLock** | Public research |
| "Danielle" vs "Daniela" | Danielle = LeadLock contractor (support@leadlockpro.com); Daniela = co-owner | M02, M04, M05 |
