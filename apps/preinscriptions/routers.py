from typing import List, Optional
from datetime import date
from io import StringIO, BytesIO
import csv

from django.http import HttpResponse
from django.core.cache import cache
from django.conf import settings
from ninja import Router, File, Form, UploadedFile
from ninja.errors import HttpError
from PIL import Image
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.encoding import iri_to_uri
from django.utils import timezone

from apps.users.models import UserProfile
from apps.academics.models import Carrera
from .models import Preinscripcion
from .schemas import PreinscripcionOut, Mensaje
from .services_pdf import build_planilla_pdf
from .schemas_promote import PrePromoteIn, PrePromoteOut
from .services_promote import promote_preinscripcion
from .schemas_public import (
    PreinscripcionOut as PublicPreinscripcionOut,
    ContactoOut, LaboralOut,
    SecundarioOut, TerciarioOut, DocumentacionOut, FotoOut,
)
from .schemas_patch import PreinscripcionPatchIn
from .pdf import render_preinscripcion_pdf

router = Router(tags=["preinscripciones"])


# ---------- helpers permisos / ip / rate limit ----------
def _is_staff_like(user: Optional[UserProfile]) -> bool:
    return user and user.rol in (UserProfile.Rol.ADMIN, UserProfile.Rol.SECRETARIA, UserProfile.Rol.BEDEL)

def _require_staff(user: Optional[UserProfile]):
    if not _is_staff_like(user):
        if not user:
            raise HttpError(401, "No autenticado")
        raise HttpError(403, "Permisos insuficientes")

def _client_ip(request) -> str:
    return request.META.get("REMOTE_ADDR", "0.0.0.0")

def _rate_limit(request, bucket: str, limit: int, window_seconds: int):
    ip = _client_ip(request)
    key = f"rl:{bucket}:{ip}"
    added = cache.add(key, 1, timeout=window_seconds)
    if not added:
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=window_seconds)
            count = 1
        if count > limit:
            raise HttpError(429, f"Demasiadas solicitudes. Intente más tarde.")

def _can_view_pre(user: UserProfile | None, pre: Preinscripcion) -> bool:
    if _is_staff_like(user):
        return True
    if not user:
        return False
    if user.rol == UserProfile.Rol.ESTUDIANTE:
        if getattr(user, "dni", None) and getattr(pre, "dni", None) and user.dni == pre.dni:
            return True
        if user.email and getattr(pre, "email", None) and user.email.lower().strip() == pre.email.lower().strip():
            return True
    return False

def _url_safe(f):
    try:
        return iri_to_uri(f.url)
    except Exception:
        return None

def _serialize_pre(pre: Preinscripcion) -> PublicPreinscripcionOut:
    carrera_id = getattr(pre, "carrera_id", 0) or 0
    foto_obj = getattr(pre, "foto_4x4", None)
    foto_url = _url_safe(foto_obj) if foto_obj and hasattr(foto_obj, 'url') else None
    tercs = []
    return PublicPreinscripcionOut(
        id=pre.id, carrera_id=carrera_id, carrera_nombre="", dni=getattr(pre, "dni", ""),
        cuil=getattr(pre, "cuil", None), apellido=getattr(pre, "apellido", None), nombres=getattr(pre, "nombres", None),
        fecha_nacimiento=str(pre.fecha_nacimiento) if getattr(pre, "fecha_nacimiento", None) else None,
        estado_civil=getattr(pre, "estado_civil", None), lugar_nac_localidad=getattr(pre, "localidad_nac", None),
        lugar_nac_provincia=getattr(pre, "provincia_nac", None), lugar_nac_pais=getattr(pre, "pais_nac", None),
        nacionalidad=getattr(pre, "nacionalidad", None),
        contacto=ContactoOut(
            domicilio=getattr(pre, "domicilio", None), tel_fijo=getattr(pre, "tel_fijo", None),
            tel_movil=getattr(pre, "tel_movil", None), email=getattr(pre, "email", None),
        ),
        laboral=LaboralOut(
            trabaja=getattr(pre, "trabaja", None), empleador=getattr(pre, "empleador", None),
            horario_trabajo=getattr(pre, "horario_trabajo", None), domicilio_trabajo=getattr(pre, "domicilio_trabajo", None),
        ),
        secundario=SecundarioOut(
            titulo_obtenido=getattr(pre, "sec_titulo", None), establecimiento=getattr(pre, "sec_establecimiento", None),
            fecha_egreso=str(pre.sec_fecha_egreso) if getattr(pre, "sec_fecha_egreso", None) else None,
            localidad=getattr(pre, "sec_localidad", None), provincia=getattr(pre, "sec_provincia", None),
            pais=getattr(pre, "sec_pais", None),
        ),
        terciarios=tercs,
        documentacion=DocumentacionOut(
            adeuda_materias=bool(getattr(pre, "doc_adeuda_materias", False)),
            adeuda_detalle=getattr(pre, "adeuda_materias_detalle", None), adeuda_escuela=getattr(pre, "adeuda_materias_escuela", None),
            cert_titulo_en_tramite=bool(getattr(pre, "doc_cert_titulo_en_tramite", False)),
            titulo_secundario=bool(getattr(pre, "doc_titulo_secundario", False)),
            dj_nota_compromiso=bool(getattr(pre, "doc_declaracion_jurada", False)),
            incumbencias=bool(getattr(pre, "doc_incumbencias", False)),
        ),
        foto=FotoOut(url=foto_url),
    )

# ===================== PÚBLICO =====================

@router.post("/", auth=None)
def crear_preinscripcion(
    request,
    carrera_id: int = Form(...),
    cuil: str = Form(...), dni: str = Form(...),
    apellido: str = Form(...), nombres: str = Form(...),
    fecha_nacimiento: str = Form(...),  # YYYY-MM-DD
    estado_civil: str = Form(...),
    localidad_nac: str = Form(...), provincia_nac: str = Form(...),
    pais_nac: str = Form(...), nacionalidad: str = Form(...),
    domicilio: str = Form(...), tel_fijo: Optional[str] = Form(None),
    tel_movil: Optional[str] = Form(None), email: str = Form(...),
    trabaja: bool = Form(False), empleador: Optional[str] = Form(None),
    horario_trabajo: Optional[str] = Form(None), domicilio_trabajo: Optional[str] = Form(None),
    sec_titulo: Optional[str] = Form(None),
    sec_establecimiento: Optional[str] = Form(None),
    sec_fecha_egreso: Optional[str] = Form(None),
    sec_localidad: Optional[str] = Form(None),
    sec_provincia: Optional[str] = Form(None),
    sec_pais: Optional[str] = Form(None),
    sup1_titulo: Optional[str] = Form(None),
    sup1_establecimiento: Optional[str] = Form(None),
    sup1_fecha_egreso: Optional[str] = Form(None),
    sup1_localidad: Optional[str] = Form(None),
    sup1_provincia: Optional[str] = Form(None),
    sup1_pais: Optional[str] = Form(None),
    sup2_titulo: Optional[str] = Form(None),
    sup2_establecimiento: Optional[str] = Form(None),
    sup2_fecha_egreso: Optional[str] = Form(None),
    sup2_localidad: Optional[str] = Form(None),
    sup2_provincia: Optional[str] = Form(None),
    sup2_pais: Optional[str] = Form(None),
    foto_4x4: Optional[UploadedFile] = File(None),
    doc_fotocopia_titulo_legalizada: bool = Form(False),
    doc_fotocopia_analitico_legalizada: bool = Form(False),
    doc_fotos_4x4: bool = Form(False),
    doc_titulo_secundario: bool = Form(False),
    doc_titulo_terciario_universitario: bool = Form(False),
    doc_cert_alumno_regular: bool = Form(False),
    doc_cert_titulo_en_tramite: bool = Form(False),
    doc_cert_buena_salud: bool = Form(False),
    doc_folios: bool = Form(False),
    doc_adeuda_materias: bool = Form(False),
    adeuda_materias_detalle: Optional[str] = Form(None),
    adeuda_materias_escuela: Optional[str] = Form(None),
    doc_incumbencias: bool = Form(False),
):
    obj = Preinscripcion(
        carrera_id=carrera_id,
        cuil=cuil, dni=dni, apellido=apellido, nombres=nombres,
        fecha_nacimiento=fecha_nacimiento, estado_civil=estado_civil,
        localidad_nac=localidad_nac, provincia_nac=provincia_nac,
        pais_nac=pais_nac, nacionalidad=nacionalidad,
        domicilio=domicilio, tel_fijo=tel_fijo or "",
        tel_movil=tel_movil or "", email=email,
        trabaja=trabaja, empleador=empleador or "",
        horario_trabajo=horario_trabajo or "", domicilio_trabajo=domicilio_trabajo or "",
        sec_titulo=sec_titulo or "", sec_establecimiento=sec_establecimiento or "",
        sec_fecha_egreso=sec_fecha_egreso or None,
        sec_localidad=sec_localidad or "", sec_provincia=sec_provincia or "",
        sec_pais=sec_pais or "",
        sup1_titulo=sup1_titulo or "", sup1_establecimiento=sup1_establecimiento or "",
        sup1_fecha_egreso=sup1_fecha_egreso or None,
        sup1_localidad=sup1_localidad or "", sup1_provincia=sup1_provincia or "",
        sup1_pais=sup1_pais or "",
        sup2_titulo=sup2_titulo or "", sup2_establecimiento=sup2_establecimiento or "",
        sup2_fecha_egreso=sup2_fecha_egreso or None,
        sup2_localidad=sup2_localidad or "", sup2_provincia=sup2_provincia or "",
        sup2_pais=sup2_pais or "",
        doc_fotocopia_titulo_legalizada=doc_fotocopia_titulo_legalizada,
        doc_fotocopia_analitico_legalizada=doc_fotocopia_analitico_legalizada,
        doc_fotos_4x4=doc_fotos_4x4,
        doc_titulo_secundario=doc_titulo_secundario,
        doc_titulo_terciario_universitario=doc_titulo_terciario_universitario,
        doc_cert_alumno_regular=doc_cert_alumno_regular,
        doc_cert_titulo_en_tramite=doc_cert_titulo_en_tramite,
        doc_cert_buena_salud=doc_cert_buena_salud,
        doc_folios=doc_folios,
        doc_adeuda_materias=doc_adeuda_materias,
        adeuda_materias_detalle=adeuda_materias_detalle or "",
        adeuda_materias_escuela=adeuda_materias_escuela or "",
        doc_incumbencias=doc_incumbencias,
    )
    if foto_4x4:
        obj.foto_4x4 = foto_4x4

    obj.full_clean()
    obj.save()
    return {"id": obj.id, "apellido": obj.apellido, "nombres": obj.nombres}

# ... (The rest of the endpoints remain) ...