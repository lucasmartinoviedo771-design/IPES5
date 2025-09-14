from datetime import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.academics.models import Carrera, Plan, Materia, Comision, Horario
from apps.inscriptions.models import InscripcionCursada

class Command(BaseCommand):
    help = "Crea una segunda comisión (materia distinta) con choque horario y pre-inscribe al alumno en la primera."

    def handle(self, *args, **kwargs):
        User = get_user_model()
        alumno = User.objects.get(username="alumno")
        carrera, _ = Carrera.objects.get_or_create(codigo="TSDS", defaults={"nombre":"Tec DS","duracion_anios":3,"activa":True})
        plan, _ = Plan.objects.get_or_create(carrera=carrera, version="2024", defaults={"año_implementacion":2024,"activo":True})

        # Materia 1
        mat1, _ = Materia.objects.get_or_create(plan=plan, codigo="PG1",
            defaults={"nombre":"Programación I","año":1,"cuatrimestre":1,"horas_semanales":6,"puntos_credito":6})

        # Materia 2 (para el choque)
        mat2, _ = Materia.objects.get_or_create(plan=plan, codigo="BD1",
            defaults={"nombre":"Bases de Datos I","año":1,"cuatrimestre":1,"horas_semanales":4,"puntos_credito":4})

        anio = timezone.now().year

        # Limpiamos inscripciones y comisiones previas para un test limpio
        InscripcionCursada.objects.filter(estudiante=alumno).delete()
        Comision.objects.filter(materia__in=[mat1, mat2]).delete()

        # Comisión 1 (sin choque)
        c1, _ = Comision.objects.get_or_create(materia=mat1, turno="M", año=anio)
        Horario.objects.get_or_create(comision=c1, dia=1, hora_inicio=time(18,0), hora_fin=time(20,0)) # Lunes 18-20

        # Comisión 2 (con choque)
        c2, _ = Comision.objects.get_or_create(materia=mat2, turno="V", año=anio)
        Horario.objects.get_or_create(comision=c2, dia=1, hora_inicio=time(19,0), hora_fin=time(21,0))  # Lunes 19-21 -> choca

        # Pre-inscribimos al alumno en la primera comisión
        InscripcionCursada.objects.create(estudiante=alumno, comision=c1)

        self.stdout.write(self.style.SUCCESS(f"Listo. Alumno pre-inscripto en comision c1={c1.id} (PG1)."))
        self.stdout.write(self.style.SUCCESS(f"Intente inscribir a comision c2={c2.id} (BD1) para forzar el choque de horario."))
