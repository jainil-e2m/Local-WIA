"""Shared transaction receipts and typed errors for production/calendar operations."""

from psycopg.types.json import Jsonb

from .store import canonical_hash


class ProductionError(ValueError):
    def __init__(self, message, code="conflict", status=409):
        super().__init__(message)
        self.code = code
        self.status = status


def receipt(conn, request_id, actor, operation, payload):
    # Serialize identical request IDs, including requests racing before the first INSERT.
    conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", ("mutation:" + request_id,))
    row = conn.execute("SELECT * FROM mutation_receipts WHERE request_id=%s", (request_id,)).fetchone()
    digest = canonical_hash(payload)
    if row and (row["actor"] != actor or row["operation"] != operation or row["request_hash"] != digest):
        raise ProductionError("Request ID is already bound to another operation.", "request_id_conflict")
    return row["response"] if row else None


def save_receipt(conn, request_id, actor, operation, payload, response):
    conn.execute(
        """INSERT INTO mutation_receipts(request_id,actor,operation,request_hash,response)
        VALUES (%s,%s,%s,%s,%s)""",
        (request_id, actor, operation, canonical_hash(payload), Jsonb(response)),
    )
    return response
