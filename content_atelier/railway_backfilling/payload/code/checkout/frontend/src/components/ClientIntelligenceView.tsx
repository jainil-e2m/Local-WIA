import React, { useState } from 'react';
import {
  ArrowUpRight, CalendarDays, CheckCircle2, ChevronRight, CircleAlert,
  FileText, MessageSquareText, Search, Sparkles, Target, TrendingDown,
} from 'lucide-react';

type Client = { name: string; offer: string; initials: string; health: 'Watch' | 'Stable' | 'Strong'; healthTone: string; leads: string; delta: string; nextCall: string; callType: string };

const clients: Client[] = [
  { name: 'The Ivory Co.', offer: 'Elevate', initials: 'IC', health: 'Watch', healthTone: 'bg-[#FFF4E8] text-[#A66326]', leads: '18 leads', delta: '−22% vs prior 30d', nextCall: 'Today, 2:00 PM', callType: 'Monthly strategy' },
  { name: 'Luna & Lace', offer: 'Elevate', initials: 'LL', health: 'Stable', healthTone: 'bg-[#EEF4FF] text-[#5070FF]', leads: '32 leads', delta: '+8% vs prior 30d', nextCall: 'Tomorrow, 11:30 AM', callType: 'Ads strategy review' },
  { name: 'Kindred Weddings', offer: 'Core', initials: 'KW', health: 'Strong', healthTone: 'bg-[#EDF8F2] text-[#38815A]', leads: '41 leads', delta: '+18% vs prior 30d', nextCall: 'Thu, 3:00 PM', callType: 'Messaging interview' },
  { name: 'Northstar Events', offer: 'Core', initials: 'NE', health: 'Stable', healthTone: 'bg-[#EEF4FF] text-[#5070FF]', leads: '24 leads', delta: '−3% vs prior 30d', nextCall: 'Fri, 10:00 AM', callType: 'LeadLock kickoff' },
];

const evidence = [
  { icon: MessageSquareText, label: 'Client call', text: '“We are seeing more inquiries, but fewer of them are booking.”', meta: 'Messaging & positioning interview · Sep 19' },
  { icon: TrendingDown, label: 'Google Ads', text: 'Lead volume is down 22% while cost per lead is up 14%.', meta: 'Last 30 days vs prior 30 days · synced 34m ago' },
  { icon: FileText, label: 'ClickUp', text: 'Landing page conversion tracking still needs verification.', meta: 'Task #WIA-482 · due Sep 27' },
];

export const ClientIntelligenceView: React.FC = () => {
  const [selectedClient, setSelectedClient] = useState(clients[0]);
  const [query, setQuery] = useState('');
  const visibleClients = clients.filter((client) => client.name.toLowerCase().includes(query.toLowerCase()));

  return <div className="space-y-7 pb-12">
    <section className="atelier-page-hero flex items-end justify-between gap-6">
      <div>
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-[#B99A43]"><Sparkles size={14} /> Owned client intelligence</div>
        <h1 className="atelier-page-title mt-3">Know what matters<br />before the call.</h1>
        <p className="atelier-page-subtitle max-w-xl">A concise, cited view of client context, performance and next actions — built for Whitney and the delivery team.</p>
      </div>
      <button className="atelier-page-primary rounded-full px-5 py-3 text-xs flex items-center gap-2 shadow-wia-btn"><CalendarDays size={15} /> Open today’s call prep <ArrowUpRight size={14} /></button>
    </section>

    <div className="grid grid-cols-1 xl:grid-cols-[1.45fr_1fr] gap-5">
      <section className="rounded-[24px] border border-[#E6E9F0] bg-white p-5 shadow-saas-card">
        <div className="flex items-start justify-between gap-4 mb-5"><div><p className="text-[11px] uppercase tracking-[0.15em] text-[#9AA3B2]">Today’s briefing</p><h2 className="font-editorial text-[25px] text-[#173354] mt-1">The Ivory Co.</h2><p className="text-xs text-[#788398] mt-1">Monthly strategy call · Today at 2:00 PM</p></div><span className="px-3 py-1.5 rounded-full text-[11px] font-semibold bg-[#FFF4E8] text-[#A66326]">Needs attention</span></div>
        <div className="grid grid-cols-3 gap-3 mb-5">{[['Lead volume', '18', '−22%'], ['Cost / lead', '$84', '+14%'], ['Client sentiment', 'Cautious', '2 signals']].map(([label, value, delta]) => <div key={label} className="rounded-2xl bg-[#F8F9FC] border border-[#EEF0F4] p-3"><p className="text-[10px] text-[#9199A7]">{label}</p><p className="text-[17px] font-semibold text-[#1B2838] mt-1">{value}</p><p className="text-[10px] text-[#A66326] mt-1">{delta}</p></div>)}</div>
        <div className="rounded-2xl bg-[#F8FAFF] border border-[#DDE6FF] p-4"><div className="flex items-center gap-2 text-[11px] font-semibold text-[#5070FF]"><Target size={14} /> What to bring into the room</div><p className="text-[13px] leading-6 text-[#34445F] mt-2">Lead quality is the central conversation. Confirm whether the booking drop is qualification or follow-up, then agree on a tracking check before changing budget.</p><button className="text-[11px] text-[#5070FF] font-semibold mt-2 flex items-center gap-1">View supporting evidence <ChevronRight size={13} /></button></div>
      </section>
      <section className="rounded-[24px] border border-[#E6E9F0] bg-[#1B2838] p-5 text-white shadow-saas-card"><div className="flex items-center justify-between"><div><p className="text-[11px] uppercase tracking-[0.15em] text-[#A9B8D8]">Team focus</p><h2 className="font-editorial text-[25px] mt-1">Open loops</h2></div><CircleAlert size={19} className="text-[#E5B744]" /></div><p className="text-[12px] leading-5 text-[#C4CEDF] mt-3">4 actions need an owner or a response before the next client touchpoint.</p><div className="space-y-3 mt-5">{['Verify Ivory Co. conversion tracking', 'Send Luna & Lace revised lead recap', 'Confirm Northstar LeadLock access'].map((item, index) => <div className="flex gap-3 items-start" key={item}><div className="mt-0.5 w-4 h-4 rounded-full border border-[#70809F] flex items-center justify-center text-[9px] text-[#E5B744]">{index === 0 ? '!' : ''}</div><div><p className="text-[12px] text-white">{item}</p><p className="text-[10px] text-[#93A0B8] mt-1">{index === 0 ? 'Due today · Carmen' : 'Needs owner · Team'}</p></div></div>)}</div><button className="mt-5 w-full rounded-full bg-white/10 hover:bg-white/15 py-2.5 text-[11px] font-semibold text-[#E8EDF8]">Open action register <ArrowUpRight size={13} className="inline ml-1" /></button></section>
    </div>

    <section><div className="flex items-end justify-between mb-4"><div><p className="text-[11px] uppercase tracking-[0.15em] text-[#B99A43]">Portfolio view</p><h2 className="font-editorial text-[28px] text-[#173354]">All clients, at a glance</h2></div><label className="relative"><Search size={15} className="absolute left-3 top-2.5 text-[#A8B0BE]" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a client" className="w-48 rounded-full border border-[#E6E9F0] bg-white py-2 pl-9 pr-3 text-xs outline-none focus:border-[#8DA1FD]" /></label></div><div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">{visibleClients.map((client) => <button key={client.name} onClick={() => setSelectedClient(client)} className={`text-left rounded-[20px] border bg-white p-4 transition-all ${selectedClient.name === client.name ? 'border-[#8DA1FD] shadow-[0_8px_28px_rgba(80,112,255,.12)]' : 'border-[#E6E9F0] shadow-saas-card hover:border-[#C9D3F5]'}`}><div className="flex justify-between items-start"><span className="w-9 h-9 rounded-full bg-[#EEF3FF] text-[#5070FF] text-xs font-semibold flex items-center justify-center">{client.initials}</span><span className={`px-2 py-1 rounded-full text-[10px] font-semibold ${client.healthTone}`}>{client.health}</span></div><h3 className="font-semibold text-[13px] text-[#1B2838] mt-4">{client.name}</h3><p className="text-[10px] text-[#9199A7] mt-1">{client.offer} · {client.leads}</p><div className="border-t border-[#F0F1F4] mt-4 pt-3"><p className="text-[10px] text-[#A66326]">{client.delta}</p><p className="text-[10px] text-[#788398] mt-2 flex items-center gap-1"><CalendarDays size={11} /> {client.nextCall}</p></div></button>)}</div></section>

    <section className="rounded-[24px] border border-[#E6E9F0] bg-white p-5 shadow-saas-card"><div className="flex justify-between items-center mb-4"><div><p className="text-[11px] uppercase tracking-[0.15em] text-[#9AA3B2]">Evidence trail</p><h2 className="font-editorial text-[24px] text-[#173354] mt-1">Why The Ivory Co. is on watch</h2></div><span className="text-[10px] text-[#9199A7] flex items-center gap-1"><CheckCircle2 size={13} className="text-[#38815A]" /> Every insight is sourced</span></div><div className="grid grid-cols-1 md:grid-cols-3 gap-3">{evidence.map(({ icon: Icon, label, text, meta }) => <div key={label} className="rounded-2xl border border-[#EEF0F4] p-4"><div className="flex items-center gap-2 text-[10px] font-semibold text-[#5070FF]"><Icon size={14} /> {label}</div><p className="text-[12px] leading-5 text-[#34445F] mt-3">{text}</p><p className="text-[10px] leading-4 text-[#9AA3B2] mt-3">{meta}</p></div>)}</div></section>
  </div>;
};
