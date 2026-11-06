/* Every URL of the app, in one place (plan 1.F1). A view and each entity inside it has a path that survives a refresh;
   the Node server serves index.html for any path without a file extension and checks the session first. */

const enc = encodeURIComponent;

export const ID = '[A-Za-z0-9_-]{1,140}';

export const paths = {
  root: '/',
  home: '/home',
  calendar: '/calendar',
  studio: '/studio',
  angles: '/studio/angles',
  week: (weekId: string) => `/studio/angles/${enc(weekId)}`,
  angle: (weekId: string, angleId: string) => `/studio/angles/${enc(weekId)}/${enc(angleId)}`,
  briefs: '/studio/briefs',
  brief: (briefId: string) => `/studio/briefs/${enc(briefId)}`,
  studioPacks: '/studio/packs',
  studioPack: (packId: string) => `/studio/packs/${enc(packId)}`,
  scheduled: '/studio/scheduled',
  previous: '/previous',
  packs: '/packs',
  pack: (packId: string) => `/packs/${enc(packId)}`,
  sources: '/sources',
  documents: '/sources/documents',
  document: (transcriptId: string) => `/sources/documents/${enc(transcriptId)}`,
  intake: '/sources/intake',
  intakeSource: (sourceId: string) => `/sources/intake/sources/${enc(sourceId)}`,
  intakeBucket: (bucketId: string) => `/sources/intake/buckets/${enc(bucketId)}`,
  cycle: '/sources/cycle',
  alerts: '/sources/alerts',
  moments: '/moments',
  moment: (momentId: string) => `/moments/${enc(momentId)}`,
  knowledge: '/knowledge',
  review: '/knowledge/review',
  known: '/knowledge/known',
  knownItem: (itemId: string) => `/knowledge/known/items/${enc(itemId)}`,
  versions: '/knowledge/versions',
  settings: '/settings',
  version: (version: string) => `/knowledge/versions/${enc(version)}`,
} as const;

export type NavView = 'home' | 'editorial' | 'previous' | 'packs' | 'sources' | 'moments' | 'knowledge' | 'settings';

/** The sidebar destination a path belongs to. */
export function navViewOf(pathname: string): NavView | null {
  if (pathname === '/' || pathname === paths.home || pathname === paths.calendar) return 'home';
  if (pathname.startsWith(paths.studio)) return 'editorial';
  if (pathname === paths.previous || pathname.startsWith(`${paths.previous}/`)) return 'previous';
  if (pathname.startsWith(paths.packs)) return 'packs';
  if (pathname.startsWith(paths.sources)) return 'sources';
  if (pathname === paths.moments || pathname.startsWith(`${paths.moments}/`)) return 'moments';
  if (pathname.startsWith(paths.knowledge)) return 'knowledge';
  if (pathname === paths.settings) return 'settings';
  return null;
}

export type StudioLink = { tab: 'angles'; week: string; angle: string } | { tab: 'briefs'; brief: string };

/** Reads a card or brief link: a path (/studio/angles/<week>/<angle>, /studio/briefs/<brief>) or the earlier
    hash form (#studio/...) that bookmarks and messages may still carry. */
export function parseStudioLink(value: string): StudioLink | null {
  const rest = value.startsWith('#studio/') ? value.slice('#studio'.length) : value.startsWith('/studio/') ? value.slice('/studio'.length) : null;
  if (rest === null) return null;
  const angle = new RegExp(`^/angles/(${ID})/(${ID})$`).exec(rest);
  if (angle) return { tab: 'angles', week: angle[1], angle: angle[2] };
  const brief = new RegExp(`^/briefs/(${ID})$`).exec(rest);
  return brief ? { tab: 'briefs', brief: brief[1] } : null;
}

/** Where a legacy #studio/... hash points now, or null for any other hash. */
export function legacyHashTarget(hash: string): string | null {
  const link = parseStudioLink(hash);
  if (!link) return null;
  return link.tab === 'angles' ? paths.angle(link.week, link.angle) : paths.brief(link.brief);
}
