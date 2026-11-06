import {
  ChartNoAxesColumnIncreasing,
  FilePenLine,
  House,
  Send,
  Settings,
  Users,
  Waypoints,
  type LucideIcon,
} from "lucide-react";

/* ────────────────────────────────────────────────────────────────
   Where everything on the variant-1 landing goes.

   One table feeds the sidebar, the orbiting cards and the command
   palette, so a destination can never mean one thing in the nav and
   another on a card. Every target is a surface that already exists:
   an Ops Hub screen (deep-linked through its `?screen=` key, see
   OpsHubPage), the automations fan, or the members portal.
   ──────────────────────────────────────────────────────────────── */

export const VAULT_URL = "https://members.weddingindustryads.com/";

export type V1Action =
  | { kind: "route"; to: string }
  | { kind: "external"; href: string }
  | { kind: "automations" }
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
    action: { kind: "route", to: "/ops-hub?screen=content" },
    hint: "Content Atelier · WIA's own marketing",
  },
  {
    id: "leads",
    label: "Leads",
    icon: Users,
    action: { kind: "route", to: "/ops-hub?screen=inbox" },
    hint: "AI Inbox · triage and drafts",
  },
  {
    id: "insights",
    label: "Insights",
    icon: ChartNoAxesColumnIncreasing,
    action: { kind: "route", to: "/ops-hub?screen=ops" },
    hint: "Ops Watch · exceptions and routines",
  },
  {
    id: "resources",
    label: "Resources",
    icon: FilePenLine,
    action: { kind: "external", href: VAULT_URL },
    hint: "The Vault · members portal",
  },
  {
    id: "settings",
    label: "Settings",
    icon: Settings,
    action: { kind: "route", to: "/ops-hub?screen=settings" },
    hint: "Source coverage and access",
  },
];

export type OrbitGlyph = "spark" | "bars" | "people" | "bolt" | "folder";

export interface OrbitCardDef {
  id: string;
  title: string;
  sub: string;
  glyph: OrbitGlyph;
  action: V1Action;
  /** Where the card starts on the orbit, in degrees (0 = 3 o'clock,
      clockwise). Chosen so the opening frame reads like the design. */
  angle: number;
}

/* At least 60° apart everywhere, so two cards never touch however far the
   orbit has turned: at the 320px orbit radius that is a 320px chord against
   a 236px card. */
export const ORBIT_CARDS: OrbitCardDef[] = [
  {
    id: "automations",
    title: "Automations",
    sub: "Save time. Do more.",
    glyph: "spark",
    action: { kind: "automations" },
    angle: 222,
  },
  {
    id: "campaigns",
    title: "Campaigns",
    sub: "Performance up 24%",
    glyph: "bars",
    action: { kind: "route", to: "/ops-hub?screen=content" },
    angle: 308,
  },
  {
    id: "clients",
    title: "Clients",
    sub: "Happy clients. Bigger dreams.",
    glyph: "people",
    action: { kind: "route", to: "/ops-hub?screen=clients" },
    angle: 8,
  },
  {
    id: "vault",
    title: "The Vault",
    sub: "Assets, templates, guides.",
    glyph: "folder",
    action: { kind: "external", href: VAULT_URL },
    angle: 72,
  },
  {
    id: "ai-ops",
    title: "AI Operations",
    sub: "Smarter. Faster. Consistent.",
    glyph: "bolt",
    action: { kind: "route", to: "/ops-hub" },
    angle: 148,
  },
];

/** The three places the team works outside this app (as RotatingDestination). */
export const EXTERNAL = [
  { id: "website", label: "Website", href: "https://weddingindustryads.com", hint: "weddingindustryads.com" },
  { id: "leadlock", label: "LeadLock", href: "https://app.leadlockpro.com/", hint: "app.leadlockpro.com" },
  { id: "vault", label: "The Vault", href: VAULT_URL, hint: "members.weddingindustryads.com" },
] as const;
