from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.middleware.auth import get_agente
from app.crud import citas as crud

router = APIRouter()


class CitaBody(BaseModel):
    inicio: str
    fin: Optional[str] = None
    titulo: Optional[str] = None
    motivo: Optional[str] = None
    conversacion_id: Optional[str] = None
    cliente_id: Optional[str] = None


@router.post("/api/citas", status_code=201)
def crear(body: CitaBody, agente=Depends(get_agente)):
    datos = body.model_dump()
    if not datos.get("titulo"):
        datos["titulo"] = "Cita"
    try:
        return crud.crear(datos)
    except Exception:
        raise HTTPException(500, detail="Error al crear la cita")


@router.delete("/api/citas/{cita_id}")
def eliminar(cita_id: str, agente=Depends(get_agente)):
    if not crud.eliminar(cita_id):
        raise HTTPException(404, detail="Cita no encontrada")
    return {"ok": True}
