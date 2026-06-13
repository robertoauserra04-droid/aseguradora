// Carga todo el contexto necesario antes de llamar a OpenAI

const db = require('../../config/database');
const { consultarDisponibilidad } = require('../googleCalendarService');

async function buildSnapshot(conversacionId) {
  const [cfgResult, faqResult, msgsResult, convResult] = await Promise.all([
    db.query('SELECT instrucciones, activo_global, contexto FROM bot_config WHERE id = 1'),
    db.query('SELECT pregunta, respuesta FROM bot_faq WHERE activo = true ORDER BY orden, created_at'),
    db.query(
      `SELECT autor, contenido FROM mensajes
       WHERE conversacion_id = $1
       ORDER BY timestamp_mensaje DESC LIMIT 12`,
      [conversacionId]
    ),
    db.query(
      'SELECT tipo_seguro, estado, cliente_nombre, cliente_email, cliente_telefono FROM conversaciones WHERE id = $1',
      [conversacionId]
    ),
  ]);

  const cfg         = cfgResult.rows[0] || null;
  const faqs        = faqResult.rows;
  const mensajes    = msgsResult.rows;
  const conversacion = convResult.rows[0] || null;

  let slotsInfo = { texto: '', slots: [] };
  if (process.env.GOOGLE_CALENDAR_ID) {
    try {
      slotsInfo = await consultarDisponibilidad();
    } catch {
      // Calendar no disponible — continúa sin slots
    }
  }

  return { cfg, faqs, mensajes, conversacion, slotsInfo };
}

module.exports = { buildSnapshot };
