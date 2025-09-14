# apps/academics/routers.py
from ninja import Router
from ninja.errors import HttpError
from django.db.models import Prefetch
from apps.users.models import UserProfile
from apps.academics.models import Carrera, Plan, Materia, Correlatividad
from apps.academics.schemas import CarreraItem, CorrelatividadesOut

router = Router(tags=["academics"])

@router.get("/carreras", response=list[CarreraItem], summary="Listar carreras (contrato legado)")
def listar_carreras(request):
    u = request.auth
    if not u or u.rol not in [UserProfile.Rol.SECRETARIA, UserProfile.Rol.BEDEL, UserProfile.Rol.ADMIN]:
        raise HttpError(403, "No tiene permisos")

    # Para cada carrera activa, tomar plan activo (si hay más de uno, priorizamos el más reciente por año_implementacion)
    carreras = (Carrera.objects.filter(activa=True)
                .prefetch_related(Prefetch("planes", queryset=Plan.objects.filter(activo=True).order_by("-año_implementacion"))))

    out = []
    for c in carreras:
        plan_activo = c.planes.first()
        if not plan_activo:
            # Si no hay plan activo, omitimos (o devolvemos plan_id null — preferimos omitir para cumplir contrato)
            continue
        plan_txt = f"{c.nombre} - Plan {plan_activo.version} (Año {plan_activo.año_implementacion})"
        out.append(CarreraItem(id=c.id, nombre=c.nombre, plan_id=plan_activo.id, plan_txt=plan_txt))
    return out

@router.get("/materias/{materia_id}/correlatividades", response=CorrelatividadesOut, summary="Correlatividades (contrato legado)")
def correlatividades_por_materia(request, materia_id: int):
    u = request.auth
    if not u or u.rol not in [
        UserProfile.Rol.SECRETARIA, UserProfile.Rol.BEDEL, UserProfile.Rol.ADMIN,
        UserProfile.Rol.DOCENTE, UserProfile.Rol.TUTOR
    ]:
        raise HttpError(403, "No tiene permisos")

    try:
        materia = Materia.objects.get(id=materia_id)
    except Materia.DoesNotExist:
        raise HttpError(404, "Materia no encontrada")

    corr_qs = Correlatividad.objects.filter(materia=materia).only(
        "materia_correlativa_id", "requiere_aprobada", "requiere_regular"
    )
    regulares = [c.materia_correlativa_id for c in corr_qs if c.requiere_regular]
    aprobadas = [c.materia_correlativa_id for c in corr_qs if c.requiere_aprobada]
    return {"regulares": regulares, "aprobadas": aprobadas}