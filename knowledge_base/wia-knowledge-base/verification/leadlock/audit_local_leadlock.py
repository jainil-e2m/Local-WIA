"""Audit existing local LeadLock evidence and the Knowledge Base mock, read-only.

Slack-shared app links are pointers, not proof of access or platform state.
No credentials are read and no external requests are made.
"""
from pathlib import Path
from collections import Counter
import json
import re

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
src = (ROOT / 'knowledge_base/wia-knowledge-base/frontend/src/data.ts').read_text(encoding='utf-8')
sections = {}
for label, following in [('EVIDENCE', 'INITIAL_ACTIONS'), ('INVOICES', 'EVENTS')]:
    start = src.index(f'export const {label}')
    end = src.index(f'export const {following}', start)
    sections[label] = src[start:end]
report = {'review_date': '2026-10-19', 'mode': 'local_archive_and_frontend_audit',
          'frontend': {'highlevel_evidence_rows': len(re.findall(r"kind: 'HighLevel'", sections['EVIDENCE'])),
                       'fictional_invoice_rows': len(re.findall(r"id: 'INV-", sections['INVOICES'])),
                       'invoice_statuses': dict(Counter(re.findall(r"status: '([^']+)'", sections['INVOICES']))),
                       'note': 'Fictional fixtures only; client account/support/outcome additions are documented but not implemented.'},
          'slack_account_references': [], 'note': 'Location IDs and URLs below are observed pointers, not validated account mappings.'}
pattern = re.compile(r'https://app\.leadlockpro\.com/(?:v2/)?location/([A-Za-z0-9]+)(?:/[^\s<>|]*)?')
for p in sorted((ROOT / 'frontend/corpus/slack/raw').glob('*.json')):
    if p.stem == 'wia-ai-team-testing':
        continue
    rows = json.loads(p.read_text(encoding='utf-8-sig'))
    for parent in rows:
        for message in [parent, *parent.get('__replies', [])]:
            for match in pattern.finditer(message.get('text', '')):
                report['slack_account_references'].append({'channel': p.stem,
                    'message_ts': message['ts'], 'location_id': match[1],
                    'url': match[0], 'archive': p.relative_to(ROOT).as_posix()})
scope_path = ROOT / 'frontend/corpus/ghl-scopes.tsv'
report['historical_scope_catalogue'] = {'file': scope_path.relative_to(ROOT).as_posix(),
    'scope_names': [line.split('\t')[0] for line in scope_path.read_text(encoding='utf-8-sig').splitlines() if line.strip()],
    'note': 'Picker catalogue captured in September; not the grants on the present token.'}
report['archived_marketing_email_bodies'] = len(list((ROOT / 'frontend/corpus/emails/raw').glob('*')))
report['unique_referenced_location_ids'] = sorted({x['location_id'] for x in report['slack_account_references']})
(OUT / 'local_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'frontend': report['frontend'],
    'account_link_occurrences': len(report['slack_account_references']),
    'unique_referenced_location_ids': report['unique_referenced_location_ids'],
    'archived_marketing_email_bodies': report['archived_marketing_email_bodies']}, indent=2))
