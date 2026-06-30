from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.middleware.auth import get_agente
from app.config.database import query
from app.crud import etapas as crud

router = APIRouter()


class EtapaBody(BaseModel):
    label: Optional[str] = None
    color: Optional[str] = None


class OrdenBody(BaseModel):
    keys: List[str]


class NotificacionBody(BaseModel):
    mensaje_template: str
    activo: bool = True


@router.get("/api/etapas")
def listar(agente=Depends(get_agente)):
    return crud.listar()


@router.post("/api/etapas", status_code=201)
def crear(body: EtapaBody, agente=Depends(get_agente)):
    try:
        return crud.crear(body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.put("/api/etapas/orden")
def reordenar(body: OrdenBody, agente=Depends(get_agente)):
    crud.reordenar(body.keys)
    return {"ok": True}


@router.put("/api/etapas/{key}")
def actualizar(key: str, body: EtapaBody, agente=Depends(get_agente)):
    if not crud.actualizar(key, body.model_dump(exclude_none=True)):
        raise HTTPException(404, detail="Fase no encontrada o sin cambios")
    return {"ok": True}


@router.delete("/api/etapas/{key}")
def eliminar(key: str, agente=Depends(get_agente)):
    r = crud.eliminar(key)
    if not r["ok"]:
        mensajes = {
            "no_existe": "La fase no existe",
            "es_cerrada": "No se puede eliminar la fase Cerrada",
            "con_conversaciones": f"La fase tiene {r.get('conversaciones', 0)} conversaciones; muévelas antes de eliminarla",
            "ultima_fase": "Debe quedar al menos una fase",
        }
        raise HTTPException(409, detail=mensajes.get(r["motivo"], "No se puede eliminar"))
    return {"ok": True}


# ── Notificaciones por fase ──────────────────────────────────────────────────

@router.get("/api/etapas/notificaciones")
def listar_notificaciones(agente=Depends(get_agente)):
    return crud.listar_notificaciones()


@router.put("/api/etapas/notificaciones/{key}")
def upsert_notificacion(key: str, body: NotificacionBody, agente=Depends(get_agente)):
    if not query("SELECT 1 FROM etapas WHERE key = %s", [key]).rows:
        raise HTTPException(404, detail="Fase no encontrada")
    crud.upsert_notificacion(key, body.mensaje_template, body.activo)
    return {"ok": True}


@router.delete("/api/etapas/notificaciones/{key}")
def eliminar_notificacion(key: str, agente=Depends(get_agente)):
    if not crud.eliminar_notificacion(key):
        raise HTTPException(404, detail="Notificación no encontrada")
    return {"ok": True}
