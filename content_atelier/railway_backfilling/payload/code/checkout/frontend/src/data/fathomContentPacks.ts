import { ContentIdea, ContentPack, ReelScript } from '../types/atelier';

type SlideCopy = [string, string];
type ReelCopy = { title: string; hook: string; paragraphs: string[]; cta: string; visual: string };
type PackCopy = { title: string; subjects: string[]; preview: string; email: string; emailCta: string; slides: SlideCopy[]; reels: [ReelCopy, ReelCopy, ReelCopy]; caption: string; linkedIn: string };

function recordingScript(id: string, copy: ReelCopy, index: number): ReelScript {
  const spokenScript = [copy.hook, ...copy.paragraphs, copy.cta].join('\n\n');
  const words = spokenScript.split(/\s+/).length;
  return {
    id: `${id}-reel-${index + 1}`, angleTitle: copy.title, hook: copy.hook,
    duration: `About ${Math.ceil(words / 170 * 60)}–${Math.ceil(words / 145 * 60)} seconds · ${words} words`,
    visualCue: copy.visual, talkingPoints: copy.paragraphs, ctaText: copy.cta,
    spokenScript, spokenScriptVersion: 2,
    visualSequence: [
      { beat: 'Opening', direction: 'Founder to camera with the spoken hook as a short caption. Keep important text in the safe area.' },
      { beat: 'Demonstration', direction: copy.visual },
      { beat: 'Principle', direction: 'Return to the founder for the central explanation. Illustrations are teaching examples, not account results.' },
      { beat: 'Invitation', direction: `Close on the founder and a restrained end card: ${copy.cta}` },
    ],
  };
}
function pack(id: string, copy: PackCopy): ContentPack {
  const phases: ContentPack['carousel']['slides'][number]['phase'][] = ['Hook', 'Problem', 'Solution', 'Solution', 'Solution', 'Solution', 'Transformation', 'CTA'];
  return {
    email: { subjectLines: copy.subjects, previewText: copy.preview, body: `${copy.email}\n\n— Whitney\nWedding Industry Ads`, ctaButton: copy.emailCta, ctaUrl: '' },
    carousel: { title: copy.title, caption: copy.caption, slides: copy.slides.map(([headline, body], index) => ({ slideNumber: index + 1, phase: phases[index], headline, body, designNote: 'Use WIA navy, ivory, and restrained gold. One idea per slide, readable type, and labelled illustrative diagrams. Use cleared assets only.' })) },
    reels: copy.reels.map((reel, index) => recordingScript(id, reel, index)),
    captions: { longFormInstagram: copy.caption, linkedIn: copy.linkedIn },
    ruleChecks: { slideCountValid: copy.slides.length === 8, frameworkBeatsPresent: true, ctaMatchesTrack: true, voiceCriticPassed: false, overlapScore: null },
  };
}

// Editorial mock drafts derived from the four saved briefs. No invented client
// outcomes, named private clients, commercial URLs, or measured overlap scores.
export const FATHOM_CONTENT_PACKS: Record<string, ContentPack> = {
  'mock-fathom-2026-10-05-fair-comparison': pack('mock-fathom-2026-10-05-fair-comparison', {
    title: 'Before You Fix the Form, Check the Comparison',
    subjects: ['The form was the same', 'What changed before the leads changed?', 'Before you edit your landing page'],
    preview: 'A quieter few days can suggest a question. They do not always tell you what to fix.',
    email: `In a recent team review, we were looking at an early difference in inquiries between two landing pages. One suggestion was to shorten the form.

So we checked the forms.

They were the same.

That did not tell us which page was better. It told us that we needed a more useful question before deciding what to change.

I understand the pressure behind that moment. When you are investing in ads and the inbox feels quieter, leaving things alone can feel like doing nothing. Changing the page gives you something concrete to do.

But a result and an explanation are different things.

Before you make the edit, I would work through three questions.

First, what actually changed? Look at the page itself, the message leading into it, and the next step you are asking the couple to take. Check the proposed explanation against what is there.

Second, who reached each version? Someone actively searching for a venue and someone returning after seeing it on Instagram may arrive with different questions. Those journeys should not be collapsed into one conclusion.

Third, is the comparison useful? Consider the observation window, how much traffic you have, and whether an inquiry means the same thing in both reports. Matching the number of days is one check. It does not establish a winner by itself.

Then look beyond the first inquiry. Does it fit the business? What happens before a tour or consultation? A percentage has more meaning when you understand the conversation behind it.

You may still decide to change the page. The difference is that you can explain which question the change is intended to answer.

That is the work I want marketing data to support: a clearer next decision, rather than another task chosen because a few days felt uncomfortable.

If the evidence is still early, write down what you need to observe next and agree when to review it. That gives the team a shared question to return to, instead of several competing explanations.

Which landing-page change are you evaluating, and what do you expect it to improve? Reply and tell me.`,
    emailCta: 'Reply with your test question',
    slides: [
      ['Before you fix the form…', 'Ask whether the comparison supports that fix. A quieter week can reveal a question without revealing its answer.'],
      ['Fewer inquiries is an observation', 'It could relate to the page, the audience, timing, or measurement. Choosing an explanation comes after checking the evidence.'],
      ['Check what actually changed', 'In a team review, the forms on two pages were identical. That mattered because shortening the form was one proposed response.'],
      ['Keep different audiences separate', 'A new search visitor and a returning Instagram visitor may need different information. Read the channel and audience alongside the page.'],
      ['Check the comparison', 'Look at the observation window, available traffic, and inquiry definition. Equal time alone does not establish a reliable winner.'],
      ['Follow the inquiry further', 'A relevant inquiry, a tour, and a booking are different steps. Ask what the next conversation tells you about fit.'],
      ['Write one test question', 'I am changing __ because I expect __. I will observe __ consistently. Give the next decision a purpose before making several edits.'],
      ['What are you trying to learn?', 'Save this checklist for your next report. Which page change are you evaluating, and what question should it answer?'],
    ],
    reels: [
      { title: 'The identical-form moment', hook: 'We were discussing a form change. Then we checked the two forms, and they were the same.', paragraphs: ['That was useful because it changed the question. A quieter few days had made shortening the form sound like a reasonable next step. But first we needed to check whether the proposed explanation matched the pages.', 'When you run a wedding business, I understand why an edit can feel reassuring. You are doing something about the result. The trouble is that changing a variable without understanding it can make the next report harder to read.', 'Start with what actually changed, who reached the page, and what the available observations support. You might still make the edit. You will have a clearer reason for making it.'], cta: 'What do you check first when inquiries slow?', visual: 'Show two identical illustrative form cards, then return to the founder. Do not display live client pages or performance counts.' },
      { title: 'What makes the comparison useful?', hook: 'If two landing pages ran for the same number of days, does that make the comparison fair?', paragraphs: ['It is one thing to check. But the audience, the amount of traffic, and what you count as an inquiry still matter.', 'Think about a couple finding your venue through search and another returning after seeing your work on Instagram. They may arrive with different questions. A page observation from one journey does not automatically explain the other.', 'Before selecting a winner, ask whether the evidence is comparable and strong enough for the decision you want to make. If it is early, the useful outcome may be your next question rather than a confident conclusion. That is still progress when it helps you choose the next test.'], cta: 'Save these three checks: audience, observation, and tracking.', visual: 'Founder with three cards labelled audience, observation, and tracking; no invented statistical chart.' },
      { title: 'Write the test before the edit', hook: 'Before you change your landing page, finish this sentence: I am changing this because…', paragraphs: ['Choose one variable and name the effect you expect. Perhaps you want the next step to feel clearer to a couple who has just discovered your venue. That is a question you can work with.', 'Then decide how you will observe it consistently. Keep the audience and the inquiry definition in view, and look at what happens after the form is submitted.', 'You do not need to change the headline, the form, and the campaign at the same time just to feel that you are responding. A deliberate test gives the edit a purpose and makes the next conversation about your results more useful.'], cta: 'Tell me one change you are evaluating and what you want to learn.', visual: 'Write variable, expected effect, and observation on a blank teaching card labelled illustrative.' },
    ],
    caption: 'A quieter week can make every part of your funnel look like the problem. In a team review, checking two identical forms helped us question one proposed fix.\n\nBefore changing the page, ask what changed, who saw it, and whether the observations are comparable. Then follow the inquiry toward the next conversation.\n\nThis is a decision checklist, not a winning-page case study. Save it for your next report. What change are you trying to evaluate?',
    linkedIn: 'A result and an explanation are different things. A recent landing-page review made that concrete: the forms were identical, although shortening the form was one proposed response.\n\nCheck the variable, audience, and measurement before selecting a fix. Early observations can shape a better question without establishing a winner. Which question should your next marketing change answer?',
  }),
  'mock-fathom-2026-10-05-buyer-stage': pack('mock-fathom-2026-10-05-buyer-stage', {
    title: 'Your Best Testimonial Has a Place in the Journey',
    subjects: ['What your best review leaves unanswered', 'Give each venue message a job', 'Can a couple picture their day?'],
    preview: 'Relevant proof helps someone choose. First, ask what they need to understand.',
    email: `A strong testimonial is worth keeping. It tells a couple that someone else trusted your venue and had a good experience.

But there is another question I would ask before making that review the opening of every ad.

What does this couple need to understand next?

In a recent messaging review, our team discussed using more of a venue’s distinctive experience in discovery ads, then testing testimonial copy with a warmer audience. The account was still receiving leads. This was a refinement to explore, not a story about fixing a failed campaign.

The bigger lesson is about giving each message a job.

Imagine a garden venue as a teaching example. A couple finding it for the first time might need help picturing the ceremony, the transition into drinks, and the kind of celebration the space supports.

A beautiful photograph can begin that picture. The copy can make the experience clearer: what is distinctive, what it feels like, and who it might suit.

Later, that couple might be wondering how the venue handles a change in weather. At that point, an approved review describing the team’s support could be relevant proof. The review is useful because it answers a concern that matters to the decision.

That is different from repeating general praise wherever the couple sees you.

It also does not mean testimonials belong in only one place. A review can help a new audience too. The question is whether it answers something useful, and the placement is something to test rather than assume.

Here is a small audit to try. Put your discovery message next to your retargeting message. Write the buyer question each one answers. Does the second message help the couple understand something new, or mainly repeat the first?

Marketing can feel more coherent when the messages develop the conversation instead of restarting it.

Keep the answer specific to your venue. The experience, practical details, and proof should accurately reflect what you offer, so a couple can connect the message they see with the conversation they will have next.

What do couples need to feel confident about before they book a tour? Reply with the question you hear most often.`,
    emailCta: 'Reply with the next buyer question',
    slides: [
      ['Your best review has a job', 'It should help a couple understand something that matters to choosing you. Start with their next question.'],
      ['New photo. Same answer?', 'Changing the image can leave the underlying message unchanged. Discovery and consideration audiences may keep receiving the same general praise.'],
      ['Help them picture the experience', 'What does the venue make possible for their day? Describe something distinctive that helps a couple recognise whether it fits.'],
      ['Make one feature meaningful', 'Illustrative example: a garden ceremony followed by an easy transition into drinks. Connect the setting to an experience, rather than only naming an amenity.'],
      ['Find the concern that remains', 'A couple considering a tour may need clarity about weather, logistics, or support. Ask what uncertainty the next message should address.'],
      ['Choose proof for its relevance', 'Use an approved review that speaks to that concern. Do not invent a customer quotation when the right proof is unavailable.'],
      ['Let the messages develop', 'Experience, practical clarity, and relevant proof can work together. Test their placement; there is no universal rule that reviews only belong later.'],
      ['What is the next question?', 'Save this message map. What do couples need to feel confident about before booking a tour with you?'],
    ],
    reels: [
      { title: 'An amenity is not the whole experience', hook: 'What should a couple imagine when they read your venue’s feature list?', paragraphs: ['Take a garden as a hypothetical example. Calling it a garden gives the buyer a feature. Describing a ceremony and an easy transition into drinks gives them a way to picture their day.', 'The detail matters because it helps someone recognise fit. You are not trying to make every couple want the same celebration. You are helping the right couple understand the experience your space can support.', 'Before adding another photograph, read the message alongside it. Does it explain why the setting matters, or mainly list what is there? One specific, accurate detail can give the image a clearer role in the conversation.'], cta: 'Which experience should your venue be known for?', visual: 'Show a fictional feature-to-experience card. Real venue footage requires permission and accurate details.' },
      { title: 'Choose the review that answers the question', hook: 'A glowing review is useful. A relevant review can answer the question a couple is actually asking.', paragraphs: ['Imagine a couple wondering what happens if the weather changes. General praise tells them someone enjoyed the venue. A genuine, approved review about the team’s support could address a more specific concern.', 'That does not make the first review bad. It means the two messages do different jobs. Before choosing the quote, decide what uncertainty you want the proof to reduce.', 'And if you do not have a review that answers that concern, do not manufacture one. Give accurate practical information instead. The goal is to make the next decision clearer, wherever the message appears in the journey.'], cta: 'Which concern does your featured review actually answer?', visual: 'Pair a hypothetical weather question with a proof topic. Do not show a fabricated testimonial.' },
      { title: 'Audit the next message', hook: 'Does your second venue ad tell a couple anything the first one did not?', paragraphs: ['Put your discovery copy next to your consideration copy. Under each, write the question that message answers. Start with the buyer, rather than the format or the photograph.', 'One message might help them picture the experience. Another might explain a practical detail or introduce relevant proof. The exact order is something to test, not a rule to follow without thinking.', 'If both messages mainly repeat the same general praise, choose one unanswered question for your next copy test. You are giving the conversation somewhere to go. That is a more useful change than swapping an image and calling it a new angle.'], cta: 'Save this audit and name the next question your copy should answer.', visual: 'Two clearly hypothetical ad-copy cards with a buyer question written below each.' },
    ],
    caption: 'Your best review has a place in the conversation. The useful question is what it helps a couple understand.\n\nExperience, practical clarity, and relevant proof can each support a different decision. A team review prompted this placement idea; the export does not show a completed test result.\n\nSave the map and look at your current messages. What do couples need answered before they book a tour?',
    linkedIn: 'Changing a photograph does not necessarily change the message. When discovery and consideration copy repeat the same answer, the buyer may still have an important question.\n\nGive each message a job: make the experience clear, explain a practical detail, or offer relevant proof. Placement should be tested. What question does your next message need to answer?',
  }),
  'mock-fathom-2026-10-05-human-automation': pack('mock-fathom-2026-10-05-human-automation', {
    title: 'Let the Conversation Set the Follow-Up',
    subjects: ['Keep control of the next conversation', 'What should trigger the next email?', 'An inquiry system with room for judgment'],
    preview: 'An automatic first step can still leave space for a thoughtful next decision.',
    email: `Our team recently discussed a request from a venue owner: send the first inquiry email automatically, but let her decide when the rest of the sequence begins.

I think that request gets to the heart of a concern many wedding professionals have about automation.

You want people to hear from you promptly. You also want the next message to make sense for the conversation you are actually having.

Those needs can belong in the same process.

Imagine an inquiry arriving while you are working an event. As a workflow example, an acknowledgment confirms receipt and gives an accurate expectation about the next step. Then a person reviews availability, fit, and anything the couple has already shared before choosing what happens next.

Our team discussed using selected opportunity stages to trigger the relevant later emails. That is a design approach to explore, not a completed rollout we can claim results from.

The important question comes before the tool settings: which decision needs human judgment, and which action should follow consistently once that decision is made?

A timer can be useful. It also needs a process around the things that change the conversation. If a couple replies, books a tour, or asks about a date you cannot offer, what should happen to the remaining messages? Who owns that review?

Those are configuration questions to confirm with the person implementing the system. I would not assume that every pause or exception is already handled just because a sequence exists.

This matters when moving tools too. Copying the old emails can preserve a process you have never had time to question. Choose one message and ask what it helps the couple decide, why it sends when it does, and whether that trigger still fits.

A thoughtful system makes repeatable work easier to manage while giving your judgment a clear place in the process.

You can start by mapping those decisions on paper. Write the incoming situation, the person responsible for reviewing it, and the message that should follow. Include what happens when that person is unavailable or the inquiry needs a different path. Then take that map to the implementation conversation. It gives the team something concrete to confirm before assuming the sequence is ready for real couples.

Which follow-up do you still send manually because it needs your judgment? Reply and tell me what you need to decide before it goes out.`,
    emailCta: 'Reply about your follow-up workflow',
    slides: [
      ['Let the conversation set the follow-up', 'A timely first response and a human-controlled next step can belong in the same inquiry system.'],
      ['The timer has limited context', 'A reply, unavailable date, or booked tour may change the next useful message. Decide how your process should respond.'],
      ['Acknowledge the inquiry', 'A first response can confirm receipt and explain an accurate next step. It should not promise availability before it has been checked.'],
      ['Choose the review point', 'Who checks availability, fit, and the existing conversation? Give that judgment a defined place in the journey.'],
      ['Give the next stage a purpose', 'The team discussed selecting opportunity stages to trigger relevant emails. This is a workflow concept; confirm the actual configuration.'],
      ['Define pauses and exceptions', 'What changes after a reply, booking, or unsuitable inquiry? Write the questions down and verify who owns each response.'],
      ['Review the process before copying it', 'For one existing email, name its buyer purpose, trigger, and owner. Moving tools is an opportunity to review all three.'],
      ['Which step needs your judgment?', 'Save this workflow map. Tell us which follow-up you still control manually, and what you need to decide first.'],
    ],
    reels: [
      { title: 'Automatic first step, thoughtful next step', hook: 'A venue wanted the first inquiry email automated, but control over the emails that followed.', paragraphs: ['Our team discussed that request, and I think the underlying need is useful to understand. The owner wanted a timely response without giving up judgment about the next conversation.', 'As a workflow example, an acknowledgment confirms receipt. A person then reviews availability, fit, and what the couple has already said before selecting the next stage.', 'The team discussed using that chosen stage to trigger a relevant message. The configuration still needs confirming, so this is a process lesson rather than a finished product demonstration. Start by deciding what needs your review and what can happen consistently once you have made that decision.'], cta: 'Which follow-up step do you want to keep control over?', visual: 'A conceptual acknowledgment → human review → chosen next stage diagram, labelled as a workflow example.' },
      { title: 'What should change after a reply?', hook: 'Imagine a couple has booked a tour. What should the remaining inquiry emails do next?', paragraphs: ['That is a hypothetical example, but it is a useful question when reviewing a follow-up system. A message asking them to take a step they have already taken may no longer fit.', 'Before assuming the sequence handles it, ask what should pause, what should change, and who checks that the conversation is in the right place.', 'Those details depend on your actual setup. A workflow diagram is not proof that every exception has been configured. Write down one event that changes the next message, then review it with the person responsible for implementation. You are making the process more deliberate, rather than relying on a timer to understand the whole conversation.'], cta: 'Review one pause condition in your own inquiry process.', visual: 'An illustrative booked-tour reply and three questions: pause, change, owner. No unverified feature tutorial.' },
      { title: 'Before you copy the old sequence', hook: 'Before moving an email into a new system, ask what it is meant to help the couple decide.', paragraphs: ['Our team discussed how common it is to want the old sequence duplicated when moving tools. I understand the appeal. Familiar messages feel like one less decision to make.', 'But choose just one follow-up and look at its purpose, its trigger, and who owns the next step. Does it answer the question the couple has at that point? Does it still need to send when it does?', 'Keep the parts that serve the conversation. Review the parts that exist mainly because they have always been there. You do not have to redesign everything at once to make one piece of the process clearer.'], cta: 'Which email would you review first?', visual: 'A blank purpose/trigger/owner worksheet with an illustrative email, without real customer data.' },
    ],
    caption: 'You can want prompt inquiry handling and still want control over the next conversation. A customer request gave our team a concrete workflow to discuss: the first email goes out, then a chosen stage guides later messages.\n\nThis is a design example, not a completed rollout or a booking claim. Confirm triggers, pauses, and ownership for your actual setup.\n\nWhich follow-up needs your judgment before it sends?',
    linkedIn: 'A useful automation question is: which decision needs human judgment, and which action should follow consistently?\n\nA venue’s request for an automatic first response with control over later emails made that distinction clear. The team discussed stage-based triggers, with implementation details still to confirm.\n\nBefore copying an old sequence, review one email’s purpose, trigger, and owner.',
  }),
  'mock-fathom-2026-10-05-existing-footage': pack('mock-fathom-2026-10-05-existing-footage', {
    title: 'Your Next Ad May Already Be in Your Wedding Footage',
    subjects: ['Look in the footage you already have', 'Which moment shows the experience?', 'Before you plan another content shoot'],
    preview: 'Start with what a couple can picture from the material already in your archive.',
    email: `In a recent creative review, our team went back through an entertainment business’s existing Instagram material. One reel stood out to me because the copy was useful.

The conversation moved toward choosing a small shortlist of posts for further campaign tests.

I think that is a useful starting point for wedding professionals who feel every advertising decision needs another content shoot first.

You may already have material that shows the experience you deliver. The first task is to recognise what it communicates.

Imagine a performance clip as a teaching example. It could show the musician doing the job, or it could give a couple a sense of the atmosphere they want for their celebration. Those are related, but the second question helps you think about the buyer’s decision.

What can they picture about their own day after seeing this moment?

Before selecting the clip, work through three checks.

First, name the experience and the opening message. What does the footage make easier to understand, and what context does the copy need to add?

Second, check whether the material is usable now. Confirm permissions, identifiable people, audio rights, and any dated details or offer information. An existing post is not automatically cleared for every new use.

Third, decide what the campaign should learn. Give the clip an audience and a relevant next step. An organic like count does not tell you whether it will produce relevant paid inquiries.

You are building a candidate to test, not declaring a winner because the reel looks good or performed well on the grid.

Try choosing three clips and writing a different experience or message next to each. That small backlog can make the next creative conversation more focused.

This does not mean you will never need new footage. It means the decision to produce more can follow an intentional look at what you already have.

Keep the shortlist useful to the person building the campaign: include where the material lives, what it communicates, and what still needs clearance. That makes the next conversation about the assets easier to act on.

Which existing clip helps a couple picture their celebration? Reply and tell me why you would choose it.`,
    emailCta: 'Reply with one existing clip',
    slides: [
      ['Your next ad may already exist', 'Look through the material you already have before planning another shoot. Start with the experience a couple needs to picture.'],
      ['More assets is not the first question', 'A full archive can still feel unusable if you have not decided what each moment communicates to the buyer.'],
      ['Find the experience', 'Look for a moment that helps a couple imagine the atmosphere, connection, or service value they want. Choose for meaning, not appearance alone.'],
      ['Give the clip a message', 'Explain why the moment matters. The opening copy should help the footage answer a specific buyer question.'],
      ['Check rights and freshness', 'Confirm footage and audio permissions, identifiable people, dated details, and the current offer before reusing an existing post.'],
      ['Choose its campaign role', 'Give the clip an audience and a relevant next step. Deliberate campaign reuse is different from boosting every organic post.'],
      ['Build three candidates to test', 'List each clip, the experience or message it communicates, and the question the test should answer. Organic engagement does not predict a paid winner.'],
      ['Which clip would you choose?', 'Save the asset audit. Tell us which existing moment helps a couple picture their celebration and why it stands out.'],
    ],
    reels: [
      { title: 'Find the moment, not just the footage', hook: 'What can a couple picture about their own celebration from this clip?', paragraphs: ['That is the question I would ask while looking through your existing event footage. A performance moment may show that you deliver the service. It may also communicate the atmosphere the couple wants to create.', 'Before requesting another shoot, choose one moment and name the experience it makes clear. Then check whether you have the permissions and current details needed to use it.', 'You are recognising a creative candidate, not proving it will win as an ad. The message, audience, and next step still need thought, and the campaign needs a test. But you now have a more useful reason to choose the footage than simply liking how it looks.'], cta: 'Which moment in your archive shows the experience best?', visual: 'Use cleared event B-roll or a labelled illustrative storyboard. Explain the buyer experience without quoting paid results.' },
      { title: 'Give the clip a job', hook: 'A useful clip still needs a job in the campaign.', paragraphs: ['Start with what it helps a couple understand. Then choose the message that gives the moment context, the audience it is relevant to, and the next step you want to make clear.', 'An organic post can be a candidate for that work. Its like count does not answer the paid-campaign question, and reusing it deliberately is different from boosting everything on the grid.', 'Before calling the asset ready, explain the experience, message, and destination together. That makes the test more intentional. You can learn whether this candidate supports relevant inquiries rather than assume popularity tells you who will buy.'], cta: 'Save the three checks: message, audience, and next step.', visual: 'Place a fictional clip frame between three readable message/audience/next-step cards.' },
      { title: 'Make a three-clip backlog', hook: 'Before planning another shoot, choose three existing clips worth reviewing.', paragraphs: ['Write a different experience or message next to each candidate. One might communicate atmosphere; another might answer a practical question about the service. Choose the role before deciding which looks best.', 'Then check rights, audio, dates, and any offer details. If something is unclear, mark it for review instead of treating the clip as ready.', 'Finally, write the question each campaign test should answer. Give the candidates a fair opportunity and assess the relevant inquiry outcome, not just views. A small shortlist helps you make the next creative decision deliberately without promising that existing footage will always outperform new production.'], cta: 'What is the first experience you would test?', visual: 'Founder fills an illustrative three-row shortlist: experience, message, clearance, test question.' },
    ],
    caption: 'Your existing archive may hold a useful creative candidate. Ask what the moment helps a couple picture, then check its rights, current details, message, and next step.\n\nThe team discussed a shortlist for further tests. That is the lesson here: a considered candidate, not a guaranteed paid winner.\n\nSave the audit. Which clip would you choose first, and what experience does it communicate?',
    linkedIn: 'Before requesting more creative, ask what the existing material makes clear to the buyer. A team archive review led to a useful discussion about selecting posts for campaign tests.\n\nChoose the experience, confirm rights and freshness, and define the message, audience, and next step. Organic engagement alone does not establish paid performance. What is already in your archive that deserves a deliberate test?',
  }),
};

export function hydrateFathomMockPack(idea: ContentIdea): ContentIdea {
  const template = FATHOM_CONTENT_PACKS[idea.id];
  return template && idea.isMock && !idea.mockContentPack ? { ...idea, mockContentPack: template } : idea;
}
