"""Deterministic style lint for WIA copy: the constructions Whitney rejects in AI output.
Findings are warnings (plan E.B10, V23): her own approved copy uses some of these forms.
Usage: from lint import lint; lint(text) -> list of (rule, match)."""
import re

# Severity from the export (section 1.8): "ban" = Whitney rejected it outright and never used it after the ban date;
# everything else is a flag, because her own approved copy uses the form or the rule depends on context.
SEVERITY = {"dont_have_x_problem": "ban"}

RULES = [
    ("dont_have_x_problem", re.compile(r"\byou\s+don'?t\s+have\s+an?\s+[\w\s-]{1,30}?problem", re.I)),
    ("price_in_public_copy", re.compile(r"\$\s?\d[\d,]*(\.\d+)?(\s?(/|per)\s?(mo|month))?", re.I)),
    ("scarcity_claim", re.compile(r"\b(only \d+ (spots|openings|seats)|limited (spots|time)|spots? (left|remaining)|won'?t reopen|last chance)\b", re.I)),
    ("guarantee_or_automatic", re.compile(r"\b(guarantee[ds]?|book clients automatically|on autopilot|done[- ]for[- ]you)\b", re.I)),
    ("former_staff_named", re.compile(r"\bFallon\b")),
    ("em_dash", re.compile(r"—|\s–\s|\s--\s")),
    ("not_x_its_y", re.compile(r"\b(it'?s|this is|that'?s|they'?re|you'?re)\s+not\s+(just\s+)?(about\s+)?[^.?!\n—]{1,60}?\s*[,;.—]\s*(it'?s|this is|that'?s|they'?re|you'?re|but)\b", re.I)),
    ("isnt_its", re.compile(r"\b(isn'?t|aren'?t|wasn'?t)\s+(just\s+)?(about\s+)?[^.?!\n]{1,50}?[,;.]\s*(it'?s|they'?re|this is)\b", re.I)),
    ("not_because_because", re.compile(r"\bnot because\b[^.?!\n]{1,60}\bbut because\b", re.I)),
    ("ai_vocab", re.compile(r"\b(delve|tapestry|landscape|game[- ]changer|unlock|unleash|elevate your|navigate the|in today'?s|ever[- ]evolving|seamless(ly)?|robust|leverage|supercharge|transformative|testament to|realm|embark|journey)\b", re.I)),
    ("heres_the_thing", re.compile(r"\b(here'?s the thing|here'?s the truth|the truth is|let'?s be honest|let that sink in|spoiler alert|plot twist)\b", re.I)),
    ("rhetorical_qa", re.compile(r"\b(the result|the reason|the answer|the secret|the kicker)\?\s", re.I)),
]


def staccato(text):
    """Three or more consecutive sentences of four words or fewer."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    run, hits = 0, 0
    for s in sents:
        if len(s.split()) <= 4:
            run += 1
            if run == 3:
                hits += 1
        else:
            run = 0
    return hits


def lint(text):
    out = []
    for name, rx in RULES:
        for m in rx.finditer(text or ""):
            out.append((name, m.group(0)[:60]))
    for _ in range(staccato(text or "")):
        out.append(("staccato", ""))
    return out


def counts(text):
    c = {}
    for name, _ in lint(text):
        c[name] = c.get(name, 0) + 1
    return c


if __name__ == "__main__":
    import sys
    print(counts(sys.stdin.read()))
