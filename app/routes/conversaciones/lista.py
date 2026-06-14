from fastapi import APIRouter, Depends, Request
from app.middleware.auth import get_agente
from app.crud.conversaciones import listar

router = APIRouter()


@router.get("/api/conversaciones")
def get_conversaciones(request: Request, agente=Depends(get_agente)):
    params = dict(request.query_params)
    return listar(params)
