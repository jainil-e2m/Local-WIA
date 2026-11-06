import { useRef, type PointerEvent } from "react";
import { ArrowRight } from "lucide-react";
import { ATELIER_LAUNCH_PATH, ATELIER_UNAVAILABLE } from "@/lib/atelierLaunch";
import { ActionLink } from "../ActionLink";
import type { LibraryItem } from "./automations";
import { CardArt } from "./Art";

/* One automation in the library: its number and status, a collage of what
   it does, then its name, a line about it and the way in. Under a mouse
   the collage's layers drift apart with the pointer, nearer pieces more,
   fed by two custom properties (--mx, --my, -1…1). */

export function Tile({
  item,
  index,
  playing,
  atelierUrl,
}: {
  item: LibraryItem;
  index: number;
  playing: boolean;
  atelierUrl?: string;
}) {
  const cardRef = useRef<HTMLElement>(null);
  const titleId = `v1-tile-${item.id}`;
  const live = item.status === "Live";

  const drift = (e: PointerEvent<HTMLElement>) => {
    const el = cardRef.current;
    if (!el || e.pointerType !== "mouse") return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--mx", (((e.clientX - r.left) / r.width) * 2 - 1).toFixed(3));
    el.style.setProperty("--my", (((e.clientY - r.top) / r.height) * 2 - 1).toFixed(3));
  };
  const settle = () => {
    cardRef.current?.style.removeProperty("--mx");
    cardRef.current?.style.removeProperty("--my");
  };

  return (
    <article
      ref={cardRef}
      className={`v1-auto${playing ? " is-playing" : ""}`}
      aria-labelledby={titleId}
      onPointerMove={drift}
      onPointerLeave={settle}
    >
      <header className="v1-auto-top">
        <span className="v1-auto-index" aria-hidden>
          {String(index + 1).padStart(2, "0")}
        </span>
        <span className={`v1-auto-status ${live ? "is-live" : "is-soon"}`}>{item.status}</span>
      </header>

      <CardArt id={item.id} />

      <div className="v1-auto-body">
        <h3 id={titleId}>{item.name}</h3>
        <p>{item.description}</p>
        <CardAction item={item} atelierUrl={atelierUrl} />
      </div>
    </article>
  );
}

function CardAction({ item, atelierUrl }: { item: LibraryItem; atelierUrl?: string }) {
  const arrow = <ArrowRight aria-hidden strokeWidth={1.7} />;
  /* The Atelier is its own deployment, reached through the authenticated
     server hand-off; where none is configured the button stays, disabled. */
  if (item.id === "content-atelier") {
    return atelierUrl ? (
      <a className="v1-auto-cta" href={ATELIER_LAUNCH_PATH} aria-label="View Content Atelier">
        View Here {arrow}
      </a>
    ) : (
      <button className="v1-auto-cta" type="button" disabled title={ATELIER_UNAVAILABLE}>
        View Here {arrow}
      </button>
    );
  }
  if (!item.action) return null;
  return (
    <ActionLink action={item.action} className={`v1-auto-cta${item.status === "Live" ? "" : " is-roadmap"}`}>
      {item.cta} {arrow}
    </ActionLink>
  );
}
