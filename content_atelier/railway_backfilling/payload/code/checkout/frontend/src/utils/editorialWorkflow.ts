import { ContentIdea, GateStatus } from '../types/atelier';
import { generateContentPackForIdea } from './packGenerator';
import { editorialWeeks, hasWeeklyCapacity } from './editorialWeeks';

export function reviveEditorialItem(idea: ContentIdea, library: ContentIdea[], revivedAt: string): ContentIdea {
  const week = editorialWeeks(library)[0];
  if (!week || !idea.editorialWeek || idea.editorialWeek >= week || !['gate1_angle', 'gate2_brief'].includes(idea.gate)) return idea;
  if (!hasWeeklyCapacity(library, week)) throw new Error('Weekly Studio already has four concepts. This concept stays in Previous Concepts until there is capacity in a new week.');
  return { ...idea, originalEditorialWeek: idea.originalEditorialWeek ?? idea.editorialWeek, editorialWeek: week, revivedAt };
}

export function advanceEditorialItem(idea: ContentIdea, newGate: GateStatus, approvedAt: string, note?: string): ContentIdea {
  if (newGate === 'gate2_brief' && idea.gate !== 'gate1_angle') return idea;
  if (newGate === 'gate3_pack' && idea.gate !== 'gate2_brief') return idea;
  if (newGate === 'approved_for_giselle' && !idea.pack) return idea;
  return {
    ...idea,
    gate: newGate,
    angleApprovedAt: newGate === 'gate2_brief' ? approvedAt : idea.angleApprovedAt,
    briefApprovedAt: newGate === 'gate3_pack' ? approvedAt : idea.briefApprovedAt,
    pack: newGate === 'gate3_pack' ? idea.pack ?? generateContentPackForIdea(idea) : idea.pack,
    brief: note ? { ...idea.brief, openQuestionsForWhitney: [`Steer Note: ${note}`, ...idea.brief.openQuestionsForWhitney] } : idea.brief,
  };
}
