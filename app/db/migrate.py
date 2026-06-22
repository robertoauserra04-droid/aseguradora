import json
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


def seed_bot_config_defaults() -> None:
    """Prellena `bot_config.contexto` con lo que antes estaba hardcodeado en el prompt
    (nombre, descripción/rol, flujo y lista de seguros), SOLO si faltan esas claves.

    Así el bot conserva el comportamiento previo de Carguill, pero ahora TODO es editable
    desde el panel (el código ya no impone identidad ni flujo de aseguradora)."""
    try:
        r = query("SELECT contexto FROM bot_config WHERE id = 1")
        if not r.rows:
            return
        ctx = r.rows[0].get("contexto") or {}
        if isinstance(ctx, str):
            try:
                ctx = json.loads(ctx)
            except Exception:
                ctx = {}

        defaults = {
            "empresa": "Seguros Carguill",
            "ciudad": "San Pedro Garza García, NL",
            "bot_nombre": "Carguill",
            "seguros": ["Vida", "Gastos Médicos Mayores", "Auto", "Daños", "Viaje", "Mascotas"],
            "descripcion": (
                "Tu rol es orientar y asesorar a los clientes que buscan un seguro. NO eres un "
                "vendedor directo: tu función es entender la necesidad del cliente, recopilar la "
                "información relevante y conectarlo con un asesor humano para la cotización formal. "
                "Trabajamos con más de 25 aseguradoras en México para encontrar la mejor opción para "
                "cada cliente."
            ),
            "proceso": (
                "1. Saluda al cliente y pregunta qué tipo de seguro le interesa o qué necesita.\n"
                '2. Una vez detectado el tipo de seguro, llama a "registrar_interes" para registrarlo.\n'
                "3. Recopila los datos básicos según el tipo:\n"
                "   • Vida: edad del titular, si fuma, monto de cobertura deseado.\n"
                "   • Gastos Médicos: edad, número de personas a asegurar, ¿condiciones preexistentes?\n"
                "   • Auto: año, marca y modelo, uso (personal/comercial), ¿amplia o limitada?\n"
                "   • Daños: tipo de bien (casa, negocio, equipo), ubicación, valor aproximado.\n"
                "   • Viaje: destino, fechas, número de viajeros, ¿cobertura médica incluida?\n"
                "   • Mascotas: especie, raza, edad.\n"
                '4. Con esa información, ofrece agendar una llamada o cita con un asesor (usa "agendar_cita").\n'
                "5. Si preguntan precios específicos, explica que dependen de sus datos y que un asesor "
                "enviará cotizaciones de varias aseguradoras. No inventes precios.\n"
                '6. Si piden hablar con una persona o la consulta es compleja, usa "escalar_a_agente".'
            ),
        }

        cambios = False
        for k, v in defaults.items():
            actual = ctx.get(k)
            vacio = actual is None or (isinstance(actual, str) and not actual.strip()) or actual == []
            if vacio:
                ctx[k] = v
                cambios = True

        if cambios:
            query("UPDATE bot_config SET contexto = %s, updated_at = NOW() WHERE id = 1", [json.dumps(ctx)])
            logger.info("seed_bot_config_defaults: configuración del bot prellenada con los valores por defecto")
    except Exception as e:
        logger.error("Error en seed_bot_config_defaults: %s", e)


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
