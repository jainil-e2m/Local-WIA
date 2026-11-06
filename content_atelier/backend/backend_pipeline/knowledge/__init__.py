"""The brand kit and context system (section 4.12, R51, R52; Phase L).

- `items`: brand-kit items, one schema per kind, and the store with validity queries (L.B1).
- `seed`: the one-time seed from the ChatGPT-export analysis and today's knowledge base (L.B2).
- `review`: the review queue's service: accept, edit or reject a candidate; approver entries (L.B3).
- `compiler`: compiled knowledge-base versions from confirmed items, approval and benchmark state (L.B4).
- `assembly`: the one context-assembly service every stage calls (L.B5).
- `mining`: the weekly learning loop over WIA's approved work (L.B6).
- `performance`: published pieces and their performance (L.B7).
- `staleness`: review intervals, retirement of expired items, and warnings (L.B8).

The knowledge-base loader stays in `backend_pipeline/knowledge_base.py`: its format is the compiler's output,
and the file-backed knowledge base stays as the offline-test fixture.
"""
