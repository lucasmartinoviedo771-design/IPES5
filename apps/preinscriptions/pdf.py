# apps/preinscriptions/pdf.py
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def _draw_checkbox(c, x, y, label, checked=False):
    box_size = 4*mm
    c.rect(x, y, box_size, box_size)
    c.setFont("Helvetica", 9)
    c.drawString(x + box_size + 2*mm, y + 1.2*mm, label)
    if checked:
        c.setLineWidth(1)
        c.line(x, y, x+box_size, y+box_size)
        c.line(x, y+box_size, x+box_size, y)

def _draw_kv(c, x, y, label, value, w_label=35*mm, w_value=120*mm, font_size=10):
    c.setFont("Helvetica-Bold", font_size)
    c.drawString(x, y, f"{label}:")
    c.setFont("Helvetica", font_size)
    c.drawString(x + w_label, y, value or "-")

def render_preinscripcion_pdf(pre) -> bytes:
    """
    Genera un PDF A4 con cabecera 'Planilla de Preinscripción 2025',
    datos del aspirante y talón desprendible.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    margin = 15*mm
    y = H - margin

    # Encabezado
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "Planilla de Preinscripción 2025")
    y -= 10*mm

    # Datos básicos
    _draw_kv(c, margin, y, "Carrera", getattr(getattr(pre, "carrera", None), "nombre", ""))
    y -= 6*mm
    _draw_kv(c, margin, y, "DNI", getattr(pre, "dni", ""))
    y -= 6*mm
    _draw_kv(c, margin, y, "CUIL", getattr(pre, "cuil", "") or "-")
    y -= 6*mm
    ap_nom = f"{getattr(pre,'apellido','')}, {getattr(pre,'nombres','')}".strip(", ")
    _draw_kv(c, margin, y, "Apellido y Nombres", ap_nom)
    y -= 6*mm
    _draw_kv(c, margin, y, "Fecha Nac.", getattr(pre, "fecha_nacimiento", "") or "-")
    y -= 8*mm

    # Contacto
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Datos de Contacto")
    y -= 6*mm
    _draw_kv(c, margin, y, "Email", getattr(pre, "email", "") or "-")
    y -= 6*mm
    _draw_kv(c, margin, y, "Tel. Móvil", getattr(pre, "tel_movil", "") or "-")
    y -= 6*mm
    _draw_kv(c, margin, y, "Domicilio", getattr(pre, "domicilio", "") or "-")
    y -= 8*mm

    # Documentación (checkboxes vacíos para completar a mano)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Documentación Presentada (a completar por Secretaría)")
    y -= 7*mm
    _draw_checkbox(c, margin, y, "Título secundario", False)
    _draw_checkbox(c, margin + 70*mm, y, "Certificado de título en trámite", False)
    y -= 7*mm
    _draw_checkbox(c, margin, y, "Adeuda materias", False)
    _draw_checkbox(c, margin + 70*mm, y, "DJ / Nota de compromiso", False)
    y -= 7*mm
    _draw_checkbox(c, margin, y, "Incumbencias (solo Certificación Docente)", False)
    y -= 10*mm

    # Foto 4x4
    foto = getattr(pre, "foto_4x4", None)
    if foto and getattr(foto, "path", None):
        try:
            c.drawImage(foto.path, W - margin - 30*mm, H - margin - 35*mm, width=30*mm, height=35*mm, preserveAspectRatio=True, mask='auto')
            c.rect(W - margin - 30*mm, H - margin - 35*mm, 30*mm, 35*mm)
        except Exception:
            pass

    # Línea de corte (talón)
    c.setDash(3, 3)
    c.line(margin, 50*mm, W - margin, 50*mm)
    c.setDash(1, 0)
    c.setFont("Helvetica", 9)
    c.drawString(margin, 52*mm, "Corte aquí — Talón Comprobante")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, 45*mm, "Comprobante de Preinscripción — IPES")
    c.setFont("Helvetica", 10)
    c.drawString(margin, 39*mm, f"Aspirante: {ap_nom} — DNI: {getattr(pre, 'dni', '')}")
    c.drawString(margin, 33*mm, f"Carrera: {getattr(getattr(pre, 'carrera', None), 'nombre', '')}")
    c.drawString(margin, 27*mm, "Documentación (a completar por Secretaría): □ Título  □ Cert. Trámite  □ Adeuda  □ DJ/Compromiso  □ Incumbencias")

    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()
    return pdf
