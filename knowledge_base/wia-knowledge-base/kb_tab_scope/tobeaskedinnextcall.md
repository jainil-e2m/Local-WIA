# To be asked in the next call

Things to clarify with WIA at the next call. Each item says what we need and why. Background is in `Action_Register_analysis.md`.

---

## 1. Pick-up for unassigned actions (Action Register)

**Context**
- Client requests are often relayed in Slack without naming anyone, for example "Dogwood let me know they want to promote their Grand Opening on the 24th."
- Decided 29 Oct (Q14): an untagged request becomes an action with no owner and goes to Needs review. An admin approves or dismisses it.

**Proposal**
- Once an admin approves an untagged action, it appears in the Action Register for **everyone affiliated with that client**: the account owner and the account team.
- **Anyone affiliated can pick it up.** One click makes them the owner, and the action history records "Picked up by …".
- Until someone picks it up, it sits in an **Unassigned** group, highlighted, with how long it has been waiting.

**To confirm**
1. Do you want pick-up, or should the admin always assign an owner at approval?
2. Who counts as "affiliated" with a client: the account owner and account team only, or anyone who has worked on the client recently?
3. Can only one person pick an action up, or can others join as collaborators?
4. If nobody picks it up, what happens? For example, remind the account owner after a set number of business days, or escalate to an admin.
5. If the action is linked to ClickUp, picking it up also sets the assignee in ClickUp. That needs the person to have connected their ClickUp account. Is that acceptable?

---

## 2. Where client requests come from (answered 30 Oct; see Action_Register_analysis.md §8)

**Context**
- In the client Slack channels, relayed requests most often name email (94) and calls (63) as their origin.
- They also name GHL/LeadLock (46), text or phone (14) and social DMs (8).
- The KB can see the original only for `hello@` email, recorded calls (Fathom) and Dubsado. Requests via GHL/LeadLock, texts, phone and DMs show up only as the Slack relay.

**To confirm**
1. Where do clients usually send requests: `hello@`, staff members' own mailboxes, texts, the GHL/LeadLock inbox, Instagram?
2. Do clients ever email staff directly? Our current decision is `hello@` only, so those emails would be missed.
3. Is it the expected practice that every client request gets posted in the client's Slack channel? If so, the Slack relay is a dependable fallback source.

---

## 3. Do you need "In progress" and "Blocked" at all? (answered 30 Oct: they track Open → Done in ClickUp)

**Context**
- In Slack, asks go from posted straight to done, or get no reply. Only about 16% of asks get a progress note, and those are mostly "will do" or "on it" when the ask arrives.
- Blockers are stated in about 2% of asks.
- ClickUp is the same: "in progress" on 6 tasks and "on hold" on 2 in the last 90 days.

**To confirm**
1. Does the Action Register need **In progress** and **Blocked**, or is **Open → Done** (plus Acknowledged) enough?
2. If you keep them, are you willing to set them in the KB by hand? The sources almost never show them.
3. Is it OK for "will do / on it" from the person asked to count as **Acknowledged**?

---

## 4. Past clients: should they be in the KB?

**Context**
- ClickUp has **43 archived client folders** that aren't in the current client list: 33 VIP Day clients, 8 Elevate clients and 2 Foolproof Follow-Up Advantage clients. The names are in a private local list (`backend/.local/past_clients.md`), not in this repo.
- Decided 29 Oct (E2M): **past clients are not backfilled** until WIA decides. Their folders show up in discovery as unmapped, and they stay out of the KB.
- A few folders look like the same client under two names. If those clients are kept, each pair is merged into one client.

**To confirm**
1. Should past clients be in the KB at all? For example, so someone can look up what was done for a returning client.
2. If yes: all of them, or only some (e.g. the last 12 months, or only Elevate)? Should they come in as archived clients, with their history loaded once and no ongoing sync?
3. If a past client comes back, is re-adding them in the KB (which reactivates their history) the expected flow?
4. Confirm the current client list: the 24 active clients, which of the 6 Foolproof Follow-Up Advantage clients are still active, and any client that's only in a programme (accelerators).

---

## 5. Access to the other mailboxes clients write to (partly answered 2 Nov: support@leadlockpro.com is Danielle's inbox, not forwarded, usually CCs hello@leadlockpro.com; access not yet granted)

**Context (from Gisselle, 30 Oct)**
- Most client requests come to `hello@` (which LeadLock syncs with both ways) and to calls.
- A smaller share goes straight to Danielle at `support@leadlockpro.com` and `hello@leadlockpro.com`, and to Carmen's own inbox for a few long-running accounts.
- Today the KB reads only `hello@weddingindustryads.com`, so those requests are invisible to it.

**To ask**
1. Can we connect `support@leadlockpro.com` and `hello@leadlockpro.com`? Who administers the leadlockpro.com mailboxes (Google Workspace or another provider), and who can approve read-only access?
2. Can we connect Carmen's inbox, read-only, limited to the client accounts she handles directly? If not, does she forward or CC those client emails to `hello@`?
3. If any of these can't be connected, we'll list them in the gap report as known blind spots. Is that acceptable?

---

## 6. Follow-ups from Gisselle's answers (30 Oct)

**Context:** Analysis §8 compares the answers with the data. About half to two-thirds of recent Slack asks have a ClickUp task. Quick, reactive asks often stay only in Slack. Recent ClickUp tasks are 15–27% unassigned.

**To ask**
1. For an ask in Slack or on a call with no ClickUp task, should the KB **suggest creating the ClickUp task** for Gisselle to approve? Quick asks like "reply to this email today" sometimes stay in Slack only.
2. After a client call, who creates the ClickUp tasks, and how soon? Do you use **Fathom's own action items** (its summary), or your own notes? If Fathom's, the KB can link each task to the moment in the call it came from.
3. What is the "forward-icon tag" in the `hello@` inbox exactly (the Gmail label's name)? We can use it as the "waiting on a team member" signal.
4. Where does the project-deadline recap live (a doc, Slack or ClickUp)? Can the KB read it?
5. Is the Monday team meeting recorded in Fathom?
6. The per-account ads split (Carmen alone, or Carmen plus Jacqueline), once confirmed with Whitney. This becomes each client's account team.
7. Once confirmed with Whitney, the turnaround targets per task type. The KB would show them as a **suggested** deadline, labelled as a target, never as a real due date.
8. **Finished statuses** (answered 2 Nov: done = onboarding, complete = client management, Closed = used by mistake, n/a = doesn't apply). The data (analysis §8.5) suggests "done" and "Closed" mean the same thing, and differ only in how the task was ticked off:
   - Danielle and WIA Support mostly use "done"; Carmen and Tina mostly use "Closed".
   - Most Closed tasks went straight to Closed, often several in the same minute.

   Questions:
   - Is there any difference, for example "Closed = reviewed by Whitney"?
   - When several tasks are closed at once, is that end-of-onboarding cleanup? If so, the close date isn't when the work was actually finished.
   - "n/a" is used for checklist steps that don't apply (e.g. referral fee, an extra reminder). Should the KB show these as "not needed", and leave them out of onboarding progress?
   - In Elevate, many tasks went from "done" to "complete" about 2–3 months later, in batches. Does that happen when a client moves from Onboarding to Elevate? If so, it gives us the date the client moved.
   - When someone marks a task complete in the KB, which status should it set in ClickUp: "done" or "Closed"? And "complete" in Elevate?

---

## 7. Gaps left in client mapping (30 Oct)

**Context:** after approving discovery, every active client is mapped in every source that applies, except the gaps below. Slack is "not applicable for now" for the 20 clients without a channel the bot is in.

**To ask**
1. **Evergreen Venues** and **SK Designs & Events** have no known email addresses: no client emails in hello@, no calendar or Fathom meetings. What are their contact emails and domains? Do they write to hello@ at all, or to a team member directly?
2. **Drive:** no client folder was found for **neu events**, **The Organic Moment Photo + Video** or **Tony Khatibi**. Do these clients have a Drive folder (what's it called, and is it shared with hello@)? Or is Drive simply not used for them?

---

## 8. Team roster and account teams (Stage 3)

**Context:** the KB needs to know who is who across Slack, ClickUp, email and Fathom, so that action owners, "awaiting our reply" and "My clients" work. A draft roster was built from Slack, ClickUp and Fathom (kept privately, not in this repo).

**To confirm**
1. **Roles:** Whitney and Daniela are the co-founders; Carmen does ads; Jacqueline does Meta ads and landing-page feedback; Tina does LeadLock copy and sequences; Danielle does technical LeadLock work; Ivy does creatives; Gisselle runs operations and support. Is that right? What is Daniela's day-to-day role?
2. **Crystal Chantel** is a ClickUp member (myfinancespa.com) but isn't in Slack. What does she do? Bookkeeping? Should she be in the KB?
3. **Shared inboxes:** is "WIA Support" in ClickUp (support@weddingindustryads.com) used only by Gisselle? Is support@leadlockpro.com used only by Danielle now (Christina Hill used it earlier in 2026)?
4. **Account owner per client:** who is the one owner of each client, the person who follows up when something is stuck? Is it Whitney for all clients?
5. **Account team per client:** the per-account ads split (Carmen alone, or Carmen plus Jacqueline), plus who covers copy, technical and creative. We'll send a pre-filled list from ClickUp assignments to confirm or correct.
6. **Former team members still assigned:** Fallon Looney is still the main assignee on Press Record's tasks (15), and Christina Hill on some Weinberg tasks. Who owns those now?

---

## 9. Follow-ups after Gisselle's round-2 answers (2 Nov)

1. **Connect hello@leadlockpro.com (read-only)?** Danielle copies it on most LeadLock-client mail, and it's the main channel for LeadLock-only clients. Who can authorise it? (It may sit in the same Google Workspace as hello@weddingindustryads.com.)
2. **LeadLock texts:** do SMS conversations from LeadLock show up anywhere we can read (hello@, Slack)? Or are they a known gap?
3. **Monday meeting recordings:** Fathom shows only about 4 "WIA Weekly Meeting" recordings since August. Who records the Monday meeting, under what title, and are those recordings shared with the Fathom team?
4. **Gisselle's Slack deadline summary:** which channel is it posted in? The bot needs to be there.
5. **Whitney:** which Slack channels should the bot stay out of (her and Daniela's private channels, finance, HR)?
6. **Whitney:** confirm Option A for the ClickUp OAuth app, since she owns the workspace. Gisselle approved it on her behalf.
7. **ClickUp "Time in Status" ClickApp:** it's off, so ClickUp keeps no status history. Would WIA turn it on (workspace Settings > ClickApps)? It would let the KB show when work started and how long tasks take. Also: 9 tasks sit in "in progress" untouched since June or earlier. Should they be cleaned up?

---

## 10. LeadLock sub-accounts with no KB client (added 5 Nov)

**Context**
- The KB's LeadLock app is installed on all 59 sub-accounts in WIA's agency (57 active; Aggieland Express and One Eleven East refused access).
- Measured 5 Nov against the KB's 24 clients:
  - 5 are mapped and collecting (the 4 pilots; Funktastic has two);
  - 16 clearly belong to KB clients that aren't mapped yet;
  - 9 are WIA's own internal, demo or template sub-accounts;
  - **29 match no KB client.** They look like LeadLock-only customers or past clients, and a few aren't wedding businesses (e.g. an electrician, a podcast company). The list is on the Connections screen, not in this file.
- Decided 5 Nov (Jainil): a LeadLock sub-account is only read once an admin maps it to a client. Unmapped sub-accounts are never read.
- **E2M's recommendation:** keep the 29 out of the KB until one becomes a WIA client. Reading them would store other businesses' leads with no client record to show them in.

**To decide**
1. Do LeadLock-only customers belong in the KB at all, now or later? If yes, as full clients or as a lighter "LeadLock-only" record?
2. Are any of the 29 actually current WIA clients missing from the client list, or past clients (see §4)?
3. Should the 2 sub-accounts that refused access be reinstalled, or are they no longer WIA's?
