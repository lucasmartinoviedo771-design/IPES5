from django.db import models
from django.core.exceptions import ValidationError
from apps.users.models import UserProfile

class Ciclo(models.Model):
    """Catálogo de ciclos lectivos: Anual, 1º Cuatr., 2º Cuatr."""
    class Codigo(models.TextChoices):
        ANUAL = "ANUAL", "Anual"
        CUAT1 = "1C", "1º Cuatrimestre"
        CUAT2 = "2C", "2º Cuatrimestre"

    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=50)
    orden = models.PositiveSmallIntegerField(default=0)  # Para ordenar en UI/listados
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Ciclo lectivo"
        verbose_name_plural = "Ciclos lectivos"
        ordering = ["orden", "id"]

    def __str__(self):
        return f"{self.nombre}"

class Carrera(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=255)
    duracion_anios = models.PositiveIntegerField()
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class Plan(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name='planes')
    version = models.CharField(max_length=20)
    año_implementacion = models.PositiveIntegerField()
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ['carrera', 'version']

    def __str__(self):
        return f"{self.carrera} - Plan {self.version}"

class Materia(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='materias', null=True)
    codigo = models.CharField(max_length=10, verbose_name='Código', default='TEMP')
    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    año = models.PositiveIntegerField(verbose_name='Año')
    cuatrimestre = models.PositiveIntegerField(  # mantenemos por compatibilidad
        choices=[(1, '1º Cuatrimestre'), (2, '2º Cuatrimestre')],
        null=True,
        blank=True,
        verbose_name='Cuatrimestre'
    )
    # NUEVO: vínculo opcional al catálogo de Ciclos
    ciclo = models.ForeignKey(
        Ciclo, on_delete=models.PROTECT, null=True, blank=True, related_name="materias"
    )
    horas_semanales = models.PositiveIntegerField(verbose_name='Horas Semanales', default=0)
    puntos_credito = models.PositiveIntegerField(verbose_name='Puntos de Crédito', default=0)

    class Meta:
        verbose_name = 'Materia'
        verbose_name_plural = 'Materias'
        unique_together = ['plan', 'codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def clean(self):
        # Si hay cuatrimestre, debe mapear coherentemente con ciclo si este se provee
        if self.ciclo and self.cuatrimestre:
            mapa = {1: "1C", 2: "2C"}
            if self.cuatrimestre in mapa and self.ciclo.codigo not in (mapa[self.cuatrimestre], "ANUAL"):
                raise ValidationError({"ciclo": "Ciclo no coincide con el cuatrimestre seleccionado."})

class Comision(models.Model):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='comisiones')
    TURNO_CHOICES = [('M','Mañana'),('T','Tarde'),('V','Vespertino')]
    turno = models.CharField(max_length=1, choices=TURNO_CHOICES, default='M')
    año = models.PositiveIntegerField()

    # NUEVO: solo para alertas, no bloquea ni abre comisiones automáticamente
    cupo_maximo = models.PositiveIntegerField(null=True, blank=True, help_text="Solo alertas; no bloquea ni abre comisiones.")

    def __str__(self):
        return f"{self.materia.codigo} - {self.get_turno_display()} {self.año}"

    # (opcional) utilidad rápida para reportes
    def cupos_utilizados(self) -> int:
        # evitamos import circular usando valores string de estado
        return self.inscripcioncursada_set.exclude(estado='BAJA').count()

class Horario(models.Model):
    comision = models.ForeignKey(Comision, on_delete=models.CASCADE, related_name='horarios')
    DIA_CHOICES = [
        (1, 'Lunes'),
        (2, 'Martes'),
        (3, 'Miércoles'),
        (4, 'Jueves'),
        (5, 'Viernes'),
        (6, 'Sábado'),
    ]
    dia = models.PositiveIntegerField(choices=DIA_CHOICES)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    def __str__(self):
        return f"{self.get_dia_display()} {self.hora_inicio}-{self.hora_fin}"

    def clean(self):
        if self.hora_inicio >= self.hora_fin:
            raise ValidationError('hora_inicio debe ser anterior a hora_fin')
        # Evita superposición dentro de la misma comisión
        qs = Horario.objects.filter(comision=self.comision, dia=self.dia)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.filter(hora_inicio__lt=self.hora_fin, hora_fin__gt=self.hora_inicio).exists():
            raise ValidationError('Horario superpuesto en la misma comisión')

class Correlatividad(models.Model):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='correlativas')
    materia_correlativa = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='es_correlativa_de')
    requiere_aprobada = models.BooleanField(default=False)
    requiere_regular = models.BooleanField(default=False)

    class Meta:
        unique_together = ['materia', 'materia_correlativa']

    def __str__(self):
        return f"{self.materia} requiere {self.materia_correlativa}"
