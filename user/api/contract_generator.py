from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from io import BytesIO
from django.conf import settings
import os


def generate_student_contract(student):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    
    story = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName='Times-Roman',
        fontSize=16,
        textColor=colors.black,
        spaceAfter=30,
        alignment=TA_CENTER,
        fontStyle='BOLD'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName='Times-Roman',
        fontSize=14,
        textColor=colors.black,
        spaceAfter=12,
        spaceBefore=12,
        alignment=TA_LEFT,
        fontStyle='BOLD'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=12,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_JUSTIFY,
        leading=14
    )
    
    center_style = ParagraphStyle(
        'CustomCenter',
        parent=normal_style,
        alignment=TA_CENTER
    )
    
    title = Paragraph("O'QUV SHARTNOMASI", title_style)
    story.append(title)
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("BIMUZ ta'lim markazi va talaba o'rtasidagi o'quv shartnomasi", center_style))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("Shartnoma №: ST-{}".format(student.id), normal_style))
    story.append(Paragraph("Sana: {}".format(student.created_at.strftime("%d.%m.%Y")), normal_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>1. TARAFLAR</b>", heading_style))
    
    story.append(Paragraph(
        "<b>Ta'lim muassasasi (Ta'minotchi):</b><br/>"
        "BIMUZ ta'lim markazi<br/>"
        "Manzil: Toshkent shahri<br/>"
        "INN: 123456789",
        normal_style
    ))
    
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph(
        "<b>Talaba (Xaridor):</b><br/>"
        "F.I.Sh: {}<br/>"
        "Telefon: {}<br/>"
        "Passport seriya va raqami: {}<br/>"
        "Tug'ilgan sana: {}<br/>"
        "Manzil: Toshkent shahri".format(
            student.full_name,
            student.phone,
            student.passport_serial_number,
            student.birth_date.strftime("%d.%m.%Y")
        ),
        normal_style
    ))
    
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>2. SHARTNOMA PREDMETI</b>", heading_style))
    story.append(Paragraph(
        "Ushbu shartnoma bo'yicha Ta'minotchi Xaridorga professional ta'lim xizmatlarini ko'rsatadi. "
        "Xaridor shartnoma shartlariga rioya qilish majburiyatini oladi.",
        normal_style
    ))
    
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>3. TARAFLARNING HUQUQ VA MAJBURIYATLARI</b>", heading_style))
    
    story.append(Paragraph("<b>3.1. Ta'minotchining huquqlari:</b>", normal_style))
    story.append(Paragraph(
        "• O'quv jarayonini tashkil etish va nazorat qilish;<br/>"
        "• O'quv dasturiga rioya qilishni talab qilish;<br/>"
        "• Shartnoma shartlarini buzgan holda shartnomani bekor qilish.",
        normal_style
    ))
    
    story.append(Spacer(1, 0.2*cm))
    
    story.append(Paragraph("<b>3.2. Ta'minotchining majburiyatlari:</b>", normal_style))
    story.append(Paragraph(
        "• Sifatli ta'lim xizmatlarini ko'rsatish;<br/>"
        "• O'quv materiallarini ta'minlash;<br/>"
        "• O'quv jarayonini tashkil etish.",
        normal_style
    ))
    
    story.append(Spacer(1, 0.2*cm))
    
    story.append(Paragraph("<b>3.3. Xaridorning huquqlari:</b>", normal_style))
    story.append(Paragraph(
        "• Sifatli ta'lim xizmatlarini olish;<br/>"
        "• O'quv jarayoni haqida ma'lumot olish;<br/>"
        "• Shartnomani bekor qilish (qonun hujjatlariga muvofiq).",
        normal_style
    ))
    
    story.append(Spacer(1, 0.2*cm))
    
    story.append(Paragraph("<b>3.4. Xaridorning majburiyatlari:</b>", normal_style))
    story.append(Paragraph(
        "• O'quv dasturiga rioya qilish;<br/>"
        "• To'lovlarni o'z vaqtida amalga oshirish;<br/>"
        "• Ta'lim muassasasining ichki tartib qoidalariga rioya qilish.",
        normal_style
    ))
    
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>4. TO'LOV SHARTLARI</b>", heading_style))
    story.append(Paragraph(
        "To'lov shartlari alohida kelishiladi va qo'shimcha shartnoma yoki qo'shimcha shartlar orqali rasmiylashtiriladi.",
        normal_style
    ))
    
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>5. SHARTNOMANING MUHLATI</b>", heading_style))
    story.append(Paragraph(
        "Shartnoma quyidagi holatlarda bekor qilinadi:<br/>"
        "• O'quv kursi yakunlanganda;<br/>"
        "• Tarafning yozma xohishi bilan;<br/>"
        "• Shartnoma shartlarini buzgan holda.",
        normal_style
    ))
    
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>6. BOSHQA SHARTLAR</b>", heading_style))
    story.append(Paragraph(
        "Barcha nizolar muzokaralar yo'li bilan hal qilinadi. Agar kelishuvga erishilmasa, "
        "nizolar qonunchilik hujjatlariga muvofiq hal qilinadi.",
        normal_style
    ))
    
    story.append(Spacer(1, 0.5*cm))
    
    data = [
        ['Ta\'minotchi:', 'Xaridor:'],
        ['BIMUZ ta\'lim markazi', student.full_name],
        ['', ''],
        ['Imzo: _______________', 'Imzo: _______________'],
        ['', ''],
        ['M.P.', 'M.P.']
    ]
    
    table = Table(data, colWidths=[9*cm, 9*cm])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    
    story.append(table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer
