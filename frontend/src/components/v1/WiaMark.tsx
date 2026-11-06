import { cn } from "@/lib/utils";

/** The round WIA monogram: hairline navy ring, serif initials. */
export function WiaMark({ className, title }: { className?: string; title?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      className={cn("v1-mark", className)}
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      <circle cx="32" cy="32" r="30.6" fill="none" stroke="currentColor" strokeWidth="1.3" />
      <text
        x="32"
        y="33"
        textAnchor="middle"
        dominantBaseline="central"
        fill="currentColor"
        className="v1-mark-text"
      >
        WIA
      </text>
    </svg>
  );
}
