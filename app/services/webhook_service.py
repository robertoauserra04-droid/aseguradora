import logging
from datetime import datetime, timezone
from app.config.database import query
from app.config.env import OPENAI_API_KEY
from app.utils.detectors import detectar_tipo_seguro
from app import crud

logger = logging.getLogger(__name__)


def _normalizar_payload(body: dict) -> tuple[dict, dict] | None:
    raw_msg = body.get("message", {})
    raw_conv = body.get("conversation", {})
    if not raw_msg or not raw_conv:
        return None

    content = (
        (raw_msg.get("text") or {}).get("body")
        or raw_msg.get("content", "")
    )
    direction = (raw_msg.get("kapso") or {}).get("direction") or raw_msg.get("direction", "inbound")
    whatsapp_id = raw_msg.get("id") or raw_msg.get("whatsapp_message_id")
    msg_type = raw_msg.get("type") or raw_msg.get("message_type", "text")

    ts = raw_msg.get("timestamp")
    if ts:
        created_at = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    elif raw_msg.get("created_at"):
        created_at = datetime.fromisoformat(raw_msg["created_at"])
    else:
        created_at = datetime.now(timezone.utc)

    raw_phone = (raw_conv.get("phone_number") or raw_msg.get("from", "")).replace(" ", "")
    phone = raw_phone if raw_phone.startswith("+") else f"+{raw_phone}"

    customer_name = (raw_conv.get("metadata") or {}).get("customer_name") or raw_conv.get("contact_name") or raw_conv.get("username") or "Cliente"

    message = {"content": content, "direction": direction, "whatsapp_id": whatsapp_id,
               "msg_type": msg_type, "created_at": created_at}
    conversation = {"phone_number": phone, "customer_name": customer_name}
    return message, conversation


def _obtener_o_crear_conversacion(phone: str, nombre: str) -> str:
    r = query("SELECT id FROM conversaciones WHERE cliente_whatsapp_id = %s", [phone])
    if r.rows:
        return str(r.rows[0]["id"])

    ins = query(
        """INSERT INTO conversaciones
             (cliente_telefono, cliente_whatsapp_id, cliente_nombre, estado, bot_activo, requiere_respuesta, created_at, ultimo_mensaje_at)
           VALUES (%s, %s, %s, 'inicio', true, false, NOW(), NOW())
           RETURNING id""",
        [phone, phone, nombre],
    )
    return str(ins.rows[0]["id"])


def procesar_mensaje_entrante(body: dict, idempotency_key: str = None,
                              event_type: str = "whatsapp.message.received") -> dict:
    """Procesa un mensaje entrante de forma SÍNCRONA.

    Devuelve dict con `disparar_bot` (bool) para que la ruta lo agende como
    BackgroundTask — así no bloquea el event loop ni se pierde por GC.
    """
    from app.crud import webhooks as crud_webhooks

    # Idempotencia
    if idempotency_key and crud_webhooks.ya_existe(idempotency_key):
        return {"status": "ok", "duplicado": True, "disparar_bot": False}

    parsed = _normalizar_payload(body)
    if parsed is None:
        raise ValueError("Payload inválido: faltan message o conversation")

    message, conversation = parsed
    if not conversation["phone_number"]:
        raise ValueError("Payload inválido: falta phone_number")

    conv_id = _obtener_o_crear_conversacion(conversation["phone_number"], conversation["customer_name"])

    # Guardar mensaje si no existe
    es_duplicado = bool(message["whatsapp_id"] and crud.mensajes.ya_existe(message["whatsapp_id"]))
    if not es_duplicado:
        requiere = bool(message["direction"] == "inbound" and "?" in (message["content"] or ""))
        autor = "cliente" if message["direction"] == "inbound" else "agente"
        nombre_autor = "Cliente" if message["direction"] == "inbound" else "Agente"

        crud.mensajes.guardar(
            conv_id=conv_id,
            autor=autor,
            nombre_autor=nombre_autor,
            contenido=message["content"] or "",
            tipo_mensaje=message["msg_type"],
            whatsapp_id=message["whatsapp_id"],
            timestamp=message["created_at"],
            requiere_respuesta=requiere,
        )

        tipo = detectar_tipo_seguro(message["content"])
        if tipo:
            query(
                "UPDATE conversaciones SET tipo_seguro = %s WHERE id = %s AND tipo_seguro IS NULL",
                [tipo, conv_id],
            )

        if message["direction"] == "inbound":
            query(
                "UPDATE conversaciones SET ultimo_mensaje_at = NOW(), updated_at = NOW(), requiere_respuesta = %s WHERE id = %s",
                [requiere, conv_id],
            )
        else:
            query(
                "UPDATE conversaciones SET ultimo_mensaje_at = NOW(), updated_at = NOW(), requiere_respuesta = false WHERE id = %s",
                [conv_id],
            )

    if idempotency_key:
        crud_webhooks.registrar(idempotency_key, event_type)

    disparar_bot = (
        message["direction"] == "inbound"
        and body.get("test") is not True
        and not es_duplicado
        and bool(OPENAI_API_KEY)
    )

    return {"status": "ok", "conversacion_id": conv_id, "disparar_bot": disparar_bot}


def ejecutar_bot(conv_id: str) -> None:
    """Genera y envía la respuesta del bot. Se ejecuta como BackgroundTask (sync, en threadpool)."""
    try:
        cfg_r = query("SELECT activo_global FROM bot_config LIMIT 1")
        if not cfg_r.rows or not cfg_r.rows[0].get("activo_global"):
            return

        conv_r = query("SELECT bot_activo, cliente_telefono FROM conversaciones WHERE id = %s", [conv_id])
        if not conv_r.rows:
            return
        conv = conv_r.rows[0]
        if conv.get("bot_activo") is False:
            return

        from app.services.ai.index import generar_respuesta
        texto = generar_respuesta(conv_id)
        if not texto:
            return

        from app.services.whatsapp.sender import enviar_mensaje
        enviar_mensaje(conv["cliente_telefono"], texto)

        query(
            """INSERT INTO mensajes
                 (conversacion_id, autor, nombre_autor, contenido, tipo_mensaje, timestamp_mensaje, requiere_respuesta)
               VALUES (%s, 'bot', 'Bot Carguill', %s, 'text', NOW(), false)""",
            [conv_id, texto],
        )
        query(
            "UPDATE conversaciones SET ultimo_mensaje_at = NOW(), updated_at = NOW(), requiere_respuesta = false WHERE id = %s",
            [conv_id],
        )
        logger.info("Respuesta del bot enviada a %s", conv["cliente_telefono"])
    except Exception as e:
        logger.error("Error al generar/enviar respuesta del bot: %s", e)
