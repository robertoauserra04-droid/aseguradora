from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.middleware.auth import get_agente
from app.crud import etapas as crud

router = APIRouter()


class EtapaBody(BaseModel):
    label: Optional[str] = None
    color: Optional[str] = None


class OrdenBody(BaseModel):
    keys: List[str]


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
