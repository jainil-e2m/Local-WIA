# Full handbook angle call setup

Jainil requested setting up the second-stage call with the original handbook converted to content-only Markdown, without extraction tags, versions, hashes or audit wrappers. He first requested tracking the current version in Git and explicitly prohibited pushing to GitHub.

Before application edits, the existing `content_atelier` repository was checkpointed locally at `c7d3eb690e2548476663bc59fe2f8cb11fe9c489` (`Checkpoint current Content Atelier before full-handbook angle context`). Existing credentials/raw runtime data remained ignored; generated test directories were excluded locally. No remote action occurred.

The clean handbook is `backend/backend_pipeline/prompt_templates/handbook_v2/wia_content_system_handbook.md`. It preserves the original substantive wording, heading order, all 11 tables, calibration examples, source limits and original hyperlink. The opening prepared/version/date line and the document-version qualifier in a source-register row were removed as presentation metadata. Original source excerpts/timestamps and meaningful claim boundaries were retained. The unchanged Word snapshot and tagged audit extraction remain available separately.

The complete latest angle feedback is in `angle_generation_feedback.md`. The actual related email was found at `corpus/emails/2026-06-10-the-question-we-ask-every-new-client.md`; its body, without export frontmatter, is supplied through `market_research_email.md`. This supplies one specific history comparison, not a complete recent-content ledger or current offer verification.

The new `full_handbook_angle_system` builder inserts the full handbook and feedback as editorial references, specifies coherence between rationale and central point, reinforces WIA process value and natural wording, and makes history availability explicit. Original system prompt bodies and moment-extraction setup remain unchanged. The existing known source namespace remains separate; the new editorial `knowledge_refs` are `handbook` and `latest_feedback`. Self-referencing alternatives are now rejected without rewriting historical records.

`scripts/prepare_week2_full_handbook_angle.py` defaults to local preparation. It uses exact `openai/gpt-6-luna-pro`, low reasoning, configured JSON-object mode, no completion cap, no embeddings, and the same two validated moments with 114 original context turns from `week2-handbook-luna-pro-20261013-b1`. Five rejected moments stay excluded. This does not fix or rerun extraction and does not add a third similarity call.

The new request run is `week2-full-handbook-angle-20261013-c1`. It stores the exact JSON request, unaugmented prompt messages, schema, source pool/context references, one history record, preflight information and a readable request preview in the ignored local testing datastore. Handbook hashes and other technical provenance stay outside the content-only Markdown and its model-reference body.

No paid call was requested or made in this setup turn. Paid execution requires explicit `--live`; the saved configuration/request must match the preview, and duplicate dispatch is blocked. Existing `b1` requests, raw responses, receipts and review are unchanged.
