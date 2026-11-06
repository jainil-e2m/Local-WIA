"""Bounded local extraction. Provider URLs are never downloaded by this module."""
from __future__ import annotations

import io
from contextlib import closing
from pathlib import Path
import subprocess
import tempfile
import zipfile
from xml.etree import ElementTree
from psycopg.types.json import Jsonb


class UnsupportedAsset(Exception):
    pass


def ocr_image(image):
    if image.width * image.height > 40_000_000:
        raise ValueError('Image exceeds the 40 megapixel extraction limit')
    with tempfile.TemporaryDirectory(prefix='atelier-ocr-') as folder:
        path = Path(folder) / 'page.png'
        image.convert('RGB').save(path)
        result = subprocess.run(['tesseract', str(path), 'stdout', '--dpi', '150', 'tsv'],
                                check=True, capture_output=True, timeout=120, text=True)
    import csv
    rows = list(csv.DictReader(io.StringIO(result.stdout), delimiter='\t'))
    groups = {}
    for row in rows:
        if row['text'].strip():
            key = (row['block_num'], row['par_num'], row['line_num'])
            groups.setdefault(key, []).append(row)
    entries = []
    for words in groups.values():
        entries.append({'text': ' '.join(w['text'] for w in words), 'extraction_method': 'ocr',
            'locator': {'boxes': [{'x': int(w['left']), 'y': int(w['top']), 'width': int(w['width']),
                                   'height': int(w['height']), 'confidence': float(w['conf'])} for w in words]}})
    return entries


def extract(data, mime, filename, settings):
    if mime.startswith('video/'):
        raise UnsupportedAsset('Video content is represented by its original provider link')
    if mime.startswith('text/') or mime == 'application/json':
        text = data.decode('utf-8-sig')
        return [{'text': line, 'locator': {'line': i}, 'extraction_method': 'text'}
                for i, line in enumerate(text.splitlines(), 1) if line.strip()]
    if mime == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 50 * 1024 * 1024:
                raise ValueError('Expanded DOCX exceeds the extraction limit')
            xml = archive.read('word/document.xml')
        root = ElementTree.fromstring(xml)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        return [{'text': ''.join(p.itertext()), 'locator': {'paragraph': i}, 'extraction_method': 'docx'}
                for i, p in enumerate(root.findall('.//w:p', ns), 1)]
    if mime == 'application/pdf':
        import pypdfium2 as pdfium
        entries = []
        with closing(pdfium.PdfDocument(data)) as document:
            if len(document) > 300:
                raise ValueError('PDF exceeds the 300 page extraction limit')
            for i, page in enumerate(document):
                with closing(page):
                    with closing(page.get_textpage()) as textpage:
                        text = textpage.get_text_range()
                    if text.strip():
                        entries.extend({'text': line, 'locator': {'page': i + 1, 'line': j}, 'extraction_method': 'pdf'}
                                       for j, line in enumerate(text.splitlines(), 1) if line.strip())
                    else:
                        width, height = page.get_size()
                        if width * height * (150 / 72) ** 2 > 40_000_000:
                            raise ValueError('Rendered PDF page exceeds the 40 megapixel extraction limit')
                        with closing(page.render(scale=150 / 72)) as bitmap:
                            for entry in ocr_image(bitmap.to_pil()):
                                entry['locator']['page'] = i + 1
                                entries.append(entry)
        return entries
    if mime.startswith('image/'):
        from PIL import Image, ImageOps
        Image.MAX_IMAGE_PIXELS = 40_000_000
        with Image.open(io.BytesIO(data)) as image:
            return ocr_image(ImageOps.exif_transpose(image))
    if mime.startswith('audio/'):
        import av
        from faster_whisper import WhisperModel
        with av.open(io.BytesIO(data)) as container:
            if container.duration is None or container.duration / av.time_base > settings.max_audio_seconds:
                raise ValueError('Audio duration is unknown or exceeds the transcription limit')
        with tempfile.TemporaryDirectory(prefix='atelier-audio-') as folder:
            path = Path(folder) / 'audio'
            path.write_bytes(data)
            model = WhisperModel(settings.audio_model, device='cpu', compute_type='int8')
            segments, _ = model.transcribe(str(path), vad_filter=True)
            return [{'text': s.text, 'start_ms': round(s.start * 1000), 'end_ms': round(s.end * 1000),
                     'locator': {'segment': s.id}, 'extraction_method': 'asr'} for s in segments]
    raise UnsupportedAsset(f'Unsupported attachment type: {mime}')


def process(repo, asset_id):
    from .normalize import record
    from .repository import lock
    from ..store import canonical_hash
    with repo.connection() as conn:
        asset = conn.execute('SELECT * FROM intake_assets WHERE asset_id=%s', (asset_id,)).fetchone()
    if asset['status'] in {'completed', 'unsupported'}:
        return
    extraction_key = canonical_hash([asset['content_hash'], asset['mime_type'], 'local-v1', repo.intake.audio_model])
    path = f'intake/extracted/{extraction_key}.json'
    if repo.store.exists(path):
        entries = repo.store.read_json(path)['entries']
    else:
        try:
            data = repo.store.read_bytes(asset['raw_artifact'])
            import hashlib
            if hashlib.sha256(data).hexdigest() != asset['content_hash']:
                raise ValueError('Attachment bytes failed integrity verification')
            entries = extract(data, asset['mime_type'], asset['filename'], repo.intake)
        except UnsupportedAsset as exc:
            with repo.connection() as conn:
                conn.execute("UPDATE intake_assets SET status='unsupported',metadata=metadata || %s WHERE asset_id=%s",
                             (Jsonb({'exclusion_reason': str(exc)}), asset_id))
            return
        if not any(e['text'].strip() for e in entries):
            raise ValueError('Attachment extraction returned no readable text')
        repo.store.write_json(path, {'entries': entries, 'extractor_version': 'local-v1'})
    with repo.connection() as conn:
        lock(conn)
        parent = conn.execute("""SELECT s.* FROM intake_sources s JOIN intake_revisions r USING(source_id)
            WHERE r.revision_id=%s""", (asset['revision_id'],)).fetchone()
        upstream = 'attachment:' + asset['provider_file_id']
        sid = repo.source(conn, parent['connection_id'], upstream, 'attachment', asset['filename'],
                          url=asset['metadata'].get('permalink'), metadata={'parent_source_id': parent['source_id']})
        digest = canonical_hash([asset['content_hash'], entries])
        normalized = record(sid, asset['filename'], 'attachment', entries,
                            url=asset['metadata'].get('permalink'), content_hash=digest)
        rid = repo.revision(conn, sid, digest, asset['raw_artifact'], normalized)
        # Required attachment indexing must also gate its parent bucket's completion.
        for membership in conn.execute('SELECT m.* FROM intake_membership m JOIN intake_buckets b USING(bucket_id) WHERE m.revision_id=%s AND b.status<>%s', (asset['revision_id'], 'completed')).fetchall():
            from ..repository import insert
            insert(conn, 'intake_membership', {'bucket_id': membership['bucket_id'], 'revision_id': rid}, conflict=True)
        conn.execute("UPDATE intake_assets SET source_id=%s,status='completed' WHERE asset_id=%s", (sid, asset_id))
