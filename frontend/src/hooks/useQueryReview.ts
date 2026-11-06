import { useCallback, useEffect, useRef, useState } from "react";
import { confirmAuditQueries, getAuditQueries } from "@/services/api/aiPresence";
import {
  buildConfirmQueriesPayload,
  countVisibilityQueries,
  getMaxQueryNumber,
  mapQueriesToSections,
  QUERY_FETCH_STATUS,
  type QueryFetchStatus,
  type QuerySection,
} from "@/lib/queryReview";

/**
 * The editable query set for one AI Presence run parked at review.
 *
 * Fetch → edit → confirm, with the run id as the identity. Everything is keyed
 * to `auditId` and reset when it changes, so opening a second run can never show
 * or submit the first one's queries.
 */
export function useQueryReview({
  auditId,
  active,
  onConfirmed,
}: {
  auditId: string | null;
  /** Whether the run is actually awaiting review — gates the fetch. */
  active: boolean;
  /** Called once the service has accepted the set and released the run. */
  onConfirmed: (auditId: string) => void;
}) {
  const [sections, setSections] = useState<QuerySection[]>([]);
  const [fetchStatus, setFetchStatus] = useState<QueryFetchStatus>(QUERY_FETCH_STATUS.IDLE);
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [retryToken, setRetryToken] = useState(0);
  const nextQueryId = useRef(0);
  /**
   * Which request has been started, as `auditId:retryToken`.
   *
   * This is what makes the fetch safe, and it replaced a `cancelled` flag tied to
   * the effect's cleanup. That flag looked right but discarded every response:
   * `fetchStatus` was an effect dependency AND the effect set it to `loading`, so
   * starting the request immediately re-ran the effect, whose cleanup cancelled
   * the request it had just made. The response arrived, saw `cancelled`, and
   * returned — leaving the panel on "Loading the generated queries…" forever
   * while the network tab showed a perfectly good 200.
   *
   * A ref keyed to the request is the right test: discard a response only when a
   * NEWER request has superseded it, never merely because the effect re-ran.
   */
  const requestedKeyRef = useRef<string | null>(null);

  const total = countVisibilityQueries(sections);

  // A different run must not inherit the previous one's set, even for the frame
  // between the id changing and the fetch resolving.
  useEffect(() => {
    setSections([]);
    setFetchStatus(QUERY_FETCH_STATUS.IDLE);
    setError("");
  }, [auditId]);

  useEffect(() => {
    if (!auditId || !active) return;

    // Deliberately NOT dependent on fetchStatus or total: this effect writes
    // fetchStatus, so depending on it makes the effect retrigger itself.
    const requestKey = `${auditId}:${retryToken}`;
    if (requestedKeyRef.current === requestKey) return;
    requestedKeyRef.current = requestKey;

    setFetchStatus(QUERY_FETCH_STATUS.LOADING);
    setError("");

    getAuditQueries(auditId)
      .then((queries) => {
        if (requestedKeyRef.current !== requestKey) return;
        setSections(mapQueriesToSections(queries));
        setFetchStatus(QUERY_FETCH_STATUS.DONE);
      })
      .catch(() => {
        if (requestedKeyRef.current !== requestKey) return;
        // A 409 while generation finishes lands here, so this is retryable rather
        // than terminal — hence the visible Try again.
        setFetchStatus(QUERY_FETCH_STATUS.ERROR);
        setError("We could not load the generated queries. Try again in a moment.");
      });
  }, [auditId, active, retryToken]);

  // Bumping the token changes the request key, which is what lets the effect run
  // again — resetting fetchStatus alone would no longer retrigger it.
  const retry = useCallback(() => setRetryToken((token) => token + 1), []);

  const updateQueryText = useCallback((sectionIndex: number, queryIndex: number, text: string) => {
    setSections((current) =>
      current.map((section, sIdx) =>
        sIdx !== sectionIndex
          ? section
          : {
              ...section,
              queries: section.queries.map((query, qIdx) =>
                qIdx === queryIndex ? { ...query, query_text: text } : query,
              ),
            },
      ),
    );
  }, []);

  const removeQuery = useCallback((sectionIndex: number, queryIndex: number) => {
    setSections((current) =>
      current.map((section, sIdx) =>
        sIdx !== sectionIndex
          ? section
          : { ...section, queries: section.queries.filter((_, qIdx) => qIdx !== queryIndex) },
      ),
    );
  }, []);

  const addQuery = useCallback((sectionIndex: number) => {
    setSections((current) => {
      // Continue past the highest generated number so a new query cannot collide
      // with an existing one — the API keys aspect inheritance off that number.
      const nextNumber = Math.max(getMaxQueryNumber(current), nextQueryId.current) + 1;
      nextQueryId.current = nextNumber;
      return current.map((section, sIdx) =>
        sIdx !== sectionIndex
          ? section
          : {
              ...section,
              queries: [...section.queries, { query_number: nextNumber, query_text: "" }],
            },
      );
    });
  }, []);

  const confirm = useCallback(async () => {
    if (!auditId || confirming) return;
    const payload = buildConfirmQueriesPayload(sections);
    if (!payload.queries.length) return;

    setConfirming(true);
    setError("");
    try {
      await confirmAuditQueries(auditId, payload.queries);
      onConfirmed(auditId);
    } catch (caught) {
      // 409 means the run already left review — another tab confirmed it, or
      // this is a double submit. Re-reading the run is the right response, not
      // an error the user has to act on.
      const status = (caught as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        onConfirmed(auditId);
        return;
      }
      setError("We could not confirm these queries. Give it another go.");
    } finally {
      setConfirming(false);
    }
  }, [auditId, confirming, onConfirmed, sections]);

  return {
    sections,
    total,
    fetchStatus,
    error,
    confirming,
    retry,
    addQuery,
    updateQueryText,
    removeQuery,
    confirm,
  };
}
