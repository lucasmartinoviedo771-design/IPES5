from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("preinscripcion", views.preinscripcion_form, name="preinscripcion_form"),
    path("preinscripcion/gracias/<int:pk>", views.preinscripcion_gracias, name="preinscripcion_gracias"),
    path("panel", views.panel, name="panel"),
    path("panel/legajo/<int:insc_id>", views.legajo_detalle, name="legajo_detalle"),
]