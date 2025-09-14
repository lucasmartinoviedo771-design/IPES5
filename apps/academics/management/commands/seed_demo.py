from datetime import time, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.apps import apps

from apps.academics.models import Carrera, Plan, Materia, Comision
from apps.inscriptions.models import Periodo


class Command(BaseCommand):
    help = "Carga datos mínimos de prueba (idempotente) para IPES5."

    def _maybe_set_api_key(self, user, key):
        # Setea api_key / auth_token solo si existen en el modelo real
        changed = False
        if hasattr(user, "api_key"):
            user.api_key = key
            changed = True
        if hasattr(user, "auth_token"):
            setattr(user, "auth_token", key)
            changed = True
        if changed:
            user.save(update_fields=["api_key"] if hasattr(user, "api_key") else None)

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        # 1) Usuarios base
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin @ipes.edu",
                "first_name": "Admin",
                "last_name": "IPES",
                "rol": "ADMIN",
                "dni": "12345678",
            },
        )
        admin.set_password("password123")
        admin.save()
        self._maybe_set_api_key(admin, "DEVKEY-ADMIN")

        alumno, _ = User.objects.get_or_create(
            username="alumno",
            defaults={
                "email": "alumno @ipes.edu",
                "first_name": "Alu",
                "last_name": "MNO",
                "rol": "ESTUDIANTE",
                "dni": "56789012",
            },
        )
        alumno.set_password("password123")
        alumno.save()
        self._maybe_set_api_key(alumno, "DEVKEY-ALUMNO")

        # 2) Carrera / Plan / Materia
        carrera, _ = Carrera.objects.get_or_create(
            codigo="TSDS",
            defaults={"nombre": "Tecnicatura en Desarrollo de Software", "duracion_anios": 3, "activa": True},
        )
        plan, _ = Plan.objects.get_or_create(
            carrera=carrera,
            version="2024",
            defaults={"año_implementacion": 2024, "activo": True},
        )
        materia, _ = Materia.objects.get_or_create(
            plan=plan,
            codigo="PG1",
            defaults={
                "nombre": "Programación I",
                "año": 1,
                "cuatrimestre": 1,
                "horas_semanales": 6,
                "puntos_credito": 6,
            },
        )

        # 3) Comisión (con el modelo actual: turno + año [+ cupo_maximo opcional])
        anio_lectivo = timezone.now().year
        comision_defaults = {}
        if hasattr(Comision, "cupo_maximo"):
            comision_defaults["cupo_maximo"] = 30  # solo alerta; no bloquea ni abre comisiones
        comision, _ = Comision.objects.get_or_create(
            materia=materia,
            turno="M",  # Mañana
            año=anio_lectivo,
            defaults=comision_defaults,
        )

        # 4) Horario (solo si el modelo existe)
        Horario = apps.get_model("academics", "Horario", require_ready=False)
        if Horario is not None:
            # introspección de campos para no asumir 'aula'
            field_names = {f.name for f in Horario._meta.get_fields()}
            horario_kwargs = dict(comision=comision, dia=1, hora_inicio=time(18, 0), hora_fin=time(20, 0)) # 1 = Lunes
            if "aula" in field_names:
                horario_kwargs["aula"] = "A101"
            Horario.objects.get_or_create(**horario_kwargs)
            self.stdout.write(self.style.SUCCESS("Horario creado o ya existente."))
        else:
            self.stdout.write("Modelo Horario no disponible. Se omite creación de horarios.")

        # 5) Período de CURSADA activo
        Periodo.objects.get_or_create(
            nombre="Cursada Demo",
            tipo="CURSADA",
            defaults={
                "fecha_inicio": timezone.now() - timedelta(days=1),
                "fecha_fin": timezone.now() + timedelta(days=30),
                "activo": True,
            },
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Datos minimos creados/asegurados"))
        self.stdout.write(f"  - admin / password123   (X-API-Key: {'DEVKEY-ADMIN' if hasattr(admin,'api_key') or hasattr(admin,'auth_token') else '—'})")
        self.stdout.write(f"  - alumno / password123  (X-API-Key: {'DEVKEY-ALUMNO' if hasattr(alumno,'api_key') or hasattr(alumno,'auth_token') else '—'})")
        self.stdout.write(f"  - comision_id = {comision.id} | estudiante_id = {alumno.id}")
