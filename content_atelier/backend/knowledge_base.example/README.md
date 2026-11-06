# WIA knowledge base: example folder

The strategist angle profile (`2026-10-18.wia-strategist.v3`) loads WIA's own documents whole, as a trusted
system-prompt prefix. This folder shows the expected layout. Every file here is a placeholder: the loader
refuses placeholder text for live and replay runs and accepts it only for offline fake runs.

The real knowledge base is committed at `backend/knowledge_base/` (this repository is private; decision of
18 October 2026). Set `CONTENT_ATELIER_KNOWLEDGE_BASE_DIR` to use another folder. The original Word documents
are in `client_documents/content_guides/`.

## Updating the knowledge base

1. Edit the document files in `backend/knowledge_base/`, as Markdown or plain UTF-8 text.
2. In `manifest.json`, bump `knowledge_base_version` and the changed document's `version`; keep `owner` and
   `status` current.
3. A new folder for another client or setup can start from a copy of this example folder.

## Expected files

| Key | File | Content | Source |
|---|---|---|---|
| `content_strategy` | `01-content-strategy.md` | Savannah's content strategy, whole: pillars, framework, idea banks, cadence, priority series | `content_guides/Strategy from Savannah.docx` |
| `founder_voice_guide` | `02-founder-voice-guide.md` | Founder Voice Guide v2.0, whole | `content_guides/Whitney _ Founder Voice Guide.docx` |
| `accelerator_strategy` | `03-accelerator-strategy.md` | Relevant sections of the Tier 1 Accelerator strategy doc: client avatar, buying behaviour, objections, content topics, behind-the-scenes processes, founder story | `content_guides/Wedding Industry Ads _ Tier 1 Accelerator Strategy Doc.docx` |
| `team_roster` | `04-team-roster.md` | WIA team members who appear on recordings, with roles | Drafted by the team; **unconfirmed by WIA** (E.X2) |
| `offer_sheet` | `05-offer-sheet.md` | Dated offer sheet: offers, who they are for, availability, what WIA does not do | Drafted by the team; **unconfirmed by WIA** (E.X2) |

All five keys are required. More documents (for example a belief bank or a process catalogue, analysis 9.2)
can be added to the manifest. Documents are rendered in manifest order.

## `manifest.json`

```json
{
  "knowledge_base_version": "wia-kb-2026-10-18.v1",
  "documents": [
    {"key": "content_strategy", "file": "01-content-strategy.md", "heading": "Document 1: ...",
     "version": "...", "owner": "...", "status": "supplied"}
  ]
}
```

- `heading` becomes the `## ` heading above the document in the prompt.
- `status` is `approved` (WIA approved it for this use), `supplied` (WIA supplied it; no approval recorded)
  or `unconfirmed` (drafted by the team, awaiting WIA's confirmation).

## What gets recorded

Each run records the knowledge base's identity, never its text: the manifest version and SHA-256, and each
document's key, file, version, owner, status, SHA-256 (of the file bytes) and length. It also records the
SHA-256 of the assembled prefix. In the SQL workflow this is frozen in `pipeline_runs.input_refs.angle_contract`;
in the file pipeline it is in the run manifest's `input_refs`. A retried SQL angle job whose knowledge base no
longer matches the frozen hashes fails rather than mixing versions.
