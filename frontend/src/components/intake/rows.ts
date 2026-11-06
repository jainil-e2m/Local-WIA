import { hostOf, profileUrlError, type ProfileOption } from "@/data/auditIntake";

/**
 * Row models for the intake repeaters, and the pure helpers the form uses to
 * decide what to submit. Kept out of the component files so those export only
 * components (and stay eligible for fast refresh).
 *
 * Both repeaters share one rule: a row left entirely blank is dropped rather than
 * treated as an error — adding a row and changing your mind must not block the
 * audit — while a row with real input in it has to be valid.
 */

/* ── Profile rows (social, real estate) ────────────────────────── */

export interface ProfileRow {
  /** Stable React key, not sent anywhere. */
  id: number;
  platform: string;
  url: string;
  /** Errors surface on blur, so a half-typed host does not flash red mid-keystroke. */
  touched: boolean;
}

/**
 * Reveal every message at once. Used when submit finds an invalid row that may be
 * scrolled away or may never have been blurred.
 */
export const markProfileRowsTouched = (rows: ProfileRow[]): ProfileRow[] =>
  rows.map((row) => ({ ...row, touched: true }));

export const filledProfileRows = (rows: ProfileRow[]): ProfileRow[] =>
  rows.filter((row) => row.url.trim());

/** Whether any row the form would submit points at the wrong platform. */
export const hasProfileErrors = (options: readonly ProfileOption[], rows: ProfileRow[]): boolean =>
  filledProfileRows(rows).some((row) => profileUrlError(options, row.platform, row.url));

/* ── Competitor rows ───────────────────────────────────────────── */

export interface CompetitorRow {
  id: number;
  brandName: string;
  domainUrl: string;
  touched: boolean;
}

export const markCompetitorRowsTouched = (rows: CompetitorRow[]): CompetitorRow[] =>
  rows.map((row) => ({ ...row, touched: true }));

/**
 * Rows worth sending. A row with only one side filled is a mistake rather than an
 * empty row, so it is kept here and caught by `competitorError`.
 */
export const filledCompetitorRows = (rows: CompetitorRow[]): CompetitorRow[] =>
  rows.filter((row) => row.brandName.trim() || row.domainUrl.trim());

/** Why this row cannot be submitted, or null when it can (blank rows included). */
export function competitorError(row: CompetitorRow): string | null {
  const brandName = row.brandName.trim();
  const domainUrl = row.domainUrl.trim();
  if (!brandName && !domainUrl) return null;
  if (!brandName) return "Add this competitor's brand name.";
  if (!domainUrl) return "Add this competitor's domain.";
  // The API prefixes a missing scheme itself, so only an unparseable host is a
  // real problem here.
  if (!hostOf(domainUrl)) return "Enter a valid domain.";
  return null;
}

export const hasCompetitorErrors = (rows: CompetitorRow[]): boolean =>
  rows.some((row) => competitorError(row));
