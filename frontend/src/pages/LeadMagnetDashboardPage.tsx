import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowUpDown,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Cpu,
  Download,
  ExternalLink,
  Flame,
  Globe,
  CalendarClock,
  Copy,
  Info,
  MessageSquareQuote,
  Loader2,
  Plus,
  RotateCw,
  Search,
  StickyNote,
  Trash2,
  Users,
  UsersRound,
  X,
} from "lucide-react";
import {
  createLead,
  deleteLead,
  listLeads,
  pollFullAudit,
  startFullAudit,
  updateLead,
  FULL_AUDIT_IDENTITY_FIELDS,
  isFullAuditRunning,
  type FullAuditIdentity,
  type Lead,
  type LeadDetails,
  type LeadType,
} from "@/services/api/leadMagnet";
import { ComboboxField } from "@/components/ui/field-menu";
import { Tooltip } from "@/components/ui/tooltip";
import { useLocationSuggestions } from "@/hooks/useLocationSuggestions";
import {
  buildLeadRows,
  normalizeDomain,
  rowMatchesQuery,
  type LeadFlag,
  type LeadRow,
} from "@/data/leadFlags";

/* ── Conversion sources ──────────────────────────────────────────────
   Maps each Lead Magnet funnel to its display chip. Labels match the funnel
   pages' own names (/technical-seo, /onpage-seo, /ai-seo) so a row names the
   page the lead came from. Colors stay on the brand ramp so every source reads
   distinctly on the navy surface. One map drives all three surfaces: the table
   chips, the source filter, and the modal's Audit Type picker. */
/* Chips sit on the light panel, so they read as white pills with a hairline
   and a tinted label — the translucent fills used elsewhere in the hub would
   disappear against near-white. */
const SOURCE_META: Record<LeadType, { label: string; chip: string }> = {
  technical_seo: {
    label: "Technical SEO",
    chip: "border-[#185470]/30 bg-white text-[#185470]",
  },
  onpage_seo: {
    label: "On-Page SEO",
    chip: "border-[#16645a]/30 bg-white text-[#16645a]",
  },
  ai_seo: {
    label: "AI Crawlability Readiness Checker",
    chip: "border-brand-primary/20 bg-white text-brand-primary",
  },
};

const SOURCE_OPTIONS = [
  { value: "all", label: "All sources" },
  ...Object.entries(SOURCE_META).map(([value, meta]) => ({ value, label: meta.label })),
];

/** Services a manually logged lead can be audited against — one per funnel. */
const AUDIT_TYPE_OPTIONS: Array<{ value: LeadType; label: string }> = Object.entries(
  SOURCE_META,
).map(([value, meta]) => ({ value: value as LeadType, label: meta.label }));

/**
 * How often the console re-reads the lead pipeline. Leads arrive at human pace,
 * so this is about how quickly a just-submitted audit shows up rather than
 * throughput: 5s reads as instant to someone watching, and the read is a small
 * JSON list. Polling (not SSE) is deliberate — see the "How the dashboard gets
 * lead data" section of leadmagnet_central_dashboard_integration.md.
 */
const LEAD_POLL_INTERVAL_MS = 5_000;

type SortBy = "date" | "score" | "name";

function formatTimestamp(iso: string): string {
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

/**
 * The booked call, in the reader's own timezone.
 *
 * Rendered in local time on purpose: whoever is working the pipeline needs to
 * know when to turn up, and the stored instant is absolute. The zone the
 * prospect booked in is shown separately, as context rather than as the time.
 */
function formatMeetingSlot(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/**
 * Did they book under details other than the ones they submitted?
 *
 * Mirrors bookingDiffersFromLead in the server's meeting-match.mjs. Compared
 * case-insensitively, and only where both sides have a value, so a booking that
 * simply omitted a name is not reported as a discrepancy.
 */
function bookingIdentityDiffers(lead: Lead): boolean {
  const meeting = lead.meeting;
  if (!meeting) return false;
  const same = (a?: string, b?: string) =>
    !a || !b || a.trim().toLowerCase() === b.trim().toLowerCase();
  return !same(meeting.bookedEmail, lead.email) || !same(meeting.bookedName, lead.name);
}

function getTimeSince(iso: string | undefined, nowMs: number): string {
  if (!iso) return "Just now";
  const diffMs = nowMs - new Date(iso).getTime();
  if (diffMs < 60_000) return "Just now";
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

/**
 * What the operator sees and quotes: lead_1, lead_2, … from the server's
 * sequence rather than the opaque primary key. Falls back to the raw id for a
 * record predating the sequence, so nothing ever renders blank.
 */
const leadDisplayId = (lead: Lead) => (lead.seq ? `lead_${lead.seq}` : lead.id);

/** Traffic-light tone for a 0–100 site score, tuned for the dark surface. */
/* Re-picked for the light panel. The dark-mode pastels (red-300, brand-teal)
   wash out to near-invisible on near-white, so these are the darker ends of
   the same hues. */
function scoreTone(score: number): { dot: string; text: string } {
  if (score < 60) return { dot: "bg-console-bad-dot", text: "text-console-bad" };
  if (score < 80) return { dot: "bg-brand-orange", text: "text-console-warn" };
  return { dot: "bg-console-good-dot", text: "text-console-good" };
}

/** Score → grade + check counts, mirroring the Lead Magnet's manual-entry rules. */
function detailsFromScore(score: number) {
  if (score < 60) return { score, grade: "D", passed: 4, warnings: 9, critical: 6 };
  if (score < 80) return { score, grade: "C+", passed: 7, warnings: 6, critical: 3 };
  if (score >= 90) return { score, grade: "A", passed: 15, warnings: 2, critical: 0 };
  return { score, grade: "B", passed: 10, warnings: 4, critical: 1 };
}

/**
 * Score each Lead Magnet funnel reports for a first crawl — the same values its
 * own pages save today. Replaced by the real audit response once the Lead Magnet
 * API is wired up.
 */
const AUDIT_BASELINE: Record<LeadType, number> = {
  technical_seo: 74,
  onpage_seo: 55,
  ai_seo: 88,
};

/* normalizeDomain now lives in data/leadFlags — the dedup grouping and this
   page have to agree on what "the same domain" means, and two copies of that
   rule would eventually disagree. */

/** Prose for a flag. Kept here, not in leadFlags, so SOURCE_META stays the one
 *  place audit-type labels are spelled out. */
function flagHeadline(flag: LeadFlag): string {
  if (flag.kind === "repeat") {
    return `${flag.count} submissions of the same audit`;
  }
  return `${flag.host} audited by ${flag.people} different people`;
}

function flagDetail(flag: LeadFlag): string {
  if (flag.kind === "repeat") {
    return `This person submitted ${SOURCE_META[flag.type].label} ${flag.count} times.`;
  }
  return (
    `${flag.audits} audits have been run on ${flag.host} by ${flag.people} different ` +
    `email addresses.`
  );
}

/**
 * Store an absolute URL even when a bare host was typed, so the row's "Visit"
 * link doesn't resolve against the dashboard's own origin.
 */
function toStoredUrl(url: string): string | undefined {
  const trimmed = url.trim();
  if (!trimmed) return undefined;
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

/**
 * Most recent scored lead for this domain on this service. Leads are stored
 * newest-first, so the first hit is the latest audit.
 */
function findPriorAudit(leads: Lead[], domainUrl: string, type: LeadType): Lead | undefined {
  const host = normalizeDomain(domainUrl);
  if (!host) return undefined;
  return leads.find(
    (lead) =>
      lead.type === type &&
      typeof lead.details?.score === "number" &&
      normalizeDomain(lead.domainUrl ?? "") === host,
  );
}

const EMPTY_NEW_LEAD = {
  name: "",
  email: "",
  phone: "",
  domainUrl: "",
  type: "technical_seo" as LeadType,
};

/* Deleting from the table acts on the whole row. When a row is a collapsed
   repeat that means several stored leads, so the dialog names the count —
   removing only the newest would silently promote an older submission into
   the row and read as a failed delete. Individual submissions can still be
   removed one at a time from the expanded detail. */
type ConfirmState =
  | { kind: "delete"; row: LeadRow }
  | { kind: "delete-one"; lead: Lead }
  | null;

/**
 * How often the console asks the server where a run is.
 *
 * 3s rather than the old 2s because these runs last minutes to hours, not the
 * ~50s the previous snapshot took — and because each poll now does real work
 * upstream (it is the call that records a finished run), so it is not free.
 */
const FULL_AUDIT_POLL_MS = 3000;

/* How often an UNWATCHED in-flight run is checked. Much slower than the
   console's own 3s tick: this exists only to notice that a run ended, not to
   animate a progress bar, and every check is a real call through to a paid
   audit backend. */
const FULL_AUDIT_RECONCILE_MS = 15_000;

/**
 * The server's own explanation of a failure, when it gave one.
 *
 * These messages are worth surfacing verbatim: "This lead has no usable website
 * URL to audit" and "On-Page SEO is at its run limit" are both actionable, and
 * collapsing them into one generic string hides which of the two happened.
 */
/**
 * Did the server refuse this start because it still needs identity?
 *
 * The server owns the real requirement — FULL_AUDIT_IDENTITY_FIELDS here is
 * documented as a UI hint, not the rule — so a 422 `identity_required` is the
 * authoritative answer, and the right response is to ask for the fields rather
 * than show an error the operator cannot act on. Without this, any drift between
 * the two lists becomes a dead end.
 */
function identityRequired(error: unknown): boolean {
  const response = (error as { response?: { status?: number; data?: { error?: unknown } } })
    ?.response;
  return response?.status === 422 && response?.data?.error === "identity_required";
}

function fullAuditErrorMessage(error: unknown): string {
  const message = (error as { response?: { data?: { message?: unknown } } })?.response?.data
    ?.message;
  if (typeof message === "string" && message.trim()) return message.trim();
  return "The audit service could not be reached.";
}

type LoadState = "loading" | "ready" | "error";

/**
 * /leadmagnetdashboard — the Lead Magnet funnels' lead console. Rows come from
 * the dashboard server's interim lead store via @/services/api/leadMagnet
 * (session-gated, same-origin); the funnel site posts captures into the same
 * store, so a prospect's submission lands here. The audit runs themselves are
 * still the 5-second simulation until the real per-service backends exist.
 *
 * Deliberately NOT gated on the Lead Magnet tile's enable flag: that flag
 * controls what the automations fan offers, and this page stays reachable for
 * any signed-in account while the tile still reads "Coming soon".
 */
export default function LeadMagnetDashboardPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<SortBy>("date");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [exactTimeId, setExactTimeId] = useState<string | null>(null);

  // Manual lead entry modal
  const [addOpen, setAddOpen] = useState(false);
  const [newLead, setNewLead] = useState(EMPTY_NEW_LEAD);
  /**
   * Result of an audit run started from inside the modal. Held separately from
   * any prior audit found in storage so a fresh run always wins, and cleared
   * whenever the domain or service changes (a different target = a different audit).
   */
  const [freshAudit, setFreshAudit] = useState<{ score: number; rerun: boolean } | null>(null);
  const [modalAuditProgress, setModalAuditProgress] = useState(0);
  const [modalAuditRunning, setModalAuditRunning] = useState(false);
  const modalAuditTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Themed replacement for window.confirm on lead deletion
  const [confirm, setConfirm] = useState<ConfirmState>(null);

  /**
   * Unsaved note text, keyed by lead id. Held apart from `leads` on purpose:
   * the 5s poll replaces that array wholesale, and a note being typed must
   * survive it. A lead with no entry here simply shows its stored note.
   */
  const [noteDrafts, setNoteDrafts] = useState<Record<string, string>>({});
  const [savingNoteId, setSavingNoteId] = useState<string | null>(null);

  /* Full-audit console. `error` is a real state, not a flavour of success: the
     previous version's catch block set "success", so an audit that never ran
     still rendered "Full Audit Completed". */
  const [auditLead, setAuditLead] = useState<Lead | null>(null);
  const [auditProgress, setAuditProgress] = useState(0);
  const [auditLogs, setAuditLogs] = useState<string[]>([]);
  const [auditStatus, setAuditStatus] = useState<"idle" | "running" | "success" | "error">("idle");
  /* Where the finished run can be read: /automations/<toolId>?run=<auditId>,
     which the existing AuditPanel resumes. The console therefore never has to
     fetch or parse a report — those are ~2MB documents the lead store is
     explicitly designed never to hold. */
  const [auditToolId, setAuditToolId] = useState<string | null>(null);
  const [auditRunId, setAuditRunId] = useState<string | null>(null);
  /* Identifies the watch this tab is running, so closing the console stops its
     polling loop. Only the WATCHING stops — the run itself keeps going upstream,
     and whoever polls next still records the result. */
  const auditWatchRef = useRef<{ leadId: string; cancelled: boolean } | null>(null);
  /* The watch as RENDER state. auditWatchRef is a ref, so it cannot drive the
     row's Running control; and the lead record only learns about the run one
     refreshLeads() later. Without this the button reads "Run full audit" for the
     first second of every run — the exact window an impatient second click
     lands in. */
  const [watchingLeadId, setWatchingLeadId] = useState<string | null>(null);

  /* The lead whose full audit is waiting on identity fields, and what has been
     typed so far. Only AI SEO ever gets here — see FULL_AUDIT_IDENTITY_FIELDS.

     Remembered per lead for THIS SESSION only, deliberately. There is no column
     to persist it to, and inventing one would store a guess as though it were a
     fact; re-asking on a later visit is the honest behaviour. Within a session
     it saves retyping when a run fails and is retried. */
  const [identityLead, setIdentityLead] = useState<Lead | null>(null);
  const identityMemory = useRef<Record<string, FullAuditIdentity>>({});

  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Re-render every 10s so "Just now" / "3m ago" labels stay fresh.
  const [nowMs, setNowMs] = useState(() => Date.now());

  const [loadState, setLoadState] = useState<LoadState>("loading");
  /** Monotonic load counter — the most recently STARTED read wins (see below). */
  const loadSeq = useRef(0);
  const pollInFlight = useRef(false);

  /**
   * Pull the pipeline from the server.
   *
   * `background: true` marks the interval poll, which differs in two ways:
   * it never flips the table to the error surface (a transient blip must not
   * blank a working table — the next tick recovers), and it skips itself while
   * a previous poll is still in flight so slow responses can't stack up.
   *
   * Responses are applied last-started-wins. Without that, a slow poll begun
   * before a delete could land after it and resurrect the removed row.
   */
  const refreshLeads = useCallback(async ({ background = false } = {}) => {
    if (background && pollInFlight.current) return;
    const seq = ++loadSeq.current;
    if (background) pollInFlight.current = true;
    try {
      const next = await listLeads();
      if (seq !== loadSeq.current) return; // a newer read already landed
      setLeads(next);
      setLoadState("ready");
    } catch {
      if (seq !== loadSeq.current) return;
      if (!background) setLoadState("error");
    } finally {
      if (background) pollInFlight.current = false;
    }
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
    void refreshLeads();
    const tick = window.setInterval(() => setNowMs(Date.now()), 10_000);
    return () => {
      window.clearInterval(tick);
      // The full-audit watch is an async loop, not an interval — leaving the
      // page has to flip its flag or it keeps polling against an unmounted
      // component. The upstream run is unaffected; only the watching stops.
      if (auditWatchRef.current) auditWatchRef.current.cancelled = true;
      if (modalAuditTimer.current) clearInterval(modalAuditTimer.current);
      if (toastTimer.current) clearTimeout(toastTimer.current);
    };
  }, [refreshLeads]);

  /* ── Live pipeline ────────────────────────────────────────────────
     Leads captured on the funnel site land here on their own, so nobody has to
     reload to see a submission that just happened. Paused while the tab is
     hidden — a background tab needs no traffic — and refreshed the moment it
     becomes visible again, which is the common case: you submit an audit in
     the funnel tab and switch straight back here. */
  useEffect(() => {
    const poll = () => {
      if (document.hidden) return;
      void refreshLeads({ background: true });
    };
    const timer = window.setInterval(poll, LEAD_POLL_INTERVAL_MS);
    const onVisibilityChange = () => {
      if (!document.hidden) poll();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [refreshLeads]);

  /* ── Reconcile runs nobody is watching ────────────────────────────
     A lead's auditStatus only reaches a terminal value when something calls the
     status route — GET /full-audit is the sole writer of one. The console's poll
     loop does that while it is watching, but a run survives a reload and a
     reload leaves nothing watching it, so without this sweep the row would show
     "Running" forever for an audit that finished minutes ago.

     Deliberately narrow: only leads the lead list already says are in flight,
     never the one the console is watching (that would double the upstream
     traffic for no gain), and paused on a hidden tab. Keyed on the SET of
     in-flight ids rather than on `leads`, or the 5s list poll would restart the
     interval and re-fire this on every tick. */
  const inFlightAuditIds = useMemo(
    () =>
      leads
        .filter((lead) => isFullAuditRunning(lead))
        .map((lead) => lead.id)
        .sort()
        .join(","),
    [leads],
  );

  useEffect(() => {
    const ids = inFlightAuditIds ? inFlightAuditIds.split(",") : [];
    const unwatched = ids.filter((id) => id !== watchingLeadId);
    if (unwatched.length === 0) return;

    let cancelled = false;
    const sweep = async () => {
      if (document.hidden) return;
      for (const id of unwatched) {
        if (cancelled) return;
        try {
          const tick = await pollFullAudit(id);
          // "unknown" is the service not answering this time, not the run
          // ending — the next sweep asks again. Anything else terminal has just
          // been written onto the lead, so pull the list to pick it up.
          if (!cancelled && tick.state !== "running" && tick.state !== "unknown") {
            void refreshLeads({ background: true });
          }
        } catch {
          // Transient. The lead keeps its in-flight status and the next sweep
          // retries; a genuinely dead run is written off upstream by isStaleRun.
        }
      }
    };

    void sweep();
    const timer = window.setInterval(() => void sweep(), FULL_AUDIT_RECONCILE_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [inFlightAuditIds, watchingLeadId, refreshLeads]);

  const modalOpen = addOpen || confirm !== null || auditLead !== null;
  useEffect(() => {
    document.body.style.overflow = modalOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [modalOpen]);

  const showToast = (message: string) => {
    setToast(message);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 3200);
  };

  /* ── Full audit ────────────────────────────────────────────────────
     Starts the deep audit for the lead's OWN product — a Technical SEO lead goes
     to the Technical SEO service, an On-Page lead to On-Page.

     WHAT THIS REPLACES. The previous version called the Lead Magnet backend for
     every lead whatever its funnel, and logged "Technical SEO snapshot" while
     doing it. That deployment runs FULL_AUDIT_ENABLED=false — it is the ~50s
     snapshot the prospect already got for free, so "Run full audit" re-ran the
     free audit under a different name and no lead ever received a full one.

     WHY THERE IS NO DEADLINE. The old loop gave up after 180s. A real full audit
     is budgeted in hours (Technical SEO's job_timeout is 86400s), so that timer
     would have failed essentially every genuine run. It is gone: the server's
     poll route records a finished run as a side effect of being called, so this
     loop is a VIEWER, not the thing responsible for the result. Closing the
     console — or the tab, or the laptop — costs update latency and nothing else. */
  /**
   * Entry point for the "Run full audit" button.
   *
   * Products whose payload a lead row already satisfies start immediately.
   * AI SEO needs a country and state that no lead carries, so it asks first —
   * and asks BEFORE submitting rather than after, because the alternative is
   * opening a progress console and replacing it with an error a second later.
   */
  const requestFullAudit = (lead: Lead) => {
    /* This tab is already watching this lead: just show the console again, with
       the logs and progress it has accumulated. Re-running the start path would
       throw that history away and open an empty console on the same run. */
    const watch = auditWatchRef.current;
    if (watch && watch.leadId === lead.id && !watch.cancelled) {
      setAuditLead(lead);
      return;
    }

    /* A run is going but nothing here is watching it — another tab started it,
       or this one was reloaded. ATTACH rather than start: the server dedupes
       (hasRunInFlight -> `attached`), so the identity modal would be asking for
       a country and state that the in-flight run has already been given. */
    if (isFullAuditRunning(lead)) {
      void runDeepDiveAudit(lead, {}, { attach: true });
      return;
    }

    if ((FULL_AUDIT_IDENTITY_FIELDS[lead.type] ?? []).length === 0) {
      void runDeepDiveAudit(lead, {});
      return;
    }
    setIdentityLead(lead);
  };

  const runDeepDiveAudit = async (
    lead: Lead,
    identity: FullAuditIdentity,
    { attach = false }: { attach?: boolean } = {},
  ) => {
    /* One watch at a time — the console has one set of logs and one progress
       bar. Cancelling the outgoing loop explicitly matters now that closing the
       console no longer does it: otherwise starting a second lead's audit would
       leave the first loop polling forever and writing into the new run's UI. */
    if (auditWatchRef.current) auditWatchRef.current.cancelled = true;
    const watch = { leadId: lead.id, cancelled: false };
    auditWatchRef.current = watch;
    setWatchingLeadId(lead.id);
    setAuditLead(lead);
    setAuditStatus("running");
    setAuditProgress(0);
    setAuditToolId(null);
    setAuditRunId(null);

    const stamp = () =>
      new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    const log = (level: string, message: string) =>
      setAuditLogs((prev) => [...prev, `[${stamp()}] [${level}] ${message}`]);

    const label = SOURCE_META[lead.type].label;
    setAuditLogs([
      attach
        ? `[${stamp()}] [INFO] Re-attaching to the full ${label} audit already running for ${lead.domainUrl ?? "this lead"}...`
        : `[${stamp()}] [INFO] Submitting ${lead.domainUrl ?? "this lead"} for a full ${label} audit...`,
    ]);

    try {
      const started = await startFullAudit(lead.id, identity);
      if (watch.cancelled) return;
      setAuditRunId(started.auditId);
      setAuditToolId(started.toolId);
      log(
        "INFO",
        started.attached
          ? `Already running — watching ${started.auditId}.`
          : `Audit accepted: ${started.auditId}`,
      );
      void refreshLeads();

      let lastStage = "";
      for (;;) {
        await new Promise((resolve) => setTimeout(resolve, FULL_AUDIT_POLL_MS));
        if (watch.cancelled) return;
        const tick = await pollFullAudit(lead.id);
        if (watch.cancelled) return;

        if (tick.state === "unknown") {
          // The service did not answer THIS time. Not the run failing — say so
          // and keep watching, because the next tick can still resolve it.
          if (tick.message) log("INFO", tick.message);
          continue;
        }
        if (tick.state === "idle") {
          log("ERROR", "This run is no longer attached to the lead.");
          setAuditStatus("error");
          return;
        }

        if (typeof tick.percent === "number" && Number.isFinite(tick.percent)) {
          setAuditProgress(Math.max(0, Math.min(100, Math.round(tick.percent))));
        }
        if (tick.stage && tick.stage !== lastStage) {
          lastStage = tick.stage;
          log("INFO", `${tick.stage.replace(/_/g, " ")}...`);
        }
        // A queued run is reported honestly rather than as an animated 0%: on a
        // single-worker deployment it can legitimately sit there for a while.
        if (tick.state === "running") {
          if (tick.auditStatus === "queued" && lastStage !== "queued") {
            lastStage = "queued";
            log("INFO", "Queued — waiting for a free worker.");
          }
          continue;
        }

        void refreshLeads();
        if (tick.state === "completed") {
          setAuditProgress(100);
          log(
            "SUCCESS",
            tick.auditStatus === "completed_partial"
              ? "Audit finished with partial coverage — the report is ready."
              : "Audit complete — the report is ready.",
          );
          setAuditStatus("success");
          showToast(`Full ${label} audit completed for ${lead.name}.`);
        } else {
          log("ERROR", tick.message || `The audit ended as ${tick.auditStatus}.`);
          setAuditStatus("error");
          showToast(`Couldn't complete the audit for ${lead.name}.`);
        }
        return;
      }
    } catch (error) {
      if (watch.cancelled) return;
      // The server's own message is surfaced verbatim where it has one — it is
      // the difference between "this lead has no website URL" and "On-Page is at
      // its run limit", and a generic string would hide both.
      /* The server says it still needs country/state. Ask for them instead of
         reporting a failure: close the console and reopen the intake, which is
         what the operator would have to do by hand anyway. */
      if (identityRequired(error)) {
        setAuditStatus("idle");
        setAuditLead(null);
        setIdentityLead(lead);
        return;
      }
      log("ERROR", fullAuditErrorMessage(error));
      setAuditStatus("error");
      showToast(`Couldn't start the audit for ${lead.name}.`);
    } finally {
      /* Only when THIS watch is still the live one. A newer run may have
         replaced it on its way in (see the cancel at the top), and clearing
         then would blank the control belonging to the run that is still going. */
      if (auditWatchRef.current === watch) {
        auditWatchRef.current = null;
        setWatchingLeadId(null);
      }
    }
  };

  /**
   * Close the console WITHOUT abandoning the run.
   *
   * The dialog promises "you can close this — it keeps going", and until now
   * that was only half true: the upstream run continued, but this handler
   * cancelled the poll loop and dropped every trace of it, so the row fell back
   * to offering "Run full audit" for an audit that was still running and no
   * completion was ever noticed. Closing now only hides — the loop keeps
   * polling, still reconciles the lead when the run ends (the status route is
   * the only thing that writes a terminal auditStatus), still toasts, and
   * re-opening restores the same console with its accumulated log.
   *
   * The watch is torn down in exactly two places, both correct: the loop's own
   * `finally` when the run ends, and the page-unmount cleanup.
   */
  const closeAudit = () => {
    setAuditLead(null);
  };

  /* ── Modal: Lead Magnet audit for the entered domain ──────────────
     A prior audit for this domain+service is read straight from storage; the
     button below runs a fresh one. Both feed the score saved with the lead. */
  const priorAudit = findPriorAudit(leads, newLead.domainUrl, newLead.type);
  const auditScore = freshAudit?.score ?? priorAudit?.details?.score ?? null;
  const hasDomain = normalizeDomain(newLead.domainUrl) !== "";

  /** Clears any fresh result — the target changed, so the old score no longer applies. */
  const resetModalAudit = () => {
    if (modalAuditTimer.current) {
      clearInterval(modalAuditTimer.current);
      modalAuditTimer.current = null;
    }
    setFreshAudit(null);
    setModalAuditRunning(false);
    setModalAuditProgress(0);
  };

  const runModalAudit = (isRerun: boolean) => {
    if (!hasDomain) return;
    if (modalAuditTimer.current) clearInterval(modalAuditTimer.current);
    setModalAuditRunning(true);
    setModalAuditProgress(0);

    const baseline = AUDIT_BASELINE[newLead.type];
    const start = Date.now();
    const duration = 1800;

    modalAuditTimer.current = setInterval(() => {
      const percent = Math.min(Math.round(((Date.now() - start) / duration) * 100), 100);
      setModalAuditProgress(percent);
      if (percent < 100) return;

      if (modalAuditTimer.current) clearInterval(modalAuditTimer.current);
      modalAuditTimer.current = null;
      // A first crawl reports the funnel's baseline. A re-crawl moves a little —
      // slightly optimistic, since fixes may have landed since the last run.
      const score = isRerun
        ? Math.max(35, Math.min(98, baseline + Math.round(Math.random() * 13) - 5))
        : baseline;
      setFreshAudit({ score, rerun: isRerun });
      setModalAuditRunning(false);
    }, 60);
  };

  const handleCreateLead = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLead.name || !newLead.email) return;

    let details: LeadDetails | undefined;
    if (freshAudit) {
      details = detailsFromScore(freshAudit.score);
    } else if (priorAudit) {
      // Carry the prior run's real check counts rather than re-deriving them.
      details = { ...priorAudit.details };
    }
    // No audit yet: the lead is saved unscored and the table offers "Run full audit".

    try {
      await createLead({
        name: newLead.name,
        email: newLead.email,
        phone: newLead.phone || undefined,
        domainUrl: toStoredUrl(newLead.domainUrl),
        type: newLead.type,
        details,
      });
    } catch {
      // Keep the modal open so nothing typed is lost.
      showToast("Couldn't save the lead — check the connection and try again.");
      return;
    }
    await refreshLeads();
    setAddOpen(false);
    setNewLead(EMPTY_NEW_LEAD);
    resetModalAudit();
    showToast("Manual lead logged into the pipeline.");
  };

  const setNoteDraft = (id: string, value: string) =>
    setNoteDrafts((drafts) => ({ ...drafts, [id]: value }));

  /** Drop the draft so the field falls back to whatever the server holds. */
  const discardNoteDraft = (id: string) =>
    setNoteDrafts((drafts) => {
      const next = { ...drafts };
      delete next[id];
      return next;
    });

  const saveNote = async (lead: Lead) => {
    const draft = noteDrafts[lead.id];
    if (draft === undefined) return;
    setSavingNoteId(lead.id);
    try {
      await updateLead(lead.id, { notes: draft });
      discardNoteDraft(lead.id);
      await refreshLeads();
      showToast(draft.trim() ? "Note saved." : "Note cleared.");
    } catch {
      // Keep the draft so nothing typed is lost.
      showToast("Couldn't save the note — try again.");
    } finally {
      setSavingNoteId(null);
    }
  };

  const handleConfirm = async () => {
    if (!confirm) return;
    const targets =
      confirm.kind === "delete" ? confirm.row.submissions.map((s) => s.id) : [confirm.lead.id];
    try {
      // Sequential rather than Promise.all: the store serializes writes, and a
      // partial failure should stop rather than leave an unknown subset gone.
      for (const id of targets) await deleteLead(id);
      showToast(targets.length > 1 ? `${targets.length} submissions removed.` : "Lead removed.");
    } catch {
      showToast("Couldn't delete — try again.");
    }
    setConfirm(null);
    await refreshLeads();
  };

  const handleExportCsv = () => {
    const rows: string[][] = [
      ["ID", "Name", "Email", "Phone", "Domain", "Type", "Timestamp", "Score", "Grade", "Notes"],
      ...leads.map((l) => [
        // The id the team sees on screen, so a CSV row can be matched back to
        // the console without translating a UUID.
        leadDisplayId(l),
        l.name,
        l.email,
        l.phone ?? "",
        l.domainUrl ?? "",
        l.type,
        l.timestamp,
        l.details?.score?.toString() ?? "",
        l.details?.grade ?? "",
        l.notes ?? "",
      ]),
    ];
    const csv = rows
      .map((row) => row.map((value) => `"${value.replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `wahha_leads_export_${new Date().toISOString().split("T")[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    showToast("CSV exported for CRM import.");
  };

  const toggleSort = (column: SortBy) => {
    if (sortBy === column) {
      setSortOrder((order) => (order === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(column);
      setSortOrder("desc");
    }
  };

  /* ── Group, filter, sort, stats ───────────────────────────────────
     Grouping runs first and on the unfiltered list: repeat detection has to
     see every submission, and a search that matched only a collapsed
     submission would otherwise drop the row that contains it. */
  const q = query.trim().toLowerCase();
  const rows = useMemo(() => buildLeadRows(leads), [leads]);
  const filteredRows = rows.filter((row) => {
    // A repeat group is single-type by construction, so testing the
    // representative is enough for the type filter.
    if (typeFilter !== "all" && row.lead.type !== typeFilter) return false;
    return rowMatchesQuery(row, q);
  });
  const sortedRows = [...filteredRows].sort((a, b) => {
    let cmp = 0;
    if (sortBy === "date")
      cmp = new Date(a.lead.timestamp).getTime() - new Date(b.lead.timestamp).getTime();
    else if (sortBy === "score") cmp = (a.lead.details?.score ?? 0) - (b.lead.details?.score ?? 0);
    else cmp = a.lead.name.localeCompare(b.lead.name);
    return sortOrder === "asc" ? cmp : -cmp;
  });
  const isFiltered = q !== "" || typeFilter !== "all";

  /* How many captures the collapsing hid, so the table can say so rather than
     leaving a silent gap between "Total leads" and the number of rows. */
  const collapsedCount = leads.length - rows.length;
  const flaggedRowCount = rows.filter((r) => r.flags.length > 0).length;

  const scored = leads.filter((l) => typeof l.details?.score === "number");
  const stats = {
    total: leads.length,
    // Leads whose deep-dive "Run full audit" has actually completed — every
    // stored lead is an audit-funnel lead now, so type can't distinguish them.
    audits: leads.filter((l) => l.details?.scheduler_cron === "FULL_AUDIT_COMPLETED").length,
    avgScore: scored.length
      ? Math.round(scored.reduce((sum, l) => sum + (l.details?.score ?? 0), 0) / scored.length)
      : 0,
  };

  return (
    <div className="bg-hero-leadmagnet relative min-h-[100svh] overflow-hidden text-white">
      {/* backdrop to match the hero — orbs use the Lead Magnet tile's teal ramp */}
      <div className="pointer-events-none absolute inset-0" aria-hidden>
        <div className="hero-grid absolute inset-0" />
        <div
          className="absolute -right-32 -top-40 h-[560px] w-[560px] rounded-full blur-[70px] opacity-40"
          style={{ background: "radial-gradient(circle, #2c7f8f, transparent 65%)" }}
        />
        <div
          className="absolute -bottom-44 -left-36 h-[480px] w-[480px] rounded-full blur-[70px] opacity-35"
          style={{ background: "radial-gradient(circle, #45a99e, transparent 65%)" }}
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
          <div className="flex items-center gap-3">
            {/* Same live badge the tool pages use, sized to sit level with the pill beside it. */}
            <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-brand-teal/35 bg-brand-teal/15 px-4 py-2 text-[12.5px] font-bold uppercase tracking-[0.14em] text-brand-teal">
              <span
                className="h-1.5 w-1.5 rounded-full bg-brand-teal animate-pulse-ring"
                aria-hidden
              />
              Live
            </span>
            <Link
              to="/"
              className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.07] px-4 py-2 text-[12.5px] font-bold uppercase tracking-[0.14em] text-white/80 transition-colors hover:bg-white/[0.14] hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to hub
            </Link>
          </div>
        </motion.div>

        {/* heading + primary actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mt-14 flex flex-wrap items-end justify-between gap-6"
        >
          <div>
            <p className="text-[11.5px] font-bold uppercase tracking-[0.3em] text-brand-orange">
              Lead Magnet
            </p>
            <h1 className="mt-2 text-4xl font-extrabold tracking-tight sm:text-5xl">
              Lead Magnet Console
            </h1>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => setAddOpen(true)}
              className="inline-flex items-center gap-2 rounded-full border border-brand-orange/70 bg-brand-orange/15 px-4 py-2.5 text-[12px] font-bold uppercase tracking-[0.12em] text-brand-orange transition-colors hover:bg-brand-orange hover:text-white"
            >
              <Plus className="h-3.5 w-3.5" />
              Log lead manually
            </button>
          </div>
        </motion.div>

        {/* stat tiles */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.18 }}
          className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-3"
        >
          <StatCard label="Total leads" value={String(stats.total)} icon={Users} tone="sky" />
          <StatCard
            label="Total full audits"
            value={String(stats.audits)}
            icon={Globe}
            tone="teal"
          />
          <StatCard
            label="Avg site score"
            value={`${stats.avgScore}%`}
            icon={Flame}
            tone="lavender"
          />
        </motion.div>

        {/* search + filter + exports */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.26 }}
          className="mt-8 flex flex-wrap items-center gap-3"
        >
          <label className="relative min-w-[220px] flex-1 sm:max-w-sm">
            <Search
              className="pointer-events-none absolute left-4 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-brand-secondary"
              aria-hidden
            />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name, email or domain…"
              aria-label="Search leads"
              className="lm-glass w-full rounded-full border py-2.5 pl-11 pr-4 text-[13.5px] font-medium text-brand-primary outline-none transition-shadow placeholder:text-brand-secondary focus:ring-2 focus:ring-brand-orange/40"
            />
          </label>

          <FilterSelect
            ariaLabel="Filter by conversion source"
            value={typeFilter}
            onChange={setTypeFilter}
            options={SOURCE_OPTIONS}
          />

          <div className="ml-auto flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleExportCsv}
              disabled={leads.length === 0}
              className="inline-flex items-center gap-2 rounded-full border border-brand-teal/50 bg-brand-teal/15 px-4 py-2.5 text-[12px] font-bold uppercase tracking-[0.12em] text-brand-teal transition-colors hover:bg-brand-teal hover:text-white disabled:pointer-events-none disabled:opacity-40"
            >
              <Download className="h-3.5 w-3.5" />
              Export CRM CSV
            </button>
          </div>
        </motion.div>

        {/* leads table */}
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.34 }}
          className="mt-8"
          aria-label="Captured leads"
        >
          {/* "Total leads" counts captures; the table counts people. When
              repeats collapse those numbers diverge, so the gap is stated
              rather than left for someone to notice and distrust. */}
          {(collapsedCount > 0 || flaggedRowCount > 0) && (
            <p className="mb-2.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] font-semibold text-white/70">
              <AlertTriangle className="h-3.5 w-3.5 text-brand-orange" aria-hidden />
              {collapsedCount > 0 && (
                <span>
                  {leads.length} captures shown as {rows.length} leads &mdash; {collapsedCount}{" "}
                  repeat {collapsedCount === 1 ? "submission" : "submissions"} folded in.
                </span>
              )}
              {flaggedRowCount > 0 && (
                <span className="text-brand-orange">
                  {flaggedRowCount} flagged {flaggedRowCount === 1 ? "row" : "rows"}.
                </span>
              )}
            </p>
          )}
          <div className="lm-glass overflow-x-auto rounded-2xl border">
            <table className="w-full min-w-[880px] border-collapse text-left">
              <thead>
                {/* Every header is centred over its column, and each column's
                    cells are centred to match — a centred header above
                    left-aligned data would read as misaligned, not centred. */}
                <tr className="lm-glass-head border-b border-console-rule">
                  <SortableTh
                    label="Client"
                    onClick={() => toggleSort("name")}
                    className="text-center"
                  />
                  <SortableTh
                    label="Captured on"
                    onClick={() => toggleSort("date")}
                    className="text-center"
                  />
                  <Th className="text-center">Audit Type</Th>
                  <SortableTh
                    label="Score"
                    onClick={() => toggleSort("score")}
                    className="text-center"
                  />
                  <Th className="text-center">Full audit</Th>
                  <Th className="text-center">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {loadState === "loading" && (
                  <tr>
                    <td colSpan={6} className="px-5 py-14 text-center">
                      <span className="inline-flex items-center gap-2.5 text-[13.5px] text-brand-secondary">
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                        Loading the lead pipeline…
                      </span>
                    </td>
                  </tr>
                )}
                {loadState === "error" && (
                  <tr>
                    <td colSpan={6} className="px-5 py-14 text-center">
                      <AlertTriangle className="mx-auto h-8 w-8 text-console-bad/70" aria-hidden />
                      <p className="mt-3 text-[15px] font-bold text-brand-secondary">
                        Couldn&apos;t load the lead pipeline
                      </p>
                      <p className="mx-auto mt-1 max-w-sm text-[13px] text-brand-secondary">
                        Check that you&apos;re signed in and the dashboard server is reachable.
                      </p>
                      <button
                        type="button"
                        onClick={() => {
                          setLoadState("loading");
                          void refreshLeads();
                        }}
                        className="mt-4 inline-flex items-center gap-2 rounded-full border border-console-rule bg-white px-4 py-2 text-[12px] font-bold uppercase tracking-[0.12em] text-brand-primary transition-colors hover:bg-brand-primary/[0.06]"
                      >
                        <RotateCw className="h-3.5 w-3.5" />
                        Retry
                      </button>
                    </td>
                  </tr>
                )}
                {loadState === "ready" && sortedRows.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-5 py-14 text-center">
                      <Users className="mx-auto h-8 w-8 text-brand-primary/25" aria-hidden />
                      <p className="mt-3 text-[15px] font-bold text-brand-secondary">
                        {isFiltered ? "No leads found" : "No leads captured yet"}
                      </p>
                      <p className="mx-auto mt-1 max-w-sm text-[13px] text-brand-secondary">
                        {isFiltered
                          ? "No leads match your search or filters."
                          : "Run an audit on any Lead Magnet funnel page and the captured lead will appear here."}
                      </p>
                    </td>
                  </tr>
                )}
                {loadState !== "loading" &&
                  sortedRows.map((row) => {
                    const lead = row.lead;
                    const expanded = expandedId === lead.id;
                    const hasFullAudit = lead.details?.scheduler_cron === "FULL_AUDIT_COMPLETED";
                    /* Two sources, deliberately. The lead record is the durable
                       one and survives a reload or another operator's tab; the
                       live watch covers the seconds between starting a run and
                       the next refreshLeads() landing. */
                    const auditRunning = isFullAuditRunning(lead) || watchingLeadId === lead.id;
                    const source = SOURCE_META[lead.type];
                    return (
                      <LeadRowGroup
                        key={row.key}
                        row={row}
                        expanded={expanded}
                        hasFullAudit={hasFullAudit}
                        auditRunning={auditRunning}
                        reportUrl={lead.auditReportUrl}
                        sourceLabel={source.label}
                        sourceChip={source.chip}
                        nowMs={nowMs}
                        exactTime={exactTimeId === lead.id}
                        onToggleExactTime={() =>
                          setExactTimeId((id) => (id === lead.id ? null : lead.id))
                        }
                        onToggleExpand={() => setExpandedId(expanded ? null : lead.id)}
                        onRunAudit={() => requestFullAudit(lead)}
                        onDelete={() => setConfirm({ kind: "delete", row })}
                        noteDraft={noteDrafts[lead.id]}
                        noteSaving={savingNoteId === lead.id}
                        onNoteChange={(value) => setNoteDraft(lead.id, value)}
                        onNoteSave={() => void saveNote(lead)}
                        onNoteDiscard={() => discardNoteDraft(lead.id)}
                      />
                    );
                  })}
              </tbody>
            </table>
          </div>
        </motion.section>
      </div>

      {/* ── Manual lead entry ─────────────────────────────────────────── */}
      <AnimatePresence>
        {addOpen && (
          <ModalShell
            label="Log a lead manually"
            onClose={() => {
              setAddOpen(false);
              resetModalAudit();
            }}
          >
            <h2 className="text-2xl font-extrabold tracking-tight">Log lead manually</h2>
            <p className="mt-1.5 text-[13px] text-white/55">
              Add offsite emails, sandbox client logs or manually resolved enquiries so pipeline
              analytics stay unified.
            </p>

            <form onSubmit={handleCreateLead} className="mt-6 space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <ModalField label="Full name *">
                  <input
                    type="text"
                    required
                    value={newLead.name}
                    onChange={(e) => setNewLead({ ...newLead, name: e.target.value })}
                    placeholder="Thomas Shelby"
                    className={MODAL_INPUT}
                  />
                </ModalField>
                <ModalField label="Business email *">
                  <input
                    type="email"
                    required
                    value={newLead.email}
                    onChange={(e) => setNewLead({ ...newLead, email: e.target.value })}
                    placeholder="t.shelby@company.com"
                    className={MODAL_INPUT}
                  />
                </ModalField>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <ModalField label="Phone">
                  <input
                    type="tel"
                    value={newLead.phone}
                    onChange={(e) => setNewLead({ ...newLead, phone: e.target.value })}
                    placeholder="(919) 555-1234"
                    className={MODAL_INPUT}
                  />
                </ModalField>
                <ModalField label="Website URL">
                  {/* Deliberately type="text": a bare host is what the audit lookup
                      matches on, and type="url" would reject it. Normalized to an
                      absolute URL on save. */}
                  <input
                    type="text"
                    value={newLead.domainUrl}
                    onChange={(e) => {
                      setNewLead({ ...newLead, domainUrl: e.target.value });
                      resetModalAudit();
                    }}
                    placeholder="company.com"
                    className={MODAL_INPUT}
                  />
                </ModalField>
              </div>

              <div className="grid grid-cols-1 items-start gap-4 sm:grid-cols-2">
                <ModalField label="Audit Type">
                  <FilterSelect
                    ariaLabel="Audit type"
                    value={newLead.type}
                    onChange={(value) => {
                      setNewLead({ ...newLead, type: value as LeadType });
                      resetModalAudit();
                    }}
                    options={AUDIT_TYPE_OPTIONS}
                  />
                </ModalField>

                <ModalField label="Lead Magnet audit">
                  {modalAuditRunning ? (
                    /* running — same progress language as the deep-dive console */
                    <div className="flex h-[46px] items-center gap-3 rounded-xl border border-white/15 bg-white/[0.06] px-4">
                      <Loader2
                        className="h-4 w-4 shrink-0 animate-spin text-brand-sky"
                        aria-hidden
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2 text-[11px] font-bold text-white/60">
                          <span className="truncate">Auditing domain…</span>
                          <span className="shrink-0">{modalAuditProgress}%</span>
                        </div>
                        <div className="mt-1 h-1 overflow-hidden rounded-full bg-white/10">
                          <div
                            className="h-full rounded-full bg-brand-sky transition-[width] duration-100"
                            style={{ width: `${modalAuditProgress}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ) : auditScore !== null ? (
                    /* a score exists — show it, with re-run beside it */
                    <div className="flex h-[46px] items-center justify-between gap-3 rounded-xl border border-white/15 bg-white/[0.06] px-4">
                      <span className="inline-flex min-w-0 items-center gap-2">
                        <span
                          className={`h-2 w-2 shrink-0 rounded-full ${scoreTone(auditScore).dot}`}
                          aria-hidden
                        />
                        <span
                          className={`font-mono text-[14px] font-bold ${scoreTone(auditScore).text}`}
                        >
                          {auditScore}/100
                        </span>
                        <span className="truncate text-[11px] font-bold uppercase tracking-[0.12em] text-white/40">
                          {freshAudit
                            ? freshAudit.rerun
                              ? "Re-audited"
                              : "Audited now"
                            : "Previous audit"}
                        </span>
                      </span>
                      <button
                        type="button"
                        onClick={() => runModalAudit(true)}
                        aria-label="Re-run Lead Magnet audit on this domain"
                        title="Re-run Lead Magnet audit on this domain"
                        className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-white/15 bg-white/[0.06] text-white/60 transition-colors hover:bg-brand-orange hover:text-white"
                      >
                        <RotateCw className="h-4 w-4" />
                      </button>
                    </div>
                  ) : (
                    /* nothing on record — offer the first run */
                    <>
                      <button
                        type="button"
                        onClick={() => runModalAudit(false)}
                        disabled={!hasDomain}
                        className="inline-flex h-[46px] w-full items-center justify-center gap-2 rounded-xl border border-brand-orange/70 bg-brand-orange/15 px-4 text-[12px] font-bold uppercase tracking-[0.12em] text-brand-orange transition-colors hover:bg-brand-orange hover:text-white disabled:pointer-events-none disabled:border-white/12 disabled:bg-white/[0.04] disabled:text-white/30"
                      >
                        <Cpu className="h-3.5 w-3.5" />
                        Run Lead Magnet audit
                      </button>
                      {!hasDomain && (
                        <span className="mt-1.5 block text-[11px] font-semibold text-white/35">
                          Add a website URL to audit this domain.
                        </span>
                      )}
                    </>
                  )}
                </ModalField>
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => {
                    setAddOpen(false);
                    resetModalAudit();
                  }}
                  className="inline-flex items-center rounded-full border border-white/15 bg-white/[0.06] px-5 py-2.5 text-[12px] font-bold uppercase tracking-[0.12em] text-white/75 transition-colors hover:bg-white/[0.12] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="inline-flex items-center gap-2 rounded-full border border-brand-orange/70 bg-brand-orange px-6 py-2.5 text-[12px] font-bold uppercase tracking-[0.12em] text-white transition-colors hover:bg-brand-orange/85"
                >
                  Save lead
                </button>
              </div>
            </form>
          </ModalShell>
        )}
      </AnimatePresence>

      {/* ── Confirm delete ───────────────────────────────────────────── */}
      <AnimatePresence>
        {confirm && (
          <ModalShell label="Confirm action" onClose={() => setConfirm(null)} narrow>
            <div className="flex items-start gap-4">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-red-400/15 text-red-300">
                <AlertTriangle className="h-5 w-5" aria-hidden />
              </span>
              <div>
                {(() => {
                  const subject = confirm.kind === "delete" ? confirm.row.lead : confirm.lead;
                  const count = confirm.kind === "delete" ? confirm.row.submissions.length : 1;
                  return (
                    <>
                      <h2 className="text-xl font-extrabold tracking-tight">
                        {count > 1 ? `Delete all ${count} submissions?` : "Delete this lead?"}
                      </h2>
                      <p className="mt-1.5 text-[13.5px] leading-relaxed text-white/60">
                        {count > 1 ? (
                          <>
                            {subject.name} ({subject.email}) submitted{" "}
                            {SOURCE_META[subject.type].label} {count} times. All {count} stored
                            submissions will be removed from the pipeline.
                          </>
                        ) : (
                          <>
                            {subject.name} ({subject.email}) will be removed from the pipeline.
                          </>
                        )}
                      </p>
                    </>
                  );
                })()}
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setConfirm(null)}
                className="inline-flex items-center rounded-full border border-white/15 bg-white/[0.06] px-5 py-2.5 text-[12px] font-bold uppercase tracking-[0.12em] text-white/75 transition-colors hover:bg-white/[0.12] hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                className="inline-flex items-center gap-2 rounded-full border border-red-400/60 bg-red-400/20 px-5 py-2.5 text-[12px] font-bold uppercase tracking-[0.12em] text-red-200 transition-colors hover:bg-red-400/35 hover:text-white"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete lead
              </button>
            </div>
          </ModalShell>
        )}
      </AnimatePresence>

      {/* ── Pre-flight: identity the lead row cannot supply ──────────── */}
      <AnimatePresence>
        {identityLead && (
          <FullAuditIdentityModal
            lead={identityLead}
            productLabel={SOURCE_META[identityLead.type].label}
            initial={identityMemory.current[identityLead.id] ?? {}}
            onCancel={() => setIdentityLead(null)}
            onSubmit={(identity) => {
              const lead = identityLead;
              identityMemory.current[lead.id] = identity;
              setIdentityLead(null);
              void runDeepDiveAudit(lead, identity);
            }}
          />
        )}
      </AnimatePresence>

      {/* ── Deep-dive audit console ──────────────────────────────────── */}
      <AnimatePresence>
        {auditLead && auditStatus !== "idle" && (
          <ModalShell label="Deep-dive audit console" onClose={closeAudit}>
            <div className="border-b border-white/10 pb-5">
              {/* Names the audit being run, straight from the lead's own source —
                  one label, shared with the table chip and filters. */}
              <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.2em] text-brand-orange">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    auditStatus === "running"
                      ? "animate-pulse bg-brand-orange"
                      : auditStatus === "error"
                        ? "bg-console-bad-dot"
                        : "bg-brand-teal"
                  }`}
                  aria-hidden
                />
                {SOURCE_META[auditLead.type].label}
              </p>
              <h2 className="mt-1 text-2xl font-extrabold tracking-tight">
                {auditStatus === "success"
                  ? "Full Audit Completed"
                  : auditStatus === "error"
                    ? "Full Audit Failed"
                    : "Full Audit in Progress"}
              </h2>
            </div>

            <div className="mt-5 space-y-4">
              <div className="flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                <div className="min-w-0">
                  <p className="text-[10.5px] font-bold uppercase tracking-[0.18em] text-white/45">
                    Target domain
                  </p>
                  <p className="mt-0.5 truncate text-[15px] font-bold text-white">
                    {auditLead.domainUrl || "wahha-seo-audit-target.com"}
                  </p>
                  <p className="mt-0.5 truncate text-[12px] text-white/50">
                    Client: {auditLead.name} ({auditLead.email})
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-[10.5px] font-bold uppercase tracking-[0.18em] text-white/45">
                    Progress
                  </p>
                  <p className="mt-0.5 text-3xl font-extrabold text-brand-sky">{auditProgress}%</p>
                </div>
              </div>

              <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-brand-sky transition-[width] duration-500"
                  style={{ width: `${auditProgress}%` }}
                />
              </div>

              <div className="scrollbar-themed h-64 overflow-y-auto rounded-2xl border border-white/10 bg-[#0b0f22] p-4 font-mono text-[12px] leading-relaxed">
                {auditLogs.map((log, index) => (
                  <div
                    key={index}
                    className={
                      log.includes("[SUCCESS]")
                        ? "font-bold text-brand-teal"
                        : log.includes("[INFO]")
                          ? "text-brand-sky"
                          : "text-white/70"
                    }
                  >
                    {log}
                  </div>
                ))}
                {auditStatus === "running" && (
                  <div className="mt-1.5 flex items-center gap-1.5 font-bold text-brand-lavender">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                    <span>Audit running. You can close this — it keeps going.</span>
                  </div>
                )}
              </div>

              {/* Only while a scan is running: aborting is the one action that
                  isn't just "close". Once it completes the dialog's own X (or
                  Escape / backdrop) closes it, so no footer is needed. */}
              <div className="flex flex-wrap items-center justify-end gap-3 border-t border-white/10 pt-4">
                {/* Reading the finished run reuses the tool page's own panel,
                    which resumes any audit from ?run= — so the console never
                    has to render a report itself. */}
                {auditStatus === "success" && auditToolId && auditRunId && (
                  <Link
                    to={`/automations/${auditToolId}?run=${encodeURIComponent(auditRunId)}`}
                    className="inline-flex items-center gap-1.5 rounded-full border border-brand-teal/40 bg-brand-teal/15 px-5 py-2.5 text-[12px] font-bold uppercase tracking-[0.12em] text-brand-teal transition-colors hover:bg-brand-teal hover:text-brand-primary"
                  >
                    <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                    Open full report
                  </Link>
                )}
                <button
                  type="button"
                  onClick={closeAudit}
                  className="inline-flex items-center rounded-full border border-white/15 bg-white/[0.06] px-5 py-2.5 text-[12px] font-bold uppercase tracking-[0.12em] text-white/75 transition-colors hover:bg-white/[0.12] hover:text-white"
                >
                  {/* Always just "Close". Not "Abort" — nothing upstream is
                      cancelled — and no longer "Stop watching" either: closing
                      keeps the watch alive, so the run still reports back and
                      the row keeps showing it as running. */}
                  Close
                </button>
              </div>
            </div>
          </ModalShell>
        )}
      </AnimatePresence>

      {/* success toast */}
      <AnimatePresence>
        {toast && (
          <motion.div
            key="lead-toast"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            transition={{ duration: 0.25 }}
            role="status"
            aria-live="polite"
            className="fixed bottom-6 left-1/2 z-[90] flex max-w-md -translate-x-1/2 items-start gap-2.5 rounded-2xl border border-brand-teal/30 bg-[#141a45]/95 px-4 py-3 text-[13px] font-medium text-white shadow-[0_24px_60px_-16px_rgba(0,0,0,0.7)] backdrop-blur-xl"
          >
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-brand-teal" aria-hidden />
            <span>{toast}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── Table rows ─────────────────────────────────────────────────────── */

function LeadRowGroup({
  row,
  expanded,
  hasFullAudit,
  auditRunning,
  reportUrl,
  sourceLabel,
  sourceChip,
  nowMs,
  exactTime,
  onToggleExactTime,
  onToggleExpand,
  onRunAudit,
  onDelete,
  noteDraft,
  noteSaving,
  onNoteChange,
  onNoteSave,
  onNoteDiscard,
}: {
  row: LeadRow;
  expanded: boolean;
  hasFullAudit: boolean;
  /** A full audit for this lead is in flight — takes precedence over hasFullAudit. */
  auditRunning: boolean;
  reportUrl?: string;
  sourceLabel: string;
  sourceChip: string;
  nowMs: number;
  exactTime: boolean;
  onToggleExactTime: () => void;
  onToggleExpand: () => void;
  onRunAudit: () => void;
  onDelete: () => void;
  /** Unsaved note text; undefined means "showing the stored note". */
  noteDraft?: string;
  noteSaving: boolean;
  onNoteChange: (value: string) => void;
  onNoteSave: () => void;
  onNoteDiscard: () => void;
}) {
  const { lead, submissions, flags } = row;
  const flagged = flags.length > 0;
  const score = lead.details?.score;
  const auditTime = lead.details?.last_audit_time ?? lead.timestamp;
  const storedNote = lead.notes ?? "";
  const noteValue = noteDraft ?? storedNote;
  const noteDirty = noteDraft !== undefined && noteDraft !== storedNote;

  return (
    <>
      <tr
        onClick={onToggleExpand}
        className={[
          "cursor-pointer border-b border-console-rule transition-colors last:border-b-0",
          expanded ? "bg-brand-primary/[0.06]" : "hover:bg-brand-primary/[0.035]",
        ].join(" ")}
      >
        <td className="px-5 py-4 text-center">
          <span className="inline-flex items-center justify-center gap-2">
            {/* Attention marker, not an error: amber rather than red, because
                red already means destructive (delete) and critical elsewhere
                in this table. Stops row-click propagation so the two actions
                stay distinguishable to screen readers even though both expand. */}
            {flagged && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleExpand();
                }}
                title={flags.map(flagHeadline).join(" · ")}
                aria-label={`${flags.length} flag${flags.length > 1 ? "s" : ""} on this lead: ${flags
                  .map(flagHeadline)
                  .join("; ")}. Opens the details.`}
                className="grid h-6 w-6 shrink-0 place-items-center rounded-full border border-brand-orange/60 bg-brand-orange/20 text-console-warn transition-colors hover:bg-brand-orange/40"
              >
                <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
              </button>
            )}
            <p className="text-[14.5px] font-bold text-brand-primary">{lead.name}</p>
          </span>
          {/* mx-auto as well as text-center: the capped box would otherwise stay
              pinned to the left of the cell even with its text centred. */}
          <p className="mx-auto mt-0.5 max-w-[220px] truncate text-[12.5px] text-brand-secondary">
            {lead.email}
          </p>
        </td>
        <td className="whitespace-nowrap px-5 py-4 text-center text-[13px] font-medium text-brand-secondary">
          {formatTimestamp(lead.timestamp)}
        </td>
        <td className="px-5 py-4 text-center">
          <span
            className={`inline-flex items-center whitespace-nowrap rounded-full border px-3 py-1 text-[11px] font-bold uppercase tracking-[0.12em] ${sourceChip}`}
          >
            {sourceLabel}
          </span>
        </td>
        <td className="px-4 py-4 text-center">
          {typeof score === "number" ? (
            <span className="inline-flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${scoreTone(score).dot}`} aria-hidden />
              <span className={`font-mono text-[13px] font-bold ${scoreTone(score).text}`}>
                {score}/100
              </span>
            </span>
          ) : (
            <span className="text-[13px] text-brand-secondary">—</span>
          )}
        </td>
        <td className="px-4 py-4 text-center" onClick={(e) => e.stopPropagation()}>
          {auditRunning ? (
            /* The third state the cell was missing. It is checked FIRST because
               a re-run of an already-audited lead is running-and-completed at
               once, and what the operator needs to see then is the run in
               flight, not last week's download.

               Clicking re-opens the live console rather than starting anything:
               requestFullAudit re-shows an existing watch, or attaches to a run
               this tab is not watching. The server would refuse to duplicate the
               run anyway, but the operator should not have to rely on that. */
            <Tooltip content="Watch this audit" focusable={false} className="inline-flex">
              <button
                type="button"
                onClick={onRunAudit}
                aria-label="Watch the full audit in progress"
                className="inline-flex items-center gap-1.5 rounded-full border border-brand-lavender/50 bg-brand-lavender/15 px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-brand-lavender transition-colors hover:bg-brand-lavender hover:text-brand-primary"
              >
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                Running
              </button>
            </Tooltip>
          ) : hasFullAudit ? (
            /* divs rather than spans: Tooltip renders a div for its trigger, and
               a div inside a span is invalid nesting. A td takes flow content. */
            <div className="inline-flex flex-col items-center gap-1">
              <button
                type="button"
                onClick={onToggleExactTime}
                title="Toggle relative / exact audit time"
                className="text-[12px] font-bold text-[#16645a] transition-colors hover:text-[#185470] hover:underline"
              >
                {exactTime
                  ? new Date(auditTime).toLocaleString([], {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })
                  : getTimeSince(auditTime, nowMs)}
              </button>
              <div className="inline-flex items-center gap-1.5">
                {/* Only when there is something to download. A failed run, or one
                    that finished before the console captured the URL, leaves the
                    re-run control on its own rather than a link that 404s. */}
                {reportUrl && (
                  <a
                    href={reportUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 rounded-full border border-[#16645a]/30 bg-white px-2.5 py-1 text-[10.5px] font-bold uppercase tracking-[0.1em] text-[#16645a] transition-colors hover:bg-[#16645a] hover:text-white"
                  >
                    <Download className="h-3 w-3" />
                    Report
                  </a>
                )}
                {/* Re-run is an icon now that Download carries the label. The
                    tooltip is what names it, so the button keeps an aria-label
                    for anyone not using a pointer. */}
                <Tooltip content="Re-run the full audit" focusable={false} className="inline-flex">
                  <button
                    type="button"
                    onClick={onRunAudit}
                    aria-label="Re-run the full audit"
                    className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-brand-secondary/30 bg-white text-brand-secondary transition-colors hover:border-console-warn/60 hover:text-console-warn"
                  >
                    <RotateCw className="h-3 w-3" />
                  </button>
                </Tooltip>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={onRunAudit}
              className="inline-flex items-center gap-1.5 rounded-full border border-brand-orange/60 bg-brand-orange/15 px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-console-warn transition-colors hover:bg-brand-orange hover:text-brand-primary"
            >
              <Cpu className="h-3.5 w-3.5" />
              Run full audit
            </button>
          )}
        </td>
        <td className="px-5 py-4 text-center" onClick={(e) => e.stopPropagation()}>
          <span className="inline-flex items-center gap-2">
            <button
              type="button"
              onClick={onToggleExpand}
              aria-label={expanded ? "Collapse lead details" : "Expand lead details"}
              className="grid h-8 w-8 place-items-center rounded-lg border border-console-rule bg-white/70 text-brand-secondary transition-colors hover:bg-brand-primary/[0.08] hover:text-brand-primary"
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
            <button
              type="button"
              onClick={onDelete}
              aria-label={`Delete lead ${lead.name}`}
              className="grid h-8 w-8 place-items-center rounded-lg border border-console-bad/30 bg-console-bad/[0.08] text-console-bad transition-colors hover:bg-console-bad/20 hover:text-console-bad"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </span>
        </td>
      </tr>

      {expanded && (
        <tr className="border-b border-console-rule last:border-b-0">
          <td colSpan={6} className="bg-brand-primary/[0.04] px-6 py-6">
            {/* Flags lead the panel: if a row is flagged, that is the first
                thing worth knowing before reading any of its numbers. */}
            {flagged && (
              <div className="mb-5 rounded-2xl border border-brand-orange/45 bg-brand-orange/[0.10] p-4">
                <div className="flex items-start gap-3">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand-orange/25 text-console-warn">
                    <AlertTriangle className="h-4 w-4" aria-hidden />
                  </span>
                  <div className="min-w-0 space-y-2.5">
                    {flags.map((flag) => (
                      <div key={flag.kind}>
                        <p className="flex items-center gap-2 text-[12.5px] font-bold uppercase tracking-[0.12em] text-console-warn">
                          {flag.kind === "repeat" ? (
                            <Copy className="h-3.5 w-3.5" aria-hidden />
                          ) : (
                            <UsersRound className="h-3.5 w-3.5" aria-hidden />
                          )}
                          {flagHeadline(flag)}
                        </p>
                        <p className="mt-1 text-[12.5px] leading-relaxed text-brand-secondary">
                          {flagDetail(flag)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Every submission behind this row, so the collapse never hides
                    a score or a date the team might need. */}
                {submissions.length > 1 && (
                  <ol
                    aria-label="Submission history"
                    className="mt-4 space-y-1.5 border-t border-brand-orange/25 pt-3"
                  >
                    {submissions.map((sub, i) => (
                      <li
                        key={sub.id}
                        className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-[12.5px]"
                      >
                        <span className="flex items-center gap-2">
                          <span className="rounded bg-brand-primary/[0.07] px-1.5 py-0.5 font-mono text-[11px] text-brand-secondary">
                            {leadDisplayId(sub)}
                          </span>
                          <span className="font-semibold text-brand-primary">
                            {formatTimestamp(sub.timestamp)}
                          </span>
                          {i === 0 && (
                            <span className="text-[10.5px] font-bold uppercase tracking-[0.12em] text-console-warn">
                              shown above
                            </span>
                          )}
                        </span>
                        <span className="flex items-center gap-3">
                          {typeof sub.details?.score === "number" ? (
                            <span
                              className={`font-mono text-[12px] font-bold ${scoreTone(sub.details.score).text}`}
                            >
                              {sub.details.score}/100
                            </span>
                          ) : (
                            <span className="text-brand-secondary">no score</span>
                          )}
                        </span>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            )}
            {/* Column heights: stretched to match only when the booking brought a
                question with it, which is the case where the middle column has
                enough content to fill the row. Stretching unconditionally would
                give a lead that never booked a tall, half-empty domain card —
                trading ragged bottoms for dead space, which reads worse. */}
            <div
              className={`grid grid-cols-1 gap-5 md:grid-cols-12 ${
                lead.meeting?.questionAnswers?.length ? "md:items-stretch" : "items-start"
              }`}
            >
              {/* contact dossier */}
              <DetailCard
                className="h-full md:col-span-4"
                icon={<Users className="h-4 w-4 text-console-warn" aria-hidden />}
                title="Lead Details"
              >
                <DetailLine label="Lead ID">
                  <span className="rounded bg-brand-primary/[0.06] px-1.5 py-0.5 font-mono text-[11px] text-brand-secondary">
                    {leadDisplayId(lead)}
                  </span>
                </DetailLine>
                <DetailLine label="Full name">
                  <span className="font-bold text-brand-primary">{lead.name}</span>
                </DetailLine>
                <DetailLine label="Email">
                  <a
                    href={`mailto:${lead.email}`}
                    className="font-semibold text-[#185470] underline-offset-2 hover:underline"
                  >
                    {lead.email}
                  </a>
                </DetailLine>
                <DetailLine label="Phone">
                  <span className="text-brand-primary">{lead.phone || "Not provided"}</span>
                </DetailLine>

                {/* The booked call, set apart from the submitted identity above
                    because it is a later, different event in the lead's life —
                    and absent entirely until zcal's webhook reports one. */}
                {lead.meeting && (
                  <>
                    <span className="block h-5" aria-hidden />
                    <DetailLine label="Meeting on:">
                      <span
                        className={
                          lead.meeting.status === "cancelled"
                            ? "text-brand-secondary/70 line-through"
                            : "inline-flex items-center gap-1.5 font-bold text-brand-primary"
                        }
                        title={
                          lead.meeting.timezone
                            ? `Booked in ${lead.meeting.timezone}; shown in your timezone`
                            : undefined
                        }
                      >
                        {lead.meeting.status !== "cancelled" && (
                          <CalendarClock className="h-3.5 w-3.5 shrink-0 text-[#16645a]" aria-hidden />
                        )}
                        {formatMeetingSlot(lead.meeting.startsAt)}
                        {lead.meeting.durationMinutes ? ` · ${lead.meeting.durationMinutes} min` : ""}
                      </span>
                    </DetailLine>
                    {lead.meeting.status === "cancelled" && (
                      <DetailLine label="Booking status">
                        <span className="font-semibold text-[#b23c17]">Cancelled by invitee</span>
                      </DetailLine>
                    )}

                    {/* Shown only when the two identities disagree. On an ordinary
                        booking the details are the ones already above, and
                        repeating them would be noise. */}
                    {bookingIdentityDiffers(lead) && (
                      <DetailLine label="Meeting Email & Name">
                        <span className="inline-flex min-w-0 items-center justify-end gap-1.5">
                          <span className="min-w-0 truncate text-brand-primary">
                            {lead.meeting.bookedEmail ?? "No email"}
                            {lead.meeting.bookedName ? ` · ${lead.meeting.bookedName}` : ""}
                          </span>
                          {/* The tooltip lives on a wrapper, not the icon: lucide
                              icons take no `title`, and a span gives a 14px glyph
                              a hover target worth aiming at. */}
                          <span
                            role="img"
                            aria-label="Booked with different details from the ones submitted in the audit form."
                            title="Booked with different details from the ones submitted in the audit form."
                            className="inline-flex shrink-0 cursor-help p-0.5 text-brand-secondary/70 hover:text-brand-secondary"
                          >
                            <Info className="h-3.5 w-3.5" aria-hidden />
                          </span>
                        </span>
                      </DetailLine>
                    )}
                  </>
                )}
              </DetailCard>

              {/* Middle column: the audited property, and under it whatever the
                  prospect asked for when booking. Stacked in one column rather
                  than dropped into the next grid row so the row keeps three
                  columns, and so this column's height grows to meet the two
                  beside it instead of leaving a short stub card. */}
              <div className="flex h-full flex-col gap-5 md:col-span-5">
              <DetailCard
                icon={<Globe className="h-4 w-4 text-[#16645a]" aria-hidden />}
                title="Web Domain Audited"
              >
                {lead.domainUrl ? (
                  <>
                    <div className="flex items-center justify-between gap-3 rounded-xl border border-console-rule bg-white/70 px-3 py-2.5">
                      <span
                        className="truncate text-[13px] font-bold text-brand-primary"
                        title={lead.domainUrl}
                      >
                        {lead.domainUrl}
                      </span>
                      <a
                        href={lead.domainUrl}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="inline-flex shrink-0 items-center gap-1 rounded-full border border-console-rule bg-white px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-brand-secondary transition-colors hover:bg-brand-primary/[0.08] hover:text-brand-primary"
                      >
                        Visit
                        <ExternalLink className="h-2.5 w-2.5" />
                      </a>
                    </div>
                    {typeof lead.details?.score === "number" && (
                      <div className="mt-3">
                        {/* Restates the audited service beside the metrics, so the
                            numbers below are never read without knowing which
                            audit produced them. Same chip as the table column. */}
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-[10.5px] font-bold uppercase tracking-[0.16em] text-brand-secondary">
                            Diagnostic metrics loaded
                          </p>
                          <span
                            className={`inline-flex shrink-0 items-center whitespace-nowrap rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] ${sourceChip}`}
                          >
                            {sourceLabel}
                          </span>
                        </div>
                        <div className="mt-2 grid grid-cols-3 gap-2 text-center">
                          <MetricPill
                            value={lead.details?.passed ?? 0}
                            label="Passed"
                            className="border-[#16645a]/30 bg-[#16645a]/[0.07] text-[#16645a]"
                          />
                          <MetricPill
                            value={lead.details?.warnings ?? 0}
                            label="Warnings"
                            className="border-brand-orange/45 bg-brand-orange/[0.12] text-console-warn"
                          />
                          <MetricPill
                            value={lead.details?.critical ?? 0}
                            label="Critical"
                            className="border-console-bad/30 bg-console-bad/[0.07] text-console-bad"
                          />
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <p className="py-3 text-center text-[12.5px] text-brand-secondary">
                    No domain properties associated with this general lead query.
                  </p>
                )}
              </DetailCard>

              {/* What the prospect typed into the booking form's own question.
                  Its own card rather than a block inside Notes: Notes is a field
                  an operator writes into, and this is a record they cannot edit
                  — mixing the two invited the reading that it could be typed
                  over. Rendered from the meeting, never merged into `notes`. */}
              {lead.meeting?.questionAnswers?.length ? (
                <DetailCard
                  className="flex-1"
                  icon={<MessageSquareQuote className="h-4 w-4 text-[#16645a]" aria-hidden />}
                  title="Question from client"
                >
                  {lead.meeting.questionAnswers.map((qa, index) => (
                    <div key={`${qa.question ?? "q"}-${index}`} className="space-y-1">
                      {/* The question's own wording, shown only when the invite
                          asks more than one thing — with a single question the
                          card title already says what this is. */}
                      {lead.meeting!.questionAnswers!.length > 1 && qa.question ? (
                        <p className="text-[11px] font-semibold italic text-brand-secondary">
                          {qa.question}
                        </p>
                      ) : null}
                      <p className="whitespace-pre-wrap break-words text-[12.5px] font-bold italic leading-relaxed text-brand-primary">
                        {qa.answer}
                      </p>
                    </div>
                  ))}
                </DetailCard>
              ) : null}
              </div>

              {/* Notes — written here by whoever works the pipeline, never
                  captured from the lead. Saved explicitly so a stray keystroke
                  can't overwrite a colleague's note. */}
              <DetailCard
                className="h-full md:col-span-3"
                icon={<StickyNote className="h-4 w-4 text-brand-lavender" aria-hidden />}
                title="Notes"
              >
                <textarea
                  value={noteValue}
                  onChange={(e) => onNoteChange(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  rows={4}
                  maxLength={2000}
                  placeholder="Call outcome, next step, context…"
                  aria-label={`Notes for ${lead.name}`}
                  className="scrollbar-themed w-full resize-y rounded-xl border border-console-rule bg-white/70 p-3 text-[12px] leading-relaxed text-brand-primary outline-none transition-colors placeholder:text-brand-secondary focus:border-brand-secondary focus:bg-white"
                />
                {noteDirty ? (
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={onNoteSave}
                      disabled={noteSaving}
                      className="inline-flex items-center gap-1.5 rounded-full border border-[#16645a]/40 bg-[#16645a]/10 px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-[#16645a] transition-colors hover:bg-brand-teal hover:text-brand-primary disabled:pointer-events-none disabled:opacity-50"
                    >
                      {noteSaving ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                      ) : (
                        <Check className="h-3.5 w-3.5" aria-hidden />
                      )}
                      {noteSaving ? "Saving" : "Save"}
                    </button>
                    <button
                      type="button"
                      onClick={onNoteDiscard}
                      disabled={noteSaving}
                      className="rounded-full px-2 py-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-brand-secondary transition-colors hover:text-brand-primary disabled:pointer-events-none"
                    >
                      Discard
                    </button>
                  </div>
                ) : (
                  <p className="text-[11px] font-semibold text-brand-secondary">
                    {storedNote ? "Saved" : "No notes yet"}
                  </p>
                )}
              </DetailCard>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

/* ── Shared presentational bits ─────────────────────────────────────── */

const MODAL_INPUT =
  "w-full rounded-xl border border-white/15 bg-white/[0.06] px-4 py-3 text-[14px] font-medium text-white placeholder:text-white/35 outline-none transition-colors focus:border-white/35 focus:bg-white/[0.09]";

/* Icon chips on the light KPI panel — a wash of the brand hue with the hue's
   darker end as the glyph, since the light tints used on dark surfaces have
   no contrast here. */
const STAT_TONES = {
  sky: "bg-[#185470]/10 text-[#185470]",
  teal: "bg-[#16645a]/10 text-[#16645a]",
  orange: "bg-brand-orange/15 text-console-warn",
  lavender: "bg-brand-primary/[0.08] text-brand-secondary",
} as const;

function StatCard({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  icon: typeof Users;
  tone: keyof typeof STAT_TONES;
}) {
  return (
    <div className="lm-glass-raised rounded-2xl border p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-brand-secondary">
          {label}
        </p>
        <span className={`grid h-9 w-9 place-items-center rounded-xl ${STAT_TONES[tone]}`}>
          <Icon className="h-4 w-4" aria-hidden />
        </span>
      </div>
      <p className="mt-2 text-3xl font-extrabold tracking-tight text-brand-primary">{value}</p>
    </div>
  );
}

function Th({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <th
      className={`px-5 py-4 text-[13px] font-bold uppercase tracking-[0.2em] text-brand-orange ${className}`}
    >
      {children}
    </th>
  );
}

function SortableTh({
  label,
  onClick,
  className = "",
}: {
  label: string;
  onClick: () => void;
  className?: string;
}) {
  return (
    <Th className={className}>
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center gap-1.5 uppercase tracking-[0.2em] transition-colors hover:text-console-warn"
      >
        {label}
        <ArrowUpDown className="h-3 w-3" aria-hidden />
      </button>
    </Th>
  );
}

function MetricPill({
  value,
  label,
  className,
}: {
  value: number;
  label: string;
  className: string;
}) {
  return (
    <div className={`rounded-xl border px-2 py-2 ${className}`}>
      <span className="block text-[15px] font-extrabold leading-none">{value}</span>
      <span className="mt-1 block text-[9.5px] font-bold uppercase tracking-[0.12em] opacity-80">
        {label}
      </span>
    </div>
  );
}

function DetailCard({
  icon,
  title,
  children,
  className = "",
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`lm-glass-raised rounded-2xl border p-5 ${className}`}>
      <h4 className="flex items-center gap-2 border-b border-console-rule pb-2.5 text-[11px] font-bold uppercase tracking-[0.16em] text-brand-secondary">
        {icon}
        {title}
      </h4>
      <div className="mt-3 space-y-2.5">{children}</div>
    </div>
  );
}

function DetailLine({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <p className="flex items-center justify-between gap-3 text-[12.5px]">
      <span className="shrink-0 font-semibold text-brand-secondary">{label}</span>
      <span className="min-w-0 truncate text-right">{children}</span>
    </p>
  );
}

/** Overlay + opaque navy panel, matching TimelineModal's dialog conventions. */
function ModalShell({
  label,
  onClose,
  children,
  narrow = false,
}: {
  label: string;
  onClose: () => void;
  children: React.ReactNode;
  narrow?: boolean;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.18 } }}
      className="fixed inset-0 z-[80] flex items-center justify-center overflow-y-auto bg-[#0b0f22]/60 px-4 py-6 backdrop-blur-xl"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={label}
    >
      <div
        className={`relative w-full ${narrow ? "max-w-md" : "max-w-2xl"}`}
        onClick={(e) => e.stopPropagation()}
      >
        <motion.div
          initial={{ opacity: 0, y: 42, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 32, scale: 0.98, transition: { duration: 0.22 } }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="relative rounded-[26px] border border-[#3d4360] bg-[#12173e] p-6 text-white shadow-[0_24px_60px_-16px_rgba(0,0,0,0.7)] md:p-8"
        >
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="absolute right-5 top-5 grid h-9 w-9 place-items-center rounded-full border border-white/12 bg-white/[0.06] text-white/60 transition-colors hover:bg-white/[0.14] hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
          {children}
        </motion.div>
      </div>
    </motion.div>
  );
}

/**
 * Asks for the identity fields AI SEO needs and a lead row cannot supply.
 *
 * WHY THIS EXISTS AT ALL. Technical SEO and On-Page accept `{ seed_urls,
 * business_name }` and a lead already carries both, so their runs start from the
 * row. AI SEO's intake declares country and state required, and the funnel never
 * asks a prospect for either.
 *
 * WHY IT ASKS RATHER THAN GUESSING. Nothing on a lead implies a location — the
 * phone number is not required to carry a country code — and the backend has
 * measured that a wrong identity is worse than none: its Knowledge Graph lookup
 * resolves "Redfin Seattle Washington broker" to Redfin but "Redfin Unknown
 * Unknown unknown" to a different company entirely. A confidently wrong
 * high-severity finding is worse than a question.
 *
 * City and business type are asked for but optional: absent, they are dropped
 * from the provider query rather than padded, which costs precision and nothing
 * else.
 */
function FullAuditIdentityModal({
  lead,
  productLabel,
  initial,
  onCancel,
  onSubmit,
}: {
  lead: Lead;
  productLabel: string;
  initial: FullAuditIdentity;
  onCancel: () => void;
  onSubmit: (identity: FullAuditIdentity) => void;
}) {
  /* Deliberately NOT prefilled from lead.name. The funnel field behind it is
     labelled "Name*", so it is a contact's name about as often as a company's,
     and for this product the business name is the primary Knowledge Graph query
     term — a wrong-but-plausible default gets accepted and audits the wrong
     entity. `initial` is only ever what the operator typed here before, so
     re-opening the modal still restores their own entry. */
  const [businessName, setBusinessName] = useState(initial.businessName ?? "");
  const [country, setCountry] = useState(initial.country ?? "");
  const [state, setState] = useState(initial.state ?? "");
  const [city, setCity] = useState(initial.city ?? "");
  const [businessType, setBusinessType] = useState(initial.businessType ?? "");

  const { countrySuggestions, stateSuggestions, citySuggestions } = useLocationSuggestions({
    country,
    state,
    city,
  });

  const canRun =
    businessName.trim() !== "" && country.trim() !== "" && state.trim() !== "";

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!canRun) return;
    onSubmit({
      businessName: businessName.trim(),
      country: country.trim(),
      state: state.trim(),
      city: city.trim(),
      businessType: businessType.trim(),
    });
  };

  return (
    <ModalShell label="Details needed before this audit" onClose={onCancel} narrow>
      <form onSubmit={submit}>
        <div className="border-b border-white/10 pb-5">
          <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.2em] text-brand-orange">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-orange" aria-hidden />
            {productLabel}
          </p>
          <h2 className="mt-1 text-2xl font-extrabold tracking-tight">
            Additional Required intake Fields
          </h2>
          {/* Just the target. The heading already says these are required intake
              fields, so the rationale that used to sit here was explaining a
              decision the operator has already made by opening this dialog. */}
          <p className="mt-2 text-[13px] font-bold leading-relaxed text-white/80">
            {lead.domainUrl ?? "this business"}
          </p>
        </div>

        <div className="mt-5 space-y-4">
          <ModalField label="Business name *">
            <input
              type="text"
              value={businessName}
              onChange={(event) => setBusinessName(event.target.value)}
              placeholder="Wahha Design"
              className={MODAL_INPUT}
            />
          </ModalField>

          <div className="grid gap-4 sm:grid-cols-2">
            <ModalField label="Country *">
              <ComboboxField
                id="full-audit-country"
                value={country}
                suggestions={countrySuggestions}
                onChange={setCountry}
                onSelect={(suggestion) => setCountry(suggestion.value)}
                placeholder="United States"
                required
                emptyHint="No match — you can still type it in."
              />
            </ModalField>
            <ModalField label="State / Region *">
              <ComboboxField
                id="full-audit-state"
                value={state}
                suggestions={stateSuggestions}
                onChange={setState}
                onSelect={(suggestion) => setState(suggestion.value)}
                placeholder="North Carolina"
                required
                emptyHint={
                  country.trim()
                    ? "No match — you can still type it in."
                    : "Pick a country first for suggestions."
                }
              />
            </ModalField>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <ModalField label="City (optional)">
              <ComboboxField
                id="full-audit-city"
                value={city}
                suggestions={citySuggestions}
                onChange={setCity}
                onSelect={(suggestion) => {
                  setCity(suggestion.value);
                  // Selecting a city fills the state it belongs to, so the two
                  // cannot end up describing different places.
                  const filled = (suggestion.data as { state?: string } | undefined)?.state;
                  if (filled) setState(filled);
                }}
                placeholder="Wilmington"
                emptyHint="No match — you can still type it in."
              />
            </ModalField>
            <ModalField label="Business type (optional)">
              <input
                type="text"
                value={businessType}
                onChange={(event) => setBusinessType(event.target.value)}
                placeholder="Marketing Agency"
                className={MODAL_INPUT}
              />
            </ModalField>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-3 border-t border-white/10 pt-4">
            <button
              type="button"
              onClick={onCancel}
              className="inline-flex items-center rounded-full border border-white/15 bg-white/[0.06] px-5 py-2.5 text-[12px] font-bold uppercase tracking-[0.12em] text-white/75 transition-colors hover:bg-white/[0.12] hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canRun}
              className="inline-flex items-center gap-1.5 rounded-full border border-brand-orange/60 bg-brand-orange/15 px-5 py-2.5 text-[12px] font-bold uppercase tracking-[0.12em] text-console-warn transition-colors hover:bg-brand-orange hover:text-brand-primary disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-brand-orange/15 disabled:hover:text-console-warn"
            >
              <Cpu className="h-3.5 w-3.5" aria-hidden />
              Run full audit
            </button>
          </div>
        </div>
      </form>
    </ModalShell>
  );
}

function ModalField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[10.5px] font-bold uppercase tracking-[0.16em] text-white/45">
        {label}
      </span>
      {children}
    </label>
  );
}

/**
 * Themed dropdown (native <select> popups are OS-styled and can't be themed).
 * Pill trigger + glass navy panel — same pattern the History page uses.
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
          "inline-flex w-full items-center justify-between gap-2.5 rounded-full border px-4 py-2.5 text-[12.5px] font-bold uppercase tracking-[0.1em] transition-colors",
          open
            ? "lm-glass ring-2 ring-brand-orange/40 text-brand-primary"
            : "lm-glass text-brand-primary hover:brightness-[0.98]",
        ].join(" ")}
      >
        {selected.label}
        <ChevronDown
          className={`h-4 w-4 text-brand-secondary transition-transform duration-200 ${open ? "rotate-180" : ""}`}
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
          "absolute left-0 top-[calc(100%+8px)] z-30 min-w-full origin-top overflow-hidden lm-glass rounded-2xl border py-1.5 shadow-[0_24px_60px_-16px_rgba(0,0,0,0.7)] backdrop-blur-xl transition-[opacity,transform] duration-150 ease-out",
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
                    ? "text-brand-primary"
                    : "text-brand-secondary hover:bg-brand-primary/[0.06] hover:text-brand-primary",
                ].join(" ")}
              >
                {o.label}
                {isSelected && <Check className="h-4 w-4 text-console-warn" aria-hidden />}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
