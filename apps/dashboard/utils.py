# apps/dashboard/utils.py
from django.utils.text import slugify

def es_certificacion_docente(carrera) -> bool:
    """
    Detecta si la carrera es Certificación Docente.
    Sirve tanto si existe un booleano como si solo está el nombre.
    """
    if not carrera:
        return False
    # Si tu modelo tiene un flag, usalo:
    if hasattr(carrera, "es_certificacion_docente"):
        return bool(getattr(carrera, "es_certificacion_docente"))
    # Fallback por nombre
    nombre = (getattr(carrera, "nombre", "") or "").lower()
    slug = slugify(nombre)
    return "certificacion" in slug and "docente" in slug

def compute_condicion_admin(pre) -> str:
    """
    Devuelve 'REGULAR' o 'CONDICIONAL' según la documentación.
    Usa getattr con default False para no romper si algún campo cambia de nombre.
    """
    is_cd = es_certificacion_docente(getattr(pre, "carrera", None))

    # Campos esperados (con defaults seguros)
    titulo_sec = bool(getattr(pre, "titulo_legalizado", False))
    titulo_ter = bool(getattr(pre, "titulo_terciario_universitario", False))
    titulo_tramite = bool(getattr(pre, "titulo_en_tramite", False))
    adeuda = bool(getattr(pre, "adeuda_materias", False))
    folios3 = bool(getattr(pre, "tres_folios", False) or getattr(pre, "foliios_3", False))
    fotos = bool(getattr(pre, "fotos_4x4", False) or getattr(pre, "dos_fotos_4x4", False))
    cert_reg = bool(getattr(pre, "cert_alumno_regular", False))

    if is_cd:
        # CD: NO titulo secundario, NO adeuda materias
        requisitos_ok = titulo_ter and folios3 and fotos and cert_reg
        if adeuda:  # por si alguien lo tilda por error
            return "CONDICIONAL"
        return "REGULAR" if requisitos_ok else "CONDICIONAL"

    # Resto de carreras:
    titulo_ok = titulo_sec or titulo_tramite or adeuda
    requisitos_ok = titulo_ok and folios3 and fotos and cert_reg
    return "REGULAR" if requisitos_ok else "CONDICIONAL"
