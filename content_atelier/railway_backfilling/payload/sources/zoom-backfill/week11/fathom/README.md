# Fathom backfill sources

Week 11; occurrence dates grouped in Asia/Kolkata.

Downloaded transcripts: 1. Additional calls: 1. Same-call Zoom overlaps: 0.

- `additional/`: Fathom calls without a corresponding transcript among the 170 existing Zoom originals; selected as additional sources.
- `zoom-overlap/`: alternate Fathom transcripts of calls already represented locally; preserved, excluded as additional processing sources.
- `paired-captures/`: metadata for alternate simultaneous Fathom captures that were not downloaded.
- `manifest.json`: source identity, selection and counterpart references.

Each downloaded source has exact `transcript.raw.json`, `metadata.json`, and readable `transcript.md`. No timing ends were invented and no original Zoom file was replaced.

Gathering only: chunks, embeddings, moments and angles have not been generated. A Fathom-aware importer is needed before these native JSON originals enter the existing TXT/VTT pipeline.
