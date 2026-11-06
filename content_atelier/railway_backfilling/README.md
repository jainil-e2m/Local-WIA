# Content Atelier — local Railway handover package

Prepared 19 October 2026. Verified payload: **6,448 files, 576,487,380 bytes (576.5 MB)**. This directory contains a curated local COPY. No Railway upload, login or deployment has been performed. Original source files and databases were preserved.

## What to use

- `payload/` is the exact prepared data area for a future handover.
- `reports/payload-manifest.csv` lists every payload file, its byte size and SHA-256.
- `reports/file-copy-manifest.json` maps copied files back to their source paths and records any code redactions.
- `reports/source-aliases.json` maps sources already present elsewhere in the package, including byte-identical legacy Zoom originals.
- `reports/omitted-files.json` and `reports/exclusion-summary.json` explain exclusions.
- `reports/database-export-report.json` and `reports/database-restore-verification.json` describe the verified database dump.
- `reports/verification-report.json` records file integrity and the credential scan scope.
- `HANDOVER_STATUS.json` records the final local package status.

The data remains confidential. The payload contains client transcripts, personal/source metadata, embeddings, generated work, private corpus material and historical experiment outputs. Do not print file contents into logs or publish this directory to Git.

## Layout

| Payload directory | Contents |
| --- | --- |
| databases | Restore-tested custom-format PostgreSQL dump of `atelier` |
| artifacts | Complete selected `.storage-artifacts` tree |
| sources/zoom-backfill | Weekly Zoom and Fathom originals, including retained duplicate/overlap captures and supporting metadata |
| sources/fathom-staging | Original Fathom staging files and operator |
| sources/legacy-zoom | Additional unique earlier Zoom exports; identical exports are mapped in the alias report |
| dating-inputs | Reconciliation inventories, meeting metadata, legacy Zoom index and relevant backfill operators |
| legacy-datastore | Retained file-backed source snapshots, paid/model requests and outputs, preparations, experiments and weekly packets |
| corpus | Private project reference corpus |
| code | Sanitized Git bundle, readable checkout snapshot, nonignored untracked files, binary-capable diff and stash listing |
| context/reference-material | Explicit Content Atelier architecture, knowledge, audit and prompt-authoring reference outputs |

## Database verification

The original Content Atelier Docker container was stopped before this work and remains stopped. Its volume was mounted read-only to make a separate copy. The copy was started without networking, and its application database was dumped. The dump was restored into another database inside the isolated helper and all 13 table counts matched.

All 170 database transcript content hashes were matched to staged original files, with no missing or mismatched source bytes.

The exported `atelier` database has PostgreSQL 17.10, pgvector 0.8.2, 170 transcripts, 2,657 chunks, 2,657 chunk embeddings, 14 moments, 13 angles and two briefs. The dump also includes all other tables in the selected database. No schema-version tracking rows were available; the version list is explicitly empty, rather than inferred from source migration filenames.

The inspected Docker and native clusters also contained test databases. Their table counts are recorded, but their fixture data and the raw physical cluster files are excluded. No separate non-test legacy intake database was found in those clusters.

## Code integrity and redactions

Source originals were not edited. Six files in the readable code snapshot required credential redactions. The Git history export retains 227 commits and exported refs after sanitization; 54 exported data blocks contained credential signatures, and 75 matches were removed. Environment/key paths were excluded from the bundle. Commit hashes therefore differ from the original history. Original ref IDs are recorded in `reports/source-git-baseline.json`.

The primary transcript, artifact, retained legacy-datastore and corpus copies were not rewritten. Their source and destination hashes are recorded. Known credential values, common token/private-key/connection-password patterns, raw payload files, ZIP-based document members and decoded Git objects were checked. The database's restored SQL stream was checked separately. These checks do not prove that every conceivable credential format is absent.

## Deliberate exclusions

Environment and key files; synthetic editorial pytest output; rebuildable tokenizer assets; ignored scratch/runtime/dependency directories; raw PostgreSQL cluster files; unrelated client projects and WIA application folders; fixture databases; and duplicate ZIPs whose extracted reference packages are retained. The exact nonignored untracked files requested by the original prompt are preserved or mapped to an already-included canonical source, including their generated backfill fixtures.

## Future upload

Use this package's `payload/` and reports as the explicit source set. Do not rerun broad discovery or untracked-file collection over the parent checkout without excluding `railway_backfilling/`, because this directory is inside that checkout and would be collected recursively.

The original upload commands use live database URLs and do not explicitly define a prepared-dump interface. The future operator must inspect the transfer scripts and adapt the upload to this package, preserving the already prepared dump and sanitization. Destination project/bucket ownership and transfer-tool behavior remain unverified here. A local verified package is not an uploaded Railway handover.

To recheck payload checksums locally:

```powershell
python .\tools\verify_package.py
```

Keep this package and the originals until the owner confirms the handover.
