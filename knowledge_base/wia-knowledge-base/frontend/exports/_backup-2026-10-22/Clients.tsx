import { ThemedSelect } from '../components/ThemedSelect';
import { useState } from 'react';
import { ArrowRight, ArrowUpRight, CalendarDays, LayoutGrid, List, Users } from 'lucide-react';
import { CALLS, CLIENTS, dateLabel, isOutstanding, timeLabel } from '../data';
import { Avatar, Badge, Coverage, Empty, SearchField, Segmented, Sparkline } from '../components/UI';
import type { WorkspaceProps } from '../types';

export default function Clients(props: WorkspaceProps) {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [layout, setLayout] = useState('grid');
  const [sort, setSort] = useState('attention');
  const filtered = CLIENTS.filter(client => `${client.name} ${client.contact} ${client.service} ${client.location}`.toLowerCase().includes(query.toLowerCase()) && (filter === 'all' || filter === 'watch' && client.health === 'Needs attention' || filter === client.type)).sort((a, b) => sort === 'name' ? a.name.localeCompare(b.name) : Number(b.health === 'Needs attention') - Number(a.health === 'Needs attention'));
  return <div className="view"><div className="toolbar"><Segmented label="Filter client portfolio" value={filter} onChange={setFilter} options={[{ id: 'all', label: 'All clients', count: 6 }, { id: 'watch', label: 'Needs attention', count: 2 }, { id: 'retainer', label: 'Retainers', count: 4 }, { id: 'accelerator', label: 'Accelerators', count: 2 }]} /><div className="toolbar-right"><SearchField label="Search clients" placeholder="Find a client…" value={query} onChange={setQuery} /><label className="sr-only" htmlFor="client-sort">Sort clients</label><ThemedSelect aria-label="Sort clients" id="client-sort" value={sort} onChange={value => setSort(value)}><option value="attention">Attention first</option><option value="name">A to Z</option></ThemedSelect><div className="layout-toggle" role="group" aria-label="Portfolio layout"><button className={layout === 'grid' ? 'selected' : ''} aria-label="Card view" aria-pressed={layout === 'grid'} onClick={() => setLayout('grid')}><LayoutGrid size={16} /></button><button className={layout === 'list' ? 'selected' : ''} aria-label="List view" aria-pressed={layout === 'list'} onClick={() => setLayout('list')}><List size={17} /></button></div></div></div>
    {!filtered.length ? <Empty title="No clients match your search" /> : <div className={`client-grid ${layout === 'list' ? 'client-list' : ''}`}>{filtered.map(client => {
      const call = CALLS.find(item => item.clientId === client.id);
      const open = props.actions.filter(a => a.clientId === client.id && isOutstanding(a));
      return <article className="client-card" key={client.id}><div className="client-card-top"><Avatar client={client} /><Badge tone={client.health === 'On track' ? 'green' : client.tone}>{client.health}</Badge></div><button className="client-name-link" onClick={() => props.openClient(client.id)}><h2>{client.name}</h2><ArrowUpRight size={16} /></button><p className="client-card-meta">{client.category} · {client.location}</p><span className="service-label">{client.service}</span><p className="client-card-focus">{client.focus}</p><div className="client-card-stats"><div><span className="small-label">OPEN ACTIONS</span><strong>{open.length.toString().padStart(2, '0')}</strong></div><div><span className="small-label">12-WEEK ACTIVITY</span><Sparkline values={client.activity} tone={client.tone} /></div></div><div className="client-card-coverage"><span>Source coverage</span><Coverage value={client.coverage} /></div><div className="client-card-footer"><span><CalendarDays size={13} />{call ? `${dateLabel(call.date)} · ${timeLabel(call.time)}` : 'No upcoming call'}</span><button className="text-button" onClick={() => props.openClient(client.id)}>Open record<ArrowRight size={14} /></button></div></article>;
    })}</div>}
    <div className="quiet-footer"><Users size={14} />Each client has one maintained record. All views read from that same history.</div>
  </div>;
}
