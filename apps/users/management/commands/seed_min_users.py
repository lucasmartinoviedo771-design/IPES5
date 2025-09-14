from django.core.management.base import BaseCommand
from apps.users.models import UserProfile

BASE_USERS = [
    {"username": "admin",      "first_name": "Admin",      "last_name": "Sistema",   "email": "admin@ipes5.edu.ar",      "dni": "10000000", "rol": UserProfile.Rol.ADMIN},
    {"username": "secretaria", "first_name": "María",      "last_name": "Secretaria","email": "secretaria@ipes5.edu.ar", "dni": "10000001", "rol": UserProfile.Rol.SECRETARIA},
    {"username": "bedel",      "first_name": "Juan",       "last_name": "Bedel",     "email": "bedel@ipes5.edu.ar",      "dni": "10000002", "rol": UserProfile.Rol.BEDEL},
    {"username": "docente",    "first_name": "Carlos",     "last_name": "Docente",   "email": "docente@ipes5.edu.ar",    "dni": "10000003", "rol": UserProfile.Rol.DOCENTE},
    {"username": "tutor",      "first_name": "Lucía",      "last_name": "Tutor",     "email": "tutor@ipes5.edu.ar",      "dni": "10000004", "rol": UserProfile.Rol.TUTOR},
    {"username": "estudiante", "first_name": "Ana",        "last_name": "Estudiante","email": "estudiante@ipes5.edu.ar", "dni": "10000005", "rol": UserProfile.Rol.ESTUDIANTE},
]

class Command(BaseCommand):
    help = "Crea usuarios mínimos y asigna api_key si falta"

    def handle(self, *args, **kwargs):
        created, keyed = 0, 0
        for data in BASE_USERS:
            obj, was_created = UserProfile.objects.get_or_create(
                username=data["username"],
                defaults={**data}
            )
            if was_created:
                obj.set_password("password123")
                obj.save()
                created += 1
            if not obj.api_key:
                obj.ensure_api_key()
                keyed += 1
            self.stdout.write(f"{obj.username} -> {obj.api_key}")
        self.stdout.write(self.style.SUCCESS(f"Usuarios creados: {created}; API keys asignadas: {keyed}"))
