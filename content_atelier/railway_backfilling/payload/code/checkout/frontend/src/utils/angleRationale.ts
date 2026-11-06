import { ContentIdea } from '../types/atelier';

/** Backfills older records without pretending a live model has been called. */
export function contentAngleRationale(idea: ContentIdea): NonNullable<ContentIdea['angleRationale']> {
  if (idea.angleRationale?.points.length) return idea.angleRationale;
  const excerpt = (value: string, limit: number) => {
    const words = value.trim().split(/\s+/);
    return words.length > limit ? `${words.slice(0, limit).join(' ')}…` : value.trim();
  };
  return {
    topic: idea.title,
    source: idea.isMock ? 'mock' : 'editorial',
    points: [
      { label: 'Angle & gist', text: `${excerpt(idea.brief.coreInsight, 16)} Turn this client problem into a practical, specific conversation.` },
      { label: 'Why it matters', text: `The audience tension is: ${excerpt(idea.brief.audiencePain, 12)}. Addressing it makes the topic relevant to prospects evaluating their next step.` },
      { label: 'Content direction', text: 'Develop an insight-led email, a step-by-step carousel, and three short reels covering the misconception, a better approach, and one useful action. Keep the message consistent across formats.' },
      { label: 'Commercial opportunity', text: `Connect the practical takeaway to ${idea.suggestedCta} through a relevant invitation. Better-informed inquiries and clearer fit could reduce wasted sales effort; revenue potential remains a hypothesis, not a guaranteed result.` },
      { label: 'Expected impact', text: 'Aim to build trust, prompt saves and replies, and encourage qualified consultations. Compare engagement and inquiry quality after publishing; validate examples and obtain consent before making client-result claims.' },
    ],
  };
}
