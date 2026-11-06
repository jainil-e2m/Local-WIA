import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gptx
sys.stdout.reconfigure(encoding="utf-8")
convs = gptx.load()
cpre, npre, after = sys.argv[1], sys.argv[2], int(sys.argv[3])
for c in gptx.find(convs, cpre):
    ms = gptx.messages(c, all_nodes=False)
    for i, m in enumerate(ms):
        if m["id"].startswith(npre):
            for mm in ms[i:i+after]:
                print(f"\n==== [{mm['role']} {gptx.ts(mm['t'])} {mm['id'][:8]}]\n{mm['text'][:int(os.environ.get("ML","3500"))]}")
