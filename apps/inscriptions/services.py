from dataclasses import dataclass
from typing import Optional, Iterable
from django.db.models import Q
from django.utils import timezone

from apps.users.models import UserProfile
from apps.academics.models import Materia, Comision, Correlatividad, Horario
from apps.inscriptions.models import InscripcionCursada, InscripcionExamen, Periodo


class BusinessError(Exception):
    """Error de regla de negocio que debe mapearse a HTTP 409."""
    def __init__(self, message: str, code: str = "CONFLICT"):
        super().__init__(message)
        self.message = message
        self.code = code


def _periodo_cursada_activo(now=None) -> Periodo:
    now = now or timezone.now()
    qs = Periodo.objects.filter(
        tipo="CURSADA", activo=True,
        fecha_inicio__lte=now, fecha_fin__gte=now
    ).order_by("-fecha_inicio")
    if not qs.exists():
        raise BusinessError("No hay un PERÍODO DE CURSADA activo.", code="PERIODO")
    return qs.first()


def _time_overlap(a_ini, a_fin, b_ini, b_fin) -> bool:
    # Solapa si intersección no vacía
    return max(a_ini, b_ini) < min(a_fin, b_fin)


def _verificar_choque_horario(estudiante: UserProfile, comision_destino: Comision):
    """Bloquea choques de horario con inscripciones activas del estudiante."""
    # Inscripciones activas (no BAJA) del alumno
    insc_activas = (InscripcionCursada.objects
                    .filter(estudiante=estudiante)
                    .exclude(estado=InscripcionCursada.Estado.BAJA)
                    .select_related("comision__materia"))

    if not insc_activas.exists():
        return

    # Horarios destino
    h_dest = list(comision_destino.horarios.all())
    if not h_dest:
        return  # si la comisión no tiene horarios, no hay choque que verificar

    # Horarios existentes del alumno
    comisiones_existentes = [i.comision_id for i in insc_activas]
    h_exist = (Horario.objects
               .filter(comision_id__in=comisiones_existentes)
               .select_related("comision__materia"))

    for he in h_exist:
        for hd in h_dest:
            if he.dia == hd.dia and _time_overlap(he.hora_inicio, he.hora_fin, hd.hora_inicio, hd.hora_fin):
                mat_e = he.comision.materia
                mat_d = comision_destino.materia
                # Regla: ante choque, debe elegirse la de AÑO más bajo
                if mat_d.año > mat_e.año:
                    raise BusinessError(
                        f"Choque de horario con {mat_e.codigo} ({mat_e.año}º). "
                        f"Debe priorizarse la materia de año más bajo.",
                        code="CHOQUE_HORARIO"
                    )
                else:
                    raise BusinessError(
                        f"Choque de horario con {mat_e.codigo}. "
                        f"Retire la otra inscripción antes de continuar.",
                        code="CHOQUE_HORARIO"
                    )


def _verificar_correlatividades_para_cursada(estudiante: UserProfile, materia_obj: Materia):
    """Verifica correlativas:
       - requiere_regular=True: debe tener REGULAR (o APROBADO) en la correlativa
       - requiere_aprobada=True: debe tener APROBADO en la correlativa
    """
    correl = Correlatividad.objects.filter(materia=materia_obj).select_related("materia_correlativa")

    for c in correl:
        m = c.materia_correlativa

        # ¿Aprobada?
        tiene_aprobada = InscripcionExamen.objects.filter(
            estudiante=estudiante, materia=m, estado=InscripcionExamen.Estado.APROBADO
        ).exists()

        # ¿Regular (o aprobada)?
        tiene_regular = (
            InscripcionCursada.objects.filter(
                estudiante=estudiante, comision__materia=m,
                estado=InscripcionCursada.Estado.REGULAR
            ).exists()
            or tiene_aprobada
        )

        if c.requiere_aprobada and not tiene_aprobada:
            raise BusinessError(
                f"Correlativa no cumplida: {m.codigo} requiere APROBADA.",
                code="CORRELATIVIDADES"
            )
        if c.requiere_regular and not tiene_regular:
            raise BusinessError(
                f"Correlativa no cumplida: {m.codigo} requiere REGULAR.",
                code="CORRELATIVIDADES"
            )


def _verificar_duplicado_materia(estudiante: UserProfile, materia_obj: Materia):
    """Evita dos comisiones de la MISMA materia activas para el mismo alumno."""
    ya_tiene = (InscripcionCursada.objects
                .filter(estudiante=estudiante, comision__materia=materia_obj)
                .exclude(estado=InscripcionCursada.Estado.BAJA)
                .exists())
    if ya_tiene:
        raise BusinessError(
            "Ya existe una inscripción activa en otra comisión de la misma materia.",
            code="DUPLICADA"
        )


def _aviso_cupo(comision: Comision) -> Optional[str]:
    cupo = getattr(comision, "cupo_maximo", None)
    if not cupo:
        return None
    usados = (InscripcionCursada.objects
              .filter(comision=comision)
              .exclude(estado=InscripcionCursada.Estado.BAJA)
              .count())
    if usados >= cupo:
        return f"Capacidad alcanzada o superada ({usados}/{cupo}). Considerar abrir otra comisión (proceso manual)."
    return None


def crear_inscripcion_cursada(*, estudiante: UserProfile, comision: Comision) -> tuple[InscripcionCursada, Optional[str]]:
    """Orquesta las validaciones y crea la inscripción en estado PENDIENTE."""
    _periodo_cursada_activo()
    _verificar_correlatividades_para_cursada(estudiante, comision.materia)
    _verificar_duplicado_materia(estudiante, comision.materia)
    _verificar_choque_horario(estudiante, comision)

    obj, created = InscripcionCursada.objects.get_or_create(
        estudiante=estudiante,
        comision=comision,
        defaults={"estado": InscripcionCursada.Estado.PENDIENTE}
    )
    # Si ya existía pero no en BAJA, unique_together lo impide. Si existía en BAJA, get_or_create lo retorna.
    aviso = _aviso_cupo(comision)
    return obj, aviso
