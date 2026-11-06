"""Occurrence dates from evidence only (plan 1.B11).

A document gets a date only when something says when it happened, and the source is recorded beside the date:

provider      the provider's own timestamp (Fathom, Slack)
manual        a person's entry
zoom_listing  Zoom's recording list (an export), matched on topic and duration
calendar      a calendar export (ICS or CSV), matched on title and duration
filename      a date in the file name (Zoom's own `GMT20260312-153000_Recording` form is exact to the second)
content       an explicit date line at the top of the transcript, or a spoken cue that says what today is ("happy
              Tuesday", "today is the 19th") inside the document's week window

Otherwise the document is **explicitly undated** (`occurred_at` null, source `unknown`) and the undated count is
reported. No date is ever derived from the week a document was admitted in: the week is where it was filed, not when
the call happened. A match that is not unique (two meetings with the same topic and length) is left undated rather
than guessed.

The Zoom backfill is the one exception to "a week says nothing": its owner filed each recording into a week folder by
its recording time, so the folder is evidence of occurrence. It is a **window**, not a date: it bounds the day a spoken
weekday or a recording list names (a "Monday" means one day inside it; a topic that recurs every week is unique inside
it), and a document with nothing better is dated to its week (kept in `date_evidence`, `occurred_at` stays null).
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCES = ("provider", "manual", "zoom_listing", "calendar", "filename", "content")
# Which source wins when two disagree: the one a person or machine recorded closest to the event.
AUTHORITY = {s: i for i, s in enumerate(SOURCES)}
EARLIEST = date(2020, 1, 1)
DURATION_TOLERANCE_MINUTES = 3

ZOOM_GMT = re.compile(r"GMT(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})")
ISO_DATE = re.compile(r"(?<!\d)(20\d{2})[-_.](\d{1,2})[-_.](\d{1,2})(?!\d)")
COMPACT_DATE = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)")
US_DATE = re.compile(r"(?<!\d)(\d{1,2})[-_.](\d{1,2})[-_.](20\d{2})(?!\d)")
MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
NAMED_MONTH = re.compile(r"(?<![a-z])(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?[ _-]+(\d{1,2})(?:st|nd|rd|th)?,?[ _-]+(20\d{2})", re.I)
DAY_FIRST = re.compile(r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?[ _-]+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?[ _-]+(20\d{2})", re.I)
HEADER_DATE = re.compile(r"^(?:date|recorded(?: on)?|meeting date)\s*[:\-]\s*(.+)$", re.I | re.M)

FOLDER_WEEK_ONE = date(2026, 6, 1)
"""Week 1 of the Zoom backfill's folders: 1 to 7 June 2026, each week filed by recording time in Asia/Kolkata
(fathom-zoom-reconciliation-2026-10-14.md: "Weekly assignment uses recording occurrence time in Asia/Kolkata, June 1–7
as Week 1")."""
FOLDER_TIMEZONE = ZoneInfo("Asia/Kolkata")
# WIA works in Chicago: "today is Monday" is Monday there. The IST week is Sunday 13:30 to Sunday 13:30 in Chicago.
SPEECH_TIMEZONE = ZoneInfo("America/Chicago")
# A greeting is said as a call opens; later, "Happy Monday ..." is mostly someone drafting a post or quoting a caption.
GREETING_MINUTES = 10
GREETING_LINES = 30  # the same bound for a transcript without timestamps


@dataclass(frozen=True)
class Window:
    """The week a source folder names: the call happened in [start, end)."""
    start: datetime
    end: datetime
    basis: str

    def contains(self, when: datetime) -> bool:
        return self.start <= when < self.end

    def near(self, when: datetime) -> bool:
        """Inside, allowing half a day either side: a date kept as noon on its day still belongs to an edge day."""
        return self.start - timedelta(hours=12) <= when < self.end + timedelta(hours=12)

    def days(self) -> list[date]:
        """The Chicago days the window touches (eight: a partial Sunday at each end)."""
        first, last = self.start.astimezone(SPEECH_TIMEZONE).date(), (self.end - timedelta(microseconds=1)).astimezone(SPEECH_TIMEZONE).date()
        return [first + timedelta(days=i) for i in range((last - first).days + 1)]

    def record(self) -> dict:
        return {"start": self.start.isoformat(), "end": self.end.isoformat(), "basis": self.basis}


@dataclass(frozen=True)
class Result:
    occurred_at: datetime | None
    source: str  # one of SOURCES, or 'unknown'
    detail: str = ""
    conflicts: tuple[str, ...] = ()
    window: Window | None = None

    def evidence(self) -> dict | None:
        """What `transcripts.date_evidence` keeps; None when there is nothing to say."""
        if not (self.detail or self.conflicts or self.window):
            return None
        return {"detail": self.detail, "conflicts": list(self.conflicts), "window": self.window.record() if self.window else None}


@dataclass(frozen=True)
class Event:
    """One dated meeting from a listing or a calendar."""
    source: str  # zoom_listing | calendar
    title: str
    start: datetime
    minutes: float | None
    origin: str  # the file and row it came from, for the record


def _plausible(value: date, today: date) -> bool:
    return EARLIEST <= value <= today + timedelta(days=1)


def _day(year, month, day) -> date | None:
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def from_filename(text: str, today: date | None = None) -> tuple[datetime | None, str]:
    """A date written in a file name or title. Zoom's GMT stamp gives the exact instant; a bare date gives noon UTC
    on that day, which keeps the calendar day right in every time zone from Hawaii to India."""
    today = today or date.today()
    stamp = ZOOM_GMT.search(text or "")
    if stamp:
        year, month, day, hour, minute, second = (int(x) for x in stamp.groups())
        try:
            value = datetime(year, month, day, hour, minute, second, tzinfo=UTC)
        except ValueError:
            value = None
        if value and _plausible(value.date(), today):
            return value, f"Zoom recording stamp {stamp.group(0)} (GMT)"
    for pattern, order in ((ISO_DATE, "ymd"), (COMPACT_DATE, "ymd"), (US_DATE, "mdy")):
        for match in pattern.finditer(text or ""):
            a, b, c = match.groups()
            found = _day(a, b, c) if order == "ymd" else _day(c, a, b)
            if found and _plausible(found, today):
                return datetime(found.year, found.month, found.day, 12, tzinfo=UTC), f"date in the name: {match.group(0)}"
    named = NAMED_MONTH.search(text or "")
    if named:
        found = _day(named.group(3), MONTHS[named.group(1).lower()[:3]], named.group(2))
        if found and _plausible(found, today):
            return datetime(found.year, found.month, found.day, 12, tzinfo=UTC), f"date in the name: {named.group(0)}"
    first = DAY_FIRST.search(text or "")
    if first:
        found = _day(first.group(3), MONTHS[first.group(2).lower()[:3]], first.group(1))
        if found and _plausible(found, today):
            return datetime(found.year, found.month, found.day, 12, tzinfo=UTC), f"date in the name: {first.group(0)}"
    return None, ""


def from_content(original_text: str, today: date | None = None) -> tuple[datetime | None, str]:
    """An explicit `Date:` / `Recorded on:` line in the first lines of the transcript."""
    head = "\n".join((original_text or "").splitlines()[:12])
    match = HEADER_DATE.search(head)
    if not match:
        return None, ""
    value, note = from_filename(match.group(1), today)
    return (value, f"header line: {match.group(0).strip()}") if value else (None, "")


def window_of(document: dict) -> Window | None:
    """The week folder a Zoom backfill document was filed in, as a window; None for any other document (a loose file's
    week index is 0, and Fathom and Slack carry their own timestamps)."""
    week = (document.get("source_metadata") or {}).get("week_index")
    if document.get("source_type") != "zoom" or not isinstance(week, int) or isinstance(week, bool) or week < 1:
        return None
    first = FOLDER_WEEK_ONE + timedelta(days=7 * (week - 1))
    if document.get("week_id") and document["week_id"] != f"week_{first.isoformat()}":
        return None  # admitted on another calendar than the backfill's folders: its number bounds nothing
    start = datetime(first.year, first.month, first.day, tzinfo=FOLDER_TIMEZONE)
    last = first + timedelta(days=6)
    return Window(start, start + timedelta(days=7), f"week folder {week} ({first.isoformat()} to {last.isoformat()}, Asia/Kolkata)")


# ---- spoken cues ------------------------------------------------------------------------------------------------
# Only words that say what TODAY is count: most weekdays in a call are about other days ("I'll send it Friday", "on Monday
# we launched", "oh yeah, it's Wednesday" about a meeting on the calendar), so a bare "it's Friday" is not a cue.

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_WD = "(" + "|".join(WEEKDAYS) + ")"
_MONTH = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
_TODAY_IS = r"\btoday(?:\s+is|'s|’s|\s+it'?s|\s+it\s+is)\s+"
GREETING = re.compile(r"\bhappy\s+" + _WD + r"\b(?!'s|’s)", re.I)
# (pattern, what it names, days from the day it names back to today)
TODAY_CUES = (
    (re.compile(_TODAY_IS + r"(?:a\s+)?" + _WD + r"\b(?!'s|’s)", re.I), "weekday", 0),
    (re.compile(r"\bit(?:'s|’s|\s+is)\s+" + _WD + r",?\s+today\b", re.I), "weekday", 0),
    (re.compile(_TODAY_IS + r"the\s+(\d{1,2})(?:st|nd|rd|th)\b", re.I), "ordinal", 0),
    (re.compile(_TODAY_IS + _MONTH + r"\s+(\d{1,2})(?:st|nd|rd|th)?\b", re.I), "month_day", 0),
    (re.compile(r"\bit(?:'s|’s|\s+is)\s+" + _MONTH + r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+today\b", re.I), "month_day", 0),
    # Read out as a heading: "Today, Monday, July 20th."
    (re.compile(r"\btoday,\s+" + _WD + r"\b(?!'s|’s)", re.I), "weekday", 0),
    (re.compile(r"\btoday,\s+(?:" + _WD[1:-1] + r"),?\s+" + _MONTH + r"\s+(\d{1,2})(?:st|nd|rd|th)?\b", re.I), "month_day", 0),
    (re.compile(r"\btomorrow(?:\s+is|'s|’s)\s+" + _WD + r"\b(?!'s|’s)", re.I), "weekday", -1),
    (re.compile(r"\byesterday\s+was\s+" + _WD + r"\b(?!'s|’s)", re.I), "weekday", 1),
)
# Words before a cue that make it hypothetical, reported or quoted ("if today is Friday", "saying, happy Monday").
NOT_SAID_AS_TODAY = re.compile(r"\b(if|say|says|saying|said|imagine|pretend|suppose|assume|whether|unless|until|when|caption|"
                               r"post|posted|wrote|write|message|text|email)\b", re.I)
# A cue followed by one of these names an event, not today ("today is Monday call day").
EVENT_WORD = re.compile(r"^\W*(call|meeting|session|class|workshop|deadline|post|office hours)\b", re.I)
CUE_TIME = re.compile(r"^\s*\[?(\d{1,2}):(\d{2}):(\d{2})(?:[.,]\d+)?\]?\s*(?:-->|$)")
SENTENCE = re.compile(r"[^.!?]+[.!?]*")


def _days_named(window: Window, kind: str, groups: tuple, offset: int) -> list[date]:
    """The Chicago days inside the window on which the cue would be true of today."""
    found = []
    for day in window.days():
        named = day - timedelta(days=offset)  # "tomorrow is Friday" (offset -1): the named day is today + 1
        if kind == "weekday" and named.weekday() == WEEKDAYS.index(groups[0].lower()):
            found.append(day)
        elif kind == "ordinal" and named.day == int(groups[0]):
            found.append(day)
        elif kind == "month_day" and (named.month, named.day) == (MONTHS[groups[0].lower()[:3]], int(groups[1])):
            found.append(day)
    return found


def from_speech(original_text: str, window: Window | None) -> tuple[datetime | None, str]:
    """A day from what someone says today is, bounded by the document's week window. Returns noon on that Chicago day
    (in UTC) and a detail that quotes the cue; (None, "") when nothing is said; (None, "conflicting spoken cues: ...")
    when cues disagree or name a day outside the window, so the caller can record it. A cue that fits two days of the
    window (a Sunday: the IST week touches two Chicago Sundays) is not used. Precision over coverage."""
    if window is None or not original_text:
        return None, ""
    found: list[tuple[date | None, str]] = []  # (day, quoted line); None = names a day outside the window
    elapsed, spoken = None, 0
    for line in original_text.splitlines():
        stamp = CUE_TIME.match(line)
        if stamp:
            hours, minutes, seconds = (int(x) for x in stamp.groups())
            elapsed = hours * 60 + minutes + seconds / 60
            continue
        if not line.strip() or line.strip().upper() == "WEBVTT":
            continue
        spoken += 1
        opening = elapsed < GREETING_MINUTES if elapsed is not None else spoken <= GREETING_LINES
        for sentence in SENTENCE.findall(line):
            cues = [(m, "weekday", (m.group(1),), 0) for m in GREETING.finditer(sentence)] if opening else []
            if not sentence.rstrip().endswith("?"):  # "today is the 19th?" asks; the answer says ("happy Monday, how are you?" greets)
                cues += [(m, kind, m.groups(), offset) for pattern, kind, offset in TODAY_CUES for m in pattern.finditer(sentence)]
            for match, kind, groups, offset in cues:
                if NOT_SAID_AS_TODAY.search(sentence[:match.start()]) or EVENT_WORD.match(sentence[match.end():]):
                    continue
                days = _days_named(window, kind, groups, offset)
                quoted = line.strip()[:160]
                if len(days) == 1:
                    found.append((days[0], quoted))
                elif not days:
                    found.append((None, quoted))
    if not found:
        return None, ""
    named = {day for day, _ in found}
    if len(named) > 1 or None in named:
        parts = [f'{day.isoformat() if day else "outside " + window.basis} from "{quoted}"' for day, quoted in found]
        return None, "conflicting spoken cues: " + "; ".join(dict.fromkeys(parts))
    day, quoted = found[0]
    value = datetime(day.year, day.month, day.day, 12, tzinfo=SPEECH_TIMEZONE).astimezone(UTC)
    agree = f"; {len(found)} cues agree" if len(found) > 1 else ""
    return value, f'spoken cue "{quoted}" names {day.strftime("%A")} {day.isoformat()} in {window.basis}{agree}'


def document_minutes(document: dict) -> float | None:
    """How long the call ran, from its timestamps; None when none are timed."""
    marks = [p.get("end_ms") if p.get("end_ms") is not None else p.get("start_ms") for p in document["passage_map"]]
    marks = [m for m in marks if m is not None]
    return max(marks) / 60000 if marks else None


def _norm_title(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def matches(document: dict, events: list[Event]) -> list[Event]:
    """Events with the same topic whose length fits the call's (when both have one)."""
    title = _norm_title(re.sub(r"\.(vtt|webvtt|txt|json)$", "", document.get("title") or "", flags=re.I))
    # A file title often carries the recorder's decoration: "Topic's transcript (3)" or "Topic transcript".
    title = re.sub(r"( s)? transcript( \d+)?$", "", title).strip()
    minutes = document_minutes(document)
    found = []
    for event in events:
        if _norm_title(event.title) != title or not title:
            continue
        if minutes is not None and event.minutes is not None and abs(event.minutes - minutes) > max(
                DURATION_TOLERANCE_MINUTES, event.minutes * 0.1):
            continue
        found.append(event)
    return found


def _in_window(window: Window | None, events) -> list[Event]:
    return [e for e in events if window is None or window.contains(e.start)]


def exclusive(documents: list[dict], events: list[Event]) -> tuple[list[Event], list[Event]]:
    """(events that fit at most one document, events that fit several). One meeting is one recording: an event whose topic
    and length fit several documents dates none of them (the real backfill had six "Check-in with Gisselle" calls of 33 to 37
    minutes, and one 35-minute calendar entry would have dated all six).

    A document filed in a week folder can only be the recording of an event inside that week, so it counts as a fit only
    for those: "Whitney Hodges's Personal Meeting Room" recurs 14 times in Zoom's list and fits ~40 documents across the
    corpus, yet an event that is the only one of its week, with one document of that topic in the week, fits exactly one
    document and is kept. The guarantee holds within the window (two such documents in the week: the event dates neither),
    and a document with no window still competes for every event of its topic."""
    windows = [window_of(d) for d in documents]
    fits = [sum(1 for d, w in zip(documents, windows) if _in_window(w, [event]) and matches(d, [event])) for event in events]
    return [e for e, n in zip(events, fits) if n <= 1], [e for e, n in zip(events, fits) if n > 1]


def resolve(document: dict, events: list[Event] = (), *, today: date | None = None, names: tuple[str, ...] = ()) -> Result:
    """The best-supported date for a document, or 'unknown'. `names` are further names the file went by (its path).
    A Zoom backfill document's week folder restricts the listing and calendar to events inside it, bounds its spoken cues,
    and is kept on the result: with no day evidence it is dated to that week (still `unknown`, `occurred_at` null)."""
    today = today or date.today()
    window = window_of(document)
    candidates: list[tuple[str, datetime, str]] = []
    if document.get("occurred_at") and document.get("occurred_at_source") in {"provider", "manual"}:
        return Result(document["occurred_at"], document["occurred_at_source"], "recorded with the document", window=window)
    pool = _in_window(window, [e for e in events if e.source == "zoom_listing"])
    hits = matches(document, pool)
    if len(hits) == 1:
        candidates.append(("zoom_listing", hits[0].start, f"Zoom recording list: {hits[0].origin}"))
    cal = matches(document, _in_window(window, [e for e in events if e.source == "calendar"]))
    if len(cal) == 1:
        candidates.append(("calendar", cal[0].start, f"calendar: {cal[0].origin}"))
    # A date matched earlier from a listing or a calendar is evidence the document keeps: normalising again (which reads
    # no listing) must not forget it, and only a new unique match from the same kind of evidence replaces it.
    stored = document.get("occurred_at_source")
    if document.get("occurred_at") and stored in {"zoom_listing", "calendar"} and not any(c[0] == stored for c in candidates):
        kept = (document.get("date_evidence") or {}).get("detail")  # the row it matched, recorded when it matched
        candidates.append((stored, document["occurred_at"], kept or f"matched earlier from the {stored.replace('_', ' ')}"))
    for text in (document.get("title") or "", *names):
        value, detail = from_filename(text, today)
        if value:
            candidates.append(("filename", value, detail))
            break
    value, detail = from_content(document.get("original_text") or "", today)
    if value:
        candidates.append(("content", value, detail))
    noted: list[str] = []
    value, detail = from_speech(document.get("original_text") or "", window)
    if value:
        candidates.append(("content", value, detail))
    elif detail:
        noted.append(detail)  # cues that disagree date nothing, but the disagreement is kept
    if not candidates:
        ambiguous = len(hits) > 1 or len(cal) > 1
        detail = "several meetings fit the topic and length; not guessed" if ambiguous else "no evidence dates this document"
        if window:
            detail += f"; dated to {window.basis}"
        return Result(None, "unknown", detail, tuple(noted), window)
    candidates.sort(key=lambda c: AUTHORITY[c[0]])
    source, when, detail = candidates[0]
    conflicts = [f"{s} says {w.date().isoformat()}" for s, w, _ in candidates[1:] if abs((w - when).total_seconds()) > 86400]
    if window and not window.near(when):
        conflicts.append(f"{when.date().isoformat()} is outside {window.basis}")
    return Result(when, source, detail, tuple(conflicts + noted), window)


# ---- evidence files ---------------------------------------------------------------------------------------------

def _parse_time(text: str, tz: ZoneInfo) -> datetime | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        value = None
        for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%b %d, %Y %I:%M:%S %p"):
            try:
                value = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=tz)


def _column(row: dict, *names: str):
    lowered = {k.strip().lower(): v for k, v in row.items() if k}
    for name in names:
        if name in lowered and lowered[name] not in (None, ""):
            return lowered[name]
    return None


def _minutes(value) -> float | None:
    """Minutes from `47`, `47.5` or `00:47:12` (hours:minutes:seconds)."""
    if value in (None, ""):
        return None
    try:
        parts = [float(x) for x in str(value).split(":")]
    except ValueError:
        return None
    return parts[0] if len(parts) == 1 else sum(x * m for x, m in zip(parts, (60, 1, 1 / 60)))


def read_zoom_listing(path, timezone: str) -> list[Event]:
    """Zoom's recording or meeting list exported as CSV: topic, start time, duration in minutes. `timezone` is the Zoom
    account's (the export shows local times without a zone); it is required because guessing it would move days."""
    tz = ZoneInfo(timezone)
    events = []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        for number, row in enumerate(csv.DictReader(handle), 2):
            topic = _column(row, "topic", "meeting topic", "title", "recording topic")
            start = _parse_time(_column(row, "start time", "start", "recording start", "meeting start time") or "", tz)
            if not topic or not start:
                continue
            length = _minutes(_column(row, "duration (minutes)", "duration", "total minutes", "meeting duration"))
            events.append(Event("zoom_listing", topic, start, length, f"{Path(path).name} row {number}"))
    return events


def read_calendar(path, timezone: str = "UTC") -> list[Event]:
    """A calendar export: ICS (VEVENT SUMMARY, DTSTART, DTEND) or CSV with subject/title and start columns."""
    path = Path(path)
    if path.suffix.lower() != ".ics":
        events = []
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for number, row in enumerate(csv.DictReader(handle), 2):
                title = _column(row, "subject", "title", "summary", "event")
                start = _parse_time(_column(row, "start", "start time", "start date") or "", ZoneInfo(timezone))
                end = _parse_time(_column(row, "end", "end time", "end date") or "", ZoneInfo(timezone))
                if title and start:
                    events.append(Event("calendar", title, start, (end - start).total_seconds() / 60 if end else None,
                                        f"{path.name} row {number}"))
        return events
    lines = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    events, current = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT" and current is not None:
            start = _ics_time(current.get("DTSTART"), timezone)
            end = _ics_time(current.get("DTEND"), timezone)
            if current.get("SUMMARY") and start:
                events.append(Event("calendar", current["SUMMARY"].replace("\\,", ","), start,
                                    (end - start).total_seconds() / 60 if end else None, f"{path.name} {current.get('UID', '')}".strip()))
            current = None
        elif current is not None and ":" in line:
            name, value = line.split(":", 1)
            key = name.split(";")[0]
            current[key] = (name, value) if key in ("DTSTART", "DTEND") else value
    return events


def _ics_time(field, default_tz: str) -> datetime | None:
    if not field:
        return None
    name, value = field if isinstance(field, tuple) else ("", field)
    tzid = re.search(r"TZID=([^;:]+)", name)
    zone = ZoneInfo(tzid.group(1)) if tzid else ZoneInfo(default_tz)
    value = value.strip()
    try:
        if value.endswith("Z"):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        if "T" in value:
            return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=zone)
        return datetime.strptime(value, "%Y%m%d").replace(hour=12, tzinfo=UTC)
    except ValueError:
        return None


def apply(conn, transcript_id: str, result: Result) -> bool:
    """Record a result on the document and its chunks, with what supports it (`date_evidence`). A person's date is never
    replaced by evidence."""
    from psycopg.types.json import Jsonb
    row = conn.execute("SELECT occurred_at_source FROM transcripts WHERE transcript_id=%s FOR UPDATE", (transcript_id,)).fetchone()
    if row is None:
        raise LookupError("Document not found")
    if row["occurred_at_source"] == "manual" and result.source != "manual":
        return False
    evidence = result.evidence()
    conn.execute("UPDATE transcripts SET occurred_at=%s,occurred_at_source=%s,date_evidence=%s WHERE transcript_id=%s",
                 (result.occurred_at, result.source, Jsonb(evidence) if evidence is not None else None, transcript_id))
    conn.execute("UPDATE transcript_chunks SET occurred_at=%s WHERE transcript_id=%s", (result.occurred_at, transcript_id))
    return True


def report(conn) -> dict:
    """How many documents are dated and by what, how many are explicitly undated or not yet looked at, and how many of
    the undated are dated to the week their folder names."""
    rows = conn.execute("""SELECT coalesce(occurred_at_source,'not_looked_at') AS source, count(*) n FROM transcripts
        WHERE included GROUP BY 1 ORDER BY 1""").fetchall()
    counts = {r["source"]: r["n"] for r in rows}
    undated = counts.get("unknown", 0) + counts.get("not_looked_at", 0)
    to_week = conn.execute("""SELECT count(*) n FROM transcripts WHERE included AND occurred_at IS NULL
        AND jsonb_typeof(date_evidence->'window')='object'""").fetchone()["n"]
    return {"by_source": counts, "undated": undated, "unknown": counts.get("unknown", 0),
            "not_looked_at": counts.get("not_looked_at", 0), "dated": sum(counts.values()) - undated, "dated_to_week": to_week}
