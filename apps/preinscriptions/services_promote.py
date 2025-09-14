from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
import secrets
import string

from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model

from apps.users.models import UserProfile
from apps.academics.models import Carrera
from apps.preinscriptions.models import Preinscripcion
from apps.inscriptions.models import (
    InscripcionCarrera,
    LegajoItemTipo,
    LegajoItem,
)


def _rand_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@dataclass
class PromoteResult:
    pre: Preinscripcion
    user: UserProfile
    temp_password: Optional[str]
    insc: InscripcionCarrera
    condicion_inicial: str
    legajo_estado_inicial: str


def _username_from_pre(pre: Preinscripcion) -> str:
    # Estrategia simple: DNI
    return pre.dni


def _split_names(nombres: str) -> Tuple[str, str]:
    """
    Devuelve (first_name, middle_names) para mapear a UserProfile.first_name
    y quizás nombre_completo; para MVP usamos todo en first_name si no hay split claro.
    """
    if not nombres:
        return ("", "")
    parts = nombres.split()
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], " ".join(parts[1:]))


@transaction.atomic
def promote_preinscripcion(pre_id: int, *, username: Optional[str] = None,
                           password: Optional[str] = None,
                           force_email: Optional[str] = None,
                           activar_usuario: bool = True,
                           set_rol_estudiante: bool = True,
                           confirmar_carrera_id: Optional[int] = None,
                           copy_photo_to_user: bool = True) -> PromoteResult:
    """
    Promueve una Preinscripción a:
      - UserProfile (rol=ESTUDIANTE) creado o existente (DNI/email)
      - InscripcionCarrera (idempotente)
      - Bootstrap de legajo: crea items pendientes según catálogo, sin marcar completos
    Reglas:
      - Si existe UserProfile con mismo DNI => se reutiliza
      - Si no existe, se crea usuario con username=(param|DNI) y password temporal (si no se pasa)
      - Si confirmar_carrera_id viene y no coincide, aborta
    """
    User = get_user_model()

    pre = Preinscripcion.objects.select_related("carrera").get(id=pre_id)

    if confirmar_carrera_id is not None and pre.carrera_id != confirmar_carrera_id:
        raise ValueError("La carrera indicada no coincide con la de la preinscripción")

    # Buscar usuario por DNI (campo único en UserProfile)
    user: Optional[UserProfile] = None
    temp_password = None

    try:
        user = User.objects.get(dni=pre.dni)
    except User.DoesNotExist:
        # fallback por email si viene force_email o el propio pre.email
        email = (force_email or pre.email or "").strip() or None
        username_final = (username or _username_from_pre(pre)).strip()

        user = User(
            username=username_final,
            dni=pre.dni,
            email=email or "",
            is_active=bool(activar_usuario),
        )

        # Mapear nombres
        first_name, _middle = _split_names(pre.nombres or "")
        user.first_name = first_name
        user.last_name = pre.apellido or ""
        user.nombre_completo = f"{user.last_name}, {pre.nombres or ''}".strip(", ")

        # Rol
        if set_rol_estudiante:
            user.rol = UserProfile.Rol.ESTUDIANTE

        # Contacto
        user.telefono = pre.tel_movil or pre.tel_fijo or ""
        user.direccion = pre.domicilio or ""
        user.fecha_nacimiento = pre.fecha_nacimiento

        # Password
        temp_password = password or _rand_password()
        user.set_password(temp_password)

        user.save()

    # Si el user existe y queremos forzar rol estudiante (sin romper otros permisos)
    if set_rol_estudiante and user.rol != UserProfile.Rol.ESTUDIANTE:
        user.rol = UserProfile.Rol.ESTUDIANTE
        user.save(update_fields=["rol"])

    # Copiar foto si corresponde
    if copy_photo_to_user and hasattr(user, "foto_4x4"):
        try:
            if pre.foto_4x4 and pre.foto_4x4.name and not user.foto_4x4:
                from django.core.files.base import ContentFile
                pre.foto_4x4.open("rb")
                data = pre.foto_4x4.read()
                pre.foto_4x4.close()
                user.foto_4x4.save(f"user_{pre.dni}.jpg", ContentFile(data), save=True)
        except Exception:
            # tolerante: no abortar promoción por error al copiar foto
            pass

    # Crear (o recuperar) InscripcionCarrera (idempotente por (estudiante, carrera))
    insc, created = InscripcionCarrera.objects.get_or_create(
        estudiante=user,
        carrera=pre.carrera,
        defaults={}
    )

    # Bootstrap del legajo: crear filas por cada LegajoItemTipo, sin marcar completos
    # (el bedel hará el “checklist”). Si ya existen, no duplica.
    tipos = list(LegajoItemTipo.objects.all())
    existentes = set(LegajoItem.objects.filter(inscripcion=insc).values_list("tipo_id", flat=True))
    nuevos = [t for t in tipos if t.id not in existentes]
    LegajoItem.objects.bulk_create([
        LegajoItem(inscripcion=insc, tipo=t, cumplido=False, observacion="")
        for t in nuevos
    ])

    # Condición inicial/estado legajo:
    # Por defecto iniciamos "CONDICIONADO" + legajo "INCOMPLETO".
    condicion = getattr(InscripcionCarrera.EstadoAlumno, "CONDICIONADO", "CONDICIONADO")
    legajo_estado = getattr(InscripcionCarrera.LegajoEstado, "INCOMPLETO", "INCOMPLETO")

    # Si de la preinscripción surge una prueba fuerte (improbable) de completitud,
    # igual preferimos dejarlo “pendiente” para validación presencial.
    # Si querés cambiar esta regla, acá sería el lugar.

    # Si el modelo tiene campos explícitos, actualizalos de forma tolerante:
    to_update = []
    if hasattr(insc, "condicion") and insc.condicion != condicion:
        insc.condicion = condicion
        to_update.append("condicion")
    if hasattr(insc, "legajo_estado") and insc.legajo_estado != legajo_estado:
        insc.legajo_estado = legajo_estado
        to_update.append("legajo_estado")
    if to_update:
        insc.save(update_fields=to_update)

    return PromoteResult(
        pre=pre,
        user=user,
        temp_password=temp_password,
        insc=insc,
        condicion_inicial=condicion,
        legajo_estado_inicial=legajo_estado,
    )