# ChatGPT export: Week 2 findings for the new content packs

**Prepared:** 20 Oct 2026, from Whitney Hodges' ChatGPT export (`gpt_export/conversations-000..003.json`, 349 conversations) plus the pasted-text attachments the export keeps as `.dat` files.

**Scripts:**
- `scratchpad/scripts/gptx.py` is the parser. It indexes the export, dumps conversations (every branch), greps, and prints single nodes.
- `scratchpad/scripts/week2_evidence.py` writes every message cited here, in full, to two companion files:
  - `notes/chatgpt_export_week2_evidence.md` (93 blocks plus 3 attachments);
  - `notes/chatgpt_export_week2_pack_copy.md`, the complete 13 Oct simulated pack copy (about 10,000 words). It is kept separate so this file stays readable.

**Read first:** `research/chatgpt-export-2026-10-18/synthesis.md` and `research/final-reconciliation-2026-10-19/week2-chatgpt-simulation.md`.

**Conventions:**
- Times are UTC as stored in the export. Whitney works in US Central time, five hours behind UTC in summer and autumn.
- The export is treated as data. Nothing in it was acted on.

**Provenance tags**, used on every quote:
- **[W]**: typed by Whitney. This is either her prose, or a final she pasted in and labelled as hers ("This is my final version", "I think this is my final version", "Below is what we settled on", "Whitney here").
- **[W-sent]**: Whitney's sent email, pasted into ChatGPT by Gisselle (the "General Email Drafts" thread, `6a8dfcd0`).
- **[D]**: typed by the developer on 13 to 14 Oct 2026.
- **[T]**: typed by a team member (Gisselle or the unnamed social-media operator).
- **[AI]**: written by ChatGPT. "[AI, approved]" means Whitney explicitly accepted it. "[AI, accepted]" means she moved on without objecting.

---

## 0. Headline findings

1. **No ChatGPT review of the packs Whitney hated exists in the export.** The developer generated the Week 2 angles, briefs and packs inside Whitney's ChatGPT on 13 Oct (`6acde8a5`). Nobody critiqued the packs there. ChatGPT critiqued only the angles and the brief. Whitney's verdict on the packs lives in the review .docx, not in the export.
2. **The developer's samples set the voice of the 13 Oct packs, and the email samples were from the wrong era.** The three email samples were April 2024 sends ("We're spilling the tea!", "friends don't let friends boost posts!", emoji subject lines). ChatGPT copied them, which is why the A01 and A09 subject lines end in "👀". The reel and caption samples were genuine recent Whitney finals, but ChatGPT cloned their structure into all 12 reels. Every reel ends "DM me ADS" or "Save this". The synthesis already says to ignore 2024 emails as voice models.
3. **The developer's own Content Atelier Week 2 output was critiqued too, in `6acdefc0` (13 Oct, 08:46 to 09:51).** It is a different set from A01 to A10:
   1. Reviews and buying research.
   2. Tour follow-up and venue capacity.
   3. Clicks without conversions.
   4. Chat-widget preparation.
   5. Noam as internal sales intelligence.

   Content Atelier's pasted output (Pasted text 8) survives in full, with transcript excerpts. ChatGPT's verdict on it: "you're still supplying a substantial part of the judgment".
4. **Week 2's strongest "WIA perspective" idea has already been published.** The idea is "reviews are not market research" and "the question we ask every new client". Whitney sent it as a list email on 10 Jun 2026, the same week as the calls, with a 10-slide carousel and a caption she wrote. ChatGPT flagged the overlap on 13 Oct: "it closely overlaps the market-research email already included in your content knowledge base". A new pack must not repeat it.
5. **The other Week 2 central points have recent published equivalents:**
   - "advertising doesn't start inside the ad platform": the UVP email, two Reels and two captions, 15 Sep to 1 Oct.
   - "more leads won't fix it" and "generating more leads is great, but…": 30 Apr, then 25 to 29 Jun.
   - "can't measure, can't optimize" and "hand-hold the very agency": 31 Jul to 6 Aug.
   - "ads give you breathing room": 18 to 20 Aug.
   - "Google reps / freelancer or agency / Are your Google Ads actually working?": the audit giveaway, 5 to 16 Oct 2026, which had only just ended.
6. **Week 2 situations have documented "what happened next" that the pipeline does not know about:**
   - **Diamond A Ranch.** Whitney's Week 2 idea (Allie's welcome video, a selfie before tours, photos in early texts) was built into the LeadLock SMS sequence by 9 Sep 2026.
   - **The Penny.** Meta went from 0 tracked leads to 105 leads in a month at about $8 per lead (Sep 2026).
   - **Erin.** Erin of the T07 office hours is Erin Smith of Carroll Hall. Her venue is the $22K-to-$70K Accelerator case study that WIA published from 31 Jul to 6 Aug, and her name must never be used.
   - **Fallon.** Fallon left WIA in mid-August 2026, and Whitney now runs every strategy call.
7. **Whitney's hook rules are consistent.** She rejects:
   - generic or "played out" hooks;
   - hooks that speak to desperation;
   - the same hook reused across sibling formats;
   - subject lines that sound like LinkedIn;
   - anything that overstates what WIA does, or implies events that did not happen (for example "nobody actually showed up live").

   She approves:
   - a specific scene or quote ("It feels like our sales are on autopilot.");
   - a concrete question built on a client fact ("What would happen if your wedding business didn't post on Instagram for the next 10 weeks?");
   - a confident founder stance ("If I don't know why someone should choose your business, I have no business running ads for it.").

---

## A. The 13 Oct 2026 conversations

### A.0 Map: which conversation is which, and who typed

| Conversation | Title | UTC window | Typed by | What it is |
|---|---|---|---|---|
| `6acd92cc-22a4-83e8-891b-2189d4efc296` | Google Doc access confirmed | 13 Oct 02:09 to 03:01 | **Whitney** (5 turns) | She asks ChatGPT to review Content Atelier's Week 1 "Content Angle Review" Google Doc (six angles). She rates it 1/5 and asks for her own version. An agent-mode branch produced a .docx; she rejected the mode ("I don't like this. Can I switch back to chat?") and kept a chat-mode answer |
| `af07ed5d-09d8-8325-a452-7c13bab9faa3` | Copy of Google Doc access confirmed | 13 Oct 02:09 to 03:01 | Whitney (copied) | A copy of the agent-mode branch, ending at "I don't like this…" |
| `6acde8a5-de40-83e8-b8e3-f6f533f943c9` | Branch · Copy of Google Doc access confirmed | 13 Oct 08:15 to 14:46 | **Developer** from message [25] | Branched from Whitney's message [24]. Contains the handbook request, the critique of two handbook-trained angles, the brief critique, the Week 2 simulation (moments, 10 angles, briefs A01/A05/A03/A09, the four packs) and the sample-driven rewrites |
| `6acdefc0-95b8-83e8-af95-004c25250a47` | Branch · Copy of Google Doc access confirmed | 13 Oct 08:45 to 11:50 | **Developer** | Pastes Content Atelier's own Week 2 angles (Pasted text 8) for critique, then asks for a CTA |
| `6acf1c9a-c908-83e8-896f-51c00c35c6e8` | Submit test result | 14 Oct 06:09 to 06:24 | Developer | MCP write-test plumbing; no content |

Attachments recovered from `.dat` files (the earlier analysis did not have their text):
- Pasted text(8): Content Atelier Week 2 angles. File `file_000000005c548211aaeda61140e8fe7d.dat`.
- Pasted text(9): two angles "generated after learning from the content system handbook". File `…8ee0820b…`.
- Pasted text(10): the Week 1 landing-page brief. File `…844881f5…`.
- Pasted text(20261013-134147): three published carousels with metadata, scraped by the developer. File `…6600820e…`.

Not in the export (sandbox links only):
- `WIA_Content_Angles_June_8_to_14.docx`, which held the full angle review and the **moment catalogue**;
- `WIA_Editorial_Briefs_A01_A05.docx` and `…A03_A09.docx`;
- `WIA_Content_Pack_1_A01.docx` to `…4_A09.docx`;
- `WIA_Content_System_Handbook.docx`, the handoff ZIP, and Whitney's `WIA_Content_Angle_Alternatives.docx`.

### A.1 Every critique of angles, briefs and packs (verbatim)

#### A.1.1 Whitney's own words on 13 Oct (Week 1 angles) [W]

`6acd92cc`, 02:30 UTC:

> "Yeah, I honestly think I would rate all of this a 1 in every single category at this point.
> I think the other thing that is missing is that our content can talk about the process of our work, not just the specifics of the conversation
> I think for all of the call recordings referenced, if they would have zoomed way out the takeaways would have been much more impactful.
> I'm seeing potential topics here of how we help wedding pros refine their landing page messaging and imagery, our process for keyword research (and negatives) plus how we go over and discuss them with a client to make sure we're in alignment, how we help venues position themselves when they are vastly different than others in their market, and with Zadie what were the things she was impressed with and liked about LeadLock on the call even though she couldn't justify the pricing"

At 02:48:

> "Can you help me create my own doc that highlights the exact same calls they are referencing and provides and angle I would approve of?
> I'm also curious to get your opinion on the categories of: argument, audience, tension, take, mechanism, reader decision. Are those actually the most important things to define here?"

At 02:59, about agent mode:

> "I don't like this. Can I switch back to chat?"

What this shows: her own unit is **the process of our work**, zoomed out. Each of her four example topics is "how we help…" or "our process for…". The fifth asks what a prospect *liked*, not what she objected to.

#### A.1.2 ChatGPT's critique of the six Week 1 angles, in Whitney's chat [AI]

Node `a43d8ebc`. It was written before her 1/5 rating, and she then went further than it did. Key verbatim lines:

- "the AI system is doing a good job identifying meaningful information from your calls, but it's not yet demonstrating the strategic judgment necessary to turn that information into compelling content for WIA."
- "Looking at these six angles, nearly everything falls into WARM."
- "Angles 1, 2, 3, and 6 are derived almost entirely from things clients or prospects said."
- "Why would WIA want to publish content encouraging prospective customers to scrutinize whether our own software is worth the investment?"
- On moments to flag: "I actually wouldn't recommend running ads yet, and here's why." / "We see this all the time with wedding venues..." / "That's something we approach differently from a lot of other agencies."
- Closing question: "why the system selected these six ideas over everything else discussed that week."

After her rating, node `4cbb6622`:

- "They're analyzing the conversations to identify *what was discussed*, when they should be analyzing them to identify **what the conversations reveal about how WIA helps wedding businesses succeed.**"
- "Our clients aren't expected to understand Google Ads at the same level we do. But their knowledge of their business, their clients, and their market is essential to building an effective campaign."
- "**That's the difference between demonstrating knowledge and demonstrating expertise in action.**"
- "the intended audience for our content is not necessarily the same as the person participating in the conversation."

On the angle fields, node `26f45f60` (the chat-mode answer that sits on Whitney's active branch):

- "**Reader Decision** | My least favorite as a required field. Not every piece of content needs to help someone make a specific decision."
- Proposed fields: Content opportunity, Strategic purpose (ATTRACT/WARM/CONVERT), Target audience, Core message, Tension or hook opportunity, WIA's expertise in action, Source evidence.
- "identifying a content opportunity and writing a content brief are two different stages."

#### A.1.3 ChatGPT's critique of the developer system's own Week 2 angles (`6acdefc0`, 08:48) [AI]

The developer pasted Content Atelier's Week 2 output [D]: "They got this another set of content angles generated from another week. Can we have your critique / views on this." The five items, verbatim titles from Pasted text 8:

1. **"Reviews and buying research answer different questions"**
   - WARM · thought_shift.
   - Source: The Penny call, 56:21 to 58:32.
   - Whitney: "reviews are not market research".
   - Whitney proposes LeadLock surveys for ELEVATE clients.
   - Fallon: "Yeah, I think that that's a great idea."
2. **"Tour follow-up has to fit both the couple's timeline and the venue's capacity"**
   - WARM · behind_the_scenes.
   - Source: T02 (Carmen's room (1)), 08:00 to 19:49.
   - Fallon: "about an 11% inquiry to tour booking conversion rate… no shows or tours that are being canceled or ghosting… is almost at like 40%".
   - Allie: "anytime. Somebody books a tour more than 2 weeks out… they're gonna find something else".
   - Allie: "we can't… don't do tours on Saturdays when we have weddings… all of us staff has babies all under 5".
   - Whitney: "can we connect on the phone first? … let's FaceTime, and I'll show you everything, like, live in action".
   - Fallon: "a supplemental email… that has that video inside".
3. **"A campaign with clicks but no conversions calls for checking the whole path"**
   - WARM · campaign_breakdown.
   - Source: T07 (Carmen's room), 25:19 to 40:50.
   - The figures: "41 clicks", "almost 20%" CTR, "$8 a day", "I really would like to determine if it's good or not by 100 clicks".
   - Erin: "It's adding site links".
   - The "wedding banner" on the corporate page.
   - Carmen's suggestion to ask Jacqueline for landing-page feedback.
4. **"A useful chat widget depends on the business information and handoff behind it"**
   - WARM · process.
   - Source: T09.
   - Danielle McGinnis: "the chat widget is only as good as what you feed in".
   - Whitney: "this is a sales tool… I don't even know that I would want the widget to be able to. Give them a link to be able to book a sales consultation without me".
   - Whitney: "better to use us as guinea pigs than an actual client".
5. **"Internal sales intelligence"** (Noam)
   - Source: T11.
   - Noam: "I don't know what I've done. I don't know what we changed… I think what I need first is an audit."
   - Whitney: "performance-based, though, isn't something that we do."
   - Whitney: "a Google Ads audit… a 45-minute call with Carmen… a one-time fee of $197". This price is internal; see section E.
   - Noam: "$197 is obviously more realistic for me right now".

ChatGPT's critique, node `c56d649b`, verbatim highlights:

- "**This batch is meaningfully better than the first one.** … The main issue is that they're still turning strong source material into cautious, somewhat generic summaries."
- Table: "1. Reviews versus buying research | Strongest central perspective in this batch | Develop · 2. Tour follow-up and venue capacity | Strong example of WIA's process; framing needs work | Develop · 3. Clicks without conversions | Useful investigation, but still fairly generic | Reframe · 4. Chat-widget preparation | … Hold or develop selectively · Noam: internal sales intelligence | Useful internally, with a missed content opportunity | Extract an additional angle"
- On item 1: "the proposed opportunity places too much emphasis on the **unimplemented survey workflow**." Also: "**praise about the experience doesn't necessarily tell you what convinced someone to book in the first place**."
- On item 2: "'follow-up has to fit both the couple's timeline and the venue's capacity' still feels like a general best practice." The stronger direction is "**how we investigate what happens between an inquiry and a venue tour—and adapt our recommendations to the business we're working with**". Also: "It also connects naturally to your wedding-industry experience: you understand that venues have weddings to execute, staffing limitations, and presentation considerations."
- On item 3: "'Check the whole path' could come from almost any advertising agency. The interesting part is **what Carmen actually investigates and how the client contributes to that investigation**." Also: "an investigation in progress is a legitimate content opportunity."
- On item 4: "Your stronger contribution is the decision to test the tool on WIA first… Before developing it, I'd establish what happened afterward."
- On Noam: "they've stopped too early… **how we help wedding pros understand what needs attention when they already have ads running**."
- "Every proposed public angle is labeled WARM… consider other supported directions—particularly solution selling."
- "The repeated claim-limit bullets also need cleanup." Pasted text 8 does print every claim-limit bullet twice.
- Close: "This batch gives you more to work with, but you're still supplying a substantial part of the judgment that turns the extracted material into worthwhile content."

CTA for item 1. The first answer, "Want your ads to speak to what actually makes couples choose you? DM us **ADS**…", was withdrawn by ChatGPT itself: "My earlier suggestion was too broad and could imply that the proposed workflow is already offered." The replacement is a no-sell action CTA:

> "The next time a couple books, ask them: 'What ultimately made you choose us over the other options you considered?' Then look at your ads and landing page. Are the reasons they gave you actually reflected in your messaging?"

#### A.1.4 ChatGPT's critique of two handbook-trained Week 2 angles (`6acde8a5`, 10:30) [AI]

These came from Pasted text 9, both from The Penny call:
- **Angle 1, "Let local client knowledge shape the map"**. Lauren on "Clovis, Visalia, Fresno, Bakersfield… more, like, price sensitivity"; Whitney: "we definitely should open it up and include, like, the Bay Area, include LA, include San Diego, but those, like, last four cities there, I think let's just leave those off".
- **Angle 2, "Reviews and buying research answer different questions"**, labelled ATTRACT · thought_shift.

Critique, node `893c90f9`:

- "**These are a meaningful improvement over the original six.** … I wouldn't rate everything a 1 this time. I also wouldn't accept the model's mostly 4s and 5s without further scrutiny."
- On Angle 1: "'Let local client knowledge shape the map' feels like an internal principle… The more interesting direction is **how we decide where to advertise a wedding venue—and what we need to understand about that business before making those decisions.**" Also: "Their 'why worthwhile' paragraph actually gets closer to that angle than their title."
- On Angle 2: "**Angle 2 is aligned with your beliefs, but raises a different concern: repetition.** … it closely overlaps the market-research email already included in your content knowledge base—the one about asking clients why they booked… the system should recognize the overlap and explain **what this version adds**." Also: "I'd also question **ATTRACT · thought shift**. Thought shifts sit within your WARM strategy."
- "Both 'nearest alternative' fields also refer to alternatives they never actually identify."

#### A.1.5 ChatGPT's critique of the editorial brief (`6acde8a5`, 11:09) [AI]

This was the Week 1 landing-page brief, Pasted text 10. Node `a142b84c`:

- "**I would not approve this brief in its current form.** It contains useful source documentation, but it makes you review a great deal of qualification and production detail while leaving the actual content direction fairly weak."
- "'Bounded inference,' 'admitted-archive review,' 'structured source-bound NumericFact,' and the repeated C3/C4 qualifications… shouldn't dominate your approval view."
- "the caution has become part of the proposed public content: label the application 'untested,' repeat a caveat beside the CTA, and use blank diagrams throughout. That would produce something stiff and difficult to connect with."
- "**The format bundle creates unnecessary repetition.** … It should not automatically stretch one modest insight into five assets."
- "**Savannah's strategy and your voice need to work together.**"
- The eight sections it proposed later became the A01/A05/A03/A09 briefs: Approved angle, Strategic purpose, Audience and reason to care, WIA perspective, Supporting example, Narrative outline, Format and creative approach, CTA and essential boundaries.

Later, node `5c91ed29`, once the developer made five assets mandatory: "although I questioned automatically producing five assets from every modest insight, you've now established that five-piece pack as the application's required output… If it doesn't [have enough substance], I'll flag that before drafting repetitive material." **It never flagged any pack.**

#### A.1.6 Critiques of the generated packs

**There are none in the export.** After the packs ([115] to [120]), the developer gave only formatting instructions, each with samples:
- "update the contents in these emails for the 4 copies";
- "Similarly for the carousels";
- "Adjust the 3 reels scripts accordingly";
- "for each of these reels i want the captions the way i write".

No message evaluates quality. ChatGPT's own self-assessment, [112]: "I'm also tightening passages where the evidence qualifications sound like briefing notes, so the published copy stays natural." The client's complaints in the review .docx (too how-to, too polished, not her voice, weak hooks, carousel slide 1 not a problem) are the only pack critique. They are not in this export.

### A.2 Pack copy generated on 13 Oct (summary; full text in `notes/chatgpt_export_week2_pack_copy.md`)

Four packs were built: A01, A05, A03 and A09. A02, A04, A06, A07, A08 and A10 were never briefed or packed. The first-draft .docx packs are missing. What survives are chat-only rewrites made after the developer pasted samples. They are all [AI].

**Emails** (node `148279fe`), rewritten "using these samples' warmer team voice":

| Pack | Subject | Opening line | CTA |
|---|---|---|---|
| A01 | "More inquiries? Here's what we look at next 👀" | "More inquiries. More couples booking tours." | "Reply 'ADS' if you'd like to explore ELEVATE and how LeadLock fits into your inquiry process." |
| A05 | "Want to feel more confident running your ads?" | "If you want to keep running your own ads, we want you to feel confident about the decisions you're making." | "Reply 'ADS' if you'd like help choosing an Ads Accelerator for your business." |
| A03 | "Ready for a dedicated team behind your ads?" | "Your advertising can be bringing in business, and you can still be ready for a dedicated team to take responsibility for it." | "Reply 'ADS' if you'd like to talk about ongoing advertising support through ELEVATE." |
| A09 | "A couple finds you on Google. What happens next? 👀" | "Google Ads + Meta Ads can make a powerful pair when each campaign has a clear job." | "Reply and tell us whether you're using Google, Meta or both for your wedding business." |

**Carousels** (node `18f55a39`), nine slides each. Slide 1 of each:
- A01: "More inquiries. More tours booked. / So why are some couples still disappearing before they visit?"
- A05: "You've built the campaign. / You've launched the ads. / Now you're wondering whether to leave them alone or change something."
- A03: "Your ads can be working, and you can still be ready for more support."
- A09: "A couple finds your business on Google. / They visit your website. / Then they leave."

All end "DM us 'ADS'…", except A09, which ends "Save this for your next advertising strategy review."

**Reels** (12 scripts, node `258218c4`; 12 caption versions, node `c0103650`). Spoken first lines:
- A01 R1: "If your venue is getting more inquiries and booking more tours, but some of those couples never actually make it through the door, here's what I want to understand before we recommend the next change."
- A01 R2: "What's a question couples keep asking during your venue tours that your marketing could help answer before they ever arrive?"
- A01 R3: "A booked tour looks like progress in your pipeline. But the venue owner might know something about that booking that changes how we interpret it."
- A05 R1: "You've launched your ads. You're looking at the account. And now you're wondering whether to leave things alone or make a change."
- A05 R2: "One of our office-hours conversations is a good example of why support after launch matters…"
- A05 R3: "If your goal is to manage your own ads, you should understand why the campaign was built the way it was."
- A03 R1: "You can be getting business from your ads and still be ready to hand the advertising over to a dedicated team."
- A03 R2: "If someone audits your ad account a few times a year, who's responsible for everything that happens between those reviews?"
- A03 R3: "If you've spent years building a wedding business that feels recognizably yours, I understand why handing your advertising to someone else can feel like a big decision."
- A09 R1: "A couple finds your wedding business on Google, spends some time on your website, and leaves without inquiring."
- A09 R2: "If a couple has already visited your website, what would you want them to understand when they see your business again?"
- A09 R3: "When a wedding business owner asks whether they should run Google or Meta ads, I want to understand what we're asking the advertising to accomplish."

**Patterns in the pack copy**, so the new packs avoid them. These are my observations, checked against the text:
1. **Boundary language leaked into public copy.**
   - "The email engagement didn't tell us why someone booked or canceled."
   - "That check didn't explain everything about its performance, but it clarified one part of the situation."
   - "Every visitor won't necessarily be reachable."
   - "That depends on the right setup and an eligible retargeting audience."
   - "Those were ideas to discuss and test."

   ChatGPT itself had warned against exactly this in the brief critique.
2. **Results-free stories.** Felipe's story has no payoff ("The experiment remained paused"). Diamond A has no outcome, although one now exists: see D.1.
3. **The same CTA in every Reel.** All 12 reels end "DM me 'ADS'" or "Save this…". The team operator had already raised this on 23 Sep 2026 [T]: "are we doing this every time? … Should we be switching it up every time".
4. **Question-stack and stacked-fragment rhythm**, of the kind the team banned on 23 Sep:
   - "An inquiry. / A scheduled tour. / An attended tour."
   - "The targeting. / The ads. / The landing page."
   - The A09 Reel 3 caption, "The business goal. / The audience. / The message. / The budget and setup."
5. **Problem-free slide 1s.** Only A01 slide 1 states a problem. A03's is a reassurance ("Your ads can be working…").
6. **Facts now stale.**
   - The packs say "You and Fallon" in the briefs and "our team" in the copy. Fallon left in mid-August 2026.
   - A01 implies that the follow-up changes were "ideas to explore". They were implemented by 9 Sep 2026 (see D.1).

### A.3 The ten Week 2 angles, and the moment catalogue

**The ten angles** (`6acde8a5` node `ef547fed`, 11:53 UTC) [AI]. Verbatim titles, pillar labels and central points are already in `week2-chatgpt-simulation.md` and are not repeated here:
- A01 What we investigate when more inquiries aren't turning into attended tours. CONVERT.
- A02 Couples keep making decisions between booking a tour and arriving for it. WARM.
- A03 You can outgrow one-off ad audits while your advertising is still working. CONVERT.
- A04 When people click but don't inquire, we investigate the experience after the click. WARM.
- A05 Learning to run your ads includes learning what to change and why. CONVERT.
- A06 The channel producing more leads may not be the one producing bookings. WARM.
- A07 Your knowledge of your business belongs in our campaign strategy. WARM.
- A08 How LeadLock fits alongside the system you use for booked clients. CONVERT.
- A09 Google and Meta can have different jobs in the same booking journey. ATTRACT.
- A10 Sometimes the right first advertising decision is to pause a campaign. ATTRACT.
- A reserve: the AI inquiry-widget discussion.

**Extra detail on four angles** survives in the developer's paste-back, node `179ed67f` [D], copying the angle cards from the docx:

**A01**
- Evidence: "T02 03:42–10:36 and 28:49–39:51."
- "Allie supplies the business experience and rain-plan concern; Whitney and Fallon contribute the review and recommendations."
- Claim boundary: "avoid publishing the mixed counts as a clean conversion rate".

**A03**
- "The prospect labeled iver describes advertising that already generates business and periodic freelance audits. He wants an ongoing relationship and better efficiency."
- Evidence: "T10 06:32–10:15, 27:29–29:07 and 32:29–34:04."
- Boundary: "Do not imply he hired WIA or achieved savings. Omit historical pricing, availability and any exceptional technology arrangement".

**A05**
- Evidence: "T11 16:21–18:53, 21:36–22:47 and 23:58–30:34; T07 01:55–19:37, especially 18:06–19:37."
- Boundaries: "Do not attribute Noam's difficulties to AI or portray a single experiment as proof that Performance Max always fails."

**A09**
- "The prospect emphasizes Google's search intent and describes Meta as primarily reaching cold audiences. Whitney explains the possible role of retargeting… He acknowledges that he had overlooked this."
- Evidence: "T10 11:20–14:35."

**The moment catalogue.** "18 useful moments" were catalogued in `WIA_Content_Angles_June_8_to_14.docx`, which is not in the export. Fragments survive in ChatGPT's progress messages (nodes `90fd0ccb`, `d2178331`, `1939fba1`, `fe429252`, `3e9c7400`):
- "how you help owners decide what kind of support they need";
- the market-research survey idea ("you discuss how the surveys could be built and delivered");
- "reviewing the route someone takes after clicking an ad";
- "distinguishing campaign activity from booking progress";
- "working through problems with clients in office hours";
- "the venue conversation about what happens after an inquiry";
- "the prospect whose ads already work but who wants an ongoing strategic partner";
- "the channel comparison… its reported numbers need verification";
- "The AI widget discussion is a reserve direction because it shows an evaluation in progress."

The best surviving record of what the transcripts contain is the excerpt set in Pasted text 8 and 9 (section A.1.3 and the evidence file). Those are verbatim transcript turns with timestamps.

**Two other Week 2 angle sets** came from the developer's Content Atelier, not from ChatGPT:
- the five items in A.1.3;
- the two items in A.1.4.

Together they are the closest thing to "what our system produced for Week 2" that survives with critique.

### A.4 What Whitney typed, and what the developer typed in her name

**Whitney typed** only the five turns in `6acd92cc`, quoted in A.1.1. Her stated wants, in her words:
- "our content can talk about the process of our work, not just the specifics of the conversation";
- "if they would have zoomed way out the takeaways would have been much more impactful";
- an angle "I would approve of";
- questioning whether "argument, audience, tension, take, mechanism, reader decision" are "actually the most important things to define here".

**Everything after 08:15 in `6acde8a5` and `6acdefc0` is the developer [D].** It is written in the first person as if it were Whitney ("i want the captions the way i write", "based on what you know about me, my voice"). Do not treat any of it as Whitney's preference. In particular:
- "build thoroughly for 1, then 2nd and then 3rd and 4th"
- "Here are a few email samples…" These were three April 2024 sends to 330, 104 and 339 recipients, one with "failed: 187". Their subject lines: "Our Secret to Consistent Lead Generation", "The secret sauce that delivers killer ad results 👀", "Stop boosting posts on Instagram!!"
- "Now for the scripts, here are the examples of the length and the tone." There were four Reels, all genuine Whitney finals:
  - the 10-week Reel (Aug 2026);
  - "If I can't tell from looking at your website…" (Sep 2026);
  - "I taught a training for Ads Accelerator clients…" (Sep to Oct 2026);
  - the $70K Reel and its caption (31 Jul 2026).
- "for each of these reels i want the captions the way i write." Three captions:
  1. "Google's recommendations aren't always what's best for your wedding business." This is [AI, accepted], `6ac3c3eb`, 8 Oct.
  2. "Engagement season is right around the corner." This is [AI, accepted], 5 Oct.
  3. "There's a lot more to running successful ads than knowing your way around an ad account." This is [AI, approved]: "Ok, that caption and punchy cover are good to go", 1 Oct.

  Two of the three "captions the way I write" were therefore ChatGPT drafts she took without editing.
- The carousel examples (Pasted text 20261013-134147) were three published carousels:
  - "You don't need another reminder to 'show up consistently.'" (19 Aug 2026);
  - "She invested $22,000 in ads during the first half of last year." (5 Aug 2026);
  - "We generated $90,000 in booked revenue from ads for a venue client in the first 90 days." (19 Jun 2026).

  Each has its siblings, engagement at scrape (5 to 6 likes) and a source note. The note on the $90K figure: "the $90,000 is 9 bookings × a ~$10,000 average booking — an estimate Whitney stands behind, not reported revenue".

---

## B. Whitney's own finished copy on Week 2 themes

The order is overlap risk, then theme. Each entry gives the date, format, provenance, text and conversation.

### B.1 Market research and "reviews aren't research". Already published in Week 2's own week (highest repeat risk)

**10 Jun 2026, list email [W]** (`6a296764`, node `48c9328c`). Pasted as "The marketing email below is being sent to our list this week". Subject: **"The question we ask every new client"**. Preview: **"I'm always surprised by the answer"**. Excerpt:

> "When we onboard a new advertising client for ELEVATE, our full-service advertising management program, we spend a lot of time getting to know their wedding business. … But then we ask a question that almost always catches people off guard: 'Have you ever surveyed your clients to find out why they actually booked?' Not asked for a review. Not collected testimonials. … And honestly? I don't think we've ever received a 'yes.' Which kind of blows my mind. … This is how ads bring in bookings, not just leads. … If you're tired of guessing how to make ads work and want an advertising strategy built around real buyer behavior instead of assumptions, I'd love to chat. Simply reply to this email…"

The CTA was her choice. On 10 Jun 13:21 [W], `6a26e8bc`: "I liked it better when it was: If you're tired of guessing… It was lower barrier, no?"

**10 Jun 2026, 10-slide carousel [W draft]** (node `519cc2f6`). Slide 1: "We ask this question to every new client / And I'm always surprised by the answer". Slide 4: "'No, but you can read our reviews!'". Slide 5: "Reviews are great. But they aren't really market research." Closing CTA: "DM us 'ADS'".

**10 Jun 2026, carousel caption [W]** (node `98033bc2`), after "You really fucking piss me off sometimes. You changed it again":

> "One of the biggest differences between our approach and most advertising agencies isn't how we build campaigns. It's where we start. … Of course, we do all of those things too. … Effective advertising doesn't start inside your ad accounts. It's created through a deep understanding of the couples you're trying to reach. … Different levels of support. The same philosophy. … send us a DM with the word ADS and let's talk."

Accuracy limits she set that day [W]:
- "We aren't conducting market research for our elevate clients yet, but we will be"
- "current state, I'd say before the ads happen we're focused on the foundations for success - messaging & positioning, landing pages, and nurture funnels"
- "I really don't want this to be about how wedding pros are getting their marketing wrong."

**8 to 9 Jun 2026, the VAULT training "Client Research for Marketing" [W]** (`6a26e8bc`). This is the training Whitney mentions on The Penny call ("Sometimes nobody shows up like today"). Her brief: "Here's what I always see when we onboard new full-serve clients… Every time, we ask if they have any surveys or market research, and I don't think I've ever gotten a yes." Her plan: "tomorrow (Tuesday) teasing the training in stories and recording a face to cam reel / Wednesday posting a b-roll reel / And Thursday posting a carousel / But this shouldn't be just teaching venues and wedding pros to go out and do their own market research… It's about highlighting how in depth we work with our clients and how this is a differentiator for us".

**Implication.** The Week 2 "reviews vs research" angle (system item 1, handbook angle 2) repeats a central point published in the same week. If used at all, it needs a new layer, such as what a first ELEVATE survey response actually changed. The export does not show one yet.

### B.2 "More leads won't fix this", lead follow-up and LeadLock

**30 Apr 2026, email to the WIA list [W final]** (`69d530e4`, node `47b48d7f`, "I think this is my final version"). Subject: **"More leads won't fix this…"**. She had written the day before [W]: "your last subject line sucked. It should be something like 'More leads won't fix this...'". Body, abridged:

> "Last week's Wedding Summit Series: Tech & AI Edition sparked a lot of ideas. … But the implementation is where things stall. … One of the clearest places this shows up is in how inquiries are handled. … Because more leads… more tools… even better marketing… don't fix the core issue if your follow-up system isn't built to support them. How quickly you respond. How consistently you follow up. How clearly you guide someone toward the next step. That's what actually determines whether a lead turns into a booking. … The marketing is working. The inquiries are coming in. But the follow-up process isn't structured to support it. Which means: – leads slip through the cracks – conversations stall – and bookings don't reflect the volume of inquiries. That's exactly why we built LeadLock. … 👉 Map out what this could look like in your business. Because the goal isn't just to get more leads. It's to actually book them. To better follow up, Daniela & Whitney"

Outcome, from the synthesis: no demos from the WIA list, while the near-identical host-sent version did book demos.

**How LeadLock works, in her words [W]** (`69d530e4`). These are the LeadLock facts any A01, A02 or A08 copy must respect:
- 16 Apr 2026: "LeadLock can go beyond consultations/tours with post-consult workflows, follow up communication, ongoing marketing emails, etc. It's just at the exact moment that someone says 'I want to book', they would create that contract/invoice in their event management software not their lead management software which is what LeadLock is"
- 16 Apr 2026, her line: "built inside LeadLock to support your inquiry process from 'We're interested...' to 'We're ready to book!'." And: "But it's the wedding couple saying it, not us, right? Are they not typically excited??"
- 21 Apr 2026: "The automated workflows are not meant to replace personalized communication. They are meant to support it. A potential client can tell the difference between an automated marketing email and a personalized email… It's almost like if there was an emergency or a super busy wedding weekend, their sales funnel doesn't break, it's still working, but yes, it will work better with their personal touch as well. So I think that is where this can really lighten the mental load."
- 21 Apr 2026: "in a sea of Calendly pages and Dubsado links, this instantly elevates the experience". This refers to the branded booking page in the Foolproof Follow-Up Advantage.
- 21 Apr 2026, her slide sub-lines: "This is where first impressions are made… and often missed." and "'Not yet' doesn't mean 'no' so don't treat it that way".
- 18 Dec 2025 (`6942fe07`): "We don't currently have LeadLock fully integrated with other platforms like Dubsado or Honeybook. Once a lead is ready for a proposal or contract, they are manually being input into those other CRMs..." This is directly relevant to A08 (Allie's Dubsado handoff). Any "fits alongside Dubsado" claim must say the handoff is manual unless the facts have changed.
- 20 Apr 2026: she used "many" instead of "most" in "Many wedding pros don't have a lead problem. They have a lead management problem." Her reason: "if I say 'most' it undermines the need for Wedding Industry Ads, a lead generation agency." That problem-swap hook was banned from 30 Apr 2026.

**Ghosting and no-shows, earlier statements [W]:**
- 7 Oct 2025 (`68e50a38`): "We started running ads for ourselves recently. It's resulted in a lot more inquiries and booked consultations. But several of those consultations have no-showed. Also, the calls that have booked from our Meta Ads are way colder… I know my clients are struggling with selling to cold traffic too". This became a VAULT training. Her edit: "This piece doesn't feel specific to the wedding industry".
- 16 Oct 2025 (`68f1454c`): "the consults we've had book from ads are VERY cold. Lots of no-shows. Low conversions."
- 14 Jan 2026 (`6967d2ea`): "Imo, when you're personally reaching out and getting ghosted, it feels a lot more personal thank if you have a system that is automatically sending nurture emails over the course of at least 30 days"
- 2 Oct 2025 (`68dde15f`): "because we are solely managing the Google Ads, all we can see is lead volume. We don't have any insights on lead quality or inquiry to tour conversions unless that information is shared with us".

**Implication for A01 and A02.** Whitney's established line is about the follow-up system: automation supports personal follow-up, so "the funnel doesn't break". It is not a diagnostic sequence. Her own scene is a busy wedding weekend.

### B.3 "Generating more leads is great…" and client strategy calls (25 to 29 Jun 2026)

**25 Jun 2026, Reel caption [W]** (`6a3d3a29`). Her draft is node `d8a7f415`; the as-posted text she pasted on 29 Jun is node `e41f373b`:

> "Generating more leads is great. But the real goal is predictable sales that don't rely on more effort from you. I know that can be hard to imagine. I've been there myself. Every inquiry depends on you. You have to respond quickly. You have to follow up. You have to keep conversations alive. You have to hope nothing falls through the cracks while you're busy serving the clients you've already booked. And if you're investing in ads, that adds another layer of frustration... You see the charges hit your credit card every month… But I had a conversation with one of our ELEVATE clients recently, and it reminded me why we do the work that we do. She told me: 'It feels like our sales are on autopilot.' They went from 17 events last year to 90 this year. … One creates activity. The other creates momentum. … If you're already investing in ads but know they aren't reaching their full potential, send us a DM."

Her corrections that day [W]:
- "I don't want this to focus so much on LeadLock. LeadLock is just one element of ELEVATE."
- "I hesitate to talk about every piece of their marketing working together. We are an ads agency. We don't touch every piece of their marketing."
- "The best clients for ELEVATE are currently dissatisfied clients of another ads agency"
- "ELEVATE potential clients aren't asking should we try ads. They are already trying, but their know in their gut there is missing potential"

**29 Jun 2026, list email [AI, approved after her body edits]** (node `489f339d`). Subject: **"It feels like our sales are on autopilot."** Her rejection of the first subject: "The subject line sucks". The rejected subject was "Predictable sales > more leads". The email carried "one spot available for ELEVATE in July" and a waitlist. Her accuracy fix: "there isn't an application for the waitlist. You simply join the waitlist". Her rejection of an anomaly frame: "It almost makes it sound like the results for this particular client are an anomaly".

**14 Aug 2026, client email [W-sent]** to Ali Epler of Diamond A (`6a8dfcd0`, node `a0aa480c`):

> "We're restructuring a bit, and moving forward, I'll be your main point of contact for anything related to ads. I'll be the one meeting with you for your strategy calls going forward, which I'm genuinely looking forward to since that's my favorite part of this work."

This is a usable founder truth: Whitney now runs every strategy call.

### B.4 Ad audits, freelancers, agencies and "hand-holding"

**31 Jul to 6 Aug 2026: the $22K-to-$70K story** (Erin; see D.4).
- Reel transcript [W], recorded by Whitney: "70K in new wedding bookings, all directly attributable to ads… having spent $22,000 on ad spend and agency fees and literally having nothing to show for it… if you have been working with, um, you know, an agency, you're seeing the credit card charges hit your card every month. But you're kind of in the dark… DM Accelerators".
- Caption [W, 30 Jul]: "Have you ever looked at your ad account and thought... 'I honestly have no idea if any of this is working.'"
- Carousel, 5 Aug [W, line by line]. Slide 1 as locked: "She invested $22,000 in ads during the first half of last year. Yet she was seriously questioning whether any of it was worth it. Because she couldn't answer one simple question: Were the ads actually working?" Slide 4 is built on her fact: "She told me that she had to hand-hold her agency. Questions weren't answered unless she asked. And when you don't know what you don't know, it's hard to know what to ask."
- Emails: 31 Jul "I honestly have no idea if this is working"; 6 Aug "You can't optimize what you can't measure", opening [W] "One thing we've learned over the years is that good marketing decisions start with good data."

**17 Jul 2026, one-to-one audit follow-up [W final]** (`6a5a2d83`, node `6e750227`, "I just don't want this to sound canned"):

> "I hope your audit with Carmen yesterday gave you a much clearer picture of what's holding your Google Ads back. That's exactly why we offer these audits. … Carmen mentioned to me that she identified a few key opportunities for improvement, including turning off your Performance Max campaign, restructuring the way keywords are split across campaigns, and creating a dedicated landing page for your ads traffic… We'd love to help you implement these recommendations together. Since you've already invested in your audit, your entire $297 will be credited toward your enrollment in the Google Search Accelerator."

Also [W]: "typically the solution is to turn performance max off entirely."

**5 to 16 Oct 2026: the annual Google Ads Audit Giveaway** (`6ac3c3eb`). It had just finished when the packs were made.
- Whitney reused the 2025 captions: "Wedding Pros: Are you totally sure your Google Ads are doing what they're supposed to? … Or if your freelancer or agency isn't showing you what's actually working…"
- New 2026 copy [AI, accepted]: "Google's recommendations aren't always what's best for your wedding business." / "Engagement season is right around the corner."
- Reel covers she chose: "Google Reps Aren't Your Marketing Strategist"; "Are Your Google Ads Actually Working?"
- Offer, as published: 5 complimentary audits, "normally $297", applications closed 16 Oct.

**Implication for A03** ("You can outgrow one-off ad audits"). WIA has just spent two weeks selling audits as the smart first step. In July Whitney positioned the audit as the start of a path, credited toward the Accelerator. A pack saying audits are not enough contradicts a live offer and ladder. Reframe it as what happens after an audit: who implements. Never as the limits of audits.

### B.5 Owners running their own ads: Accelerators, office hours, the VAULT

**Scope, in her words, 13 Apr 2026 [W]** (`69cd32e6`):

> "We don't build the foundation. We teach them what makes a good foundation. They build it. They can get our feedback. The learn our ad strategy and how to customize it for their business. They create the content. We launch the campaigns. We give them resources to interpret the data plus access to us on what to shift, change, try to improve results. It's not a one-time set up and then everything is great. Ads are a process. We are here to give them clarity throughout that process (when and if they ask for it). … We teach them how to interpret and think for themselves"

**15 Sep 2026, list email [W final, "Below is what we settled on"]** (`6aa98079`, node `3eb7f12d`). Subject: **"What I taught my clients this week"**. Key lines:

> "I taught a training yesterday morning that technically had nothing to do with running ads. … No targeting. No keywords. No campaign settings. **Because advertising doesn't start inside Google Ads or Meta Ads Manager.** … This is the part of advertising that doesn't happen inside the ad platform. … We didn't want to create another course that teaches wedding pros where to click inside Ads Manager… We help you get clear on the messaging. We build your initial campaigns for you. We look at the data together and teach you how to make decisions from it. Because running successful ads shouldn't mean buying a course, watching 47 videos, and then opening a blank ad account wondering what you're supposed to do next. You're building an advertising system around your business, with someone beside you who knows what that system needs to look like. … If you want to run ads but also know you need more support than an online course or YouTube can give you, that's exactly what the Ads Accelerators were built for. [Explore the Ads Accelerators →] Whitney"

Her accuracy check that day [W]: "Is it disingenuous to say 'we' about writing ads and landing page when ultimately it's up to the accelerator clients to do that but with our guidance?"

**16 Sep 2026, Reel scripts [W drafts]** (`6aaaba8c`):
- Reel 1 hook: "If I don't know why someone should choose your business, I have no business running ads for it."
- Her direction: "How do we make this not just about the clarity to write the ads… but about actually running ad campaigns that convert ideal clients? That's the transformation folks are actually after."
- And: "we need to be clearer about the fact that our work with clients drives results. We have real examples of wedding pros who've wasted thousands without results to now seeing a great ROI from advertising. I don't want to skirt around that. I want to own it"

**1 Oct 2026, captions** (`6abeb98d`). Her objections [W]:
- "That first line is terrible. It's not a great ad strategy if you're struggling"
- "I don't want to work with clients who have shitty websites. I think we need to start over."
- "I don't know that I want the caption to only be about the Ads Accelerators. No matter what capacity they work with us, the foundational work is going to take place no matter what. It's just a matter of who's doing it."
- "Also, nobody actually showed up live for the training, so I don't want to be disengenuous"
- "I feel like we've lost the plot. Does this follow Savannah's framework?"
- "Ok, I like it overall but can we make it more wedding industry specific. It's feeling kind of generic"

Approved results:
- Caption A [AI, approved]: "There's a lot more to running successful ads than knowing your way around Google Ads or Meta Ads Manager." Cover: "The best ad strategies / start BEFORE the ads."
- Caption B [AI, approved after her edits]: "Getting your wedding business in front of more couples isn't automatically going to lead to more bookings. Because couples aren't choosing a photographer, planner, venue or any other wedding pro in a vacuum. They're comparing options… *I found you.* to *I think you might be exactly what we're looking for.* to *How do we book you?* … Because more visibility isn't the goal. Turning more of the right couples into clients is."

**Office hours** (6 Oct 2026, `6a8dfcd0`, node `5f69db84`). Her two-line reply to Shannon, an Accelerator client [W-sent]:

> "Hi Shannon! I'm so glad to hear you're happy with the Meta Ads and the lead quality you're seeing! I also understand what you're saying about Google Ads. If you'd ever like for Carmen to take an additional look, please feel free to pop into her office hours. Best, Whitney"

**Implication for A05.** "Guided implementation" and "learning what to change and why" sit on the same message as the 15 Sep email and the 1 Oct captions. The Felipe example adds a live-support scene, but that scene had no payoff. A new pack needs an outcome, or a sharper founder stance (her "we teach them how to interpret and think for themselves").

### B.6 Google and Meta channel roles (A09, A06)

Whitney's own statements [W]:
- 30 Jan 2026 (`697cb7d4`): "what we find is that Google captures high-intent searches first. Meta then retargets them and drives conversions."
- 30 Jan 2026, a client story: "even after a month of great results, she asked us to turn Google Ads off. Because when we looked about results in isolation, Google wasn't driving the conversions, Meta was, but we had to explain that Meta's performance increased because Google was driving the traffic first, so Meta could better retarget." Also: "the shift wasn't just about increasing ad spend. It was about diversifying strategy." **This is A06 and A10 in her own words, already told in January's giveaway warm-up emails.**
- 1 Apr 2026: "Yes, Meta can create demand, but it is also a very powerful retargeting tool. This piece is very appealing to our clients."
- 13 Jul 2026, sent email to a venue prospect, "K one final review before I send": "We typically see the best results when venues advertise on both platforms because each plays a different role in helping couples find your venue. … These ads are designed to introduce your venue to couples and keep it top of mind while they're dreaming and planning through retargeting. … when couples move from inspiration to actively researching venues, Google is still one of the highest-intent places they search. … we're never locked into a one-size-fits-all approach… Some of our venue clients ultimately invest more heavily in one platform than the other".
- 20 Aug 2026: "I think there needs to be a better explanation about how Google and Meta ads work together and have a compounding effect. We aren't just using Meta for couples who haven't heard of them. Retargeting is a big piece of it."
- 4 Jan 2026 (a guardrail): "If someone is just leaning towards the Google Search Accelerator, I don't want this slide to make that strategy feel insufficient"
- Historical: 2024 "The Ultimate Advertising Power Couple" training and email ("running evergreen ads on both Google AND Meta!").

**Implication for A09.** The 13 Oct A09 pack hedged ("may", "eligible", "every visitor won't necessarily be reachable") and ended "Save this". Whitney states the point confidently and with a client result. Her "Google drove the traffic, Meta got the credit" story is the stronger, true version.

### B.7 Pausing campaigns and budget decisions (A10)

- 30 Jan 2026 [W]: the client who asked to turn Google off (above).
- 1 to 6 Oct 2026 [W-sent]: Shannon turned off her Google Ads. Whitney did not argue ("I also understand what you're saying about Google Ads").
- 16 Sep 2026 [T Slack recap of Whitney's call] (`6aab0052`): "Please **turn off the Philadelphia videography campaign**. It has spent nearly $300 without gaining traction".
- 15 Sep 2026, The Penny, from a Zoom AI summary relayed by Gisselle: "Whitney confirmed that the budget is healthy and recommended not making any changes until seeing full funnel data."

**Implication for A10.** Pausing is a routine, low-drama judgment in her account work. The Penny's real story is better than "pause": the old campaigns had "good visibility and website traffic but failed to track leads"; the new conversion-focused campaigns produced 105 leads in a month (see D.2).

### B.8 Venues, and capacity and "breathing room"

- **19 Jun 2026, carousel:** "We generated $90,000 in booked revenue from ads for a venue client in the first 90 days." Uses the Five Foundations list. CTA "ROI".
- **18 to 20 Aug 2026, Reel, carousel, captions and email:** "What would happen if your wedding business didn't post on Instagram for the next 10 weeks?" This is a planner client, not a venue.
  - Her ask [W, 13 Aug]: "Should I kick off with talking about her not posting in 10 weeks. Should we pose it as a question??"
  - Her fact [W]: "she felt like she had permission not to post for 10 weeks straight because she knew the ads were running, it gave her the breathing room."
  - Carousel slide 1: "You don't need another reminder to 'show up consistently.' / You need a marketing strategy that accounts for the fact that sometimes, you can't."
- **January 2026:** "Being good isn't enough if couples can't find you" (email and carousel).
- **13 Oct Week 1 critique, ChatGPT in her chat:** venue positioning is "Very high" potential, for example "One of the biggest marketing mistakes an all-inclusive wedding venue can make is assuming couples understand the value of what's included."

**Implication.** Capacity ("I couldn't do it all") is spent for now. A02's real insight is the venue's own capacity: no Saturday tours, staff with babies, Sundays as "our ugliest day". That is a different and fresh angle from the planner's capacity, but it needs Allie's permission and must stay unnamed.

### B.9 Other on-brand finals for reference

- **1 May 2026, email [W final]:** "A smarter way to get in front of the right clients". It keeps "There's a pattern we see over and over again with wedding pros…" in the email, a hook she rejected for the Reel the same day. It also uses "It's not that you aren't getting inquiries. / It's that you're not getting in front of enough of the right people, consistently." Reel hook: "You can't book clients who never find you."
- **2 Jun 2026, subject line she wrote [W]:** "Visibility isn't something you earn." Preview: "You engineer it."
- **22 Jan 2026, her brief for content [W]:** "How can we turn the takeaways themselves into content that isn't purely educational but ties into how we serve clients and presents us as the solution."

---

## C. Whitney's reactions to hooks, subject lines and CTAs (mid-2026 onward)

Every row is [W] unless marked.

| Date (UTC) | Conversation | Verbatim | Applies to |
|---|---|---|---|
| 28 Apr | `69d530e4` | "your last subject line sucked. It should be something like 'More leads won't fix this...'" | Email subject: she wrote the winner |
| 1 May | `69c14c0f` | "Don't love the subject line. And this line at the beginning of the email feels contradictory to it: A lot of you are not struggling to book." | Subject; internal contradiction |
| 1 May | `69c14c0f` | "We did a market research survey recently and asked clients what they struggled with the most before working with us, and the majority said 'Getting in front of enough of the right people consistently'" | Her audience-language source |
| 1 May | `69c14c0f` | "'There's a pattern we see over and over again…' this is a terrible hook. I need for the reel to have a very strong hook because that is all that it will be - a strong hook on top of b-roll… The carousel… I don't want it to be the hook of the reel verbatim" | Reel text hook; one hook per format |
| 1 May | `69c14c0f` | "I will use this for the reel hook: You can't book clients who never find you." | Approved Reel hook |
| 13 May | `6a026ad2` | "I like this one: If you're seeing this, this is your sign to create a more predictable inquiry pipeline for your wedding business." | Approved b-roll text hook |
| 13 May | `6a026ad2` | "No, that hook sucks. Caption needs to go from cold to sold." | Caption hook |
| 13 May | `6a026ad2` | "By repeat, I meant repeat ideas, not repeat language. The hook of this caption is identical to the hook of the caption for the carousel" | Sibling hooks |
| 13 May | `6a026ad2` | "That hook speaks to someone who's in a place of desperation. That is not our ideal client" | Audience screen |
| 13 May | `6a026ad2` | "I like this: Whether you want hands-on support or a proven strategy you can implement with guidance, we have options designed for different stages of business growth." | CTA covering both offers |
| 18 to 19 May | `6a06061f` | "Do I need a CTA?" / "I feel like an email really needs a CTA though, no?" / "The email is fine, but the subject line sucks" | Email CTA; subject. The sent subject was "The goal isn't going viral" |
| 2 Jun | `6a1efd89` | "I don't like this. The subject line and opening line are played out… We need to speak to those with a growth mindset, not a lack mindset" | Subject; audience |
| 2 Jun | `6a1efd89` | "What if the subject line is Visibility isn't something you earn. Preview text: You engineer it." | Her subject line |
| 10 Jun | `6a26e8bc` | "I liked it better when it was: If you're tired of guessing… Simply reply to this email… It was lower barrier, no?" | Email CTA: reply beats offer pick |
| 10 Jun | `6a296764` | "I think you took too many liberties. I'd like for it to be a bit closer to the actual email" | Repurposing email to carousel |
| 10 Jun | `6a296764` | "Wtf? Why did you complete change the opening??" | Refine, don't replace |
| 16 Jun | `6a0c862f` | "The subject and hook of the first email are contradictory to a lot of our own recent marketing. I don't like this angle" | Consistency with recent content |
| 18 Jun | `6a0c862f` | "I kind of think we need something more straight to the point, so they know from the subject that they're being invited to a valuable event." | Event-invite subject |
| 25 Jun | `6a3d3a29` | "That hook is terrible and so generic. Did you actually follow the caption structure I prescribed?" | Caption hook; Savannah framework |
| 29 Jun | `6a3d3a29` | "The subject line sucks" (rejecting "Predictable sales > more leads") | Subject. The sent one was the client quote |
| 29 Jun | `6a3d3a29` | "No, I don't like this direction at all. You took way too much liberty… Stay true to the first version" / "You are very obtuse. Here's my edit:" | Refine mode |
| 29 Jul | `6a68eccd` | "Currently it's 'Build a Business You Control'. That feels generic." / "Right now we have 'How Couples Actually Choose'. How do we feel about that?" | Reel covers |
| 30 Jul | `6a4d4971` | "I think the hook is way too generic. If you ask a question that is so general, it's how much business did your marketing produce? A business owner might say all of it. What they don't actually have the data on is which marketing channel produced what." | Hook precision |
| 4 Aug | `6a721147` | "This is a good starting point but it feels kind of generic, let's edit it slide by slide." / "Isn't that hook the same as what we used to accompany the reel?" | Carousel slide 1; sibling hooks |
| 13 Aug | `6a73993f` | "Whitney here… I don't think the opening is really a hook. Should I kick off with talking about her not posting in 10 weeks. Should we pose it as a question??" | Reel hook: she chose the concrete question |
| 13 Aug | `6a73993f` | "I'm hesitant to use the exact same hook for this carousel as we're using for the reel and email..." / "Yes, love the new hook." | Sibling hooks; approval |
| 23 Sep | `6ab41e90` [T] | "are we doing this every time? If you're ready to build advertising… DM me 'ADS.'… Should we be switching it up every time" | CTA repetition (team) |
| 15 to 16 Sep | `6aaaba8c` | "I'm also debating making the solution/cta more generic about working with us and DMing me Ads than mentioning the Accelerators specifically." | CTA scope |
| 1 Oct | `6abeb98d` | "That first line is terrible. It's not a great ad strategy if you're struggling" | Caption hook logic |
| 1 Oct | `6abeb98d` | "Ok, that caption and punchy cover are good to go." Cover: "The best ad strategies / start BEFORE the ads." | Approval |
| 8 Oct | `6ac3c3eb` | "I'm going with the first recommendation." Cover: "Google Reps Aren't Your Marketing Strategist". / "I'll go with option 1." Cover: "Are Your Google Ads Actually Working?" | Reel covers |

**Email subject lines she wrote or sent in 2026:**
- "More leads won't fix this…" (30 Apr)
- "A smarter way to get in front of the right clients" (1 May)
- "The goal isn't going viral" (19 May)
- "Visibility isn't something you earn." / "You engineer it." (2 Jun)
- "The question we ask every new client" / "I'm always surprised by the answer" (10 Jun)
- "It feels like our sales are on autopilot." (29 Jun)
- "I honestly have no idea if this is working" (31 Jul)
- "You can't optimize what you can't measure" (6 Aug)
- "She didn't post on Instagram for 10 weeks" (20 Aug; the published-carousel metadata adds 😱)
- "What I taught my clients this week" (15 Sep)
- From April: "If your ads aren't performing like they should, read this" (14 Apr) and "If you want better ad performance, read this".

The pattern is a quote, an observation or a plain first-person statement, mostly without emoji. None uses a rhetorical "What happens next? 👀" form.

**Reel hooks she approved:**
- "You can't book clients who never find you." (b-roll text)
- "If you're seeing this, this is your sign to create a more predictable inquiry pipeline for your wedding business." (b-roll text)
- "Generating more leads is great." (caption)
- "70K in new wedding bookings, all directly attributable to ads." (spoken)
- "What would happen if your wedding business didn't post on Instagram for the next 10 weeks?"
- "If I can't tell from looking at your website or Instagram why couples should choose to book you for their wedding day, then we don't have any business running your ads, at least not yet."
- "I taught a training for Ads Accelerator clients this week that technically had nothing to do with running ads."

---

## D. Week 2 clients, prospects and situations

### D.1 Diamond A Ranch, Ali (not "Allie") Epler, owner (venue, Texas)

**Spelling.** She signs "**Ali Epler**, *Owner*, Diamond A Ranch Events", and Whitney writes "Hi Ali". The transcript label is `aliepler`. Team notes and the 13 Oct angles spell it "Allie". Use **Ali** if she is ever named. Normally she should not be named.

**What happened after Week 2** [W-sent, relayed by Gisselle in `6a8dfcd0`]:

- **17 Aug.** Ali: "I was in discussion with Fallen about adding videos to some of our lead messaging." Whitney: "I'll take over for any additions or changes you'd like to make to the email/text sequences including incorporating videos. We had to do some testing to figure out the best way to add the videos to SMS messages… I'm thinking we could send your personal video via SMS about 30 minutes after the lead comes in". The existing text then read: "This is Ali + Dani at the Diamond A Ranch… The best way to know if it's the right venue is to walk the property. And it is truly better in person, pictures don't do it justice!"
- **31 Aug recap [W-sent].** "Send us a selfie photo for use in tour confirmation messages / Send us a couple of indoor/outdoor photos of the venue for use in early SMS messages". Ali sent five photos: "I tried to make them more appealing to gen z style versus so staged."
- **9 Sep internal meeting** (transcript excerpt). Tina Henares: "those are all done. And we put the selfie picture in the tour confirmation text… she had sent over. Other pictures, so I put them in the first couple SMS texts… And I created a landing page for the packages". This is **the Week 2 recommendation implemented**: a personal connection before a far-off tour. Outcome data is not shown.
- **11 Sep, August report.** ChatGPT's draft mentioned "a dip in Google leads, tour volume remained steady". **Whitney's sent version stripped every performance claim** [W-sent]: "Inside the report, you'll find a full breakdown of performance along with a video walkthrough… Please let me know of any questions or concerns before and next call."
- **22 to 25 Sep, AI Max.** Ali forwarded advice from her own "AI agent", which named campaigns that do not exist. Viktor, WIA's AI agent [AI], checked the account and reported: "one live Search campaign, one ad group, 17 phrase keywords". It also said Google showed "**19 form-lead conversions Sept 1–22 on $367.80** (vs 5 in all of August, $506)… Google-reported only… I'd verify against the CRM before quoting it to Ali." Whitney's sent reply [W-sent]: "The change your AI agent mentioned is real, but your Google Ads account and your campaign is not affected… whether it's something we'd want to test intentionally in the future."
- **26 Jun 2026** (`6a3efb83`, [AI] note): "The Diamond A guide is more functional, while Dos Palomas feels much more premium because it sells the experience before the price."

How Whitney talks to this account: warm, brief, logistics-first, and no numbers in writing. She offers a call, and she owns changes personally ("I'll take over").

### D.2 The Penny, Lauren Christensen, Director of Sales & Operations (venue, San Luis Obispo area, CA)

- **Week 2 call** (Pasted text 9). Lauren on the valley cities: "price sensitivity… a lot of inquiries, but they were not super. quality leads". Whitney: "they were very specifically only targeting San Luis Obispo… we definitely should open it up and include, like, the Bay Area, include LA, include San Diego". The same call contains Whitney's survey idea (B.1).
- **28 Aug 2026.** Tirzah Caffee (a venue consultant) introduced Lauren to LeadLock: "I just finished a deep dive analysis on Lauren's packages and marketing materials… just $147 a month. Totally worth every penny!" This price is a third party's statement, so treat it as internal.
- **11 Sep.** "this is **The Penny's first monthly report**" [AI note].
- **15 Sep strategy call** (Zoom AI summary relayed by Gisselle; not Whitney's prose):
  - "previous campaigns had good visibility and website traffic but failed to track leads. The new conversion-focused lead generation campaigns have generated 105 leads in the past month alone, compared to zero leads from the previous setup."
  - "cost per lead of $8, which is below the typical $10-15 range for venues".
  - "Whitney confirmed that the budget is healthy and recommended not making any changes until seeing full funnel data."
  - "Lauren shared that sales for 2027 have been lower than normal, so she implemented price drops for events booked through May".
  - LeadLock onboarding with Danielle followed on 16 Sep.
- **13 Oct.** Lauren: "for leadlock the incentive is only for weddings!"
- **Use.** The Penny is now a strong before-and-after (0 to 105 tracked leads). It is private, so permission is needed before using the figures (see the `results_register` rule). The lower 2027 sales and the price drops are sensitive and must never appear in public copy.

### D.3 Felipe (Week 2 T07 is **Felipe Cortes**)

- The only other Felipe in the export is **Felipe Luna** (June 2025, `6852f632` "Ad Review and Improvements", "Felipe and his boss Beth"). That is a different, earlier client. **Do not merge them.**
- Felipe Cortes appears nowhere outside the Week 2 transcript and the 13 Oct simulation. Nothing records whether his experiment ever ran.

### D.4 Erin is Erin Smith, Carroll Hall, Brooklyn (venue marketing lead)

- 5 Oct 2025 (`68e04f1c`, [AI] list): "Erin Smith — Carroll Hall (Brooklyn, NY)… excellent fit for **Google Search Accelerator**". She later became an Ads Accelerator client; the export does not record the enrolment itself.
- She is **the $22K-to-$70K Accelerator client**. The case study ran 7 to 30 Jul (`6a4d4971`). The Reel, caption, carousel and two emails ran from 31 Jul to 6 Aug.
- Whitney [W, 16 Jul]: "we can't actually use Erin's name in our marketing."
- Her facts [W]:
  - "The first half of last year, they spent $22K on ad spend and agency fees with nothing to show for it. Compare that to the first half of this year… only $6K spent… $70K in new wedding bookings";
  - "she had to hand-hold her agency";
  - "she's a marketing director at a wedding venue in a saturated urban market".
- The team's 5 Aug brief: "the script video Whitney recorded about Erin's/Carroll Hall case study".
- **Week 2 T07** is Erin's office-hours session about a **corporate-events** campaign (41 clicks, the wedding banner on the corporate page). Her site is Carroll Hall.
- **9 Oct 2026 office hours** [T, Carmen's recap]: "Carmen helped Erin diagnose any issues causing a slow down of leads in her ad campaign. Noticing a trend of micro wedding searches… recommending a separate ad group for micro weddings… a separate landing page".
- **Risk.** A04 or A05 content built on Erin's T07 session would describe the most-published client of summer 2026, whose name is banned, whose leads were slowing in October, and whose identity could be linked through "corporate campaign at a venue". Use only as a heavily anonymised process scene, or not at all.

### D.5 Noam (Noam Wolf, prospect, T11)

He appears nowhere outside Week 2 and the 13 Oct material. There is no record of an audit booked. Facts in his call:
- "I already have 5 different campaigns that I built";
- "one for weddings, one for corporate";
- "reading and watching for me, sometimes I can read the same paragraph 1400 times and nothing gets in";
- "I can't spend more now".

Whitney's quotes to him are internal pricing ($197 audit), so keep them out. The July 2026 audit price was $297, credited to GSA; the published giveaway value was $297.

### D.6 Ivor (T10; the transcript label is "iver", and Whitney says "Hi, Ivor")

He appears nowhere else. The 13 Oct cards say "periodic freelance audits", "an ongoing relationship and better efficiency" and "how personal his marketing felt". The A09 email describes "someone searching for his specific kind of elopement experience". Prospect only. Never imply he hired WIA.

### D.7 Shannon (Shannon Lee, Love Like Wild, Orlando photographer; Accelerator client)

- **Not in the Week 2 transcripts.** No match for "Shannon" in the 11 files.
- 8 Sep 2026: "I will check out that link and book a time soon."
- 24 Sep: the team checks in because she "didnt [attend office hours] in this 4 weeks".
- 1 Oct, Shannon: "I've made the decision to turn off my google ads… it wasn't performing well in the Orlando area. I'm very happy with my Meta ads! … I'm very happy with the lead quality currently."
- 6 Oct, Whitney's two-line reply (B.5).

Voice lesson, from Gisselle's thread [AI note]: "Whitney didn't push back on Shannon's decision or make the response feel like another assignment."

### D.8 People and team facts the packs must respect

- **Fallon Looney** ran the Week 2 calls with Whitney and left in mid-August 2026 ("We're restructuring a bit"). Do not write "Fallon and I" in present-tense copy.
- **Danielle McGinnis** handles LeadLock (T09; "Danielle will continue to be your go-to for anything LeadLock related").
- **Tina Henares** builds LeadLock sequences and landing pages.
- **Carmen Cruickshank** runs the Google Ads weekly office hours.
- **Jacqueline Hood** is "a real expert in landing pages" (Carmen, T07).
- **Viktor** is an AI agent.

---

## E. Findings for the separate "system improvement" document

1. **Store the attachments.** Every critique on 13 Oct worked only because the developer pasted Content Atelier output (`Pasted text(8)`, `(9)`, `(10)`). Their text is in the export's `.dat` files, which the 18 Oct analysis did not read. The pipeline should ingest `conversation_asset_file_names.json` and the `.dat` texts, not only `mapping` parts.
2. **The export's `mapping` nodes have no `children` arrays**, only `parent` links. Any parser that walks `children` silently returns nothing, as `gptx.py` did at first. Branches (agent mode versus chat mode, regenerated answers) must be rebuilt from `parent`.
3. **Branch and author detection is essential.** `6acde8a5` and `6acdefc0` start with Whitney's five turns, then switch to the developer writing in the first person ("i want the captions the way i write"). Without a cut-over marker, a voice learner would take the developer's samples, including 2024 emails, as Whitney's taste.
4. **A recent-published register would have caught the main repeat.** Market research and reviews went out on 10 Jun 2026, in Week 2's own week. ChatGPT caught it from its knowledge-base memory; Content Atelier did not. The register should also hold:
   - the UVP cluster (15 Sep to 1 Oct);
   - the audit giveaway (5 to 16 Oct);
   - the $22K cluster (31 Jul to 6 Aug);
   - the 10-week cluster (18 to 20 Aug);
   - "More leads won't fix this" (30 Apr);
   - "sales on autopilot" (25 to 29 Jun).
5. **Follow the story past the week.** Each Week 2 account has a documented sequel in later client email threads (`6a8dfcd0`, `6a95e197`, `6aa43a8b`, `6aab0052`):
   - Diamond A: SMS video, selfie and photos implemented by 9 Sep; Google form conversions 19 vs 5;
   - The Penny: 0 to 105 tracked leads at $8;
   - Erin: micro-wedding slowdown in October;
   - Shannon: paused Google in October.

   A pipeline that reads only the week's transcripts writes "results-free" stories and stale boundaries ("ideas to discuss and test"). A per-client timeline keyed to names in the transcripts would let a brief say what actually happened, permission allowing.
6. **Resolve identities across sources:**
   - `aliepler`, "Allie" and "Ali Epler" are one person;
   - "iver" is Ivor;
   - "Erin" in T07 is Erin Smith of Carroll Hall, the anonymised $70K client;
   - Felipe Cortes is not Felipe Luna.

   Without this, a privacy rule ("never name Erin") cannot fire, and a do-not-merge rule cannot protect Felipe.
7. **Keep team and offer facts with dates.** Fallon left in mid-August. Whitney runs all strategy calls from August. LeadLock's contract handoff to Dubsado or HoneyBook is manual (Dec 2025). Audit prices were $197 on the June call, $297 in July, and "$297 value" in the October giveaway. The ELEVATE waitlist has no application.
8. **Mark the provenance of "her" samples.** Two of the three caption samples the developer called "the way i write" were ChatGPT drafts she accepted without edits on 5 and 8 Oct. Her truly typed prose is visible in captions such as `98033bc2` (10 Jun) and `d8a7f415` (25 Jun). Her canvas edits ("Made some edits. Thoughts?") are invisible in the export; only the before and the next ChatGPT echo survive.
9. **Never let boundary text into public copy.** ChatGPT warned (brief critique) that "the caution has become part of the proposed public content". The 13 Oct packs then did exactly that. Boundaries belong in a reviewer note. Public copy should say what is true confidently, or omit it.
10. **CTAs are an inventory.** Whitney uses:
    - DM "ADS" (Instagram);
    - reply to the email (her "lower barrier" choice);
    - "Explore the Ads Accelerators →";
    - "Map out what this could look like in your business";
    - "DM Accelerators", "DM ROI", "DM ELEVATE";
    - "Comment 'Google Ads Audit'";
    - no CTA on some clips ("2 clips without CTA and the thirds case study clip with CTA", team, 28 Jul).

    The 13 Oct packs used "ADS" in 15 of 20 pieces. A rotation rule per week is needed.
11. **Savannah's caption framework is applied, and Whitney checks it** ("Does this follow Savannah's framework?", 1 Oct; "Did you actually follow the caption structure I prescribed?", 25 Jun). Her versions of it:
    - "Hook / Problems, Desires, Symptoms / Main Point / Transformation / CTA" (25 Jun);
    - "hook, problem, transformation, solution, cta" (4 Aug);
    - "hook, problem, transformation, solution (our accelerators)" (15 Sep).

    The pipeline should hold one dated canonical version and tag each beat in drafts.
12. **The audience screen fires on hooks, not only angles.** "It's not a great ad strategy if you're struggling", "That hook speaks to someone who's in a place of desperation", and "I don't want to work with clients who have shitty websites" all come from her objection to a hook or opening line. Lint the first line of every asset against the growth-stage screen.
13. **Honesty about events.** "nobody actually showed up live for the training, so I don't want to be disengenuous" (1 Oct). "Sometimes nobody shows up like today" (Week 2 transcript of The Penny call; the date of 9 Jun is inferred from the VAULT training plan, "tomorrow (Tuesday)", made on 8 Jun). Copy must not imply attendance, a live audience or reactions that did not happen. Claims about workshops need an attendance fact.
14. **Whitney's sent client emails are much shorter than ChatGPT's drafts, and carry fewer numbers.** Examples: the Diamond A August report, and the replies to Shannon and to Ali on AI Max. The one-to-one voice register differs from list-email voice. Gisselle's thread keeps "email sent by whitney" pairs, which form a ready preference dataset of drafts against finals.
15. **The client-side "AI agent" phenomenon.** Ali's own AI agent invented campaigns ("Fort Worth, Granbury, Weatherford…"). Viktor caught it. This is a timely, true founder topic (WIA checks the account instead of trusting AI guesses), but it is client-specific and must stay private unless anonymised.

---

## F. What this means for the new Week 2 packs (practical cautions)

**Avoid, as central points, anything already said since June 2026:**
- reviews are not market research, or "the question we ask every new client";
- advertising starts before the ad platform, or UVP;
- more leads won't fix weak follow-up;
- "generating more leads is great";
- you can't optimize what you can't measure, or hand-holding an agency;
- ads give you breathing room;
- Google reps, audits, or "Are your Google Ads actually working?".

They may appear as supporting lines, phrased differently.

**Underused, true and fresh in the Week 2 material, with her sources:**
1. **What a venue owner knows that the pipeline doesn't.**
   - Ali: tours booked "more than 2 weeks out… they're gonna find something else".
   - The real operating limits ("we don't do tours on Saturdays when we have weddings").
   - Whitney's "let's FaceTime, and I'll show you everything, like, live in action".
   - Then **what WIA actually built** (a welcome video by SMS, a selfie before the tour, real photos in the first texts), as long as no results are claimed.

   This fits her "show what we actually do" demand and her 21 Apr LeadLock truth: automation supports the personal touch.
2. **"We'd rather be your guinea pig"** (T09): WIA tests a tool on itself before offering it to clients, and the AI-agent anecdote (D.1). This is a founder-forward, ATTRACT-capable stance. Check current status first, since the source shows only planning.
3. **Channel credit**: "Google drove the traffic, Meta got the credit." This is her own January story, retold with a Week 2 prospect who had "overlooked" retargeting. It must be confident, not hedged.
4. **The Penny before-and-after** (no tracked leads, then 105 a month), if permission is obtained. Otherwise use the decision logic only: open up targeting to where her ideal clients actually come from, using her knowledge of her market.

**Language rules, from her own reactions:**
- Use "Ali", or better, no name.
- Never say "Fallon and I".
- No "👀" subjects.
- No hedged boundary sentences.
- Vary the CTA.
- Write slide 1 and Reel hook 1 as a concrete scene or stance, never a reassurance.
- Do not reuse a hook across siblings.
- Write to owners who are "already trying, but… know in their gut there is missing potential".
