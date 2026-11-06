# The screens, decluttered (26 October 2026)

The owner looked at production on 26 Oct and found the screens unpresentable: technical detail everywhere, cards that print
whole documents, a content pack page with a side panel nobody asked for, admin pages where the useful part (intake) is
buried, a knowledge compile with no feedback and no way back, a "not found" on reload, and a "Content Atelier" strip on
every page pushing the content down. The owner's instruction: decide what a user needs to see and remove the rest, screen
by screen. These are the decisions. The 20 October mockup (`frontend/src/mock`, run with `VITE_ATELIER_MODE=mock`) is the
visual reference: white rounded cards, Playfair titles, pill buttons, the four-step stepper, quiet grey text.

## Rules for every screen

- **Never shown to the team:** decision codes and plan item ids (D12, N4, 2.B11, P1, R43...), "under delegation", model or
  prompt names and versions, profile names, job/stage names, run ids, internal statuses in raw form (`moment_extraction`,
  `pending`), passage/word/scene counts, costs (except the administrators' costs card), confidence scores, "the system
  changed", "written by the system", provenance lines ("Set by x on y") except where the page is about who set it.
- **The page header** is the page's own title (Playfair) with one short subtitle line and its main buttons, drawn in the top
  bar beside the bell and the account (`PageHeading`, portal into the shell). No "Content Atelier" strip, no info-tooltips,
  no footer lines ("Monday–Sunday weeks · ...").
- **Cards summarise; dialogs and detail pages hold the full text.** A card is at most: title, status pill, one meta line,
  two or three short lines of substance, and its buttons.
- **Forms that are used occasionally** (upload a transcript, add a fact, record a published piece, import figures) open in
  a dialog from a button; they are not printed on the page.
- **Filters**: a search box and at most three dropdowns in view; anything else behind "More filters". No facet-count clouds.
- **Every button that changes something** says what happened right where it was pressed (a short status line, or the new
  item highlighted), shows a busy state while it runs, and an irreversible or slow one asks first.

## Screen by screen

### Shell
- Top bar: page title + subtitle + page buttons on the left, bell and account on the right. Not sticky.
- Sidebar unchanged (the mockup's), Administration group as is.

### Home
- Greeting ("Good morning" + the person's first name; an organisation account gets no name), the subtitle, Flag idea.
- "This week": angles waiting, briefs waiting, packs to review, packs ready to publish, the next cycle. No spending-limit
  line (an administrator sees limits under Alerts and costs), no "latest cycle" duplicate.

### Weekly Studio (stepper: Content Angle, Content Briefing, Content Packs, Scheduled Content)
- Header: "Weekly Studio", subtitle "18 Oct – 24 Oct, 2026 · Latest week"; buttons: Download review (secondary),
  Previous Concepts →, Flag idea.
- The stepper, search and the offers filter as in the mockup. No "Showing only ..." line, no footer.
- **Angle card:** title, status pill, "date · offer", the content type (WARM/ATTRACT/CONVERT) and the angle in two or three
  lines, "Why it matters" in two lines. Buttons: Review angle; Approve & create brief (waiting) or Open brief / Open pack
  (approved). Removed from the card: the full rationale, evidence, guardrails, "Source moment & research", "Approved ...
  under delegation".
- Removed from the Studio: "Why these ideas" (the strategy panel) and "Cycle details" (moves to Sources → Weekly cycle, for
  administrators). "Held, skipped and other ideas" becomes a quiet "Other ideas this week (n)" list (title + one line +
  its action).
- **Brief card:** title, status pill, "date · offer", the central point, the purpose in one line (WARM · Process or
  framework), the formats in one line. Buttons: Read full brief; Approve & generate pack (waiting) or Open pack.
- **Packs and Scheduled steps:** the pack card below; Scheduled shows "Ready to publish" and "Published" sections only,
  without explanations about the calendar.

### The angle / brief dialog (Content Angle · Content Brief · Content Pack · Schedule tabs, as the mockup)
- Angle tab: title, status ("Approved 25 Oct 2026"), the rationale (type, audience, why it matters, WIA's expertise,
  evidence with call times, guardrails, next step), and "What was said on the call" folded.
- Removed: "Decision: ... (D12)", the account record (calls on record, latest records), "Verify before publishing",
  "Evidence: some points need a look", "The brief · done".
- Brief tab: the brief, as written.

### Content Packs (library) and the pack card
- Header "Content Packs & Deliverable Scripts", subtitle "6 packs"; one state filter. Packs grouped by week (week heading
  with the count), as the mockup groups by month. No "Refresh", no archived-weeks toggle.
- **Pack card:** offer track badge, status pill, title, the central point in two lines, chips "1 Email · 7 Slides ·
  3 Reels", "Open pack →". No "notes to check", no "Made ...".

### The content pack
- Header: "← Content packs", the title, offer badge and status pill; buttons: Copy all, and the one next step (Mark ready
  to publish while in review; Back to review as a quiet link once ready).
- Piece tabs (Email · Carousel · Reel 1 · Reel 2 · Reel 3), one piece shown at a time, laid out as the mockup: the
  piece's heading and Copy; date / send time / recipients in a row; then each part (subjects, preview, body, slides,
  script, caption) with Copy, and Edit on hover. "Mark published" (or "Published 26 Oct") on the piece.
- Removed: the whole right-hand panel (Before publishing, Stronger with permission, Personal lines, Checks to consider,
  Notes from the system, Finish again, Versions), "Details: how this pack was made", "Written by the system...",
  "Approved by the team under delegation...", "Finished from the brief", "What the system changed", "Use the brief's line",
  the top links to the week's plan and the brief (the brief opens from a quiet "View brief" link). The notes stay in the
  week's review document.

### Previous Concepts
- Header with "← Weekly Studio"; only weeks that have concepts, each with its counts ("3 angles · 1 waiting"). No archived
  toggle, no footer.

### Sources (administrators): All documents · Intake · Weekly cycle · Alerts and costs
- **All documents:** header "Sources", subtitle "166 calls included · 28 excluded"; button "Upload a transcript" (dialog).
  Search + Source + Call type + Included; the rest behind "More filters". Rows: title, date, source · call type, client,
  Included/Excluded pill, "Needs a call type" when waiting for a person (with its inline choice). No passages/words, no
  extraction status unless it failed, no exclusion reasons with codes on the row (the reason, without codes, on the
  document page). The extraction-health block moves to the bottom, folded ("Processing health").
- **Intake:** the connectors (Fathom, Slack) with status and Activate; the weekly buckets; recently received. "Processing"
  shows only what is queued or running and what failed in the last 7 days, with plain names ("Scenes from a call",
  "Pack check"), never superseded or cancelled jobs; older failures behind "Show earlier".
- **Weekly cycle:** the cycle panel that used to sit at the bottom of the Studio.
- **Alerts and costs:** as is, plain.

### Moments (administrators)
- Search + Type + Client + Consent in view; speaker, source, call type, topic, dates behind "More filters". A moment card:
  the quote, "speaker · date · client", consent pill, "Read the moment". No "THE SCENE ..." blob, no "Human line" label.

### Knowledge (administrators): Review queue · What the system knows · Versions
- **What the system knows:** the list, grouped, each entry its text and one quiet line (in use from, public or internal);
  provenance folded into History. "Add a fact", "Record a published piece", "Add a figure", "Import figures" are buttons
  that open dialogs.
- **Versions:** "Compile a new version" asks first (what it does), shows "Compiling…" while it runs, then says what
  happened beside the button and scrolls to the new draft. A draft can be **discarded** (new route; a version used by a run
  or approved cannot). Change labels in plain words ("Takes effect when approved", "Needs a benchmark first"). Reloading a
  version's page works (the server treated the dot in the version name as a file).

### Settings (administrators)
- The weekly schedule (day, hour, time zone) in one card; the weekly spending limits as a plain table (purpose, up to).
  Removed: model and prompt tables, the knowledge-base pin line, the duplicate cutoff, "calls each week".

## What was done (26 October 2026)

All of the above is built, on the branch `ui/declutter`, checked screen by screen at 1440 px on a local copy of production's
database (restored from a one-off dump through a temporary proxy, deleted after use), with every button pressed on that copy.
Beyond the list:

- **Confirmations were invisible.** Every write's result ("Saved", "Marked ready", "Compiled…") went only to a screen-reader
  live region. `useWriteFeedback` now also shows it in a pill at the bottom of the screen (`Confirmation`, `shared/a11y.tsx`).
- **Reloading a knowledge version's page said "Not Found":** the frontend server took the dot in the version name for a file
  extension. Only real asset types are files now (`server/app.mjs` `isAsset`), with a test.
- **Server-written sentences** (alerts, waits, job errors, exclusion reasons, knowledge entries) go through `plainMessage`
  (`utils/plainText.ts`): no commands, plan or decision codes, "under delegation" or internal ids. The budget message itself no
  longer names a command ("an administrator can raise it").
- **Knowledge:** `POST /storage/context/versions/{version}/discard` (approver; refused for a version that is active, approved,
  pinned or used by any run); Compile asks first, says "Compiling…", says the result and scrolls to the new draft. The draft the
  owner compiled on production stays until someone presses "Discard draft".
- **Kept on purpose:** a line that blocks "Ready to publish" can still be confirmed as true on the piece ("It is true"); a
  waiting angle or brief keeps its decision, checks and editing tools (folded); the week's pack document downloads from the
  Content Packs step and each week of the library; "Download review" downloads the Word file directly.
- **Removed writes:** the frontend server no longer relays `pieces/{key}/revert`, `weeks/{id}/reassess` or `weeks/{id}/runs`,
  which no screen calls any more.

Production has no OpenRouter key since 26 October (DEPLOYMENT.md): the paid steps wait until one is set again.
