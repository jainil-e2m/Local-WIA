import { ContentIdea, ContentPack } from '../types/atelier';
import { stampEditorialItem, WEEKLY_CONCEPT_LIMIT } from '../utils/editorialWeeks';
import { reelProduction } from '../utils/reelProduction';
import { FATHOM_WEEKLY_ANGLES, FATHOM_STARTER_PLANS } from './fathomWeeklyAngles';
import { prepareFathomContentBrief } from './fathomContentBriefs';
import { hydrateFathomMockPack } from './fathomContentPacks';

// Fictional demo concepts, not sourced client results or live research.
const concepts: [string, string, string, string][] = [
  ['The Inquiry That Arrived After Midnight', 'Venues', 'After-hours inquiries go unanswered until the next afternoon.', 'A warm instant acknowledgment can offer a tour slot without promising availability.'],
  ['Your Portfolio Is Not a Pricing Strategy', 'Photographers', 'Beautiful galleries attract attention but leave buyers unsure of the investment.', 'Explain the experience and starting investment before inviting a consultation.'],
  ['The Three Questions Before a Floral Proposal', 'Florists', 'Detailed custom proposals are written before confirming fit.', 'Ask about priorities, guest count, and investment before designing a proposal.'],
  ['Why Couples Abandon the Venue Tour Form', 'Venues', 'A long first-contact form creates friction for curious couples.', 'Collect the essentials first and gather planning details after the tour is booked.'],
  ['Stop Selling Hours, Start Selling Peace of Mind', 'Coordinators', 'Coordination is compared purely on hours and price.', 'Show the decisions and last-minute problems a coordinator takes off the couple’s plate.'],
  ['The Wedding Film Preview That Starts a Conversation', 'Videographers', 'Long highlight films are shared without a clear next step.', 'Pair a short emotional preview with a specific invitation to discuss the couple’s story.'],
  ['A Consultation Is Not a Free Planning Session', 'Designers', 'Discovery calls drift into unpaid design work.', 'Use a structured conversation to establish fit before offering detailed creative recommendations.'],
  ['The Calm Follow-Up After a Busy Wedding Weekend', 'Beauty Teams', 'Weekend inquiries are forgotten during on-site bookings.', 'Create a Monday follow-up queue with personalized availability and trial invitations.'],
  ['The Venue Tour Before the Venue Tour', 'Venues', 'Couples arrive without understanding ceremony and reception flow.', 'A short walkthrough email helps couples picture their day before visiting.'],
  ['When a Photography Package Has Too Many Choices', 'Photographers', 'Buyers struggle to compare a long menu of add-ons.', 'Lead with a recommended collection and explain which circumstances justify extras.'],
  ['The Seasonal Flower Conversation', 'Florists', 'Pinterest requests create unrealistic expectations about seasonal availability.', 'Teach the desired visual effect before discussing individual flower varieties.'],
  ['The Travel Fee Nobody Wants to Explain', 'Videographers', 'Destination travel costs appear too late in the proposal.', 'Set transparent travel expectations during qualification and connect them to reliable coverage.'],
  ['A Menu Tasting That Sells the Guest Experience', 'Caterers', 'Tastings focus on dishes rather than how the event will feel.', 'Connect the menu to service flow, dietary care, and guest comfort.'],
  ['The Rental Wishlist Versus the Real Floor Plan', 'Rental Teams', 'Couples request beautiful items that do not fit the venue.', 'Start with a room plan, then build a cohesive rental selection.'],
  ['What Your Inquiry Auto-Reply Should Never Say', 'Coordinators', 'Generic replies make a premium service feel impersonal.', 'Acknowledge the event, explain the next step, and give a realistic response window.'],
  ['The Band Demo That Answers the Wrong Question', 'Entertainment', 'Performance clips do not show how a band handles an entire reception.', 'Demonstrate transitions, announcements, and the energy arc as well as musical ability.'],
  ['The Micro-Wedding Is Not a Miniature Package', 'Venues', 'Smaller celebrations are assumed to require proportionally less planning.', 'Describe the intentional experience and fixed production requirements of intimate events.'],
  ['The Engagement Shoot as a Trust Builder', 'Photographers', 'Engagement sessions are presented as a bonus rather than preparation.', 'Explain how the session builds confidence and clarifies the couple’s preferences.'],
  ['Why Floral Budgets Need a Priority Map', 'Florists', 'Every inspiration image is treated as equally important.', 'Identify the two or three visual moments that should carry the floral investment.'],
  ['The Audio Detail Couples Forget to Ask About', 'Videographers', 'Film inquiries focus only on visuals.', 'Show how vows, speeches, and ambient sound make a film personal.'],
  ['A Rain Plan Is Part of the Luxury Experience', 'Designers', 'Contingency plans are treated as an unwelcome afterthought.', 'Show that thoughtful alternatives protect both the guest experience and the design.'],
  ['The Late-Night Snack That Fits the Timeline', 'Caterers', 'Food additions are chosen without considering service timing.', 'Position late-night service around dancing, transport, and the guest journey.'],
  ['When Custom Stationery Starts Too Late', 'Stationers', 'Couples underestimate proofing and production lead times.', 'Publish a backwards planning timeline that makes the next decision easy.'],
  ['The Trial Appointment Before the Beauty Booking', 'Beauty Teams', 'Clients are unsure what a trial establishes.', 'Use the trial to align style, comfort, timing, and photography expectations.'],
  ['The Destination Wedding Inquiry Checklist', 'Coordinators', 'Destination leads arrive without travel or event scope details.', 'Qualify the location, number of events, and support needed before preparing a proposal.'],
  ['Your Venue’s Quietest Month Has a Different Buyer', 'Venues', 'Off-season messaging simply discounts the standard offer.', 'Explain the distinct atmosphere and flexibility of a quieter season.'],
  ['The Gallery Delivery Email Worth Remembering', 'Photographers', 'Gallery handoffs contain only a download link.', 'Guide couples through reliving, sharing, and preserving their images.'],
  ['Repurposing Ceremony Flowers Without Losing the Moment', 'Florists', 'Reusing installations is discussed without considering transfer logistics.', 'Explain the timing, labor, and design requirements of thoughtful repurposing.'],
  ['The Welcome Party Has Its Own Story', 'Videographers', 'Multi-day coverage is sold only as extra hours.', 'Explain how welcome events add context and relationships to the final film.'],
  ['The Signature Cocktail Beyond the Pretty Name', 'Caterers', 'Custom drinks are selected without checking service practicality.', 'Balance the couple’s story with batch preparation, glassware, and guest preferences.'],
  ['The Dance Floor Size That Changes the Reception', 'Rental Teams', 'Dance floors are chosen by appearance alone.', 'Connect floor size to guest count, furniture placement, and the entertainment plan.'],
  ['The Ceremony Music Brief That Prevents Surprises', 'Entertainment', 'Song requests arrive without cues or arrangement preferences.', 'Collect entrance timing, transitions, and live performance requirements in one brief.'],
  ['Your Wedding Website Is a Guest-Service Tool', 'Stationers', 'Wedding websites are treated as purely decorative.', 'Make travel, dress code, schedules, and RSVP instructions easy to find.'],
  ['The First Look Is a Timeline Decision', 'Photographers', 'First-look advice is framed as a universal rule.', 'Explain the trade-offs in daylight, privacy, portraits, and time with guests.'],
  ['The Venue FAQ That Saves a Consultation', 'Venues', 'Basic logistical questions consume every discovery call.', 'Answer access, transport, curfews, and inclusions before the couple books a call.'],
  ['The Mood Board Is a Conversation, Not a Contract', 'Designers', 'Inspiration boards are interpreted as exact promises.', 'Use the board to align palette and feeling while clarifying what can change.'],
  ['The Ceremony Arch and the Camera Angle', 'Florists', 'An installation looks beautiful in isolation but blocks important views.', 'Design the ceremony focal point around guest sightlines and photography positions.'],
  ['The Film Length Question Hides a Bigger Need', 'Videographers', 'Couples compare film packages by runtime alone.', 'Ask which people and moments they want to remember before recommending deliverables.'],
  ['The Dietary RSVP Detail That Protects Dinner Service', 'Caterers', 'Dietary requirements are collected informally and reach the kitchen too late.', 'Create one reliable collection deadline and communicate how requirements will be handled.'],
  ['The Beauty Schedule Before the Wedding Morning', 'Beauty Teams', 'Preparation timing is planned without accounting for the full group.', 'Build the schedule backwards from dressing and portrait times, with realistic buffers.'],
  ['The Hotel Block Is Part of the Guest Journey', 'Coordinators', 'Accommodation is booked without considering transport and event timing.', 'Choose the block alongside transfers, accessibility, and the weekend schedule.'],
  ['The Furniture Package That Makes Conversation Easier', 'Rental Teams', 'Lounge selections are based only on matching colors.', 'Use seating groups and pathways to support natural conversation and circulation.'],
  ['The Reception Entrance Should Not Feel Rehearsed', 'Entertainment', 'Couples receive generic entrance formats that do not suit their personalities.', 'Offer a few tailored energy levels and confirm names, cues, and preferences.'],
  ['The Invitation Detail That Reduces Guest Questions', 'Stationers', 'Invitations omit practical information in favor of minimal styling.', 'Keep the main card elegant while giving guests a clear route to essential details.'],
  ['The Site Visit Is More Than a Walkthrough', 'Designers', 'Site visits happen without a shared decision agenda.', 'Review access, power, layout, sightlines, and responsibilities before approving the design.'],
  ['The Backup Camera Conversation Builds Confidence', 'Photographers', 'Equipment questions are dismissed as too technical.', 'Explain redundancy and contingency procedures in plain language without overwhelming the couple.'],
  ['The Venue Comparison Sheet With No Fine Print', 'Venues', 'Couples compare headline prices without understanding what is included.', 'Show inclusions, restrictions, and likely additional needs in a transparent comparison.'],
  ['The Post-Wedding Thank-You That Opens a Referral', 'Coordinators', 'Referral requests arrive before the couple has had time to reflect.', 'Lead with a personal thank-you, then offer an optional review or referral invitation.'],
];

// Keep the 48 fictional demos in Previous Concepts. The current week uses
// four source-based Fathom proposals; existing demo approvals stay attached.
const weekSizes = [4, 3, 2, 4, 1, 3, 4, 2, 4, 3, 2, 4, 3, 4, 3, 2];
const assignments = weekSizes.flatMap((count, weekIndex) => {
  const monday = new Date('2026-10-05T06:30:00Z');
  monday.setUTCDate(monday.getUTCDate() - 7 * (weekIndex === 0 ? 1 : weekIndex + 1));
  return Array.from({ length: count }, (_, slot) => ({ week: monday.toISOString().slice(0, 10), weekIndex, slot }));
});
// Seeded randomness: varied stages, stable after reload, no accidental rerolls.
let randomState = 1729;
const stageRolls = assignments.map(() => {
  randomState = (Math.imul(randomState, 1664525) + 1013904223) >>> 0;
  return randomState % 3;
});
const studioNames = ['Willow & Stone', 'Juniper House', 'Aster Collective', 'Ivory Lane', 'Cedar & Silk', 'Saffron Studio', 'Marigold House', 'Linen & Light'];

function mockPack(idea: ContentIdea): ContentPack {
  const insight = idea.brief.coreInsight;
  const spine = idea.brief.messageSpine;
  const cta = `Explore ${idea.suggestedCta} with Wedding Industry Ads`;
  const phases: ContentPack['carousel']['slides'][number]['phase'][] = ['Hook', 'Problem', 'Problem', 'Solution', 'Solution', 'Transformation', 'How We Help', 'CTA'];
  const beats = [idea.title, idea.brief.audiencePain, 'The question behind the inquiry', insight, spine[1], spine[2], 'Build this into your client journey', cta];
  return {
    email: { subjectLines: [idea.title, `A better approach for ${idea.client}`, `The next step: ${idea.subtitle}`], previewText: insight,
      body: `Mock editorial draft — fictional example.\n\n${idea.title}\n\n${idea.brief.audiencePain}\n\n${insight}\n\n${spine.map((line, index) => `${index + 1}. ${line}`).join('\n\n')}\n\nStart by reviewing one real inquiry and identifying where this conversation can be clearer.\n\n${cta}\n\n— Whitney`, ctaButton: cta, ctaUrl: `https://weddingindustryads.com/${idea.suggestedCta.toLowerCase()}` },
    carousel: { title: idea.title, caption: `Mock draft: ${insight} Save this checklist for your next client conversation.`, slides: beats.map((headline, index) => ({ slideNumber: index + 1, phase: phases[index], headline, body: index === 0 ? idea.subtitle : index === 7 ? cta : spine[(index - 1) % spine.length], designNote: 'Navy type, ivory surface, restrained gold accent.' })) },
    reels: ['The misconception', 'The better conversation', 'One action to try'].map((angleTitle, index) => ({ id: `${idea.id}-reel-${index + 1}`, angleTitle: `${idea.title}: ${angleTitle}`, duration: '30–45 seconds', hook: [idea.title, idea.brief.audiencePain, insight][index], visualCue: 'Founder speaking to camera with a fictional inquiry checklist.', talkingPoints: [spine[index], insight, 'Use a fictional example; make no unverified performance claims.'], ctaText: cta })).map((reel, index) => ({ ...reel, ...reelProduction(reel, index) })),
    captions: { longFormInstagram: `${idea.title}\n\n${insight}\n\n${spine.join('\n\n')}\n\n${cta}\n\nMock content for demonstration.`, linkedIn: `${idea.title}\n\n${idea.brief.audiencePain}\n\n${insight}\n\n${cta}\n\nFictional editorial example.` },
    ruleChecks: { slideCountValid: true, frameworkBeatsPresent: true, ctaMatchesTrack: true, voiceCriticPassed: false, overlapScore: 0 },
  };
}

const FICTIONAL_ARCHIVE_IDEAS: ContentIdea[] = concepts.map(([title, sector, pain, insight], index) => {
  const { week: editorialWeek, slot, weekIndex } = assignments[index];
  const createdAt = `${editorialWeek}T03:${String(slot * 5).padStart(2, '0')}:00.000Z`;
  const stage = weekIndex === 0 ? [0, 1, 0, 2][slot] : stageRolls[index];
  const gate = (['gate1_angle', 'gate2_brief', 'gate3_pack'] as const)[stage];
  const suggestedCta = (['Elevate', 'Accelerators', 'LeadLock'] as const)[index % 3];
  const idea: ContentIdea = {
    id: `mock-editorial-v1-${String(index + 1).padStart(2, '0')}`, isMock: true, mockLayoutVersion: 3, title, subtitle: `A practical client-acquisition angle for ${sector.toLowerCase()}.`,
    badge: (['Client Call', 'Industry Trend', 'Client Story', 'Workshop Vault'] as const)[index % 4], daysAgo: 'Mock content', createdAt, editorialWeek, timestamp: editorialWeek,
    primaryQuote: `We want a clearer way to help couples with this: ${pain}`, client: `${studioNames[slot]} · ${sector}`, sourceType: 'manual', sourceDetails: `Mock weekly digest · ${sector} · fictional client example`, score: 82 + index % 16,
    scoresBreakdown: { proof: 80 + index % 15, audiencePain: 86 + index % 12, offerFit: 85 + index % 13, recurrence: 80 + index % 16, novelty: 78 + index % 19, demand: 84 + index % 14 }, suggestedCta, gate,
    angleApprovedAt: gate === 'gate1_angle' ? undefined : `${editorialWeek}T05:00:00.000Z`, briefApprovedAt: gate === 'gate3_pack' ? `${editorialWeek}T06:00:00.000Z` : undefined,
    brief: { coreInsight: insight, messageSpine: [pain, insight, `Make the next step a simple, relevant invitation for ${sector.toLowerCase()} clients.`], audiencePain: pain,
      formatSplit: { emailFocus: `Founder perspective: ${title}. Lead with the inquiry problem and one practical change.`, carouselFocus: `An eight-slide breakdown of ${title.toLowerCase()}, from problem to recommended client journey.`, reelsFocus: `Three short videos: the misconception, a better conversation, and one action to try for ${sector.toLowerCase()}.` }, claimsRequiringConsent: ['All client examples are fictional. Replace mock quotes and validate claims before publishing.'], openQuestionsForWhitney: [`Should ${title.toLowerCase()} lead with the client story or the practical checklist?`] },
    research: { searchQuery: `${sector.toLowerCase()} ${title.toLowerCase()}`, googleTrendsScore: 72 + index % 24, trendDirection: index % 2 ? 'stable' : 'rising', peopleAlsoAsk: [`How can ${sector.toLowerCase()} improve this client conversation?`, `What should couples know about ${title.toLowerCase()}?`, `How can wedding professionals address: ${pain.toLowerCase()}`], autocomplete: [`${sector.toLowerCase()} inquiry checklist`, `${title.toLowerCase()} advice`], forumDiscussions: [{ source: 'Mock research note — not live search data', snippet: pain, date: editorialWeek }] },
  };
  if (gate === 'gate3_pack') idea.pack = mockPack(idea);
  return idea;
});

export const EDITORIAL_MOCK_IDEAS: ContentIdea[] = [...FATHOM_WEEKLY_ANGLES, ...FICTIONAL_ARCHIVE_IDEAS];

/** Add demo records once without replacing any saved changes to their stable IDs. */
export function mergeEditorialMocks(existing: ContentIdea[]): ContentIdea[] {
  const seedById = new Map(EDITORIAL_MOCK_IDEAS.map(idea => [idea.id, idea]));
  const migrated = existing.map(idea => hydrateFathomMockPack(prepareFathomContentBrief(idea, FATHOM_STARTER_PLANS[idea.id]))).map(idea => {
    const seed = seedById.get(idea.id);
    if (!seed || idea.revivedAt) return idea;
    // Reset the old prepared/replayed Fathom week once. Future manual approvals
    // keep version 4 and survive reloads; source analysis and edits stay attached.
    if (seed.mockLayoutVersion === 4 && (idea.mockLayoutVersion ?? 0) < 4) {
      return { ...idea, mockLayoutVersion: 4, gate: 'gate1_angle' as const,
        mockContentPack: idea.pack ?? idea.mockContentPack, pack: undefined,
        angleApprovedAt: undefined, briefApprovedAt: undefined,
        publishingApprovedAt: undefined, scheduledAt: undefined, contentSchedules: undefined, mockSimulation: undefined };
    }
    if (idea.mockLayoutVersion === seed.mockLayoutVersion) return idea;
    const untouched = (idea.gate === 'gate1_angle' && !idea.angleApprovedAt)
      || (idea.gate === 'gate2_brief' && idea.angleApprovedAt?.endsWith('T05:00:00.000Z') && !idea.briefApprovedAt)
      || (idea.gate === 'gate3_pack' && idea.angleApprovedAt?.endsWith('T05:00:00.000Z') && idea.briefApprovedAt?.endsWith('T06:00:00.000Z'));
    return { ...seed, ...idea, mockLayoutVersion: 3, createdAt: seed.createdAt, editorialWeek: seed.editorialWeek, timestamp: seed.timestamp,
      ...(untouched ? { gate: seed.gate, pack: seed.pack, angleApprovedAt: seed.angleApprovedAt, briefApprovedAt: seed.briefApprovedAt } : {}) };
  });
  const ids = new Set(migrated.map(idea => idea.id));
  const result = [...migrated, ...EDITORIAL_MOCK_IDEAS.filter(idea => !ids.has(idea.id))];
  // Existing user records keep their dates. Move only demo overflow to earlier weeks.
  const counts = new Map<string, number>();
  for (const idea of result.filter(idea => !seedById.has(idea.id) || idea.revivedAt)) {
    const week = stampEditorialItem(idea).editorialWeek!;
    counts.set(week, (counts.get(week) || 0) + 1);
  }
  return result.map(idea => {
    if (!seedById.has(idea.id) || idea.revivedAt) return idea;
    let week = idea.editorialWeek!;
    while ((counts.get(week) || 0) >= WEEKLY_CONCEPT_LIMIT) {
      const monday = new Date(`${week}T06:30:00Z`);
      monday.setUTCDate(monday.getUTCDate() - 7);
      week = monday.toISOString().slice(0, 10);
    }
    counts.set(week, (counts.get(week) || 0) + 1);
    return week === idea.editorialWeek ? idea : { ...idea, editorialWeek: week, createdAt: `${week}T03:00:00.000Z`, timestamp: week };
  });
}
