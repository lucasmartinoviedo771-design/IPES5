from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string

class UserProfile(AbstractUser):
    api_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True, blank=False)

    class Rol(models.TextChoices):
        ESTUDIANTE = 'ESTUDIANTE', 'Estudiante'
        DOCENTE = 'DOCENTE', 'Docente'
        SECRETARIA = 'SECRETARIA', 'Secretaría'
        BEDEL = 'BEDEL', 'Bedel'
        TUTOR = 'TUTOR', 'Tutor'
        ADMIN = 'ADMIN', 'Administrador'

    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.ESTUDIANTE,
        verbose_name='Rol'
    )
    nombre_completo = models.CharField(max_length=255, blank=True, verbose_name='Nombre Completo')
    dni = models.CharField(max_length=20, unique=True, null=True, blank=True)
    foto_4x4 = models.ImageField(
        upload_to="users/foto4x4/",
        null=True,
        blank=True,
        help_text="Foto tipo carnet 4x4 del estudiante"
    )

    def save(self, *args, **kwargs):
        if not self.nombre_completo:
            self.nombre_completo = f"{self.last_name}, {self.first_name}".strip()
        super().save(*args, **kwargs)

    def ensure_api_key(self, save=True):
        if not self.api_key:
            self.api_key = get_random_string(40)
            if save:
                self.save(update_fields=["api_key"])
        return self.api_key
