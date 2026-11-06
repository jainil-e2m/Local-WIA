"""Offline audit of bounded Calendar samples. Does not access Google or tokens."""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
initial = json.loads((ROOT / 'live_probe.json').read_text(encoding='utf-8'))
followup = json.loads((ROOT / 'followup_probe.json').read_text(encoding='utf-8'))
rows = {}
samples = []
calls = initial['calls'] + followup['calls']
for report_name, report in [('live_probe.json', initial), ('followup_probe.json', followup)]:
    for sample in report['event_samples']:
        events = sample['events']
        samples.append({'report': report_name, 'calendar_id': sample['calendar_id'],
                        'rows': len(events), 'pagination_complete': sample['pagination_complete']})
        for event in events:
            rows[(sample['calendar_id'], event['id'])] = event

events = list(rows.values())
ical = collections.defaultdict(set)
for (calendar_id, event_id), event in rows.items():
    if event.get('iCalUID'):
        # Keep source copies. This grouping is a candidate cross-calendar comparison,
        # not an automatic production merge; offsets can differ for the same instant.
        ical[event['iCalUID']].add(calendar_id)

audit = {
    'source': 'Google Calendar', 'offline_only': True,
    'http_statuses': dict(collections.Counter(str(c.get('http_status')) for c in calls)),
    'successful_gets': sum(c.get('ok', False) for c in calls),
    'discovered_calendars': len(initial['calendars']),
    'sampled_event_calendars': len({k[0] for k in rows}),
    'samples': samples,
    'raw_list_rows': sum(s['rows'] for s in samples),
    'unique_calendar_event_rows': len(rows),
    'statuses': dict(collections.Counter(e['status'] for e in events)),
    'recurring_occurrence_rows': sum(bool(e.get('recurring_event_id')) for e in events),
    'all_day_rows': sum('date' in (e.get('start') or {}) for e in events),
    'attendee_response_rows': dict(collections.Counter(a['response_status'] for e in events for a in e['attendees'])),
    'ical_uids_present_on_multiple_sampled_calendars': sum(len(v) > 1 for v in ical.values()),
    'calendar_event_rows_are_not_unique_meeting_or_client_counts': True,
    'notifications_registered': False, 'full_backfill': False,
    'frontend_calls_are_fictional': True,
}
(ROOT / 'local_audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
print(json.dumps(audit, indent=2))
