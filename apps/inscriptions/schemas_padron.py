from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

# Respuesta genérica de error/estado
class Mensaje(BaseModel):
    detalle: str

# === Inscripción a Carrera ===

class InscCarreraCreateIn(BaseModel):
    estudiante_id: int = Field(..., ge=1, description="ID del estudiante (rol ESTUDIANTE)")
    carrera_id: int = Field(..., ge=1, description="ID de la carrera")

class InscripcionCarreraOut(BaseModel):
    id: int
    estudiante_id: int
    carrera_id: int
    estado_legajo: str
    condicion: str

    model_config = ConfigDict(from_attributes=True)

# === Checklist (Legajo del alumno) ===

class LegajoItemOut(BaseModel):
    id: int
    nombre: str = Field(..., description="Nombre del ítem de legajo (p.ej. DNI, Título Secundario)")
    obligatorio: bool
    completo: bool
    observaciones: str

    # Este modelo se arma a mano (join) en el router, no directo del ORM

class LegajoToggleIn(BaseModel):
    completo: bool
    observaciones: Optional[str] = ""

# === Catálogo de ítems por carrera ===

class LegajoItemTipoOut(BaseModel):
    id: int
    carrera_id: int
    nombre: str
    obligatorio: bool

    model_config = ConfigDict(from_attributes=True)
