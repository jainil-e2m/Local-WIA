"""Offline evidence/coverage audit; reads saved probe reports, makes no requests."""
from collections import Counter
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
live = json.loads((HERE / 'live_probe.json').read_text(encoding='utf-8'))
followup = json.loads((HERE / 'wia_recorder_probe.json').read_text(encoding='utf-8'))
source = ROOT / 'knowledge_base/wia-knowledge-base/frontend/src'
data = (source / 'data.ts').read_text(encoding='utf-8')
inline = live['observations']['inline_content']
checks = []
for check in followup['filter_checks']:
    matches = [m['recording_id'] for m in check['meetings']
               if m.get('recorded_by', {}).get('email') == check['recorded_by']]
    checks.append({'requested_recorder': check['recorded_by'],
                   'returned': check['returned_count'], 'matching_recordings': matches,
                   'mismatched_count': len(check['meetings']) - len(matches),
                   'returned_ids_equal_default_list':
                   {m['recording_id'] for m in check['meetings']} ==
                   {m['recording_id'] for m in live['meetings']}})
audit = {
    'source_reports': ['live_probe.json', 'wia_recorder_probe.json'],
    'http_status_counts': dict(Counter(str(c.get('http_status', 'network_error'))
                                      for r in [live, followup] for c in r['calls'])),
    'unique_default_recordings': len(live['meetings']),
    'inline_content_recordings': len(inline),
    'recordings_with_transcripts': sum(c['transcript_present'] for c in inline),
    'total_transcript_segments': sum(c['transcript_segments'] for c in inline),
    'segments_with_speaker': sum(c['segments_with_speaker'] for c in inline),
    'segments_with_timestamp': sum(c['segments_with_timestamp'] for c in inline),
    'segments_with_matched_email': sum(c['segments_with_matched_email'] for c in inline),
    'recordings_with_summary': sum(c['summary_present'] for c in inline),
    'action_items': sum(c['action_items_count'] for c in inline),
    'actions_with_assignee': sum(c['actions_with_assignee'] for c in inline),
    'actions_with_due_field': sum(c['actions_with_due_field'] for c in inline),
    'highlights': sum(c['highlights_count'] or 0 for c in inline),
    'crm_errors': list({c['crm_error'] for c in inline if c['crm_error']}),
    'recorder_filter_validation': checks,
    'frontend_fathom_evidence_count': len(re.findall(r"kind: 'Fathom'", data)),
    'frontend_fathom_evidence_lines': [i for i, line in enumerate(data.splitlines(), 1)
                                        if "kind: 'Fathom'" in line and "name: 'Fathom'" not in line],
    'frontend_fathom_connector_lines': [i for i, line in enumerate(data.splitlines(), 1)
                                         if "name: 'Fathom'" in line],
    'scope_status': 'transport_and_content_verified_WIA_client_call_coverage_unverified',
}
# The connector row also contains kind:'Fathom'; evidence count is the evidence section only.
evidence_section = data.split('export const EVIDENCE:')[1].split('export const INITIAL_ACTIONS:')[0]
audit['frontend_fathom_evidence_count'] = len(re.findall(r"kind: 'Fathom'", evidence_section))
(HERE / 'local_audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
print(json.dumps(audit, indent=2))
