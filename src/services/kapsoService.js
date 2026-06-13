const axios = require('axios');

async function enviarMensaje(telefono, texto) {
  const apiKey = process.env.KAPSO_API_KEY;
  const phoneNumberId = process.env.KAPSO_PHONE_NUMBER_ID;

  if (!apiKey || !phoneNumberId) {
    console.warn('[Kapso] KAPSO_API_KEY o KAPSO_PHONE_NUMBER_ID no configurados');
    return;
  }

  // Normalizar: Kapso/Meta esperan número sin '+'
  const to = telefono.replace(/^\+/, '');

  await axios.post(
    `https://api.kapso.ai/meta/whatsapp/v24.0/${phoneNumberId}/messages`,
    {
      messaging_product: 'whatsapp',
      recipient_type: 'individual',
      to,
      type: 'text',
      text: { body: texto },
    },
    { headers: { 'X-API-Key': apiKey, 'Content-Type': 'application/json' } }
  );
}

module.exports = { enviarMensaje };
