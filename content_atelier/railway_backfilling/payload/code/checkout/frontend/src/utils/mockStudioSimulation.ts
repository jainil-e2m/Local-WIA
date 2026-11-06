import { ContentIdea, MockStudioStage } from '../types/atelier';
import { FATHOM_CONTENT_PACKS } from '../data/fathomContentPacks';
import { advanceEditorialItem } from './editorialWorkflow';
import { approvePackForScheduling, scheduleFields, schedulePack } from './publishingSchedule';

const sourceIds = new Set(Object.keys(FATHOM_CONTENT_PACKS));

/** Replay only the four sourced mocks. Keep their analysis, edits, IDs and week. */
export function simulateMockStudio(library: ContentIdea[], stage: MockStudioStage, changedAt = new Date().toISOString()): ContentIdea[] {
  const now = Date.parse(changedAt);
  if (!Number.isFinite(now)) throw new Error('Choose a valid simulation time.');
  let slot = 0;
  return library.map(idea => {
    if (!idea.isMock || !sourceIds.has(idea.id) || !idea.mockContentPack) return idea;
    const date = new Date(`${scheduleFields(changedAt).date}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() + 1 + slot++);
    const start: ContentIdea = {
      ...idea, gate: 'gate1_angle', pack: undefined, angleApprovedAt: undefined, briefApprovedAt: undefined,
      publishingApprovedAt: undefined, scheduledAt: undefined, contentSchedules: undefined,
      mockSimulation: { version: 1, stage, changedAt },
    };
    if (stage === 'angles') return start;
    const withBrief = advanceEditorialItem(start, 'gate2_brief', changedAt);
    if (stage === 'briefs') return withBrief;
    const withPack = advanceEditorialItem(withBrief, 'gate3_pack', changedAt);
    if (stage === 'packs') return withPack;
    const ready = approvePackForScheduling(withPack, changedAt);
    if (stage === 'scheduling') return ready;
    return schedulePack(ready, date.toISOString().slice(0, 10), '10:00', now);
  });
}
