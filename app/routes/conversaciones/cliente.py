from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.middleware.auth import get_agente
from app.crud.conversaciones import editar_cliente

router = APIRouter()

TIPOS_VALIDOS = {"vida", "auto", "medical", "daño", "viaje"}


class ClienteBody(BaseModel):
    cliente_nombre: Optional[str] = None
    cliente_email: Optional[str] = None
    tipo_seguro: Optional[str] = None


@router.patch("/api/conversaciones/{conv_id}/cliente")
def patch_cliente(conv_id: str, body: ClienteBody, agente=Depends(get_agente)):
    datos = body.model_dump(exclude_none=True)

    if "tipo_seguro" in datos and not body.cliente_nombre:
        if datos["tipo_seguro"] and datos["tipo_seguro"] not in TIPOS_VALIDOS:
            raise HTTPException(400, detail="Tipo de seguro no válido")
        editar_cliente(conv_id, datos)
        return {"success": True}

    if not body.cliente_nombre:
        raise HTTPException(400, detail="cliente_nombre es requerido")

    editar_cliente(conv_id, datos)
    return {"success": True}
