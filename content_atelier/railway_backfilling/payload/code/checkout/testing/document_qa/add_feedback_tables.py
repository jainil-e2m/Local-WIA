"""Replace freeform feedback with the client's five-criterion review form."""
from hashlib import sha256
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / 'client_review/week1_content_angles_for_review_ui_fields.docx'
OUTPUT = ROOT / 'client_review/week1_content_angles_feedback_tables.docx'
RUN = ROOT / 'testing/.data/experiments/default/runs/week1-gpt6-luna-partial-angle-diagnostic-20261008-a4'
QA = Path(__file__).resolve().parent / 'feedback_tables'
SCALE = 'Scale: 1 = Poor / Disagree; 2 = Moderate; 3 = Good / Mostly agree; 4 = Very good / Strongly agree; 5 = Excellent / Completely agree.'
CRITERIA = [
    ('End client relevance', 'The angle is relevant to the intended end client.'),
    ('Complexity', 'The complexity is appropriate for the intended audience.'),
    ('Angle fit to the brand', "The angle aligns with the brand's positioning."),
    ('Voice / tone', 'The framing sounds like something Whitney would naturally teach or discuss.'),
    ('Distinctiveness', 'The angle offers a meaningfully different perspective from the other angles or recent content.'),
]
FIELD_LABELS = [('title', 'Title'), ('argument', 'Argument'), ('audience', 'Audience'), ('tension', 'Tension'), ('take', 'Take'), ('mechanism', 'Mechanism'), ('reader_decision', 'Reader decision')]


def after(paragraph, text, bold_label=None):
    element = OxmlElement('w:p')
    paragraph._p.addnext(element)
    new = Paragraph(element, paragraph._parent)
    new.style = 'Normal'
    new.paragraph_format.keep_with_next = True
    if bold_label:
        new.add_run(bold_label + ' ').bold = True
    new.add_run(text)
    return new


def style_table(table):
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    widths = [2.4, 1.3, 3.3]
    for col, width in zip(table.columns, widths):
        col.width = Inches(width)
    borders = OxmlElement('w:tblBorders')
    for name in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        border = OxmlElement('w:' + name)
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), '6')
        border.set(qn('w:color'), 'D9D9D9')
        borders.append(border)
    table._tbl.tblPr.append(borders)
    for row_index, row in enumerate(table.rows):
        row.height = Inches(.38 if row_index == 0 else 1.1)
        row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
        no_split = OxmlElement('w:cantSplit')
        row._tr.get_or_add_trPr().append(no_split)
        if row_index == 0:
            repeat = OxmlElement('w:tblHeader')
            row._tr.get_or_add_trPr().append(repeat)
        for cell_index, (cell, width) in enumerate(zip(row.cells, widths)):
            cell.width = Inches(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            properties = cell._tc.get_or_add_tcPr()
            margin = OxmlElement('w:tcMar')
            for side in ('top', 'left', 'bottom', 'right'):
                value = OxmlElement('w:' + side)
                value.set(qn('w:w'), '110')
                value.set(qn('w:type'), 'dxa')
                margin.append(value)
            properties.append(margin)
            shading = OxmlElement('w:shd')
            shading.set(qn('w:fill'), '383838' if row_index == 0 else ('F5F5F5' if row_index % 2 else 'FFFFFF'))
            properties.append(shading)
            for p in cell.paragraphs:
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.1
                p.paragraph_format.keep_together = True
                p.paragraph_format.keep_with_next = False
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if cell_index == 1 else WD_ALIGN_PARAGRAPH.LEFT
                for run in p.runs:
                    run.font.size = Pt(11)
                    run.font.color.rgb = RGBColor(255, 255, 255) if row_index == 0 else RGBColor(0, 0, 0)
                    if row_index == 0:
                        run.bold = True


def main():
    original_hash = sha256(ORIGINAL.read_bytes()).hexdigest()
    angles = json.loads((RUN / 'candidates.json').read_text(encoding='utf-8'))
    doc = Document(ORIGINAL)
    quotes_before = [p.text for p in doc.paragraphs if p.style.name == 'Transcript excerpt']
    boundaries_before = [p.text for p in doc.paragraphs if p.text.startswith('Claim boundary:')]
    headings = [p for p in doc.paragraphs if p.text == 'Client feedback']
    assert len(headings) == len(angles) == 6
    for number, (heading, angle) in enumerate(zip(headings, angles), 1):
        heading.text = f'Client feedback for Angle {number}'
        heading.paragraph_format.page_break_before = True
        heading.paragraph_format.keep_with_next = True
        old = heading._p.getnext()
        for expected in ('Decision:', 'Changes to the argument or voice:', 'Source corrections or permission concerns:'):
            assert old is not None and old.tag == qn('w:p')
            old_paragraph = Paragraph(old, heading._parent)
            assert old_paragraph.text.startswith(expected), old_paragraph.text
            next_element = old.getnext()
            old.getparent().remove(old)
            old = next_element
        current = after(heading, angle['title'], 'Content Angle:')
        current = after(current, SCALE)
        current = after(current, 'Circle or mark one rating per row and add comments in the final column.')
        current = after(current, 'For complexity, rate how appropriate the complexity is, not how difficult the angle feels. Higher ratings mean a better result for every criterion.')
        table = doc.add_table(rows=6, cols=3)
        for cell, text in zip(table.rows[0].cells, ('Question', 'Rating\n1 to 5', 'Comments')):
            cell.text = text
        for row, (label, statement) in zip(table.rows[1:], CRITERIA):
            p = row.cells[0].paragraphs[0]
            p.add_run(label).bold = True
            p.add_run('\n' + statement)
            row.cells[1].text = '1  2  3  4  5'
            row.cells[2].text = ''
        style_table(table)
        current._p.addnext(table._tbl)
    for p in doc.paragraphs:
        if p.text.startswith('For each angle, choose approve, revise or hold.'):
            p.text = 'Use the feedback table following each angle to rate end client relevance, complexity, brand fit, voice and tone, and distinctiveness. Give each criterion a score from 1 to 5 and explain your rating in its comments cell. Confirm permission before using client names, identifiable circumstances or quotations in public content.'
    doc.save(OUTPUT)
    verified = Document(OUTPUT)
    texts = [p.text for p in verified.paragraphs]
    assert len(verified.tables) == 6
    for angle in angles:
        for field, label in FIELD_LABELS:
            assert f'{label}: {angle[field]}' in texts, (angle['angle_id'], field)
    for table in verified.tables:
        assert len(table.rows) == 6 and len(table.columns) == 3
        assert [r.cells[0].text.split('\n', 1)[0] for r in table.rows[1:]] == [c[0] for c in CRITERIA]
        assert all(not r.cells[2].text for r in table.rows[1:])
    assert texts.count(SCALE) == 6
    assert quotes_before == [p.text for p in verified.paragraphs if p.style.name == 'Transcript excerpt']
    assert boundaries_before == [p.text for p in verified.paragraphs if p.text.startswith('Claim boundary:')]
    assert sha256(ORIGINAL.read_bytes()).hexdigest() == original_hash
    QA.mkdir(parents=True, exist_ok=True)
    audit = {'output': str(OUTPUT), 'original_preserved_sha256': original_hash, 'docx_sha256': sha256(OUTPUT.read_bytes()).hexdigest(), 'feedback_tables': 6, 'criteria_per_table': 5, 'criteria': [c[0] for c in CRITERIA], 'scale': SCALE, 'verified_ui_field_values': 42, 'unchanged_quotes': len(quotes_before), 'provider_calls': 0, 'visual_qa': 'pending'}
    (QA / 'feedback_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(json.dumps(audit))


if __name__ == '__main__':
    main()
