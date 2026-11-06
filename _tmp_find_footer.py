import pathlib

p = pathlib.Path(r"C:\Users\Jainil Trivedi\Desktop\Wedding_Industry_Ads\WIA-Blueprint-v0.html")
text = p.read_text(encoding="utf-8")

old = (
    'children:[C.jsxs("span",{className:"text-[10px] text-white/40",children:["Version ",Vs(Ln,["version"])," \u00b7 ",Vs(Ln,["date"])," \u00b7 ",Vs(Ln,["classification"])]}),'
    'Array.isArray(Ln.sourceBasis)&&Ln.sourceBasis.length>0&&C.jsx("span",{className:"text-[10px] text-white/40",children:Ln.sourceBasis.join(" \u00b7 ")}),'
    'C.jsx("a",'
)
new = 'children:[C.jsx("a",'

count = text.count(old)
print("match_count", count)
if count != 1:
    raise SystemExit(f"expected exactly 1 match, got {count}")

p.write_text(text.replace(old, new, 1), encoding="utf-8")
print("updated")
