from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class EstadoCursadaEnum(str, Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    REGULAR = "REGULAR"
    LIBRE = "LIBRE"
    BAJA = "BAJA"

class InscripcionCursadaCreateIn(BaseModel):
    """
    Si el usuario autenticado es ESTUDIANTE, se ignora estudiante_id (se usa el del token).
    Para SECRETARIA/BEDEL/ADMIN, estudiante_id es obligatorio.
    """
    comision_id: int = Field(..., ge=1)
    estudiante_id: Optional[int] = Field(None, ge=1)

class InscripcionCursadaOut(BaseModel):
    id: int
    estudiante_id: int
    comision_id: int
    estado: EstadoCursadaEnum
    fecha_inscripcion: datetime
    aviso: Optional[str] = None

    class Config:
        from_attributes = True

class Mensaje(BaseModel):
    detalle: str
