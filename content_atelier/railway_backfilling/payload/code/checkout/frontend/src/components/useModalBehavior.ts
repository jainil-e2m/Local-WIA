import { useEffect, useRef } from 'react';

export function useModalBehavior(onClose: () => void) {
  const modalRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverflow = document.documentElement.style.overflow;
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';
    const modal = modalRef.current;
    const focusable = () => Array.from(modal?.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex="0"]') ?? []).filter(element => element.getClientRects().length > 0);
    (focusable()[0] ?? modal)?.focus({ preventScroll: true });
    const onKeyDown = (event: KeyboardEvent) => {
      // Let the development annotation popup handle its own Escape and Tab keys.
      if (import.meta.env.DEV && event.composedPath().some(target => target instanceof Element && target.closest('[data-agentation-root], [data-agentation-portal]'))) return;
      if (event.key === 'Escape') { event.preventDefault(); closeRef.current(); }
      if (event.key !== 'Tab') return;
      const elements = focusable();
      const first = elements[0];
      const last = elements[elements.length - 1];
      if (!first) { event.preventDefault(); modal?.focus(); return; }
      if (event.shiftKey && (document.activeElement === first || document.activeElement === modal)) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.overflow = previousHtmlOverflow;
      document.removeEventListener('keydown', onKeyDown);
      if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
    };
  }, []);
  return modalRef;
}
