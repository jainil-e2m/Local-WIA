# MVP review changes

Every change made to `mvp/index.html` for the client MVP reviews, one section per version. Each version is reviewed with the client before the next one starts.

`mvp/index.html` started as a byte-identical copy of `frontend/exports/client-portfolio.html` (sha256 `0bd862f5…d0f5`, copied 2026-11-02). The changes below exist only in `mvp/index.html`, not in the React source. Reapply them by hand after any re-export.

---

## MVP v1 (2026-11-02)

### Renamed: Action Register → Action Hub

- Every "Action Register" / "Action register" in the page now reads "Action Hub". That's 23 places:
  - the two sidebar entries ("Action Hub" and "Action Hub v2 · Teams")
  - the page heading, the browser tab title ("Action Hub · WIA Client Knowledge"), and the action window's "Action Hub · <client>" label
  - the "Open in Action Hub" buttons, and the toasts, hints, source labels and assistant answers that mention it
- The URLs are unchanged (`#actions`, `#actions-v3`). The original page's "Register" tab keeps its name.
- Headings in this log that say "Action Register" describe the same pages before the rename.

### Ping on Slack (Action Hub v2 · Teams)

- **Footer button.** An open action in **Pending (team)** or **Pending (client)** now has a "Ping on Slack" button (with the Slack logo) next to Change status. It isn't shown on Pending (you) or Completed items. Internal tasks get it too.
- **Where it posts:**
  - client actions go to that client's channel, for example `#client-bloom-manor` and `#client-harbor-house`
  - Internal tasks go to `#meta-accelerator` or `#google-accelerator`
  - These are all internal WIA channels, so there's no shared-channel warning.
- **What it records:** a line in History, depending on the stage:
  - **Team:** "Pinged #client-bloom-manor on Slack by Whitney: @Jacqueline, is this on track?"
  - **Client:** "…waiting on Elise Bennett; @Danielle (Account owner · LeadLock) to follow up." It names the first person on the client's ClickUp account team.
- **Toast top right:** "Pinged #client-bloom-manor on Slack." It shows above the open action window for about 3 seconds. Other toasts keep their usual position.
- **Sent timer:** after a ping the button reads "Sent 0 mins ago". It counts up live ("1 min ago" … "2 hrs ago" … "3 days ago") and is saved on the action, so it survives closing the window or reloading.
- **2-minute cooldown:** for 2 minutes after a ping the button is dimmed and does nothing.
  - Hovering it shows the countdown, for example "You can ping again in 1:53".
  - After that, hovering shows "Ping #client-… again", and clicking pings again and restarts the timer.
  - Before the first ping, hovering shows "Post a reminder in #client-…".
- **Board cards:** once an item has been pinged, a small Slack logo appears in the bottom-right corner, just left of the priority tag (for example the Slack logo, then High). Hovering the card adds "Slack ping sent N mins ago" to the card tooltip, worked out at the moment you hover.
- **Preview only:** nothing is actually posted to Slack. Real sending needs a backend, plus the `chat:write` scope on the WIA AI BOT Slack app.

### Client record tabs reordered

- The tab row now reads: Now · Profile · **Commitments · Meetings · History · Handover brief** · Health (Soon) · Support · Invoices & terms (Soon) · Accounts & sources. Before, it was History, Handover brief, Commitments, Meetings.
- Each tab's URL (`#clients/<id>/commitments` and so on) and its content are unchanged.

### Client record header made compact

- **Cover:** it's sized to its content instead of a fixed minimum height, with less padding (24px top and 22px bottom, where it was 42px and 34px).
  - The gap above the Active / Elevate chips drops from 12px to 10px, and the gap above the account-owner row drops from 24px to 14px.
  - At 1920px the cover goes from 294px to 238px tall. The "Needs attention" card still fits inside it.
- **Record strip** (Client since · Earliest evidence · Processed through · sources):
  - It drops its fixed 82px minimum height and has less padding, going from 82px to 60px tall.
  - The gap below it goes from 23px to 14px.
- **Tabs:** the gap below the tab row goes from 26px to 16px, and the gap above the strip from 22px to 16px.
- **Result:** Next meeting, Last meeting and every card below them sit 103px higher, starting at 465px instead of 568px on a 1920×1000 screen.
- **Phones:** the cover changes apply from 701px wide and up, so the stacked phone header is unchanged apart from the smaller strip and tab gaps.

### Client record "Now" tab: even 2×2 grid + full-width card

- **New layout:** the Now tab is laid out as one even grid.
  - **Row 1:** Next meeting and Last meeting.
  - **Row 2:** Action items and Client sentiment.
  - **Below:** Communication this week across the full width.
  - Both columns are always the same width, and the gaps between cards are all 22px. At 1920px wide each card is 766px.
- **What was uneven before:**
  - Action items and Client sentiment were split about 60/40 (1.55fr / 1fr).
  - The second row was aligned to the top, so its cards ended at different heights.
  - Next meeting had an extra 20px top margin left over from an older rule, so it sat lower than Last meeting. It also had smaller corners (13px instead of 20px).
- **Now:**
  - Cards in the same row share a height, and their footer lines ("Open in Meetings", "Health") sit at the bottom.
  - Next meeting lines up with Last meeting and uses the same 20px corners. It keeps its tinted background.
- **Narrow Action items card:** when the card is narrower than 620px (for example a 1280px window), each action row reflows. The title and client line get the full width, and the due date, status and source tag sit on a second line. At wider sizes the row is unchanged, all on one line.
- **900px and below:** all five cards stack in one column at the same width.

### Client portfolio: card menu and archiving

- **Card ⋯ menu** now has two items:
  - **Open client record:** unchanged.
  - **Mark as archived** (in red). On an archived card this item reads **Restore from archive**.
  - Removed: "Open actions", "Prepare for <date> call" (Call Preparation is Coming soon) and "Copy Slack channel".
- **Archiving** moves the client out of My clients and All clients into a new **Archived** tab next to them, for example "All clients 5 · Archived 1".
  - Archived cards show a greyed-out logo.
  - A toast confirms ("Bloom Manor archived. Find it under Archived.").
  - Restoring puts the client back.
  - The Archived tab says "No archived clients" when it's empty.
- **Pin to top** is a third menu item, between the other two, with a pin icon. It reads **Unpin** on a pinned card.
  - Pinned clients sort first in My clients and All clients, in both Card and List view. The most recently pinned comes first, and everyone else keeps the usual order (most overdue first, then A–Z).
  - Pinned cards show a small pin badge in the top-left of the logo, and List view adds a pin after the client's name.
  - A toast confirms each change ("Everly Films pinned to the top.").
  - Archived cards don't offer Pin. A pinned client that's archived and later restored comes back pinned.
- **Saved in this browser only.** Pins and archived clients are remembered in this browser's local storage. Other people and other browsers don't see them, and clearing site data resets both.
- **Portfolio page only.** Archiving doesn't hide the client anywhere else. Its actions still show in the Action Hub, and its record still opens.

### List view: one line per row

- The Action Hub's List view shows only the main line in each column:
  - **Action item:** the title
  - **Client:** the name
  - **Assigned to:** the person
  - **Due date:** the date
- The grey sublines are hidden: the description under the title, the service or "Internal" under the client, the role (for example "Admin · founder") under the person, the "(1 day late)" / "(Today)" under the date, and the "Deadline change pending" flag.
- Board cards and the action window are unchanged.

### Original Action Hub (v1) removed; v2 is now the only Action Hub

- The original Action Hub page (`#actions`, with its Register / Needs review / Internal tabs and grouped list) is removed. Its sidebar entry is gone too, along with the open-count badge.
- The remaining sidebar entry is just **"Action Hub"**:
  - It uses the v1 page's checklist icon.
  - The "v2 · Teams" tag is gone.
  - Its tooltip and screen-reader label no longer say "v2 (account teams)".
- Every way into the old page now opens this one (`#actions-v3`):
  - an old `#actions` or `#actions/…` link or bookmark (the URL is rewritten)
  - the "Open Action Hub" buttons (relabelled from "Open action register")
  - "Open in Action Hub"
  - the notifications drawer's "Open the Action Hub" button
  - the assistant's "Open the Action Hub" links
- See the earlier "Action Hub vs v2 · Teams" comparison for what the v1 page had that v2 doesn't, such as snooze, the owner and status filters, grouping, and bulk Slack.

### Agentation review toolbar removed (for the first deploy, then restored 2026-11-03)

- The floating annotation toolbar used for collecting page feedback during these reviews is gone from the deployed page. Feedback rounds after deploy need the local export, `frontend/exports/client-portfolio.html`, which still has it.

### Add action: Type field removed

- The "Type" dropdown (Admin, Copy, … with "· needs verification" on some types) is gone from the "Add an action" window. Every Action Hub page uses this same window.
- **Priority** now sits on its own in that row.
- New actions are saved with type **Admin**, which was the old default, so they close at Done and need no separate verification check.

### Pending (team) asks who should own it

Moving an item into Pending (team) now always asks which team member should own it. This happens in both places an item can be moved there:

- **Change status menu** in the action window. "Pending (team) ›" opens the member list inside the same menu, with a "‹ Pending (team): who should own it?" line to go back.
- **Dragging a card** onto the Team pending column, or onto the Pending (team) KPI when a KPI filter is on. A small "Who should own it?" window opens.

How the list works:

- **Order:** people related to the item come first. For a client action that's "On this client's account team", from the client's team in ClickUp, with their role (for example Jacqueline · Account owner, Carmen · Ads manager). For an Internal task it's "On this accelerator". Everyone else follows under "Other team members".
- **Leaves you out:** you're never in the list, because assigning to yourself is Pending (you).
- **Shows the current owner:** they're highlighted and marked "current owner".
- **What a pick does:**
  - The chosen person becomes the owner and the item moves to the WIA side.
  - Their acknowledgement resets ("New owner must acknowledge"), and a completed item is reopened.
  - The move is written to History ("Moved to Pending (team) by Whitney; assigned to Carmen. New owner must acknowledge.") and confirmed with a toast.
- **Cancelling:** closing the window or clicking outside the menu leaves the item where it was.
- **Owner field:** it still works on its own for reassigning without changing stage.

### Sidebar: Overview, Call Preparation, Health & Sentiment, Client 360 and Invoices & Contracts moved to "Coming soon"

- **Live tabs hidden.** The working sidebar entries for these sections are no longer rendered. That covers Overview, both Call preparation entries, all three Health & sentiment entries, Client 360, and Invoices & contracts.
- **New "COMING SOON" section** sits between "THE CLIENT DESK" and "THE FOUNDATION". It lists the five sections with their usual icons and a "Soon" badge. The items are plain `div`s with `aria-disabled="true"` and no click handler, so clicking them does nothing.
- **Client portfolio is now the landing page.** It replaces Overview as the page the app opens on, and as the fallback for any unknown or blocked URL.

### Action register (revised layout) removed

- The "Action register · Revised" sidebar entry and its page (`#actions-v2`) are gone from the file entirely, not just hidden.
- The sidebar now has two Action register entries: the original "Action register" and "Action register v2 · Teams".
- Anything that used to open the revised page now opens "v2 · Teams" (`#actions-v3`) instead:
  - an old `#actions-v2` link or bookmark (the URL is rewritten)
  - the "Open in Action Register" buttons
  - the date-change requests in the notifications drawer

### Client portfolio record: Health and Invoices & terms tabs marked "Soon"

- Each client record's **Health** and **Invoices & terms** tabs now show a "Soon" badge and are disabled `<button>`s, so they can't be clicked.
- **Invoices & terms is now shown to every viewer** as a disabled "Soon" tab. Before, it was a working tab that only finance admins could see.

### No route into those sections

A guard in the hash router (`cd`) blocks these views, whether opened by URL, sidebar, search, notifications or in-page buttons:

- **Blocked views:** `#dashboard` (Overview), `#calls`, `#calls-v2`, `#health`, `#health-v2`, `#health-v3`, `#assistant`, `#money`, `#money-v2`, plus any `#clients/<id>/health` or `#clients/<id>/money`.
- **Behaviour:**
  - The URL goes back to the last allowed page and the view stays where it was, without scrolling.
  - A "Coming soon. This section isn't part of this preview yet." notice shows for 3 seconds.
  - Opening a blocked URL directly lands on Client portfolio.
- **In-page buttons this affects:**
  - Client record "Now" tab: "Prepare for the call", "View brief", and "Health" on the Client sentiment card.

### Action Register header and KPI cards

These changes were made to both the "Revised" (`#actions-v2`) and "v2 · Teams" (`#actions-v3`) Action register pages. The Revised page has since been removed (see "Action register (revised layout) removed"), so they now show only on "v2 · Teams".

- **"Client intelligence" eyebrow removed.** The "Action Register" title moves up into its place.
- **Description moved into an ⓘ icon.** "Track, manage and stay on top of every action across your clients, team and client contacts." no longer shows under the title. It appears as a tooltip when you hover or focus the ⓘ icon beside "Action Register".
- **KPI wording:** "Pending (your actions)" is now "Pending (you)".
- **KPI descriptions moved into ⓘ icons.** Each KPI's grey line now appears as a tooltip on an ⓘ icon beside the KPI heading:
  - "Items assigned to you"
  - "Items assigned to your team"
  - "Waiting on client response"
  - "Done or verified"
- **Shorter KPI cards.** Padding goes from 20/18px to 12px top and bottom, and the content is centred vertically. Cards are 84px tall at 1440px wide.
  - Clicking a card still filters the list. Clicking the ⓘ icon doesn't.
  - The last card's tooltip opens to the left so the screen edge doesn't cut it off.
- **Filter bar keeps only "Needs review".**
  - The All, My pending, Team pending, Client pending and Completed pills are removed, since the KPI cards above already do those filters.
  - To go back to all items, click the selected KPI card again.
  - Clicking a KPI card while in Needs review returns to the action list.
  - "Needs review" only appears for viewers who could see it before.
- **Board cards: the done check moves to the top-right corner and the owner avatar to the top-left.**
  - The title, place, date and priority now start where the check used to be.
  - The title leaves room on its right for the check.
  - The chevron stays centred on the right edge.
  - The check still opens the "What shows it's done?" dialog.
  - This changes the Board layout only. List (table) rows are unchanged.
- **Board cards: client initials, plain date, hover tooltip.**
  - **Avatar:** it now shows the client's initials (BM = Bloom Manor) instead of the assigned team member's. Programme-ops cards show MA or GA in the programme colour.
  - **Date:** the date shows on its own, for example "29 Aug 2026" with no "(41 days late)". Late dates stay red.
  - **"Programme ops" renamed "Internal" everywhere in the app.** That covers:
    - the pill on board cards and List rows
    - the List's place sub-line
    - the item drawer's subtitle
    - the "Programme ops" filter tab and section heading on the original Action register page (`#actions`)
  - **Tooltip:** hovering (or focusing) a card shows the client name and its timing, centred above the card:
    - "N days late"
    - "Due today"
    - "Due tomorrow (1 day left)"
    - "N days left"
    - "No due date"
    - "Completed"
  - **Board only:** List (table) rows are unchanged.
- **Drag a card onto a KPI to change its status** (Board view).
  - **The card itself moves:** it lifts with a shadow and a slight tilt and follows the pointer, leaving its slot empty. This replaces the browser's faded copy.
  - **Where you drop depends on the view:**
    - **No KPI selected (four-column board):** drag the card between the columns (My pending, Team pending, Client pending, Completed). The columns get a dashed outline, and the one under the pointer fills with its colour.
    - **A KPI selected (one spread-out column):** drag the card onto one of the four KPI cards in the header instead, with the same highlighting.
    - Either way the drop does the same thing, as listed below.
  - **Dropping elsewhere:** the card slides back to its place.
  - **Clicks still work:** a plain click (under 6px of movement) still opens the card. A drag never opens it.
  - **Pending (you):** assigns the action to the current viewer, sets it WIA-side, and reopens it if it was done.
  - **Pending (client):** marks it as waiting on the client, and reopens it if it was done.
  - **Pending (team):** always asks "Who should own it?" first (see "Pending (team) asks who should own it").
  - **Completed:** opens the existing "What shows it's done?" modal. Nothing is closed until you confirm there.
  - **Internal (programme) items:**
    - They can move between pending and Completed.
    - Dropping one on Pending (you) assigns it to you.
    - They can't be moved to Pending (client).
  - **History and confirmation:** every move is written to the action's history ("Moved to Pending (client) by Whitney.") and confirmed with a toast.
  - **Other ways to change status still work:** the modal's own buttons, the Owner field and the done check.
- **Action dialog: "Source" and "ClickUp" links removed.**
  - The header of an opened action now shows only its status, priority and verification badges.
  - The "Sources disagree" note in the body is unchanged.
- **Action dialog: "Mark blocked" replaced by "Change status".**
  - The button in the footer of an open action now opens a small menu that opens upward. It lists the board stages other than the one the action is in now: Pending (you), Pending (team) and Pending (client). For example, a team-pending action offers Pending (you) and Pending (client).
  - Completing an action stays on the "Mark done…" button next to it, so the menu doesn't repeat it.
  - Each pick moves the action the same way dragging its card does:
    - **Pending (you):** you become the owner, on the WIA side.
    - **Pending (client):** it moves to the client side.
    - **Pending (team):** opens a list of team members inside the menu (see "Pending (team) asks who should own it").
  - Each move is written to the action's history ("Moved to Pending (client) by Whitney.") and confirmed with a toast. The KPI counts update straight away.
  - The menu closes on a pick, a click anywhere outside it, or Escape.
  - It shows only while the action is pending. Done actions keep their "Reopen" button.
- **Action dialog: comment box starts collapsed.**
  - The "Add a comment" label and the open two-line box are replaced by a single one-line field that reads "Add a comment…". You type straight into it.
  - Clicking into the field expands it and shows the "Post comment" button.
  - After posting, or when you click away with the field empty, it collapses back to one line.
  - If you click away while there's text in the field, it stays expanded with the button visible, so the draft isn't hidden.
- **Internal tasks open in the full action window.**
  - Clicking an Internal (accelerator upkeep) card used to open a small box with only the status, the programme and a single Mark done button. It now opens the same window as client actions: Description, Owner & deadline with the Assigned/Acknowledged chip, and History with comments.
  - The header reads "Internal · Meta Ads Accelerator" (or Google Search Accelerator), with the status, an "Internal" tag and the recurrence (for example "Weekly") instead of priority and verification.
  - The line "Accelerator upkeep is internal work: it isn't counted as any client's open action" now sits under the description.
  - Change status offers only Pending (you) and Pending (team), because an Internal task can't wait on a client.
  - Mark done… completes the task straight away, with no "What shows it's done?" step. Reopen works as before.
  - Recurring tasks are never shown as overdue in the header.
  - Description edits, comments, owner and deadline changes, and moves are all written to the task's History.
- **Board cards: priority tag moved to the bottom right.**
  - The High, Medium or Low tag (and "Completed" or "Awaiting check" on done cards) now sits in the card's bottom-right corner, lined up under the round done check.
  - The date stays bottom-left.
- **KPI tooltip fix at narrow widths.** At 1100px and below the KPI cards sit in two columns. There, the "Pending (team)" ⓘ tooltip stuck out 1px past the window and caused a small sideways scroll. Tooltips in the right-hand column now open leftward, and the page no longer scrolls sideways.
- **Header row aligned.**
  - The top bar keeps its full width, so the bell and avatar stay at the top right on every page.
  - On the Action register pages, the whole header is now one line: the "Action Register" title and its ⓘ, the "1 source failed to sync" chip, the bell and the avatar.
    - The page moves up 20px so the title lines up with the bell and avatar, with everything centred on the same height.
    - The KPI row moves up with it.
    - This applies at desktop widths only (701px and up).
- **Footer stays at the bottom.** On short pages, the "Wedding Industry Ads ✧ Client Knowledge Base" footer now sits at the bottom of the window instead of right under the content. On long pages it follows the content as before.
- **Filtered board spreads across the page.**
  - When a KPI filter leaves only one board column, that column takes the full width.
  - Its cards sit side by side in a grid of cards at least 280px wide: 3 per row at 1440px and 4 at 1920px.
  - Every card in that column shows straight away, and the "View more (N)" button is hidden. For example, Team pending shows all 11 and Completed all 21.
  - The unfiltered four-column board is unchanged. It still shows 5 per column with "View more".
- **Selected KPI outline blinks.** The KPI card whose filter is on now blinks its solid 1px border line.
  - The line fades from the card's own colour to a light tint and back every 1.6s.
  - The existing soft ring around the selected card stays still. Only the line animates.
  - It stops when the filter is cleared.
  - It's turned off for viewers whose system is set to reduce motion.
- **Account-scope line removed ("v2 · Teams" page only)** for every viewer, in both Board and List.
  - Removed for team members: "Showing *Bloom Manor, Rosewood Estate, …* (your account teams), plus anything assigned to you elsewhere."
  - Removed for admins (Whitney): "You see *every client* as an admin. Others see only the clients whose account team they're on, plus anything assigned to them."
  - The "Revised" page never had this line.
  - What each viewer can see is unchanged. Only the explanation is gone.

### Header: workspace search removed

- The "Search ⌘K" button is gone from the top bar on every page.
- The Ctrl/⌘+K shortcut no longer opens the search dialog.
- The top bar keeps only the attention-items bell and the viewer avatar.
- Search boxes inside individual pages are unchanged, for example "Search action items…" in the Action register.

### Fit to screen on laptops (2026-11-04)

- On any window from 1280px to 1919px wide (every MacBook at its default display setting), the page now shows the same layout as a 1920px monitor, shrunk to fit. It no longer switches to its narrower layout.
  - Same 4 board columns, same card line breaks, same sidebar.
  - Scale: about 0.75 on a 13" MacBook (1440px), 0.79 on a 14" (1512px), 0.9 on a 16" (1728px).
  - It shrinks to the window's width. MacBook screens are taller in proportion, so they show a little more of the page at the bottom.
- Every page is covered, not just the Action Hub.
- A new icon button at the left of the top bar's bell switches it on and off. It's on by default, and each browser remembers its own setting.
  - Turn it off to get the regular layout back, for example to make text bigger with Cmd/Ctrl + Plus. While it's on, browser zoom doesn't make text bigger.
  - The button only shows between 1280px and 1919px.
- At 1920px and wider, and below 1280px (tablets, phones), nothing changes.

### Technical notes (for reapplying after a re-export)

All edits are in the inlined module script, plus one `<style id="mvp-v1">` block before `</head>`.

1. **Sidebar filter:** `Lr.filter(e=>!s.includes(e.id))` also excludes the blocked view ids.
2. **Sidebar section:** a "COMING SOON" label and five `nav-item nav-soon` items are inserted before the "THE FOUNDATION" divider.
3. **Client tabs:**
   - The tab list (`h=[…]`) sets `soon:!0` on `health` and on `money`, and the `pt(e.viewer)` admin check on `money` is removed.
   - The tab button gets `disabled` and an `aria-disabled` and `title`, and its `onClick` checks `n.soon` first.
4. **Router:**
   - The original `cd` is renamed `cd0`, and its fallback view changes from `dashboard` to `clients`.
   - A new `cd` wraps it. It blocks the views listed above, remembers the last allowed hash (`mvpLast`, which starts as `#clients`) and shows the notice (`mvpSoon`).
   - The `hashchange` handler skips its scroll-to-top when a link was blocked (`mvpBlocked`).
5. **CSS:** dims the `.nav-soon` items and disabled `.client-tabs` buttons, and styles `.mvp-soon-toast`.
6. **Action Register header (components `Ko` and `Nl`):**
   - The `rb-eyebrow` and `rb-lede` paragraphs are replaced by a `.mvp-title-row`: the `h1` plus a `scope-info` ⓘ button (icon `Pn`) with a `scope-tip` tooltip.
   - These reuse the Client 360 tooltip styles.
7. **KPI arrays (`Po` and `Sl`):** the `kpi` value for `mine` is now `Pending (you)`.
8. **KPI render:**
   - The `<small>{e.detail}</small>` is removed.
   - The label becomes `.mvp-kpi-label`, holding the text and a `.mvp-kpi-info` ⓘ with a `scope-tip` (`id="kpi-tip-<id>"`). Its click stops propagation.
   - The KPI button gets `aria-describedby`.
9. **KPI CSS:**
   - `.rb-kpi` gets `padding:12px 20px`, `align-items:center` and `overflow:visible`, so the tooltip isn't clipped.
   - The decorative `:after` ellipse is redrawn as a radial gradient inside the card, so it stays clipped without `overflow:hidden`. It loses its slight tilt.
   - The hovered card is raised with `z-index:5`.
10. **Filter row (`.rb-filters` in `Ko` and `Nl`):** the `[[`all`,`All`,…],...Po/Sl.map(…)].map(…)` pill list is deleted. Only the `n&&` "Needs review" `rb-review-pill` button remains.
11. **Board card CSS (no markup change):**
    - `.rb-card` gets `position:relative` and `align-items:flex-start`.
    - `.rb-card>.rb-check` is set to `position:absolute` at `top:10px` and `right:10px`.
    - `.rb-card .rb-card-open` gets `align-items:flex-start`.
    - `.rb-card .rb-card-body strong` gets `padding-right:18px`.
    - `.rb-card .rb-chev` gets `align-self:center`.
12. **Header search (App `ud`):**
    - The `header-search` button is deleted.
    - The keydown handler `let n=e=>{(e.ctrlKey||e.metaKey)&&e.key.toLowerCase()===`k`&&…}` becomes `let n=e=>{};`. It stays registered, so the listener cleanup is unchanged.
13. **Scope line (`Nl` only):** the `r===`actions`&&(0,R.jsx)(`p`,{className:`rt-scope`,…})` expression after `.rb-bar` is deleted. The unused `.rt-scope` CSS is left in place.
14. **Filtered board and KPI pulse CSS (no markup change):**
    - `.rb-board:has(>.rb-column:only-child){grid-template-columns:1fr}`.
    - The only column's `ul` becomes `display:grid` with `repeat(auto-fill,minmax(280px,1fr))`.
    - `@keyframes mvp-kpi-pulse` animates only `border-color`, from `var(--ink-tone)` to `color-mix(in srgb,var(--ink-tone) 20%,#fff)` and back.
    - It's applied to `.rb-kpi.selected` at `1.6s ease-in-out infinite` and disabled under `prefers-reduced-motion`.
15. **Board column slicing (`Ko` uses `Io`, `Nl` uses `wl`):**
    - `i=r?t:t.slice(0,LIMIT)` becomes `i=r||s!==`all`?t:t.slice(0,LIMIT)`.
    - The "View more" button's condition `t.length>LIMIT&&` becomes `s===`all`&&t.length>LIMIT&&`.
16. **Board card render (`we` in `Ko`, `I` in `Nl`):**
    - The avatar's `Vo/kl(n.owner)` becomes `n.placeInitials`, with an `is-programme` class for programme items.
    - The date drops `n.rel&&` (${n.rel})``.
    - A `<span class="mvp-card-tip" role="tooltip">` is appended inside `.rb-card` with `n.place` and a label built from `n.closed` and `n.rel`.
    - CSS shows it on `.rb-card:hover` and `:focus-within`, centred above the card (`left:50%;bottom:calc(100% + 6px);transform:translateX(-50%)`), and raises the hovered `li` to `z-index:30`.
17. **Drag to KPI (`Ko` and `Nl`):**
    - A `mvpDrop(q,k)` declarator is added to each component's `let` chain, right after the "open item" helper (`ye=` in `Ko`, `Se=` in `Nl`).
    - It uses each component's own helpers:

      | Component | done toggle | open | history | programme toggle |
      |---|---|---|---|---|
      | `Ko` | `ve` | `ye` | `F` | `_e` |
      | `Nl` | `xe` | `Se` | `ve` | `be` |

    - It also uses `re` (the programme-items setter), `e.updateAction`, `e.notify` and the viewer `t`.
    - Board cards (`.rb-card`) get `onPointerDown:z=>mvpPointerDrag(z,e,mvpDrop)`. This uses pointer events, not HTML5 drag-and-drop.
    - `mvpPointerDrag` is a module-level function placed just before `var mvpLast`. It works like this:
      - It ignores presses on the done check.
      - It starts after 6px of movement, then adds `.mvp-lifted` and `body.mvp-dragging`.
      - It moves the real card with `transform:translate(…) rotate(1.5deg)`.
      - It picks its targets from the board. If `.rb-board` has exactly one `.rb-column` (a KPI filter is on), the targets are `.rb-kpi` and the body class is `mvp-dragging-kpi`. Otherwise the targets are `.rb-column` and the body class is `mvp-dragging-cols`.
      - It hit-tests the targets with `document.elementsFromPoint`, marks the one under the pointer with `.mvp-drop`, and reads the bucket from its `tone-*` class.
      - It swallows the click that follows a drag.
      - On release over a KPI it calls `mvpDrop(item, tone)`. Otherwise it animates the card back.
    - CSS:
      - `.rb-board .rb-card{cursor:grab;touch-action:none}`
      - `.rb-card.mvp-lifted{position:relative;z-index:1000;…}`
      - `body.mvp-dragging` disables text selection.
18. **Footer CSS:**
    - `.workspace` gets `display:flex`, `flex-direction:column` and `min-height:100dvh`.
    - `.workspace>main` gets `flex:1 0 auto`, `width:100%` and `box-sizing:border-box`.
    - `.workspace>.workspace-footer` gets `flex-shrink:0`.
    - `.workspace>.utility-header` gets `width:100%`, `box-sizing:border-box` and `flex-shrink:0`. Without this, the flex column shrinks the header and centres the bell and avatar.
    - `#main-content .rb-head` gets `align-items:center`.
    - `#main-content .rb-head>.rb-sync` gets `align-self:center` and `margin-right:96px`, which leaves room for the bell and avatar.
    - `@media (width>=701px){#main-content .rb-view{margin-top:-84px}}`. The app's own value is `-64px`. A negative margin on `.rb-head` doesn't work, because it collapses into the view's margin.
19. **"Programme ops" → "Internal":** every `` `Programme ops` `` string literal in the bundle becomes `` `Internal` ``. There are 10 in all:
    - 4 `rb-pill pill-programme` spans
    - 2 `placeSub`
    - 2 drawer `subtitle`
    - the `h2` and the `programme` filter `label` in the original Action register
    
    Afterwards no "Programme ops" text remains in the file.
20. **Action dialog `meta` (shared by every Action register page):**
    - `t.sourceId&&(0,R.jsx)(Wr,{…label:`Source`})` is deleted.
    - `t.clickupUrl&&(0,R.jsxs)(`a`,{…children:[`ClickUp`,…]})` is deleted.
21. **Action dialog footer status menu (`Gi`, the modal variant):**
    - `[mvpSO,mvpSetSO]=(0,y.useState)(!1)` and an `mvpFx=(0,y.useEffect)(…)` are added at the start of `Gi`'s `let` chain. While the menu is open, the effect adds a capturing `pointerdown` listener on `document` that closes the menu when the press is outside `.mvp-status`.
    - The footer's `c&&(0,R.jsx)(`button`,{…children:t.status===`Blocked`?`Unblock`:`Mark blocked`})` is replaced by a `div.mvp-status` holding a `Change status` trigger (`aria-haspopup`, `aria-expanded`) and, when open, a `div.mvp-status-menu[role=menu]`.
    - The menu lists the stages `[[`mine`,`Pending (you)`],[`team`,`Pending (team)`],[`client`,`Pending (client)`]]` minus the current one. The current stage uses the board's bucket rule: `t.side===`Client`?`client`:t.owner===n?`mine`:`team``.
    - A pick mirrors `mvpDrop`:
      - It builds `w={side:k===`client`?`Client`:`WIA`}`.
      - For `mine` it also sets `w.owner=n`.
      - It sets `w.history=u(`Moved to … by …`)`, then calls `e.updateAction` and `e.notify`.
      - `team` when `t.owner===n` only shows a toast and focuses `.action-detail-modal [aria-label="Owner"]`.
    - Escape on the wrapper closes the menu without closing the dialog.
    - CSS: `.mvp-status-menu` is `position:absolute;bottom:calc(100% + 6px);left:0`, so it opens upward. Each option has a `.mvp-status-dot-{mine|team|client}` dot.
    - The drawer variant (`Ki`) still has its own Mark blocked and Unblock buttons. It isn't used on these pages.
22. **Action dialog comment form (`Gi`):**
    - `(0,R.jsxs)(`label`,{children:[`Add a comment`,(0,R.jsx)(`textarea`,{…rows:2,placeholder:`Leave context for the team`})]})` becomes a bare `textarea` with `rows:1`, `aria-label:`Add a comment`` and `placeholder:`Add a comment…``.
    - CSS: the textarea is 36px with `resize:none`.
    - It grows to `min-height:72px` with `resize:vertical` under `.action-detail-comment-form:focus-within` or `textarea:not(:placeholder-shown)`.
    - The button is hidden with `.action-detail-comment-form:not(:focus-within):has(textarea:placeholder-shown) .button{display:none}`.

23. **Revised Action register (`#actions-v2`) removed.** Notes 6–17 above still name `Ko`, `Po`, `Io` and `we`. After this note, only their `Nl` half applies.
    - `function Ko(e){…}` is deleted, about 15.3k characters. It ends right before `var qo=e=>({mood:e.mood[7]`. Its bounds were checked by parsing the cut-out function on its own.
    - Its helpers (`Po`, `Io` and the rest) are left in place, unused.
    - The sidebar list `Lr` drops `{id:`actions-v2`,…,icon:Hn}`.
    - The nav render drops the `actions-v2` aria-label and title branches and the `Revised` badge.
    - The App render drops `e.view===`actions-v2`&&(0,R.jsx)(Ko,…)`. The header breadcrumb condition drops `e.view!==`actions-v2``.
    - The valid-view list `od` drops `actions-v2`.
    - The three `navigate(`actions-v2`)` calls become `navigate(`actions-v3`)`. The notifications drawer's `window.location.hash=`actions-v2/review`` becomes `actions-v3`.
    - The MVP `cd` wrapper first rewrites any `#actions-v2` or `#actions-v2/…` hash to `#actions-v3` with `replaceState`.
    - The localStorage key `wia-client-portfolio-html-actions-v2` is unchanged. It's only a storage name, and renaming it would reset saved preview data.
24. **Internal item modal (`Nl`):**
    - `Te&&(0,R.jsx)(Yr,{title:Te.title,subtitle:`Internal`,…Mark done…})` is replaced by `Te&&(0,R.jsx)(Gi,{…})`.
      - It gets `action:{...Te,kind:`programme`,side:`WIA`,note:Te.note||``,verifyRequired:!1}` and `deadlineRequests:!1`.
      - `updateAction:(q,w)=>re(z=>z.map(z=>z.id===q?{...z,...w}:z))` writes into the programme-items state.
      - `requestDone` sets `status:`Done`` and appends a history entry.
    - `Gi` branches on `t.kind===`programme``:
      - The subtitle is `Internal · ${t.programme}` (so `j(t.clientId)` isn't called).
      - The meta badges are `Internal` and `t.recurring` instead of priority and verification.
      - The hint paragraph follows the description.
      - The stage menu filter drops `client`.
    - The status badge's overdue test becomes `ue(t)&&!t.recurring`.
25. **Board card pill CSS:** `.rb-board .rb-card{padding-bottom:14px}`. The pill (and the Slack icon from note 29) is wrapped in `span.mvp-card-end`, which is `position:absolute;right:10px;bottom:12px;display:inline-flex;gap:6px`. An earlier version positioned `.rb-pill` itself. The card is already `position:relative`, and the List view is unaffected.
26. **KPI tooltip CSS:** `@media (width<=1100px){.rb-kpi:nth-child(2n) .mvp-kpi-info .scope-tip{left:auto;right:0}}`. It matches the app's own `(width<=1100px)` rule that switches `.rb-kpis` to 2 columns.
27. **Team-member picker:**
    - Two module-level functions are placed just before `mvpPointerDrag`:
      - `mvpTeamOptions(item, viewer)` builds the list. Related people come from `xl[item.programme]` for Internal items, or `bl()[item.clientId]` (the ClickUp account teams) for actions. Other people are the rest of `C`, and the viewer is excluded.
      - `MvpTeamPick({item,viewer,current,onPick,onBack})` renders it.
    - `Gi`:
      - `[mvpPk,mvpSetPk]=(0,y.useState)(!1)` is added. The trigger resets it.
      - The team option now runs `mvpSetPk(!0)` instead of the old toast-and-focus, and gets a `›` marker.
      - While `mvpPk` is set, the menu (`.mvp-status-menu.is-picking`) renders `MvpTeamPick`. A pick calls `e.updateAction` with `side`, `owner`, `acknowledged:!1`, `ackMethod:void 0`, `assignedOn:S` and a history entry.
    - `Nl`:
      - `[mvpPick,mvpSetPick]=(0,y.useState)(null)` is added at the start of the `let` chain.
      - `mvpDrop` returns `mvpSetPick(q)` for `k===`team`` before any other branch. The old `Se(q)`+toast handover branches are removed.
      - A new `mvpTeamDo(q,name)` declarator handles a pick. It writes into `re` for programme items and calls `e.updateAction` for actions, and reopens done items.
      - A `mvpPick&&(0,R.jsx)(Yr,{title:`Who should own it?`,className:`mvp-pick-modal`,…})` is rendered before the action modal.
    - CSS covers `.mvp-pick*` and `.mvp-status-more`.
28. **Rename:** a regex `Action [Rr]egister` → `Action Hub` over the whole file replaced 23 occurrences, all display strings. View ids, hashes and the localStorage key are untouched. Run it after reapplying every other edit, since some earlier notes quote the old strings.
29. **Ping on Slack:**
    - Module-level functions placed before `mvpTeamOptions`:
      - `MvpSlackIcon` is an inline 4-colour Slack SVG.
      - `mvpChannel(item)` returns `te[clientId].channel`. Programme items use `#meta-accelerator` or `#google-accelerator`, and anything else falls back to `#client-<id>`.
      - `mvpAgo(iso, now)` formats "N mins/hrs/days ago".
      - `mvpTopToast(text)` adds a `div.mvp-top-toast` shown with `popover=manual` and `showPopover()`, so it draws above the modal `<dialog>`. It's removed after 3.2s.
      - `MvpPing({action,viewer,now,update,hist})` is the button plus its `.mvp-ping-tip` tooltip. The 2-minute cooldown is `12e4` ms and uses `aria-disabled`, so hover still works. A click calls `update(id,{slackPingedAt,slackChannel,history})`.
    - `Gi`:
      - `[mvpNow,mvpSetNow]=(0,y.useState)(…)` and `mvpTick=(0,y.useEffect)(…)` are added. The effect ticks every 1s while `t.slackPingedAt` is set.
      - The footer fragment `p` starts with `c&&(t.side===`Client`||t.owner!==n)&&(0,R.jsx)(MvpPing,{…})`.
      - Internal items go through the programme `updateAction` adapter from note 24.
    - `Nl` cards:
      - `Ee` adds `pinged:t.slackPingedAt` to both the programme and action shapes.
      - The card foot adds `n.pinged&&span.mvp-card-slack` after the date.
      - `.mvp-card-tip` adds `span.mvp-card-ping[data-at]`.
      - The card gets `onPointerEnter`, which refreshes that span's text from `data-at`.
    - CSS covers `.mvp-ping*`, `.mvp-slack-icon`, `.mvp-card-slack`, `.mvp-card-ping` and `.mvp-top-toast` (with the `mvp-top-toast-in` keyframes), plus `.rb-board .rb-card-foot{justify-content:flex-start}`.
30. **Add action form (`da`):**
    - The `(0,R.jsxs)(`label`,{children:[`Type`,(0,R.jsx)(ni,{…name:`type`,defaultValue:`Admin`,…Mi.map(…)})]})` label is deleted from the Priority row's `form-two-col`.
    - The submit handler's `c=String(a.get(`type`))` becomes `c=String(a.get(`type`)||`Admin`)`, so `actionType` stays `Admin` and `verifyRequired` stays `false`.

31. **Agentation toolbar removed (before the first deploy):**
    - The lazy loader `,yv=(0,y.lazy)(()=>Cd(()=>Promise.resolve().then(()=>(vv(),mv)),void 0))` is deleted. The root render changes from `children:[(0,R.jsx)(ud,{}),yv&&(0,R.jsx)(y.Suspense,{…(0,R.jsx)(yv,{})})]` to `children:[(0,R.jsx)(ud,{})]`.
    - The agentation module's code and CSS are still inlined, but they never initialise, because `vv()` is never called. No toolbar is drawn and no requests go to a local agentation server.
    - For local review with the toolbar, use `frontend/exports/client-portfolio.html`.
    - **Restored 2026-11-03** for the next feedback rounds: the `yv` lazy loader and the `yv&&(0,R.jsx)(y.Suspense,…)` render child are back exactly as they were. Remove them again (this note's two edits) before the next push to `mvp`, because Railway auto-deploys that branch.
32. **v1 Action Hub (`#actions`) removed:**
    - `function oa(e){…}` (about 6.1k characters) is deleted. Its bounds were checked by parsing it on its own. Its helpers (`na`, `Ui`, `Ki`, `Bi` and the rest) are left in place.
    - The sidebar list `Lr`:
      - drops `{id:`actions`,…,icon:zn}`
      - gives `actions-v3` the icon `zn` instead of `Bn`
    - The nav render:
      - `aria-label` and `title` become plain `r`
      - the `t===`actions`&&n>0` count badge and the `v2 · Teams` badge are deleted
    - The App render drops `e.view===`actions`&&(0,R.jsx)(Zi,{})` from the header and `e.view===`actions`&&(0,R.jsx)(oa,…)` from main. The breadcrumb condition drops `e.view!==`actions``, and `od` drops `actions`.
    - Links:
      - `e.navigate(`actions`)` ×3, `D(`actions`)` and the assistant link handler's `t.navigate(`actions`)` now use `actions-v3`.
      - The two "Open action register" labels become "Open Action Hub", and "Open the action register" becomes "Open the Action Hub".
    - The `cd` wrapper's regex becomes `/^#actions(-v2)?(\/|$)/`, so `#actions…` and `#actions-v2…` both rewrite to `#actions-v3`.
33. **List view CSS:** `.rb-table .rb-sub,.rb-table .rb-person small,.rb-table .rb-due small,.rb-table td .rb-flag{display:none}`. There's no markup change.
34. **Client card menu and archive (`xi`, `Ci`):**
    - Module-level `var mvpArchKey=`wia-mvp-archived-clients``, plus `mvpArchLoad()` and `mvpArchSave(ids)` (a JSON array in localStorage), placed before `MvpSlackIcon`.
    - `xi` takes `mvpIsArc` and `mvpToggle`. Its `cp-menu-list` children are replaced with "Open client record" and an archive or restore button (`.mvp-menu-archive` when archiving).
    - `Ci`:
      - `[mvpA,mvpSetA]=(0,y.useState)(mvpArchLoad)` is added.
      - `mvpLive` and `mvpArc` split `w`. `mvpT(client)` toggles, saves and notifies.
      - `_` (My clients) is built from `mvpLive`, and `v` uses `mvpArc` when `n===`archived``.
      - The scope list gets `[`archived`,`Archived`,mvpArc.length]`, and All clients counts `mvpLive`.
      - The card gets `is-archived`, and the empty state has an Archived variant.
    - CSS covers `.mvp-menu-archive` and `.cp-card.is-archived`.
35. **Pin to top (`xi`, `Ci`):**
    - Module-level `var mvpPinKey=`wia-mvp-pinned-clients``, plus `mvpPinLoad()` and `mvpPinSave()`.
    - `xi` takes `mvpIsPin` and `mvpPin`. On non-archived cards it renders a `.mvp-menu-pin` button with icon `ar` (pin) or `ir` (pin-off).
    - `Ci`:
      - `[mvpP,mvpSetP]=(0,y.useState)(mvpPinLoad)` is added.
      - `mvpPT(client)` toggles a pin and prepends new pins.
      - The portfolio sort is prefixed with the pin order (`indexOf` when both items are pinned, otherwise pinned-first), before the existing overdue and name sort.
      - Pinned cards get a `span.mvp-pin-badge`, and the List view name gets a `span.mvp-pin-inline`.
    - CSS covers `.mvp-menu-pin`, `.mvp-pin-badge` and `.mvp-pin-inline`.
36. **Now tab grid CSS (no markup change):**
    - `.client-record-body>.now-meetings` and `.client-record-body>.now-lower` both get `display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px;align-items:stretch;margin:0 0 22px`. This overrides `.now-lower`'s `1.55fr 1fr` and `align-items:start`.
    - Their `.now-card` children get `margin:0;min-width:0`, which removes `.next-meeting`'s `margin-top:20px`. `.next-meeting` gets `border-radius:20px`.
    - `.comms-card` is kept at `margin:0 0 22px`.
    - Both grids collapse to one column at `width<=900px`.
    - The `.now-lower` cards get `container-type:inline-size`, with an `@container (width<620px)` rule that makes `.action-row` a grid: areas `"chk main main chev" ". due src chev"`, with `.action-due` set to `flex-direction:row`.
37. **Compact record header CSS (no markup change):**
    - Under `@media (width>=701px)`:
      - `.client-cover-content{min-height:0;padding:24px 34px 22px}` (it was `min-height:294px;padding:42px 38px 34px`)
      - `.cover-identity .portfolio-chips{margin-top:10px}`
      - `.cover-identity .cover-client-facts{margin-top:14px}`
    - At all widths:
      - `.view.client-detail .client-record-body{padding-top:16px}`
      - `.client-record-body>.record-strip{min-height:0;padding:11px 18px;margin-bottom:14px}`
      - `.client-record-body>.client-tabs{margin-bottom:16px}`
38. **Client record tab order:** in the tab list `h=[…]`, the `commitments` and `meetings` entries are moved ahead of `history` and `brief`.

34. **Client Portfolio cards and header (2026-11-03):**
    - `Ci` renders each `.cp-name` as an anchor with `href:#clients/${t.id}/now`. Its absolutely positioned `::after` covers the card, making the logo, body, badges and blank space follow the same link. Keyboard Enter and native browser link actions work.
    - `.cp-menu` and the footer open button sit above the stretched link so their actions still work independently. The link has no underline and keyboard focus outlines the card.
    - `.cp-head` matches the Action Hub title size (44px), line-height (1.15), spacing and title/info row. The repeated eyebrow is removed and the description moves to `#cp-lede-tip`, shown from the accessible info button. The Add client button reserves 112px on desktop for the existing utility-header controls. Mobile header rules are retained.
    - Only portfolio markup and `.cp-*` CSS change; Action Hub code and shared title/tooltip styles are unchanged.
    - Verified all six full-card destinations, keyboard activation, independent menu/actions routing, the info tooltip, and the 1920×957 layout. Inline JavaScript syntax checks pass.

35. **Portfolio card owner alignment (2026-11-03):** `.cp-owner` uses `margin:auto 0 16px` and `padding-top:14px`; `.cp-stats` uses `margin-top:0`. Flexible space now sits above the owner row, keeping it aligned at the lower end of every card immediately above the action-count divider. Only these two portfolio CSS rules change.

36. **Sidebar account placement (2026-11-03):** Remove the `.sidebar-footnote` span containing "A shared memory for your team" from `Rr`. The bottom section already uses `margin-top:auto`, so removing the footnote lowers the account row into that space while retaining its bottom padding. No account-switching behavior changes. Inline JavaScript syntax checks pass.

37. **Client tabs order (2026-11-03):** Swap the adjacent Health and Support entries in the client-detail tab array. Support now precedes Health (Soon); routes, counts and availability remain unchanged.

38. **Profile label legend removed (2026-11-03):** Delete the `.label-legend` div at the start of `so` (client profile). Individual fact tags and evidence links remain in place. Inline JavaScript syntax checks pass.

39. **Commitments pagination for every client (2026-11-03):** `uo` filters by current client and side, sorts due dates ascending (undated last), and renders 10 actions per page with Previous/Next controls and a range/page count. Reset on client or side changes; clamp after action updates. `.commitments-pagination` styles are in the appended style block. Applied to both the MVP source and real_index.html, so build_real_index.py retains pagination when rebuilding the real-data page from the MVP. Action Hub is unchanged.

40. **Portfolio health tags removed (2026-11-03):** In `Ci` (client portfolio), the card footer's `(0,R.jsx)(Si,{id:t.id})` becomes an empty `span`, so the open-record chevron stays right-aligned; the list view drops the `Health` `th` and its `td`. `Si` (HealthPill) is now unused. Health is still "Soon", so showing "Settling in" / "Unassessed" on every card implied a reading that doesn't exist. The "Health & sentiment" filter in the toolbar is unchanged.

41. **Now tab: Client sentiment card shows "Coming soon" (2026-11-03):** `io` now renders only the panel shell (title "Client sentiment", eyebrow "LAST 30 DAYS", a `soon-tag` "Soon" badge) with a centred `.now-soon` block: "Coming soon" / "Client sentiment arrives with Health & sentiment." The old drivers, quote and Health link are gone. `.now-soon` and `.sentiment-card.is-soon` styles sit before `.sentiment-line{` in the style block.

42. **Now tab: "+N more in Commitments" opens the Commitments tab (2026-11-03):** In `ro` (Action items card), the `p.hint` becomes `button.text-button.now-more-link` with `onClick:()=>e.openClient(t.id,\`commitments\`)` and an arrow icon (`Vt`). Applied to `mvp/index.html`; `real_index.html` inherits it on rebuild.

43. **Engagement switch removed for all clients (2026-11-03):** Remove the conditional `.engagement-switch` block before `.client-tabs` in the shared client-detail renderer. Applied to MVP (the real-data rebuild source) and real_index.html, so rebuilding preserves removal.

44. **Client record header: health badge removed (2026-11-03):** In the record cover, the `.cover-health` card loses its `button.cover-health-link` (category such as "Settling in" / "Unassessed", its first cause, and the link to the Health tab); the card keeps only the call button ("Prepare for the call" or "View meetings"). Its category modifier class is replaced by `cover-health-calls`, so no health colour remains. The `.cover-health-link` CSS is now unused.

45. **Client logo sizing (2026-11-03):** The logo hook passes optional `logos[id].scale` through `--portfolio-logo-scale`. The portfolio-logo-sizing style scales only banner images, leaving list thumbnails unchanged. Real client overlays set individual scale values to compensate for padding in the supplied artwork; Funktastic retains its existing size.

46. **Now tab: Action items card shows 3 rows (2026-11-03):** In `ro`, `a.slice(0,5)` becomes `a.slice(0,3)` and the "+N more in Commitments" link appears when `a.length>3` with `a.length-3` as N. The link still opens the Commitments tab (note 42); the We owe / Client owes counts are unchanged.

47. **History tab: period control replaces Timeline / Activity feed (2026-11-03):** `co` drops the "History display" segmented control (the tab always shows the lane chart plus "Moments that shaped the account"). A "History period" segmented control offers All time / Month / Year / Custom range: Month uses `input[type=month]` (bounded by earliest evidence and today), Year a ThemedSelect of years with evidence, Custom two `input[type=date]` (swapped if From > To). Events are filtered to the window, and the lane chart's axis and end labels use the window (All time keeps "Processed through …"). Lane filter and "Since last call" still apply. `.history-period*` / `.history-range` styles sit before `.sentiment-line{`.

48. **Handover brief: Regenerate button and generated date (2026-11-03):** In `lo`, a "Regenerate" button (`dr` RefreshCw icon, spins with "Regenerating…" for ~0.9 s) sits before Copy and Download. It rebuilds the brief from the current record and stamps the local date and time in `localStorage` under `wia-brief-generated-v1:<clientId>`, re-read when the client changes, defaulting to the snapshot date. The eyebrow reads "CONTINUITY, WITHOUT THE CATCH-UP · GENERATED <date[, time]>"; the intro line and the Copy/Download markdown carry the same stamp. There's no AI call: the brief is assembled from the record on every render. build_real_index.py renames the key for the real-data copy.

49. **Deploy page: agentation toolbar stripped at build time (2026-11-03):** `build_real_index.py` applies note 31's two edits (delete the `yv` lazy loader; root render children become `[(0,R.jsx)(ud,{})]`) to `mvp/real_index.html` only, asserting each hook is found once. `mvp/index.html` keeps the toolbar. The build also writes `backend/.local/raw_pull/real/real_index.html` (gitignored) with the toolbar and the "LOCAL · real client data" title, for review rounds. The deploy copy keeps the plain "Client Portfolio" title.

50. **Sidebar "Coming soon" items no longer greyed out (2026-11-03):** In the `mvp-v1` style block, `.nav-item.nav-soon` changes `opacity:.55` to `opacity:1` and adds `color:#1c2430` (near-black), plus a new `.nav-item.nav-soon svg{color:#1c2430}` rule so the icons match (the base `.nav-item svg` is slate `#6c7d95`), so Overview, Call Preparation, Health & Sentiment, Client 360 and Invoices & Contracts read in black rather than faded grey. The other nav items keep their slate `#667286`. The "Soon" badges, `aria-disabled`, the not-allowed cursor and the disabled hover stay.

51. **Sidebar: "The Foundation" moved above the account row (2026-11-03):** In the sidebar, the divider, "THE FOUNDATION" label and the Source library / Connections buttons leave the main `nav` and move into a new `nav.nav-foundation` ("The foundation") placed just before `.sidebar-bottom`. CSS `.nav-foundation{margin-top:auto}.nav-foundation+.sidebar-bottom{margin-top:0;padding-top:4px}` (before `.nav-item.nav-soon svg{`) pins it to the bottom, directly above the Whitney Hodges account row. Buttons, routes and active states are unchanged.

52. **Sidebar: Foundation items in black (2026-11-03):** `.nav-foundation .nav-item:not(.active),.nav-foundation .nav-item:not(.active) svg{color:#1c2430}` (after `.nav-foundation{margin-top:auto}`) gives Source library and Connections the same near-black text and icons as the Coming soon items (note 50). The active item keeps its own highlight style.

53. **Sidebar: "THE FOUNDATION" label in black (2026-11-03):** `.nav-foundation .nav-label{color:#1c2430}` (after `.nav-foundation{margin-top:auto}`) changes the label from grey `#9a9c9f` to the same near-black as the Foundation items (note 52). The other section labels ("THE CLIENT DESK", "COMING SOON") stay grey.

54. **Fit to screen (2026-11-04):** A self-contained `<style id="fit-screen">` + `<script id="fit-screen-js">` block sits directly before the first `</head>` (after `<style id="portfolio-logo-sizing">`). It touches no other markup or bundle code, so after a re-export, paste the block back before `</head>` and rebuild `real_index.html`. With the toggle on and the window 1280–1919px wide, it sets `html{zoom: innerWidth/1920}` and:
    - **Media queries:** every `@media` rule whose conditions are all widths (88 in this build) is re-inserted (`deleteRule`/`insertRule`; Chrome may leave a `mediaText` edit unapplied until its next frame) as `all`/`not all` per its result at 1920px. The originals are restored when off. Print and reduced-motion rules are left alone.
    - **Viewport units:** every `vh`/`vw`/`dvh`/`svh`/`lvh` length in the stylesheets (26+ rules; skipping `url(...)` values and `@font-face`) is rewritten once to `calc(N<unit> * var(--fit-inv))`. `--fit-inv` is `1/zoom` (1 when off), so `100dvh` parts like the sidebar and modals still fill the window.
    - **Coordinates:** under `zoom`, Chrome reports rects, pointer coordinates, scroll offsets and `innerWidth`/`innerHeight` in screen pixels, but CSS lengths the code writes are page pixels. Without a fix, every JS-positioned menu would land at zoom × its intended position. The script divides `getBoundingClientRect`/`getClientRects` (Element and Range), `innerWidth/innerHeight`, `scrollX/Y`/`pageX/YOffset`, `MouseEvent`/`Touch` `clientX/Y`, `pageX/Y`, `x/y`, and the root's `clientWidth/Height` by the zoom, and multiplies `elementFromPoint(s)` and `window.scrollTo/scroll/scrollBy` arguments by it. With zoom 1 everything passes through unchanged.
    - **Toggle:** `button.icon-button.fit-toggle`, put first in `.utility-header .header-tools` and re-inserted by a MutationObserver if the header re-renders. Preference in `localStorage` `wia-fit-screen-v1` (`off` to disable); the build doesn't rename it, so the sample and real pages share it per browser. `.fit-in-range .cp-head .cp-add{margin-right:162px}` (was 112px) makes room for it next to "Add client".
    - **Verified (Chrome 152, 2026-11-04):** 1920×957 is unchanged (zoom 1, toggle hidden). At 1280×700, 1440×790, 1470×830, 1512×860, 1710×980 and 1728×1000, the Action Hub has 4 columns at 364px with the same title breaks as 1920. The sidebar is full height, there's no sideways scroll, and these all work: the date dropdown, the info tip, the action window and its upward Change status menu, and drag and drop between columns (including the Pending (team) owner picker). Client portfolio and a client record also checked. 1279px falls back to the regular layout. Not yet checked on a real Mac or in Safari.
    - **Automation caveat:** browser tools that locate elements through the page's own `getBoundingClientRect`/`innerWidth` (like Claude's browser pane) get page pixels while it's zoomed, so their clicks land off-target. Turn the toggle off before scripted testing at laptop widths.

55. **Satin ribbon as the sidebar's edge toggle (2026-11-05):** A self-contained `<style id="edge-toggle">` + `<script id="edge-toggle-js">` block sits directly before the first `</head>` (after the fit-screen block), in both `index.html` and `real_index.html`; after a re-export, paste it back before `</head>`. It appends one `button.edge-toggle` to `aside.sidebar` (`overflow:visible`), positioned `absolute` at `top:44%; right:-20px` (21×47, its left edge 1px over the sidebar border; drawn in a 26×58 viewBox and scaled down, reduced from 26×58 on 2026-11-05 at Jainil's request).
    - **Look:** a deep blue duchess-satin swallowtail ribbon drawn as inline SVG. Satin sheen stops run along its length (`#1f449a`→`#86a9ef`→`#1b3d8c`), with 2.4px gold piping on both long edges (`#f6e3a4`→`#c9a44c`→`#8f6e27`), a dark tuck gradient at the root so it reads as passing under the sidebar edge, a `drop-shadow` filter, and a gold `#f3dc96` chevron.
    - **Hover motion:** the ribbon draws out from under the sidebar (`.et-ribbon` `scaleX(1.12)` from its root, 0.55 s ease-out). It then sways like fabric in a light draught (`.et-sway`, `@keyframes etSway`: `skewY` ±2.6° with a slight `scaleY` breath, 2.6 s loop, root fixed). Its shadow lifts (`drop-shadow` 1px 2px → 2.5px 4px), a light band sweeps across once (`etSheen`, 1.1 s), and the chevron leans the way the sidebar will move (`.et-nudge`, ±1.6px, `etNudge`/`etNudgeOut` depending on `.collapsed`). The chevron turns 180° when the aside is `.collapsed`. `prefers-reduced-motion` turns all of it off.
    - **Behaviour:** a click calls the app's own toggle: `.sidebar .collapse-button` (the old account-row chevron, now hidden with `display:none!important`), or `.sidebar .mobile-close` when that is visible. At ≤700px the ribbon is hidden until the drawer opens, then sits on its edge and closes it. `aria-label`/`title` flip between "Collapse sidebar" and "Expand sidebar"; a `MutationObserver` re-inserts it if the sidebar re-renders.
    - **How it was chosen (2026-11-04 to 11-05):** an animated lotus video tab was rejected (`lotus_sway_alpha.webm` is still in `mvp/`, unreferenced, and can be deleted). Then came rounds of seal and tab shapes, then satin ribbons and variations on the blue one (velvet with an embroidered lotus, wavy drape, gold clasp, layered over gold). Jainil kept the plain blue-and-gold satin ribbon ("R2").
    - **Verified (Chrome, localhost:8094 "mvp-static", 2026-11-05):** a single ribbon on the edge; collapse and expand work with the label flipping; hover runs the draw-out, sway, shadow lift and chevron lean (sampled computed transforms); at 375px it's hidden with the drawer closed and closes the open drawer; no console errors. Not checked in Safari.
    - **Moved into the React source + made fluid (2026-11-05, Jainil: "move it to the actual frontend directory… fluid movement"):** the source of truth is now `frontend/src/components/SidebarEdgeToggle.tsx` + `SidebarEdgeToggle.css`, rendered by `Sidebar.tsx` (calls `toggleCollapsed` directly, or `closeMobile` on the phone drawer; the old account-row collapse button is removed from the source). The block in these two pages is its plain-JS twin, with the CSS copied from the source file (regenerate both pages with `python frontend/scripts/sync-edge-toggle-to-mvp.py`; the JS twin lives in `frontend/scripts/edge-toggle-mvp.html`, and the script also adds `.sidebar-person .collapse-button{display:none!important}` because this bundle still has that button).
        - **Why it lagged:** each frame of the sidebar's width animation fired the perimeter-light canvas's `ResizeObserver`, which re-sampled its path 1,024 times (~44 ms, almost 3 frames' budget). Layout itself costs 1–7 ms. Fix: the light fades out while the sidebar resizes and re-measures once, 160 ms after the size settles (`SidebarOrbit.tsx`; in these pages the bundle's `let v=new ResizeObserver(m);` is replaced by a debounced wrapper; reapply after a re-export until the export carries the source fix).
        - **Why it "broke":** on expand, labels re-appeared at 80 px and wrapped, so rows jumped in height. Now `.et-resizing` (on only during the width transition) holds labels to one line, and labels fade in (`etLabelIn`, 0.28 s after 0.2 s). The width transition is 0.3 s `cubic-bezier(.4,0,.2,1)` (was 0.2 s linear-ish `ease`).
        - **Ribbon motion is compositor-only:** every moving part is an HTML layer animated with `transform`/`opacity`. Nothing animates inside the SVG, and no `filter` is animated: the hover shadow is a pre-blurred silhouette whose opacity fades. The sway, chevron lean and sheen are Web Animations, so on pointer leave they ease back to rest (0.45 s) instead of snapping, and the sheen finishes its sweep. Hover motion is skipped for touch.
        - **Verified:** in the dev app (port 3001) and on localhost:8094: toggle both ways, `.et-resizing` on during and off after, labels nowrap only while resizing, hover starts sway/lean/sheen and leave settles. The orbit patch is present. The frame rate wasn't measured live: the Claude browser pane was hidden, so it ran no animation frames.
