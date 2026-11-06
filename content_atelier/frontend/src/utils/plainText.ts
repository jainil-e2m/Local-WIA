/* Text the server wrote for people (an alert, a reason a pack waits, a failed step, why a call was excluded) can carry what
   only the team that runs the system reads: a command to run, a plan item or decision code, an internal id. `plainMessage`
   takes those out, so a screen shows the sentence and nothing else. */

// A command in brackets or back-ticks: "(storage_cli budgets set)", "`storage_cli plan create ...`", "(python -m ...)".
const COMMAND = /\s*[(`][^()`]*\b(?:storage_cli|python -m|backend_pipeline|ATELIER_[A-Z_]+)\b[^()`]*[)`]/g;
// Plan items and decisions in brackets: "(D12)", "(N4, decided under delegation, D12)", "(2.B11)", "(delegated review under D21, N8, 25 October 2026)".
// The knowledge base's own references count too: "(F-megaemail-1, 2026-10, team)", "(R-7)", "(D-delivery-2, 2026-07-17)".
const CODES = /\s*\((?=[^()]*\b(?:[DNRSE]\d{1,2}[a-z]?|\d\.[A-Z]{1,2}\d{1,2}[a-z]?|NP\.[A-Z]?\d+|X\.\d|[A-Z]-[a-z]*-?\d+|[A-Z]-[a-z]+-\d+)\b)[^()]*\)/g;
// Internal ids that can follow a sentence: "angle_b8c6…", "brief_run_…".
const IDS = /\b(?:angle|brief|brief_run|pack|run|job|transcript|moment|momemb_job|momemb_run|alert)_[0-9a-f]{8,}\b/g;
const DELEGATION = /\s+under delegation\b/gi;

export function plainMessage(text: string | null | undefined): string {
  if (!text) return '';
  return text.replace(COMMAND, '').replace(CODES, '').replace(IDS, 'it').replace(DELEGATION, '')
    .replace(/\s+([.,;:])/g, '$1').replace(/\.{2,}/g, '.').replace(/\s{2,}/g, ' ').trim();
}
