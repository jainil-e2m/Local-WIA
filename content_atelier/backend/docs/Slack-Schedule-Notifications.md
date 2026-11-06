# Slack schedule notifications

Backend implementation, 5 November 2026. This does not publish content. It posts schedule notices through the existing bot, from committed schedule_saved audit events, using the existing scheduler.

## Mapping and activation

The owner's current **testing override** is prepared in backend/deploy/slack-schedule-notifications.settings.json:

| Destination | Channel ID |
| --- | --- |
| Email marketing — testing | C0C3FT6DZAS |
| Social media (carousels and Reels) — testing | C0C3FT6DZAS |

Both notification types go to this testing channel as separate messages. The sender allows one message per actual channel per scheduler pass, so a full pack's two notices can arrive over two passes. Before production activation, restore the intended email channel C0BQ6RW7C84 and social channel C063XKRCJ0M in the mapping file. This local override has not been applied to production settings.

The file also supplies the documented public app origin, https://content-atelier.up.railway.app. Review it if the deployment hostname changes. Each piece links to /studio/packs/{pack_id}?piece={slot_key}.

1. Apply migration 012 through the existing migration/deployment workflow. Deploy schema-compatible backend services together; the frontend and existing Slack bot service need no changes for this backend feature.
2. From backend/, with the intended database and verified administrator configured, review then apply:

       python -m backend_pipeline.storage_cli settings apply --file deploy/slack-schedule-notifications.settings.json --actor <admin email> --dry-run
       python -m backend_pipeline.storage_cli settings apply --file deploy/slack-schedule-notifications.settings.json --actor <admin email>

3. Set the existing bot credential as ATELIER_SLACK_BOT_TOKEN on the **scheduler service only**, using the deployment's secret configuration, and restart that service. Do not use ATELIER_SLACK_INTAKE_TOKEN: it authenticates inbound intake, not Slack posting. The bot must have chat:write and access to both channels.
4. The first configured scheduler pass initializes each destination and skips its visible historical events. Wait for the “Slack schedule destination initialized” logs before the agreed new-save acceptance check. This prevents an initial historical notification flood.

Production settings have not been changed. Initial automated verification used synthetic records and mocked Slack. The later live local acceptance check is recorded below.

The settings can alternatively come from scheduler environment variables:

| Environment fallback | Registered setting |
| --- | --- |
| ATELIER_SLACK_EMAIL_CHANNEL_ID | slack.schedule_notifications.email_channel_id |
| ATELIER_SLACK_SOCIAL_CHANNEL_ID | slack.schedule_notifications.social_channel_id |
| ATELIER_PUBLIC_APP_URL | slack.schedule_notifications.public_app_url |

Table values win over environment fallbacks. All three default to unset. An absent bot token disables the sender before any database or HTTP work; absent destinations disable their route. A missing/invalid public HTTPS origin pauses delivery with a configuration error. Tokens never enter settings rows, editorial snapshots or message payloads.

## Messages

After **Save all schedules** commits, a five-piece save normally produces one email-channel notice and one social-channel notice listing its four pieces. Partial saves include only the changed pieces in the affected destination.

The opening says “Content Atelier has … scheduled for publishing at the times below.” This follows the owner's updated publication workflow; it does not depend on the retired whole-pack Ready to publish action or imply that something has already been published. Genuine reschedules say that the schedule changed, with previous time → new time.

Every piece includes its title (email's first subject option; social piece's title), publishing instant in the calendar's configured display timezone, and a direct link to its pack tab. Message labels are escaped and unfurls are disabled. No full copy, transcripts, attachments, mentions, new public endpoint or model calls are involved.

## Delivery and recovery

The sender discovers events through a delivery ledger anti-join, not a timestamp cursor. Request receipt replay creates no new event; unchanged publishing instants create skipped deliveries. Failed calendar transactions have no committed event to send.

Each destination/source-event pair is unique. Claims have a 60-second lease; channel cooldowns also coordinate concurrent schedulers. Each pass makes at most two HTTP attempts and at most one per actual channel. Slack HTTP success must also report ok: true, the intended channel and a message timestamp.

Transient failures retry with delays of 30 seconds, 2 minutes, 10 minutes and 30 minutes, up to five attempts. Slack's longer Retry-After takes precedence. Permission/authentication/payload failures are terminal until corrected. Expired claims recover on a later pass. Acknowledgement loss can still produce a rare duplicate; network delivery is not exactly once.

Before each attempt, cancelled, replaced, published, superseded, changed-version and past-time schedules are filtered out. Unsent events older than 24 hours are skipped. Calendar writes and the scheduler's other parts do not depend on Slack succeeding.

Inspect delivery state using a read-only query:

    SELECT notification_id, destination, channel_id, status, attempt_count,
           last_error, next_attempt_at, sent_at, payload->>'pack_id' AS pack_id
    FROM slack_schedule_notifications
    ORDER BY created_at DESC, notification_id;

After correcting a terminal error, an operator can re-arm one specifically reviewed delivery:

    UPDATE slack_schedule_notifications
    SET status='pending', attempt_count=0, next_attempt_at=now(), last_error=NULL
    WHERE notification_id='<reviewed notification id>' AND status='failed';

Do not reset sent rows or the activation markers to retry a failed delivery. Already queued rows retain their original channel; changing configuration does not redirect them to another conversation. Review and reconcile a changed destination explicitly.

## Disable / rollback

Remove ATELIER_SLACK_BOT_TOKEN from the scheduler and restart it to stop sending. Or clear the effective destination settings; account for table overrides when changing environment fallbacks. Pending events remain available for bounded catch-up, subject to the age/staleness checks.

After migration 012, retain a schema-compatible backend image even when notifications are disabled. The earlier image at schema 011 rejects unknown recorded schema versions; disabling the sender does not require a destructive schema rollback.

## Local verification, 5 November 2026

- 130 focused tests passed: notification delivery/rendering (39), migration upgrades (19), settings (55) and database settings (17).
- Final notification-only rerun: all 39 passed, including the actual calendar transaction/receipt/replay/rollback path with existing pack validation isolated by a test stub.
- Schema catalogue check passed for every recorded version; backend Ruff and OpenAPI drift checks passed; documentation/secret-classification checks passed.
- A broader RQ-worker run had 91 passed and 9 failed on this Windows host because its timeout handler requires unavailable signal.SIGALRM. The failures occur in RQ worker execution, not Slack transport. No unrelated worker changes were made; this does not certify the entire backend suite green.
- These initial checks made no live Slack, publishing, embedding or model requests and changed no production database. Existing frontend publication work was preserved.

Evidence logs are in the ignored backend/.test-runs directory: slack-final, slack-delivery-verified, slack-schema-verified, slack-docs-verified and slack-integration.

## Live local delivery, 5 November 2026

At the owner's request, localhost now uses the real Python storage API and the existing isolated `atelier_schedule_preview_test` database, migrated to 012. The previous publication preview's mocked responses could not produce SQL scheduling events; its script and JSON state were preserved. The current built frontend is served unchanged.

The local notifier reuses WIA's existing bot credential from the sibling project's ignored environment file, in memory only. The bot was verified as a member of `C0C3FT6DZAS` (`#wia-ai-team-testing`). Both destination settings in this test database point to that channel. Local notices carry `[Local test]` and link to `http://localhost:3000`; those links require localhost to be running on the viewing computer.

This preview uses a dedicated five-second loop around the same notification function. It does not start unrelated intake, generation or embedding jobs. The explicit `local_test_channel` argument permits loopback links only with synthetic storage, a database name ending `_test`, an explicitly supplied HTTP client, and every enabled route targeting that one nominated channel. The normal scheduler does not supply that argument and continues to require a public HTTPS origin.

Live acceptance passed through the browser's **Save all schedules** action: all five sample pieces committed, producing two Slack-confirmed deliveries on their first attempt (one email; four social pieces). Existing sample schedules produced the appropriate reschedule/mixed-update wording. Ten historical destination/event records were skipped at activation; none were replayed. Both notices were sent only to the testing channel.

- [Email notice](https://weddingindustryads.slack.com/archives/C0C3FT6DZAS/p1793882221283519)
- [Social notice](https://weddingindustryads.slack.com/archives/C0C3FT6DZAS/p1793882227001399)

The notification suite now has **41 passing tests**, including explicit local-origin and single-channel restrictions. Ruff passed for the changed backend modules and test file. Local service scripts, PID files, sanitized delivery evidence and browser results are in the ignored `.qa/local-slack/` directory; its README records restart/stop instructions. The database contains synthetic sample copy, not production content. The live tests did not deploy services or change production settings, schedules or channels.
