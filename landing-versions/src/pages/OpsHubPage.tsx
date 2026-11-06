/* ────────────────────────────────────────────────────────────────
   AI Operations Hub — /ops-hub

   Seven screens behind one shell, showing what a connected operations layer
   looks like across Gmail, Slack, ClickUp, Zoom, Fathom, Drive and HighLevel.

   IT IS A MOCK, AND IT SAYS SO ON EVERY SCREEN. There is no /api counterpart
   and no connector: the sidebar carries a "Demo environment · synthetic data"
   badge, every action toast ends in "simulated", and Settings lists what the
   environment is not. That is deliberate — the point of this build is to
   answer "how is it all connected?" in one place, which is a question about
   shape, not about live data.

   WHY A ROUTE AND NOT A MODAL. It has its own sidebar, its own seven-screen
   navigation and its own command palette. Nesting that inside the hero's
   AutomationsModal would put two navigation systems on top of each other.

   RELATIONSHIP TO THE STANDALONE CONSOLES. /onboarding, /roll-call and
   /internal-meeting are deliberately separate builds, and the separation is a
   claim about sequencing rather than about architecture: each is one Phase 1
   initiative that can ship, be used and be judged on its own (ON-01, MP-01,
   MK-01), while this hub is the surface they report into once several of them
   are live. Two consequences are stated on screen rather than assumed —
   Settings lists "No onboarding orchestration" first in its out-of-scope list,
   and the overlapping reads (office-hours attendance on Client Hub, execution
   packs on Meetings) carry a line naming the standalone console as the system
   of record. The onboarding console also runs on real ClickUp reads and
   terminates at a real human approval; this hub is synthetic throughout.

   STATE LIVES IN ONE HOOK. `useOpsHub` holds it all, because the counts are
   cross-screen: approving an email on Inbox has to decrement the Home KPI,
   the nav badge and the topbar bell in the same render.

   AND IT IS ADDRESSABLE. Screen, queue, item, meeting, client and tab are
   mirrored into the query string, so a specific review item has a URL that
   can be handed to a colleague — F03. Only navigation is mirrored: the
   MUTABLE demo state (what has been approved, nudged, released) deliberately
   is not, because a link that also replayed someone else's decisions would
   be a different and much stranger thing.
   ──────────────────────────────────────────────────────────────── */

import { useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { useOpsHub } from "@/hooks/useOpsHub";
import { OpsHubShell } from "@/components/opshub/OpsHubShell";
import { HomeScreen } from "@/components/opshub/screens/HomeScreen";
import { InboxScreen } from "@/components/opshub/screens/InboxScreen";
import { MeetingsScreen } from "@/components/opshub/screens/MeetingsScreen";
import { ClientHubScreen } from "@/components/opshub/screens/ClientHubScreen";
import { OpsWatchScreen } from "@/components/opshub/screens/OpsWatchScreen";
import { ContentAtelierScreen } from "@/components/opshub/screens/ContentAtelierScreen";
import { SettingsScreen } from "@/components/opshub/screens/SettingsScreen";

/* Which navigation keys ride in the URL, and their state field. */
const URL_KEYS = [
  ["screen", "screen"],
  ["q", "inboxQueue"],
  ["item", "emailId"],
  ["owner", "inboxOwner"],
  ["state", "inboxStateFilter"],
  ["meeting", "meetingId"],
  ["client", "clientId"],
  ["tab", "clientTab"],
  ["ops", "opsTab"],
  ["signal", "contentId"],
  ["format", "contentTab"],
  ["user", "user"],
] as const;

export default function OpsHubPage() {
  const hub = useOpsHub();
  const [params, setParams] = useSearchParams();
  const hydrated = useRef(false);

  /* Read the URL once on mount. After that the state is the source of truth
     and the URL follows it — two-way binding on every render would fight the
     back button. */
  useEffect(() => {
    if (hydrated.current) return;
    hydrated.current = true;
    const patch: Record<string, unknown> = {};
    for (const [key, field] of URL_KEYS) {
      const v = params.get(key);
      if (v !== null && v !== "") patch[field] = v;
    }
    if (Object.keys(patch).length) hub.patch(patch);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!hydrated.current) return;
    const next = new URLSearchParams();
    for (const [key, field] of URL_KEYS) {
      const v = (hub.state as unknown as Record<string, unknown>)[field];
      if (typeof v === "string" && v) next.set(key, v);
    }
    /* `replace` so a walkthrough does not fill the back button with one entry
       per click, while the address bar still carries a shareable link. */
    if (next.toString() !== params.toString()) setParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    hub.state.screen,
    hub.state.inboxQueue,
    hub.state.emailId,
    hub.state.inboxOwner,
    hub.state.inboxStateFilter,
    hub.state.meetingId,
    hub.state.clientId,
    hub.state.clientTab,
    hub.state.opsTab,
    hub.state.contentId,
    hub.state.contentTab,
    hub.state.user,
  ]);

  return (
    <OpsHubShell hub={hub}>
      {hub.state.screen === "home" && <HomeScreen hub={hub} />}
      {hub.state.screen === "inbox" && <InboxScreen hub={hub} />}
      {hub.state.screen === "meetings" && <MeetingsScreen hub={hub} />}
      {hub.state.screen === "clients" && <ClientHubScreen hub={hub} />}
      {hub.state.screen === "ops" && <OpsWatchScreen hub={hub} />}
      {hub.state.screen === "content" && <ContentAtelierScreen hub={hub} />}
      {hub.state.screen === "settings" && <SettingsScreen hub={hub} />}
    </OpsHubShell>
  );
}
