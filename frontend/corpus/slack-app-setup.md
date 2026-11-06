# Slack app — setup

Read access to the three channels the Content Atelier watches:

`#google-search-accelerator` · `#meta-ads-accelerator` · `#social-proof-and-results`

The 21 September handover added a person to those channels. **Membership is not
an integration** — reading them programmatically needs an app with a bot token.
This is that app.

---

## Who does what

You are already a member of the workspace, so most of this is yours. Only two
steps need someone at WIA.

| Step | Who | Why |
|---|---|---|
| 1 · Create the app from the manifest | **E2M** | Any workspace member can create an app |
| 2 · Approve the install | **WIA — workspace owner or admin** | Most workspaces require admin approval before an app can be installed |
| 3 · Install to workspace, copy the bot token | **E2M**, after approval | Token is shown once |
| 4 · **Invite the bot to each of the three channels** | **WIA or E2M** — anyone in the channel | The step everyone forgets. A bot token sees nothing until the bot joins |
| 5 · Confirm whether the channels are private | **WIA** | Changes which scopes are actually needed |

If WIA's workspace has app installation open to all members, steps 2 and 3
collapse into one and nothing is needed from Whitney at all beyond step 4.

---

## 1 · Create the app

<https://api.slack.com/apps> → **Create New App** → **From an app manifest** →
pick the Wedding Industry Ads workspace → paste this:

```yaml
display_information:
  name: Content Atelier
  description: Read-only reader for WIA's content signal channels.
  background_color: "#1f2937"
  long_description: >-
    Watches three channels for moments worth turning into marketing content —
    client results, screenshots of client emails, and feedback relayed from
    office hours. It reads messages, files and emoji reactions in the channels
    it has been invited to. It cannot post, reply, or send anything, and it has
    no access to direct messages or to any channel it has not been added to.
features:
  bot_user:
    display_name: Content Atelier
    always_online: false
oauth_config:
  scopes:
    bot:
      - channels:history
      - channels:read
      - groups:history
      - groups:read
      - files:read
      - users:read
      - reactions:read
settings:
  org_deploy_enabled: false
  socket_mode_enabled: false
  token_rotation_enabled: false
  interactivity:
    is_enabled: false
```

**Note what is not in there.** No `chat:write`, no `im:write`, no event
subscriptions, no request URL. Reasons below.

---

## 2 · The scopes, and why each one

| Scope | What it buys |
|---|---|
| `channels:history` | The messages themselves, in public channels |
| `channels:read` | Channel names and ids, so the three can be resolved by name |
| `groups:history` · `groups:read` | The same, for **private** channels |
| `files:read` | The screenshots Whitney drops into `#social-proof-and-results`. Without this we get a message saying a file exists and nothing else |
| `users:read` | Resolves `U01ABC` to "Jacqueline", so relayed feedback is attributable |
| `reactions:read` | Lets a single emoji be the flag that marks a message content-worthy — open question #1 in `Content_Atelier.md` |

### Threads need no extra scope

`conversations.history` returns **parent messages only** — a client quote
relayed as a thread reply is invisible to it, and it fails as absence rather
than as an error.

The fix is not a permission. `conversations.replies` takes the **same**
`*:history` scopes as `conversations.history`; threads are a second endpoint,
not a second capability. So the ingest must walk threads — one extra call per
message with `reply_count > 0` — and the app config stays exactly as it is.

`probe-slack.mjs` calls `conversations.replies` rather than assuming, so the
run output confirms it on the live token instead of taking this on trust.

The same goes for message permalinks: `chat.getPermalink` needs no scope beyond
seeing the channel, so linking a candidate back to its original Slack message
for provenance is free.

**All three target channels are private — confirmed by WIA, 22 September.** So
`groups:history` and `groups:read` are not speculative, they are the two scopes
the whole integration rests on. Do not trim them.

`channels:history` and `channels:read` are, by the same token, currently unused.
They stay: removing them is a scope change and a reinstall for no gain, and the
first public channel anyone wants read would put them straight back.

### Why no write scopes

`chat:write` and `im:write` would let the Atelier post drafts back to Giselle or
DM Whitney with a question. Both are **open product decisions** — questions #2
and #4 — not permissions details, and requesting them now would mean asking for
the ability to message the team before deciding whether it should.

Adding them later is an edit plus a reinstall on the **same app** — no new app,
no new bot user, no re-inviting to channels. Cheap, but not free: it costs an
admin re-approval. See *Changing this later* below.

### Why no Events API

The obvious design is Slack pushing events to a URL on Railway. That needs a
public HTTPS endpoint, URL verification, signing-secret validation and an app
that is reliably up.

For Phase 1, **polling `conversations.history` on a schedule is simpler and
gives up nothing**: these channels see a handful of messages a day, the Atelier
is not real-time, and Whitney is the selector anyway. No public URL, no signing
secret, no inbound surface at all. Revisit if latency ever matters.

---

## 3 · Install and collect the token

After approval: **Install to Workspace** → authorise → copy the **Bot User OAuth
Token** from *OAuth & Permissions*. It starts `xoxb-` and is shown once.

Into `.env` as `SLACK_BOT_TOKEN`, and into LastPass.

---

## 4 · Invite the bot to each channel

**This is the step that gets missed**, and it fails silently — the API returns
an empty history rather than an error.

In each of the three channels:

```
/invite @Content Atelier
```

Or: channel name → Integrations → Add apps.

---

## 5 · What to send back

Answered 22 September except where noted.

| | |
|---|---|
| Bot token, via LastPass | ✓ done |
| Bot is in all three channels | **outstanding** — currently the scratch channel only |
| Are any of the three private | ✓ **all three are private.** See the scope note above |
| Does signal ever arrive by DM | ✓ no — anything that lands in a DM gets forwarded into one of the three channels, so `im:history` is not needed |

**On that last one.** The forwarding is a human habit, not a technical
guarantee: a DM nobody reposts is invisible to the Atelier, and it will look
like it never happened rather than like it was missed. Not a blocker, and not
worth a scope to fix — but it makes the three channels the single point of
capture, which raises the stakes on the missing `social-proof-and-results`
rather than lowering them.

---

## Verifying it works

```bash
node --env-file=.env corpus/probe-slack.mjs
```

Lists the channels the bot can actually see, pulls a few recent messages from
each, and reports whether files and reactions come through. Same pattern as the
GHL probe: confirm the surface before building against it.

Pass a channel name to test somewhere harmless first:

```bash
node --env-file=.env corpus/probe-slack.mjs wia-ai-team-testing
```

### Verified 22 September 2026

Run against a private scratch channel, `#wia-ai-team-testing`. Everything
technical is confirmed on the live token:

| | |
|---|---|
| `groups:history` · `groups:read` | ✓ private channel read cleanly |
| `files:read` | ✓ downloaded a real 1080×1080 WebP, not a login page |
| `reactions:read` | ✓ surfaced `exploding_head` |
| Threads | ✓ `conversations.replies` works on the same scopes. 3 of 7 messages were replies — a real pattern, not a hypothetical |
| Rate limits | ✓ nowhere near binding |
| `corpus/fetch-slack.mjs` | ✓ writes markdown, raw JSON and attachments |

Two documented traps both fired in practice and are now guarded in the
fetcher: the HTML login page served with a 200 in place of a file, and thread
replies appearing in `conversations.history` at top level as well as under
their parent, which rendered every reply twice.

**Still open, and all of it access rather than engineering:**

- The bot is in the scratch channel only — being added to the three real ones

**Channel names confirmed 22 September.** All three exist and all three are
private. The earlier worry that `social-proof-and-results` was missing was a
sidebar-scrolling artefact, not a real gap:

```
googlesearchaccelerator
metaadsaccelerator
social-proof-and-results
```

These are now the defaults in `probe-slack.mjs` and `fetch-slack.mjs`, pinned
rather than matched loosely. The workspace also contains `google-ads` and
`meta-ads`, so the previous loose targets of `google` and `meta` could have
matched the wrong channel — `find()` returns the first hit and the API does not
promise an order.

**`#social-media` also exists**, and is where generated content accumulates
alongside the Atelier view in the Command Center. It is an output destination
rather than a signal source, so it is deliberately **not** in the fetcher
defaults. See `Content_Atelier.md` §7 — it bears on open questions #3 and #4,
and it is arguably also an input, being a record of what actually survived
review.
- Eleven `c_*` per-client channels exist — `c_pressrecordco`,
  `c_misslyssplanning`, `c_funktasticproductions_djhybrid` among them — which
  map onto the precedent chains. The 16 September call named three channels;
  the workspace has roughly twenty. Whether client channels are in scope is a
  decision nobody has made
- **The workspace was four days from the end of a Pro trial on 22 September.**
  On the free plan Slack stops serving older history, so a backfill that waits
  is a backfill that loses data

---

## Changing this later

Future automations will need to write to Slack, and different people on the
team will need different things from it. Neither requires a second app.

### Adding write scopes

**Same app.** Edit `oauth_config.scopes.bot`, reinstall, done:

1. App config → **OAuth & Permissions** → add the scope
2. **Reinstall to Workspace** — Slack requires this for any new scope
3. If the workspace gates installs, **an admin re-approves**. They see exactly
   which new scopes are being requested
4. Re-read the bot token from the OAuth page and update `.env`

| Persists | Redone |
|---|---|
| The app, its id and its bot user | The install (one click) |
| **Channel membership** — no re-inviting | Admin approval, if the workspace gates it |
| The display name and icon | Reading the token out of the UI |

On step 4: for a given app-plus-workspace pair the `xoxb-` token is normally
stable across reinstalls, but Slack does not guarantee it. Treat re-reading the
token as part of the ritual rather than assuming it survived — a silently
rotated token fails as `invalid_auth`, which is at least loud.

**No code change is involved.** The token is a credential; the scopes decide
which calls return 200 instead of `missing_scope`. Adding `chat:write` changes
what the app may do, not how it authenticates.

The write scopes likely to be wanted:

| Scope | For |
|---|---|
| `chat:write` | Post to channels the bot is already in |
| `chat:write.public` | Post to public channels **without** being invited |
| `chat:write.customize` | Override display name and avatar per message |
| `im:write` | Open a DM — e.g. asking Whitney to set a CTA |
| `files:write` | Upload a generated file |
| `reactions:write` | React to a message, e.g. acknowledging a flag |
| `channels:join` | Join a public channel unaided |

### Per-user access — three different questions

"Different users need different access" splits three ways, with very different
costs. Work out which one applies before building anything.

**1 · Different people may do different things in the Atelier.** Whitney
approves, Giselle only stages. **This is not a Slack concern.** The bot holds
one fixed set of Slack permissions; the Atelier reads the `user` field off the
message or event and decides what that person may trigger. Ordinary
authorisation in our own code, keyed on Slack user ids. Same app, same token,
no Slack change at all.

Most requirements of this shape turn out to be this one, and it is the cheapest
by a wide margin.

**2 · The automation must act *as* a specific person** — read Jacqueline's DMs,
see a private channel only Whitney is in, post under her own name rather than a
bot's. That needs a **user token** (`xoxp-`), which inherits that individual's
own access. Still the same app: user scopes sit under
`oauth_config.scopes.user` beside the bot ones, and each person authorises once.

The cost is real. A user token cannot be copied out of the UI the way a bot
token can — it requires a full OAuth redirect flow, which means a public HTTPS
callback on Railway, which is precisely the inbound surface *Why no Events API*
above avoids. Be sure it is needed.

**3 · It only needs to look as though it came from someone.**
`chat:write.customize` sets a per-message username and icon. This often
satisfies what reads like requirement 2, with no user tokens and no OAuth flow.
Try it first.

### When a second app IS warranted

One good reason: **dev/prod separation.** A second app — "Content Atelier
(dev)" — installed to a scratch channel or a test workspace means a development
token physically cannot post into `#social-proof-and-results`. Worth setting up
*before* write scopes exist, not after the first accident.

Two reasons that are not: adding capability (covered above), and serving more
than one workspace. If LeadLock ever resells this, that is one app in
*distributed* mode, not one app per client.

### The description is a promise

`long_description` currently states the app *"cannot post, reply, or send
anything"*. That text appears in the Slack admin UI, in front of whoever
approves the install. The moment `chat:write` is added it becomes false, and an
admin who reads it and then sees the bot post will treat the next request with
less trust.

**Update the description in the same edit as the scope.** If write is added
before it is used, say so plainly — that it can post but currently does not.

### Recommendation

Install read-only now and take the reinstall later, for three reasons: the
reinstall is genuinely cheap and channel membership survives it; "it cannot
post anything" is worth being able to say in the first conversation about a bot
reading client channels; and by the time write is needed, open questions #2 and
#4 in `Content_Atelier.md` will be settled, so the ask will name **one**
specific scope rather than three speculative ones.

The counter-argument holds if admin attention at WIA is slow to get. Batching
two approvals into one has real value — in which case add `chat:write` and
`im:write` now, leave them unused, and write the description accordingly.

---

## Notes

**Enterprise Grid.** If WIA is on Grid rather than a standard workspace, the app
may need org-level approval in addition to workspace approval, and
`org_deploy_enabled` would need to be true. Unlikely at their size.

**Rate limits.** `conversations.history` is Tier 3 — roughly 50 requests a
minute. Nowhere near a constraint for three low-traffic channels.

**Downloading files.** A file's `url_private_download` needs the bot token in an
`Authorization: Bearer` header. Fetching it unauthenticated returns a login
page, not the image, and does so with a 200 — so a naive fetcher will happily
write HTML into a PNG.
