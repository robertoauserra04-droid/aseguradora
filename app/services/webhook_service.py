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


def _hora_monterrey() -> int:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Monterrey")).hour
    except Exception:
        return datetime.now(timezone.utc).hour


def _fuera_de_horario(contexto: dict) -> bool:
    if not contexto.get("solo_horario"):
        return False
    try:
        inicio = int(contexto.get("hora_inicio", 9))
        fin = int(contexto.get("hora_fin", 18))
    except (ValueError, TypeError):
        return False
    return not (inicio <= _hora_monterrey() < fin)


def ejecutar_bot(conv_id: str) -> None:
    """Genera y envía la respuesta del bot. Se ejecuta como BackgroundTask (sync, en threadpool)."""
    try:
        cfg_r = query("SELECT activo_global, contexto FROM bot_config LIMIT 1")
        if not cfg_r.rows or not cfg_r.rows[0].get("activo_global"):
            return
        contexto = cfg_r.rows[0].get("contexto") or {}

        conv_r = query("SELECT bot_activo, cliente_telefono FROM conversaciones WHERE id = %s", [conv_id])
        if not conv_r.rows:
            return
        conv = conv_r.rows[0]
        if conv.get("bot_activo") is False:
            return

        # Número excluido (ej. número personal del dueño) → el bot nunca responde
        from app.crud.bot import numero_excluido
        if numero_excluido(conv["cliente_telefono"]):
            logger.info("Bot omitido: %s está en la lista de excluidos", conv["cliente_telefono"])
            return

        from app.services.whatsapp.sender import enviar_mensaje

        # Fuera del horario de atención
        if _fuera_de_horario(contexto):
            msg_fuera = (contexto.get("mensaje_fuera_horario") or "").strip()
            if msg_fuera and not _bot_respondio_reciente(conv_id):
                enviar_mensaje(conv["cliente_telefono"], msg_fuera)
                _guardar_respuesta_bot(conv_id, msg_fuera)
            return

        from app.services.ai.index import generar_respuesta
        texto = generar_respuesta(conv_id)
        if not texto:
            return

        enviar_mensaje(conv["cliente_telefono"], texto)
        _guardar_respuesta_bot(conv_id, texto)
        logger.info("Respuesta del bot enviada a %s", conv["cliente_telefono"])
    except Exception as e:
        logger.error("Error al generar/enviar respuesta del bot: %s", e)


def _guardar_respuesta_bot(conv_id: str, texto: str) -> None:
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


def _bot_respondio_reciente(conv_id: str, horas: int = 4) -> bool:
    """Evita repetir el mensaje de fuera de horario en cada mensaje del cliente."""
    r = query(
        """SELECT 1 FROM mensajes
           WHERE conversacion_id = %s AND autor = 'bot'
             AND timestamp_mensaje > NOW() - make_interval(hours => %s)
           LIMIT 1""",
        [conv_id, horas],
    )
    return len(r.rows) > 0
