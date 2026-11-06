import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gptx
sys.stdout.reconfigure(encoding="utf-8")
convs = gptx.load()
want = [
 ("6a296764","48c9328c","EMAIL sent to list 10 Jun 2026 (Whitney's final)"),
 ("6a3d3a29","e41f373b","REEL CAPTION posted 25 Jun 2026 (Whitney's final, pasted by her)"),
 ("6a3d3a29","21a9939a","EMAIL draft rewritten by Whitney herself 29 Jun 2026 ('You are very obtuse. Here's my edit')"),
 ("6a73993f","dc245172","REEL TRANSCRIPT recorded by Whitney 18 Aug 2026 (spoken register)"),
 ("6a721147","5b2364b0",None),
 ("6aa98079","3eb7f12d","EMAIL sent 15 Sep 2026 ('Below is what we settled on')"),
 ("6abeb98d","1d9f0000",None),
]
out=[]
for c_,n_,label in want:
    if not label: continue
    for c in gptx.find(convs,c_):
        for m in gptx.messages(c, all_nodes=True):
            if m["id"].startswith(n_):
                out.append(f"\n\n### {label}\n\n{m['text']}")
open(sys.argv[1],"w",encoding="utf-8").write("# Whitney Hodges: real finished content (verbatim from her ChatGPT history)\n"+"".join(out))
print(len(out))
