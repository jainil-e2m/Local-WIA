"""0.B7: the S3 implementation against a real S3-compatible endpoint (boto3 over HTTP).

Skipped unless ATELIER_TEST_S3_ENDPOINT names a throwaway server (a local moto or MinIO); the bucket is created and
emptied by the test. Run: ATELIER_TEST_S3_ENDPOINT=http://127.0.0.1:19000 python -m pytest backend_pipeline/tests/test_artifact_store_live.py
"""
from __future__ import annotations

import os
import uuid

import pytest

from backend_pipeline.artifacts import S3Backend, s3_client
from backend_pipeline.store import JsonStore

ENDPOINT = os.getenv("ATELIER_TEST_S3_ENDPOINT")
pytestmark = pytest.mark.skipif(not ENDPOINT, reason="Set ATELIER_TEST_S3_ENDPOINT to a throwaway S3-compatible server")


@pytest.fixture
def store():
    client = s3_client({"ATELIER_S3_ENDPOINT": ENDPOINT, "ATELIER_S3_ACCESS_KEY_ID": os.getenv("ATELIER_TEST_S3_KEY", "test"),
                        "ATELIER_S3_SECRET_ACCESS_KEY": os.getenv("ATELIER_TEST_S3_SECRET", "test"), "ATELIER_S3_REGION": "us-east-1"})
    bucket = "atelier-live-" + uuid.uuid4().hex[:10]
    client.create_bucket(Bucket=bucket)
    yield JsonStore(S3Backend(bucket, client, prefix="production"))
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            client.delete_object(Bucket=bucket, Key=obj["Key"])
    client.delete_bucket(Bucket=bucket)


def test_round_trip_listing_and_immutability_over_http(store):
    store.write_json("brief-runs/r1/cost_summary.json", {"total": 0.01})
    store.write_json("brief-runs/r1/cost_summary.json", {"total": 9})
    assert store.read_json("brief-runs/r1/cost_summary.json") == {"total": 0.01}
    store.write_bytes("source-originals/h.original", b"\x00\x01exact")
    with pytest.raises(ValueError):
        store.write_bytes("source-originals/h.original", b"other")
    for n in range(1100):  # past one listing page
        store.write_bytes(f"bulk/{n:04d}.bin", b"x")
    assert len(store.names("bulk")) == 1100
    assert store.names("brief-runs") == ["r1"] and store.json_names("brief-runs/r1") == ["brief-runs/r1/cost_summary.json"]
    assert store.exists("brief-runs/r1") and not store.exists("brief-runs/r2")
    assert store.modified("source-originals/h.original") > 0
    with pytest.raises(FileNotFoundError):
        store.read_json("nothing/here.json")
