import { CLIENTS } from './data';
import { RECORDS } from './records';

// Account teams for the per-client visibility preview (Action Hub v2).
// Taken from each client's team (ClickUp assignees / Role field in production).

export interface TeamMember { name: string; role: string; source: 'ClickUp' }
export type AccountTeams = Record<string, TeamMember[]>;

export const seedTeams = (): AccountTeams => Object.fromEntries(CLIENTS.map(c => [c.id, RECORDS[c.id].team.map(t => ({ ...t, source: 'ClickUp' as const }))]));

/** Programme upkeep is visible to the programme's coach plus ops; participants are handled as clients. */
export const PROGRAMME_TEAMS: Record<string, string[]> = {
  'Meta Ads Accelerator': ['Jacqueline', 'Gisselle', 'Whitney'],
  'Google Search Accelerator': ['Carmen', 'Gisselle', 'Whitney'],
};
