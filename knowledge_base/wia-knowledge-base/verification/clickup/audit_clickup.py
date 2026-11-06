"""Offline audit of current ClickUp verification reports and the frontend mock."""
from collections import Counter
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
reports = [json.loads((HERE / name).read_text(encoding='utf-8'))
           for name in ['live_probe.json', 'onboarding_probe.json']]
lists = [row for report in reports for row in report['list_samples']]
tasks = {t['id']: t for row in lists for t in row['tasks']}
all_tasks = list(tasks.values())

def resolve(field):
    value = field.get('value')
    if value is None:
        return None
    if field.get('type') == 'drop_down':
        for option in field.get('options', []):
            if str(value) in [str(option.get('id')), str(option.get('orderindex'))]:
                return option.get('name', '').strip()
    return value

def stats(rows):
    return {
        'tasks': len(rows),
        'status_labels': dict(Counter(t['status']['status'] for t in rows)),
        'status_types': dict(Counter(t['status']['type'] for t in rows)),
        'with_due_date': sum(bool(t['due_date']) for t in rows),
        'without_due_date': sum(not t['due_date'] for t in rows),
        'with_assignee': sum(bool(t['assignees']) for t in rows),
        'without_assignee': sum(not t['assignees'] for t in rows),
        'multiple_assignees': sum(len(t['assignees']) > 1 for t in rows),
        'with_description': sum(bool(t['description_characters']) for t in rows),
        'subtasks': sum(bool(t['parent']) for t in rows),
        'with_dependencies': sum(bool(t['dependencies']) for t in rows),
        'with_checklists': sum(bool(t['checklists']) for t in rows),
        'terminal_tasks_with_unresolved_checklists': [t['id'] for t in rows
             if t['status']['type'] in ['done', 'closed']
             and any((c.get('unresolved') or 0) > 0 for c in t['checklists'])],
        'with_tracked_time': sum(bool(t['time_spent_ms']) for t in rows),
        'with_estimate': sum(bool(t['time_estimate_ms']) for t in rows),
        'role_values': dict(Counter(str(resolve(f)) for t in rows for f in t['custom_fields']
                                   if f['name'] == 'Role' and f.get('value') is not None)),
    }

attendance = []
for row in lists:
    found = [t for t in row['tasks'] if 'attendance' in t['name'].lower()]
    if not found:
        continue
    urls = set()
    for t in found:
        # Only extract normal Markdown destination links, avoiding escaped display labels.
        urls.update(re.findall(r'\]\((https://docs\.google\.com/spreadsheets/[^)]+)\)',
                               t['description_excerpt']))
    attendance.append({'space': row['metadata']['space_name'],
                       'task_ids': [t['id'] for t in found],
                       'candidate_sheet_urls': sorted(urls),
                       'sheet_contents_fetched': False})

data = (ROOT / 'knowledge_base/wia-knowledge-base/frontend/src/data.ts').read_text(encoding='utf-8')
evidence = data.split('export const EVIDENCE:')[1].split('export const INITIAL_ACTIONS:')[0]
audit = {
    'http_status_counts': dict(Counter(str(c.get('http_status', 'network_error'))
                                      for r in reports for c in r['calls'])),
    'workspace': reports[0]['selected_workspace'],
    'space_count': len(reports[0]['spaces']),
    'folder_count_returned': sum(len(s['folders']) for s in reports[0]['hierarchy']),
    'folderless_list_count_returned': sum(len(s['folderless_lists']) for s in reports[0]['hierarchy']),
    'list_count_sampled': len(lists), 'unique_sampled_tasks': len(tasks),
    'sampled_lists_pagination_complete': all(row['pagination_complete'] for row in lists),
    'aggregate_task_stats': stats(all_tasks),
    'by_list': [{'id': row['metadata']['id'], 'name': row['metadata']['name'],
                 'space': row['metadata']['space_name'], 'folder': row['metadata']['folder_name'],
                 'hierarchy_task_count_reported': row['metadata']['task_count_reported'],
                 'field_names': [f['name'] for f in row['fields']],
                 **stats(row['tasks'])} for row in lists],
    'task_detail_count': sum(len(r['task_samples']) for r in reports),
    'comment_queries': sum('/comment' in c['path'] and c['path'].startswith('/task/')
                           for r in reports for c in r['calls']),
    'comments_returned': sum(s['comment_count_returned'] for r in reports for s in r['task_samples']),
    'thread_reply_requests': sum(c['path'].endswith('/reply') for r in reports for c in r['calls']),
    'attendance_candidates': attendance,
    'frontend_clickup_evidence_count': len(re.findall(r"kind: 'ClickUp'", evidence)),
    'frontend_clickup_evidence_lines': [i for i, line in enumerate(data.splitlines(), 1)
                                         if "kind: 'ClickUp'" in line and "name: 'ClickUp'" not in line],
    'frontend_clickup_connector_lines': [i for i, line in enumerate(data.splitlines(), 1)
                                          if "name: 'ClickUp'" in line],
    'scope_status': 'task_ownership_dates_status_hierarchy_fields_verified_sampled_comments_empty',
}
(HERE / 'local_audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k:v for k,v in audit.items() if k != 'attendance_candidates'}, indent=2))
