import { ContentIdea } from '../types/atelier';

export function briefingOverview(idea: ContentIdea) {
  const saved = idea.brief.contentPlan;
  const focus = idea.brief.formatSplit;
  const direction = idea.brief.productionBrief;
  const overview = [
    { label: 'Email', purpose: 'Build understanding & start a conversation', gist: saved?.email ?? `${focus.emailFocus} Develop the insight into a personal, context-rich message with one relevant invitation to ${idea.suggestedCta}.` },
    { label: 'Carousel', purpose: 'Explain the process visually', gist: saved?.carousel ?? `${focus.carouselFocus} Move from the problem through a clear decision framework to a practical takeaway; each slide should advance the argument.` },
    { label: 'Reel 1', purpose: 'Challenge the misconception', gist: saved?.reels[0] ?? `Use “${idea.title}” to expose the mistaken assumption behind this problem: ${idea.brief.audiencePain} Focus on recognition and the cost of leaving it unaddressed, not a full tutorial.` },
    { label: 'Reel 2', purpose: 'Demonstrate the better approach', gist: saved?.reels[1] ?? `Show the alternative in action: ${idea.brief.coreInsight} Use a concrete scenario or before-and-after conversation to demonstrate the change. Unlike Reel 1, this is about the solution, not the misconception.` },
    { label: 'Reel 3', purpose: 'Give one actionable next step', gist: saved?.reels[2] ?? `Turn the perspective into one small action viewers can try before their next client conversation. Base it on: ${focus.reelsFocus} Unlike Reel 2, keep this a single takeaway, with a relevant invitation rather than repeating the demonstration.` },
  ];
  return overview.map((piece, index) => index < 2 || !direction ? piece : { ...piece, purpose: direction.reels[index - 2].role });
}

/** Only a dated review against a complete published archive can substantiate 'no similar content'. */
export function briefingSimilarity(idea: ContentIdea, now = new Date()) {
  const review = idea.brief.similarityReview;
  if (!review) return { status: 'Not verified', summary: 'The published-content archive for the last four months has not been checked. Generated packs, mock calendar entries, and scheduled content are not evidence of publication.', matches: [] };
  const end = new Date(review.periodEnd);
  const start = new Date(review.periodStart);
  const expectedStart = new Date(end);
  expectedStart.setUTCMonth(expectedStart.getUTCMonth() - 4);
  const valid = Number.isFinite(end.getTime()) && Number.isFinite(start.getTime()) && start <= expectedStart && Number.isFinite(Date.parse(review.checkedAt)) && now.getTime() - end.getTime() <= 86400000 && end.getTime() <= now.getTime() + 86400000;
  if (!valid) return { status: 'Not verified', summary: 'The saved review does not cover a current, valid four-month publishing window. Recheck the published archive before approval.', matches: [] };
  const matches = review.matches.filter(match => {
    const date = Date.parse(match.publishedAt);
    return Number.isFinite(date) && date >= expectedStart.getTime() && date <= end.getTime();
  });
  const window = `${start.toISOString().slice(0, 10)} to ${end.toISOString().slice(0, 10)}`;
  return {
    status: matches.length ? 'Similar past content found' : review.publishedHistoryComplete ? 'No similar content found' : 'Not verified',
    summary: `${review.publishedHistoryComplete ? 'Published archive reviewed' : 'Partial published archive reviewed'}: ${window}. ${matches.length ? 'Review the overlap and the planned changes below.' : review.publishedHistoryComplete ? 'No similar published content was identified in this four-month window.' : 'Incomplete history cannot establish that the content is new.'}`,
    matches,
  };
}
