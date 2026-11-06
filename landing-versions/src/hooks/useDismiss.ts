import { useEffect, useRef } from "react";

/**
 * Close a popup on an outside pointer press or on Escape.
 *
 * Shared by the two popup families that draw their own list rather than
 * delegating to the OS: the dark intake controls (`ui/field-menu`) and the
 * light Ops Hub `Menu`. The dismissal contract is identical in both and easy
 * to get subtly wrong — `mousedown` rather than `click`, so a press that
 * starts outside closes the list before the click resolves, and `touchstart`
 * alongside it so the same holds on touch.
 *
 * Returns the ref to attach to the popup's root element. Anything inside that
 * root is treated as part of the popup and does not dismiss it.
 */
export function useDismiss<T extends HTMLElement = HTMLDivElement>(
  open: boolean,
  close: () => void,
) {
  const rootRef = useRef<T | null>(null);

  useEffect(() => {
    if (!open) return;

    const onPointerDown = (event: MouseEvent | TouchEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) close();
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("touchstart", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("touchstart", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, close]);

  return rootRef;
}
