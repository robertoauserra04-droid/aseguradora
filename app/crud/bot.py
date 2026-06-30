import json
from app.config.database import query


def get_config() -> dict:
    r = query("SELECT instrucciones, activo_global, contexto, calendar_id, drive_folder_id, whatsapp_template_notif, google_email, updated_at FROM bot_config WHERE id = 1")
    row = r.rows[0] if r.rows else {"instrucciones": "", "activo_global": False, "contexto": {}, "calendar_id": None, "drive_folder_id": None, "whatsapp_template_notif": "actualizacion_seguro_fase", "google_email": None, "updated_at": None}
    row["contexto"] = row.get("contexto") or {}
    if not row.get("whatsapp_template_notif"):
        row["whatsapp_template_notif"] = "actualizacion_seguro_fase"
    return row


def reset_config() -> None:
    """Limpia la configuración del bot (instrucciones y contexto) a valores vacíos.
    No cambia activo_global para no apagar el bot por accidente."""
    query("UPDATE bot_config SET instrucciones = '', contexto = '{}', updated_at = NOW() WHERE id = 1")


def update_config(datos: dict) -> None:
    sets = ["updated_at = NOW()"]
    params = []

    if "instrucciones" in datos:
        sets.append("instrucciones = %s")
        params.append(datos["instrucciones"])
    if "activo_global" in datos:
        sets.append("activo_global = %s")
        params.append(bool(datos["activo_global"]))
    if "contexto" in datos:
        sets.append("contexto = %s")
        params.append(json.dumps(datos["contexto"]))
    if "calendar_id" in datos:
        sets.append("calendar_id = %s")
        params.append(datos["calendar_id"] or None)
    if "drive_folder_id" in datos:
        sets.append("drive_folder_id = %s")
        params.append(datos["drive_folder_id"] or None)
    if "whatsapp_template_notif" in datos:
        sets.append("whatsapp_template_notif = %s")
        params.append((datos["whatsapp_template_notif"] or "actualizacion_seguro_fase").strip())

    query(f"UPDATE bot_config SET {', '.join(sets)} WHERE id = 1", params)


def list_faq() -> list:
    r = query("SELECT * FROM bot_faq WHERE activo = true ORDER BY orden, created_at")
    return r.rows


def create_faq(pregunta: str, respuesta: str) -> dict:
    r = query(
        "INSERT INTO bot_faq (pregunta, respuesta) VALUES (%s, %s) RETURNING *",
        [pregunta, respuesta],
    )
    return r.rows[0]


def delete_faq(faq_id: str) -> None:
    query("UPDATE bot_faq SET activo = false WHERE id = %s", [faq_id])


# ── Números excluidos (el bot nunca responde a estos) ──

def _normalizar_numero(numero: str) -> str:
    numero = (numero or "").replace(" ", "").replace("-", "")
    return numero if numero.startswith("+") else f"+{numero}"


def list_excluidos() -> list:
    r = query("SELECT id, numero, motivo, created_at FROM bot_numeros_excluidos ORDER BY created_at DESC")
    for row in r.rows:
        row["id"] = str(row["id"])
    return r.rows


def add_excluido(numero: str, motivo: str = None) -> dict:
    r = query(
        """INSERT INTO bot_numeros_excluidos (numero, motivo)
           VALUES (%s, %s)
           ON CONFLICT (numero) DO UPDATE SET motivo = EXCLUDED.motivo
           RETURNING id, numero, motivo, created_at""",
        [_normalizar_numero(numero), motivo],
    )
    r.rows[0]["id"] = str(r.rows[0]["id"])
    return r.rows[0]


def delete_excluido(excluido_id: str) -> bool:
    r = query("DELETE FROM bot_numeros_excluidos WHERE id = %s RETURNING id", [excluido_id])
    return len(r.rows) > 0


def numero_excluido(telefono: str) -> bool:
    r = query("SELECT 1 FROM bot_numeros_excluidos WHERE numero = %s", [_normalizar_numero(telefono)])
    return len(r.rows) > 0
