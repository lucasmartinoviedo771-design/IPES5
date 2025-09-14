from django.contrib import admin
from .models import Preinscripcion

@admin.register(Preinscripcion)
class PreinscripcionAdmin(admin.ModelAdmin):
    """
    Panel de administración para gestionar las preinscripciones.
    Permite una gestión rápida de la documentación presentada.
    """
    # --- Vista de Lista ---
    list_display = (
        'apellido',
        'nombres',
        'dni',
        'carrera',
        'creado',
        # Documentos clave para toggle rápido
        'doc_titulo_secundario',
        'doc_cert_titulo_en_tramite',
        'doc_adeuda_materias',
        'doc_fotos_4x4',
        'doc_declaracion_jurada',
    )
    # --- Checkboxes editables directamente en la lista ---
    list_editable = (
        'doc_titulo_secundario',
        'doc_cert_titulo_en_tramite',
        'doc_adeuda_materias',
        'doc_fotos_4x4',
        'doc_declaracion_jurada',
    )
    # --- Filtros y Búsqueda ---
    list_filter = ('carrera', 'creado')
    search_fields = ('apellido', 'nombres', 'dni', 'cuil')
    date_hierarchy = 'creado'

    # --- Vista de Detalle (Formulario) ---
    # Organiza los campos en secciones lógicas
    fieldsets = (
        ("Datos del Postulante", {
            'fields': ('carrera', ('apellido', 'nombres'), ('dni', 'cuil'), 'fecha_nacimiento', 'estado_civil')
        }),
        ("Origen y Contacto", {
            'fields': (('localidad_nac', 'provincia_nac', 'pais_nac'), 'nacionalidad', 'domicilio', ('tel_fijo', 'tel_movil'), 'email')
        }),
        ("Datos Laborales", {
            'classes': ('collapse',), # Opcional: se puede ocultar por defecto
            'fields': ('trabaja', 'empleador', 'horario_trabajo', 'domicilio_trabajo')
        }),
        ("Estudios Cursados", {
            'classes': ('collapse',),
            'fields': (
                'sec_titulo', 'sec_establecimiento', 'sec_fecha_egreso',
                ('sec_localidad', 'sec_provincia', 'sec_pais'),
                'sup1_titulo', 'sup1_establecimiento', 'sup1_fecha_egreso',
                'sup2_titulo', 'sup2_establecimiento', 'sup2_fecha_egreso',
            )
        }),
        ("Documentación Presentada (Gestión Interna)", {
            'fields': (
                # Grupo 1: Estado del secundario
                'doc_titulo_secundario',
                'doc_cert_titulo_en_tramite',
                'doc_adeuda_materias',
                # Detalles si adeuda
                ('adeuda_materias_detalle', 'adeuda_materias_escuela'),
                # Grupo 2: Documentos generales
                'doc_fotocopia_titulo_legalizada',
                'doc_fotocopia_analitico_legalizada',
                'doc_fotos_4x4',
                'doc_cert_buena_salud',
                'doc_folios',
                'doc_declaracion_jurada',
                # Grupo 3: Específicos
                'doc_incumbencias',
                'doc_titulo_terciario_universitario',
                'doc_cert_alumno_regular',
            )
        }),
        ("Foto 4x4", {
            'fields': ('foto_4x4',)
        })
    )

    def get_queryset(self, request):
        # Optimiza la carga de la FK a carrera
        return super().get_queryset(request).select_related('carrera')