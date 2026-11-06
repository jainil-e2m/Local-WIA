import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowUpRight,
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronDown,
  Download,
  LayoutList,
  Loader2,
  Search,
  Table2,
  XCircle,
} from "lucide-react";
import { type AuditRecord, type AuditStatus } from "@/data/audits";
import { auditActionLabel, requiresQueryApproval } from "@/lib/auditActions";
import { tools } from "@/data/tools";
import {
  clientPdfDownloadUrl,
  getAuditStatus,
  listAudits,
  openAuditProgress,
  LISTABLE_AUDIT_TYPES,
  type AuditProgressEvent,
  type AuditStatusDetail,
  type AuditSummary,
  type AuditType,
} from "@/services/api/audits";

type View = "list" | "table";

const toolName = (id: string) => tools.find((t) => t.id === id)?.name ?? id;

/* ── Backend → AuditRecord mapping ──────────────────────────────────
   Each listable audit service maps to its tool tile (drives the row
   icon/colors) and a row label. */
const AUDIT_SOURCES: Record<AuditType, { toolId: string; label: string }> = {
  technical: { toolId: "technical-seo", label: "Technical SEO audit" },
  ai: { toolId: "ai-seo", label: "AI Crawlability Readiness audit" },
  "on-page": { toolId: "on-page-seo", label: "On-Page SEO audit" },
  "ai-presence": { toolId: "ai-presence-checker", label: "AI Presence Checker audit" },
};

const BACKEND_COMPLETED = new Set(["completed"]);
const BACKEND_PARTIAL = new Set(["completed_partial"]);
const BACKEND_FAILED = new Set(["failed", "cancelled", "interrupted"]);
const TERMINAL_BACKEND_STATUSES = new Set([
  "completed",
  "completed_partial",
  "failed",
  "cancelled",
  "interrupted",
]);
const STATUS_POLL_INTERVAL_MS = 8_000;

/**
 * AI Presence renders its client PDF on a separate queue *after* the run is
 * finalized, so `report_ready` is true while the download URL is still seconds
 * to minutes away. This is the bounded follow-up poll for that window only — it
 * mirrors useAuditRun's and never affects a run's outcome.
 */
const REPORT_POLL_INTERVAL_MS = 10_000;
const REPORT_POLL_WINDOW_MS = 5 * 60_000;
/**
 * How recently a listed run must have started for a missing PDF to be worth
 * waiting on. A run whose render failed — or any run on a deployment with no
 * Drive credentials — stays report-ready-without-a-URL forever, and without this
 * every such historical row would open its own poll on every visit to /history.
 */
const REPORT_FRESHNESS_MS = 30 * 60_000;

/** "type:id" — every stream and status read must go back to the owning service. */
const rowKey = (record: Pick<AuditRecord, "auditType" | "id">) =>
  `${record.auditType}:${record.id}`;

function parseRowKey(key: string): { auditType: AuditType; id: string } {
  const separator = key.indexOf(":");
  return { auditType: key.slice(0, separator) as AuditType, id: key.slice(separator + 1) };
}

const REPORT_UNAVAILABLE_MSG =
  "That report isn't available to download — its PDF wasn't uploaded to Google Drive for this audit.";

/** Preserve partial success instead of flattening it into a full completion. */
function mapStatus(backendStatus: string): AuditStatus {
  if (BACKEND_COMPLETED.has(backendStatus)) return "completed";
  if (BACKEND_PARTIAL.has(backendStatus)) return "partial";
  if (BACKEND_FAILED.has(backendStatus)) return "failed";
  return "running"; // queued | running | anything not yet terminal
}

function displayUrl(url: string): string {
  return url.replace(/^https?:\/\//i, "").replace(/\/+$/, "");
}

function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatDuration(startIso?: string | null, endIso?: string | null): string | undefined {
  if (!startIso || !endIso) return undefined;
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return undefined;
  const totalSeconds = Math.round((end - start) / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
}

/** GET /audits summary → an AuditRecord row. */
function toAuditRecord(summary: AuditSummary, auditType: AuditType): AuditRecord {
  const status = mapStatus(summary.status);
  const businessUrl = displayUrl(summary.seed_urls?.[0] ?? "");
  const source = AUDIT_SOURCES[auditType];
  const succeeded = status === "completed" || status === "partial";
  const reportUrl = succeeded ? (summary.client_pdf_download_url ?? undefined) : undefined;
  // A row that is permanently report-ready with no PDF must not poll forever.
  // An unparseable timestamp yields NaN, which fails this comparison — that is
  // the intended direction: no timestamp means no wait.
  const startedIso = summary.started_at ?? summary.submitted_at ?? null;
  const recentlyStarted =
    startedIso !== null && Date.now() - new Date(startedIso).getTime() < REPORT_FRESHNESS_MS;
  return {
    id: summary.audit_id,
    toolId: source.toolId,
    auditType,
    label: source.label,
    business: summary.business_name?.trim() || businessUrl || "Unknown business",
    businessUrl,
    status,
    awaitingReview: summary.awaiting_review === true,
    progressPercent: summary.progress_percent,
    progressStage: summary.progress_stage,
    progressUpdatedAt: summary.progress_updated_at ?? undefined,
    startedAt: formatTimestamp(summary.started_at ?? summary.submitted_at),
    sortKey: summary.submitted_at ?? summary.started_at ?? "",
    duration: formatDuration(summary.started_at, summary.finished_at),
    summary: summary.failure_reason ?? undefined,
    failureReason: status === "failed" ? (summary.failure_reason ?? undefined) : undefined,
    reportUrl,
    // Covers the case the SSE path cannot: /history opened while a PDF is still
    // rendering, so the row arrives already terminal and applyTerminalDetail
    // never runs for it.
    reportPending: succeeded && summary.report_ready === true && !reportUrl && recentlyStarted,
  };
}

/** Merge the DB-synced terminal detail (fetched when a run's SSE ends) into a row. */
function applyTerminalDetail(record: AuditRecord, detail: AuditStatusDetail): AuditRecord {
  const status = mapStatus(detail.status);
  const succeeded = status === "completed" || status === "partial";
  // Keep any URL the row already carried: AI Presence renders its PDF after the
  // run goes terminal, so an early detail fetch legitimately has none yet and
  // must not erase a link a later poll found.
  const reportUrl = succeeded ? (clientPdfDownloadUrl(detail) ?? record.reportUrl) : undefined;
  return {
    ...record,
    status,
    duration: formatDuration(detail.started_at, detail.finished_at) ?? record.duration,
    summary: detail.failure_reason ?? record.summary,
    failureReason: status === "failed" ? (detail.failure_reason ?? undefined) : undefined,
    reportUrl,
    // `report_ready` is AI Presence's field — the other services' details do not
    // carry it — so `=== true` means their rows are never marked pending and are
    // never polled by the report effect.
    reportPending: succeeded && detail.report_ready === true && !reportUrl,
  };
}

function applyProgressDetail(record: AuditRecord, detail: AuditStatusDetail): AuditRecord {
  if (TERMINAL_BACKEND_STATUSES.has(detail.status)) return applyTerminalDetail(record, detail);
  return {
    ...record,
    status: "running",
    // Refreshed on every poll, so a run confirmed in another tab stops asking
    // for approval here without a reload.
    awaitingReview: detail.awaiting_review === true,
    progressPercent: Math.max(0, Math.min(99, Number(detail.progress_percent) || 0)),
    progressStage: detail.progress_stage || "Running",
    progressUpdatedAt: detail.progress_updated_at ?? record.progressUpdatedAt,
  };
}

/**
 * /history — past and currently running audits across all tools.
 * Two views: "list" (cards, grouped by running/past) and "table"
 * (Timestamp · Business · Status · Audit Type · Download Report).
 * Loads from GET /audits. SSE provides fast updates; authenticated polling is
 * retained as the source-of-truth fallback if a stream is interrupted.
 */
export default function HistoryPage() {
  const [view, setView] = useState<View>("list");
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all"); // "all" | tool id
  const [statusFilter, setStatusFilter] = useState<"all" | AuditStatus>("all");
  const [records, setRecords] = useState<AuditRecord[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const sourcesRef = useRef<Map<string, EventSource>>(new Map());
  // Per-row deadline for the report wait. A ref rather than effect-local state:
  // the report effect re-runs whenever the awaiting set changes — one sibling
  // row resolving is enough — and a counter in the effect body would hand every
  // remaining row a fresh five minutes each time.
  const reportDeadlines = useRef<Map<string, number>>(new Map());
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const reportUnavailable = () => {
    setToast(REPORT_UNAVAILABLE_MSG);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 5000);
  };

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  // "type:id" so a refresh reopens against the service the row came from.
  const runningKeysKey = records
    .filter((record) => record.status === "running")
    .map(rowKey)
    .sort()
    .join("|");

  // Finished runs whose client PDF has not landed yet. Provably disjoint from
  // runningKeysKey: that set is `status === "running"` and this one excludes it,
  // so no row is ever polled by both effects. A joined string again, so
  // membership changes here cannot churn the running effect or reopen a stream.
  const awaitingReportKeysKey = records
    .filter((record) => record.status !== "running" && record.reportPending && !record.reportUrl)
    .map(rowKey)
    .sort()
    .join("|");

  // Load the audit history once from each live audit service. One service being
  // unreachable must not hide the others, so failures are per-source: the error
  // state is reserved for every source failing.
  useEffect(() => {
    let cancelled = false;
    Promise.allSettled(
      LISTABLE_AUDIT_TYPES.map((auditType) =>
        listAudits(auditType).then((summaries) =>
          summaries.map((summary) => toAuditRecord(summary, auditType)),
        ),
      ),
    ).then((results) => {
      if (cancelled) return;
      const loaded = results.flatMap((result) =>
        result.status === "fulfilled" ? result.value : [],
      );
      if (results.every((result) => result.status === "rejected")) {
        setLoadState("error");
        return;
      }
      // Newest first across every source; startedAt is already display-formatted,
      // so sorting uses the raw submitted/started timestamp captured on the row.
      loaded.sort((a, b) => (b.sortKey ?? "").localeCompare(a.sortKey ?? ""));
      setRecords(loaded);
      setLoadState("ready");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Live status for still-running rows. A transient SSE disconnect is never
  // treated as completion: periodic DB-backed status reads continue until an
  // authoritative terminal state is available.
  useEffect(() => {
    const sources = sourcesRef.current;
    // Each key is "auditType:auditId" so every reopened stream and status read
    // goes back to the service that owns the run.
    const runningKeys = new Set(runningKeysKey ? runningKeysKey.split("|") : []);
    let disposed = false;

    const refreshStatus = async (key: string) => {
      const { auditType, id } = parseRowKey(key);
      try {
        const detail = await getAuditStatus(auditType, id);
        if (disposed) return;
        setRecords((prev) =>
          prev.map((record) =>
            record.id === id && record.auditType === auditType
              ? applyProgressDetail(record, detail)
              : record,
          ),
        );
      } catch {
        // Preserve the last known state. The next poll can still recover it.
      }
    };

    for (const [key, source] of sources) {
      if (!runningKeys.has(key)) {
        source.close();
        sources.delete(key);
      }
    }
    for (const key of runningKeys) {
      if (sources.has(key)) continue;
      const { auditType, id } = parseRowKey(key);
      const source = openAuditProgress(auditType, id);
      sources.set(key, source);
      source.onmessage = (event) => {
        let update: AuditProgressEvent;
        try {
          update = JSON.parse(event.data) as AuditProgressEvent;
        } catch {
          return;
        }
        if (!update.done && !TERMINAL_BACKEND_STATUSES.has(update.status ?? "")) {
          setRecords((prev) =>
            prev.map((record) =>
              record.id === id && record.auditType === auditType
                ? {
                    ...record,
                    progressPercent: Math.max(0, Math.min(99, Number(update.percent) || 0)),
                    progressStage: update.stage || "Running",
                  }
                : record,
            ),
          );
          return;
        }
        source.close();
        sources.delete(key);
        void refreshStatus(key);
      };
      source.onerror = () => {
        // Polling below takes over after a dropped stream.
        source.close();
        sources.delete(key);
        void refreshStatus(key);
      };
    }
    const pollTimer = window.setInterval(() => {
      for (const key of runningKeys) void refreshStatus(key);
    }, STATUS_POLL_INTERVAL_MS);
    for (const key of runningKeys) void refreshStatus(key);

    return () => {
      disposed = true;
      window.clearInterval(pollTimer);
    };
  }, [runningKeysKey]);

  // Follow-up poll for a PDF that lands after its run went terminal. Separate
  // from the effect above on purpose: it must not touch runningKeysKey, must not
  // open a stream, and must keep working once the row has left the running set.
  useEffect(() => {
    if (!awaitingReportKeysKey) return;
    const keys = awaitingReportKeysKey.split("|");
    const deadlines = reportDeadlines.current;
    const startedAt = Date.now();
    for (const key of keys) {
      if (!deadlines.has(key)) deadlines.set(key, startedAt + REPORT_POLL_WINDOW_MS);
    }
    let disposed = false;

    // Reads only `keys` and the deadline ref — never `records`, which would be
    // this render's snapshot. Every write goes through the functional updater.
    const refreshReport = async (key: string) => {
      const { auditType, id } = parseRowKey(key);
      try {
        const detail = await getAuditStatus(auditType, id);
        if (disposed) return;
        setRecords((prev) =>
          prev.map((record) =>
            record.id === id && record.auditType === auditType
              ? applyTerminalDetail(record, detail)
              : record,
          ),
        );
      } catch {
        // A transient failure is not a verdict on the report; only the deadline
        // ends this wait.
      }
    };

    const timer = window.setInterval(() => {
      const now = Date.now();
      const expired = keys.filter((key) => (deadlines.get(key) ?? 0) <= now);
      if (expired.length) {
        // Give up honestly. Clearing the flag restores the plain Download button
        // and its "not available" toast — the truth once the render job has had
        // its window — and drops the key from the derived set, so this effect
        // re-runs and the last one out leaves no interval behind.
        const expiredKeys = new Set(expired);
        setRecords((prev) =>
          prev.map((record) =>
            record.reportPending && expiredKeys.has(rowKey(record))
              ? { ...record, reportPending: false }
              : record,
          ),
        );
      }
      for (const key of keys) {
        if ((deadlines.get(key) ?? 0) > now) void refreshReport(key);
      }
    }, REPORT_POLL_INTERVAL_MS);
    // No immediate read: the list row or detail this state came from was fetched
    // moments ago, so the first useful attempt is one interval out.

    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [awaitingReportKeysKey]);

  // Close every open stream when leaving the page.
  useEffect(() => {
    const sources = sourcesRef.current;
    return () => {
      for (const source of sources.values()) source.close();
      sources.clear();
      if (toastTimer.current) clearTimeout(toastTimer.current);
    };
  }, []);

  const q = query.trim().toLowerCase();
  const filtered = records.filter((a) => {
    if (typeFilter !== "all" && a.toolId !== typeFilter) return false;
    if (statusFilter !== "all" && a.status !== statusFilter) return false;
    if (q) {
      const haystack = [toolName(a.toolId), a.business, a.businessUrl, a.startedAt]
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });
  const isFiltered = q !== "" || typeFilter !== "all" || statusFilter !== "all";

  const running = filtered.filter((a) => a.status === "running");
  const past = filtered.filter((a) => a.status !== "running");

  return (
    <div className="bg-hero relative min-h-[100svh] overflow-hidden text-white">
      {/* backdrop to match the hero */}
      <div className="pointer-events-none absolute inset-0" aria-hidden>
        <div className="hero-grid absolute inset-0" />
        <div
          className="absolute -right-32 -top-40 h-[560px] w-[560px] rounded-full blur-[70px] opacity-40"
          style={{ background: "radial-gradient(circle, #49559f, transparent 65%)" }}
        />
        <div
          className="absolute -bottom-44 -left-36 h-[480px] w-[480px] rounded-full blur-[70px] opacity-35"
          style={{ background: "radial-gradient(circle, #6d79b2, transparent 65%)" }}
        />
      </div>

      <div className="container relative z-10 min-h-[100svh] pb-20 pt-8">
        {/* top bar */}
        <motion.div
          initial={{ opacity: 0, y: -14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex items-center justify-between"
        >
          <Link to="/" aria-label="Back to the Automation Hub">
            <img src="/logo-white.svg" alt="Wahha Design" className="h-8 w-auto md:h-9" />
          </Link>
          <Link
            to="/"
            className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.07] px-4 py-2 text-[12.5px] font-bold uppercase tracking-[0.14em] text-white/80 transition-colors hover:bg-white/[0.14] hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to hub
          </Link>
        </motion.div>

        {/* heading + view toggle */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mt-14 flex flex-wrap items-end justify-between gap-6"
        >
          <div>
            <p className="text-[11.5px] font-bold uppercase tracking-[0.3em] text-brand-orange">
              Automation Hub
            </p>
            <h1 className="mt-2 text-4xl font-extrabold tracking-tight sm:text-5xl">History</h1>
            <p className="mt-3 max-w-xl text-lg text-white/70">
              Past and currently running audits across your automations.
            </p>
          </div>

          {/* view switch */}
          <div
            role="tablist"
            aria-label="History view"
            className="inline-flex rounded-full border border-white/15 bg-white/[0.06] p-1"
          >
            <button
              type="button"
              role="tab"
              aria-selected={view === "list"}
              onClick={() => setView("list")}
              className={[
                "inline-flex items-center gap-2 rounded-full px-4 py-2 text-[12px] font-bold uppercase tracking-[0.14em] transition-colors",
                view === "list" ? "bg-white/15 text-white" : "text-white/50 hover:text-white/80",
              ].join(" ")}
            >
              <LayoutList className="h-4 w-4" />
              List
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={view === "table"}
              onClick={() => setView("table")}
              className={[
                "inline-flex items-center gap-2 rounded-full px-4 py-2 text-[12px] font-bold uppercase tracking-[0.14em] transition-colors",
                view === "table" ? "bg-white/15 text-white" : "text-white/50 hover:text-white/80",
              ].join(" ")}
            >
              <Table2 className="h-4 w-4" />
              Table
            </button>
          </div>
        </motion.div>

        {/* search + filters */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.18 }}
          className="mt-8 flex flex-wrap items-center gap-3"
        >
          <label className="relative min-w-[220px] flex-1 sm:max-w-sm">
            <Search
              className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-white/40"
              aria-hidden
            />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search audits…"
              aria-label="Search audits"
              className="w-full rounded-full border border-white/15 bg-white/[0.06] py-2.5 pl-11 pr-4 text-[13.5px] font-medium text-white placeholder:text-white/35 outline-none transition-colors focus:border-white/35 focus:bg-white/[0.09]"
            />
          </label>

          <FilterSelect
            ariaLabel="Filter by audit type"
            value={typeFilter}
            onChange={setTypeFilter}
            options={[
              { value: "all", label: "All types" },
              ...tools.map((t) => ({ value: t.id, label: t.name })),
            ]}
          />

          <FilterSelect
            ariaLabel="Filter by status"
            value={statusFilter}
            onChange={(v) => setStatusFilter(v as "all" | AuditStatus)}
            options={[
              { value: "all", label: "All statuses" },
              { value: "running", label: "Running" },
              { value: "completed", label: "Completed" },
              { value: "partial", label: "Partial" },
              { value: "failed", label: "Failed" },
            ]}
          />
        </motion.div>

        {loadState === "loading" ? (
          <div className="mt-16 flex items-center justify-center gap-3 text-white/55">
            <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
            <span className="text-sm">Loading audits…</span>
          </div>
        ) : loadState === "error" ? (
          <p className="mt-16 max-w-xl text-white/55">
            Couldn&apos;t load audit history. Check that the audit services are reachable, then
            reload.
          </p>
        ) : view === "list" ? (
          <>
            {/* running now */}
            {running.length > 0 && (
              <motion.section
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.22 }}
                className="mt-12"
                aria-label="Currently running audits"
              >
                <h2 className="text-[12.5px] font-bold uppercase tracking-[0.22em] text-white/55">
                  Running now
                </h2>
                <div className="mt-4 space-y-3">
                  {running.map((a) => (
                    <AuditRow key={a.id} audit={a} onReportUnavailable={reportUnavailable} />
                  ))}
                </div>
              </motion.section>
            )}

            {/* past */}
            <motion.section
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.32 }}
              className="mt-12"
              aria-label="Past audits"
            >
              <h2 className="text-[12.5px] font-bold uppercase tracking-[0.22em] text-white/55">
                Past audits
              </h2>
              {past.length > 0 ? (
                <div className="mt-4 space-y-3">
                  {past.map((a) => (
                    <AuditRow key={a.id} audit={a} onReportUnavailable={reportUnavailable} />
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-white/50">
                  {isFiltered
                    ? "No audits match your search or filters."
                    : "No audits have run yet."}
                </p>
              )}
            </motion.section>
          </>
        ) : (
          /* table view — Timestamp · Business · Status · Audit Type · Download Report */
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mt-12"
            aria-label="Audit history table"
          >
            <div className="overflow-x-auto rounded-2xl border border-white/12 bg-white/[0.05] backdrop-blur-sm">
              <table className="w-full min-w-[760px] border-collapse text-left">
                <thead>
                  <tr className="border-b border-white/12">
                    <Th>Timestamp</Th>
                    <Th>Business</Th>
                    <Th>Status</Th>
                    <Th>Audit Type</Th>
                    <Th className="text-right">Download Report</Th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-5 py-10 text-center text-[14px] text-white/45">
                        {isFiltered
                          ? "No audits match your search or filters."
                          : "No audits have run yet."}
                      </td>
                    </tr>
                  )}
                  {filtered.map((a) => (
                    <tr
                      key={a.id}
                      className="border-b border-white/[0.07] transition-colors last:border-b-0 hover:bg-white/[0.04]"
                    >
                      <td className="px-5 py-4 text-[13px] font-medium text-white/65">
                        {a.startedAt}
                      </td>
                      <td className="px-5 py-4 text-[14px] font-bold text-white">{a.business}</td>
                      <td className="px-5 py-4">
                        <StatusChip status={a.status} percent={a.progressPercent} />
                      </td>
                      <td className="px-5 py-4 text-[13.5px] font-bold text-white/85">
                        {toolName(a.toolId)}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <DownloadReport
                          available={a.status === "completed" || a.status === "partial"}
                          reportUrl={a.reportUrl}
                          pending={a.reportPending}
                          onUnavailable={reportUnavailable}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.section>
        )}
      </div>
      <ReportToast message={toast} />
    </div>
  );
}

/**
 * Themed dropdown (native <select> popups are OS-styled and can't be themed).
 * Pill trigger + glass navy panel, matching the platform.
 */
function FilterSelect({
  value,
  onChange,
  options,
  ariaLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  ariaLabel: string;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = options.find((o) => o.value === value) ?? options[0];

  // close on outside click / Escape
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className={[
          "inline-flex items-center gap-2.5 rounded-full border px-4 py-2.5 text-[12.5px] font-bold uppercase tracking-[0.1em] transition-colors",
          open
            ? "border-white/35 bg-white/[0.12] text-white"
            : "border-white/15 bg-white/[0.06] text-white/80 hover:bg-white/[0.1] hover:text-white",
        ].join(" ")}
      >
        {selected.label}
        <ChevronDown
          className={`h-4 w-4 text-white/50 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          aria-hidden
        />
      </button>

      {/* always mounted; CSS-only open/close so a closed panel can never
          linger invisibly and block clicks */}
      <ul
        role="listbox"
        aria-label={ariaLabel}
        aria-hidden={!open}
        className={[
          "absolute left-0 top-[calc(100%+8px)] z-30 min-w-full origin-top overflow-hidden rounded-2xl border border-white/15 bg-[#141a45]/95 py-1.5 shadow-[0_24px_60px_-16px_rgba(0,0,0,0.7)] backdrop-blur-xl transition-[opacity,transform] duration-150 ease-out",
          open
            ? "visible translate-y-0 scale-100 opacity-100"
            : "pointer-events-none invisible -translate-y-1.5 scale-95 opacity-0",
        ].join(" ")}
      >
        {options.map((o) => {
          const isSelected = o.value === value;
          return (
            <li key={o.value}>
              <button
                type="button"
                role="option"
                aria-selected={isSelected}
                onClick={() => {
                  onChange(o.value);
                  setOpen(false);
                }}
                className={[
                  "flex w-full items-center justify-between gap-6 whitespace-nowrap px-4 py-2.5 text-left text-[13px] font-semibold transition-colors",
                  isSelected
                    ? "text-white"
                    : "text-white/65 hover:bg-white/[0.08] hover:text-white",
                ].join(" ")}
              >
                {o.label}
                {isSelected && <Check className="h-4 w-4 text-brand-orange" aria-hidden />}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Th({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <th
      className={`px-5 py-4 text-[11px] font-bold uppercase tracking-[0.2em] text-white/45 ${className}`}
    >
      {children}
    </th>
  );
}

function StatusChip({ status, percent }: { status: AuditRecord["status"]; percent?: number }) {
  if (status === "running")
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-sky/15 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.12em] text-brand-sky">
        <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
        {typeof percent === "number" ? `${Math.round(percent)}%` : "Running"}
      </span>
    );
  if (status === "completed")
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-teal/15 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.12em] text-brand-teal">
        <CheckCircle2 className="h-3 w-3" aria-hidden />
        Done
      </span>
    );
  if (status === "partial")
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-orange/15 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.12em] text-brand-orange">
        <AlertTriangle className="h-3 w-3" aria-hidden />
        Partial
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-red-400/15 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.12em] text-red-300">
      <XCircle className="h-3 w-3" aria-hidden />
      Failed
    </span>
  );
}

function AuditRow({
  audit,
  onReportUnavailable,
}: {
  audit: AuditRecord;
  onReportUnavailable: () => void;
}) {
  const tool = tools.find((t) => t.id === audit.toolId);
  if (!tool) return null;
  const Icon = tool.icon;

  return (
    // Vertical stack, not one flex row: the failure reason below needs a line of
    // its own. As a `w-full` child of a `sm:flex-nowrap` row it could not wrap, so
    // it competed for the single line and crushed every sibling — the business
    // name collapsed to one word per line and overlapped the timestamp.
    <div className="rounded-2xl border border-white/12 bg-white/[0.05] p-4 backdrop-blur-sm sm:px-5">
      <div className="flex flex-wrap items-center gap-4 sm:flex-nowrap sm:gap-5">
        {/* tool identity */}
        <span
          className="grid h-11 w-11 shrink-0 place-items-center rounded-xl text-white"
          style={{ background: `linear-gradient(135deg, ${tool.from}, ${tool.to})` }}
          aria-hidden
        >
          <Icon className="h-5 w-5" />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
            <span className="text-[15px] font-bold text-white">{audit.business}</span>
            <span className="whitespace-nowrap text-[12px] font-bold uppercase tracking-[0.12em] text-white/45">
              {tool.name}
            </span>
          </div>
          <p className="mt-0.5 truncate text-[13px] text-white/55">{audit.businessUrl}</p>
          {audit.status === "running" && (
            <div className="mt-3 max-w-xl">
              <div className="flex items-center justify-between gap-3 text-[11px] font-semibold text-white/55">
                <span className="truncate">
                  {audit.progressStage || "Waiting for worker progress"}
                </span>
                <span className="shrink-0">{Math.round(audit.progressPercent ?? 0)}%</span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-brand-sky transition-[width] duration-500"
                  style={{ width: `${Math.max(0, Math.min(100, audit.progressPercent ?? 0))}%` }}
                />
              </div>
              {audit.progressUpdatedAt && (
                <p className="mt-1 text-[10.5px] text-white/35">
                  Worker update: {formatTimestamp(audit.progressUpdatedAt)}
                </p>
              )}
            </div>
          )}
        </div>

        {/* timing — whitespace-nowrap so a long timestamp cannot break mid-value */}
        <div className="shrink-0 text-right">
          <p className="whitespace-nowrap text-[13px] font-semibold text-white/70">
            {audit.startedAt}
          </p>
          {audit.duration && <p className="mt-0.5 text-[12px] text-white/40">{audit.duration}</p>}
        </div>

        {/* successful and partial audits expose their available client PDF. */}
        <div className="w-[132px] shrink-0 text-right">
          {audit.status === "completed" || audit.status === "partial" ? (
            <DownloadReport
              available
              reportUrl={audit.reportUrl}
              pending={audit.reportPending}
              onUnavailable={onReportUnavailable}
            />
          ) : requiresQueryApproval({ status: audit.status, awaitingReview: audit.awaitingReview }) ? (
            /* The run is blocked on this person, so the row offers the way back
               into it rather than a progress chip that will never advance. The
               id travels in the URL — that is what makes the run addressable
               from here at all. */
            <Link
              to={`/automations/${audit.toolId}?run=${encodeURIComponent(audit.id)}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-brand-orange/70 bg-brand-orange/15 px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-brand-orange transition-colors hover:bg-brand-orange hover:text-white"
            >
              {auditActionLabel({ status: audit.status, awaitingReview: audit.awaitingReview })}
              <ArrowUpRight className="h-3.5 w-3.5" aria-hidden />
            </Link>
          ) : (
            <StatusChip status={audit.status} percent={audit.progressPercent} />
          )}
        </div>
      </div>

      {/* Own line, outside the row above — see the note on the wrapper. */}
      {audit.status === "failed" && audit.failureReason && (
        <p className="mt-3 text-[12px] text-red-200/80 sm:pl-16">{audit.failureReason}</p>
      )}
    </div>
  );
}

function DownloadReport({
  available,
  reportUrl,
  pending = false,
  onUnavailable,
}: {
  available: boolean;
  reportUrl?: string;
  /** Run finished, PDF still rendering. Not the same as "there is no report". */
  pending?: boolean;
  onUnavailable: () => void;
}) {
  const enabledClass =
    "inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/[0.07] px-4 py-2 text-[12px] font-bold uppercase tracking-[0.12em] text-white/85 transition-colors hover:bg-white/[0.15] hover:text-white";
  const disabledClass =
    "inline-flex cursor-not-allowed items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-[12px] font-bold uppercase tracking-[0.12em] text-white/30";
  if (available && reportUrl) {
    return (
      <a href={reportUrl} target="_blank" rel="noopener noreferrer" className={enabledClass}>
        <Download className="h-3.5 w-3.5" />
        Download
      </a>
    );
  }
  // Ordered after the link branch so a URL always wins over a stale flag.
  if (available && pending) {
    return (
      <span aria-live="polite" className={disabledClass}>
        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
        Preparing
      </span>
    );
  }
  if (available) {
    return (
      <button type="button" onClick={onUnavailable} className={enabledClass}>
        <Download className="h-3.5 w-3.5" />
        Download
      </button>
    );
  }
  return (
    <span aria-disabled className={disabledClass}>
      <Download className="h-3.5 w-3.5" />
      Download
    </span>
  );
}

function ReportToast({ message }: { message: string | null }) {
  return (
    <AnimatePresence>
      {message && (
        <motion.div
          key="report-toast"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 24 }}
          transition={{ duration: 0.25 }}
          role="status"
          aria-live="polite"
          className="fixed bottom-6 left-1/2 z-[90] flex max-w-md -translate-x-1/2 items-start gap-2.5 rounded-2xl border border-red-400/30 bg-[#141a45]/95 px-4 py-3 text-[13px] font-medium text-white shadow-[0_24px_60px_-16px_rgba(0,0,0,0.7)] backdrop-blur-xl"
        >
          <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-300" aria-hidden />
          <span>{message}</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
