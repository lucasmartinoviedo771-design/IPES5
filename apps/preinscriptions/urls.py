# apps/preinscriptions/urls.py
from django.urls import path
from .views_pdf import preinscripcion_pdf

app_name = "preinscriptions"

urlpatterns = [
    path("preinscripcion/<int:pk>/pdf/", preinscripcion_pdf, name="pre_pdf"),
]