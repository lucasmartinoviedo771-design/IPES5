from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

ROLES = ["ADMIN","SECRETARIA","BEDEL","DOCENTE","TUTOR","ESTUDIANTE"]

class Command(BaseCommand):
    help = "Crea (si faltan) grupos base de roles. Idempotente."

    def handle(self, *args, **kwargs):
        created = 0
        for name in ROLES:
            _, was_created = Group.objects.get_or_create(name=name)
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Grupos creados: {created} (si 0, ya existían)"))
