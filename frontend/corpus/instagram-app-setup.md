# Instagram — Meta Graph API setup

Read access to `@weddingindustryads` — captions, carousel slides and reel
metadata for the voice corpus.

The 21 September handover supplied **five public post URLs**. Five approved
captions is too thin to derive a voice card from, and it reaches none of the
carousel structure. This is the integration that reaches the whole back
catalogue.

Handle recovered from the email footer chrome:
<https://www.instagram.com/weddingindustryads>

---

## Who does what

Most of this is WIA's, because the app has to be created by someone who
administers the Instagram account.

| Step | Who | Why |
|---|---|---|
| 0 · Confirm the account is **Business or Creator**, not Personal | **WIA** | The API cannot see a Personal account at all. This is the one thing that can stop the whole route |
| 1 · Create the Meta app | **WIA or E2M** | Whoever creates it becomes admin. Simpler if WIA does it on the `ai@` identity |
| 2 · Add the Instagram product and permissions | **E2M** | Mechanical |
| 3 · Generate the token, exchange for long-lived | **E2M** | Needs a login as someone who administers the account |
| 4 · Send back the token and the IG user id | **E2M → `.env`** | — |

**No App Review is needed.** App Review applies to apps reading *other people's*
accounts. An app in Development mode can read the accounts of its own admins,
developers and testers — which is exactly this case, because WIA owns the
account and will be the app admin. Skipping review is the difference between
same-day and several weeks.

---

## 0 · The prerequisite that decides everything

In the Instagram app → **Settings → Account type and tools**.

- **Business** or **Creator** → proceed.
- **Personal** → nothing below works. Switching is free, reversible, and does
  not affect existing posts or followers, but it is Whitney's call and she
  should make it knowingly.

While there, note whether the account is linked to a **Facebook Page**. It
decides which of two routes to take in step 2, and both are fine.

---

## 1 · Create the app

<https://developers.facebook.com/apps> → **Create App**.

- **Use case:** `Other` → **Type:** `Business`
- **Name:** `WIA Content Atelier`
- **Contact email:** `ai@weddingindustryads.com`

Leave it in **Development** mode. It never needs to go Live.

---

## 2 · Add the Instagram product

Two routes. Pick by what step 0 found.

### Route A — Instagram API with Instagram Login *(preferred)*

No Facebook Page required. Fewer moving parts, and it does not break if the
Page link is ever removed.

Dashboard → **Add Product** → **Instagram** → **API setup with Instagram
business login**.

Permissions:

| Permission | Why |
|---|---|
| `instagram_business_basic` | The media list itself — captions, permalinks, timestamps, carousel children |
| `instagram_business_manage_insights` | Reach, saves and shares per post. Optional, and worth having — see below |

### Route B — Instagram API with Facebook Login

Use when the account is already firmly wired to a Page and nobody wants to
touch that wiring.

Dashboard → **Add Product** → **Facebook Login**, then the Instagram product.

Permissions: `instagram_basic`, `pages_show_list`, `pages_read_engagement`,
and `instagram_manage_insights` if you want the metrics.

### Why insights are worth the extra permission

The email corpus made the case. `corpus/emails/README.md` lists open and click
rate as a wanted field precisely because it tells you *which subjects and CTAs
actually worked* — a corpus of approved content teaches form, but a corpus of
approved content with performance attached teaches judgement. Saves and shares
are the Instagram equivalent, and a carousel's save rate is the closest thing
to a quality score WIA has.

It is optional. Nothing in the fetcher depends on it.

---

## 3 · Generate the token

**Graph API Explorer** — <https://developers.facebook.com/tools/explorer>

1. Select the app. Select **User Token**. Tick the permissions from step 2.
2. **Generate Access Token** → log in as someone who administers the Instagram
   account → grant.
3. That token is **short-lived — one hour.** Do not stop here.

Exchange it for a long-lived token (60 days):

```
GET https://graph.facebook.com/v21.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id={app-id}
  &client_secret={app-secret}
  &fb_exchange_token={short-lived-token}
```

Then find the Instagram user id:

```
GET https://graph.facebook.com/v21.0/me/accounts?access_token={long-lived}
GET https://graph.facebook.com/v21.0/{page-id}?fields=instagram_business_account&access_token={long-lived}
```

On Route A the id comes straight back from `/me` and these two calls are
unnecessary.

**The 60-day clock is a real operational fact, not a footnote.** Whoever runs
the backfill should run it in the same week the token is issued. A long-lived
token can be refreshed before it expires; one that has already expired cannot,
and step 3 has to be repeated.

---

## 4 · What to send back

Into `.env` — never into git, and `.env.example` carries the names only:

```
IG_TOKEN=
IG_USER_ID=
```

Then:

```bash
node --env-file=.env corpus/fetch-instagram.mjs
```

---

## What this reaches

| Asset | Reached | As |
|---|---|---|
| **Captions** | Yes — every post | Text. This is the prize |
| Post metadata | Yes | Permalink, timestamp, type, and the engagement counts |
| **Carousel slides** | Yes — as images | `children` gives one image per slide, in order. **The copy is burned into the JPEG** |
| **Reels** | Metadata and caption only | The video file. **The script is spoken audio** |
| Insights | With the optional permission | Reach, saves, shares |

## What it does not reach

**Stories are gone.** The `/stories` edge returns the last 24 hours and nothing
else. Every story WIA has ever published is unrecoverable through this API.
That matters because Stories was named twice on 16 September as an output
surface — as caption scripts, and as where the Slack screenshots get placed.
The Atelier can still *write* story copy; it just cannot learn from any that
already went out.

**Carousel copy is not text here, and reel scripts are not text anywhere on
Instagram.** Both are the reason `canva-descript-access.md` exists. Instagram is
the right source for captions and the wrong source for the other two — going
after them here means OCR on every slide and a speech-to-text provider that is
still the component's open blocker.

---

## Verifying it works

```bash
curl -s "https://graph.facebook.com/v21.0/{ig-user-id}/media?fields=id,caption,media_type,timestamp,permalink&limit=5&access_token={token}"
```

Five recent posts with captions means the route is good. Two things to check
that a naive test misses:

- **`media_type` distribution.** If everything comes back `IMAGE` and nothing
  is `CAROUSEL_ALBUM`, the `children` field is not being requested and the
  carousel structure is silently absent.
- **Pagination.** The default page is 25. A run that reports "25 posts" has
  almost certainly not walked `paging.next`. The fetcher does; a curl test does
  not.

---

## Notes

The app stays in Development mode permanently. It reads one account — the one
belonging to its own admins — and that is precisely the case Development mode
covers. Going Live would require App Review and buy nothing.

Every call the fetcher makes is a `GET`. There is no publishing path, no
comment or reply capability, and no permission requested that would allow one.
That is the same boundary the Slack app holds, and for the same reason: this
component drafts copy for a person to place, and nothing in it posts.
