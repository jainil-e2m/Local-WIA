-- Explicit administrator operation; no content changes, tables or vector columns.
CREATE INDEX transcript_chunks_text_search_idx
  ON transcript_chunks USING gin (to_tsvector('english', chunk_text));
