"""Build the client .docx of the three v2 packs, in the style of the earlier
'WIA - Content Atelier Review' document (used as the template: header, logo,
title block, margins and styles).

usage: python packs2docx.py <template.docx> <packs.md> <out.docx>
"""
import copy, re, sys
import docx
from docx.enum.text import WD_BREAK, WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Inches

TEMPLATE, MD, OUT = sys.argv[1:4]
BLUE = RGBColor(0x2E, 0x75, 0xB6)
TEXT = RGBColor(0x1A, 0x1A, 0x1A)
FONT = "Calibri"

d = docx.Document(TEMPLATE)
body = d.element.body

# Keep the title block (logo, title, subtitle, "Wedding Industry Ads", spacers); drop the rest.
children = [c for c in body.iterchildren()]
paras_seen = 0
for c in children:
    tag = c.tag.split('}')[1]
    if tag == 'sectPr':
        continue
    if tag == 'p' and paras_seen < 7:
        paras_seen += 1
        continue
    body.remove(c)

ps = d.paragraphs
# Subtitle: replace the old "Feedback on..." text.
sub = ps[2]
for i, r in enumerate(sub.runs):
    r.text = ("       Content Angles, Briefs and Packs" if i == 0 else "")
# Remove any leftover client/author metadata from the Google export.
cp = d.core_properties
cp.title = "WIA Content Packs: week of 8 to 14 June 2026"
cp.author = "E2M Solutions"
cp.last_modified_by = "E2M Solutions"
cp.comments = ""
cp.subject = ""
cp.keywords = ""


def fmt_run(r, size=11, bold=None, italic=None, color=TEXT):
    r.font.name = FONT
    rpr = r._element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = rpr.makeelement(qn('w:rFonts'), {})
        rpr.insert(0, rf)
    for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rf.set(qn(a), FONT)
    r.font.size = Pt(size)
    r.font.color.rgb = color
    if bold is not None:
        r.font.bold = bold
    if italic is not None:
        r.font.italic = italic


def para(style=None, before=0, after=8, keep=False, indent=None, hanging=None, align=None):
    p = d.add_paragraph(style=style) if style else d.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = 1.1
    pf.keep_with_next = keep
    if indent is not None:
        pf.left_indent = Inches(indent)
    if hanging is not None:
        pf.first_line_indent = Inches(-hanging)
    if align is not None:
        p.alignment = align
    return p


TOK = re.compile(r'(\*\*.+?\*\*|(?<![\w*])\*[^*\n]+?\*(?![\w*]))')


def add_inline(p, text, size=11, bold=False):
    for part in TOK.split(text):
        if not part:
            continue
        if part.startswith('**') and part.endswith('**') and len(part) > 4:
            fmt_run(p.add_run(part[2:-2]), size, bold=True)
        elif part.startswith('*') and part.endswith('*') and len(part) > 2:
            fmt_run(p.add_run(part[1:-1]), size, bold=bold, italic=True)
        else:
            fmt_run(p.add_run(part), size, bold=bold)


def add_lines(p, lines, size=11):
    for i, ln in enumerate(lines):
        if i:
            p.add_run().add_break()
        add_inline(p, ln, size)


def heading(text, level, size, before, after=6, page_break=False, prefix=None):
    p = para(style=f"Heading {level}", before=before, after=after, keep=True)
    if page_break:
        p.paragraph_format.page_break_before = True
    if prefix:
        fmt_run(p.add_run(prefix), size, bold=True, color=BLUE)
    fmt_run(p.add_run(text), size + (1 if prefix else 0), bold=True, color=BLUE)
    return p


def label(text, size=12, before=10):
    p = para(before=before, after=4, keep=True)
    fmt_run(p.add_run(text), size, bold=True, color=BLUE if size >= 12 else TEXT)
    return p


# ---- read the packs section of the markdown ----
src = open(MD, encoding='utf-8').read().splitlines()
start = next(i for i, l in enumerate(src) if l.startswith('# Pack 1'))
end = next(i for i, l in enumerate(src) if l.startswith('# Content bank'))
lines = src[start:end]

# group into blocks separated by blank lines
blocks, cur = [], []
for l in lines:
    if l.strip() == '':
        if cur:
            blocks.append(cur); cur = []
    else:
        cur.append(l.rstrip())
if cur:
    blocks.append(cur)

# a lead line followed directly by list items becomes two blocks
LIST = re.compile(r'^(- |\d+\. )')
split = []
for b in blocks:
    i = next((k for k in range(1, len(b)) if LIST.match(b[k])), None)
    if i is not None and not LIST.match(b[0]):
        split += [b[:i], b[i:]]
    else:
        split.append(b)
blocks = split

pack_no = 0
section = None          # 'angle' | 'brief' | 'pack'
pending_angle = False
first_pack = True

for b in blocks:
    first = b[0]
    if first.strip() == '---':
        continue
    if first.startswith('# Pack'):
        pack_no += 1
        heading(first[2:].strip(), 1, 18, before=0 if first_pack else 0, after=4,
                page_break=not first_pack)
        first_pack = False
        continue
    if first.startswith('## Content angle'):
        section, pending_angle = 'angle', True
        continue
    if first.startswith('### ') and pending_angle:
        heading(first[4:].strip(), 2, 14, before=10, prefix=f"Angle {pack_no}: ")
        pending_angle = False
        continue
    if first.startswith('## Content brief'):
        section = 'brief'
        heading("Content Brief", 2, 14, before=18)
        continue
    if first.startswith('## '):
        title = first[3:].strip()
        if title == 'Email':
            section = 'pack'
            heading("Content Pack", 2, 14, before=18)
            heading("Email", 3, 13, before=8)
        elif title.startswith('Carousel'):
            heading("Instagram " + title, 3, 13, before=18)
        else:
            heading(title, 3, 13, before=18)
        continue

    # lists (the block may mix numbered items, nested bullets and indented continuations)
    if re.match(r'^(- |\d+\. )', first):
        for l in b:
            m_num = re.match(r'^(\d+)\. (.*)', l)
            m_bul = re.match(r'^- (.*)', l)
            m_sub = re.match(r'^\s{2,}- (.*)', l)
            if m_num:
                p = para(after=4, indent=0.3, hanging=0.25)
                fmt_run(p.add_run(m_num.group(1) + ". "), 11)
                add_inline(p, m_num.group(2))
            elif m_bul:
                p = para(after=3, indent=0.3, hanging=0.2)
                fmt_run(p.add_run("•  "), 11)
                add_inline(p, m_bul.group(1))
            elif m_sub:
                p = para(after=3, indent=0.6, hanging=0.2)
                fmt_run(p.add_run("–  "), 11)
                add_inline(p, m_sub.group(1))
            else:
                p = para(after=4, indent=0.3)
                add_inline(p, l.strip())
        continue
    if re.match(r'^\s{2,}\S', first):           # indented continuation of a list item
        p = para(after=4, indent=0.3)
        add_lines(p, [l.strip() for l in b])
        continue

    # carousel slide: bold label, then each line its own short paragraph
    m = re.match(r'^\*\*(Slide \d+)\*\*$', first)
    if m:
        label(m.group(1), size=11, before=8)
        for l in b[1:]:
            add_inline(para(after=3), l)
        continue

    # brief fields "**Label.** text" -> sub-heading + text (as in the earlier document)
    m = re.match(r'^\*\*([^*]+?)\.\*\*\s*(.*)$', first)
    if section == 'brief' and m:
        label(m.group(1))
        rest = [m.group(2)] if m.group(2) else []
        rest += b[1:]
        if rest:
            add_lines(para(), rest)
        continue

    # "Script:" / "Caption:" style labels on their own
    if re.match(r'^\*\*[^*]+:\*\*$', first) and len(b) == 1:
        label(first.strip('*'), size=11, before=8)
        continue

    # ordinary paragraph (multi-line blocks keep their line breaks: email header, slide copy)
    add_lines(para(), b)

d.save(OUT)
print("saved", OUT, "packs", pack_no)
