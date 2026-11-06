import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Upload } from 'lucide-react';
import { UPLOAD_CHARACTERS, useClassifyDocument, useUploadDocument, type CallType, type DocumentSummary } from '../api/documents';
import { paths } from '../app/routes';
import { CALL_LABELS, CALL_TYPES, callLabel } from '../utils/documents';
import { DARK_BUTTON, Dialog, FIELD, HEADER_PRIMARY, LABEL, QUIET_BUTTON, SELECT, StatusLine } from './AdminParts';
import { Select } from './ThemedSelect';
import { DateInput } from './DateInput';

/* The Sources screen's two writes, offered to editors only (the server checks the role again):
   - a person decides what kind of call a document is, above all for a call the rules could not place (it waits for a
     person). The decision is recorded as the person's, with their reason, and no rule or model overwrites it.
   - a transcript file (a Zoom export, or any call as .txt or .vtt) goes through the same import as `documents import`:
     the same parsing, the same identity (the same file twice is one document), then normalisation on the queue. It opens in
     a dialog from the page header's "Upload a transcript". */

export function ClassifyControl({ doc, compact = false }: { doc: Pick<DocumentSummary, 'transcript_id' | 'title' | 'call_type' | 'needs_review'>; compact?: boolean }) {
  const classify = useClassifyDocument(doc.transcript_id);
  const [callType, setCallType] = useState<CallType | ''>(doc.needs_review ? '' : (doc.call_type as CallType | null) ?? '');
  const [reason, setReason] = useState('');
  const ready = !!callType && !!reason.trim() && !classify.isPending;
  return <form aria-label={`Classify ${doc.title}`} className="flex flex-wrap items-end gap-2"
    onSubmit={e => { e.preventDefault(); if (ready && callType) classify.mutate({ call_type: callType, reason: reason.trim() }); }}>
    <label className={LABEL}><span className={compact ? 'sr-only' : ''}>{doc.needs_review ? 'What kind of call is this?' : 'Call type'}</span>
      <Select className={`${SELECT} ${compact ? '' : 'mt-1.5'} block`} value={callType} onChange={e => setCallType(e.target.value as CallType | '')}>
        <option value="">{doc.needs_review ? 'Choose a call type…' : 'Choose…'}</option>{CALL_TYPES.map(type => <option key={type} value={type}>{CALL_LABELS[type]}</option>)}
      </Select></label>
    <label className={`${LABEL} grow min-w-48`}><span className={compact ? 'sr-only' : ''}>Why (kept with the decision)</span>
      <input className={`${FIELD} ${compact ? '!mt-0 !py-1.5 !rounded-full' : ''}`} value={reason} maxLength={500} onChange={e => setReason(e.target.value)} placeholder="Why: what in the call tells you" /></label>
    <button className={QUIET_BUTTON} disabled={!ready}>{classify.isPending ? 'Saving…' : 'Save the call type'}</button>
    {classify.data && <div className="basis-full"><StatusLine>Saved as {callLabel(classify.data.call_type)}{classify.data.included ? ', included' : ', excluded'}.</StatusLine></div>}
    {classify.error && <div className="basis-full"><StatusLine tone="error">{classify.error.message}</StatusLine></div>}
  </form>;
}

const SOURCE_KINDS = [['zoom', 'Zoom export'], ['file', 'Other call file'], ['manual', 'Typed notes']] as const;
type SourceKind = typeof SOURCE_KINDS[number][0];

/** The upload form; `onDone` closes the dialog it sits in. */
export function TranscriptUpload({ onDone }: { onDone?: () => void }) {
  const upload = useUploadDocument();
  const [file, setFile] = useState<File | null>(null);
  const [kind, setKind] = useState<SourceKind>('zoom');
  const [day, setDay] = useState('');
  const [problem, setProblem] = useState('');
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setProblem('');
    if (!file) return;
    if (!/\.(txt|vtt|webvtt)$/i.test(file.name)) return setProblem('Choose a .txt, .vtt or .webvtt file. A Fathom call comes in through intake.');
    const content = await file.text();
    if (!content.trim()) return setProblem('This file is empty.');
    if (content.length > UPLOAD_CHARACTERS) return setProblem(`This file is longer than ${UPLOAD_CHARACTERS.toLocaleString('en-US')} characters.`);
    // A calendar day only: noon UTC is the same day in Texas and in India, and the date is recorded as the person's.
    upload.mutate({ filename: file.name, content, source_type: kind, occurred_at: day ? `${day}T12:00:00Z` : null });
  };
  const result = upload.data;
  return <form aria-label="Upload a transcript" className="space-y-4" onSubmit={e => void submit(e)}>
    <p className="text-[13px] text-[#667184]">A Zoom transcript or any call as a .txt or .vtt file. It is added to the documents, then sorted and dated.</p>
    <label className={LABEL}>File
      <input type="file" accept=".txt,.vtt,.webvtt,text/plain,text/vtt" className="mt-1.5 block text-[13px]" onChange={e => { setFile(e.target.files?.[0] ?? null); upload.reset(); setProblem(''); }} /></label>
    <div className="grid gap-4 sm:grid-cols-2">
      <label className={LABEL}>Kind
        <Select className={FIELD} value={kind} onChange={e => setKind(e.target.value as SourceKind)}>
          {SOURCE_KINDS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select></label>
      <label className={LABEL}>Date of the call (optional)
        <DateInput className={FIELD} value={day} onChange={e => setDay(e.target.value)} /></label>
    </div>
    <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
      {onDone && <button type="button" className={QUIET_BUTTON} onClick={onDone}>{result ? 'Close' : 'Cancel'}</button>}
      <button className={DARK_BUTTON} disabled={!file || upload.isPending}>{upload.isPending ? 'Uploading…' : 'Upload'}</button>
    </div>
    <StatusLine tone="error">{problem || upload.error?.message}</StatusLine>
    {result && <StatusLine>
      {result.created ? 'Added: ' : 'Already stored, nothing added: '}
      <Link className="underline" to={paths.document(result.transcript_id)}>{result.document.title}</Link>
      {result.created ? '. It is sorted and dated shortly.' : '.'}
    </StatusLine>}
  </form>;
}

/** The page header's "Upload a transcript", with its dialog. */
export function UploadTranscriptButton() {
  const [open, setOpen] = useState(false);
  return <>
    <button type="button" className={HEADER_PRIMARY} onClick={() => setOpen(true)}><Upload aria-hidden="true" className="h-3.5 w-3.5" />Upload a transcript</button>
    {open && <Dialog title="Upload a transcript" onClose={() => setOpen(false)}><TranscriptUpload onDone={() => setOpen(false)} /></Dialog>}
  </>;
}
