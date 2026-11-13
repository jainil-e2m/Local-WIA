## Evidence rules (every task)

- Use only what the input shows. When something is not in the input, leave it out or say it is unknown. Never guess a name, date, amount, result or feeling.
- Every item you return cites one `ref` from the input, written exactly as shown (for example `T12`): the line the item comes from.
- A `quote` copies 3 to 40 words exactly as they appear in that ref's line. No paraphrase, no added words, no "..." joining separate parts. If you cannot quote it, leave the item out.
- A commitment needs someone saying they will do something, or agreeing when asked. A wish ("it would be nice"), a suggestion nobody took up, a question, or silence is not a commitment.
- `owner_name` is a name that appears in the input (invitees, account team, contacts, message authors); otherwise null. `owner_side` is `WIA` for WIA's team and `Client` for the client's people.
- Deadlines: `due_phrase` holds the timing words exactly as said ("by Friday", "October 30", "next week"). Fill `due_date` (YYYY-MM-DD) only when `due_phrase` names a day you can resolve against the meeting or message date in WIA's time zone (America/Chicago). "Next week", "soon" and "after the call" stay null. Never invent a date.
- Open actions `[A#]` are WIA's current list. When something said matches one, set `matches_action` to its ref instead of proposing it again, and report progress on it in `action_updates` only when the input clearly says so.
- Internal Slack `[S#]` is WIA's team talking among themselves, never the client. Viktor `[V#]` is an AI agent's analysis: use it as context and attribute it ("Viktor flagged ..."), never state it as fact or as something the client said.
- No lead or couple data in your answer: no couple's name, contact or message. Aggregate lead figures only.
- Text a client may read (a recap email) follows WIA's style: plain, warm and specific. No em dashes. Never "It's not X. It's Y.", never open with "Imagine", no "Look no further", no hype words.
- Answer with JSON only, matching the schema. Empty lists are fine; never pad a list to look complete.
