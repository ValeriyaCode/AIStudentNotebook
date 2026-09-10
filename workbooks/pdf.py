"""Portable workbook export with an embedded Cyrillic font."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak, Table, TableStyle


pdfmetrics.registerFont(TTFont('Workbook', str(Path(__file__).parent / 'fonts' / 'DejaVuSans.ttf')))


def build_workbook_pdf(workbook, pages=None):
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=18*mm, bottomMargin=18*mm,
                            title=workbook.template.title, author='AI Notebook')
    body = ParagraphStyle('body', fontName='Workbook', fontSize=10, leading=15, spaceAfter=8)
    heading = ParagraphStyle('heading', parent=body, fontSize=22, leading=28, spaceAfter=16)
    label = ParagraphStyle('label', parent=body, fontSize=11, leading=16, textColor=colors.HexColor('#695000'), keepWithNext=True)

    def p(value, style=body):
        return Paragraph(escape(str(value if value not in (None, '') else '—')).replace('\n', '<br/>'), style)

    def footer(canvas, document):
        canvas.setFont('Workbook', 8)
        canvas.setFillColor(colors.HexColor('#777777'))
        canvas.drawString(18*mm, 10*mm, 'AI Notebook')
        canvas.drawRightString(A4[0]-18*mm, 10*mm, str(document.page))

    story = [Spacer(1, 30*mm), p(workbook.template.title, heading),
             p(workbook.student.get_full_name() or workbook.student.username),
             p(workbook.template.description)]
    answers = {answer.block_id: answer.value for answer in workbook.answers.all()}
    if pages is None:
        pages = workbook.template.pages.all()
    for page in pages.prefetch_related('blocks'):
        story.extend([PageBreak(), p(page.title, heading), p(page.subtitle), Spacer(1, 6*mm)])
        for block in page.blocks.all():
            if block.block_type == 'static_text':
                story.append(p(block.label))
                continue
            story.append(p(block.label, label))
            value = answers.get(block.pk, '')
            config = block.config or {}
            if block.block_type == 'table':
                columns = config.get('columns', [])
                saved = value if isinstance(value, list) else []
                data = [[p(''), *[p(col) for col in columns]]]
                row_labels = ([row.get('_row', str(i + 1)) if isinstance(row, dict) else str(i + 1) for i, row in enumerate(saved)]
                              if block.pk in answers else config.get('rows', []))
                for index, row_label in enumerate(row_labels):
                    row = saved[index] if index < len(saved) and isinstance(saved[index], dict) else {}
                    data.append([p(row_label), *[p(row.get(col, '')) for col in columns]])
                if columns and len(data) > 1:
                    table = Table(data, colWidths=[doc.width / (len(columns)+1)] * (len(columns)+1),
                                  repeatRows=1, splitByRow=1, splitInRow=1)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5edcf')),
                        ('GRID', (0, 0), (-1, -1), .5, colors.HexColor('#d8d4c9')),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 7),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
                        ('TOPPADDING', (0, 0), (-1, -1), 7),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                    ]))
                    story.append(table)
                else:
                    story.append(p(''))
            elif block.block_type == 'checkboxes':
                story.append(p(', '.join(map(str, value)) if isinstance(value, list) else value))
            elif block.block_type == 'rating' and value:
                story.append(p(f'{value} / {config.get("max", 5)}'))
            else:
                story.append(p(value))
            story.append(Spacer(1, 5*mm))
        # A trailing spacer can spill onto an otherwise empty page before PageBreak.
        if isinstance(story[-1], Spacer):
            story.pop()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
