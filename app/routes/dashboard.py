from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from app.middleware.auth import get_agente
from app.config.database import query

router = APIRouter()


@router.get("/api/dashboard/kpis")
def kpis(agente=Depends(get_agente)):
    hoy = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    por_estado = query("SELECT estado, COUNT(*) AS total FROM conversaciones WHERE activo = true GROUP BY estado")
    hoy_nuevos = query("SELECT COUNT(*) AS total FROM conversaciones WHERE created_at >= %s", [hoy])
    hoy_propuestas = query(
        "SELECT COUNT(*) AS total FROM cambios_estado_historico WHERE estado_nuevo = 'cotizacion' AND timestamp >= %s", [hoy]
    )
    hoy_polizas = query(
        "SELECT COUNT(*) AS total FROM cambios_estado_historico WHERE estado_nuevo = 'vigente' AND timestamp >= %s", [hoy]
    )
    pendientes = query("SELECT COUNT(*) AS total FROM conversaciones WHERE requiere_respuesta = true AND activo = true")
    criticas = query(
        """SELECT c.id, c.cliente_nombre, c.estado, c.prioridad,
                  EXTRACT(EPOCH FROM (NOW() - c.ultimo_mensaje_at)) / 3600 AS horas_sin_respuesta,
                  m.contenido AS ultimo_mensaje
           FROM conversaciones c
           LEFT JOIN LATERAL (
             SELECT contenido FROM mensajes
             WHERE conversacion_id = c.id
             ORDER BY timestamp_mensaje DESC LIMIT 1
           ) m ON true
           WHERE c.requiere_respuesta = true AND c.activo = true
           ORDER BY horas_sin_respuesta DESC
           LIMIT 10"""
    )

    conversaciones_por_estado = {row["estado"]: int(row["total"]) for row in por_estado.rows}

    return {
        "hoy": {
            "nuevos_contactos": int(hoy_nuevos.rows[0]["total"]),
            "pendientes_ahora": int(pendientes.rows[0]["total"]),
            "propuestas_enviadas": int(hoy_propuestas.rows[0]["total"]),
            "polizas_activadas": int(hoy_polizas.rows[0]["total"]),
        },
        "conversaciones_por_estado": conversaciones_por_estado,
        "conversaciones_criticas": [
            {
                "id": str(r["id"]),
                "cliente_nombre": r["cliente_nombre"],
                "estado": r["estado"],
                "horas_sin_respuesta": round(float(r["horas_sin_respuesta"] or 0)),
                "prioridad": r["prioridad"],
                "ultimo_mensaje": r["ultimo_mensaje"],
            }
            for r in criticas.rows
        ],
    }
