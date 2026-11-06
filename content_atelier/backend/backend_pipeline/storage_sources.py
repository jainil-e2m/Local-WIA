"""Local admission and reconstruction. Every evidence range resolves into SQL originals."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .models import Span, Transcript
from .prepare import packet_for, read_source
from .store import canonical_hash


def capture(path: Path, week_index: int, ordinal: int, *, source_id: str | None = None):
    if path.name == 'transcript.raw.json':
        from .fathom_sources import capture_fathom
        return capture_fathom(path, week_index, ordinal)
    raw, source = read_source(path, week=week_index, meeting_ref=f"m{ordinal}", first_ref=1, source_id=source_id)
    text = raw.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
    lines = text.splitlines(keepends=True)
    offsets, cursor = [], 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line)
    passages = []
    for turn in source['turns']:
        start = offsets[turn['source_lines'][0][0] - 1]
        end = offsets[turn['source_lines'][-1][0] - 1] + len(turn['source_lines'][-1][1])
        if text[start:end] != turn['text']:
            raise ValueError("Original passage offsets do not round-trip")
        passage_id = f"{source['source_id']}:span:{turn['ordinal']}"
        passages.append({"passage_id": passage_id, "ordinal": turn['ordinal'],
                         "start": start, "end": end,
                         **{k: turn.get(k) for k in ('kind', 'start_ms', 'end_ms', 'speaker', 'cue_settings')}})
    if not passages:
        raise ValueError("Refusing an empty transcript")
    transcript_id = 'transcript_' + canonical_hash({'source': source['source_id'], 'raw': source['raw_sha256']})[:24]
    return {"transcript_id": transcript_id, "source_type": "zoom", "upstream_id": source['source_id'],
            "title": path.name, "original_text": text, "content_hash": source['raw_sha256'],
            "passage_map": passages,
            "source_metadata": {"legacy_source_id": source['source_id'], "packet_metadata": source['metadata'],
                                "file_order": ordinal, "week_index": week_index, "normalized_sha256": hashlib.sha256(text.encode()).hexdigest()}}


def chunks(record, max_characters=2400):
    # Consecutive whole turns, limited by size and a 90 second conversational gap.
    # No cutting quotations; an unusually large turn remains a single chunk.
    groups, group, size, last = [], [], 0, None
    for p in record['passage_map']:
        value = record['original_text'][p['start']:p['end']]
        gap = last is not None and p['start_ms'] is not None and p['start_ms'] - last > 90_000
        if group and (size + len(value) > max_characters or gap):
            groups.append(group); group, size = [], 0
        group.append(p); size += len(value)
        last = p['end_ms'] if p['end_ms'] is not None else p['start_ms']
    if group:
        groups.append(group)
    result = []
    for group in groups:
        body = '\n'.join(record['original_text'][p['start']:p['end']] for p in group)
        contextual = f"Source: {record['title']}\n" + body
        refs = [{"passage_id": p['passage_id'], "start": p['start'], "end": p['end']} for p in group]
        digest = canonical_hash({"text": contextual, "passages": refs})
        result.append({"chunk_id": 'chunk_' + canonical_hash([record['transcript_id'], digest])[:24],
                       "chunk_text": contextual, "passage_refs": refs, "content_hash": digest})
    return result


def reconstruct(records):
    transcripts, sources, refs = [], [], {}
    for i, record in enumerate(records, 1):
        metadata = record['source_metadata']
        # Documents chosen by window or set need not come from a weekly admission: the week and the packet header are
        # derived from what the document itself holds (plan 1.B13).
        metadata = {'legacy_source_id': record['upstream_id'] or record['transcript_id'], 'week_index': 0,
                    'packet_metadata': {'filename_label': record['title'], 'name': record['title'],
                                        'date': record['occurred_at'].date().isoformat() if record.get('occurred_at') else None,
                                        'timezone': 'UTC', 'status': 'document_intake'}, **metadata}
        if hashlib.sha256(record['original_text'].encode()).hexdigest()!=metadata['normalized_sha256']:
            raise ValueError('Stored original text failed its admitted integrity hash')
        for ordinal,p in enumerate(record['passage_map']):
            if p['ordinal']!=ordinal or not 0<=p['start']<p['end']<=len(record['original_text']):
                raise ValueError('Stored passage map is not a valid ordered view of its original')
        legacy_id = metadata['legacy_source_id']
        # JSONB preserves values but not insertion order. The calibrated request
        # renders this object as text, so retain the reader's exact header order
        # to preserve reusable request fingerprints across the SQL transition.
        packet_metadata = metadata['packet_metadata']
        header_keys = ('filename_label','name','date','weekday','timezone','status')
        delivery_metadata = {key:packet_metadata[key] for key in header_keys if key in packet_metadata}
        delivery_metadata.update({key:packet_metadata[key] for key in sorted(set(packet_metadata)-set(header_keys))})
        spans, turns = [], []
        for p in record['passage_map']:
            text = record['original_text'][p['start']:p['end']]
            ref = f"m{i}.t{p['ordinal'] + 1:04d}"
            refs[ref] = p['passage_id']
            spans.append(Span(span_id=p['passage_id'], source_id=legacy_id, ordinal=p['ordinal'], text=text,
                              speaker=p['speaker'], start_seconds=p['start_ms']/1000 if p['start_ms'] is not None else None,
                              end_seconds=p['end_ms']/1000 if p['end_ms'] is not None else None))
            turns.append({**p, "text": text, "ref": ref})
        transcripts.append(Transcript(source_id=legacy_id, week_index=metadata['week_index'], path=record['title'],
                                      content_hash=record['content_hash'], spans=spans,
                                      source_format=('timestamped_text' if record['source_type']=='fathom' else
                                                     'webvtt' if any(p['kind']=='cue' for p in record['passage_map']) else 'plain_text'),
                                      source_metadata=delivery_metadata))
        sources.append({"meeting_ref": f"m{i}", "metadata": delivery_metadata, "turns": turns})
    return transcripts, packet_for(sources), refs
