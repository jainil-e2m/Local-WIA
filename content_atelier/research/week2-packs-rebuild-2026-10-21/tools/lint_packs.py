import json, re, sys
pats = json.load(open(r'C:\Users\KENIL\Desktop\wedding_industry_ads\WIA-Content-Atelier\backend\knowledge_base\rejection-rules.patterns.json', encoding='utf-8'))['rules']
doc = open(sys.argv[1], encoding='utf-8').read().split('\n')
# Determine copy regions: lines under '## Email', '## Reel', '## Carousel' until '## Before you publish' or next '# '
region = None; copy_lines = []
for i, line in enumerate(doc):
    if line.startswith('# '): region = None
    if line.startswith('## Email') or line.startswith('## Reel') or line.startswith('## Carousel'):
        region = line
    elif line.startswith('## ') and not (line.startswith('## Email') or line.startswith('## Reel') or line.startswith('## Carousel')):
        region = None
    if region: copy_lines.append((i+1, region, line))
print('copy lines:', len(copy_lines))
hits = 0
for r in pats:
    try: rx = re.compile(r['pattern'], re.I)
    except re.error as e: print('bad pattern', r['id'], e); continue
    for n, reg, line in copy_lines:
        if r.get('applies_to') == 'email' and 'Email' not in reg: continue
        if line.startswith('**DATE') or line.startswith('**SEND') or line.startswith('**RECIP'): continue
        m = rx.search(line)
        if m:
            hits += 1
            print(f"{r['id']:6} {r['kind']:4} L{n} [{reg[:40]}] '{m.group(0)}' :: {line[:110]}")
# whole-doc em dash check
for i,l in enumerate(doc):
    if '\u2014' in l: print('EMDASH anywhere L', i+1, l[:100])
print('hits', hits)
