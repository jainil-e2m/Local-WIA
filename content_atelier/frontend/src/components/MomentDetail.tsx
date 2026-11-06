import React, { useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { ArrowLeft, ExternalLink } from 'lucide-react';
import { MOMENT_TOPIC_READS, changeMomentTopics, useMoment, useTopics, type MomentDetail, type MomentTopic } from '../api/moments';
import { useInvalidate } from '../api/query';
import { errorMessage } from '../api/client';
import { paths } from '../app/routes';
import { callLabel, clock, sourceLabel } from '../utils/documents';
import { useMe } from '../utils/me';
import {
  CONSENT_HINTS, UNVERIFIED_NOTE, approvalLabel, consentLabel, consentReasons, evidenceRoleLabel, failedChecks, highlight, repairNote,
  speakerLabel, whenLine,
} from '../utils/moments';
import { ConsentBadge } from './MomentsLedger';
import { PageHeading } from './PageHeading';
import { PANEL, Pill, QUIET_BUTTON, SELECT, StatusLine, TEXT_BUTTON } from './AdminParts';
import { ErrorState, LoadingState } from './shared/states';
import { Select } from './ThemedSelect';

/* One moment at a path of its own (2.F2): the scene, the exact quote, the conversation around it with the quote marked,
   who said it and in what role, when, the recording when the source has one, whether it may be used and why, its topics,
   the checks that failed and the cards that cite it. Written for a reviewer: no passage IDs or offsets on the surface. An
   editor may add or remove topics; nothing else here changes a moment. */

const term = 'text-[11px] font-semibold uppercase tracking-[0.1em] text-[#A38B61]';
const section = `${PANEL} p-6 space-y-3`;
const sectionTitle = 'font-editorial text-xl text-[#1B2433]';

function TopicEditor({ moment, topics }: { moment: string; topics: MomentTopic[] }) {
  const { me } = useMe();
  const canEdit = me.roles.includes('editor');
  const available = useTopics(canEdit);
  const invalidate = useInvalidate();
  const [choice, setChoice] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState('');
  const change = async (body: { add?: string[]; remove?: string[] }, message: string) => {
    setBusy(true); setError(''); setDone('');
    try { await changeMomentTopics(moment, body); await invalidate(...MOMENT_TOPIC_READS); setChoice(''); setDone(message); }
    catch (failure) { setError(errorMessage(failure, 'The topics could not be changed.')); }
    finally { setBusy(false); }
  };
  const options = (available.data?.items ?? []).filter(topic => !topics.some(t => t.topic_id === topic.topic_id));
  return <section aria-label="Topics" className={section}>
    <h3 className={sectionTitle}>Topics</h3>
    {!topics.length && <p className="text-[13px] text-[#8B93A3]">No topic has been assigned yet.</p>}
    <ul className="flex flex-wrap gap-2 text-[13px]">{topics.map(topic => <li key={topic.topic_id} className="inline-flex items-center gap-2 rounded-full bg-[#F7F8FB] px-3 py-1.5">
      {topic.name}
      {canEdit && <button type="button" className="text-[#8B93A3] hover:text-red-700" disabled={busy} aria-label={`Remove the topic ${topic.name}`}
        onClick={() => void change({ remove: [topic.topic_id] }, `Removed ${topic.name}.`)}>×</button>}
    </li>)}</ul>
    {canEdit && <form className="flex flex-wrap items-center gap-2" onSubmit={e => { e.preventDefault(); if (choice) void change({ add: [choice] }, 'Topic added.'); }}>
      <label className="sr-only" htmlFor={`topic-${moment}`}>Add a topic</label>
      <Select id={`topic-${moment}`} className={SELECT} value={choice} onChange={e => setChoice(e.target.value)}>
        <option value="">Add a topic…</option>{options.map(topic => <option key={topic.topic_id} value={topic.topic_id}>{topic.name}</option>)}</Select>
      <button className={QUIET_BUTTON} disabled={!choice || busy}>{busy ? 'Saving…' : 'Add'}</button>
      <StatusLine>{done}</StatusLine>
    </form>}
    {error && <ErrorState message={error} />}
  </section>;
}

export function MomentBody({ detail }: { detail: MomentDetail }) {
  const { summary, citation, document, surrounding, topics, cards } = detail;
  const quote = citation?.quote ?? summary.quote;
  const recording = [citation?.recording_url, document?.recording_url].find(url => url && /^https?:\/\//.test(url)) ?? null;
  const start = clock(citation?.start_ms ?? detail.passages.find(p => p.roles.includes('anchor'))?.start_ms);
  const reasons = consentReasons(detail.checks);
  const { recorded, failures } = failedChecks(detail.checks);
  const repair = repairNote(detail.quote_repair);
  const unverified = !summary.quote_verified;
  return <article className="space-y-5">
    <section className={`${PANEL} p-6 space-y-5`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-[12px] text-[#8B93A3]">{summary.client_name || 'No client recorded'}</h2>
        <div className="flex flex-wrap gap-1.5">
          {unverified && <Pill tone="waiting">Quote not verified</Pill>}
          <ConsentBadge status={summary.consent_status} />
        </div>
      </div>
      {summary.consent_status === 'do_not_use' && <p role="note" className="rounded-xl bg-red-50 p-3 text-[13px] text-red-800">
        <strong>Do not use.</strong> {CONSENT_HINTS.do_not_use}</p>}
      {quote
        ? <blockquote className={`font-editorial text-[26px] leading-snug text-[#1B2433] ${unverified ? 'rounded-xl border border-dashed border-amber-300 p-4' : ''}`}>“{quote}”</blockquote>
        : <p className="text-[13px] text-[#8B93A3]">No quote is stored for this moment.</p>}
      {unverified && <p role="note" className="rounded-xl bg-[#FFF8E9] p-3 text-[13px] text-[#947021]">{UNVERIFIED_NOTE}</p>}
      <dl className="grid gap-x-8 gap-y-4 text-[13px] sm:grid-cols-2 lg:grid-cols-4">
        <div><dt className={term}>Said by</dt><dd className="mt-1">{summary.speaker_label || 'Speaker not recorded'} <span className="text-[#8B93A3]">· {speakerLabel(summary.speaker_role)}</span></dd></div>
        <div><dt className={term}>When</dt><dd className="mt-1">{whenLine(summary.occurred_at)}{start ? `, ${start} into the call` : ''}</dd></div>
        <div><dt className={term}>Recording</dt><dd className="mt-1">{recording
          ? <a className={`inline-flex items-center gap-1 ${TEXT_BUTTON}`} href={recording} target="_blank" rel="noopener noreferrer">Open the recording{start ? ` (at ${start})` : ''}<ExternalLink size={12} aria-hidden="true" /></a>
          : <span className="text-[#8B93A3]">This source has no recording to open.</span>}</dd></div>
        {document && <div><dt className={term}>From</dt><dd className="mt-1">
          <Link className="text-[#5070FF] hover:underline" to={paths.document(document.document_id)}>{document.title}</Link>
          <span className="text-[#8B93A3]">, {sourceLabel(document.source_type)}{document.call_type ? `, ${callLabel(document.call_type)}` : ''}</span></dd></div>}
      </dl>
    </section>

    <section aria-label="Whether it can be used" className={section}>
      <h3 className={sectionTitle}>Can it be used?</h3>
      <p className="text-[13px]"><ConsentBadge status={summary.consent_status} /> <span className="ml-1">{CONSENT_HINTS[summary.consent_status] ?? `Recorded as ${consentLabel(summary.consent_status).toLowerCase()}.`}</span></p>
      {reasons.length > 0 && <ul className="list-disc space-y-1 pl-5 text-[13px] text-[#34445F] marker:text-[#A38B61]">{reasons.map((reason, i) => <li key={i}>{reason}</li>)}</ul>}
    </section>

    <section aria-label="The scene" className={section}>
      <h3 className={sectionTitle}>The scene</h3>
      {summary.record ? <p className="text-[13px] leading-relaxed">{summary.record}</p> : <p className="text-[13px] text-[#8B93A3]">No scene was recorded for this moment.</p>}
      {summary.context_summary && <p className="text-[13px] leading-relaxed text-[#667184]">{summary.context_summary}</p>}
      {summary.qualifications.length > 0 && <ul className="list-disc space-y-1 pl-5 text-[13px] text-[#667184] marker:text-[#A38B61]">{summary.qualifications.map((item, i) => <li key={i}>{item}</li>)}</ul>}
    </section>

    <section aria-label="The conversation around the quote" className={section}>
      <h3 className={sectionTitle}>In the conversation</h3>
      {!detail.evidence_intact && <p role="note" className="rounded-xl bg-[#FFF8E9] p-3 text-[13px] text-[#947021]">Part of the original conversation could not be matched to this moment, so some of it is not shown below.</p>}
      {!surrounding.length && <p className="text-[13px] text-[#8B93A3]">The conversation around this moment is not available.</p>}
      <ol className="space-y-3">{surrounding.map(passage => {
        const marked = highlight(passage, citation, quote);
        const time = clock(passage.start_ms);
        return <li key={passage.passage_id} data-cited={passage.cited || undefined}
          className={`text-[13px] leading-relaxed ${passage.cited ? 'border-l-2 border-[#E9D9A6] pl-3' : 'pl-3.5'}`}>
          <p className="text-[11px] text-[#8B93A3]"><span className="font-semibold text-[#34445F]">{passage.speaker || 'Speaker not recorded'}</span> ({speakerLabel(passage.speaker_role)}){time ? ` · ${time}` : ''}</p>
          <p className="whitespace-pre-wrap text-[#34445F]">{marked ? <>{marked[0]}<mark className="rounded bg-[#F6E3A6] px-0.5">{marked[1]}</mark>{marked[2]}</> : passage.text}</p>
        </li>;
      })}</ol>
    </section>

    <div className="grid gap-5 lg:grid-cols-2">
      <TopicEditor moment={summary.moment_id} topics={topics} />
      <section aria-label="Cards that use this moment" className={section}>
        <h3 className={sectionTitle}>Angles that use it</h3>
        {!cards.length && <p className="text-[13px] text-[#8B93A3]">No card uses this moment yet.</p>}
        <ul className="space-y-1.5 text-[13px]">{cards.map(card => <li key={`${card.week_id}-${card.angle_id}`}>
          <Link className="text-[#5070FF] hover:underline" to={paths.angle(card.week_id, card.angle_id)}>{card.title || 'Untitled card'}</Link>
          <span className="text-[#8B93A3]">, {evidenceRoleLabel(card.evidence_role).toLowerCase()} · {approvalLabel(card.approval_status)}</span></li>)}</ul>
      </section>
    </div>

    <details className={`group ${PANEL}`} aria-label="Checks">
      <summary className="flex cursor-pointer list-none items-center justify-between px-6 py-4 text-[13px] font-semibold text-[#34445F] [&::-webkit-details-marker]:hidden">
        <span>Checks{failures.length ? <span className="ml-2 font-normal text-[#947021]">· {failures.length} to look at</span> : null}</span>
        <span aria-hidden="true" className="text-[11px] font-normal text-[#9AA3B2]"><span className="group-open:hidden">Show</span><span className="hidden group-open:inline">Hide</span></span></summary>
      <div className="space-y-2 border-t border-[#EEF0F4] px-6 py-4 text-[13px]">
        {repair && <div><p>{repair.note}</p>
          {(repair.before || repair.after) && <div className="mt-1 space-y-1 text-[#667184]">
            {repair.before && <p><span className={term}>First wording </span>“{repair.before}”</p>}
            {repair.after && <p><span className={term}>Transcript's wording </span>“{repair.after}”</p>}</div>}</div>}
        {failures.length > 0 && <ul className="space-y-1 text-[#947021]" aria-label="Checks that failed">{failures.map((failure, i) => <li key={i} className="rounded-xl bg-[#FFF8E9] p-2.5">{failure}</li>)}</ul>}
        {recorded && !failures.length && <p>The checks on the figures and on who said it all passed.</p>}
        {!recorded && !repair && <p className="text-[#8B93A3]">{unverified ? 'No checks could be made without a verified quote.' : 'No checks are recorded for this moment.'}</p>}
      </div>
    </details>
  </article>;
}

/** The ledger the person came from, with its filters, or the plain ledger after a refresh or a pasted link. */
export function backTarget(state: unknown): string {
  const from = state && typeof state === 'object' ? (state as { from?: unknown }).from : null;
  return typeof from === 'string' && /^\/moments(?:[?#]|$)/.test(from) ? from : paths.moments;
}

/** The page of one moment (the path /moments/ and its id), at a path that survives a refresh. */
export function MomentView() {
  const { momentId = '' } = useParams();
  const location = useLocation();
  const moment = useMoment(momentId);
  return <div className="space-y-4">
    <PageHeading title="Moments" subtitle="A moment" />
    <Link to={backTarget(location.state)} className="inline-flex items-center gap-1 text-[12px] font-medium text-[#5070FF] hover:underline"><ArrowLeft size={14} />All moments</Link>
    {moment.isPending && !moment.error && <LoadingState>Loading the moment…</LoadingState>}
    {moment.error && <ErrorState message={moment.error.message} onRetry={() => void moment.refetch()} />}
    {moment.data && <MomentBody detail={moment.data} />}
  </div>;
}
