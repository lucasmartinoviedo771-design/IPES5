from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import LegajoItem

@receiver(post_save, sender=LegajoItem)
def _recalc_legajo_y_condicion(sender, instance, **kwargs):
    """
    After a LegajoItem is saved, recalculate the student's
    overall legajo status and academic condition.
    """
    instance.insc_carrera.recalcular_condicion()
