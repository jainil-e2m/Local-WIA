import { useId, useMemo, useState, type CSSProperties, type KeyboardEvent, type ReactNode } from 'react';
import { AlertTriangle, ArrowLeft, Check, ImageOff, ImagePlus, Info, Lock, MapPin, PencilLine, Plus, RotateCcw, Trash2, Upload, X } from 'lucide-react';
import { CLIENTS, TEAM, dateLabel } from '../data';
import { ENGAGEMENT_TYPES, LIFECYCLES, recordFor, suggestionWhy } from '../records';
import { DEFAULT_COVER_ID, coverById, savedCoverId } from '../clientCovers';
import { LOGO_ACCEPT, LOGO_DEFAULT_TINT, LOGO_SCALE, LOGO_TINTS, initialsFor, loadOverride, originalDetails, prepareLogo, saveClientDetails } from '../clientDetails';
import { NOT_EXTRACTED, blank, overrideFrom, type DetailsBase, type DetailsDraft, type LogoState } from '../clientOverride';
import { isAdmin } from '../views/Actions';
import type { Client } from '../types';
import CoverLibrary from './ClientCoverPicker';
import { ThemedDatePicker } from './ThemedDatePicker';
import { ThemedSelect } from './ThemedSelect';
import { EditConflict } from '../sharedEdits';
import { Dialog } from './UI';
import './ClientDetailsEditor.css';

export type EditorTab = 'details' | 'logo' | 'cover';
type Draft = DetailsDraft & { coverId: string };

const MAX_ALIASES = 8;
// Local calendar date (not UTC), so an evening edit in the US or an early-morning one in India keeps its own day.
const today = () => new Date().toLocaleDateString('en-CA');
const sameList = (a: unknown[], b: unknown[]) => JSON.stringify(a) === JSON.stringify(b);
/** What the card and header will show: the typed value, or the KB's "Not extracted yet" when left empty. */
const shown = (value: string, kb: string) => value.trim() || (kb === NOT_EXTRACTED ? kb : '');

/**
 * One place to edit a client: name and aliases, category and location, account owner, stage and engagements,
 * the portfolio logo (upload, size, background) and the record cover. Admins edit everything; others
 * can change the cover only. One Save applies every tab; closing with unsaved changes asks first.
 */
export default function ClientDetailsEditor({ client, viewer, initialTab = 'details', onClose, notify }: { client: Client; viewer: string; initialTab?: EditorTab; onClose: () => void; notify: (message: string) => void }) {
  const base = originalDetails(client.id);
  const canEditIdentity = isAdmin(viewer);
  const baseTint = base.logo?.tint ?? LOGO_DEFAULT_TINT;
  const kb: DetailsBase = { ...base, hasLogo: !!base.logo, tint: baseTint };
  const kbDraft = (): Draft => ({
    name: base.name, aliases: base.aliases, category: blank(base.category), location: blank(base.location), owner: base.owner, lifecycle: base.lifecycle,
    engagements: base.engagements.map(e => ({ ...e })), logo: base.logo ? { kind: 'extracted' } : { kind: 'none' }, logoScale: 1, logoTint: baseTint,
    coverId: client.coverId ? coverById(client.coverId).id : DEFAULT_COVER_ID,
  });
  const initial = useMemo<Draft>(() => {
    const o = loadOverride(client.id);
    return {
      name: o.name ?? base.name, aliases: o.aliases ?? base.aliases, category: blank(o.category ?? base.category), location: blank(o.location ?? base.location),
      owner: o.owner ?? base.owner, lifecycle: o.lifecycle ?? base.lifecycle, engagements: (o.engagements ?? base.engagements).map(e => ({ ...e })),
      logo: o.logo ? { kind: 'uploaded', uploaded: o.logo } : o.logoRemoved || !base.logo ? { kind: 'none' } : { kind: 'extracted' },
      logoScale: o.logoScale ?? 1, logoTint: o.logoTint ?? baseTint, coverId: savedCoverId(client.id, client.coverId),
    };
  }, [client.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const [draft, setDraft] = useState<Draft>(initial);
  const [tab, setTab] = useState<EditorTab>(initialTab);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => { setDraft(d => ({ ...d, [key]: value })); setConfirmDiscard(false); };
  const uid = useId();
  // The KB's owner suggestion (from recent activity), offered when no owner is set; choosing it is the user's call.
  const suggestion = recordFor(client.id).ownerSuggestion;
  const suggestedValue = suggestion ? TEAM.find(p => p === suggestion.name.split(' ')[0]) ?? suggestion.name : '';
  const owners = [...new Set([...TEAM, ...(suggestedValue ? [suggestedValue] : []), ...(draft.owner ? [draft.owner] : [])])];

  const name = draft.name.trim();
  const nameError = !name ? 'A business name is required.' : name.length > 80 ? 'Keep the name under 80 characters.' : '';
  const duplicate = name && CLIENTS.some(c => c.id !== client.id && c.name.trim().toLowerCase() === name.toLowerCase());
  const dirty = JSON.stringify(draft) !== JSON.stringify(initial);
  const requestClose = () => { if (dirty) { setConfirmDiscard(true); } else onClose(); };

  const [saving, setSaving] = useState(false);
  const save = async () => {
    if (nameError) { setTab('details'); return; }
    const o = overrideFrom(kb, draft);
    if (Object.keys(o).length) { o.editedBy = viewer; o.editedAt = today(); }
    const detailsChanged = JSON.stringify({ ...draft, coverId: '' }) !== JSON.stringify({ ...initial, coverId: '' });
    // Details and cover in one save, so it applies whole or not at all.
    setSaving(true);
    try {
      await saveClientDetails(client.id, viewer, detailsChanged ? o : undefined,
                              draft.coverId !== initial.coverId ? draft.coverId : undefined);
    } catch (error) {
      setSaving(false);
      // A colleague saved first: this draft was made on their old copy, so saving it again would undo their change.
      if (error instanceof EditConflict) { notify(`${error.message} Reopen the editor to make your change on it.`); onClose(); return; }
      notify((error as Error).message);
      return;
    }
    setSaving(false);
    notify(`Details saved for ${name}. Everyone sees the change.`);
    onClose();
  };

  const footer = confirmDiscard
    ? <><p className="cde-confirm" role="alert"><AlertTriangle size={14} />Discard your unsaved changes?</p><div className="cde-actions"><button className="button button-outline" onClick={() => setConfirmDiscard(false)}>Keep editing</button><button className="button cde-discard" onClick={onClose}>Discard</button></div></>
    : <><div className="cde-foot-note">{canEditIdentity && <button className="text-button" onClick={() => setDraft(kbDraft())}><RotateCcw size={13} />Reset all to the KB record</button>}<p className="hint">Saved for everyone when you press Save changes.</p></div><div className="cde-actions"><button className="button button-outline" onClick={requestClose}>Cancel</button><button className="button button-primary" disabled={!dirty || !!nameError || saving} onClick={() => void save()}><Check size={14} />{saving ? "Saving…" : "Save changes"}</button></div></>;

  const notExtracted = (kbValue: string) => kbValue === NOT_EXTRACTED ? NOT_EXTRACTED : undefined;
  return <Dialog title="Edit client details" subtitle={`CLIENT · ${base.name}`} size="lg" className="client-details-editor" onClose={requestClose} footer={footer}>
    {/* The previews are the way in: the card opens the logo, the cover opens the backdrop; clicking again returns to details. */}
    <Previews tab={tab} pick={t => setTab(tab === t ? 'details' : t)} draft={draft} name={name || base.name} category={shown(draft.category, base.category)} location={shown(draft.location, base.location)} logoMark={logoMark(draft.logo, base.logo?.mark)} />
    {tab !== 'details' && <div className="cde-panel-head"><button type="button" className="text-button" onClick={() => setTab('details')}><ArrowLeft size={14} />Back to details</button><h3>{tab === 'logo' ? 'Logo' : 'Cover'}</h3></div>}
    {!canEditIdentity && tab !== 'cover' && <p className="cde-locked"><Lock size={13} />Only admins (Gisselle, Whitney) can change a client’s name, details and logo. You can change the cover.</p>}

    {tab === 'details' && <section aria-label="Client details" className="cde-panel">
      <Field id={`${uid}-name`} label="Business name" changed={name !== base.name} onReset={() => set('name', base.name)} disabled={!canEditIdentity}
        hint="Shown across the portfolio, the client record and the Action Hub. The client keeps its ID, so linked Slack, Drive, ClickUp and LeadLock sources are unaffected."
        error={nameError} warning={duplicate ? 'Another client already has this name.' : ''}>
        <input id={`${uid}-name`} value={draft.name} maxLength={90} disabled={!canEditIdentity} aria-invalid={!!nameError} onChange={e => set('name', e.target.value)} placeholder="e.g. Cedar Hollow Farm" />
      </Field>
      <Field id={`${uid}-alias`} label="Also known as" changed={!sameList(draft.aliases, base.aliases)} onReset={() => set('aliases', base.aliases)} disabled={!canEditIdentity}
        hint="Former or alternative names, such as a trading name or a venue’s old name, so the client is recognised under each. Press Enter to add each one.">
        <AliasInput id={`${uid}-alias`} value={draft.aliases} onChange={v => set('aliases', v)} disabled={!canEditIdentity} />
      </Field>
      <div className="cde-two">
        <Field id={`${uid}-category`} label="Category" origin={notExtracted(base.category)} changed={draft.category.trim() !== blank(base.category)} onReset={() => set('category', blank(base.category))} disabled={!canEditIdentity}>
          <input id={`${uid}-category`} value={draft.category} maxLength={60} disabled={!canEditIdentity} onChange={e => set('category', e.target.value)} placeholder="e.g. Wedding venue" />
        </Field>
        <Field id={`${uid}-location`} label="Location" origin={notExtracted(base.location)} changed={draft.location.trim() !== blank(base.location)} onReset={() => set('location', blank(base.location))} disabled={!canEditIdentity}>
          <input id={`${uid}-location`} value={draft.location} maxLength={80} disabled={!canEditIdentity} onChange={e => set('location', e.target.value)} placeholder="City, State" />
        </Field>
      </div>

      <h3 className="cde-section">Relationship</h3>
      <div className="cde-two">
        <Field id={`${uid}-owner`} label="Account owner" changed={draft.owner !== base.owner} onReset={() => set('owner', base.owner)} disabled={!canEditIdentity}
          hint={suggestion && !draft.owner ? undefined : 'The WIA person responsible for this client. “My clients” lists the clients you own.'}>
          <ThemedSelect id={`${uid}-owner`} aria-label="Account owner" value={draft.owner} disabled={!canEditIdentity} onChange={v => set('owner', v)}><option value="">Unassigned</option>{owners.map(p => <option key={p} value={p}>{p}</option>)}</ThemedSelect>
          {suggestion && !draft.owner && <p className="cde-suggest"><span><strong>Suggested: {suggestion.name}</strong> · {suggestionWhy(suggestion)}</span>
            {canEditIdentity && <button type="button" className="text-button" onClick={() => set('owner', suggestedValue)}><Check size={12} />Use suggestion</button>}</p>}
        </Field>
        <Field id={`${uid}-stage`} label="Stage" changed={draft.lifecycle !== base.lifecycle} onReset={() => set('lifecycle', base.lifecycle)} disabled={!canEditIdentity}>
          <ThemedSelect id={`${uid}-stage`} aria-label="Stage" value={draft.lifecycle} disabled={!canEditIdentity} onChange={v => set('lifecycle', v as Draft['lifecycle'])}>{LIFECYCLES.map(l => <option key={l} value={l}>{l}</option>)}</ThemedSelect>
        </Field>
      </div>
      <Field id={`${uid}-engagement-0`} label="Engagements" changed={!sameList(draft.engagements, base.engagements)} onReset={() => set('engagements', base.engagements.map(e => ({ ...e })))} disabled={!canEditIdentity}
        hint="Each service WIA provides, with its start date. The earliest start is shown as “Client since”.">
        <Engagements uid={uid} value={draft.engagements} onChange={v => set('engagements', v)} disabled={!canEditIdentity} />
      </Field>
    </section>}

    {tab === 'logo' && <section aria-label="Logo" className="cde-panel">
      <LogoPanel draft={draft} set={set} base={base} viewer={viewer} disabled={!canEditIdentity} />
    </section>}

    {tab === 'cover' && <section aria-label="Cover" className="cde-panel">
      <div className="cde-cover-head"><p className="hint">The backdrop behind this client’s record header. Each client has its own.</p><button type="button" className="text-button" onClick={() => set('coverId', DEFAULT_COVER_ID)}><RotateCcw size={13} />Default cover</button></div>
      <CoverLibrary value={draft.coverId} onChange={id => set('coverId', id)} />
    </section>}
  </Dialog>;
}

function logoMark(logo: LogoState, extracted: ReactNode): ReactNode {
  if (logo.kind === 'uploaded') return <img src={logo.uploaded.dataUri} alt="" style={{ maxWidth: '78%', maxHeight: '70%', objectFit: 'contain' }} />;
  if (logo.kind === 'extracted') return extracted;
  return null;
}

/** Live previews of the two places these details appear: the portfolio card and the record cover. */
function Previews({ tab, pick, draft, name, category, location, logoMark: mark }: { tab: EditorTab; pick: (tab: 'logo' | 'cover') => void; draft: Draft; name: string; category: string; location: string; logoMark: ReactNode }) {
  const cover = coverById(draft.coverId);
  const initials = initialsFor(name);
  return <div className="cde-previews" data-tab={tab}>
    <figure className="cde-preview-card">
      <figcaption>Portfolio card</figcaption>
      <button type="button" className="cde-preview-hit" aria-pressed={tab === 'logo'} aria-label="Edit the logo" onClick={() => pick('logo')}>
      <span className="cde-edit-chip" aria-hidden="true"><PencilLine size={11} />Edit logo</span>
      <div className="cde-card">
        <div className={`cp-banner ${mark ? '' : 'is-fallback'}`} style={mark ? { background: draft.logoTint, ['--logo-user-scale' as string]: draft.logoScale } as CSSProperties : undefined}>{mark ?? <span className="cp-pending"><ImageOff size={12} />Logo pending</span>}</div>
        <span className="cp-avatar" aria-hidden="true">{initials}</span>
        <div className="cde-card-body"><strong>{name}</strong><small><MapPin size={11} />{location || 'Location not recorded'}</small></div>
      </div>
      </button>
    </figure>
    <figure className="cde-preview-cover">
      <figcaption>Record cover</figcaption>
      <button type="button" className="cde-preview-hit" aria-pressed={tab === 'cover'} aria-label="Change the cover" onClick={() => pick('cover')}>
      <span className="cde-edit-chip" aria-hidden="true"><PencilLine size={11} />Change cover</span>
      <div className="cover-preview">
        <img key={cover.id} src={cover.image} alt="" style={{ objectPosition: cover.position }} />
        {/* Same wording as the record header: category (or "Client"), then location when there is one. */}
        <div className="cover-preview-copy"><span>{initials}</span><div><strong>{name}</strong><p>{category || 'Client'}{location && ` · ${location}`}</p></div></div>
      </div>
      </button>
    </figure>
  </div>;
}

function Field({ id, label, hint, error, warning, origin = 'From KB record', changed, onReset, disabled, children }: { id: string; label: string; hint?: string; error?: string; warning?: string; origin?: string; changed: boolean; onReset: () => void; disabled?: boolean; children: ReactNode }) {
  return <div className={`cde-field ${error ? 'has-error' : ''}`}>
    <div className="cde-field-head"><label htmlFor={id}>{label}</label>{changed ? <span className="cde-edited">Edited{!disabled && <button type="button" onClick={onReset} aria-label={`Use the KB value for ${label}`}><RotateCcw size={11} />Use KB value</button>}</span> : <span className="cde-origin">{origin}</span>}</div>
    {children}
    {error ? <p className="cde-error" role="alert">{error}</p> : warning ? <p className="cde-warning"><AlertTriangle size={12} />{warning}</p> : hint && <p className="cde-hint">{hint}</p>}
  </div>;
}

function AliasInput({ id, value, onChange, disabled }: { id: string; value: string[]; onChange: (v: string[]) => void; disabled?: boolean }) {
  const [text, setText] = useState('');
  const add = () => {
    const next = text.split(',').map(s => s.trim().slice(0, 60)).filter(Boolean);
    if (!next.length) return;
    onChange([...new Set([...value, ...next])].slice(0, MAX_ALIASES));
    setText('');
  };
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add(); }
    if (e.key === 'Backspace' && !text && value.length) onChange(value.slice(0, -1));
  };
  return <div className={`cde-chips ${disabled ? 'is-disabled' : ''}`} onClick={e => (e.currentTarget.querySelector('input') as HTMLInputElement | null)?.focus()}>
    {value.map(a => <span className="cde-chip" key={a}>{a}{!disabled && <button type="button" aria-label={`Remove ${a}`} onClick={() => onChange(value.filter(x => x !== a))}><X size={11} /></button>}</span>)}
    {!disabled && value.length < MAX_ALIASES && <input id={id} value={text} onChange={e => setText(e.target.value)} onKeyDown={onKey} onBlur={add} placeholder={value.length ? 'Add another' : 'e.g. Dos Palomas'} />}
    {disabled && !value.length && <span className="cde-none">None recorded</span>}
  </div>;
}

/** Engagement rows: WIA service type and start date. A type imported from ClickUp stays selectable until it is replaced. */
function Engagements({ uid, value, onChange, disabled }: { uid: string; value: DetailsDraft['engagements']; onChange: (v: DetailsDraft['engagements']) => void; disabled: boolean }) {
  const update = (i: number, patch: Partial<DetailsDraft['engagements'][number]>) => onChange(value.map((e, j) => j === i ? { ...e, ...patch } : e));
  return <div className="cde-engagements">
    {value.map((e, i) => <div className="cde-engagement" key={i}>
      {disabled ? <span className="cde-readonly">{e.type}</span>
        : <ThemedSelect id={`${uid}-engagement-${i}`} aria-label={`Engagement ${i + 1} type`} value={e.type} onChange={type => update(i, { type })}>{[...new Set([e.type, ...ENGAGEMENT_TYPES])].map(t => <option key={t} value={t}>{ENGAGEMENT_TYPES.includes(t) ? t : `${t} (from ClickUp)`}</option>)}</ThemedSelect>}
      {disabled ? <span className="cde-readonly">{e.start ? `Since ${dateLabel(e.start, { day: 'numeric', month: 'short', year: 'numeric' })}` : 'Start not recorded'}</span>
        : <ThemedDatePicker label={`Engagement ${i + 1} start date`} value={e.start} clearable onChange={start => update(i, { start })} />}
      {!disabled && <button type="button" className="icon-button" aria-label={`Remove engagement ${i + 1}`} onClick={() => onChange(value.filter((_, j) => j !== i))}><Trash2 size={14} /></button>}
    </div>)}
    {!value.length && <p className="cde-none">No engagements recorded.</p>}
    {!disabled && <button type="button" className="text-button cde-add" onClick={() => onChange([...value, { type: ENGAGEMENT_TYPES[0], start: '' }])}><Plus size={13} />Add engagement</button>}
  </div>;
}

function LogoPanel({ draft, set, base, viewer, disabled }: { draft: Draft; set: <K extends keyof Draft>(key: K, value: Draft[K]) => void; base: ReturnType<typeof originalDetails>; viewer: string; disabled: boolean }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notes, setNotes] = useState<string[]>([]);
  const [over, setOver] = useState(false);
  const take = async (file?: File | null) => {
    if (!file || disabled) return;
    setBusy(true); setError(''); setNotes([]);
    const result = await prepareLogo(file);
    setBusy(false);
    if (!result.ok) { setError(result.error); return; }
    set('logo', { kind: 'uploaded', uploaded: { ...result.logo, uploadedAt: today(), uploadedBy: viewer } });
    setNotes(result.notes);
  };
  const hasLogo = draft.logo.kind !== 'none';
  const source = draft.logo.kind === 'uploaded'
    ? <>Uploaded <strong>{draft.logo.uploaded.file}</strong> · {draft.logo.uploaded.width}×{draft.logo.uploaded.height}px · {draft.logo.uploaded.uploadedBy}, {dateLabel(draft.logo.uploaded.uploadedAt)}</>
    : draft.logo.kind === 'extracted' && base.logo ? <>From {base.logo.source}: <strong>{base.logo.file}</strong> · {base.logo.source === 'Uploaded in the KB' ? 'uploaded' : 'extracted'} {dateLabel(base.logo.extracted)}</>
    : <>No logo. The card shows <strong>Logo pending</strong> with the client’s initials.</>;

  return <div className="cde-logo">
    <div className="cde-logo-main">
      <div className="cde-logo-source"><p>{source}</p>
        <div className="cde-logo-buttons">
          {draft.logo.kind === 'uploaded' && <button type="button" className="text-button" disabled={disabled} onClick={() => { set('logo', base.logo ? { kind: 'extracted' } : { kind: 'none' }); setNotes([]); }}><RotateCcw size={13} />{base.logo ? 'Use the extracted logo' : 'Remove upload'}</button>}
          {draft.logo.kind === 'extracted' && <button type="button" className="text-button cde-danger" disabled={disabled} onClick={() => set('logo', { kind: 'none' })}><Trash2 size={13} />Hide this logo</button>}
          {draft.logo.kind === 'none' && base.logo && <button type="button" className="text-button" disabled={disabled} onClick={() => set('logo', { kind: 'extracted' })}><RotateCcw size={13} />Restore the extracted logo</button>}
        </div>
      </div>
      <label className={`cde-drop ${over ? 'is-over' : ''} ${disabled ? 'is-disabled' : ''}`} onDragOver={e => { e.preventDefault(); if (!disabled) setOver(true); }} onDragLeave={() => setOver(false)} onDrop={e => { e.preventDefault(); setOver(false); void take(e.dataTransfer.files[0]); }}>
        <input type="file" accept={LOGO_ACCEPT} disabled={disabled} className="sr-only" onChange={e => { void take(e.target.files?.[0]); e.target.value = ''; }} />
        <span className="cde-drop-icon">{busy ? <Upload size={18} /> : <ImagePlus size={18} />}</span>
        <span><strong>{busy ? 'Preparing the logo…' : hasLogo ? 'Replace the logo' : 'Upload a logo'}</strong><small>Drop a file here or browse · SVG, PNG, WebP or JPG · under 2 MB</small></span>
      </label>
      {error && <p className="cde-error" role="alert">{error}</p>}
      {notes.length > 0 && <ul className="cde-notes">{notes.map(n => <li key={n}><Info size={12} />{n}</li>)}</ul>}

      <div className={`cde-display ${hasLogo ? '' : 'is-off'}`} aria-disabled={!hasLogo}>
        <div className="cde-size">
          <label htmlFor="cde-logo-size">Size <output htmlFor="cde-logo-size">{Math.round(draft.logoScale * 100)}%</output></label>
          <div><input id="cde-logo-size" type="range" min={LOGO_SCALE.min} max={LOGO_SCALE.max} step={LOGO_SCALE.step} value={draft.logoScale} disabled={disabled || !hasLogo} onChange={e => set('logoScale', Number(e.target.value))} />
            <button type="button" className="text-button" disabled={disabled || !hasLogo || draft.logoScale === 1} onClick={() => set('logoScale', 1)}>Reset</button></div>
        </div>
        <div className="cde-tints" role="radiogroup" aria-label="Banner background">
          <span>Background</span>
          <div>{LOGO_TINTS.map(t => <button key={t.id} type="button" role="radio" aria-checked={draft.logoTint === t.id} aria-label={t.label} title={t.label} disabled={disabled || !hasLogo} className={draft.logoTint === t.id ? 'is-on' : ''} style={{ background: t.id }} onClick={() => set('logoTint', t.id)}>{draft.logoTint === t.id && <Check size={12} />}</button>)}</div>
        </div>
      </div>
    </div>
    <aside className="cde-guide">
      <h3>What works best</h3>
      <ul>
        <li><strong>SVG</strong>, or a <strong>PNG with a transparent background</strong>. They stay crisp and sit cleanly on the banner.</li>
        <li><strong>512px wide or more</strong> (1000px is ideal). Larger files are scaled down to 1000px.</li>
        <li>A <strong>horizontal lockup</strong> suits the wide banner (about 5 : 2). Square marks work too: raise the Size.</li>
        <li>Under <strong>2 MB</strong> (SVGs under 300 KB). White or very light logos need the <strong>Ink</strong> background.</li>
      </ul>
      <p>Extracted logos come from the client’s Drive brand folder or their contact’s email signature, never their website.</p>
    </aside>
  </div>;
}
