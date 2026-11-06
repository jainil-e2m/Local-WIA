"""Create a source-checked client review document without provider calls."""
from pathlib import Path
from hashlib import sha256
import json
import re

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'testing' / '.data'
RUN = DATA / 'experiments/default/runs/week1-gpt6-luna-partial-angle-diagnostic-20261008-a4'
PACKET = DATA / 'weekly_packets/week1/69fb4aa434a2070188d7ce7b86884ce17628e6f9a2df30eb5d943678797a32a0'
OUT = ROOT / 'client_review/week1_content_angles_for_review.docx'
QA = Path(__file__).resolve().parent

SELECTIONS = [
    ('m1', [24, 26, 52, 64]),
    ('m3', [230, 231, 234, 235]),
    ('m3', [365, 368, 371, 372, 373]),
    ('m8', [147, 252, 254, 257]),
    ('m8', [283, 284, 287, 288, 289, 290, 291]),
    ('m9', [223, 228, 229, 234, 241]),
]
NOTES = [
    'This is a service and messaging distinction from the photographer\'s account. It does not demonstrate a change in inquiries or bookings. The quoted candid proportion is self-reported.',
    'The regional preferences reflect this photographer\'s clients. Colorado targeting was a future possibility. No comparison of landing-page performance was reported.',
    'The small, approximate client count is not an ad-attributed conversion rate. The recommendation is to investigate fit, not automatically retain or exclude the term.',
    'The transcript records an ambiguous "$30" price. Verify all prices, inclusions and outside-cost estimates before publishing; do not calculate savings from these quotes. Landing-page use was a suggestion, not a tested result.',
    'This is a proposed strategy for one venue, not reported campaign results. Different creative objectives do not guarantee inquiries, tours or bookings.',
    'This is one prospect\'s stated affordability concern. It does not establish a universal price threshold or a confirmed purchase outcome. Historical offer details are not current pricing.',
]


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def para(doc, text='', bold_lead=None, style=None):
    p = doc.add_paragraph(style=style)
    if bold_lead:
        p.add_run(bold_lead + ' ').bold = True
    p.add_run(text)
    return p


def plain_heading(text):
    return re.sub(r'[^A-Za-z0-9 ]', '', text.replace('-', ' '))


def build():
    angles = load(RUN / 'candidates.json')
    moments = {m['moment_id']: m for m in load(RUN / 'moments.json')}
    refs = load(PACKET / 'reference_map.json')
    assert len(angles) == len(SELECTIONS) == 6
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = section.bottom_margin = Inches(.65)
    section.left_margin = section.right_margin = Inches(.75)
    section.footer_distance = Inches(.28)
    for name in ['Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Heading 3']:
        style = doc.styles[name]
        style.font.name = 'Calibri'
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.underline = False
        rpr = style.element.get_or_add_rPr()
        for col in rpr.findall(qn('w:color')):
            col.attrib.clear()
            col.set(qn('w:val'), '000000')
        ppr = style.element.get_or_add_pPr()
        for border in list(ppr.findall(qn('w:pBdr'))):
            ppr.remove(border)
    normal = doc.styles['Normal']
    normal.font.size = Pt(11)
    normal.paragraph_format.line_spacing = 1.03
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.widow_control = True
    normal.paragraph_format.keep_together = True
    title = doc.styles['Title']
    title.font.size = Pt(26)
    title.paragraph_format.space_after = Pt(12)
    h1 = doc.styles['Heading 1']
    h1.font.size = Pt(16)
    h1.paragraph_format.space_before = Pt(0)
    h1.paragraph_format.space_after = Pt(9)
    h2 = doc.styles['Heading 2']
    h2.font.size = Pt(12)
    h2.paragraph_format.space_before = Pt(9)
    h2.paragraph_format.space_after = Pt(5)
    quote_style = doc.styles.add_style('Transcript excerpt', 1)
    quote_style.base_style = normal
    quote_style.font.size = Pt(10.5)
    quote_style.paragraph_format.space_after = Pt(5)
    quote_style.paragraph_format.line_spacing = 1.02
    quote_style.paragraph_format.keep_together = True
    meta_style = doc.styles.add_style('Source reference', 1)
    meta_style.base_style = normal
    meta_style.font.size = Pt(10)
    meta_style.paragraph_format.space_after = Pt(5)

    # Page numbers make this multi-angle review easy to reference on a call.
    footer = section.footer.paragraphs[0]
    footer.alignment = 2
    footer.add_run('Page ').font.size = Pt(9)
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    doc.core_properties.title = 'Content Atelier Week 1 Content Angle Review'
    doc.core_properties.subject = 'Proposed angles with supporting transcript excerpts'
    doc.core_properties.author = 'Content Atelier'
    doc.core_properties.last_modified_by = 'Content Atelier'
    doc.core_properties.comments = ''

    doc.add_paragraph('Content Atelier Week 1 Content Angle Review', 'Title')
    para(doc, 'Prepared for client review on 8 October 2026', style='Subtitle')
    para(doc, 'Please review these six proposed content angles for relevance, accuracy and fit with your voice. Each angle includes the intended audience, its central argument, a practical takeaway and the exact transcript turns supporting it. These are directions for content development, not finished ads or approved publication copy.')
    doc.add_heading('Angles for review', 2)
    for i, angle in enumerate(angles, 1):
        para(doc, angle['title'], bold_lead=f'{i}.')
    doc.add_heading('How to review', 2)
    para(doc, 'For each angle, choose approve, revise or hold. Note what you would change in the argument or emphasis, whether it sounds like something you would teach, and whether any supporting details need correction. Confirm permission before using client names, identifiable circumstances or quotations in public content.')
    doc.add_heading('Reading the sources', 2)
    para(doc, 'The proposed arguments and takeaways are interpretations. The source excerpts are selected, unchanged transcript turns; intervening dialogue is omitted. Each quoted turn keeps its recorded speaker name and elapsed time. Transcription wording, including apparent errors, is preserved. Times are positions within the call, not clock times.')
    para(doc, 'Week 1 identifies the supplied test batch. Source references use the Zoom export filenames. Speaker names are transcript labels and should be confirmed before public attribution.', style='Source reference')

    audit = {'run': RUN.name, 'output': str(OUT), 'provider_calls': 0, 'angles': []}
    for index, (angle, selection, note) in enumerate(zip(angles, SELECTIONS, NOTES), 1):
        doc.add_page_break()
        doc.add_heading(f'Angle {index} {plain_heading(angle["title"])}', 1)
        # Preserve the exact generated title as body text when headings sanitize punctuation.
        if plain_heading(angle['title']) != angle['title']:
            para(doc, angle['title'], bold_lead='Original angle title:')
        para(doc, angle['argument'], bold_lead='Core argument:')
        para(doc, angle['audience'], bold_lead='Intended audience:')
        para(doc, angle['take'], bold_lead='Content takeaway:')
        para(doc, angle['reader_decision'], bold_lead='Practical next step:')
        doc.add_heading('Supporting source content', 2)
        meeting, numbers = selection
        source = load(PACKET / 'sources' / f'{meeting}.json')
        original = Path(source['source_path'])
        assert sha256(original.read_bytes()).hexdigest() == source['raw_sha256'], original
        filename = original.name
        para(doc, filename, bold_lead='Zoom export:', style='Source reference')
        para(doc, 'Selected turns below are separated in the original dialogue unless their timestamps are adjacent.', style='Source reference')
        supported = set()
        for moment_id in angle['moment_ids']:
            supported.update(moments[moment_id]['context_span_ids'])
            supported.update(moments[moment_id]['anchor_span_ids'])
        selected = []
        source_turns = {t['ref']: t for t in source['turns']}
        for number in numbers:
            ref = f'{meeting}.t{number:04d}'
            record = refs[ref]
            assert record['canonical_span_id'] in supported, (angle['angle_id'], ref)
            turn = source_turns[ref]
            assert record['text'] == turn['text']
            p = doc.add_paragraph(style='Transcript excerpt')
            p.add_run(f'[{turn["start_raw"][:-4]}] ').bold = True
            p.add_run(turn['text'])
            selected.append({'ref': ref, 'canonical_span_id': record['canonical_span_id'], 'start_raw': turn['start_raw'], 'end_raw': turn['end_raw'], 'speaker': turn['speaker'], 'text': turn['text']})
        para(doc, note, bold_lead='Claim boundary:')
        doc.add_heading('Client feedback', 2)
        para(doc, 'Decision:  Approve / Revise / Hold')
        para(doc, 'Changes to the argument or voice:')
        para(doc, 'Source corrections or permission concerns:')
        audit['angles'].append({'angle_id': angle['angle_id'], 'title': angle['title'], 'moment_ids': angle['moment_ids'], 'filename': filename, 'raw_sha256': source['raw_sha256'], 'quotes': selected})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    loaded = Document(OUT)
    all_paragraphs = [p.text for p in loaded.paragraphs]
    for angle in angles:
        for key in ['argument', 'audience', 'take', 'reader_decision']:
            assert any(angle[key] in p for p in all_paragraphs), (angle['angle_id'], key)
    for angle in audit['angles']:
        for quote in angle['quotes']:
            assert any(p.endswith(quote['text']) for p in all_paragraphs), quote['ref']
    audit['verified_quote_count'] = sum(len(a['quotes']) for a in audit['angles'])
    audit['docx_sha256'] = sha256(OUT.read_bytes()).hexdigest()
    audit['visual_qa'] = 'pending'
    (QA / 'source_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(OUT), 'angles': len(angles), 'verified_quotes': audit['verified_quote_count'], 'provider_calls': 0}))


if __name__ == '__main__':
    build()
