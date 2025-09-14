from django.core.management.base import BaseCommand
from apps.academics.models import Ciclo

class Command(BaseCommand):
    help = "Crea ciclos lectivos básicos (Anual, 1C, 2C) si no existen"

    def handle(self, *args, **kwargs):
        data = [
            {"codigo": "ANUAL", "nombre": "Anual", "orden": 0, "activo": True},
            {"codigo": "1C",    "nombre": "1º Cuatrimestre", "orden": 1, "activo": True},
            {"codigo": "2C",    "nombre": "2º Cuatrimestre", "orden": 2, "activo": True},
        ]
        created = 0
        for d in data:
            obj, was_created = Ciclo.objects.get_or_create(codigo=d["codigo"], defaults=d)
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Ciclos creados: {created}"))
