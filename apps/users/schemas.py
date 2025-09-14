# apps/users/schemas.py
from pydantic import BaseModel

class EstudianteResumen(BaseModel):
    id: int
    nombre_completo: str
    dni: str
    email: str

    class Config:
        from_attributes = True