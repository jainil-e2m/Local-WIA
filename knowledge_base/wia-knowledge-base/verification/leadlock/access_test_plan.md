# LeadLock client-data access test plan

Updated: **20 October 2026**. The configured keys were retested; no permission, app installation, token exchange or remote record was changed.

## What the current keys establish

| Credential | Successful read | Blocked reads |
|---|---|---|
| `GHL_AGENCY_PIT` | Dogwood Reserve location identity | Contacts, pipelines, opportunities and calendars: HTTP 401, token not authorised for scope |
| `GHL_PIT` | Wedding Industry Ads location identity | Pipelines and opportunities: the same HTTP 401 |

Two additional opportunity requests using the current documented `Version: v3` and `locationId` parameter also returned scope denial. The initial recheck used pinned `2021-07-28` routes with their matching parameters. This distinguishes valid metadata access from feature permissions; neither an invalid key nor an empty client database follows from these results. The original 59-location inventory is discovery, not proof of client-outcome access.

The official scope catalogue explicitly marks `locations.readonly` as **Sub-Account, Agency**, while `opportunities.readonly`, `contacts.readonly` and the calendar scopes are **Sub-Account** capabilities. This explains why an agency discovery token can succeed on location metadata without proving authority for the lead/outcome endpoints. The exact live grants still need inspection; this is not a claim that every PIT is invalid for sub-account features. [Scope catalogue](https://marketplace.gohighlevel.com/docs/Authorization/Scopes/).

Evidence: [eight-request recheck](access_recheck_2026-10-20.json), [two-request v3 comparison](v3_access_recheck_2026-10-20.json). Credential values and full contact/opportunity bodies are not retained.

## Recommended central authorisation route

The user's preference is one managed integration rather than separately maintained private tokens for each client. Use **one private OAuth application**, authorised for the intended sub-accounts, with location credentials managed centrally by the backend. This is different from the agency Settings → Private Integrations token already created.

HighLevel documents private OAuth apps, account installation and agency-versus-location token types. Its location-token endpoint specifically describes obtaining a location OAuth token from an **agency OAuth access token**. Do not assume the existing agency PIT can be substituted for that OAuth token or that a location ID parameter grants missing scopes. [OAuth setup](https://marketplace.gohighlevel.com/docs/Authorization/OAuth2.0/), [location-token endpoint](https://marketplace.gohighlevel.com/docs/2021-07-28/ghl/oauth/get-location-access-token/).

The concrete setup sequence is:

1. In the HighLevel developer Marketplace, create a **Private** OAuth app for Client Knowledge Base. Configure it for the required sub-account data and agency-managed installation. Its installation/distribution settings determine whether authorisation returns a location token or an agency token; use the matching documented flow.
2. Configure the minimum read scopes needed for the first outcome test, an actual OAuth callback handler/redirect URL, and client ID/secret. Do not reuse the Google OAuth callback solely because it is already available; it does not implement HighLevel token exchange. Keep new credentials in backend/test configuration, never frontend-exposed variables or chat.
3. Have the authorised agency administrator install/approve it for **Dogwood Reserve first**. If the app returns an authorised agency OAuth token, obtain the corresponding location token through the documented endpoint; if it returns a location token, use that token for the location. Check returned location identity and scopes. Broader installations follow only the intended account roster.
4. Run the bounded checks below using the authorised location credential, then reconcile the results against the actual LeadLock UI and agreed business definitions. Maintain token refresh centrally.

One managed OAuth app still requires authorisation for each intended account; it avoids manually creating a separate PIT integration for every client. If a suitable installed OAuth app already exists, inspect and reuse its authorised grants instead of creating another. Current local configuration contains PITs, not demonstrated OAuth app credentials/access.

For the agency-managed installation requested here, distinguish **who installs/manages the app** from **the resources it targets**:

| App setting | Configuration to assess |
|---|---|
| App type | Private, for this internal integration |
| Target user | Sub-Account, because client opportunities/pipelines belong to locations |
| Who can install | Agency Only, allowing the agency admin/owner to manage installation |
| Resulting flow | Agency authorisation returns a Company token; exchange it for a Location token for each authorised installed client account |

This is a documented supported combination, not a tested WIA installation. Setting the app's Target User to Agency merely because an agency administrator is configuring it can target the wrong resource level. [Agency installation of a Sub-Account-targeted app](https://marketplace.gohighlevel.com/docs/Authorization/TargetUserSubAccount/index.html).

Private Integration scopes can be edited without replacing their token, but edits only help when that integration's account level and resource support are appropriate. Adding an agency metadata scope cannot be assumed to grant location opportunities. [Private Integration permissions](https://marketplace.gohighlevel.com/docs/Authorization/PrivateIntegrationsToken/).

## Minimum source permissions to verify

| Scope | Purpose |
|---|---|
| `locations.readonly` | Confirm the selected account identity |
| `contacts.readonly` | Read necessary lead/contact identity and deduplication evidence |
| `opportunities.readonly` | Read pipelines/stages and opportunity records/status |
| `calendars.readonly` | Identify the relevant booking calendars |
| `calendars/events.readonly` | Read actual appointment records and statuses |
| `locations/customFields.readonly`, if required | Interpret account-specific outcome/custom fields |

Check the current app's scope catalogue and endpoint requirements. Relevant message/conversation read scopes are a separate dependency if lead-response/follow-up measures require those records; the initial outcome snapshot does not need every financial, survey or write permission. See [scope reference](https://marketplace.gohighlevel.com/docs/Authorization/Scopes/).

## Read-only validation cases after authorisation

| Check | Required result |
|---|---|
| Account identity | HTTP 200 and the expected Dogwood location ID/name, not only the agency or WIA's own account |
| Pipelines/stages | Retrieve definitions; review which stages actually represent inquiries, tours and bookings |
| Opportunity sample | Retrieve a small page; validate a known real record's ID, mapped contact, stage/status and dates against the UI |
| Booked outcome | Reconcile a known won/booked example with WIA's accepted business definition; CRM `won` is not automatically the agreed booking criterion |
| Appointment sample | Use the actual relevant calendar ID and bounded dates; validate scheduled/cancelled/rescheduled/no-show semantics |
| Snapshot | Complete pagination for the agreed period/cohort; deduplicate and reproduce counts with source IDs and refresh time |
| Coverage failure / empty result | Distinguish denied access, partial pages and a genuinely complete empty query; do not turn unknowns into zeros |
| Multi-account check | Repeat on a second intended client to prove central installation/location handling; do not extrapolate one account to all 59 locations |

No billing/contract facts are needed to prove this first lead-outcome path. Dubsado signing/payment events remain on the approved Gmail route. Once the reads work, metric definitions, historical activity/stage availability and full coverage still require validation before declaring the Client Profile snapshot complete.

## Dogwood dashboard screenshot — reconciliation target

The user supplied a Dogwood dashboard screenshot on 20 October. This is UI evidence, not a successful API extraction. It shows Last 30 days and Status change on the widgets; upper widgets select All pipelines, while Funnel and Stages Distribution select DND. Saved conditions/date overrides and pipeline visibility settings are not exposed in the screenshot.

| Visible widget | Screenshot observation | Underlying data/calculation to assess after OAuth authorisation |
|---|---|---|
| Opportunity Status | 103 total: 102 Open, 1 Won | Count opportunities by status within the same account, pipeline selection, date property and conditions. These are not established unique-lead or WIA-client counts |
| Opportunity Value | Total revenue displayed as $0 | Sum the applicable recorded opportunity values; validate missing versus zero amounts and the widget's aggregation |
| Conversion Rate | 0.97%, won revenue $0 | 1 / 103 x 100 is consistent with the displayed rate. Reconcile the actual included records and denominator rather than assume the formula is proven by the screenshot |
| Funnel | DND pipeline; visible Do Not Text stage and Won outcome | Apply the provider's cumulative stage/visible-stage logic, relevant statuses/values and last-status-change reporting basis |
| Stages Distribution | DND pipeline; 5 displayed opportunities | Group current open opportunities by visible stage, with outcomes handled separately according to the widget's rules |

HighLevel documents the General Funnel widget as cumulative across the current and downstream visible stages, including applicable won records; Stages Distribution reflects current placement instead. Replicating that cumulative display is different from proving each historical transition, time-in-stage or a cohort conversion. Those historical measures still require suitable history. [Funnel/distribution definitions](https://help.gohighlevel.com/support/solutions/articles/155000001455-how-funnels-and-stage-distribution-widgets-work).

Widget-specific date properties, date overrides and saved conditions can affect the results. Use the same account timezone and selected period; do not replace Status change with created/updated time. A record's latest status-change timestamp does not establish a complete transition log. [General-widget settings](https://help.gohighlevel.com/support/solutions/articles/155000008856-configure-and-filter-general-widgets-on-your-sub-account-dashboard), [opportunity date properties](https://help.gohighlevel.com/support/solutions/articles/155000008109-opportunities-widgets-in-dashboards-reports).

OAuth with the correct installation/scopes is the access mechanism for the underlying records; it does not itself return or reproduce an entire saved dashboard. No public endpoint returning this exact dashboard/configuration was verified in this review. The intended approach is record retrieval plus reconciled backend calculations. Check returned field and visibility-setting availability before promising exact parity for every widget. Opportunity monetary value is CRM pipeline data, not proof of collected payments or WIA's Dubsado invoice state.

## Current test commands

```powershell
node knowledge_base/wia-knowledge-base/verification/recheck_source_access.mjs --leadlock
node knowledge_base/wia-knowledge-base/verification/recheck_source_access.mjs --leadlock --current-version
```

These repeat the existing PIT checks and overwrite their corresponding dated recheck reports. They do not create an OAuth app, exchange tokens, change grants or implement the future OAuth callback. Repeating the same denied read without an authorisation change is not a substitute for the setup above.
