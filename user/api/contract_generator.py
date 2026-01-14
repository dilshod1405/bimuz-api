from io import BytesIO
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from decimal import Decimal
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
import os
import logging

logger = logging.getLogger(__name__)


# Font configuration is handled by WeasyPrint in HTML template


def format_currency(amount):
    """Format amount as currency in Uzbek format"""
    if isinstance(amount, Decimal):
        amount = float(amount)
    return f"{amount:,.0f}".replace(',', ' ')


def number_to_words_uz(num):
    """Convert number to Uzbek words in Latin script"""
    if num == 0:
        return "nol"
    
    ones = ['', 'bir', 'ikki', 'uch', "to'rt", 'besh', 'olti', 'yetti', 'sakkiz', "to'qqiz"]
    tens = ['', "o'n", 'yigirma', "o'ttiz", 'qirq', 'ellik', 'oltmish', 'yetmish', 'sakson', "to'qson"]
    hundreds = ['', 'yuz', 'ikki yuz', 'uch yuz', "to'rt yuz", 'besh yuz', 'olti yuz', 'yetti yuz', 'sakkiz yuz', "to'qqiz yuz"]
    
    def convert_three_digits(n):
        if n == 0:
            return ''
        result = []
        if n >= 100:
            result.append(hundreds[n // 100])
            n %= 100
        if n >= 10:
            result.append(tens[n // 10])
            n %= 10
        if n > 0:
            result.append(ones[n])
        return ' '.join(result)
    
    if num < 1000:
        return convert_three_digits(num)
    elif num < 1000000:
        thousands = num // 1000
        remainder = num % 1000
        result = []
        if thousands > 0:
            result.append(convert_three_digits(thousands) + ' ming')
        if remainder > 0:
            result.append(convert_three_digits(remainder))
        return ' '.join(result)
    else:
        millions = num // 1000000
        remainder = num % 1000000
        result = []
        if millions > 0:
            result.append(convert_three_digits(millions) + ' million')
        if remainder > 0:
            result.append(number_to_words_uz(remainder))
        return ' '.join(result)


def get_speciality_display_uz(speciality_id):
    """Get Uzbek display name for speciality"""
    speciality_map = {
        'revit_architecture': 'Autodesk Revit Architecture',
        'revit_structure': 'Autodesk Revit Structure',
        'tekla_structure': 'Tekla Structure'
    }
    return speciality_map.get(speciality_id, speciality_id)


def get_dates_display_uz(dates):
    """Get Uzbek display for lesson dates in Latin script"""
    dates_map = {
        'mon_wed_fri': 'Dushanba, Chorshanba, Juma',
        'tue_thu_sat': 'Seshanba, Payshanba, Shanba'
    }
    return dates_map.get(dates, dates)


def get_month_name_uz(month_num):
    """Get Uzbek month name in Latin script"""
    months = {
        1: 'yanvar', 2: 'fevral', 3: 'mart', 4: 'aprel',
        5: 'may', 6: 'iyun', 7: 'iyul', 8: 'avgust',
        9: 'sentabr', 10: 'oktabr', 11: 'noyabr', 12: 'dekabr'
    }
    return months.get(month_num, '')


def generate_student_contract(student):
    """
    Generate contract PDF for student using HTML template.
    All text in Latin script (Uzbek Latin alphabet).
    Uses HTML template with CSS styling for better control and flexibility.
    """
    buffer = BytesIO()
    
    # Prepare context data for template
    contract_number = f"BIMCEN-{student.id:04d}"
    current_date = timezone.now().date()
    month_name = get_month_name_uz(current_date.month)
    contract_date = f'"{current_date.day}" {month_name} {current_date.year} yil'
    
    # Get group information if available
    group = student.group
    if group:
        speciality_display = get_speciality_display_uz(group.speciality_id)
        starting_date = group.starting_date.strftime('%d.%m.%Y') if group.starting_date else '__.__.2026'
        finish_date = group.finish_date.strftime('%d.%m.%Y') if group.finish_date else '__.__.2026'
        total_lessons = group.total_lessons if group.total_lessons else '___'
        midpoint_lesson = group.get_midpoint_lesson() if group.total_lessons else '___'
        
        if group.price > 0:
            total_price = float(group.price)
            first_installment = total_price / 2
            second_installment = total_price / 2
            
            total_price_formatted = format_currency(total_price)
            total_price_words = number_to_words_uz(int(total_price))
            first_installment_formatted = format_currency(first_installment)
            first_installment_words = number_to_words_uz(int(first_installment))
            second_installment_formatted = format_currency(second_installment)
            second_installment_words = number_to_words_uz(int(second_installment))
            
            if group.total_lessons and midpoint_lesson and midpoint_lesson != '___' and total_lessons != '___':
                second_half_start = int(midpoint_lesson) + 1
                second_half_lessons = int(total_lessons) - int(midpoint_lesson)
            else:
                second_half_start = '___'
                second_half_lessons = '___'
        else:
            total_price_formatted = 'kelishuv asosida'
            total_price_words = ''
            first_installment_formatted = 'kelishuv asosida'
            first_installment_words = ''
            second_installment_formatted = 'kelishuv asosida'
            second_installment_words = ''
            midpoint_lesson = '___'
            second_half_start = '___'
            second_half_lessons = '___'
    else:
        speciality_display = 'Autodesk Revit Structure'
        starting_date = '__.__.2026'
        finish_date = '__.__.2026'
        total_lessons = '___'
        midpoint_lesson = '___'
        total_price_formatted = 'kelishuv asosida'
        total_price_words = ''
        first_installment_formatted = 'kelishuv asosida'
        first_installment_words = ''
        second_installment_formatted = 'kelishuv asosida'
        second_installment_words = ''
        second_half_start = '___'
        second_half_lessons = '___'
    
    # Get student information
    student_address = student.address if student.address else "___________________, ___________________________________, ________________________ko'chasi, ___- uy."
    student_inn = student.inn if student.inn else "______________________"
    student_pinfl = student.pinfl if student.pinfl else "______________________"
    student_phone = student.phone if student.phone else "______________________"
    
    # Find stamp image path
    stamp_url = None
    stamp_paths = []
    
    if hasattr(settings, 'CONTRACT_STAMP_PATH') and settings.CONTRACT_STAMP_PATH:
        if os.path.isabs(settings.CONTRACT_STAMP_PATH):
            stamp_paths.append(settings.CONTRACT_STAMP_PATH)
        else:
            stamp_paths.append(os.path.join(settings.BASE_DIR, settings.CONTRACT_STAMP_PATH))
    
    stamp_paths.extend([
        os.path.join(settings.BASE_DIR, 'static', 'stamp.png'),
        os.path.join(settings.BASE_DIR, 'media', 'stamp.png'),
        os.path.join(settings.STATIC_ROOT, 'stamp.png') if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT else None,
    ])
    
    for stamp_path in stamp_paths:
        if stamp_path and os.path.exists(stamp_path):
            stamp_url = stamp_path
            logger.info(f"Electronic stamp found at: {stamp_path}")
            break
    
    if not stamp_url:
        logger.warning("Electronic stamp image not found. Place stamp.png in static/ or media/ directory, or set CONTRACT_STAMP_PATH in settings.")
    
    # Prepare template context
    context = {
        'contract_number': contract_number,
        'contract_date': contract_date,
        'student_full_name': student.full_name,
        'student_address': student_address,
        'student_inn': student_inn,
        'student_pinfl': student_pinfl,
        'student_phone': student_phone,
        'speciality_display': speciality_display,
        'starting_date': starting_date,
        'finish_date': finish_date,
        'total_lessons': total_lessons,
        'midpoint_lesson': midpoint_lesson,
        'second_half_start': second_half_start,
        'second_half_lessons': second_half_lessons,
        'total_price_formatted': total_price_formatted,
        'total_price_words': total_price_words,
        'first_installment_formatted': first_installment_formatted,
        'first_installment_words': first_installment_words,
        'second_installment_formatted': second_installment_formatted,
        'second_installment_words': second_installment_words,
        'stamp_url': stamp_url,
    }
    
    # Render HTML template
    html_string = render_to_string('user/contracts/contract.html', context)
    
    # Convert HTML to PDF using WeasyPrint
    font_config = FontConfiguration()
    HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf(
        buffer,
        font_config=font_config
    )
    
    buffer.seek(0)
    return buffer
