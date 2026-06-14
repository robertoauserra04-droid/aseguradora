from app.config.database import query


def listar(search: str = None) -> list:
    conditions = ["cl.activo = true"]
    params = []
    if search:
        conditions.append("(cl.nombre ILIKE %s OR cl.telefono ILIKE %s OR cl.email ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    where = "WHERE " + " AND ".join(conditions)

    r = query(
        f"""SELECT cl.id, cl.nombre, cl.telefono, cl.email, cl.rfc,
                   cl.agente_asignado, cl.created_at,
                   COUNT(p.id) AS num_polizas
            FROM clientes cl
            LEFT JOIN polizas p ON p.cliente_id = cl.id
            {where}
            GROUP BY cl.id
            ORDER BY cl.created_at DESC""",
        params,
    )
    for row in r.rows:
        row["id"] = str(row["id"])
        row["num_polizas"] = int(row["num_polizas"])
        if row.get("agente_asignado"):
            row["agente_asignado"] = str(row["agente_asignado"])
    return r.rows


def obtener_por_id(cliente_id: str) -> dict | None:
    r = query("SELECT * FROM clientes WHERE id = %s", [cliente_id])
    if not r.rows:
        return None

    polizas = query(
        """SELECT id, numero_poliza, ramo, aseguradora, estado,
                  fecha_inicio, fecha_vencimiento, prima, moneda, comision_monto
           FROM polizas WHERE cliente_id = %s ORDER BY fecha_vencimiento DESC NULLS LAST""",
        [cliente_id],
    )
    convs = query(
        """SELECT id, estado, tipo_seguro, ultimo_mensaje_at
           FROM conversaciones WHERE cliente_id = %s ORDER BY ultimo_mensaje_at DESC NULLS LAST""",
        [cliente_id],
    )

    return {
        "cliente": r.rows[0],
        "polizas": polizas.rows,
        "conversaciones": convs.rows,
    }


def buscar_por_telefono(telefono: str) -> dict | None:
    r = query("SELECT * FROM clientes WHERE telefono = %s", [telefono])
    return r.rows[0] if r.rows else None


def crear(datos: dict) -> dict:
    r = query(
        """INSERT INTO clientes (nombre, telefono, email, rfc, fecha_nacimiento, direccion, notas, agente_asignado)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING id, nombre, telefono, email, rfc, created_at""",
        [
            datos.get("nombre", "Cliente"),
            datos.get("telefono"),
            datos.get("email"),
            datos.get("rfc"),
            datos.get("fecha_nacimiento"),
            datos.get("direccion"),
            datos.get("notas"),
            datos.get("agente_asignado"),
        ],
    )
    return r.rows[0]


def actualizar(cliente_id: str, datos: dict) -> dict | None:
    campos = ["nombre", "telefono", "email", "rfc", "fecha_nacimiento", "direccion", "notas", "agente_asignado"]
    sets = ["updated_at = NOW()"]
    params = []
    for campo in campos:
        if campo in datos:
            sets.append(f"{campo} = %s")
            params.append(datos[campo])
    params.append(cliente_id)
    r = query(
        f"UPDATE clientes SET {', '.join(sets)} WHERE id = %s RETURNING id, nombre, telefono, email",
        params,
    )
    return r.rows[0] if r.rows else None


def desactivar(cliente_id: str) -> bool:
    r = query("UPDATE clientes SET activo = false WHERE id = %s RETURNING id", [cliente_id])
    return len(r.rows) > 0
