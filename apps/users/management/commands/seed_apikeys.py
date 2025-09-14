from django.core.management.base import BaseCommand
from apps.users.models import UserProfile

class Command(BaseCommand):
    help = "Asigna api_key a usuarios que no la tengan"

    def handle(self, *args, **opts):
        created = 0
        for u in UserProfile.objects.all():
            if not u.api_key:
                u.ensure_api_key()
                created += 1
                self.stdout.write(f"{u.username} -> {u.api_key}")
        self.stdout.write(self.style.SUCCESS(f"Listo. API keys asignadas: {created}"))