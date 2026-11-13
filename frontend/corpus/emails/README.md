# Email corpus — intake

Approved WIA marketing emails, captured from LeadLock (the white-label GHL
tenant, location `Xi40zxmRvW8Pbyk5DYHp`). This is the **shape** layer for
[`prompts/marketing-email.md`](../../prompts/marketing-email.md) — what teaches
the model the form.

Nothing here is generated. Every file is something that actually went out.

---

## What we need, per email

| Field | Where it is in LeadLock | Why it matters |
|---|---|---|
| Campaign title | Campaigns list | Carries subject + date + CTA in one string |
| **Subject as sent** | Open the campaign → Settings | May differ from the campaign title |
| **Preview / preheader** | Same screen | Voice card §3 has a slot for it and we have no data |
| **Body, plain text** | Preview URL → select all → copy | The corpus itself |
| CTA button label | In the body | — |
| CTA destination URL | Button settings | **Fills the offer map gap** — the one thing blocking every generated CTA |
| Send date | Execution Date column | Cadence |
| Open % / click % | **Statistics tab** | Which subjects and CTAs actually worked |
| Source session | Whitney or Giselle only | The input→output pairing. Nobody else can supply this |
| Instagram sibling | Whitney or Giselle only | Every email has one. It is the derivation rule |

The last two are the ones that cannot be scraped. They are also the two that
make the corpus worth more than a style guide.

---

## Three ways to get the bodies out

Ranked by effort. Any of them works; pick one and stay consistent.

### A · Preview URL → copy-paste *(lowest effort, start here)*

Each campaign has a preview URL of the form
`backend.leadconnectorhq.com/emails/schedule/preview/{location}/{id}`.

Open it, select all, copy, paste into a file below. Plain text is fine and
preferred — the HTML wrapper is template chrome, not voice.

### B · Print to PDF

Preview URL → Print → Save as PDF. Slower to read back, but it preserves
layout and button placement, which matters if we later want to study structure
visually. Drop the PDFs in this folder and I will extract them.

### C · GHL API — Private Integration Token

Not blocked on anything external. A **Private Integration Token (PIT)** is a
long-lived API v2 key you create yourself from inside the tenant, with no OAuth
app and no marketplace submission.

**Path:** sub-account → **Settings → Private Integrations → Create new
integration** → name it, tick scopes, generate. *The token is shown once.*

Agency admins can create PITs by default. The permission is restrictable per
role under Settings → Team → Roles and Permissions, at two levels — the
agency's own private integrations, and its sub-accounts'.

**Scopes to tick.** Read off the live picker on 21 Sep 2026 — the tenant
exposes 162, and these are the ones this integration needs. Note that `emails`
is a *family* of five separate scopes, not one:

```
emails/campaigns.readonly    the sent campaigns
emails/schedule.readonly     scheduled + sent sends, and their ids
emails/stats.readonly        open and click rates
emails/templates.readonly    templates
emails/builder.readonly      "View Email Templates" — the builder payload
campaigns.readonly           generic campaigns, distinct from emails/campaigns
locations.readonly           confirms the location resolves
contacts.readonly            list size and engagement context
```

Deliberately NOT ticked: every `.write` in the family. `emails/campaigns.write`
and `emails/schedule.write` would let the token create and schedule sends,
which is precisely the boundary the Atelier is built around. Add
`emails/campaigns.write` only if drafting back into GHL is agreed — that is
open question #4 in `Content_Atelier.md`, not a permissions detail.

`emails/stats.readonly` is the one worth noticing: it makes open and click
rates reachable programmatically, so the corpus can record which subjects and
CTAs actually worked rather than only what was written.

**Auth.** API v2 needs both headers. White-labelling changes the UI domain, not
the API host — it stays `services.leadconnectorhq.com`.

```bash
curl -s "https://services.leadconnectorhq.com/locations/Xi40zxmRvW8Pbyk5DYHp" \
  -H "Authorization: Bearer pit-XXXXXXXX" \
  -H "Version: 2021-07-28"
```

**Then probe whether it returns bodies.** Statistics are confirmed reachable
(`emails/stats.readonly` exists as a scope). What is **still unconfirmed** is
whether any endpoint returns the email **body/HTML** of a sent campaign, or
only metadata — id, name, status, dates. Probe before committing:

```bash
curl -s "https://services.leadconnectorhq.com/emails/schedule?locationId=Xi40zxmRvW8Pbyk5DYHp&limit=20" \
  -H "Authorization: Bearer pit-XXXXXXXX" \
  -H "Version: 2021-07-28" | head -c 3000
```

If it returns only metadata, the API still earns its keep — it gives you every
**campaign id**, and the preview URL is a predictable template:

```
backend.leadconnectorhq.com/emails/schedule/preview/{locationId}/{campaignId}
```

Which makes option A a loop over ids rather than twelve manual copy-pastes.

**If the Private Integrations menu is not there**, it is one of two things, both
on the LeadLock side: the agency plan tier does not include API access, or the
permission is switched off for sub-account users. Neither is fixable from
inside WIA — see the ask in `_INDEX.md`.

**Also worth grabbing while you are in there:**
- The **Statistics** tab — open and click rates per campaign
- The **Templates** tab — if the emails share a template, its structure is a
  constraint on everything we generate
- Scroll the Campaigns list past the fold — `_INDEX.md` only covers what was
  visible in one screenshot

---

## File format

One file per email, named `YYYY-MM-DD-slug.md`. Copy `_TEMPLATE.md`.

Do not clean up the copy. Typos, odd line breaks and inconsistent capitalisation
are signal — they are part of how she actually writes.

If a field is unknown, write `unknown`. Do not guess and do not leave it blank;
a blank reads as "none" and an empty preheader is a real finding we would then
get wrong.
