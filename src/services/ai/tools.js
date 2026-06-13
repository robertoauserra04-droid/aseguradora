// Definiciones de funciones para OpenAI function calling — bot de seguros

function buildTools(slotsInfo) {
  const tools = [];

  // Registrar el tipo de seguro detectado en la conversación
  tools.push({
    type: 'function',
    function: {
      name: 'registrar_interes',
      description:
        'Registra el tipo de seguro que le interesa al cliente. ' +
        'Úsalo tan pronto identifiques de qué seguro quiere hablar el cliente.',
      parameters: {
        type: 'object',
        properties: {
          tipo_seguro: {
            type: 'string',
            enum: ['vida', 'medical', 'auto', 'daño', 'viaje', 'mascotas'],
            description: 'Tipo de seguro de interés del cliente.',
          },
          resumen_datos: {
            type: 'string',
            description:
              'Resumen breve de los datos recopilados del cliente relevantes para este seguro ' +
              '(ej: "Hombre, 35 años, no fuma, cobertura 1M"). Puede estar vacío si aún no hay datos.',
          },
        },
        required: ['tipo_seguro'],
      },
    },
  });

  // Escalar a agente humano
  tools.push({
    type: 'function',
    function: {
      name: 'escalar_a_agente',
      description:
        'Escala la conversación a un asesor humano cuando el cliente lo pide explícitamente ' +
        'o cuando la consulta requiere atención personalizada.',
      parameters: {
        type: 'object',
        properties: {
          motivo: {
            type: 'string',
            description: 'Motivo por el que se escala (ej: "Cliente solicitó hablar con un asesor").',
          },
        },
        required: ['motivo'],
      },
    },
  });

  // Agendar cita (solo si hay slots de calendario disponibles)
  if (slotsInfo && slotsInfo.slots && slotsInfo.slots.length > 0) {
    tools.push({
      type: 'function',
      function: {
        name: 'agendar_cita',
        description:
          'Agenda una cita con un asesor de Seguros Carguill cuando el cliente confirma un horario disponible.',
        parameters: {
          type: 'object',
          properties: {
            slot_index: {
              type: 'number',
              description: 'Índice del slot elegido (0-based) de la lista de horarios disponibles.',
            },
            motivo: {
              type: 'string',
              description: 'Motivo o tipo de seguro de la cita (ej: "Cotización seguro de auto").',
            },
            tipo_seguro: {
              type: 'string',
              enum: ['vida', 'medical', 'auto', 'daño', 'viaje', 'mascotas'],
              description: 'Tipo de seguro para el que se agenda la cita.',
            },
          },
          required: ['slot_index', 'motivo'],
        },
      },
    });
  }

  return tools;
}

module.exports = { buildTools };
