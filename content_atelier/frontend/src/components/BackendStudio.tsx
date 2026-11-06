import React, { useRef, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { CalendarClock, Download, FileText, Layers, Lightbulb, Plus, Search } from "lucide-react";
import type { FeatureFlags } from "../utils/workspace";
import { paths } from "../app/routes";
import { useApiQuery, useInvalidate } from "../api/query";
import { useMe } from "../utils/me";
import { weekLabel } from "../utils/editorialWeeks";
import { PageHeading } from "./PageHeading";
import { ThemedSelect } from "./ThemedSelect";
import { SeedCaptureModal } from "./SeedCapture";
import { useWriteFeedback } from "./shared/a11y";
import { OFFER_FILTERS, type OfferFilter } from "./studio/parts";
import { packPage, stageCounts, stagePath, useStudioWeek, useWeekReads, type StageCounts, type StageId, type StudioContext } from "./studio/studioWeek";

/** The stepper's stages in order (the 20 October mockup): each a path under /studio. Content Packs and Scheduled Content are
    out of scope unless packs are switched on (S.F2, R31). */
export function studioTabs(flags: FeatureFlags): [StageId, string][] {
  return [
    ["angles", "Content Angle"],
    ["briefs", "Content Briefing"],
    ...(flags.packs ? [["packs", "Content Packs"] as [StageId, string], ["scheduled", "Scheduled Content"] as [StageId, string]] : []),
  ];
}

const ICONS: Record<StageId, typeof Lightbulb> = { angles: Lightbulb, briefs: FileText, packs: Layers, scheduled: CalendarClock };

/** Each stage's counts in words, as the mockup's stepper says them. */
export function stageWords(stage: StageId, c: StageCounts, calendar: boolean): string {
  if (stage === "angles") return `${c.waiting} waiting · ${c.approved} approved · ${c.generated} generated`;
  if (stage === "briefs") return `${c.briefsWaiting} waiting · ${c.generated} generated`;
  if (stage === "packs") return `${c.generated} generated`;
  const pieces = `${c.published} ${c.published === 1 ? "piece" : "pieces"} published`;
  return `${c.awaitingPublication} awaiting publication · ${pieces}`;
}

/** "Download review": the week's review document (5.B14) as a Word file, one button in the header. */
export function DownloadReview({ weekId }: { weekId: string }) {
  return <a href={`/api/atelier/weeks/${encodeURIComponent(weekId)}/review.docx`} download
    className="inline-flex h-10 items-center gap-2 rounded-full border border-[#E6E9F0] bg-white px-4 text-[12px] font-medium text-[#34445F] hover:bg-[#F7F8FB]">
    <Download aria-hidden="true" className="w-3.5 h-3.5" />Download review</a>;
}

/** The Weekly Studio frame, as the mockup's: the title in the top bar with the week, "Download review", "Previous Concepts →"
    and "Flag idea"; the four-step stepper with each step's counts; the week's search and offer filter; then the step's
    screen. A content pack's page is shown on its own. */
export function BackendStudio({ flags, children }: { flags: FeatureFlags; children?: React.ReactNode }) {
  // A content pack's page, or a week's plan, shows its own week in the frame, without the week's search and filter.
  const page = packPage(useLocation().pathname);
  const shownPack = useApiQuery("/packs/{pack_id}", { path: { pack_id: page.packId } }, { enabled: !!page.packId });
  const detail = !!page.packId || !!page.weekId;
  const { week, isLatest, stage, weeks } = useStudioWeek(page.weekId || shownPack.data?.week_id || "");
  const { review, briefs, packs } = useWeekReads(week, flags.packs);
  const counts = stageCounts(review.data, briefs.data?.items, packs.data?.items);
  const { me } = useMe();
  const invalidate = useInvalidate();
  const feedback = useWriteFeedback();
  const [query, setQuery] = useState("");
  const [offer, setOffer] = useState<OfferFilter>("all");
  const [flagging, setFlagging] = useState(false);
  const flagRef = useRef<HTMLButtonElement>(null);
  const start = weeks.data?.find(w => w.week_id === week)?.week_start ?? (/^week_\d{4}-\d{2}-\d{2}$/.test(week) ? week.slice(5) : "");
  const range = start ? weekLabel(start) : "";
  const context: StudioContext = { week, query, offer };
  const tabs = studioTabs(flags);
  // A content pack has its own page header; it is shown without the Studio's frame.
  if (page.packId) return <>{children ?? <Outlet context={context} />}</>;
  const subtitle = range ? `${range} · ${isLatest ? "Latest week" : "Earlier week"}` : weeks.data && !weeks.data.length ? "No week has been stored yet." : "";
  return (
    <div className="space-y-6">
      {feedback.region}
      <PageHeading title="Weekly Studio" subtitle={subtitle} actions={<>
        {week && <DownloadReview weekId={week} />}
        <Link to={paths.previous} className="inline-flex h-10 items-center rounded-full border border-[#E6E9F0] bg-white px-4 text-[12px] text-[#34445F] hover:bg-[#F7F8FB]">Previous Concepts <span aria-hidden="true">&nbsp;→</span></Link>
        {me.can.edit_cards && <button ref={flagRef} type="button" onClick={() => setFlagging(true)} className="atelier-page-primary flex items-center gap-2 rounded-full px-5 text-[12px]"><Plus aria-hidden="true" className="w-3.5 h-3.5" /> Flag idea</button>}
      </>} />
      <nav aria-label="Editorial pipeline" className="editorial-pipeline">
        {tabs.map(([id, label]) => {
          const Icon = ICONS[id];
          const selected = id === stage;
          return <Link key={id} to={stagePath(id, week)} aria-current={selected ? "page" : undefined} className={`editorial-pipeline-step ${selected ? "is-selected" : ""}`}>
            <svg aria-hidden="true" className="editorial-pipeline-shape" viewBox="0 0 320 56" preserveAspectRatio="none">
              <path d="M28 1 H293 L318 28 L293 55 H28 A27 27 0 0 1 28 1 Z" vectorEffect="non-scaling-stroke" />
            </svg>
            <span className="editorial-pipeline-content"><Icon aria-hidden="true" className="w-4 h-4 shrink-0" /><span className="flex flex-col items-start gap-0.5">
              <span className="font-semibold">{label}</span><span className="editorial-pipeline-count">{stageWords(id, counts, flags.calendar)}</span></span></span>
          </Link>;
        })}
      </nav>
      {(!detail || !isLatest) && <div className="flex flex-wrap justify-between items-center gap-4 border-b border-[#E3E7EF] pb-4">
        <p className="text-[12px] text-[#8B93A3]">{!isLatest && week && <Link className="text-[#5070FF]" to={stagePath(stage, "")}>Go to the latest week</Link>}</p>
        {!detail && <div className="flex flex-wrap items-center gap-2 max-w-full">
          <div className="relative max-w-full"><Search aria-hidden="true" className="absolute top-3 left-3 w-3.5 h-3.5 text-[#9AA3B2]" />
            <input aria-label="Search this week" value={query} onChange={event => setQuery(event.target.value)} placeholder="Search this week…"
              className="h-9 w-60 max-w-full rounded-full border border-[#E6E9F0] bg-white pl-9 pr-3 text-[11px] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#8DA1FD]" /></div>
          <ThemedSelect aria-label="Filter by offer" value={offer} onChange={value => setOffer(value as OfferFilter)} className="h-9 px-3 text-[11px]">
            <option value="all">All offers</option>{OFFER_FILTERS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</ThemedSelect>
        </div>}
      </div>}
      {children ?? <Outlet context={context} />}
      {flagging && <SeedCaptureModal onClose={() => setFlagging(false)}
        onSaved={() => { void invalidate("/seeds"); feedback.announce("Flagged for the next cycle.", flagRef.current); }} />}
    </div>
  );
}
