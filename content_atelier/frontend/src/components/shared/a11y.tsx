import React, { useCallback, useEffect, useRef, useState } from 'react';

/* Focus and announcements around writes and swapped controls (6.F6).

   After a write the control the person pressed is often gone: a card or a brief is keyed by its version, a pack's new
   version opens in place, a form closes. Focus would fall back to the page and a screen reader would hear nothing.
   `useWriteFeedback` says the result in a polite live region and moves focus to a stable place on the page as it is after
   the write: the new version's heading, or the control's replacement. Its region is rendered above the part that is
   replaced, so the announcement survives the remount.

   A focus target carries `data-focus-key`; the key names the version it belongs to (`angle:<id>:<hash>`), so the target of a
   write is found only once the page shows the version the write made, never the old one about to be replaced. */

/** The selector of an element by its focus key. */
export const focusKey = (key: string) => `[data-focus-key="${key}"]`;
/** Any element whose focus key starts with this prefix (a brief opened by id whose version is not read yet). */
export const focusKeyPrefix = (prefix: string) => `[data-focus-key^="${prefix}"]`;

const WAIT_MS = 10_000;
const FOCUSABLE = 'a[href],button,input,select,textarea,[tabindex]';

/** Focus without changing what the element is: a heading or a line gets tabindex -1 so it can take focus, but stays out of
    the tab order. */
export function focusElement(element: HTMLElement) {
  if (!element.matches(FOCUSABLE)) element.setAttribute('tabindex', '-1');
  element.focus();
}

/** A polite live region whose text is said once per announcement, even when the same words are said twice in a row. */
export function LiveRegion({ text, count = 0 }: { text: string; count?: number }) {
  return <div role="status" aria-live="polite" aria-atomic="true" className="sr-only" data-live-region>{text && <span key={count}>{text}</span>}</div>;
}

/** What an action did, shown for a few seconds at the bottom of the screen, so a sighted person sees it as well as hears it
    (the live region above says it to a screen reader). Each new message restarts the time. */
export function Confirmation({ text, count = 0 }: { text: string; count?: number }) {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (!text) return;
    setShown(true);
    const timer = setTimeout(() => setShown(false), 4500);
    return () => clearTimeout(timer);
  }, [text, count]);
  if (!text) return null;
  return <div aria-hidden="true" data-confirmation className={`pointer-events-none fixed bottom-6 left-1/2 z-[60] -translate-x-1/2 rounded-full bg-[#1B2838] px-5 py-2.5 text-[13px] font-medium text-white shadow-[0_12px_32px_rgba(16,24,40,0.28)] transition-all duration-300 ${shown ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}`}>{text}</div>;
}

export type WriteTarget = string | HTMLElement | null | undefined;

export function useWriteFeedback() {
  const [said, setSaid] = useState({ text: '', count: 0 });
  const stop = useRef<() => void>(() => {});
  useEffect(() => () => stop.current(), []);

  /** Says `text` and moves focus to `target` once it is on the page: a selector (usually `focusKey(...)`), or the element the
      person was on when the write started (it is focused again once it is back and enabled). Focus is moved only if the
      person has not gone somewhere else meanwhile. */
  const announce = useCallback((text: string, target?: WriteTarget) => {
    setSaid(previous => ({ text, count: previous.count + 1 }));
    stop.current();
    if (!target || typeof document === 'undefined') return;
    const origin = document.activeElement;
    const find = () => {
      const element = typeof target === 'string' ? document.querySelector<HTMLElement>(target) : target;
      return element && element.isConnected && !element.matches(':disabled') ? element : null;
    };
    const free = () => {
      const active = document.activeElement;
      return !active || active === document.body || active === origin || !active.isConnected || active.matches(':disabled');
    };
    const attempt = () => {
      const element = find();
      if (!element) return false;
      if (free()) focusElement(element);
      return true;
    };
    if (attempt()) return;
    const observer = new MutationObserver(() => { if (attempt()) stop.current(); });
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['disabled', 'data-focus-key'] });
    const timer = setTimeout(() => stop.current(), WAIT_MS);
    stop.current = () => { observer.disconnect(); clearTimeout(timer); stop.current = () => {}; };
  }, []);

  return { announce, region: <><LiveRegion text={said.text} count={said.count} /><Confirmation text={said.text} count={said.count} /></> };
}

/** For a control that swaps itself for a small form ("Edit", "Mark done", "Attest it is true", "Grant"): when the person
    opens it focus moves to the form's field, and when they cancel it moves back to the control. Call `arm()` in the click
    that opens or cancels; a form closed by a save is left to the write's own focus target. */
export function useSwapFocus(open: boolean) {
  const field = useRef<HTMLElement | null>(null);
  const control = useRef<HTMLElement | null>(null);
  const armed = useRef(false);
  useEffect(() => {
    if (!armed.current) return;
    armed.current = false;
    (open ? field.current : control.current)?.focus();
  }, [open]);
  return {
    arm: () => { armed.current = true; },
    fieldRef: (element: HTMLElement | null) => { field.current = element; },
    controlRef: (element: HTMLElement | null) => { control.current = element; },
  };
}
