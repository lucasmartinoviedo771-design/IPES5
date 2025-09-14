import csv
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from .models import Preinscripcion

@staff_member_required
def export_preinscripciones_csv(request):
    qs = (Preinscripcion.objects
          .values('carrera__nombre')
          .annotate(total=Count('id'))
          .order_by('carrera__nombre'))

    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="preinscripciones_por_carrera.csv"'
    w = csv.writer(resp)
    w.writerow(['Carrera', 'Total'])
    for row in qs:
        w.writerow([row['carrera__nombre'] or '(sin carrera)', row['total']])
    return resp