import { apiGet } from '../api/routes';
import { useApiQuery } from '../api/query';
import type { Capabilities, Me } from '../api/schema';

/** Who the signed-in person is to the system (0.B9, 0.F1): the answer of GET /me, resolved on the server from the
    verified email. The server checks every action again; this only decides what to offer. The types are the generated
    ones (backend/openapi.json); `useMe` reads the cache every screen shares, so identity is fetched once. */
export type Role = NonNullable<Me['role']>;
export type { Capabilities, Me };
export const ROLES: readonly Role[] = ['viewer', 'editor', 'approver', 'admin'];

const CAPABILITIES: (keyof Capabilities)[] = ['edit_cards', 'edit_briefs', 'decide', 'approve_briefs', 'review_knowledge', 'identity_review',
  'manage_users', 'manage_intake', 'generate_packs', 'approve_packs', 'schedule_calendar'];

/** Nothing is offered until the answer arrives, or if it fails. */
export const ME_NONE: Me = {
  email: null, name: null, role: null, roles: [], source: 'none', identity_approver: false,
  can: Object.fromEntries(CAPABILITIES.map(name => [name, false])) as unknown as Capabilities,
};

const isRole = (value: unknown): value is Role => typeof value === 'string' && (ROLES as readonly string[]).includes(value);

/** Read the answer defensively: a capability is true only when the server says exactly true. */
export function readMe(value: unknown): Me {
  const v = (value && typeof value === 'object' ? value : {}) as Record<string, unknown>;
  const can = (v.can && typeof v.can === 'object' ? v.can : {}) as Record<string, unknown>;
  return {
    email: typeof v.email === 'string' ? v.email : null,
    name: typeof v.name === 'string' ? v.name : null,
    role: isRole(v.role) ? v.role : null,
    roles: Array.isArray(v.roles) ? v.roles.filter(isRole) : [],
    source: v.source === 'users' || v.source === 'lists' ? v.source : 'none',
    identity_approver: v.identity_approver === true,
    can: Object.fromEntries(CAPABILITIES.map(name => [name, can[name] === true])) as unknown as Capabilities,
  };
}

export async function getMe(): Promise<Me> {
  return readMe(await apiGet('/me'));
}

/** The signed-in person's roles and capabilities, from the shared cache. `loaded` is true once the server has answered
    (or failed to), so a screen can tell "not allowed" from "not known yet". */
export function useMe(): { me: Me; loaded: boolean } {
  const query = useApiQuery('/me', undefined, { staleTime: 60_000 });
  return { me: query.data ? readMe(query.data) : ME_NONE, loaded: !query.isPending };
}

/** Who is shown the technical details (costs by stage and model, the knowledge-base version and strategist profile a cycle ran
    on, an alert's own message and counts): an approver or an administrator, inside a collapsed section (the owner, 25 October
    2026). Everyone else reads the same screens in plain words. */
export const seesDetails = (me: { can: Pick<Me['can'], 'decide'>; roles: readonly string[] }) => me.can.decide || me.roles.includes('admin');
