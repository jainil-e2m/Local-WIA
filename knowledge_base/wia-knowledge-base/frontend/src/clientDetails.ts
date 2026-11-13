import { createElement } from 'react';
import { CLIENTS } from './data';
import { RECORDS, type Engagement, type Lifecycle } from './records';
import { LOGOS, type ClientLogo } from './logos';
import { editOf, saveEdit } from './sharedEdits';

/*
 * Client details edited in the KB (name, aliases, category, location, logo and its display).
 *
 * Only fields that differ from the KB record are stored, so a field nobody touched keeps following the
 * source. The client's ID never changes, so source mappings (Slack, Drive, ClickUp, LeadLock) are unaffected.
 *
 * Saved for everyone as the client's shared edit (sharedEdits.ts: revision-checked and audited on the KB server),
 * in the same row as its cover (clientCovers.ts) and its archived flag.
 */

export interface UploadedLogo { dataUri: string; file: string; width: number; height: number; uploadedAt: string; uploadedBy: string }
export interface ClientDetailsOverride {
  name?: string;
  aliases?: string[];
  category?: string;
  location?: string;
  /** Account owner ('' = Unassigned), lifecycle stage and engagements (type + start date). */
  owner?: string;
  lifecycle?: Lifecycle;
  engagements?: Engagement[];
  /** A logo uploaded in the KB. Takes precedence over the extracted one. */
  logo?: UploadedLogo;
  /** True hides the extracted logo, so the card shows "Logo pending". */
  logoRemoved?: boolean;
  /** Display multiplier on top of the logo's own fit (1 = as extracted/uploaded). */
  logoScale?: number;
  /** Banner background behind the logo. */
  logoTint?: string;
  editedBy?: string;
  editedAt?: string;
}

interface Original { name: string; initials: string; category: string; location: string; aliases: string[]; owner: string; lifecycle: Lifecycle; engagements: Engagement[]; logo: ClientLogo | undefined }

// Fields of the client's shared edit that aren't details: they have their own readers.
const OTHER_FIELDS = ['coverId', 'archived'];
export const LOGO_MAX_BYTES = 2 * 1024 * 1024;
export const LOGO_DEFAULT_TINT = '#f6f7f4';
export const LOGO_SCALE = { min: 0.6, max: 1.6, step: 0.05 };
/** Banner backgrounds that keep logos readable; Ink is for white or very light logos. */
export const LOGO_TINTS = [
  { id: '#f6f7f4', label: 'Porcelain' }, { id: '#ffffff', label: 'White' }, { id: '#f8f3ea', label: 'Ivory' },
  { id: '#eef1e6', label: 'Sage' }, { id: '#f6ecea', label: 'Blush' }, { id: '#eaf0f8', label: 'Mist' },
  { id: '#e7e9ee', label: 'Stone' }, { id: '#26303f', label: 'Ink' },
];

const originals = new Map<string, Original>();
const listeners = new Set<() => void>();
let version = 0;

const snapshot = (id: string): Original | undefined => {
  if (!originals.has(id)) {
    const c = CLIENTS.find(x => x.id === id);
    if (!c) return undefined;
    const r = RECORDS[id];
    originals.set(id, {
      name: c.name, initials: c.initials, category: c.category, location: c.location, aliases: [...(r?.aliases ?? [])],
      owner: r?.owner ?? '', lifecycle: r?.lifecycle ?? 'Active', engagements: (r?.engagements ?? []).map(e => ({ ...e })), logo: LOGOS[id],
    });
  }
  return originals.get(id);
};

/** The KB record's own values, before any edit made here. */
export const originalDetails = (id: string) => snapshot(id)!;

export const initialsFor = (name: string) => {
  const words = name.replace(/[^\p{L}\p{N}\s&/-]/gu, ' ').split(/[\s/&-]+/).filter(Boolean);
  return ((words[0]?.[0] ?? '') + (words[1]?.[0] ?? '')).toUpperCase() || '?';
};

export function loadOverride(id: string): ClientDetailsOverride {
  const data = editOf('client', id)?.data ?? {};
  return Object.fromEntries(Object.entries(data).filter(([k]) => !OTHER_FIELDS.includes(k))) as ClientDetailsOverride;
}

const uploadedMark = (logo: UploadedLogo) => createElement('img', { src: logo.dataUri, alt: `${logo.file} (logo)`, style: { maxWidth: '78%', maxHeight: '70%', objectFit: 'contain' } });

/** Writes the KB values plus this client's overrides onto the shared records, so every view reads them. */
function apply(id: string) {
  const base = snapshot(id);
  const client = CLIENTS.find(x => x.id === id);
  if (!base || !client) return;
  const o = loadOverride(id);
  client.name = o.name ?? base.name;
  client.initials = o.name ? initialsFor(o.name) : base.initials;
  client.category = o.category ?? base.category;
  client.location = o.location ?? base.location;
  const record = RECORDS[id];
  if (record) {
    record.aliases = o.aliases ?? base.aliases;
    record.owner = o.owner ?? base.owner;
    record.lifecycle = o.lifecycle ?? base.lifecycle;
    record.engagements = (o.engagements ?? base.engagements).map(e => ({ ...e }));
  }
  const logo: ClientLogo | undefined = o.logo
    ? { mark: uploadedMark(o.logo), tint: LOGO_DEFAULT_TINT, source: 'Uploaded in the KB', file: o.logo.file, extracted: o.logo.uploadedAt }
    : o.logoRemoved ? undefined : base.logo && { ...base.logo };
  LOGOS[id] = logo && { ...logo, tint: o.logoTint ?? logo.tint, userScale: o.logoScale };
}

const emit = () => { version += 1; listeners.forEach(fn => fn()); };
export const subscribeClientDetails = (fn: () => void) => { listeners.add(fn); return () => { listeners.delete(fn); }; };
export const clientDetailsVersion = () => version;
/** Re-render views after a change stored elsewhere (the cover keeps its own key in clientCovers.ts). */
export const refreshClientDetails = emit;

/**
 * Saves the client's details (the whole override: a field left out goes back to the KB's value) and/or its
 * cover, in one save for everyone, then refreshes every view. Throws with a reason the person can read.
 */
export async function saveClientDetails(id: string, viewer: string, override?: ClientDetailsOverride, coverId?: string): Promise<void> {
  const changes: Record<string, unknown> = {};
  if (override) {
    const empty = Object.keys(override).every(k => k === 'editedBy' || k === 'editedAt');
    for (const k of Object.keys(loadOverride(id))) changes[k] = null;  // cleared fields follow the KB again
    if (!empty) Object.assign(changes, override);
  }
  if (coverId !== undefined) changes.coverId = coverId;
  if (!Object.keys(changes).length) return;
  try { await saveEdit('client', id, changes, viewer); }
  finally { apply(id); emit(); }  // on a conflict this shows the colleague's version that won
}

// Apply saved edits once, after the KB snapshot (kbLive) has replaced the sample records.
CLIENTS.forEach(c => apply(c.id));

/* ---------- Logo upload: validate, then fit to a light data URI the banner can show crisply ---------- */

const ACCEPTED = ['image/svg+xml', 'image/png', 'image/webp', 'image/jpeg'];
export const LOGO_ACCEPT = '.svg,.png,.webp,.jpg,.jpeg,' + ACCEPTED.join(',');
const MAX_EDGE = 1000;
// SVGs are stored as text, unshrunk; browsers allow ~5 MB per site, shared with the Action Hub's saved edits.
const SVG_MAX_CHARS = 300_000;

const readAs = (file: File, mode: 'text' | 'dataUrl') => new Promise<string>((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(String(reader.result));
  reader.onerror = () => reject(reader.error);
  if (mode === 'text') reader.readAsText(file); else reader.readAsDataURL(file);
});
const loadImage = (src: string) => new Promise<HTMLImageElement>((resolve, reject) => {
  const img = new Image();
  img.onload = () => resolve(img);
  img.onerror = () => reject(new Error('unreadable'));
  img.src = src;
});

export type PreparedLogo = { ok: true; logo: Omit<UploadedLogo, 'uploadedAt' | 'uploadedBy'>; notes: string[] } | { ok: false; error: string };

export async function prepareLogo(file: File): Promise<PreparedLogo> {
  const isSvg = file.type === 'image/svg+xml' || /\.svg$/i.test(file.name);
  if (!isSvg && !ACCEPTED.includes(file.type)) return { ok: false, error: 'Use an SVG, PNG, WebP or JPG file.' };
  if (file.size > LOGO_MAX_BYTES) return { ok: false, error: `That file is ${(file.size / 1048576).toFixed(1)} MB. Logos must be under 2 MB.` };
  const notes: string[] = [];
  try {
    if (isSvg) {
      const text = await readAs(file, 'text');
      if (!/<svg[\s>]/i.test(text)) return { ok: false, error: 'This SVG file has no drawing in it.' };
      const dataUri = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(text)}`;
      if (dataUri.length > SVG_MAX_CHARS) return { ok: false, error: `This SVG is too heavy to keep (${Math.round(dataUri.length / 1024)} KB once stored; the limit is ${SVG_MAX_CHARS / 1000} KB). It probably has a photo inside. Export it as a PNG instead.` };
      const img = await loadImage(dataUri);
      return { ok: true, logo: { dataUri, file: file.name, width: img.naturalWidth, height: img.naturalHeight }, notes };
    }
    const img = await loadImage(await readAs(file, 'dataUrl'));
    const { naturalWidth: w, naturalHeight: h } = img;
    if (Math.max(w, h) < 256) notes.push(`Only ${w}×${h}px, so it may look soft. 512px or wider is best.`);
    if (file.type === 'image/jpeg') notes.push('JPG has no transparency, so its background box shows on the banner. A PNG or SVG with a transparent background looks best.');
    if (w / h < 1.2) notes.push('Square and tall marks sit smaller on the wide banner. Use Size to enlarge it.');
    const k = Math.min(1, MAX_EDGE / Math.max(w, h));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(w * k); canvas.height = Math.round(h * k);
    canvas.getContext('2d')!.drawImage(img, 0, 0, canvas.width, canvas.height);
    // WebP keeps transparency at a fraction of PNG's size; browsers without WebP encoding return PNG.
    const dataUri = canvas.toDataURL('image/webp', 0.92);
    return { ok: true, logo: { dataUri, file: file.name, width: w, height: h }, notes };
  } catch {
    return { ok: false, error: 'This image could not be read. Try exporting it again as PNG or SVG.' };
  }
}
