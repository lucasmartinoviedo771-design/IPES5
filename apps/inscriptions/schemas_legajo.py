# apps/inscriptions/schemas_legajo.py
from typing import List, Optional
from pydantic import BaseModel, Field

# ==== ya existente (se conserva) ====
class LegajoItemUpdateIn(BaseModel):
    id: int = Field(..., description="ID del LegajoItem a actualizar")
    cumplido: bool = Field(..., description="Marca si el item está cumplido")
    observacion: Optional[str] = Field(None, description="Observación opcional")

class LegajoEstadoOut(BaseModel):
    inscripcion_id: int
    items_actualizados: int
    legajo_estado: str
    condicion: str

# ==== NUEVO: salida detallada de legajo ====
class LegajoItemTipoOut(BaseModel):
    id: int
    codigo: Optional[str] = None
    nombre: str

class LegajoItemOut(BaseModel):
    id: int
    tipo: LegajoItemTipoOut
    cumplido: bool
    observacion: Optional[str] = None

class LegajoDetalleOut(BaseModel):
    inscripcion_id: int
    legajo_estado: str
    condicion: str
    total: int
    cumplidos: int
    items: List[LegajoItemOut]

class LegajoRecomputeOut(BaseModel):
    inscripcion_id: int
    total: int
    cumplidos: int
    legajo_estado: str
    condicion: str
