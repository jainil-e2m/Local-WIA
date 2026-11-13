# S3 people and roster validation

Validated locally on 30 October 2026. Implementation is complete; business sign-off
and full-history coverage remain open.

## Verified

- All 166 backend tests pass against isolated PostgreSQL, including actual page
  publication, pinned admin links, bounded resolver lookups, mailbox history,
  roster merges, stale revisions, owner uniqueness, and team suggestion replay.
- Migration `c04a20261030` applies to the existing development database and a fresh
  test database. Empty-database downgrade to `c03a20261030` and re-upgrade pass.
  Alembic reports no model drift.
- The private roster creates 30 pending entries: three staff, six contractors,
  fourteen former members, four shared mailboxes, one service account, and two
  unidentified deactivated workspace members. Automatic contact resolution adds
  seven client-contact people.
- All 69 provider identities have a non-null party: 39 internal, six shared
  mailbox, sixteen client, one partner, and seven unknown.
- All 26 directory-visible Slack humans and all twelve ClickUp members link to a
  person. Two deactivated Slack accounts link to pending unknown placeholders;
  they have not been assigned invented names or staff roles.
- Nine team suggestions cover all three active clients with retained ClickUp
  tasks updated in the last 120 days (39 distinct current tasks).
- Repeating roster load, full identity resolution, and team suggestions changes
  no persisted rows, revisions, timestamps, or audit counts.
- Ordered row hashes confirm businesses, aliases, contacts, source scopes,
  client-source decisions, sender rules, and record associations are unchanged.
- Live 30-day discovery completes for all six connectors with zero roster
  addresses among contact candidates. The normal enumeration and central filter
  run with proposal persistence replaced by validation, preserving mapping rows.
- Scanning S3 code, tests, migration, and example against private roster values
  finds no real names, emails, or provider IDs. Real data and validation details
  remain in ignored `backend/.local/`.

## Open sign-off and coverage

All 24 active clients still need a confirmed owner. Pending roles and people,
including the two unidentified deactivated accounts, need business confirmation.
Five other identities have no person and remain in the frequency-ranked unknown
queue for review; resolution deliberately avoids matching client display names.

The development database contains an earlier limited backfill. Suggestions cover
retained tasks only, not all upstream work over 120 days. No former-person open
assignments were found in retained records; this does not establish that upstream
work has been reassigned. Broader task coverage and former-member handoffs still
need verification.

Shared inboxes remain separate from their holders. Undated conflicting holder
history yields no attributed human until dates are established. Exact client
associations remain contact- and scope-based.

Private evidence: `.local/s3-validation.json`, `.local/s3-unknown.txt`,
`.local/s3-teams.txt`, `.local/s3-privacy-check.json`, and the pre-migration
database backup `.local/s3-before-roster.dump`. Live discovery counts are in
`.local/s3-discovery-validation.json`.
