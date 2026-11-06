import { useCallback, useEffect, useRef, useState } from "react";
import {
  clientPdfDownloadUrl,
  getAuditStatus,
  openAuditProgress,
  startAudit,
  TERMINAL_AUDIT_STATUSES,
  type AuditBackendStatus,
  type AuditProgressEvent,
  type AuditRunRequest,
  type AuditStatusDetail,
  type AuditType,
} from "@/services/api/audits";

/**
 * `awaiting_review` is not a backend status — the run is still `running` as far
 * as the shared vocabulary is concerned. It is a separate phase because the UI
 * has to swap a progress bar for an editor, and because a run can sit in it
 * indefinitely: nothing will move it along until a person acts.
 */
export type AuditPhase =
  | "idle"
  | "running"
  | "awaiting_review"
  | "completed"
  | "partial"
  | "failed"
  | "error";

export interface AuditBusiness {
  name: string;
  url: string;
}

/** Business-identity fields beyond name + URL. Only AI SEO consumes them. */
export type AuditRunIdentity = Omit<AuditRunRequest, "businessName" | "businessUrl">;

const POLL_INTERVAL_MS = 8_000;

/**
 * After a run finishes, its client PDF may still be rendering.
 *
 * Technical SEO renders the PDF inside the run, so its download URL exists the
 * moment the status goes terminal. AI Presence renders on a queue, so the URL
 * lands seconds to minutes later — and by then the progress stream and the
 * status poll have both stopped, which would leave the download button hidden
 * until the user reloaded. This is a short, bounded follow-up poll for that
 * window only; it never affects the audit's own outcome.
 */
const REPORT_POLL_INTERVAL_MS = 10_000;
const REPORT_POLL_MAX_ATTEMPTS = 30; // ~5 minutes

function isTerminalStatus(status: string): status is AuditBackendStatus {
  return TERMINAL_AUDIT_STATUSES.has(status as AuditBackendStatus);
}

function terminalPhase(
  status: AuditBackendStatus,
): Extract<AuditPhase, "completed" | "partial" | "failed"> {
  if (status === "completed") return "completed";
  if (status === "completed_partial") return "partial";
  return "failed";
}

/**
 * Stage label for a run that is still in flight.
 *
 * A straight pass-through of what the service reports, because every service
 * already derives `progress_stage` from the stage its worker is actually in —
 * On-Page answers "Crawling pages (128 / 340 crawled)", "Classifying pages",
 * "Running checks (18 / 33 complete)", "Building the report"; AI SEO answers
 * "Check 14". The poll therefore has a real stage name to show and does not
 * need to invent one.
 *
 * Nothing about the dashboard's transport belongs in this string. The suffix
 * that used to be appended here — "live stream unavailable; polling" — read as
 * a fault on a run that was progressing perfectly well: it fired on every
 * stream that ended for any reason, including a healthy one the service closed
 * at its own lifetime cap, and it stayed on screen for the rest of the run
 * because the stream is never reopened. Losing the stream costs eight seconds
 * of latency and nothing else, which is not news for the person watching.
 *
 * The fallback covers only a service that reports no stage at all. `queued` is
 * called out separately because "Running" would contradict it.
 */
function inFlightStage(detail: AuditStatusDetail): string {
  const label = detail.progress_stage?.trim();
  if (label) return label;
  return detail.status === "queued" ? "Queued" : "Running";
}

function terminalStage(status: AuditBackendStatus): string {
  return (
    {
      queued: "Queued",
      running: "Running",
      completed: "Completed",
      completed_partial: "Completed with warnings",
      failed: "Failed",
      cancelled: "Cancelled",
      interrupted: "Interrupted",
    } satisfies Record<AuditBackendStatus, string>
  )[status];
}

/**
 * State machine for one audit run. SSE is used for responsive progress, while
 * authenticated status polling is the source of truth for every terminal state
 * and automatically takes over if a stream is interrupted.
 */
export function useAuditRun(type: AuditType) {
  const [phase, setPhase] = useState<AuditPhase>("idle");
  const [percent, setPercent] = useState(0);
  const [stage, setStage] = useState("");
  const [business, setBusiness] = useState<AuditBusiness | null>(null);
  const [auditId, setAuditId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AuditStatusDetail | null>(null);
  const streamRef = useRef<EventSource | null>(null);
  const pollRef = useRef<number | null>(null);
  const reportPollRef = useRef<number | null>(null);
  const phaseRef = useRef<AuditPhase>("idle");

  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);

  const closeStream = useCallback(() => {
    streamRef.current?.close();
    streamRef.current = null;
  }, []);

  const clearPolling = useCallback(() => {
    if (pollRef.current !== null) window.clearInterval(pollRef.current);
    pollRef.current = null;
  }, []);

  const clearReportPolling = useCallback(() => {
    if (reportPollRef.current !== null) window.clearInterval(reportPollRef.current);
    reportPollRef.current = null;
  }, []);

  const stop = useCallback(() => {
    closeStream();
    clearPolling();
    clearReportPolling();
  }, [clearPolling, clearReportPolling, closeStream]);

  /** Watch a finished run until its client PDF URL appears, then stop. */
  const startReportPolling = useCallback(
    (id: string) => {
      if (reportPollRef.current !== null) return;
      let attempts = 0;
      reportPollRef.current = window.setInterval(async () => {
        attempts += 1;
        try {
          const nextDetail = await getAuditStatus(type, id);
          if (clientPdfDownloadUrl(nextDetail)) {
            setDetail(nextDetail);
            clearReportPolling();
            return;
          }
        } catch {
          // A transient failure is not a verdict on the report; keep waiting
          // until the attempt cap, which is the only thing that ends this.
        }
        if (attempts >= REPORT_POLL_MAX_ATTEMPTS) clearReportPolling();
      }, REPORT_POLL_INTERVAL_MS);
    },
    [clearReportPolling, type],
  );

  const applyTerminalDetail = useCallback(
    (id: string, nextDetail: AuditStatusDetail, status: AuditBackendStatus) => {
      stop();
      setDetail(nextDetail);
      setPercent(100);
      setStage(terminalStage(status));
      setPhase(terminalPhase(status));
      // The run is over but its PDF may not be. Only wait when the service says
      // a report exists, so a failed or report-less run settles immediately.
      if (nextDetail.report_ready && !clientPdfDownloadUrl(nextDetail)) {
        startReportPolling(id);
      }
    },
    [startReportPolling, stop],
  );

  const syncStatus = useCallback(
    async (id: string): Promise<boolean> => {
      try {
        const nextDetail = await getAuditStatus(type, id);
        setDetail(nextDetail);
        if (isTerminalStatus(nextDetail.status)) {
          applyTerminalDetail(id, nextDetail, nextDetail.status);
          return true;
        }
        // Parked on a human, not on the pipeline. Stop the stream and polling:
        // nothing will change until the query set is confirmed, and a spinner
        // that keeps ticking reads as progress that is not happening.
        if (nextDetail.awaiting_review) {
          stop();
          setPercent(Math.max(0, Math.min(99, Number(nextDetail.progress_percent) || 0)));
          setStage("Waiting for query review");
          setPhase("awaiting_review");
          return true;
        }
        setPercent(Math.max(0, Math.min(99, Number(nextDetail.progress_percent) || 0)));
        setStage(inFlightStage(nextDetail));
        return false;
      } catch {
        return false;
      }
    },
    [applyTerminalDetail, stop, type],
  );

  const startPolling = useCallback(
    (id: string) => {
      if (pollRef.current !== null || phaseRef.current !== "running") return;
      // The stage is deliberately left alone. Whatever is on screen — the last
      // streamed stage, or "Queued"/"Loading audit…" when the stream never
      // opened — is still true, and the first poll below replaces it with the
      // service's own label within a round trip. Writing a "switching to
      // polling" line here only put the dashboard's plumbing in front of the
      // user for that one round trip.
      void syncStatus(id);
      pollRef.current = window.setInterval(() => {
        void syncStatus(id);
      }, POLL_INTERVAL_MS);
    },
    [syncStatus],
  );

  const listen = useCallback(
    (id: string) => {
      const source = openAuditProgress(type, id);
      streamRef.current = source;
      source.onmessage = (event) => {
        let update: AuditProgressEvent;
        try {
          update = JSON.parse(event.data) as AuditProgressEvent;
        } catch {
          // A malformed event must not turn a real audit into a false success.
          startPolling(id);
          return;
        }
        setPercent(Math.max(0, Math.min(100, Number(update.percent) || 0)));
        setStage(update.stage || "Running");
        // The stream keeps heartbeating while a run waits on its review, so this
        // is the in-session path into the gate — sync to pick up the query set.
        if (update.awaiting_review) {
          closeStream();
          void syncStatus(id);
          return;
        }
        if (update.done || (typeof update.status === "string" && isTerminalStatus(update.status))) {
          // SSE is advisory; fetch persisted status before deciding success,
          // partial completion, cancellation, interruption, or failure.
          closeStream();
          void syncStatus(id).then((terminal) => {
            if (!terminal) startPolling(id);
          });
        }
      };
      source.onerror = () => {
        closeStream();
        // Do not surface a transient transport loss as an audit failure. The
        // persisted status endpoint is retried until it reaches a terminal state.
        startPolling(id);
      };
    },
    [closeStream, startPolling, syncStatus, type],
  );

  useEffect(() => stop, [stop]);

  const run = useCallback(
    async (name: string, url: string, identity: AuditRunIdentity = {}) => {
      if (phaseRef.current === "running") return;
      stop();
      setBusiness({ name, url });
      setAuditId(null);
      setDetail(null);
      setPhase("running");
      setPercent(0);
      setStage("Submitting audit…");
      try {
        const response = await startAudit(type, {
          businessName: name,
          businessUrl: url,
          ...identity,
        });
        setAuditId(response.auditId);
        setStage("Queued");
        listen(response.auditId);
      } catch {
        stop();
        setStage("Unable to start audit");
        setPhase("error");
      }
    },
    [listen, stop, type],
  );

  /**
   * Attach to a run that already exists, instead of starting one.
   *
   * This is what makes a run addressable after the tab that started it is gone:
   * the tool page reads an id out of the URL and calls this. Business identity
   * comes from the persisted detail rather than the intake form, which the
   * returning user never filled in.
   */
  const resume = useCallback(
    async (id: string) => {
      if (phaseRef.current === "running" && auditId === id) return;
      stop();
      setAuditId(id);
      setDetail(null);
      setPhase("running");
      setPercent(0);
      setStage("Loading audit…");
      const terminal = await syncStatus(id);
      // Only listen if there is still something to listen to: a finished run and
      // one parked on review are both settled as far as the stream goes.
      if (!terminal) listen(id);
    },
    [auditId, listen, stop, syncStatus],
  );

  /** Re-read a run after an out-of-band change, e.g. its queries were confirmed. */
  const refresh = useCallback(
    async (id: string) => {
      const terminal = await syncStatus(id);
      if (!terminal) {
        setPhase("running");
        listen(id);
      }
    },
    [listen, syncStatus],
  );

  const reset = useCallback(() => {
    stop();
    setPhase("idle");
    setPercent(0);
    setStage("");
    setBusiness(null);
    setAuditId(null);
    setDetail(null);
  }, [stop]);

  return { phase, percent, stage, business, auditId, detail, run, resume, refresh, reset };
}
