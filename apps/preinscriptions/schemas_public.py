# apps/preinscriptions/schemas_public.py
from typing import Optional, List
from pydantic import BaseModel

class ContactoOut(BaseModel):
    domicilio: Optional[str] = None
    tel_fijo: Optional[str] = None
    tel_movil: Optional[str] = None
    email: Optional[str] = None
    emergencia_tel: Optional[str] = None
    emergencia_parentesco: Optional[str] = None

class LaboralOut(BaseModel):
    trabaja: Optional[bool] = None
    empleador: Optional[str] = None
    horario_trabajo: Optional[str] = None
    domicilio_trabajo: Optional[str] = None

class SecundarioOut(BaseModel):
    titulo_obtenido: Optional[str] = None
    establecimiento: Optional[str] = None
    fecha_egreso: Optional[str] = None
    localidad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None

class TerciarioOut(BaseModel):
    titulo_obtenido: Optional[str] = None
    establecimiento: Optional[str] = None
    fecha_egreso: Optional[str] = None
    localidad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None

class DocumentacionOut(BaseModel):
    adeuda_materias: bool = False
    adeuda_detalle: Optional[str] = None
    adeuda_escuela: Optional[str] = None
    cert_titulo_en_tramite: bool = False
    titulo_secundario: bool = False
    dj_nota_compromiso: bool = False
    incumbencias: bool = False  # para Certificación Docente

class FotoOut(BaseModel):
    url: Optional[str] = None

class PreinscripcionOut(BaseModel):
    id: int
    carrera_id: int
    carrera_nombre: str

    dni: str
    cuil: Optional[str] = None
    apellido: Optional[str] = None
    nombres: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    estado_civil: Optional[str] = None
    lugar_nac_localidad: Optional[str] = None
    lugar_nac_provincia: Optional[str] = None
    lugar_nac_pais: Optional[str] = None
    nacionalidad: Optional[str] = None

    contacto: ContactoOut
    laboral: LaboralOut
    secundario: SecundarioOut
    terciarios: List[TerciarioOut] = []
    documentacion: DocumentacionOut
    foto: FotoOut
