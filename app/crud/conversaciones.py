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
    incluir_cerradas = str(filtros.get("incluir_cerradas", "")).lower() in ("true", "1", "yes")

    conditions = ["c.activo = true"]
    params = []

    # Por defecto solo conversaciones abiertas (el tablero). La lista/historial pasa
    # incluir_cerradas=true para ver también los casos ya cerrados.
    if not incluir_cerradas:
        conditions.append("c.closed_at IS NULL")

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
              c.id, c.cliente_nombre, c.cliente_telefono, c.tipo_seguro, c.tipos_seguro,
              c.estado, c.agente_asignado, c.agente_nombre,
              c.requiere_respuesta, c.prioridad, c.dias_en_estado,
              c.created_at, c.updated_at, c.ultimo_mensaje_at, c.closed_at,
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
            "tipos_seguro": r.get("tipos_seguro") or [],
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
            "closed_at": r["closed_at"],
        })

    return {"conversaciones": conversaciones, "total": total, "limit": limit, "offset": offset}


def obtener_por_id(conv_id: str) -> dict | None:
    r = query("SELECT * FROM conversaciones WHERE id = %s", [conv_id])
    if not r.rows:
        return None

    mensajes, cotizaciones, notas, historial = (
        # Conversación COMPLETA del cliente: todos sus mensajes a lo largo de todos sus casos
        # (la conversación de WhatsApp es continua aunque cada caso sea una fila distinta).
        query(
            """SELECT m.id, m.autor, m.nombre_autor, m.contenido, m.tipo_mensaje,
                      m.timestamp_mensaje, m.palabras_clave, m.sentimiento, m.requiere_respuesta
               FROM mensajes m
               JOIN conversaciones c2 ON c2.id = m.conversacion_id
               WHERE c2.cliente_telefono = (SELECT cliente_telefono FROM conversaciones WHERE id = %s)
               ORDER BY m.timestamp_mensaje ASC""",
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


def cerrar(conv_id: str, agente: dict) -> str | None:
    """Cierra el caso: deja de aparecer en el tablero y queda en la lista como 'cerrada'.
    Congela `closed_at` (para la métrica de tiempo de conversación) y registra el cambio.
    Devuelve el estado anterior, o None si la conversación no existe."""
    r = query("SELECT estado FROM conversaciones WHERE id = %s", [conv_id])
    if not r.rows:
        return None
    estado_actual = r.rows[0]["estado"]

    query(
        """UPDATE conversaciones
           SET estado = 'cerrada', estado_anterior = %s, closed_at = NOW(),
               fecha_cambio_estado = NOW(), updated_at = NOW()
           WHERE id = %s""",
        [estado_actual, conv_id],
    )

    agente_nombre = agente.get("nombre", "Sistema")
    agente_id = agente.get("id", "sistema")
    query(
        """INSERT INTO cambios_estado_historico
             (conversacion_id, estado_anterior, estado_nuevo, realizado_por, nombre_quien_realizo, motivo)
           VALUES (%s, %s, 'cerrada', %s, %s, %s)""",
        [conv_id, estado_actual, agente_id, agente_nombre, "Conversación cerrada"],
    )
    return estado_actual


def crear_manual(datos: dict, agente: dict) -> str:
    """Crea un caso manualmente desde el panel (botón 'Nuevo' del kanban).

    Acepta un cliente existente (`cliente_id`) o uno nuevo (`cliente_nombre` + `cliente_telefono`).
    Coloca el caso en la fase indicada (`estado`) y, si viene `nota`, la registra.
    """
    cliente_id = datos.get("cliente_id")
    estado = datos.get("estado") or "inicio"

    if cliente_id:
        cli = query("SELECT id, nombre, telefono FROM clientes WHERE id = %s", [cliente_id])
        if not cli.rows:
            raise ValueError("Cliente no encontrado")
        nombre = cli.rows[0]["nombre"] or "Cliente"
        telefono = cli.rows[0]["telefono"]
        if not telefono:
            raise ValueError("El cliente no tiene teléfono")
    else:
        nombre = (datos.get("cliente_nombre") or "Cliente").strip() or "Cliente"
        telefono = (datos.get("cliente_telefono") or "").strip()
        if not telefono:
            raise ValueError("El teléfono es requerido para un cliente nuevo")
        existente = query("SELECT id FROM clientes WHERE telefono = %s", [telefono])
        if existente.rows:
            cliente_id = str(existente.rows[0]["id"])
        else:
            ins_cli = query(
                "INSERT INTO clientes (nombre, telefono) VALUES (%s, %s) RETURNING id",
                [nombre, telefono],
            )
            cliente_id = str(ins_cli.rows[0]["id"])

    ins = query(
        """INSERT INTO conversaciones
             (cliente_telefono, cliente_whatsapp_id, cliente_nombre, estado, cliente_id,
              bot_activo, requiere_respuesta, created_at, ultimo_mensaje_at)
           VALUES (%s, %s, %s, %s, %s, true, false, NOW(), NOW())
           RETURNING id""",
        [telefono, telefono, nombre, estado, cliente_id],
    )
    conv_id = str(ins.rows[0]["id"])

    nota = (datos.get("nota") or "").strip()
    if nota:
        crear_nota(conv_id, nota, agente)

    return conv_id


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

    # Varios tipos de seguro. tipo_seguro = principal (primer tipo) para compatibilidad.
    if "tipos_seguro" in datos and not cliente_nombre:
        tipos = datos["tipos_seguro"] or []
        principal = tipos[0] if tipos else None
        query(
            "UPDATE conversaciones SET tipos_seguro = %s, tipo_seguro = %s, updated_at = NOW() WHERE id = %s",
            [tipos, principal, conv_id],
        )
        return

    # Sólo cambia el tipo de seguro (un valor): se permite null/"" para "Sin tipo".
    if "tipo_seguro" in datos and not cliente_nombre:
        tipo = datos["tipo_seguro"] or None
        query(
            "UPDATE conversaciones SET tipo_seguro = %s, tipos_seguro = %s, updated_at = NOW() WHERE id = %s",
            [tipo, ([tipo] if tipo else []), conv_id],
        )
        return

    nombre = cliente_nombre.strip()
    query(
        "UPDATE conversaciones SET cliente_nombre = %s, cliente_email = %s, updated_at = NOW() WHERE id = %s",
        [nombre, cliente_email or None, conv_id],
    )
    # Propagar el nombre/email al registro de `clientes` enlazado para que el cambio
    # se vea también en la sección Clientes (y el webhook no lo pise por ser manual).
    query(
        """UPDATE clientes SET nombre = %s, email = COALESCE(%s, email), updated_at = NOW()
           WHERE id = (SELECT cliente_id FROM conversaciones WHERE id = %s)""",
        [nombre, cliente_email or None, conv_id],
    )


def toggle_bot(conv_id: str, bot_activo: bool) -> None:
    query("UPDATE conversaciones SET bot_activo = %s WHERE id = %s", [bot_activo, conv_id])
