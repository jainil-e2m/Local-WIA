// Fictional ad-performance context for Call Preparation v2.
// Paid media is not an approved KB source, so every figure here is attributed to Viktor's analysis.

export type PerfStatus = 'On track' | 'Watch' | 'Problem' | 'No data';
export interface ChannelPerf {
  channel: 'Google Ads' | 'Meta Ads';
  status: PerfStatus;
  /** [since last call, same length of time before] */
  spend?: [number, number];
  leads?: [number, number];
  note: string;
}
export interface ClientPerf { channels: ChannelPerf[]; tracking: { ok: boolean; note: string }; source: string; asOf: string; empty?: string }

export const PERFORMANCE: Record<string, ClientPerf> = {
  bloom: { source: 'Viktor’s analysis', asOf: '2026-10-06', tracking: { ok: true, note: 'Google and Meta conversions recording' },
    channels: [
      { channel: 'Google Ads', status: 'Watch', spend: [1840, 1790], leads: [23, 28], note: 'Leads down 18% on similar spend; search terms drifting to “cheap wedding venue”.' },
      { channel: 'Meta Ads', status: 'On track', spend: [960, 1010], leads: [14, 13], note: 'Steady. Gallery creative is the best performer.' },
    ] },
  rosewood: { source: 'Viktor’s analysis', asOf: '2026-10-07', tracking: { ok: true, note: 'Meta pixel and LeadLock forms recording' },
    channels: [{ channel: 'Meta Ads', status: 'On track', spend: [1250, 1180], leads: [31, 27], note: 'More leads at a lower cost; winter tours not yet advertised.' }] },
  everly: { source: 'Viktor’s analysis', asOf: '2026-10-06', tracking: { ok: true, note: 'Meta pixel recording' },
    channels: [{ channel: 'Meta Ads', status: 'Watch', spend: [620, 600], leads: [9, 11], note: 'Fewer leads; ads still promote autumn dates that are fully booked.' }] },
  harbor: { source: 'Viktor’s analysis', asOf: '2026-10-08', tracking: { ok: false, note: 'No tracking set up yet' }, channels: [], empty: 'No ad spend yet: ads start after the LeadLock setup.' },
  willow: { source: 'Programme member', asOf: '2026-10-08', tracking: { ok: false, note: 'Member runs her own ads; WIA has no account access' }, channels: [], empty: 'Maya manages her own Meta account; numbers come only from what she shares in office hours.' },
  magnolia: { source: 'Viktor’s analysis', asOf: '2026-10-08', tracking: { ok: true, note: 'Conversion tracking fixed Oct 7; needs a check that it’s recording' },
    channels: [{ channel: 'Google Ads', status: 'Watch', spend: [540, 500], leads: [6, 2], note: 'Conversions jumped after the tracking fix; too early to tell if real.' }] },
};

export const perfStatus = (p?: ClientPerf): PerfStatus => !p || !p.channels.length ? 'No data' : p.channels.some(c => c.status === 'Problem') ? 'Problem' : p.channels.some(c => c.status === 'Watch') ? 'Watch' : 'On track';
