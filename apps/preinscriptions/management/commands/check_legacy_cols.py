from django.core.management.base import BaseCommand
from django.db import connection


LEGACY = [
    "loc_nacimiento","prov_nacimiento","pais_nacimiento",
    "secu_titulo","secu_institucion","secu_promedio","secu_anio_egreso",
    "sup1_titulo","sup1_institucion","sup2_titulo","sup2_institucion",
]


class Command(BaseCommand):
    help = "Muestra conteos de no-nulos en columnas legadas para decidir drop"

    def handle(self, *args, **opts):
        with connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM preinscriptions_preinscripcion")
            total = cur.fetchone()[0]
            self.stdout.write(self.style.NOTICE(f"Total filas: {total}"))
            for col in LEGACY:
                try:
                    cur.execute(f"SELECT SUM({col} IS NOT NULL) FROM preinscriptions_preinscripcion")
                    cnt = cur.fetchone()[0]
                    self.stdout.write(f"{col:30s} → {cnt}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"{col:30s} → ERROR: {e}"))
