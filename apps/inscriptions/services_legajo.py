# apps/inscriptions/services_legajo.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from django.db import transaction

from .models import InscripcionCarrera, LegajoItem

@dataclass
class LegajoRecalcResult:
    inscripcion: InscripcionCarrera
    items_actualizados: int
    legajo_estado: str
    condicion: str

def _const_or(default: str, enum_cls, name: str) -> str:
    # si enum no existe o el miembro no existe, usa default
    try:
        val = getattr(enum_cls, name)
        if isinstance(val, tuple):
            return val[0]
        return val
    except Exception:
        return default

@transaction.atomic
def update_items_and_recompute(inscripcion_id: int, updates: Iterable[dict]) -> LegajoRecalcResult:
    insc = InscripcionCarrera.objects.select_for_update().get(id=inscripcion_id)

    updated = 0
    # Aplica updates (solo dentro de la misma inscripción)
    for u in updates:
        item = LegajoItem.objects.select_for_update().get(id=u["id"], inscripcion=insc)
        changed = False
        if item.cumplido != bool(u["cumplido"]):
            item.cumplido = bool(u["cumplido"])
            changed = True
        if "observacion" in u:
            obs = u["observacion"] or ""
            if item.observacion != obs:
                item.observacion = obs
                changed = True
        if changed:
            item.save(update_fields=["cumplido", "observacion"])
            updated += 1

    # Recalcular estado del legajo (completo si TODOS cumplidos)
    qs = LegajoItem.objects.filter(inscripcion=insc)
    total = qs.count()
    cumplidos = qs.filter(cumplido=True).count()
    completo = (total > 0 and cumplidos == total)

    # Determinar strings tolerantes
    legajo_completo = _const_or("COMPLETO", getattr(InscripcionCarrera, "LegajoEstado", object), "COMPLETO")
    legajo_incompleto = _const_or("INCOMPLETO", getattr(InscripcionCarrera, "LegajoEstado", object), "INCOMPLETO")
    cond_regular = _const_or("REGULAR", getattr(InscripcionCarrera, "EstadoAlumno", object), "REGULAR")
    cond_condicionado = _const_or("CONDICIONADO", getattr(InscripcionCarrera, "EstadoAlumno", object), "CONDICIONADO")

    nuevo_legajo = legajo_completo if completo else legajo_incompleto
    nueva_cond = cond_regular if completo else cond_condicionado

    fields = []
    if hasattr(insc, "legajo_estado") and insc.legajo_estado != nuevo_legajo:
        insc.legajo_estado = nuevo_legajo
        fields.append("legajo_estado")
    if hasattr(insc, "condicion") and insc.condicion != nueva_cond:
        insc.condicion = nueva_cond
        fields.append("condicion")
    if fields:
        insc.save(update_fields=fields)

    return LegajoRecalcResult(
        inscripcion=insc,
        items_actualizados=updated,
        legajo_estado=nuevo_legajo,
        condicion=nueva_cond,
    )

def recompute_only(inscripcion_id: int) -> LegajoRecalcResult:
    insc = InscripcionCarrera.objects.select_for_update().get(id=inscripcion_id)
    qs = LegajoItem.objects.filter(inscripcion=insc)
    total = qs.count()
    cumplidos = qs.filter(cumplido=True).count()
    completo = (total > 0 and cumplidos == total)

    legajo_completo = _const_or("COMPLETO", getattr(InscripcionCarrera, "LegajoEstado", object), "COMPLETO")
    legajo_incompleto = _const_or("INCOMPLETO", getattr(InscripcionCarrera, "LegajoEstado", object), "INCOMPLETO")
    cond_regular = _const_or("REGULAR", getattr(InscripcionCarrera, "EstadoAlumno", object), "REGULAR")
    cond_condicionado = _const_or("CONDICIONADO", getattr(InscripcionCarrera, "EstadoAlumno", object), "CONDICIONADO")

    nuevo_legajo = legajo_completo if completo else legajo_incompleto
    nueva_cond = cond_regular if completo else cond_condicionado

    fields = []
    if hasattr(insc, "legajo_estado") and insc.legajo_estado != nuevo_legajo:
        insc.legajo_estado = nuevo_legajo
        fields.append("legajo_estado")
    if hasattr(insc, "condicion") and insc.condicion != nueva_cond:
        insc.condicion = nueva_cond
        fields.append("condicion")
    if fields:
        insc.save(update_fields=fields)

    return LegajoRecalcResult(
        inscripcion=insc,
        items_actualizados=0,
        legajo_estado=nuevo_legajo,
        condicion=nueva_cond,
    )