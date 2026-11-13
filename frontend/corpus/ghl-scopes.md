# LeadLock / GHL — Private Integration scopes

Captured from the live scope picker in the Wedding Industry Ads sub-account
(location `Xi40zxmRvW8Pbyk5DYHp`) on 21 September 2026.

**160 of 162.** The full list is [`ghl-scopes.tsv`](./ghl-scopes.tsv) — scope
token, tab, display label. Recapture with
[`capture-ghl-scopes.js`](./capture-ghl-scopes.js).

The two unaccounted-for rows are almost certainly the picker's own "Select all"
control and a group header rather than real scopes. Nothing in the gap can be
email-related: the whole `emails/*` family is present and consistent.

---

## What the Content Atelier uses

```
emails/campaigns.readonly    sent campaigns
emails/schedule.readonly     scheduled + sent sends, and their ids
emails/stats.readonly        open and click rates
emails/templates.readonly    templates
emails/builder.readonly      builder payload — "View Email Templates"
campaigns.readonly           generic campaigns, distinct from emails/campaigns
locations.readonly           confirms the location resolves
contacts.readonly            list size and engagement context
```

Every `.write` in the email family is deliberately excluded.
`emails/campaigns.write` and `emails/schedule.write` would let the token create
and schedule sends, which is exactly the boundary the Atelier is built around.
Adding write is a product decision — open question #4 in `Content_Atelier.md` —
not a permissions detail. See [`emails/README.md`](./emails/README.md).

---

## Things worth knowing about this tenant

**It is running ahead of the public docs.** HighLevel publishes ~124 scopes.
This tenant exposes 162, and the extras are not minor: a **Voice AI** suite
(`voice-ai-agents`, `voice-ai-agent-goals`, `voice-ai-dashboard`), **Agent
Studio**, **Knowledge Bases**, **Brand Boards** and **Conversation AI**. Do not
conclude an API surface is unavailable because the published scope list omits
it — check the picker.

**Suffixes are not uniform.** Most scopes end `.readonly` / `.write`, but the
tenant also has `.read` (`numberpools.read`, `phonenumbers.read`,
`saas/location.read`, `twilioaccount.read`) and `.create` (`pipelines.create`).
Anything parsing these should not assume two forms.

**Some labels were never localised.** `emailsstatsreadonly`, `pipelinescreate`,
`chatwidgetreadonly` and similar are the scope name with its punctuation
stripped, sitting where a human label should be. The scopes are real and they
work.

**Hyphens are part of the resource name.** `voice-ai-agents.readonly`,
`knowledge-bases.readonly`, `countdown-timer/timer.readonly`,
`payments/custom-provider.write`. An earlier capture assumed `[A-Za-z0-9_]` and
truncated about 24 tokens — worth remembering if anything here ever parses a
scope string again.

**`socialplanner/post.readonly` may close the Instagram gap.** The Atelier
records Instagram as "not granted" because we hold five public post URLs and no
Business Suite seat. If WIA's Instagram is connected through LeadLock's Social
Planner, that scope reaches the captions directly, and
`socialplanner/statistics.readonly` would add performance on top. Cheap to tick
and probe — it would remove the dependency on Meta entirely.

---

## Families at a glance

For orientation only; the TSV is the reference.

| Family | Relevant to the Atelier |
|---|---|
| `emails/*` + `campaigns` + `lc-email` | **Yes** — the eight above |
| `socialplanner/*` | Possibly, for Instagram |
| `conversations/*` | Not yet — a candidate Slack-adjacent surface |
| `locations/*` | `locations.readonly` only |
| `payments/*`, `invoices/*`, `products/*`, `store/*` | No |
| `calendars/*`, `blogs/*`, `funnels/*`, `forms`, `surveys` | No |
| Voice AI, Agent Studio, Knowledge Bases, Brand Boards, Conversation AI | No, but note they exist |
