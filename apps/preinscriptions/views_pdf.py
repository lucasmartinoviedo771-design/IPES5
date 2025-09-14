# apps/preinscriptions/views_pdf.py
from io import BytesIO
from datetime import date
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

import qrcode
import traceback

from .models import Preinscripcion  # ajustá el import si tu app cambia


# ------------------------ helpers ------------------------

def _img_or_none(path_like):
    try:
        p = Path(path_like)
        if p.is_file():
            return ImageReader(str(p))
    except Exception:
        pass
    return None


def _text(c, x, y, text, size=9, bold=False):
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.drawString(x, y, str(text) if text is not None else "")


    # === espaciado global ===
ROW = 5 * mm  # interlineado estándar de TODO el formulario

def gap(n=1):
    """n saltos de interlineado (5mm cada uno). gap(1) = 4 mm."""
    return n * ROW

def _img_or_none(path_like):
    try:
        p = Path(path_like)
        if p.is_file():
            return ImageReader(str(p))
    except Exception:
        pass
    return None


def _text(c, x, y, text, size=9, bold=False):
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.drawString(x, y, str(text) if text is not None else "")


def _label_value(c, x, y, label, value, lw=35*mm, gap=3*mm, size=9):
    _text(c, x, y, f"{label}:", size=size, bold=True)
    _text(c, x + lw + gap, y, value or "", size=9)

def _label_value_auto(c, x, y, label, value, gap=5*mm, size=9, min_lw=35*mm):
    """
    Dibuja 'Label:  Value' midiendo el ancho real de la etiqueta para que
    el valor nunca se superponga. min_lw es el mínimo reservado para etiqueta.
    """
    lbl = f"{label}:"
    # medir ancho real de la etiqueta en la fuente bold
    label_w = c.stringWidth(lbl, "Helvetica-Bold", size)
    lw = max(min_lw, label_w)
    _text(c, x, y, lbl, size=size, bold=True)
    _text(c, x + lw + gap, y, value or "", size=size)


def _section_title(c, x, y, title, width):
    _text(c, x, y, title, size=11, bold=True)
    c.line(x, y-2, x+width, y-2)


def _line(c, x1, y1, x2, y2):
    c.line(x1, y1, x2, y2)


def _checkbox(c, x, y, label, checked=False, size=4.5*mm, gap=3*mm):
    c.rect(x, y, size, size, stroke=1, fill=0)
    if checked:
        c.setLineWidth(1)
        c.line(x+1, y+1, x+size-1, y+size-1)
        c.line(x+1, y+size-1, x+size-1, y+1)
    _text(c, x + size + gap, y + 1, label, size=9)

def _two_col_kv(c, y_start, left_pairs, right_pairs, left_x, right_x, row_h=ROW, pad=1):
    """Pares (label, valor) en dos columnas. 'pad' = saltos extra al final."""
    y_l = y_start
    y_r = y_start
    for label, value in left_pairs:
        _label_value(c, left_x, y_l, label, value); y_l -= row_h
    for label, value in right_pairs:
        _label_value(c, right_x, y_r, label, value); y_r -= row_h
    return min(y_l, y_r) - pad * row_h  # un 'salto' extra por defecto

def _checkbox_cols(c, y_start, items, col_xs, row_gap=ROW):
    """Checkboxes en N columnas, con interlineado configurable."""
    ys = [y_start for _ in col_xs]
    col = 0
    for label, checked in items:
        _checkbox(c, col_xs[col], ys[col], label, checked)
        ys[col] -= row_gap
        col = (col + 1) % len(col_xs)
    return min(ys)


def _draw_qr(c, data, x_mm, y_mm, size_mm):
    if not data:
        return
    qr = qrcode.QRCode(border=0, box_size=6)
    qr.add_data(str(data))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    c.drawImage(ImageReader(buf), x_mm*mm, y_mm*mm, width=size_mm*mm, height=size_mm*mm, preserveAspectRatio=True, mask='auto')


def _get(v, *alts):
    """Devuelve v o el primer atributo alternativo existente en el objeto v si v es None."""
    if v is not None:
        return v
    # si se usa con pre y nombres alternativos: _get(getattr(pre,'localidad_nac',None), pre.loc_nacimiento, ...)
    for a in alts:
        if a:
            return a
    return None

def _nz(v, placeholder="---"):
    return str(v) if (v is not None and str(v).strip() != "") else placeholder


def _section_title(c, x, y, title, width):
    _text(c, x, y, title, size=11, bold=True)
    c.line(x, y-2, x+width, y-2)


def _line(c, x1, y1, x2, y2):
    c.line(x1, y1, x2, y2)


def _checkbox(c, x, y, label, checked=False, size=4.5*mm, gap=3*mm):
    c.rect(x, y, size, size, stroke=1, fill=0)
    if checked:
        c.setLineWidth(1)
        c.line(x+1, y+1, x+size-1, y+size-1)
        c.line(x+1, y+size-1, x+size-1, y+1)
    _text(c, x + size + gap, y + 1, label, size=9)

def _two_col_kv(c, y_start, left_pairs, right_pairs, left_x, right_x, row_h=ROW, pad=1):
    """Pares (label, valor) en dos columnas. 'pad' = saltos extra al final."""
    y_l = y_start
    y_r = y_start
    for label, value in left_pairs:
        _label_value(c, left_x, y_l, label, value); y_l -= row_h
    for label, value in right_pairs:
        _label_value(c, right_x, y_r, label, value); y_r -= row_h
    return min(y_l, y_r) - pad * row_h  # un 'salto' extra por defecto

def _checkbox_cols(c, y_start, items, col_xs, row_gap=ROW):
    """Checkboxes en N columnas, con interlineado configurable."""
    ys = [y_start for _ in col_xs]
    col = 0
    for label, checked in items:
        _checkbox(c, col_xs[col], ys[col], label, checked)
        ys[col] -= row_gap
        col = (col + 1) % len(col_xs)
    return min(ys)


def _draw_qr(c, data, x_mm, y_mm, size_mm):
    if not data:
        return
    qr = qrcode.QRCode(border=0, box_size=6)
    qr.add_data(str(data))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    c.drawImage(ImageReader(buf), x_mm*mm, y_mm*mm, width=size_mm*mm, height=size_mm*mm, preserveAspectRatio=True, mask='auto')


def _get(v, *alts):
    """Devuelve v o el primer atributo alternativo existente en el objeto v si v es None."""
    if v is not None:
        return v
    # si se usa con pre y nombres alternativos: _get(getattr(pre,'localidad_nac',None), pre.loc_nacimiento, ...)
    for a in alts:
        if a:
            return a
    return None

def _nz(v, placeholder="---"):
    return str(v) if (v is not None and str(v).strip() != "") else placeholder

# === espaciado global ===
ROW = 4 * mm  # interlineado estándar de TODO el formulario

def gap(n=1):
    """n saltos de interlineado (5mm cada uno). gap(1) = 4 mm."""
    return n * ROW

# ------------------------ main view ------------------------

def preinscripcion_pdf(request, pk):
    try:
        pre = get_object_or_404(Preinscripcion, pk=pk)

        anio = pre.anio or date.today().year
        carrera = str(getattr(pre, "carrera", ""))
        numero = getattr(pre, "numero", "") or f"PRE-{anio}-{pre.pk:04d}"

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        W, H = A4
        M = 18 * mm
        usable_w = W - 2 * M
        row_h = ROW

        # --- Geometría del comprobante (parte de abajo fija) ---
        COMP_MARGIN_BOTTOM = 12 * mm        # margen inferior
        COMP_H             = 38 * mm        # alto destinado al comprobante (título + 3 líneas + QR)
        COMP_TOP           = COMP_MARGIN_BOTTOM + COMP_H   # y de la línea separadora

        # ===== Encabezado =====
        TOP_H = 52 * mm          # altura reservada de encabezado (más generosa)
        QR_SIZE = 24 * mm

        title_y    = H - 16 * mm
        subtitle_y = title_y - 6 * mm

        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(W / 2, title_y, f"PLANILLA DE PREINSCRIPCIÓN {anio}")
        c.setFont("Helvetica", 11)
        c.drawCentredString(W / 2, subtitle_y, carrera)

        

        # Logo arriba-izquierda
        logo_path = Path(settings.BASE_DIR) / "Logos" / "logoipes.jpg"
        if not logo_path.is_file():
            logo_path = Path(settings.BASE_DIR) / "static" / "img" / "ipes-logo.png"
        logo = _img_or_none(logo_path)
        logo_w = 24 * mm; logo_h = 24 * mm
        logo_x = M; logo_y = H - M - logo_h + 2 * mm
        if logo:
            c.drawImage(logo, logo_x, logo_y, width=logo_w, height=logo_h,
                        preserveAspectRatio=True, mask='auto')

        # Foto arriba-derecha
        foto_reader = None
        try:
            if getattr(pre, "foto_4x4", None):
                foto_reader = ImageReader(pre.foto_4x4.path)
        except Exception:
            pass
        if foto_reader:
            foto_w = 30 * mm; foto_h = 30 * mm
            foto_x = W - M - foto_w
            foto_y = H - M - foto_h + 2 * mm
            c.drawImage(foto_reader, foto_x, foto_y, width=foto_w, height=foto_h,
                        preserveAspectRatio=True, mask='auto')

        # --- calcular dónde empieza el contenido (debajo de logo/foto) ---
        # si alguno no existe, tomamos el que haya; si no hay ninguno, usamos un margen seguro
        element_bottoms = []

        # ojo: en reportlab, 'y' es la coordenada de la BASE de la imagen
        if logo:
            element_bottoms.append(logo_y)                 # base del logo
        if foto_reader:
            element_bottoms.append(foto_y)                 # base de la foto

        # espacio mínimo bajo el título/subtítulo
        subtitle_clearance = subtitle_y - 3*ROW         # ~15mm

        if element_bottoms:
            # empezamos el contenido 6mm por debajo del elemento más bajo (logo o foto)
            content_start = min(element_bottoms) - ROW      # 5mm
            # por seguridad, no subir por encima del subtítulo despejado
            y = min(content_start, subtitle_clearance)
        else:
            # si no hay logo/foto, arrancamos apenas debajo del subtítulo
            y = subtitle_clearance

        # ===== Datos personales =====
        _section_title(c, M, y, "Datos personales", usable_w)
        y -= gap(2)

        left_x  = M
        right_x = M + usable_w / 2 + 6 * mm

        _label_value(c, left_x, y, "C.U.I.L. / C.U.I.T.", _get(getattr(pre, "cuil_cuit", None), getattr(pre, "cuil", None))); y -= gap(1)
        _label_value(c, left_x, y, "D.N.I.", getattr(pre, "dni", "")); y -= gap(1)
        _label_value(c, left_x, y, "Apellido", getattr(pre, "apellido", "")); y -= gap(1)
        _label_value(c, left_x, y, "Nombres", getattr(pre, "nombres", "")); y -= gap(1)
        _label_value(c, left_x, y, "Fecha de nacimiento", getattr(pre, "fecha_nacimiento", "")); y -= gap(1)
        _label_value(c, left_x, y, "Estado civil", getattr(pre, "estado_civil", "")); y -= gap(1)

        y2 = y + 5 * row_h
        _label_value(c, right_x, y2, "Localidad de nacimiento", _get(getattr(pre, "localidad_nac", None), getattr(pre, "loc_nacimiento", None))); y2 -= gap(1)
        _label_value(c, right_x, y2, "Provincia de nacimiento", _get(getattr(pre, "provincia_nac", None), getattr(pre, "prov_nacimiento", None))); y2 -= gap(1)
        _label_value(c, right_x, y2, "País de nacimiento", _get(getattr(pre, "pais_nac", None), getattr(pre, "pais_nacimiento", None))); y2 -= gap(1)
        _label_value(c, right_x, y2, "Nacionalidad", getattr(pre, "nacionalidad", ""))

        y = min(y, y2) - gap(1)

        # ===== Contacto (dos columnas) =====
        _section_title(c, M, y, "Datos de contacto", usable_w)
        y -= gap(2)
        left_x  = M
        right_x = M + usable_w/2 + 6*mm

        left_pairs = [
            ("Domicilio", getattr(pre, "domicilio", "")),
            ("Teléfono fijo", getattr(pre, "tel_fijo", "")),
        ]
        right_pairs = [
            ("Teléfono móvil", getattr(pre, "tel_movil", "")),
            ("E-mail", getattr(pre, "email", "")),
        ]
        y = _two_col_kv(c, y, left_pairs, right_pairs, left_x, right_x, row_h)

        # ===== Estudios (3 niveles: Secundario, Terciario, Universitario) =====
        _section_title(c, M, y, "Estudios", usable_w)
        y -= gap(2)

        left_x  = M
        right_x = M + usable_w/2 + 6*mm

        # Interlineados (compacto para que entren los 3 bloques)
        row_h_std   = ROW
        row_h_dense = ROW

        # ---------- SECUNDARIO ----------
        _text(c, M, y, "Secundario", size=10, bold=True); y -= gap(1)
        left_pairs = [
            ("Título",      _nz(_get(getattr(pre,"sec_titulo",None), getattr(pre,"secu_titulo",None)))),
            ("Fecha egreso",_nz(_get(getattr(pre,"sec_fecha_egreso",None), getattr(pre,"secu_fecha_egreso",None)))),
            ("Provincia",   _nz(_get(getattr(pre,"sec_provincia",None), getattr(pre,"secu_provincia",None)))),
        ]
        right_pairs = [
            ("Establecimiento", _nz(_get(getattr(pre,"sec_establecimiento",None), getattr(pre,"secu_establecimiento",None)))),
            ("Localidad",       _nz(_get(getattr(pre,"sec_localidad",None), getattr(pre,"secu_localidad",None)))),
            ("País",            _nz(_get(getattr(pre,"sec_pais",None), getattr(pre,"secu_pais",None)))),
        ]
        y = _two_col_kv(c, y, left_pairs, right_pairs, left_x, right_x, row_h_std)

        # ---------- TERCIARIO (opcional pero SIEMPRE visible) ----------
        _text(c, M, y, "Terciario (opcional)", size=10, bold=True); y -= gap(1)
        left_pairs = [
            ("Título",      _nz(_get(getattr(pre,"ter_titulo",None),       getattr(pre,"terciario_titulo",None)))),
            ("Fecha egreso",_nz(_get(getattr(pre,"ter_fecha_egreso",None), getattr(pre,"terciario_fecha_egreso",None)))),
            ("Provincia",   _nz(_get(getattr(pre,"ter_provincia",None),    getattr(pre,"terciario_provincia",None)))),
        ]
        right_pairs = [
            ("Establecimiento", _nz(_get(getattr(pre,"ter_establecimiento",None), getattr(pre,"terciario_establecimiento",None)))),
            ("Localidad",       _nz(_get(getattr(pre,"ter_localidad",None),       getattr(pre,"terciario_localidad",None)))),
            ("País",            _nz(_get(getattr(pre,"ter_pais",None),            getattr(pre,"terciario_pais",None)))),
        ]
        y = _two_col_kv(c, y, left_pairs, right_pairs, left_x, right_x, row_h_dense)

        # ---------- UNIVERSITARIO (opcional pero SIEMPRE visible) ----------
        _text(c, M, y, "Universitario (opcional)", size=10, bold=True); y -= gap(1)
        left_pairs = [
            ("Título",      _nz(_get(getattr(pre,"uni_titulo",None),       getattr(pre,"universitario_titulo",None)))),
            ("Fecha egreso",_nz(_get(getattr(pre,"uni_fecha_egreso",None), getattr(pre,"universitario_fecha_egreso",None)))),
            ("Provincia",   _nz(_get(getattr(pre,"uni_provincia",None),    getattr(pre,"universitario_provincia",None)))),
        ]
        right_pairs = [
            ("Establecimiento", _nz(_get(getattr(pre,"uni_establecimiento",None), getattr(pre,"universitario_establecimiento",None)))),
            ("Localidad",       _nz(_get(getattr(pre,"uni_localidad",None),       getattr(pre,"universitario_localidad",None)))),
            ("País",            _nz(_get(getattr(pre,"uni_pais",None),            getattr(pre,"universitario_pais",None)))),
        ]
        y = _two_col_kv(c, y, left_pairs, right_pairs, left_x, right_x, row_h_dense)

        # ===== Datos laborales (dos columnas) =====
        _section_title(c, M, y, "Datos laborales", usable_w)
        y -= gap(2)
        left_x  = M
        right_x = M + usable_w/2 + 6*mm

        left_pairs = [
            ("¿Trabaja?", "SI" if getattr(pre,"trabaja",False) else "NO"),
            ("Horario",   getattr(pre,"horario_trabajo","")),
        ]
        right_pairs = [
            ("Empleador", getattr(pre,"empleador","")),
            ("Domicilio de trabajo", getattr(pre,"domicilio_trabajo","")),
        ]
        y = _two_col_kv(c, y, left_pairs, right_pairs, left_x, right_x, row_h)

        # Respiro para evitar solape con el siguiente título
        y -= 4 * mm

        # ===== Documentación presentada (tres columnas) =====
        _section_title(c, M, y, "Documentación presentada", usable_w)
        y -= gap(2)

        # x de 3 columnas equidistantes
        col_xs = [
            M,
            M + usable_w/3 + 4*mm,
            M + 2*usable_w/3 + 8*mm,
        ]

        items = [
            ("Fotocopia legalizada del D.N.I.", getattr(pre,"doc_fotocopia_titulo_legalizada",False)),
            ("Fotocopia legalizada de analítico", getattr(pre,"doc_fotocopia_analitico_legalizada",False)),
            ("2 fotos carnet 4x4", getattr(pre,"doc_fotos_4x4",False)),
            ("Título sec./terc./univ.",   # ← abreviado
                getattr(pre,"doc_titulo_terciario_universitario",False) or getattr(pre,"doc_titulo_secundario",False)),
            ("Certificado de alumno regular", getattr(pre,"doc_cert_alumno_regular",False)),
            ("Certificado de buena salud", getattr(pre,"doc_cert_buena_salud",False)),
            ("Certificado de título en trámite", getattr(pre,"doc_cert_titulo_en_tramite",False)),
            ("3 folios oficio", getattr(pre,"doc_folios",False)),
        ]

        # Condicional docente
        is_docente = "docent" in (carrera or "").lower()
        if is_docente:
            items.append(("Incumbencias", getattr(pre,"doc_incumbencias",False)))

        items.append(("Si adeuda materias (adjunta constancia)", bool(getattr(pre,"doc_adeuda_materias",False))))

        y_docs_bottom = _checkbox_cols(c, y, items, col_xs, row_gap=ROW)

        

        # y para firmas: 14mm por debajo del ítem más bajo
        y = y_docs_bottom - 14*mm

        # ===== Bloque inferior: Firmas + Comprobante =====
        # 1) Separador del comprobante (fijo)
        _line(c, M, COMP_TOP, W - M, COMP_TOP)

        # 2) FIRMAS: debajo de “Documentación” pero por encima del comprobante
        FIRMAS_Y = max(COMP_TOP + 3*ROW, y_docs_bottom - 3*ROW)  # ~15mm arriba del comp. o 15mm bajo docs

        _line(c, M, FIRMAS_Y, M + 78*mm, FIRMAS_Y)
        _text(c, M, FIRMAS_Y - 11, "Fecha, firma y aclaración del inscripto", size=9)

        _line(c, W - M - 78*mm, FIRMAS_Y, W - M, FIRMAS_Y)
        _text(c, W - M - 72*mm, FIRMAS_Y - 11, "Fecha, firma, cargo y aclaración del personal", size=9)

        # 3) COMPROBANTE (debajo de la línea)
        # Título del comprobante (debajo de la línea)
        _text(c, M, COMP_TOP - ROW, "Comprobante de Inscripción del alumno", size=11, bold=True)

        comp_left_x = M + 6*mm     # más a la izquierda
        # Reservamos mínimo 40mm para etiqueta y medimos por si la etiqueta es más larga
        _label_value_auto(c, comp_left_x, COMP_MARGIN_BOTTOM + 18*mm, "Carrera", carrera,               gap=5*mm, min_lw=40*mm)
        _label_value_auto(c, comp_left_x, COMP_MARGIN_BOTTOM + 12*mm, "Alumno/a", f"{getattr(pre,'apellido','')}, {getattr(pre,'nombres','')}", gap=5*mm, min_lw=40*mm)
        _label_value_auto(c, comp_left_x, COMP_MARGIN_BOTTOM +  6*mm, "Número de preinscripción", numero, gap=5*mm, min_lw=40*mm)

        # QR del comprobante (abajo a la derecha, igual que antes)
        _draw_qr(c, numero, x_mm=(W / mm) - 30, y_mm=8, size_mm=22)

        c.showPage()
        c.save()

        buffer.seek(0)
        resp = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="pre_{numero}.pdf"'
        return resp
    except Exception as e:
        # Si DEBUG está activo, mostrar el error para depurar
        if settings.DEBUG:
            tb = traceback.format_exc()
            return HttpResponse("PDF ERROR\n\n" + tb,
                                content_type="text/plain", status=500)
        raise
