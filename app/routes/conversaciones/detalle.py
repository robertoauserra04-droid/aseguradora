from fastapi import APIRouter, Depends, HTTPException
from app.middleware.auth import get_agente
from app.crud.conversaciones import obtener_por_id, eliminar

router = APIRouter()


@router.get("/api/conversaciones/{conv_id}")
def get_conversacion(conv_id: str, agente=Depends(get_agente)):
    resultado = obtener_por_id(conv_id)
    if not resultado:
        raise HTTPException(404, detail="Conversación no encontrada")
    return resultado


@router.delete("/api/conversaciones/{conv_id}")
def delete_conversacion(conv_id: str, agente=Depends(get_agente)):
    if not eliminar(conv_id):
        raise HTTPException(404, detail="Conversación no encontrada")
    return {"status": "ok"}
