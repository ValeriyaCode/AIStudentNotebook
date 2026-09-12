"""Portable workbook export with an embedded Cyrillic font."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from django.conf import settings
from .bonus import BONUS
from .models import WorkbookBlock
from functools import lru_cache
from PIL import Image as PillowImage, ImageFilter
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak, Table, TableStyle, Image, Flowable


pdfmetrics.registerFont(TTFont('Workbook', str(Path(__file__).parent / 'fonts' / 'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('WorkbookBold', str(Path(__file__).parent / 'fonts' / 'DejaVuSans-Bold.ttf')))


class SectionNumber(Flowable):
    def __init__(self, number):
        super().__init__()
        self.number = str(number)
        self.width = self.height = 36

    def draw(self):
        self.canv.setFillColor(colors.HexColor('#ffd044'))
        self.canv.circle(18, 18, 18, fill=1, stroke=0)
        self.canv.setFillColor(colors.HexColor('#181818'))
        self.canv.setFont('WorkbookBold', 15)
        self.canv.drawCentredString(18, 12.5, self.number)



@lru_cache(maxsize=4)
def soft_plant(path):
    with PillowImage.open(path) as source:
        image = source.convert('RGBA')
        image.thumbnail((300, 400))
        return ImageReader(image.filter(ImageFilter.GaussianBlur(3)))


def build_workbook_pdf(workbook, pages=None):
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=30*mm, bottomMargin=22*mm,
                            title=workbook.template.title, author='AI Notebook')
    body = ParagraphStyle('body', fontName='Workbook', fontSize=10, leading=15, spaceAfter=12, textColor=colors.HexColor('#28374d'))
    heading = ParagraphStyle('heading', parent=body, fontName='WorkbookBold', textColor=colors.HexColor('#181818'), fontSize=22, leading=28, spaceAfter=16)
    label = ParagraphStyle('label', parent=body, fontName='WorkbookBold', fontSize=11, leading=16, textColor=colors.HexColor('#181818'), keepWithNext=True, spaceBefore=8, spaceAfter=10)

    def p(value, style=body):
        return Paragraph(escape(str(value if value not in (None, '') else '—')).replace('\n', '<br/>'), style)

    assets = Path(settings.BASE_DIR) / 'static' / 'images' / 'design'
    illustrations = ['notebook.png', 'books.png', 'books.png', 'lamp.png', 'headphone.png', 'pens.png',
                     'laptop.png', 'keyboard.png', 'cup.png', 'mouse.png', 'robot.png', 'cup_victory.png', 'present.png']
    answer_style = ParagraphStyle('answer', parent=body, backColor=colors.white,
        borderColor=colors.HexColor('#e3dfd4'), borderWidth=.6, borderRadius=8,
        borderPadding=10, spaceBefore=7, spaceAfter=16)

    def artwork(path, width, height):
        image = Image(str(path), kind='proportional', width=width, height=height)
        image.hAlign = 'CENTER'
        return image

    def footer(canvas, document):
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(colors.HexColor('#fffdf7'))
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor('#fbf2df'))
        canvas.ellipse(-100, -100, width+80, 55, fill=1, stroke=0)
        canvas.ellipse(width-125, height-330, width+180, height+80, fill=1, stroke=0)
        if document.page != 1:
            canvas.setFillColor(colors.HexColor('#191919'))
            canvas.roundRect(18*mm, height-22*mm, width-36*mm, 15*mm, 8, fill=1, stroke=0)
            canvas.drawImage(str(assets/'logo/white_yellow.png'), 22*mm, height-22*mm, 15*mm, 15*mm, mask='auto')
            canvas.setFont('Workbook', 10)
            canvas.setFillColor(colors.white)
            canvas.drawString(40*mm, height-16*mm, 'AI Notebook')
        canvas.setFillAlpha(.24)
        canvas.drawImage(soft_plant(str(assets/'plants/3.png')), -22*mm, height-67*mm, 48*mm, 64*mm, mask='auto')
        canvas.saveState()
        canvas.translate(width, 0)
        canvas.rotate(180)
        canvas.drawImage(soft_plant(str(assets/'plants/4.png')), -15*mm, -58*mm, 48*mm, 64*mm, mask='auto')
        canvas.restoreState()
        canvas.setFillAlpha(1)
        canvas.setFont('Workbook', 8)
        canvas.setFillColor(colors.HexColor('#777777'))
        canvas.drawString(18*mm, 11*mm, 'Мій AI-щоденник')
        canvas.drawRightString(width-18*mm, 11*mm, str(document.page))
        canvas.restoreState()

    avatar = assets / 'other/robot.png'
    if workbook.student.avatar:
        try:
            candidate = Path(workbook.student.avatar.path)
            if candidate.is_file():
                avatar = candidate
        except (ValueError, NotImplementedError):
            pass
    cover_title = ParagraphStyle('cover-title', parent=heading, fontSize=32, leading=40, alignment=1, spaceAfter=20)
    cover_name = ParagraphStyle('cover-name', parent=heading, fontSize=22, leading=28, alignment=1)
    story = [Spacer(1, 5*mm),
             p(f'{workbook.student.first_name or workbook.student.username}, привіт!', cover_name),
             p('ТВІЙ AI-ЩОДЕННИК', cover_title),
             artwork(assets / 'log_in/girl.png', 110*mm, 115*mm)]
    answers = {answer.block_id: answer.value for answer in workbook.answers.all()}
    if pages is None:
        pages = workbook.template.pages.all()
    profile_fields = list(WorkbookBlock.objects.filter(page__in=pages, half_width=True))
    if profile_fields:
        profile_cells = [[p(block.label, label), p(answers.get(block.pk, ''), body)] for block in profile_fields]
        profile_rows = [profile_cells[index:index+2] for index in range(0, len(profile_cells), 2)]
        if len(profile_rows[-1]) == 1:
            profile_rows[-1].append('')
        profile_table = Table(profile_rows, colWidths=[(doc.width-38*mm)/2]*2)
        profile_table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
        profile = Table([[artwork(avatar, 29*mm, 29*mm), profile_table]], colWidths=[34*mm, doc.width-34*mm])
        profile.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.white),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#e3dfd4')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
        story.extend([p('Про мене', label), profile, Spacer(1, 6*mm)])
    for page in pages.prefetch_related('blocks'):
        if page.title == 'БОНУС':
            story.extend([PageBreak(), p('БОНУС', heading),
                          p(BONUS['intro'], body), artwork(assets / 'notebook/teacher.png', 110*mm, 65*mm), Spacer(1, 6*mm)])
            cards = []
            for course in BONUS['courses']:
                cards.append([artwork(Path(settings.BASE_DIR) / 'static' / course['icon'], 16*mm, 16*mm),
                              p(course['name'], label), p(course['text'], body)])
            courses = Table([[cards[0], '', cards[1]]], colWidths=[(doc.width-12)/2, 12, (doc.width-12)/2])
            courses.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),colors.white),('BACKGROUND',(2,0),(2,0),colors.white),
                ('BOX',(0,0),(0,0),.7,colors.HexColor('#ead9a1')),('BOX',(2,0),(2,0),.7,colors.HexColor('#ead9a1')),
                ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),
                ('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12)]))
            discount = ParagraphStyle('discount', parent=label, alignment=1, fontSize=14, leading=21,
                                      backColor=colors.HexColor('#ffda65'), borderPadding=12, borderRadius=8, spaceBefore=20, spaceAfter=20)
            story.extend([courses, Spacer(1, 8*mm), p(BONUS['discount'], discount), p(BONUS['contact'], body)])
            continue
        page_blocks = list(page.blocks.all())
        tool_blocks = [block for block in page_blocks if block.card_style == 'tool']
        tool_lines = []
        for block in tool_blocks:
            if block.block_type == 'static_text':
                tool_lines.append(p(block.label, body))
            else:
                tool_lines.append(p(f'{block.label}: {answers.get(block.pk) or chr(8212)}', body))
        title_card = Table([[[SectionNumber(page.position + 1), Spacer(1, 8), p(page.title, heading)], artwork(assets / 'other' / illustrations[page.position % 13], 34*mm, 34*mm)]], colWidths=[doc.width-40*mm, 40*mm])
        title_card.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),12)]))
        story.extend([PageBreak(), title_card, *tool_lines, Spacer(1, 4*mm)])
        profile_fields = [block for block in page_blocks if block.half_width]
        for block in page_blocks:
            if block in tool_blocks:
                continue
            if block.half_width or (profile_fields and block.card_style == 'profile'):
                continue
            if block.block_type == 'static_text':
                story.append(p(block.label, label if block.position == 0 else body))
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
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
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
                story.append(p(', '.join(map(str, value)) if isinstance(value, list) else value, answer_style))
            elif block.block_type == 'rating' and value:
                story.append(p('★' * int(value) + '☆' * max(0, int(config.get('max', 5))-int(value)), answer_style))
            else:
                story.append(p(value, answer_style))
            story.append(Spacer(1, 5*mm))
        if page.title == 'БОНУС':
            story.extend([Spacer(1, 8*mm), artwork(assets / 'notebook/girl.png', 120*mm, 112*mm)])
        # A trailing spacer can spill onto an otherwise empty page before PageBreak.
        if isinstance(story[-1], Spacer):
            story.pop()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
