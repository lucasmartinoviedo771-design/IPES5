from django.core.management.base import BaseCommand
from apps.academics.models import Comision

class Command(BaseCommand):
    help = "Lista comisiones con cupo_maximo definido y su ocupación actual"

    def handle(self, *args, **options):
        qs = Comision.objects.exclude(cupo_maximo__isnull=True)
        if not qs.exists():
            self.stdout.write("No hay comisiones con cupo_maximo configurado.")
            return
        for c in qs.select_related("materia"):
            usados = c.inscripcioncursada_set.exclude(estado="BAJA").count()
            marca = " ⚠" if c.cupo_maximo and usados >= c.cupo_maximo else ""
            self.stdout.write(f"[{c.id}] {c} — {usados}/{c.cupo_maximo}{marca}")