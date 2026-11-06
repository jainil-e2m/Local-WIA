import { ContentIdea } from '../types/atelier';
import { prepareFathomContentBrief } from './fathomContentBriefs';
import { hydrateFathomMockPack } from './fathomContentPacks';

// Editorial mock proposals built from the six-recording export on 6 October.
// Four unique conversations: two Google captures and two Meta captures overlap.
// Sources are transcript-matched; recording attribution and publication consent
// remain unverified. Scores are editorial estimates, never search-provider data.
export const FATHOM_EDITORIAL_WEEK = '2026-10-05';
const createdAt = '2026-10-06T12:00:00.000Z';
type Evidence = NonNullable<ContentIdea['editorialContext']>['sources'][number];
const recordings: Record<string, { meeting: string; recordedAt: string; url: string }> = {
  '189606894': { meeting: 'Google Ads Meeting · 5 Oct', recordedAt: '2026-10-05T15:02:45Z', url: 'https://fathom.video/calls/849503794' },
  '189649334': { meeting: 'Meta Ads team review · 5 Oct', recordedAt: '2026-10-05T16:02:30Z', url: 'https://fathom.video/calls/849595108' },
  '189685435': { meeting: 'WIA Weekly Meeting · 5 Oct', recordedAt: '2026-10-05T17:01:42Z', url: 'https://fathom.video/calls/847484025' },
  '189088443': { meeting: 'Whitney + Alina · 2 Oct', recordedAt: '2026-10-02T14:31:19Z', url: 'https://fathom.video/calls/845873735' },
};
function passage(recordingId: string, timestamp: string, speaker: string, quote: string, role: Evidence['role'], interpretation: string): Evidence {
  const recording = recordings[recordingId];
  const seconds = timestamp.split(':').reduce((total, part) => total * 60 + Number(part), 0);
  return { recordingId, ...recording, timestamp, speaker, quote, role, interpretation, speakerVerified: false, url: `${recording.url}?timestamp=${seconds}` };
}
const industryContext = {
  title: 'WeddingPro · Vendor insights from the 2026 Real Weddings Study',
  url: 'https://pros.weddingpro.com/blog/entrepreneurship/real-wedding-study-vendor-insights/',
  summary: 'US industry context: the report discusses personal celebrations, guest experience, clear value, and the continuing importance of human connection. This informs the framing; it does not verify WIA client outcomes or demand for this angle.',
};
const testingContext = {
  title: 'Google Ads Help · Monitor your experiments',
  url: 'https://support.google.com/google-ads/answer/6318747?hl=en',
  summary: 'Experiment reporting distinguishes statistically significant results from insufficient data. Equal elapsed time alone does not establish a winner in the sequential page observations discussed here.',
};
const voiceReference = { title: 'Founder Voice Guide v2.0', section: 'Teach principles before tactics; explain why before how; earn the CTA.' };
const questionResearch = (searchQuery: string, questions: string[], note: string): ContentIdea['research'] => ({
  origin: 'editorial', searchQuery, googleTrendsScore: null, trendDirection: null,
  peopleAlsoAsk: questions, autocomplete: [], forumDiscussions: [], note,
});
type Proposal = Pick<ContentIdea, 'id' | 'title' | 'subtitle' | 'client' | 'score' | 'scoresBreakdown' | 'suggestedCta' | 'angleRationale' | 'editorialContext' | 'brief' | 'research'>;
function angle(proposal: Proposal): ContentIdea {
  const primary = proposal.editorialContext!.sources.find(source => source.role === 'Primary passage')!;
  return {
    ...proposal, isMock: true, mockLayoutVersion: 4, badge: 'Team Strategy', scoreBasis: 'editorial',
    daysAgo: 'Prepared 6 Oct', createdAt, editorialWeek: FATHOM_EDITORIAL_WEEK,
    timestamp: primary.recordedAt.slice(0, 10), sourceType: 'fathom',
    primaryQuote: primary.quote, sourceDetails: `${primary.meeting} · ${primary.speaker} · ${primary.timestamp}`,
    gate: 'gate1_angle',
  };
}

const SOURCE_ANGLE_PROPOSALS: ContentIdea[] = [
  angle({
    id: 'mock-fathom-2026-10-05-fair-comparison',
    title: 'Before You Fix the Form, Check the Comparison',
    subtitle: 'Two landing pages used the same form. The more useful question was whether the evidence supported changing it.',
    client: 'Venue landing-page review', suggestedCta: 'Accelerators', score: 87,
    scoresBreakdown: { proof: 82, audiencePain: 91, offerFit: 89, recurrence: 73, novelty: 88, demand: 65 },
    angleRationale: { source: 'editorial', topic: 'Make the next marketing change a decision you can explain.', points: [
      { label: 'Angle & gist', text: 'An early difference in leads can tempt a venue owner to shorten a form immediately. Whitney checked the forms first: they were identical. Build the angle around asking what changed, who clicked, and whether the comparison is fair before selecting a fix.' },
      { label: 'Why it matters', text: 'A venue inquiry is one step toward a tour and a booking. Owners with modest traffic can overreact to a handful of leads, make several changes, and lose the ability to learn which decision helped.' },
      { label: 'Founder fit', text: 'This is Whitney demonstrating “better decisions outperform better tactics.” Her willingness to investigate her own team’s preferred page makes the lesson credible and grounded.' },
      { label: 'Content direction', text: 'Open with the same-form observation. Explain a fair comparison, then show why Google prospecting and Meta retargeting can require different interpretations. Give the audience a decision checklist.' },
      { label: 'Commercial opportunity', text: 'Connect the lesson to the Accelerators’ guided strategy and interpretation. Invite readers to describe the change they are trying to evaluate; Whitney chooses the final CTA.' },
      { label: 'Evidence boundary', text: 'The team reported 7 leads from 100 clicks versus 2 from 64 in different windows. These are early observations, not proof of page superiority. The Meta review supplies a counterpoint; duplicate recordings add no recurrence.' },
    ] },
    editorialContext: {
      audience: 'Established venues and wedding professionals running ads who make website decisions from small weekly lead counts.',
      objective: 'Help owners replace reactive edits with a clear, testable question and ask more useful questions about their reports.',
      funnelStage: 'Warm', pillar: 'Education · Strategic decision-making',
      beliefShift: 'From “fewer leads means the form needs fixing” to “first establish what changed and whether the comparison supports that explanation.”',
      suggestedInvitation: 'Reply with the landing-page change you are trying to evaluate. Offer fit and destination require Whitney’s confirmation.',
      sources: [
        passage('189606894', '00:01:51', 'Whitney Hodges', 'The forms are exactly the same.', 'Primary passage', 'The diagnosis starts by checking the proposed explanation against the actual pages.'),
        passage('189606894', '00:00:28', 'Carmen Cruickshank', "is funny, because, so basically, Victor was saying that since we moved it back to the old landing page, before when we had the LeadLock landing page, we got seven leads per 100 clicks, and then since we switched it back, it's gotten, like, 64 clicks and only two leads, which isn't like, like, it says it's a decrease, which I understand, but I feel like we don't have enough time for, like, actual data, you know, so I feel like I'll just leave it for now, but it says to shorten the form.", 'Supporting passage', 'Reported lead/click counts provide the trigger, with an explicit concern about insufficient observation time.'),
        passage('189606894', '00:09:30', 'Whitney Hodges', "So, let's, like, give it a full eight days, like we did for the LeadLock page before we decide.", 'Supporting passage', 'A request for comparable windows, not a universal eight-day testing rule or a significance finding.'),
        passage('189649334', '00:27:00', 'Jacqueline Hood', "The website has been working so well that we're like, well, why change it if we don't need to?", 'Counterpoint', 'The Meta retargeting review described a different early picture for the same client. Channel, audience, sample size, and measurement must stay separate.'),
      ],
      brandReferences: [voiceReference, { title: 'Strategy from WLF Savannah', section: 'Warm: Education; what you spend learning today saves you next season.' }, { title: 'Founder Voice Knowledge Base', section: 'Why some businesses convert more inquiries than others; The goal isn’t going viral.' }],
      externalContext: [testingContext],
    },
    brief: {
      coreInsight: 'A marketing result is useful when you understand the comparison behind it. Check what changed, the traffic source, and the strength of the evidence before deciding what to fix.',
      audiencePain: 'You invest in ads, see a quieter few days, and feel pressure to change the form, page, and campaign at once without knowing which part needs attention.',
      messageSpine: ['Start with the same form on two pages and the temptation to shorten it after fewer leads.', 'Separate the observation from the explanation: page, audience, time window, and tracking each matter.', 'Compare like with like, check the full inquiry-to-tour journey, and change one deliberate variable.', 'An early lead count can suggest the next question; a stronger comparison supports the next decision.'],
      formatSplit: { emailFocus: 'A thoughtful account of the moment Whitney checked the forms before choosing a fix.', carouselFocus: 'A decision checklist for evaluating a landing-page change.', reelsFocus: 'Three different questions: what changed, is the comparison fair, and what happens after the inquiry.' },
      contentPlan: {
        email: 'Tell the same-form observation from a team review. Walk the reader through why a plausible recommendation still needs checking. End by asking which variable they are changing and why.',
        carousel: 'Use 8 slides to distinguish observation, hypothesis, traffic source, sample size, tracking, downstream lead quality, and the next test. Present the reported counts only with scope and permission; otherwise use a clearly hypothetical example.',
        reels: ['Show how checking two identical forms changes the question you ask about a page. Give one diagnostic action.', 'Explain why matching the number of days is only part of a fair comparison. Keep audience, traffic source, and sufficient observations in view.', 'Trace one inquiry toward a tour or consultation. Explain why the percentage alone does not establish business value.'],
      },
      claimsRequiringConsent: ['Obtain permission before naming the venue, showing its pages, or publishing its reported lead/click counts.', 'Verify screen data and speaker attribution against the recording. No statistically established winner, booking lift, or universal eight-day rule is supported.'],
      openQuestionsForWhitney: ['Can we use an anonymised team-review story, or should the comparison remain a hypothetical teaching example?', 'Confirm the relevant date windows, channel mix, and inquiry definitions before including any numbers.', 'Which Accelerator invitation and destination should follow this lesson?'],
    },
    research: questionResearch('How should a wedding venue evaluate a landing-page change?', ['What changed besides the landing page?', 'Do both pages receive comparable traffic?', 'Are inquiries turning into tours or consultations?'], 'Editorial questions derived from the meetings, not Google People Also Ask. External guidance provides testing context; no search volume, Trends index, or completed archive similarity review is available.'),
  }),
  angle({
    id: 'mock-fathom-2026-10-05-buyer-stage',
    title: 'Your Best Testimonial Has a Place in the Journey',
    subtitle: 'Help a couple picture their wedding first, then use the right proof to make choosing you feel safer.',
    client: 'Venue messaging review', suggestedCta: 'Elevate', score: 86,
    scoresBreakdown: { proof: 79, audiencePain: 88, offerFit: 92, recurrence: 70, novelty: 86, demand: 66 },
    angleRationale: { source: 'editorial', topic: 'Give each message a job in the couple’s decision.', points: [
      { label: 'Angle & gist', text: 'A strong testimonial can build confidence, but repetition alone does not explain the experience a venue offers. The team proposed leading discovery ads with distinctive venue features and using testimonial copy further along the journey.' },
      { label: 'Why it matters', text: 'A couple discovering a venue and a couple deciding whether to book have different questions. Owners can mistake changing a photograph for changing the message, while repeating the same answer to both audiences.' },
      { label: 'Founder fit', text: 'The voice guide says marketing shapes decisions and buyers need confidence. Whitney’s existing experiential storytelling shows how to let people picture themselves in a celebration before asking them to choose.' },
      { label: 'Content direction', text: 'Use one hypothetical venue to demonstrate two messages: an invitation to imagine a distinctive experience, and a relevant review that answers a remaining concern. Explain the reasoning before showing the copy.' },
      { label: 'Commercial opportunity', text: 'Reveal the strategic work behind ELEVATE: coordinate audience, message, page, and follow-up. Invite a conversation about whether the current funnel answers the couple’s next question.' },
      { label: 'Evidence boundary', text: 'This was a proposed adjustment during a campaign review. The export contains no post-change result. Testimonial placement is a hypothesis to test, not a rule that reviews cannot work for new audiences.' },
    ] },
    editorialContext: {
      audience: 'Venue owners with established reviews and ad creative who keep recycling the same message across discovery and retargeting.',
      objective: 'Help owners map a message to the question a couple needs answered at that stage.',
      funnelStage: 'Warm', pillar: 'Lightbulb Moments · Buyer psychology',
      beliefShift: 'From “a good testimonial should lead every ad” to “choose the message that helps this audience make its next decision.”',
      suggestedInvitation: 'Reply with the question couples ask before they book a tour. Confirm the ELEVATE invitation with Whitney.',
      sources: [
        passage('189649334', '00:21:18', 'Jacqueline Hood', "I think there's so many different angles on venues that we can like lean into as well that we're not.", 'Primary passage', 'The editorial opportunity is broader messaging that reflects a venue’s distinctive experience.'),
        passage('189649334', '00:20:31', 'Jacqueline Hood', 'So I think I had suggested swapping them, like taking this copy here, putting it on the top of funnel campaigns, or even putting this ad in the top of funnel campaign and putting the top of funnel ads with the testimonial copy, putting that in the middle of funnel, just like moving them to the other campaigns.', 'Supporting passage', 'A proposed placement test across discovery and warmer audiences; implementation and outcome remain unproven.'),
        passage('189649334', '00:22:00', 'Jacqueline Hood', 'So maybe some fresh ad copy as well, just leaning more into the venue and use the testimonial copy for the middle funnel.', 'Supporting passage', 'The recommendation joins experience-led discovery messaging with supporting proof later.'),
        passage('189649334', '00:22:13', 'Jacqueline Hood', "But overall, I mean, leads are still coming in, so it's still working.", 'Counterpoint', 'The team framed the change as refinement. Do not turn a functioning account into a failure story.'),
      ],
      brandReferences: [voiceReference, { title: 'Founder Voice Guide v2.0', section: 'Marketing shapes decisions; buyers need confidence; people buy emotionally.' }, { title: 'Strategy from WLF Savannah', section: 'Warm: Lightbulb Moments; Unique Processes, Frameworks & Beliefs.' }, { title: 'Founder Voice Knowledge Base', section: 'Taylor Swift reel: help couples imagine themselves inside the experience.' }],
      externalContext: [industryContext],
    },
    brief: {
      coreInsight: 'A useful message meets the couple at their next decision. Help them see why the experience fits, then use relevant proof to address the uncertainty that remains.',
      audiencePain: 'You have beautiful photos and glowing reviews, yet every ad sounds similar and you cannot tell which question it answers for a couple.',
      messageSpine: ['Ask what a couple needs to understand when they first discover the venue.', 'Show a specific experience they can picture themselves in.', 'Introduce a relevant review when it answers a remaining concern about choosing the venue.', 'Map discovery, consideration, and inquiry messages; test the placement rather than assume one opening suits everyone.'],
      formatSplit: { emailFocus: 'Founder reflection on the difference between showing proof and helping someone recognise fit.', carouselFocus: 'A couple’s decision map with experience, practical clarity, and relevant proof.', reelsFocus: 'Experience versus amenities; choosing the right review; auditing repeated copy.' },
      contentPlan: {
        email: 'Begin with a team conversation about repeated testimonial openings. Explain why a review can be excellent yet leave the experience unclear. Use a hypothetical venue and invite the reader to name their couple’s next question.',
        carousel: 'An 8-slide decision map: discovery, desired experience, differentiation, practical questions, relevant proof, clear inquiry step, messaging audit, and invitation. Use invented copy explicitly labelled as an example.',
        reels: ['Turn one generic venue amenity into a concrete experience a couple can imagine. Demonstrate the thinking, not a promised conversion increase.', 'Select a review that answers a real concern about the day. Show why its relevance matters more than a general five-star claim.', 'Compare discovery and retargeting copy. Ask whether each message advances the decision or repeats the same information.'],
      },
      claimsRequiringConsent: ['Keep client identity, live creative, and account information private unless permission is granted.', 'No result from swapping messages is present. Do not promise lower CPL or imply testimonials never work in discovery ads.'],
      openQuestionsForWhitney: ['Which venue experience should the hypothetical example demonstrate?', 'Can we reference the internal review anonymously?', 'Confirm the offer connection and final CTA; avoid implying the proposed test has already succeeded.'],
    },
    research: questionResearch('Which question should a venue ad answer at each stage?', ['Can a couple picture their day from this message?', 'Which uncertainty does this testimonial address?', 'Does retargeting add useful information?'], 'Audience questions are editorial prompts. The industry report informs framing only; the meeting supplies a proposed test with no confirmed outcome or measured external demand.'),
  }),
  angle({
    id: 'mock-fathom-2026-10-05-human-automation',
    title: 'Let the Conversation Set the Follow-Up',
    subtitle: 'An instant first response and a human-controlled next step can belong in the same sales system.',
    client: 'LeadLock inquiry-sequence review', suggestedCta: 'LeadLock', score: 91,
    scoresBreakdown: { proof: 85, audiencePain: 94, offerFit: 96, recurrence: 82, novelty: 91, demand: 68 },
    angleRationale: { source: 'editorial', topic: 'Build automation around the decisions your sales team actually makes.', points: [
      { label: 'Angle & gist', text: 'A venue wanted its first inquiry email to send automatically while retaining control over later messages. The team discussed opportunity stages that trigger the relevant sequence. Automation can protect responsiveness while preserving judgment about the next conversation.' },
      { label: 'Why it matters', text: 'Wedding inquiries depend on date, fit, availability, and what the couple has already said. A timer can send a message that no longer fits, while relying entirely on memory can leave opportunities waiting during event work.' },
      { label: 'Founder fit', text: 'The guide connects better systems with freedom and buyer confidence. This makes that belief concrete: free the owner from repetitive execution while allowing them to guide the decision.' },
      { label: 'Content direction', text: 'Show a simple inquiry journey: acknowledge, review, select a next stage, send the matching message. Contrast a calendar timer with a meaningful sales milestone using a clearly hypothetical couple.' },
      { label: 'Commercial opportunity', text: 'A natural LeadLock discussion for owners who want follow-up consistency and control. Explain a workflow approach; have Whitney confirm configuration, service scope, and the invitation.' },
      { label: 'Evidence boundary', text: 'The discussion describes a requested configuration and ongoing work. It does not prove a completed rollout or higher booking rate. The migration discussion also shows why copying an old sequence can preserve an outdated process.' },
    ] },
    editorialContext: {
      audience: 'Wedding venues and service businesses with multi-step sales conversations who fear automated messages will feel impersonal or arrive at the wrong moment.',
      objective: 'Show how a repeatable follow-up process can retain human judgment and make a sales-workflow conversation feel useful.',
      funnelStage: 'Warm → Convert', pillar: 'Unique Processes · Solution Selling',
      beliefShift: 'From “I must choose between manual follow-up and a fully timed sequence” to “automate repeatable actions around the stages I deliberately choose.”',
      suggestedInvitation: 'Ask readers which follow-up they still send manually and why; offer a LeadLock conversation after confirming fit.',
      sources: [
        passage('189685435', '00:25:04', 'Danielle McGinnis', 'In a nutshell, she wants the first inquiry email to go out, and then she wants to have the power over when she generates the rest of the inquiry emails in the sequence.', 'Primary passage', 'A concrete customer need: responsiveness together with control over subsequent messages.'),
        passage('189685435', '00:25:12', 'Danielle McGinnis', "So we're adding different stages in the opportunity so that she can just move them over and those different emails will trigger instead of them just going on a timer type of thing.", 'Supporting passage', 'The discussed implementation connects messages to selected sales stages rather than elapsed time alone.'),
        passage('189685435', '00:25:45', 'Danielle McGinnis', 'It seems like at the beginning, everyone that\'s transitioning, they just want us to duplicate what they had.', 'Supporting passage', 'Related migration pattern: review the workflow’s purpose before copying it into a new tool.'),
        passage('189685435', '00:22:49', 'Danielle McGinnis', "But yeah, so we're still not fully converted all the way over to LeadLock.", 'Counterpoint', 'A separate migration still had an old-system lead. Do not claim migrations or all configurations are complete.'),
      ],
      brandReferences: [voiceReference, { title: 'Founder Voice Guide v2.0', section: 'Growth comes from better systems; marketing should create freedom.' }, { title: 'Strategy from WLF Savannah', section: 'Warm: Unique Processes; Convert: Solution Selling.' }, { title: 'Founder Voice Knowledge Base', section: 'It feels like our sales are on autopilot: system-level framing; historical figures are not evidence for this new workflow.' }],
      externalContext: [industryContext],
    },
    brief: {
      coreInsight: 'A thoughtful sales system makes timely actions repeatable while leaving room for the judgment a wedding inquiry deserves.',
      audiencePain: 'You want inquiries answered promptly, but worry that automatic messages will ignore availability, questions, or the conversation you have already had.',
      messageSpine: ['Recognise the tension between keeping up with inquiries and making every exchange feel considered.', 'Introduce the real request: send the first email, then let the team choose when the next sequence begins.', 'Explain a stage-based workflow with explicit ownership, pauses, and checks for reply or booking.', 'Before moving tools, review what each message is supposed to accomplish and preserve the parts that serve the buyer.'],
      formatSplit: { emailFocus: 'Empathetic founder explanation of how automation and judgment can work together.', carouselFocus: 'Map one inquiry through automatic acknowledgment and human-selected next stages.', reelsFocus: 'The hybrid workflow; the pause after a reply; auditing a sequence before migration.' },
      contentPlan: {
        email: 'Open with the request to keep control of later inquiry emails. Validate the concern, explain the role of a sales milestone, and ask what the reader needs to review personally before the next message.',
        carousel: 'An 8-slide conceptual workflow: new inquiry, acknowledgment, review by the owner, next-stage decision, relevant message, pause conditions, tour or consultation, and a natural invitation. Confirm actual LeadLock configuration before presenting product instructions.',
        reels: ['Demonstrate an automatic first acknowledgment followed by a human-selected next step, using a fictional inquiry.', 'Explain why a reply or booked tour should prompt a review of the remaining messages. Give a workflow-check question rather than an unverified feature tutorial.', 'Before copying an old CRM sequence, identify the job of one email and whether its trigger still fits your sales process.'],
      },
      claimsRequiringConsent: ['Confirm customer permission and speaker attribution before using names or quotes publicly.', 'Confirm the discussed stage triggers and pause logic with the implementation team; the export is not a completed product acceptance test.', 'No increased bookings, time savings, AI conversation capability, or seamless migration claim is established by these passages.'],
      openQuestionsForWhitney: ['Which human review point should the example use: availability, fit, or a tour invitation?', 'Confirm what the supported LeadLock configuration currently includes and who owns each stage.', 'Can the customer request be referenced anonymously, and what is the approved LeadLock CTA destination?'],
    },
    research: questionResearch('How can wedding inquiry follow-up preserve human judgment?', ['Which response should happen immediately?', 'Which decision requires the owner’s review?', 'What should stop or change the remaining sequence?'], 'Editorial questions based on the inquiry-sequence discussion. External industry context supports the human-connection framing, not the performance or availability of any particular workflow.'),
  }),
  angle({
    id: 'mock-fathom-2026-10-05-existing-footage',
    title: 'Your Next Ad May Already Be in Your Wedding Footage',
    subtitle: 'Look for the moment that helps a couple imagine their celebration before scheduling another content shoot.',
    client: 'Entertainment creative review', suggestedCta: 'Accelerators', score: 88,
    scoresBreakdown: { proof: 83, audiencePain: 92, offerFit: 91, recurrence: 84, novelty: 86, demand: 67 },
    angleRationale: { source: 'editorial', topic: 'Choose creative for the experience it communicates, then test it deliberately.', points: [
      { label: 'Angle & gist', text: 'The team went back through an entertainment business’s existing Instagram footage and selected performances, hooks, and strong copy for new ad tests. The useful lesson is how to recognise a persuasive moment in material the business already has.' },
      { label: 'Why it matters', text: 'Wedding professionals often deliver a compelling experience every weekend but feel they need to create another polished asset before advertising. A specific guest reaction or live performance may explain the value more clearly than a generic service list.' },
      { label: 'Founder fit', text: 'Whitney’s voice guide prioritises the larger principle and sustainable systems. Her experiential storytelling asks whether a couple can picture themselves there; this angle applies that question to selecting footage.' },
      { label: 'Content direction', text: 'Walk through an asset audit: identify the experience, choose the moment that shows it, check rights and relevance, pair it with an appropriate invitation, and test within a campaign. Distinguish existing-post reuse from indiscriminate boosting.' },
      { label: 'Commercial opportunity', text: 'A useful bridge to the Meta Ads Accelerator for content-comfortable businesses that need campaign strategy. Invite readers to identify one existing clip and the decision it could help a couple make.' },
      { label: 'Evidence boundary', text: 'The team discussed early lead observations and planned further tests. Avoid quoting an unscoped CPL, calling the saxophone discussion a verified industry trend, or claiming organic popularity predicts ad performance.' },
    ] },
    editorialContext: {
      audience: 'Wedding entertainers, venues, photographers, and other established professionals with existing event footage but limited time for continual new creative production.',
      objective: 'Help owners identify one useful existing creative asset and understand the strategy needed to test it as an ad.',
      funnelStage: 'Attract → Warm', pillar: 'Campaign Breakdowns · Education',
      beliefShift: 'From “advertising needs a new polished shoot” to “first look for footage that makes the value of the experience easy to imagine.”',
      suggestedInvitation: 'Invite readers to choose one clip and explain what it helps a couple picture. Confirm the Meta Ads Accelerator invitation with Whitney.',
      sources: [
        passage('189649334', '00:10:06', 'Whitney Hodges', "There's one on September 10th where the copy on the reel is really good.", 'Primary passage', 'Whitney selects an existing reel for its message rather than simply requesting more assets.'),
        passage('189649334', '00:09:02', 'Jacqueline Hood', "I'm just wondering for them if we try, since it works so well for DJ Hybrid, so far anyway, like pulling in an organic post from Instagram into the campaign and let that be another test as well.", 'Supporting passage', 'Existing organic content is a candidate for a deliberate campaign test; the speaker explicitly qualifies the early observation.'),
        passage('189649334', '00:10:53', 'Carmen Cruickshank', "Yeah, I think I'll like make a list of like top three or top five and just have a backlog of that.", 'Supporting passage', 'The conversation suggests a repeatable asset shortlist rather than an endless production treadmill.'),
        passage('189088443', '00:42:52', 'Whitney Hodges', 'And if we feel like it would make sense to repurpose it, we totally can.', 'Supporting passage', 'The client call also discusses reviewing existing organic material for potential reuse, independently of the duplicate Meta capture.'),
        passage('189649334', '00:07:52', 'Jacqueline Hood', "And let's give the, give a fair test to the other two.", 'Counterpoint', 'Creative selection still needs adequate test opportunity. More attractive or popular footage is not automatically the winner.'),
      ],
      brandReferences: [voiceReference, { title: 'Founder Voice Guide v2.0', section: 'Marketing shapes decisions; growth comes from better systems.' }, { title: 'Strategy from WLF Savannah', section: 'Attract: Campaign Breakdowns; Warm: Education; Stop Boosting Posts.' }, { title: 'Founder Voice Knowledge Base', section: 'Taylor Swift experiential reel; Where most wedding pros get stuck with Meta ads.' }],
      externalContext: [industryContext],
    },
    brief: {
      coreInsight: 'Useful ad creative can start with footage you already own. Select the moment that communicates a desirable experience, then give it a clear message, audience, next step, and test.',
      audiencePain: 'You have galleries and reels from real weddings, yet feel advertising requires another expensive shoot or a constant stream of brand-new content.',
      messageSpine: ['Begin with the team finding a strong message inside an existing entertainment reel.', 'Ask what the clip helps a couple picture about their own celebration.', 'Check permissions, dated details, message, landing destination, and the role of the creative in the campaign.', 'Build a small test backlog and evaluate relevant inquiries; organic popularity alone does not establish paid performance.'],
      formatSplit: { emailFocus: 'Founder observation about recognising an asset’s value before commissioning more production.', carouselFocus: 'An existing-footage selection and testing checklist.', reelsFocus: 'Recognising an experiential moment; matching it to a message; making an asset backlog.' },
      contentPlan: {
        email: 'Describe the team opening the existing Instagram archive and finding a useful reel. Explain the difference between showing a service and helping someone imagine its experience. Invite a simple asset audit.',
        carousel: 'An 8-slide audit from footage to test: buyer experience, candidate clip, opening message, permissions, current dates and offer, destination, test plan, and invitation. Use approved footage or a clearly labelled illustrative example.',
        reels: ['Use an approved or illustrative entertainment clip to explain the experience it communicates. Keep the lesson in buyer psychology.', 'Pair one existing clip with a specific opening message and a relevant next step. Explain why a like count does not tell you who will inquire.', 'Demonstrate a three-item creative backlog organised by experience and campaign role. Include rights and freshness checks before testing.'],
      },
      claimsRequiringConsent: ['Confirm usage rights, client permission, identifiable guest consent where applicable, and music licensing before showing real event footage.', 'Do not publish unscoped CPL figures or turn an early observation into a bookings claim.', 'Describe a deliberate campaign test, not a recommendation to boost every organic post or a claim that organic content always beats designed ads.'],
      openQuestionsForWhitney: ['Which footage is actually cleared for public use, or should this be a teaching example?', 'Should the invitation be an engagement prompt or a Meta Ads Accelerator conversation?', 'Confirm current dates, offer details, and the intended landing destination before referencing an existing post.'],
    },
    research: questionResearch('Which existing wedding footage could communicate value in an ad?', ['What experience does the clip help a couple imagine?', 'Are rights, booking dates, and the offer current?', 'What inquiry outcome should the campaign test measure?'], 'Editorial asset-selection questions, not scraped search suggestions. Two separate conversations support the reuse process; neither proves a universal performance advantage.'),
  }),
];

// Retain the earlier proposal plans for a field-by-field saved-library upgrade.
export const FATHOM_STARTER_PLANS = Object.fromEntries(SOURCE_ANGLE_PROPOSALS.map(idea => [idea.id, idea.brief.contentPlan]));
export const FATHOM_WEEKLY_ANGLES = SOURCE_ANGLE_PROPOSALS.map(idea => hydrateFathomMockPack(prepareFathomContentBrief(idea, idea.brief.contentPlan)));
