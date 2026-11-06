import re, sys, glob, os
for fn in sorted(glob.glob(sys.argv[1] + '/T*.txt')):
    raw = open(fn, encoding='utf-8').read()
    header = raw.split('\n', 1)[0]
    cues = re.findall(r'(\d\d:\d\d:\d\d)\.\d+ --> [^\n]+\n(.*?)(?=\n\n|\Z)', raw, re.S)
    out, cur_spk, cur_t, buf = [], None, None, []
    for t, body in cues:
        body = body.strip().replace('\n', ' ')
        m = re.match(r'([^:]{1,60}):\s(.*)', body)
        spk, txt = (m.group(1), m.group(2)) if m else (cur_spk, body)
        if spk == cur_spk:
            buf.append(txt)
        else:
            if buf: out.append(f"[{cur_t}] {cur_spk}: " + ' '.join(buf))
            cur_spk, cur_t, buf = spk, t, [txt]
    if buf: out.append(f"[{cur_t}] {cur_spk}: " + ' '.join(buf))
    dst = fn.replace('.txt', '.compact.md')
    open(dst, 'w', encoding='utf-8').write(header + '\n\n' + '\n'.join(out))
    print(os.path.basename(dst), len(raw), '->', sum(len(x) for x in out))
