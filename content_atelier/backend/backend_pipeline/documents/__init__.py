"""Documents (plan Phase 1, section 9): every transcript, backfilled or live, as a document of its own.

intake       week-less file import, idempotent, raw bytes to the artifact store, a normalise job per new document (1.B3)
jobs         the `document_normalise` stage: speakers, classification, dates, segmentation, duplicates (1.B4 to 1.B6, 1.B10, 1.B11)
duplicates   a stored canonical link between copies of one document (1.B10)
select       documents chosen by date window or an explicit set, never by `week_id`, and queued for extraction (1.B13)
reembed      the planned `bulk` run that embeds current chunks under one contract (1.B6)
slack_export import of the Slack workspace export, one document per thread (1.B7)
api          the documents API (1.B8)
cli          `storage_cli documents ...`
"""
NORMALISE_STAGE = "document_normalise"
RUN_SCOPE = "document_intake"
