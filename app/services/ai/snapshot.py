from app.config.database import query
from app.config.env import GOOGLE_CALENDAR_ID


def build_snapshot(conversacion_id: str) -> dict:
    cfg_r = query("SELECT instrucciones, activo_global, contexto FROM bot_config WHERE id = 1")
    faq_r = query("SELECT pregunta, respuesta FROM bot_faq WHERE activo = true ORDER BY orden, created_at")
    msgs_r = query(
        """SELECT autor, contenido FROM mensajes
           WHERE conversacion_id = %s
           ORDER BY timestamp_mensaje DESC LIMIT 12""",
        [conversacion_id],
    )
    conv_r = query(
        "SELECT tipo_seguro, estado, cliente_nombre, cliente_email, cliente_telefono FROM conversaciones WHERE id = %s",
        [conversacion_id],
    )

    cfg = cfg_r.rows[0] if cfg_r.rows else None
    faqs = faq_r.rows
    mensajes = msgs_r.rows
    conversacion = conv_r.rows[0] if conv_r.rows else None

    slots_info = {"texto": "", "slots": []}
    if GOOGLE_CALENDAR_ID:
        try:
            from app.services.calendar.client import consultar_disponibilidad
            slots_info = consultar_disponibilidad()
        except Exception:
            pass

    return {"cfg": cfg, "faqs": faqs, "mensajes": mensajes, "conversacion": conversacion, "slots_info": slots_info}
