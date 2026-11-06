import {
  CalendarCheck,
  ClipboardCheck,
  LayoutDashboard,
  ListChecks,
  Sparkles,
  FileSearch,
  LineChart,
  Magnet,
  Radar,
  type LucideIcon,
} from "lucide-react";
import type { AuditType } from "@/services/api/audits";
import type { UserRole } from "@/services/api/auth";
import { resolveToolStatus } from "./toolFlags";

export type ToolStatus = "live" | "development";

export interface Tool {
  id: string;
  name: string;
  description: string;
  tags: string[];
  status: ToolStatus;
  /** Roles allowed to see/use this tool. Permissive by default (all roles).
      To gate a tool to a role, narrow this AND enforce it server-side on the
      /api/technical-seo proxy — a hidden tile is not access control. */
  roles: UserRole[];
  /** External dashboard link for non-audit (link-out) tools. Audit tools use
      their integration through the audit API client instead. */
  url: string;
  /** In-app page this tool opens, when it is not the generic
      /automations/<id> stub. Takes precedence over `url`. */
  route?: string;
  /** Card CTA text (fan modal + ToolCard). Defaults to "Run Audit" — override
      for a tool that isn't an audit runner, e.g. Lead Magnet's "View Console". */
  ctaLabel?: string;
  icon: LucideIcon;
  /** Gradient tint used on the icon tile + hover glow. */
  from: string;
  to: string;
  /** Set for audit-style tools — selects its independently deployed service and
      renders the inline intake → progress runner on the tool page. */
  auditType?: AuditType;
  /** Keep the tool out of the automations library — the fan modal and the
      tools section — while leaving it fully reachable at its own URL.
      HistoryPage and ToolPage read the unfiltered `tools` list, so a hidden
      tool still resolves when someone types /automations/<id> and its audit
      history stays joined.

      NOT access control: the tile is gone, the route is not. Anything that
      genuinely must be denied needs the route guard plus a server-side check,
      same as `roles`. */
  hidden?: boolean;
}

/* ────────────────────────────────────────────────────────────────
   EDIT HERE to wire each automation.
   • Every audit tool runs through the same-origin authenticated BFF, so its
     upstream URL and bearer token stay server-side (see server/index.mjs).
   • Link-out tools (no auditType): set `url` to the external dashboard link.
   • In-app tools with their own page (not the /automations/<id> stub): set `route`.
   • `status` below is the DEFAULT. Each tool can be flipped live/locked from the
     environment without touching this file — see data/toolFlags.ts for the
     VITE_TOOL_<ID>_ENABLED contract. An unset flag keeps the value written here.
   Hero counters and every route derive from the resolved status.
   ──────────────────────────────────────────────────────────────── */
const TOOLS: Tool[] = [
  /* THE HUB COMES FIRST, and it is in this list as well as on the hero.
     It was reachable only from the hero's own button, which meant the
     automations library — the thing a client opens to see "what did you build
     for us" — listed three single-purpose consoles and no sign of the surface
     they report into. That is the wrong first impression of the work: the
     question it answers is Whitney's own ("how is it all connected?",
     26 Aug @19:21), and an index of the work should start with the answer. */
  {
    id: "ops-hub",
    name: "AI Operations Hub",
    description:
      "One command centre over Gmail, Slack, ClickUp, Zoom, Fathom, Drive and HighLevel — what needs a decision today, the context behind it, and the approval gate in front of anything that leaves the building.",
    tags: ["Six screens", "Every source", "Review gate"],
    status: "live",
    roles: ["team", "client"],
    url: "",
    route: "/ops-hub",
    ctaLabel: "Open Hub",
    icon: LayoutDashboard,
    /* Opens the shared ramp one step above Client Onboarding — it is the
       surface the others report into, so it reads as the brightest card. */
    from: "#3244c4",
    to: "#4f63ea",
  },
  {
    // id stays "technical-seo": it is the route segment
    // (/automations/technical-seo), the BFF mount path (/api/technical-seo),
    // the `auditType: "technical"` cross-reference, and the key HistoryPage
    // and data/timeline.ts join on. Only the display name changes.
    id: "technical-seo",
    name: "Client Onboarding",
    description:
      "Signature to checklist — watches for the signed contract and paid invoice, pairs them to one client, and holds the ClickUp list for review before anything is written.",
    tags: ["Signature trigger", "Review gate", "ClickUp"],
    status: "live",
    roles: ["team", "client"],
    url: "",
    /* Its own review console, not the generic audit stub — a queue of
       provisioning decisions rather than an audit runner. `route` wins over
       the /automations/<id> stub, so the card opens the console.

       `auditType` stays on purpose despite there being no audit to run here:
       HistoryPage and data/timeline.ts join on it, and dropping it would
       orphan every existing technical-audit record. Same reasoning as the
       id — rename the display, keep the keys. */
    auditType: "technical",
    route: "/onboarding",
    ctaLabel: "Open Console",
    icon: ClipboardCheck,
    /* Card gradients run one even ramp across the two Wedding Industry Ads
       colour families — brand blue stepping through indigo into the warm
       browns (deep blue → indigo → slate-violet → brown → mocha).

       These are SHADES of the extracted hues (#5070ff, #4b4137, #87725f,
       #221e17), deepened rather than used raw. The reason is contrast, not
       taste: card copy is white, and the palette's light end (#8da1fd,
       #c39878) sits near 2.2:1 on white type. Every stop below clears 5.3:1,
       so a card reads at its light end as well as its dark one. Same depth
       across all five so none glares. Keep new tools on this ramp. */
    from: "#3644b8",
    to: "#4a5ce0",
  },
  {
    id: "internal-meeting",
    name: "Internal Meeting + Action Items",
    description:
      "Paste a meeting transcript and get the action items with owners, dates and the exact words they came from — checked against what was still open last time, so nothing is recorded twice.",
    tags: ["Paste intake", "Review gate", "Own ledger"],
    status: "live",
    roles: ["team", "client"],
    url: "",
    /* Its own console rather than the /automations/<id> audit stub: this is a
       transcript reader feeding a decision queue, not an audit runner.

       No `auditType` on purpose — unlike Client Onboarding there is no history
       of audit records to keep joined, so adding one would put an empty tool
       into HistoryPage and data/timeline.ts. */
    route: "/internal-meeting",
    ctaLabel: "Open Console",
    icon: ListChecks,
    /* Next stop on the shared ramp after Client Onboarding's #3644b8 → #4a5ce0
       (see the note there): indigo stepping toward slate-violet. Clears the
       same contrast floor for white card copy. */
    from: "#3a3f96",
    to: "#4b52b0",
  },
  {
    id: "roll-call",
    name: "Office Hours Roll Call",
    description:
      "Paste an office-hours transcript and it works out who attended, keeps the running count of consecutive misses per member, and raises the two-week and four-week flags on separate counters per track.",
    tags: ["Paste intake", "Two tracks", "Flag only"],
    status: "live",
    roles: ["team", "client"],
    url: "",
    /* Its own console rather than the /automations/<id> audit stub: a two-tab
       attendance register, not an audit runner. No `auditType` for the same
       reason as Internal Meeting — there is no audit history to keep joined. */
    route: "/roll-call",
    ctaLabel: "Open Console",
    icon: CalendarCheck,
    /* Third stop on the shared ramp (see the note on Client Onboarding):
       slate-violet, between Internal Meeting's indigo and the warm browns. */
    from: "#3c3a86",
    to: "#4e4ba2",
  },
  {
    // id stays "ai-seo": it is the route segment (/automations/ai-seo), the BFF
    // mount path (/api/ai-seo), and the cross-reference used by data/timeline.ts
    // and pages/HistoryPage.tsx. Only the display name changes.
    id: "ai-seo",
    /* Inherited from the Wahha dashboard this was forked from, and not
       part of the Wedding Industry Ads engagement. Hidden from the
       library; still live at its own URL. */
    hidden: true,
    name: "AI Crawlability Readiness Checker",
    description:
      "Be readable by AI. Audit whether AI crawlers can reach, parse and trust your site — structured data, content design, authorship and blockers.",
    tags: ["AI crawlability", "Structured data", "Crawler access"],
    status: "live",
    roles: ["team", "client"],
    url: "", // inline runner uses the authenticated AI crawlability BFF
    auditType: "ai",
    icon: Sparkles,
    from: "#3a3f96",
    to: "#4d55b4",
  },
  {
    id: "ai-presence-checker",
    /* Inherited from the Wahha dashboard this was forked from, and not
       part of the Wedding Industry Ads engagement. Hidden from the
       library; still live at its own URL. */
    hidden: true,
    name: "AI Presence Checker",
    description:
      "See where your brand shows up across AI assistants — presence, mentions and how often ChatGPT, Gemini and Perplexity surface you.",
    tags: ["AI presence", "Brand mentions", "Assistant coverage"],
    status: "live",
    roles: ["team", "client"],
    url: "", // inline runner — see AI_PRESENCE_AUDIT_URL note in services/api/audits.ts
    auditType: "ai-presence",
    icon: Radar,
    from: "#3c3a6e",
    to: "#52508e",
  },
  {
    id: "on-page-seo",
    /* Inherited from the Wahha dashboard this was forked from, and not
       part of the Wedding Industry Ads engagement. Hidden from the
       library; still live at its own URL. */
    hidden: true,
    name: "On-Page SEO",
    description:
      "Page-by-page optimization — content scoring, metadata, internal links and keyword coverage in one view.",
    tags: ["Content scoring", "Metadata", "Internal links"],
    status: "live",
    roles: ["team", "client"],
    url: "", // inline runner uses the authenticated On-Page SEO BFF
    auditType: "on-page",
    icon: FileSearch,
    from: "#4b4137",
    to: "#6a5b4a",
  },
  /* ON THE ROADMAP, NOT BUILT — and deliberately listed anyway.

     Tina spends the first few business days of every month assembling client
     reports by hand (Sept 2 @33:01): screenshots per ad account, written
     context, a recorded walkthrough. Derived at 18–24 hrs/month, it is the
     largest single recurring cost named anywhere in discovery — larger than
     every audited assistant task combined. Whitney asked for it directly, in
     the form of an executive summary rather than another screenshot deck.

     It has no console yet, so it carries `status: "development"` with an empty
     `url`, which locks the card to "Coming soon". A library that silently
     omitted the biggest item on the roadmap would misrepresent the plan. */
  {
    id: "monthly-report-pack",
    name: "Monthly Client Report Pack",
    description:
      "Replaces the hand-built monthly report: pulls each client's Google and Meta numbers, writes the plain-English executive summary of what changed and why, and hands it over for review before a client ever sees it.",
    tags: ["Monthly", "Exec summary", "PM-03"],
    /* NOT "Run Audit". This is a reporting build, not an audit runner, and
       the default CTA promised a button that does not exist for it. */
    ctaLabel: "Coming soon",
    status: "development",
    roles: ["team", "client"],
    url: "",
    icon: LineChart,
    from: "#4b4137",
    to: "#6a5b4a",
  },
  {
    id: "lead-magnet",
    /* Inherited from the Wahha dashboard this was forked from, and not
       part of the Wedding Industry Ads engagement. Hidden from the
       library; still live at its own URL. */
    hidden: true,
    name: "Lead Magnet",
    description:
      "Capture and convert — track lead magnet performance, downloads and the pipeline they feed, in real time.",
    tags: ["Lead capture", "Conversions", "Pipeline"],
    status: "development",
    // Open to every signed-in account. The console lists lead PII (name, email,
    // phone), so the boundary is the session itself: requireSession on the
    // /api/leadmagnet/leads routes, with no role narrowing above it.
    roles: ["team", "client"],
    url: "",
    // Its own console, not the generic stub — the lead pipeline is a records
    // list rather than an audit runner.
    route: "/leadmagnetdashboard",
    ctaLabel: "View Console",
    icon: Magnet,
    from: "#5c4c3c",
    to: "#7a6752",
  },
];

/**
 * The list every consumer reads, with each `status` resolved against its
 * environment flag. Doing it here means one gate covers all of them — the
 * automations fan, the tool page (including someone typing the URL directly),
 * the inline audit panel and the hero counters.
 */
export const tools: Tool[] = TOOLS.map((tool) => ({
  ...tool,
  status: resolveToolStatus(tool.id, tool.status),
}));

/** Where a tool opens in-app. */
export const toolRoute = (tool: Tool) => tool.route ?? `/automations/${tool.id}`;

/**
 * Tools to offer a given role. Until this existed `Tool.roles` was declared,
 * populated and read by nothing, so every account saw every tile.
 *
 * A signed-out visitor (role `null`) gets the CLIENT view — the least-privileged
 * one — so an internal, team-only tool is not advertised on the public landing
 * page before anyone has signed in.
 *
 * This is presentation only. Hiding a tile is not access control: the route
 * guard and the server-side role check on the tool's own API are.
 */
export const toolsForRole = (role: UserRole | null | undefined): Tool[] =>
  tools.filter((tool) => !tool.hidden && tool.roles.includes(role ?? "client"));
