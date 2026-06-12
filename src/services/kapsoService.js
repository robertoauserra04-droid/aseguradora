const axios = require('axios');

const KAPSO_BASE_URL = 'https://api.kapso.io/v1';

async function obtenerHistorialMensajes(phoneNumber, limit = 100) {
  const apiKey = process.env.KAPSO_API_KEY;
  if (!apiKey) throw new Error('KAPSO_API_KEY no configurada');

  const response = await axios.get(`${KAPSO_BASE_URL}/conversations`, {
    headers: { 'X-API-Key': apiKey },
    params: { phone_number: phoneNumber, limit },
  });

  return response.data;
}

async function enviarMensaje(telefono, texto) {
  const apiKey = process.env.KAPSO_API_KEY;
  const phoneNumberId = process.env.KAPSO_PHONE_NUMBER_ID;
  if (!apiKey) throw new Error('KAPSO_API_KEY no configurada');

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

module.exports = { obtenerHistorialMensajes, enviarMensaje };
