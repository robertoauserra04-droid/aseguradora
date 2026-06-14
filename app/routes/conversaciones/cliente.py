from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.middleware.auth import get_agente
from app.crud.conversaciones import editar_cliente

router = APIRouter()

TIPOS_VALIDOS = {"vida", "auto", "medical", "daño", "viaje"}


class ClienteBody(BaseModel):
    cliente_nombre: Optional[str] = None
    cliente_email: Optional[str] = None
    tipo_seguro: Optional[str] = None
    tipos_seguro: Optional[List[str]] = None


@router.patch("/api/conversaciones/{conv_id}/cliente")
def patch_cliente(conv_id: str, body: ClienteBody, agente=Depends(get_agente)):
    # exclude_unset conserva un tipo_seguro explícito en null (para dejar "Sin tipo");
    # exclude_none lo descartaría y no se podría limpiar el tipo.
    datos = body.model_dump(exclude_unset=True)

    # Varios tipos de seguro (lista). Validar cada uno.
    if "tipos_seguro" in datos and "cliente_nombre" not in datos:
        tipos = datos["tipos_seguro"] or []
        if any(t not in TIPOS_VALIDOS for t in tipos):
            raise HTTPException(400, detail="Tipo de seguro no válido")
        editar_cliente(conv_id, datos)
        return {"success": True}

    # Sólo cambia el tipo de seguro (un valor): se permite null/"" para "Sin tipo".
    if "tipo_seguro" in datos and "cliente_nombre" not in datos:
        if datos["tipo_seguro"] and datos["tipo_seguro"] not in TIPOS_VALIDOS:
            raise HTTPException(400, detail="Tipo de seguro no válido")
        editar_cliente(conv_id, datos)
        return {"success": True}

    if not body.cliente_nombre:
        raise HTTPException(400, detail="cliente_nombre es requerido")

    editar_cliente(conv_id, datos)
    return {"success": True}
