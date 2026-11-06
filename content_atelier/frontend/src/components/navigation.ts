import type { FeatureFlags } from '../utils/workspace';
import { paths, type NavView } from '../app/routes';

export type { NavView };
export type NavIcon = 'home' | 'studio' | 'previous' | 'packs' | 'sources' | 'moments' | 'knowledge' | 'settings';
/** `main` is the navigation the WIA team works in (the 20 October mockup's four items); `admin` is the quiet Administration group. */
export type NavGroup = 'main' | 'admin';
export interface NavItem { id: NavView; label: string; icon: NavIcon; count: string | null; path: string; group: NavGroup }

export interface NavAccess {
  /** A team account (not a client's). */
  isTeam: boolean;
  /** May read the settings: an editor or an approver (6.F7). */
  canReadSettings?: boolean;
  /** Shown the Administration group: an approver, an administrator, or a team member whose tools live there (intake, knowledge). */
  administration?: boolean;
}

/** The sidebar's destinations. Only real, in-scope screens are listed (S.F2, R31). The main group is the mockup's: Home, the
    Weekly Studio, Previous Concepts and Content Packs. Sources, Moments, Knowledge and Settings stay reachable (by the sidebar
    for the people who use them, and by their paths for everyone the server lets in), in the Administration group below. */
export function navigationItems(flags: FeatureFlags, pendingGatesCount: number, access: NavAccess): NavItem[] {
  const { isTeam, canReadSettings = false, administration = false } = access;
  const admin = isTeam && administration;
  return [
    { id: 'home', label: 'Home', icon: 'home', count: null, path: paths.home, group: 'main' },
    { id: 'editorial', label: 'Weekly Studio', icon: 'studio', count: pendingGatesCount > 0 ? String(pendingGatesCount) : null, path: paths.studio, group: 'main' },
    // Earlier weeks' concepts, read from the stored weeks (the week picker behind the archived-weeks toggle).
    { id: 'previous', label: 'Previous Concepts', icon: 'previous', count: null, path: paths.previous, group: 'main' },
    // Packs appear only when switched on.
    ...(flags.packs ? [{ id: 'packs' as const, label: 'Content Packs', icon: 'packs' as const, count: null, path: paths.packs, group: 'main' as const }] : []),
    ...(admin ? [{ id: 'sources' as const, label: 'Sources', icon: 'sources' as const, count: null, path: paths.sources, group: 'admin' as const }] : []),
    // The moments ledger (Phase 2): what was said, where, by whom and whether it may be used. A team view, like Sources.
    ...(admin ? [{ id: 'moments' as const, label: 'Moments', icon: 'moments' as const, count: null, path: paths.moments, group: 'admin' as const }] : []),
    // What the system knows, its review queue and its versions (Phase L), behind the context flag.
    ...(admin && flags.context ? [{ id: 'knowledge' as const, label: 'Knowledge', icon: 'knowledge' as const, count: null, path: paths.knowledge, group: 'admin' as const }] : []),
    // What the system runs with (6.F7), for the team members who may read settings: an editor or an approver.
    ...(admin && canReadSettings ? [{ id: 'settings' as const, label: 'Settings', icon: 'settings' as const, count: null, path: paths.settings, group: 'admin' as const }] : []),
  ];
}
