"""
Generate PDF matching the BIPARD "All Questions" page exactly:
  - "All Questions" bold centered title
  - "Total: N Questions" subtitle
  - Each question in a rounded bordered card
  - "Question N:" bold dark heading
  - Question text in orange-red
  - Options  1. 2. 3. 4.  in blue
  - Correct option row has full-width pink highlight background
"""
import json, os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus.flowables import HRFlowable

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_FILE= os.path.join(BASE_DIR, 'questions.json')
OUTPUT_FILE   = os.path.join(BASE_DIR, 'BIPARD_All_Questions.pdf')

# ── exact colours from the screenshot ───────────────────────────────────────
CLR_ORANGE   = colors.HexColor('#c0392b')   # question text  (orange-red)
CLR_BLUE     = colors.HexColor('#2980b9')   # option text    (blue)
CLR_HEADING  = colors.HexColor('#1a1a2e')   # "Question N:"  (near-black)
CLR_PINK_BG  = colors.HexColor('#f1948a')   # correct-answer highlight
CLR_BORDER   = colors.HexColor('#cccccc')   # card border

PAGE_W, PAGE_H = A4
LEFT_M = RIGHT_M = 1.8*cm
CARD_W = PAGE_W - LEFT_M - RIGHT_M          # full usable width


def load_questions():
    with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def sx(t):
    """Escape XML special chars for ReportLab Paragraphs."""
    return str(t or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')


# ── paragraph styles ─────────────────────────────────────────────────────────
S_TITLE = ParagraphStyle('Title',
    fontSize=20, fontName='Helvetica-Bold',
    textColor=CLR_HEADING, alignment=TA_CENTER, spaceAfter=2)

S_SUB = ParagraphStyle('Sub',
    fontSize=11, fontName='Helvetica',
    textColor=colors.HexColor('#666666'), alignment=TA_CENTER, spaceAfter=16)

S_QHEAD = ParagraphStyle('QHead',
    fontSize=11, fontName='Helvetica-Bold',
    textColor=CLR_HEADING, spaceAfter=4)

S_QTEXT = ParagraphStyle('QText',
    fontSize=10, fontName='Helvetica',
    textColor=CLR_ORANGE, leading=15, spaceAfter=6)

S_OPT = ParagraphStyle('Opt',
    fontSize=10, fontName='Helvetica',
    textColor=CLR_BLUE, leading=14)

S_OPT_HI = ParagraphStyle('OptHi',          # highlighted (correct) option
    fontSize=10, fontName='Helvetica-Bold',
    textColor=CLR_BLUE, leading=14)


# ── build one question card ──────────────────────────────────────────────────
def question_card(num, q):
    q_text  = sx(q.get('question', ''))
    options = q.get('options', [])
    ans_idx = q.get('answer', -1)            # 0-based index

    # Inner rows of the card (list of [Paragraph] rows for the inner table)
    rows       = []
    row_styles = []

    # Row 0: heading
    rows.append([Paragraph(f'Question {num}:', S_QHEAD)])
    # Row 1: question text
    rows.append([Paragraph(q_text, S_QTEXT)])

    # Rows 2+: options
    for oi, opt in enumerate(options):
        label   = str(oi + 1)
        is_correct = (ans_idx == oi)
        style   = S_OPT_HI if is_correct else S_OPT
        rows.append([Paragraph(f'{label}. {sx(opt)}', style)])
        if is_correct:
            ri = len(rows) - 1              # row index in the inner table
            row_styles.append(
                ('BACKGROUND', (0, ri), (-1, ri), CLR_PINK_BG)
            )

    # Inner table (options section) — full card width minus padding
    inner_w = CARD_W - 24                   # 12pt padding each side
    inner = Table(rows, colWidths=[inner_w])
    inner.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        *row_styles,
    ]))

    # Outer card wrapper: single-cell table giving the border + rounded look
    card = Table([[inner]], colWidths=[CARD_W])
    card.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 0.8, CLR_BORDER),
        ('BACKGROUND',    (0, 0), (-1, -1), colors.white),
        ('LEFTPADDING',   (0, 0), (-1, -1), 12),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))

    return KeepTogether([card, Spacer(1, 8)])


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    print('Loading questions ...')
    questions = load_questions()
    print(f'Total: {len(questions)}')

    doc = SimpleDocTemplate(
        OUTPUT_FILE, pagesize=A4,
        leftMargin=LEFT_M, rightMargin=RIGHT_M,
        topMargin=2*cm, bottomMargin=2*cm,
        title='BIPARD – All Questions',
    )

    story = []
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph('All Questions', S_TITLE))
    story.append(Paragraph(f'Total: {len(questions)} Questions', S_SUB))
    story.append(HRFlowable(width='100%', thickness=0.8,
                            color=CLR_BORDER, spaceAfter=12))

    print('Building cards ...')
    for i, q in enumerate(questions, 1):
        story.append(question_card(i, q))
        if i % 500 == 0:
            print(f'  {i}/{len(questions)}')

    print('Writing PDF ...')
    doc.build(story)
    mb = os.path.getsize(OUTPUT_FILE) / 1048576
    print(f'Done! {OUTPUT_FILE}  ({mb:.2f} MB)')


if __name__ == '__main__':
    main()
