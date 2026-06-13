// Orquestador principal del bot — Seguros Carguill

const OpenAI = require('openai');
const { buildSnapshot }            = require('./snapshot');
const { buildSystemPrompt, buildMessages } = require('./prompt');
const { buildTools }               = require('./tools');
const { handleToolCall }           = require('./tool_handlers');

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

  // 1. Cargar contexto completo
  const snapshot = await buildSnapshot(conversacionId);
  if (!snapshot.cfg || !snapshot.cfg.activo_global) return null;

  // 2. Construir prompt + historial
  const systemPrompt = buildSystemPrompt(snapshot.cfg, snapshot.faqs, snapshot.slotsInfo);
  const messages     = buildMessages(systemPrompt, snapshot.mensajes);
  const tools        = buildTools(snapshot.slotsInfo);

  // 3. Primera llamada a OpenAI
  const resp = await openai.chat.completions.create({
    model: 'gpt-4o-mini',
    messages,
    max_tokens: 400,
    temperature: 0.65,
    ...(tools.length > 0 ? { tools, tool_choice: 'auto' } : {}),
  });

  const choice = resp.choices[0];

  // 4. Manejar tool calls
  if (choice.finish_reason === 'tool_calls' && choice.message.tool_calls?.length > 0) {
    messages.push(choice.message);

    for (const toolCall of choice.message.tool_calls) {
      const args   = JSON.parse(toolCall.function.arguments);
      const result = await handleToolCall(toolCall.function.name, args, {
        conversacionId,
        conversacion: snapshot.conversacion,
        slotsInfo:    snapshot.slotsInfo,
      });

      messages.push({
        role:         'tool',
        tool_call_id: toolCall.id,
        content:      result,
      });
    }

    // 5. Segunda llamada para obtener la respuesta en lenguaje natural
    const resp2 = await openai.chat.completions.create({
      model:       'gpt-4o-mini',
      messages,
      max_tokens:  300,
      temperature: 0.65,
    });

    return resp2.choices[0]?.message?.content?.trim() || null;
  }

  return choice.message?.content?.trim() || null;
}

module.exports = { generarRespuesta };
