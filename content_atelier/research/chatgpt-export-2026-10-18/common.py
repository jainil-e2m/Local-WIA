"""Shared helpers for the 18 October ChatGPT-export experiments."""
import json, pathlib, re

ROOT = pathlib.Path(__file__).parent
REPO = ROOT.parents[1]
KB_DIR = REPO / "backend" / "knowledge_base"


def kb_text():
    """The knowledge base as the strategist loads it (manifest order, headings, header line)."""
    m = json.loads((KB_DIR / "manifest.json").read_text(encoding="utf-8"))
    parts = ["# WIA KNOWLEDGE BASE (supplied by Wedding Industry Ads; strategy, positioning and voice)"]
    for d in m["documents"]:
        parts.append(f"## {d['heading']}\n(status: {d['status']}; version: {d['version']})\n\n" +
                     (KB_DIR / d["file"]).read_text(encoding="utf-8").strip())
    return "\n\n".join(parts)


def load_jsonl(path):
    return [json.loads(l) for l in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def parse_json(content):
    """Lenient JSON extraction from a model reply."""
    if content is None:
        return None
    if isinstance(content, dict):
        return content
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None
