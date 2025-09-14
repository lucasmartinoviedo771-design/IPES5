# apps/academics/schemas.py
from pydantic import BaseModel
from typing import List

class CarreraItem(BaseModel):
    id: int
    nombre: str
    plan_id: int
    plan_txt: str

class CorrelatividadesOut(BaseModel):
    regulares: List[int]
    aprobadas: List[int]