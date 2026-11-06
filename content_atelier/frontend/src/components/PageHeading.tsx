import React, { createContext, useContext } from 'react';
import { createPortal } from 'react-dom';

/** Where the page's own header goes: the shell's top bar, beside the bell and the account. */
export const PageHeaderSlot = createContext<HTMLElement | null>(null);

interface PageHeadingProps {
  title: string;
  /** One short line under the title (the week, a count). */
  subtitle?: React.ReactNode;
  /** The page's main buttons, shown at the right of the title. */
  actions?: React.ReactNode;
  /** Kept for older callers; no longer shown. */
  description?: string;
}

/** The page's title, with its one-line subtitle and its main buttons, drawn in the shell's top bar so the page starts at
    the top. Outside the shell (a test, a dialog) it is drawn in place. */
export function PageHeading({ title, subtitle, actions }: PageHeadingProps) {
  const slot = useContext(PageHeaderSlot);
  const header = <div className="atelier-page-header flex flex-wrap lg:flex-nowrap items-start justify-between gap-x-6 gap-y-3 min-w-0">
    {/* The title keeps at least about 20rem; on a narrower screen the buttons move under it rather than squeezing it. */}
    <div className="min-w-0 flex-[1_1_20rem]">
      <h1 className="atelier-page-title">{title}</h1>
      {subtitle && <p className="mt-1 text-[13px] text-[#B99A43]">{subtitle}</p>}
    </div>
    {actions && <div className="flex flex-wrap items-center gap-2.5 shrink-0 lg:pt-1.5">{actions}</div>}
  </div>;
  return slot ? createPortal(header, slot) : header;
}
