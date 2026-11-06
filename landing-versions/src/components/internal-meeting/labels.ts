import type { Decision } from "@/hooks/useInternalMeetingRun";

/* Kept out of parts.tsx so that file exports only components — the same
   react-refresh contract `context/auth.ts` is split for. Type-only imports do
   not create a runtime edge back to the hook. */

/** How a recorded decision reads once it is made, in past tense. */
export const DECISION_LABEL: Record<Decision, string> = {
  record: "Recorded",
  not_an_item: "Not an item",
  closed: "Closed by you",
  snooze: "Snoozed to next run",
};
