from typing import Optional

DOCENTE_TOKENS = ("docent", "certifica")

def is_docente_track(carrera) -> bool:
    name = getattr(carrera, "nombre", str(carrera) if carrera else "") or ""
    return any(t in name.lower() for t in DOCENTE_TOKENS)

def _val(data, obj, key):
    if data is not None:
        v = data.get(key)
        if isinstance(v, str):
            return v.lower() in ("1", "true", "on", "yes")
        return bool(v)
    return bool(getattr(obj, key, False))

def compute_condicion_admin(obj=None, data: Optional[dict] = None) -> str:
    """Devuelve 'REGULAR' o 'CONDICIONAL' según reglas indicadas.
    Puede evaluar sobre instancia (`obj`) o sobre `data` (POST).
    """
    docente = is_docente_track(getattr(obj, 'carrera', None))
    titulo_sec = _val(data, obj, 'doc_fotocopia_titulo_legalizada')
    titulo_ter = _val(data, obj, 'doc_titulo_terciario_universitario')
    cert_tram = _val(data, obj, 'doc_cert_titulo_en_tramite')
    adeuda = _val(data, obj, 'doc_adeuda_materias') and not docente
    folios = _val(data, obj, 'doc_folios')
    fotos = _val(data, obj, 'doc_fotos_4x4')
    analit = _val(data, obj, 'doc_fotocopia_analitico_legalizada')
    alumreg = _val(data, obj, 'doc_cert_alumno_regular')
    incumb = _val(data, obj, 'doc_incumbencias') if docente else True

    base_ok = folios and fotos and alumreg
    if docente:
        titulo_ok = titulo_ter and incumb
    else:
        titulo_ok = titulo_sec or titulo_ter

    if cert_tram or adeuda:
        return 'CONDICIONAL'

    return 'REGULAR' if (base_ok and titulo_ok) else 'CONDICIONAL'
