from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("preinscripcion", views.preinscripcion_form, name="preinscripcion"),
    path("preinscripcion/<int:pk>/ok", views.preinscripcion_ok, name="pre_ok"),
    path("panel", views.panel, name="panel"),
    path("panel/legajo/<int:insc_id>", views.legajo_detalle, name="legajo_detalle"),
]