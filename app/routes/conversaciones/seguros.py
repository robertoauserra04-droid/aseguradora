from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.middleware.auth import get_agente
from app.crud.conversaciones import asegurar_cliente_id, obtener_por_id
from app.crud import polizas as crud_polizas

router = APIRouter()


class SeguroBody(BaseModel):
    ramo: Optional[str] = None
    aseguradora: Optional[str] = None
    estado: Optional[str] = "vigente"
    numero_poliza: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    suma_asegurada: Optional[float] = None
    prima: Optional[float] = None
    moneda: Optional[str] = "MXN"
    forma_pago: Optional[str] = "anual"
    comision_pct: Optional[float] = 0
    notas: Optional[str] = None


@router.get("/api/conversaciones/{conv_id}/seguros")
def listar_seguros(conv_id: str, agente=Depends(get_agente)):
    detalle = obtener_por_id(conv_id)
    if not detalle:
        raise HTTPException(404, detail="Conversación no encontrada")
    return {"seguros": detalle.get("polizas", [])}


@router.post("/api/conversaciones/{conv_id}/seguros", status_code=201)
def crear_seguro(conv_id: str, body: SeguroBody, agente=Depends(get_agente)):
    cliente_id = asegurar_cliente_id(conv_id)
    if not cliente_id:
        raise HTTPException(404, detail="Conversación no encontrada")
    datos = body.model_dump()
    datos["cliente_id"] = cliente_id
    datos["conversacion_id"] = conv_id
    try:
        return crud_polizas.crear(datos)
    except Exception:
        raise HTTPException(500, detail="Error al crear el seguro")
