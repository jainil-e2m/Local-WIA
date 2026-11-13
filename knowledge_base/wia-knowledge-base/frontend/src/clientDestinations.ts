import type { ClientTab } from './types';

/** Client shortcuts share the main workspaces and their URL-backed client filters. */
export function clientSectionHash(id: string, tab: ClientTab = 'now'): string {
  if (tab === 'health') return `health-v2/${id}`;
  if (tab === 'money') return `money/${id}`;
  return `clients/${id}/${tab}`;
}
