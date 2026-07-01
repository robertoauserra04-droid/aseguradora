import os
import time
import logging
from datetime import datetime, timezone
from app.config.database import query
from app.config.env import OPENAI_API_KEY
from app.utils.detectors import detectar_tipo_seguro, menciona_seguros
from app import crud

logger = logging.getLogger(__name__)

# Segundos de espera para agrupar una ráfaga de mensajes del cliente antes de responder.
# Evita que 3 mensajes seguidos generen 3 respuestas; una sola respuesta cubre los 3.
BOT_DEBOUNCE_SEG = float(os.getenv("BOT_DEBOUNCE_SEG", "4"))


def _es_nombre_generico(nombre: str | None, phone: str) -> bool:
    """True si el nombre es vacío, el placeholder 'Cliente' o el propio teléfono."""
    if not nombre:
        return True
    n = nombre.strip()
    return n == "" or n.lower() == "cliente" or n == phone


def _extraer_nombre(raw_conv: dict, raw_msg: dict, phone: str) -> str:
    """Extrae el nombre de perfil del contacto probando las rutas que mandan
    Kapso y Meta Cloud API. Si ninguna trae un nombre real, devuelve el teléfono."""
    conv_kapso = raw_conv.get("kapso") or {}
    msg_kapso = raw_msg.get("kapso") or {}
    contactos = raw_conv.get("contacts") or []
    contacto0 = contactos[0] if contactos else {}

    candidatos = [
        (raw_conv.get("metadata") or {}).get("customer_name"),
        raw_conv.get("contact_name"),
        conv_kapso.get("contact_name"),
        msg_kapso.get("contact_name"),
        (contacto0.get("profile") or {}).get("name"),
        (raw_conv.get("profile") or {}).get("name"),
        raw_conv.get("username"),
    ]

    for c in candidatos:
        if c and isinstance(c, str) and c.strip() and c.strip() != phone:
            return c.strip()

    return phone


def _normalizar_payload(body: dict) -> tuple[dict, dict] | None:
    raw_msg = body.get("message", {})
    raw_conv = body.get("conversation", {})
    if not raw_msg or not raw_conv:
        return None

    content = (
        (raw_msg.get("text") or {}).get("body")
        or (raw_msg.get("kapso") or {}).get("content")
        or raw_msg.get("content", "")
    )
    direction = (raw_msg.get("kapso") or {}).get("direction") or raw_msg.get("direction", "inbound")
    # origin: cómo entró el mensaje al sistema.
    #   cloud_api    -> lo envió la propia app/bot vía la API de Kapso (ya guardado)
    #   business_app -> lo envió un humano desde la app de WhatsApp Business
    #   history_sync -> backfill de historial
    origin = (raw_msg.get("kapso") or {}).get("origin")
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

    customer_name = _extraer_nombre(raw_conv, raw_msg, phone)

    message = {"content": content, "direction": direction, "whatsapp_id": whatsapp_id,
               "msg_type": msg_type, "created_at": created_at, "origin": origin}
    conversation = {"phone_number": phone, "customer_name": customer_name}
    return message, conversation


def _sincronizar_cliente(phone: str, nombre: str, conv_id: str) -> None:
    """Crea/actualiza el registro en `clientes` y lo enlaza a la conversación.

    Así cada contacto de WhatsApp aparece en la sección Clientes con su teléfono
    y, en cuanto Kapso manda el nombre de perfil, con su nombre real (sin esperar
    al backfill de arranque). No pisa un nombre ya editado a mano.
    """
    r = query("SELECT id, nombre FROM clientes WHERE telefono = %s", [phone])
    if r.rows:
        cli_id = r.rows[0]["id"]
        actual = r.rows[0].get("nombre")
        if _es_nombre_generico(actual, phone) and not _es_nombre_generico(nombre, phone):
            query("UPDATE clientes SET nombre = %s, updated_at = NOW() WHERE id = %s", [nombre, cli_id])
    else:
        ins = query(
            """INSERT INTO clientes (nombre, telefono)
               VALUES (%s, %s)
               ON CONFLICT (telefono) DO NOTHING
               RETURNING id""",
            [nombre, phone],
        )
        cli_id = ins.rows[0]["id"] if ins.rows else query(
            "SELECT id FROM clientes WHERE telefono = %s", [phone]
        ).rows[0]["id"]

    query(
        "UPDATE conversaciones SET cliente_id = %s WHERE id = %s AND cliente_id IS NULL",
        [cli_id, conv_id],
    )


def _obtener_o_crear_conversacion(phone: str, nombre: str) -> str:
    # Solo se reusa una conversación ABIERTA. Si el cliente tenía su caso cerrado y vuelve a
    # escribir, se abre un caso NUEVO en 'inicio' (el cerrado queda intacto en el historial).
    r = query(
        """SELECT id, cliente_nombre FROM conversaciones
           WHERE cliente_whatsapp_id = %s AND closed_at IS NULL
           ORDER BY created_at DESC LIMIT 1""",
        [phone],
    )
    if r.rows:
        conv_id = str(r.rows[0]["id"])
        # Reactivar la conversación: si se había eliminado (activo=false) y vuelve a
        # escribir, debe reaparecer en el panel. Sin esto el mensaje se guardaría en
        # una conversación oculta y nunca se vería.
        query("UPDATE conversaciones SET activo = true WHERE id = %s AND activo = false", [conv_id])
        # Si el nombre guardado es genérico y ahora llega uno real, actualizarlo.
        # No se sobrescribe un nombre editado manualmente por un agente.
        actual = r.rows[0].get("cliente_nombre")
        if _es_nombre_generico(actual, phone) and not _es_nombre_generico(nombre, phone):
            query(
                "UPDATE conversaciones SET cliente_nombre = %s, updated_at = NOW() WHERE id = %s",
                [nombre, conv_id],
            )
    else:
        ins = query(
            """INSERT INTO conversaciones
                 (cliente_telefono, cliente_whatsapp_id, cliente_nombre, estado, bot_activo, requiere_respuesta, created_at, ultimo_mensaje_at)
               VALUES (%s, %s, %s, 'inicio', true, false, NOW(), NOW())
               RETURNING id""",
            [phone, phone, nombre],
        )
        conv_id = str(ins.rows[0]["id"])

    _sincronizar_cliente(phone, nombre, conv_id)
    return conv_id


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

    # Guardar mensaje si no existe.
    # Los salientes que envió la propia app/bot vía la API (origin=cloud_api) ya
    # quedaron guardados al enviarse; su eco por webhook se ignora para no duplicar.
    # Los salientes desde la app de WhatsApp Business (origin=business_app) SÍ se
    # guardan, porque son la única fuente de esos mensajes en el panel.
    es_duplicado = bool(message["whatsapp_id"] and crud.mensajes.ya_existe(message["whatsapp_id"]))
    es_eco_api = bool(message["direction"] != "inbound" and message["origin"] == "cloud_api")
    if not es_duplicado and not es_eco_api:
        requiere = bool(message["direction"] == "inbound" and "?" in (message["content"] or ""))
        autor = "cliente" if message["direction"] == "inbound" else "agente"
        nombre_autor = conversation["customer_name"] if message["direction"] == "inbound" else "Agente"

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
                "UPDATE conversaciones SET ultimo_mensaje_at = NOW(), updated_at = NOW(), requiere_respuesta = %s, ultimo_autor = 'cliente' WHERE id = %s",
                [requiere, conv_id],
            )
        else:
            query(
                "UPDATE conversaciones SET ultimo_mensaje_at = NOW(), updated_at = NOW(), requiere_respuesta = false, ultimo_autor = %s WHERE id = %s",
                [autor, conv_id],
            )
            # Pausa automática del bot cuando un agente humano responde
            if autor == "agente":
                query(
                    "UPDATE conversaciones SET bot_auto_pausado = true, agente_respondio_at = NOW() WHERE id = %s",
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


def _es_sobre_seguros(conv_id: str, contexto: dict) -> bool:
    """Con modo 'solo_seguros' activo, decide si el bot debe responder.

    Responde si la conversación ya tiene tipo_seguro detectado (ya hubo interés)
    o si alguno de los últimos mensajes del cliente menciona un seguro. En cualquier
    otro caso el bot se queda callado y el mensaje queda en el panel para un humano.
    """
    if not contexto.get("solo_seguros"):
        return True  # modo apagado → comportamiento de siempre
    r = query("SELECT tipo_seguro FROM conversaciones WHERE id = %s", [conv_id])
    if r.rows and r.rows[0].get("tipo_seguro"):
        return True  # conversación ya enganchada con un tipo de seguro
    # Si el bot ya respondió antes en esta conversación, ya está enganchada: continúa
    # aunque los mensajes de seguimiento no repitan una palabra de seguros.
    b = query(
        "SELECT 1 FROM mensajes WHERE conversacion_id = %s AND autor = 'bot' LIMIT 1",
        [conv_id],
    )
    if b.rows:
        return True
    # Se revisan los últimos mensajes del cliente (no solo el último): con el debounce
    # que agrupa ráfagas, "quiero un seguro" + "gracias" debe seguir enganchando.
    m = query(
        "SELECT contenido FROM mensajes WHERE conversacion_id = %s AND autor = 'cliente' "
        "ORDER BY timestamp_mensaje DESC LIMIT 5",
        [conv_id],
    )
    return any(menciona_seguros(row.get("contenido")) for row in m.rows)


def ejecutar_bot(conv_id: str) -> None:
    """Genera y envía la respuesta del bot. Se ejecuta como BackgroundTask (sync, en threadpool)."""
    try:
        cfg_r = query("SELECT activo_global, contexto FROM bot_config LIMIT 1")
        if not cfg_r.rows or not cfg_r.rows[0].get("activo_global"):
            return
        contexto = cfg_r.rows[0].get("contexto") or {}

        conv_r = query("SELECT bot_activo, bot_auto_pausado, agente_respondio_at, cliente_telefono FROM conversaciones WHERE id = %s", [conv_id])
        if not conv_r.rows:
            return
        conv = conv_r.rows[0]
        if conv.get("bot_activo") is False:
            return

        # Auto-pausa: el bot se detiene cuando un agente humano tomó la conversación.
        # Se reactiva cuando han pasado 48 h desde la última respuesta del agente.
        if conv.get("bot_auto_pausado"):
            respondio_at = conv.get("agente_respondio_at")
            if respondio_at:
                horas = (datetime.now(timezone.utc) - respondio_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
                if horas < 48:
                    logger.info("Bot omitido (auto-pausa agente): conv %s, %0.1f h desde respuesta del agente", conv_id, horas)
                    return
                else:
                    query("UPDATE conversaciones SET bot_auto_pausado = false, agente_respondio_at = NULL WHERE id = %s", [conv_id])
            else:
                # Sin timestamp de referencia → limpiar la pausa para no bloquear indefinidamente
                query("UPDATE conversaciones SET bot_auto_pausado = false WHERE id = %s", [conv_id])

        # Número excluido (ej. número personal del dueño) → el bot nunca responde
        from app.crud.bot import numero_excluido
        if numero_excluido(conv["cliente_telefono"]):
            logger.info("Bot omitido: %s está en la lista de excluidos", conv["cliente_telefono"])
            return

        # Modo "solo seguros": el bot solo responde si la conversación es sobre seguros
        if not _es_sobre_seguros(conv_id, contexto):
            logger.info("Bot omitido (modo solo-seguros): conv %s no es sobre seguros aún", conv_id)
            return

        # Anti-duplicados: agrupa la ráfaga de mensajes y reclama el turno de forma
        # atómica. Si otra tarea ya lo reclamó (mismo o más nuevo), esta se aborta.
        if not _reclamar_turno(conv_id):
            logger.info("Bot omitido (turno ya atendido / ráfaga agrupada): conv %s", conv_id)
            return

        # Re-verificar tras la espera: si el asesor humano intervino mientras el bot
        # "pensaba", el bot se calla (el guard inicial se evaluó con el estado previo).
        rp = query("SELECT bot_auto_pausado, bot_activo FROM conversaciones WHERE id = %s", [conv_id])
        if rp.rows and (rp.rows[0].get("bot_auto_pausado") or rp.rows[0].get("bot_activo") is False):
            logger.info("Bot omitido (asesor intervino durante la espera): conv %s", conv_id)
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
        "UPDATE conversaciones SET ultimo_mensaje_at = NOW(), updated_at = NOW(), requiere_respuesta = false, ultimo_autor = 'bot' WHERE id = %s",
        [conv_id],
    )


def _reclamar_turno(conv_id: str) -> bool:
    """Candado anti-duplicados ante ráfagas de mensajes o reintentos de webhook.

    1. Espera BOT_DEBOUNCE_SEG para que los mensajes que llegan casi juntos se
       agrupen (todas las tareas verán el mismo 'último mensaje del cliente').
    2. Reclama el turno de forma atómica con un UPDATE condicional: solo la tarea
       que ve el mensaje del cliente más reciente logra fijar bot_turno_respondido_at;
       las demás no obtienen fila y se abortan. Como el UPDATE toma lock de fila,
       funciona aunque haya varios procesos/workers.
    """
    if BOT_DEBOUNCE_SEG > 0:
        time.sleep(BOT_DEBOUNCE_SEG)

    ts_row = query(
        "SELECT MAX(timestamp_mensaje) AS ts FROM mensajes WHERE conversacion_id = %s AND autor = 'cliente'",
        [conv_id],
    )
    ts_cliente = ts_row.rows[0]["ts"] if ts_row.rows else None
    if not ts_cliente:
        return False

    claim = query(
        """UPDATE conversaciones
           SET bot_turno_respondido_at = %s
           WHERE id = %s
             AND (bot_turno_respondido_at IS NULL OR bot_turno_respondido_at < %s)
           RETURNING id""",
        [ts_cliente, conv_id, ts_cliente],
    )
    return len(claim.rows) > 0


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
