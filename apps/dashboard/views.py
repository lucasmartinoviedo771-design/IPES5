from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.db.models import Count
from apps.users.models import UserProfile
from apps.preinscriptions.models import Preinscripcion
from apps.inscriptions.models import InscripcionCarrera, LegajoItem
from apps.academics.models import Carrera
from django.core.files.base import ContentFile
from django.urls import reverse
from apps.preinscriptions.forms import PreinscripcionForm
from apps.preinscriptions.pdf_utils import render_pdf_from_template

import logging
from django.http import HttpResponse, HttpResponseServerError
from django.contrib import messages
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

def _is_staff_like(user):
    return user.is_authenticated and getattr(user, "rol", None) in (
        UserProfile.Rol.ADMIN, UserProfile.Rol.SECRETARIA, UserProfile.Rol.BEDEL
    )

def home(request):
    return render(request, "dashboard/home.html", {})

def preinscripcion_form(request):
    if request.method == 'POST':
        form = PreinscripcionForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pre = form.save()
                # Intentar generar y guardar el PDF, pero no fallar si algo sale mal
                try:
                    pdf_bytes = render_pdf_from_template(
                        "preinscripciones/pdf/preinscripcion_pdf.html",
                        {"pre": pre}
                    )
                    pre.comprobante_pdf.save(f"{pre.numero}.pdf", ContentFile(pdf_bytes), save=True)
                    messages.success(request, f"¡Preinscripción enviada correctamente! Nº {pre.numero}")
                except Exception as e:
                    logger.exception("Error generando PDF de preinscripción para %s: %s", pre.numero, e)
                    messages.warning(
                        request,
                        f"Tu preinscripción {pre.numero} se guardó, pero no pudimos generar el comprobante en PDF. "
                        "Podrás descargarlo más adelante."
                    )
                
                return redirect(reverse("dashboard:preinscripcion_gracias", args=[pre.id]))
            except Exception as e:
                logger.exception("Error al guardar preinscripción: %s", e)
                form.add_error(None, "Ocurrió un error inesperado al guardar la preinscripción. Intentalo nuevamente o contactá a la administración.")
        else:
            messages.error(request, "No se pudo guardar. Por favor, revisá los campos marcados en rojo.")
    else:
        form = PreinscripcionForm()

    return render(request, "dashboard/preinscripcion_form.html", {"form": form})


def preinscripcion_gracias(request, pk):
    pre = get_object_or_404(Preinscripcion, pk=pk)
    return render(
        request,
        "dashboard/preinscripcion_gracias.html",
        {
            "pre": pre,
            "link_pdf": pre.comprobante_pdf.url if pre.comprobante_pdf else None,
        },
    )

@login_required
def panel(request):
    if not _is_staff_like(request.user):
        return HttpResponseForbidden("Permisos insuficientes")

    por_carrera = (
        Preinscripcion.objects.values("carrera__id", "carrera__nombre")
        .annotate(total=Count("id"))
        .order_by("carrera__nombre")
    )

    recientes = (
        Preinscripcion.objects.select_related("carrera")
        .order_by("-id")[:20]
    )

    return render(request, "dashboard/panel.html", {
        "por_carrera": por_carrera,
        "recientes": recientes,
    })

@login_required
def legajo_detalle(request, insc_id: int):
    if not _is_staff_like(request.user):
        return HttpResponseForbidden("Permisos insuficientes")

    insc = (
        InscripcionCarrera.objects
        .select_related("estudiante", "carrera")
        .filter(id=insc_id)
        .first()
    )
    if not insc:
        return render(request, "dashboard/legajo.html", {"error": "Inscripción no encontrada"})

    items = (
        LegajoItem.objects
        .select_related("tipo")
        .filter(inscripcion=insc)
        .order_by("tipo__nombre")
    )
    total = items.count()
    cumplidos = items.filter(cumplido=True).count()

    return render(request, "dashboard/legajo.html", {
        "insc": insc,
        "items": items,
        "total": total,
        "cumplidos": cumplidos,
        "legajo_estado": getattr(insc, "legajo_estado", "INCOMPLETO"),
        "condicion": getattr(insc, "condicion", "CONDICIONADO"),
    })
