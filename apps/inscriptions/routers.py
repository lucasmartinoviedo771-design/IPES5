from ninja import Router
from ninja.errors import HttpError
from pydantic import BaseModel, Field
from typing import Optional, List
from django.contrib.auth import get_user_model
from django.db.models import Prefetch

from apps.users.models import UserProfile
from apps.academics.models import Comision
from apps.inscriptions.models import InscripcionCursada, InscripcionCarrera, LegajoItem
from .services import crear_inscripcion_cursada, BusinessError
from .schemas_legajo import (
    LegajoItemUpdateIn, LegajoEstadoOut,
    LegajoDetalleOut, LegajoItemOut, LegajoItemTipoOut,
    LegajoRecomputeOut
)
from .services_legajo import update_items_and_recompute, recompute_only

router = Router(tags=["inscripciones"])

def _is_staff_like(user):
    return user and user.rol in (UserProfile.Rol.ADMIN, UserProfile.Rol.SECRETARIA, UserProfile.Rol.BEDEL)

def _require_staff(user):
    if not _is_staff_like(user):
        if not user:
            raise HttpError(401, "No autenticado")
        raise HttpError(403, "Permisos insuficientes")

class InscripcionCursadaCreateIn(BaseModel):
    comision_id: int = Field(..., description="ID de la comisión a inscribirse")
    estudiante_id: Optional[int] = Field(None, description="Solo roles de gestión: inscribir a un tercero")

class InscripcionCursadaOut(BaseModel):
    id: int
    estudiante_id: int
    comision_id: int
    estado: str
    fecha_inscripcion: str
    aviso: Optional[str] = None
    class Config:
        from_attributes = True

@router.post("/cursadas", response={201: InscripcionCursadaOut, 400: dict, 401: dict, 403: dict, 404: dict, 409: dict})
def inscribir_cursada(request, payload: InscripcionCursadaCreateIn):
    user = request.auth
    if not user:
        return 401, {"detalle": "No autenticado"}

    # Resolver estudiante según rol
    estudiante: UserProfile
    if payload.estudiante_id:
        # Solo gestión puede inscribir a terceros
        if user.rol not in [UserProfile.Rol.SECRETARIA, UserProfile.Rol.BEDEL, UserProfile.Rol.ADMIN]:
            return 403, {"detalle": "No tiene permisos para inscribir a terceros"}
        try:
            estudiante = UserProfile.objects.get(id=payload.estudiante_id, rol=UserProfile.Rol.ESTUDIANTE)
        except UserProfile.DoesNotExist:
            return 404, {"detalle": "Estudiante no encontrado"}
    else:
        # Auto-inscripción: debe ser estudiante
        if user.rol != UserProfile.Rol.ESTUDIANTE:
            return 403, {"detalle": "Debe indicar estudiante_id o ser ESTUDIANTE"}
        estudiante = user

    # Comisión
    try:
        comision = Comision.objects.select_related("materia").get(id=payload.comision_id)
    except Comision.DoesNotExist:
        return 404, {"detalle": "Comisión no encontrada"}

    # Ejecutar reglas
    try:
        obj, aviso = crear_inscripcion_cursada(estudiante=estudiante, comision=comision)
    except BusinessError as be:
        return 409, {"detalle": be.message}
    except Exception as e:
        return 400, {"detalle": f"Error inesperado: {e}"}

    return 201, {
        "id": obj.id,
        "estudiante_id": obj.estudiante_id,
        "comision_id": obj.comision_id,
        "estado": obj.estado,
        "fecha_inscripcion": obj.fecha_inscripcion.isoformat(),
        "aviso": aviso,
    }

@router.patch(
    "/carrera/{insc_id}/legajo/items",
    response=LegajoEstadoOut,
    summary="(Gestión) Actualiza items del legajo y recalcula estado/condición"
)
def legajo_bulk_update(request, insc_id: int, payload: List[LegajoItemUpdateIn]):
    _require_staff(request.auth)
    res = update_items_and_recompute(
        inscripcion_id=insc_id,
        updates=[p.model_dump() for p in payload]
    )
    return {
        "inscripcion_id": res.inscripcion.id,
        "items_actualizados": res.items_actualizados,
        "legajo_estado": res.legajo_estado,
        "condicion": res.condicion,
    }

@router.get(
    "/carrera/{insc_id}/legajo",
    response=LegajoDetalleOut,
    summary="(Gestión) Ver detalle de legajo de una inscripción a carrera"
)
def legajo_detail(request, insc_id: int):
    _require_staff(request.auth)

    insc = (
        InscripcionCarrera.objects
        .prefetch_related(Prefetch("legajoitem_set", queryset=LegajoItem.objects.select_related("tipo")))
        .filter(id=insc_id)
        .first()
    )
    if not insc:
        raise HttpError(404, "Inscripción a carrera no encontrada")

    items = list(insc.legajoitem_set.all())
    total = len(items)
    cumplidos = sum(1 for it in items if it.cumplido)

    legajo_estado = getattr(insc, "legajo_estado", "INCOMPLETO") or "INCOMPLETO"
    condicion = getattr(insc, "condicion", "CONDICIONADO") or "CONDICIONADO"

    return {
        "inscripcion_id": insc.id,
        "legajo_estado": legajo_estado,
        "condicion": condicion,
        "total": total,
        "cumplidos": cumplidos,
        "items": [
            LegajoItemOut(
                id=it.id,
                cumplido=it.cumplido,
                observacion=it.observacion or None,
                tipo=LegajoItemTipoOut(
                    id=it.tipo_id,
                    codigo=getattr(it.tipo, "codigo", None),
                    nombre=getattr(it.tipo, "nombre", str(it.tipo_id)),
                )
            ).model_dump()
            for it in items
        ],
    }

@router.patch(
    "/carrera/{insc_id}/legajo/recompute",
    response=LegajoRecomputeOut,
    summary="(Gestión) Recalcula estado de legajo y condición sin modificar ítems"
)
def legajo_recompute(request, insc_id: int):
    _require_staff(request.auth)

    res = recompute_only(insc_id)
    # contar ítems para respuesta
    from .models import LegajoItem
    total = LegajoItem.objects.filter(inscripcion=res.inscripcion).count()
    cumplidos = LegajoItem.objects.filter(inscripcion=res.inscripcion, cumplido=True).count()

    return {
        "inscripcion_id": res.inscripcion.id,
        "total": total,
        "cumplidos": cumplidos,
        "legajo_estado": res.legajo_estado,
        "condicion": res.condicion,
    }