import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gptx
sys.stdout.reconfigure(encoding="utf-8")
convs = gptx.load()
pres = sys.argv[2:]
out = open(sys.argv[1], "w", encoding="utf-8")
for pre in pres:
    for c in gptx.find(convs, pre):
        out.write(f"\n\n######## {c.get('title')}  [{(c.get('conversation_id') or c.get('id'))[:8]}]  {gptx.ts(c.get('create_time'))}\n")
        for m in gptx.messages(c, all_nodes=False):
            if m["role"] == "user" and m["text"].strip():
                t = m["text"]
                if len(t) > 6000: t = t[:6000] + " [...TRUNC]"
                out.write(f"\n>>> {gptx.ts(m['t'])} :: {t}\n")
