import sys,json,re,collections,statistics as st
sys.path.insert(0,'.'); import render
sys.stdout.reconfigure(encoding='utf-8')
WE=re.compile(r"\b(we|our|us|WIA|LeadLock|ELEVATE|Accelerator)\b",re.I)
BAN=[(r"\u2014","em dash"),(r"\bit'?s not\b[^.]*\bit'?s\b","it's not X, it's Y"),(r"\bisn't\b[^.]{0,60}, it'?s\b","isn't X, it's Y"),(r"don'?t have an? [^.]{0,40} problem","X problem"),(r"\b(delve|tapestry|landscape|game-changing|hack|secret)\b","banned word")]
HEDGE=re.compile(r"\b(may|might|can|could|potentially|possibly|not necessarily|does not establish|not established|unverified|speaker labeled)\b",re.I)
for rid in sys.argv[1:]:
    cs,internal=render.cards(rid)
    o=render.load(rid)
    meta=o['meta']
    purposes=collections.Counter(c['purpose'].split(' / ')[0] for c in cs)
    titles=[c['title'] for c in cs]
    text=' '.join(c['title']+' '+c['core_perspective']+' '+c['why_it_matters'] for c in cs)
    bans=collections.Counter(n for p,n in BAN for _ in re.finditer(p,text,re.I))
    words=len(text.split())
    raw=o['output']
    if 'week_summary' in raw:
        lim=st.mean(len(a['verify_before_publishing']) for a in raw['angles']); drop=len(raw['considered_not_selected'])
    else:
        lim=st.mean(len(a['qualifiers'])+len(a['risks']) for a in raw['angles']); drop=0
    print(f"{rid}: angles={len(cs)} internal={len(internal)} purposes={dict(purposes)} WIA-in-title={sum(bool(WE.search(t)) for t in titles)}/{len(titles)} title_words={st.mean(len(t.split()) for t in titles):.1f} hedges_per_100w={100*len(HEDGE.findall(text))/words:.1f} limits_per_angle={lim:.1f} dropped_listed={drop} banned={dict(bans)} out_tokens={meta['completion_tokens']} cost=${meta['cost']:.3f}")
