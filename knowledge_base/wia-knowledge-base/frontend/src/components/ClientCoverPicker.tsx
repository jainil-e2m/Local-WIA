import { useState } from 'react';
import { Check } from 'lucide-react';
import { CLIENT_COVERS, coverById, type CoverCategory } from '../clientCovers';

/** The cover library: category filter, thumbnails and the selected photo's credit. Used in the client editor's Cover tab. */
export default function CoverLibrary({ value, onChange }: { value: string; onChange: (id: string) => void }) {
  const [category, setCategory] = useState<CoverCategory | 'All'>('All');
  const cover = coverById(value);
  const visible = CLIENT_COVERS.filter(item => category === 'All' || item.category === category);
  return <div className="cover-library">
    <div className="cover-picker-tools"><div className="cover-filters" role="group" aria-label="Filter cover library">{(['All', 'Architecture', 'Botanical', 'Texture'] as const).map(item => <button type="button" key={item} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>)}</div><span>{CLIENT_COVERS.length} covers</span></div>
    <div className="cover-options" role="group" aria-label="Choose a client cover">{visible.map(item => <button type="button" key={item.id} className={`cover-option ${value === item.id ? 'is-selected' : ''}`} aria-pressed={value === item.id} onClick={() => onChange(item.id)}><div><img src={item.image} alt="" loading="lazy" style={{ objectPosition: item.position }} />{value === item.id && <span className="cover-check"><Check size={14} /></span>}</div><span>{item.name}</span></button>)}</div>
    <div className="cover-credit"><span>{cover.name} · {cover.credit}</span>{cover.source && <a href={cover.source} target="_blank" rel="noreferrer">View original ↗</a>}</div>
  </div>;
}
