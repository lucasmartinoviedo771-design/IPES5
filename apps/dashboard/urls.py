from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("preinscripcion/", views.preinscripcion_form, name="preinscripcion"),
    path("preinscripcion/<int:pk>/ok/", views.preinscripcion_ok, name="pre_ok"),
    path("panel/", views.panel, name="panel"),
    path("panel/legajo/<int:insc_id>/", views.legajo_detalle, name="legajo_detalle"),
    path("preinscripcion/<int:pk>/confirmar/", views.preinscripcion_confirmar, name="pre_confirmar"),
    path("preinscripcion/numero/<str:numero>/", views.preinscripcion_verificar_public, name="pre_public_verify"),

    # Rutas de autorización
    path("autorizar/", views.preinscripciones_autorizar_list, name="pre_autorizar_list"),
    path("autorizar/<int:pk>/", views.preinscripcion_autorizar, name="pre_autorizar"),
]