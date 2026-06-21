from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from app.middleware.auth import get_agente
from app.crud.conversaciones import listar, crear_manual
from app.utils.estados import es_estado_valido

router = APIRouter()


class NuevaConvBody(BaseModel):
    cliente_id: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_telefono: Optional[str] = None
    estado: str = "inicio"
    nota: Optional[str] = None


@router.get("/api/conversaciones")
def get_conversaciones(request: Request, agente=Depends(get_agente)):
    params = dict(request.query_params)
    return listar(params)


@router.post("/api/conversaciones", status_code=201)
def post_conversacion(body: NuevaConvBody, agente=Depends(get_agente)):
    if not es_estado_valido(body.estado):
        raise HTTPException(400, detail=f"Fase inválida: {body.estado}")
    try:
        conv_id = crear_manual(body.model_dump(), agente)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    return {"success": True, "conversacion_id": conv_id}
