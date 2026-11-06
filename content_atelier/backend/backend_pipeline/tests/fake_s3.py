"""An in-memory stand-in for the boto3 S3 client calls the artifact store makes (no network in the offline suites)."""
from __future__ import annotations

import io
from datetime import UTC, datetime

from botocore.exceptions import ClientError


def _error(code: str, status: int, operation: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}, "ResponseMetadata": {"HTTPStatusCode": status}}, operation)


class FakeS3:
    def __init__(self, bucket: str = "atelier-test", page_size: int = 1000):
        self.bucket, self.page_size = bucket, page_size
        self.objects: dict[str, tuple[bytes, datetime]] = {}
        self.calls: list[str] = []

    def _check(self, Bucket):
        if Bucket != self.bucket:
            raise _error("NoSuchBucket", 404, "bucket")

    def put_object(self, *, Bucket, Key, Body, **_):
        self._check(Bucket)
        self.calls.append("put")
        self.objects[Key] = (bytes(Body), datetime.now(UTC))
        return {}

    def head_object(self, *, Bucket, Key):
        self._check(Bucket)
        self.calls.append("head")
        if Key not in self.objects:
            raise _error("404", 404, "HeadObject")
        data, at = self.objects[Key]
        return {"ContentLength": len(data), "LastModified": at}

    def get_object(self, *, Bucket, Key):
        self._check(Bucket)
        self.calls.append("get")
        if Key not in self.objects:
            raise _error("NoSuchKey", 404, "GetObject")
        return {"Body": io.BytesIO(self.objects[Key][0])}

    def list_objects_v2(self, *, Bucket, Prefix="", Delimiter=None, ContinuationToken=None, **_):
        self._check(Bucket)
        self.calls.append("list")
        keys = sorted(k for k in self.objects if k.startswith(Prefix))
        entries, seen = [], set()
        for key in keys:
            rest = key[len(Prefix):]
            if Delimiter and Delimiter in rest:
                folder = Prefix + rest.split(Delimiter, 1)[0] + Delimiter
                if folder not in seen:
                    seen.add(folder)
                    entries.append(("prefix", folder))
            else:
                entries.append(("key", key))
        start = int(ContinuationToken or 0)
        page = entries[start:start + self.page_size]
        truncated = start + self.page_size < len(entries)
        return {"CommonPrefixes": [{"Prefix": v} for kind, v in page if kind == "prefix"],
                "Contents": [{"Key": v} for kind, v in page if kind == "key"],
                "IsTruncated": truncated, **({"NextContinuationToken": str(start + self.page_size)} if truncated else {})}
