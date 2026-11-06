import { ContentIdea } from '../types/atelier';

export function groupPacksByMonth(ideas: ContentIdea[]) {
  const groups = new Map<string, { key: string; label: string; ideas: ContentIdea[] }>();
  for (const idea of ideas.filter(idea => idea.pack)) {
    const raw = idea.briefApprovedAt ?? idea.createdAt ?? (idea.editorialWeek ? `${idea.editorialWeek}T06:30:00Z` : undefined);
    const date = raw ? new Date(raw) : undefined;
    const valid = date && Number.isFinite(date.getTime());
    const parts = valid ? new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Calcutta', year: 'numeric', month: '2-digit' }).formatToParts(date) : [];
    const key = valid ? `${parts.find(part => part.type === 'year')!.value}-${parts.find(part => part.type === 'month')!.value}` : 'undated';
    const label = valid ? date.toLocaleDateString('en-IN', { timeZone: 'Asia/Calcutta', month: 'long', year: 'numeric' }) : 'Undated packs';
    const group = groups.get(key) ?? { key, label, ideas: [] };
    group.ideas.push(idea);
    groups.set(key, group);
  }
  return [...groups.values()].sort((a, b) => a.key === 'undated' ? 1 : b.key === 'undated' ? -1 : b.key.localeCompare(a.key));
}
