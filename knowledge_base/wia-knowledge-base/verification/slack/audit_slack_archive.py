"""Read the preserved Slack archive; write counts and evidence candidates only.

No Slack API calls or source-archive edits. Candidate matches are not verified
actions/sentiment: a reviewer must read the source and its thread.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
CORPUS = ROOT / 'frontend/corpus/slack'
PATTERNS = {
    'commitment': r"\b(I(?:'|’)ll|I will|we(?:'|’)ll|we will|can you|could you|please review|please send)\b",
    'completion_or_approval': r'\b(approved|completed|finished|looks good|all set|updated|fixed)\b',
    'deadline': r'\b(by (?:Monday|Tuesday|Wednesday|Thursday|Friday|tomorrow)|due|deadline|end of (?:day|week))\b',
    'client_signal': r'\b(thank you|thank you so much|frustrat\w*|confus\w*|concern\w*|struggling|happy with|excited)\b',
    'external_reference': r'https?://(?:docs\.google\.com|drive\.google\.com|app\.clickup\.com|(?:[\w-]+\.)?gohighlevel\.com|app\.leadlockpro\.com)',
}
report = {'review_date': '2026-10-19', 'mode': 'offline_archive_audit',
          'note': 'Observed raw payloads; pattern matches are candidates, not extracted facts.',
          'excluded': ['wia-ai-team-testing'], 'channels': [], 'candidates': {k: [] for k in PATTERNS}}
totals = Counter()
for path in sorted((CORPUS / 'raw').glob('*.json')):
    if path.stem == 'wia-ai-team-testing':
        continue
    parents = json.loads(path.read_text(encoding='utf-8-sig'))
    md = (CORPUS / f'{path.stem}.md').read_text(encoding='utf-8-sig')
    channel_id = re.search(r'Private channel · `([^`]+)`', md).group(1)
    messages = [m for p in parents for m in [p, *p.get('__replies', [])]]
    unique = {m['ts']: m for m in messages}
    counts = Counter()
    for msg in unique.values():
        for key in ('user', 'text', 'blocks', 'files', 'reactions', 'edited', 'bot_id', 'attachments'):
            counts[key] += bool(msg.get(key))
    files = [f for m in unique.values() for f in m.get('files', [])]
    days = [datetime.fromtimestamp(float(m['ts']), timezone.utc).isoformat() for m in unique.values()]
    declared = sum(p.get('reply_count', 0) for p in parents)
    actual = sum(len(p.get('__replies', [])) for p in parents)
    row = {'name': path.stem, 'channel_id': channel_id, 'parents': len(parents),
           'replies': actual, 'declared_replies': declared, 'unique_messages': len(unique),
           'duplicate_message_occurrences': len(messages) - len(unique),
           'first_utc': min(days), 'last_utc': max(days), 'field_presence': dict(counts),
           'unique_authors': len({m['user'] for m in unique.values() if m.get('user')}),
           'files_local_occurrences': sum(bool(f.get('__local')) for f in files),
           'files_over_cap_occurrences': sum(f.get('__skipped', {}).get('reason') == 'over cap' for f in files),
           'external_files_occurrences': sum(bool(f.get('__external')) for f in files),
           'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    report['channels'].append(row)
    for key in ('parents', 'replies', 'declared_replies', 'unique_messages',
                'duplicate_message_occurrences', 'files_local_occurrences', 'files_over_cap_occurrences'):
        totals[key] += row[key]
    for category, pattern in PATTERNS.items():
        hits = [m for m in unique.values() if re.search(pattern, m.get('text', ''), re.I)]
        # Keep a small spread across channels for manual review, with stable provenance.
        for msg in hits[:3]:
            root_ts = msg.get('thread_ts') or msg['ts']
            report['candidates'][category].append({
                'channel': path.stem, 'ts': msg['ts'], 'thread_ts': root_ts,
                'user': msg.get('user'), 'bot_id': msg.get('bot_id'),
                'excerpt': msg.get('text', '')[:900],
                'permalink': f"https://weddingindustryads.slack.com/archives/{channel_id}/p{msg['ts'].replace('.', '')}",
                'archive': path.relative_to(ROOT).as_posix(),
            })
report['totals'] = dict(totals)
output = OUT / 'archive_audit.json'
output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({'output': str(output), 'totals': report['totals'], 'channels': report['channels']}, indent=2))
