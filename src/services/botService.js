const OpenAI = require('openai');
const db = require('../config/database');
const { consultarDisponibilidad, crearEvento } = require('./googleCalendarService');

let openaiClient = null;

function getOpenAI() {
  if (!openaiClient && process.env.OPENAI_API_KEY) {
    openaiClient = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  }
  return openaiClient;
}

async function generarRespuesta(conversacionId) {
  const openai = getOpenAI();
  if (!openai) return null;

  // 1. Config global del bot
  const cfgResult = await db.query('SELECT instrucciones, activo_global FROM bot_config LIMIT 1');
  const cfg = cfgResult.rows[0];
  if (!cfg || !cfg.activo_global) return null;

  // 2. FAQs activos
  const faqResult = await db.query(
    'SELECT pregunta, respuesta FROM bot_faq WHERE activo = true ORDER BY orden, created_at'
  );

  // 3. Últimos 12 mensajes de la conversación
  const msgsResult = await db.query(
    `SELECT autor, contenido FROM mensajes
     WHERE conversacion_id = $1
     ORDER BY timestamp_mensaje DESC LIMIT 12`,
    [conversacionId]
  );

  // 4. Disponibilidad en Google Calendar (solo si está configurado)
  let slotsInfo = { texto: '', slots: [] };
  if (process.env.GOOGLE_CALENDAR_ID) {
    try { slotsInfo = await consultarDisponibilidad(); } catch {}
  }

  // 5. Armar system prompt
  const faqText = faqResult.rows.length > 0
    ? '\n\nBase de conocimiento:\n' +
      faqResult.rows.map(f => `P: ${f.pregunta}\nR: ${f.respuesta}`).join('\n\n')
    : '';

  const calText = slotsInfo.texto
    ? '\n\n' + slotsInfo.texto + '\nSi el cliente quiere agendar una cita, usa la función agendar_cita con el índice del slot elegido (0-based).'
    : '';

  const systemPrompt = (cfg.instrucciones || '').trim() + faqText + calText;

  // 6. Historial en formato OpenAI (cronológico)
  const messages = [{ role: 'system', content: systemPrompt }];
  for (const m of msgsResult.rows.reverse()) {
    messages.push({ role: m.autor === 'cliente' ? 'user' : 'assistant', content: m.contenido });
  }

  // 7. Tools de función calling (solo si Calendar está activo)
  const tools = (process.env.GOOGLE_CALENDAR_ID && slotsInfo.slots.length > 0) ? [
    {
      type: 'function',
      function: {
        name: 'agendar_cita',
        description: 'Agenda una cita en el calendario cuando el cliente confirma un horario disponible.',
        parameters: {
          type: 'object',
          properties: {
            slot_index: {
              type: 'number',
              description: 'Índice del slot elegido (0-based) de la lista de horarios disponibles.',
            },
            motivo: {
              type: 'string',
              description: 'Motivo o tipo de la cita (ej: "Revisión de cotización", "Firma de póliza").',
            },
          },
          required: ['slot_index', 'motivo'],
        },
      },
    },
  ] : [];

  // 8. Primera llamada a OpenAI
  const resp = await openai.chat.completions.create({
    model: 'gpt-4o-mini',
    messages,
    max_tokens: 350,
    temperature: 0.7,
    ...(tools.length > 0 ? { tools, tool_choice: 'auto' } : {}),
  });

  const choice = resp.choices[0];

  // 9. Manejar tool call (agendar cita)
  if (choice.finish_reason === 'tool_calls' && choice.message.tool_calls?.length > 0) {
    const toolCall = choice.message.tool_calls[0];

    if (toolCall.function.name === 'agendar_cita') {
      const args   = JSON.parse(toolCall.function.arguments);
      const slot   = slotsInfo.slots[args.slot_index];
      let toolResult = 'Cita agendada correctamente.';

      if (slot) {
        try {
          const convData = await db.query(
            'SELECT cliente_nombre, cliente_telefono, cliente_email FROM conversaciones WHERE id = $1',
            [conversacionId]
          );
          const conv = convData.rows[0];

          await crearEvento({
            titulo:       `Cita: ${conv?.cliente_nombre || 'Cliente'} — ${args.motivo}`,
            descripcion:  `Cliente: ${conv?.cliente_nombre}\nTel: ${conv?.cliente_telefono}\nMotivo: ${args.motivo}`,
            inicio:       slot.inicio,
            fin:          slot.fin,
            emailCliente: conv?.cliente_email || null,
          });

          console.log(`[Bot+Calendar] Cita agendada: ${slot.label}`);
        } catch (err) {
          toolResult = 'Hubo un problema al agendar. Por favor confirma por otro medio.';
          console.error('[Bot+Calendar] Error agendando:', err.message);
        }
      } else {
        toolResult = 'El horario seleccionado ya no está disponible. Por favor elige otro.';
      }

      // Segunda llamada para obtener la respuesta final en texto
      messages.push(choice.message);
      messages.push({ role: 'tool', tool_call_id: toolCall.id, content: toolResult });

      const resp2 = await openai.chat.completions.create({
        model: 'gpt-4o-mini',
        messages,
        max_tokens: 250,
        temperature: 0.7,
      });

      return resp2.choices[0]?.message?.content?.trim() || null;
    }
  }

  return choice.message?.content?.trim() || null;
}

module.exports = { generarRespuesta };
