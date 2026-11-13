import { ArrowRight, CheckCircle2, Quote } from 'lucide-react';
import { clientById, dateLabel, sourceById } from '../data';
import { Badge, Dialog, SourceIcon } from './UI';
import type { ClientTab } from '../types';

export default function EvidenceDrawer({ id, onClose, openClient }: { id: string; onClose: () => void; openClient: (id: string, tab?: ClientTab) => void }) {
  const source = sourceById(id);
  if (!source) return null;
  const client = clientById(source.clientId);
  return <Dialog title="Behind the insight" subtitle="Source evidence" drawer onClose={onClose}><div className="evidence-source"><span className={`source-mark source-${source.kind.toLowerCase()}`}><SourceIcon kind={source.kind} size={22} /></span><div><h3>{source.title}</h3><p>{source.kind} · {dateLabel(source.date)} · {client.name}</p></div></div><div className="evidence-meta"><Badge tone="blue" dot={false}>{source.tag}</Badge><span>{source.locator}</span></div><div className="evidence-quote"><Quote size={24} strokeWidth={1.2} /><p>{source.excerpt}</p></div><dl className="detail-list"><div><dt>Recorded by</dt><dd>{source.author}</dd></div><div><dt>Client</dt><dd>{client.name}</dd></div><div><dt>Source date</dt><dd>{dateLabel(source.date, { day: 'numeric', month: 'long', year: 'numeric' })}</dd></div><div><dt>Record type</dt><dd>Fictional preview excerpt</dd></div></dl><div className="note-box"><CheckCircle2 size={16} /><p>The statement and its interpretation are shown separately. This excerpt is sample content for the frontend review.</p></div><button className="button button-primary full-width" onClick={() => { onClose(); openClient(client.id, 'history'); }}>See the client’s full history<ArrowRight size={15} /></button></Dialog>;
}
