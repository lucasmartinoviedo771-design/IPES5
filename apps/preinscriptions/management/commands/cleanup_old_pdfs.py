import os
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.preinscriptions.models import Preinscripcion

class Command(BaseCommand):
    help = "Elimina los archivos PDF de comprobantes de preinscripción con más de dos años de antigüedad."

    def handle(self, *args, **options):
        two_years_ago = timezone.now() - timedelta(days=365 * 2)
        
        self.stdout.write(f"Buscando comprobantes de preinscripción anteriores a {two_years_ago.strftime('%Y-%m-%d')}...")
        
        old_preinscriptions = Preinscripcion.objects.filter(
            creado__lt=two_years_ago
        ).exclude(comprobante_pdf__exact='')

        if not old_preinscriptions.exists():
            self.stdout.write(self.style.SUCCESS("No se encontraron comprobantes antiguos para eliminar."))
            return

        count = 0
        for pre in old_preinscriptions:
            if pre.comprobante_pdf:
                self.stdout.write(f"Eliminando archivo: {pre.comprobante_pdf.name}")
                pre.comprobante_pdf.delete(save=False) # Borra el archivo físico
                pre.save(update_fields=['comprobante_pdf']) # Actualiza el registro en la BD
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f"Se eliminaron exitosamente {count} archivos PDF antiguos."))
