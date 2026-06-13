const axios = require('axios');

const KAPSO_BASE_URL = 'https://api.kapso.ai/meta/whatsapp';

async function enviarMensaje(telefono, texto) {
  const apiKey = process.env.KAPSO_API_KEY;
  if (!apiKey) {
    console.warn('[Kapso] KAPSO_API_KEY no configurada — mensaje no enviado');
    return;
  }

  const phoneNumberId = process.env.KAPSO_PHONE_NUMBER_ID;

  await axios.post(
    `${KAPSO_BASE_URL}/messages/send-a-message`,
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
