from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.middleware.auth import get_agente
from app.crud.conversaciones import crear_nota

router = APIRouter()


class NotaBody(BaseModel):
    contenido: str


@router.post("/api/conversaciones/{conv_id}/notas", status_code=201)
def post_nota(conv_id: str, body: NotaBody, agente=Depends(get_agente)):
    if not body.contenido:
        raise HTTPException(400, detail="contenido es requerido")
    nota_id = crear_nota(conv_id, body.contenido, agente)
    return {"success": True, "nota_id": nota_id}
