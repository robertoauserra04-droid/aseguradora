from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.middleware.auth import get_agente
from app.crud import bot as crud

router = APIRouter()


class BotConfigBody(BaseModel):
    instrucciones: Optional[str] = None
    activo_global: Optional[bool] = None
    contexto: Optional[dict] = None


class FaqBody(BaseModel):
    pregunta: str
    respuesta: str


class BotToggleBody(BaseModel):
    bot_activo: bool


@router.get("/api/bot/config")
def get_config(agente=Depends(get_agente)):
    return crud.get_config()


@router.put("/api/bot/config")
def update_config(body: BotConfigBody, agente=Depends(get_agente)):
    crud.update_config(body.model_dump(exclude_none=True))
    return {"ok": True}


@router.get("/api/bot/faq")
def list_faq(agente=Depends(get_agente)):
    return crud.list_faq()


@router.post("/api/bot/faq")
def create_faq(body: FaqBody, agente=Depends(get_agente)):
    if not body.pregunta or not body.respuesta:
        raise HTTPException(400, detail="Faltan pregunta o respuesta")
    return crud.create_faq(body.pregunta, body.respuesta)


@router.delete("/api/bot/faq/{faq_id}")
def delete_faq(faq_id: str, agente=Depends(get_agente)):
    crud.delete_faq(faq_id)
    return {"ok": True}


@router.patch("/api/conversaciones/{conv_id}/bot")
def toggle_bot(conv_id: str, body: BotToggleBody, agente=Depends(get_agente)):
    from app.crud.conversaciones import toggle_bot as crud_toggle
    crud_toggle(conv_id, body.bot_activo)
    return {"ok": True, "bot_activo": body.bot_activo}
