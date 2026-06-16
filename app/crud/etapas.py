import re
from app.config.database import query


def _slug(texto: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (texto or "").lower().strip()).strip("_")
    return s or "fase"


def listar() -> list:
    r = query(
        "SELECT key, label, color, orden, es_cerrada FROM etapas WHERE activo = true ORDER BY orden ASC, label ASC"
    )
    return r.rows


def crear(datos: dict) -> dict:
    label = (datos.get("label") or "").strip()
    if not label:
        raise ValueError("El nombre de la fase es requerido")
    # key única a partir del nombre
    base = _slug(label)
    key = base
    i = 2
    while query("SELECT 1 FROM etapas WHERE key = %s", [key]).rows:
        key = f"{base}_{i}"
        i += 1
    color = datos.get("color") or "#3B82F6"
    orden_r = query("SELECT COALESCE(MAX(orden), 0) + 1 AS o FROM etapas WHERE es_cerrada = false")
    orden = int(orden_r.rows[0]["o"])
    query(
        "INSERT INTO etapas (key, label, color, orden, es_cerrada) VALUES (%s, %s, %s, %s, false)",
        [key, label, color, orden],
    )
    return {"key": key, "label": label, "color": color, "orden": orden}


def actualizar(key: str, datos: dict) -> bool:
    sets, params = [], []
    if "label" in datos and (datos["label"] or "").strip():
        sets.append("label = %s"); params.append(datos["label"].strip())
    if "color" in datos and datos["color"]:
        sets.append("color = %s"); params.append(datos["color"])
    if not sets:
        return False
    params.append(key)
    r = query(f"UPDATE etapas SET {', '.join(sets)} WHERE key = %s RETURNING key", params)
    return len(r.rows) > 0


def reordenar(keys: list) -> None:
    for i, k in enumerate(keys):
        query("UPDATE etapas SET orden = %s WHERE key = %s AND es_cerrada = false", [i + 1, k])


def contar_conversaciones(key: str) -> int:
    r = query("SELECT COUNT(*) AS c FROM conversaciones WHERE estado = %s AND activo = true", [key])
    return int(r.rows[0]["c"])


def eliminar(key: str) -> dict:
    """Devuelve {ok: bool, motivo: str}. No borra la fase 'cerrada' ni fases con
    conversaciones activas, ni deja menos de 1 fase abierta."""
    row = query("SELECT es_cerrada FROM etapas WHERE key = %s", [key])
    if not row.rows:
        return {"ok": False, "motivo": "no_existe"}
    if row.rows[0]["es_cerrada"]:
        return {"ok": False, "motivo": "es_cerrada"}
    n = contar_conversaciones(key)
    if n > 0:
        return {"ok": False, "motivo": "con_conversaciones", "conversaciones": n}
    abiertas = query("SELECT COUNT(*) AS c FROM etapas WHERE es_cerrada = false AND activo = true")
    if int(abiertas.rows[0]["c"]) <= 1:
        return {"ok": False, "motivo": "ultima_fase"}
    query("DELETE FROM etapas WHERE key = %s", [key])
    return {"ok": True}
