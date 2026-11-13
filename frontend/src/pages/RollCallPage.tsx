import { useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  Ban,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  FileText,
  HelpCircle,
  Loader2,
  Mail,
  MessageSquare,
  MinusCircle,
  RotateCw,
  Send,
  ShieldCheck,
  Sparkles,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import {
  ATTENDANCE_MIN_TURNS,
  ATTENDANCE_MIN_WORDS,
  FLAG_META,
  renderMessage,
  shortDate,
  TRACKS,
  type CellState,
  type GridRow,
  type MessageChannel,
  type Track,
  type TrackId,
} from "@/lib/rollCall";
import { formatDuration } from "@/lib/internalMeeting";
import { STAGES, TRACKED_MONTH_LABEL } from "@/data/rollCall";
import {
  toFollowUpList,
  toSheetColumn,
  memberById,
  useRollCallRun,
  type ResolvedAttendee,
} from "@/hooks/useRollCallRun";

/* ────────────────────────────────────────────────────────────────
   Roll call — paste an office-hours transcript, get attendance and the flags.

   THE CONSTRAINT IS THE PRODUCT. Gisselle's own words on the audit sheet:
   "Just needs to flag, we will manually follow up." Nothing here sends a
   portal DM or an email. The output is a flag with an owner.

   THE HONEST LIMIT, stated on screen rather than buried. Fathom's share
   payload has no attendee list — `byline` is literally "Unknown" — so
   attendance is inferred from who SPOKE. Whitney described the format as an
   open drop-in (26 Aug @12:00, "it's really like an open meeting for clients
   to come in"; @13:32, "they can join like at any moment during that hour"),
   which means a member who joins, listens and leaves silently is scored
   ABSENT — and that is exactly the disengaged member the 2-week flag exists to
   catch. At three attendees this holds. At six it would not. So the page says
   so, every run, and every absence is a flag for a human rather than an action.

   THREE THINGS HERE ARE LOAD-BEARING:

   1. TWO TABS, TWO COUNTERS. Google and Meta are separate sheets today
      (26 Aug @10:36) and the counters are genuinely independent — attending
      Google does not clear a Meta miss. Nora Chen is in both, which is what
      makes that visible rather than asserted.

   2. FIRE ONCE ON CROSSING. A flag is raised on the run that crosses the
      threshold, not every week after. Dale Okoro is already six misses deep;
      without this rule he would generate a fresh "DM him" task every Thursday
      forever and the flag would stop being read.

   3. THE AMBIGUOUS NAME. Two members join as "Jillian". The transcript gives
      a bare first name, so the card refuses to pick and asks. This is the real
      failure surface of the whole approach, and hiding it would be the one
      thing that makes the output untrustworthy.
   ──────────────────────────────────────────────────────────────── */

const Pill = ({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) => (
  <span
    className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${className}`}
  >
    {children}
  </span>
);

const CELL_META: Record<CellState, { mark: string; className: string; title: string }> = {
  attended: { mark: "✓", className: "bg-emerald-50 text-emerald-700", title: "Attended" },
  missed: { mark: "—", className: "bg-red-50 text-red-600", title: "Missed" },
  not_enrolled: { mark: "·", className: "bg-brand-mist/40 text-brand-slate", title: "Not in this channel" },
  no_session: { mark: "", className: "bg-white text-brand-slate", title: "No transcript read yet" },
};

function AttendeeRow({
  attendee,
  onChoose,
  onDismiss,
  onConfirmShort,
  locked,
}: {
  attendee: ResolvedAttendee;
  onChoose: (memberId: string) => void;
  onDismiss: () => void;
  onConfirmShort: () => void;
  locked: boolean;
}) {
  const { observed, match, crossTrack } = attendee;
  const resolved = match.member;

  return (
    <article className="rounded-xl border border-brand-mist bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h4 className="text-sm font-semibold text-brand-ink">{observed.label}</h4>
          <p className="mt-0.5 text-xs text-brand-gray">
            {observed.turns} turns · {observed.words} words · {observed.firstDisplay}–
            {observed.lastDisplay}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {attendee.dismissed ? (
            <Pill className="border-brand-mist bg-brand-mist/40 text-brand-gray">
              <Ban className="h-3 w-3" /> Not a member
            </Pill>
          ) : observed.belowThreshold && !attendee.shortConfirmed ? (
            <Pill className="border-amber-200 bg-amber-50 text-amber-800">
              <MinusCircle className="h-3 w-3" /> below the engagement floor
            </Pill>
          ) : observed.belowThreshold && attendee.shortConfirmed ? (
            <Pill className="border-emerald-200 bg-emerald-50 text-emerald-700">
              <CheckCircle2 className="h-3 w-3" /> present — confirmed by hand
            </Pill>
          ) : resolved ? (
            <Pill className="border-emerald-200 bg-emerald-50 text-emerald-700">
              <CheckCircle2 className="h-3 w-3" /> present
            </Pill>
          ) : null}
          {match.method === "ambiguous" && !attendee.chosenMemberId && (
            <Pill className="border-red-200 bg-red-50 text-red-700">
              <HelpCircle className="h-3 w-3" /> two members join under this name
            </Pill>
          )}
          {match.method === "unknown" && (
            <Pill className="border-red-200 bg-red-50 text-red-700">
              <AlertTriangle className="h-3 w-3" /> not on the roster
            </Pill>
          )}
          {crossTrack && (
            <Pill className="border-amber-200 bg-amber-50 text-amber-800">
              <Users className="h-3 w-3" /> wrong channel
            </Pill>
          )}
        </div>
      </div>

      {resolved && (
        <p className="mt-2 text-xs text-brand-secondary">
          Matched to <strong>{resolved.accountName}</strong> — {resolved.business} ·{" "}
          <span className="text-brand-gray">
            {match.method === "alias"
              ? "known join name"
              : `fuzzy match, ${Math.round(match.score * 100)}%`}
          </span>
        </p>
      )}

      {crossTrack && resolved && (
        <p className="mt-2 rounded-lg bg-amber-50 px-2.5 py-1.5 text-xs leading-relaxed text-amber-900">
          In the <strong>{resolved.tracks.map((t) => TRACKS[t].channel).join(" and ")}</strong>{" "}
          channel, not this one. Does not count towards either track.
        </p>
      )}

      {match.method === "ambiguous" && !locked && !attendee.chosenMemberId && (
        <div className="mt-3">
          <p className="mb-2 text-xs text-brand-secondary">
            First name only, and two members use it. Which one was on the call?
          </p>
          <div className="flex flex-wrap gap-2">
            {match.candidates.map((candidate) => (
              <button
                key={candidate.memberId}
                onClick={() => onChoose(candidate.memberId)}
                className="rounded-lg border border-brand-mist px-2.5 py-1 text-xs font-medium text-brand-secondary transition-colors hover:border-brand-primary hover:text-brand-primary"
              >
                {candidate.accountName} · {candidate.business}
              </button>
            ))}
            <button
              onClick={onDismiss}
              className="rounded-lg border border-brand-mist px-2.5 py-1 text-xs font-medium text-brand-secondary hover:border-brand-stone"
            >
              Neither — not a member
            </button>
          </div>
        </div>
      )}

      {match.method === "unknown" && !locked && !attendee.dismissed && (
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            onClick={onDismiss}
            className="rounded-lg border border-brand-mist px-2.5 py-1 text-xs font-medium text-brand-secondary hover:border-brand-stone"
          >
            Not a member — ignore
          </button>
        </div>
      )}

      {/* THE OVERRIDE THE WARNING PROMISED AND DID NOT PROVIDE. Selecting a
          roster member left the engagement floor in force, so a reviewer
          could say "yes, they were here" and still see the member scored
          absent. Confirming here is what actually decides it. */}
      {observed.belowThreshold &&
        !attendee.shortConfirmed &&
        !attendee.dismissed &&
        !locked && (
          <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
            <p className="text-xs leading-relaxed text-amber-900">
              {observed.turns} turn{observed.turns === 1 ? "" : "s"}, {observed.words} words —
              under the floor of {ATTENDANCE_MIN_TURNS} and {ATTENDANCE_MIN_WORDS}. Your call
              overrides it.
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                onClick={onConfirmShort}
                className="rounded-lg bg-brand-primary px-2.5 py-1 text-xs font-semibold text-white"
              >
                They were here — count as present
              </button>
              <button
                onClick={onDismiss}
                className="rounded-lg border border-amber-300 px-2.5 py-1 text-xs font-medium text-amber-900"
              >
                Not a member — ignore
              </button>
            </div>
          </div>
        )}
    </article>
  );
}

function Grid({
  rows,
  track,
  sent,
  onCompose,
}: {
  rows: GridRow[];
  track: TrackId;
  sent: Record<string, MessageChannel>;
  onCompose: (row: GridRow) => void;
}) {
  const sessions = rows[0]?.cells.map((c) => c.session) ?? [];
  if (!rows.length) {
    return (
      <p className="rounded-xl border border-dashed border-brand-stone p-6 text-center text-sm text-brand-gray">
        No members in the {TRACKS[track].channel} channel.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto rounded-xl border border-brand-mist bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-brand-mist text-left">
            <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-brand-secondary">
              Member
            </th>
            {sessions.map((session) => (
              <th
                key={session.sessionId}
                className="px-2 py-2 text-center text-xs font-medium text-brand-gray"
              >
                {shortDate(session.date)}
                {!session.recorded && (
                  <span className="block text-[10px] font-normal text-brand-slate">
                    not read
                  </span>
                )}
              </th>
            ))}
            <th className="px-2 py-2 text-center text-xs font-semibold uppercase tracking-wide text-brand-secondary">
              Misses
            </th>
            <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-brand-secondary">
              Flag
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.member.memberId} className="border-b border-brand-mist/60 last:border-0">
              <td className="px-3 py-2">
                <span className="font-medium text-brand-ink">{row.member.accountName}</span>
                <span className="block text-[11px] text-brand-gray">{row.member.business}</span>
              </td>
              {row.cells.map((cell) => {
                const meta = CELL_META[cell.state];
                return (
                  <td key={cell.session.sessionId} className="px-2 py-2 text-center">
                    <span
                      title={meta.title}
                      className={`inline-flex h-6 w-6 items-center justify-center rounded ${meta.className}`}
                    >
                      {meta.mark}
                    </span>
                  </td>
                );
              })}
              <td className="px-2 py-2 text-center font-semibold text-brand-ink">
                {row.consecutiveMisses}
              </td>
              <td className="px-3 py-2">
                {row.flag === "none" ? (
                  <span className="text-xs text-brand-slate">—</span>
                ) : (
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Pill
                      className={
                        row.flag === "four_week"
                          ? "border-red-200 bg-red-50 text-red-700"
                          : "border-amber-200 bg-amber-50 text-amber-800"
                      }
                    >
                      {row.flag === "four_week" ? (
                        <Mail className="h-3 w-3" />
                      ) : (
                        <MessageSquare className="h-3 w-3" />
                      )}
                      {FLAG_META[row.flag].label}
                      {row.crossedThisRun && " · new"}
                    </Pill>
                    {/* The action sits with the flag. A member flagged three
                        weeks ago is actionable here without pasting anything,
                        which is the whole point of the register. */}
                    {sent[row.member.memberId] ? (
                      <Pill className="border-emerald-200 bg-emerald-50 text-emerald-700">
                        <Check className="h-3 w-3" />
                        {sent[row.member.memberId] === "email" ? "sent" : "DM sent"}
                      </Pill>
                    ) : (
                      <button
                        onClick={() => onCompose(row)}
                        className="inline-flex items-center gap-1 rounded-md border border-brand-primary px-2 py-0.5 text-[11px] font-semibold text-brand-primary transition-colors hover:bg-brand-primary/10"
                      >
                        {row.flag === "four_week" ? "Draft email" : "Draft DM"}
                      </button>
                    )}
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FlagCard({
  row,
  owner,
  sentChannel,
  onCompose,
}: {
  row: GridRow;
  owner: string;
  sentChannel?: MessageChannel;
  onCompose: () => void;
}) {
  const tier = row.flag as "two_week" | "four_week";
  const meta = FLAG_META[tier];
  const isEmail = tier === "four_week";
  return (
    <div
      className={`rounded-xl border p-4 ${
        isEmail ? "border-red-200 bg-red-50/40" : "border-amber-200 bg-amber-50/40"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold text-brand-ink">{row.member.accountName}</h4>
          <p className="text-xs text-brand-gray">{row.member.business}</p>
        </div>
        <Pill
          className={
            isEmail
              ? "border-red-200 bg-white text-red-700"
              : "border-amber-200 bg-white text-amber-800"
          }
        >
          {isEmail ? <Mail className="h-3 w-3" /> : <MessageSquare className="h-3 w-3" />}
          {meta.label}
        </Pill>
      </div>
      <p className="mt-2 text-xs leading-relaxed text-brand-secondary">
        {row.consecutiveMisses} consecutive misses · last attended{" "}
        {row.lastAttended ? shortDate(row.lastAttended) : "never"}
      </p>
      <p className="mt-2 text-xs text-brand-gray">
        {meta.action} — <span className="font-medium text-brand-ink">{owner}</span>
      </p>

      {/* The tier decides the channel, so the button cannot offer the wrong
          one: two weeks is a portal DM, four weeks escalates to email. */}
      <div className="mt-3">
        {sentChannel ? (
          <Pill className="border-emerald-200 bg-emerald-50 text-emerald-700">
            <Check className="h-3 w-3" />
            {sentChannel === "email" ? "Email sent" : "DM sent"} to {row.member.firstName}
          </Pill>
        ) : (
          <button
            onClick={onCompose}
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-primary px-3 py-1.5 text-xs font-semibold text-white"
          >
            {isEmail ? <Mail className="h-3.5 w-3.5" /> : <MessageSquare className="h-3.5 w-3.5" />}
            {isEmail ? "Draft the email" : "Draft the DM"}
          </button>
        )}
      </div>
    </div>
  );
}

/** Compose the filled template, review it, send it. */
function ComposeModal({
  row,
  track,
  sessionDate,
  dmAlreadySent,
  onSend,
  onClose,
}: {
  row: GridRow;
  track: Track;
  sessionDate: string;
  dmAlreadySent: boolean;
  onSend: (channel: MessageChannel) => void;
  onClose: () => void;
}) {
  const tier = row.flag as "two_week" | "four_week";
  const draft = renderMessage(row.member, track, tier, sessionDate);
  const [body, setBody] = useState(draft.body);
  const [subject, setSubject] = useState(draft.subject ?? "");
  const isEmail = draft.channel === "email";

  return (
    <div className="fixed inset-0 z-[70] flex items-start justify-center overflow-y-auto bg-brand-ink/40 px-4 py-10 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-2xl border border-brand-mist bg-white shadow-xl">
        <header className="flex items-start justify-between gap-3 border-b border-brand-mist px-5 py-4">
          <div>
            <h3 className="text-base font-semibold text-brand-ink">
              {isEmail ? "Follow-up email" : "Portal DM"} · {row.member.accountName}
            </h3>
            <p className="mt-0.5 text-xs text-brand-gray">
              {FLAG_META[tier].label} · {row.consecutiveMisses} consecutive misses
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-brand-slate transition-colors hover:bg-brand-mist/50 hover:text-brand-ink"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="space-y-3 px-5 py-4">
          {/* The 4-week email opens by referring to a DM "I sent a couple weeks
              ago". If that DM never actually went, the first line is false to
              the client — worth catching before it goes, not after. */}
          {isEmail && !dmAlreadySent && (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900">
              <strong>Check the first line.</strong> This email says &ldquo;the message I sent a
              couple weeks ago&rdquo;, but no two-week DM is recorded as sent to{" "}
              {row.member.firstName}. If the DM never went out, reword it before sending.
            </p>
          )}

          <div className="grid gap-2 text-xs">
            <div className="flex gap-2">
              <span className="w-14 shrink-0 font-medium text-brand-gray">From</span>
              <span className="text-brand-ink">{draft.from}</span>
            </div>
            <div className="flex gap-2">
              <span className="w-14 shrink-0 font-medium text-brand-gray">To</span>
              <span className="text-brand-ink">{draft.to}</span>
            </div>
          </div>

          {isEmail && (
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-brand-gray">Subject</span>
              <input
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full rounded-lg border border-brand-mist px-3 py-2 text-sm focus:border-brand-primary focus:outline-none"
              />
            </label>
          )}

          <label className="block">
            <span className="mb-1 block text-xs font-medium text-brand-gray">
              {isEmail ? "Message" : "DM"}
            </span>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={isEmail ? 12 : 7}
              className="w-full rounded-lg border border-brand-mist px-3 py-2.5 text-sm leading-relaxed focus:border-brand-primary focus:outline-none"
            />
          </label>

          {/* Every substitution, shown — so a wrong name or a wrong session
              date is visible before it reaches a client rather than after. */}
          <div className="rounded-lg border border-brand-mist bg-brand-mist/20 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-secondary">
              Filled from your data
            </p>
            <ul className="mt-1 space-y-0.5">
              {draft.filled.map((f) => (
                <li key={f.token} className="text-[11px] text-brand-gray">
                  <code className="text-brand-secondary">{f.token}</code> → {f.value}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-brand-mist px-5 py-4">
          <button
            onClick={onClose}
            className="rounded-lg border border-brand-mist px-3 py-2 text-sm text-brand-secondary hover:border-brand-stone"
          >
            Cancel
          </button>
          <div className="flex items-center gap-3">
            <span className="text-[11px] text-brand-gray">
              Goes out as {track.followUpOwner.split(" ")[0]}
            </span>
            <button
              onClick={() => onSend(draft.channel)}
              disabled={!body.trim() || (isEmail && !subject.trim())}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            >
              <Send className="h-4 w-4" /> {isEmail ? "Send email" : "Send DM"}
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default function RollCallPage() {
  const run = useRollCallRun();
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  /* Carries the track as well as the row: the message signs off as that
     track's owner (Carmen for Google, Jacqueline for Meta) and fills that
     track's session time, so composing from the Meta tab must not sign as
     Carmen. */
  const [composing, setComposing] = useState<{ row: GridRow; track: TrackId } | null>(null);
  const [toast, setToast] = useState<
    | { kind: "recorded"; present: number }
    | { kind: "message"; channel: MessageChannel; name: string; owner: string }
    | null
  >(null);

  /* One fixture per track. Google is the REAL 12 Feb session; Meta is a
     synthetic one carrying the two exception cases the real transcript does
     not contain — a brief speaker and a member who never speaks at all. The
     button says which, because they are not the same kind of evidence. */
  const loadDemo = async () => {
    setLoading(true);
    if (run.runTrack === "meta") {
      const mod = await import("@/data/rollCallMetaTranscript");
      run.setText(mod.META_TRANSCRIPT);
    } else {
      const mod = await import("@/data/rollCallTranscript");
      run.setText(mod.DEMO_TRANSCRIPT);
    }
    setLoading(false);
  };

  const copy = async (label: string, value: string) => {
    await navigator.clipboard.writeText(value);
    setCopied(label);
    window.setTimeout(() => setCopied(null), 1800);
  };

  const download = (name: string, value: string) => {
    const url = URL.createObjectURL(new Blob([value], { type: "text/plain" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = name;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const recorded = run.state === "recorded";
  const t = run.transcript;

  return (
    <div className="bg-hero min-h-[100svh]">
      <div className="container py-10">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-brand-gray transition-colors hover:text-brand-primary"
        >
          <ArrowLeft className="h-4 w-4" /> Command Center
        </Link>

        <header className="mt-4 mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold text-brand-ink">Office Hours Roll Call</h1>
            <p className="mt-1 max-w-2xl text-sm leading-relaxed text-brand-gray">
              Who attended, consecutive misses per member, and the two- and four-week flags.
            </p>
            <p className="mt-2 max-w-2xl text-sm text-brand-secondary">
              Each flag arrives with the message written. You read it and press send.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Pill className="border-amber-200 bg-amber-50 text-amber-800">
              <FileText className="h-3 w-3" /> paste intake · flag only
            </Pill>
            {run.state !== "idle" && (
              <button
                onClick={run.reset}
                className="rounded-lg border border-brand-mist bg-white p-2 text-brand-gray transition-colors hover:border-brand-stone"
                aria-label="Start over"
              >
                <RotateCw className="h-4 w-4" />
              </button>
            )}
          </div>
        </header>

        {/* ── INTAKE ───────────────────────────────────────────── */}
        {run.state === "idle" && (
          <div className="space-y-6">
            <div className="rounded-xl border border-brand-mist bg-white p-5">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="text-sm font-semibold text-brand-ink">
                    Upload an office-hours transcript
                  </h2>
                  <p className="mt-0.5 text-xs text-brand-gray">
                    {run.track.label} · {run.track.slot} · hosted by {run.track.host}
                  </p>
                </div>
                <button
                  onClick={() => void loadDemo()}
                  disabled={loading}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-brand-primary px-3 py-1.5 text-xs font-semibold text-brand-primary disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5" />
                  )}
                  {run.runTrack === "meta"
                    ? "Load Meta fixture (invented)"
                    : "Load the real 12 Feb transcript"}
                </button>
              </div>
              {/* WHICH SESSION. Track and date were hard-coded to Google /
                  12 Feb, so a Meta session could not be processed at all and
                  half the described workflow had no demonstration. A
                  cancelled week is offered and refused rather than hidden,
                  which is how the rule becomes visible. */}
              <div className="mb-3 rounded-lg border border-brand-mist bg-brand-surface p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-secondary">
                  Which session is this?
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {(["google", "meta"] as const).map((id) => (
                    <button
                      key={id}
                      onClick={() => run.chooseTrack(id)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                        run.runTrack === id
                          ? "bg-brand-primary text-white"
                          : "border border-brand-mist bg-white text-brand-secondary hover:border-brand-stone"
                      }`}
                    >
                      {TRACKS[id].label}
                    </button>
                  ))}
                  <span className="mx-1 h-4 w-px bg-brand-mist" aria-hidden />
                  {run.selectableSessions.map((session) => {
                    const on = session.sessionId === run.runSessionId;
                    return (
                      <button
                        key={session.sessionId}
                        disabled={session.cancelled}
                        onClick={() => run.setRunSessionId(session.sessionId)}
                        title={session.cancelledReason ?? undefined}
                        className={`rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors ${
                          session.cancelled
                            ? "cursor-not-allowed border border-dashed border-brand-mist text-brand-slate line-through"
                            : on
                              ? "bg-brand-ink text-white"
                              : "border border-brand-mist bg-white text-brand-secondary hover:border-brand-stone"
                        }`}
                      >
                        {shortDate(session.date)}
                        {session.recorded && !on ? " ✓" : ""}
                      </button>
                    );
                  })}
                </div>
                <p className="mt-2 text-xs text-brand-gray">
                  {run.runSession?.cancelled ? (
                    <span className="text-amber-800">{run.runSession.cancelledReason}</span>
                  ) : run.runSession?.recorded ? (
                    <>Already read — reading it again replaces that attendance.</>
                  ) : (
                    <>Not yet read. Cancelled weeks are struck through and count as no miss.</>
                  )}
                  <span className="ml-1.5 text-brand-slate">
                    Source: transcript speech (fallback). Zoom participant report not connected.
                  </span>
                </p>
              </div>

              <textarea
                value={run.text}
                onChange={(event) => run.setText(event.target.value)}
                placeholder="Paste the Fathom copy for this week's session…"
                rows={9}
                className="w-full rounded-lg border border-brand-mist px-3 py-2.5 font-mono text-xs leading-relaxed focus:border-brand-primary focus:outline-none"
              />
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <button
                  onClick={() => run.start(run.text)}
                  disabled={run.text.trim().length < 200}
                  className="inline-flex items-center gap-2 rounded-lg bg-brand-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
                >
                  <Check className="h-4 w-4" /> Read this session
                </button>
                <span className="text-xs text-brand-gray">
                  {run.text.trim()
                    ? `${run.text.length.toLocaleString()} characters pasted`
                    : "Nothing pasted yet"}
                </span>
              </div>
            </div>

            {/* The month as it stands before anything is read, so the paste
                visibly changes it rather than arriving pre-filled. */}
            <div>
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-brand-secondary">
                Monthly tracking · {TRACKED_MONTH_LABEL}
              </h3>
              <TabbedGrids run={run} onCompose={(row, track) => setComposing({ row, track })} />
            </div>
          </div>
        )}

        {/* ── PROCESSING ───────────────────────────────────────── */}
        {run.state === "running" && (
          <div className="rounded-xl border border-brand-mist bg-white p-6">
            <h2 className="text-sm font-semibold text-brand-ink">
              Reading {run.track.label}
            </h2>
            <ol className="mt-4 space-y-3">
              {STAGES.map((stage, index) => {
                const done = index < run.stageIndex;
                const active = index === run.stageIndex;
                return (
                  <li key={stage.id} className="flex items-start gap-3">
                    <span className="mt-0.5">
                      {done ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      ) : active ? (
                        <Loader2 className="h-4 w-4 animate-spin text-brand-primary" />
                      ) : (
                        <span className="block h-4 w-4 rounded-full border border-brand-mist" />
                      )}
                    </span>
                    <div className="min-w-0">
                      <p className={`text-sm ${done || active ? "text-brand-ink" : "text-brand-slate"}`}>
                        {stage.label}
                        {!stage.real && (
                          <Pill className="ml-2 border-amber-200 bg-amber-50 text-amber-800">
                            roster is a fixture — GHL invite not accepted yet
                          </Pill>
                        )}
                      </p>
                      {done && stage.id === "read" && t && (
                        <p className="mt-0.5 text-xs text-brand-gray">
                          {t.turns.length} turns · {formatDuration(t.durationSeconds)} ·{" "}
                          {t.firstDisplay}–{t.lastDisplay}
                        </p>
                      )}
                      {done && stage.id === "attendance" && (
                        <p className="mt-0.5 text-xs text-brand-gray">
                          {run.attendees.length} non-staff speakers ·{" "}
                          {run.attendees.filter((a) => !a.observed.belowThreshold).length} cleared
                          the floor of {ATTENDANCE_MIN_TURNS} turns and {ATTENDANCE_MIN_WORDS} words
                        </p>
                      )}
                      {done && stage.id === "roster" && (
                        <p className="mt-0.5 text-xs text-brand-gray">
                          {run.attendees.filter((a) => a.match.member).length} matched ·{" "}
                          {run.attendees.filter((a) => a.match.method === "ambiguous").length}{" "}
                          ambiguous · {run.attendees.filter((a) => a.crossTrack).length} in another
                          channel
                        </p>
                      )}
                      {done && stage.id === "flags" && (
                        <p className="mt-0.5 text-xs text-brand-gray">
                          {run.grids[run.runTrack].length} members on this track checked
                        </p>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>
        )}

        {/* ── REVIEW / RECORDED ────────────────────────────────── */}
        {(run.state === "review" || recorded) && t && (
          <div /* pb-28 reserves clearance for the sticky action bar below, which is
                 the last child: without it the bar lands on top of the final
                 section at full scroll and that content is unreachable. */
            className="space-y-8 pb-28">
            <div className="rounded-xl border border-brand-mist bg-white p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <h2 className="text-lg font-semibold text-brand-ink">
                  {run.track.label} ·{" "}
                  {run.runSession ? shortDate(run.runSession.date) : "12 Feb 2026"}
                </h2>
                {recorded ? (
                  <Pill className="border-emerald-200 bg-emerald-50 text-emerald-700">
                    <ShieldCheck className="h-3 w-3" /> Attendance recorded · flags raised
                  </Pill>
                ) : (
                  <Pill className="border-brand-primary/30 bg-brand-primary/5 text-brand-primary">
                    {run.undecided.length} need a decision
                  </Pill>
                )}
              </div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-brand-gray">
                <span>{t.charCount.toLocaleString()} characters</span>
                <span>{t.turns.length} turns</span>
                <span>hosted by {run.track.host}</span>
                <span>{run.track.channel}</span>
              </div>
              {/* The limit of the method, stated every run rather than once —
                  together with the source that replaces it in production.
                  Without the second half this reads as the only way the flags
                  can ever be derived, which would be wrong: the sessions are
                  Zoom meetings on their own account (Sept 2 @5:24), and Zoom's
                  past-meeting participant report gives join/leave times for
                  everyone who attended, silent or not. The transcript pass is
                  the fallback for a session where that report is unavailable,
                  and it is what this console demonstrates because it is what
                  runs with no Zoom access granted. */}
              <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900">
                <strong>Attendance here is who spoke.</strong> A silent member reads as absent — add them below. Zoom's participant report is the production source.
              </p>
            </div>

            <section>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-brand-secondary">
                Who spoke on the call · {run.attendees.length}
              </h3>
              <p className="mb-3 max-w-3xl text-xs text-brand-gray">
                {run.track.host} excluded as host. Others matched to the {run.track.channel} roster.
              </p>
              <div className="space-y-3">
                {run.attendees.map((attendee) => (
                  <AttendeeRow
                    key={attendee.observed.label}
                    attendee={attendee}
                    locked={recorded}
                    onChoose={(id) => run.chooseMember(attendee.observed.label, id)}
                    onDismiss={() => run.dismiss(attendee.observed.label)}
                    onConfirmShort={() => run.confirmShort(attendee.observed.label)}
                  />
                ))}
              </div>
            </section>

            {/* THE SILENT ATTENDEE. They produce no observed-speaker row —
                that is the whole failure mode — so there is nothing to
                correct. Presence is added from the roster instead. */}
            {!recorded && (
              <section>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-brand-secondary">
                  Attended without speaking
                </h3>
                <p className="mb-3 max-w-3xl text-xs leading-relaxed text-brand-gray">
                  Not in the transcript. Add anyone the host remembers being on the call.
                </p>
                <div className="flex flex-wrap gap-2">
                  {run.silentCandidates.length === 0 && (
                    <p className="text-xs text-brand-gray">
                      Every member on this track already has a speaking row.
                    </p>
                  )}
                  {run.silentCandidates.map((m) => {
                    const added = Boolean(run.manualPresent[m.memberId]);
                    return (
                      <button
                        key={m.memberId}
                        onClick={() =>
                          added ? run.removePresent(m.memberId) : run.addPresent(m.memberId)
                        }
                        className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors ${
                          added
                            ? "bg-emerald-600 text-white"
                            : "border border-brand-mist bg-white text-brand-secondary hover:border-brand-primary hover:text-brand-primary"
                        }`}
                      >
                        {added ? <Check className="h-3 w-3" /> : <UserPlus className="h-3 w-3" />}
                        {m.accountName}
                      </button>
                    );
                  })}
                </div>
              </section>
            )}

            {/* THE FINAL PREVIEW. Exactly who this run will mark present and
                why, before the confirm rather than discovered in the grid
                afterwards. */}
            <section>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-brand-secondary">
                {recorded ? "Recorded as present" : "Will be marked present"} ·{" "}
                {run.presentPreview.length}
              </h3>
              <p className="mb-3 max-w-3xl text-xs text-brand-gray">
                Everyone else on this track is a miss for{" "}
                {run.runSession ? shortDate(run.runSession.date) : "this session"}.
              </p>
              <div className="rounded-xl border border-brand-mist bg-white divide-y divide-brand-mist">
                {run.presentPreview.length === 0 && (
                  <p className="px-4 py-3 text-xs text-brand-gray">
                    Nobody yet. Resolve the decisions above, or add a silent attendee.
                  </p>
                )}
                {run.presentPreview.map((row) => (
                  <div
                    key={row.accountName}
                    className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5 flex-none text-emerald-600" />
                    <span className="min-w-0 flex-1 text-sm text-brand-ink">
                      {row.accountName}
                    </span>
                    <span className="text-xs text-brand-gray">{row.reason}</span>
                  </div>
                ))}
              </div>
            </section>

            {recorded && (
              <>
                {run.newFlags.length > 0 && (
                  <section>
                    <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-brand-secondary">
                      New flags from this session · {run.newFlags.length}
                    </h3>
                    <p className="mb-3 max-w-3xl text-xs text-brand-gray">
                      Each fires once, on the run that crosses the threshold.
                    </p>
                    <div className="grid gap-3 md:grid-cols-2">
                      {run.newFlags.map((row) => (
                        <FlagCard
                          key={row.member.memberId}
                          row={row}
                          owner={run.track.followUpOwner}
                          sentChannel={run.sent[row.member.memberId]}
                          onCompose={() => setComposing({ row, track: run.runTrack })}
                        />
                      ))}
                    </div>
                  </section>
                )}

                {run.standingFlags.length > 0 && (
                  <section>
                    <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-brand-secondary">
                      Already flagged before this session · {run.standingFlags.length}
                    </h3>
                    <p className="mb-3 max-w-3xl text-xs text-brand-gray">
                      Still open, deliberately not re-raised.
                    </p>
                    <div className="rounded-xl border border-brand-mist bg-white divide-y divide-brand-mist">
                      {run.standingFlags.map((row) => (
                        <div
                          key={row.member.memberId}
                          className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5"
                        >
                          <span className="min-w-0 flex-1 text-sm text-brand-ink">
                            {row.member.accountName}
                          </span>
                          <span className="text-xs text-brand-gray">
                            {row.consecutiveMisses} misses · last attended{" "}
                            {row.lastAttended ? shortDate(row.lastAttended) : "never"}
                          </span>
                          <Pill className="border-brand-mist bg-brand-mist/40 text-brand-gray">
                            <Clock className="h-3 w-3" /> flagged already
                          </Pill>
                          {/* Still composable. These are the MOST overdue
                              members, so read-only here would be exactly the
                              wrong way round: the flag is not re-raised, but
                              the message stays available to send. */}
                          {run.sent[row.member.memberId] ? (
                            <Pill className="border-emerald-200 bg-emerald-50 text-emerald-700">
                              <Check className="h-3 w-3" />
                              {run.sent[row.member.memberId] === "email" ? "Email sent" : "DM sent"}
                            </Pill>
                          ) : (
                            <button
                              onClick={() => setComposing({ row, track: run.runTrack })}
                              className="inline-flex items-center gap-1.5 rounded-lg border border-brand-primary px-2.5 py-1 text-xs font-semibold text-brand-primary"
                            >
                              {row.flag === "four_week" ? (
                                <Mail className="h-3 w-3" />
                              ) : (
                                <MessageSquare className="h-3 w-3" />
                              )}
                              Draft
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </>
            )}

            {/* FOLLOW-UP HISTORY. Sends were stored per member alone, so a
                Google DM and a Meta email were indistinguishable and the
                four-week email could not tell whether the two-week DM had
                actually gone on ITS track. Each row now carries the track,
                the tier, the session it came out of, and the ClickUp
                monitoring task Gisselle creates today by hand. */}
            {run.sentLog.length > 0 && (
              <section>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-brand-secondary">
                  Follow-up history · {run.sentLog.length}
                </h3>
                <p className="mb-3 max-w-3xl text-xs text-brand-gray">
                  Recorded when a human pressed send. Nothing left this browser.
                </p>
                <div className="rounded-xl border border-brand-mist bg-white divide-y divide-brand-mist">
                  {run.sentLog.map((r, i) => (
                    <div
                      key={`${r.memberId}-${r.track}-${i}`}
                      className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5"
                    >
                      <span className="min-w-0 flex-1 text-sm text-brand-ink">
                        {memberById(r.memberId)?.accountName ?? r.memberId}
                      </span>
                      <Pill className="border-brand-mist bg-brand-mist/40 text-brand-gray">
                        {TRACKS[r.track].label}
                      </Pill>
                      <Pill
                        className={
                          r.tier === "four_week"
                            ? "border-red-200 bg-red-50 text-red-700"
                            : "border-amber-200 bg-amber-50 text-amber-800"
                        }
                      >
                        {r.tier === "four_week" ? "4-week email" : "2-week DM"}
                      </Pill>
                      <span className="text-xs text-brand-gray">
                        after {shortDate(
                          run.sessions.find((x) => x.sessionId === r.sessionId)?.date ??
                            "2026-02-12",
                        )}
                      </span>
                      <span className="w-full text-xs text-brand-slate">
                        ClickUp monitoring task: {r.monitorTask}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            <div>
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-brand-secondary">
                Monthly tracking · {TRACKED_MONTH_LABEL}
              </h3>
              <TabbedGrids run={run} onCompose={(row, track) => setComposing({ row, track })} />
            </div>

            {!recorded ? (
              /* A sticky bar floats OVER whatever is behind it, so it has to
                 look like it is floating. With `shadow-sm` and a flat white
                 fill it read as a panel that had collided with the table
                 underneath and clipped a row in half. The lift, the ring and
                 the blur are what make it legible as an action bar. */
              <div className="sticky bottom-4 z-20 flex flex-wrap items-center gap-3 rounded-xl border border-brand-mist bg-white/95 p-4 shadow-lg ring-1 ring-brand-ink/5 backdrop-blur-md">
                <button
                  onClick={() => {
                    const result = run.confirm();
                    setToast({ kind: "recorded", present: result.present });
                  }}
                  disabled={run.undecided.length > 0}
                  className="inline-flex items-center gap-2 rounded-lg bg-brand-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
                >
                  <ShieldCheck className="h-4 w-4" />
                  Record attendance
                  {run.undecided.length > 0 && ` · ${run.undecided.length} to decide`}
                </button>
                <span className="text-xs text-brand-gray">
                  Marks {run.presentAccounts.length} present and recomputes the flags. No message
                  is sent.
                </span>
              </div>
            ) : (
              <div className="rounded-xl border border-brand-mist bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-brand-secondary">
                  What she does next
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    onClick={() =>
                      void copy(
                        "sheet column",
                        toSheetColumn(run.grids[run.tab], "2026-02-12"),
                      )
                    }
                    className="inline-flex items-center gap-1.5 rounded-lg border border-brand-mist px-3 py-2 text-xs font-medium text-brand-secondary transition-colors hover:border-brand-stone"
                  >
                    <Copy className="h-3.5 w-3.5" />
                    {copied === "sheet column" ? "Copied" : `Copy the ${TRACKS[run.tab].id} sheet column`}
                  </button>
                  <button
                    onClick={() =>
                      void copy("follow-ups", toFollowUpList(run.newFlags, run.track.followUpOwner))
                    }
                    className="inline-flex items-center gap-1.5 rounded-lg border border-brand-mist px-3 py-2 text-xs font-medium text-brand-secondary transition-colors hover:border-brand-stone"
                  >
                    <MessageSquare className="h-3.5 w-3.5" />
                    {copied === "follow-ups" ? "Copied" : "Copy the follow-up list"}
                  </button>
                  <button
                    onClick={() =>
                      download(
                        "roll-call-2026-02-12.txt",
                        toSheetColumn(run.grids[run.tab], "2026-02-12"),
                      )
                    }
                    className="inline-flex items-center gap-1.5 rounded-lg border border-brand-mist px-3 py-2 text-xs font-medium text-brand-secondary transition-colors hover:border-brand-stone"
                  >
                    <Download className="h-3.5 w-3.5" /> Export
                  </button>
                </div>
                <p className="mt-3 text-xs leading-relaxed text-brand-gray">
                  Tab-delimited in the same shape as your roll-call sheets, so it pastes
                  straight in.
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* The composer, mounted at the page root so it overlays cleanly. */}
      {composing && (
        <ComposeModal
          row={composing.row}
          track={TRACKS[composing.track]}
          /* Anchored to the last session actually READ for this track, so
             {{DATE}} is the genuine next one: 19 Feb on Google once 12 Feb is
             recorded, but still 12 Feb on Meta, whose session has not been
             read. A hard-coded date would be wrong on one of the two tabs. */
          sessionDate={run.lastRecordedDate(composing.track)}
          /* Per TRACK, not per member. A Google DM in January must not make
             a Meta email in February think the DM already went. */
          dmAlreadySent={run
            .sentFor(composing.row.member.memberId, composing.track)
            .some((r) => r.channel === "portal_dm")}
          onClose={() => setComposing(null)}
          onSend={(channel) => {
            run.markSent(composing.row.member.memberId, channel, {
              track: composing.track,
              tier: composing.row.flag === "four_week" ? "four_week" : "two_week",
              accountName: composing.row.member.accountName,
            });
            setToast({
              kind: "message",
              channel,
              name: composing.row.member.accountName,
              /* The composing track's owner, not the run's: a Meta send is
                 from Jacqueline even when the pasted session was Google. */
              owner: TRACKS[composing.track].followUpOwner,
            });
            setComposing(null);
          }}
        />
      )}

      <AnimatePresence>
        {toast && (
          <motion.div
            key="roll-call-toast"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            className="fixed bottom-6 right-6 z-50 max-w-sm rounded-xl border border-brand-mist bg-white p-4 shadow-lg"
            role="status"
          >
            <div className="flex items-start gap-3">
              <div className="rounded-full bg-emerald-50 p-1.5">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
              </div>
              <div className="flex-1">
                {toast.kind === "message" ? (
                  <>
                    <p className="text-sm font-semibold text-brand-ink">
                      {toast.channel === "email" ? "Email" : "DM"} sent to {toast.name}
                    </p>
                    {/* The confirmation asked for, and the truth about it in the
                        same breath. There is no mail or portal integration in
                        this build, so claiming delivery alone would be the one
                        dishonest string on the page. */}
                    <p className="mt-0.5 text-xs leading-relaxed text-brand-gray">
                      Recorded as sent by {toast.owner.split(" ")[0]}.{" "}
                      <strong>
                        Demo send — nothing left the browser. Wiring this to{" "}
                        {toast.channel === "email" ? "hello@" : "the members portal"} is the next
                        step.
                      </strong>
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-sm font-semibold text-brand-ink">Attendance recorded</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-brand-gray">
                      {toast.present} member{toast.present === 1 ? "" : "s"} marked present for
                      12 Feb. {run.newFlags.length} new flag
                      {run.newFlags.length === 1 ? "" : "s"} raised, {run.standingFlags.length}{" "}
                      already standing and not re-raised. Draft the follow-ups below.
                    </p>
                  </>
                )}
              </div>
              <button
                onClick={() => setToast(null)}
                aria-label="Dismiss notification"
                className="rounded p-1 text-brand-slate transition-colors hover:bg-brand-mist/50 hover:text-brand-ink"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/** The two tabs — one per track, each on its own counter. */
function TabbedGrids({
  run,
  onCompose,
}: {
  run: ReturnType<typeof useRollCallRun>;
  onCompose: (row: GridRow, track: TrackId) => void;
}) {
  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2" role="tablist">
        {(["google", "meta"] as TrackId[]).map((id) => {
          const flags = run.grids[id].filter((r) => r.flag !== "none").length;
          const active = run.tab === id;
          return (
            <button
              key={id}
              role="tab"
              aria-selected={active}
              onClick={() => run.setTab(id)}
              className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-semibold transition-colors ${
                active
                  ? "border-brand-primary bg-brand-primary/10 text-brand-primary"
                  : "border-brand-mist bg-white text-brand-secondary hover:border-brand-stone"
              }`}
            >
              {TRACKS[id].channel}
              {flags > 0 && (
                <span className="rounded-full bg-amber-100 px-1.5 text-[10px] font-bold text-amber-800">
                  {flags}
                </span>
              )}
            </button>
          );
        })}
      </div>
      <Grid
        rows={run.grids[run.tab]}
        track={run.tab}
        sent={run.sent}
        onCompose={(row) => onCompose(row, run.tab)}
      />
      <p className="mt-2 text-[11px] leading-relaxed text-brand-gray">
        {run.tab === run.runTrack
          ? "Attendance resets the count. The two tracks run on separate counters — attending one does not clear a miss on the other."
          : `No ${TRACKS[run.tab].label} transcript has been read for 12 Feb, so that column is empty rather than counted as a miss.`}
      </p>
    </div>
  );
}
