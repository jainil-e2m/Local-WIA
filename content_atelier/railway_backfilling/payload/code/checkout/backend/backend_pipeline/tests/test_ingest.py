from pathlib import Path

from backend_pipeline.ingest import parse_transcript


def test_parse_webvtt_and_keep_speaker(tmp_path: Path):
    source = tmp_path / "meeting.txt"
    source.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nWhitney: The landing page matters.\n", encoding="utf-8")
    parsed = parse_transcript(source, 1)
    assert parsed.source_format == "webvtt"
    assert parsed.spans[0].speaker == "Whitney"
    assert parsed.spans[0].text == "The landing page matters."
