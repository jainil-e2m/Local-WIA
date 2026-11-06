from __future__ import annotations

from pathlib import Path

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS angle_vectors (
    angle_id text PRIMARY KEY,
    run_id text NOT NULL,
    embedding_profile text NOT NULL,
    signature_hash text NOT NULL,
    generated_at timestamptz NOT NULL,
    eligible boolean NOT NULL DEFAULT true,
    embedding vector(1536) NOT NULL
);

CREATE INDEX IF NOT EXISTS angle_vectors_run_idx ON angle_vectors(run_id);
"""


def write_schema(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SCHEMA, encoding="utf-8", newline="\n")
    return path


def project_json_vectors(*, connection, angle_records: list[dict]) -> int:
    """Project validated JSON angle vectors; JSON remains authoritative."""
    connection.execute(SCHEMA)
    count = 0
    for angle in angle_records:
        vector = angle.get("embedding")
        if not vector or len(vector) != 1536:
            continue
        connection.execute(
            """INSERT INTO angle_vectors
               (angle_id, run_id, embedding_profile, signature_hash, generated_at, embedding)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (angle_id) DO UPDATE SET
                 run_id=excluded.run_id, embedding_profile=excluded.embedding_profile,
                 signature_hash=excluded.signature_hash, generated_at=excluded.generated_at,
                 embedding=excluded.embedding""",
            (
                angle["angle_id"],
                angle["run_id"],
                angle.get("embedding_profile", "text-embedding-3-small:1536"),
                angle.get("signature_hash", ""),
                angle["generated_at"],
                vector,
            ),
        )
        count += 1
    return count
