import { ContentIdea } from '../types/atelier';
import { FATHOM_WEEKLY_ANGLES } from '../data/fathomWeeklyAngles';

const mockIds = new Set(FATHOM_WEEKLY_ANGLES.map(idea => idea.id));

/** Restart the four demo workflows once per deployment, retaining source edits. */
export function resetStudioForDeployment(ideas: ContentIdea[], deploymentId: string): ContentIdea[] {
  if (!deploymentId) throw new Error('A studio deployment ID is required.');
  return ideas.map(idea => {
    if (!mockIds.has(idea.id) || idea.mockDeploymentId === deploymentId) return idea;
    return { ...idea, mockDeploymentId: deploymentId, gate: 'gate1_angle',
      mockContentPack: idea.pack ?? idea.mockContentPack, pack: undefined,
      angleApprovedAt: undefined, briefApprovedAt: undefined,
      publishingApprovedAt: undefined, scheduledAt: undefined, contentSchedules: undefined, mockSimulation: undefined };
  });
}
