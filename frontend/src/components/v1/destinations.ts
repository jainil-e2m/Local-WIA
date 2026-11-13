import {
  FilePenLine,
  House,
  Send,
  Waypoints,
  type LucideIcon,
} from "lucide-react";

/* ────────────────────────────────────────────────────────────────
   Where everything on the variant-1 landing goes.

   One table feeds the sidebar, the orbiting cards and the command
   palette, so a destination can never mean one thing in the nav and
   another on a card. The targets include the automation library, the
   members portal, and the Content Atelier's launch link (lib/atelierLaunch.ts).
   ──────────────────────────────────────────────────────────────── */

export const VAULT_URL = "https://members.weddingindustryads.com/";

/** The deployed build timeline (its own app, WIA-Automation-Timeline). */
export const TIMELINE_URL = "https://timeline-wia.up.railway.app/";

export type V1Action =
  | { kind: "route"; to: string }
  | { kind: "external"; href: string }
  /* The Content Atelier, its own app: a full-page navigation through the
     sign-on hand-off, unavailable where the Atelier is not configured. */
  | { kind: "atelier" }
  | { kind: "automations" }
  | { kind: "timeline" }
  | { kind: "overview" }
  | { kind: "top" }
  | { kind: "explore" };

export interface V1NavItem {
  id: string;
  label: string;
  icon: LucideIcon;
  action: V1Action;
  /** One line for the command palette. */
  hint: string;
}

export const NAV: V1NavItem[] = [
  { id: "home", label: "Home", icon: House, action: { kind: "top" }, hint: "This page" },
  {
    id: "automations",
    label: "Automations",
    icon: Waypoints,
    action: { kind: "automations" },
    hint: "Open the automations library",
  },
  {
    id: "campaigns",
    label: "Campaigns",
    icon: Send,
    action: { kind: "atelier" },
    hint: "Content Atelier · WIA's own marketing",
  },
  {
    id: "resources",
    label: "Resources",
    icon: FilePenLine,
    action: { kind: "external", href: VAULT_URL },
    hint: "The Vault · members portal",
  },
];

/** The three places the team works outside this app (as RotatingDestination). */
export const EXTERNAL = [
  { id: "website", label: "Website", href: "https://weddingindustryads.com", hint: "weddingindustryads.com" },
  { id: "leadlock", label: "LeadLock", href: "https://app.leadlockpro.com/", hint: "app.leadlockpro.com" },
  { id: "vault", label: "The Vault", href: VAULT_URL, hint: "members.weddingindustryads.com" },
] as const;

export type OrbitGlyph = "folder" | "lock" | "globe";

export interface OrbitCardDef {
  id: string;
  title: string;
  glyph: OrbitGlyph;
  action: V1Action;
  /** Where the card starts on the orbit, in degrees (0 = 3 o'clock,
      clockwise). Chosen so the opening frame reads like the design. */
  angle: number;
}

const site = (id: (typeof EXTERNAL)[number]["id"]): V1Action => ({
  kind: "external",
  href: EXTERNAL.find((e) => e.id === id)!.href,
});

/* The three places the team works outside this app, riding the hero's
   orbit — the same links as the footer, read from EXTERNAL. A third of a
   turn apart, so they never crowd however far the orbit has turned. */
export const ORBIT_CARDS: OrbitCardDef[] = [
  { id: "vault", title: "The Vault", glyph: "folder", action: site("vault"), angle: 222 },
  { id: "leadlock", title: "LeadLock", glyph: "lock", action: site("leadlock"), angle: 342 },
  { id: "website", title: "Wedding Industry Ads", glyph: "globe", action: site("website"), angle: 102 },
];
