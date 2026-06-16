from app.config.database import query


def crear(datos: dict) -> dict:
    r = query(
        """INSERT INTO citas (conversacion_id, cliente_id, titulo, motivo, inicio, fin, google_event_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           RETURNING id""",
        [
            datos.get("conversacion_id"),
            datos.get("cliente_id"),
            datos.get("titulo"),
            datos.get("motivo"),
            datos["inicio"],
            datos.get("fin"),
            datos.get("google_event_id"),
        ],
    )
    return {"id": str(r.rows[0]["id"])}


def listar_rango(start: str = None, end: str = None) -> list:
    cond, params = ["c.estado <> 'cancelada'"], []
    if start:
        cond.append("c.inicio >= %s"); params.append(start)
    if end:
        cond.append("c.inicio <= %s"); params.append(end)
    where = "WHERE " + " AND ".join(cond)
    r = query(
        f"""SELECT c.id, c.titulo, c.motivo, c.inicio, c.fin, c.estado, c.conversacion_id,
                   COALESCE(cl.nombre, conv.cliente_nombre) AS cliente_nombre
            FROM citas c
            LEFT JOIN clientes cl ON cl.id = c.cliente_id
            LEFT JOIN conversaciones conv ON conv.id = c.conversacion_id
            {where}
            ORDER BY c.inicio ASC""",
        params,
    )
    return r.rows


def eliminar(cita_id: str) -> bool:
    r = query("DELETE FROM citas WHERE id = %s RETURNING id", [cita_id])
    return len(r.rows) > 0
