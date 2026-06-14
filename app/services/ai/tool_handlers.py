import logging
from app.config.database import query

logger = logging.getLogger(__name__)


def handle_tool_call(tool_name: str, args: dict, context: dict) -> str:
    conversacion_id = context["conversacion_id"]
    conversacion = context.get("conversacion", {})
    slots_info = context.get("slots_info", {})

    if tool_name == "registrar_interes":
        query(
            "UPDATE conversaciones SET tipo_seguro = %s, updated_at = NOW() WHERE id = %s AND tipo_seguro IS NULL",
            [args["tipo_seguro"], conversacion_id],
        )
        resumen = args.get("resumen_datos", "")
        logger.info("Interés registrado: %s%s", args["tipo_seguro"], f". Datos: {resumen}" if resumen else "")
        return f"Interés en seguro de tipo \"{args['tipo_seguro']}\" registrado correctamente."

    if tool_name == "escalar_a_agente":
        query(
            "UPDATE conversaciones SET requiere_respuesta = true, prioridad = 'alta', updated_at = NOW() WHERE id = %s",
            [conversacion_id],
        )
        logger.info("Escalando a agente — %s — conv %s", args.get("motivo"), conversacion_id)
        return "Conversación marcada para atención de asesor humano."

    if tool_name == "agendar_cita":
        slots = slots_info.get("slots", [])
        idx = int(args.get("slot_index", -1))
        if idx < 0 or idx >= len(slots):
            return "El horario seleccionado ya no está disponible. Por favor elige otro."
        slot = slots[idx]
        try:
            from app.services.calendar.client import crear_evento
            crear_evento(
                titulo=f"Cita Carguill: {conversacion.get('cliente_nombre', 'Cliente')} — {args.get('motivo', '')}",
                descripcion="\n".join([
                    f"Cliente: {conversacion.get('cliente_nombre', '')}",
                    f"Tel: {conversacion.get('cliente_telefono', '')}",
                    f"Seguro: {args.get('tipo_seguro', 'Por definir')}",
                    f"Motivo: {args.get('motivo', '')}",
                ]),
                inicio=slot["inicio"],
                fin=slot["fin"],
                email_cliente=conversacion.get("cliente_email"),
            )
            query(
                "UPDATE conversaciones SET estado = 'tramite_oficina', updated_at = NOW() WHERE id = %s AND estado = 'inicio'",
                [conversacion_id],
            )
            logger.info("Cita agendada: %s — conv %s", slot["label"], conversacion_id)
            return f"Cita agendada correctamente para el {slot['label']}."
        except Exception as e:
            logger.error("Error agendando cita: %s", e)
            return "Hubo un problema al agendar la cita. Por favor confírmala por otro medio o intenta de nuevo."

    return "Acción no reconocida."
