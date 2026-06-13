const axios = require('axios');

// Configurar KAPSO_API_BASE_URL en Railway con la URL correcta de tu cuenta Kapso
// (revisar en el dashboard de Kapso → API → Base URL o Settings → Integrations)
const KAPSO_BASE_URL = (process.env.KAPSO_API_BASE_URL || '').replace(/\/$/, '');

async function enviarMensaje(telefono, texto) {
  const apiKey = process.env.KAPSO_API_KEY;
  if (!apiKey) {
    console.warn('[Kapso] KAPSO_API_KEY no configurada — mensaje no enviado');
    return;
  }
  if (!KAPSO_BASE_URL) {
    console.warn('[Kapso] KAPSO_API_BASE_URL no configurada — mensaje no enviado');
    return;
  }

  const phoneNumberId = process.env.KAPSO_PHONE_NUMBER_ID;

  await axios.post(
    `${KAPSO_BASE_URL}/messages`,
    {
      phone_number_id: phoneNumberId,
      to: telefono,
      type: 'text',
      text: { body: texto },
    },
    { headers: { 'X-API-Key': apiKey, 'Content-Type': 'application/json' } }
  );
}

module.exports = { enviarMensaje };
