from typing import List, Optional
from ninja import Router
from ninja.errors import HttpError

from apps.users.models import UserProfile
from apps.academics.models import Carrera
from apps.inscriptions.models import (
    InscripcionCarrera, LegajoItem, LegajoItemTipo
)
from .schemas_padron import (
    Mensaje, InscCarreraCreateIn, InscripcionCarreraOut,
    LegajoItemOut, LegajoToggleIn, LegajoItemTipoOut,
)

router = Router(tags=["padron"])  # aparecerá como "padron" en /api/v1/docs


# ===== Helpers de permisos/visibilidad =====

def _is_staff_like(user: UserProfile) -> bool:
    return user and user.rol in (
        UserProfile.Rol.ADMIN,
        UserProfile.Rol.SECRETARIA,
        UserProfile.Rol.BEDEL,
    )

def _is_tutor(user: UserProfile) -> bool:
    return user and user.rol == UserProfile.Rol.TUTOR

def _require_roles(user: Optional[UserProfile], roles: list[UserProfile.Rol]):
    if not user:
        raise HttpError(401, "No autenticado")
    if user.rol not in roles:
        raise HttpError(403, "Permisos insuficientes")

def _get_insc_visible_para_usuario(user: UserProfile, insc_id: int) -> InscripcionCarrera:
    try:
        insc = InscripcionCarrera.objects.select_related("estudiante", "carrera").get(id=insc_id)
    except InscripcionCarrera.DoesNotExist:
        raise HttpError(404, "Inscripción de carrera no encontrada")

    # Staff y tutor ven todo; estudiante solo lo propio
    if _is_staff_like(user) or _is_tutor(user):
        return insc
    if user and user.rol == UserProfile.Rol.ESTUDIANTE and insc.estudiante_id == user.id:
        return insc

    raise HttpError(403, "No tiene permisos para ver esta inscripción")


# ===== Endpoints =====

@router.post(
    "/carreras/inscribir",
    response={201: InscripcionCarreraOut, 400: Mensaje, 401: Mensaje, 403: Mensaje, 404: Mensaje},
    summary="Inscribir estudiante a una carrera (gestión)",
    description="Crea la inscripción del estudiante a la carrera y si existe catálogo de legajo de esa carrera, inicializa su checklist.",
)
def inscribir_carrera(request, payload: InscCarreraCreateIn):
    _require_roles(request.auth, [UserProfile.Rol.ADMIN, UserProfile.Rol.SECRETARIA, UserProfile.Rol.BEDEL])

    # Validaciones básicas de existencia
    if not UserProfile.objects.filter(id=payload.estudiante_id, rol=UserProfile.Rol.ESTUDIANTE).exists():
        return 404, {"detalle": "Estudiante no encontrado (o no es ESTUDIANTE)"}
    if not Carrera.objects.filter(id=payload.carrera_id).exists():
        return 404, {"detalle": "Carrera no encontrada"}

    insc, created = InscripcionCarrera.objects.get_or_create(
        estudiante_id=payload.estudiante_id, carrera_id=payload.carrera_id
    )

    # Inicializa checklist según catálogo (si faltan ítems, se crean)
    tipos = LegajoItemTipo.objects.filter(carrera_id=payload.carrera_id)
    for t in tipos:
        LegajoItem.objects.get_or_create(insc_carrera=insc, item=t)

    return 201, InscripcionCarreraOut.from_orm(insc)


@router.get(
    "/carreras/mias",
    response=List[InscripcionCarreraOut],
    summary="Mis inscripciones a carrera (estudiante)",
)
def mis_inscripciones_carrera(request):
    user = request.auth
    if not user:
        raise HttpError(401, "No autenticado")
    if user.rol != UserProfile.Rol.ESTUDIANTE:
        raise HttpError(403, "Solo estudiantes")

    qs = InscripcionCarrera.objects.filter(estudiante_id=user.id)
    return [InscripcionCarreraOut.from_orm(x) for x in qs]


@router.get(
    "/carreras",
    response=List[InscripcionCarreraOut],
    summary="Listar inscripciones a carrera (gestión/tutor)",
    description="Permite filtrar por estudiante_id. Staff y tutor pueden ver todas; estudiante no puede usar este endpoint.",
)
def listar_insc_carrera(request, estudiante_id: Optional[int] = None):
    user = request.auth
    if not user:
        raise HttpError(401, "No autenticado")
    if not (_is_staff_like(user) or _is_tutor(user)):
        raise HttpError(403, "Permisos insuficientes")

    qs = InscripcionCarrera.objects.select_related("estudiante", "carrera").all()
    if estudiante_id:
        qs = qs.filter(estudiante_id=estudiante_id)
    return [InscripcionCarreraOut.from_orm(x) for x in qs]


@router.get(
    "/carreras/{insc_id}",
    response=InscripcionCarreraOut,
    summary="Detalle de una inscripción de carrera",
)
def detalle_insc_carrera(request, insc_id: int):
    insc = _get_insc_visible_para_usuario(request.auth, insc_id)
    return InscripcionCarreraOut.from_orm(insc)


@router.get(
    "/carreras/{insc_id}/checklist",
    response=List[LegajoItemOut],
    summary="Ver checklist de legajo de una inscripción de carrera",
)
def ver_checklist(request, insc_id: int):
    insc = _get_insc_visible_para_usuario(request.auth, insc_id)

    items = (
        LegajoItem.objects
        .filter(insc_carrera=insc)
        .select_related("item")
        .order_by("item__nombre")
    )

    # Armamos el esquema saliente con info del catálogo + estado
    salida: list[LegajoItemOut] = []
    for li in items:
        salida.append(LegajoItemOut(
            id=li.id,
            nombre=li.item.nombre,
            obligatorio=li.item.obligatorio,
            completo=li.completo,
            observaciones=li.observaciones or "",
        ))
    return salida


@router.patch(
    "/carreras/checklist/{item_id}",
    response={200: LegajoItemOut, 401: Mensaje, 403: Mensaje, 404: Mensaje},
    summary="Actualizar/tildar un ítem del checklist (gestión)",
)
def toggle_checklist(request, item_id: int, payload: LegajoToggleIn):
    _require_roles(request.auth, [UserProfile.Rol.ADMIN, UserProfile.Rol.SECRETARIA, UserProfile.Rol.BEDEL])

    try:
        li = LegajoItem.objects.select_related("item", "insc_carrera").get(id=item_id)
    except LegajoItem.DoesNotExist:
        return 404, {"detalle": "Ítem de checklist no encontrado"}

    li.completo = payload.completo
    li.observaciones = payload.observaciones or ""
    li.save()  # signal recalcula estado_legajo/condición

    return 200, LegajoItemOut(
        id=li.id,
        nombre=li.item.nombre,
        obligatorio=li.item.obligatorio,
        completo=li.completo,
        observaciones=li.observaciones or "",
    )


@router.get(
    "/carreras/{carrera_id}/checklist-def",
    response=List[LegajoItemTipoOut],
    summary="Listado del catálogo de ítems de legajo por carrera (gestión/tutor)",
)
def listar_catalogo_legajo(request, carrera_id: int):
    user = request.auth
    if not user:
        raise HttpError(401, "No autenticado")
    if not (_is_staff_like(user) or _is_tutor(user)):
        raise HttpError(403, "Permisos insuficientes")

    if not Carrera.objects.filter(id=carrera_id).exists():
        raise HttpError(404, "Carrera no encontrada")

    qs = LegajoItemTipo.objects.filter(carrera_id=carrera_id).order_by("nombre")
    return [LegajoItemTipoOut.from_orm(x) for x in qs]
