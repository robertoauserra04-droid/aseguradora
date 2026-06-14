from app.config.database import query


def listar(filtros: dict) -> dict:
    estado = filtros.get("estado")
    estados = filtros.get("estados")
    tipo_seguro = filtros.get("tipo_seguro")
    agente_asignado = filtros.get("agente_asignado")
    requiere_respuesta = filtros.get("requiere_respuesta")
    search = filtros.get("search")
    limit = int(filtros.get("limit", 50))
    offset = int(filtros.get("offset", 0))
    sort_by = filtros.get("sort_by", "mas_reciente")

    conditions = ["c.activo = true"]
    params = []

    if estado:
        conditions.append("c.estado = %s")
        params.append(estado)
    elif estados:
        lista = [s.strip() for s in estados.split(",") if s.strip()]
        if lista:
            placeholders = ", ".join(["%s"] * len(lista))
            conditions.append(f"c.estado IN ({placeholders})")
            params.extend(lista)

    if tipo_seguro:
        conditions.append("c.tipo_seguro = %s")
        params.append(tipo_seguro)
    if agente_asignado:
        conditions.append("c.agente_asignado = %s")
        params.append(agente_asignado)
    if requiere_respuesta is not None:
        conditions.append("c.requiere_respuesta = %s")
        params.append(requiere_respuesta == "true")
    if search:
        conditions.append("(c.cliente_nombre ILIKE %s OR c.cliente_telefono ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = "WHERE " + " AND ".join(conditions)

    order_map = {
        "mas_reciente":  "c.ultimo_mensaje_at DESC NULLS LAST",
        "mas_urgente":   "CASE c.prioridad WHEN 'critica' THEN 0 WHEN 'alta' THEN 1 WHEN 'normal' THEN 2 WHEN 'baja' THEN 3 ELSE 4 END ASC",
        "sin_respuesta": "c.requiere_respuesta DESC, c.ultimo_mensaje_at ASC NULLS LAST",
    }
    order = order_map.get(sort_by, order_map["mas_reciente"])

    count_result = query(f"SELECT COUNT(*) as cnt FROM conversaciones c {where}", params)
    total = int(count_result.rows[0]["cnt"])

    data_result = query(
        f"""SELECT
              c.id, c.cliente_nombre, c.cliente_telefono, c.tipo_seguro,
              c.estado, c.agente_asignado, c.agente_nombre,
              c.requiere_respuesta, c.prioridad, c.dias_en_estado,
              c.created_at, c.updated_at, c.ultimo_mensaje_at,
              m.contenido AS ultimo_mensaje_contenido,
              m.timestamp_mensaje AS ultimo_mensaje_timestamp,
              m.autor AS ultimo_mensaje_autor
            FROM conversaciones c
            LEFT JOIN LATERAL (
              SELECT contenido, timestamp_mensaje, autor
              FROM mensajes
              WHERE conversacion_id = c.id
              ORDER BY timestamp_mensaje DESC
              LIMIT 1
            ) m ON true
            {where}
            ORDER BY {order}
            LIMIT %s OFFSET %s""",
        params + [limit, offset],
    )

    conversaciones = []
    for r in data_result.rows:
        conversaciones.append({
            "id": str(r["id"]),
            "cliente_nombre": r["cliente_nombre"],
            "cliente_telefono": r["cliente_telefono"],
            "tipo_seguro": r["tipo_seguro"],
            "estado": r["estado"],
            "agente_asignado": str(r["agente_asignado"]) if r["agente_asignado"] else None,
            "agente_nombre": r["agente_nombre"],
            "requiere_respuesta": r["requiere_respuesta"],
            "prioridad": r["prioridad"],
            "dias_en_estado": r["dias_en_estado"],
            "ultimo_mensaje": {
                "contenido": r["ultimo_mensaje_contenido"],
                "timestamp": r["ultimo_mensaje_timestamp"],
                "autor": r["ultimo_mensaje_autor"],
            } if r["ultimo_mensaje_contenido"] else None,
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })

    return {"conversaciones": conversaciones, "total": total, "limit": limit, "offset": offset}


def obtener_por_id(conv_id: str) -> dict | None:
    r = query("SELECT * FROM conversaciones WHERE id = %s", [conv_id])
    if not r.rows:
        return None

    mensajes, cotizaciones, notas, historial = (
        query(
            """SELECT id, autor, nombre_autor, contenido, tipo_mensaje,
                      timestamp_mensaje, palabras_clave, sentimiento, requiere_respuesta
               FROM mensajes WHERE conversacion_id = %s ORDER BY timestamp_mensaje ASC""",
            [conv_id],
        ),
        query(
            """SELECT id, aseguradora, prima, moneda, cobertura, estado,
                      fecha_cotizacion, fecha_vencimiento
               FROM cotizaciones WHERE conversacion_id = %s ORDER BY created_at DESC""",
            [conv_id],
        ),
        query(
            """SELECT id, agente_nombre, contenido, created_at
               FROM notas_internas WHERE conversacion_id = %s ORDER BY created_at DESC""",
            [conv_id],
        ),
        query(
            """SELECT estado_anterior, estado_nuevo, realizado_por, nombre_quien_realizo, motivo, timestamp
               FROM cambios_estado_historico WHERE conversacion_id = %s ORDER BY timestamp ASC""",
            [conv_id],
        ),
    )

    cliente_id = r.rows[0].get("cliente_id")
    polizas = []
    if cliente_id:
        polizas = query(
            """SELECT id, numero_poliza, ramo, aseguradora, estado,
                      fecha_inicio, fecha_vencimiento, suma_asegurada, prima,
                      moneda, forma_pago, comision_pct, comision_monto, notas
               FROM polizas WHERE cliente_id = %s
               ORDER BY fecha_vencimiento ASC NULLS LAST, created_at DESC""",
            [cliente_id],
        ).rows
        for p in polizas:
            p["id"] = str(p["id"])

    return {
        "conversacion": r.rows[0],
        "mensajes": mensajes.rows,
        "cotizaciones": cotizaciones.rows,
        "notas": notas.rows,
        "historial_estados": historial.rows,
        "polizas": polizas,
    }


def asegurar_cliente_id(conv_id: str) -> str | None:
    """Devuelve el cliente_id de la conversación; lo crea/enlaza por teléfono si falta.
    Permite gestionar seguros (pólizas) desde el chat aunque la conversación sea vieja."""
    r = query("SELECT cliente_id, cliente_telefono, cliente_nombre FROM conversaciones WHERE id = %s", [conv_id])
    if not r.rows:
        return None
    if r.rows[0].get("cliente_id"):
        return str(r.rows[0]["cliente_id"])

    telefono = r.rows[0].get("cliente_telefono")
    nombre = r.rows[0].get("cliente_nombre") or "Cliente"

    cli = query("SELECT id FROM clientes WHERE telefono = %s", [telefono])
    if cli.rows:
        cli_id = cli.rows[0]["id"]
    else:
        ins = query(
            """INSERT INTO clientes (nombre, telefono)
               VALUES (%s, %s) ON CONFLICT (telefono) DO NOTHING RETURNING id""",
            [nombre, telefono],
        )
        cli_id = ins.rows[0]["id"] if ins.rows else query(
            "SELECT id FROM clientes WHERE telefono = %s", [telefono]
        ).rows[0]["id"]

    query("UPDATE conversaciones SET cliente_id = %s WHERE id = %s", [cli_id, conv_id])
    return str(cli_id)


def eliminar(conv_id: str) -> bool:
    """Borrado suave: la conversación deja de aparecer en kanban/lista (activo=false).
    No se borra el historial; se puede recuperar reactivándola en la BD."""
    r = query(
        "UPDATE conversaciones SET activo = false, updated_at = NOW() WHERE id = %s RETURNING id",
        [conv_id],
    )
    return len(r.rows) > 0


def cambiar_estado(conv_id: str, estado_nuevo: str, motivo: str, agente: dict) -> None:
    r = query("SELECT estado FROM conversaciones WHERE id = %s", [conv_id])
    if not r.rows:
        return None
    estado_actual = r.rows[0]["estado"]

    query(
        """UPDATE conversaciones
           SET estado = %s, estado_anterior = %s, fecha_cambio_estado = NOW(),
               motivo_cambio_estado = %s, updated_at = NOW()
           WHERE id = %s""",
        [estado_nuevo, estado_actual, motivo, conv_id],
    )

    agente_nombre = agente.get("nombre", "Sistema")
    agente_id = agente.get("id", "sistema")

    query(
        """INSERT INTO cambios_estado_historico
             (conversacion_id, estado_anterior, estado_nuevo, realizado_por, nombre_quien_realizo, motivo)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        [conv_id, estado_actual, estado_nuevo, agente_id, agente_nombre, motivo],
    )
    return estado_actual


def crear_nota(conv_id: str, contenido: str, agente: dict) -> str:
    agente_nombre = agente.get("nombre", "Agente")
    agente_id = agente.get("id")
    r = query(
        """INSERT INTO notas_internas (conversacion_id, agente_id, agente_nombre, contenido)
           VALUES (%s, %s, %s, %s) RETURNING id""",
        [conv_id, agente_id, agente_nombre, contenido],
    )
    return str(r.rows[0]["id"])


def crear_cotizacion(conv_id: str, datos: dict) -> str:
    r = query(
        """INSERT INTO cotizaciones
             (conversacion_id, aseguradora, prima, moneda, cobertura, estado, fecha_vencimiento)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        [
            conv_id,
            datos["aseguradora"],
            datos.get("prima"),
            datos.get("moneda", "MXN"),
            datos.get("cobertura"),
            datos.get("estado", "cotizando"),
            datos.get("fecha_vencimiento"),
        ],
    )
    return str(r.rows[0]["id"])


def editar_cliente(conv_id: str, datos: dict) -> None:
    cliente_nombre = datos.get("cliente_nombre")
    cliente_email = datos.get("cliente_email")

    # Sólo cambia el tipo de seguro: se permite null/"" para dejarlo "Sin tipo".
    if "tipo_seguro" in datos and not cliente_nombre:
        query(
            "UPDATE conversaciones SET tipo_seguro = %s, updated_at = NOW() WHERE id = %s",
            [datos["tipo_seguro"] or None, conv_id],
        )
        return

    query(
        "UPDATE conversaciones SET cliente_nombre = %s, cliente_email = %s, updated_at = NOW() WHERE id = %s",
        [cliente_nombre.strip(), cliente_email or None, conv_id],
    )


def toggle_bot(conv_id: str, bot_activo: bool) -> None:
    query("UPDATE conversaciones SET bot_activo = %s WHERE id = %s", [bot_activo, conv_id])
