const OpenAI = require('openai');
const db = require('../config/database');

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

  // 3. Últimos 12 mensajes de la conversación (más contexto)
  const msgsResult = await db.query(
    `SELECT autor, contenido FROM mensajes
     WHERE conversacion_id = $1
     ORDER BY timestamp_mensaje DESC LIMIT 12`,
    [conversacionId]
  );

  // 4. Armar system prompt
  const faqText = faqResult.rows.length > 0
    ? '\n\nBase de conocimiento (úsala para responder con precisión):\n' +
      faqResult.rows.map(f => `P: ${f.pregunta}\nR: ${f.respuesta}`).join('\n\n')
    : '';

  const systemPrompt = (cfg.instrucciones || '').trim() + faqText;

  // 5. Historial en formato OpenAI (cronológico)
  const messages = [{ role: 'system', content: systemPrompt }];
  for (const m of msgsResult.rows.reverse()) {
    const role = m.autor === 'cliente' ? 'user' : 'assistant';
    messages.push({ role, content: m.contenido });
  }

  // 6. Llamar a OpenAI
  const resp = await openai.chat.completions.create({
    model: 'gpt-4o-mini',
    messages,
    max_tokens: 350,
    temperature: 0.7,
  });

  return resp.choices[0]?.message?.content?.trim() || null;
}

module.exports = { generarRespuesta };
