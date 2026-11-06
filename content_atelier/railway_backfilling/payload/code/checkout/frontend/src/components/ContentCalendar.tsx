import React, { useId, useMemo, useState, useEffect } from "react";
import { ChevronLeft, ChevronRight, Info } from "lucide-react";
import { SavedSchedule } from "../types/production";
import { civilFields } from "../utils/production";
import { CalendarEntry as DeskPost } from "../types/calendar";
import { calendarDayPreview } from "../utils/calendarDisplay";
import { CalendarDayModal } from "./CalendarDayModal";
interface ContentCalendarProps {
  entries: SavedSchedule[];
  onOpenEntry: (entry: SavedSchedule) => void;
  timezone: string;
  query?: string;
  initialMonth?: { year: number; month: number };
  onMonthChange?: (month: { year: number; month: number }) => void;
}
type DeskView = "month" | "week" | "day";
const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] as const;
const WEEKDAY_FULL = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];
const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
interface CalendarCell {
  key: string;
  label: number;
  inMonth: boolean;
  monthDay: number | null;
}
function shiftMonth(cursor: { year: number; month: number }, delta: number) {
  const date = new Date(cursor.year, cursor.month + delta, 1);
  return { year: date.getFullYear(), month: date.getMonth() };
}
export function buildCivilMonth(cursor: {
  year: number;
  month: number;
}): CalendarCell[] {
  const firstWeekday = new Date(cursor.year, cursor.month, 1).getDay();
  const leading = (firstWeekday + 6) % 7;
  const daysInMonth = new Date(cursor.year, cursor.month + 1, 0).getDate();
  const prevDays = new Date(cursor.year, cursor.month, 0).getDate();
  const cells: CalendarCell[] = [];
  for (let i = leading - 1; i >= 0; i -= 1) {
    const day = prevDays - i;
    cells.push({
      key: `lead-${day}`,
      label: day,
      inMonth: false,
      monthDay: null,
    });
  }
  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push({ key: `day-${day}`, label: day, inMonth: true, monthDay: day });
  }
  let trail = 1;
  while (cells.length % 7 !== 0) {
    cells.push({
      key: `trail-${trail}`,
      label: trail,
      inMonth: false,
      monthDay: null,
    });
    trail += 1;
  }
  return cells;
}
export const ContentCalendar: React.FC<ContentCalendarProps> = ({
  entries,
  onOpenEntry,
  timezone,
  query = "",
  initialMonth,
  onMonthChange,
}) => {
  const today = civilFields(new Date(), timezone).date;
  const [cursor, setCursor] = useState(
    initialMonth || {
      year: Number(today.slice(0, 4)),
      month: Number(today.slice(5, 7)) - 1,
    },
  );
  const [view, setView] = useState<DeskView>("month");
  const [focusDay, setFocusDay] = useState(Number(today.slice(8)));
  const [agendaDay, setAgendaDay] = useState<number | null>(null);
  useEffect(() => {
    const media = window.matchMedia("(max-width: 640px)");
    const adapt = () => {
      if (media.matches) setView("day");
    };
    adapt();
    media.addEventListener("change", adapt);
    return () => media.removeEventListener("change", adapt);
  }, []);
  useEffect(() => {
    onMonthChange?.(cursor);
    setAgendaDay(null);
    setFocusDay((day) =>
      Math.min(day, new Date(cursor.year, cursor.month + 1, 0).getDate()),
    );
  }, [cursor, onMonthChange]);
  const cells = useMemo(() => buildCivilMonth(cursor), [cursor]);
  const needle = query.trim().toLowerCase();
  const postsForDay = (
    day: number | null,
    respectSearch = true,
  ): DeskPost[] => {
    if (day === null) return [];
    return entries.flatMap((entry) => {
      const fields = civilFields(entry.scheduled_for, timezone);
      if (
        Number(fields.date.slice(0, 4)) !== cursor.year ||
        Number(fields.date.slice(5, 7)) - 1 !== cursor.month ||
        Number(fields.date.slice(8)) !== day
      )
        return [];
      const channel =
        entry.format === "email"
          ? "Email"
          : entry.format === "carousel"
            ? "Carousel"
            : "Reel";
      if (
        respectSearch &&
        needle &&
        ![entry.title, channel, entry.pack_title].some((v) =>
          v.toLowerCase().includes(needle),
        )
      )
        return [];
      return [
        {
          id: entry.calendar_entry_id,
          ideaId: entry.pack_id,
          day,
          channel,
          time: fields.time,
          title: entry.title,
          warning:
            entry.effective_status === "needs_review"
              ? "Needs review"
              : entry.overdue
                ? "Overdue"
                : undefined,
        },
      ];
    });
  };
  const openPost = (entryId: string) => {
    const entry = entries.find((item) => item.calendar_entry_id === entryId);
    if (entry) onOpenEntry(entry);
  };
  const focusPosts = postsForDay(focusDay);
  const weekStartIndex =
    Math.floor(
      Math.max(
        0,
        cells.findIndex((cell) => cell.monthDay === focusDay),
      ) / 7,
    ) * 7;
  const weekCells = cells.slice(weekStartIndex, weekStartIndex + 7);
  const infoId = useId();
  return (
    <section className="atelier-calendar bg-white rounded-[22px] border border-[#E7EAF0] shadow-[0_10px_30px_-22px_rgba(20,32,54,0.45)] overflow-x-auto">
      <div className="flex items-center justify-between flex-wrap gap-4 px-4 sm:px-5 pt-3 pb-2">
        <div className="flex flex-col items-start gap-3">
          <div className="flex items-center gap-2">
            <h2 className="font-editorial text-[22px] font-medium tracking-tight text-[#173354]">
              Content Calendar
            </h2>
            <span className="relative group/calendar-info">
              <button
                type="button"
                aria-label="About the content calendar"
                aria-describedby={infoId}
                className="flex items-center justify-center w-6 h-6 rounded-full text-[#8B93A3] hover:bg-[#EFF3FF] hover:text-[#5070FF] focus-visible:outline-2 focus-visible:outline-[#8DA1FD] cursor-default"
              >
                <Info className="w-4 h-4" strokeWidth={1.75} />
              </button>
              <span
                id={infoId}
                role="tooltip"
                className="absolute left-0 top-full mt-2 z-30 w-64 rounded-xl border border-[#E6E9F0] bg-white p-3 text-[12px] leading-relaxed text-[#667184] shadow-saas-dropdown opacity-0 invisible transition-opacity group-hover/calendar-info:opacity-100 group-hover/calendar-info:visible group-focus-within/calendar-info:opacity-100 group-focus-within/calendar-info:visible"
              >
                Saved backend schedules across emails, carousels, and reels.
                Switch between month, week, and day views, and click an entry to
                inspect its linked content pack.
              </span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              aria-label="Previous month"
              onClick={() => setCursor((current) => shiftMonth(current, -1))}
              className="w-7 h-7 rounded-full text-[#1C2434] hover:bg-[#F4F6FA] flex items-center justify-center cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" strokeWidth={1.75} />
            </button>
            <h3 className="atelier-calendar-month font-editorial text-[22px] font-semibold tracking-tight text-[#1B2433] min-w-[132px] text-center">
              {MONTHS[cursor.month]} {cursor.year}
            </h3>
            <button
              type="button"
              aria-label="Next month"
              onClick={() => setCursor((current) => shiftMonth(current, 1))}
              className="w-7 h-7 rounded-full text-[#1C2434] hover:bg-[#F4F6FA] flex items-center justify-center cursor-pointer"
            >
              <ChevronRight className="w-4 h-4" strokeWidth={1.75} />
            </button>
          </div>
        </div>
        <div className="flex items-center gap-5 pr-1">
          {(["month", "week", "day"] as DeskView[]).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setView(mode)}
              className={`pb-1 text-[13px] capitalize cursor-pointer ${
                view === mode
                  ? "text-[#1B2433] font-semibold border-b-2 border-[#1B2433]"
                  : "text-[#A8B0BE] font-medium hover:text-[#5E6878]"
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>
      <p className="px-5 pb-3 text-xs text-slate-500">
        {timezone} · Saved publishing plan
      </p>
      {view !== "month" && (
        <label className="block px-5 pb-3 text-xs text-slate-500">
          Selected date{" "}
          <input
            type="date"
            aria-label="Calendar selected date"
            className="ml-2 border rounded p-1"
            value={`${cursor.year}-${String(cursor.month + 1).padStart(2, "0")}-${String(focusDay).padStart(2, "0")}`}
            onChange={(e) => {
              if (!e.target.value) return;
              const [year, month, day] = e.target.value.split("-").map(Number);
              setCursor({ year, month: month - 1 });
              setFocusDay(day);
            }}
          />
        </label>
      )}
      {view === "month" && (
        <>
          <div className="grid grid-cols-7 border-t border-[#EEF1F5]">
            {WEEKDAYS.map((day) => (
              <div
                key={day}
                className="px-2.5 py-2 text-[8px] font-medium tracking-[0.16em] uppercase text-[#526C91] text-center bg-[#FAFBFE]"
              >
                {day}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7 border-t border-[#EEF1F5]">
            {cells.map((cell) => {
              const posts = postsForDay(cell.monthDay);
              const preview = calendarDayPreview(posts);
              return (
                <div
                  key={cell.key}
                  className="atelier-calendar-cell min-h-[128px] overflow-hidden border-t border-[#F0F2F6] border-r px-2 pt-2 pb-1.5 [&:nth-child(7n)]:border-r-0"
                >
                  <div className="flex items-start justify-between gap-1 mb-1 px-0.5">
                    <button
                      type="button"
                      onClick={() => {
                        if (cell.monthDay) {
                          setFocusDay(cell.monthDay);
                          setAgendaDay(cell.monthDay);
                        }
                      }}
                      className={`text-[12px] font-medium leading-none ${
                        cell.monthDay ? "cursor-pointer" : "cursor-default"
                      }`}
                    >
                      <span
                        className={
                          cell.inMonth ? "text-[#173354]" : "text-[#9CAEC4]"
                        }
                      >
                        {cell.label}
                      </span>
                    </button>
                  </div>
                  <div className="space-y-1">
                    {preview.visible.map((post) => (
                      <PostCard
                        key={post.id}
                        post={post}
                        onOpen={() => openPost(post.id)}
                      />
                    ))}
                    {preview.more > 0 && (
                      <div className="flex justify-center pt-0.5">
                        <button
                          type="button"
                          aria-label={`Show ${preview.more} more content items for ${MONTHS[cursor.month]} ${cell.monthDay}`}
                          onClick={() => setAgendaDay(cell.monthDay)}
                          className="w-full rounded-full px-3 py-0.5 text-center text-[10px] leading-[14px] font-medium text-[#5070FF] transition-colors hover:bg-[#EFF3FF] focus-visible:outline-2 focus-visible:outline-[#8DA1FD]"
                        >{`${preview.more} more`}</button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex items-center justify-between px-4 py-2.5 border-t border-[#F2F4F7]">
            <span className="flex items-center gap-2 text-[7px] tracking-[0.18em] uppercase text-[#8C9AB0] font-medium">
              <span className="w-6 h-px bg-[#C8A83E]" /> Scroll to explore
            </span>
            <span className="text-[7px] text-right tracking-[0.18em] uppercase text-[#8C9AB0] font-medium">
              Building a stronger
              <br />
              wedding industry
            </span>
          </div>
        </>
      )}
      {view === "week" && (
        <div className="border-t border-[#EEF1F5]">
          <div className="grid grid-cols-7">
            {WEEKDAYS.map((day) => (
              <div
                key={day}
                className="px-2.5 py-2.5 text-[10px] font-medium tracking-[0.16em] uppercase text-[#B0B6C2]"
              >
                {day}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7 border-t border-[#EEF1F5] min-h-[320px]">
            {weekCells.map((cell) => {
              const posts = postsForDay(cell.monthDay);
              const preview = calendarDayPreview(posts);
              const today = new Date();
              const isToday =
                cursor.year === today.getFullYear() &&
                cursor.month === today.getMonth() &&
                cell.monthDay === today.getDate();
              return (
                <div
                  key={cell.key}
                  className="border-r border-[#F0F2F6] last:border-r-0 p-2"
                >
                  <button
                    type="button"
                    onClick={() => {
                      if (cell.monthDay) {
                        setFocusDay(cell.monthDay);
                        setAgendaDay(cell.monthDay);
                      }
                    }}
                    className="mb-2 cursor-pointer"
                  >
                    {isToday ? (
                      <span className="w-6 h-6 rounded-full bg-[#1B2838] text-white inline-flex items-center justify-center text-[12px] font-semibold">
                        {cell.label}
                      </span>
                    ) : (
                      <span
                        className={`text-[13px] font-medium ${cell.inMonth ? "text-[#8E97A6]" : "text-[#D5DAE2]"}`}
                      >
                        {cell.label}
                      </span>
                    )}
                  </button>
                  <div className="space-y-1.5">
                    {preview.visible.map((post) => (
                      <PostCard
                        key={post.id}
                        post={post}
                        onOpen={() => openPost(post.id)}
                      />
                    ))}
                    {preview.more > 0 && (
                      <div className="flex justify-center pt-1.5">
                        <button
                          type="button"
                          aria-label={`Show ${preview.more} more content items for ${MONTHS[cursor.month]} ${cell.monthDay}`}
                          onClick={() => setAgendaDay(cell.monthDay)}
                          className="w-full rounded-full px-3 py-1 text-center text-[10px] font-medium text-[#5070FF] transition-colors hover:bg-[#EFF3FF] focus-visible:outline-2 focus-visible:outline-[#8DA1FD]"
                        >{`${preview.more} more`}</button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
      {view === "day" && (
        <div className="border-t border-[#EEF1F5] px-6 py-6 min-h-[320px]">
          <p className="text-[10px] tracking-[0.18em] uppercase text-[#A8B0BE] font-medium">
            {
              WEEKDAY_FULL[
                (new Date(cursor.year, cursor.month, focusDay).getDay() + 6) % 7
              ]
            }
          </p>
          <h3 className="font-editorial text-[32px] font-medium text-[#1B2433] mt-1">
            {MONTHS[cursor.month]} {focusDay}
          </h3>
          <div className="mt-5 max-w-md space-y-2">
            {focusPosts.length === 0 && (
              <p className="text-[13px] text-[#8E97A6]">
                Nothing scheduled on this day.
              </p>
            )}
            {focusPosts.map((post) => (
              <PostCard
                key={post.id}
                post={post}
                onOpen={() => openPost(post.id)}
                roomy
              />
            ))}
          </div>
        </div>
      )}
      {agendaDay !== null && (
        <CalendarDayModal
          key={`${cursor.year}-${cursor.month}-${agendaDay}`}
          date={{ ...cursor, day: agendaDay }}
          entries={postsForDay(agendaDay, false)}
          onClose={() => setAgendaDay(null)}
          onOpenContent={(post) => {
            setAgendaDay(null);
            openPost(post.id);
          }}
        />
      )}
    </section>
  );
};
const PostCard: React.FC<{
  post: DeskPost;
  onOpen: () => void;
  roomy?: boolean;
}> = ({ post, onOpen, roomy = false }) => {
  const cream = post.channel === "Carousel";
  const channelStyle =
    post.channel === "Email"
      ? "bg-[#F2F1FF] border-[#F2F1FF]"
      : cream
        ? "bg-[#FBF7EF] border-[#FBF7EF]"
        : "bg-[#EFF9FC] border-[#EFF9FC]";
  return (
    <button
      type="button"
      onClick={onOpen}
      className={`flex w-full flex-col overflow-hidden text-left rounded-lg border cursor-pointer transition-shadow hover:shadow-[0_4px_12px_-8px_rgba(20,32,54,0.45)] ${
        roomy ? "h-[88px] px-3 py-2.5" : "h-[72px] px-2.5 py-2"
      } ${channelStyle}`}
    >
      {post.warning && (
        <span className="text-[10px] text-amber-800">{post.warning}</span>
      )}
      <div className="flex w-full shrink-0 items-center justify-between gap-1">
        <span className="flex items-center gap-1 min-w-0">
          <span
            className={`w-[5px] h-[5px] rounded-full shrink-0 ${cream ? "bg-[#C8AA63]" : post.channel === "Reel" ? "bg-[#46B8AB]" : post.channel === "Email" ? "bg-[#7A69EC]" : "bg-[#4C9CFF]"}`}
          />
          <span className="text-[8.5px] font-semibold tracking-[0.12em] text-[#7E8BA0] truncate">
            {post.channel}
          </span>
        </span>
        <span className="text-[8.5px] text-[#A7B0BE] shrink-0">
          {post.time}
        </span>
      </div>
      <p
        className={`w-full shrink-0 font-medium text-[#243044] leading-snug line-clamp-2 ${roomy ? "text-[13px] mt-1.5" : "text-[10.5px] mt-1"}`}
      >
        {post.title}
      </p>
    </button>
  );
};
