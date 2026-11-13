"""Offline Gmail/Drive evidence audit. No network calls; no token values output."""
from pathlib import Path
from collections import Counter
import json
import re

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=HERE.parents[3]
gmail=json.loads((BASE/'gmail/live_probe.json').read_text(encoding='utf-8'))
drive=json.loads((BASE/'drive/live_probe.json').read_text(encoding='utf-8'))
follow=json.loads((HERE/'followup_probe.json').read_text(encoding='utf-8'))
refresh=json.loads((HERE/'refresh_probe.json').read_text(encoding='utf-8'))
g_calls=gmail['calls']+[c for c in follow['calls'] if 'gmail.googleapis.com' in c['endpoint']]
d_calls=drive['calls']+[c for c in follow['calls'] if 'gmail.googleapis.com' not in c['endpoint']]
messages={m['id']:m for m in gmail['messages']}
for thread in follow['threads']:
    messages.update({m['id']:m for m in thread['messages']})
if follow.get('attachment_message'):
    m=follow['attachment_message'];messages[m['id']]=m
data=(ROOT/'knowledge_base/wia-knowledge-base/frontend/src/data.ts').read_text(encoding='utf-8')
evidence=data.split('export const EVIDENCE:')[1].split('export const INITIAL_ACTIONS:')[0]
events=[]
for m in gmail['messages']:
    if m.get('from')!='Dubsado <noreply@dubsado.com>':
        continue
    kind='payment_reported' if ' has paid ' in m['subject'] else 'contract_signing_reported' if ' has signed ' in m['subject'] else 'unknown'
    urls=re.findall(r'https?://[^\s<>"\]\)]+',m['body_excerpt'])
    targets=[u.rstrip('.,;') for u in urls if '/public/invoices/' in u or '/public/contract/view/' in u]
    events.append({'message_id':m['id'],'subject':m['subject'],'candidate_event_type':kind,
                   'source_date_header':m['date'],'normalised_event_links':targets,
                   'target_content_fetched':False})

def summary(calls):
    return dict(Counter(str(c.get('http_status','network_error')) for c in calls))

ga={
 'mailbox':gmail['profile']['emailAddress'],'http_status_counts':summary(g_calls),
 'initial_message_body_samples':len(gmail['messages']),'unique_message_samples_with_followup':len(messages),
 'draft_ids':[m['id'] for m in messages.values() if 'DRAFT' in m['label_ids']],
 'sent_ids':[m['id'] for m in messages.values() if 'SENT' in m['label_ids']],
 'initial_thread_metadata_sizes':[t['messages_returned'] for t in gmail['threads']],
 'full_thread_sizes':[t['total_messages'] for t in follow['threads']],
 'dubsado_event_samples':events,'attachment_read':follow['attachment'],
 'searches_have_more_pages':all(s['additional_page_present'] for s in gmail['searches']),
 'search_count_is_estimate_not_complete':True,
 'frontend_gmail_evidence_count':len(re.findall(r"kind: 'Gmail'",evidence)),
 'notifications_verified':False,'full_financial_ledger_verified':False,
}
documents=drive['documents']+follow['documents']
da={
 'drive_user':drive['user']['emailAddress'],'http_status_counts':summary(d_calls),
 'unique_metadata_files':len(drive['files']),
 'metadata_mime_types':dict(Counter(f['mimeType'] for f in drive['files'])),
 'name_searches_have_more_pages':all(s['additional_page_present'] for s in drive['searches']),
 'folder_child_samples':drive['folder_reads'],
 'unique_document_content_samples':len({d['id'] for d in documents}),
 'document_titles':[d['title'] for d in documents],
 'attendance_sheet_count':len(drive['sheets']),
 'attendance_first_tab_rows':[{ 'title':s['title'],'range':s['sample_range'],
    'rows_returned':len(s['sample_values'] or []),'timezone':s['timezone']} for s in drive['sheets']],
 'attendance_session_rows':[{'title':s['title'],'range':s['range'],
    'rows_excluding_header':max(0,len(s['values'] or [])-1)} for s in follow['sheet_sessions']],
 'frontend_drive_evidence_count':len(re.findall(r"kind: 'Drive'",evidence)),
 'notifications_verified':False,'archive_completeness_verified':False,
}
for target,value in [('gmail',ga),('drive',da)]:
    (BASE/target/'local_audit.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
all_calls=g_calls+d_calls
print(json.dumps({'source_GET_statuses':summary(all_calls),'gmail_GETs':len(g_calls),'drive_GETs':len(d_calls),
 'unique_message_samples':len(messages),'documents':da['unique_document_content_samples'],
 'attendance_session_rows':da['attendance_session_rows'],
 'drafts':len(ga['draft_ids']),'frontend_gmail':ga['frontend_gmail_evidence_count'],
 'frontend_drive':da['frontend_drive_evidence_count'],'oauth_refresh':refresh['result'],
 'drive_mime_types':da['metadata_mime_types']},indent=2))
