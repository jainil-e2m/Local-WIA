import re, sys
sys.stdout.reconfigure(encoding="utf-8")
# Constructions WIA's team flagged as "AI phrases" in ChatGPT (Jul-Sep 2026)
P = {
 "not-X-it's-Y (next sentence)": r"\b(isn't|is not|wasn't|aren't|doesn't|don't|didn't)\b[^.?!]{0,80}[.?!]\s+(It's|It is|It was|They're|It|They)\b",
 "not because X but because Y": r"\bnot because\b",
 "the goal isn't / the real X is": r"\b(the goal isn't|the real (goal|win|value|question|skill) (is|was))\b",
 "you don't have an X problem": r"you don't have an? \w+ problem",
 "staccato (3+ sentences <=4 words in a row)": None,
 "em dash": "\u2014",
}
text = open(sys.argv[1], encoding="utf-8").read()
for name, pat in P.items():
    if pat is None:
        sents = re.split(r"(?<=[.!?])\s+", text)
        run=0; hits=0
        for s in sents:
            w=len(s.split())
            run = run+1 if 0<w<=4 else 0
            if run==3: hits+=1
        print(f"{name}: {hits}")
    else:
        print(f"{name}: {len(re.findall(pat, text, re.I))}")
print("words:", len(text.split()))
