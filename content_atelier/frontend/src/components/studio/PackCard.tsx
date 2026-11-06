import React from 'react';
import { Link } from 'react-router-dom';
import { Layers, Mail, Video } from 'lucide-react';
import type { PackSummaryV2 } from '../../api/types';
import { packReason } from '../HomeSummary';
import { packHref } from '../packParts';
import { CARD, Pill, type PillTone } from './parts';
import { TAKES } from './GenerationTime';

/* A content pack as a card in the 20 October mockup's form (src/mock EditorialHub's pack card): its type badge and state,
   the title, the pieces it holds, and "Open pack". */

const STATE: Record<string, { text: string; tone: PillTone }> = {
  finishing: { text: 'Being written', tone: 'progress' }, waiting: { text: 'Waiting', tone: 'alert' },
  in_review: { text: 'Generated', tone: 'quiet' }, ready_to_publish: { text: 'Generated', tone: 'quiet' },
  superseded: { text: 'Replaced by a newer version', tone: 'quiet' },
};
const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** One line under the pieces, only when there is something to say: the pack is being written, waits, or is partly published. */
export function packLeft(pack: Pick<PackSummaryV2, 'state' | 'pieces' | 'state_reason'>): string {
  if (pack.state === 'finishing') return `Being written from the approved brief. This takes ${TAKES.pack}.`;
  if (pack.state === 'waiting') return pack.state_reason ? `Waiting: ${packReason(pack.state_reason)}.` : 'Waiting to continue.';
  const published = pack.pieces.filter(p => p.published).length;
  if (!published) return '';
  return published === pack.pieces.length ? 'Every piece is published.' : `${published} of ${pack.pieces.length} pieces published.`;
}

/** The pieces as the mockup's chips: "1 Email", "1 Carousel", "3 Reels". */
function pieceChips(pack: PackSummaryV2): { icon: typeof Mail; text: string }[] {
  const written = pack.pieces.filter(p => p.origin !== 'not_written');
  const count = (channel: string) => written.filter(p => p.key.startsWith(channel)).length;
  return [
    count('email') ? { icon: Mail, text: plural(count('email'), 'Email') } : null,
    count('carousel') ? { icon: Layers, text: plural(count('carousel'), 'Carousel') } : null,
    count('reel') ? { icon: Video, text: plural(count('reel'), 'Reel') } : null,
  ].filter((chip): chip is { icon: typeof Mail; text: string } => !!chip);
}

export function PackCard({ pack, base }: { pack: PackSummaryV2; base: string; showWeek?: boolean }) {
  const state = STATE[pack.state] ?? STATE.in_review;
  const left = packLeft(pack);
  return <article className={`${CARD} !gap-3.5`} data-pack={pack.pack_id}>
    <div className="flex justify-between items-center gap-3">
      {pack.pillar ? <span className="rounded-md border border-[#D1DBFF] bg-[#EFF3FF] px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-[#5070FF]">{pack.pillar}</span> : <span />}
      <Pill tone={state.tone}>{state.text}</Pill>
    </div>
    <h3 className="font-editorial text-[22px] leading-tight text-[#1B2433]"><Link className="hover:underline" to={packHref(base, pack.pack_id)}>{pack.title}</Link></h3>
    <div className="grid grid-cols-3 gap-2" aria-label="The pieces">
      {pieceChips(pack).map(({ icon: Icon, text }) => <span key={text} className="flex items-center gap-2 rounded-xl border border-[#E6E9F0] bg-[#F7F8FB] px-3 py-2 text-[11px] text-[#34445F]">
        <Icon aria-hidden="true" strokeWidth={1.6} className="w-3.5 h-3.5 text-[#5070FF] shrink-0" />{text}</span>)}
    </div>
    {left && <p className="text-[12px] text-[#7A8496]">{left}</p>}
    <div className="pt-3 border-t border-[#EEF0F4] flex flex-wrap items-center gap-2">
      <Link className="text-[12px] font-semibold text-[#5070FF] hover:underline" to={packHref(base, pack.pack_id)} aria-label={`Open the content pack ${pack.title}`}>Open pack <span aria-hidden="true">→</span></Link>
    </div>
  </article>;
}
