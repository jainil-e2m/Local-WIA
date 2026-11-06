# Wedding Industry Ads — AI Blueprint v0

**Component map and build record.** E2M Solutions is the author; Wedding Industry Ads is
the audit subject. The E2M visual theme is unchanged — palette, fonts, hero image and logo
are untouched.

---

## 1. What was built

| | |
|---|---|
| Departments | 7 |
| Initiatives | 23 |
| Matrix entries | 23 |
| Phases | 2 |
| Governance categories | 4 |
| Human-review gates | 8 |
| Activation: assets / APIs / owner actions | 15 / 12 / 15 |
| Portal modules | 0 |

### Headline stats

| Tile | Value | Detail |
|---|---|---|
| Manual hours verified (one role) | **~18 hrs/month** |  |
| Estimated full load (one role) | **45–70 hrs/month** |  |
| Share of assistant's ~108-hr month | **40–65%** |  |
| Blueprint automation count | **23** | Across 7 departments: 14 from the audited task rows, 6 from the Aug 26 call, 1 in build, 2 paid media reporting. |

### Phases

**Phase 1 — Stop the Leaks**  
- Build on Gmail, ClickUp, Slack, and GHL as they stand
- Low build effort, human review on every send
- Targets ~12 of the ~18 verified hrs/month

`ON-01  CC-02  CC-01  MP-01  MK-01  MP-02  ON-02  CC-03  MK-02  OP-01  OP-03  ON-03  PM-01  PM-02`

**Phase 2 — Free the Founder**  
- Returns Whitney's sales and marketing time
- Drafts prepared in advance, reviewed before sending
- Content generated from call recordings already captured

`MC-01  MC-02  CC-05  OP-02  MP-03  CC-04  MK-03  MC-03  MC-04`

### Initiatives

| ID | Initiative | Dept | Pri | Ph | Time saved |
|---|---|---|---|---|---|
| `CC-01` | Inbox Triage & Auto-Filing | client-comms | High | 1 | — |
| `CC-02` | Draft Emails in Whitney's Voice | client-comms | High | 1 | — |
| `CC-03` | Waiting-Tag Follow-Up Detector | client-comms | Medium | 1 | — |
| `CC-04` | Post-Meeting Template Recap Emails | client-comms | Medium | 2 | — |
| `CC-05` | Post-Sales-Call Proactive Drafts | client-comms | Medium | 2 | — |
| `MC-01` | Transcript -> Content Idea Queue | marketing | High | 2 | — |
| `MC-02` | Reel Script Gen w/ Voice-Note Steering | marketing | High | 2 | — |
| `MC-03` | Multi-Format Repurposing | marketing | Medium | 2 | — |
| `MC-04` | Case-Study Extraction | marketing | Medium | 2 | — |
| `MK-01` | Meeting Recap -> Action Items -> ClickUp | meetings | Medium | 1 | Up to 4 hrs/month (R6: 1 hr × 4 Mondays) |
| `MK-02` | Zoom Asset Auto-Archival | meetings | Medium | 1 | 15 min per client meeting |
| `MK-03` | Client-Facing Recap Drafting | meetings | Medium | 2 | — |
| `MP-01` | Roll Call & Absence Flagging | member-portal | High | 1 | 2 hrs/month (R13: 10 min × 12) |
| `MP-02` | Session Reminder Posts | member-portal | Medium | 1 | 3 hrs/month (R11: 15 min × 12) |
| `MP-03` | Session Recap Post + Canva Banner | member-portal | Medium | 2 | 6 hrs/month (R12: ~0.5 hr × 12) |
| `ON-01` | Dubsado Contact Signing & Invoice Paid Monitoring | onboarding | Complete | 0 | — |
| `ON-02` | Welcome Email + Checklist Assignment | onboarding | Medium | 1 | 2 hrs per client onboarding (R8) |
| `ON-03` | Client Asset Intake -> Drive Filing | onboarding | Low | 1 | 15 min per meeting (R14) |
| `OP-01` | Overdue Task Digest -> Slack | operations | Low | 1 | 2 hrs/month (R5: 0.5 hr × 4 Mondays) |
| `OP-02` | Action-Item Chase & Ack Tracking | operations | High | 2 | — |
| `OP-03` | Billing & Data-Hygiene Flags | operations | Medium | 1 | ~1.1 hrs/month (R15: 3 min × ~22 workdays) |
| `PM-01` | Google Ads Reporting | paid-media | Medium | 1 | — |
| `PM-02` | Meta Ads Reporting | paid-media | Medium | 1 | — |

### Departments

| Department | Team | Manual | Recoverable |
|---|---|---|---|
| **Operations & Task Orchestration** | Gisselle Jimenez (executive assistant), Whitney Hodges (owne | ~3.1 hrs/month (R5+R15) | Up to ~3.1 hrs/month |
| **Member Portal & Community** | Gisselle Jimenez (EA), Carmen (Google Ads office hours), Jac | 11 hrs/month (R11+R12+R13) | Up to 11 hrs/month |
| **Meetings & Knowledge Capture** | Gisselle Jimenez, Whitney Hodges | 4 hrs/month (R6) | Up to 4 hrs/month |
| **Client Onboarding** | Gisselle Jimenez, Whitney Hodges, Multiple owners across onb | Not separately quantified | Not separately quantified |
| **Marketing & Content Engine** | Whitney Hodges, Gisselle Jimenez | Not separately quantified | Not separately quantified |
| **Client Communications** | Whitney Hodges (Owner/Founder), Gisselle Jimenez (EA) | Not separately quantified | Not separately quantified |
| **Paid Media Reporting** | Gisselle Jimenez, Whitney Hodges | Not separately quantified | Not separately quantified |

---

## 2. Component map

Every rendered component in the sample, what it showed for E2M, what it now shows for WIA,
and the risk of filling it naively. Produced by four agents reading the audit sheet and the
26 August transcript, then adversarially verified.

### Strategic roadmap and the impact-vs-effort matrix

#### Strategic Roadmap section header + subhead (above the three phase cards)

- **Sample showed** — Unknown exact string. Inferable from SCHEMA.md: the E2M sample's phases are named by effort tier (phase 1 is literally "Quick Wins"), so the header frames the roadmap as a generic effort-sequenced rollout across E2M's own 28 blueprint automations.
- **WIA content** — Header: "Strategic Roadmap". Subhead: "Twenty-two initiatives across three phases, plus one build already underway. Sequenced from the Aug 26 task audit and the Aug 26 discovery call. The audit covers operations and admin work performed by one person; fulfillment work was not audited and is not represented here."
- **Why** — SOURCES section 6 fixes 22 initiatives and 3 phases. Section 2 header: the 12 audited rows are "All Gisselle, all department Operations / Admin / Internal". Section 5: fulfillment (creative briefs, ad copy, landing pages, Carmen's and Jacqueline's work) was NEVER AUDITED and Aug 26 deferred it by design (@22:05-22:38). Section 4: ON-01 is already in build and demos at this review.
- **Risk if filled naively** — Leaving E2M's effort-tier framing loses the actual thesis — section 1 says Whitney is buying turnover-proofing, not speed. Filling naively without the scope sentence makes a roadmap built from one contractor's admin tasks read as an agency-wide plan, which invites Whitney to assume ad delivery was assessed. Section 5 forbids representing that as anything but an explicit gap.

#### Phase 1 card — name and strategy bullets

- **Sample showed** — name: "Quick Wins"; strategy: ["Build on existing tools and data", "Low build effort", "Immediate time recovery"] (verbatim from the SCHEMA.md Phase object example).
- **WIA content** — name: "Stop the Leaks". strategy: ["Build on Gmail, ClickUp, Slack and GHL as they stand", "Low build effort; no process revamp required", "Recovers the audit rows that carry verified monthly totals", "Flag only on roll call and billing; a human does the follow-up"]
- **Why** — SOURCES section 6 renames phase 1 "Stop the Leaks" with the gloss "build on Gmail/GHL/ClickUp as they stand; immediate recovery". Bullet 4 encodes the hard constraints from R13 ("Just needs to flag, we will manually follow up") and R15 ("Just flag to Gisselle/Whitney"), both phase 1 (MP-01, OP-03). Bullet 3 is true of this phase: R5 (2 hrs), R6 (4), R11 (3), R13 (2), R15 (~1.1) all sit in phase 1.
- **Risk if filled naively** — Keeping "Quick Wins" flattens the phase into a speed claim when its real job is stopping known leakage. Dropping bullet 4 is the dangerous one: MP-01 and OP-03 are flag-only per verbatim sheet text, and a card promising automated follow-up contradicts section 4's non-negotiable that client relationship contact stays human.

#### Phase 1 card — featured initiative code list

- **Sample showed** — featuredInitiatives: ["SEO-01", "BS-01", "BS-02"] — three E2M service-line codes.
- **WIA content** — featuredInitiatives: ["CC-01", "CC-02", "MP-01", "MK-01"] — Inbox Triage & Auto-Filing; AI Draft Replies in Whitney's Voice; Roll Call & Absence Flagging; Meeting Recap to ClickUp Tasks. Phase 1 contains eleven initiatives in total (CC-01, CC-02, CC-03, ON-02, ON-03, MK-01, MK-02, OP-01, OP-03, MP-01, MP-02); the card features four and the rest live in the department sections.
- **Why** — SOURCES section 6 phase column. CC-01/CC-02 come from R4, the only HIGH-priority row that also runs "Everyday" and is confirmed as the focus item at @23:45. MP-01 comes from R13, HIGH priority, and is the task Gisselle tried to automate and failed at (@5:25-7:30, "wasn't able to figure out how we could best automate this"). MK-01 is R6, one of the six rows with a verified total (4 hrs/mo).
- **Risk if filled naively** — E2M's codes reference services WIA does not buy. Featuring by score alone would surface ON-01 (9/4) here, but ON-01 is phase 0 and already in build. Featuring all eleven turns the card into a list nobody reads and buries the two items that answer @19:21 ("I don't even know what we should be starting with").

#### Phase 2 card — name and strategy bullets

- **Sample showed** — Unknown exact strings. By the sample's pattern, an effort/impact tier name such as "Major Projects" or "Strategic Builds" with three generic bullets about higher build effort and cross-system integration.
- **WIA content** — name: "Free the Founder". strategy: ["Draft client recaps and proposals before Whitney asks", "Track acknowledgements so nobody chases the team", "Turn call recordings into marketing input", "Return Whitney's attention to sales and marketing"]
- **Why** — SOURCES section 6 renames phase 2 "Free the Founder — reclaim Whitney's attention so she can sell". Bullet 1 maps CC-04, CC-05 and MK-03 (@33:39 "proactively have an email drafted for that"; @17:30-18:30 the recap chain). Bullet 2 maps OP-02 and @16:54 "It always feels like we're chasing the team to get done the things that need to get done." Bullet 3 maps MC-01/MC-02 (@19:40-21:00). Bullet 4 is @21:20 "we need more leads. We need more sales ... if we're not marketing actively, that's not going to happen", plus section 1 (Fallon's resignation pushed Whitney back into client work and blocked her sales time).
- **Risk if filled naively** — A generic "bigger builds" name hides that this phase is the one Whitney is actually paying for. Naively writing "sends client recaps automatically" breaks the section 7 hard constraint (human review gate before anything client-facing, @14:15/@18:30/@39:09) and directly contradicts Minu's stated constraint at @14:15 that no AI-generated content goes to clients directly.

#### Phase 2 card — featured initiative code list

- **Sample showed** — Unknown; three E2M service codes following the phase 1 pattern.
- **WIA content** — featuredInitiatives: ["OP-02", "MC-01", "MC-02"] — Action-Item Chase & Ack Tracking; Transcript to Content Idea Queue; Reel Script Gen with Voice-Note Steering. Phase 2 also contains CC-04, CC-05, MK-03 and MP-03.
- **Why** — SOURCES section 6 phase column. OP-02 is R10, HIGH priority, "Every day", and matches @16:54. MC-01 and MC-02 come from @19:40-21:00, which Whitney herself calls a huge area of opportunity, including the voice-note steering ask verbatim at @20:40.
- **Risk if filled naively** — Featuring CC-05 or MK-03 instead would put two more client-facing drafting items on the card and make phase 2 look like an outbound-automation phase, which the @14:15 and @39:09 constraints do not support. Omitting MC-01/MC-02 drops the only initiatives sourced from Whitney's own stated priority rather than from Gisselle's task sheet.

#### Phase 3 card — name and strategy bullets

- **Sample showed** — Unknown exact strings. By pattern, a horizon/tier name (e.g. "Transformational" or "Revisit Later") with generic bullets about long-term platform work.
- **WIA content** — name: "The Agency Brain". strategy: ["Hold process knowledge in the system, not in individual contractors", "Connect the inbox, Slack and Google Drive into one surface", "Repurpose one call recording into every content format", "Survive the next account-manager resignation"]
- **Why** — SOURCES section 6 names phase 3 "The Agency Brain — institutional memory; survives the next resignation". Bullet 1 and 4 are section 1 verbatim in substance: the next account-manager hire "is just a person who is kind of like running it. We have the agency brain", triggered by Fallon's resignation. Bullet 2 is @19:00 ("whatever is scanning the inbox needs to also be seeing what's happening in Slack ... inside of our Google Drive") and @19:21 ("is there one place that we're going, and then there are just different tabs?"). Bullet 3 maps MC-03/MC-04 (@21:00).
- **Risk if filled naively** — This is the phase that carries the actual purchase motive; a generic "long-term" label wastes it. The naive failure is writing bullet 4 as a headcount claim — nothing in SOURCES supports reducing staff, and section 4 is explicit that the human touch on client experience stays human, with Daniela on record that clients hire WIA for hand-holding.

#### Phase 3 card — featured initiative code list

- **Sample showed** — Unknown; three E2M service codes.
- **WIA content** — featuredInitiatives: ["PLATFORM-01", "MC-03", "MC-04"] — The Agency Brain; Multi-Format Repurposing; Case-Study Extraction. These are the only three phase 3 initiatives, so the card is complete rather than a selection.
- **Why** — SOURCES section 6: only MC-03 (7/7), MC-04 (7/8) and PLATFORM-01 (10/9) carry phase 3. PLATFORM-01 is sourced to section 1 plus @19:21, the central question of the engagement.
- **Risk if filled naively** — If an engineer pads this list to match the other cards' length by borrowing phase 2 codes, the same initiative renders twice on the roadmap and the phase counts stop reconciling with the 22 matrix dots.

#### Delivered / in-build item (ON-01) placement on the roadmap

- **Sample showed** — Unknown. The SCHEMA.md Phase object only defines phases 1-3, and the initiative schema carries a `status` field described as "OPTIONAL, only for phase 0 / Complete items" — so the sample has some phase 0 treatment, but its rendered form on the roadmap is not visible from the schema.
- **WIA content** — Render ON-01 as a separate delivered strip above Phase 1, labelled "In build — demonstrated at this review", priority "Complete", phase 0. status text: "Observes Dubsado signed and paid alerts, correlates the pair, notifies a Command Center dashboard; a human activates and edits the execution draft (rename tasks, change assignees and dates, remove rows) before batch approval. No ClickUp writes in this build; approved is terminal." Do not place ON-01 on any of the three phase cards and do not include it in START HERE.
- **Why** — SOURCES section 4: the Client Onboarding MVP is ALREADY IN BUILD by E2M and demoing at this Blueprint Review, and "This must appear as a delivered/in-build item, not a proposal." Section 6 assigns it priority Complete, phase 0, impact 9 effort 4. The trigger is Dubsado because section 4 records that only Foolproof Follow-Up Advantage has moved to GHL and "majority of our contracts are in Dubsado" (Sept 2 @23:29, @24:09).
- **Risk if filled naively** — With only three phase cards, a phase 0 item silently disappears from the roadmap while still plotting as a 9/4 dot in QUICK WINS — so the one thing E2M has actually built reads as an unstarted suggestion. The inverse error is worse: listing it as a phase 1 proposal misrepresents delivered work to the client watching it demoed minutes later. A third naive error is writing the trigger as GHL; the migration is only partial, so a GHL-triggered claim would be false.

#### Automation Priorities section header + intro paragraph (above the scatter)

- **Sample showed** — Unknown exact string. Frames E2M's own 28 prioritized automations (SCHEMA.md headline stats: "Blueprint automation count 28, detail: Prioritized from 42 ...") plotted on impact versus effort.
- **WIA content** — Header: "Automation Priorities". Intro: "Twenty-two initiatives plotted by impact against build effort. Scores are E2M estimates derived from the Aug 26 task audit and the Aug 26 discovery call, not measured values. The plot covers operations and admin work performed by one person; fulfillment work — creative briefs, ad copy, landing page builds and QA, and campaign management — was not audited and does not appear."
- **Why** — SOURCES section 6 supplies all 22 impact/effort pairs and no measurement method, so they must be labelled as estimates. Section 5: fulfillment was never audited and must be represented as an explicit gap, NOT as empty departments and NOT as invented initiatives. Section 2 header: every audited row is Gisselle's.
- **Risk if filled naively** — Left as E2M's copy, the intro cites 28 automations against 22 rendered dots and the numbers visibly disagree. Filled naively without the estimate qualifier, impact 10 / effort 9 on PLATFORM-01 reads as a measurement. Without the fulfillment sentence, the visible density in the low-effort region implies the whole business is nearly automated, when in fact the unaudited half of the business is simply absent from the chart.

#### Scatter matrix axes, scale and quadrant split

- **Sample showed** — X axis build effort, Y axis impact, both on a 1-10 frame with a fixed quadrant threshold. The exact threshold value the sample uses is unknown from SCHEMA.md.
- **WIA content** — Keep the sample's existing 1-10 frame and its existing quadrant threshold unchanged. Axis labels: X "Build effort", Y "Impact". Do not rescale the axes to the WIA data range. WIA's data spans effort 2-9 and impact 5-10, so the lower band of the plot is legitimately empty.
- **Why** — SOURCES section 6 lists every score; the lowest impact in the set is 5 (ON-03, OP-01, OP-03) and the lowest effort is 2 (OP-01, OP-03, MP-02). No source states an axis threshold, so re-deriving one would be an invention.
- **Risk if filled naively** — Rescaling axes to fit the data would stretch the effort-2 items toward the middle of the plot and make the three genuine two-point-effort tasks (R5, R11, R15 — all described in the sheet as small or easy tasks Gisselle simply forgets) look like real builds. Changing the threshold to fill the empty quadrant would silently reclassify initiatives and break agreement with the phase cards.

#### Scatter dot labels (the `ap[].label` short strings on each node)

- **Sample showed** — E2M service-line short names, e.g. "AI Visibility Dashboard" for SEO-01 (SCHEMA.md matrix entry example).
- **WIA content** — CC-01 "Inbox Triage & Auto-Filing"; CC-02 "Draft Replies in Whitney's Voice"; CC-03 "Waiting-Tag Follow-Up Detector"; CC-04 "Post-Meeting Recap Emails"; CC-05 "Post-Sales-Call Drafts"; ON-01 "Signed+Paid Onboarding Draft"; ON-02 "Welcome Email + Checklist"; ON-03 "Client Asset Intake to Drive"; MK-01 "Meeting Recap to ClickUp Tasks"; MK-02 "Zoom Asset Auto-Archival"; MK-03 "Client-Facing Recap Drafting"; OP-01 "Overdue Task Digest"; OP-02 "Action-Item Chase & Ack"; OP-03 "Billing & Data-Hygiene Flags"; MP-01 "Roll Call & Absence Flagging"; MP-02 "Session Reminder Posts"; MP-03 "Session Recap + Canva Banner"; MC-01 "Transcript to Content Queue"; MC-02 "Reel Script from Voice Note"; MC-03 "Multi-Format Repurposing"; MC-04 "Case-Study Extraction"; PLATFORM-01 "The Agency Brain". All are under 34 characters.
- **Why** — Titles are fixed by SOURCES section 6; SCHEMA.md requires `label` to be a distinct short string under ~34 chars, one entry per initiative, or the impact/effort spread resolves to undefined. Tool names inside labels are normalized to the canonical strings ("ClickUp", "Drive", "Canva") per the tool-consistency rule.
- **Risk if filled naively** — A missing `ap` entry silently drops impactScore and effortScore for that initiative and the dot disappears while the initiative still renders in its department, so the two sections stop reconciling. Reusing the full `title` overflows the node and collides in the crowded low-effort region. Writing "Highlevel" or "LeadLock" instead of "GHL" inside a label would also fragment the derived dependency graph, which draws edges from shared tool strings.

#### Quadrant label — QUICK WINS (high impact, low effort)

- **Sample showed** — The label itself is generic and carries no E2M-specific content; it is populated with E2M's own low-effort service automations.
- **WIA content** — Keep the label string "QUICK WINS" unchanged. Twelve of the twenty-two WIA dots land here: CC-01 (7/3), CC-02 (10/5), CC-03 (6/3), CC-04 (7/5), ON-01 (9/4), ON-02 (7/4), MK-01 (8/5), MK-02 (6/3), MP-01 (8/4), MP-02 (6/2), MP-03 (7/5), MC-01 (9/5). Style ON-01 distinctly as already in build.
- **Why** — Computed from the impact/effort pairs in SOURCES section 6. ON-01's status is section 4 (already in build, demoing at this review).
- **Risk if filled naively** — Twelve dots in one corner will collide; without a collision strategy the labels become unreadable exactly where the reader looks first. Substantively, the crowding is an artefact of audit scope — section 5 records that only low-complexity admin work was audited — so presenting it as evidence that the agency is mostly easy to automate is unsupported. And ON-01 sitting undifferentiated among eleven proposals reads as a recommendation for work already underway.

#### Quadrant label — MAJOR PROJECTS (high impact, high effort)

- **Sample showed** — Generic label populated with E2M's larger platform builds.
- **WIA content** — Keep the label string "MAJOR PROJECTS" unchanged. Seven WIA dots land here: CC-05 (8/6), MK-03 (7/6), OP-02 (8/7), MC-02 (8/6), MC-03 (7/7), MC-04 (7/8), PLATFORM-01 (10/9). PLATFORM-01 is the top-right extreme.
- **Why** — Computed from SOURCES section 6. PLATFORM-01 at 10/9 is sourced to section 1 and @19:21, the unanswered central question of the engagement.
- **Risk if filled naively** — If PLATFORM-01 is quietly dropped or rescored to look cheaper, the chart stops answering @19:21 ("how is it all connected? How does it all kind of work together") — the one thing Whitney said she was most looking for. Leaving E2M's items here shows Whitney a build queue for services she is not buying.

#### Quadrant label — FILL-INS (low impact, low effort)

- **Sample showed** — Generic label populated with E2M's minor automations.
- **WIA content** — Keep the label string "FILL-INS" unchanged. Three WIA dots land here: ON-03 (5/3), OP-01 (5/2), OP-03 (5/2). Both OP-01 and OP-03 sit in phase 1 despite low impact.
- **Why** — Computed from SOURCES section 6 (ON-03, OP-01, OP-03 are the only impact-5 entries). Their phase 1 placement is justified by the sheet comments: R15 "Easy task but I tend to forget", and R5 is a verified 2 hrs/month.
- **Risk if filled naively** — An engineer reconciling the matrix against the phase cards may assume FILL-IN items belong in a later phase and move them, breaking agreement between the two components. The other trap is inflating their impact so the roadmap looks coherent — R5, R9/R14 and R15 are genuinely small, and R15 must stay flag-only per its verbatim opportunity text.

#### Quadrant label — REVISIT LATER (low impact, high effort)

- **Sample showed** — Generic label populated with E2M's deprioritized items.
- **WIA content** — Keep the label string "REVISIT LATER" unchanged but render it with an explicit empty-state line: "No audited task scored low impact and high effort." Zero of the twenty-two WIA initiatives land in this quadrant.
- **Why** — Computed from SOURCES section 6: every initiative scoring impact 5 (ON-03, OP-01, OP-03) also scores effort 3 or below, and every initiative scoring effort 6 or above scores impact 7 or above. The quadrant is empty as a matter of arithmetic, not omission.
- **Risk if filled naively** — An unexplained empty quadrant reads as missing data or an incomplete build. The far worse naive fix is relocating a real initiative into it to balance the picture — that would fabricate a priority call SOURCES does not support. Deleting the quadrant entirely also misleads, because it hides that nothing was deprioritized.

#### START HERE quick-wins list (beside the matrix)

- **Sample showed** — Unknown exact entries. By the sample's construction it lists E2M's own highest impact-to-effort initiatives, most likely the phase 1 featured codes (SEO-01, BS-01, BS-02).
- **WIA content** — Ordered list of five, each with code, short label and an honest recovery line: 1. CC-01 Inbox Triage & Auto-Filing — Not separately quantified (R4 monthly total blank; runs every day). 2. MP-01 Roll Call & Absence Flagging — 2 hrs/month verified; flag only. 3. MP-02 Session Reminder Posts — 3 hrs/month verified. 4. OP-03 Billing & Data-Hygiene Flags — approx. 1.1 hrs/month verified; flag only. 5. CC-02 AI Draft Replies in Whitney's Voice — Not separately quantified; approx. 5 drafts per day. Footer line: "Verified monthly recovery from the three quantified items above: approx. 6 hrs/month. The two unquantified items are the highest-priority rows in the audit." Exclude ON-01.
- **Why** — This component is the direct answer to @19:21, "I don't even know what we should be starting with." CC-01/CC-02 are R4, Priority HIGH, freq "Everyday", confirmed as the focus item @23:45; the only volume figure available is Whitney @36:28 "I would say 5 regularly". MP-01 is R13, Priority HIGH, 10 min x 12 = 2 hrs/mo, and is the task Gisselle attempted and abandoned (@5:25-7:30, "it got very very complicated"). MP-02 is R11, 15 min x 12 = 3 hrs/mo, comment "it has happen that I forget to post on time". OP-03 is R15, 3 min x ~22 workdays = approx. 1.1 hrs/mo, comment "Easy task but I tend to forget". The 6 hrs figure is 2 + 3 + 1.1 from those three rows only. Flag-only wording is verbatim from R13 and R15.
- **Risk if filled naively** — Sorting by impact-to-effort alone puts ON-01 (9/4) at the top — recommending as a starting point something E2M is demoing as built (section 4). Leading with CC-02 on its impact 10 is the adoption risk: section 1 records AI literacy near zero and Whitney has never used Claude, and @39:09 sets her bar as output she does not have to heavily edit or rewrite; a voice-matching model as the first deliverable can fail that bar and stall the engagement. Printing a single clean hours total here would breach section 2's explicit instruction not to print a precise total and would imply a team-wide figure when only Gisselle was audited (section 5).

#### Matrix legend / phase colour key

- **Sample showed** — Unknown exact strings. Colour key over the sample's phase set, using its effort-tier phase names (phase 1 "Quick Wins", others unknown).
- **WIA content** — Four keys, not three: 0 "In build" (ON-01 only, visually distinct from proposals), 1 "Stop the Leaks", 2 "Free the Founder", 3 "The Agency Brain". Dot counts by phase are 1 / 11 / 7 / 3.
- **Why** — SOURCES section 6 supplies the three phase names and assigns ON-01 to phase 0 with priority Complete; SCHEMA.md's matrix entry carries a `phase` field, so the legend is data-driven. Section 4 requires ON-01 to read as delivered/in-build rather than proposed.
- **Risk if filled naively** — If the legend carries only phases 1-3, ON-01's phase 0 falls through to an undefined colour or is silently coloured as phase 1, and the single already-built item becomes indistinguishable from eleven proposals sitting in the same quadrant. Reusing E2M's phase names in the legend also puts different phase labels on the legend and the roadmap cards.

**Warnings raised for this group**

- REVISIT LATER renders with zero dots. All three impact-5 initiatives (ON-03, OP-01, OP-03) score effort 3 or below, and every effort-6-or-above initiative scores impact 7 or above. Handle as an explicit empty state; do not move an initiative in to balance the chart.
- The lower band of the plot is empty — no WIA initiative scores impact below 5 and none scores effort below 2. Do not rescale the axes to the data range; effort-2 tasks would then render as mid-effort builds.
- QUICK WINS holds 12 of 22 dots and will suffer label collision. Plan a collision or hover strategy. Also note in copy that the density reflects audit scope (one person's admin work, SOURCES section 5), not agency-wide ease of automation.
- ON-01 is phase 0 / priority Complete and therefore appears on none of the three phase cards while still plotting at 9/4 inside QUICK WINS. It needs an explicit delivered/in-build treatment on the roadmap and a distinct legend key, or the only built item reads as an unstarted suggestion.
- No hours total may appear on any phase card or quadrant. Only 6 of the 12 audit rows carry a monthly figure (R5, R6, R11, R13, R15 plus a derived R15 estimate) and every row belongs to Gisselle. SOURCES section 2 explicitly forbids printing a single precise total, and section 5 forbids implying a team-wide figure.
- The Phase object in SCHEMA.md has no timeframe or date field. If the rendered card shows week or month ranges, that copy is not data-driven — do not invent delivery dates; nothing in SOURCES supports a schedule.
- Impact and effort scores are the estimates listed in SOURCES section 6, not measured values, and the quadrant threshold the E2M sample uses is unknown. Reuse the sample's existing threshold; do not re-derive one, and do not adjust scores to change which quadrant an item falls in.
- Nothing in the roadmap or matrix may reference fulfillment work — creative briefs, ad copy, landing page builds and QA, Google or Meta campaign management, or anything Carmen or Jacqueline do. Aug 26 deferred it by design (@22:05-22:38) and SOURCES section 5 requires it be shown as an explicit gap, never as invented initiatives.
- The audit sheet's rows 2-3 ("Sara", "James") are E2M's own example rows and must not surface in any label, count or list. The initiative count is 22 and the audited-row count is 12.
- Tool strings in every label and card bullet must use the canonical forms: GHL, Gmail, ClickUp, Slack, Zoom, Fathom, Google Drive, Google Sheets, Canva, Claude API, Dubsado. The audit sheet writes "Highlevel" and the call says "LeetLog/LeadLock" — normalize all of these to "GHL", or the derived dependency graph fragments.
- ON-01's trigger must be described as Dubsado, not GHL. The Dubsado to GHL migration is only partly done — Foolproof Follow-Up Advantage moved, but the majority of contracts remain in Dubsado (SOURCES section 4).
- Phase 1 (MP-01, OP-03) contains two flag-only initiatives whose sheet text is unambiguous (R13: "Just needs to flag, we will manually follow up"; R15: "Just flag to Gisselle/Whitney"). Any phase-card bullet implying automated follow-up contradicts them and the @14:15 constraint that no AI-generated content reaches clients directly.

### Hero, Executive Summary, stat tiles, Before/After

#### Hero eyebrow — date + classification tokens

- **Sample showed** — "JUNE 2026" and "CONFIDENTIAL", rendered from document metadata date: "June 2026", classification: "Confidential".
- **WIA content** — Classification stays "CONFIDENTIAL". The date must be the actual delivery date of this Blueprint Review, not June 2026. SOURCES.md fixes no publication date; the latest dated evidence is the Sept 2 call and the onboarding MVP demos at this review, so the date is on or after September 2026. Set a placeholder "SEPTEMBER 2026" and confirm with Minu Bhatt before publishing.
- **Why** — SOURCES section 4: the Client Onboarding MVP is "ALREADY IN BUILD by E2M, demoing at this Blueprint Review"; the most recent dated evidence is the Sept 2 call (@13:21 top-tier GHL plan, @23:29 and @24:09 Dubsado migration). No publication date appears anywhere in SOURCES, so this is a build-time input, not a carried-over fact.
- **Risk if filled naively** — Leaving "JUNE 2026" dates a document that discusses a September build and reads as a recycled template — a serious problem for a buyer whose AI literacy is near zero (section 1) and who is judging whether E2M actually listened. Equally, do not hard-code a precise day; the field is not in evidence and must be confirmed.

#### Hero eyebrow — organization token ("E2M SOLUTIONS")

- **Sample showed** — "E2M SOLUTIONS". In the sample this token is ambiguous by accident: the sample metadata sets client: "E2M" AND preparedBy: "E2M Solutions" because E2M is auditing itself.
- **WIA content** — Keep "E2M SOLUTIONS" but disambiguate it as the author: eyebrow reads "SEPTEMBER 2026 · CONFIDENTIAL · PREPARED BY E2M SOLUTIONS". The audit subject, "Wedding Industry Ads, LLC", belongs in the H1/subtitle, never in this token.
- **Why** — SOURCES section 0: the SUBJECT of the audit is Wedding Industry Ads, LLC (dba LeadLock / LeadLock Pro), Liberty Hill TX; the AUTHOR is E2M Solutions and "E2M branding/theme is UNCHANGED". SCHEMA.md metadata comments mark client as the subject and preparedBy as the author.
- **Risk if filled naively** — Naively swapping this token to "WEDDING INDUSTRY ADS" erases the author and makes the deck look self-produced by the client. Leaving it undifferentiated preserves the sample's accidental reading that E2M is the audit subject — which is literally what the sample is.

#### Hero H1

- **Sample showed** — The blueprint title for E2M itself; metadata title is "AI Blueprint". Exact hero string unknown.
- **WIA content** — "AI Blueprint" with the subject on the line beneath, or a single line "AI Blueprint — Wedding Industry Ads". Use the legal name "Wedding Industry Ads, LLC" at first mention and "WIA" thereafter. Do not title the deck "LeadLock". Keep all numbers out of the H1.
- **Why** — SOURCES section 0: "Wedding Industry Ads, LLC (dba LeadLock / LeadLock Pro)" — LeadLock is the white-labeled GoHighLevel product they sell ($1,697+ setup / $147/mo, section 4), not the agency.
- **Risk if filled naively** — Titling it "LeadLock AI Blueprint" scopes the whole engagement to the product, when all 12 audited rows are agency operations logged under "Operations / Admin / Internal" (section 2). An H1 carrying an hours figure inherits the sample's "370 hrs/month" framing, which SOURCES line 125 explicitly forbids reproducing in any form.

#### Hero subtitle

- **Sample showed** — Tracks metadata.purpose: "Prioritized automation roadmap grounded in E2M's task audit, workflow analysis, and 2026 industry research." Backed by sourceBasis: ["Task audit analysis", "Workflow and tooling review", "Industry research (2026)"].
- **WIA content** — "Prioritized automation roadmap grounded in a 12-row task audit of one executive assistant, the August 26 workflow review, and the client onboarding build already in progress." Remove "industry research" from the subtitle AND from the sourceBasis array; replace the third sourceBasis entry with "Client onboarding MVP build (in progress)".
- **Why** — SOURCES section 2 (12 real rows, all Gisselle); section 3 dates the workflow review to Aug 26; section 4 (ON-01 already in build). No industry research was produced for WIA — section 5 enumerates what is not in evidence and research is not among the permitted sources.
- **Risk if filled naively** — Carrying "2026 industry research" asserts a research basis that does not exist — fabrication, which SOURCES names as "the single worst failure mode for this deliverable". Writing "task audit" without "one executive assistant" implies the agency was audited; section 5 states plainly that no hours exist for anyone except Gisselle.

#### Hero primary CTA

- **Sample showed** — Unknown. In the sample the two hero buttons are in-page anchors, presumably to the roadmap and the impact/effort matrix.
- **WIA content** — "View the 22 initiatives" — anchor to the phased roadmap section (Phase 1 "Stop the Leaks", Phase 2 "Free the Founder", Phase 3 "The Agency Brain").
- **Why** — SOURCES section 6: 22 initiatives across 7 departments, with the 3 phases rethemed from the E2M sample and named exactly as above.
- **Risk if filled naively** — A CTA that promises a return figure ("See your hours saved", "See your ROI") writes a cheque SOURCES cannot cash: the Aug 11 question — how much time back in 3 months, what % can actually be automated — was asked and NEVER ANSWERED (section 1). Putting that promise in the hero and not delivering it in the body is the fastest way to lose this deal.

#### Hero secondary CTA

- **Sample showed** — Unknown; second in-page anchor in the sample hero.
- **WIA content** — "See the onboarding MVP (in build)" — anchor to ON-01. Label it as in build, not as a proposal.
- **Why** — SOURCES section 4: the Client Onboarding MVP is already in build by E2M and "demoing at this Blueprint Review ... This must appear as a delivered/in-build item, not a proposal." Section 6 lists ON-01 at priority "Complete", phase 0.
- **Risk if filled naively** — If both CTAs point at proposals, the only thing already built is buried, and the deck reads as another pitch to a buyer whose stated blocker (@19:21) is "I don't even know what we should be starting with". Conversely, do not label it "delivered" without qualification — the build stops at batch approval with a persistent toast and writes nothing to ClickUp.

#### Document metadata block (client / preparedBy / contact) — drives hero and footer

- **Sample showed** — client: "E2M"; preparedBy: "E2M Solutions"; contact: "Manali Sharma, E2M Solutions"; version: "1.1"; classification: "Confidential".
- **WIA content** — client: "Wedding Industry Ads, LLC". preparedBy: "E2M Solutions" (unchanged). contact: "Minu Bhatt, E2M Solutions". Remove "Manali Sharma" entirely. Reset version to "1.0" unless a prior WIA version actually shipped.
- **Why** — SOURCES section 0 names the E2M side as Minu Bhatt (AI adoption specialist), Jainil (AI engineer), Asha Kumar, Khushbu Doshi. Minu is the person on record speaking for E2M on the Aug 26 call (@14:15 the no-AI-to-clients constraint, @22:05 the efficiency/fulfillment split, @38:17 the process-revamp question). "Manali Sharma" does not appear in SOURCES.
- **Risk if filled naively** — A leftover contact name routes the client to someone who was never on a call and marks the document as a find-and-replace job. Do not invent a surname or job title for Jainil — SOURCES gives a first name only. Do not carry version "1.1", which implies a WIA v1.0 that does not exist.

#### Executive Summary — body copy

- **Sample showed** — E2M's summary of its own internal audit, framed around hours identified and hours automatable (mirroring the 370/200 hrs stat tiles).
- **WIA content** — Three paragraphs. (1) Mandate: "Wedding Industry Ads runs a boutique agency of roughly 12 clients on Google Ads, Meta Ads, and a white-labeled GoHighLevel product. Operating knowledge sits in individual contractors' heads. When the account manager hired in May resigned, Whitney Hodges returned to client-facing work and lost her sales and marketing time. The mandate for this blueprint is to move that knowledge into a system WIA owns, so the next account-manager hire runs the system rather than rebuilds it." (2) Scope: "This audit covers internal operating efficiency only. One person was audited: Gisselle Jimenez, executive assistant, across 12 recurring tasks. Six carry a monthly hour figure and total roughly 18 hrs/month. Six do not, including the highest-priority task. Fulfillment work was deferred by agreement on August 26 and has not been audited." (3) Response: "Twenty-two initiatives are grouped into 7 departments and 3 phases. One, the client onboarding draft builder, is already in build and is demonstrated in this review. Every initiative that touches a client keeps a named human approver before anything is sent."
- **Why** — Section 0 (~12 clients; Google Ads + Meta Ads + white-labeled GHL; Gisselle ~25 hrs/week); section 1 (Fallon hired May resigned, pushing Whitney back into client-facing work and blocking sales/marketing time; "We have the agency brain"); section 2 and the hours arithmetic at lines 114-118; @22:05-22:38 (Minu splits efficiency vs fulfillment, Aug 26 covers EFFICIENCY ONLY); section 4 (ON-01 in build); section 7 (human review gate on everything).
- **Risk if filled naively** — Framing the summary around hours saved reproduces the E2M sample's framing and walks straight into the Aug 11 question that was never answered. Section 1 states the driver is turnover-proofing, NOT time-saving — an hours-first summary sells the wrong thing to the actual buyer. Omitting "one person was audited" lets the ~18 hrs/month read as an agency-wide figure. Naming Fallon is permitted by SOURCES but is a judgment call in a client-facing document; "the account manager hired in May" is the safer default — confirm with Whitney.

#### Executive Summary — audit scope caveat line (NEW element, no sample equivalent)

- **Sample showed** — Nothing. The E2M sample audits itself across genuinely measured departments and carries no scope disclaimer.
- **WIA content** — A single rule line directly beneath the stat tiles: "Scope: one executive assistant, 12 tasks, internal operations. Fulfillment delivery work — creative briefs, ad copy, landing page builds and QA, and Google/Meta campaign management — is not yet audited."
- **Why** — Section 5: fulfillment was NEVER AUDITED, specifically creative briefs, ad copy, landing page builds and QA, Google/Meta campaign management, and the work Carmen and Jacqueline do; SOURCES requires this be represented as an explicit "not yet audited" gap, not as empty departments and not as invented initiatives. Section 2 line 35: all 12 rows are Gisselle's.
- **Risk if filled naively** — Without this line, the "7 departments" figure in the stat tiles reads as 7 audited departments. Carmen (Google Ads office hours, @8:16) and Jacqueline (Meta Ads office hours, @8:16) appear nowhere in the audit sheet, so a reader assumes their work was measured and priced. If an engineer instead fills the gap by generating fulfillment initiatives, that is exactly the prohibited failure in section 5.

#### Headline stat tile 1

- **Sample showed** — { label: "Manual hours identified", value: "370 hrs/month" }
- **WIA content** — { label: "Tasks audited", value: "12 (one executive assistant)" }
- **Why** — Section 2: 12 real rows (R4-R15), all Gisselle, all logged under department "Operations / Admin / Internal". Section 0: the "Sara" and "James" rows at sheet rows 2-3 are E2M's own example rows — row 2 col M reads "These are just an example tasks" — and must be excluded.
- **Risk if filled naively** — Reusing the "Manual hours identified" label forces a single headline hours total into the most prominent slot on the page, which SOURCES line 125 forbids outright ("DO NOT PRINT A SINGLE PRECISE TOTAL LIKE '370 hrs/month'"). If Sara and James are counted the tile reads "14" and the audit appears to have covered three people.

#### Headline stat tile 2

- **Sample showed** — { label: "Automatable or AI-assisted", value: "200 hrs/month" }
- **WIA content** — { label: "Verified manual hours", value: "~18 hrs/month (6 of 12 tasks)" }
- **Why** — Hours arithmetic, SOURCES lines 114-116: R5 = 2.0, R6 = 4.0, R11 = 3.0, R12 = 6.0, R13 = 2.0, R15 = ~1.1 (3 min × ~22 workdays), subtotal ~18 hrs/month VERIFIED. These are the only six rows that yield a monthly total.
- **Risk if filled naively** — Do NOT reuse the "Automatable or AI-assisted" label with a WIA number in it. Nothing in SOURCES quantifies how many hours are automatable — that is precisely the question Whitney asked on Aug 11 that was never answered (section 1: "That unanswered question is this deal"). Inventing a value here fabricates the single most consequential open figure in the engagement. Also keep "(6 of 12 tasks)" inside the value string: the schema allows `detail` only on the last tile.

#### Headline stat tile 3

- **Sample showed** — { label: "New opportunities", value: "8" }
- **WIA content** — { label: "Estimated all-in load, unverified", value: "45–70 hrs/month" }
- **Why** — SOURCES line 122: "~18 hrs/month verified; plausibly 45-70 hrs/month all-in. Against Gisselle's ~108 hrs/month capacity that is roughly 40-65% of her documented load." The ~108 hrs/month comes from section 0 (~25 hrs/week cap).
- **Risk if filled naively** — The value must remain a labelled range with "unverified" or "estimated" visible in the label. Collapsing it to a midpoint ("57 hrs/month") invents precision SOURCES forbids. The label must not say "team" or "agency" — this is one contractor's load against a 108 hrs/month personal cap, not organizational capacity. Reusing "New opportunities: 8" is also unsupported; no long-list of new revenue opportunities was produced for WIA, and section 4 forbids proposing automated client relationship contact, which is where such opportunities would otherwise come from.

#### Headline stat tile 4 (the only tile permitted a `detail` string)

- **Sample showed** — { label: "Blueprint automation count", value: "28", detail: "Prioritized from 42 ..." }
- **WIA content** — { label: "Initiatives in this blueprint", value: "22", detail: "Across 7 departments and 3 phases; one already in build" }
- **Why** — Section 6: 22 initiatives, 7 departments (client-comms, onboarding, meetings, operations, member-portal, marketing, platform), 3 phases. ON-01 is priority "Complete", phase 0, and section 4 confirms it is already in build.
- **Risk if filled naively** — Do not carry "Prioritized from 42" — no 42-item long list exists for WIA and inventing one is fabrication. Do not upgrade "in build" to "delivered" without qualification: the current build observes Dubsado signed+paid alerts, correlates the pair, notifies a Command Center dashboard, produces an editable execution draft, batch approves, and shows a persistent toast — with NO ClickUp writes, and APPROVED as terminal. Also note the "7 departments" figure needs the scope caveat line beside it, or it implies seven audited functions.

#### STRATEGIC OBJECTIVES block

- **Sample showed** — E2M's own objectives. Exact copy unknown; inferable from the sample's framing as hours recovered plus service expansion (it carries a "New opportunities" stat tile and per-initiative `revenue` fields).
- **WIA content** — Four verb-led objectives: (1) "Move operating knowledge out of individual contractors' heads into a system WIA owns." (2) "Return Whitney's time to sales and marketing." (3) "Connect the inbox, Slack, Google Drive, ClickUp, and GHL so work is visible in one place." (4) "Keep a named human approver in front of every client-facing output."
- **Why** — (1) Section 1: the goal is turnover-proofing so the next account-manager hire "is just a person who is kind of like running it. We have the agency brain." (2) Section 1, the Fallon trigger, plus @21:20: "we need more leads. We need more sales ... if we're not marketing actively, that's not going to happen." (3) @19:00 ("whatever is scanning the inbox needs to also be seeing what's happening in Slack ... where the call recordings and all the client things are living inside of our Google Drive") and @19:21, the central question: "how is it all connected? ... is there one place that we're going, and then there are just different tabs?" (4) @14:15, @18:30, @39:09, and section 4 (Daniela on hand-holding).
- **Risk if filled naively** — Objectives framed as "reduce headcount" or "recover X hours" mis-sell the deal — section 1 states the driver is explicitly NOT time-saving, and an hours objective re-opens the unanswered Aug 11 question in the hero. Any objective implying automated client contact contradicts the hard non-negotiable in section 4 and would be rejected outright by co-founder Daniela Justus. Objective (3) must be phrased as connection/visibility, not consolidation — nothing in SOURCES commits WIA to leaving Gmail; @35:43-36:08 explains exactly why they stay in it (Whitney does not see replies drafted in GHL, and GHL breaks formatting on send).

#### TASK AUDIT FINDINGS block

- **Sample showed** — E2M's own findings, presumably hours and task counts broken out per audited department.
- **WIA content** — Six factual findings: (1) "12 recurring tasks logged by one executive assistant; every row is marked Manual and every row's department field reads 'Operations / Admin / Internal'." (2) "Six tasks carry a monthly figure totalling roughly 18 hrs/month. Six do not, including the highest-priority task, filing emails and drafting responses." (3) "The only volume figure available for that highest-priority task is about 5 emails drafted per day." (4) "Two tasks are flag-only by client instruction: absence flagging and billing/data-hygiene checks. The human does the follow-up." (5) "Two prior in-house automation attempts did not succeed: the roll call sheet and recurring ClickUp task creation." (6) "Fulfillment delivery work was deferred on August 26 and is not represented in these findings."
- **Why** — (1) Section 2 line 35 and the Manual marking on every row R4-R15. (2) Lines 114-118; R4 is Priority HIGH with a BLANK monthly total. (3) @36:28, Whitney: "I would say 5 regularly". (4) R13 verbatim: "(Just needs to flag, we will manually follow up)"; R15 verbatim: "Just flag to Gisselle/Whitney". (5) @5:25-7:30, Gisselle on the roll call: "it got very very complicated ... wasn't able to figure out how we could best automate this", and on ClickUp recurrence: "it got confusing and I haven't been able to figure that out". (6) @22:05-22:38.
- **Risk if filled naively** — A findings block that reports hours by department implies each of the 7 departments was separately measured. It was not — the 7 departments are E2M's analytical grouping of one person's 12 rows plus call evidence, and section 6 shows the marketing department has zero sheet rows ("call 19:21-21:47 ONLY, not in sheet"). Dropping finding (5) loses the strongest evidence for why WIA needs a partner rather than another tool: their own capable EA already tried and stalled. Dropping finding (4) invites a build that auto-sends DMs and invoice chases, breaching a verbatim client constraint.

#### BEFORE AI column

- **Sample showed** — E2M's pre-automation state per process area. Exact rows unknown.
- **WIA content** — Five rows, present tense, no adjectives. Inbox: "Whitney stars incoming email; Gisselle files no-action mail into folders, drafts replies, tags threads 'waiting', and monitors whether team members reply within 24–48 business hours." Roll call: "Gisselle copies and pastes rows between two Google Sheets each week and updates the date to count consecutive misses." Meetings: "An AI notetaker records the call; the recap, the action items, the ClickUp tasks, and the chasing are all done by hand." Onboarding: "Onboarding is documented in ClickUp and executed manually at every step across multiple owners." Content: "Whitney flags a call; Gisselle pastes the transcript into ChatGPT for a reel script; Whitney refines and records; each additional format is redone from scratch."
- **Why** — Inbox: R4 plus @24:00-25:38 (Monday triage, 24-48 business hour target, emails get lost in team inboxes) and @27:00-29:56 (the starring system and the 'waiting' tag). Roll call: @11:06 ("manually copies/pastes rows and updates the date each week", two sheets for Google Ads and Meta Ads) and R13. Meetings: R6 (1 hr × 4 Mondays) and @17:30-18:30 ("even with an AI notetaker, it's still all on us to write a recap ... and then chase those action items"). Onboarding: @15:50-16:43 ("very heavy lift ... a lot that happens manually every step of the way", "so many hands that are in the onboarding"). Content: @19:40-21:00.
- **Risk if filled naively** — A generic "manual, slow, error-prone" before-column discards the specifics that prove E2M listened — the starring system, the two roll-call sheets, the 24-48 hour reply target — to a client whose adoption risk exceeds build risk (section 1). Note also: ChatGPT is accurate here as current state ONLY. It must never appear in an initiative `tools[]` array; the canonical tool strings are GHL, Gmail, ClickUp, Slack, Zoom, Fathom, Google Drive, Google Sheets, Canva, Claude API, Dubsado. Do not editorialize the onboarding row beyond the quoted narration — section 4 records that nobody at E2M has ever seen the ClickUp onboarding template.

#### AFTER AI column

- **Sample showed** — E2M's post-automation state per process area. Exact rows unknown.
- **WIA content** — Five rows, paired to the BEFORE rows, each preserving the human gate. Inbox: "Replies are drafted into the Gmail drafts folder in Whitney's voice; Whitney reviews and sends. Filing and 'waiting' follow-ups run on rules." Roll call: "Consecutive misses are counted and flagged at 2 weeks and 4 weeks. The DM and the email stay manual." Meetings: "Action items are drafted per team member with ClickUp task rows and due dates; Gisselle reviews before anything reaches Slack." Onboarding: "A signed-and-paid pair is detected and an editable execution draft is produced; a human activates it, edits assignees and dates, and batch approves." Content: "Call transcripts feed an idea queue; a voice note steers the reel script; Whitney still records and approves."
- **Why** — Inbox: @30:51-31:18 (drafts sit in the Gmail drafts folder, Gisselle marks the thread when ready for Whitney) and @39:09-40:19 (Whitney wants emails "proactively drafted", covering "the bulk of what I want them to say", in her voice). Roll call: R13 verbatim "(Just needs to flag, we will manually follow up)" and @14:15-15:11. Meetings: R6 opportunity verbatim "Y (Gisselle to review before sending to Slack)". Onboarding: section 4, the MVP scope as built. Content: @19:40-21:00, voice-note steering.
- **Risk if filled naively** — Any AFTER row that says "sent automatically" for client-facing output breaks the hard constraint Minu stated at @14:15 — WIA make sure "there isn't any AI-generated content that's going to the clients directly" — and would be rejected on sight. Putting an hours-saved number on each AFTER row fabricates figures: six of the twelve rows have no baseline to subtract from. For the onboarding row specifically, do NOT claim ClickUp tasks are created — the current build has no ClickUp writes and APPROVED is terminal. For the roll-call row, do not promise the DM or email is sent.

#### TASK AUDIT SNAPSHOT (compact table/summary inside the BEFORE/AFTER section)

- **Sample showed** — A condensed view of the sample's audit rows. Exact form unknown; presumably task counts and hours totalled by department.
- **WIA content** — Four facts, no totals row. Scope: "12 rows. Owner: Gisselle Jimenez, executive assistant, ~25 hrs/week cap (~108 hrs/month). Department as logged: 'Operations / Admin / Internal' on all 12." Priority split: "High 3 — email filing and drafting, action-item follow-up, roll call. Medium 7. Low 2." Quantification: "6 rows quantified, ~18 hrs/month. 6 rows show 'Not separately quantified'." Tools named in the sheet: "Gmail, ClickUp, Slack, Fathom, Zoom, Google Drive, Google Sheets, Canva, GHL."
- **Why** — Row-by-row priorities in section 2: HIGH = R4, R10, R13; MED = R6, R7, R8, R11, R12, R14, R15; LOW = R5, R9. Quantified vs blank per lines 114-118. Gisselle's capacity per section 0. Tool set is the union of the tools columns on R4-R15; the sheet writes "Highlevel", which SCHEMA.md requires be normalized to "GHL" because graph edges are derived from shared tool strings.
- **Risk if filled naively** — If the snapshot renders an hours column with six blanks, it reads as missing data rather than as unmeasured work — label those six "Not separately quantified". If it sums the hours column into a single figure it publishes a false agency-wide total, which SOURCES line 125 prohibits. If tool strings are copied verbatim from the sheet ("Highlevel", "Drive", "Clickup", "Google sheets"), the derived dependency graph fragments into disconnected clusters and the one thing Whitney actually asked for at @19:21 — "how is it all connected?" — renders as visual proof that it is not.

**Warnings raised for this group**

- PUBLICATION DATE IS NOT IN EVIDENCE. SOURCES.md contains no document date. "September 2026" is inferred from the Sept 2 call being the latest dated evidence and ON-01 demoing at this review. Treat as a confirm-before-publish field; do not ship "June 2026".
- DO NOT FILL THE SAMPLE'S "Automatable or AI-assisted" STAT. No figure in SOURCES quantifies automatable hours or an automatable percentage. That is the exact question Whitney asked on the Aug 11 discovery call which was never answered (section 1). A number in that slot is fabrication of the deal's central open figure.
- NO SINGLE HOURS TOTAL ANYWHERE IN THE HERO OR SUMMARY. SOURCES line 125 forbids printing a single precise total. Use "~18 hrs/month verified (6 of 12 tasks)" and the labelled range "45–70 hrs/month, unverified" as separate values, never merged.
- ONE PERSON WAS AUDITED. Every hours figure belongs to Gisselle Jimenez alone against a ~108 hrs/month personal cap. No stat tile, objective, or summary sentence may imply a team-wide or agency-wide hours total (section 5, line 263).
- THE 7 DEPARTMENTS WERE NOT AUDITED AS DEPARTMENTS. They are E2M's analytical grouping of one EA's 12 rows plus call evidence; all 12 sheet rows carry the single department value "Operations / Admin / Internal", and the marketing department has no sheet rows at all. Any hero element showing "7 departments" needs the scope caveat line adjacent to it.
- FULFILLMENT IS AN EXPLICIT GAP, NOT AN EMPTY SECTION. Creative briefs, ad copy, landing page builds and QA, Google/Meta campaign management, and the work Carmen and Jacqueline do were deferred by agreement on Aug 26. Represent as "not yet audited". Do not generate initiatives to fill it and do not render it as empty departments.
- "Manali Sharma" IS NOT IN EVIDENCE — remove from the contact field. Use Minu Bhatt, E2M Solutions. Do not invent a surname or job title for Jainil; SOURCES gives a first name only.
- REMOVE "Industry research (2026)" FROM THE SUBTITLE AND sourceBasis. No industry research was produced for WIA. Replace with the onboarding MVP build as the third basis.
- EXCLUDE THE SARA AND JAMES ROWS. Audit sheet rows 2-3 are E2M's own example rows (row 2 col M: "These are just an example tasks"). Counting them makes the task count 14 and implies three people were audited.
- TOOL STRINGS MUST BE NORMALIZED BEFORE THEY REACH ANY RENDERED SURFACE: the sheet's "Highlevel" becomes "GHL", "Clickup" becomes "ClickUp", "Drive" becomes "Google Drive", "Google sheets" becomes "Google Sheets". Graph edges are derived from shared tool strings (SCHEMA.md), so inconsistency fragments the dependency graph. ChatGPT (@19:40) is current-state narration only and must never appear in an initiative tools[] array.
- THE ONBOARDING MVP STOPS AT BATCH APPROVAL. No ClickUp writes exist in the current build and APPROVED is terminal. Hero and summary copy may say "in build" and "demonstrated in this review" but must not claim ClickUp tasks are created. Separately, nobody at E2M has seen the ClickUp onboarding template — onboarding claims are second-hand narration and should not be stated with more confidence than that.
- STAT TILE SCHEMA CONSTRAINT: exactly 4 entries, and `detail` is permitted only on the fourth. All caveats for tiles 1-3 must live inside the label or value strings, which is why the qualifiers are written into them above.
- REGISTER: en dashes for ranges (45–70, 24–48), no exclamation marks, and none of "seamless", "leverage", "empower", "revolutionize", "game-changing". Whitney has never used Claude and AI literacy is near zero — hero copy should avoid unexplained jargon entirely.
- NAMING FALLON IS A JUDGMENT CALL. SOURCES permits it, but naming a departed contractor in a client-facing hero should be confirmed with Whitney. "The account manager hired in May" is the safer default.

### Dependency graph, workflow index, department sections

#### Automation graph — node set / node count (the "29-node interconnected automation graph" canvas)

- **Sample showed** — 29 force-directed nodes, one per E2M initiative. The E2M headline stat says "Blueprint automation count: 28", so the 29th node's origin is unknown — likely a capstone/hub node that is not counted as a billable automation, or an off-by-one between the stat and the `ap` array.
- **WIA content** — 22 nodes — exactly the 22 approved initiatives: CC-01..CC-05, ON-01..ON-03, MK-01..MK-03, OP-01..OP-03, MP-01..MP-03, MC-01..MC-04, PLATFORM-01. No 23rd node. PLATFORM-01 is the intended visual hub, not an extra.
- **Why** — SOURCES section 6 fixes the structure at 22 initiatives, approved by Jainil. SCHEMA.md: every initiative needs exactly one `ap` entry or its impact/effort spread resolves to undefined, so the node set is `ap.length` = 22.
- **Risk if filled naively** — If any count is hardcoded (canvas size, layout seed, a "29 automations" caption, legend counters), the graph renders 22 nodes under a 29 label. Worse: padding WIA back up to 29 means inventing seven initiatives, which SOURCES section 5 explicitly forbids — fulfillment work was never audited and must not be represented as invented initiatives.

#### Automation graph — node label text on each node

- **Sample showed** — The short `ap.label` string for each E2M initiative (e.g. "AI Visibility Dashboard"), kept under ~34 chars — deliberately not the same string as `title`.
- **WIA content** — CC-01 Inbox Triage & Auto-Filing | CC-02 Draft Replies in Whitney's Voice | CC-03 Waiting-Tag Follow-Up Detector | CC-04 Post-Meeting Recap Emails | CC-05 Post-Sales-Call Drafts | ON-01 Signed+Paid Onboarding Draft | ON-02 Welcome Email + Checklist | ON-03 Client Asset Intake to Drive | MK-01 Meeting Recap to ClickUp Tasks | MK-02 Zoom Asset Auto-Archival | MK-03 Client-Facing Recap Drafting | OP-01 Overdue Task Digest to Slack | OP-02 Action-Item Chase & Ack Tracking | OP-03 Billing & Data-Hygiene Flags | MP-01 Roll Call & Absence Flagging | MP-02 Session Reminder Posts | MP-03 Session Recap Post + Banner | MC-01 Transcript to Content Queue | MC-02 Reel Script + Voice-Note Steer | MC-03 Multi-Format Repurposing | MC-04 Case-Study Extraction | PLATFORM-01 The Agency Brain. All 22 are 16-32 chars.
- **Why** — SCHEMA.md matrix entry: `label` is the short name shown on the graph node and matrix dot, keep under ~34 chars. Titles come from SOURCES section 6; the full title "AI Draft Replies in Whitney's Voice" is 35 chars and must be shortened for the node.
- **Risk if filled naively** — Reusing `title` verbatim overflows the node on CC-02 and MK-01 and truncates mid-word. Diverging the label from the matrix dot label breaks the visual link between the scatter and the graph — the reviewer cannot tell they are the same item.

#### Automation graph — node grouping / colour by department

- **Sample showed** — Nodes coloured by `departmentId` against E2M's own department set (operations, SEO, etc. — the sample uses ids like "operations" and initiative prefixes OPS-, SEO-, BS-, SL-).
- **WIA content** — Seven colour groups keyed to the approved departmentIds: client-comms (5 nodes), onboarding (3), meetings (3), operations (3), member-portal (3), marketing (4), platform (1).
- **Why** — SOURCES section 6, "7 departments (departmentId)" with the exact id strings. SCHEMA.md department object: `id` must match the initiative's `departmentId`.
- **Risk if filled naively** — E2M's palette has as many slots as its own department count; a mismatch silently recycles a colour so two WIA departments render identically. The single-node platform group also needs a visually distinct treatment or PLATFORM-01 reads as a stray dot rather than the capstone Whitney actually asked for (@19:21).

#### Automation graph — node size / weight

- **Sample showed** — Unknown from SCHEMA.md. Most plausibly derived from `impact` in the `ap` array (the only per-node magnitude the schema carries), possibly modulated by edge degree.
- **WIA content** — Use the approved impact scores from SOURCES section 6: CC-02 10, PLATFORM-01 10, ON-01 9, MC-01 9, MK-01 8, MP-01 8, OP-02 8, CC-05 8, MC-02 8, CC-01 7, ON-02 7, MC-03 7, MC-04 7, CC-04 7, MP-03 7, MK-03 7, CC-03 6, MK-02 6, MP-02 6, ON-03 5, OP-01 5, OP-03 5.
- **Why** — SOURCES section 6 gives impact/effort for all 22 (e.g. CC-02 10/5, PLATFORM-01 10/9). SCHEMA.md: the `ap` entry drives the scatter AND derives impact/effort via the `...ct[id]` spread.
- **Risk if filled naively** — If node size is instead driven by an hours field, WIA breaks: only six of 22 initiatives have a monthly hours figure at all (R5, R6, R11, R12, R13, R15). Sixteen nodes would size to zero or NaN, and the highest-priority item in the whole audit — R4 inbox work — would render as the smallest dot on the graph.

#### "DRAG TO REARRANGE" affordance label above/beside the graph

- **Sample showed** — Static UI hint text. No E2M-specific content.
- **WIA content** — Unchanged — "DRAG TO REARRANGE". Content-free chrome.
- **Why** — Nothing in SOURCES.md bears on this string; SCHEMA.md carries no field for it. E2M branding/theme is UNCHANGED per SOURCES section 0.
- **Risk if filled naively** — Low, but do not delete it. With 22 nodes instead of 29 the force layout has more slack and PLATFORM-01 will likely settle in the centre with high edge degree; reviewers need to pull it aside to read the seven department clusters. Removing the hint hides the only way to make the graph legible.

#### Legend entry 1 — DIRECT DEPENDENCY

- **Sample showed** — Edge style for links derived from `dependencies[]`. In the E2M sample `dependencies[]` holds access/data/decision strings ("Client GBP manager access", "Brand voice and service information"), not initiative ids — so the exact match rule that turns those into node-to-node edges is not documented in SCHEMA.md.
- **WIA content** — Keep the legend entry and populate real WIA dependency strings, but the engineer must first read the link-derivation function to learn what it matches on. The genuine WIA direct dependencies to encode are: CC-02 depends on CC-01 (filing signals feed drafting); CC-03 depends on CC-01; MK-03 depends on MK-01 and MK-02; ON-02 depends on ON-01; MC-02 depends on MC-01; MC-03 and MC-04 depend on MC-01; PLATFORM-01 depends on CC-01, CC-02, MK-01 and OP-02.
- **Why** — SCHEMA.md: "Edges compute at runtime from `dependencies[]`, shared `tools[]`, and `departmentId`" and "Graph links are DERIVED — do not author them." The chained ordering is grounded: @19:40-21:00 describes the content chain (flag a call, transcript, reel script, then carousel and email marketing); @19:00 states the platform must see the inbox, Slack and Drive together.
- **Risk if filled naively** — If the derivation matches dependency strings against initiative ids/labels and WIA fills `dependencies[]` only with access strings ("Gmail API access", "Dubsado alert access"), the DIRECT DEPENDENCY legend key renders with zero edges — a dead key in the legend, and the graph collapses into nothing but shared-tool and same-department links. Conversely, if the rule is a loose string match, generic strings like "Whitney's approval" repeated across cards will draw dozens of meaningless edges.

#### Legend entry 2 — SHARED SYSTEM

- **Sample showed** — Edge style for links derived from two initiatives naming the same string in `tools[]`. In the E2M sample this is what the schema calls "the main lever for making the dependency graph read well".
- **WIA content** — Keep. WIA's shared-system edges must come from exactly eleven canonical strings and no others: GHL, Gmail, ClickUp, Slack, Zoom, Fathom, Google Drive, Google Sheets, Canva, Claude API, Dubsado. Per initiative: CC-01 [Gmail, Claude API, GHL]; CC-02 [Gmail, Claude API]; CC-03 [Gmail, Claude API]; CC-04 [Google Drive, Gmail, Zoom, Claude API]; CC-05 [Gmail, GHL, Claude API]; ON-01 [Dubsado, Gmail]; ON-02 [ClickUp, Gmail, Claude API]; ON-03 [Gmail, Google Drive]; MK-01 [Fathom, ClickUp, Slack, Claude API]; MK-02 [Zoom, Google Drive]; MK-03 [Zoom, Fathom, Gmail, Claude API]; OP-01 [ClickUp, Slack]; OP-02 [Slack, Gmail, ClickUp]; OP-03 [GHL]; MP-01 [GHL, Google Sheets]; MP-02 [GHL]; MP-03 [GHL, Canva, Slack]; MC-01 [Zoom, Fathom, Google Drive, Claude API]; MC-02 [Claude API, Google Drive]; MC-03 [Claude API, Canva]; MC-04 [Claude API, Google Drive, Fathom]; PLATFORM-01 [Gmail, Slack, Google Drive, GHL, ClickUp, Claude API].
- **Why** — SCHEMA.md: "naming the same tool string in two initiatives draws an edge between them. Use tool names consistently (always \"GHL\", never sometimes \"GoHighLevel\") or the graph fragments." Tool assignments trace to the audit sheet tool columns (R4 Gmail, R5 ClickUp+Slack, R6 Fathom+ClickUp+Slack, R7 Drive+Gmail+Zoom, R8 ClickUp, R9 Gmail+Drive, R10 Slack, R11 Highlevel, R12 Highlevel+Canva, R13 Highlevel+Google sheets, R14 Zoom, R15 Highlevel) and to @19:00 for PLATFORM-01.
- **Risk if filled naively** — The audit sheet writes "Highlevel" and "Google sheets"; SOURCES section 4 and the call say "GoHighLevel", "LeadLock", "LeetLog", "high level". Copying those raw produces five separate nodes-worth of tool strings where one belongs, and MP-01/MP-02/MP-03/OP-03/CC-01/CC-05/PLATFORM-01 stop sharing an edge — the member-portal cluster detaches from the rest of the graph entirely. Second trap: @19:40 says Gisselle currently pastes transcripts into ChatGPT. ChatGPT is not on the canonical list and must stay in `currentProcess` prose only; putting it in `tools[]` invents a spurious cluster around a tool WIA is being moved off.

#### Legend entry 3 — SAME DEPARTMENT

- **Sample showed** — Edge style for links derived from a matching `departmentId`. In the E2M sample this creates one dense clique per department.
- **WIA content** — Keep. Produces five cliques and one isolate: client-comms (CC-01..CC-05, 10 edges), onboarding (ON-01..ON-03, 3), meetings (MK-01..MK-03, 3), operations (OP-01..OP-03, 3), member-portal (MP-01..MP-03, 3), marketing (MC-01..MC-04, 6), platform (PLATFORM-01, 0 — it has no same-department peer).
- **Why** — SOURCES section 6 assigns every initiative to exactly one of the seven approved departmentIds. SCHEMA.md lists `departmentId` as one of the three derivation inputs.
- **Risk if filled naively** — PLATFORM-01 draws zero same-department edges by construction. If it also has thin `tools[]`, the single most important node in the deck — the answer to Whitney's central question @19:21, "how is it all connected?" — floats disconnected at the edge of the canvas. That is the exact opposite of the message. Give PLATFORM-01 the full six-tool list so shared-system edges pull it to the centre.

#### Legend entry 4 — PORTAL MODULE

- **Sample showed** — Unknown. SCHEMA.md names the rendered link type but documents only three derivation inputs (dependencies, tools, departmentId) — none of which obviously yields "portal module". Most likely an E2M-specific rule keyed off a client-portal product string or a flag on the department. The engineer must read the link-derivation function before touching this.
- **WIA content** — If the rule is retargetable: bind it to the GoHighLevel member portal so MP-01, MP-02 and MP-03 link as portal modules — the portal is the GHL Communities feature and Accelerator clients get portal access plus the vault plus office hours. If the rule is hardwired to an E2M product string, either retarget it to GHL Communities or remove the fourth legend entry. Do not leave it rendering an empty key.
- **Why** — @15:17: the member portal is built inside GoHighLevel ("our high level, which is LeetLog/LeadLock"), the Communities feature. R11, R12 and R13 are all portal work (reminder posts, session recap posts, roll call). @14:15: the 2-week flag results in a DM through the member portal.
- **Risk if filled naively** — Highest-risk legend item in the group. Left as-is it either (a) renders a legend key with no matching edges — a visible defect on the client's own blueprint, or (b) still matches an E2M product string and draws edges between WIA initiatives on the basis of a tool WIA does not use. Filling it naively is worse: sweeping all of GHL into "portal module" would portal-tag OP-03 (overdue invoices) and CC-05 (lead pipeline), which are not portal work at all.

#### Automation graph — edge density / overall legibility

- **Sample showed** — 29 nodes with E2M's tool spread produce a particular edge count and force-layout equilibrium tuned to that density.
- **WIA content** — 22 nodes over a deliberately narrow eleven-tool vocabulary. Gmail appears in 8 initiatives, Claude API in 11, GHL in 6, ClickUp in 5, Slack in 5, Google Drive in 6 — so shared-system edges will be denser per node than E2M's, not sparser. Expect a hairball around Claude API unless the renderer de-weights ubiquitous tools.
- **Why** — SCHEMA.md flags shared-tool edges as "the main lever". SOURCES prescribes exactly eleven canonical tool strings, and WIA's stack really is that concentrated: section 4, "100% GoHighLevel for both domains (one sub-account)" plus Gmail, ClickUp, Slack, Zoom, Fathom, Google Drive, Google Sheets, Canva, Dubsado.
- **Risk if filled naively** — A small tool vocabulary across 22 nodes over-connects. If every Claude API pair draws an edge, the graph says "everything depends on everything", which reads as hand-waving to a founder whose stated complaint (@19:21) is that she cannot tell how the pieces fit. Consider excluding Claude API from shared-system edge derivation, or rendering it at lower opacity — but decide this deliberately, do not discover it at render time.

#### WORKFLOW INDEX — list body

- **Sample showed** — A flat or department-grouped index of every initiative in the E2M deck, keyed by id and short label, acting as the jump list into the deep-dive sections.
- **WIA content** — 22 rows in this order: CC-01, CC-02, CC-03, CC-04, CC-05, ON-01, ON-02, ON-03, MK-01, MK-02, MK-03, OP-01, OP-02, OP-03, MP-01, MP-02, MP-03, MC-01, MC-02, MC-03, MC-04, PLATFORM-01 — using the short labels listed for the graph nodes. ON-01 carries a Complete/Phase 0 marker in the index, not just on its card.
- **Why** — SOURCES section 6 gives the id order and the id-to-title mapping. SOURCES section 4: the Client Onboarding MVP is ALREADY IN BUILD and demoing at this Blueprint Review — "This must appear as a delivered/in-build item, not a proposal."
- **Risk if filled naively** — If ON-01 appears in the index looking identical to the 21 proposals, the one thing E2M has actually shipped gets read as another promise — in a deal whose live risk (SOURCES section 1) is an unanswered ROI question from Aug 11. Also: index ordering must match the deep-dive section ordering or the anchors jump to the wrong department.

#### WORKFLOW INDEX — header / count caption

- **Sample showed** — Unknown; if the sample prints a count it reflects E2M's 28-or-29 figure.
- **WIA content** — "22" if a count is shown. Do not print any hours figure in this header.
- **Why** — SOURCES section 6: 22 initiatives. SOURCES section 2, hours arithmetic: "DO NOT PRINT A SINGLE PRECISE TOTAL LIKE '370 hrs/month'."
- **Risk if filled naively** — An index header that sums department hours would produce something like "18 hrs/month across 22 workflows", which is doubly wrong — it silently converts a six-row verified subtotal into an all-initiatives total, and it undersells the engagement, since sixteen of the 22 have no hours figure at all (the honest range is ~18 hrs/month verified, plausibly 45-70 all-in).

#### Department deep-dive section 1 — Client Communications

- **Sample showed** — An E2M department block: name, team array, currentManualHours, recoverableHours, one-sentence summary, then its initiative cards.
- **WIA content** — id `client-comms`; name "Client Communications"; team ["Whitney Hodges (owner)", "Gisselle Jimenez (EA)"]; currentManualHours "Not separately quantified — R4 and R7 monthly totals are blank"; recoverableHours "Not separately quantified; every outbound send stays human-approved"; summary "Drafts, files, and tracks the Gmail inbox that carries all client communication in and out." Cards: CC-01 Inbox Triage & Auto-Filing (High, Phase 1, 7/3), CC-02 AI Draft Replies in Whitney's Voice (High, Phase 1, 10/5), CC-03 Waiting-Tag Follow-Up Detector (Medium, Phase 1, 6/3), CC-04 Post-Meeting Template Recap Emails (Medium, Phase 2, 7/5), CC-05 Post-Sales-Call Proactive Drafts (Medium, Phase 2, 8/6).
- **Why** — SOURCES section 6 maps R4 and R7 plus call 23:45-40:19 to this department. @18:30: the inbox "is basically where all client communication is coming in and going out from". R4 monthly total is BLANK and R7 monthly total is BLANK (section 2). @36:28 gives the only volume on record: ~5 emails drafted per day.
- **Risk if filled naively** — This is the department with the HIGHEST-priority audit row (R4, Priority HIGH) and NO hours. Inventing a number here — e.g. deriving "5 emails/day x 10 min" into a monthly figure — manufactures precision SOURCES section 2 forbids. Leaving E2M's "52 hrs/month minimum" in place attributes an E2M workload to a two-person WIA function.

#### Department deep-dive section 2 — Client Onboarding

- **Sample showed** — E2M department block as above.
- **WIA content** — id `onboarding`; name "Client Onboarding"; team ["Gisselle Jimenez (EA)", "Whitney Hodges (owner)", "Multiple contributors across onboarding steps"]; currentManualHours "Not separately quantified — R8 records ~2 hrs per onboarding at a frequency of 'depending on clients onboarding'; R9 is 'Varies'"; recoverableHours "Not separately quantified — the ON-01 build stops at batch approval and writes nothing to ClickUp"; summary "Prepares onboarding checklists, welcome emails, and client asset intake once a client signs and pays." Cards: ON-01 Signed+Paid to Onboarding Draft (Complete, Phase 0, 9/4), ON-02 Welcome Email + Checklist Assignment (Medium, Phase 1, 7/4), ON-03 Client Asset Intake to Drive Filing (Low, Phase 1, 5/3).
- **Why** — SOURCES section 6 maps R8 and R9 plus call 15:50-17:00 here. @15:50-16:43: onboarding is documented in ClickUp but is a "very heavy lift ... a lot that happens manually every step of the way", with "so many hands that are in the onboarding" and "different contingencies". SOURCES section 4: no ClickUp writes in the current build; APPROVED is terminal.
- **Risk if filled naively** — Two specific traps. First, naming the "multiple contributors" as identified people — SOURCES section 4 says nobody at E2M has ever seen the ClickUp onboarding template and the flow is second-hand narration, so any named per-step owner is fabricated. Second, writing a recoverableHours figure for ON-01 implies the MVP already saves onboarding hours; it currently produces an editable draft a human must approve and does not touch ClickUp, so it saves nothing measurable yet.

#### Department deep-dive section 3 — Meetings & Knowledge Capture

- **Sample showed** — E2M department block as above.
- **WIA content** — id `meetings`; name "Meetings & Knowledge Capture"; team ["Gisselle Jimenez (EA)", "Whitney Hodges (owner)", "Monday team meeting attendees"]; currentManualHours "4 hrs/month verified (R6: 1 hr x 4 Mondays, recorded as a maximum); R7 and R14 monthly totals blank"; recoverableHours "Up to 4 hrs/month verified; client-facing recaps remain review-gated"; summary "Converts Monday team meetings and client Zoom calls into action items, ClickUp tasks, and archived assets." Cards: MK-01 Meeting Recap to Action Items to ClickUp (Medium, Phase 1, 8/5), MK-02 Zoom Asset Auto-Archival (Medium, Phase 1, 6/3), MK-03 Client-Facing Recap Drafting (Medium, Phase 2, 7/6).
- **Why** — SOURCES section 6 maps R6, R7 and R14 plus call 17:00-19:00 here. R6 is explicitly "1 hr x 4 (Mondays) = 4 hrs/mo (max)". @17:30-18:30 describes the full manual chain after a client Zoom even with an AI notetaker present.
- **Risk if filled naively** — R6's 4 hrs is a stated maximum, not an average — printing "4 hrs/month" without the qualifier overstates the only verified figure in this department. Also R7 is counted in both client-comms (CC-04) and meetings (MK-02, as R7b); if anyone later assigns R7 an hours figure it must not be added into both departments or the total double-counts.

#### Department deep-dive section 4 — Operations & Task Orchestration

- **Sample showed** — E2M department block as above. Note the E2M sample's own department is literally named "Operations & Admin" with team ["All team members"] — the closest name collision in the deck.
- **WIA content** — id `operations`; name "Operations & Task Orchestration"; team ["Gisselle Jimenez (EA)", "Team members tagged in Slack", "Whitney Hodges (owner)"]; currentManualHours "~3.1 hrs/month verified (R5 2.0 + R15 ~1.1); R10 monthly total blank"; recoverableHours "~3.1 hrs/month verified; OP-03 flags only, the human does the follow-up"; summary "Tracks overdue ClickUp tasks, chases unacknowledged Slack action items, and flags overdue invoices and invalid emails in GHL." Cards: OP-01 Overdue Task Digest to Slack (Low, Phase 1, 5/2), OP-02 Action-Item Chase & Ack Tracking (High, Phase 2, 8/7), OP-03 Billing & Data-Hygiene Flags (Medium, Phase 1, 5/2).
- **Why** — SOURCES section 6 maps R5, R10, R15 here. Verified arithmetic in section 2: R5 = 2.0, R15 = ~1.1 (3 min x ~22 workdays). R10 is Priority HIGH with a blank total. R15 verbatim: "Just flag to Gisselle/Whitney".
- **Risk if filled naively** — Name collision — this is the one WIA department whose id (`operations`) matches the E2M sample's id, so a partial data swap can leave E2M's "Operations & Admin" name, its "All team members" team array, and its E2M initiative cards visible under a WIA heading. It will not error; it will just silently render E2M content. Second risk: the audit sheet's department column reads "Operations / Admin / Internal" for ALL twelve rows, so a naive importer dumps all 22 initiatives into this one department and the other six render empty.

#### Department deep-dive section 5 — Member Portal & Community

- **Sample showed** — E2M department block as above.
- **WIA content** — id `member-portal`; name "Member Portal & Community"; team ["Gisselle Jimenez (EA)", "Carmen (Google Ads office hours)", "Jacqueline (Meta Ads office hours)"]; currentManualHours "11 hrs/month verified (R11 3.0 + R12 6.0 + R13 2.0)"; recoverableHours "Up to 11 hrs/month; MP-01 flags only — the human sends the DM at 2 weeks and the email at 4 weeks"; summary "Runs reminder posts, session recaps, and attendance flagging inside the GoHighLevel member portal." Cards: MP-01 Roll Call & Absence Flagging (High, Phase 1, 8/4), MP-02 Session Reminder Posts (Medium, Phase 1, 6/2), MP-03 Session Recap Post + Canva Banner (Medium, Phase 2, 7/5).
- **Why** — SOURCES section 6 maps R11, R12, R13 plus call 5:25-15:17 here. Hours are the verified rows: R11 15 min x 12 = 3, R12 ~0.5 x 12 = 6, R13 10 min x 12 = 2. @8:16 names Carmen on Google Ads office hours (~10-11am CST Thursdays) and Jacqueline on Meta Ads (~3:30pm). @15:17 places the portal in GoHighLevel Communities. @14:15-15:11 gives the 2-week DM / 4-week email escalation.
- **Risk if filled naively** — This department carries 11 of the 18 verified hours — 61% of everything defensible in the audit — so it will look like the biggest win on the graph. That is accurate but must not be over-read: MP-01 is FLAG ONLY per R13 verbatim ("Just needs to flag, we will manually follow up"), so the 2 hrs of R13 is the checking time, not the follow-up time. Listing Carmen and Jacqueline on the team is correct for who runs the sessions, but neither was audited — do not let their presence imply their hours are inside the 11.

#### Department deep-dive section 6 — Marketing & Content Engine

- **Sample showed** — E2M department block as above, presumably with an hours figure since every E2M department was audited.
- **WIA content** — id `marketing`; name "Marketing & Content Engine"; team ["Whitney Hodges (owner)", "Gisselle Jimenez (EA)"]; currentManualHours "Not audited — raised on the Aug 26 call, no rows in the task audit sheet"; recoverableHours "Not separately quantified"; summary "Turns client call recordings into reel scripts, carousels, and email marketing under Whitney's direction." Cards: MC-01 Transcript to Content Idea Queue (High, Phase 2, 9/5), MC-02 Reel Script Generation with Voice-Note Steering (High, Phase 2, 8/6), MC-03 Multi-Format Repurposing (Medium, Phase 3, 7/7), MC-04 Case-Study Extraction (Medium, Phase 3, 7/8).
- **Why** — SOURCES section 6 marks this department "call 19:21-21:47 ONLY, not in sheet". @19:40-21:00: Whitney flags a call to Gisselle, Gisselle puts the transcript into ChatGPT, reel script, Whitney refines and records, then carousel and email marketing; she wants to steer it with a voice note. @21:20: "we need more leads. We need more sales ... if we're not marketing actively, that's not going to happen."
- **Risk if filled naively** — This is the only department with zero audit rows, so it is the most tempting place to invent hours. Any figure here is pure fabrication. The currentManualHours string must say "Not audited" rather than "Not separately quantified" — the two are different claims, and the distinction matters because SOURCES section 1 records that Whitney's marketing time is exactly what Fallon's resignation destroyed.

#### Department deep-dive section 7 — Platform (capstone)

- **Sample showed** — E2M department block as above. Unknown whether the sample has a single-initiative capstone department at all.
- **WIA content** — id `platform`; name "Platform"; team ["Whitney Hodges (owner)", "Gisselle Jimenez (EA)", "Next account-manager hire"]; currentManualHours "Not applicable — cross-cutting capstone with no audit rows"; recoverableHours "Not separately quantified — the deliverable is retained institutional knowledge, not recovered hours"; summary "Connects Gmail, Slack, Google Drive, ClickUp, and GHL into one retrievable record of how the agency runs." Card: PLATFORM-01 The Agency Brain (High, Phase 3, 10/9).
- **Why** — SOURCES section 6 lists department 7 as "Platform capstone (turnover-proofing + call @19:21)". Section 1: Whitney's actual goal is turnover-proofing so the next account-manager hire "is just a person who is kind of like running it. We have the agency brain." @19:00: "whatever is scanning the inbox needs to also be seeing what's happening in Slack ... where the call recordings and all the client things are living inside of our Google Drive." @19:21 is the central question.
- **Risk if filled naively** — Two ways to wreck this. Putting an hours figure on it reframes the one initiative that answers Whitney's real buying motive as a time-savings play, when SOURCES section 1 states plainly the driver is NOT saving time. Rendering it as a normal one-card department buries it — it is the answer to "how is it all connected?" and should read as the capstone, not as the smallest department in the deck. Also note the source label is "Platform capstone"; "capstone" is a structural note, not a display name.

#### Department field — `currentManualHours` / `recoverableHours` across all seven sections (aggregate reading)

- **Sample showed** — E2M free-text values such as "178 hrs/month", "52 hrs/month minimum", "20 hrs/month for image sourcing", "Not separately quantified", "New revenue service only", "Varies by active client services" — a mix, proving qualifiers are acceptable in this field.
- **WIA content** — Only three of seven departments carry a number: meetings 4 hrs/month, operations ~3.1, member-portal 11 — total 18.1 hrs/month verified. The other four read "Not separately quantified" or "Not audited". Every numeric string must carry the word "verified" and the source rows. Nowhere in the department region may a grand total be printed.
- **Why** — SOURCES section 2: six rows yield a monthly total (R5 2.0, R6 4.0, R11 3.0, R12 6.0, R13 2.0, R15 ~1.1) for a ~18 hrs/month verified subtotal; six rows including the highest-priority R4 are unquantified. "Honest total: ~18 hrs/month verified; plausibly 45-70 hrs/month all-in." Section 5: "No hours exist for anyone except Gisselle. Do not imply a team-wide hours total."
- **Risk if filled naively** — The single most dangerous component in this group. Every one of the 18.1 hours belongs to ONE contractor — Gisselle, capped at ~25 hrs/week (~108 hrs/month). If the UI sums department hours, or if a reader adds the three visible numbers, the deck implies a team-wide 18 hrs/month across an agency of Whitney, Gisselle, Carmen, Jacqueline and Daniela. That is both understated (it is 40-65% of Gisselle's documented load, which is the actually impressive framing) and misattributed. Leaving E2M's "178 hrs/month" in even one department is a client-visible fabrication in a deal whose open risk is precisely an unanswered ROI question (SOURCES section 1, Aug 11).

#### Department field — `team` array rendered as a roster chip row per section

- **Sample showed** — E2M role strings, e.g. ["All team members"].
- **WIA content** — Only these strings appear anywhere: "Whitney Hodges (owner)", "Gisselle Jimenez (EA)", "Carmen (Google Ads office hours)", "Jacqueline (Meta Ads office hours)", "Team members tagged in Slack", "Monday team meeting attendees", "Multiple contributors across onboarding steps", "Next account-manager hire".
- **Why** — SOURCES section 0 lists the real people: Whitney Hodges (owner/founder), Gisselle Jimenez (EA via Dot agency, Honduras, ~25 hrs/week, ~1 yr tenure, Whitney's proxy), Carmen (Google Ads office hours), Jacqueline (Meta Ads office hours), Daniela Justus (co-founder). Section 0 also states explicitly: "NOT WIA STAFF: 'Sara' and 'James' appear in audit sheet rows 2-3 but those are E2M's own example rows."
- **Risk if filled naively** — Sara and James are sitting in the source spreadsheet and will be pulled in by any naive import — row 2 column M literally says "These are just an example tasks". Shipping a client deck that staffs their agency with two people who do not exist is unrecoverable. Second risk: the team array reads as "who was audited". Carmen and Jacqueline appear on member-portal because they run the sessions, not because their work was measured — the section needs to make that distinction or the roster implies coverage the audit does not have. Do not add Daniela Justus to any department team; nothing in SOURCES places her in an audited workflow.

#### "Fulfillment / delivery not yet audited" gap notice — a needed NEW block in the department deep-dive region

- **Sample showed** — Nothing. The E2M sample has no such block because every E2M department was audited.
- **WIA content** — A single non-department callout placed after the seven sections, reading approximately: "Fulfillment and delivery work is not covered by this blueprint. Creative briefs, ad copy, landing page builds and QA, and Google and Meta campaign management were not audited — the Aug 26 session covered internal operations only, and fulfillment was deferred by agreement. No initiatives are proposed for that scope." No hours, no node on the graph, no initiative cards, no eighth department id.
- **Why** — SOURCES section 5: "Fulfillment/delivery work was NEVER AUDITED: creative briefs, ad copy, landing page builds and QA, Google/Meta campaign management, the work Carmen and Jacqueline do. Aug 26 deferred it by design. Represent this as an explicit 'not yet audited' gap, NOT as empty departments and NOT as invented initiatives." @22:05-22:38: Minu splits the engagement into (1) efficiency of internal operations and (2) fulfillment of the work; Aug 26 covers EFFICIENCY ONLY. @16:43 records Whitney's fulfillment asks (creative briefs, first drafts of copy, first drafts of landing pages, checking landing pages for errors and conversion) — asks, not audited work.
- **Risk if filled naively** — Without this block the seven departments read as a complete picture of the agency, and Whitney concludes her delivery operation was reviewed and found to need nothing. When fulfillment work later surfaces as out of scope, the blueprint looks like it concealed a gap. The opposite failure is equally bad: creating an eighth "Fulfillment" department with empty or invented cards violates SOURCES section 5 twice over, and @16:43 gives just enough material to make invention tempting.

#### Initiative card — id chip (e.g. "OPS-01")

- **Sample showed** — E2M ids matching /^[A-Z]+-\d{2}$/ — OPS-, SEO-, BS-, SL- prefixes.
- **WIA content** — Six prefixes: CC- (5), ON- (3), MK- (3), OP- (3), MP- (3), MC- (4), plus PLATFORM-01. All match the regex, including PLATFORM-01.
- **Why** — SOURCES section 6 fixes the exact id strings. SCHEMA.md: `id: "OPS-01", // string, matches /^[A-Z]+-\d{2}$/`.
- **Risk if filled naively** — Note the near-collision: `MK-` is Meetings & Knowledge Capture while `MC-` is Marketing & Content Engine, and `OP-` is Operations while `ON-` is Onboarding. Two pairs one character apart. Any hand-transcription will cross them, and because the graph colours nodes by `departmentId` rather than by prefix, a mistyped id puts a card in the right section with the wrong anchor and a broken jump from the WORKFLOW INDEX. Validate every id against section 6 programmatically.

#### Initiative card — `title`

- **Sample showed** — Full descriptive E2M titles, e.g. "Google Business Profile Automation Suite".
- **WIA content** — The 22 titles from SOURCES section 6 verbatim, including the longer forms the graph node abbreviates: "AI Draft Replies in Whitney's Voice", "Meeting Recap -> Action Items -> ClickUp" (render the arrows as text or an en dash chain, not as a raw ASCII arrow), "Reel Script Gen w/ Voice-Note Steering", "Signed+Paid -> Onboarding Draft (MVP)".
- **Why** — SOURCES section 6 lists all 22 id/title pairs. SCHEMA.md distinguishes `title` from the shorter `label`.
- **Risk if filled naively** — Titles naming a person ("in Whitney's Voice") are correct and grounded at @39:09 ("it sounds like it's in my voice") — do not sanitise them into generic phrasing, that specificity is what tells Whitney she was heard. Conversely the ASCII arrows are shorthand from the source doc, not intended display text.

#### Initiative card — `owner` line

- **Sample showed** — E2M ownership strings like "All team members" — who owns the WORK, not the automation.
- **WIA content** — Gisselle Jimenez (EA) on CC-01, CC-02, CC-03, CC-04, ON-01, ON-02, ON-03, MK-01, MK-02, OP-01, OP-02, OP-03, MP-01, MP-02, MP-03 (15 cards). Whitney Hodges on CC-05, MK-03, MC-01, MC-02, MC-03, MC-04, PLATFORM-01 (7 cards).
- **Why** — SOURCES section 2: all twelve audit rows are Gisselle, all in department "Operations / Admin / Internal". Whitney owns the sales-call drafting (@33:39), the client-facing recap (@17:30, since @14:15 forbids AI content reaching clients directly), the content engine (@19:40, she flags the call and refines the script), and the capstone (section 1).
- **Risk if filled naively** — Fifteen of 22 cards naming the same person looks lopsided and there will be pressure to spread ownership onto Carmen, Jacqueline or Daniela to balance it. Do not. Section 5 is explicit that no hours exist for anyone but Gisselle and that fulfillment was never audited; assigning them owners fabricates audited scope. The concentration is itself the honest finding — one contractor holds this much, which is exactly the turnover exposure Whitney is buying against (section 1).

#### Initiative card — priority badge

- **Sample showed** — One of "High" | "Medium" | "Low" | "Complete" | "Strategic" per the schema enum.
- **WIA content** — High: CC-01, CC-02, OP-02, MP-01, MC-01, MC-02, PLATFORM-01. Medium: CC-03, CC-04, CC-05, ON-02, MK-01, MK-02, MK-03, OP-03, MP-02, MP-03, MC-03, MC-04. Low: ON-03, OP-01. Complete: ON-01. "Strategic" is unused.
- **Why** — SOURCES section 6 priority column. Note it abbreviates Medium as "Med" for CC-03, CC-04, CC-05, ON-02, MK-01, MK-02, MK-03, OP-03, MP-02, MP-03, MC-03, MC-04.
- **Risk if filled naively** — "Med" is not in the schema enum. Copied literally it either fails a badge lookup and renders unstyled, or falls through to a default colour that misreads as Low. Also check the E2M sample's priority-to-colour mapping still holds: WIA has only one Complete item and no Strategic item, so if the legend or filter chips enumerate all five states, two chips will filter to zero or one result.

#### Initiative card — phase badge

- **Sample showed** — Phase 0-3 with E2M's own phase names; the sample's phase 1 is "Quick Wins".
- **WIA content** — Phase 0: ON-01 only. Phase 1: CC-01, CC-02, CC-03, ON-02, ON-03, MK-01, MK-02, OP-01, OP-03, MP-01, MP-02 (11). Phase 2: CC-04, CC-05, MK-03, OP-02, MP-03, MC-01, MC-02 (7). Phase 3: MC-03, MC-04, PLATFORM-01 (3). Phase names retheme to 1 "Stop the Leaks", 2 "Free the Founder", 3 "The Agency Brain".
- **Why** — SOURCES section 6 phase column and the three rethemed phase names with their strategies: phase 1 "build on Gmail/GHL/ClickUp as they stand; immediate recovery", phase 2 "reclaim Whitney's attention so she can sell", phase 3 "institutional memory; survives the next resignation". Phase 3's framing traces to section 1 (Fallon's resignation) and @19:21.
- **Risk if filled naively** — SOURCES gives no name for phase 0 — that string is not in evidence and needs Jainil's call, not an invention. Second: "Quick Wins" is E2M's phase 1 name and will survive a partial swap, which flattens the deliberate narrative arc (leaks, founder, brain) that maps to Whitney's actual driver. Third: phase 3's name "The Agency Brain" collides with PLATFORM-01's title "The Agency Brain"; that is intentional per section 6 but the card must not look like a rendering bug.

#### Initiative card — `status` line (phase 0 / Complete items only)

- **Sample showed** — An optional string, e.g. "POC delivered; ...", shown only for phase 0 / Complete initiatives.
- **WIA content** — Present on ON-01 only: "In build by E2M and demoing at this Blueprint Review. Observes Dubsado signed and paid alerts, correlates the pair, surfaces the match on a Command Center dashboard for a human to activate, then produces an editable execution draft — rename tasks, change assignees and dates, remove rows — ending in batch approval and a persistent toast. Writes nothing to ClickUp in this build; approval is terminal." Omit the key entirely on the other 21.
- **Why** — SOURCES section 4 gives this flow step by step and states "This must appear as a delivered/in-build item, not a proposal." SCHEMA.md marks `status` OPTIONAL, "only for phase 0 / Complete items".
- **Risk if filled naively** — Overstating it is the risk in both directions. Describing ON-01 as creating ClickUp tasks is false — there are no ClickUp writes in this build — and it would also justify adding ClickUp to ON-01's `tools[]`, drawing shared-system edges to ON-02, OP-01, OP-02 and MK-01 that assert an integration that does not exist. Understating it is the other failure: if ON-01 renders like the other 21 proposals, the only shipped thing in the deck loses its status in a deal already carrying an unanswered ROI question.

#### Initiative card — `timeSaved` field

- **Sample showed** — Free text. The E2M sample itself uses "3-5 hrs per client per month", "N/A - new service offering", "Not separately quantified" — proving qualifiers are valid values, not placeholders.
- **WIA content** — Only six cards carry a number: OP-01 "2 hrs/month (R5, verified)"; MK-01 "Up to 4 hrs/month (R6, verified maximum)"; MP-02 "3 hrs/month (R11, verified)"; MP-03 "6 hrs/month (R12, verified)"; MP-01 "2 hrs/month (R13, verified — checking time only, follow-up stays manual)"; OP-03 "~1.1 hrs/month (R15: 3 min x ~22 workdays)". The remaining sixteen read "Not separately quantified" with the reason, e.g. CC-02 "Not separately quantified; ~5 drafts per day is the only volume on record", and the four MC- cards read "Not separately quantified — raised on the Aug 26 call, not in the task audit". PLATFORM-01 reads "Not separately quantified — turnover-proofing, not hours recovery".
- **Why** — SOURCES section 2 hours arithmetic gives exactly these six figures and names the six unquantified rows (R4, R7, R8, R9, R10, R14). @36:28 is the only volume for R4: "I would say 5 regularly". Section 7: "timeSaved must be honest: use the verified figure where one exists, otherwise 'Not separately quantified' or a labelled estimate. Never invent precision."
- **Risk if filled naively** — Sixteen "Not separately quantified" strings will read as an unfinished document and someone will want to fill them. Every filled value would be fabricated. The specific temptation is CC-02, the highest-impact initiative in the deck (10/5) attached to the highest-priority audit row (R4, HIGH), sitting there with no number — the multiplication "5 emails x 10 min x 22 days" is right there and it is not in evidence. Also do not let a UI sum this column; six of 22 values are numeric and any total silently means "six initiatives" while appearing to mean "all of them".

#### Initiative card — `currentProcess` sentence

- **Sample showed** — One sentence, present tense, factual pain statement, no adjectives like "painful" — e.g. "Local-client profiles are neglected or inconsistently managed despite ...".
- **WIA content** — One factual sentence per card drawn from the audit row or call. Examples: MP-01 "Gisselle copies and pastes rows between two roll call sheets each week and updates the date by hand to count consecutive misses." CC-01 "Whitney stars incoming email, Gisselle files threads that need no reply, tags threads awaiting a customer response, and drafts the rest." MC-01 "Whitney flags a call to Gisselle, who pastes the transcript into ChatGPT to produce a reel script." ON-01 "Onboarding is documented in ClickUp but each step is triggered and tracked by hand across multiple contributors."
- **Why** — @11:06 for MP-01 (manual copy/paste, two sheets, members, consecutive misses, last attended, 2-week and 4-week flags). @24:00-25:38 and @27:00-29:56 for CC-01. @19:40 for MC-01. @15:50-16:43 for ON-01. SCHEMA.md register rule: present tense, states the pain factually, no adjectives, "State what happens, let the reader conclude."
- **Risk if filled naively** — Two register traps. First, the calls contain quotable frustration — @16:54 "it never feels like it's actually going smoothly. It always feels like we're chasing the team", @5:25 Gisselle's "it got very very complicated" — and dropping those in violates the no-adjectives rule and reads as the vendor characterising the client's team as disorganised in a document the whole team will see. Second, ChatGPT belongs in this prose (it is what they actually do today) but must never migrate into `tools[]`.

#### Initiative card — `outcome` sentence

- **Sample showed** — One sentence starting with a verb, describing what the system does — "Manages posts, responses, Q&A, profile-integrity alerts, and monthly reporting."
- **WIA content** — Verb-led, one sentence, describing system behaviour and stopping where the human takes over. Examples: MP-01 "Tracks office-hours attendance across both sheets and flags members at two and four consecutive misses." OP-03 "Checks GHL for overdue invoices and invalid email addresses daily and flags them to Gisselle and Whitney." CC-02 "Drafts replies in Whitney's voice into the Gmail drafts folder for her review and send." PLATFORM-01 "Connects inbox, Slack, Drive, ClickUp and GHL activity into one retrievable record of how the agency runs."
- **Why** — SCHEMA.md register rule: starts with a verb ("Manages", "Creates", "Extends", "Runs"), describes what the system does, not what the client feels. R13 verbatim "Just needs to flag, we will manually follow up" and R15 verbatim "Just flag to Gisselle/Whitney" set the stopping point for MP-01 and OP-03. @30:51-31:18 puts CC-02's output in the Gmail drafts folder.
- **Risk if filled naively** — The verb choice encodes the scope commitment. Writing "Sends" or "Follows up" on MP-01 or OP-03 breaks the FLAG-ONLY constraint stated verbatim in the audit rows and in SOURCES section 7. Writing "Sends" on any CC- card breaks the absolute human-review gate (@14:15, @18:30, @39:09) and, for member-facing items, breaks @14:15's constraint that no AI-generated content goes to clients directly. On this account a single wrong verb is a scope and trust failure, not a copy edit.

#### Initiative card — `capabilities` bullet list

- **Sample showed** — 3-7 terse noun phrases, not sentences, no trailing periods — e.g. "Weekly keyword-optimized posts", "Review-response drafts within two hours".
- **WIA content** — Worked example, MP-01: ["Consecutive-miss counting across both office-hours sheets", "Reset on attendance", "Two-week and four-week flags", "No automated member contact"]. Worked example, CC-01: ["Thread filing by client label", "Waiting-tag application", "Follow-up creation on waiting threads", "Vendor newsletters left unfiled"]. Worked example, ON-01: ["Dubsado signed and paid alert correlation", "Command Center match surfacing", "Editable execution draft", "Batch approval", "No ClickUp writes"].
- **Why** — @9:18-9:47 for the reset-on-attendance and consecutive-miss logic; @14:15-15:11 for the two-week and four-week notches. R4 opportunity text for the CC-01 items (filing, starring, waiting tags, follow-ups). @30:08: the "tools" label is vendor newsletters (Canva, Dubsado), "usually not priority" but NOT auto-archived because occasionally one matters. SOURCES section 4 for the ON-01 chain.
- **Risk if filled naively** — Capabilities is where scope inflation happens invisibly — each bullet reads as a build commitment but none is individually checked against a source. Two concrete errors to avoid: adding "auto-archives low-priority newsletters" to CC-01 directly contradicts @30:08, and adding any send/DM/email capability to MP-01 contradicts R13. Note also that the negative bullets ("No automated member contact", "No ClickUp writes") are load-bearing here, not filler — they are the visible record of a constraint.

#### Initiative card — `tools` chip row

- **Sample showed** — Concrete named systems and real APIs per initiative, e.g. ["Google Business Profile API", "Claude API", "GHL"].
- **WIA content** — The eleven canonical strings only, assigned per the SHARED SYSTEM legend entry above. Normalise the source spellings: audit-sheet "Highlevel" and call-transcript "GoHighLevel" / "high level" / "LeetLog" / "LeadLock" all become "GHL"; "Google sheets" becomes "Google Sheets"; bare "Drive" becomes "Google Drive". ChatGPT, Dot, and Google Tag Manager do not appear in any `tools[]`.
- **Why** — SCHEMA.md: tools are "concrete named systems only. Real APIs and products", and consistent strings are what keep the graph from fragmenting. SOURCES section 4 lists the stack. The task brief fixes the eleven canonical strings.
- **Risk if filled naively** — Chips are the most visible place an inconsistency shows: a card reading "Highlevel" next to another reading "GHL" tells the client's own engineer the deck was assembled by hand, and simultaneously severs the graph edge. Two subtler traps. First, LeadLock is WIA's white-labelled product name for their GHL build (@15:17), not a separate system — chipping it creates a phantom twelfth tool. Second, @8:16 says an AI notetaker is present at office hours without naming it; R6 names Fathom for the Monday team meeting. Do not extend Fathom to the office-hours initiatives (MP-02, MP-03) — that attribution is not in evidence and would draw false edges into the meetings department.

#### Initiative card — `dependencies` list

- **Sample showed** — Access, data and decisions that must be true before build starts — "Client GBP manager access", "Brand voice and service information".
- **WIA content** — Real WIA blockers. CC-01: ["Gmail API access on Whitney's and Gisselle's accounts", "Decision on whether the current star and label taxonomy is kept or rebuilt", "Current client-label list"]. CC-02: ["Approved corpus of Whitney's sent email for voice matching", "Decision on Gmail versus GHL as the send surface"]. ON-01/ON-02: ["Walkthrough of the ClickUp onboarding template", "Dubsado to GHL migration status per offer"]. MP-01: ["Access to both roll call Google Sheets", "GHL Communities attendance data"]. MC-02: ["Decision on the voice-note capture channel"]. PLATFORM-01: ["Client requirements document listing steps and accesses"].
- **Why** — @39:09 Whitney is "NOT TIED TO THE LABELING SYSTEM at all", making the taxonomy an open decision rather than a fixed input. @35:43-36:08 gives the reason they stay in Gmail: drafts in GHL are not visible to Whitney and formatting breaks on send — so the send-surface choice is a real unresolved dependency, sharpened by @33:10 (Gmail syncs to GHL; Whitney works the lead pipeline in GHL). SOURCES section 4: nobody at E2M has ever seen the ClickUp onboarding template, Whitney offered a walkthrough on Sept 2 @19:59 and it never happened; the Dubsado to GHL migration is in progress with only Foolproof Follow-Up Advantage moved and "majority of our contracts are in Dubsado". @11:06 for the two roll call sheets. @40:33 names the client requirements document as the agreed next step.
- **Risk if filled naively** — Leaving E2M's dependency strings makes the blueprint unactionable and, because edges derive partly from this field, wires the WIA graph off E2M's inputs. Filling it with generic placeholders ("API access", "stakeholder approval") is nearly as bad: the ClickUp-template gap and the Dubsado migration split are the two real reasons ON-01 and ON-02 could slip, and burying them in a generic string means the client never sees the blocker that is theirs to clear. Naming them here is also the honest disclosure that the onboarding flow in this deck is second-hand narration.

#### Initiative card — `humanReview` line

- **Sample showed** — Names WHO reviews and WHAT they gate. Always present. E2M sample: "E2M approves generated posts and review responses before publication."
- **WIA content** — Present on all 22, naming a real WIA person. CC-01 "Gisselle Jimenez reviews the filing queue; vendor-newsletter threads are never auto-archived." CC-02 "Whitney Hodges reviews and sends every draft; drafts wait in the Gmail drafts folder." CC-03 "Gisselle Jimenez reviews flagged waiting threads each Monday and asks Whitney whether to follow up." CC-04 "Gisselle Jimenez or Whitney Hodges reviews before sending." CC-05 "Whitney Hodges reviews and sends the proposal email draft." ON-01 "A human activates the correlated pair and edits the execution draft before batch approval; approval is terminal." ON-02 "Gisselle Jimenez reviews the welcome email and checklist assignment before it reaches the client." ON-03 "Gisselle Jimenez confirms file placement in the client's Drive folder." MK-01 "Gisselle Jimenez reviews the action-item list before it posts to Slack." MK-02 "Gisselle Jimenez confirms the recording, transcript and summary landed in the client folder." MK-03 "Whitney Hodges reviews every client-facing recap before send." OP-01 "Gisselle Jimenez reviews the digest before the team is tagged." OP-02 "Gisselle Jimenez decides which unacknowledged items get chased." OP-03 "Flag only — Gisselle Jimenez or Whitney Hodges performs the follow-up." MP-01 "Flag only — a team member DMs at two weeks and emails at four weeks." MP-02 "Gisselle Jimenez confirms the reminder posted before the session." MP-03 "Gisselle Jimenez reviews the banner and recap post before publishing." MC-01 "Whitney Hodges selects which calls enter the queue." MC-02 "Whitney Hodges refines the script before recording." MC-03 "Whitney Hodges approves each derived format before publishing." MC-04 "Whitney Hodges approves case-study copy before use." PLATFORM-01 "Whitney Hodges and Gisselle Jimenez remain the approval gate on every outbound touchpoint the system surfaces."
- **Why** — R6 opportunity column literally reads "Y (Gisselle to review before sending to Slack)"; R7 reads "Y (Gisselle/Whitney to review before sending)"; R5 reads "Could send to Gisselle for review first"; R13 and R15 are flag-only verbatim. @14:15 Minu states the constraint that no AI-generated content goes to clients directly. @18:30 "we would still want to be able to review it before anything goes out". @30:51-31:18 drafts sit in Gmail drafts with a symbol marking review-ready. @14:15-15:11 the team member sends the DM. @19:40 Whitney flags the call; @20:40 she refines the script. SOURCES section 7: every initiative must name a human reviewer.
- **Risk if filled naively** — This field is the entire trust architecture of the engagement. E2M's sample string names "E2M team" as reviewer — left in place, it tells Whitney that the vendor, not her people, gates her client communication, on an account where co-founder Daniela is explicit that wedding-industry clients hire them for hand-holding and personal connection (section 4). Omitting the field on even one card breaks the "no exceptions" rule in section 7. And a generic "human review required" is not compliant with the schema, which requires naming WHO and WHAT.

#### Initiative card — `revenue` line (optional field)

- **Sample showed** — Present on some E2M cards, e.g. "$200-$500/month per client", marking initiatives that are billable new service offerings.
- **WIA content** — Omit the key entirely on all 22 cards. No revenue figure appears anywhere in the department deep-dives.
- **Why** — SCHEMA.md marks `revenue` OPTIONAL — "omit unless genuinely billable". Every one of the 22 is internal efficiency or turnover-proofing for WIA's own operation (SOURCES sections 1 and 6); none is a service WIA resells. WIA's public pricing exists in section 4 (Google Search Accelerator $1,997, Meta Ads Accelerator $1,697, Bundle $3,197, Elevate avg $2,500/mo incl ad spend, LeadLock $1,697+ setup / $147/mo) but those are prices for WIA's existing services, not revenue attributable to any initiative here.
- **Risk if filled naively** — Two failures. If the card template renders the revenue row unconditionally, 22 cards show an empty or "undefined" value. If someone fills it by reaching for the public pricing in section 4, the deck asserts that an internal automation generates $1,997 of revenue — a fabricated causal claim about the client's own P&L, using real numbers, which is the most credible-looking and therefore most damaging kind of invention available in this document.

#### Initiative card — impact / effort score display (from the `ap` spread)

- **Sample showed** — impactScore and effortScore spread onto each initiative via `...ct["OPS-01"]`, sourced from the matching `ap` matrix entry.
- **WIA content** — All 22 pairs from SOURCES section 6: CC-01 7/3, CC-02 10/5, CC-03 6/3, CC-04 7/5, CC-05 8/6, ON-01 9/4, ON-02 7/4, ON-03 5/3, MK-01 8/5, MK-02 6/3, MK-03 7/6, OP-01 5/2, OP-02 8/7, OP-03 5/2, MP-01 8/4, MP-02 6/2, MP-03 7/5, MC-01 9/5, MC-02 8/6, MC-03 7/7, MC-04 7/8, PLATFORM-01 10/9.
- **Why** — SOURCES section 6 lists impact/effort for every initiative. SCHEMA.md: "Every initiative needs exactly one entry here or its impact/effort spread resolves to undefined."
- **Risk if filled naively** — A missing or mis-keyed `ap` entry does not throw — it silently resolves to undefined, so the card renders a blank or NaN score and the graph node loses its size. The likely victims are the two prefix near-collisions (MK-/MC-, OP-/ON-) and PLATFORM-01, whose id is the only one longer than three characters and the only one that will break a hardcoded prefix parser. Verify all 22 keys resolve before publishing rather than eyeballing the graph.

**Warnings raised for this group**

- PORTAL MODULE link derivation is undocumented. SCHEMA.md names four rendered link types but lists only three derivation inputs (dependencies[], tools[], departmentId). The engineer must read the link-derivation function before this legend entry can be retargeted. If it keys off an E2M-specific product string it will render an empty legend key for WIA.
- DIRECT DEPENDENCY derivation is ambiguous. The E2M sample's dependencies[] holds access/data/decision strings, not initiative ids, so it is unclear how those become node-to-node edges. If the rule matches dependency strings against initiative ids or labels, the WIA dependency strings recommended here (access grants, open decisions) will draw zero direct-dependency edges. Confirm the rule, then decide whether to add explicit id references alongside the access strings.
- Node count changes 29 to 22. Verify nothing is hardcoded: canvas dimensions, force-layout seed, legend counters, a WORKFLOW INDEX count caption, or any 'N automations' string. Do not pad WIA back to 29 — SOURCES section 5 forbids inventing initiatives for the unaudited fulfillment scope.
- Phase 0 has no name in SOURCES.md. Section 6 rethemes phases 1, 2 and 3 only. ON-01 is the sole phase 0 item and needs a display name from Jainil, not an invented one.
- SOURCES section 6 abbreviates priority as 'Med'. The SCHEMA enum requires 'Medium'. Twelve initiatives are affected: CC-03, CC-04, CC-05, ON-02, MK-01, MK-02, MK-03, OP-03, MP-02, MP-03, MC-03, MC-04.
- The 'Strategic' priority value in the schema enum is unused by WIA, and 'Complete' is used exactly once. Any priority filter chips or legend that enumerates all five states will show two chips resolving to zero or one card.
- The `revenue` key is omitted on all 22 cards. Confirm the card template hides the row when the key is absent rather than rendering an empty or undefined value.
- Only three of seven departments carry a numeric currentManualHours (meetings 4, operations ~3.1, member-portal 11 = 18.1 hrs/month verified). No component in this region may sum, average, or total department hours — every one of those hours belongs to Gisselle alone, and a printed total would imply a team-wide figure that SOURCES section 5 explicitly prohibits.
- The unaudited fulfillment scope has no home in the approved 7-department structure. It needs a non-department callout block that does not exist in the E2M sample — a new component, not a data swap. It must carry no hours, no graph node, and no initiative cards.
- ChatGPT appears in the current content-engine process (@19:40) but is not one of the eleven canonical tool strings. Keep it in currentProcess prose only. Same for LeadLock and LeetLog, which are WIA's brand names for their GHL build (@15:17), not separate systems.
- The audit sheet writes 'Highlevel' and 'Google sheets'; the transcript writes 'GoHighLevel', 'high level', 'LeadLock', 'LeetLog'. All must normalise to 'GHL' and 'Google Sheets' or the member-portal cluster detaches from the graph entirely.
- R6 names Fathom for the Monday team meeting; @8:16 says only that an AI notetaker is present at office hours, without naming it. Do not attribute Fathom to MP-02 or MP-03 — that would draw unsupported edges between the member-portal and meetings departments.
- 'Sara' and 'James' are in the source audit sheet rows 2-3 and are E2M's own example rows (row 2 col M: 'These are just an example tasks'). Any naive import will staff WIA's departments with two people who do not exist. Add an explicit exclusion filter.
- Two id prefix near-collisions will survive hand-transcription: MK- (Meetings) versus MC- (Marketing), and OP- (Operations) versus ON- (Onboarding). Validate all 22 ids programmatically against SOURCES section 6; a mis-keyed `ap` entry resolves to undefined silently rather than throwing.
- The `operations` departmentId is shared between the E2M sample and WIA. A partial data swap will leave E2M's 'Operations & Admin' name, its ['All team members'] roster and its cards rendering under a WIA heading with no error.
- The audit sheet lists all twelve rows under department 'Operations / Admin / Internal'. Any importer that reads the sheet's department column will collapse all 22 initiatives into one department and leave six empty. Departments must come from SOURCES section 6, not from the sheet.

### Portal, Impact, Controls, Activation

#### Portal section header — eyebrow chip, H2 title, and the lead paragraph (renders `np.title`, then `np.positioning` + " " + `np.rationale`)

- **Sample showed** — Eyebrow "PLATFORM-01". Title "E2M Client Intelligence Portal". Paragraph: "E2M's own branded product, built and maintained by E2M Solutions. Clients who repeatedly use a unified portal have a stronger retention relationship than clients who only receive monthly email reports."
- **WIA content** — Eyebrow stays "PLATFORM-01". Title: "The Agency Brain". positioning: "An internal operations surface for Whitney Hodges and Gisselle Jimenez, built and maintained by E2M Solutions and owned by Wedding Industry Ads." rationale: "Whitney asked how the pieces connect and whether there is one place to go with different tabs; today the answer lives in individual contractors' heads."
- **Why** — SOURCES sec.6 names PLATFORM-01 "The Agency Brain". Sec.1 states the driver is turnover-proofing — extract institutional knowledge out of individual contractors' heads into a system they own, so the next account-manager hire "is just a person who is kind of like running it. We have the agency brain." Aug 26 @19:21: "how is it all connected? How does it all kind of work together... is there one place that we're going, and then there are just different tabs?"
- **Risk if filled naively** — Leaving the E2M copy sells WIA a white-label product for THEIR clients. WIA already runs a client-facing member portal inside GoHighLevel Communities (@15:17) and already sells a white-labeled GHL product called LeadLock. A second client-facing portal collides with both, and it contradicts the sec.4 non-negotiable that client relationship contact stays human. Naive fill in the other direction — swapping "E2M" for "Wedding Industry Ads" and keeping "Client Intelligence Portal" — produces exactly that collision while also stating a retention claim about WIA's clients that appears nowhere in evidence.

#### "Connected client modules" grid — 7 tiles, each rendering module `name`, an initiative-id chip from `sourceInitiativeId`, and `status`

- **Sample showed** — AI Visibility Score (SEO-01, "POC exists"), Organic Rankings (SEO-02, Phase 1), Website Health Score (WD-02, Phase 2), Google Ads Performance (OPS-04, Phase 2), GBP Stats (OPS-01, Phase 2), Review Sentiment (OPS-03, Phase 2), Monthly Report Archive (OPS-02, Phase 2)
- **WIA content** — Retitle the block "Connected internal modules". Seven tiles: "Onboarding Command Center" (ON-01, status "Active build"); "Inbox Triage" (CC-01, Phase 1); "Draft Replies in Whitney's Voice" (CC-02, Phase 1); "Meeting Recap and Action Items" (MK-01, Phase 1); "Roll Call and Absence Flags" (MP-01, Phase 1); "Action-Item Chase" (OP-02, Phase 2); "Content Idea Queue" (MC-01, Phase 2).
- **Why** — Every id and phase comes from the sec.6 initiative table. ON-01's status is set by sec.4: the Client Onboarding MVP is already in build by E2M and demoing at this Blueprint Review, and must appear as a delivered/in-build item, not a proposal. The word "internal" is required by sec.1 and @19:21 — the surface is for Whitney and Gisselle.
- **Risk if filled naively** — Two failure modes. First, the word "client" in the block heading re-frames an internal tool as a client deliverable. Second, the "Module activation pipeline" list below reuses these same `status` strings and highlights a tile in orange only when the status matches /poc|live|active/i — so a literal "In build" renders grey and reads as not-yet-started, burying the one thing E2M has actually shipped. "Active build" is both honest and matches the regex. Do not write "Live" — sec.4 says the build stops at batch approval with a toast and performs no ClickUp writes.

#### "Rollout sequence" list — numbered phases, from `np.rollout`

- **Sample showed** — A single string, "Launch with the existing AI Visibility module, then add each module as its source automation goes live.", split on ", then " by the renderer into auto-labelled entries "Foundation launch" and "Expansion phase 1".
- **WIA content** — Supply `rollout` as an array of three objects so the phase names from the blueprint survive: {name: "Stop the Leaks", description: "Build on Gmail, GHL, ClickUp and Slack as they stand; recover the tasks that already have a verified monthly figure."}, {name: "Free the Founder", description: "Reclaim Whitney's attention so she can sell."}, {name: "The Agency Brain", description: "Hold institutional memory so the system survives the next resignation."}
- **Why** — Sec.6 defines the three phase names and their one-line meanings verbatim. Sec.1 gives the resignation trigger: account manager Fallon resigned, pushing Whitney back into client-facing work and blocking her sales/marketing time.
- **Risk if filled naively** — If `rollout` is left as a comma-string, the renderer invents its own labels ("Foundation launch", "Expansion phase 1") and the three named phases the rest of the blueprint is organised around never appear in this section — the Portal reads as disconnected from the roadmap. The renderer accepts an array of {name, description}; use it.

#### Portal "Dependencies" panel — three hardcoded rows (Integration layer / Platform foundation / Activation requirements) inside the JSX, not the data file

- **Sample showed** — Integration layer: "Semrush, Google Ads, Google Business Profile, and Search Console — provisioned and tested by E2M." Platform foundation: "Existing React + backend POC, client authentication, and white-label domain — managed by E2M." Activation requirements: "Source automations must be live before each portal module can be enabled for clients."
- **WIA content** — Integration layer: "GHL, Gmail, ClickUp, Slack, Zoom, Fathom, Google Drive, Google Sheets and Canva — access granted by Wedding Industry Ads, integrated by E2M." Platform foundation: "The Command Center dashboard from the onboarding MVP, plus logins for Whitney Hodges and Gisselle Jimenez." Activation requirements: "Each source automation must be live before its tab is enabled for Whitney and Gisselle."
- **Why** — Sec.4 lists the stack: GoHighLevel (one sub-account across both domains), Gmail, ClickUp, Slack, Zoom, Fathom, Google Drive, Google Sheets, Canva, Dubsado. Sec.4 also describes the in-build MVP as notifying on a Command Center dashboard where a human activates the draft. Sec.0 names Whitney and Gisselle.
- **Risk if filled naively** — These strings live in the component, not in the data object — an engineer who edits only the data file ships Semrush, Google Business Profile and Search Console to a wedding-industry ads agency that uses none of them. "enabled for clients" is the same client-facing error as above. Also do not name Dubsado here as an ongoing integration layer without the caveat in the API card: sec.4 says the Dubsado to GHL migration is in progress and only Foolproof Follow-Up Advantage has moved.

#### Portal "Platform specifications" panel — three rows: Technology (from `tools`), White-label (hardcoded string), Pricing (from `revenueModel`)

- **Sample showed** — Technology: "Semrush, Google Ads, Google Business Profile, Google Search Console, Existing React + backend POC, Client authentication, White-label domain". White-label: "100% branded as E2M and maintained by E2M Solutions." Pricing: "$150–$500/month per client, tiered by active modules".
- **WIA content** — Technology: ["GHL", "Gmail", "ClickUp", "Slack", "Zoom", "Fathom", "Google Drive", "Google Sheets", "Canva", "Claude API"]. Replace the White-label row with an Ownership row: "Owned by Wedding Industry Ads. Built and maintained by E2M Solutions. Not exposed to WIA's clients." Pricing row: remove it, or set it to "Not applicable — internal system. No pricing agreed on the record."
- **Why** — Tool strings are the canonical list required for the dependency graph. Sec.1: the point is a system THEY own. Sec.5 and sec.7: no revenue, cost or pricing figure for this engagement exists in evidence; timeSaved and equivalent fields must say "Not separately quantified" rather than carry a fake number.
- **Risk if filled naively** — Two distinct fabrications. "100% branded as E2M" states that the thing Whitney is buying in order to own is branded by the vendor — the exact opposite of the sec.1 driver, and the kind of line that reads as a land-grab in a review meeting. On pricing, the tempting naive fill is WIA's own published price list from sec.4 (Accelerators at $1,997 and $1,697, bundle $3,197, Elevate ~$2,500/mo, LeadLock $1,697 setup / $147/mo). Those are prices WIA charges its clients today; presenting any of them as portal revenue invents a business model. Note also: the `tools` strings feed the dependency graph — write "GHL", never "GoHighLevel" or "Highlevel", even though the audit sheet spells it "Highlevel" in rows R11–R15.

#### Portal footer strip — three hardcoded feature bullets with icons

- **Sample showed** — "Secure, authenticated client access" | "100% E2M branded experience" | "Human-reviewed insights and recommendations"
- **WIA content** — "Access limited to Whitney Hodges and Gisselle Jimenez" | "Owned by Wedding Industry Ads; survives contractor turnover" | "Human review gate before any client-facing output"
- **Why** — Sec.0 names the two people. Sec.1: extract institutional knowledge into a system they own so the next account-manager hire just runs it; trigger was Fallon's resignation. Sec.7: human review gate before anything client-facing, no exceptions (@14:15, @18:30, @39:09).
- **Risk if filled naively** — Hardcoded in the JSX array — invisible to anyone editing data only. "Client access" tells the room that WIA's wedding clients log into this, which contradicts the section above it and the sec.4 non-negotiable that clients hire WIA for hand-holding and personal connection.

#### Impact section header — eyebrow, H2, and subhead paragraph (all hardcoded in JSX)

- **Sample showed** — Eyebrow "Strategic value". H2 "Quantifiable impact". Subhead "E2M can recover capacity across every department while opening productized, recurring revenue streams."
- **WIA content** — Eyebrow "Audit scope". H2 "What the audit measured". Subhead: "Twelve tasks were audited, all belonging to Gisselle Jimenez. Six carry a monthly hours figure and total approximately 18 hrs/month. The remaining six, including the highest-priority item, have no figure. Fulfillment work was not audited."
- **Why** — Sec.2 hours arithmetic: six rows yield a monthly total (R5 2.0, R6 4.0, R11 3.0, R12 6.0, R13 2.0, R15 ~1.1) for a subtotal of ~18 hrs/month verified; six rows are unquantified (R4, R7, R8, R9, R10, R14) and R4 is the highest-priority item. Sec.2 header: "All Gisselle, all department 'Operations / Admin / Internal'." Sec.5: fulfillment was never audited and must be represented as an explicit gap.
- **Risk if filled naively** — "Quantifiable impact" is a promise the evidence cannot pay. Half the audited rows have a blank monthly total, and the one with the highest priority (R4, email filing and drafting) is among them. Keeping the E2M heading forces whoever fills the cards below it to produce numbers, which is how "370 hrs/month" style fabrication enters. "Recover capacity across every department" is also false for WIA: five of the seven departments have no hours at all, and one (marketing) has no audit-sheet rows whatsoever.

#### Impact horizontal scroller — "Hours recovered" cards, one per row of the department-hours array (`NA`)

- **Sample showed** — Six cards. Brand Strategy 178 hrs → 110 hrs, 62% reduction; SEO & Content 71 → 42, 59%; Web Development 52 → 17, 33%; Sales/Lead Gen 48 → 31, 65%; Design 20 → —, "New service"; Total 369 → 200, 54%. Each card's detail is assembled by a hardcoded sentence frame: `"{current} manual hours/month to {recoverable} recoverable | {reduction} reduction"`.
- **WIA content** — Seven cards, every one labelled with the single auditee. Member Portal & Community (Gisselle Jimenez): "11 hrs/month verified — R11, R12, R13". Meetings & Knowledge Capture (Gisselle Jimenez): "4 hrs/month verified — R6; R7 and R14 have no figure". Operations & Task Orchestration (Gisselle Jimenez): "~3 hrs/month verified — R5 and R15; R10 has no figure". Client Communications (Gisselle Jimenez): "No monthly figure recorded — R4 and R7; the only volume on record is ~5 emails drafted per day". Client Onboarding (Gisselle Jimenez): "No monthly figure recorded — R8 and R9". Marketing & Content Engine: "Not in the task audit — sourced from the Aug 26 call only". Audited total: "~18 hrs/month verified across 6 of 12 tasks; 45–70 hrs/month plausible all-in against Gisselle's ~108 hrs/month capacity". Add an eighth card, "Fulfillment — not audited": "Creative briefs, ad copy, landing page builds and QA, and Google and Meta campaign management were deferred by design."
- **Why** — Per-department sums are arithmetic on the sec.2 rows: member-portal R11 3.0 + R12 6.0 + R13 2.0 = 11.0; meetings R6 = 4.0; operations R5 2.0 + R15 ~1.1 = ~3.1. Sec.2: "Honest total: ~18 hrs/month verified; plausibly 45-70 hrs/month all-in. Against Gisselle's ~108 hrs/month capacity that is roughly 40-65% of her documented load." @36:28 gives the only R4 quantity: "I would say 5 regularly." Sec.6 maps marketing to the call at 19:21-21:47 only, not the sheet. Sec.5 lists the unaudited fulfillment work and @22:05-22:38 records Minu deferring it.
- **Risk if filled naively** — This is the highest-fabrication-risk component in the group. The card frame demands three numbers per row and the E2M version has 24 of them; filling seven WIA rows the same way means inventing at least 15 figures. It would also imply a team-wide total when sec.5 states flatly that no hours exist for anyone except Gisselle — Carmen, Jacqueline, Whitney and Daniela have none. Two mechanical traps: (1) the detail sentence frame is hardcoded, so a value of "Not separately quantified" renders as "Not separately quantified manual hours/month to Not separately quantified recoverable" — the frame itself must be edited, not just the data; (2) do not add a "reduction %" for any row, since no recoverable-hours estimate exists anywhere in evidence. Also do not create cards for "Sara" or "James" — sec.0 confirms rows 2-3 of the audit sheet are E2M's own example rows.

#### Impact horizontal scroller — "Revenue opportunity" cards, one per row of the new-services array (`OA`)

- **Sample showed** — Seven cards. Website Health Monitor $99–$199/site; GBP Automation Suite $200–$500/client; AI Chatbot $99–$299/site; Social Media Calendar $299–$499/client; Review Monitoring $99–$199/client; Client Intelligence Portal $150–$500/client; Pre-Sales Audit "Increases close rate". Detail frame: `"{monthlyRate} | {targetClients}"`.
- **WIA content** — Remove the revenue card set — set the array empty. If the section needs a second card group, re-label the eyebrow "Strategic outcome" and use non-numeric cards grounded in the call: "Turnover-proofing — the next account-manager hire runs the system rather than rebuilding it"; "Founder time — Whitney is back in client-facing work since Fallon resigned, which blocks selling"; "Open question — how much time back in three months, and what share can be automated, was asked on Aug 11 and never answered". Rename the two detail keys if you do this; the current frame prints a pricing pipe.
- **Why** — Sec.5 and sec.7 permit no invented dollar figures. Sec.1 gives all three outcome statements: the agency-brain quote, the Fallon trigger blocking Whitney's sales/marketing time, and the unanswered Aug 11 ROI question — "That unanswered question is this deal." @21:20 Whitney: "we need more leads. We need more sales... if we're not marketing actively, that's not going to happen."
- **Risk if filled naively** — There is no revenue evidence of any kind for this engagement, so every card here would be fabricated. The specific trap is that SOURCES sec.4 does contain real dollar figures — WIA's published prices for Google Search Accelerator, Meta Ads Accelerator, the bundle, Elevate and LeadLock. Those are what WIA charges clients today, not new revenue this blueprint creates; pasting them into these cards would misrepresent existing revenue as incremental. Leaving the E2M cards in place is worse still: it pitches GBP, Semrush and chatbot services to an agency that runs Google Ads, Meta Ads and GHL.

#### Impact closing line — single centred sentence, reads `documentMeta.phaseOneImpact` with a hardcoded fallback

- **Sample showed** — "Phase 1 targets approximately 80 recovered hours per month." The E2M document-metadata object does NOT define `phaseOneImpact` — this string is the component's own default and prints unconditionally.
- **WIA content** — Set `phaseOneImpact` explicitly to: "Phase 1 covers approximately 12 verified hrs/month, plus the daily email drafting load that carries no figure."
- **Why** — Phase 1 initiatives in sec.6 that trace to a quantified audit row: OP-01 (R5, 2.0), MK-01 (R6, 4.0), MP-02 (R11, 3.0), MP-01 (R13, 2.0), OP-03 (R15, ~1.1) = ~12.1 hrs/month. MP-03 carries R12's 6.0 hrs but sits in phase 2, so it is excluded. Phase 1 also contains CC-01, CC-02 and CC-03 against R4, which sec.2 records as unquantified — hence the second clause.
- **Risk if filled naively** — Silent fabrication with no edit required to trigger it. Because the WIA metadata object will almost certainly not define `phaseOneImpact` either, the page will print E2M's "approximately 80 recovered hours per month" to Whitney under a WIA masthead. This is the single most likely fabricated number to reach the client in this component group. It must be set explicitly, not omitted.

#### Controls section header — eyebrow, H2, and paragraph (all hardcoded in JSX)

- **Sample showed** — Eyebrow "Expert governance". H2 "Human-in-the-loop controls". Paragraph "Automation handles volume and scaffolding. E2M retains judgment, creative direction, and final approval for every client-facing output."
- **WIA content** — Eyebrow and H2 can stand. Paragraph: "Automation drafts and flags. Wedding Industry Ads keeps judgment and final approval on every client-facing output. No AI-generated content reaches a client without a named human sending it."
- **Why** — @14:15 Minu states the constraint: WIA make sure "there isn't any AI-generated content that's going to the clients directly. Everything is custom on every touchpoint." @18:30 Whitney on inbox drafting: "we would still want to be able to review it before anything goes out." @39:09: "making sure that the end output is good, and it's not negatively affecting the client experience in any way." Sec.4: co-founder Daniela is explicit that wedding-industry clients hire them for hand-holding.
- **Risk if filled naively** — The E2M sentence assigns final approval to E2M. For WIA that is factually wrong and commercially bad: it reads as the vendor holding the approval authority over Whitney's client relationships, in a section whose entire purpose is reassuring her that the human touch survives. "E2M retains creative direction" is doubly wrong given @19:40-21:00, where Whitney personally refines every reel script and records it herself.

#### Human-review gates grid — one card per entry of the gates array, each rendering `category`, initiative-id chips from `initiativeIds`, "Reviewer: {reviewer}", and `rule`

- **Sample showed** — Five cards: Brand Strategy outputs (BS-01…BS-07, Brand Strategy Lead); SEO content and copy (SEO-06, SEO Lead); Client communications (OPS-02, OPS-03, SL-04, "E2M team"); Review responses (OPS-01, OPS-03, "E2M team"); Lead generation and proposals (SL-02, SL-03, SL-05).
- **WIA content** — Seven cards covering all 22 initiative ids. (1) "Client-facing email" — CC-01, CC-02, CC-03, CC-04, CC-05, MK-03, ON-02 — reviewer "Whitney Hodges; Gisselle Jimenez drafts and pre-reviews" — rule: "Drafts stay in the Gmail drafts folder, marked with a symbol, until Whitney reviews and sends." (2) "Internal Slack and ClickUp posts" — OP-01, OP-02, MK-01 — reviewer "Gisselle Jimenez" — rule: "Gisselle reviews before anything posts to Slack or creates a task." (3) "Flag-only workflows" — MP-01, OP-03 — reviewer "Gisselle Jimenez and Whitney Hodges" — rule: "The system flags only. The human does the follow-up. No automated DM, email or invoice chase." (4) "Member portal posts" — MP-02, MP-03 — reviewer "Gisselle Jimenez" — rule: "Gisselle approves reminder and recap posts before they publish to the GHL Communities portal." (5) "Marketing content" — MC-01, MC-02, MC-03, MC-04 — reviewer "Whitney Hodges" — rule: "Whitney refines every script and records it herself." (6) "Onboarding execution" — ON-01, ON-03, MK-02 — reviewer "Gisselle Jimenez" — rule: "A human activates the draft and batch-approves the edited task list. Approval is terminal and the current build writes nothing to ClickUp." (7) "Platform" — PLATFORM-01 — reviewer "Whitney Hodges" — rule: "Every tab surfaces drafts and flags; nothing leaves the system without a named human approving it."
- **Why** — Sec.7 requires a named human reviewer on every initiative. Card 1: @30:51-31:18 drafts sit in the Gmail drafts folder and Gisselle marks the thread with a symbol when it is ready for Whitney to review and send; @18:30. Card 2: R5 "(Could send to Gisselle for review first)" and R6 "Y (Gisselle to review before sending to Slack)". Card 3: R13 "(Just needs to flag, we will manually follow up)" and R15 "Just flag to Gisselle/Whitney", reinforced by sec.7. Card 4: R11, R12, and @15:17 confirming the member portal is the GoHighLevel Communities feature. Card 5: @19:40-21:00 — Whitney refines the reel script and records the reel. Card 6: sec.4 — human activates, editable execution draft, batch approve, APPROVED is terminal, no ClickUp writes. Card 7: sec.7.
- **Risk if filled naively** — Three failures. First, "E2M team" as reviewer is wrong for every WIA gate — the reviewers are Whitney and Gisselle, and naming the vendor as approver of Whitney's client emails inverts the relationship she is buying protection for. Second, the chip renderer filters ids against the initiative registry and returns null when none match, so any id left as BS-01 or OPS-02 vanishes silently and the card renders with no coverage shown — check all 22 WIA ids appear across the arrays, since an initiative absent from every card has no visible gate despite sec.7 requiring one. Third, softening the flag-only rule is a substantive breach: R13 and R15 say flag only in the client's own words, and MP-01 touches members who have missed office hours — an automated DM or email there is precisely the client-relationship contact sec.4 forbids.

#### Operational guardrails — "Data Security" card (rules list)

- **Sample showed** — "Store no client credentials or sensitive business data beyond what the automation requires." / "Encrypt all API tokens." / "Use JWT authentication with session expiry for client portals." / "Follow SOC 2-aligned data handling practices."
- **WIA content** — Rules grounded in the WIA surface area: "Scope inbox access to what each automation reads; Gmail holds all inbound and outbound client communication." / "Send nothing from Whitney's account without her approval; drafts remain drafts." / "Use GHL webhooks rather than email parsing where the plan allows." / "Store no client credentials or sensitive business data beyond what the automation requires." Mark the JWT, encryption and SOC 2 lines as pending: they are E2M policy statements and none is in the WIA evidence — confirm with E2M before printing.
- **Why** — @18:30: the inbox "is basically where all client communication is coming in and going out from". @33:10-33:39: Gmail is effectively the CRM for client comms and syncs to GHL. @39:09 and sec.7: nothing goes out without review. Sec.4 and sec.7: WIA are on the top-tier GHL agency SaaS plan (Sept 2 call @13:21), so webhooks are available, not just email parsing.
- **Risk if filled naively** — The E2M rules are assertions about E2M's own build practices. Restating "SOC 2-aligned" and "JWT with session expiry for client portals" under a WIA blueprint makes a compliance and architecture claim that nothing in SOURCES supports, and "client portals" again implies a client-facing build that is not what this is. Conversely, dropping the section leaves the most sensitive fact unaddressed: this system reads the founder's inbox, which is the agency's entire client-communication record.

#### Operational guardrails — "Cost Controls" card (rules list)

- **Sample showed** — "Meter Claude API use per automation run." / "Estimate $1–$2 per full AI visibility scan." / "Budget $150–$400/month for the total automation stack, scaling with client volume." / "Set per-automation alerts for unusual usage."
- **WIA content** — "Meter Claude API use per automation run." / "Set per-automation alerts for unusual usage." / "Per-run and monthly cost ceilings: not separately quantified — to be agreed before build." Drop the two dollar lines entirely.
- **Why** — Sec.7 and sec.3: where a figure is not in evidence, write "Not separately quantified" and never invent precision. No run cost, stack budget or spend ceiling for WIA appears anywhere in SOURCES.
- **Risk if filled naively** — "$150–$400/month" and "$1–$2 per scan" are E2M's own numbers for a Semrush and GBP stack that WIA does not run. Printed under a WIA masthead they become an implied budget commitment Whitney can hold E2M to, derived from a completely different toolset. The "AI visibility scan" line also references an initiative that does not exist in the WIA blueprint.

#### Operational guardrails — "Rollback Policy" card (rules list)

- **Sample showed** — "Keep a manual fallback so a failed automation does not lose data or block work." / "Deploy and test every automation in staging before production."
- **WIA content** — Keep both rules and add two WIA-specific ones: "Every automated task keeps its manual path working; Gisselle must be able to complete the task by hand on any day the automation fails." / "For the onboarding build, batch approval is the terminal state and no writes reach ClickUp, so a failed run leaves ClickUp untouched."
- **Why** — @5:25-7:30: Gisselle attempted to automate the roll call and failed — "it got very very complicated... I got confused on how to do like the rows... wasn't able to figure out how we could best automate this" — and had the same outcome in ClickUp. Sec.4: the MVP notifies on a Command Center dashboard, a human activates, the execution draft is editable, batch approve is terminal, and there are NO ClickUp writes in this build.
- **Risk if filled naively** — The generic E2M rules are safe but say nothing to the one person who has already been burned by a half-built automation here. More importantly, if the rollback card is filled naively with claims about reverting ClickUp state, it contradicts sec.4 — the current build never writes to ClickUp, so there is nothing to revert, and asserting a rollback capability implies a write path that does not exist.

#### Operational guardrails — "Iteration Policy" card (rules list)

- **Sample showed** — "Deliver a functional MVP before adding all configuration options." / "Collect feedback from Brand Strategy Lead, Web Development Lead, and SEO Lead after two to four weeks." / "Apply feedback in the following sprint." / "Only release versions that provide immediate value."
- **WIA content** — "Deliver a functional MVP before adding all configuration options." / "Collect feedback from Whitney Hodges and Gisselle Jimenez after two to four weeks." / "Apply feedback in the following sprint." / "Budget enablement time in every release: Whitney has not used Claude before, so adoption is the constraint, not build." / "Keep added review load inside Gisselle's ~25 hrs/week cap."
- **Why** — Sec.0: Gisselle works ~25 hrs/week, about 108 hrs/month, as an EA via the Dot agency, and is Whitney's proxy. Sec.1: "AI literacy is near zero (Whitney has never used Claude). Adoption risk > build risk." @39:09: Whitney wants a process where the system learns from her sent output so drafts sound like her voice, which is an iteration loop, not a one-time build.
- **Risk if filled naively** — Naming three E2M leads leaves the WIA blueprint with no feedback owner and reads as copy-paste. Omitting the enablement and capacity lines is the substantive risk: sec.1 identifies adoption as the dominant risk in this deal, and every human-review gate in the section above adds review minutes to a contractor with a hard 25 hrs/week ceiling. A governance section that adds review burden without acknowledging the ceiling is internally inconsistent.

#### Implementation dependencies — section header and intro paragraph (hardcoded in JSX)

- **Sample showed** — Eyebrow "Deployment requirements". H2 "Implementation dependencies". Paragraph "API integrations are provisioned and tested by E2M. The one-time setup checklist below captures the templates and business inputs E2M provides to activate the blueprint."
- **WIA content** — Header stands. Paragraph: "E2M provisions and tests the integrations. The one-time setup checklist captures the templates, access and decisions Wedding Industry Ads must hand over before build starts."
- **Why** — Sec.0 separates the parties: WIA is the subject of the audit, E2M Solutions is the author. Sec.4: nobody at E2M has ever seen the ClickUp onboarding template; Whitney offered a walkthrough on the Sept 2 call at 19:59 and it never happened, so the onboarding flow is second-hand narration. @40:33: the next step named on the call was a "client requirements document" listing steps and accesses.
- **Risk if filled naively** — In the E2M sample, E2M is both author and subject, so "E2M provides" is unambiguous there and ambiguous here. Left as-is, the checklist reads as E2M's homework when in fact every item is blocked on Whitney or Gisselle — and the deal has already stalled on exactly this handover. Getting the provider attribution wrong turns the one section that could unblock the engagement into a list of things the client thinks are already handled.

#### Implementation dependencies — "API access" cards (`api` label, requiredBy chips, `action` text)

- **Sample showed** — Twelve cards: Semrush, Google Ads, Google Business Profile, Google Search Console, NiftyQuoter, Asana, Harvest, GHL, Google Drive, Google Sheets, Whisper, Yelp Fusion — each with an E2M-provisions action line.
- **WIA content** — Eleven cards for the WIA stack. "GHL API" — ON-01, MP-01, MP-02, MP-03, OP-03 — "E2M connects via GHL webhooks on WIA's top-tier agency SaaS plan; webhooks are available, not only email parsing." "Gmail API" — CC-01, CC-02, CC-03, CC-04, CC-05, ON-02, ON-03 — "WIA grants delegated access; Gmail is the record of client communication." "ClickUp API" — MK-01, OP-01, OP-02, ON-02 — "E2M connects; the ON-01 build performs no ClickUp writes." "Slack API" — OP-01, OP-02, MK-01 — "E2M provisions workspace access for digests and acknowledgement tracking." "Zoom API" — MK-02, ON-03, MC-01 — "E2M configures recording, transcript and summary retrieval." "Fathom" — MK-01, MK-03 — "E2M connects meeting transcripts and summaries." "Google Drive API" — MK-02, ON-03, CC-04 — "WIA authorizes Workspace access; E2M configures client-folder filing." "Google Sheets API" — MP-01 — "E2M reads the two roll-call sheets, Google Ads and Meta Ads." "Canva" — MP-03 — "E2M configures session banner generation." "Claude API" — CC-01, CC-02, MK-01, MK-03, MC-01, MC-02, MC-03, MC-04 — "E2M provisions; usage metered per run." "Dubsado" — ON-01 — "E2M observes signed and paid alerts; the GHL migration is in progress and only Foolproof Follow-Up Advantage has moved."
- **Why** — Stack list from sec.4. Webhook availability from sec.4 (Sept 2 call @13:21) and sec.7. Gmail as the communication record from @18:30 and @33:10-33:39. No-ClickUp-writes and the Dubsado migration state from sec.4 (Sept 2 @23:29 and @24:09: "majority of our contracts are in Dubsado," and FFA has moved for just one offer). Two roll-call sheets from @11:06. Canva banner from R12. Fathom from R6.
- **Risk if filled naively** — Leaving E2M's list ships Semrush, Yelp Fusion, Asana, Harvest and NiftyQuoter into a blueprint for an agency that runs none of them, which visibly destroys credibility in the one section an engineer will work from. Two subtler traps. First, the Dubsado card must carry the migration caveat: sec.4 records that only one offer has moved to GHL, so an onboarding trigger that watches Dubsado alone will miss GHL-signed clients and vice versa. Second, these `api` label strings are display-only and do NOT feed the dependency graph — the graph reads each initiative's `tools[]`. Do not "harmonise" initiative tools to read "Gmail API" or "GHL API"; that breaks the shared-tool edges against every initiative using the canonical "Gmail" and "GHL".

#### Implementation dependencies — "One-time setup" cards (`item`, `provider` badge, requiredBy chips)

- **Sample showed** — Nine items, all provided by E2M's own leads: brand brief Word template, discovery workbook base template, onboarding workflow guide, strategy document format, past strategy examples (3–5), MODx template structure, master job-list format, standard proposal packages and pricing, ICP training examples (5–10 clients).
- **WIA content** — Eight WIA-provided items. "ClickUp onboarding checklist template" — ON-01, ON-02 — Whitney Hodges. "Gmail starring and label definitions" — CC-01, CC-03 — Gisselle Jimenez / Whitney Hodges. "Sent-email samples in Whitney's voice" — CC-02 — Whitney Hodges. "Post-meeting email templates from Google Drive" — CC-04 — Gisselle Jimenez. "Roll-call sheet structure for both office hours" — MP-01 — Gisselle Jimenez. "Canva session banner template" — MP-03 — Gisselle Jimenez. "Dubsado contract inventory and GHL migration status" — ON-01 — Whitney Hodges. "Client requirements document listing steps and accesses" — all initiatives — Whitney Hodges.
- **Why** — Item 1: sec.4 — nobody at E2M has ever seen the ClickUp onboarding template; the Sept 2 @19:59 walkthrough never happened. Item 2: @27:00-29:56 describes the full starring system and the "waiting" tag; note alongside it that @39:09 records Whitney as "NOT TIED TO THE LABELING SYSTEM at all", so it may be replaced rather than reproduced. Item 3: @39:09 — she wants drafts that cover the bulk of what she wants to say, learning from her sent output, so it "sounds like it's in my voice". Item 4: R7 names Drive templates. Item 5: @11:06 — two sheets with members, consecutive misses, last attended, and the 2-week and 4-week flags. Item 6: R12. Item 7: sec.4. Item 8: @40:33 names the client requirements document as the next step.
- **Risk if filled naively** — The provider badge is the load-bearing field: if it keeps saying "Brand Strategy Lead" or is naively filled with "E2M Solutions", the client leaves the review believing E2M already holds these assets, and the ClickUp template — the single overdue blocker on the one initiative already in build — stays unrequested for another cycle. Second risk: writing the Gmail starring item as a spec to be reproduced. It is an input for a redesign, not a requirement to preserve; @39:09 explicitly opens the labeling system to change, and building the current seven-symbol scheme into the automation would harden a process the founder has already offered to abandon.

#### Activation section — H2 and intro paragraph (hardcoded in JSX)

- **Sample showed** — H2 "Ready for activation?". Paragraph "The blueprint defines 28 prioritized automations across brand strategy, SEO, web development, sales, and operations. These five actions capture the templates, validation, and business inputs E2M provides — E2M handles API integration and technical feasibility separately."
- **WIA content** — H2 stands. Paragraph: "The blueprint defines 22 initiatives across client communications, onboarding, meetings, operations, member portal, marketing and the platform capstone. One is already in build. These five actions capture the templates, access and decisions Wedding Industry Ads provides; E2M handles integration and technical feasibility separately. Fulfillment work is not yet audited and is scoped in a later pass."
- **Why** — Sec.6 lists exactly 22 initiatives and the seven department names. Sec.4: the Client Onboarding MVP (ON-01) is already in build and demoing at this review. Sec.5 and @22:05-22:38: Minu split the engagement into internal efficiency and fulfillment, Aug 26 covered efficiency only, and fulfillment was explicitly deferred to later weeks.
- **Risk if filled naively** — "28 automations across brand strategy, SEO, web development" is a straightforward count-and-scope error that a client will spot immediately. The subtler risk is the reverse: correcting the count to 22 while staying silent on fulfillment lets the blueprint read as a complete picture of the agency, when four whole categories of work — creative briefs, ad copy, landing page builds and QA, and campaign management by Carmen and Jacqueline — were never looked at. Sec.5 requires that gap be stated, not left as an inference.

#### Activation section — five numbered next-step cards (`owner` heading, `action` body; initiative ids in the body auto-render as chips)

- **Sample showed** — Five cards owned by SEO Lead, Brand Strategy Lead, Web Development Lead, Sales Lead, and "Whole team" — e.g. "Review the 28-automation blueprint and confirm which initiatives to activate first."
- **WIA content** — (1) Whitney Hodges — "Walk E2M through the ClickUp onboarding template. Offered on the Sept 2 call and still outstanding; ON-01 is built on second-hand narration until then." (2) Whitney Hodges — "Answer the question left open on Aug 11: how much time back in three months, and what share of the work can be automated." (3) Gisselle Jimenez — "Hand over the two roll-call sheets, the starring and label definitions, and the post-meeting email templates." (4) Whitney Hodges and Minu Bhatt — "Schedule the fulfillment audit. Creative briefs, ad copy, landing pages and campaign management have not been audited." (5) Minu Bhatt and Jainil — "Produce the client requirements document listing steps and accesses."
- **Why** — Card 1: sec.4 — nobody at E2M has seen the ClickUp onboarding template, the walkthrough offered at Sept 2 @19:59 never happened, and the onboarding flow is second-hand narration. Card 2: sec.1 — the Aug 11 discovery question "how much time back in 3 months / what % can actually be automated?" was never answered, and "That unanswered question is this deal." Card 3: @11:06, @27:00-29:56, R7. Card 4: sec.5 and @16:43, where Whitney names creative briefs, first drafts of copy, first drafts of landing pages and landing-page QA as her fulfillment asks; @22:05-22:38 defers all of it. Card 5: @40:33. Owners from sec.0.
- **Risk if filled naively** — E2M's role names produce five cards no one at WIA owns, so nothing moves. Filling them naively with generic asks ("review the blueprint", "confirm priorities") wastes the highest-leverage real estate in the document: the two things that actually block this engagement are the unseen ClickUp template and the unanswered ROI question, and both are Whitney's. Note the action text auto-links any valid initiative id it contains, so writing ON-01 in card 1 renders a live chip; writing a non-existent id renders as plain text and looks like a typo.

**Warnings raised for this group**

- phaseOneImpact is the highest-risk field in this group. The Impact section's closing line reads documentMeta.phaseOneImpact but the E2M metadata object never defines it, so the component's hardcoded fallback prints instead: 'Phase 1 targets approximately 80 recovered hours per month.' If the WIA metadata object also omits the key, that fabricated E2M number renders under the WIA masthead with no edit and no error. Set it explicitly.
- Most of the visible prose in this group is hardcoded in the JSX, not in the data file. Editing only the data objects leaves E2M's words on screen. The literals to change: the three portal feature bullets ('Secure, authenticated client access' / '100% E2M branded experience' / 'Human-reviewed insights and recommendations'); the three portal dependency rows (Integration layer / Platform foundation / Activation requirements) and the 'White-label' spec row ('100% branded as E2M and maintained by E2M Solutions.'); the Impact header block ('Strategic value' / 'Quantifiable impact' / 'E2M can recover capacity across every department while opening productized, recurring revenue streams.'); the Controls header block ('Expert governance' / 'Human-in-the-loop controls' / 'Automation handles volume and scaffolding. E2M retains judgment...'); the guardrails header ('Risk mitigation' / 'Operational guardrails' / 'Security, spend, recoverability...'); the Implementation dependencies intro; and the Activation intro paragraph.
- The Impact 'hours recovered' card builds its detail line from a hardcoded sentence frame: '{currentManualHours} manual hours/month to {recoverableHours} recoverable | {reduction} reduction'. Honest qualifier text does not fit it — a value of 'Not separately quantified' renders as 'Not separately quantified manual hours/month to Not separately quantified recoverable'. The frame itself must be edited for WIA, or the section must not use this card type. Do not solve this by inventing numbers that fit the frame.
- No hours exist for anyone except Gisselle Jimenez (SOURCES sec.5). Every hours figure in the Impact section must be labelled with her name. Nothing in this group may render a team-wide total, a per-department team, or a percentage reduction — no recoverable-hours estimate exists anywhere in evidence, so every '% reduction' value would be fabricated.
- No revenue, pricing, per-run cost or monthly budget figure exists for this engagement. Three components invite one: the Impact revenue cards, PLATFORM-01's revenue/revenueModel and the portal 'Pricing' spec row, and the Cost Controls guardrail. The specific trap is that SOURCES sec.4 does contain real dollar figures — WIA's published prices for the Accelerators, the bundle, Elevate and LeadLock. Those are existing client prices, not value created by this blueprint; do not move them into any of these fields.
- The portal is internal, not client-facing. WIA already runs a client-facing member portal inside GoHighLevel Communities (@15:17) and already sells a white-labeled GHL product (LeadLock). Any surviving reference to 'client access', 'white-label' or 'per client' pricing in the Portal section creates a product that collides with two things WIA already has, and contradicts the sec.4 non-negotiable that client relationship contact stays human.
- Initiative-id chips are filtered against the initiative registry and render nothing when no id matches. Leftover E2M ids (BS-01, OPS-02, SEO-06, SL-04) disappear silently rather than erroring, so a review-gate card or dependency card can ship looking coverage-complete while showing none. Cross-check that all 22 WIA ids appear across the human-review gates arrays — sec.7 requires every initiative to have a named reviewer, and an id absent from every card has no visible gate.
- The 'Module activation pipeline' list highlights a module only when its status string matches /poc|live|active/i. ON-01 is already in build and must read as delivered (sec.4), so a literal status of 'In build' renders grey and reads as not-started. Use 'Active build' — honest and matched. Do not use 'Live': the build stops at batch approval with a toast and performs no ClickUp writes.
- Supply np.rollout as an array of {name, description} objects. If it is left as a comma-string the renderer splits on ', then ' and invents its own labels ('Foundation launch', 'Expansion phase 1'), so the three named phases from sec.6 — Stop the Leaks, Free the Founder, The Agency Brain — never appear in the Portal section.
- The 'API access' card labels ('Gmail API', 'GHL API') are display-only and do not feed the dependency graph — the graph draws edges from each initiative's tools[] array. Do not harmonise initiative tools[] to match these labels. Keep the canonical strings exactly: GHL, Gmail, ClickUp, Slack, Zoom, Fathom, Google Drive, Google Sheets, Canva, Claude API, Dubsado. Note the audit sheet spells GHL as 'Highlevel' in R11–R15; that spelling must not reach tools[].
- The Data Security guardrail's JWT, token-encryption and SOC 2 lines are E2M assertions about E2M's own practice. Nothing in SOURCES establishes any of them for the WIA build. They are not facts to restate — confirm them against E2M's actual policy before printing, or replace them with the rules that are grounded (inbox access scoping, no sends without approval, GHL webhooks over email parsing).
- Fulfillment work was never audited and must appear as an explicit gap, not as empty departments and not as invented initiatives (sec.5). This affects the Impact scroller — which needs a 'not audited' card covering creative briefs, ad copy, landing page builds and QA, and Carmen's and Jacqueline's campaign work — and the Activation intro. Do not let the blueprint read as a complete picture of the agency.
- 'Sara' and 'James' appear in rows 2-3 of the task audit sheet but are E2M's own example rows (row 2 col M: 'These are just an example tasks'). They are not WIA staff. They must not appear as owners, reviewers, providers or card labels anywhere in this group.
- Every human-review gate added here consumes Gisselle's time, and she is capped at ~25 hrs/week (~108 hrs/month) as an EA via the Dot agency. The Iteration Policy card should acknowledge this ceiling; a governance model that adds unbounded review load to a capped contractor is internally inconsistent with the section it sits in.
- MP-01 and OP-03 are flag-only in the client's own words (R13: 'Just needs to flag, we will manually follow up'; R15: 'Just flag to Gisselle/Whitney'). The review-gate card for them must not be softened into 'human approves the outgoing message' — there is no outgoing message. MP-01 in particular touches members who have missed office hours, and automating that contact is exactly what sec.4 forbids.
- Adjacent to this group and easy to miss: the footer prints documentMeta.client, version, date, classification and sourceBasis. client must become 'Wedding Industry Ads, LLC' while preparedBy stays 'E2M Solutions' — the sample uses 'E2M' for both because E2M was its own audit subject.

---

## 3. Known gaps (internal record)

Recorded here for the E2M team. Per the client decision of 9 September, the
deliverable does **not** call any of these out on the page — no statement that
fulfillment work is pending, deferred or unaudited appears anywhere in the HTML.

- **Only one role was audited.** All 12 usable rows are Gisselle's. No hours exist for
  anyone else, so no team-wide total is claimed anywhere.
- **Six of twelve audited rows carry no monthly total**, including R4 (email filing and
  drafting) which is the highest-priority item in the sheet. ~18 hrs/month is what the
  arithmetic actually supports; 45–70 is a labelled estimate.
- **Fulfillment work was never audited** — creative briefs, ad copy, landing page builds
  and QA, and the office hours Carmen and Jacqueline run. Deferred by design on 26 August
  (@22:05). Whitney raised all four herself at @16:43, so it may come up in the room; the
  blueprint does not pre-empt it. Removed from the page on 9 September at the client's
  direction — see `editorial.py`, which strips it on every rebuild.
- **Nobody at E2M has seen the ClickUp onboarding template.** The onboarding flow is
  second-hand narration. It is the first activation asset requested.
- **The 2 September transcript was not supplied to this build.** Only facts already
  recovered in earlier sessions were used from it.

## 4. Verification

- 20 data regions replaced by located byte-range, not hand-edited.
- Pre-rendered DOM stripped (2.49 MB): the Chrome "Save Page As" export carried every
  string twice, so patching the data alone would have changed nothing on screen.
- Validated: 22/22 matrix entries reconcile to 22 initiatives, no dangling initiative id in
  any phase, review gate, portal module or activation row, and zero surviving references to
  E2M's own staff roles, products or stack.
- Rendered and measured in-browser: 16 sections, 22 graph nodes, ApexCharts live, no
  console errors, no horizontal overflow.

Two rendering defects were found by measuring the live DOM and fixed:

1. The department hour fields are interpolated into a sentence
   (`{manual} manual hours/month to {recoverable} recoverable`). The authored provenance
   strings ran 100–229 chars and destroyed the grammar. Shortened to slot size with compact
   source tags (`11 hrs/month (R11+R12+R13)`); full provenance kept in each initiative.
2. Three places in the compiled JSX key off the sample's department ids. `Vy{}` holds the
   graph's seed positions and `Hl.find(id==="web-development")` drives the department
   spotlight — both were rebound, which fixed a stat rendering as an empty " recoverable"
   and a graph layout that had lost its seeds.

## 5. Open items before the review

- Confirm the office-hours and monthly-session volume with Gisselle. The audit sheet's
  12/month and the session cadence described on the call have not been reconciled.
- Measure R4. It is the largest unknown in the hours picture and the one number Whitney is
  most likely to ask about.
- Confirm the delivery date in the eyebrow (currently SEPTEMBER 2026).