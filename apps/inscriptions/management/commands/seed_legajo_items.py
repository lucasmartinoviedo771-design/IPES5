from typing import Iterable, Tuple
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.models import Carrera
from apps.inscriptions.models import InscripcionCarrera, LegajoItemTipo, LegajoItem


DEFAULT_ITEMS: Tuple[Tuple[str, bool], ...] = (
    ("DNI", True),
    ("Partida de nacimiento", True),
    ("Título secundario", True),
    ("Foto 4x4", True),
)


class Command(BaseCommand):
    help = (
        "Siembra el catálogo de ítems de legajo (LegajoItemTipo) por carrera. "
        "Idempotente. Opcionalmente borra y recrea (--reset) y hace backfill "
        "de LegajoItem para InscripcionCarrera existentes (--backfill)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--carrera-id",
            type=int,
            default=None,
            help="ID de la carrera a sembrar. Si se omite, se siembran todas las carreras.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Borra el catálogo existente de la(s) carrera(s) y lo vuelve a crear.",
        )
        parser.add_argument(
            "--backfill",
            action="store_true",
            help="Crea (get_or_create) LegajoItem faltantes para InscripcionCarrera existentes.",
        )

    def _get_carreras(self, carrera_id: int | None) -> Iterable[Carrera]:
        if carrera_id:
            return Carrera.objects.filter(id=carrera_id)
        return Carrera.objects.all()

    @transaction.atomic
    def handle(self, *args, **options):
        carrera_id = options.get("carrera_id")
        do_reset = options.get("reset", False)
        do_backfill = options.get("backfill", False)

        carreras = list(self._get_carreras(carrera_id))
        if not carreras:
            if carrera_id:
                self.stdout.write(self.style.WARNING(f"No se encontró la carrera id={carrera_id}."))
            else:
                self.stdout.write(self.style.WARNING("No hay carreras para procesar."))
            return

        total_created_tipos = 0
        total_backfilled_items = 0

        for carrera in carreras:
            self.stdout.write(f"-> Carrera {carrera.id} [{carrera.codigo}] - {carrera.nombre}")

            if do_reset:
                # Elimina el catálogo (y por FK, los LegajoItem asociados a esos tipos)
                deleted, _ = LegajoItemTipo.objects.filter(carrera=carrera).delete()
                self.stdout.write(self.style.WARNING(f"  Reset catálogo: borrados {deleted} registros (tipos + items por FK)."))

            # Crear catálogo base (idempotente)
            created_count = 0
            for nombre, obligatorio in DEFAULT_ITEMS:
                _, created = LegajoItemTipo.objects.get_or_create(
                    carrera=carrera,
                    nombre=nombre,
                    defaults={"obligatorio": obligatorio},
                )
                if created:
                    created_count += 1
            total_created_tipos += created_count
            self.stdout.write(self.style.SUCCESS(f"  Catálogo: {created_count} tipo(s) nuevos; el resto ya existían."))

            if do_backfill:
                # Asegurar LegajoItem para cada InscripcionCarrera de esta carrera
                tipos = list(LegajoItemTipo.objects.filter(carrera=carrera))
                if not tipos:
                    self.stdout.write("  Backfill: sin tipos que propagar (catálogo vacío).")
                else:
                    backfill_count = 0
                    insc_qs = InscripcionCarrera.objects.filter(carrera=carrera).only("id")
                    for insc in insc_qs:
                        for t in tipos:
                            _, created = LegajoItem.objects.get_or_create(
                                insc_carrera=insc,
                                item=t,
                                defaults={"completo": False, "observaciones": ""},
                            )
                            if created:
                                backfill_count += 1
                    total_backfilled_items += backfill_count
                    self.stdout.write(self.style.SUCCESS(f"  Backfill: creados {backfill_count} LegajoItem nuevos."))

        # Resumen final
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Seed completado"))
        self.stdout.write(f"  Tipos creados: {total_created_tipos}")
        if do_backfill:
            self.stdout.write(f"  LegajoItem backfilled: {total_backfilled_items}")
