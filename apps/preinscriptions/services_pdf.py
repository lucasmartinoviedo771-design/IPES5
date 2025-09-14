from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors

from .models import Preinscripcion


def build_planilla_pdf(pre: Preinscripcion) -> bytes:
    """
    Genera 'Planilla de Preinscripción 2025' + talón inferior (comprobante).
    Diseño simple y legible; se puede embellecer luego.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4

    def header(y):
        c.setFont("Helvetica-Bold", 14)
        c.drawString(20*mm, y, "Planilla de Preinscripción 2025")
        c.setFont("Helvetica", 9)
        c.drawRightString(W - 20*mm, y, f"N° {pre.id} – {pre.created_at.strftime('%Y-%m-%d %H:%M')}")

    def field(label, value, x, y, w=80*mm):
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, y, f"{label}:")
        c.setFont("Helvetica", 9)
        c.drawString(x + 35*mm, y, str(value or ""))

    # Página principal
    y = H - 25*mm
    header(y)
    y -= 10*mm
    c.line(15*mm, y, W-15*mm, y)
    y -= 8*mm

    # Carrera
    field("Carrera", f"{pre.carrera.codigo} - {pre.carrera.nombre}", 20*mm, y); y -= 8*mm

    # Datos personales
    c.setFont("Helvetica-Bold", 10); c.drawString(20*mm, y, "A) Datos Personales"); y -= 6*mm
    field("DNI", pre.dni, 20*mm, y); field("CUIL/CUIT", pre.cuil, 120*mm, y); y -= 8*mm
    field("Apellido", pre.apellido, 20*mm, y); field("Nombres", pre.nombres, 120*mm, y); y -= 8*mm
    field("Fecha Nac.", pre.fecha_nacimiento, 20*mm, y); field("Estado civil", pre.estado_civil, 120*mm, y); y -= 8*mm
    field("Nacionalidad", pre.nacionalidad, 20*mm, y); field("Lugar Nac.", f"{pre.loc_nacimiento}, {pre.prov_nacimiento}, {pre.pais_nacimiento}", 120*mm, y); y -= 10*mm

    # Contacto
    c.setFont("Helvetica-Bold", 10); c.drawString(20*mm, y, "B) Datos de Contacto"); y -= 6*mm
    field("Domicilio", pre.domicilio, 20*mm, y); y -= 8*mm
    field("Tel. fijo", pre.tel_fijo, 20*mm, y); field("Tel. móvil", pre.tel_movil, 120*mm, y); y -= 8*mm
    field("E-mail", pre.email, 20*mm, y); y -= 8*mm
    field("Emergencia", f"{pre.emergencia_telefono} ({pre.emergencia_parentesco})", 20*mm, y); y -= 10*mm

    # Laboral
    c.setFont("Helvetica-Bold", 10); c.drawString(20*mm, y, "C) Datos Laborales (opcional)"); y -= 6*mm
    field("Trabaja", "Sí" if pre.trabaja else "No", 20*mm, y); y -= 8*mm
    if pre.trabaja:
        field("Empleador", pre.empleador, 20*mm, y); field("Horario", pre.horario_trabajo, 120*mm, y); y -= 8*mm
        field("Domicilio trabajo", pre.domicilio_trabajo, 20*mm, y); y -= 10*mm
    else:
        y -= 4*mm

    # Estudios
    c.setFont("Helvetica-Bold", 10); c.drawString(20*mm, y, "D) Estudios Cursados"); y -= 6*mm
    if not pre.es_certificacion_docente:
        field("Título secundario", pre.secu_titulo, 20*mm, y); y -= 8*mm
        field("Establecimiento", pre.secu_establecimiento, 20*mm, y); field("Egreso", pre.secu_fecha_egreso, 120*mm, y); y -= 8*mm
        field("Lugar", f"{pre.secu_localidad}, {pre.secu_provincia}, {pre.secu_pais}", 20*mm, y); y -= 8*mm

    # Superiores
    c.setFont("Helvetica-Bold", 9); c.drawString(20*mm, y, "Títulos Terciarios / Universitarios:"); y -= 6*mm
    for t in pre.titulos_superiores.all()[:2]:
        field("Título", t.titulo, 20*mm, y); field("Egreso", t.fecha_egreso, 120*mm, y); y -= 8*mm
        field("Establecimiento", t.establecimiento, 20*mm, y); field("Lugar", f"{t.localidad}, {t.provincia}, {t.pais}", 120*mm, y); y -= 8*mm

    y -= 6*mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20*mm, y, "E) Documentación presentada (a completar por el establecimiento)")
    y -= 8*mm

    # --- Checkboxes en 2 columnas ---
    c.setFont("Helvetica", 9)
    col1_x, col2_x = 20*mm, 110*mm
    line_height = 6*mm
    
    # Determinar la lista de documentos
    is_cert_doc = "cert" in pre.carrera.codigo.lower() if pre.carrera else False

    docs = []
    if is_cert_doc:
        docs.append("Incumbencias")
    else:
        docs.extend(["Título secundario", "Certificado de título en trámite", "Adeuda materias"])

    docs.extend([
        "Fotocopia legalizada del título",
        "Fotocopia legalizada del analítico",
        "Fotos carnet 4x4",
        "Certificado de buena salud",
        "Folios",
        "Declaración jurada / Nota compromiso"
    ])

    # Dibujar la lista en dos columnas
    initial_y = y
    for i, label in enumerate(docs):
        col_x = col1_x if i % 2 == 0 else col2_x
        # La y se resetea a la mitad de la lista
        if i > 0 and i % 2 == 0:
            y -= line_height

        c.rect(col_x, y - 2*mm, 3.5*mm, 3.5*mm)  # Dibuja el cuadrado
        c.drawString(col_x + 5*mm, y - 1.5*mm, label)

    # Ajustar 'y' final basado en el número de filas
    num_rows = (len(docs) + 1) // 2
    y = initial_y - (num_rows * line_height) - 4*mm

    # Texto condicional para "Adeuda materias"
    if not is_cert_doc:
        c.setFont("Helvetica", 8)
        c.drawString(20*mm, y, "Si “Adeuda materias”: Materias que adeuda: __________________ Escuela: __________________")
        y -= 8*mm

    # Línea de corte y talón
    c.setStrokeColor(colors.grey)
    c.setDash(3, 2)
    c.line(15*mm, 35*mm, W-15*mm, 35*mm)
    c.setDash()

    # Talón (comprobante)
    c.setFont("Helvetica-Bold", 10); c.drawString(20*mm, 28*mm, "Comprobante de Inscripción (Desprendible)")
    c.setFont("Helvetica", 9)
    c.drawString(20*mm, 22*mm, f"Apellido y Nombres: {pre.apellido}, {pre.nombres}")
    c.drawString(20*mm, 17*mm, f"DNI: {pre.dni} – Carrera: {pre.carrera.codigo} - {pre.carrera.nombre}")
    c.drawString(20*mm, 12*mm, f"Fecha: {pre.created_at.strftime('%Y-%m-%d')}")

    c.showPage()
    c.save()
    return buffer.getvalue()
