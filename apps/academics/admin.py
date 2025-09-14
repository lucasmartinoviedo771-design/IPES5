from django.contrib import admin
from .models import Ciclo, Carrera, Plan, Materia, Correlatividad, Comision, Horario

@admin.register(Ciclo)
class CicloAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "orden", "activo")
    list_filter = ("activo",)
    ordering = ("orden", "codigo")
