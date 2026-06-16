import logging
import os
from app.config.database import query

logger = logging.getLogger(__name__)

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def run_migrations() -> None:
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            sql = f.read()
        query(sql)
        logger.info("Migraciones ejecutadas correctamente")
    except Exception as e:
        logger.error("Error al ejecutar migraciones: %s", e)
        raise


def seed_etapas() -> None:
    """Carga las fases por defecto en la tabla `etapas` si está vacía.
    Idempotente: ON CONFLICT no pisa fases que el usuario haya editado."""
    try:
        from app.utils.estados import ESTADOS
        for e in ESTADOS.values():
            query(
                """INSERT INTO etapas (key, label, color, orden, es_cerrada)
                   VALUES (%s, %s, %s, %s, false)
                   ON CONFLICT (key) DO NOTHING""",
                [e["key"], e["label"], e["color"], e["orden"]],
            )
        # Fase "Cerrada" (única, para el botón de cierre y estadísticas)
        query(
            """INSERT INTO etapas (key, label, color, orden, es_cerrada)
               VALUES ('cerrada', 'Cerrada', '#64748B', 99, true)
               ON CONFLICT (key) DO NOTHING"""
        )
    except Exception as e:
        logger.error("Error en seed_etapas: %s", e)


def backfill_clientes_polizas() -> None:
    """Normaliza datos legados: crea clientes y pólizas desde conversaciones.

    Idempotente — solo actúa sobre conversaciones sin cliente_id y pólizas
    que aún no existan (chequeo por conversacion_id).
    """
    try:
        # 1. Crear cliente por cada conversación con teléfono que no exista aún
        query(
            """INSERT INTO clientes (nombre, telefono, email)
               SELECT DISTINCT ON (cliente_telefono)
                      cliente_nombre, cliente_telefono, cliente_email
               FROM conversaciones
               WHERE cliente_telefono IS NOT NULL
               ON CONFLICT (telefono) DO NOTHING"""
        )

        # 2. Enlazar conversaciones a su cliente
        query(
            """UPDATE conversaciones c
               SET cliente_id = cl.id
               FROM clientes cl
               WHERE c.cliente_id IS NULL
                 AND c.cliente_telefono = cl.telefono"""
        )

        # 3. Crear póliza por cada conversación con numero_poliza sin póliza enlazada
        r = query(
            """INSERT INTO polizas
                 (cliente_id, conversacion_id, numero_poliza, ramo, aseguradora,
                  fecha_inicio, fecha_vencimiento, prima)
               SELECT c.cliente_id, c.id, c.numero_poliza,
                      COALESCE(c.tipo_seguro, 'vida'),
                      COALESCE(NULLIF(c.aseguradora_ofrecida[1], ''), 'Por definir'),
                      c.fecha_inicio_poliza, c.fecha_vencimiento_poliza, c.prima_poliza
               FROM conversaciones c
               WHERE c.numero_poliza IS NOT NULL
                 AND c.cliente_id IS NOT NULL
                 AND NOT EXISTS (
                   SELECT 1 FROM polizas p WHERE p.conversacion_id = c.id
                 )
               RETURNING id"""
        )
        if r.rowcount:
            logger.info("Backfill: %s pólizas creadas desde conversaciones", r.rowcount)
    except Exception as e:
        logger.error("Error en backfill_clientes_polizas: %s", e)
