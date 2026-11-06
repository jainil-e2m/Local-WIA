import React, { useId } from 'react';
import { Info } from 'lucide-react';

/** Shared page title with contextual help available on hover or keyboard focus. */
export function PageHeading({ title, description }: { title: string; description: string }) {
  const infoId = useId();
  return <div className="flex items-center gap-3">
    <h1 className="atelier-page-title">{title}</h1>
    {/* Optical alignment with the serif letterforms, rather than their taller line box. */}
    <span className="relative top-[3px] inline-flex items-center justify-center group/page-info shrink-0 leading-none">
      <button type="button" aria-label={`About ${title}`} aria-describedby={infoId} className="flex h-7 w-7 items-center justify-center rounded-full text-[#B99A39] hover:bg-[#FFF8E9] focus-visible:outline-2 focus-visible:outline-[#8DA1FD] cursor-default">
        <Info className="w-[18px] h-[18px]" strokeWidth={1.75} />
      </button>
      <span id={infoId} role="tooltip" className="absolute right-0 top-full mt-2 z-40 w-72 max-w-[calc(100vw-3rem)] rounded-xl border border-[#E6E9F0] bg-white p-4 text-[12px] leading-relaxed font-normal text-[#667184] shadow-saas-dropdown invisible opacity-0 transition-opacity group-hover/page-info:visible group-hover/page-info:opacity-100 group-focus-within/page-info:visible group-focus-within/page-info:opacity-100">
        {description}
      </span>
    </span>
  </div>;
}
