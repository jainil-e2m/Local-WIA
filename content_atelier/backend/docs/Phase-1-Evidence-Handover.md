> The governing plan is `Content-Atelier-Implementation-Plan-Brief-Generation.md` (Phase 1, section 9). This note says what Phase 1 left and how to operate it.

# Phase 1: evidence model and intake, hand-over

Branch `item/1-evidence-intake`, built on the Phase 0 branch. Item status is in the plan (section 9 and "Implementation status"); the log row is in Appendix G.

## What exists now

| Part | Where | What it does |
| --- | --- | --- |
| Migration 007 (plan label 006) | `migrations/007_evidence_model.sql` | `clients`, `people`, `glossary_terms`, `slack_channels`; documents gain call type, inclusion with a reason, occurrence date with a source, participants, speaker map, canonical link, raw object key; chunks gain header, date, speaker roles, embedding model, segmentation version, a current flag, a search copy and a generated full-text column. The plan's later migrations shift by one. |
| One normaliser per source | `normalise/sources.py` | A Fathom call is built by one function whether it comes from the API or from native JSON (same passages, ids, speaker emails). Slack messages group by thread. |
| Classification | `normalise/classify.py` | The corpus index's rules, extended; a fast model only for what the rules cannot place (`models.document_classification`); a person's decision is never overwritten. |
| Speakers | `normalise/speakers.py` | Labels to `people` and a role; an email is fact, a name is marked inferred; stored in `transcripts.speaker_map` beside the immutable passage map. |
| Dates | `normalise/dates.py` | Evidence only: provider, filename, header line, Zoom recording list, calendar. No week is ever a source; no unique match means explicitly undated. |
| Segmentation v2 | `normalise/segment.py` | Header (date, type, client, speakers with roles), one-turn overlap, roles per chunk. Old chunks retire and stay readable. |
| Glossary | `normalise/glossary.py`, `reference.py` | Names and their mis-transcriptions, applied to a search copy and to hints, never to the original text. |
| Documents | `documents/` | Intake (`intake.py`), the `document_normalise` job (`jobs.py`), copies (`duplicates.py`), selection by window or set (`select.py`), the planned re-embedding (`reembed.py`), the Slack export (`slack_export.py`), the API (`api.py`), the commands (`cli.py`). |
| People and clients | `reference.py` | `people` mirror the confirmed roster (saving a roster item updates the row in the same transaction); clients load from a reviewed list kept outside the repository. |

Operating commands and the backfill runbook are in `DEPLOYMENT.md`, "Documents and evidence".

## Rules worth knowing

- **Identity is the content.** A text file is the same document wherever it came from; a Fathom call is the same document from the API and from native JSON. Importing twice adds nothing.
- **Selection ignores weeks.** `documents/select.py` takes included, normalised, non-duplicate documents by date window or explicit set. A selected cycle run records `selected_by` and the cycle container (a `weeks` row named by the window) holds no documents of its own. Excluded documents (internal, vendor, fragment, copies) are not extracted by weekly runs either.
- **Research reads included, current chunks.** A document whose current chunks are not all embedded drops out of the live-intake archive until the planned re-embedding completes; the legacy weekly archive stays strict.
- **A live document is normalised before it is indexed.** The intake's indexing job waits for the `document_normalise` job (bulk queue), so there is one segmentation and no chunks to throw away.
- **Revisions are not copies.** Two revisions of one intake source (an edited Slack message) are versions; two documents with the same text from different sources are copies, and the earliest admitted one stays canonical. Selection reads only a source's current, undeleted revision.
- **Normalising again keeps what was learned.** A person's call type, a model's placement of an unchanged request, and a date matched from Zoom's list or a calendar all survive `documents normalise --all`; with no run plan the model is not asked and the call waits for a person. `documents normalise --all --estimate` counts the model calls first.
- **Between normalising and re-embedding, brief research waits.** Normalising a backfilled document gives it version 2 chunks with no vector, and `retrieval.archive` refuses an archive with an unembedded current chunk; run `documents reembed` straight after (its estimate and plan approved beforehand).

## What is not done, and why

- **Real-corpus runs** (1.B4 agreement with the corpus index, 1.B5 on a real sample, 1.B6 re-embedding the archive, 1.B9, 1.B11 dates for the 164 Zoom transcripts) need S.B10's originals and, for dates, a Zoom recording list or calendar export from WIA. Everything is built and tested on synthetic transcripts; the commands are in the runbook, and `documents dates` and `documents agreement` report what a person still has to resolve.
- **The client list** is WIA's, kept outside the repository (`clients import --file`); until it is supplied no call is tied to a client and every consent is the default, `anonymise_only`.
- **Live Slack grouping by thread.** The bot still delivers one source per message, so a live thread is several documents; the export import and the normaliser group by thread. Moving the live path needs whole-thread revisions across batches (Phase 6, live hardening).
- **The Slack export** itself (September) has not been transferred; the importer is tested against an export-shaped folder and zip.
- **A person's classification** is recorded by `documents classify` or `POST /documents/{id}/classification`. The Node server relays only the two `GET` routes the app calls (the allowlist is exactly the routes the app uses), so the screen shows a decision but cannot yet make one; a control for it is the first addition when someone asks for it.
