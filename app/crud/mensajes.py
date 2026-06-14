from datetime import datetime
from app.config.database import query


def guardar(conv_id: str, autor: str, nombre_autor: str, contenido: str,
            tipo_mensaje: str = "text", whatsapp_id: str = None,
            timestamp: datetime = None, requiere_respuesta: bool = False) -> None:
    query(
        """INSERT INTO mensajes
             (conversacion_id, autor, nombre_autor, contenido, tipo_mensaje,
              whatsapp_message_id, timestamp_mensaje, requiere_respuesta)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        [conv_id, autor, nombre_autor, contenido, tipo_mensaje,
         whatsapp_id, timestamp or datetime.utcnow(), requiere_respuesta],
    )


def obtener_historial(conv_id: str, limite: int = 12) -> list:
    r = query(
        """SELECT autor, contenido FROM mensajes
           WHERE conversacion_id = %s
           ORDER BY timestamp_mensaje DESC LIMIT %s""",
        [conv_id, limite],
    )
    return r.rows


def ya_existe(whatsapp_message_id: str) -> bool:
    r = query("SELECT id FROM mensajes WHERE whatsapp_message_id = %s", [whatsapp_message_id])
    return len(r.rows) > 0
