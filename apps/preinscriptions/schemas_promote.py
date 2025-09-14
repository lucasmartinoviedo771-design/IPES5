from typing import Optional
from pydantic import BaseModel, Field


class PrePromoteIn(BaseModel):
    """
    Parámetros de control para la promoción.
    Si no pasás nada, usa defaults seguros:
    - username = DNI
    - password temporal aleatoria
    - carrera se toma de la preinscripción
    """
    username: Optional[str] = Field(None, description="Username a crear/usar; por defecto, DNI")
    force_email: Optional[str] = Field(None, description="Email a forzar si el de la preinscripción está vacío/incorrecto")
    password: Optional[str] = Field(None, description="Password explícito. Si no se pasa, se genera uno temporal")
    activar_usuario: bool = Field(default=True, description="Si se crea usuario, marcar is_active=True")
    set_rol_estudiante: bool = Field(default=True, description="Forzar rol ESTUDIANTE si corresponde")
    confirmar_carrera_id: Optional[int] = Field(None, description="Si se quiere confirmar que coincide con pre.carrera_id")


class PrePromoteOut(BaseModel):
    preinscripcion_id: int
    estudiante_id: int
    username: str
    temp_password: Optional[str] = None
    inscripcion_carrera_id: int
    condicion_inicial: str
    legajo_estado_inicial: str
    mensaje: str


class Mensaje(BaseModel):
    detalle: str
