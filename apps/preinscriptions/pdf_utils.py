from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa

def render_pdf_from_template(template_name: str, context: dict) -> bytes:
    template = get_template(template_name)
    html = template.render(context)
    result = BytesIO()
    pisa.CreatePDF(html, dest=result, encoding='UTF-8')
    return result.getvalue()