from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.middleware.auth import get_agente
from app.crud.conversaciones import crear_cotizacion

router = APIRouter()


class CotizacionBody(BaseModel):
    aseguradora: str
    prima: Optional[float] = None
    moneda: Optional[str] = "MXN"
    cobertura: Optional[str] = None
    estado: Optional[str] = "cotizando"
    fecha_vencimiento: Optional[str] = None


@router.post("/api/conversaciones/{conv_id}/cotizaciones", status_code=201)
def post_cotizacion(conv_id: str, body: CotizacionBody, agente=Depends(get_agente)):
    if not body.aseguradora:
        raise HTTPException(400, detail="aseguradora es requerida")
    cotizacion_id = crear_cotizacion(conv_id, body.model_dump())
    return {"success": True, "cotizacion_id": cotizacion_id}
