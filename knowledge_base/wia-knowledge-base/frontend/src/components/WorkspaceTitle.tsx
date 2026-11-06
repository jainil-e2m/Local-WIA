import { useId } from 'react';
import { Info } from 'lucide-react';
import './WorkspaceTitle.css';

export default function WorkspaceTitle({ title, description }: { title: string; description: string }) {
  const tooltipId = useId();
  return <div className="workspace-title"><h1>{title}</h1><span className="workspace-title-help"><button type="button" className="icon-button" aria-label={`About ${title}`} aria-describedby={tooltipId}><Info size={18} /></button><span id={tooltipId} className="workspace-title-tooltip" role="tooltip">{description}</span></span></div>;
}
