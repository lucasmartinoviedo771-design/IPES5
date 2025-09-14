from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class Mensaje(BaseModel):
    detalle: str


# Títulos superiores (lista de hasta 2)
class TituloSuperiorIn(BaseModel):
    titulo: str
    establecimiento: str
    fecha_egreso: Optional[str] = None  # ISO date
    localidad: Optional[str] = ""
    provincia: Optional[str] = ""
    pais: Optional[str] = ""


class PreinscripcionCreateIn(BaseModel):
    carrera_id: int

    # Personales
    cuil: str
    dni: str = Field(..., min_length=7, max_length=8)
    apellido: str
    nombres: str
    fecha_nacimiento: str  # ISO (yyyy-mm-dd)
    estado_civil: Optional[str] = ""
    loc_nacimiento: Optional[str] = ""
    prov_nacimiento: Optional[str] = ""
    pais_nacimiento: Optional[str] = ""
    nacionalidad: Optional[str] = ""

    # Contacto
    domicilio: str
    tel_fijo: Optional[str] = ""
    tel_movil: Optional[str] = ""
    email: str
    emergencia_telefono: Optional[str] = ""
    emergencia_parentesco: Optional[str] = ""

    # Laboral
    trabaja: bool = False
    empleador: Optional[str] = ""
    horario_trabajo: Optional[str] = ""
    domicilio_trabajo: Optional[str] = ""

    # Secundario
    secu_titulo: Optional[str] = ""
    secu_establecimiento: Optional[str] = ""
    secu_fecha_egreso: Optional[str] = None  # ISO
    secu_localidad: Optional[str] = ""
    secu_provincia: Optional[str] = ""
    secu_pais: Optional[str] = ""

    # Documentación (mutuamente excluyentes)
    doc_titulo_secundario: bool = False
    doc_certificado_tramite: bool = False
    doc_adeuda_materias: bool = False
    doc_adeuda_detalle: Optional[str] = ""
    doc_adeuda_escuela: Optional[str] = ""
    # Adicional (lo deja False el estudiante)
    doc_declaracion_jurada: bool = False
    # Certificación Docente
    doc_incumbencias: bool = False

    # Superiores
    titulos_superiores: List[TituloSuperiorIn] = Field(default_factory=list)


class PreinscripcionOut(BaseModel):
    id: int
    estado: str
    carrera_id: int
    apellido: str
    nombres: str
    dni: str
    email: str

    model_config = ConfigDict(from_attributes=True)
