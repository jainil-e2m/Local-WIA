from pathlib import Path

from backend_pipeline.store import JsonStore


def test_store_does_not_overwrite_completed_artifact(tmp_path: Path):
    store = JsonStore(tmp_path)
    first = store.write_json("x.json", {"value": 1})
    second = store.write_json("x.json", {"value": 2})
    assert first == second
    assert store.read_json("x.json") == {"value": 1}
