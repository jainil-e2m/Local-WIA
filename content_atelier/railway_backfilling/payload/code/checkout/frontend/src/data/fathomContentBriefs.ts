import { BriefBeat, ContentIdea, ProductionBrief } from '../types/atelier';

export const FATHOM_BRIEFS_PREPARED_AT = '2026-10-06T12:16:31.000Z';
const voice: ProductionBrief['voice'] = {
  perspective: 'Whitney as a thoughtful wedding-business strategist. Use “our team discussed” for a team member’s observation; use “I noticed” only for Whitney’s own recorded contribution. Proposed hooks below are copy directions, not transcript quotes.',
  tone: 'Warm, calm, curious, and specific. Explain the principle before giving the practical step.',
  writingRules: ['Start with a recognisable situation and help the reader reach the conclusion.', 'Use concrete wedding-business decisions, plain language, and varied sentence lengths.', 'Describe transformation as clearer thinking or a more intentional process; do not invent a client result.', 'Give each format one job and earn its invitation.'],
  avoid: ['Hype, fear, blame, and “secret” or “hack” language.', 'Invented first-person anecdotes, quotes, case-study endings, or before-and-after metrics.', 'Repeating the same opening and CTA across all five deliverables.'],
};
const creative: ProductionBrief['creativeDirection'] = {
  treatment: 'Use the existing WIA brand kit: restrained navy, ivory, and gold; clear editorial typography and generous spacing. Show decisions with simple diagrams rather than decorative dashboards.',
  assets: ['Founder talking-head footage with a neutral background.', 'Illustrative cards, diagrams, and documents labelled as examples; omit client identifiers and live account screenshots by default.'],
  accessibility: ['Use readable text, adequate contrast, and captions for every reel.', 'Keep important text within each platform’s safe area; do not rely on colour alone to explain a comparison.', 'Write alt text that describes the practical takeaway and diagram.'],
};
const reviewChecklist = [
  'Confirm that every deliverable teaches this brief’s central principle and advances a distinct reader decision.',
  'Separate meeting observations, proposed tests, hypothetical examples, and completed results.',
  'Verify speaker identity from the recording and obtain clearance for any public quote, client name, account screenshot, or event footage actually used.',
  'Resolve relevant founder questions and check the complete published archive for the past four months before claiming novelty.',
  'Confirm the final CTA and any commercial destination; brief preparation does not authorise publication.',
];
function slide(number: number, beat: BriefBeat, headlineDirection: string, detail: string, visualDirection: string): ProductionBrief['carousel']['slides'][number] {
  return { number, beat, headlineDirection, detail, visualDirection };
}
function reel(title: string, role: string, summary: string, hookDirection: string, beats: string[], visualDirection: string, cta: string): ProductionBrief['reels'][number] {
  return { title, role, summary, durationGuidance: '45–60 seconds; aim for approximately 95–130 spoken words, then time the read. Captions and production notes are separate from spoken copy.', hookDirection, beats, visualDirection, cta };
}
function brief(direction: Omit<ProductionBrief, 'version' | 'preparedAt' | 'preparationBasis' | 'briefType' | 'voice' | 'creativeDirection' | 'reviewChecklist'> & { creativeDirection?: ProductionBrief['creativeDirection'] }): ProductionBrief {
  return {
    version: 1, preparedAt: FATHOM_BRIEFS_PREPARED_AT,
    preparationBasis: 'Prepared at the user’s request to develop all four selected weekly angles. Brief approval and publication clearance remain pending.',
    briefType: 'Strategic editorial brief + email, carousel, and short-video production direction',
    voice, creativeDirection: creative, reviewChecklist, ...direction,
  };
}

export const FATHOM_CONTENT_BRIEFS: Record<string, ProductionBrief> = {
  'mock-fathom-2026-10-05-fair-comparison': brief({
    readerPromise: 'Leave with a simple way to decide what a landing-page result tells you, what it leaves unanswered, and which question to test next.',
    distinctiveness: 'This is about interpreting a comparison before changing a marketing variable. Keep it separate from the testimonial angle’s message placement and the footage angle’s creative selection.',
    narrative: [
      { beat: 'Hook', direction: 'Open on the team considering a form change, followed by Whitney checking that both forms were identical.' },
      { beat: 'Problem', direction: 'A quieter week creates pressure to change several things at once. Recognise that pressure without shaming the owner or the team.' },
      { beat: 'Main point', direction: 'A result and an explanation are different. Check page differences, audience, traffic source, observation window, and tracking before choosing a fix.' },
      { beat: 'Transformation', direction: 'The owner can identify what remains uncertain and make one deliberate next decision rather than chase each weekly fluctuation.' },
      { beat: 'CTA', direction: 'Ask the reader which change they are evaluating and what they expect it to improve.' },
    ],
    evidencePolicy: {
      established: ['Whitney said the forms were identical and requested a comparable observation window in the Google review.', 'The team reported early lead/click counts and questioned whether enough time had passed.', 'The separate Meta review described a different early picture for the same client.'],
      hypotheses: ['The page, audience, or measurement could explain the observed difference; the export does not isolate causation.', 'A more controlled comparison could support a better decision. Equal elapsed time alone is insufficient.'],
      excludedClaims: ['One landing page statistically beat the other.', 'Shortening this form would improve conversion.', 'Eight days is a universal testing rule, or a higher inquiry rate guarantees more bookings.'],
    },
    email: {
      summary: 'A founder reflection on the identical-form moment, moving from a plausible fix to a more useful question.',
      readerJob: 'Recognise a reactive decision in their own reporting and describe a clearer test.',
      lengthGuidance: '350–500 words; one observation, one practical diagnostic sequence, and one reply invitation.',
      subjectDirections: ['The form was the same', 'What changed before the leads changed?', 'Before you edit your landing page'],
      openingDirection: 'Describe the internal Google review anonymously. Start with the proposed form change and the discovery that the forms matched. Omit exact counts and client identity in the default draft.',
      outline: ['Make the pressure familiar: a few slower days can make every part of the funnel look suspect.', 'Use the same-form finding to separate an observation from an explanation.', 'Walk through three questions: what actually changed, who saw each page, and whether tracking and observation are comparable.', 'Acknowledge the Meta counterpoint without combining its results with Google.', 'End with the reader’s next test, not a declared winner or a promised improvement.'],
      cta: 'Invite a reply naming one landing-page change and the question it is intended to answer.',
    },
    carousel: {
      summary: 'An eight-slide comparison checklist that turns a quiet week into a testable question.',
      readerJob: 'Save a decision aid and use it before changing a live page.',
      slides: [
        slide(1, 'Hook', 'Before you fix the form…', 'Introduce the question: does the comparison support that fix?', 'A simple page outline and one highlighted question; no performance number.'),
        slide(2, 'Problem', 'Fewer leads is an observation', 'Show how a result can lead to several plausible explanations. Avoid treating one explanation as fact.', 'Observation card branching to page, audience, timing, and tracking.'),
        slide(3, 'Main point', 'Check what actually changed', 'Use the identical-form moment. Inspect the pages before acting on a form recommendation.', 'Two illustrative form outlines labelled “example”; identical fields highlighted.'),
        slide(4, 'Main point', 'Compare the audience and channel', 'Cold Google traffic and Meta retargeting answer different questions. Keep their observations separate.', 'Two clearly labelled audience paths; no invented results.'),
        slide(5, 'Main point', 'Check the window and tracking', 'Comparable periods, enough observations, and consistent inquiry definitions matter. Same number of days is not proof.', 'A checklist, not a fabricated significance chart.'),
        slide(6, 'Transformation', 'Follow the inquiry further', 'Ask about relevance and the next sales step, such as a tour or consultation; do not declare quality from volume alone.', 'Inquiry → review → tour/consultation → booking, with uncertainty shown.'),
        slide(7, 'Transformation', 'Choose one next question', 'Write down the variable, the expected effect, and the evidence needed before changing several things.', 'A blank three-field decision card the reader can use.'),
        slide(8, 'CTA', 'What are you trying to learn?', 'Invite readers to save the checklist and describe the page decision they are evaluating.', 'A single readable invitation; no sales button or unconfirmed URL.'),
      ],
      captionDirection: 'Explain that this checklist comes from a team-review lesson, not a winning-page case study. Add the uncertainty about early comparisons and one invitation to save or comment.',
    },
    reels: [
      reel('The identical-form moment', 'Challenge the diagnosis', 'Use one observation to show why a plausible fix still needs checking.', 'Start with the surprise that the proposed form fix concerned two identical forms.', ['Recognise the temptation to shorten a form after fewer inquiries.', 'Reveal what Whitney checked.', 'Explain why checking the proposed cause comes before choosing a tactic.'], 'Founder to camera; cut to two fictional form cards. No live account data.', 'Ask what the viewer checks first when inquiries slow.'),
      reel('What makes the comparison useful?', 'Explain the evidence', 'Demonstrate why time, audience, and measurement must be read together.', 'Ask whether two equal-length windows automatically make a fair comparison.', ['Name audience and channel as variables.', 'Explain why equal time does not ensure sufficient or comparable observations.', 'End with the question the available evidence can actually answer.'], 'Founder with three cards: audience, observation, tracking. No statistical tutorial or invented chart.', 'Invite viewers to save the three checks for their next report.'),
      reel('Write the test before the edit', 'Give a practical action', 'Help the viewer turn one proposed page edit into a clear test question.', 'Ask the viewer to finish: “I am changing this because…”', ['Choose one variable.', 'State the expected effect and a consistent way to observe it.', 'Keep downstream inquiry quality in view and avoid changing several variables together.'], 'Show a handwritten example labelled illustrative; keep it simple enough to read.', 'Invite a comment describing one change and its intended purpose.'),
    ],
    cta: { primaryAction: 'Reply, save, or comment with a diagnostic question.', wordingDirection: 'Which landing-page change are you evaluating, and what do you expect it to improve?', offerBridge: 'Accelerators fit the need for guided interpretation. Keep this Warm content engagement-led; a commercial invitation is optional after Whitney confirms fit.', destination: 'Email reply or native post engagement. No commercial link is required for the default draft.', avoid: 'A guarantee, a universal test duration, or a claim that WIA already identified the winning page.' },
    distribution: { channels: ['WIA founder email', 'Instagram carousel', 'Three founder reels for Instagram; adapt selected reels to TikTok'], sequence: 'Use the email for context, the carousel as the reusable checklist, and the reels as separate entry points. Scheduling dates are not assigned by this brief.', adaptation: 'For LinkedIn, adapt the caption into a short decision-making observation; retain the uncertainty and omit unapproved numbers.' },
    success: { primarySignal: 'Readers describe a concrete test question or a variable they are evaluating.', secondarySignals: ['Checklist saves and shares.', 'Relevant replies from businesses already running ads.'], measurementNote: 'Review available engagement and replies qualitatively. No numerical target or conversion lift is established; reach alone does not demonstrate understanding.' },
  }),
  'mock-fathom-2026-10-05-buyer-stage': brief({
    readerPromise: 'Know how to give discovery and consideration messages different jobs, and choose a review that answers a real buyer concern.',
    distinctiveness: 'This teaches message relevance across the couple’s decision journey. It does not diagnose landing-page performance or argue that testimonials are ineffective.',
    narrative: [
      { beat: 'Hook', direction: 'Begin with a venue using an excellent testimonial repeatedly and ask what a newly discovering couple still needs to understand.' },
      { beat: 'Problem', direction: 'Changing the photograph can leave the underlying message unchanged. Praise the existing proof while exposing the unanswered question.' },
      { beat: 'Main point', direction: 'Let discovery messaging make the experience and fit concrete. Use relevant proof wherever it addresses a meaningful concern; placement remains a test.' },
      { beat: 'Transformation', direction: 'Each message now helps the couple make a next decision rather than hearing the same general praise again.' },
      { beat: 'CTA', direction: 'Ask which question a couple needs answered before booking a venue tour.' },
    ],
    evidencePolicy: {
      established: ['The Meta review discussed underused venue angles and proposed moving experience-oriented and testimonial copy between funnel stages.', 'The account was still receiving leads during that discussion.'],
      hypotheses: ['Experience-oriented discovery messaging and more relevant proof for warmer audiences may answer different questions.', 'The proposed placement needs testing; the export contains no post-change results.'],
      excludedClaims: ['Testimonials never work with cold audiences.', 'Moving the copy improved CPL or bookings.', 'The account was failing, or a particular buyer stage has one universally correct message.'],
    },
    email: {
      summary: 'A thoughtful distinction between showing that people loved a venue and helping a couple understand why it fits their own day.',
      readerJob: 'Identify the question their current venue copy leaves unanswered.',
      lengthGuidance: '350–500 words; one hypothetical venue and two clearly different message jobs.',
      subjectDirections: ['What your best review leaves unanswered', 'Give each venue message a job', 'Can a couple picture their day?'],
      openingDirection: 'Attribute the observation to a team messaging review. Describe the proposed refinement without claiming it has been launched or won. Use a fictional venue for copy demonstrations.',
      outline: ['Acknowledge that a strong review is valuable proof.', 'Ask what the couple knows when they first discover the venue and what they still need to imagine.', 'Use an illustrative garden venue to show the experience: a ceremony, a relaxed transition, and a celebration that feels like them; label the scenario hypothetical.', 'Show a review topic that could address a later concern, such as rain-plan support; describe the topic without inventing a customer quotation.', 'Explain that relevance drives placement, and conclude with a one-question copy audit.'],
      cta: 'Ask the reader to reply with the question couples most often ask before booking a tour.',
    },
    carousel: {
      summary: 'An eight-slide message map: experience, practical clarity, and relevant proof each answer a different question.',
      readerJob: 'Audit whether discovery and retargeting copy help the couple progress.',
      slides: [
        slide(1, 'Hook', 'Your best review has a job', 'Introduce message relevance rather than criticising testimonials.', 'A review-shaped card beside an unanswered buyer question.'),
        slide(2, 'Problem', 'New photo. Same answer?', 'Repeated copy can leave discovery and warmer audiences with identical information.', 'Two illustrative ad cards with different images and the same generic message.'),
        slide(3, 'Main point', 'Discovery: help them picture it', 'Show the distinctive experience and who it fits. Avoid an amenities list without context.', 'An illustrative garden-venue scene; no claim about a real client.'),
        slide(4, 'Main point', 'Make the experience specific', 'Connect one true venue feature to what the day feels like; use a hypothetical example until assets and details are confirmed.', 'Feature → experience → fit, with a short labelled example.'),
        slide(5, 'Main point', 'Consideration: answer the concern', 'Name a realistic question about the day, logistics, or support instead of assuming more general praise is enough.', 'A buyer-question card such as a rain-plan concern.'),
        slide(6, 'Main point', 'Choose proof for its relevance', 'Select an approved review that speaks to that concern. If unavailable, show the review-selection prompt rather than fabricate a quote.', 'Concern matched to a proof topic; no invented star rating or testimonial.'),
        slide(7, 'Transformation', 'Build a conversation across ads', 'Experience, clarity, and proof work together. Test placement instead of treating this as a rigid funnel rule.', 'Three message cards leading toward one inquiry step.'),
        slide(8, 'CTA', 'What is the next question?', 'Invite a save and a comment about the question couples ask before a tour.', 'One clear question and restrained brand sign-off.'),
      ],
      captionDirection: 'Explain that the proposed placement is a test, that reviews can work at different stages, and that the goal is a more useful message. Invite one question from the audience.',
    },
    reels: [
      reel('An amenity is not the whole experience', 'Reframe the message', 'Turn a generic venue feature into an experience a couple can picture.', 'Ask what a couple should imagine when they read the venue’s feature list.', ['Choose one hypothetical venue feature.', 'Connect it to a concrete part of the day.', 'Explain why specificity helps the buyer assess fit.'], 'Founder with an illustrative feature-to-experience card; approved venue footage is optional.', 'Ask viewers which experience their venue should be known for.'),
      reel('Choose the review that answers the question', 'Demonstrate relevant proof', 'Show how a concern changes which testimonial topic is useful.', 'Start with a couple’s practical concern, rather than a fabricated glowing quote.', ['Name an illustrative concern.', 'Describe the kind of approved review that could answer it.', 'Explain that proof should reduce uncertainty, wherever it is placed.'], 'Question and proof-topic cards; do not create a fictitious customer quotation.', 'Invite viewers to check which concern their featured review actually answers.'),
      reel('Audit the next message', 'Give a copy audit', 'A simple side-by-side check of discovery and consideration copy.', 'Ask whether the second ad says anything the first one did not.', ['Write the question each audience needs answered.', 'Label the job of each current message.', 'Choose one unanswered question for the next copy test.'], 'Two fictional message cards and one blank buyer-question prompt.', 'Invite a save or comment with the next question to answer.'),
    ],
    cta: { primaryAction: 'Reply or comment with a buyer question; save the message map.', wordingDirection: 'What do couples need to feel confident about before they book a tour?', offerBridge: 'ELEVATE fits coordinated audience, message, page, and follow-up strategy. Retain an engagement CTA for this Warm lesson; confirm any ELEVATE invitation separately.', destination: 'Email reply or native post engagement; commercial destination pending founder confirmation.', avoid: 'A rigid cold-versus-warm rule or an unsupported promise that this copy swap increases sales.' },
    distribution: { channels: ['WIA founder email', 'Instagram carousel', 'Three Instagram reels with optional TikTok adaptations'], sequence: 'Use the email to establish the distinction, the carousel as a message map, and each reel to answer a separate messaging question.', adaptation: 'The LinkedIn caption can discuss message relevance with one hypothetical example; maintain the distinction between a proposed test and a result.' },
    success: { primarySignal: 'Readers can name an unanswered buyer question and match a message or proof topic to it.', secondarySignals: ['Message-map saves.', 'Relevant venue-owner replies about discovery versus consideration copy.'], measurementNote: 'Use available engagement and reply quality to assess understanding. The creative-placement test has no observed outcome in this export.' },
  }),
  'mock-fathom-2026-10-05-human-automation': brief({
    readerPromise: 'See a practical way to combine timely inquiry handling with control over what happens next, and identify one workflow worth reviewing.',
    distinctiveness: 'This is a sales-process design lesson about triggers and human review, not a product feature launch, migration success story, or generic speed-to-lead claim.',
    narrative: [
      { beat: 'Hook', direction: 'Start with the customer request: send the first inquiry email automatically, but let the owner choose when later messages begin.' },
      { beat: 'Problem', direction: 'An owner wants reliable follow-up without messages arriving after a conversation has changed. Name the tension between memory and an inflexible timer.' },
      { beat: 'Main point', direction: 'Map the buyer’s next decision, identify the human review point, and attach repeatable actions to a meaningful stage. Describe this as a workflow concept.' },
      { beat: 'Transformation', direction: 'The owner can define what should happen, who decides, and which events require a pause or a different next step.' },
      { beat: 'CTA', direction: 'Invite readers to identify the follow-up they still control manually. A LeadLock conversation can follow once configuration and scope are confirmed.' },
    ],
    evidencePolicy: {
      established: ['Danielle described a customer asking for an automatic first email with control over the rest of the sequence.', 'The team discussed selecting opportunity stages to trigger subsequent emails.', 'Migration work remained in progress; the discussion also raised the tendency to copy old sequences.'],
      hypotheses: ['Stage-based triggers may fit the sales conversation better than elapsed time alone.', 'Reply, booking, unavailability, and other pause conditions are review requirements for the proposed example, not confirmed product behaviour.'],
      excludedClaims: ['The setup is fully implemented or migrations are seamless.', 'This configuration has increased bookings or saved a measured number of hours.', 'LeadLock automatically handles every reply, booking event, or AI conversation described in the example.'],
    },
    email: {
      summary: 'An empathetic explanation of how repeatable actions and human judgment can work in the same inquiry system.',
      readerJob: 'Choose which decision needs their review and which action can follow consistently.',
      lengthGuidance: '400–550 words; one conceptual inquiry journey and one optional, approved commercial next step.',
      subjectDirections: ['Keep control of the next conversation', 'What should trigger the next email?', 'An inquiry system with room for judgment'],
      openingDirection: 'Introduce a request our team discussed, not a conversation Whitney personally had. Paraphrase anonymously by default and clearly state that the workflow is being designed.',
      outline: ['Validate the concern about a sequence sending the wrong message after a meaningful reply.', 'Explain the first-response-plus-human-review request.', 'Map a fictional inquiry: acknowledgment, availability/fit review, chosen next stage, and a relevant message.', 'Name pause and exception checks that the implementer must confirm; do not present an unverified feature tutorial.', 'Ask what the reader needs to decide personally before the next follow-up, then offer a LeadLock discussion only with confirmed scope and destination.'],
      cta: 'Primary: reply with the follow-up that still needs personal judgment. Optional Convert ending: an approved LeadLock inquiry invitation; choose one ending, not both.',
    },
    carousel: {
      summary: 'An eight-slide conceptual workflow showing where an immediate response, human review, selected stage, and pause checks belong.',
      readerJob: 'Map one inquiry sequence before copying it into a CRM.',
      slides: [
        slide(1, 'Hook', 'Let the conversation set the follow-up', 'Introduce responsiveness with control over the next step.', 'A simple inquiry path with a clearly marked review point.'),
        slide(2, 'Problem', 'The timer does not know the whole conversation', 'A reply, unavailable date, or booked appointment can change what is relevant. Use a hypothetical scenario.', 'Message timer beside a new reply; label it a workflow example.'),
        slide(3, 'Main point', 'Acknowledge the inquiry', 'Describe the role of a first response: confirm receipt and set an accurate next-step expectation.', 'Illustrative acknowledgment card; no availability or response-time promise.'),
        slide(4, 'Main point', 'Choose the human review point', 'Decide who checks availability, fit, and existing conversation before selecting the next stage.', 'Owner-review checkpoint with a named responsibility placeholder.'),
        slide(5, 'Main point', 'Give the next stage a purpose', 'A chosen sales stage can trigger the relevant message. Confirm actual configuration before teaching click-by-click steps.', 'Concept diagram labelled “configuration to confirm,” not a fake product screenshot.'),
        slide(6, 'Main point', 'Define the pauses and exceptions', 'Specify what should happen after a reply, booking, or unsuitable inquiry; these are implementation questions.', 'Exception checklist with questions, not feature-complete checkmarks.'),
        slide(7, 'Transformation', 'Move the process, not just the old emails', 'Review each email’s job and trigger before migrating a sequence.', 'Old email → buyer need → chosen trigger → new workflow.'),
        slide(8, 'CTA', 'Which follow-up needs your judgment?', 'Invite a comment or an approved LeadLock inquiry, selecting the ending that fits the intended funnel stage.', 'One invitation only; commercial URL added after confirmation.'),
      ],
      captionDirection: 'State that this is a workflow-design example based on a customer request. Clarify that detailed behaviour depends on configuration; avoid a rollout-success claim.',
    },
    reels: [
      reel('Automatic first step, thoughtful next step', 'Explain the hybrid approach', 'Demonstrate the requested balance between responsiveness and control.', 'Start with the request to automate the first email while controlling the rest.', ['Introduce the request through the team’s discussion.', 'Show the human review point.', 'Explain that a selected stage can guide the relevant next action, subject to confirmed setup.'], 'Founder and a conceptual three-card journey; no product screens by default.', 'Ask which step the viewer wants to keep control over.'),
      reel('What should change after a reply?', 'Expose the exception', 'Use one hypothetical reply to reveal why pause logic deserves attention.', 'Ask what the remaining sequence should do after a couple has already booked a tour.', ['Label the example hypothetical.', 'Identify the message that may now be irrelevant.', 'Ask the implementer to verify what pauses, changes, and who owns the review.'], 'Illustrative reply card and pause-question overlay, not a feature demonstration.', 'Invite viewers to review one pause condition in their own process.'),
      reel('Before you copy the old sequence', 'Give a migration audit', 'Audit one email’s purpose before transferring an existing CRM sequence.', 'Ask what the email is meant to help the couple decide.', ['Select one existing follow-up.', 'Name its buyer purpose and current trigger.', 'Keep or revise it intentionally rather than copying it by default.'], 'A blank purpose/trigger/owner worksheet, with no customer data.', 'Ask viewers to name the email they would review first; a LeadLock invitation needs founder confirmation.'),
    ],
    cta: { primaryAction: 'Reply with a workflow need; optional LeadLock inquiry after scope and destination are approved.', wordingDirection: 'Which follow-up do you still send manually because it needs your judgment?', offerBridge: 'LeadLock is the relevant service conversation. Explain the design need before introducing the offer; confirm supported triggers, exceptions, ownership, and current scope.', destination: 'Email reply or native engagement by default. The commercial inquiry link or booking destination is not yet supplied and must be confirmed.', avoid: 'Inventing a booking URL, a DM keyword workflow, an automatic reply capability, or a completed customer outcome.' },
    distribution: { channels: ['WIA founder email', 'Instagram carousel', 'Three founder reels for Instagram with selected TikTok adaptations'], sequence: 'Introduce the concept in email, map it in the carousel, and let the reels cover the hybrid workflow, the exception, and the migration audit separately.', adaptation: 'For LinkedIn, focus on process ownership and one implementation question. Use the Convert version only after the offer details are confirmed.' },
    success: { primarySignal: 'Owners describe a specific trigger, review point, or exception they need to resolve.', secondarySignals: ['Workflow-map saves.', 'Relevant LeadLock inquiries where an approved invitation is used.'], measurementNote: 'Count attributable inquiries only if the chosen CTA and tracking support that claim. The meeting supplies no bookings or time-saved baseline.' },
  }),
  'mock-fathom-2026-10-05-existing-footage': brief({
    readerPromise: 'Choose one existing clip that helps a couple picture the experience and define a deliberate next test without commissioning a new shoot first.',
    distinctiveness: 'This is about recognising and preparing an existing creative asset. It complements the buyer-stage lesson but centres on footage selection and the production backlog, not testimonial placement.',
    narrative: [
      { beat: 'Hook', direction: 'Start with the team opening the entertainment business’s Instagram archive and Whitney noticing useful copy on an existing reel.' },
      { beat: 'Problem', direction: 'Owners have real event material yet feel a new polished shoot must precede advertising. Acknowledge the production burden without dismissing polished assets.' },
      { beat: 'Main point', direction: 'Choose a moment that makes the desired experience tangible, check rights and freshness, and give it a message, audience, destination, and test.' },
      { beat: 'Transformation', direction: 'An intentional shortlist gives the owner candidates to test rather than an endless demand for more content. It does not guarantee ad performance.' },
      { beat: 'CTA', direction: 'Ask which existing clip helps a couple imagine their celebration and why.' },
    ],
    evidencePolicy: {
      established: ['The Meta team discussed importing existing organic posts into a campaign as further tests.', 'Whitney identified an existing reel for its copy; the team discussed a small creative backlog.', 'The independent Alina call also discussed reviewing material for possible reuse.'],
      hypotheses: ['An existing performance or guest-experience clip may communicate value more clearly than a generic service list.', 'A selected organic asset still needs a fair paid test; engagement does not establish inquiry or booking performance.'],
      excludedClaims: ['Organic footage always beats designed creative or predicts paid performance.', 'The saxophone discussion establishes a verified industry trend.', 'A clip delivered an unscoped CPL, more bookings, or a completed before-and-after transformation.'],
    },
    email: {
      summary: 'A founder observation about recognising a useful experience in the existing archive before asking for another shoot.',
      readerJob: 'Identify one owned asset and explain the buyer decision it could support.',
      lengthGuidance: '350–500 words; one source observation, one illustrative selection example, and one small audit.',
      subjectDirections: ['Look in the footage you already have', 'Which moment shows the experience?', 'Before you plan another content shoot'],
      openingDirection: 'Describe the team’s archive review anonymously. Whitney can reference noticing strong reel copy, but the public draft should not identify the post or imply permission to show it.',
      outline: ['Recognise the pressure to produce more while serving real weddings.', 'Explain the difference between showing a service and showing the experience a couple wants.', 'Use an illustrative entertainment moment to demonstrate experience, opening message, and next step; do not invent performance.', 'Give a three-item audit: what the clip communicates, whether rights and details are current, and what the campaign should learn.', 'Suggest a small backlog and distinguish deliberate campaign reuse from boosting every post.'],
      cta: 'Ask the reader to reply with one existing clip and what it helps a couple picture.',
    },
    carousel: {
      summary: 'An eight-slide asset-to-test checklist for turning existing wedding footage into a considered creative candidate.',
      readerJob: 'Build a small, usable shortlist and identify what each candidate still needs.',
      slides: [
        slide(1, 'Hook', 'Your next ad may already exist', 'Invite a look through existing footage before another production request.', 'Illustrative archive thumbnails; no copied client material.'),
        slide(2, 'Problem', 'More assets is not the first question', 'Ask what the buyer needs to picture rather than counting how much content is available.', 'Asset folder beside one buyer-experience question.'),
        slide(3, 'Main point', 'Find the experience', 'Look for a moment that communicates atmosphere, connection, or service value; avoid presenting one aesthetic as universal.', 'Approved or staged entertainment moment with an experience label.'),
        slide(4, 'Main point', 'Give the clip a message', 'Choose an opening that explains why this moment matters to the couple.', 'Clip frame plus a clearly hypothetical opening-copy direction.'),
        slide(5, 'Main point', 'Check permission and freshness', 'Confirm usage rights, identifiable people, audio, dated details, and the current offer before reuse.', 'A rights-and-details checklist; no unsupported clearance tick.'),
        slide(6, 'Main point', 'Choose the audience and next step', 'Place the clip in a considered campaign with a relevant destination. Reuse is not indiscriminate boosting.', 'Experience → message → audience → destination diagram.'),
        slide(7, 'Transformation', 'Build a shortlist to test', 'List three candidates with a different experience or message, then give each an adequate test opportunity.', 'Blank candidate/message/question backlog; no invented winning score.'),
        slide(8, 'CTA', 'Which clip would you choose?', 'Invite readers to save the audit and explain the experience their chosen clip communicates.', 'One simple question and a save prompt.'),
      ],
      captionDirection: 'Explain why the shortlist supports a test rather than predicts a winner. Keep the offer connection light, and ask for a clip choice or a buyer-experience observation.',
    },
    reels: [
      reel('Find the moment, not just the footage', 'Recognise the asset', 'Show how an experiential moment becomes a creative candidate.', 'Ask what a couple can imagine from one existing clip.', ['Show an approved, owned, or staged example.', 'Name the experience it communicates.', 'Explain why that makes it worth considering, without calling it a winner.'], 'Founder with approved B-roll; fallback is a storyboard card explicitly labelled illustrative.', 'Ask viewers which moment in their footage shows the experience best.'),
      reel('Give the clip a job', 'Demonstrate campaign context', 'Pair a candidate clip with a message and a relevant next step.', 'Ask what the clip should help a couple decide.', ['Choose one illustrative message.', 'Match its audience and next step.', 'Explain why organic likes do not answer the paid-campaign question.'], 'Three cards around a fictional clip frame: message, audience, next step.', 'Invite viewers to save the three-part check.'),
      reel('Make a three-clip backlog', 'Give a production action', 'Turn an existing archive into a small test shortlist.', 'Ask viewers to choose three clips before planning another shoot.', ['Assign a different experience or message to each candidate.', 'Check rights, dates, and offer details.', 'Write one learning question for each candidate and test deliberately.'], 'Founder filling a blank three-row shortlist with illustrative labels; no client media required.', 'Invite a comment about the first experience the viewer wants to test.'),
    ],
    cta: { primaryAction: 'Choose a clip, explain its buyer value, and save the asset audit.', wordingDirection: 'Which clip already helps a couple picture their celebration?', offerBridge: 'The Meta Ads Accelerator fits owners who have material but need strategy for using it in a campaign. Keep Attract/Warm invitations engagement-led unless Whitney selects a commercial version.', destination: 'Email reply or native comments/saves by default; no unconfirmed course URL or DM automation.', avoid: 'A performance prediction based on likes, a blanket boosting recommendation, or a promise that no new footage will ever be needed.' },
    creativeDirection: { ...creative, assets: ['Founder talking-head footage.', 'Owned and approved event clips with confirmed usage permissions and audio rights; otherwise use a staged example or an illustrative storyboard.', 'A three-row asset shortlist with experience, message, rights/freshness, and test-question columns.'] },
    distribution: { channels: ['WIA founder email', 'Instagram carousel', 'Three reels for Instagram with selected TikTok adaptations'], sequence: 'Use the first reel as an entry point, the carousel as the selection aid, and the email for the larger principle. Later reels demonstrate context and the backlog; assign dates separately.', adaptation: 'LinkedIn can use the same asset-selection principle with a short process caption. Use cleared footage and platform-appropriate audio for each published version.' },
    success: { primarySignal: 'Owners identify an existing clip and articulate the experience or question it could communicate.', secondarySignals: ['Asset-audit saves.', 'Relevant replies from businesses with footage but no clear creative-testing process.'], measurementNote: 'Assess whether responses show asset-selection understanding. Organic engagement is not proof of paid performance; campaign inquiries require a separate measured test.' },
  }),
};

/** Hydrate the four requested briefs without replacing saved edits or completed approvals. */
export function prepareFathomContentBrief(idea: ContentIdea, starterPlan?: ContentIdea['brief']['contentPlan']): ContentIdea {
  const productionBrief = FATHOM_CONTENT_BRIEFS[idea.id];
  if (!productionBrief || idea.brief.productionBrief) return idea;
  const savedPlan = idea.brief.contentPlan;
  const contentPlan = {
    email: !savedPlan || savedPlan.email === starterPlan?.email ? productionBrief.email.summary : savedPlan.email,
    carousel: !savedPlan || savedPlan.carousel === starterPlan?.carousel ? productionBrief.carousel.summary : savedPlan.carousel,
    reels: productionBrief.reels.map((reel, index) => !savedPlan || savedPlan.reels[index] === starterPlan?.reels[index] ? reel.summary : savedPlan.reels[index]) as [string, string, string],
  };
  return {
    ...idea,
    brief: { ...idea.brief, contentPlan, productionBrief },
  };
}
