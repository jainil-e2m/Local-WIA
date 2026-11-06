import { ContentIdea } from '../types/atelier';
import { selectDraftContents } from '../stages/ideaStages';

export function approvePackForScheduling(idea: ContentIdea, now = new Date().toISOString()): ContentIdea {
  if (!idea.pack || !['gate3_pack', 'approved_for_giselle'].includes(idea.gate)) return idea;
  return { ...idea, publishingApprovedAt: idea.publishingApprovedAt ?? now };
}

export function schedulePack(idea: ContentIdea, date: string, time: string, now = Date.now()): ContentIdea {
  if (!idea.pack || !idea.publishingApprovedAt) throw new Error('Approve the content pack for publishing first.');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^\d{2}:\d{2}$/.test(time)) throw new Error('Choose a valid date and time.');
  const instant = new Date(`${date}T${time}:00+05:30`);
  if (!Number.isFinite(instant.getTime()) || scheduleFields(instant.toISOString()).date !== date || scheduleFields(instant.toISOString()).time !== time) throw new Error('Choose a valid date and time.');
  if (instant.getTime() <= now) throw new Error('Choose a publishing time in the future.');
  return { ...idea, scheduledAt: instant.toISOString(), contentSchedules: undefined };
}

/** Individual dates are authoritative; older full-pack dates apply to all pieces. */
export function contentScheduleFor(idea: ContentIdea, order: number): string | undefined {
  return idea.contentSchedules === undefined ? idea.scheduledAt : idea.contentSchedules[order];
}

export function contentScheduleProgress(idea: ContentIdea) {
  const pieces = selectDraftContents(idea.pack);
  const scheduled = pieces.filter(piece => contentScheduleFor(idea, piece.order)).length;
  return { total: pieces.length, scheduled, waiting: pieces.length - scheduled };
}

export function scheduleContentPiece(idea: ContentIdea, order: number, date: string, time: string, now = Date.now()): ContentIdea {
  const pieces = selectDraftContents(idea.pack);
  if (!pieces.some(piece => piece.order === order)) throw new Error('Choose a content piece from this pack.');
  const validated = schedulePack(idea, date, time, now);
  const dates = idea.contentSchedules ?? Object.fromEntries(pieces.flatMap(piece => idea.scheduledAt ? [[piece.order, idea.scheduledAt]] : []));
  return { ...idea, scheduledAt: undefined, contentSchedules: { ...dates, [order]: validated.scheduledAt } };
}

export function scheduleFields(iso: string) {
  const shifted = new Date(Date.parse(iso) + 330 * 60_000).toISOString();
  return { date: shifted.slice(0, 10), time: shifted.slice(11, 16) };
}

export function scheduleLabel(iso: string) {
  return `${new Date(iso).toLocaleString('en-IN', { timeZone: 'Asia/Calcutta', dateStyle: 'medium', timeStyle: 'short' })} IST`;
}
