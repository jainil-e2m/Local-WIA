import { useEffect, useState } from "react";

/**
 * Whether a media query currently matches, kept live as the viewport changes.
 * Answers false where matchMedia does not exist (jsdom, very old browsers).
 */
export function useMatchMedia(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window !== "undefined" && typeof window.matchMedia === "function"
      ? window.matchMedia(query).matches
      : false,
  );
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange();
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [query]);
  return matches;
}

/** The width at which the landing hero has room beside its copy for the marble and florals. */
export const HERO_WIDE = "(min-width: 1100px)";
