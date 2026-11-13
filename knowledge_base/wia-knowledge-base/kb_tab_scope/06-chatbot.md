# Tab 6 — Client 360 (chatbot)

**Status:** Draft · N1–N4 decided, N2 revised 22 Oct (sidebar tab only) · 22 Oct 2026 · Unsequenced (delivery position open [Agreed])
**Labels:** **[Agreed]** = already decided (KB-CH-43/44/59/68, chatbot_KB.md, FR-CHT). **[Proposed]** = new in this draft. **[Finding]** = from sources.

`chatbot_KB.md` already defines what the assistant must do correctly (question types, answer rules, privacy, cost). This document decides **what the user sees and does**: the tab, its parts, and where it lives.

---

## 1. What this tab is for

**One question:** *Ask anything about our clients and get a cited answer, without clicking through every tab.*

It's a conversation on top of the same records, evidence and permissions as the rest of the KB [Agreed]. It answers, explains, finds evidence and suggests; it does not change records by itself [Agreed: initially read-only].

**What WIA does today [Finding]:** Whitney asks Viktor in Slack: "how are things going with this client?", "remind me about this situation", "everything outstanding" (Carmen). The history is buried in long Slack threads, so she asks instead of searching. Complaints: verbose; lives in Slack threads; not owned. The tab must be **short, cited, organised and owned**.

---

## 2. Name [Decided, N1: Client 360]

**Client 360**: it sees the whole client from every side. Also considered:

| Option | Why | Concern |
|---|---|---|
| **Ask the Brain** | Whitney's own phrase: "We have the agency brain" (discovery call). Instantly understood internally | Informal |
| **Ask WIA** | Plain, branded | Could be confused with asking the team |
| **Concierge** | Matches the product's warm, wedding-industry tone | Less obvious what it does |
| **Ask Client Knowledge** | Matches the product name ("Client Knowledge") | Long |

Sidebar placement: under THE CLIENT DESK, after Health & sentiment. It is reached **only from the sidebar**: no header button and no keyboard shortcut (N2, revised 22 Oct). Other names considered later: Maid of Honour, The Little Black Book, Know-It-All.

---

## 3. One way in [Decided, N2 revised 22 Oct: single sidebar tab]

| Surface | When | Behaviour |
|---|---|---|
| **The tab** (full page, sidebar) | Any question: quick checks, longer research, going back to old conversations | Thread list + conversation + "what I looked at" panel. You set the client and period in the scope bar |

Client 360 is **one chatbot view in the sidebar**. It does not appear on other screens:
- No side panel on every screen, and no header button or `Ctrl/⌘ J` shortcut.
- No *Ask about this* buttons on the client record, action drawer, call brief, Health card or evidence drawer.

**Why:** the other tabs stay focused on their own job, and there is one place to ask, with one thread list. **Trade-off:** a question about a specific action or call starts without that record attached, so you name it in the question or pick the client in the scope bar.

---

## 4. Who uses it

| Person | Typical questions |
|---|---|
| Whitney | "How are things going with Bloom?" · "What did we agree with Dana about winter tours?" · "Bring me up to speed before the strategy call" |
| Carmen / Jacqueline | "Everything outstanding for Magnolia" · "Did the conversion-tracking fix stick?" · "What's assigned to me this week?" |
| Gisselle | "Which clients are waiting on a reply from us?" · "Who hasn't acknowledged their tasks?" |
| Danielle | "What CRM does Harbor use?" · "What did Elise say about the LeadLock setup?" |
| New hire | "What does this business do and what are we helping them achieve?" |

---

## 5. The tab: layout

```
┌──────────────┬─────────────────────────────────────────┬──────────────────┐
│ Conversations│  Scope bar: [Bloom Manor ▾] [All time ▾] │ What I looked at │
│ + New        │                                         │ (sources, counts,│
│ Today        │  Conversation                            │  freshness,      │
│  · Bloom prep│   ┌ You: What did Sarah ask last week? ┐ │  gaps)           │
│ This week    │   └──────────────────────────────────┘ │                  │
│  · Overdue   │   ┌ Answer card ─────────────────────┐ │                  │
│ Older        │   │ status · answer · [1][2] · gaps  │ │                  │
│              │   └──────────────────────────────────┘ │                  │
│              │  Composer: Ask…  @client #action /brief │                  │
└──────────────┴─────────────────────────────────────────┴──────────────────┘
```

### 5.1 Conversation list (left)
| Component | Notes | Status |
|---|---|---|
| **New conversation** | Starts empty or with the current scope | Proposed |
| Threads grouped Today / This week / Older | Title auto-named from the first question; rename | Proposed |
| **Scope chip per thread** | "Bloom Manor" or "All my clients", so you know what it was about | Agreed (explicit scope) |
| Search threads | Your own threads only | Proposed |
| Delete | Your own threads; retention by admin policy [Agreed Q16] | Agreed |
| Privacy note | "Only you can see your conversations. Admins see usage, not content." [Agreed Q15] | Agreed |

### 5.2 Scope bar (top of the conversation) [Agreed: visible, pinned scope]
- **Client(s):** one, several, or *All my clients* (only clients you can access).
- **Engagement:** all / Elevate / LeadLock… (when the client has several).
- **Period:** all time / since last call / last 30 days / custom.
- **Sections:** Actions, Meetings, Profile, Health, Support, Finance (**admins only**, F2).
- **Freshness line:** "Answering from the KB as of 9:42 AM" (or "checking live sources" if that mode is chosen after testing [Agreed: test-dependent]).
- **Scope never changes silently.** If you pick another client in the scope bar while a thread is about Bloom, it asks "This conversation is about Bloom Manor. Switch to Harbor House or start a new one?" [Agreed].

### 5.3 Empty state
- **Suggested questions**, personalised to the viewer and today: "Prep me for my 2:00 PM Bloom call", "What's overdue for my clients?", "What has Maya asked that we haven't answered?"
- **By category** (from chatbot_KB.md §3): Client background · Last call · Actions & who owes what · Find evidence · Handover · Concerns & support · Lead outcomes · Definitions.
- **Definitions** answered instantly without AI: "What does Verified mean?", "How is the health category set?" [Agreed: FAQ/direct answers, KB-CH-44].

### 5.4 Composer
| Feature | Example | Status |
|---|---|---|
| Free text | "What changed since the last strategy call?" | Agreed |
| **@ mention** a client or person | "@Bloom Manor", "@Jacqueline" | Proposed |
| **# attach** a record | "#Send the revised landing page" | Proposed |
| **/ shortcuts** | `/brief` (call prep) · `/handover` · `/recap last call` · `/owed` · `/define` | Proposed |
| Stop | Cancel a long answer [Agreed FR-CHT-17] | Agreed |

### 5.5 Answer card [Agreed answer contract, Proposed look]
| Part | Content |
|---|---|
| **Status chip** | Answered · Partial · Need to clarify · No evidence · Unavailable · Conflict [Agreed result categories] |
| **Scope line** | "Bloom Manor · Elevate · last call: Sep 30 strategy call" |
| **Direct answer** | Short by default (the verbosity lesson). *More detail* expands |
| **Labels** | Each paragraph marked *Fact* / *Interpretation* / *Suggestion* [Agreed] |
| **Inline citations** | [1] [2] → source list with author, date, locator (timestamp, message, sheet range); click opens the evidence drawer [Agreed] |
| **Gaps & conflicts** | "No transcript for the Oct 8 office hours." "ClickUp says Oct 12; the call said Oct 8 (meeting wins)." [Agreed] |
| **Links** | Open the action / client tab / call brief |
| **Follow-ups** | 2–3 suggested next questions |
| **Reuse note** | "Same answer as 10:01; sources unchanged since then" when a cached answer is reused [Agreed: cache never makes old evidence look new] |
| **Feedback** | 👍 / 👎 + reason ("wrong client", "missing info", "too long") → QA review [Proposed] |
| **Copy** | Copies the answer with its citations |

**Clarification** shows as buttons, not a paragraph: "Which call? · Sep 30 strategy call · Oct 8 office hours".

**Progress** for longer answers: "Finding the last call… checking actions… reading the transcript" with Stop.

### 5.6 What I looked at (right panel)
Records and sources consulted (counts and dates), freshness per source, what was out of reach ("LeadLock data unavailable", "no transcript"), and **not** anything you don't have access to. Collapsible; hidden on small screens behind a "Sources" button.

### 5.7 What the assistant can do beyond answering [Decided, N3: strictly read-only]
The assistant **answers, explains, cites and links. That's all.** It has no buttons that create tasks, draft messages or change anything.

| It does | It doesn't |
|---|---|
| Answer with citations | Add tasks, even as proposals |
| Link to the record (action, client tab, call brief, Handover brief) so you act there | Draft emails or Slack messages |
| Suggest next steps **in words**, labelled *Suggestion* | Change owners, dates or status; acknowledge or verify |
| | Send anything |

If a user asks "add this as a task", it explains it can't and links to the place to do it (e.g. the Action Register's *Add an action*). Writing actions can be revisited later [Agreed: initially read-only].

---

## 6. Rules the user will notice [Agreed, from chatbot_KB.md]

- "Last call" means the last **completed** relevant call with content; it says which one, and asks when it matters.
- Counts come from the records, not from how many passages it found ("You have 3 overdue items" is a real count).
- It says **"I couldn't find that"** rather than guessing; and distinguishes "no evidence" from "no access" without revealing hidden clients.
- A conversation never becomes a client fact by itself.
- Finance answers only for admins [F2]; no website or other unapproved sources [Agreed].
- Viktor's past posts can be cited as *Viktor's analysis*, never as client words [Agreed].

---

## 7. Possible additions

| Addition | Value | Dependency | Suggest |
|---|---|---|---|
| ~~Side panel + Ask-about-this buttons~~ | Use it where the work is | — | **Dropped** (N2 revised 22 Oct): one sidebar tab only |
| **Suggested questions** (personalised) | Fast start, teaches what to ask | — | Not in first version (N4); a plain category list stays on the empty state |
| **Slash shortcuts and @/# mentions** | Speed for daily users | — | Not in first version (N4) |
| **Answer feedback** → QA | Improves quality; catches wrong answers | Review owner | Not in first version (N4). Note: QA then relies on test sets only |
| **Pin / save an answer** | Keep "Bloom background" handy; pinned answers show when their sources change | — | **First version (N4)** |
| **Morning digest link** ("Ask about today") | Ties into Call Prep digest | C4 digest | Low |
| **Voice input** on phones | Ask between calls | Browser speech | Low |
| **Ask in Slack** (DM the KB) | Where Whitney already asks Viktor | External channel, **out of current scope** [Agreed] | Later |
| Shared threads | Team research | **Excluded for now** [Agreed Q15] | Out |
| Admin reading conversations | — | **Excluded** [Agreed Q15] | Out |

---

## 8. Phone and tablet

The tab becomes a single column; thread list behind a back arrow; citations as tappable chips; the "What I looked at" panel behind a *Sources* button [Agreed: responsive].

---

## 9. Data readiness

The chatbot only works as well as the records under it: everything in Tabs 1–5. Open items that affect it: LeadLock outcomes (H6), Zoom history, KB-only vs live-read mode (to test), model/route selection (hybrid vs Viktor-led, to test) [Agreed].

---

## 10. Decisions

| # | Decision | Outcome |
|---|---|---|
| N1 | Tab name | **Client 360.** Sidebar label *Client 360* |
| N2 | Where it appears | **Revised 22 Oct: a single sidebar tab only.** The side panel on every screen, the header button / `Ctrl/⌘ J` and the *Ask about this* buttons were dropped (previously: full tab + side panel + *Ask about this* buttons) |
| N3 | Beyond answering | **Strictly read-only.** Answers, citations, links and worded suggestions only |
| N4 | First-version extras | **Pin answers.** Suggested questions (personalised), slash shortcuts/mentions and answer feedback are not in the first version |

**Effect of N4 on §5:** the composer is plain text (no `/` or `@`/`#`, and no attached-record chip since N2 was revised); the empty state shows the question categories and definitions, not personalised suggestions; the answer card has no 👍/👎 (wrong answers can still be reported to E2M as a technical issue). Pinned answers get their own list above conversations.

---

## 11. Mockup coverage (22 Oct)

Mockup: `frontend/exports/client-portfolio.html#assistant`, reached from the sidebar only. Built from `src/views/Client360.tsx` and `Client360.css`. Answers come from a **rule-based mock engine over the sample records**, not a language model: it shows the intended answer shape, citations and boundaries, not real AI quality.

| In the mockup | Not in the mockup yet |
|---|---|
| **Tab:** pinned answers (one flagged "Sources changed" with Refresh), conversations grouped Today / This week / Older with client chip, search, delete, privacy note; scope bar (client, period, sections, "Answering from the KB as of"); empty state with 8 question categories; composer; *What I looked at* panel | Real period filtering; retention settings |
| Removed 22 Oct (N2 revised): header button and `Ctrl/⌘ J`, side panel, all *Ask about this* buttons | — |
| | **Scope safety** prompt ("New conversation about it / Switch this one"): it was triggered from *Ask about this*, so it isn't reachable in the mockup now |
| **Answer card:** status (Answered, Partial, Need to clarify, No evidence, Unavailable), scope line, summary, Fact / Interpretation / Suggestion / Definition labels, numbered citations opening the evidence drawer, *More detail*, gaps, links, follow-ups, pin | Conflict example; reuse ("same answer as 10:01") note |
| **Behaviours shown:** last-call clarification buttons; outstanding items counted from the full register; client's own words; health "why"; prep from the call brief; lead outcomes or *Unavailable*; background from the Marketing Profile; glossary definitions without AI; **read-only refusal** with links; **finance refused for non-admins**; **website refused**; "I couldn't find that" instead of guessing | Live-read mode; real model routing |
| Progress steps with **Stop** | — |
