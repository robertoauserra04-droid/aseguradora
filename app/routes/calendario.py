from fastapi import APIRouter, Depends
from typing import Optional
from app.middleware.auth import get_agente
from app.crud.calendario import obtener_eventos

router = APIRouter()


@router.get("/api/calendario/eventos")
def eventos(start: Optional[str] = None, end: Optional[str] = None, agente=Depends(get_agente)):
    return obtener_eventos(start, end)
