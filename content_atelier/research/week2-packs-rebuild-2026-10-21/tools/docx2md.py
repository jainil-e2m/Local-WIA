"""Dump a .docx to markdown-ish text: body paragraphs and tables in order, plus comments."""
import sys, zipfile, re
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def iter_block(parent):
    body = parent.element.body
    for child in body.iterchildren():
        if child.tag == W + "p":
            yield Paragraph(child, parent)
        elif child.tag == W + "tbl":
            yield Table(child, parent)
        elif child.tag == W + "sdt":
            for p in child.iter(W + "p"):
                yield Paragraph(p, parent)


def para_text(p):
    # include comment anchors
    out = []
    for node in p._p.iter():
        if node.tag == W + "t":
            out.append(node.text or "")
        elif node.tag == W + "commentRangeStart":
            out.append("[[C%s>" % node.get(W + "id"))
        elif node.tag == W + "commentRangeEnd":
            out.append("<C%s]]" % node.get(W + "id"))
        elif node.tag == W + "tab":
            out.append("\t")
        elif node.tag == W + "br":
            out.append("\n")
    return "".join(out)


def main(path, out):
    doc = Document(path)
    lines = []
    for blk in iter_block(doc):
        if isinstance(blk, Paragraph):
            t = para_text(blk)
            style = blk.style.name if blk.style is not None else ""
            if style.startswith("Heading"):
                lvl = re.sub(r"\D", "", style) or "1"
                lines.append("#" * int(lvl) + " " + t)
            elif style.startswith("Title"):
                lines.append("# " + t)
            elif "List" in style:
                lines.append("- " + t)
            else:
                lines.append(t)
        else:
            lines.append("<TABLE>")
            for row in blk.rows:
                cells = []
                for c in row.cells:
                    cells.append(" / ".join(para_text(p) for p in c.paragraphs).strip())
                lines.append("| " + " | ".join(cells) + " |")
            lines.append("</TABLE>")
    # comments
    z = zipfile.ZipFile(path)
    if "word/comments.xml" in z.namelist():
        root = etree.fromstring(z.read("word/comments.xml"))
        lines.append("\n\n=== COMMENTS ===")
        for c in root.iter(W + "comment"):
            txt = " ".join("".join(t.text or "" for t in p.iter(W + "t")) for p in c.iter(W + "p"))
            lines.append("C%s [%s %s]: %s" % (c.get(W + "id"), c.get(W + "author"), c.get(W + "date"), txt))
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(out, len(lines))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
