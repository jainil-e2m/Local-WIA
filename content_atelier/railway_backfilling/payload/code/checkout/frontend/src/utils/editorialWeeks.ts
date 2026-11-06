import { ContentIdea } from '../types/atelier';

export const WEEKLY_CONCEPT_LIMIT = 4;
export function hasWeeklyCapacity(ideas: ContentIdea[], week: string): boolean {
  return new Set(ideas.filter(idea => stampEditorialItem(idea).editorialWeek === week).map(idea => idea.id)).size < WEEKLY_CONCEPT_LIMIT;
}

/** Monday–Sunday editorial weeks use the platform's India timezone. */
export function editorialWeekFor(date: string): string {
  const instant = new Date(date);
  if (!Number.isFinite(instant.getTime())) throw new Error('Invalid editorial date');
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Calcutta', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(instant);
  const get = (name: string) => parts.find(part => part.type === name)!.value;
  const day = new Date(`${get('year')}-${get('month')}-${get('day')}T00:00:00Z`);
  day.setUTCDate(day.getUTCDate() - (day.getUTCDay() + 6) % 7);
  return day.toISOString().slice(0, 10);
}

export function stampEditorialItem(idea: ContentIdea, now = new Date().toISOString()): ContentIdea {
  // Legacy mock labels are relative to their original snapshot, not each reload.
  const age = Number(idea.daysAgo.match(/^(\d+) days? ago$/)?.[1] || 0);
  const legacy = new Date('2026-10-05T06:30:00Z');
  legacy.setUTCDate(legacy.getUTCDate() - age);
  const idTime = idea.id.match(/^idea-(\d{13})$/)?.[1];
  const createdAt = idea.createdAt && Number.isFinite(Date.parse(idea.createdAt))
    ? idea.createdAt : idTime ? new Date(Number(idTime)).toISOString()
    : /^idea-[1-4]$/.test(idea.id) ? legacy.toISOString() : now;
  const week = idea.editorialWeek;
  const validWeek = week && /^\d{4}-\d{2}-\d{2}$/.test(week) && Number.isFinite(Date.parse(`${week}T00:00:00Z`)) && editorialWeekFor(`${week}T06:30:00Z`) === week;
  return { ...idea, createdAt, editorialWeek: validWeek ? week : editorialWeekFor(createdAt) };
}

export function editorialWeeks(ideas: ContentIdea[]): string[] {
  return [...new Set(ideas.map(idea => stampEditorialItem(idea).editorialWeek!))].sort().reverse();
}

export function weekLabel(week: string): string {
  const start = new Date(`${week}T06:30:00Z`);
  const end = new Date(start);
  end.setUTCDate(end.getUTCDate() + 6);
  const format = (date: Date) => date.toLocaleDateString('en-IN', { timeZone: 'Asia/Calcutta', day: 'numeric', month: 'short' });
  return `${format(start)} – ${format(end)}, ${end.getUTCFullYear()}`;
}

/** Archive labels belong to the month in which the Monday falls. */
export function archiveWeekHeading(week: string): string {
  const start = new Date(`${week}T06:30:00Z`);
  const month = start.toLocaleDateString('en-IN', { timeZone: 'Asia/Calcutta', month: 'short' });
  return `Month ${month} · Week ${Math.ceil(start.getUTCDate() / 7)}`;
}

export function archiveStageItems(ideas: ContentIdea[], stage: 'angles' | 'briefs' | 'packs'): ContentIdea[] {
  return ideas.filter(idea => stage === 'angles' ? idea.gate === 'gate1_angle' : stage === 'briefs' ? idea.gate === 'gate2_brief' : !!idea.pack);
}

/** Exclusive pipeline counts: approved means in Briefs, not already generated. */
export function editorialStageCounts(ideas: ContentIdea[]) {
  const unique = [...new Map(ideas.map(idea => [idea.id, idea])).values()];
  return {
    waiting: unique.filter(idea => idea.gate === 'gate1_angle').length,
    approved: unique.filter(idea => idea.gate === 'gate2_brief').length,
    generated: unique.filter(idea => idea.gate === 'gate3_pack' || idea.gate === 'approved_for_giselle').length,
  };
}
