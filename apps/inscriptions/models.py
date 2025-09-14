# apps/inscriptions/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.users.models import UserProfile
from apps.academics.models import Materia, Comision


class InscripcionCursada(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        CONDICIONAL = 'CONDICIONAL', 'Condicional por conflicto'
        REGULAR = 'REGULAR', 'Regular'
        LIBRE = 'LIBRE', 'Libre'
        BAJA = 'BAJA', 'Baja'

    class Tipo(models.TextChoices):
        REGULAR = "REGULAR", "Regular"
        OYENTE = "OYENTE", "Oyente"

    estudiante = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        limit_choices_to={'rol': UserProfile.Rol.ESTUDIANTE},
    )
    comision = models.ForeignKey(Comision, on_delete=models.CASCADE)
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    fecha_estado = models.DateTimeField(auto_now=True)
    motivo_condicion = models.CharField(max_length=80, blank=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.REGULAR)

    class Meta:
        verbose_name = 'Inscripción a Cursada'
        verbose_name_plural = 'Inscripciones a Cursada'
        unique_together = ['estudiante', 'comision']

    def clean(self):
        if self.estudiante.rol != UserProfile.Rol.ESTUDIANTE:
            raise ValidationError('Solo estudiantes pueden inscribirse a cursadas')

    def __str__(self):
        return f"{self.estudiante_id} -> {self.comision_id} ({self.estado})"


class InscripcionExamen(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        PRESENTE = 'PRESENTE', 'Presente'
        AUSENTE = 'AUSENTE', 'Ausente'
        APROBADO = 'APROBADO', 'Aprobado'
        DESAPROBADO = 'DESAPROBADO', 'Desaprobado'

    estudiante = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        limit_choices_to={'rol': UserProfile.Rol.ESTUDIANTE},
    )
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    fecha_examen = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    nota = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    intento = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Inscripción a Examen'
        verbose_name_plural = 'Inscripciones a Examen'
        unique_together = ['estudiante', 'materia', 'intento']

    def clean(self):
        if self.estudiante.rol != UserProfile.Rol.ESTUDIANTE:
            raise ValidationError('Solo estudiantes pueden inscribirse a exámenes')
        # exigir fecha en estados operativos
        if self.estado in {
            self.Estado.CONFIRMADA, self.Estado.PRESENTE,
            self.Estado.APROBADO, self.Estado.DESAPROBADO
        } and not self.fecha_examen:
            raise ValidationError({'fecha_examen': 'Debe estar definida para este estado.'})

    def __str__(self):
        return f"{self.estudiante_id} -> {self.materia_id} ({self.estado})"


class Periodo(models.Model):
    nombre = models.CharField(max_length=100, verbose_name='Nombre del Período')
    tipo = models.CharField(
        max_length=20,
        choices=[('CURSADA', 'Cursada'), ('EXAMEN', 'Examen')],
        verbose_name='Tipo',
    )
    fecha_inicio = models.DateTimeField(verbose_name='Fecha de Inicio')
    fecha_fin = models.DateTimeField(verbose_name='Fecha de Fin')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Período'
        verbose_name_plural = 'Períodos'

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

# --- NUEVO: inscripción de un estudiante a una carrera ---
class InscripcionCarrera(models.Model):
    class EstadoLegajo(models.TextChoices):
        COMPLETO = "COMPLETO", "Completo"
        INCOMPLETO = "INCOMPLETO", "Incompleto"

    class Condicion(models.TextChoices):
        REGULAR = "REGULAR", "Regular"
        CONDICIONADO = "CONDICIONADO", "Condicionado"

    estudiante = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE,
        limit_choices_to={'rol': UserProfile.Rol.ESTUDIANTE},
        related_name="inscripciones_carrera",
    )
    carrera = models.ForeignKey("academics.Carrera", on_delete=models.CASCADE)
    fecha_alta = models.DateTimeField(auto_now_add=True)

    estado_legajo = models.CharField(
        max_length=12, choices=EstadoLegajo.choices, default=EstadoLegajo.INCOMPLETO
    )
    condicion = models.CharField(
        max_length=13, choices=Condicion.choices, default=Condicion.CONDICIONADO
    )

    class Meta:
        unique_together = ["estudiante", "carrera"]

    def __str__(self):
        return f"{self.estudiante} → {self.carrera}"

    def recalcular_condicion(self):
        """Si TODO el checklist está OK → legajo COMPLETO → condición REGULAR."""
        total = self.checklist_items.count()
        completos = self.checklist_items.filter(completo=True).count()
        legajo = self.EstadoLegajo.COMPLETO if total and completos == total else self.EstadoLegajo.INCOMPLETO
        condicion = self.Condicion.REGULAR if legajo == self.EstadoLegajo.COMPLETO else self.Condicion.CONDICIONADO
        self.estado_legajo = legajo
        self.condicion = condicion
        self.save(update_fields=["estado_legajo", "condicion"])


# --- NUEVO: catálogo de ítems de legajo (configurable por carrera) ---
class LegajoItemTipo(models.Model):
    carrera = models.ForeignKey("academics.Carrera", on_delete=models.CASCADE, related_name="legajo_items_def")
    nombre = models.CharField(max_length=120)     # p.ej., "DNI", "Título secundario", "Foto 4x4"
    obligatorio = models.BooleanField(default=True)

    class Meta:
        unique_together = ["carrera", "nombre"]

    def __str__(self):
        return f"{self.carrera.codigo} - {self.nombre}"


# --- NUEVO: checklist del alumno para su inscripción de carrera ---
class LegajoItem(models.Model):
    insc_carrera = models.ForeignKey(InscripcionCarrera, on_delete=models.CASCADE, related_name="checklist_items")
    item = models.ForeignKey(LegajoItemTipo, on_delete=models.CASCADE)
    completo = models.BooleanField(default=False)          # casilla de verificación
    observaciones = models.TextField(blank=True)

    class Meta:
        unique_together = ["insc_carrera", "item"]

    def __str__(self):
        return f"{self.insc_carrera} / {self.item} → {'OK' if self.completo else 'FALTA'}"


class Alerta(models.Model):
    class Tipo(models.TextChoices):
        CONFLICTO_HORARIO = "CONFLICTO_HORARIO", "Conflicto de horario"

    class Estado(models.TextChoices):
        ABIERTA = "ABIERTA", "Abierta"
        RESUELTA = "RESUELTA", "Resuelta"

    tipo = models.CharField(max_length=40, choices=Tipo.choices)
    estudiante = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="alertas")
    detalle = models.TextField()
    comision_a = models.ForeignKey("academics.Comision", on_delete=models.CASCADE, related_name="+")
    comision_b = models.ForeignKey("academics.Comision", on_delete=models.CASCADE, related_name="+")
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ABIERTA)
    created_at = models.DateTimeField(auto_now_add=True)


class SolicitudExComision(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    estudiante = models.ForeignKey(UserProfile, on_delete=models.CASCADE, limit_choices_to={'rol': UserProfile.Rol.ESTUDIANTE})
    materia = models.ForeignKey("academics.Materia", on_delete=models.CASCADE)
    comision_destino = models.ForeignKey("academics.Comision", on_delete=models.CASCADE)
    motivo = models.TextField(blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
