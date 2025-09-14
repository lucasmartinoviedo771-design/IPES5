from io import BytesIO
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from .models import Preinscripcion

def preinscripcion_pdf(request, pk):
    pre = get_object_or_404(Preinscripcion, pk=pk)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    y = h - 25*mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20*mm, y, "Planilla de Preinscripción 2025")
    y -= 10*mm

    c.setFont("Helvetica", 10)
    c.drawString(20*mm, y, f"Número: {pre.numero or '-'}")
    y -= 6*mm
    c.drawString(20*mm, y, f"Carrera: {getattr(pre.carrera, 'nombre', '-')}")
    y -= 6*mm

    c.drawString(20*mm, y, f"Apellido: {pre.apellido or '-'}    Nombres: {pre.nombres or '-'}")
    y -= 6*mm
    c.drawString(20*mm, y, f"DNI: {pre.dni or '-'}    CUIL/CUIT: {pre.cuil or '-'}")
    y -= 6*mm
    c.drawString(20*mm, y, f"Fecha nac.: {pre.fecha_nacimiento or '-'}  Localidad nac.: {pre.localidad_nac or '-'}")
    y -= 6*mm
    c.drawString(20*mm, y, f"Provincia nac.: {pre.provincia_nac or '-'}  País nac.: {pre.pais_nac or '-'}")
    y -= 6*mm
    c.drawString(20*mm, y, f"Nacionalidad: {pre.nacionalidad or '-'}")
    y -= 10*mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(20*mm, y, "Documentación (a completar en mesa de entradas)")
    y -= 8*mm
    c.setFont("Helvetica", 10)
    checks = [
        "Fotocopia legalizada del título", "Analítico legalizado",
        "Fotos carnet 4x4", "Título secundario",
        "Certificado de alumno regular", "Certificado de título en trámite",
        "Certificado de buena salud", "Folios",
        "Declaración jurada / Nota compromiso"
    ]
    for label in checks:
        c.rect(20*mm, y-3*mm, 4*mm, 4*mm)  # casilla vacía
        c.drawString(26*mm, y-2*mm, label)
        y -= 7*mm
        if y < 20*mm:
            c.showPage(); y = h - 20*mm; c.setFont("Helvetica", 10)

    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()

    return HttpResponse(pdf, content_type='application/pdf')