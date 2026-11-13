# Client details editor

Written 6 November 2026. One modal for editing how a client is identified and presented: name, aliases, category, location, portfolio logo and record cover.

## Why one modal

Before this, the only edit was the cover picker on the client record. Identity and logo could not be corrected at all. The KB extracts these values (logos from the Drive brand folder or email signature, per P10), and extraction is sometimes wrong or missing. For example, real pilot clients show "Not extracted yet" and *Logo pending*.

One modal means one mental model: "this is where I fix how this client looks and is named." It is reachable from both places people notice a problem:

| Entry point | Opens on | Why |
| --- | --- | --- |
| Portfolio card ⋯ menu → **Edit client details** | Details | The card is where the name and logo are seen most |
| Record header → **Edit cover** | Cover panel | Keeps the user's intent; details are one click away |

## What it contains

There are no tabs. The two previews at the top are the way in: click the **portfolio card** (chip: *Edit logo*) for the Logo panel, or the **record cover** (chip: *Change cover*) for the Cover panel. The panel replaces the details form below the previews, with **Back to details**; clicking the selected preview again also returns. The selected preview shows a blue ring.

| Panel | Fields | Rules |
| --- | --- | --- |
| **Details** | Business name, Also known as (chips), Category, Location; **Relationship:** account owner, stage, engagements (WIA service type + start date) | The name is required, at most 80 characters, and warns on a duplicate. Each field shows *From KB record*, *Not extracted yet* or *Edited*, with **Use KB value** to revert that field. "Not extracted yet" from the KB opens as an empty field, never as a value. Initials follow the name. The earliest engagement start becomes *Client since*; a ClickUp list name stays selectable as "(from ClickUp)" until replaced. |
| **Logo** | Upload (drop or browse), size 60–160 %, background (8 tested tints, including **Ink** for white logos), hide or restore the extracted logo | SVG/PNG/WebP/JPG up to 2 MB; SVGs must be under 300 KB once stored, because they are kept as text and browser storage (~5 MB) is shared with the Action Hub's saved edits. Rasters are scaled to 1000 px on the long edge and stored as WebP (~15 KB for a typical wordmark). Upload notes flag files under 256 px, JPG (no transparency) and square marks (suggest Size). The guide panel states the preferred format. The source line keeps the file name, pixel size, uploader and date, as P10 requires. |
| **Cover** | The 12-image library with category filters and a default reset | Unchanged library and contract (`clientCovers.ts`). |

The top of the modal has a live preview of the two surfaces these fields drive: the **portfolio card** (logo banner, initials, name, location) and the **record cover** (cover photo, initials, name, category · location). On narrow screens both previews show on Details (they are the entry points); inside a panel only the one being edited shows.

**One Save for all panels.** Closing with unsaved changes (Cancel, ✕, Escape, backdrop) asks *Discard your unsaved changes?*. **Reset all to the KB record** restores every field, the extracted logo and the default cover; it still needs Save.

## Permissions (preview)

- **Admins and ops** (Whitney, Gisselle): every tab.
- **Everyone else:** the Cover tab only. Details and Logo are read-only, with a note naming who can change them.

This follows the agreed model: client identity is a reviewed record (editors propose, resolvers apply, KB-CH-66), while the cover is presentation. The final rule is a WIA decision (see Open decisions).

## Data rules

- **Only differences are stored.** A field nobody edited keeps following the KB record, so later corrections from extraction still flow through. Reverting every field removes the override.
- **The client ID never changes.** Renaming does not touch source mappings (Slack, Drive, ClickUp, LeadLock) or URLs.
- **The source of every logo is shown:** *Drive · Brand folder*, *Gmail · email signature* or *Uploaded in the KB*, with file and date. Logos are never taken from the client's website.
- **Every view reads the same values.** Overrides are applied onto the shared client, record and logo maps, and the app re-renders on save. Portfolio cards and list, record header, breadcrumb and page title all agree.

## Implementation

| File | Role |
| --- | --- |
| `src/clientDetails.ts` | Override store (`wia-client-details-v1:<id>`), applies overrides after `kbLive`, change subscription, logo validation and resizing (`prepareLogo`) |
| `src/clientOverride.ts` | The storage rule (`overrideFrom`): which edited fields differ from the KB record. Pure, checked by `node scripts/verify-client-details.mjs` |
| `src/components/ClientDetailsEditor.tsx` / `.css` | The modal, previews, tabs, alias chips, logo panel |
| `src/components/ClientCoverPicker.tsx` | Now `CoverLibrary`, the cover grid used by the Cover tab |
| `src/views/Clients.tsx` | Menu entry; banner and list thumbnail apply tint and size (`--logo-user-scale`) |
| `src/views/ClientDetail.tsx` | **Edit cover** opens the editor on the Cover tab; the cover is read from storage each render |

## Backend contract (to replace the browser adapter)

Saved in this browser only, like the cover. For team-wide persistence:

- `PATCH /api/v1/clients/{id}` with `{ revision, name?, aliases?, category?, location?, owner?, lifecycle?, engagements?, logoDisplay?: { scale, tint }, coverId? }`. Use `null` to revert a field to the KB value. Require `allowed_actions` to include `client.edit_identity` for identity and logo, and `client.edit_appearance` for the cover. Reject stale revisions (409) and write an audit row per field.
- `POST /api/v1/clients/{id}/logo` (multipart) stores the file in object storage. Return `{ logoId, file, width, height, uploadedBy, uploadedAt }` and record the source as *Uploaded in the KB*. Do not store image bytes on the client row. `DELETE` hides the logo; restoring brings back the extracted one.
- The snapshot/read model returns the effective values plus a per-field `origin: 'kb' | 'edited'`, so the *Edited* badges work for everyone.

## Open decisions

1. Who may edit identity and logo: admins and ops only, or also the account owner?
2. Should a rename or alias change feed source matching (for example, Gmail sender rules), or stay display-only?
3. Should managers' cover changes apply to everyone or only to themselves?
4. Aliases currently show only in this editor, because the record header no longer lists them. Should they appear somewhere, such as Profile → Business?
