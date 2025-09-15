# apps/preinscripciones/models.py
from django.conf import settings
from django.db import models, transaction
from django.core.validators import RegexValidator, EmailValidator
from django.core.exceptions import ValidationError
from apps.academics.models import Carrera
from django.utils import timezone
import uuid

class PreinscripcionSequence(models.Model):
    anio = models.IntegerField(unique=True)
    last = models.IntegerField(default=0)

    class Meta:
        db_table = "preinscriptions_sequence"

class EstadoCivil(models.TextChoices):
    SOLTERO = "SOLTERO", "Soltero/a"
    CASADO = "CASADO", "Casado/a"
    DIVORCIADO = "DIVORCIADO", "Divorciado/a"
    VIUDO = "VIUDO", "Viudo/a"
    OTRO = "OTRO", "Otro"

dni_validator = RegexValidator(regex=r"^\d{8}$", message="DNI debe tener 8 dígitos")
cuil_validator = RegexValidator(regex=r"^\d{2}-\d{8}-\d{1}$", message="CUIL/CUIT con formato 00-00000000-0")

class Preinscripcion(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.PROTECT)
    cuil = models.CharField(max_length=13, validators=[cuil_validator], verbose_name="CUIL/CUIT")
    dni = models.CharField(max_length=8, validators=[dni_validator], verbose_name="DNI")
    apellido = models.CharField(max_length=80)
    nombres = models.CharField(max_length=120)
    fecha_nacimiento = models.DateField()
    estado_civil = models.CharField(max_length=15, choices=EstadoCivil.choices, default=EstadoCivil.SOLTERO)
    localidad_nac = models.CharField(max_length=80)
    provincia_nac = models.CharField(max_length=80)
    pais_nac = models.CharField(max_length=80)
    nacionalidad = models.CharField(max_length=80)
    domicilio = models.CharField(max_length=200)
    tel_fijo = models.CharField(max_length=30, blank=True)
    tel_movil = models.CharField(max_length=30, blank=True)
    email = models.EmailField(validators=[EmailValidator()])
    trabaja = models.BooleanField(default=False)
    empleador = models.CharField(max_length=120, blank=True)
    horario_trabajo = models.CharField(max_length=120, blank=True)
    domicilio_trabajo = models.CharField(max_length=200, blank=True)
    sec_titulo = models.CharField(max_length=160, blank=True)
    sec_establecimiento = models.CharField(max_length=160, blank=True)
    sec_fecha_egreso = models.DateField(null=True, blank=True)
    sec_localidad = models.CharField(max_length=120, blank=True)
    sec_provincia = models.CharField(max_length=120, blank=True)
    sec_pais = models.CharField(max_length=120, blank=True)
    sup1_titulo = models.CharField(max_length=160, blank=True)
    sup1_establecimiento = models.CharField(max_length=160, blank=True)
    sup1_fecha_egreso = models.DateField(null=True, blank=True)
    sup1_localidad = models.CharField(max_length=120, blank=True)
    sup1_provincia = models.CharField(max_length=120, blank=True)
    sup1_pais = models.CharField(max_length=120, blank=True)
    sup2_titulo = models.CharField(max_length=160, blank=True)
    sup2_establecimiento = models.CharField(max_length=160, blank=True)
    sup2_fecha_egreso = models.DateField(null=True, blank=True)
    sup2_localidad = models.CharField(max_length=120, blank=True)
    sup2_provincia = models.CharField(max_length=120, blank=True)
    sup2_pais = models.CharField(max_length=120, blank=True)
    foto_4x4 = models.ImageField(upload_to="preinsc/fotos/", null=True, blank=True)
    doc_fotocopia_titulo_legalizada = models.BooleanField(default=False)
    doc_fotocopia_analitico_legalizada = models.BooleanField(default=False)
    doc_fotos_4x4 = models.BooleanField(default=False)
    doc_titulo_secundario = models.BooleanField(default=False)
    doc_titulo_terciario_universitario = models.BooleanField(default=False)
    doc_cert_alumno_regular = models.BooleanField(default=False)
    doc_cert_titulo_en_tramite = models.BooleanField(default=False)
    doc_cert_buena_salud = models.BooleanField(default=False)
    doc_folios = models.BooleanField(default=False)
    doc_adeuda_materias = models.BooleanField(default=False)
    adeuda_materias_detalle = models.TextField(blank=True)
    adeuda_materias_escuela = models.CharField(max_length=160, blank=True)
    doc_incumbencias = models.BooleanField(default=False)
    doc_declaracion_jurada = models.BooleanField(default=False)
    estado = models.CharField(max_length=15, choices=[("NUEVA", "Nueva"), ("CONFIRMADA", "Confirmada")], default="NUEVA")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="preinscripciones",
        help_text="Usuario dueño de esta preinscripción"
    )
    anio = models.PositiveIntegerField(db_index=True, default=timezone.now().year)
    numero = models.CharField(
        "Número",
        max_length=32,
        unique=True,
        null=True, blank=True,
        db_index=True,
    )
    comprobante_pdf = models.FileField(upload_to="preinscripciones/%Y/", blank=True, null=True)
    creado = models.DateTimeField(default=timezone.now, editable=False)
    created_at = models.DateTimeField(auto_now_add=True) # Mantener created_at para compatibilidad

    class Meta:
        ordering = ["-creado"]

    def save(self, *args, **kwargs):
        if not self.anio:
            self.anio = timezone.now().year

        if not self.numero:
            with transaction.atomic():
                seq, _ = PreinscripcionSequence.objects.select_for_update().get_or_create(anio=self.anio)
                seq.last += 1
                seq.save(update_fields=["last"])
                self.numero = f"PRE-{self.anio}-{seq.last:04d}"
        
        super().save(*args, **kwargs)

    def clean(self):
        if self.doc_titulo_secundario and (self.doc_cert_titulo_en_tramite or self.doc_adeuda_materias):
            raise ValidationError("‘Título secundario’ es incompatible con ‘en trámite’ o ‘adeuda materias’.")
        if self.doc_cert_titulo_en_tramite and (self.doc_titulo_secundario or self.doc_adeuda_materias):
            raise ValidationError("‘Título en trámite’ es incompatible con ‘título’ o ‘adeuda materias’.")
        if self.doc_adeuda_materias:
            if not self.adeuda_materias_detalle.strip() or not self.adeuda_materias_escuela.strip():
                raise ValidationError("Si marca ‘Adeuda materias’, debe indicar materias y escuela.")

    def __str__(self):
        return f"{self.apellido}, {self.nombres} ({self.dni})"

class PortalNotification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portal_notifications",
        db_index=True
    )
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "portal_notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.title}"

    def is_read(self):
        return self.read_at is not None

    def mark_read(self):
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])
        return self
