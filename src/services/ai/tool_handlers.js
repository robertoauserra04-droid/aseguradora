// Ejecución de cada tool call del bot de seguros

const db = require('../../config/database');
const { crearEvento } = require('../googleCalendarService');

async function handleToolCall(toolName, args, { conversacionId, conversacion, slotsInfo }) {
  switch (toolName) {

    case 'registrar_interes': {
      await db.query(
        `UPDATE conversaciones
         SET tipo_seguro = $1, updated_at = NOW()
         WHERE id = $2 AND tipo_seguro IS NULL`,
        [args.tipo_seguro, conversacionId]
      );
      const resumen = args.resumen_datos
        ? `Interés registrado: ${args.tipo_seguro}. Datos: ${args.resumen_datos}`
        : `Interés registrado: ${args.tipo_seguro}`;
      console.log(`[Bot] ${resumen} — conv ${conversacionId}`);
      return `Interés en seguro de tipo "${args.tipo_seguro}" registrado correctamente.`;
    }

    case 'escalar_a_agente': {
      await db.query(
        `UPDATE conversaciones
         SET requiere_respuesta = true, prioridad = 'alta', updated_at = NOW()
         WHERE id = $1`,
        [conversacionId]
      );
      console.log(`[Bot] Escalando a agente — ${args.motivo} — conv ${conversacionId}`);
      return 'Conversación marcada para atención de asesor humano.';
    }

    case 'agendar_cita': {
      const slot = slotsInfo.slots[args.slot_index];
      if (!slot) {
        return 'El horario seleccionado ya no está disponible. Por favor elige otro.';
      }
      try {
        await crearEvento({
          titulo:       `Cita Carguill: ${conversacion?.cliente_nombre || 'Cliente'} — ${args.motivo}`,
          descripcion:  [
            `Cliente: ${conversacion?.cliente_nombre || ''}`,
            `Tel: ${conversacion?.cliente_telefono || ''}`,
            `Seguro: ${args.tipo_seguro || 'Por definir'}`,
            `Motivo: ${args.motivo}`,
          ].join('\n'),
          inicio:       slot.inicio,
          fin:          slot.fin,
          emailCliente: conversacion?.cliente_email || null,
        });

        // Marcar la conversación como con cita agendada (tramite_oficina)
        await db.query(
          `UPDATE conversaciones
           SET estado = 'tramite_oficina', updated_at = NOW()
           WHERE id = $1 AND estado = 'inicio'`,
          [conversacionId]
        );

        console.log(`[Bot+Calendar] Cita agendada: ${slot.label} — conv ${conversacionId}`);
        return `Cita agendada correctamente para el ${slot.label}.`;
      } catch (err) {
        console.error('[Bot+Calendar] Error agendando:', err.message);
        return 'Hubo un problema al agendar la cita. Por favor confírmala por otro medio o intenta de nuevo.';
      }
    }

    default:
      return 'Acción no reconocida.';
  }
}

module.exports = { handleToolCall };
