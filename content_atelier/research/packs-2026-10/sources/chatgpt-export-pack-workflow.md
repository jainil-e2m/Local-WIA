# What a weekly content pack was in WIA's ChatGPT workflow

**Prepared:** 24 October 2026, for the owner's pack-scope decision (D43, Phase NP).
**Source:** Whitney Hodges' ChatGPT export (`gpt_export/conversations-000..003.json`, 349 conversations, 11 Jun 2025 to 14 Oct 2026). Read locally only; nothing from it was copied into a repository. No paid API calls.
**Read first, and extended rather than repeated:** `research/chatgpt-export-2026-10-18/` (README, synthesis, `data/pack_rules.md`, `kb-candidates/content-workflow.md`, `format-guide.md`, `cta-catalogue.md`, `published-content-log.md`, `rejection-rules.md`), `research/week2-packs-rebuild-2026-10-21/notes/chatgpt_export_week2_findings.md`, and the loaded knowledge base (`backend/knowledge_base/08`, `09`, `10`, `14`, and the rulings R-9 and R-10 in `01`).

## How to read this

- **Markers.** **[EXISTING]** means the point is already in a research file or the knowledge base (the file is named). **[NEW]** means this pass found it. **[EXTENDS]** means an existing point with new evidence or a new consequence for packs.
- **Citations** give the conversation title, the date of the message (UTC) and the first 8 characters of the conversation id, for example *WIA Marketing week of 8.3.26, 2026-08-04, 6a721147*.
- **Quotes** are under 15 words. Most evidence is paraphrased.
- **Who typed.** Whitney typed most WIA marketing chats. Three of the four "week" chats were partly typed by an unnamed team member (marked **[T]**), and the 13 Oct chats by the developer. Whitney's canvas edits ("Made some edits. Thoughts?") are invisible in the export: only her ask and ChatGPT's echo survive.
- **Privacy.** Client names, private figures and internal prices are left out. Published case studies are named by their public description (the $22K-to-$70K Accelerator client; the 10-week planner client).
- **Method.** A local parser rebuilt every conversation from `parent` links. I identified 91 conversations that are WIA's or LeadLock's own marketing (not client delivery, sales or personal) and counted Whitney's requests by deliverable type. I then read in full the four conversations titled as weekly units, the March 2026 "Data Driven Decisions" campaign plan, the Savannah strategy chat, and the user turns of about 45 more content chats. I also checked the 13 October feedback-call transcript in `research/week2-packs-rebuild-2026-10-21/feedback-13-october/` where it speaks to packs.

---

## 0. Bottom line

1. **WIA's real "pack" was a small campaign around one anchor, assembled over one to three weeks, not a document produced in one go.** The four chats WIA itself titled as weeks ("Social Media Week of July 27", "Marketing week of 8.3.26", "Week of 8.17.26", "Week of 9.14.26") each produced one email plus two to four Instagram pieces (Reels with cover text and caption, a carousel with caption). Recording sat in the middle: script, then Whitney records, then the caption and cover are written **from the recorded transcript**. [NEW as a pack-stage requirement]
2. **In the most recent four months (July to October 2026) the pack had four piece types: Reel (cover text, script or clip, caption), carousel (slides, caption), list email (send header, subject, preview, body) and nothing else.** Stories and Threads requests stop after June and May 2026. TikTok was planned (March to May 2026) and then dropped by ruling R-10. [EXTENDS content-workflow, R-10]
3. **Brief contract v4 already carries almost everything WIA published.** The real gaps are process and week-level, not new asset types: a post-recording caption and cover pass; a week-level allocation (one email a week across all packs, two no-CTA pieces and one CTA piece, posting order); an exact cut sheet when the source is existing footage; and one consolidated, unabbreviated publishing sheet. [NEW]
4. **Whitney once asked ChatGPT for the maximal pack**: one day-by-day plan with every Reel cut, cover, caption, three TikToks a day with hooks and captions, daily Story sequences and the Tuesday email, then Threads and a carousel (Data Driven Decisions, 28 to 29 Mar 2026, 69c5403c). The short repeated clips that came out of that approach coincided with follower loss; she later rejected repeated clips as off-brand. A pack should not maximise volume. [EXTENDS synthesis 4.6]
5. **Production is human and light.** Whitney records and posts; she planned to cut clips herself, found editing many clips "overwhelming", and preferred to record new scripts. Carousels are designed in Canva from copy (in October 2026 Whitney wanted copy only, which Gisselle pastes into Canva). Covers are minimal, editorial images with a one- or two-line title. Email goes out through LeadLock (GoHighLevel). No scheduling tool appears for WIA's own content. [NEW in detail]

---

## 1. The pack's pieces (Question 1)

### 1.1 Frequency across WIA's own-marketing chats

Counts are over the 91 own-marketing conversations, counting only Whitney's or the team's messages that ask for or discuss the item. They are approximate (a keyword can appear in passing).

| Deliverable | Conversations | Messages | Months seen | Last seen |
|---|---|---|---|---|
| List email (any) | 57 | 258 | 15 | Oct 2026 |
| Email subject or preview line | 32 | 65 | 12 | Jul 2026 |
| Instagram caption | 45 | 140 | 14 | Oct 2026 |
| Reel (any) | 48 | 126 | 14 | Oct 2026 |
| Script or transcript for a Reel | 35 | 68 | 14 | Oct 2026 |
| Carousel | 38 | 91 | 11 | Oct 2026 |
| Reel cover text | 21 | 35 | 11 | Oct 2026 |
| Stories (sequence or set) | 29 | 53 | 13 | Jun 2026 as a request |
| Story Highlights (evergreen funnel) | 16 | 25 | 9 | Apr 2026 |
| Threads | 14 | 35 | 9 | May 2026 |
| TikTok | 10 | 28 | 8 | Jul 2026 (plan only) |
| Clips cut from existing footage | 9 | 34 | 6 | Sep 2026 |
| B-roll Reel with on-screen hook | 9 | 10 | 4 | Jun 2026 |
| Graphic or GIF | 18 | 40 | 9 | Jun 2026 |
| Audio or music for a post | 8 | 10 | 6 | Feb 2026 |
| Landing, opt-in or sales page copy | 36 | 93 | 15 | Oct 2026 |
| Lead magnet or masterclass | 35 | 78 | 13 | Sep 2026 |
| Comment-keyword CTA | 2 | 2 | 2 | Oct 2026 |
| Organic piece reused as an ad | 8 | 11 | 7 | Jun 2026 |
| LinkedIn, blog, Facebook-specific, YouTube | 0 for WIA's own content | | | YouTube only as a podcast link (Dec 2025) |

### 1.2 Each deliverable: structure, length and whether it was used

| Deliverable | Typical structure and length | Used or published? | Marker |
|---|---|---|---|
| **List email** | Send header (DATE, SEND TIME, RECIPIENTS list name), SUBJECT, PREVIEW, "Hi {{contact.first_name}}," then short flowing paragraphs, one bold line, reply or link CTA, sign-off. 250 to 500 words. | Yes, about one a week; many confirmed sends | [EXISTING: format-guide; KB 09] |
| **Email P.S. line** | One line after the sign-off: a soft second CTA (book a call, check the guide, reply with your takeaway, share the giveaway). Seen in about eight of her email drafts and sequences, Jul 2025 to Feb 2026 (for example *Emily Foster Podcast Email, 2026-01-09, 69614c3b*; *2026 Planners Workshop Emails, 2026-01-26, 6977702e*), and once in a caption (*Ads Accelerator Caption, 2026-02-05, 698407f8*). Absent from the July to October 2026 finals. | Yes in 2025 to early 2026 | [NEW] |
| **Email link button** | A single arrow link line (for example "Explore the Ads Accelerators →") tracked through LeadLock (*Write Ad Caption, 2026-10-01, 6abeb98d*). | Yes (15 Sep 2026 send) | [NEW detail] |
| **Reel, new talking-head script** | Whitney to camera, 200 to 450 spoken words (1 to 3 minutes). Her own drafts carry Savannah beat labels (HOOK, PROBLEM/SYMPTOMS, MAIN POINT, TRANSFORMATION, SOLUTION/CTA) and sometimes an "On-screen CTA" line (*Workshop reel script, 2026-09-16, 6aaaba8c*). ChatGPT estimated her approved Taylor script at about 2.5 to 3 minutes (*Taylor - Wedding Marketing Masterclass, 2026-07-02, 6a46ad95*). | Yes; recorded Reels went out Jun, Jul, Aug, Sep 2026 | [EXTENDS format-guide] |
| **Reel from existing footage (clip)** | Exact start and end lines from a transcript of a podcast or a founders' conversation; no rewriting; prefer longer clips. Podcast clips end on the podcast link. | Yes (podcast clips Jul 2026; founders' clips Mar to May 2026) | [EXISTING: format-guide] |
| **B-roll Reel with on-screen text** | One strong text hook over brand b-roll; "the caption does the heavy lifting". | Yes (May, Jun 2026, including two trial Reels) | [EXISTING: format-guide] |
| **Voiceover Reel** | Brand b-roll with a recorded voiceover: the 2025 social media manager wrote voiceover scripts (*Google Ads Audit, 2025-09-09, 68befe84*); evergreen offer Reels started from earlier voiceovers (*Evergreen Reels Hooks, 2025-12-23, 694acab5*). Whitney later doubted voiceovers for Stories. | Yes in 2025; the evergreen GSA and Meta b-roll Reels were finalised Dec 2025 to Jan 2026 (whether the final cut kept a voiceover is not shown) | [NEW] |
| **Reel cover text** | A short title, often set as two lines, with an optional subheading (the $70K Reel: "Know What's Working" plus a guesswork-to-$70K subhead). Covers in one week are planned as a set and are written after the transcript exists. | Yes; chosen for every recorded Reel Jul to Oct 2026 | [EXTENDS format-guide] |
| **Reel caption** | Savannah's framework from 25 Jun 2026; 150 to 300 words; its own hook; CTA only on some; IG limit of 2,200 characters checked twice (*Meta Ads Reel Text Suggestions, 2025-12-26, 694ecc87*; *Ads Accelerator Caption, 2026-02-05, 698407f8*). | Yes | [EXISTING: format-guide; F08] |
| **Carousel slides** | 7 to 12 slides, real text on each, built slide by slide; final slide is a DM CTA; she asked whether IG still caps at 10 slides (*Accelerator Sales Page Optimization, 2026-05-01, 69c14c0f*). | Yes (Jan, Feb, Apr, Jun, Aug, Oct 2026) | [EXISTING: format-guide] |
| **Carousel caption** | Longer than the slides need; deepens rather than repeats; personal storytelling; sign-off follows the CTA. | Yes | [EXISTING] |
| **Stories sequence (in-week)** | 3 to 7 text frames that lead to the day's Reel, then the Reel shared to Stories; in March 2026 she noted current Stories carry a lot of text per frame (*Data Driven Decisions, 2026-03-28, 69c5403c*). Also a Story set the same day as a carousel (2026-04-08) and a Tuesday Story tease of a training (*[VAULT] Client Research for Marketing, 2026-06-08, 6a26e8bc*). | Yes in Sep 2025 to Jun 2026; no requests after June | [EXTENDS format-guide] |
| **Story Highlight funnel (evergreen)** | 30+ frames per offer, pinned; text animated in; she asked how many seconds a frame needs to be readable (*IG Funnel Design Collaboration, 2025-12-27, 694f3d51*). | Yes (GSA Dec 2025; Meta Apr 2026) | [EXISTING: format-guide] |
| **Threads post** | Under 500 characters, no CTA, a test bed. | Yes Aug 2025 to May 2026; none after | [EXISTING] |
| **TikTok cuts, hooks, captions** | Same clip split into three shorter videos, each with on-screen hook text and a one-line caption; links not clickable, bridge to Instagram. | Planned Mar to May 2026; posting not confirmed; out by ruling R-10 | [EXTENDS content-workflow] |
| **Graphic** | Event promo graphic at 1080 × 1350 (*Instagram Promo Graphic, 2026-06-18, 6a33f6dd*); podcast graphic; giveaway cover. Email graphics are rare at WIA. | Occasionally | [EXISTING for email; NEW for size] |
| **GIF in email** | Launch tease and Halloween emails in Oct 2025 (a movie-scream GIF chosen by Whitney, *Repurpose IG reel to email, 2025-10-31, 6902aa8a*). None after 2025. | Yes, 2025 only | [NEW] |
| **Audio or music** | She asked for audio suggestions for a carousel and a giveaway post and picked IG music herself; she asked whether ChatGPT knew trending audio (it did not). | Chosen by Whitney at posting | [NEW] |
| **DM keyword and comment keyword** | DM "ADS" (default from Aug 2026), "Accelerators", "ELEVATE", "Google"; comment "Google Ads Audit" in both giveaway years. No ManyChat or auto-DM tool named. | Yes | [EXISTING: cta-catalogue; comment keyword NEW] |
| **Organic piece reused as an ad** | A separate caption for running the full-length Reel as a cold-traffic ad (*Data Driven Decisions, 2026-04-09, 69c5403c*); carousels written evergreen so they can be pinned or run as ads; a carousel "ran as an ad" and drove guide opt-ins (*Summit Content Customization, 2026-04-23, 69d530e4*). | Yes, occasionally | [EXTENDS format-guide] |
| **Trial Reel variants** | Two b-roll Reels with different text hooks and the same caption, published as Instagram trial Reels (*[WIA] Wedding Marketing Visibility, 2026-06-05, 6a1efd89*). | Yes | [NEW] |
| **Campaign-only assets** | Landing pages, application questions, confirmation, approval and reminder emails, info-session invites, post-event surveys, lead magnets, summit host emails. These belong to offer launches and giveaways, not weekly angles. | Yes, per campaign | [EXISTING: content-workflow section 6] |
| **LinkedIn, blog, Facebook-specific posts, YouTube** | None for WIA. ChatGPT proposed a LinkedIn repurpose once (in a June 2026 "content OS" answer); Whitney never asked. Whitney told the development team on 13 Oct that more angles would raise posting on "Instagram and Facebook", which suggests Instagram posts also appear on Facebook, not separate Facebook copy. | No | [NEW] |

### 1.3 What the pieces looked like in the four "week" chats

| Week (as WIA titled it) | Pieces produced | Typed by | Evidence it went out |
|---|---|---|---|
| Social Media Week of July 27 (*2026-07-28, 6a68eccd*) | Three Reels: two podcast clips and one case-study talking head. For each, a cover title (with a subheading considered for the case study) and a caption. Plus the case-study email on Friday 31 Jul. | [T] on 28 Jul; Whitney on 29 Jul ("I made some edits to the caption for podcast clip 1") | Captions appear in the team's published list (*Caption strategy summary, 2026-09-23, 6ab41e90*); "They did well" for the Reel and email (*2026-08-04, 6a721147*) |
| Marketing week of 8.3.26 (*2026-08-04, 6a721147*) | A 9-slide carousel retelling the case study, built slide by slide; its caption; an email rewritten from the caption for people who missed last week's | Whitney | Caption in the team's published list; email confirmed in the published-content log |
| Marketing Week of 8.17.26 (*2026-08-05 to 08-18, 6a73993f*) | A Reel script (case study, Whitney records); an email; a 12-slide carousel; a carousel caption; a Reel caption written from her recorded transcript | [T] 5 Aug; Whitney 13 Aug ("Whitney here"); [T] 18 Aug | Captions in the team's published list (Aug 2026) |
| Marketing Week of 9.14.26 (*2026-09-15, 6aa98079*) and its follow-ons (*6aaaba8c, 6ab41e90, 6abeb98d, 6abeb5fb*) | Email first (sent); three Reel concepts, two scripts workshopped and recorded; captions and covers for both, written 23 Sep [T] and redone 1 Oct by Whitney from the recorded transcripts | Whitney and [T] | Email "went out recently" (1 Oct); captions approved as "good to go" (1 Oct) |

**What this shows [NEW]:** in WIA's own words, a "week" was **one email plus two or three Instagram pieces, all from one anchor**, with Reel covers and captions finished only after recording. None of the four weeks included Stories, Threads, TikTok, a graphic or audio notes.

---

## 2. Pack shape and cadence (Question 2)

### 2.1 Was there a weekly unit?

Yes, but it was a campaign unit, not a calendar slot. **[EXISTING: content-workflow sections 2 to 4]** already documents "one real asset, one campaign" and lists nine format orders. This pass adds the following.

- **The pack took one to three weeks of elapsed time [EXTENDS content-workflow 3].** The 10-week case study ran from the first script draft on 5 Aug to captions on 18 Aug; the UVP pieces from the email on 15 Sep to final captions on 1 Oct. In between, Whitney recorded.
- **The anchor was usually the email or the recorded Reel, never the carousel [NEW, from the chains].** Email first: UVP (15 Sep 2026), market research (10 Jun 2026), Google Ads Email A (Jan 2026 from the Stories funnel). Reel first: case study (31 Jul 2026), sales on autopilot (25 Jun 2026), points of entry (12 May 2026). The carousel was always a later retelling ("They did well. I'd like to create a carousel that tells the same story", 4 Aug 2026).
- **Each later piece is made from the approved earlier piece, not from the source [NEW].** She pasted the final email or caption and asked for the next format; when ChatGPT drifted back to the raw material or invented points, she pulled it back ("too many liberties... closer to the actual email", *[WIA] Marketing Assumptions vs Data, 2026-06-10, 6a296764*). For the reverse direction she asked why the final caption could not simply become the email (*[WIA] Wedding Ads Strategy, 2026-05-12, 6a026ad2*).

### 2.2 How many pieces per week, which days

| Source | What it says | Date | Status |
|---|---|---|---|
| Her own practice | About one list email a week, Tuesday preferred; two to four Instagram pieces a campaign week | 2025 to 2026 | [EXISTING: content-workflow 3; KB 14] |
| The 27 Jul team plan | Three posts; two without a CTA and the case-study clip with one | 2026-07-28, 6a68eccd | [EXISTING] |
| Her own weekly plan for a training | Tuesday: tease the training in Stories and record a face-to-camera Reel; Wednesday: a b-roll Reel; Thursday: a carousel | *[VAULT] Client Research for Marketing, 2026-06-08, 6a26e8bc* | [NEW] |
| Her aspiration, April 2026 | Three TikToks a day, one Instagram post plus a Story sequence a day, one Threads post a day | *4/15/26 Marketing Email Strategy, 2026-04-14, 69dec86e* | [EXISTING: content-workflow 3, as unmet] |
| Savannah's cadence (marketing consultant) | TikTok every weekday; Instagram every weekday: one Attract Reel repurposed from TikTok plus one Warm or Convert feed post (Warm Mon, Wed, Fri; Convert Tue, Thu), Stories doing the opposite of the feed | *[WLF] Content Strategy Execution, 2026-06-29, 6a3acdf8* | [EXISTING: KB 01, superseded by ruling R-10] |
| Whitney to the development team | Hopes for "three really strong angles per week" to raise posting volume; fewer is fine in light weeks; repeating a point after one to two months is fine | 13 Oct feedback call (not in the export) | [EXISTING in transcript; consequence NEW below] |
| Ruling R-10 (knowledge base) | One list email a week (Tuesday), three Instagram pieces (two without an offer CTA, one with), Threads optional, no TikTok | KB 01, 14 | [EXISTING] |

**Consequence for packs [NEW]:** three approved angles a week, each with a brief carrying an email, would produce three emails for a one-email week. The pack stage needs a week-level step that picks which pack's email is sent that Tuesday (the others can become a later week's email or a nurture-sequence email, which WIA already does: *IG Funnel Design Collaboration, 2025-12-27, 694f3d51*), and which three Instagram pieces go out, with the CTA split.

### 2.3 The maximal pack she once asked for

On 28 to 29 Mar 2026 (*Data Driven Decisions Video - IG Reel Strategy, 69c5403c*) Whitney asked ChatGPT to turn one recorded founders' conversation into a full week. Over 15 turns she demanded, and got, one document that she could follow day by day:

- per posting day (Mon, Tue, Thu, Sat): the Reel's theme, exact start and end lines, full clip transcript, cover text and caption;
- three TikToks a day, each with post time, exact cut, transcript, on-screen hook text and a one-line caption;
- a 6- or 7-frame Instagram Story sequence a day ending in the shared Reel;
- the Tuesday email (send time, subject, body);
- later: four Threads posts, a depth carousel, a Story set for the carousel day, and a separate cold-traffic ad caption for the full video.

Her process corrections on that plan are the clearest pack-format instructions in the export **[NEW]**:
- She wanted everything in one place, every day, with nothing summarised: she rejected "same as before", said checking back on previous versions was painful, and objected when captions and the email were abbreviated or silently changed (2026-03-28 and 03-29).
- She wanted cut points she could edit from, exact to the line.
- She rejected re-posting the same clip with different hooks as off-brand, and accepted splitting a 30-second clip into three shorter videos instead.

**What happened next [EXISTING: synthesis 4.6; EXTENDS]:** the short repeated conversation clips posted in April coincided with "we lost a lot of followers" (*[WIA] Organic vs Paid Strategy, 2026-05-02, 69f5361f*), and she said very short Reels were not what she saw working on Instagram. Already on 14 Apr she had said that editing so many clips felt overwhelming and that recording would be faster (*4/15/26 Marketing Email Strategy, 2026-04-14, 69dec86e*). From May 2026 the packs shrink back to the four piece types above.

### 2.4 Was there a calendar?

No persistent calendar appears. Day-by-day plans were asked for three times (28 to 29 Mar, 14 Apr and 8 Jun 2026) and always for one campaign. Posting decisions were relative ("a reel I'm going to post tomorrow", "since I just posted a carousel, can we do a reel instead?", *Summit Content Customization, 2026-04-22, 69d530e4*). **[NEW]**: format alternation was a live consideration; Instagram order "graphic, then Reel, then carousel" is **[EXISTING: KB 09]**.

---

## 3. Her instructions and corrections on pack-level output (Question 3)

### 3.1 Already captured (do not re-derive)

These are in `data/pack_rules.md`, `kb-candidates/rejection-rules.md` (F01 to F09, V and R rules) and KB 09. Listed so the pack stage reuses them:

- one hook per format; siblings repeat ideas, not language (F01, F02);
- carousels with real substance; no fluffy transition slide; build slide by slide and lock (F03; format-guide);
- fit platform length (F04); CTA fits channel and job, not every piece sells (F05);
- time-bound offers in the caption, never on the designed asset (F06); emails stand alone (F07);
- captions follow Savannah's framework (F08); copy before visuals (F09);
- refine, don't replace; return the complete piece (R rules);
- em dashes, the problem-swap hook, "it's not X, it's Y", staccato stacks, stock phrases (V rules; team-authored where marked);
- pronouns and sign-offs follow who speaks and who the CTA names (V11);
- client stories exact, with what a figure does and does not include (A08).

### 3.2 New or extended pack-level instructions

| # | Instruction (paraphrase, or short quote) | Evidence | Marker |
|---|---|---|---|
| P1 | **Write the Reel caption and cover from the recorded transcript, after recording, and keep the caption to what was actually said.** | The team asked ChatGPT to check the caption against the clip (*6a68eccd, 2026-07-28*); the 18 Aug caption request pastes Whitney's recorded transcript, which differs from the 13 Aug script (*6a73993f*); the 23 Sep and 1 Oct captions were written from transcripts that differ from the 16 Sep scripts (*6ab41e90; 6abeb98d*). ChatGPT itself retracted points "not in the clip". | [NEW] |
| P2 | **One consolidated plan, nothing abbreviated, nothing "as before".** | *69c5403c, 2026-03-28 to 03-29* (section 2.3). Related: she asked for compiled finals "based on all of my approvals" (*6a721147, 2026-08-04*) and for full previews of all slides. | [EXTENDS R "complete piece"] |
| P3 | **Vary the wording across a week's captions, especially CTAs and signature phrases.** | [T] flagged a repeated "send us a DM, we'd love to help" on the second caption (*6a68eccd, 2026-07-28*); [T] asked whether every caption ends the same way (*6ab41e90, 2026-09-23*). | [EXTENDS F02; week2 findings E.10] |
| P4 | **"We" when both co-founders speak on camera; "I" in Whitney's emails.** | Caption switched to "we" because both co-founders are in the clip (*6a68eccd, 2026-07-28*); carousel in "we" throughout, email CTA back to "I" and "me" (*6a721147, 2026-08-04*). | [EXTENDS V11] |
| P5 | **Scripts must sound spoken, not written.** She asked to make a workshopped script "more natural/conversational"; spell out "Unique Value Proposition" rather than "UVP"; the transformation is campaigns that convert, not clarity; own the results. | *Workshop reel script, 2026-09-16, 6aaaba8c*; 13 Oct call: scripts "a little less polished". | [EXTENDS KB 18 spoken voice] |
| P6 | **Covers: specific, not generic, not educational-sounding; often her own line.** She rejected "Build a Business You Control" as generic, questioned "How Couples Actually Choose", found ChatGPT's alternatives boring, then wrote "For a wedding business, every touchpoint matters more." (*6a68eccd, 2026-07-29*). For giveaway Reels she took ChatGPT's first option twice (*Revise Giveaway Caption, 2026-10-08, 6ac3c3eb*). | | [EXTENDS format-guide] |
| P7 | **A case-study pack leads with the feeling, carries the number in the subhead or later, and states what the number covers.** | Slide 1 starts with the doubt, not the $70K; she asked whether to say the $70K is only ad-attributable revenue (*6a721147, 2026-08-04*). | [EXTENDS A08] |
| P8 | **Sibling pieces in the same week must not share an opening; later pieces take a new door.** She refused the same hook for the carousel as the Reel and email, then approved a new one (*6a73993f, 2026-08-13*); for two Reels "in a similar vein" she wanted "aligned without being redundant" (*6abeb98d, 2026-10-01*). | | [EXISTING: F01; KB 09 "specificity outranks distinctness"] |
| P9 | **Stories: text-heavy frames that lead into the Reel, then the Reel itself; never a near copy of yesterday's.** | *69c5403c, 2026-03-28*; *[WIA] Repurposing for Stories & Threads, 2026-05-04 to 05-06, 69f9018e*. | [EXTENDS format-guide] |
| P10 | **Don't stack the same clip with new hooks; prefer fewer, complete thoughts.** | *69c5403c, 2026-03-29*; *69f5361f, 2026-05-02* (clips as incomplete thoughts; follower loss). | [EXTENDS format-guide] |
| P11 | **Alternate formats across consecutive posts.** | "since I just posted a carousel, can we do a reel instead?" (*69d530e4, 2026-04-22*). | [NEW] |
| P12 | **A separate caption when an organic piece runs as an ad; and a trial-Reel variant can share a caption.** | *69c5403c, 2026-04-09*; *6a1efd89, 2026-06-05*. | [NEW] |
| P13 | **CTA scope: by August 2026, prefer a CTA that fits whichever offer suits the reader ("DM us ADS", "explore our options"), not one offer, unless the piece is an offer piece.** | Carousel CTA broadened beyond the Accelerators (*6a721147, 2026-08-04*); she debated a generic "DM me ADS" over naming the Accelerators (*6aaaba8c, 2026-09-16*); caption should not be only about the Accelerators (*6abeb98d, 2026-10-01*); CTA covering both offers (*6a026ad2, 2026-05-13*). | [EXTENDS cta-catalogue] |
| P14 | **She edits in place and wants an editable surface.** She asked twice for copy "in a format I can edit right here" and for a doc or Google Doc of the final. | *6aa98079, 2026-09-15*; *6a46ad95, 2026-07-02*; *Evergreen Reels Hooks, 2025-12-27, 694acab5*; *UVP Workshop Planning Feedback, 2026-08-18, 6a7e2852*. | [EXTENDS synthesis 1.4] |
| P15 | **Honesty about events in pack copy.** No implied live attendance (*6abeb98d, 2026-10-01*); no "no pressure, no pitch" after naming an offer. | | [EXISTING: rejection rules; week2 findings E.13] |

### 3.3 Raw-to-final chains that define pack quality

| Chain | ChatGPT's draft | What Whitney changed | Final | Source |
|---|---|---|---|---|
| $70K carousel | A generic 9-slide outline | Wrote slides 1, 3, 4, 5 and 7 herself with her facts (the hand-holding detail; the doubt; "not even the point"); no fluffy slide; "we" throughout | 9 slides, posted | *6a721147, 2026-08-04* |
| $70K carousel caption | Reused the Reel's hook | Rejected the repeat; chose a new hook; edited in canvas | "You can't optimize what you can't measure." | *6a721147, 2026-08-04* |
| 10-week Reel | AI-phrase-heavy scripts ([T] flagged AI constructions in five messages) | Whitney chose the 10-weeks question as the hook and added that the client is a strong marketer | Recorded; differed again from the script | *6a73993f, 2026-08-05 to 08-18* |
| UVP Reel 1 | ChatGPT's 15 Sep script, brought by Whitney to workshop | She rewrote the transformation, asked for a more conversational version, insisted on owning results | Recorded differently again; caption written from the recording | *6aaaba8c, 2026-09-16*; *6ab41e90* |
| Podcast clip captions | 450 to 500 words with contrasts and "send us a DM" | [T] cut AI phrases; Whitney edited lines and rejected "Wedding businesses have months" as imprecise | Posted with podcast link CTA | *6a68eccd, 2026-07-28 to 07-29* |

**Pattern [NEW]:** in pack work, what shipped unedited from ChatGPT was mostly cover options and some captions; what Whitney always rewrote was the email subject, carousel slide 1, the Reel hook and any line carrying a fact. The pack stage should spend its effort on those five places.

---

## 4. Production-facing details (Question 4)

| Topic | What the export shows | Source | Marker |
|---|---|---|---|
| **Who films** | Whitney records talking-head Reels, sometimes with Daniela (founders' conversations, podcast style). She will not re-record raw footage. | *Reel Feedback and Edits, 2026-03-25, 69c3f6de*; *69c954cf* | [EXISTING] |
| **Who edits video** | In March 2026 Whitney planned to cut the clips herself and asked for exact trims ("I haven't edited the video down into individual reels yet"); in April she found editing many clips overwhelming and preferred recording. In Aug 2026 the team picked podcast sections to "modify in Descript". | *69c5403c, 2026-03-28*; *69dec86e, 2026-04-14*; *Generate Instagram Clips, 2026-08-28, 6a92168b* | [NEW] |
| **Transcripts** | ChatGPT could not watch video; every caption was written from a transcript the team pasted. | *6a68eccd*; *69c5403c*; *690295b8* | [EXISTING: synthesis 6.3] |
| **B-roll** | WIA has "plenty of brand photos and brand b-roll"; b-roll Reels carry one text hook. | *694f3d51, 2025-12-27* | [EXTENDS] |
| **Stage directions in scripts** | ChatGPT added camera, tone and on-screen notes often (about 55 "on-screen text" and 41 "visual" cues in its drafts). Whitney kept only light ones in her own scripts ("Lean in, relatable tone", "(pause)", "CUT TO FORMULAS", "On-screen CTA"). | *Email marketing spin-off, 2025-09-24, 68d2c564*; *69d530e4, 2026-04-22*; *6a06061f, 2026-05-14*; *6aaaba8c, 2026-09-16* | [NEW] |
| **Carousel design** | Designed in Canva from brand guidelines (a Canva brand deck). Whitney iterated slide designs herself with ChatGPT feedback for the giveaway carousel (*6983f0ce, 2026-02-05*); she proposed "brand fonts on blank slides" with a founders' photo on the final DM slide (*Refining Carousel Copy, 2025-12-31, 6954922b*). In October 2026 she wanted copy only, which Gisselle pastes into Canva; font emphasis left to WIA. | 13 Oct call; *694f3d51* | [NEW] |
| **Slide headers** | When ChatGPT labelled slides in capitals she asked whether those labels belonged on the slides; the answer was "selectively" (*6a73993f, 2026-08-13*). | | [NEW] |
| **Sizes and limits** | Feed graphic 1080 × 1350; IG caption 2,200 characters; Threads 500 characters; carousel slide cap queried (10 vs more). | *6a33f6dd*; *698407f8*; *694ecc87*; *69c14c0f* | [NEW, partly EXISTING] |
| **Covers** | Pre-designed cover images (the team attached three; ChatGPT described them as minimal, editorial and premium); title text overlaid, sometimes a subheading; set planned across a week. | *6a68eccd, 2026-07-28* | [EXTENDS] |
| **Audio** | Chosen by Whitney in Instagram at posting; ChatGPT asked only for vibe. If a Reel may run as an ad, trending IG music may not be licensed for ads (raised in a client thread). | *IG Carousel Audio Tips, 2026-01-14, 6967eeb2*; *698407f8*; *Press Record Co. Draft ad music response, 2026-08-17, 6a837617* | [NEW] |
| **Email platform** | LeadLock (white-label GoHighLevel): merge field `{{contact.first_name}}` and tracked links on HighLevel's link domain in the sent UVP email. | *6abeb98d, 2026-10-01* | [NEW evidence] |
| **Send times and recipients** | "Tuesday, October 28 at 6am"; "SEND TIME: Morning"; recipients are named LeadLock lists (a "clean deliverability" list, minus full-service clients). Emojis in subject lines at most once or twice a month (13 Oct call). Evergreen emails also join the Investment Guide nurture. | *Google Ads VIP Day, 2025-10-24, 68f973df*; *GSA Black Friday promo plan, 2025-11-25, 691ce202* | [EXISTING: format-guide; emoji frequency NEW] |
| **Scheduling** | No scheduling tool for WIA's own posts appears. Meta Business Suite scheduling appears only as a service offered to clients. Whitney posts ("I posted this reel today"). | *69f9018e, 2026-05-06*; *General Email Drafts, 2026-09-01, 6a8dfcd0* | [NEW] |
| **Link routing** | Link in bio, then "click Accelerate" (a link-in-bio page); Savannah's audit asked for "Apply to work with us" and offers first in the link list. TikTok link in bio unavailable to WIA (May 2026). | *69f9018e*; *6a3acdf8, 2026-06-23*; *69f5361f, 2026-05-01* | [NEW] |
| **Approval flow** | 2025: a social media manager drafted posts, voiceovers and a holiday carousel; Whitney reviewed and often rewrote. Jul to Sep 2026: an unnamed team member drafted captions and scripts; Whitney stepped in ("Whitney here"). Gisselle handles Canva paste and client communications. Whitney approves everything. | *68b87900*; *694b0a01*; *694ecc87*; *6a73993f* | [EXISTING: synthesis 1.2; Canva step NEW] |

---

## 5. Offers and CTAs per piece (Question 5)

**Already captured [EXISTING: cta-catalogue; KB 10; rulings R-9, R-10]:** CTA fits the channel (DM keyword on Instagram, reply in email, none on Threads); not every piece sells; ATTRACT no CTA or follow and save, WARM soft or none, CONVERT the offer CTA; three Instagram pieces a week, one with an offer CTA; sign-off follows the CTA; check capacity; pricing gated; reply beats choosing an offer.

**How a week actually split its CTAs:**

| Week | Pieces and CTA | Source |
|---|---|---|
| 27 Jul 2026 | Podcast clip 1: no offer CTA, podcast link. Clip 2: podcast link. Case-study Reel: DM "Accelerators". Friday email: reply ("I read every response myself"). | *6a68eccd*; *6a721147* |
| 3 Aug 2026 | Carousel: DM "ADS" covering both managed and learn-it-yourself support. Caption: DM "ADS". Email: reply, from "me". | *6a721147* |
| 17 Aug 2026 | Reel: DM "ADS". Carousel and Reel captions: DM "ADS" with a personal invitation. Email: conversational reply CTA. | *6a73993f*; *6ab41e90* |
| 14 Sep 2026 | Email: link to the Accelerators page. Reels: DM "ADS" (both, which [T] questioned). Captions: varied endings. | *6aa98079*; *6ab41e90* |
| Sep 2025 audit giveaway | So many audit-CTA posts that Whitney made one a no-CTA nurture post | *Google Ads Audit, 2025-09-11, 68befe84* [EXISTING: cta-catalogue rule 2] |

**New observations:**
- **In practice the recent weeks were CTA-heavier than R-10 [NEW].** August and September 2026 put a DM "ADS" CTA on most Instagram pieces; only the 27 Jul week followed the two-without, one-with split. The team's 23 Sep question and ruling R-10 point the same way: fewer and varied CTAs.
- **One offer CTA a week is not a stated rule, but one *offer-specific* CTA a week is the observed norm [NEW].** Named offers appear once a week (Accelerators in the case-study Reel; the Accelerators link in the UVP email); the other pieces use the general "ADS" keyword or a reply.
- **The email CTA is a reply or one link, never a DM [EXISTING: F05].** The 31 Jul send added a personal line about reading every reply.
- **The comment keyword ("Comment 'Google Ads Audit'") is used only for the giveaway [NEW].** No automation tool is named; how comments were answered is not in the export.
- **Savannah's stage CTAs (follow, comment, engage for ATTRACT and WARM) were not used in Whitney's finals**: she disliked asking for comments that won't come (Threads, Dec 2025) and asked whether to request a follow at all (*6a06061f, 2026-05-18*). [EXISTING in part: KB 01 ruling R-9]

---

## 6. Quality bar (Question 6)

### 6.1 What she praised vs rejected in pack content

Counts are messages in the 91 own-marketing chats.

| Signal | Messages (conversations) | Typical words | What triggered it |
|---|---|---|---|
| Approval | 66 (35) | "good to go", "Love it!", "This is perfect!", "No further edits needed", "let's goooo" | After her own edits, or when a draft used her fact and her line |
| Strong rejection | 59 (32) | "sucks", "terrible", "makes me want to barf" | Generic hooks and subject lines; desperation framing; AI cadence |
| "Go deeper" / depth | 50 (30) | "go deeper", "in depth" | Carousels and captions; strongest Dec 2025 to Jan 2026 |
| Surface level / fluff | 27 (19) | "surface level", "fluffy" | Carousel slides, Highlight copy, captions |
| Generic | 21 (18) | "generic", "not wedding industry specific" | Hooks, captions, UVP examples |
| Thought leadership | 20 (15) | "we're thought leaders" | Nov 2025 to Apr 2026; then the voice guide took over the job |
| Sounds AI | 17 (8) | "AI speak", "sounds so AI" | Contrast pairs, stock openers |
| Accuracy check | 29 (21) | "accurate?", "misleading", "disingenuous" | Offer scope, events, claims |
| Desperation screen | 22 (18) | "lack mindset", "desperate", "struggling" | Hooks and opening lines |
| Took liberties | 10 (9) | "too many liberties", "why did you change" | Repurposing and refining |

### 6.2 What "publish as is" meant

- **Her definition was functional, not stylistic [NEW].** The pieces she declared ready were the ones where (a) the hook named a specific scene, quote or stance, (b) every fact was hers or the client's, (c) no line spoke to a struggling reader, (d) the piece did not repeat its siblings, and (e) it sounded like her talking. That matches the existing rules; the new part is that **readiness was judged per piece in context of the week**: a caption was "good to go" only once the sibling Reel's hook and cover were fixed (*6abeb98d, 2026-10-01*).
- **ChatGPT pack drafts shipped unedited mainly for covers (chosen from options) and giveaway captions** **[EXISTING: week2 findings A.4]**. Scripts, slide 1 and subject lines were rewritten nearly every time (section 3.3).
- **Volume was never the quality bar.** She wanted fewer, deeper pieces when forced to choose (longer clips; carousels with 5 to 9 sentences a slide; long captions), and said in October 2026 she was fine with fewer angles in a light week.

---

## 7. Gaps against brief contract v4 (Question 7)

Contract v4 (`backend_pipeline/briefs/contracts_v4.py`) already carries: up to three Reels (kind story, stance or b-roll text; cover text; on-screen hook; spoken opening; full script or up to three screens; beats, including exact start and end lines for an existing clip; read time; source; caption); a carousel (title, 7 to 12 slides, caption); an email (send header with DATE, SEND TIME, RECIPIENTS; two to four subjects; preview; opening; body; ending); an optional `stories` plan of up to eight frames (from v2); offer descriptors; and the brief's CTA decision. **Note:** the summary given for this research did not mention `stories`; check whether writer v5 fills it.

Ranked by how central each missing item was to WIA's publishing:

| Rank | Gap | Why it matters (evidence) | Centrality |
|---|---|---|---|
| 1 | **Post-recording pass: caption and cover written from the recorded transcript** | Every recorded Reel from July to October 2026 got its final caption and cover after recording, from a transcript that differed from the script (P1). v4 writes the caption from the script, before recording. | Very high |
| 2 | **Week-level allocation across packs** | One email a week; three Instagram pieces with two without an offer CTA; one offer-specific CTA; posting order and alternation (sections 2.2, 5). v4 is per brief; three briefs a week each carry an email and up to three Reels. | Very high |
| 3 | **Existing-footage cut sheet** | When the source is a podcast or founders' recording, WIA needed exact start and end lines, no rewording, longer complete clips (sections 1.2, 2.3). v4 `beats` can hold start and end lines, but there is no slot for the transcript excerpt, the full-length version, or the podcast-link CTA. | High when the week has footage |
| 4 | **One consolidated publishing sheet** | She demanded one unabbreviated, day-by-day document with every piece in final form (P2). v4 renders per brief; nothing gathers a week. | High |
| 5 | **Cover set and subheading** | Covers carry an optional subheading and are planned as a set for the week (section 1.2; P6). v4 has one `cover_text` per Reel. | Medium |
| 6 | **Stories sequence tied to the day's piece** | Common from Sep 2025 to Jun 2026, then absent. v4 has `stories.frames` (up to eight) but no link to which Reel or carousel it leads into. | Medium, falling |
| 7 | **Ad and trial variants** | A cold-traffic caption for a Reel run as an ad; a second b-roll hook for a trial Reel (P12). Not in v4. | Low to medium |
| 8 | **Light production notes** | A note on which carousel lines take emphasis (WIA declined this "for now"), the founders' photo on the final slide, cover image choice. v4 has `job` direction fields; nothing for design. | Low (WIA said copy only) |
| 9 | **Email extras** | An optional P.S. (common until early 2026) and a single link-button line when the CTA is a page. v4 `ending` can hold both, but the writer is not told they exist. | Low |
| 10 | **Threads post** | Optional per R-10; none after May 2026. | Low |
| 11 | **Story Highlight funnels, lead magnets, launch and giveaway sequences** | Real WIA output, but per offer or campaign, not per weekly angle. | Out of weekly scope |
| 12 | **TikTok, LinkedIn, blog, YouTube, Facebook-specific copy, audio picks, graphics, GIFs** | TikTok out by R-10; the rest absent or chosen by Whitney at posting. | Out of scope |

---

## 8. Implications for a pack stage

Each requirement has an evidence strength: **strong** (repeated across months, in her finals or her explicit words), **medium** (clear but few instances, or team-typed), **weak** (one instance or inference).

### 8.1 What a pack is

| # | Requirement | Strength | Evidence |
|---|---|---|---|
| R1 | A pack is the publishable set for **one approved brief**: one email, one to three Reels (each with cover text and caption), one carousel (with caption). Nothing else is required. Stories and Threads are optional add-ons, off by default. | Strong | Four "week" chats (section 1.3); KB 14; R-10; no Stories or Threads requests after June 2026 |
| R2 | The pack **reuses the brief's v4 copy as its first draft** and changes only what the pack stage must (week fit, post-recording pass, cut sheet). It must not rewrite approved lines. | Strong | Refine-don't-replace (R rules, about 52 events); "too many liberties" (*6a296764*) |
| R3 | **Later pieces derive from the approved earlier piece**, in the brief's order (anchor first), not freshly from the source. | Strong | Section 2.1 chains |
| R4 | **Do not maximise volume.** No auto-splitting into many short clips or repeated clips with new hooks; complete thoughts only. | Strong | *69c5403c*; *69f5361f* (follower loss) |

### 8.2 Week-level assembly

| # | Requirement | Strength | Evidence |
|---|---|---|---|
| R5 | A **week view** across all packs: one list email (Tuesday by default, send time and recipients proposed for WIA to confirm), three Instagram pieces, a proposed posting order with format alternation. Extra emails are held for a later week or the nurture sequence. | Strong (email cadence, CTA split); medium (alternation) | R-10; KB 14; content-workflow; *69d530e4*; *694f3d51* |
| R6 | **CTA allocation per week:** two pieces without an offer CTA, one with; at most one offer-specific CTA a week; email CTA a reply or one link; vary CTA wording across the week. | Strong | R-9, R-10; cta-catalogue; *6a68eccd*; *6ab41e90*; section 5 |
| R7 | **Distinct openings across the whole week**, not only within a pack: no two pieces share a hook, cover or subject. | Strong | F01, F02; *6a73993f*; *6abeb98d* |
| R8 | Respect the **one-to-two-month repeat window** and the recent-published register when two packs in a week overlap. | Medium | 13 Oct call; week2 findings E.4 |

### 8.3 Reels and recording

| # | Requirement | Strength | Evidence |
|---|---|---|---|
| R9 | **Two passes for recorded Reels:** before recording, the script (spoken register, beat labels allowed, no stage directions beyond light cues); after recording, a **caption and cover pass from the uploaded transcript** that keeps to what was said. The pack is not "done" for that Reel until the second pass runs. | Strong | P1; *6a68eccd*; *6a73993f*; *6ab41e90*; *6abeb98d* |
| R10 | When the source is **existing footage**, produce a cut sheet: exact start and end lines, the verbatim excerpt, whether the full-length version also posts, and the podcast-link CTA where relevant. No reworded lines. | Strong | *69c954cf*; *69c3f6de*; *69c5403c*; *6a68eccd* |
| R11 | **Covers as a set** for the week, each a specific title with an optional subheading, written after the transcript. Offer two or three options; Whitney often picks or writes her own. | Medium | *6a68eccd*; *6ac3c3eb*; *694ecc87* |
| R12 | Reel kinds stay as v4 (story, stance, b-roll text). A **voiceover-on-b-roll** kind is optional and low priority. | Weak | 2025 voiceovers only |

### 8.4 Carousel, email and hand-off

| # | Requirement | Strength | Evidence |
|---|---|---|---|
| R13 | Carousel copy is **copy only**, slide by slide, ready for Gisselle to paste into Canva; no font or layout instructions unless WIA asks. Slide 1 carries the promise; final slide the DM CTA. | Strong (copy only, 13 Oct call); strong (slide rules) | 13 Oct call; F03; KB 09 |
| R14 | Email keeps v4's send header and adds an optional P.S. and an optional single link line; no graphics or GIFs by default; emoji in a subject at most once or twice a month. | Medium | Section 1.2; 13 Oct call |
| R15 | **One consolidated pack document per week**, every piece in final form, unabbreviated, editable (Google Doc or the app's editor), with a short "before publishing" note per piece kept out of the copy. | Strong (one document, unabbreviated); medium (Google Doc) | *69c5403c*; *6a721147*; *694acab5*; *6a7e2852*; week2 findings E.9 |
| R16 | Record **who approved what and when the piece went out** (Whitney or a named relay; posted date), so "they did well" can drive reuse later. | Medium | Synthesis 7; content-workflow 5 |

### 8.5 Optional or later

| # | Requirement | Strength | Evidence |
|---|---|---|---|
| R17 | Optional **Stories sequence** for a chosen piece: three to seven text-rich frames that lead into the Reel, then the Reel. Off by default. | Medium (falling) | *69f9018e*; *69c5403c*; *6a26e8bc* |
| R18 | Optional **ad variant** caption (cold traffic) and **trial-Reel** alternate hook. | Weak | *69c5403c, 2026-04-09*; *6a1efd89* |
| R19 | Optional **Threads** post (under 500 characters, no CTA). | Weak | R-10 "optional"; none since May 2026 |
| R20 | Out of scope for the weekly pack: TikTok, Story Highlight funnels, landing pages, lead magnets, launch and giveaway sequences, audio picks, graphics, LinkedIn, blog, YouTube. | Strong | Section 1; R-10 |

### 8.6 Open questions to put to WIA (or the owner) before building

1. With three angles a week, does WIA want three full packs each with an email draft (two held back), or should only one pack per week carry an email? (R5)
2. Should the post-recording caption pass be in the app (Whitney uploads a transcript or Fathom-style recording) or stay manual? (R9)
3. Are Stories still wanted at all after June 2026? (R17)
4. Is the Google Doc export enough, or does Gisselle need a per-piece copy view for Canva? (R13, R15)

---

## Appendix: conversations cited

| Title | Date (first message) | Id prefix |
|---|---|---|
| Threads | 2025-08-12 | 689b8798 |
| Instagram post ideas | 2025-09-03 | 68b87900 |
| Google Ads Audit | 2025-09-08 | 68befe84 |
| Email marketing spin-off | 2025-09-23 | 68d2c564 |
| Google Ads VIP Day (GSA launch) | 2025-10-23 | 68f973df |
| Repurpose IG reel to email | 2025-10-30 | 6902aa8a |
| GSA Black Friday promo plan | 2025-11-18 | 691ce202 |
| Evergreen Reels Hooks | 2025-12-23 | 694acab5 |
| Carousel Feedback and Suggestions | 2025-12-23 | 694b0a01 |
| Meta Ads Reel Text Suggestions | 2025-12-26 | 694ecc87 |
| IG Funnel Design Collaboration | 2025-12-27 | 694f3d51 |
| Refining Carousel Copy | 2025-12-31 | 6954922b |
| IG Carousel Audio Tips | 2026-01-14 | 6967eeb2 |
| IG Carousel Giveaway Design Feedback | 2026-02-05 | 6983f0ce |
| Ads Accelerator Caption | 2026-02-05 | 698407f8 |
| [WIA] Accelerator Sales Page Optimization | 2026-03-23 | 69c14c0f |
| Reel Feedback and Edits | 2026-03-25 | 69c3f6de |
| Data Driven Decisions Video - IG Reel Strategy | 2026-03-26 | 69c5403c |
| General Advertising Freelancers/Agencies Video | 2026-03-29 | 69c954cf |
| IG Stories Set Offer Framework | 2026-04-01 | 69cd32e6 |
| Summit Content Customization | 2026-04-07 | 69d530e4 |
| 4/15/26 Marketing Email Strategy | 2026-04-14 | 69dec86e |
| [WIA] Organic vs Paid Strategy | 2026-05-01 | 69f5361f |
| [WIA] Repurposing for Stories & Threads | 2026-05-04 | 69f9018e |
| [WIA] Wedding Ads Strategy | 2026-05-11 | 6a026ad2 |
| [WIA] Marketing Formulas for Success | 2026-05-14 | 6a06061f |
| [WIA] Wedding Marketing Visibility | 2026-06-02 | 6a1efd89 |
| [VAULT] Client Research for Marketing | 2026-06-08 | 6a26e8bc |
| [WIA] Marketing Assumptions vs Data | 2026-06-10 | 6a296764 |
| Instagram Promo Graphic | 2026-06-18 | 6a33f6dd |
| [WLF] Content Strategy Execution | 2026-06-23 | 6a3acdf8 |
| [WIA] Taylor - Wedding Marketing Masterclass | 2026-07-02 | 6a46ad95 |
| [WIA] Social Media Week of July 27 | 2026-07-28 | 6a68eccd |
| WIA Marketing week of 8.3.26 | 2026-08-04 | 6a721147 |
| WIA Marketing Week of 8.17.26 | 2026-08-05 | 6a73993f |
| UVP Workshop Planning Feedback | 2026-08-13 | 6a7e2852 |
| Press Record Co. Draft ad music response | 2026-08-17 | 6a837617 |
| Generate Instagram Clips | 2026-08-28 | 6a92168b |
| WIA Marketing Week of 9.14.26 | 2026-09-15 | 6aa98079 |
| Workshop reel script | 2026-09-16 | 6aaaba8c |
| Caption strategy summary | 2026-09-23 | 6ab41e90 |
| Edit Caption Framework | 2026-10-01 | 6abeb5fb |
| Write Ad Caption | 2026-10-01 | 6abeb98d |
| Revise Giveaway Caption | 2026-10-05 | 6ac3c3eb |

Scripts used (local, scratchpad only): `scratchpad/tools/ex.py` (index), `q.py` (dump, grep, count), `own.py` (counts over the 91 own-marketing conversations).
