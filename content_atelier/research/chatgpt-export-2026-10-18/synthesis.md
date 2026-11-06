# Whitney Hodges' ChatGPT export: synthesis for Content Atelier

**Date:** 18 October 2026. **Inputs:**
- twelve chunk reports with 430 exemplars;
- two attachment reports;
- section 7 of the Content Quality Analysis;
- the knowledge base as loaded (`backend/knowledge_base/`, 01 to 05);
- section 4.3 of the implementation plan.

**Citations** use the chunk report name (for example `A-social-3`), with a conversation file and date where they matter.

**Companion files:**
- `kb-candidates/` holds eleven draft knowledge-base documents and an exemplar bank of 60 entries.
- `data/pack_rules.md` and `data/pack_exemplars.jsonl` are the test pack.

**Bottom line.** Whitney's ChatGPT produced good WIA content for four reasons:
1. She, or a team member, pasted in the context: offers, approved sibling pieces, client facts and her own drafts.
2. She started from a real WIA asset and asked what it showed about how WIA works.
3. She corrected positioning and accuracy line by line.
4. She shipped her own wording.

ChatGPT itself contributed weak first drafts, stale memory and several fabrications. Content Atelier can beat it by storing what she pasted, in dated and checked form, and by making "what this shows about WIA" a structural requirement rather than a hope.

---

## 1. What the export really contains

### 1.1 Counts

| Item | Count |
|---|---|
| Conversations (11 Jun 2025 to 14 Oct 2026) | 349, with 4,766 user turns |
| WIA conversations analysed in twelve chunks | 309, with 3,895 user turns |
| Conversations excluded as personal or unrelated (home decor and similar) | 40 |
| Extracted document attachments | 70 (a further 247 are referenced but absent) |
| Library entries (`library_files.json`) | 336, of which 320 are present as `.dat` files; 174 texts extracted |
| Exemplars extracted | 430: 112 approved finals, 104 of her drafts, 64 preference pairs, 55 rejected AI drafts, 28 accepted hooks, 67 feedback statements |

| Chunk | Conversations | User turns | Period | Content |
|---|---|---|---|---|
| A-social-1, 2, 3 | 27, 14, 16 | 316, 300, 196 | Jun 2025 to Oct 2026 | WIA's own social content |
| B-strategy-1, 2, 3 | 18, 29, 20 | 326, 276, 262 | Jun 2025 to Oct 2026 | Offers, positioning, voice, case studies |
| C-email-1, 2 | 27, 13 | 304, 293 | Jun 2025 to Oct 2026 | Launches and list email |
| D-delivery-1, 2 | 37, 44 | 428, 372 | Jun 2025 to Oct 2026 | Client delivery, process, playbooks |
| E-sales-1 | 63 | 383 | Jun 2025 to 14 Oct 2026 | Sales correspondence, operations, the developer's 13 Oct sessions |
| F-megaemail-1 | 1 | 439 | 25 Aug to 13 Oct 2026 | "General Email Drafts", typed by Gisselle |

### 1.2 Who typed

**This is a shared team tool, not Whitney's private notebook.** Counting only conversations typed wholly or mainly by someone else, about 45 conversations and at least about 790 of the 3,895 WIA user turns (about 20%) are not Whitney's. Mixed conversations raise the share further.

| Operator | Where | Evidence |
|---|---|---|
| **Gisselle Jiménez** (operations, client communications) | F-megaemail-1 (439 turns); about 27 per-client project chats in D-delivery-2 (164 turns); two C-email-2 conversations (Accelerator application emails, 49 turns; VAULT sequence); B-strategy-3 (31 Aug, 11 Sep) | "ive asked whitney"; relays labelled "Whitney's final version"; Whitney's speech mislabelled in transcripts |
| **An unnamed team member** ("T") | A-social-3: the week of 27 Jul, the 5 Aug script, 28 Aug podcast mining, 23 Sep captions | Opens "Based on the founder's voice guide, create an instagram caption…"; refers to "the script video Whitney recorded" |
| Team members in 2025 | B-strategy-1 (three June client chats); D-delivery-1 (a designer, two chats) | Lowercase, client-creative requests |
| **The developer** | E-sales-1, 13 and 14 Oct 2026 (Whitney typed only 6acd92cc and af07ed5d) | Produced `handbook_v2` and the Week 2 simulation |
| Daniela (drafts pasted in) | C-email-1; B-strategy-1 | "Drafted by Daniela, not Whitney" |

**Whose rules are whose**

- **Whitney's:**
  - positioning (ads agency, growth-stage audience, never disparage referrals or SEO, thought leadership, offer scope, LeadLock kept separate from WIA);
  - accuracy (no fabrication; say when something can't be read; source statistics; real anecdotes; verbatim video);
  - process (refine, don't replace);
  - the em-dash ban (from 26 Dec 2025);
  - the problem-swap hook ban;
  - one hook per format;
  - a CTA that fits its channel.
- **The team's:**
  - most of the "it's not X, it's Y" bans (13 of about 17 events);
  - "Not because X, but because Y";
  - "NO STACCATO FRAGMENTS" and the buzzword list (a pasted rule set, 23 Sep 2026);
  - "Dont give me options";
  - client-email house rules (no "xx", bold only action items, always the complete email).
- **Both:** em dashes, brevity, and "sounds AI".

Section 7.3 of the analysis presents team rules as Whitney's.

**The two sometimes disagree.** On 1 Oct 2026 Gisselle pushed "we need to make our clients fully supported" for a client who had switched off Google Ads. Whitney sent a two-line reply with no push (F-megaemail-1).

### 1.3 Custom GPTs, projects and files

| Container | Conversations | What it is |
|---|---|---|
| "Whitney's AI Assistant" (`g-68504dcd…`) | 148 | Main WIA GPT from 16 Jun 2025; its knowledge included the Q2 2025 Investment Guide (B-strategy-1). Instructions not exported |
| "[WIA]" (`g-6960547a…`) | 39 | Marketing GPT, Jan to Sep 2026 (B-strategy-2) |
| Ads-strategy GPT; home-interior GPT | 12; 7 | Client creative (partly team-typed); personal |
| No GPT | 115 | Includes the chat that invented the most prices (B-strategy-1, 68e9b0e0) |
| Projects | 8, 8, 4, 3 and two small | Per-client copy for three venue clients, the team "Playbooks" project (attachments) |
| "Whitney 2.0" and "Whitney's Writing Assistant" | n/a | A voice GPT (B-strategy-2); email-voice instructions pasted in full, 31 Aug 2026 (B-strategy-3; E-sales-1) |

**Library and attachments** (attachments):
- **The "Founder Voice Knowledge Base" PDF.** It is not a knowledge base. It is a corpus of 4 Reels and 17 list emails, uploaded on 8 Jul 2026 as a chat attachment, from which ChatGPT wrote Voice Guide v2.0 (our KB 02).
- **WIA's method documents:** two versions of the Messaging & Positioning Questionnaire; the Client Marketing Profile master template; the UVP workshop decks and presenter document; the Strategy & Budget templates; the Meta Ads Accelerator timeline; the creative approval form; a VAULT lesson on Meta ad leads.
- **The Google, Meta and Landing Page playbooks**, generated by ChatGPT on 25 Aug 2026 from WIA's trainings.
- Benchmark trainings; giveaway assets for 2025 and 2026; client call transcripts.
- The developer's published-content log.
- **Sensitive material:** a credit-card statement and eight lead forms.

### 1.4 What her ChatGPT had that our knowledge base lacks

1. **Dated offer facts:** prices, inclusions, status, capacity, retired names, and who does what. KB 05 has eleven undated lines and no prices.
2. **WIA's methods:** how WIA works with clients, as documents. KB 03 only names them.
3. **The evidence behind the voice guide** (the corpus) and roughly 110 approved finals with their siblings, so the system can see what has already been said.
4. **Client results with their framing and permission context.**
5. **Audience language from DMs, applications, emails and her sales-call notes.**
6. **Her edits.** She edited in ChatGPT's canvas ("Made some edits. Thoughts?" 11 times in A-social-3 and 14 in B-strategy-3), so the diffs are invisible even in the export.
7. **Memory and custom-GPT instructions.** Not exported, and as section 6 shows, not trustworthy.

---

## 2. How WIA actually makes content

| # | Practice | Evidence | New or in s7 |
|---|---|---|---|
| 1 | **Start from one real asset.** In 25 content conversations (A-social-1): published pieces 8, operational moments 6, offer assets 4, borrowed formats 5, cultural wrappers 4. In 2026 the sources widened to recorded founder conversations, VAULT trainings taught that morning, client check-ins, sales-call notes, podcasts and her own settled emails | A-social-1, 2, 3; B-strategy-3 | In s7.2; counts and 2026 sources **new** |
| 2 | **Weekly plan.** Three posts in the week of 27 Jul 2026: "2 clips without CTA and the thirds case study clip with CTA", covers planned as a set, the case-study Reel plus a matching email on Friday. In practice, one list email a week (Tuesday performs best) plus two to four Instagram pieces. An April 2026 target of daily TikTok, Instagram and Threads posts was never met | A-social-3, 6a68eccd; A-social-2; C-email-1; C-email-2 | Partly in s7.2 (which says Whitney planned it; the chat was team-operated); volume **new** |
| 3 | **Reuse only if a piece performed.** "They did well" turned the 31 Jul Reel and email into the next week's carousel; a July 2025 carousel with "a good amount of profile visits" was remade; last year's audit campaign was refreshed | A-social-3, 6a721147; A-social-2; A-social-3, 6ac3c3eb | **New** |
| 4 | **A hook per format.** Reel, caption, carousel and email each get their own hook and job ("reel = story, email = reflective, carousel = perspective shift"). The caption never repeats the on-screen text. Sibling pieces are "aligned without being redundant" | A-social-1 (11-18); A-social-3 (08-04, 08-05, 10-01); B-strategy-3 (06-04) | Caption versus Reel in s7.3; generalised **new** |
| 5 | **How CTA posts are chosen.** Not every post sells. The CTA follows the channel (DM keyword on Instagram; reply in email; none on Threads), the funnel stage (DM "ADS", "ELEVATE", "Accelerators") and the offer's capacity. Pricing stays gated. A lower-barrier reply beats asking readers to pick an offer | A-social-2; A-social-3; B-strategy-3; D-delivery-2 (06-10) | **New** |
| 6 | **Emails stand alone.** The list includes leads from Google and ChatGPT who never see Instagram, so there are no Instagram references; evergreen emails also join the nurture sequence. Drafts carry date, time, segment, subject and preview | A-social-2 (Email A); A-social-3 (08-04); C-email-1 | **New** |
| 7 | **Video comes from WIA's own recordings, cut verbatim.** "I'm not going to re-record… It is what it is." Exact start and end lines; captions match the clip; longer clips preferred | A-social-2, 69c954cf; A-social-3, 6a68eccd | **New** |
| 8 | **Campaign sequences.** Threads post, then carousel, email and Reel (Oct to Nov 2025); the GSA launch (tease, launch day 6am, sales page, info session); Reel, then caption, email, carousel and offer caption (May 2026); email first, then three Reels (Sep 2026); graphic, then Reel, then carousel. Each offer has an evergreen Story Highlight pre-sell funnel ending in "DM us to apply" | A-social-1; B-strategy-2; A-social-3; C-email-2 | "Small campaign" in s7.2; sequences **new** |
| 9 | **Threads is the test bed**: short takes posted first and expanded weeks later | A-social-1 | **New** |
| 10 | **She benchmarks against approved work** ("on par with (not a copy of)") and checks every piece against the posts beside it | A-social-2; B-strategy-3 | **New** |
| 11 | **Operations become content and training the same week.** WIA's cold Meta leads became a member training; a student's DM became a VAULT workshop; a UVP training became an email and three Reels | B-strategy-1 (68e50a38); E-sales-1; A-social-3 | Partly in s7.2 |

Her 22 Jan 2026 request is the Content Atelier brief in her own words: content "that isn't purely educational but ties into how we serve clients and presents us as the solution". She rejected the first plan because it led with "problems that LeadLock solves, not that the Accelerator Bundle solves" (C-email-1).

---

## 3. The correction catalogue

Counts are distinct correction events summed across the chunk reports, and are approximate. "Ban" means reject or rewrite. "Flag" means warn, because she enforces the rule by judgement or her own approved copy breaks it. Full origins, quotes and sources are in `kb-candidates/rejection-rules.md`.

### 3.1 The fifteen that matter most

| # | Rule (generalised) | Category | Count | Author | First to last | Scope | Ban or flag |
|---|---|---|---|---|---|---|---|
| 1 | The piece must show what WIA's work demonstrates; interpret, don't repeat | Positioning | ≈6 | Whitney (one relayed) | 2026-01-22 to 2026-10-05 | angle | Ban (no WIA contribution) |
| 2 | Speak to established, growth-stage owners; never desperation, struggle or "lack mindset" | Audience | ≈36 | Whitney | 2025-09-24 to 2026-10-01 | angle | Ban |
| 3 | Never fabricate testimonials, quotes, anecdotes, footage or results | Accuracy | ≈18 | Whitney | 2025-10-05 to 2026-10-05 | all | Ban |
| 4 | Work only from supplied material; say when a link, file or video can't be read | Accuracy | ≈21 | Whitney | 2025-09-08 to 2026-01-04 | all | Ban |
| 5 | Offer facts current and dated; exact scope (LeadLock does no contracts; automation is not AI conversation; no waitlist application) | Accuracy | ≈63 | Whitney (team repeats) | 2025-06-19 to 2026-09-17 | all | Ban |
| 6 | WIA is an ads agency; the Accelerators are a done-for-you launch plus guided support, not a course or full management | Positioning | ≈44 | Whitney | 2025-06-19 to 2026-10-05 | all | Ban |
| 7 | Never disparage referrals, SEO, organic, Instagram or single-platform advertising | Positioning | ≈11 | Whitney | 2025-08-13 to 2026-05-11 | all | Ban |
| 8 | Possibility, not pain; never frame ads or WIA's offers as frustrating or risky | Positioning | ≈28 | Whitney, Gisselle | 2025-09-23 to 2026-09-29 | angle | Ban (negative framing); flag (pain-led openings) |
| 9 | Thought-leadership depth; don't re-teach basics | Audience | ≈26 | Whitney | 2025-11-10 to 2026-04-01 | angle | Flag |
| 10 | Specific, concrete and wedding-industry specific; no vague or generic lines | Voice and style | ≈60 | Whitney | 2025-09-10 to 2026-10-05 | all | Flag |
| 11 | Refine, don't replace; keep her wording, length and locked lines | Process | ≈52 explicit | Whitney | 2025-10-07 to 2026-09-22 | all | Ban (edit scope) |
| 12 | Client stories exact, caveated, anonymised, owned; proof shows capability, not a promise | Accuracy | ≈24 | Whitney | 2025-11-24 to 2026-09-23 | all | Ban |
| 13 | No em dashes | Voice and style | ≈26 | Both | **2025-12-26** to 2026-10-09 | all | Ban from 26 Dec 2025 |
| 14 | Never the "you don't have an X problem, you have a Y problem" hook | Voice and style | ≈6 | Whitney | 2025-12-31 (flag), **2026-04-30** (ban), 2026-08-04 ("never suggest it again") | all | Ban from 30 Apr 2026 |
| 15 | One hook per format; sibling pieces repeat ideas, not language; CTA fits channel; emails stand alone | Format | ≈38 | Whitney | 2025-09-03 to 2026-10-05 | brief | Ban (identical hooks, DM in email); flag otherwise |

### 3.2 The rest

| Rule | Category | Count | Author | First to last | Scope | Ban or flag |
|---|---|---|---|---|---|---|
| Keep the door open to buyers burned by DIY or agencies | Audience | 2 | W | 2026-02-03 to 04-14 | angle | Flag |
| Model the audience's real belief and language | Audience | ≈13 | W | 2025-08-12 to 2026-05-11 | angle | Flag |
| Copy fits every offer it names; don't centre one component | Positioning | ≈14 | W | 2025-12-30 to 2026-10-01 | angle | Flag |
| LeadLock never undercuts WIA's lead generation | Positioning | ≈7 | W | 2025-11-20 to 2026-06-16 | all | Ban |
| No prerequisites before working with WIA | Positioning | ≈5 | W | 2026-06-17 to 09-15 | angle | Ban |
| Own WIA's results; not an anomaly | Positioning | ≈6 | W | 2026-06-17 to 09-16 | angle | Flag |
| Authority without defensiveness; not "pick me"; don't spotlight unasked limits | Voice | ≈19 | W | 2025-10-02 to 2026-09-22 | all | Flag |
| Education stays unsalesy; cold to sold | Positioning | ≈19 | W, G | 2025-08-13 to 2026-09-08 | brief | Flag |
| Write for the audience's temperature | Audience | ≈4 | W | 2026-01-20 to 01-30 | brief | Flag |
| Prices out of public copy | Accuracy | 3 | W | 2025-09-24 to 12-27 | brief | Ban |
| Source every statistic | Accuracy | ≈8 | W | 2025-09-09 to 12-27 | all | Ban |
| Platform and technical accuracy | Accuracy | ≈14 | W | 2025-08-12 to 2026-01-03 | all | Ban |
| Real scarcity; no invented deadlines | Accuracy | 1+ | W | 2025-12-27 | brief | Ban |
| Don't overstate maturity or popularity | Accuracy | ≈6 | W | 2025-11-20 to 2026-02-16 | all | Ban |
| Never imply events that didn't happen | Accuracy | 1 | W | 2026-10-01 | all | Ban |
| Promise nothing WIA can't guarantee | Accuracy | ≈8 | W, G | 2025-12-22 to 2026-09-23 | all | Ban |
| WIA's own figures only as approved | Accuracy | 2 | W | 2025-08-12 | all | Ban |
| Phrasing fits the date; reusable pieces evergreen | Accuracy | ≈9 | W | 2025-09-23 to 2026-01-30 | brief | Flag |
| "It's not X, it's Y" / "the goal isn't X" | Voice | ≈17 | Mostly team | 2025-12-31 to 2026-09-23 | all | Flag |
| "Not because X, but because Y" | Voice | 5 | Team | 2026-07-28 to 08-05 | all | Flag |
| Staccato stacks, punchy one-liner chains | Voice | 2 | Team, W | 2026-09-15 to 09-23 | all | Flag |
| Stock AI phrasing ("That's why we created", "Here's the truth") | Voice | ≈54 events | Both | 2025-12-09 to 2026-10-06 | all | Flag |
| Precise words and logic | Voice | ≈24 | W | 2025-11-17 to 2026-06-21 | all | Flag |
| Brevity; refine without lengthening | Voice | ≈42 | Both | 2025-06-18 to 2026-10-06 | all | Flag |
| No redundancy inside a piece | Voice | ≈23 | Both | 2025-12-27 to 2026-10-05 | all | Flag |
| Pronouns and sign-offs follow the speaker and the CTA; names alphabetical | Voice | ≈11 | W | 2025-09-02 to 2026-08-04 | brief | Flag |
| Calm, warm, confident; no hustle guilt | Voice | ≈23 | Both | 2025-12-23 to 2026-10-13 | all | Flag |
| Minimal emojis, no hashtags | Voice | 3 | Both | 2025-11-26 to 2026-10-13 | brief | Flag |
| Contractions; flowing paragraphs | Voice | ≈3 | W | 2026-01-30 to 04-29 | brief | Flag |
| Carousels with substance on every slide | Format | 5 | W | 2025-12-26 to 2026-04-01 | brief | Flag |
| Fit platform length | Format | 4 | W | 2025-09-30 to 2026-05-04 | brief | Flag |
| Time-bound offers never on the asset | Format | 2 | W | 2025-09-24 to 11-18 | brief | Flag |
| Savannah's caption framework | Format | ≈8 | W | 2026-06-25 to 10-01 | brief | Flag |
| Recorded video used as said | Accuracy | ≈5 | W | 2026-03-25 to 07-28 | brief | Ban |
| Strategy before copy; background is not copy | Process | ≈24 | W | 2025-10-03 to 2026-09-22 | all | Flag |
| Build piece by piece and lock | Process | ≈8 | W | 2025-11-18 to 2026-08-04 | brief | Flag |
| Return the complete, editable piece | Process | ≈39 | Both | 2026-03-28 to 10-13 | brief | Flag |
| Honest critique, no flattery | Process | ≈11 | W | 2025-08-13 to 2026-01-22 | all | Flag |
| Check the record and the source before conceding or claiming | Process | ≈5 | W | 2026-08-18 to 10-13 | all | Flag |

**How the rules move over time:**
- **The em-dash ban starts on 26 Dec 2025** (six times within an hour), yet her own sends of 20 and 26 Jan 2026 and the approved GSA Highlight still contain em dashes.
- **The problem-swap hook** appears in her own Threads post (Aug 2025) and her April 2026 copy ("Many wedding pros don't have a lead problem. They have a lead management problem."). She banned it on 30 Apr and made it absolute on 4 Aug 2026.
- **"Not X, it's Y" appears in her approved copy** ("It's not that you aren't getting inquiries. It's that you're not getting in front of enough of the right people", May 2026; "The difference wasn't working harder… It was…", June 2026). KB 02 even lists "The goal isn't…" as on-voice.
- **The SEO-respect rule postdates** August 2025 copy she approved that disparaged SEO.
- **Words on KB 02's avoid list appear in her copy:** "Magic" and "skyrocket" (2025), and "You're leaving money on the table." (7 Apr 2026).

---

## 4. Facts

### 4.1 Offers timeline (summary; full dated table in `kb-candidates/offer-facts.md`)

**Internal** marks prices quoted privately or set in contracts. Never use them in public copy.

| Offer | Timeline |
|---|---|
| **Google** | VIP Day (2024 to 2025), rebranded Google Search Accelerator in Oct 2025 ($1,497 founding rate, 10 spots; contract $1,597, internal). Black Friday $1,497, normally $1,697 (public). $1,697 from Dec 2025 (gated); 2 × $848.50 from Aug 2026; "a hybrid program… done-for-you, done-with-you, and DIY elements". Support: four months (Jan 2026) or three (May 2026), a conflict |
| **Meta** | "Meta Ads Immersive Experience" at $1,997 (Jun 2025); renamed Meta Ads Accelerator (Dec 2025), access by reply only; gated page at $1,997 (Apr 2026); Learn, Launch, then 3 months, with the client creating the ads (Oct 2026) |
| **Bundle** | $3,197 (Dec 2025, gated); giveaway "$3,694 value" (Feb 2026, public); 2 × $1,598.50 (Aug 2026) |
| **ELEVATE** | Named Sep 2025; retainer quotes $1,397 to $1,497/month (internal); "two spots left" (Nov 2025); "we no longer have capacity" and a waitlist (4 Jan 2026); requires LeadLock (May to Jun 2026); "one opening for ELEVATE in July" (public); $1,997 onboarding + $1,497/month + at least $1,000 spend (Aug 2026, internal); "ads management only" exceptions (Sep 2026) |
| **LeadLock** | "our white label version of GHL" (Oct 2025); dropped from WIA's sales process; brands separated (Jan 2026); "LeadLock is the platform. The Foolproof Follow-Up Advantage is the system." (Apr 2026) |
| **Audit, VAULT** | Annual giveaway of 5 audits, normally $297 (public). VAULT office hours stated as bi-monthly, fortnightly and weekly at different dates; workshops twice monthly, then monthly (Jul 2026) |

### 4.2 Roster corrections (full list in `kb-candidates/roster-corrections.md`)

- **Whitney** signs as "Co-founder", not "founder". Since mid-August 2026 she runs every ELEVATE strategy call.
- **Daniela's surname** is Justus.
- **Jacqueline Hood** (Meta; "By far our most experienced Meta Ads Manager (even more than me)") is missing.
- **Tina Henares** (LeadLock pages and nurture) and **Ivy Ayala** (ad creative) are missing.
- **Fallon Looney** left in mid-August 2026.
- **Carmen** is Google lead and manages Meta for some clients; she no longer runs client calls.
- **Gisselle Jiménez** handles operations and client communications.
- **Viktor** is an AI agent, not a person.
- **Christina Hill** (left Feb 2026) and **Yulia** (left Dec 2025) are former team.
- **ChatGPT invented** "Matt" and "Daniela Martinez".
- **Savannah Jordan** is an external consultant, not WIA staff.

### 4.3 Named frameworks and methods (full list in `kb-candidates/process-catalogue.md`)

- **Client methods:** the Messaging & Positioning Interview ("100 vendors" test); the Client Marketing Profile with four evidence labels; the UVP method; the Google + Meta Strategy & Budget; the lead definition; creative approval; reporting with video walkthroughs; scope discipline; the Accelerator journey; the nine-step application reply.
- **Teaching frameworks:** Five Foundations; her top five Google Ads mistakes; why campaigns fall flat; why Meta ad leads behave differently; the post-call sequence; Savannah's caption framework (mandatory from 25 Jun 2026).

### 4.4 Results

- **Public results** (published by WIA, client unnamed): the venue's 59 leads and 3,667% ROAS; the band and DJ client's 17 to 90 events; the Accelerator venue's $22K to about $70K (name never to be used); the planner who doubled; the planner who stopped posting for 10 weeks; a photographer at 15X; WIA's own results; the Q4 2025 seasonality proof.
- **Private results:** twelve client results appear only in reports, emails and Slack. `kb-candidates/case-study-method.md` lists them as client type, metric type and "permission needed", without figures.
- **Consent:** the GSA contract (Oct 2025) lets WIA share members' testimonials and results unless they object.

### 4.5 Ideal-client signals and audience language (full detail in `kb-candidates/audience-language.md`)

**Signals.**
- "Making sales, already seeing growth, putting real effort into organic marketing, knows they need to spend money to make money."
- Strong brand: they know the ideal client, have a designer, a conversion website, inquiries in DMs and organic Google leads.
- Tried DIY or an agency and got stuck.
- Budget of $500 a month per platform.
- In the Americas, or targeting US couples.
- **Anti-signals:** "wondering where their next lead is coming from"; poor websites; wanting done-for-you Meta only.

**Prospects' words.**
- "always leave more confused than when we started";
- "cannot pinpoint one booked wedding";
- "every decision depends on another one";
- "The hamster wheel";
- "I have no idea what I'm reading";
- "I don't want this all to be on me".

**Caveat.** The May 2026 survey's options were written with ChatGPT. Her 23 Apr 2026 sales-call notes are the reliable voice of the customer.

### 4.6 What performed and what didn't

| Performed | Didn't |
|---|---|
| 24 Sep 2025 "reality check" email: replies, one promo spot sold, a contract sent (A-social-1) | GSA promo week: 0 discovery calls, about 12 info-session sign-ups (C-email-1) |
| "Want the replay? Just reply": "That got me some replies" (C-email-1) | Summits "doesn't result in any new clients" (C-email-1, Dec 2025) |
| "Send it" Venue Masterclass email: "a great response" (C-email-1) | Speed to Lead nurture click-through by email: 34.58%, 3.39%, 1.75%, 0%, 0% (C-email-1) |
| An Investment Guide caption "always did a great job of driving investment guide downloads" (B-strategy-2) | Re-engagement to 279 people: 0 demos; 73 guide opt-ins: 0 demos (C-email-1, C-email-2) |
| WIA's copy sent under a summit host's name booked LeadLock demos; the same copy to WIA's list booked none (C-email-2) | Visibility Blueprint email: 2 opt-ins; carousel: 1 profile visit (B-strategy-3) |
| "Modern couples demand instant responses" carousel ad drove guide opt-ins and at least one sale (C-email-2) | Repeated short conversation clips: "we lost a lot of followers" (B-strategy-2, Apr 2026) |
| 31 Jul 2026 case-study Reel and email: "They did well" (A-social-3) | Live workshops with no attendees (Jan and Sep 2026) |
| New welcome DM: multi-message replies within 48 hours (E-sales-1) | "Our content isn't actually converting at this point. Not enough people are seeing it" (B-strategy-3, 8 Jul 2026) |

The lesson: sender, list, timing and a named offer mattered more than the prose. The system needs per-asset outcomes, which the export almost never records.

---

## 5. Contradictions with today's knowledge base

| Knowledge base says | Export says | Date and source |
|---|---|---|
| **KB 02 is presented as "Founder Voice Guide v2.0" with status "supplied"** | ChatGPT drafted it on 8 Jul 2026 from her corpus of 4 Reels and 17 emails ("Defining Brand Voice", 2026-07-07_6a4d2bd9). She said she was "unclear on what my voice is" and did not want to "act like I know better than [Savannah]". Its last section is ChatGPT addressing her | B-strategy-3; attachments |
| KB 02 hook: "One of our clients went from 17 weddings to 90." | "the DJ side of the biz has gone from 17 events last year to 90 this year"; published copy says "17 events". Only her non-verbatim Reel summary says "weddings" | 2026-06-25; B-strategy-3; attachments V02 |
| KB 02 belief: "Marketing isn't about getting attention. It's about shaping decisions." | "But the goal kind of is more attention..." | 2026-06-04; B-strategy-3 |
| KB 02 belief: "Buyers don't need more information. They need more confidence." | "People want more information before committing to a conversation." | 2025; attachments E02 |
| KB 02 avoid list: "Magic", "Skyrocket"; off-voice "You're leaving money on the table." | "strategy becomes magic" (E08); "skyrocketed" (E02); "you're leaving bookings on the table" (Nov 2025); "You're leaving money on the table." (her session copy) | 2025 to 7 Apr 2026; C-email-1, C-email-2 |
| KB 02 on-voice: "The goal isn't…"; rhythm "Long explanation. Short emphasis."; uses em dashes ("with her—not being lectured") | Team: "Example: The goal isn't to replace referrals" (banned); "NO STACCATO FRAGMENTS"; Whitney: "I hate em dashes" | 2026-07-28, 09-23; 2026-01-29 |
| KB 02 has no one-to-one register | A separate email-voice specification exists ("Whitney's Writing Assistant"), and about 29 relayed one-to-one finals show none of KB 02's signature phrases | 2026-08-31; F-megaemail-1 |
| KB 01: "Referrals and organic are a beautiful ceiling, and unfortunately you've already hit that." | "You can build an incredible business solely based on referrals. I don't want to discount that." | 2025-12-26; A-social-1 |
| KB 01: "Posting organic content every single day is not an actual marketing strategy." | "do I think spending time… on organic social media is a waste of time? Absolutely not!"; that framing "often appeals to people who don't really like social media" | 2025-12-10, 12-30; A-social-1, A-social-2 |
| KB 01 Convert: "Feast or famine inquiries"; KB 03: "Inconsistent inquiries" | "I don't know that I want to lean into the pain of inconsistent inquiries. IMO that speaks to desperate wedding pros." | 2026-04-02; B-strategy-2 |
| KB 01: "you can't DIY ads… you absolutely can"; KB 03 lists "You shouldn't DIY your ads" | "DIYing isn't going to cut it either"; "You'll be doing the work, but you won't be left to figure it out on your own" | 2026-01-04, 2026-08-20; B-strategy-1, 3 |
| KB 01: "TikTok daily… Instagram daily" | No TikTok in 2025; "TikTok should be purely educational attraction content"; "Were doing 3 posts total" | 2026-03-28, 07-28; A-social-2, 3 |
| KB 01: "Elevate & Accelerators builds the funnel and foundations first" | "We don't require that they do a funnel build with us first" (Nov 2025); Accelerators: "We don't build the foundation… They build it" | 2025-11-14, 2026-04-13; D-delivery-1, A-social-2 |
| KB 01: "all-female team in our 20s and 30s" | "All-female, Millennial + Gen Z team" | 2026-06-23; B-strategy-3 |
| KB 03: prospects who ask for examples "don't move forward" | A prospect pressed for data and then signed | Sep to Oct 2026; E-sales-1 |
| KB 03: "USUALLY not beginner" | GSA "a better fit for those who haven't run Google Ads before" | 2025-10-04; B-strategy-1 |
| KB 04 roster and KB 05 offers | See 4.1 and 4.2: wrong titles, missing staff, an ex-member listed; no prices, dates or capacity; "Waitlist only"; LeadLock "one component of ELEVATE"; audit "with Carmen" only; weekly office hours | Jan to Oct 2026 |

---

## 6. Risks

1. **ChatGPT's memory is stale and wrong.** Asked on 12 May 2026 (the "VISTARA" prompt, B-strategy-2) to dump what it knew, ChatGPT:
   - listed retired offers as current and was unsure whether VIP Days were still sold;
   - omitted Daniela, named staff with unverified roles and gave a full-service price that matched no quote;
   - allowed the problem-swap hook "unless heavily nuanced";
   - filled "case studies" with private client escalations.

   She never replied. Pulling context from her ChatGPT would import these errors.
2. **It fabricated testimonials and results.**
   - **October 2025:** attributed testimonials and a client result ("booked three weddings within a few weeks"), later called "truthful summaries" (B-strategy-1).
   - **Invented prices and offers:** an introductory rate, a $3,682 value stack and "just 5 spots" (68e9b0e0, outside the GPT); "100+ Wedding Pros Served"; "Millions in Ad Spend Managed".
   - **Invented people:** "Matt"; "Daniela Martinez".
   - **Invented quotes:** "I just need someone to tell me what buttons to click".
   - **Shipped errors:** "onboarding won't reopen until January"; a "395%" that was 295%.

   The ICP analysis and survey options from the same period may carry composites.
3. **It claimed to read what it had not:** videos, Drive links, Dubsado and screenshot text. This drew about 18 corrections ("I'm really losing confidence in you"; B-strategy-1; D-delivery-1).
4. **Approved lines were silently reverted.**
   - The "final" GSA Highlight reintroduced em dashes, dropped the locked line "Google Ads work regardless of SEO" and dropped "on repeat". She approved it without noticing (A-social-1, 27 Dec 2025).
   - Other cases: a locked subject line changed (C-email-1); "Why'd you backtrack?" (D-delivery-1); suggestions announced but not implemented (B-strategy-3).
5. **Bans are looser in practice** (section 3). A rigid lint would reject her own best copy. Team rules recorded as hers would harden further.
6. **Two operators.** Unattributed verdicts would teach the team's style rules as Whitney's taste.
7. **Facts churn.** Two renames and three price points in about 90 days; ELEVATE's status flipped three times; one featured client's leads were slowing by October 2026.
8. **Privacy.** A credit-card statement (15 Sep 2026); HR details (a resignation, pay, contractor terms); WIA's revenue figures and targets; private client names attached to numbers, and a client in dispute; eight lead forms with contact details; candid internal remarks about a client; client ads used in training without explicit permission; Whitney's private doubts. None of this belongs in the knowledge base or in prompts.

---

## 7. Store from day 1, capture going forward, ignore

| Item | Knowledge-base key | Plan item |
|---|---|---|
| Dated correction catalogue with author, scope, ban or flag | `rejection_rules` (`kb-candidates/rejection-rules.md`) | E.B11; lint patterns E.B10 |
| Dated offers with a visibility flag; retired names | `offer_sheet`, replaced (`offer-facts.md`) | E.B11; confirm E.X2 |
| Roster with roles and invented names to block | `team_roster` (`roster-corrections.md`) | E.B11; E.X2; verifier E.B10 |
| Client journey and named methods, each with "what this shows" | `process_catalogue` (`process-catalogue.md`) | E.B11; E.B21 moves the process list out of the prompt |
| Voice corpus V01 to V06 and E01 to E17, era-tagged | `voice_knowledge_base` (attachments-voicekb Part A) | E.B11 |
| 60 curated exemplars with contrastive pairs | `exemplars` (`exemplar-bank.jsonl`) | E.B11; provenance E.B17 |
| Public results and permission list | `results_register` (`case-study-method.md`) | E.B11; E.X2 |
| Per-channel structure | `format_guide` (`format-guide.md`) | E.B15 |
| CTAs by channel and offer | `cta_catalogue` (`cta-catalogue.md`) | E.B15 |
| Published items and hooks | `recent_published` (`published-content-log.md`) | 3.B10 |
| Week and campaign structure | `content_plan` (`content-workflow.md`) | E.X1, E.X2; E.B21 (`week_summary`) |
| Ideal-client signals, prospects' words, objections | **new** `audience_language` | E.B11; E.B21 |
| Beliefs in her own words (replacing KB 02's model-written beliefs as the belief bank) | **new** `belief_statements` | E.B11; E.B21 |
| Evidence labels (Documented Fact, Voice of Customer, Strategic Interpretation, Needs Validation) | **new** claim-status vocabulary in the brief ledger | E.B15; E.B10 |
| Do-not-name and dispute list (internal only) | **new** `privacy_register` (not loaded into prompts; read by the verifier) | E.B10 |
| KB 02: strip ChatGPT's closing note, add era note, demote to "derived" | `founder_voice_guide` | E.B11 |
| Manifest: Savannah is an external consultant | manifest | E.B11 |

**Capture going forward:**
- **Gate decisions and her line edits as diffs**, with an **author field** (Whitney or a named relay), locked lines, the chosen option and a reason code (E.B20).
- **Founder seeds:** her drafts, recorded transcripts, VAULT trainings, sales-call notes, DM replies (E.B19).
- **What went live:** channel, date, hook, siblings, and per-asset outcomes such as replies, opt-ins, DMs, demos and sales (3.B10, plus a new `performance_log`).
- **Offer and capacity changes**, each with a `valid_from` date (E.B11).
- **New results with consent and an "as of" date** (`results_register`).
- **Expertise sources:** VAULT topics, office-hours recaps and monthly strategy-call recaps.

**Ignore:**
- generic ChatGPT frameworks and "why this works" commentary;
- AI-invented statistics, prices and lists;
- design, mockup, music and hashtag work;
- technical how-tos;
- HR and personal threads;
- the VISTARA memory dump, except as a warning;
- the simulation packs, except for evaluation;
- 2024 emails as voice models.

---

## 8. Implications

**What would most raise quality.** Make "what this shows about WIA" structural, and give the system the material her ChatGPT had. Every angle should name:
1. the scene from the source;
2. the WIA move in that scene (a step from `process_catalogue`, or a decision a team member made);
3. the belief it proves, quoted from `belief_statements`;
4. the audience belief it shifts, in `audience_language` terms.

An angle that cannot fill items 2 and 3 is an educational takeaway, which is exactly what drew the 1 out of 5. The export's best pieces were all of this shape: going dark on Instagram, the question asked at every onboarding, a training that "had nothing to do with running ads", a client who stopped posting for 10 weeks.

**Strategist prompt (E.B21).**
- Load `process_catalogue`, `belief_statements`, `audience_language`, the dated offers and `recent_published`.
- Rank by WIA contribution first.
- Apply the audience screen as a hard test: "would this speak to a desperate or struggling owner?"
- Give each angle a campaign plan: formats, one hook per format, which pieces carry a CTA, a standalone email, and the proposed order in the week.
- Treat prospect and member questions, applications and VAULT topics as first-class sources, not only call transcripts.
- Keep KB 02 as derived guidance below her corrections and her finals.

**Brief writer (E.B15).**
- Carry the offer fact and its visibility flag for every offer mention, and the CTA from `cta_catalogue` checked against capacity.
- Label every claim with the evidence labels. Take client results only from `results_register` with permission.
- Use a date-weighted exemplar set per format, normalised (no em dashes).
- When seeded with Whitney's draft, switch to refine mode: lock her lines, show a diff, and change only what is flagged.
- Run the final assembly through lint, so the GSA Highlight reversion can't recur.

**Verifier and lint (E.B10).**
- **Block:**
  - em dashes in new copy;
  - the problem-swap hook;
  - team names not on the roster;
  - prices or spot counts not marked public;
  - client names outside `results_register`;
  - "AI handles conversations" and done-for-you claims about the Accelerators;
  - "DM" in an email;
  - statistics without a source;
  - quotes not traceable to a span.
- **Warn:** contrast frequency, stacked fragments, stock phrases from the list, emojis and hashtags, length.
- **Test the lint on her own approved finals:** a ban should fire on them only where the rule postdates the piece.

**Gate screens (E.F1, E.F2).**
- Show the WIA move, the evidence spans, audience fit, offer status and prior coverage on each card.
- Use reason codes that match her categories (positioning, audience, accuracy, voice, format, edit scope).
- Record who decided (Whitney, or Gisselle relaying her).
- Keep review to one pass; she rejects "time-consuming back and forth".

**Evaluation.**
- Run the judge experiment with the condensed rules and exemplars (`data/pack_rules.md`, `data/pack_exemplars.jsonl`) against `t1_pairs`, and measure how often judges prefer her text.
- Add a false-positive test: no ban fires on her post-ban finals.
- Track her Gate 1 dispositions by reason code week on week.
- Score each brief for (a) a WIA contribution, (b) audience fit, (c) offer accuracy and (d) distinctiveness against `recent_published`.

---

## 9. Corrections to analysis section 7

| Section | Says | Correction |
|---|---|---|
| 7.1 | "The export contains no custom-GPT instructions, memory entries or project files." | 320 of 336 library files are present: playbooks, client profiles, UVP decks, trainings. GPT instructions and memory are absent, but the "Whitney's Writing Assistant" email instructions are pasted in full (31 Aug and 2 Sep 2026) |
| 7.1 | "Several conversations are typed by team members" | About 45 conversations, including the largest (439 turns), and at least about 20% of WIA user turns. Many "her" corrections are Gisselle's or another team member's |
| 7.1, 7.2 | About 45 conversations reviewed | 309 WIA conversations now analysed, with counts |
| 7.2 | "She plans a week as a sequence. On 27 July…" | The 27 July week was team-operated, with Whitney's edits; its rule was "2 clips without CTA" plus a case study with a CTA, and the operator was asked to "use marketing discernment". The voice guide was pasted by the team member |
| 7.3 #1 | No em dashes, no "it's not this, it's that", no staccato fragments, no "delve, tapestry", attributed to Whitney | The em-dash ban dates from 26 Dec 2025. The contrast, staccato and buzzword bans are mostly the team's (Jul to Sep 2026), and Whitney's approved copy uses contrasts. The problem-swap hook appears in her own April 2026 copy and is banned from 30 Apr 2026. Treat these as dated, and mostly as flags |
| 7.3 #4 | "We aren't conducting market research for our elevate clients yet." | True on 10 Jun 2026; by September a post-booking survey was being built for one client |
| 7.3 #4 | "LeadLock is just one element of ELEVATE." | True as positioning; ELEVATE required LeadLock from about May 2026, with "ads management only" exceptions from September |
| 7.3 | List of corrections | Omits the most frequent: refine, don't replace (about 52); offer accuracy (about 63); fabrication and "tell me if you can't read it" (about 39) |
| 7.5 | "Project knowledge files: the voice guide and a 'Founder Voice knowledge base'" | Both were chat attachments. The "knowledge base" is the corpus of 4 Reels and 17 emails behind KB 02, which ChatGPT wrote on 8 Jul 2026 |
| 7.5 | "Memory of sixteen months of drafts and corrections" as an advantage | Memory was stale and partly wrong (VISTARA, 12 May 2026). Its real advantage was pasted context and her edits |
| 7.7 | Transfer what makes it good into a versioned knowledge base | Confirmed. Add: never import ChatGPT memory, and confirm every derived document with WIA before it becomes trusted instruction |
