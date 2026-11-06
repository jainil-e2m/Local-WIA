import type { Engagement, Lifecycle } from './records';
import type { ClientDetailsOverride, UploadedLogo } from './clientDetails';

/*
 * Decides which edited client fields to store. Pure and import-free at runtime, so
 * scripts/verify-client-details.mjs can check it directly with Node.
 */

/** The KB writes this for fields extraction hasn't filled. Editors treat it as empty, never as a value. */
export const NOT_EXTRACTED = 'Not extracted yet';
export const blank = (value: string) => (value === NOT_EXTRACTED ? '' : value);

export type LogoState = { kind: 'extracted' } | { kind: 'uploaded'; uploaded: UploadedLogo } | { kind: 'none' };
interface Shared { name: string; aliases: string[]; category: string; location: string; owner: string; lifecycle: Lifecycle; engagements: Engagement[] }
export interface DetailsBase extends Shared { hasLogo: boolean; tint: string }
export interface DetailsDraft extends Shared { logo: LogoState; logoScale: number; logoTint: string }

/** Only fields that differ from the KB record are kept, so a field nobody touched keeps following the source. */
export function overrideFrom(base: DetailsBase, draft: DetailsDraft): ClientDetailsOverride {
  const o: ClientDetailsOverride = {};
  const name = draft.name.trim();
  const aliases = [...new Set(draft.aliases.map(a => a.trim()).filter(a => a && a.toLowerCase() !== name.toLowerCase()))];
  const engagements = draft.engagements.filter(e => e.type.trim());
  if (name !== base.name) o.name = name;
  if (JSON.stringify(aliases) !== JSON.stringify(base.aliases)) o.aliases = aliases;
  if (draft.category.trim() !== blank(base.category)) o.category = draft.category.trim();
  if (draft.location.trim() !== blank(base.location)) o.location = draft.location.trim();
  if (draft.owner !== base.owner) o.owner = draft.owner;
  if (draft.lifecycle !== base.lifecycle) o.lifecycle = draft.lifecycle;
  if (JSON.stringify(engagements) !== JSON.stringify(base.engagements)) o.engagements = engagements;
  if (draft.logo.kind === 'uploaded') o.logo = draft.logo.uploaded;
  if (draft.logo.kind === 'none' && base.hasLogo) o.logoRemoved = true;
  if (draft.logo.kind !== 'none' && draft.logoScale !== 1) o.logoScale = draft.logoScale;
  if (draft.logo.kind !== 'none' && draft.logoTint !== base.tint) o.logoTint = draft.logoTint;
  return o;
}
