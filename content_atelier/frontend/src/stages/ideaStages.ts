import { ContentIdea, ContentPack } from '../types/atelier';
import { briefingOverview, briefingSimilarity } from '../utils/briefingOverview';
import { reelProduction } from '../utils/reelProduction';
import { productionBriefMarkdown } from '../utils/productionBriefMarkdown';

/**
 * The detail modal tabs are pipeline stages. Each selector below returns only
 * the artifact that stage is allowed to show.
 *
 * 1. Approvals & Gates — the content angle, and the brief that arrived with it.
 * 2. Content Brief — the model's one-page brief, as markdown.
 * 3. Draft Pack — the five generated contents (email, carousel, three reels).
 */

export interface ContentAngleView {
  title: string;
  subtitle: string;
  quote: string;
  client: string;
  sourceDetails: string;
  badge: string;
  score: number;
  suggestedCta: ContentIdea['suggestedCta'];
  scores: { label: string; value: number }[];
}

export interface ReceivedBriefView {
  coreInsight: string;
  messageSpine: string[];
  audiencePain: string;
  formatSplit: {
    email: string;
    carousel: string;
    reels: string;
  };
  claims: string[];
  openQuestions: string[];
}

export type DraftContentKind = 'email' | 'carousel' | 'reel';

export interface DraftSection {
  label: string;
  text: string;
  heading?: string;
}

export interface DraftContentPiece {
  order: number;
  id: string;
  kind: DraftContentKind;
  title: string;
  meta: string;
  sections: DraftSection[];
  sourceText?: string;
}

const DRAFT_CONTRACT_SIZE = 5;

/** Split supplied production copy for reading while retaining the original for copy/export. */
function labelledSections(text: string): DraftSection[] {
  const markers = [...text.matchAll(/^(DATE|SEND TIME|RECIPIENTS|SUBJECT|PREVIEW TEXT|Format|Cover|On-screen hook|Script|Caption|On-screen text(?: \([^\n)]+\))?):[ \t]*/gm)];
  const labels: Record<string, string> = { DATE: 'Date', 'SEND TIME': 'Send time', RECIPIENTS: 'Recipients', SUBJECT: 'Subject', 'PREVIEW TEXT': 'Preview text', Script: 'Spoken script' };
  return markers.flatMap((marker, index) => {
    const body = text.slice(marker.index! + marker[0].length, markers[index + 1]?.index ?? text.length).trim();
    if (marker[1].startsWith('On-screen text')) {
      const screens = [...body.matchAll(/^\d+\.\s+([\s\S]*?)(?=^\d+\.\s|$(?![\s\S]))/gm)];
      if (screens.length) return screens.map((screen, number) => ({ label: `Screen ${number + 1}`, text: screen[1].trim() }));
    }
    return [{ label: labels[marker[1]] ?? marker[1], text: body }];
  });
}

function suppliedCarouselSections(text: string): DraftSection[] {
  const captionStart = text.indexOf('\nCaption:\n');
  const slides = captionStart >= 0 ? text.slice(0, captionStart) : text;
  return [
    ...[...slides.matchAll(/^Slide (\d+)\n([\s\S]*?)(?=^Slide \d+\n|$(?![\s\S]))/gm)].map(match => {
      const [heading, ...body] = match[2].trim().split('\n');
      return { label: `Slide ${match[1]}`, heading, text: body.join('\n') };
    }),
    ...(captionStart >= 0 ? [{ label: 'Carousel caption', text: text.slice(captionStart + '\nCaption:\n'.length).trim() }] : []),
  ];
}

export function selectContentAngle(idea: ContentIdea): ContentAngleView {
  const scores = idea.scoresBreakdown;
  return {
    title: idea.title,
    subtitle: idea.subtitle,
    quote: idea.primaryQuote,
    client: idea.client,
    sourceDetails: idea.sourceDetails,
    badge: idea.badge,
    score: idea.score,
    suggestedCta: idea.suggestedCta,
    scores: [
      { label: 'Proof', value: scores.proof },
      { label: 'Audience pain', value: scores.audiencePain },
      { label: 'Offer fit', value: scores.offerFit },
      { label: 'Recurrence', value: scores.recurrence },
      { label: 'Novelty', value: scores.novelty },
      { label: 'Demand', value: scores.demand },
    ],
  };
}

export function selectReceivedBrief(idea: ContentIdea): ReceivedBriefView {
  const brief = idea.brief;
  return {
    coreInsight: brief.coreInsight,
    messageSpine: brief.messageSpine,
    audiencePain: brief.audiencePain,
    formatSplit: {
      email: brief.formatSplit.emailFocus,
      carousel: brief.formatSplit.carouselFocus,
      reels: brief.formatSplit.reelsFocus,
    },
    claims: brief.claimsRequiringConsent,
    openQuestions: brief.openQuestionsForWhitney,
  };
}

/** The content-brief stage is the model's write-up, not the structured brief cards. */
export function composeContentBriefMarkdown(idea: ContentIdea): string {
  if (idea.suppliedCopy?.brief) return idea.suppliedCopy.brief;
  if (idea.brief.productionBrief) return productionBriefMarkdown(idea);
  const brief = selectReceivedBrief(idea);
  const angle = selectContentAngle(idea);
  const plan = briefingOverview(idea);
  const similarity = briefingSimilarity(idea);
  const spine = brief.messageSpine.map((line, index) => `${index + 1}. ${line}`).join('\n');
  const claims = brief.claims.length
    ? brief.claims.map((claim) => `- ${claim}`).join('\n')
    : '- All claims verified and cleared for public use.';
  const questions = brief.openQuestions.length
    ? brief.openQuestions.map((question) => `- ${question}`).join('\n')
    : '- No unresolved questions.';

  return [
    `# ${angle.title}`,
    '',
    `> ${angle.quote}`,
    '',
    `*${angle.client} · ${angle.sourceDetails}*`,
    '',
    `**Target offer:** ${angle.suggestedCta}`,
    '',
    '## Core insight',
    '',
    brief.coreInsight,
    '',
    '## Audience pain',
    '',
    brief.audiencePain,
    '',
    '## Message spine',
    '',
    spine,
    '',
    '## What we will generate',
    '',
    ...plan.flatMap(piece => [`### ${piece.label} · ${piece.purpose}`, '', piece.gist, '']),
    '## Past four months · Similarity review',
    '',
    `**${similarity.status}**`,
    '',
    similarity.summary,
    '',
    ...similarity.matches.flatMap(match => [`### ${match.title} · ${match.publishedAt.slice(0, 10)}`, '', `**Overlap:** ${match.similarity}`, '', '**How this version differs:**', '', ...(match.modifications.length ? match.modifications.map(change => `- ${change}`) : ['- Changes have not been documented yet. Define a distinct angle before approval.']), '']),
    '',
    '## Claims requiring consent',
    '',
    claims,
    '',
    '## Open questions',
    '',
    questions,
    '',
  ].join('\n');
}

function emailPiece(pack: ContentPack): DraftContentPiece {
  return {
    order: 1,
    id: 'email',
    kind: 'email',
    title: pack.email.subjectLines[0] ?? 'Marketing email',
    meta: 'Email',
    sections: [
      {
        label: 'Subject lines',
        text: pack.email.subjectLines.map((line) => `• ${line}`).join('\n'),
      },
      { label: 'Preview', text: pack.email.previewText },
      { label: 'Body', text: pack.email.body },
      { label: 'Call to action', text: `${pack.email.ctaButton}\n${pack.email.ctaUrl}` },
      { label: 'LinkedIn caption', text: pack.captions.linkedIn },
    ],
  };
}

function carouselPiece(pack: ContentPack): DraftContentPiece {
  return {
    order: 2,
    id: 'carousel',
    kind: 'carousel',
    title: pack.carousel.title,
    meta: `Carousel · ${pack.carousel.slides.length} slides`,
    sections: [
      ...pack.carousel.slides.map((slide) => ({
        label: `Slide ${slide.slideNumber} · ${slide.phase}`,
        text: `${slide.headline}\n\n${slide.body}`,
      })),
      { label: 'Carousel caption', text: pack.carousel.caption },
      { label: 'Instagram caption', text: pack.captions.longFormInstagram },
    ],
  };
}

function reelPiece(pack: ContentPack, index: number): DraftContentPiece | null {
  const reel = pack.reels[index];
  if (!reel) return null;
  const production = reelProduction(reel, index);
  return {
    order: 3 + index,
    id: reel.id || `reel-${index + 1}`,
    kind: 'reel',
    title: reel.angleTitle,
    meta: `Reel ${index + 1} · ${production.duration}`,
    sections: [
      { label: 'Hook', text: reel.hook },
      { label: 'Visual direction', text: reel.visualCue },
      {
        label: 'Talking points',
        text: reel.talkingPoints.map((point) => `• ${point}`).join('\n'),
      },
      { label: 'Call to action', text: reel.ctaText },
      { label: 'Spoken script', text: production.spokenScript },
      { label: 'What to show · Suggested video visuals', text: production.visualSequence.map(shot => `${shot.beat}\n${shot.direction}`).join('\n\n') },
    ],
  };
}

/**
 * Draft pack is a fixed five-content contract: one email, one carousel,
 * and three reels. Missing reels are omitted rather than invented.
 */
export function selectDraftContents(pack: ContentPack | undefined): DraftContentPiece[] {
  if (!pack) return [];
  if (pack.suppliedCopy) {
    const copy = pack.suppliedCopy;
    const bodyStart = copy.email.indexOf('Hi {{contact.first_name}},');
    const emailSections = bodyStart >= 0
      ? [...labelledSections(copy.email.slice(0, bodyStart)), { label: 'Email body', text: copy.email.slice(bodyStart).trim() }]
      : [{ label: 'Email body', text: copy.email }];
    return [
      { order: 1, id: 'email', kind: 'email', title: pack.email.subjectLines[0], meta: 'Email', sourceText: copy.email, sections: emailSections },
      { order: 2, id: 'carousel', kind: 'carousel', title: pack.carousel.title, meta: `Carousel · ${pack.carousel.slides.length} slides`, sourceText: copy.carousel, sections: suppliedCarouselSections(copy.carousel) },
      ...pack.reels.map((reel, index): DraftContentPiece => ({ order: index + 3, id: reel.id, kind: 'reel', title: reel.angleTitle,
        meta: `Reel ${index + 1} · ${reel.visualCue}`, sourceText: copy.reels[index], sections: labelledSections(copy.reels[index]) })),
    ];
  }
  const reels = [0, 1, 2]
    .map((index) => reelPiece(pack, index))
    .filter((piece): piece is DraftContentPiece => piece !== null);
  return [emailPiece(pack), carouselPiece(pack), ...reels];
}

export function draftPackIsComplete(pieces: DraftContentPiece[]): boolean {
  return pieces.length === DRAFT_CONTRACT_SIZE;
}

export function draftPieceToText(piece: DraftContentPiece): string {
  const body = piece.sourceText ?? piece.sections.map((section) => `${section.label}\n${section.heading ? section.heading + '\n' : ''}${section.text}`).join('\n\n');
  return `${piece.order}. ${piece.meta}: ${piece.title}\n\n${body}`;
}

export function draftPackToText(title: string, pieces: DraftContentPiece[]): string {
  return [`CONTENT SUITE: ${title}`, '', ...pieces.map(draftPieceToText)].join('\n\n');
}
