import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { AlertTriangle, ArrowDownRight, ArrowUpRight, CalendarCheck, CalendarClock, Info, Inbox, MessageSquareReply, RefreshCw, Trophy } from 'lucide-react';
import { Dialog } from '../components/UI';
import { ThemedSelect } from '../components/ThemedSelect';
import { ThemedDatePicker } from '../components/ThemedDatePicker';
import EChart, { CHART_FONT, escapeHtml, INK, NEUTRAL, PALETTE, TOOLTIP, tooltipRow, type ChartOption } from '../components/EChart';
import './LeadsTab.css';

/*
 * Client record > Leads. Reads GET /api/v1/clients/{slug}/leads (backend/services/read_models/leads.py), which
 * aggregates the venue's LeadLock records. Every figure is a count of stored records; the KB stores no couple
 * names, emails, phone numbers or message text, so nothing here can show them.
 */
type Period = '7d' | '14d' | '30d' | '90d' | '180d' | '12m' | 'all';
interface Kpi { value: number | null; previous?: number | null }
interface Row { label: string; count: number }
interface LeadsData {
  client: { slug: string; name: string };
  as_of: string;
  synced_at: string | null;
  period: { key: Period | 'custom'; start: string | null; end: string; days: number | null };
  sub_accounts: { location_id: string; name: string }[];
  collecting: boolean;
  kpis: {
    inquiries: Kpi; tours_booked: Kpi; upcoming_tours: Kpi;
    awaiting_reply: { value: number; oldest_days: number | null; older_unread: number };
    won: { tracked: boolean; value: number | null; previous: number | null };
  };
  monthly: { month: string; inquiries: number; tours: number }[];
  pipelines: { pipeline: string; sub_account: string | null; total: number; ordered: boolean; stages: { stage: string; count: number }[] }[];
  outcomes: { tracked: boolean; counts: Record<string, number>; all_time: Record<string, number> };
  sources: Row[];
  forms: Row[];
  channels: { label: string; count: number; awaiting: number }[];
  appointments: Record<string, number>;
  coverage: { records: Record<string, number>; first_inquiry: string | null };
}

const PERIODS: { id: Period; label: string; menu: string; long: string; days: number | null }[] = [
  { id: '7d', label: '7 days', menu: 'Last 7 days', long: 'the previous 7 days', days: 7 },
  { id: '14d', label: '14 days', menu: 'Last 14 days', long: 'the previous 14 days', days: 14 },
  { id: '30d', label: '30 days', menu: 'Last 30 days', long: 'the previous 30 days', days: 30 },
  { id: '90d', label: '90 days', menu: 'Last 90 days', long: 'the previous 90 days', days: 90 },
  { id: '180d', label: '180 days', menu: 'Last 180 days', long: 'the previous 180 days', days: 180 },
  { id: '12m', label: '12 months', menu: 'Last 12 months', long: 'the previous 12 months', days: 365 },
  { id: 'all', label: 'All time', menu: 'All time', long: '', days: null },
];
// Validated with the dataviz palette checker (CVD + normal-vision separation; aqua needs visible labels, which it has).
const SERIES = { inquiries: '#2a78d6', tours: '#eb6834' };
const OUTCOME_ORDER = [
  { id: 'open', label: 'Open', color: '#2a78d6' },
  { id: 'won', label: 'Won', color: '#1baf7a' },
  { id: 'lost', label: 'Lost', color: '#eb6834' },
  { id: 'abandoned', label: 'Abandoned', color: '#6250d6' },
];
const TOUR_STATUS: Record<string, string> = { confirmed: 'Confirmed', showed: 'Showed', cancelled: 'Cancelled', noshow: 'No-show', invalid: 'Invalid', new: 'New', booked: 'Booked' };

const n = (value: number) => value.toLocaleString('en-US');
const pct = (part: number, whole: number) => whole ? Math.round(part / whole * 100) : 0;
const monthLabel = (ym: string, long = false) => new Date(`${ym}-01T00:00:00Z`).toLocaleDateString('en-US', { month: long ? 'long' : 'short', year: long ? 'numeric' : undefined, timeZone: 'UTC' });
const SERIF = "'Playfair Display', Georgia, serif";
const OTHER = 'Other';
const REMAINING = 'Remaining';
const NOT_RECORDED = '#c9d1de';
const TOP_SOURCES = 4; // donut: 4 sources + Other (approved 5 Nov)
const OTHER_PIE_MAX = 8;

/* Period: a preset dropdown plus a from/to date range beside it (5 Nov). Presets end today; a custom range is
 * whole days, inclusive, compared with the same number of days just before it. */
type Range = { kind: 'preset'; id: Period } | { kind: 'custom'; start: string; end: string };
const DAY_MS = 86_400_000;
const isoDay = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const todayIso = () => isoDay(new Date());
const parseDay = (iso: string) => new Date(`${iso}T00:00:00`);
const shortDay = (iso: string, year = false) => parseDay(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: year ? 'numeric' : undefined });
const daysIn = (start: string, end: string) => Math.round((parseDay(end).getTime() - parseDay(start).getTime()) / DAY_MS) + 1;
function rangeText(start: string, end: string) {
  const sameYear = start.slice(0, 4) === end.slice(0, 4);
  return start === end ? shortDay(start, true) : `${shortDay(start, !sameYear)} – ${shortDay(end, true)}`;
}
/** Dates a preset covers, for filling the from/to fields. */
function presetDates(id: Period, firstInquiry: string | null) {
  const end = todayIso();
  const days = PERIODS.find(p => p.id === id)?.days;
  if (!days) return { start: firstInquiry ?? end, end };
  return { start: isoDay(new Date(Date.now() - (days - 1) * DAY_MS)), end };
}
/** label: short ("90 days", "Oct 1 – Oct 15, 2026"); phrase: after "from"/"in"; long: the comparison window. */
function describeRange(range: Range) {
  if (range.kind === 'custom') {
    const days = daysIn(range.start, range.end);
    const text = rangeText(range.start, range.end);
    return { label: text, phrase: text, long: `the previous ${days} day${days === 1 ? '' : 's'}` };
  }
  const p = PERIODS.find(x => x.id === range.id)!;
  return { label: p.label, phrase: p.id === 'all' ? 'all time' : `the last ${p.label}`, long: p.long };
}

function RangePicker({ range, onChange, firstInquiry }: { range: Range; onChange: (r: Range) => void; firstInquiry: string | null }) {
  const shown = range.kind === 'custom' ? range : presetDates(range.id, firstInquiry);
  const [draft, setDraft] = useState(shown);
  // Follow the applied range (a preset picked from the dropdown refills the dates).
  useEffect(() => { setDraft(shown); }, [shown.start, shown.end]); // eslint-disable-line react-hooks/exhaustive-deps
  const valid = Boolean(draft.start && draft.end && draft.start <= draft.end && draft.end <= todayIso());
  const changed = draft.start !== shown.start || draft.end !== shown.end;
  // The platform's own dropdown and calendar (ThemedSelect / ThemedDatePicker), not the browser's.
  return <div className="leads-range" role="group" aria-label="Period">
    <ThemedSelect aria-label="Preset period" className="leads-range-select" value={range.kind === 'custom' ? 'custom' : range.id}
      onChange={value => { if (value !== 'custom') onChange({ kind: 'preset', id: value as Period }); }}>
      {PERIODS.map(p => <option key={p.id} value={p.id}>{p.menu}</option>)}
      <option value="custom" disabled={range.kind !== 'custom'}>Custom range</option>
    </ThemedSelect>
    <div className={`leads-range-dates ${range.kind === 'custom' ? 'is-active' : ''}`}>
      <ThemedDatePicker label="From" value={draft.start} onChange={start => setDraft(d => ({ ...d, start }))} />
      <span aria-hidden="true">–</span>
      <ThemedDatePicker label="To" value={draft.end} onChange={end => setDraft(d => ({ ...d, end }))} />
      <button type="button" className="leads-range-apply" disabled={!valid || !changed}
        title={draft.start > draft.end ? 'The start date is after the end date' : draft.end > todayIso() ? 'The end date is in the future' : undefined}
        onClick={() => { if (valid) onChange({ kind: 'custom', start: draft.start, end: draft.end }); }}>Apply</button>
    </div>
  </div>;
}
const rangeKey = (r: Range) => (r.kind === 'custom' ? `${r.start}..${r.end}` : r.id);

export default function LeadsTab({ clientId, clientName }: { clientId: string; clientName: string }) {
  const [range, setRange] = useState<Range>({ kind: 'preset', id: '90d' });
  const [data, setData] = useState<LeadsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    const query = range.kind === 'custom' ? `start=${range.start}&end=${range.end}` : `period=${range.id}`;
    fetch(`/api/v1/clients/${encodeURIComponent(clientId)}/leads?${query}`, { signal: controller.signal })
      .then(async response => {
        if (response.status === 404) throw new Error('unknown');
        if (response.status === 503) throw new Error('database');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json() as Promise<LeadsData>;
      })
      .then(json => { setData(json); setLoading(false); })
      .catch((reason: Error) => { if (reason.name !== 'AbortError') { setError(reason.message); setLoading(false); } });
    return () => controller.abort();
  }, [clientId, rangeKey(range), attempt]); // eslint-disable-line react-hooks/exhaustive-deps

  const retry = () => setAttempt(a => a + 1);
  if (error && !data) return <div className="leads-tab"><LeadsNotice error={error} clientName={clientName} retry={retry} /></div>;
  if (!data) return <div className="leads-tab"><LeadsSkeleton /></div>;
  const history = Object.values(data.coverage.records).some(n => n > 0);
  if (!data.sub_accounts.length && !history) return <div className="leads-tab"><div className="leads-panel leads-notice"><Info size={20} /><div><h3>No LeadLock sub-account mapped</h3><p>{clientName} has no LeadLock sub-account approved in the KB yet. An admin maps it from the sources list (<code>kb scope-add leadlock location …</code>).</p></div></div></div>;

  const periodInfo = describeRange(range);
  return <div className={`leads-tab ${loading ? 'is-loading' : ''}`} aria-busy={loading}>
    <header className="leads-toolbar">
      <h2>Leads &amp; enquiries</h2>
      <div className="leads-toolbar-right">
        <span className="leads-sync"><RefreshCw size={12} />{data.synced_at ? `${data.collecting ? 'Synced' : 'Not collected since'} ${new Date(data.synced_at).toLocaleString('en-US', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })}` : data.collecting ? 'Not synced yet' : 'Not collected'}</span>
        <RangePicker range={range} onChange={setRange} firstInquiry={data.coverage.first_inquiry} />
      </div>
    </header>

    <KpiRow data={data} periodLong={periodInfo.long} />

    <div className="leads-grid leads-grid-main">
      <MonthlyChart monthly={data.monthly} />
      <Outcomes data={data} periodLabel={periodInfo.phrase} />
    </div>
    <div className="leads-grid leads-grid-two">
      <PipelineMap pipelines={data.pipelines} periodLabel={periodInfo.phrase} />
      <Sources rows={data.sources} periodLabel={periodInfo.label} />
    </div>
    <div className="leads-grid leads-grid-three">
      <Channels channels={data.channels} periodLabel={periodInfo.label} />
      <HBars title="Forms filled in" eyebrow={`Submissions · ${periodInfo.label}`} rows={data.forms} empty="No form submissions in this period." kind="Submissions" />
      <Tours appointments={data.appointments} upcoming={data.kpis.upcoming_tours.value ?? 0} periodLabel={periodInfo.phrase} />
    </div>
  </div>;
}

function Delta({ kpi, periodLong, higherIsBetter = true }: { kpi: Kpi; periodLong: string; higherIsBetter?: boolean }) {
  if (kpi.previous === undefined || kpi.previous === null || kpi.value === null) return null;
  const { value, previous } = kpi;
  if (previous === 0) return <span className="leads-delta">{value ? `New: none in ${periodLong}` : `None in ${periodLong} either`}</span>;
  const change = Math.round((value - previous) / previous * 100);
  if (change === 0) return <span className="leads-delta">Level with {periodLong}</span>;
  const up = change > 0;
  return <span className={`leads-delta ${up === higherIsBetter ? 'is-good' : 'is-bad'}`}>{up ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}{up ? '+' : ''}{change}% vs {periodLong} ({n(previous)})</span>;
}

function Tile({ label, icon, value, children, tone }: { label: string; icon: ReactNode; value: ReactNode; children?: ReactNode; tone?: 'flag' | 'muted' }) {
  return <div className={`leads-kpi ${tone ? `leads-kpi-${tone}` : ''}`}>
    <div className="leads-kpi-label"><span>{label}</span><span className="leads-kpi-icon">{icon}</span></div>
    <div className="leads-kpi-value">{value}</div>
    <div className="leads-kpi-detail">{children}</div>
  </div>;
}

function KpiRow({ data, periodLong }: { data: LeadsData; periodLong: string }) {
  const { kpis, outcomes } = data;
  const allTime = Object.values(outcomes.all_time).reduce((a, b) => a + b, 0);
  const openShare = pct(outcomes.all_time.open ?? 0, allTime);
  const waiting = kpis.awaiting_reply;
  return <section className="leads-kpis" aria-label="Lead headline figures">
    <Tile label="New inquiries" icon={<Inbox size={15} />} value={n(kpis.inquiries.value ?? 0)}>
      <Delta kpi={kpis.inquiries} periodLong={periodLong} />{!periodLong && 'Opportunities created, all time'}
    </Tile>
    <Tile label="Tours booked" icon={<CalendarCheck size={15} />} value={n(kpis.tours_booked.value ?? 0)}>
      <Delta kpi={kpis.tours_booked} periodLong={periodLong} />{!periodLong && 'Appointments not cancelled'}
    </Tile>
    <Tile label="Upcoming tours" icon={<CalendarClock size={15} />} value={n(kpis.upcoming_tours.value ?? 0)}>Booked for the next 30 days</Tile>
    <Tile label="Awaiting reply" icon={<MessageSquareReply size={15} />} value={n(waiting.value)} tone={waiting.value >= 10 ? 'flag' : undefined}>
      {waiting.value ? <>{waiting.value >= 10 && <AlertTriangle size={12} />}Oldest waiting {waiting.oldest_days ?? 0} day{waiting.oldest_days === 1 ? '' : 's'}</> : 'No unread inbound threads in this period'}
      {waiting.older_unread > 0 && <span className="leads-kpi-aside">+{n(waiting.older_unread)} older thread{waiting.older_unread === 1 ? '' : 's'} still unread in LeadLock</span>}
    </Tile>
    {kpis.won.tracked
      ? <Tile label="Marked won" icon={<Trophy size={15} />} value={n(kpis.won.value ?? 0)}><Delta kpi={kpis.won} periodLong={periodLong} />{!periodLong && 'Marked won in LeadLock, any inquiry date'}</Tile>
      : <Tile label="Won" icon={<Trophy size={15} />} value="Not tracked" tone="muted">{openShare}% of opportunities are still open: this venue doesn’t mark won or lost in LeadLock</Tile>}
  </section>;
}

function MonthlyChart({ monthly }: { monthly: LeadsData['monthly'] }) {
  const total = monthly.reduce((a, m) => ({ inquiries: a.inquiries + m.inquiries, tours: a.tours + m.tours }), { inquiries: 0, tours: 0 });
  const option = useMemo<ChartOption>(() => ({
    grid: { left: 4, right: 8, top: 14, bottom: 2, containLabel: true },
    tooltip: {
      ...TOOLTIP, trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(80,112,224,.07)' } },
      formatter: (items: unknown) => {
        const m = monthly[(items as { dataIndex: number }[])[0].dataIndex];
        return `<b style="color:${INK.primary}">${monthLabel(m.month, true)}</b>` + tooltipRow(SERIES.inquiries, 'Inquiries', n(m.inquiries)) + tooltipRow(SERIES.tours, 'Tours held', n(m.tours));
      },
    },
    xAxis: { type: 'category', data: monthly.map(m => monthLabel(m.month)), axisTick: { show: false }, axisLine: { lineStyle: { color: INK.axis } }, axisLabel: { color: INK.muted, fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1, splitNumber: 4, axisLabel: { color: INK.muted, fontSize: 10 }, splitLine: { lineStyle: { color: INK.grid } } },
    series: [
      { name: 'Inquiries', type: 'bar', data: monthly.map(m => m.inquiries), barMaxWidth: 16, barGap: '12%', itemStyle: { color: SERIES.inquiries, borderRadius: [4, 4, 0, 0] } },
      { name: 'Tours held', type: 'bar', data: monthly.map(m => m.tours), barMaxWidth: 16, itemStyle: { color: SERIES.tours, borderRadius: [4, 4, 0, 0] } },
    ],
  }), [monthly]);
  return <section className="leads-panel leads-monthly">
    <div className="leads-panel-head">
      <div><p className="leads-eyebrow">Last 12 months</p><h3>Inquiries and tours by month</h3></div>
    </div>
    <div className="leads-legend">
      <span><i style={{ background: SERIES.inquiries }} />Inquiries <b>{n(total.inquiries)}</b></span>
      <span><i style={{ background: SERIES.tours }} />Tours held <b>{n(total.tours)}</b></span>
    </div>
    <EChart option={option} height={248} label={`Inquiries and tours held per month, last 12 months: ${monthly.map(m => `${monthLabel(m.month, true)} ${m.inquiries} inquiries, ${m.tours} tours`).join('; ')}`} />
  </section>;
}

type OutcomeRow = (typeof OUTCOME_ORDER)[number] & { count: number };

/** One horizontal stacked bar (ECharts) of outcome rows, with a hover tooltip per segment. */
function OutcomeStack({ rows, label }: { rows: OutcomeRow[]; label: string }) {
  const total = rows.reduce((a, r) => a + r.count, 0);
  const option = useMemo<ChartOption>(() => ({
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: { type: 'value', show: false, max: total },
    yAxis: { type: 'category', show: false, data: ['Inquiries'] },
    tooltip: { ...TOOLTIP, trigger: 'item', formatter: (p: unknown) => { const r = rows[(p as { seriesIndex: number }).seriesIndex]; return tooltipRow(r.color, r.label, `${n(r.count)} · ${pct(r.count, total)}%`); } },
    series: rows.map((r, i) => ({
      name: r.label, type: 'bar', stack: 'all', data: [r.count], barWidth: 18,
      itemStyle: { color: r.color, borderColor: '#fff', borderWidth: 1, borderRadius: rows.length === 1 ? 6 : i === 0 ? [6, 0, 0, 6] : i === rows.length - 1 ? [0, 6, 6, 0] : 0 },
    })),
  }), [rows, total]);
  return <EChart option={option} height={22} className="leads-stack-chart" label={label} />;
}

function OutcomeList({ rows }: { rows: OutcomeRow[] }) {
  const total = rows.reduce((a, r) => a + r.count, 0);
  return <ul className="leads-outcome-list">{rows.map(r => <li key={r.id}><i style={{ background: r.color }} /><span>{r.label}</span><b>{n(r.count)}</b><em>{pct(r.count, total)}%</em></li>)}</ul>;
}

/*
 * "Where they stand now", two views while we choose one (5 Nov):
 *   split   decided vs still open as a meter, then how the decided ones went (won / lost / abandoned) with a win
 *           rate. Open is 63-100% at every pilot venue, so taking it out is what makes won/lost readable.
 *   all     the original: all four outcomes in one stacked bar and a list.
 * Outcome colours are the same in both views (won aqua, lost orange, abandoned violet).
 */
function Outcomes({ data, periodLabel }: { data: LeadsData; periodLabel: string }) {
  const [view, setView] = useState<'split' | 'all'>('split');
  const counts = data.outcomes.counts;
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const rows = useMemo(() => OUTCOME_ORDER.map(o => ({ ...o, count: counts[o.id] ?? 0 })).filter(o => o.count), [counts]);
  const decidedRows = rows.filter(r => r.id !== 'open');
  const decided = decidedRows.reduce((a, r) => a + r.count, 0);
  const open = counts.open ?? 0;
  const won = counts.won ?? 0;
  const tracked = data.outcomes.tracked;
  const caveat = <p className="leads-caveat"><Info size={13} />This venue rarely closes opportunities in LeadLock, so “open” includes leads that went cold or booked elsewhere. Read progress from the pipeline stages instead.</p>;
  return <section className="leads-panel leads-outcomes">
    <div className="leads-panel-head"><div><p className="leads-eyebrow">Inquiries from {periodLabel}</p><h3>Where they stand now</h3></div>
      {total > 0 && <div className="leads-view-toggle" role="group" aria-label="Show as">
        <button aria-pressed={view === 'split'} className={view === 'split' ? 'selected' : ''} onClick={() => setView('split')}>Decided split</button>
        <button aria-pressed={view === 'all'} className={view === 'all' ? 'selected' : ''} onClick={() => setView('all')}>All outcomes</button>
      </div>}</div>
    {!total ? <p className="leads-empty">No inquiries in this period.</p>
      : view === 'all' ? <>
        <OutcomeStack rows={rows} label={rows.map(r => `${r.label} ${r.count}`).join(', ')} />
        <OutcomeList rows={rows} />
        {!tracked && caveat}
      </>
      : <>
        <div className="leads-decided">
          <div className="leads-decided-head"><span>Decided</span><b>{n(decided)} <em>of {n(total)}</em></b><span className="leads-decided-share">{pct(decided, total)}%</span></div>
          <div className="leads-meter" role="img" aria-label={`${n(decided)} of ${n(total)} inquiries decided, ${n(open)} still open`}>
            <i style={{ width: `${decided ? Math.max(1.5, (decided / total) * 100) : 0}%` }} />
          </div>
          <p className="leads-decided-foot">{n(open)} still open</p>
        </div>
        {tracked && decided > 0 ? <div className="leads-winrate">
          <div className="leads-winrate-head">
            <div><p className="leads-eyebrow">How the decided ones went</p><p className="leads-winrate-value">{pct(won, decided)}%<span>win rate</span></p></div>
            <p className="leads-winrate-note">{n(won)} of {n(decided)} decided inquiries were marked won</p>
          </div>
          <OutcomeStack rows={decidedRows} label={`Decided inquiries: ${decidedRows.map(r => `${r.label} ${r.count}`).join(', ')}`} />
          <OutcomeList rows={decidedRows} />
        </div>
          : tracked ? <p className="leads-empty">None of this period’s inquiries has been marked won, lost or abandoned yet.</p>
          : <>{caveat}{decided > 0 && <p className="leads-decided-few">Only {n(decided)} marked: {decidedRows.map(r => `${n(r.count)} ${r.label.toLowerCase()}`).join(', ')}. Too few to read a win rate from.</p>}</>}
      </>}
  </section>;
}

/** White or dark ink, whichever reads better on a tile colour (WCAG contrast). */
function inkOn(hex: string) {
  const channel = (i: number) => { const c = parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16) / 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  const lum = 0.2126 * channel(0) + 0.7152 * channel(1) + 0.0722 * channel(2);
  const ink = 0.2126 * 0.0137 + 0.7152 * 0.0409 + 0.0722 * 0.1248; // INK.primary #1f3a63, linearised
  return (1.05) / (lum + 0.05) >= (lum + 0.05) / (ink + 0.05) ? '#fff' : INK.primary;
}
const richSafe = (text: string) => text.replace(/[{}]/g, m => (m === '{' ? '(' : ')'));

interface StageTile { name: string; value: number; count: number; pipeline: string; pipelineTotal: number; step: number; steps: number; ordered: boolean }

/*
 * Heat shading for stage tiles: the dataviz sequential blue ramp (step 150 -> 700), light = few inquiries,
 * dark = many. Pipelines stay neutral frames, so colour only ever means "how many inquiries sit here".
 * Counts are heavily skewed (one stage can hold 900 while the rest hold 1-40), so a continuous scale paints
 * nearly everything the same shade. Instead the tiles are split into up to five bands by quantile (about a
 * fifth of the tiles each), every band a clearly different step, and the legend prints each band's real range.
 */
const HEAT_RAMP = ['#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7', '#3987e5', '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281', '#0d366b'];
const HEAT_BANDS = 5;
interface HeatBand { lo: number; hi: number; colour: string; tiles: number }

function heatBands(values: number[]): HeatBand[] {
  const v = values.filter(x => x > 0).sort((a, b) => a - b);
  if (!v.length) return [];
  const k = Math.min(HEAT_BANDS, new Set(v).size);
  const cuts: number[] = [];
  for (let c = 1; c <= k; c++) {
    const cut = v[Math.ceil((c * v.length) / k) - 1];
    if (!cuts.length || cut > cuts[cuts.length - 1]) cuts.push(cut);
  }
  const bands: HeatBand[] = [];
  cuts.forEach((hi, i) => {
    const inBand = v.filter(x => x <= hi && (i === 0 || x > cuts[i - 1]));
    const prev = bands[bands.length - 1];
    // Near-ties share a shade: with few tiles, quantiles would otherwise paint 35 and 38 differently.
    if (prev && inBand[0] <= prev.hi * 1.1) { prev.hi = hi; prev.tiles += inBand.length; }
    else bands.push({ lo: inBand[0], hi, tiles: inBand.length, colour: '' });
  });
  const last = HEAT_RAMP.length - 1;
  bands.forEach((b, i) => { b.colour = HEAT_RAMP[bands.length === 1 ? 6 : Math.round((i * last) / (bands.length - 1))]; });
  return bands;
}
const bandOf = (bands: HeatBand[], value: number) => bands.find(b => value <= b.hi) ?? bands[bands.length - 1];
const bandLabel = (b: HeatBand) => (b.lo === b.hi ? n(b.lo) : `${n(b.lo)}–${n(b.hi)}`);
const FRAME = '#e3e9f2';
/* Stages with no inquiries in the period: one small fixed-size tile each, drawn as an empty slot (near-white fill,
 * grey outline, muted text) so they read as "nothing here" and never as the palest blue band. */
const ZERO_FILL = '#f7f9fc', ZERO_LINE = '#d3dae6';
const ZERO_TILE_PX = 64 * 36;
const ZERO_RICH = { name: { fontSize: 9, lineHeight: 14, color: INK.muted }, count: { fontSize: 10, fontWeight: 600, lineHeight: 14, color: INK.secondary } };

function HeatScale({ bands, zero, empty }: { bands: HeatBand[]; zero: boolean; empty?: { on: boolean; toggle: () => void } }) {
  return <div className="leads-heat-scale">
    {empty && <button type="button" role="switch" aria-checked={empty.on} className={`leads-switch ${empty.on ? 'is-on' : ''}`} onClick={empty.toggle}>
      <span className="leads-switch-track" aria-hidden="true"><i /></span>Show empty stages
    </button>}
    <span className="leads-heat-caption">Inquiries in a stage</span>
    <ul aria-label="Shade key: inquiries in a stage">
      {zero && <li className="leads-heat-zero"><i style={{ background: ZERO_FILL, boxShadow: `inset 0 0 0 1px ${ZERO_LINE}` }} />0</li>}
      {bands.map(b => <li key={b.hi}><i style={{ background: b.colour }} />{bandLabel(b)}</li>)}
    </ul>
  </div>;
}

/*
 * Readable sizing. A true-to-scale treemap turns a small pipeline (Dos Palomas' DND: 38 of 1,081) or a
 * one-inquiry stage into a sliver whose label can't fit. So every tile gets a floor in pixels, worked out
 * from the chart's measured width: a stage at least big enough for its name and count, a pipeline at least
 * wide enough for its header. Bigger items share what's left in proportion to their counts. Labels, tooltips
 * and shading always use the exact counts; only the area of the smallest items is rounded up.
 */
/** Rough label width at the 10.5px label font: capitals and digits run wider than lower case. */
const textPx = (text: string) => [...text].reduce((a, ch) => a + (/[A-Z0-9]/.test(ch) ? 7.2 : /[\s.,'’·&/-]/.test(ch) ? 3.4 : 5.6), 0);
/** Smallest area at which this stage's name (up to ~110px; longer ones may still end in "…") and its count
 *  fit. Tiles come out up to ~1.6:1, so the floor is sized for the narrow way round. */
const tileFloorPx = (name: string) => { const w = Math.min(textPx(name), 110) + 16; return Math.max(76 * 48, 1.6 * w * w); };
const PIPE_MIN_PX = 130 * 120;   // a pipeline header ("DND · 38") plus one tile
const PIPE_MIN_W = 116;          // narrowest a pipeline column may get
const FRAME_SHARE = 0.82;        // what's left of a pipeline once its header and gaps are taken
const MAP_MIN_H = 380, MAP_MAX_H = 640;
const SIZE_ROOM = 1.6;           // map area per unit of floors: what's left over keeps big stages visibly bigger
const SMALL_TILE_RICH = { name: { fontSize: 9.5, lineHeight: 13 }, count: { fontSize: 12.5, fontWeight: 600, lineHeight: 17 } };

/** Shares of 1 that follow `values`, except that no item drops below its floor (water-filling). */
function fitShares(values: number[], floors: number[]): number[] {
  const sumFloors = floors.reduce((a, b) => a + b, 0);
  const f = sumFloors > 0.9 ? floors.map(x => (x * 0.9) / sumFloors) : floors;
  const pinned = new Set<number>();
  for (;;) {
    const free = values.map((_, i) => i).filter(i => !pinned.has(i));
    if (!free.length) { const sf = f.reduce((a, b) => a + b, 0); return f.map(x => x / sf); }
    const room = 1 - [...pinned].reduce((a, i) => a + f[i], 0);
    const k = room / free.reduce((a, i) => a + values[i], 0);
    const newly = free.filter(i => values[i] * k < f[i]);
    if (!newly.length) return values.map((v, i) => (pinned.has(i) ? f[i] : v * k));
    newly.forEach(i => pinned.add(i));
  }
}

function useWidth() {
  const [el, setEl] = useState<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(640);
  useEffect(() => {
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setWidth(Math.max(280, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, [el]);
  return [setEl, width] as const;
}

function PipelineMap({ pipelines: raw, periodLabel }: { pipelines: LeadsData['pipelines']; periodLabel: string }) {
  // Name the business when a client has several sub-accounts ("DJ Hybrid Chicago · Inquiry").
  const pipelines = useMemo(() => {
    const multi = new Set(raw.map(p => p.sub_account)).size > 1;
    return raw.map(p => ({ ...p, pipeline: multi && p.sub_account ? `${p.sub_account} · ${p.pipeline}` : p.pipeline }));
  }, [raw]);
  const used = useMemo(() => pipelines.filter(p => p.total), [pipelines]);
  const total = used.reduce((a, p) => a + p.total, 0);
  const bands = useMemo(() => heatBands(used.flatMap(p => p.stages.map(s => s.count))), [used]);
  const emptyStages = used.reduce((a, p) => a + p.stages.filter(s => !s.count).length, 0);
  const [showEmpty, setShowEmpty] = useState(true);
  const [measure, width] = useWidth();
  // On-screen area per pipeline and stage: exact share where it is readable, the floor where it isn't.
  // Many stages (or long stage names) make the map taller rather than the tiles smaller.
  const { layout, height } = useMemo(() => {
    // Stages with inquiries are always drawn; empty ones get the fixed small tile while "Show empty stages" is on.
    const live = used.map(p => p.stages.map((s, i) => ({ s, i, floor: s.count ? tileFloorPx(s.stage) : ZERO_TILE_PX })).filter(x => showEmpty || x.s.count));
    const pipeFloorPx = live.map(st => Math.max(PIPE_MIN_PX, st.reduce((a, x) => a + x.floor, 0) / FRAME_SHARE));
    const h = Math.min(MAP_MAX_H, Math.max(MAP_MIN_H, Math.ceil((pipeFloorPx.reduce((a, b) => a + b, 0) * SIZE_ROOM) / width)));
    const area = width * h;
    // A small pipeline is laid out as a full-height strip, so its floor is also a width (room for its header).
    const pipeShares = fitShares(used.map(p => p.total), pipeFloorPx.map(px => Math.max(px / area, PIPE_MIN_W / width)));
    return {
      height: h,
      layout: live.map((st, k) => {
        const room = area * pipeShares[k] * FRAME_SHARE;
        const stageShares = fitShares(st.map(({ s }) => s.count), st.map(x => x.floor / room));
        return st.map(({ s, i, floor }, j) => ({ s, i, size: pipeShares[k] * stageShares[j] * 100000, cramped: room * stageShares[j] < floor * 0.95 }));
      }),
    };
  }, [used, width, showEmpty]);
  const option = useMemo<ChartOption>(() => {
    const data = used.map((p, k) => ({
      name: p.pipeline, value: layout[k].reduce((a, x) => a + x.size, 0), count: p.total,
      children: layout[k].map(({ s, i, size, cramped }) => {
        if (!s.count) return {
          name: s.stage, value: size, count: 0, pipeline: p.pipeline, pipelineTotal: p.total, step: i + 1, steps: p.stages.length, ordered: p.ordered,
          itemStyle: { color: ZERO_FILL, borderColor: ZERO_LINE, borderWidth: 1 }, label: { rich: ZERO_RICH },
          emphasis: { itemStyle: { color: '#eef2f8', borderColor: ZERO_LINE } },
        };
        const color = bandOf(bands, s.count).colour;
        return {
          name: s.stage, value: size, count: s.count, pipeline: p.pipeline, pipelineTotal: p.total, step: i + 1, steps: p.stages.length, ordered: p.ordered,
          itemStyle: { color },
          // A tile that couldn't get its full floor (a very crowded map) uses a smaller label.
          label: { color: inkOn(color), ...(cramped ? { rich: SMALL_TILE_RICH } : {}) },
        };
      }),
    }));
    return {
      tooltip: { ...TOOLTIP, trigger: 'item', formatter: (p: unknown) => {
        const { data: d, treePathInfo } = p as { data: Partial<StageTile> & { children?: unknown[] }; treePathInfo: unknown[] };
        if (treePathInfo.length <= 1) return `<b style="color:${INK.primary}">All pipelines</b>` + tooltipRow(NEUTRAL, 'Inquiries', n(total));
        if (d.children) return `<b style="color:${INK.primary}">${escapeHtml(d.name ?? '')}</b>` + tooltipRow(NEUTRAL, 'Inquiries', `${n(d.count ?? 0)} · ${pct(d.count ?? 0, total)}% of all`);
        const t = d as StageTile;
        if (!t.count) return `<b style="color:${INK.primary}">${escapeHtml(t.pipeline)} › ${escapeHtml(t.name)}</b><div style="margin-top:3px">No inquiries here in this period</div>`
          + (t.ordered ? `<div style="margin-top:6px;color:${INK.muted}">Stage ${t.step} of ${t.steps} in LeadLock</div>` : '');
        return `<b style="color:${INK.primary}">${escapeHtml(t.pipeline)} › ${escapeHtml(t.name)}</b>` + tooltipRow(bandOf(bands, t.count).colour, 'Inquiries now here', `${n(t.count)} · ${pct(t.count, t.pipelineTotal)}% of pipeline`)
          + (t.ordered ? `<div style="margin-top:6px;color:${INK.muted}">Stage ${t.step} of ${t.steps} in LeadLock</div>` : '');
      } },
      series: [{
        type: 'treemap', name: 'All pipelines', data, roam: false, nodeClick: false, cursor: 'default', left: 0, right: 0, top: 0, bottom: 0,
        squareRatio: 0.55 * (1 + Math.sqrt(5)), visibleMin: 1, breadcrumb: { show: false },
        // 'break' would wrap long names, but ECharts then drops the line break before the count ("Inquired923").
        label: { show: true, overflow: 'truncate', ellipsis: '…', fontSize: 10.5, lineHeight: 15,
          // Empty stages are short tiles: one line with the 0 first, so truncation only ever cuts the name.
          formatter: (p: unknown) => { const { name, data } = p as { name: string; data: { count: number } }; return data.count ? `{name|${richSafe(name)}}\n{count|${n(data.count)}}` : `{count|0}  {name|${richSafe(name)}}`; },
          rich: { name: { fontSize: 10.5, lineHeight: 15 }, count: { fontSize: 15, fontWeight: 600, lineHeight: 20 } } },
        upperLabel: { show: true, height: 24, fontSize: 11, fontWeight: 600, color: INK.primary, overflow: 'truncate', ellipsis: '…',
          formatter: (p: unknown) => { const { name, data } = p as { name: string; data: { count: number } }; return `${richSafe(name)}  ·  ${n(data.count)}`; } },
        levels: [
          { itemStyle: { borderWidth: 0, gapWidth: 6 }, upperLabel: { show: false } },
          { itemStyle: { color: FRAME, borderColor: FRAME, borderWidth: 3, gapWidth: 2, borderRadius: 6 },
            emphasis: { itemStyle: { borderColor: '#cfd9e8' } } },
          { itemStyle: { borderColor: '#fff', borderWidth: 0, gapWidth: 2, borderRadius: 4 }, emphasis: { itemStyle: { borderColor: '#fff' } } },
        ],
      }],
    };
  }, [used, bands, total, layout]);
  return <section className="leads-panel leads-pipelines">
    <div className="leads-panel-head"><div><p className="leads-eyebrow">Pipeline stages · inquiries from {periodLabel}</p><h3>Where inquiries sit</h3>
      <p className="leads-sub">{total ? `${n(total)} inquiries across ${used.length} pipeline${used.length === 1 ? '' : 's'}, by their current stage. Bigger, darker tiles hold more inquiries.` : ''}</p></div>
      {total > 0 && <HeatScale bands={bands} zero={showEmpty && emptyStages > 0}
        empty={emptyStages > 0 ? { on: showEmpty, toggle: () => setShowEmpty(v => !v) } : undefined} />}</div>
    {total > 0
      ? <>
        <div ref={measure}><EChart option={option} height={height} label={`Inquiries by pipeline and stage: ${used.map(p => `${p.pipeline} ${p.total} (${p.stages.filter(s => s.count).map(s => `${s.stage} ${s.count}`).join(', ')})`).join('; ')}`} /></div>
      </>
      : <p className="leads-empty">No inquiries in this period.</p>}
  </section>;
}

/** Categorical colour by slot; "Not recorded", "Other" and "Remaining" stay neutral so they never take a hue. */
function colourSlices(rows: Row[]) {
  let slot = 0;
  return rows.map(r => ({ ...r, color: r.label === 'Not recorded' ? NOT_RECORDED : r.label === OTHER || r.label === REMAINING ? NEUTRAL : PALETTE[slot++ % PALETTE.length] }));
}

function sliceTooltip(total: number, hint: (name: string) => string) {
  return { ...TOOLTIP, trigger: 'item', formatter: (p: unknown) => {
    const { name, value, color } = p as { name: string; value: number; color: string };
    return `<b style="color:${INK.primary}">${escapeHtml(name)}</b>` + tooltipRow(color, `${n(value)} contact${value === 1 ? '' : 's'}`, `${pct(value, total) || '<1'}%`) + hint(name);
  } };
}

function Sources({ rows, periodLabel }: { rows: Row[]; periodLabel: string }) {
  const [showOther, setShowOther] = useState(false);
  const total = rows.reduce((a, r) => a + r.count, 0);
  const rest = useMemo(() => rows.slice(TOP_SOURCES), [rows]);
  const slices = useMemo(() => colourSlices([...rows.slice(0, TOP_SOURCES), ...(rest.length ? [{ label: OTHER, count: rest.reduce((a, r) => a + r.count, 0) }] : [])]), [rows, rest]);
  const option = useMemo<ChartOption>(() => ({
    tooltip: sliceTooltip(total, name => name === OTHER ? `<div style="margin-top:6px;color:${INK.muted}">${rest.length} smaller sources · click to see them</div>` : ''),
    title: { text: n(total), subtext: 'new contacts', left: 'center', top: 'middle', itemGap: 2,
      textStyle: { fontFamily: SERIF, fontSize: 24, fontWeight: 500, color: INK.primary }, subtextStyle: { fontSize: 10, color: INK.muted } },
    series: [{
      type: 'pie', radius: ['46%', '66%'], center: ['50%', '50%'], avoidLabelOverlap: true,
      // Each slice is named on the chart itself (no legend): identity never rests on colour alone.
      label: { show: true, formatter: (p: unknown) => {
        const { name, value, percent } = p as { name: string; value: number; percent: number };
        const short = name.length > 26 ? `${name.slice(0, 25)}…` : name;
        return `{name|${richSafe(name === OTHER ? `Other · ${rest.length} sources` : short)}}\n{pct|${Math.round(percent)}%}{count|  ${n(value)}}`;
      }, rich: { name: { color: INK.secondary, fontSize: 10.5, lineHeight: 15 }, pct: { color: INK.primary, fontSize: 11.5, fontWeight: 600, lineHeight: 17 }, count: { color: INK.muted, fontSize: 10, lineHeight: 17 } } },
      labelLine: { show: true, length: 10, length2: 14, lineStyle: { color: '#cdd6e6' } },
      labelLayout: { hideOverlap: false, moveOverlap: 'shiftY' },
      itemStyle: { borderColor: '#fff', borderWidth: 2, borderRadius: 4 }, emphasis: { scale: true, scaleSize: 5 },
      data: slices.map(s => ({ name: s.label, value: s.count, itemStyle: { color: s.color } })),
    }],
  }), [slices, total, rest.length]);
  return <section className="leads-panel leads-sources">
    <div className="leads-panel-head"><div><p className="leads-eyebrow">New contacts · {periodLabel}</p><h3>Where leads come from</h3></div></div>
    {total ? <>
      <EChart option={option} height={300} label={`Lead sources: ${slices.map(s => `${s.label} ${s.count}`).join(', ')}`} onClick={p => { if (p.name === OTHER) setShowOther(true); }} />
      {rest.length > 0 && <button type="button" className="leads-other-link leads-other-cta" onClick={() => setShowOther(true)}>
        <i style={{ background: NEUTRAL }} />See the {rest.length} other source{rest.length === 1 ? '' : 's'} ({n(rest.reduce((a, r) => a + r.count, 0))} contacts)<ArrowUpRight size={12} />
      </button>}
    </> : <p className="leads-empty">No new contacts in this period.</p>}
    {showOther && <OtherSources rows={rest} total={total} periodLabel={periodLabel} onClose={() => setShowOther(false)} />}
  </section>;
}

function OtherSources({ rows, total, periodLabel, onClose }: { rows: Row[]; total: number; periodLabel: string; onClose: () => void }) {
  const otherTotal = rows.reduce((a, r) => a + r.count, 0);
  // A pie stays readable to about 8 slices: the rest fold into "Remaining", and the table lists every source.
  const folded = rows.length > OTHER_PIE_MAX;
  const slices = useMemo(() => colourSlices(folded
    ? [...rows.slice(0, OTHER_PIE_MAX - 1), { label: REMAINING, count: rows.slice(OTHER_PIE_MAX - 1).reduce((a, r) => a + r.count, 0) }]
    : rows), [rows, folded]);
  const colourOf = (label: string) => slices.find(s => s.label === label)?.color ?? NEUTRAL;
  const option = useMemo<ChartOption>(() => ({
    tooltip: sliceTooltip(total, name => `<div style="margin-top:6px;color:${INK.muted}">${name === REMAINING ? `${rows.length - OTHER_PIE_MAX + 1} sources, listed in the table · ` : ''}% of all new contacts</div>`),
    series: [{ type: 'pie', radius: ['0%', '86%'], label: { show: false }, labelLine: { show: false },
      itemStyle: { borderColor: '#fff', borderWidth: 2 }, emphasis: { scale: true, scaleSize: 5 },
      data: slices.map(s => ({ name: s.label, value: s.count, itemStyle: { color: s.color } })) }],
  }), [slices, total, rows.length]);
  return <Dialog title="Other lead sources" subtitle={`Where leads come from · ${periodLabel}`} size="lg" onClose={onClose}
    meta={<span>{rows.length} sources · {n(otherTotal)} of {n(total)} new contacts ({pct(otherTotal, total) || '<1'}%)</span>}>
    <div className="leads-other-modal">
      <EChart option={option} height={260} label={`Other lead sources: ${rows.map(r => `${r.label} ${r.count}`).join(', ')}`} />
      <table className="leads-table">
        <thead><tr><th>Source</th><th>Contacts</th><th>Of all</th></tr></thead>
        <tbody>{rows.map(r => <tr key={r.label}>
          <td><span className="leads-swatch-cell"><i style={{ background: colourOf(r.label) }} />{r.label}</span></td>
          <td>{n(r.count)}</td><td>{pct(r.count, total) || '<1'}%</td>
        </tr>)}</tbody>
      </table>
    </div>
  </Dialog>;
}

function HBars({ title, eyebrow, rows, empty, kind }: { title: string; eyebrow: string; rows: Row[]; empty: string; kind: string }) {
  const total = rows.reduce((a, r) => a + r.count, 0);
  const option = useMemo<ChartOption>(() => ({
    grid: { left: 0, right: 44, top: 2, bottom: 2, containLabel: true },
    tooltip: { ...TOOLTIP, trigger: 'item', formatter: (p: unknown) => { const r = rows[(p as { dataIndex: number }).dataIndex]; return `<b style="color:${INK.primary}">${escapeHtml(r.label)}</b>` + tooltipRow(r.label === OTHER ? NEUTRAL : SERIES.inquiries, kind, `${n(r.count)} · ${pct(r.count, total)}%`); } },
    xAxis: { type: 'value', show: false },
    yAxis: { type: 'category', inverse: true, data: rows.map(r => r.label), axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: INK.secondary, fontSize: 10.5, width: 150, overflow: 'truncate' } },
    series: [{ type: 'bar', barWidth: 10, showBackground: true, backgroundStyle: { color: '#eef3fc', borderRadius: 4 },
      label: { show: true, position: 'right', color: INK.primary, fontSize: 10.5, fontWeight: 600, formatter: (p: unknown) => n((p as { value: number }).value) },
      data: rows.map(r => ({ value: r.count, itemStyle: { color: r.label === OTHER ? NEUTRAL : SERIES.inquiries, borderRadius: 4 } })) }],
  }), [rows, total, kind]);
  return <section className="leads-panel">
    <div className="leads-panel-head"><div><p className="leads-eyebrow">{eyebrow}</p><h3>{title}</h3></div></div>
    {rows.length ? <EChart option={option} height={rows.length * 32 + 8} label={`${title}: ${rows.map(r => `${r.label} ${r.count}`).join(', ')}`} /> : <p className="leads-empty">{empty}</p>}
  </section>;
}

function Channels({ channels, periodLabel }: { channels: LeadsData['channels']; periodLabel: string }) {
  const waiting = channels.reduce((a, c) => a + c.awaiting, 0);
  const option = useMemo<ChartOption>(() => ({
    grid: { left: 0, right: 44, top: 2, bottom: 2, containLabel: true },
    tooltip: { ...TOOLTIP, trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(80,112,224,.06)' } }, formatter: (items: unknown) => {
      const c = channels[(items as { dataIndex: number }[])[0].dataIndex];
      return `<b style="color:${INK.primary}">${escapeHtml(c.label)}</b>` + tooltipRow(SERIES.inquiries, 'Read or answered', n(c.count - c.awaiting)) + tooltipRow(SERIES.tours, 'Awaiting reply', n(c.awaiting));
    } },
    xAxis: { type: 'value', show: false },
    yAxis: { type: 'category', inverse: true, data: channels.map(c => c.label), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: INK.secondary, fontSize: 10.5, width: 110, overflow: 'truncate' } },
    series: [
      { name: 'Read or answered', type: 'bar', stack: 'c', barWidth: 10, data: channels.map(c => c.count - c.awaiting), itemStyle: { color: SERIES.inquiries, borderRadius: 4 } },
      { name: 'Awaiting reply', type: 'bar', stack: 'c', barWidth: 10, data: channels.map(c => c.awaiting), itemStyle: { color: SERIES.tours, borderRadius: 4, borderColor: '#fff', borderWidth: 1 },
        label: { show: true, position: 'right', color: INK.primary, fontSize: 10.5, fontWeight: 600, formatter: (p: unknown) => n(channels[(p as { dataIndex: number }).dataIndex].count) } },
    ],
  }), [channels]);
  return <section className="leads-panel">
    <div className="leads-panel-head"><div><p className="leads-eyebrow">Conversations active · {periodLabel}</p><h3>Channels</h3></div></div>
    {channels.length ? <>
      <div className="leads-legend"><span><i style={{ background: SERIES.inquiries }} />Read or answered</span><span><i style={{ background: SERIES.tours }} />Awaiting reply <b>{n(waiting)}</b></span></div>
      <EChart option={option} height={channels.length * 32 + 8} label={`Conversations by channel: ${channels.map(c => `${c.label} ${c.count}, ${c.awaiting} awaiting`).join('; ')}`} />
    </> : <p className="leads-empty">No conversations in this period.</p>}
  </section>;
}

function Tours({ appointments, upcoming, periodLabel }: { appointments: Record<string, number>; upcoming: number; periodLabel: string }) {
  const total = Object.values(appointments).reduce((a, b) => a + b, 0);
  const rows = Object.entries(appointments).sort((a, b) => b[1] - a[1]);
  const cancelled = (appointments.cancelled ?? 0) + (appointments.noshow ?? 0);
  return <section className="leads-panel leads-tours">
    <div className="leads-panel-head"><div><p className="leads-eyebrow">Tours dated in {periodLabel}</p><h3>Tours</h3></div></div>
    {total ? <>
      <div className="leads-tour-figures">
        <div><b>{n(total)}</b><span>on the calendar</span></div>
        <div><b>{pct(cancelled, total)}%</b><span>cancelled or no-show</span></div>
        <div><b>{n(upcoming)}</b><span>in the next 30 days</span></div>
      </div>
      <ul className="leads-chips">{rows.map(([status, count]) => <li key={status} className={`leads-chip leads-chip-${status}`}>{TOUR_STATUS[status] ?? status}<b>{n(count)}</b></li>)}</ul>
    </> : <p className="leads-empty">No tours in this period.</p>}
  </section>;
}

function LeadsSkeleton() {
  return <div className="leads-skeleton" aria-busy="true" aria-label="Loading leads">
    <div className="leads-kpis">{Array.from({ length: 5 }, (_, i) => <div key={i} className="leads-kpi leads-shimmer" />)}</div>
    <div className="leads-grid leads-grid-main"><div className="leads-panel leads-shimmer" style={{ height: 320 }} /><div className="leads-panel leads-shimmer" style={{ height: 320 }} /></div>
  </div>;
}

function LeadsNotice({ error, clientName, retry }: { error: string; clientName: string; retry: () => void }) {
  if (error === 'unknown') return <div className="leads-panel leads-notice"><Info size={20} /><div><h3>No lead data for {clientName}</h3><p>This client isn’t in the KB database the API is reading.</p></div></div>;
  const body = error === 'database'
    ? <>The KB database isn’t running. It runs in Docker Desktop, so start Docker Desktop, wait for the <code>wia-kb</code> database to come up, then retry.</>
    : <>The Leads tab reads the local KB API on port 8010 and couldn’t reach it ({error}). Start the <code>kb-api</code> launch configuration, then retry.</>;
  return <div className="leads-panel leads-notice is-error"><AlertTriangle size={20} /><div><h3>{error === 'database' ? 'The KB database is offline' : 'Lead figures couldn’t load'}</h3><p>{body}</p><button type="button" className="leads-retry" onClick={retry}><RefreshCw size={12} />Retry</button></div></div>;
}
