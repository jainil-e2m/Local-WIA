/* ────────────────────────────────────────────────────────────────
   Per-automation enable flags.

   Each tool can be switched between "live" (card opens its page, Run
   Audit is clickable) and "development" (locked, Coming soon) from the
   environment, without a code change:

     VITE_TOOL_OPS_HUB_ENABLED=true
     VITE_TOOL_TECHNICAL_SEO_ENABLED=true
     VITE_TOOL_INTERNAL_MEETING_ENABLED=true
     VITE_TOOL_ROLL_CALL_ENABLED=true
     VITE_TOOL_MONTHLY_REPORT_PACK_ENABLED=false
     VITE_TOOL_AI_SEO_ENABLED=true
     VITE_TOOL_AI_PRESENCE_CHECKER_ENABLED=true
     VITE_TOOL_ON_PAGE_SEO_ENABLED=false
     VITE_TOOL_LEAD_MAGNET_ENABLED=false

   Two things worth knowing:

   1. These are VITE_ vars, so they are baked into the client bundle at
      BUILD time — changing one on Railway requires a redeploy, not just a
      restart (unlike the server-side audit BFF variables, which are read at
      runtime). It is also the reason the lookup below is a literal map rather
      than a computed key: Vite statically replaces `import.meta.env.VITE_X`
      only when X is written out literally. `import.meta.env[someVar]`
      silently yields undefined in a production build.

   2. An unset (or empty, or unrecognised) flag falls back to the `status`
      committed in tools.ts. Omission therefore never changes behaviour —
      a deploy that sets none of these keeps working exactly as before, and
      the env var is a deliberate override rather than a required input.
   ──────────────────────────────────────────────────────────────── */

/** Raw env value per tool id. Literal accesses — see note 1 above. */
export const TOOL_FLAG_ENV: Record<string, string | undefined> = {
  "ops-hub": import.meta.env.VITE_TOOL_OPS_HUB_ENABLED,
  "technical-seo": import.meta.env.VITE_TOOL_TECHNICAL_SEO_ENABLED,
  "internal-meeting": import.meta.env.VITE_TOOL_INTERNAL_MEETING_ENABLED,
  "roll-call": import.meta.env.VITE_TOOL_ROLL_CALL_ENABLED,
  "monthly-report-pack": import.meta.env.VITE_TOOL_MONTHLY_REPORT_PACK_ENABLED,
  "ai-seo": import.meta.env.VITE_TOOL_AI_SEO_ENABLED,
  "ai-presence-checker": import.meta.env.VITE_TOOL_AI_PRESENCE_CHECKER_ENABLED,
  "on-page-seo": import.meta.env.VITE_TOOL_ON_PAGE_SEO_ENABLED,
  "lead-magnet": import.meta.env.VITE_TOOL_LEAD_MAGNET_ENABLED,
};

/** The env var name for a tool id, e.g. "lead-magnet" → VITE_TOOL_LEAD_MAGNET_ENABLED. */
export const toolFlagName = (id: string) =>
  `VITE_TOOL_${id.replace(/-/g, "_").toUpperCase()}_ENABLED`;

const TRUE_VALUES = new Set(["true", "1", "yes", "on", "enabled", "live"]);
const FALSE_VALUES = new Set([
  "false",
  "0",
  "no",
  "off",
  "disabled",
  "locked",
  "coming-soon",
  "coming_soon",
]);

/**
 * Read one flag value.
 *
 * Returns `undefined` for unset, empty (docker/Railway passthrough sends "")
 * and unrecognised input, so the caller falls back rather than guessing —
 * a typo like `VITE_TOOL_LEAD_MAGNET_ENABLED=ture` must not silently lock a
 * live tool.
 */
export function parseToolFlag(raw: string | undefined): boolean | undefined {
  if (typeof raw !== "string") return undefined;
  const value = raw.trim().toLowerCase();
  if (value === "") return undefined;
  if (TRUE_VALUES.has(value)) return true;
  if (FALSE_VALUES.has(value)) return false;
  if (import.meta.env.DEV) {
    console.warn(
      `[tools] Unrecognised enable-flag value ${JSON.stringify(raw)} — ` +
        `expected one of ${[...TRUE_VALUES].join(", ")} / ${[...FALSE_VALUES].join(", ")}. ` +
        "Falling back to the status committed in data/tools.ts.",
    );
  }
  return undefined;
}

/** Resolve a tool's effective status: env flag when set, committed status otherwise. */
export function resolveToolStatus<T extends "live" | "development">(
  id: string,
  committed: T,
): "live" | "development" {
  const flag = parseToolFlag(TOOL_FLAG_ENV[id]);
  if (flag === undefined) return committed;
  return flag ? "live" : "development";
}
