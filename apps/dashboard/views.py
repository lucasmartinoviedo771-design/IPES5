from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.db.models import Count
from apps.users.models import UserProfile
from apps.preinscriptions.models import Preinscripcion
from apps.inscriptions.models import InscripcionCarrera, LegajoItem
from apps.academics.models import Carrera
from django.core.files.base import ContentFile
from django.urls import reverse
from apps.preinscriptions.forms import PreinscripcionForm
from apps.preinscriptions.pdf_utils import render_pdf_from_template

import logging
from django.http import HttpResponse, HttpResponseServerError
from django.contrib import messages
from django.views.decorators.http import require_http_methods

import io
import os
from datetime import datetime

from django.conf import settings
from django.http import Http404
from django.templatetags.static import static

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger("django.request")

def _is_staff_like(user):
    return user.is_authenticated and getattr(user, "rol", None) in (
        UserProfile.Rol.ADMIN, UserProfile.Rol.SECRETARIA, UserProfile.Rol.BEDEL
    )

def home(request):
    return render(request, "dashboard/home.html", {})

import traceback

def preinscripcion_form(request):
    try:
        if request.method == 'POST':
            form = PreinscripcionForm(request.POST, request.FILES)
            if form.is_valid():
                pre = form.save()
                return redirect('dashboard:pre_ok', pk=pre.pk)
        else:
            form = PreinscripcionForm()
        return render(request, 'dashboard/preinscripcion_form.html', {'form': form})

    except Exception:
        logger.exception("Fallo en preinscripcion_form")
        if settings.DEBUG:
            # <<— fuerza a ver el traceback en el navegador
            tb = traceback.format_exc()
            return HttpResponseServerError(f"<h1>Traceback</h1><pre>{tb}</pre>")
        return render(
            request,
            'dashboard/error_simple.html',
            {'mensaje': 'No pudimos cargar el formulario. Reintentá en unos minutos.'},
            status=500,
        )

def preinscripcion_ok(request, pk: int):
    """
    Muestra la página de OK. Si algo falla, devuelve el traceback en DEBUG.
    """
    try:
        pre = get_object_or_404(Preinscripcion, pk=pk)
        return render(request, "dashboard/preinscripcion_ok.html", {"pre": pre})
    except Exception:
        logger.exception("Error en preinscripcion_ok")
        if settings.DEBUG:
            return HttpResponse(
                traceback.format_exc(),
                content_type="text/plain",
                status=500,
            )
        # En prod, relanzar
        raise

def preinscripcion_gracias(request, pk):
    pre = get_object_or_404(Preinscripcion, pk=pk)
    return render(
        request,
        "dashboard/preinscripcion_gracias.html",
        {
            "pre": pre,
            "link_pdf": pre.comprobante_pdf.url if pre.comprobante_pdf else None,
        },
    )

@login_required
def panel(request):
    if not _is_staff_like(request.user):
        return HttpResponseForbidden("Permisos insuficientes")

    por_carrera = (
        Preinscripcion.objects.values("carrera__id", "carrera__nombre")
        .annotate(total=Count("id"))
        .order_by("carrera__nombre")
    )

    recientes = (
        Preinscripcion.objects.select_related("carrera")
        .order_by("-id")[:20]
    )

    return render(request, "dashboard/panel.html", {
        "por_carrera": por_carrera,
        "recientes": recientes,
    })

@login_required
def legajo_detalle(request, insc_id: int):
    if not _is_staff_like(request.user):
        return HttpResponseForbidden("Permisos insuficientes")

    insc = (
        InscripcionCarrera.objects
        .select_related("estudiante", "carrera")
        .filter(id=insc_id)
        .first()
    )
    if not insc:
        return render(request, "dashboard/legajo.html", {"error": "Inscripción no encontrada"})

    items = (
        LegajoItem.objects
        .select_related("tipo")
        .filter(inscripcion=insc)
        .order_by("tipo__nombre")
    )
    total = items.count()
    cumplidos = items.filter(cumplido=True).count()

    return render(request, "dashboard/legajo.html", {
        "insc": insc,
        "items": items,
        "total": total,
        "cumplidos": cumplidos,
        "legajo_estado": getattr(insc, "legajo_estado", "INCOMPLETO"),
        "condicion": getattr(insc, "condicion", "CONDICIONADO"),
    })

def draw_qr(c, pre, x_mm, y_mm, size_mm=28, show_label=True):
    """
    Dibuja un QR en (x_mm, y_mm) mm (esquina inferior izquierda), tamaño size_mm x size_mm.
    Si settings.PREINSCRIPCION_VERIFY_BASE está definido, el QR codifica una URL; si no, el número.
    """
    verify_base = getattr(settings, 'PREINSCRIPCION_VERIFY_BASE', None)
    if verify_base:
        qr_value = f"{verify_base}{pre.pk}/{pre.numero}/"
    else:
        qr_value = pre.numero or ""

    size = size_mm * mm
    x = x_mm * mm
    y = y_mm * mm

    qr_widget = qr.QrCodeWidget(qr_value, barLevel='H')  # corrección de error alta
    x1, y1, x2, y2 = qr_widget.getBounds()
    w, h = (x2 - x1), (y2 - y1)

    d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
    d.add(qr_widget)

    # Fondo blanco para “quiet zone”
    c.setFillColorRGB(1, 1, 1)
    c.rect(x - 1*mm, y - 1*mm, size + 2*mm, size + 2*mm, fill=1, stroke=0)

    renderPDF.draw(d, c, x, y)

    if show_label and getattr(pre, 'numero', None):
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 9)
        c.drawCentredString(x + size/2, y - 4*mm, pre.numero)

def preinscripcion_pdf(request, pk):
    try:
        pre = get_object_or_404(Preinscripcion, pk=pk)

        # ======= utilidades (igual que antes) =======
        FONT_MAIN = "Helvetica"
        font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "DejaVuSans.ttf")
        if os.path.isfile(font_path):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
                FONT_MAIN = "DejaVuSans"
            except Exception:
                pass

        def F(c, size, bold=False):
            if FONT_MAIN == "DejaVuSans":
                c.setFont(FONT_MAIN, size)
            else:
                c.setFont("Helvetica-Bold" if bold else "Helvetica", size)

        def S(x):
            s = "" if x is None else str(x)
            if FONT_MAIN != "DejaVuSans":
                s = (s.replace("–", "-").replace("—", "-")
                       .replace("’", "'" ).replace("“", '"').replace("”", '"'))
            return s

        # ======= salida PDF =======
        anio = pre.anio or datetime.now().year
        numero = pre.numero or f"PRE-{anio}-{pre.pk:04d}"
        filename = f"preinscripcion-{numero}.pdf"

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        W, H = A4
        Mx, My = 18*mm, 15*mm
        y_top = H - My

        def line(ypos):
            c.setLineWidth(0.7)
            c.line(Mx, ypos, W - Mx, ypos)

        def label_value(x, y, label, value, lw=140, lh=12):
            F(c, 9, bold=True);  c.drawString(x, y, S(label))
            F(c, 10, bold=False); c.drawString(x + lw, y, S(value))
            return y - lh

        def checkbox(x, y, checked=False, label=""):
            size = 10
            c.rect(x, y - size + 2, size, size, fill=0)
            if checked:
                c.setLineWidth(2)
                c.line(x+2, y - size + 4, x+size-2, y-2)
                c.line(x+2, y-2, x+size-2, y - size + 4)
                c.setLineWidth(1)
            if label:
                F(c, 10); c.drawString(x + size + 4, y - size + 4, S(label))

        # ======= Encabezado =======
        # Logos (opcional)
        for path, dx in [
            (os.path.join(settings.BASE_DIR, "static", "img", "logo_provincia.png"), Mx),
            (os.path.join(settings.BASE_DIR, "static", "img", "logo_ipes.png"), W-Mx-22*mm),
        ]:
            try:
                if os.path.isfile(path):
                    c.drawImage(ImageReader(path), dx, y_top-22*mm, width=22*mm, height=22*mm, mask='auto')
            except Exception:
                pass

        # Títulos
        F(c, 14, bold=True); c.drawCentredString(W/2, y_top-10*mm, S(f"PLANILLA DE PREINSCRIPCIÓN {anio}"))
        F(c, 11);            c.drawCentredString(W/2, y_top-16*mm, S(str(pre.carrera) or ""))

        # --- QR PRINCIPAL (arriba-izquierda) ---
        page_w, page_h = c._pagesize
        qr_main_size = 28  # mm
        # margen izquierdo ~18mm, margen superior ~24mm
        draw_qr(
            c, pre,
            x_mm=18,
            y_mm=(page_h/mm) - 24 - qr_main_size,
            size_mm=qr_main_size,
            show_label=False,   # sin número debajo para no chocar con "Datos personales"
        )

        # Foto 4x4 (un poco más arriba)
        try:
            if pre.foto_4x4:
                foto_path = os.path.join(settings.MEDIA_ROOT, str(pre.foto_4x4))
                if os.path.isfile(foto_path):
                    c.drawImage(ImageReader(foto_path),
                                W-Mx-35*mm, y_top-39*mm,  # antes -45mm -> la subimos ~6mm
                                width=32*mm, height=32*mm, mask='auto')
        except Exception:
            pass

        # Espacio seguro antes de “Datos personales” (evita superposición con el código)
        y = y_top - 40*mm

        # ======= Datos personales =======
        F(c, 12, bold=True); c.drawString(Mx, y, S("Datos personales")); y -= 10; line(y); y -= 12
        y = label_value(Mx, y, "C.U.I.L. / C.U.I.T.:", pre.cuil or "")
        y = label_value(Mx, y, "D.N.I.:", pre.dni or "")
        y = label_value(Mx, y, "Apellido:", pre.apellido or "")
        y = label_value(Mx, y, "Nombres:", pre.nombres or "")
        y = label_value(Mx, y, "Fecha de nacimiento:",
                        pre.fecha_nacimiento.strftime("%d/%m/%Y") if pre.fecha_nacimiento else "")
        y = label_value(Mx, y, "Estado civil:", pre.estado_civil or "")
        y = label_value(Mx, y, "Localidad de nacimiento:", pre.localidad_nac or getattr(pre, "loc_nacimiento", "") or "")
        y = label_value(Mx, y, "Provincia de nacimiento:", pre.provincia_nac or getattr(pre, "prov_nacimiento", "") or "")
        y = label_value(Mx, y, "País de nacimiento:", pre.pais_nac or getattr(pre, "pais_nacimiento", "") or "")
        y = label_value(Mx, y, "Nacionalidad:", pre.nacionalidad or "")

        y -= 6
        # ======= Contacto =======
        F(c, 12, bold=True); c.drawString(Mx, y, S("Datos de contacto")); y -= 10; line(y); y -= 12
        y = label_value(Mx, y, "Domicilio:", pre.domicilio or "")
        y = label_value(Mx, y, "Teléfono fijo:", pre.tel_fijo or "")
        y = label_value(Mx, y, "Teléfono móvil:", pre.tel_movil or "")
        y = label_value(Mx, y, "E-mail:", pre.email or "")

        y -= 6
        # ======= Estudios =======
        F(c, 12, bold=True); c.drawString(Mx, y, S("Estudios")); y -= 10; line(y); y -= 12
        y = label_value(Mx, y, "Título secundario:", pre.sec_titulo or getattr(pre, "secu_titulo", "") or "")
        y = label_value(Mx, y, "Establecimiento:", pre.sec_establecimiento or getattr(pre, "secu_establecimiento", "") or "")
        y = label_value(Mx, y, "Fecha de egreso:",
                        (pre.sec_fecha_egreso or getattr(pre, "secu_fecha_egreso", None) or None).strftime("%d/%m/%Y")
                        if (pre.sec_fecha_egreso or getattr(pre, "secu_fecha_egreso", None)) else "")
        y = label_value(Mx, y, "Localidad:", pre.sec_localidad or getattr(pre, "secu_localidad", "") or "")
        y = label_value(Mx, y, "Provincia:", pre.sec_provincia or getattr(pre, "secu_provincia", "") or "")
        y = label_value(Mx, y, "País:", pre.sec_pais or getattr(pre, "secu_pais", "") or "")

        y -= 6
        # ======= Laborales =======
        F(c, 12, bold=True); c.drawString(Mx, y, S("Datos laborales")); y -= 10; line(y); y -= 12
        y = label_value(Mx, y, "¿Trabaja?:", "SI" if pre.trabaja else "NO")
        y = label_value(Mx, y, "Empleador:", pre.empleador or "")
        y = label_value(Mx, y, "Horario:", pre.horario_trabajo or "")
        y = label_value(Mx, y, "Domicilio de trabajo:", pre.domicilio_trabajo or "")

        y -= 6
        # ======= Documentación presentada =======
        F(c, 12, bold=True); c.drawString(Mx, y, S("Documentación presentada")); y -= 10; line(y); y -= 16
        xcol = Mx; col2 = Mx + 85*mm

        checkbox(xcol, y,     bool(pre.doc_fotocopia_titulo_legalizada), "Fotocopia legalizada del D.N.I.")
        checkbox(xcol, y-16,  bool(pre.doc_fotocopia_analitico_legalizada), "Fotocopia legalizada de analítico")
        checkbox(xcol, y-32,  bool(pre.doc_fotos_4x4), "2 fotos carnet 4x4")
        checkbox(xcol, y-48,  bool(pre.doc_titulo_secundario), "Título secundario / terciario / universitario")
        checkbox(xcol, y-64,  bool(pre.doc_cert_alumno_regular), "Certificado de alumno regular")
        checkbox(xcol, y-80,  bool(pre.doc_cert_buena_salud), "Certificado de buena salud")

        checkbox(col2, y,     bool(pre.doc_cert_titulo_en_tramite), "Certificado de título en trámite")
        checkbox(col2, y-16,  bool(pre.doc_folios), "3 folios oficio")
        checkbox(col2, y-32,  bool(pre.doc_adeuda_materias), "Si adeuda materias (adjunta constancia)")

        # Orden pedido: Escuela primero, luego Detalle
        F(c, 9)
        c.drawString(col2+18*mm, y-46, S(f"Escuela: {getattr(pre,'doc_adeuda_materias_escuela','') or getattr(pre,'adeuda_materias_escuela','')}"))
        c.drawString(col2+18*mm, y-58, S(f"Detalle: {getattr(pre,'doc_adeuda_materias_detalle','') or getattr(pre,'adeuda_materias_detalle','')}"))

        # Incumbencias solo para certificación docente
        is_cert_doc = "certific" in (str(pre.carrera) or "").lower() and "docent" in (str(pre.carrera) or "").lower()
        if is_cert_doc:
            checkbox(col2, y-74, bool(getattr(pre, "doc_incumbencias", False)), "Incumbencias")

        y -= 100

        # Firmas
        y -= 12
        c.line(Mx, y, Mx+70*mm, y); F(c, 9); c.drawString(Mx, y-12, S("Firma, aclaración del inscripto"))
        c.line(W-Mx-70*mm, y, W-Mx, y); c.drawString(W-Mx-70*mm, y-12, S("Firma, aclaración del personal"))

        # Talón inferior
        F(c, 11, bold=True); c.drawString(Mx, 38*mm, S("Comprobante de Inscripción del alumno"))
        F(c, 10); c.drawString(Mx, 32*mm, S(f"Carrera: {pre.carrera}"))
        c.drawString(Mx, 26*mm, S(f"Alumno/a: {pre.apellido}, {pre.nombres}"))
        c.drawString(Mx, 20*mm, S(f"Número de preinscripción: {numero}"))
        
        # --- QR DEL COMPROBANTE (abajo-derecha, más abajo que antes) ---
        qr_comp_size = 22  # mm
        # queda a la derecha; lo bajo cerca del pie (antes ~30mm, ahora ~14mm del borde)
        draw_qr(
            c, pre,
            x_mm=(W/mm) - 25 - qr_comp_size,
            y_mm=14,
            size_mm=qr_comp_size,
            show_label=True,    # acá sí mostramos el número
        )


        c.showPage(); c.save()
        pdf = buf.getvalue(); buf.close()
        response.write(pdf)
        return response

    except Exception:
        if settings.DEBUG:
            return HttpResponse("PDF ERROR\n\n" + traceback.format_exc(),
                                content_type="text/plain", status=500)
        raise
