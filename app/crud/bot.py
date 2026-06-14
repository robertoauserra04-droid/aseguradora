import json
from app.config.database import query


def get_config() -> dict:
    r = query("SELECT instrucciones, activo_global, contexto FROM bot_config WHERE id = 1")
    row = r.rows[0] if r.rows else {"instrucciones": "", "activo_global": False, "contexto": {}}
    row["contexto"] = row.get("contexto") or {}
    return row


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
