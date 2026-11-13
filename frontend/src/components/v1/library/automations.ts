import { TIMELINE_URL, type V1Action } from "../destinations";

/* ────────────────────────────────────────────────────────────────
   What the automation library shows, in order. The Content Atelier is
   live (its own deployment, reached through the server hand-off — see
   Tile); the other two are on the roadmap and open the deployed build
   timeline in a new tab.
   Each card's illustration is keyed by id in Art.tsx.
   ──────────────────────────────────────────────────────────────── */

export interface LibraryItem {
  id: string;
  name: string;
  /** The label on the card: "Live" or "Coming soon". */
  status: "Live" | "Coming soon";
  /** The filter chip it answers to. */
  category: string;
  description: string;
  /** Where the card's button goes; none for a build without a surface yet. */
  action?: V1Action;
  cta?: string;
}

export const LIBRARY: readonly LibraryItem[] = [
  {
    id: "content-atelier",
    name: "Content Atelier",
    status: "Live",
    category: "Content",
    description: "Turns real client moments into ready-to-post content in Whitney's voice: emails, reel scripts, carousels.",
  },
  {
    id: "client-knowledge-base",
    name: "Client Knowledge Base",
    status: "Coming soon",
    category: "Knowledge",
    description: "Everything about every client in one place, with sources: open asks, call prep and history from Slack, email and calls.",
    action: { kind: "external", href: TIMELINE_URL },
    cta: "View timeline",
  },
  {
    id: "paid-media-reporting",
    name: "Paid Media Reporting",
    status: "Coming soon",
    category: "Reporting",
    description: "Google and Meta results checked against WIA's own benchmarks, with clear next steps for every client.",
    action: { kind: "external", href: TIMELINE_URL },
    cta: "View timeline",
  },
];
