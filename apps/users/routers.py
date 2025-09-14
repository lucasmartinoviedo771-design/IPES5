# apps/users/routers.py
from typing import Dict, List
from ninja import Router
from ninja.errors import HttpError
from django.contrib.auth import get_user_model
from apps.users.models import UserProfile
from apps.users.schemas import EstudianteResumen

router = Router(tags=["estudiantes"])

@router.get("/", response=Dict[str, List[EstudianteResumen]], summary="Listar estudiantes")
def listar_estudiantes(request):
    user = request.auth
    if not user:
        raise HttpError(403, "No autenticado")

    qs = UserProfile.objects.filter(rol=UserProfile.Rol.ESTUDIANTE)

    if user.rol in [UserProfile.Rol.SECRETARIA, UserProfile.Rol.BEDEL, UserProfile.Rol.ADMIN, UserProfile.Rol.TUTOR]:
        pass  # acceso completo (TUTOR solo lectura)
    elif user.rol == UserProfile.Rol.DOCENTE:
        # TODO: filtrar "sus alumnos" (por comisiones asignadas al docente)
        raise HttpError(501, "Funcionalidad en desarrollo (docente - scoping por comisiones)")
    else:
        # estudiante no accede aquí (tiene endpoints propios)
        raise HttpError(403, "No tiene permisos")

    return {"items": list(qs.values("id", "nombre_completo", "dni", "email"))}