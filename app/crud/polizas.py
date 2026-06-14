from app.config.database import query


def listar(filtros: dict) -> list:
    conditions = []
    params = []

    if filtros.get("ramo"):
        conditions.append("p.ramo = %s")
        params.append(filtros["ramo"])
    if filtros.get("estado"):
        conditions.append("p.estado = %s")
        params.append(filtros["estado"])
    if filtros.get("aseguradora"):
        conditions.append("p.aseguradora = %s")
        params.append(filtros["aseguradora"])
    if filtros.get("search"):
        conditions.append("(cl.nombre ILIKE %s OR p.numero_poliza ILIKE %s)")
        params.extend([f"%{filtros['search']}%", f"%{filtros['search']}%"])
    if filtros.get("por_vencer") == "true":
        conditions.append("p.fecha_vencimiento IS NOT NULL AND p.fecha_vencimiento <= NOW()::date + 30")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    r = query(
        f"""SELECT p.id, p.numero_poliza, p.ramo, p.aseguradora, p.estado,
                   p.fecha_inicio, p.fecha_vencimiento, p.suma_asegurada,
                   p.prima, p.moneda, p.forma_pago, p.comision_pct, p.comision_monto,
                   p.cliente_id, cl.nombre AS cliente_nombre,
                   (p.fecha_vencimiento - NOW()::date) AS dias_para_vencer
            FROM polizas p
            JOIN clientes cl ON cl.id = p.cliente_id
            {where}
            ORDER BY p.fecha_vencimiento ASC NULLS LAST""",
        params,
    )
    for row in r.rows:
        row["id"] = str(row["id"])
        row["cliente_id"] = str(row["cliente_id"])
    return r.rows


def _calc_comision(prima, pct, monto):
    if monto is not None:
        return monto
    if prima is not None and pct:
        return round(float(prima) * float(pct) / 100, 2)
    return None


def crear(datos: dict) -> dict:
    comision_monto = _calc_comision(datos.get("prima"), datos.get("comision_pct"), datos.get("comision_monto"))
    r = query(
        """INSERT INTO polizas
             (cliente_id, conversacion_id, numero_poliza, ramo, aseguradora, estado,
              fecha_inicio, fecha_vencimiento, suma_asegurada, prima, moneda, forma_pago,
              comision_pct, comision_monto, notas)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING id""",
        [
            datos["cliente_id"],
            datos.get("conversacion_id"),
            datos.get("numero_poliza"),
            datos["ramo"],
            datos["aseguradora"],
            datos.get("estado", "vigente"),
            datos.get("fecha_inicio"),
            datos.get("fecha_vencimiento"),
            datos.get("suma_asegurada"),
            datos.get("prima"),
            datos.get("moneda", "MXN"),
            datos.get("forma_pago", "anual"),
            datos.get("comision_pct", 0),
            comision_monto,
            datos.get("notas"),
        ],
    )
    return {"id": str(r.rows[0]["id"]), "comision_monto": comision_monto}


def actualizar(poliza_id: str, datos: dict) -> dict | None:
    campos = ["numero_poliza", "ramo", "aseguradora", "estado", "fecha_inicio",
              "fecha_vencimiento", "suma_asegurada", "prima", "moneda", "forma_pago",
              "comision_pct", "notas"]
    sets = ["updated_at = NOW()"]
    params = []
    for campo in campos:
        if campo in datos:
            sets.append(f"{campo} = %s")
            params.append(datos[campo])

    # Recalcular comisión si cambió prima o pct
    if "prima" in datos or "comision_pct" in datos:
        actual = query("SELECT prima, comision_pct FROM polizas WHERE id = %s", [poliza_id])
        if actual.rows:
            prima = datos.get("prima", actual.rows[0]["prima"])
            pct = datos.get("comision_pct", actual.rows[0]["comision_pct"])
            sets.append("comision_monto = %s")
            params.append(_calc_comision(prima, pct, None))

    params.append(poliza_id)
    r = query(
        f"UPDATE polizas SET {', '.join(sets)} WHERE id = %s RETURNING id",
        params,
    )
    return r.rows[0] if r.rows else None


def eliminar(poliza_id: str) -> bool:
    r = query("DELETE FROM polizas WHERE id = %s RETURNING id", [poliza_id])
    return len(r.rows) > 0


def resumen_comisiones(fecha_inicio: str = None, fecha_fin: str = None) -> dict:
    conditions = ["comision_monto IS NOT NULL"]
    params = []
    if fecha_inicio:
        conditions.append("fecha_inicio >= %s")
        params.append(fecha_inicio)
    if fecha_fin:
        conditions.append("fecha_inicio <= %s")
        params.append(fecha_fin)
    where = "WHERE " + " AND ".join(conditions)

    total = query(f"SELECT COALESCE(SUM(comision_monto), 0) AS total FROM polizas {where}", params)
    por_aseguradora = query(
        f"""SELECT aseguradora, COALESCE(SUM(comision_monto), 0) AS total, COUNT(*) AS num
            FROM polizas {where} GROUP BY aseguradora ORDER BY total DESC""",
        params,
    )
    por_ramo = query(
        f"""SELECT ramo, COALESCE(SUM(comision_monto), 0) AS total, COUNT(*) AS num
            FROM polizas {where} GROUP BY ramo ORDER BY total DESC""",
        params,
    )

    return {
        "total": float(total.rows[0]["total"]),
        "por_aseguradora": por_aseguradora.rows,
        "por_ramo": por_ramo.rows,
    }
