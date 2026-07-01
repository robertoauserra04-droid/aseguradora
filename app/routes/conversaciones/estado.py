import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.middleware.auth import get_agente
from app.crud.conversaciones import cambiar_estado, cerrar
from app.utils.estados import es_estado_valido

logger = logging.getLogger(__name__)
router = APIRouter()


class EstadoBody(BaseModel):
    estado_nuevo: str
    motivo: Optional[str] = None


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
    except Exception as e:
        logger.warning("[Estado] No se pudo crear el evento de calendario (conv %s): %s", conv_id, e)


def _notificacion_fase(estado_nuevo: str, conv_id: str) -> None:
    """Envía WhatsApp al cliente si la nueva fase tiene una notificación activa configurada.

    Usa siempre un template de WhatsApp aprobado por Meta para garantizar entrega
    incluso cuando han pasado más de 24 h desde el último mensaje del cliente.

    Template esperado (4 variables en el body):
        {{1}} = nombre del cliente
        {{2}} = nombre de la empresa
        {{3}} = nombre de la fase
        {{4}} = mensaje personalizado configurado por fase en el panel
    """
    try:
        from app.config.database import query
        from app.crud.etapas import obtener_notificacion
        from app.services.whatsapp.sender import enviar_template

        notif = obtener_notificacion(estado_nuevo)
        if not notif or not notif.get("activo"):
            return

        conv_r = query(
            "SELECT cliente_nombre, cliente_telefono, agente_nombre FROM conversaciones WHERE id = %s",
            [conv_id],
        )
        if not conv_r.rows:
            return
        conv = conv_r.rows[0]

        cfg_r = query("SELECT contexto, whatsapp_template_notif FROM bot_config WHERE id = 1")
        empresa = ""
        template_name = "actualizacion_seguro_fase"
        if cfg_r.rows:
            ctx = cfg_r.rows[0].get("contexto") or {}
            empresa = (ctx.get("empresa") or "").strip()
            template_name = (cfg_r.rows[0].get("whatsapp_template_notif") or "actualizacion_seguro_fase").strip()

        etapa_r = query("SELECT label FROM etapas WHERE key = %s", [estado_nuevo])
        etapa_label = etapa_r.rows[0]["label"] if etapa_r.rows else estado_nuevo

        telefono = conv.get("cliente_telefono", "")
        nombre = conv.get("cliente_nombre") or "cliente"
        asesor = conv.get("agente_nombre") or "un asesor"

        # El mensaje personalizado del panel puede incluir {asesor} además de texto libre
        mensaje_personalizado = (notif["mensaje_template"]
                                 .replace("{nombre}", nombre)
                                 .replace("{empresa}", empresa)
                                 .replace("{etapa}", etapa_label)
                                 .replace("{asesor}", asesor))

        # params = [{{1}}, {{2}}, {{3}}, {{4}}] del template en Meta
        enviar_template(telefono, template_name, [nombre, empresa, etapa_label, mensaje_personalizado])
    except Exception as e:
        logger.warning("[Estado] No se pudo enviar la notificación de fase (conv %s): %s", conv_id, e)


@router.post("/api/conversaciones/{conv_id}/estado")
def post_estado(conv_id: str, body: EstadoBody, background: BackgroundTasks, agente=Depends(get_agente)):
    if not es_estado_valido(body.estado_nuevo):
        raise HTTPException(400, detail=f"Estado inválido: {body.estado_nuevo}")

    estado_anterior = cambiar_estado(conv_id, body.estado_nuevo, body.motivo or "", agente)
    if estado_anterior is None:
        raise HTTPException(404, detail="Conversación no encontrada")

    background.add_task(_evento_calendario, body.estado_nuevo, conv_id)
    background.add_task(_notificacion_fase, body.estado_nuevo, conv_id)

    return {"success": True, "conversacion_id": conv_id}


@router.post("/api/conversaciones/{conv_id}/cerrar")
def post_cerrar(conv_id: str, agente=Depends(get_agente)):
    estado_anterior = cerrar(conv_id, agente)
    if estado_anterior is None:
        raise HTTPException(404, detail="Conversación no encontrada")
    return {"success": True, "conversacion_id": conv_id}
