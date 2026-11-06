import type { AuditType } from "@/services/api/audits";

/**
 * Intake data shared by the audit runner's form: which fields each audit product
 * collects, and the closed sets its repeaters offer.
 *
 * These lists are API contracts rather than display copy — every `id` here is a
 * value some backend matches on. Changing one silently changes what gets audited.
 */

/* ── Which fields each product collects ────────────────────────── */

export interface IntakeProfile {
  /** Country, state, city and business type. */
  identity: boolean;
  /** City is refused when blank rather than merely offered. */
  cityRequired: boolean;
  /**
   * The social profile repeater. AI SEO grounds its discoverability checks on
   * these; an AI Presence run does not use them, so it does not ask.
   */
  socialProfiles: boolean;
  /** Assistant selection, target keyword, competitors, real-estate profiles. */
  presence: boolean;
}

/**
 * Technical SEO takes only `seed_urls` + `business_name`, so the identity fields
 * are withheld from it rather than shown and discarded. On-Page SEO is minimal
 * for the same reason, not because it is unfinished: its API accepts a site URL
 * and a client name and has nowhere to put the rest.
 */
export const INTAKE_PROFILES: Record<AuditType, IntakeProfile> = {
  technical: { identity: false, cityRequired: false, socialProfiles: false, presence: false },
  ai: { identity: true, cityRequired: false, socialProfiles: true, presence: false },
  "ai-presence": { identity: true, cityRequired: true, socialProfiles: false, presence: true },
  "on-page": { identity: false, cityRequired: false, socialProfiles: false, presence: false },
};

/* ── Profile repeater options ──────────────────────────────────── */

export interface ProfileOption {
  /** Value sent to the API. A backend contract, not a display string. */
  id: string;
  label: string;
  /**
   * Matched against the parsed hostname rather than the raw string, so a path or
   * query containing another platform's name cannot satisfy it —
   * `instagram.com/x.com` is still Instagram. The `(^|\.)` prefix accepts
   * subdomains (`www.`, `m.`, `uk.`) while rejecting suffix tricks such as
   * `instagram.com.attacker.net`.
   */
  hostPattern: RegExp;
  example: string;
}

/**
 * Social platforms the intake offers.
 *
 * The list is pinned by AI SEO, whose grounding checks match on these exact
 * lowercase keys — they are the keys of `_dataset_id()` in
 * `services/discoverability/section4_social_orchestration.py`, each with a
 * configured scraper dataset. Do NOT add a platform here without adding it there
 * first: an unrecognised key resolves to no dataset and the profile comes back as
 * the error "Bright Data dataset id is not configured for <platform>", which
 * counts against the run and can turn a clean audit into `completed_partial`.
 * TikTok and Reddit were removed for that reason — TikTok appears in the backend
 * only inside page-scanning host lists, and Reddit is handled by mention
 * *discovery* from search (section7), not by a profile URL anyone submits.
 *
 * AI Presence has no such dataset requirement (it stores the profiles on the run's
 * ranking config), so it can safely reuse the same list.
 */
export const SOCIAL_PLATFORMS: readonly ProfileOption[] = [
  {
    id: "youtube",
    label: "YouTube",
    hostPattern: /(^|\.)(youtube\.com|youtu\.be)$/,
    example: "youtube.com/@yourchannel",
  },
  {
    id: "linkedin",
    label: "LinkedIn",
    hostPattern: /(^|\.)linkedin\.com$/,
    example: "linkedin.com/company/yourbrand",
  },
  {
    id: "instagram",
    label: "Instagram",
    hostPattern: /(^|\.)instagram\.com$/,
    example: "instagram.com/yourbrand",
  },
  {
    id: "facebook",
    label: "Facebook",
    hostPattern: /(^|\.)(facebook\.com|fb\.com|fb\.me)$/,
    example: "facebook.com/yourbrand",
  },
  {
    id: "twitter",
    label: "X (Twitter)",
    hostPattern: /(^|\.)(x\.com|twitter\.com)$/,
    example: "x.com/yourbrand",
  },
  {
    // Pinterest runs many ccTLDs (pinterest.co.uk, pinterest.ca), plus pin.it
    // for shared links.
    id: "pinterest",
    label: "Pinterest",
    hostPattern: /(^|\.)(pinterest\.[a-z]{2,3}(\.[a-z]{2,3})?|pin\.it)$/,
    example: "pinterest.com/yourbrand",
  },
];

export interface RealEstateProfileOption extends ProfileOption {
  /**
   * Real-estate profiles are not a list on the AI Presence intake — each one is
   * its own top-level key, so a row's platform decides which field it fills.
   */
  payloadKey: "zillowProfileUrl" | "realtorProfileUrl" | "homeLightProfileUrl";
}

export const REAL_ESTATE_PLATFORMS: readonly RealEstateProfileOption[] = [
  {
    id: "zillow",
    label: "Zillow",
    payloadKey: "zillowProfileUrl",
    hostPattern: /(^|\.)zillow\.com$/,
    example: "zillow.com/profile/yourbrand",
  },
  {
    id: "realtor",
    label: "Realtor.com",
    payloadKey: "realtorProfileUrl",
    hostPattern: /(^|\.)realtor\.com$/,
    example: "realtor.com/realestateagents/yourbrand",
  },
  {
    id: "homelight",
    label: "HomeLight",
    payloadKey: "homeLightProfileUrl",
    hostPattern: /(^|\.)homelight\.com$/,
    example: "homelight.com/agents/yourbrand",
  },
];

/**
 * Business types for which the real-estate profile fields are worth asking about.
 * Matched as substrings of the typed business type, which is free text — a
 * "Residential Real Estate Broker" has to trigger this as surely as "Realtor".
 */
export const REAL_ESTATE_BUSINESS_TERMS = [
  "real estate",
  "realtor",
  "broker",
  "home buyer",
  "cash home",
  "property investor",
] as const;

export function looksLikeRealEstate(businessType: string): boolean {
  const normalized = businessType.trim().toLowerCase();
  if (!normalized) return false;
  return REAL_ESTATE_BUSINESS_TERMS.some((term) => normalized.includes(term));
}

/* ── AI assistants evaluated by the Presence Checker ───────────── */

export interface AiAssistant {
  /**
   * Value sent in `llm_eval_targets`. Deliberately the backend's own provider key
   * (see `services/llm_model_calls/providers.py`) rather than a separate UI id —
   * a second identifier per assistant is one more place for `gemini` and
   * `google_gemini` to drift apart.
   */
  id: string;
  label: string;
  /**
   * Brand mark under `public/logos/`, named for the id. These are the
   * light-on-dark variants — ChatGPT, Perplexity and Grok are white marks that
   * would vanish on a pale surface, and the intake only ever sits on the navy
   * hero. A light-theme surface would need the dark variants alongside them.
   */
  logo: string;
}

/**
 * The backend also exposes a `google_ai_overviews` target, deliberately left out
 * here: it is scraped through SerpAPI rather than served as a model, and stays
 * disabled unless the audit service sets LLM_EVAL_GOOGLE_AI_OVERVIEWS_ENABLED
 * and a SerpAPI key. Because the form always sends a non-empty
 * `llm_eval_targets`, omitting it from this list is what keeps it out of a run —
 * an empty list would mean "every target" to the backend and pull it back in.
 */
export const AI_ASSISTANTS: readonly AiAssistant[] = [
  { id: "chatgpt", label: "ChatGPT", logo: "/logos/chatgpt.png" },
  { id: "claude", label: "Claude", logo: "/logos/claude.png" },
  { id: "perplexity", label: "Perplexity", logo: "/logos/perplexity.png" },
  { id: "grok", label: "Grok", logo: "/logos/grok.png" },
  { id: "google_gemini", label: "Gemini", logo: "/logos/google_gemini.png" },
];

/**
 * Everything on by default. An empty `llm_eval_targets` means "all targets" to the
 * backend, so an all-selected default matches what an untouched form would do
 * anyway — but sending the list explicitly keeps the request self-describing.
 */
export const DEFAULT_AI_ASSISTANTS: string[] = AI_ASSISTANTS.map((assistant) => assistant.id);

/* ── URL validation shared by the repeaters ────────────────────── */

/**
 * Hostname of a pasted profile URL, tolerating a missing scheme — people paste
 * `instagram.com/brand` far more often than the absolute form.
 */
export function hostOf(rawUrl: string): string | null {
  const trimmed = rawUrl.trim();
  if (!trimmed) return null;
  const absolute = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
  try {
    return new URL(absolute).hostname.toLowerCase();
  } catch {
    return null;
  }
}

/**
 * Why this URL does not belong to the selected platform, or null when it does.
 *
 * A blank URL is not an error — an empty row is dropped on submit rather than
 * blocking it. This exists to catch the specific mistake of pasting one
 * platform's URL under another's label, which would otherwise reach the backend
 * as a confidently mislabelled profile.
 */
export function profileUrlError(
  options: readonly ProfileOption[],
  platformId: string,
  rawUrl: string,
): string | null {
  if (!rawUrl.trim()) return null;
  const platform = options.find((option) => option.id === platformId);
  if (!platform) return "Choose a platform for this profile.";
  const host = hostOf(rawUrl);
  if (!host) return "Enter a valid URL.";
  if (!platform.hostPattern.test(host)) {
    return `That is not a ${platform.label} URL — expected something like ${platform.example}.`;
  }
  return null;
}
