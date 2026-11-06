import httpx, re, sys
env = open(r'C:\Users\KENIL\Desktop\wedding_industry_ads\WIA-Content-Atelier\backend\.env', encoding='utf-8').read()
key = re.search(r'^FATHOM_API_KEY=(.*)$', env, re.M).group(1).strip().strip('"\'')
c = httpx.Client(base_url='https://api.fathom.ai/external/v1/', headers={'X-Api-Key': key}, timeout=60)
for start, end in [('2026-06-01T00:00:00Z','2026-06-22T00:00:00Z'), ('2026-10-05T00:00:00Z','2026-10-20T00:00:00Z')]:
    cursor=None; n=0
    print(f'== window {start} .. {end}')
    while True:
        p={'created_after':start,'created_before':end}
        if cursor: p['cursor']=cursor
        r=c.get('meetings',params=p); r.raise_for_status(); b=r.json()
        for m in b.get('items',[]):
            n+=1
            print(' ', m.get('recording_start_time') or m.get('created_at'), '|', m.get('title') or m.get('meeting_title'), '|', m.get('url') or m.get('share_url'))
        cursor=b.get('next_cursor')
        if not cursor: break
    print('  total', n)
