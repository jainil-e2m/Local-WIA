"""Parse Whitney's ChatGPT export (data only) into indexed, readable text.

Usage:
  python -I gptx.py index                -> out/index.tsv (all conversations)
  python -I gptx.py dump <id-prefix>...  -> out/conv_<id>.md (active-branch + all nodes)
  python -I gptx.py grep <regex> [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--role user|assistant] [--ctx N]
"""
import json, sys, re, os, datetime as dt
from pathlib import Path

EXPORT = Path(r"C:\Users\KENIL\Desktop\wedding_industry_ads\gpt_export")
OUT = Path(__file__).resolve().parent.parent / "out"
OUT.mkdir(exist_ok=True)

def load():
    convs = []
    for i in range(4):
        p = EXPORT / f"conversations-00{i}.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        for c in data:
            c["_file"] = p.name
            convs.append(c)
    return convs

def ts(t):
    if not t:
        return ""
    return dt.datetime.fromtimestamp(float(t), dt.timezone.utc).strftime("%Y-%m-%d %H:%M")

def part_text(p):
    if isinstance(p, str):
        return p
    if isinstance(p, dict):
        ct = p.get("content_type")
        if ct == "image_asset_pointer":
            return f"[image {p.get('asset_pointer','')}]"
        for k in ("text", "content"):
            if isinstance(p.get(k), str):
                return p[k]
        return f"[{ct or 'part'}]"
    return str(p)

def msg_text(m):
    c = m.get("content") or {}
    ct = c.get("content_type")
    if "parts" in c and c["parts"] is not None:
        return "\n".join(part_text(p) for p in c["parts"])
    if ct in ("code", "execution_output"):
        return c.get("text", "")
    if ct == "tether_quote":
        return f"[quote {c.get('title','')} {c.get('url','')}]\n{c.get('text','')}"
    if ct == "tether_browsing_display":
        return c.get("result", "") or ""
    if ct == "user_editable_context":
        return "[user_editable_context]\n" + (c.get("user_profile") or "") + "\n" + (c.get("user_instructions") or "")
    if "text" in c:
        return c.get("text") or ""
    return f"[{ct}]"

def active_path(c):
    mp = c["mapping"]
    node = c.get("current_node")
    path = []
    while node and node in mp:
        path.append(node)
        node = mp[node].get("parent")
    return list(reversed(path))

def ordered_all(c):
    """All nodes in DFS order from root (captures non-active branches too)."""
    mp = c["mapping"]
    roots = [k for k, v in mp.items() if not v.get("parent") or v.get("parent") not in mp]
    out = []
    kidmap = {}
    for k, v in mp.items():
        p = v.get("parent")
        if p in mp:
            kidmap.setdefault(p, []).append(k)
    def walk(k, depth):
        out.append((k, depth))
        kids = list(dict.fromkeys((mp[k].get("children") or []) + kidmap.get(k, [])))
        kids = sorted(kids, key=lambda x: (mp.get(x, {}).get("message") or {}).get("create_time") or 0)
        for ch in kids:
            if ch in mp:
                walk(ch, depth + (1 if len(kids) > 1 else 0))
    for r in roots:
        walk(r, 0)
    return out

def messages(c, all_nodes=False):
    mp = c["mapping"]
    act = set(active_path(c))
    seq = ordered_all(c) if all_nodes else [(k, 0) for k in active_path(c)]
    res = []
    for k, d in seq:
        m = mp[k].get("message")
        if not m:
            continue
        role = (m.get("author") or {}).get("role")
        txt = msg_text(m)
        meta = m.get("metadata") or {}
        if role == "system" and not txt.strip():
            continue
        if meta.get("is_visually_hidden_from_conversation") and not txt.strip():
            continue
        att = [a.get("name") for a in (meta.get("attachments") or [])]
        res.append(dict(id=k, role=role, name=(m.get("author") or {}).get("name"), t=m.get("create_time"),
                        text=txt, active=k in act, depth=d, attachments=att,
                        ctype=(m.get("content") or {}).get("content_type"),
                        recipient=m.get("recipient")))
    return res

def cmd_index(convs):
    rows = []
    for c in convs:
        n_user = sum(1 for v in c["mapping"].values() if (v.get("message") or {}).get("author", {}).get("role") == "user")
        rows.append((ts(c.get("create_time")), ts(c.get("update_time")), c.get("conversation_id") or c.get("id"),
                     c.get("_file"), str(n_user), (c.get("title") or "").replace("\t", " "),
                     c.get("gizmo_id") or "", c.get("conversation_template_id") or ""))
    rows.sort()
    with open(OUT / "index.tsv", "w", encoding="utf-8") as f:
        f.write("created\tupdated\tid\tfile\tuser_turns\ttitle\tgizmo\ttemplate\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    print(len(rows), "conversations ->", OUT / "index.tsv")

def find(convs, prefix):
    return [c for c in convs if (c.get("conversation_id") or c.get("id") or "").startswith(prefix)]

def cmd_dump(convs, prefixes, all_nodes=True):
    for pre in prefixes:
        for c in find(convs, pre):
            cid = c.get("conversation_id") or c.get("id")
            lines = [f"# {c.get('title')}", f"id: {cid}  file: {c['_file']}  created: {ts(c.get('create_time'))}  updated: {ts(c.get('update_time'))}  gizmo: {c.get('gizmo_id')}", ""]
            for i, m in enumerate(messages(c, all_nodes=all_nodes)):
                if m["role"] == "tool" and m["ctype"] not in ("text", "multimodal_text"):
                    body = m["text"][:1500]
                else:
                    body = m["text"]
                flag = "" if m["active"] else " [NON-ACTIVE BRANCH]"
                att = f" attachments={m['attachments']}" if m["attachments"] else ""
                lines.append(f"\n----- [{i}] {m['role']}{'/'+m['name'] if m['name'] else ''} {ts(m['t'])} node={m['id'][:8]} depth={m['depth']}{flag}{att} ctype={m['ctype']} -> {m['recipient']}")
                lines.append(body)
            p = OUT / f"conv_{cid}.md"
            p.write_text("\n".join(lines), encoding="utf-8")
            print("wrote", p, len(lines))

def cmd_grep(convs, pattern, frm=None, to=None, role=None, ctx=300):
    rx = re.compile(pattern, re.I)
    hits = 0
    for c in sorted(convs, key=lambda c: c.get("create_time") or 0):
        cid = c.get("conversation_id") or c.get("id")
        for m in messages(c, all_nodes=True):
            d = ts(m["t"])[:10]
            if frm and d and d < frm: continue
            if to and d and d > to: continue
            if role and m["role"] != role: continue
            for mm in rx.finditer(m["text"] or ""):
                s = max(0, mm.start() - ctx); e = min(len(m["text"]), mm.end() + ctx)
                snippet = m["text"][s:e].replace("\n", " / ")
                print(f"{d} {cid[:8]} {m['role']} node={m['id'][:8]} [{(c.get('title') or '')[:50]}] :: ...{snippet}...")
                hits += 1
                break
    print("hits:", hits, file=sys.stderr)


def cmd_compact(convs, prefixes, alen=500):
    """Active-branch dump: user messages in full, assistant text messages truncated to alen chars."""
    for pre in prefixes:
        for c in find(convs, pre):
            cid = c.get("conversation_id") or c.get("id")
            lines = [f"# {c.get('title')}", f"id: {cid} created {ts(c.get('create_time'))} updated {ts(c.get('update_time'))} gizmo {c.get('gizmo_id')}"]
            for i, m in enumerate(messages(c, all_nodes=False)):
                if m["role"] == "user":
                    att = f" ATT={m['attachments']}" if m["attachments"] else ""
                    lines.append(f"\n>>> USER {ts(m['t'])} node={m['id'][:8]}{att}\n{m['text']}")
                elif m["role"] == "assistant" and m["ctype"] == "text" and m["text"].strip():
                    t = m["text"]
                    lines.append(f"\n--- asst {ts(m['t'])} node={m['id'][:8]} len={len(t)}\n{t[:alen]}{' [...]' if len(t)>alen else ''}")
            p = OUT / f"cmp_{cid[:8]}.md"
            p.write_text("\n".join(lines), encoding="utf-8")
            print("wrote", p.name, sum(len(x) for x in lines))

def cmd_node(convs, cpre, npre):
    for c in find(convs, cpre):
        for m in messages(c, all_nodes=True):
            if m["id"].startswith(npre):
                print(f"[{m['role']} {ts(m['t'])} {m['id']}]\n{m['text']}\n")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    convs = load()
    a = sys.argv[1:]
    if a[0] == "index":
        cmd_index(convs)
    elif a[0] == "dump":
        cmd_dump(convs, a[1:])
    elif a[0] == "compact":
        cmd_compact(convs, a[1:])
    elif a[0] == "node":
        cmd_node(convs, a[1], a[2])
    elif a[0] == "grep":
        pat = a[1]; kw = {}
        rest = a[2:]
        i = 0
        while i < len(rest):
            if rest[i] == "--from": kw["frm"] = rest[i+1]; i += 2
            elif rest[i] == "--to": kw["to"] = rest[i+1]; i += 2
            elif rest[i] == "--role": kw["role"] = rest[i+1]; i += 2
            elif rest[i] == "--ctx": kw["ctx"] = int(rest[i+1]); i += 2
            else: i += 1
        cmd_grep(convs, pat, **kw)
