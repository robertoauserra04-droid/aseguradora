from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.middleware.auth import get_agente
from app.crud.conversaciones import cambiar_estado
from app.utils.estados import es_estado_valido

router = APIRouter()


class EstadoBody(BaseModel):
    estado_nuevo: str
    motivo: str


def _evento_calendario(estado_nuevo: str, conv_id: str) -> None:
    try:
        from app.config.database import query
        from app.services.calendar.client import crear_evento_etapa
        r = query(
            "SELECT cliente_nombre, cliente_telefono, tipo_seguro FROM conversaciones WHERE id = %s",
            [conv_id],
        )
        if r.rows:
            crear_evento_etapa(estado_nuevo, r.rows[0])
    except Exception:
        pass


@router.post("/api/conversaciones/{conv_id}/estado")
def post_estado(conv_id: str, body: EstadoBody, background: BackgroundTasks, agente=Depends(get_agente)):
    if not es_estado_valido(body.estado_nuevo):
        raise HTTPException(400, detail=f"Estado inválido: {body.estado_nuevo}")

    estado_anterior = cambiar_estado(conv_id, body.estado_nuevo, body.motivo, agente)
    if estado_anterior is None:
        raise HTTPException(404, detail="Conversación no encontrada")

    background.add_task(_evento_calendario, body.estado_nuevo, conv_id)

    return {"success": True, "conversacion_id": conv_id}
