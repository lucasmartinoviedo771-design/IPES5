# apps/preinscriptions/schemas_patch.py
from typing import Optional
from pydantic import BaseModel, Field

class PreinscripcionPatchIn(BaseModel):
    # Datos de contacto (correcciones típicas)
    email: Optional[str] = Field(None, description="Correo del aspirante")
    tel_movil: Optional[str] = Field(None, description="Teléfono móvil")
    tel_fijo: Optional[str] = Field(None, description="Teléfono fijo")
    domicilio: Optional[str] = Field(None, description="Domicilio actual")

    # Documentación (ajustes mínimos en etapa de revisión)
    doc_adeuda_materias: Optional[bool] = None
    doc_adeuda_detalle: Optional[str] = None
    doc_adeuda_escuela: Optional[str] = None
    doc_cert_titulo_tramite: Optional[bool] = None
    doc_titulo_secundario: Optional[bool] = None
    doc_dj_nota_compromiso: Optional[bool] = None
    doc_incumbencias: Optional[bool] = None  # para "Certificación Docente"

    # Acción de gestión
    marcar_revisado: Optional[bool] = Field(
        None, description="Si true, marca la preinscripción como revisada"
    )
