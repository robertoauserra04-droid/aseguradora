// Construye el system prompt para el bot de Seguros Carguill

function buildSystemPrompt(cfg, faqs, slotsInfo) {
  const c = cfg.contexto || {};
  const partes = [];

  // --- IDENTIDAD ---
  const empresa = c.empresa || 'Seguros Carguill';
  const ciudad  = c.ciudad  || 'San Pedro Garza García, NL';
  partes.push(
    `Eres el asistente virtual de ${empresa}, un broker de seguros ubicado en ${ciudad}, México. ` +
    `Tu nombre es Carguill. Responde siempre en español, de forma clara y concisa.`
  );

  // --- ROL Y MISIÓN ---
  partes.push(
    `Tu rol es orientar y asesorar a los clientes que buscan un seguro. ` +
    `NO eres un vendedor directo: tu función es entender la necesidad del cliente, ` +
    `recopilar la información relevante y conectarlo con un asesor humano para la cotización formal. ` +
    `Trabajamos con más de 25 aseguradoras en México para encontrar la mejor opción para cada cliente.`
  );

  // --- SEGUROS DISPONIBLES ---
  const seguros = Array.isArray(c.seguros) && c.seguros.length > 0
    ? c.seguros
    : ['Vida', 'Gastos Médicos Mayores', 'Auto', 'Daños', 'Viaje', 'Mascotas'];
  partes.push(`Seguros que ofrecemos:\n${seguros.map(s => `• ${s}`).join('\n')}`);

  // --- ASEGURADORAS ---
  if (c.aseguradoras) {
    partes.push(`Aseguradoras con las que trabajamos: ${c.aseguradoras}.`);
  }

  // --- FLUJO DE ATENCIÓN POR TIPO DE SEGURO ---
  partes.push(`
FLUJO DE ATENCIÓN (síguelo en orden):

1. Saluda al cliente y pregunta qué tipo de seguro le interesa o qué necesita.
2. Una vez detectado el tipo de seguro, llama a "registrar_interes" para registrarlo.
3. Recopila los datos básicos según el tipo:
   • Vida: edad del titular, si fuma, monto de cobertura deseado.
   • Gastos Médicos: edad, número de personas a asegurar, ¿tiene condiciones preexistentes?
   • Auto: año, marca y modelo del vehículo, uso (personal/comercial), ¿amplia o limitada?
   • Daños: tipo de bien (casa, negocio, equipo), ubicación, valor aproximado.
   • Viaje: destino, fechas, número de viajeros, ¿tiene cobertura médica incluida?
   • Mascotas: especie, raza, edad de la mascota.
4. Con esa información, ofrece al cliente agendar una llamada o cita con un asesor para la cotización formal.
   Si el cliente acepta, usa "agendar_cita".
5. Si el cliente pregunta precios específicos, dile que los precios dependen de sus datos y que un asesor
   le enviará cotizaciones comparativas de varias aseguradoras. No inventes precios.
6. Si el cliente pide hablar con una persona o la consulta es muy compleja, usa "escalar_a_agente".`.trim()
  );

  // --- HORARIO ---
  if (c.horario) {
    partes.push(`Horario de atención: ${c.horario}.`);
  }

  // --- TONO ---
  const tonos = {
    formal:   'Responde en tono formal y profesional.',
    amigable: 'Responde en tono amigable y cercano.',
    ambos:    'Responde en tono formal pero amigable y cálido.',
  };
  if (c.tono && tonos[c.tono]) partes.push(tonos[c.tono]);

  // --- BIENVENIDA ---
  if (c.bienvenida) {
    partes.push(`Cuando un cliente escriba por primera vez salúdalo así: "${c.bienvenida}"`);
  }

  // --- RESTRICCIONES ---
  partes.push(
    `RESTRICCIONES IMPORTANTES:\n` +
    `• Nunca inventes precios, primas ni coberturas específicas.\n` +
    `• Nunca prometas aprobación de una póliza.\n` +
    `• No proporciones datos de clientes de terceros.\n` +
    `• Si no sabes algo, dilo honestamente y ofrece conectar con un asesor.\n` +
    (c.restricciones ? `• ${c.restricciones}` : '')
  );

  // --- INSTRUCCIONES ADICIONALES ---
  if ((cfg.instrucciones || '').trim()) {
    partes.push(cfg.instrucciones.trim());
  }

  // --- BASE DE CONOCIMIENTO (FAQs) ---
  if (faqs && faqs.length > 0) {
    const faqTexto = faqs.map(f => `P: ${f.pregunta}\nR: ${f.respuesta}`).join('\n\n');
    partes.push(`BASE DE CONOCIMIENTO:\n${faqTexto}`);
  }

  // --- SLOTS DE CALENDARIO ---
  if (slotsInfo && slotsInfo.texto) {
    partes.push(
      slotsInfo.texto +
      '\nSi el cliente quiere agendar, usa la función "agendar_cita" con el índice del slot elegido (0-based).'
    );
  }

  return partes.join('\n\n');
}

function buildMessages(systemPrompt, mensajes) {
  const messages = [{ role: 'system', content: systemPrompt }];
  for (const m of [...mensajes].reverse()) {
    messages.push({
      role: m.autor === 'cliente' ? 'user' : 'assistant',
      content: m.contenido,
    });
  }
  return messages;
}

module.exports = { buildSystemPrompt, buildMessages };
