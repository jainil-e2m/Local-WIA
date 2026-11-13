import { clientById, SLACK_CHANNELS, TEAM } from './data';
import { PROGRAMME_TEAMS, seedTeams } from './teams';
import type { Action, ActionHistoryEntry } from './types';
import { me } from './auth';

/*
 * Action Hub pieces shared by the board and the detail modal: Slack pings (preview only, nothing is posted),
 * the "who should own it?" picker, and pointer drag between the four pending buckets.
 */

const PING_COOLDOWN_MS = 2 * 60 * 1000;

export function SlackIcon() {
  return <span className="mvp-slack-icon" aria-hidden><svg viewBox="0 0 24 24" width="13" height="13" focusable="false">
    <path fill="#E01E5A" d="M5.04 15.17a2.53 2.53 0 1 1-2.52-2.53h2.52zm1.27 0a2.53 2.53 0 0 1 5.05 0v6.31a2.53 2.53 0 1 1-5.05 0z" />
    <path fill="#36C5F0" d="M8.83 5.04a2.53 2.53 0 1 1 2.53-2.52v2.52zm0 1.27a2.53 2.53 0 0 1 0 5.05H2.52a2.53 2.53 0 0 1 0-5.05z" />
    <path fill="#2EB67D" d="M18.96 8.83a2.53 2.53 0 1 1 2.52 2.53h-2.52zm-1.27 0a2.53 2.53 0 0 1-5.05 0V2.52a2.53 2.53 0 1 1 5.05 0z" />
    <path fill="#ECB22E" d="M15.17 18.96a2.53 2.53 0 1 1-2.53 2.52v-2.52zm0-1.27a2.53 2.53 0 0 1 0-5.05h6.31a2.53 2.53 0 1 1 0 5.05z" />
  </svg></span>;
}

/** Programme items go to the accelerator channel; client items to the client's channel. */
export function slackChannelFor(a: Pick<Action, 'kind' | 'programme' | 'clientId'>) {
  if (a.kind === 'programme') return String(a.programme).startsWith('Meta') ? '#meta-accelerator' : '#google-accelerator';
  return SLACK_CHANNELS[a.clientId]?.channel || `#client-${a.clientId}`;
}

export function timeAgo(iso: string, now = Date.now()) {
  const mins = Math.max(0, Math.floor((now - new Date(iso).getTime()) / 60000));
  const hrs = Math.floor(mins / 60);
  const days = Math.floor(mins / 1440);
  if (mins < 60) return `${mins} ${mins === 1 ? 'min' : 'mins'} ago`;
  if (mins < 1440) return `${hrs} ${hrs === 1 ? 'hr' : 'hrs'} ago`;
  return `${days} ${days === 1 ? 'day' : 'days'} ago`;
}

/** A toast above any open modal: a manual popover sits in the top layer with the dialog. */
export function topToast(message: string) {
  const el = document.createElement('div');
  el.className = 'mvp-top-toast';
  el.setAttribute('role', 'status');
  el.textContent = message;
  try { el.popover = 'manual'; } catch { /* older browsers: plain fixed toast */ }
  document.body.appendChild(el);
  try { el.showPopover(); } catch { /* not supported */ }
  setTimeout(() => el.remove(), 3200);
}

/** "Ping on Slack" with a two-minute cooldown; records the ping on the action's history. */
export function SlackPing({ action: a, viewer, now, update, log }: { action: Action; viewer?: string; now: number; update: (id: string, patch: Partial<Action>) => void; log: (text: string) => ActionHistoryEntry[] }) {
  const channel = slackChannelFor(a);
  const since = a.slackPingedAt ? now - new Date(a.slackPingedAt).getTime() : Infinity;
  const cooling = since < PING_COOLDOWN_MS;
  const left = Math.max(0, Math.ceil((PING_COOLDOWN_MS - since) / 1000));
  const ping = () => {
    if (cooling) return;
    const lead = seedTeams()[a.clientId]?.[0];
    const text = a.side === 'Client'
      ? `Pinged ${channel} on Slack by ${me(viewer) || 'Someone'}: waiting on ${a.owner || clientById(a.clientId).contact || 'the client'}; ${lead ? `@${lead.name} (${lead.role})` : 'the account team'} to follow up.`
      : `Pinged ${channel} on Slack by ${me(viewer) || 'Someone'}: ${a.owner ? `@${a.owner}` : 'the team'}, is this on track?`;
    update(a.id, { slackPingedAt: new Date().toISOString(), slackChannel: channel, history: log(text) });
    topToast(`Pinged ${channel} on Slack.`);
  };
  return <span className={`mvp-ping ${cooling ? 'is-cooling' : ''}`}>
    <button type="button" className="button button-small button-outline mvp-ping-btn" aria-disabled={cooling} aria-label={a.slackPingedAt ? `Slack ping sent ${timeAgo(a.slackPingedAt, now)}` : `Ping ${channel} on Slack`} onClick={ping}>
      <SlackIcon />{a.slackPingedAt ? `Sent ${timeAgo(a.slackPingedAt, now)}` : 'Ping on Slack'}
    </button>
    <span className="mvp-ping-tip" role="tooltip">{cooling ? `You can ping again in ${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')}` : a.slackPingedAt ? `Ping ${channel} again` : `Post a reminder in ${channel}`}</span>
  </span>;
}

type PickTarget = { kind?: Action['kind']; programme?: string; clientId?: string };
type PickOption = { name: string; role: string };

/** The client's account team (or the accelerator team) first, then everyone else; never the viewer. */
function ownerOptions(item: PickTarget, viewer?: string) {
  const related: PickOption[] = item.kind === 'programme'
    ? (PROGRAMME_TEAMS[item.programme || ''] || []).map(name => ({ name, role: 'Accelerator team' }))
    : (seedTeams()[item.clientId || ''] || []).map(m => ({ name: m.name, role: m.role }));
  const names = new Set(related.map(o => o.name));
  return { related: related.filter(o => o.name !== viewer), other: TEAM.filter(n => !names.has(n) && n !== viewer).map(name => ({ name, role: 'WIA team' })) };
}

export function OwnerPick({ item, viewer, current, onPick, onBack }: { item: PickTarget; viewer?: string; current?: string; onPick: (name: string) => void; onBack?: () => void }) {
  const { related, other } = ownerOptions(item, viewer);
  const option = (o: PickOption) => <button key={o.name} type="button" role="menuitem" className={`mvp-pick-option ${o.name === current ? 'is-current' : ''}`} onClick={() => onPick(o.name)}>
    <span className="mvp-pick-avatar" aria-hidden>{o.name.slice(0, 1)}</span>
    <span className="mvp-pick-text"><strong>{o.name}</strong><small>{o.name === current ? `${o.role} · current owner` : o.role}</small></span>
  </button>;
  return <div className="mvp-pick">
    {onBack && <button type="button" className="mvp-pick-back" onClick={onBack}>‹ Pending (team): who should own it?</button>}
    {related.length > 0 && <p className="mvp-pick-label">{item.kind === 'programme' ? 'On this accelerator' : 'On this client’s account team'}</p>}
    {related.map(option)}
    {other.length > 0 && <p className="mvp-pick-label">{related.length ? 'Other team members' : 'Team members'}</p>}
    {other.map(option)}
  </div>;
}

/**
 * Drag a board card onto another column (or onto a KPI tile when only one column shows).
 * Starts after 6px of movement so plain clicks still open the card; the drop target's tone-* class names the bucket.
 */
export function startCardDrag<T>(event: React.PointerEvent<HTMLElement>, item: T, drop: (item: T, bucket: string) => void) {
  if (event.button !== 0 || (event.target as HTMLElement).closest('.rb-check')) return;
  const el = event.currentTarget;
  const x0 = event.clientX, y0 = event.clientY;
  const board = el.closest('.rb-board');
  const kpiMode = !!board && board.querySelectorAll(':scope > .rb-column').length === 1;
  const targetClass = kpiMode ? 'rb-kpi' : 'rb-column';
  const mode = kpiMode ? 'mvp-dragging-kpi' : 'mvp-dragging-cols';
  let dragging = false;
  let over: Element | null = null;
  const targetAt = (x: number, y: number) => document.elementsFromPoint(x, y).find(n => n.classList?.contains(targetClass)) || null;
  const move = (m: PointerEvent) => {
    const dx = m.clientX - x0, dy = m.clientY - y0;
    if (!dragging) {
      if (Math.hypot(dx, dy) < 6) return;
      dragging = true;
      el.classList.add('mvp-lifted');
      document.body.classList.add('mvp-dragging', mode);
    }
    m.preventDefault();
    el.style.transform = `translate(${dx}px,${dy}px) rotate(1.5deg)`;
    const target = targetAt(m.clientX, m.clientY);
    if (target !== over) { over?.classList.remove('mvp-drop'); over = target; over?.classList.add('mvp-drop'); }
  };
  const up = () => {
    removeEventListener('pointermove', move);
    removeEventListener('pointerup', up);
    removeEventListener('pointercancel', up);
    if (!dragging) return;
    document.body.classList.remove('mvp-dragging', mode);
    // Swallow the click that follows the drop so the card doesn't open.
    const stop = (c: MouseEvent) => { c.stopPropagation(); c.preventDefault(); };
    addEventListener('click', stop, true);
    setTimeout(() => removeEventListener('click', stop, true), 0);
    const target = over;
    over?.classList.remove('mvp-drop');
    over = null;
    const bucket = target?.className.match(/tone-(\w+)/)?.[1];
    if (bucket) { el.classList.remove('mvp-lifted'); el.style.transform = ''; drop(item, bucket); return; }
    el.style.transition = 'transform .2s ease';
    el.style.transform = '';
    setTimeout(() => { el.style.transition = ''; el.classList.remove('mvp-lifted'); }, 200);
  };
  addEventListener('pointermove', move, { passive: false });
  addEventListener('pointerup', up);
  addEventListener('pointercancel', up);
}
