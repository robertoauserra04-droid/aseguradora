from app.config.database import query

COLORS = {
    "poliza_vigente":     "#10B981",
    "poliza_vencimiento": "#EF4444",
    "cotizacion":         "#F97316",
    "tramite":            "#3B82F6",
    "renovacion":         "#EF4444",
}


def obtener_eventos(start: str = None, end: str = None) -> list:
    eventos = []

    # Pólizas: fecha inicio
    params_inicio = []
    extra_inicio = ""
    if start:
        extra_inicio += " AND fecha_inicio_poliza >= %s"
        params_inicio.append(start)
    if end:
        extra_inicio += " AND fecha_inicio_poliza <= %s"
        params_inicio.append(end)

    r = query(
        f"""SELECT id, cliente_nombre, tipo_seguro, numero_poliza, fecha_inicio_poliza
            FROM conversaciones
            WHERE fecha_inicio_poliza IS NOT NULL AND activo = true{extra_inicio}
            ORDER BY fecha_inicio_poliza""",
        params_inicio,
    )
    for row in r.rows:
        tipo = row.get("tipo_seguro", "")
        eventos.append({
            "id": f"poliza-inicio-{row['id']}",
            "title": f"Inicio póliza: {row['cliente_nombre']}" + (f" ({tipo})" if tipo else ""),
            "start": row["fecha_inicio_poliza"],
            "color": COLORS["poliza_vigente"],
            "extendedProps": {"tipo": "poliza_inicio", "conversacion_id": str(row["id"]), "numero_poliza": row.get("numero_poliza")},
        })

    # Pólizas: fecha vencimiento
    params_venc = []
    extra_venc = ""
    if start:
        extra_venc += " AND fecha_vencimiento_poliza >= %s"
        params_venc.append(start)
    if end:
        extra_venc += " AND fecha_vencimiento_poliza <= %s"
        params_venc.append(end)

    r = query(
        f"""SELECT id, cliente_nombre, tipo_seguro, numero_poliza, fecha_vencimiento_poliza,
                   fecha_vencimiento_poliza - NOW()::date AS dias_restantes
            FROM conversaciones
            WHERE fecha_vencimiento_poliza IS NOT NULL AND activo = true{extra_venc}
            ORDER BY fecha_vencimiento_poliza""",
        params_venc,
    )
    for row in r.rows:
        proxima = (row.get("dias_restantes") or 999) <= 30
        tipo = row.get("tipo_seguro", "")
        eventos.append({
            "id": f"poliza-venc-{row['id']}",
            "title": f"Vence póliza: {row['cliente_nombre']}" + (f" ({tipo})" if tipo else ""),
            "start": row["fecha_vencimiento_poliza"],
            "color": COLORS["poliza_vencimiento"] if proxima else COLORS["poliza_vigente"],
            "extendedProps": {"tipo": "poliza_vencimiento", "conversacion_id": str(row["id"]),
                              "numero_poliza": row.get("numero_poliza"), "dias_restantes": row.get("dias_restantes")},
        })

    # Cotizaciones por vencer
    params_cot = []
    extra_cot = ""
    if start:
        extra_cot += " AND co.fecha_vencimiento >= %s"
        params_cot.append(start)
    if end:
        extra_cot += " AND co.fecha_vencimiento <= %s"
        params_cot.append(end)

    r = query(
        f"""SELECT co.id, co.aseguradora, co.fecha_vencimiento,
                   c.id as conv_id, c.cliente_nombre, c.tipo_seguro
            FROM cotizaciones co
            JOIN conversaciones c ON c.id = co.conversacion_id
            WHERE co.fecha_vencimiento IS NOT NULL AND co.estado NOT IN ('rechazada'){extra_cot}
            ORDER BY co.fecha_vencimiento""",
        params_cot,
    )
    for row in r.rows:
        eventos.append({
            "id": f"cotizacion-{row['id']}",
            "title": f"Cotización vence: {row['cliente_nombre']} — {row['aseguradora']}",
            "start": row["fecha_vencimiento"],
            "color": COLORS["cotizacion"],
            "extendedProps": {"tipo": "cotizacion", "conversacion_id": str(row["conv_id"]), "aseguradora": row["aseguradora"]},
        })

    # Tramites activos
    r = query(
        """SELECT id, cliente_nombre, tipo_seguro, estado, fecha_cambio_estado
           FROM conversaciones
           WHERE estado IN ('tramite_oficina', 'tramite_aseguradora', 'entrega')
             AND fecha_cambio_estado IS NOT NULL AND activo = true
           ORDER BY fecha_cambio_estado"""
    )
    labels = {"tramite_oficina": "Trámite Oficina", "tramite_aseguradora": "Trámite Aseguradora", "entrega": "Entrega"}
    for row in r.rows:
        eventos.append({
            "id": f"tramite-{row['id']}",
            "title": f"{labels.get(row['estado'], row['estado'])}: {row['cliente_nombre']}",
            "start": row["fecha_cambio_estado"],
            "color": COLORS["tramite"],
            "extendedProps": {"tipo": "tramite", "conversacion_id": str(row["id"]), "estado": row["estado"]},
        })

    # Renovaciones
    r = query(
        """SELECT id, cliente_nombre, tipo_seguro, fecha_vencimiento_poliza
           FROM conversaciones
           WHERE estado = 'renovacion' AND activo = true
           ORDER BY fecha_vencimiento_poliza"""
    )
    for row in r.rows:
        if row.get("fecha_vencimiento_poliza"):
            tipo = row.get("tipo_seguro", "")
            eventos.append({
                "id": f"renovacion-{row['id']}",
                "title": f"Renovación: {row['cliente_nombre']}" + (f" ({tipo})" if tipo else ""),
                "start": row["fecha_vencimiento_poliza"],
                "color": COLORS["renovacion"],
                "extendedProps": {"tipo": "renovacion", "conversacion_id": str(row["id"])},
            })

    # --- Cartera real: vencimientos de pólizas registradas ---
    params_pol = []
    extra_pol = ""
    if start:
        extra_pol += " AND p.fecha_vencimiento >= %s"
        params_pol.append(start)
    if end:
        extra_pol += " AND p.fecha_vencimiento <= %s"
        params_pol.append(end)

    r = query(
        f"""SELECT p.id, p.numero_poliza, p.ramo, p.aseguradora, p.fecha_vencimiento,
                   cl.nombre AS cliente_nombre, cl.id AS cliente_id,
                   (p.fecha_vencimiento - NOW()::date) AS dias_restantes
            FROM polizas p
            JOIN clientes cl ON cl.id = p.cliente_id
            WHERE p.fecha_vencimiento IS NOT NULL AND p.estado = 'vigente'{extra_pol}
            ORDER BY p.fecha_vencimiento""",
        params_pol,
    )
    for row in r.rows:
        proxima = (row.get("dias_restantes") or 999) <= 30
        eventos.append({
            "id": f"poliza-{row['id']}",
            "title": f"Vence póliza: {row['cliente_nombre']} ({row['ramo']} · {row['aseguradora']})",
            "start": row["fecha_vencimiento"],
            "color": COLORS["poliza_vencimiento"] if proxima else COLORS["poliza_vigente"],
            "extendedProps": {
                "tipo": "poliza",
                "poliza_id": str(row["id"]),
                "cliente_id": str(row["cliente_id"]),
                "numero_poliza": row.get("numero_poliza"),
                "dias_restantes": row.get("dias_restantes"),
            },
        })

    return eventos
