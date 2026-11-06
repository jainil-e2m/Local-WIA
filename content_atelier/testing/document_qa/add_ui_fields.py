"""Add all seven saved UI fields while retaining the original review document."""
import json
from hashlib import sha256
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / 'client_review/week1_content_angles_for_review.docx'
OUTPUT = ROOT / 'client_review/week1_content_angles_for_review_ui_fields.docx'
RUN = ROOT / 'testing/.data/experiments/default/runs/week1-gpt6-luna-partial-angle-diagnostic-20261008-a4'
QA = Path(__file__).resolve().parent / 'ui_fields'
FIELDS = ('title', 'argument', 'audience', 'tension', 'take', 'mechanism', 'reader_decision')
LABELS = dict(zip(FIELDS, ('Title', 'Argument', 'Audience', 'Tension', 'Take', 'Mechanism', 'Reader decision')))


def replace(paragraph, label, text):
    paragraph.clear()
    paragraph.add_run(label + ': ').bold = True
    paragraph.add_run(text)


def after(paragraph, label, text):
    element = OxmlElement('w:p')
    paragraph._p.addnext(element)
    added = Paragraph(element, paragraph._parent)
    added.style = 'Normal'
    replace(added, label, text)
    return added


def main():
    before_hash = sha256(ORIGINAL.read_bytes()).hexdigest()
    angles = json.loads((RUN / 'candidates.json').read_text(encoding='utf-8'))
    doc = Document(ORIGINAL)
    source_before = [p.text for p in doc.paragraphs if p.style.name == 'Transcript excerpt']
    boundaries = [p.text for p in doc.paragraphs if p.text.startswith('Claim boundary:')]
    headings = [p for p in doc.paragraphs if p.style.name == 'Heading 1' and p.text.startswith('Angle ')]
    assert len(headings) == len(angles) == 6
    for heading, angle in zip(headings, angles):
        section = []
        current = heading._p.getnext()
        while current is not None:
            if not current.tag.endswith('}p'):
                current = current.getnext()
                continue
            paragraph = Paragraph(current, heading._parent)
            if paragraph.style.name == 'Heading 1':
                break
            section.append(paragraph)
            current = current.getnext()
        by_prefix = {p.text.split(':', 1)[0]: p for p in section if ':' in p.text}
        original_title = by_prefix.get('Original angle title')
        if original_title is not None:
            replace(original_title, LABELS['title'], angle['title'])
        else:
            after(heading, LABELS['title'], angle['title'])
        replacements = {'argument': 'Core argument', 'audience': 'Intended audience', 'take': 'Content takeaway', 'reader_decision': 'Practical next step'}
        for field, old_label in replacements.items():
            replace(by_prefix[old_label], LABELS[field], angle[field])
        after(by_prefix['Intended audience'], LABELS['tension'], angle['tension'])
        after(by_prefix['Content takeaway'], LABELS['mechanism'], angle['mechanism'])
        # Keep the feedback prompts together if a source section needs another page.
        for paragraph in section:
            if paragraph.text.startswith(('Decision:', 'Changes to the argument or voice:')):
                paragraph.paragraph_format.keep_with_next = True
    for paragraph in doc.paragraphs:
        if paragraph.text.startswith('Please review these six proposed content angles'):
            paragraph.clear()
            paragraph.add_run('Please review these six proposed content angles for relevance, accuracy and fit with your voice. Each angle shows the seven fields intended for the Content Atelier UI: title, argument, audience, tension, take, mechanism and reader_decision. The field values match the saved generation output, with supporting transcript turns below. These are directions for content development, not finished ads or approved publication copy.')
    doc.save(OUTPUT)
    verified = Document(OUTPUT)
    texts = [p.text for p in verified.paragraphs]
    for angle in angles:
        for field in FIELDS:
            assert f'{LABELS[field]}: {angle[field]}' in texts, (angle['angle_id'], field)
    assert source_before == [p.text for p in verified.paragraphs if p.style.name == 'Transcript excerpt']
    assert boundaries == [p.text for p in verified.paragraphs if p.text.startswith('Claim boundary:')]
    assert sha256(ORIGINAL.read_bytes()).hexdigest() == before_hash
    QA.mkdir(parents=True, exist_ok=True)
    audit = {'output': str(OUTPUT), 'original_preserved_sha256': before_hash, 'docx_sha256': sha256(OUTPUT.read_bytes()).hexdigest(), 'fields': list(FIELDS), 'angles': len(angles), 'verified_field_values': len(angles) * len(FIELDS), 'unchanged_quotes': len(source_before), 'provider_calls': 0, 'visual_qa': 'pending'}
    (QA / 'field_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(json.dumps(audit))


if __name__ == '__main__':
    main()
