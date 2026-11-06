"""The second-family critic used on the 21 October packs (E.B3's extension prototype).

Sends through the product's `dispatch` (privacy routing, a file run plan, the plan's cost cap), never directly.

usage:
  python critic.py plan <approver-email> <max-usd>        # writes run_plan.json beside this file
  python critic.py run <packs.md> <model> <out.md>         # e.g. openai/gpt-6.1-sol
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "backend"))

from backend_pipeline.llm.run_plans import FilePlanStore, new_plan  # noqa: E402
from backend_pipeline.llm.transport import dispatch  # noqa: E402

KB = REPO / "backend" / "knowledge_base"
FEEDBACK = HERE.parent / "feedback-13-october" / "13-october-feedback-call-transcript.md"
PLAN = HERE / "run_plan.json"
URL = "https://openrouter.ai/api/v1/chat/completions"


def key() -> str:
    for line in (REPO / "backend" / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY_CLIENT=") or line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no OpenRouter key in backend/.env")


def kb(name: str) -> str:
    return (KB / name).read_text(encoding="utf-8")


def copy_only(doc: str) -> str:
    """The email, Reel and carousel sections of each pack, with the pack titles."""
    parts = []
    for block in re.split(r"(?m)^(?=# Pack )", doc):
        m = re.match(r"# (Pack [^\n]+)", block)
        if not m:
            continue
        parts.append("\n\n######## " + m.group(1))
        parts += [s.strip() for s in re.findall(r"(?ms)^## (?:Email|Reel|Carousel)[^\n]*\n.*?(?=^## |\Z)", block)]
    return "\n\n".join(parts)


SYSTEM = ("You are Whitney Hodges's most demanding editor. Whitney is the founder of Wedding Industry Ads (WIA), a paid-ads "
          "agency for wedding businesses. She rejected an earlier set of AI-written content packs as too how-to/educational/DIY, "
          "too polished, not her voice, with weak hooks. Your job: review the NEW content packs below and find everything she "
          "would still reject or edit. Be specific and harsh but fair; do not praise. Judge against her own documents and rules "
          "(supplied). Facts in the packs come from real call transcripts you cannot see; flag claims that sound invented, "
          "overstated, or that a reader could misread, but do not assume they are false.")

ASK = """## What to return (markdown)
1. Overall verdict in 4-6 sentences: would Whitney approve these as a first draft to edit, or reject them? Compare with the problems she named in the feedback call.
2. For EACH asset (Pack N / Email, Reel 1-3 script, each caption, carousel, carousel caption): hook strength 1-5; 'sounds like Whitney' 1-5; the single biggest problem; any rule violation (cite rule id); any line that sounds like AI cadence or is too polished; any claim that sounds invented or overstated.
3. The 12 most important line-level fixes across all packs: quote the exact current line, then give the exact replacement line in Whitney's voice. Never use em dashes.
4. Anything strategically off (wrong audience, desperation framing, DIY/how-to drift, offer misdescribed, CTA problems, repetition between sibling pieces)."""


def run(packs: str, model: str, out: str) -> None:
    feedback = FEEDBACK.read_text(encoding="utf-8")[:16000]
    user = (f"## Whitney's founder voice guide\n{kb('02-founder-voice-guide.md')}\n\n"
            f"## How Whitney edits (editing guide)\n{kb('17-editing-guide.md')}\n\n"
            f"## Rejection rules\n{kb('06-rejection-rules.md')}\n\n## Format guide\n{kb('09-format-guide.md')}\n\n"
            f"## Approved exemplars\n{kb('15-exemplars.md')}\n\n"
            f"## Whitney's spoken feedback on the earlier packs (call transcript, 13 Oct)\n{feedback}\n\n"
            f"## THE NEW PACKS TO REVIEW (copy only)\n{copy_only(pathlib.Path(packs).read_text(encoding='utf-8'))}\n\n{ASK}")
    body = {"model": model, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
            "max_tokens": 16000, "usage": {"include": True},
            "reasoning": {"enabled": False} if "anthropic" in model else {"effort": "medium"}}
    raw = dispatch(plan=FilePlanStore(PLAN), runs=None, stage="evaluation", model=model, fingerprint=pathlib.Path(out).name,
                   url=URL, body=body, headers=lambda: {"Authorization": "Bearer " + key()}, timeout=600)
    content = ((raw.get("choices") or [{}])[0].get("message") or {}).get("content")
    if not content:  # E.B1's extension: null content with a length finish
        raise SystemExit("no content: " + json.dumps(raw)[:1500])
    pathlib.Path(out).write_text(content, encoding="utf-8")
    print("usage", json.dumps(raw.get("usage"))[:400])


def make_plan(approver: str, max_usd: str) -> None:
    if PLAN.exists():
        raise SystemExit("run_plan.json exists")
    plan = new_plan(purpose="Week 2 packs critic (research)", stages=["evaluation"], models=["openai/gpt-6.1-sol"],
                    input_set_hash="*", max_calls=2, max_cost_usd=float(max_usd), approver=approver)
    PLAN.write_text(json.dumps(plan, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2, default=str))


if __name__ == "__main__":
    if sys.argv[1:2] == ["plan"]:
        make_plan(*sys.argv[2:4])
    else:
        run(*sys.argv[2:5])
