const db = require('../config/database');

const conversacionesPrueba = [
  {
    nombre: 'Carlos Méndez Ruiz',
    telefono: '+528112345601',
    tipo: 'vida',
    estado: 'inicio',
    prioridad: 'normal',
    mensajes: [
      { autor: 'cliente', contenido: 'Hola, quiero información sobre seguros de vida', horas: 5 },
    ],
  },
  {
    nombre: 'María González López',
    telefono: '+528112345602',
    tipo: 'medical',
    estado: 'inicio',
    prioridad: 'alta',
    mensajes: [
      { autor: 'cliente', contenido: 'Buenos días, me interesa un seguro de gastos médicos para mi familia', horas: 10 },
      { autor: 'agente', contenido: '¡Hola María! Con gusto te ayudo. ¿Cuántas personas incluiría la póliza?', horas: 9 },
      { autor: 'cliente', contenido: 'Somos 4: mi esposo, yo y 2 hijos de 8 y 12 años', horas: 8 },
      { autor: 'agente', contenido: 'Perfecto, ¿tienen alguna condición preexistente?', horas: 7 },
      { autor: 'cliente', contenido: 'No ninguna, estamos todos sanos', horas: 6 },
    ],
  },
  {
    nombre: 'Roberto Salinas',
    telefono: '+528112345603',
    tipo: 'auto',
    estado: 'cotizacion',
    prioridad: 'normal',
    mensajes: [
      { autor: 'cliente', contenido: 'Necesito asegurar mi carro, es un Nissan Versa 2022', horas: 24 },
      { autor: 'agente', contenido: 'Claro Roberto, ¿tiene algún siniestro previo?', horas: 23 },
      { autor: 'cliente', contenido: 'No, es mi primer seguro', horas: 22 },
      { autor: 'agente', contenido: 'Excelente, ya estoy cotizando con GNP, Qualitas y AXA. Te mando resultados pronto', horas: 21 },
    ],
  },
  {
    nombre: 'Alejandra Torres',
    telefono: '+528112345604',
    tipo: 'vida',
    estado: 'cotizacion',
    prioridad: 'alta',
    requiere_respuesta: true,
    mensajes: [
      { autor: 'cliente', contenido: 'Me interesa un seguro de vida, tengo 35 años', horas: 48 },
      { autor: 'agente', contenido: 'Hola Alejandra, tengo una excelente propuesta para ti', horas: 36 },
      { autor: 'agente', contenido: 'Te envié por WhatsApp las cotizaciones de Metlife y Seguros Monterrey', horas: 35 },
      { autor: 'cliente', contenido: '¿Cuánto tiempo tengo para decidir?', horas: 3 },
    ],
  },
  {
    nombre: 'Fernando Ibarra Castillo',
    telefono: '+528112345605',
    tipo: 'auto',
    estado: 'tramite_oficina',
    prioridad: 'critica',
    mensajes: [
      { autor: 'cliente', contenido: 'Ya revisé las cotizaciones, me convence la de Qualitas', horas: 72 },
      { autor: 'agente', contenido: '¡Perfecto Fernando! ¿Procedemos con el pago?', horas: 71 },
      { autor: 'cliente', contenido: 'Sí, ¿qué necesitan de mí?', horas: 70 },
      { autor: 'agente', contenido: 'Solo necesitamos tu factura del auto y licencia de manejo', horas: 69 },
      { autor: 'cliente', contenido: 'Ok ya los tengo, ¿a dónde los mando?', horas: 2 },
    ],
  },
  {
    nombre: 'Lucía Ramírez Vega',
    telefono: '+528112345606',
    tipo: 'medical',
    estado: 'entrega',
    prioridad: 'alta',
    mensajes: [
      { autor: 'cliente', contenido: 'Ya firmé los documentos que me mandaron', horas: 96 },
      { autor: 'agente', contenido: 'Perfecto Lucía, ya los recibimos. Solo falta el pago de la primera prima', horas: 94 },
      { autor: 'cliente', contenido: '¿Puedo pagar con tarjeta de crédito?', horas: 93 },
      { autor: 'agente', contenido: 'Sí, acepta Visa y Mastercard. Te mando el link de pago', horas: 92 },
    ],
  },
  {
    nombre: 'Jorge Herrera Muñoz',
    telefono: '+528112345607',
    tipo: 'vida',
    estado: 'vigente',
    prioridad: 'normal',
    numero_poliza: 'MET-2024-789456',
    mensajes: [
      { autor: 'sistema', contenido: 'Póliza activada correctamente. Vigencia: 12 meses', horas: 200 },
      { autor: 'cliente', contenido: '¿Ya puedo descargar mi póliza?', horas: 48 },
      { autor: 'agente', contenido: 'Sí Jorge, ya está disponible en tu email y también te la mandé por WhatsApp', horas: 47 },
    ],
  },
  {
    nombre: 'Sofía Morales',
    telefono: '+528112345608',
    tipo: 'medical',
    estado: 'vigente',
    prioridad: 'normal',
    numero_poliza: 'GNP-2023-112233',
    mensajes: [
      { autor: 'cliente', contenido: '¿Cómo hago válida mi póliza si necesito ir al médico?', horas: 120 },
      { autor: 'agente', contenido: 'Hola Sofía, llamas al 800-GNP-SALUD y te orientan. También puedes usar la app', horas: 119 },
      { autor: 'cliente', contenido: 'Gracias, muy amable', horas: 118 },
    ],
  },
  {
    nombre: 'Patricio Domínguez',
    telefono: '+528112345609',
    tipo: 'auto',
    estado: 'renovacion',
    prioridad: 'alta',
    requiere_respuesta: true,
    numero_poliza: 'QUA-2023-445566',
    fecha_vencimiento: 15,
    mensajes: [
      { autor: 'sistema', contenido: 'Póliza próxima a vencer en 15 días', horas: 48 },
      { autor: 'agente', contenido: 'Hola Patricio, tu seguro de auto vence el 24 de junio. ¿Lo renovamos?', horas: 24 },
    ],
  },
  {
    nombre: 'Daniela Fuentes',
    telefono: '+528112345610',
    tipo: 'vida',
    estado: 'renovacion',
    prioridad: 'baja',
    numero_poliza: 'MET-2024-998877',
    mensajes: [
      { autor: 'cliente', contenido: 'Gracias por el recordatorio, ya renové', horas: 240 },
      { autor: 'agente', contenido: '¡Perfecto Daniela! Tu nueva póliza ya está activa por 12 meses más', horas: 238 },
    ],
  },
  {
    nombre: 'Andrés Castillo Peña',
    telefono: '+528112345611',
    tipo: 'auto',
    estado: 'renovacion',
    prioridad: 'baja',
    mensajes: [
      { autor: 'agente', contenido: 'Hola Andrés, tu póliza venció hace 30 días. ¿Te gustaría renovarla?', horas: 720 },
      { autor: 'cliente', contenido: 'No gracias, ya contraté con otra aseguradora', horas: 715 },
    ],
  },
  {
    nombre: 'Valentina Cruz',
    telefono: '+528112345612',
    tipo: 'viaje',
    estado: 'inicio',
    prioridad: 'normal',
    requiere_respuesta: true,
    mensajes: [
      { autor: 'cliente', contenido: 'Hola! Voy a viajar a Europa en julio, ¿tienen seguro de viaje?', horas: 3 },
    ],
  },
  {
    nombre: 'Miguel Ángel Reyes',
    telefono: '+528112345613',
    tipo: 'daño',
    estado: 'cotizacion',
    prioridad: 'normal',
    mensajes: [
      { autor: 'cliente', contenido: 'Quiero asegurar mi negocio, es una taquería en Monterrey', horas: 36 },
      { autor: 'agente', contenido: '¿Cuántos metros cuadrados tiene el local?', horas: 35 },
      { autor: 'cliente', contenido: 'Como 80 metros, tenemos equipo de cocina y mesas', horas: 34 },
      { autor: 'agente', contenido: 'Perfecto, cotizando seguro de daños para tu negocio', horas: 33 },
    ],
  },
  {
    nombre: 'Isabel Navarro',
    telefono: '+528112345614',
    tipo: 'medical',
    estado: 'cotizacion',
    prioridad: 'normal',
    mensajes: [
      { autor: 'cliente', contenido: 'Soy freelancer y necesito seguro médico individual', horas: 60 },
      { autor: 'agente', contenido: 'Hola Isabel, te mandé 3 opciones por WhatsApp. ¿Las pudiste revisar?', horas: 24 },
      { autor: 'cliente', contenido: 'Sí las vi, la de AXA me parece bien', horas: 20 },
    ],
  },
  {
    nombre: 'Héctor Villanueva',
    telefono: '+528112345615',
    tipo: 'vida',
    estado: 'entrega',
    prioridad: 'critica',
    requiere_respuesta: true,
    mensajes: [
      { autor: 'agente', contenido: 'Héctor, ya tienes todo listo para activar tu póliza, solo falta el comprobante de pago', horas: 48 },
      { autor: 'cliente', contenido: 'Ya pagué, ¿a dónde mando el comprobante?', horas: 2 },
    ],
  },
];

async function limpiarDatos() {
  await db.query('DELETE FROM idempotencia_webhooks');
  await db.query('DELETE FROM cambios_estado_historico');
  await db.query('DELETE FROM cotizaciones');
  await db.query('DELETE FROM notas_internas');
  await db.query('DELETE FROM mensajes');
  await db.query('DELETE FROM conversaciones WHERE cliente_telefono LIKE \'+5281123456%\'');
}

async function insertarDatos() {
  console.log('[Seed] Insertando datos de prueba...');

    for (const conv of conversacionesPrueba) {
      const hoy = new Date();

      const vencimiento = conv.fecha_vencimiento
        ? new Date(hoy.getTime() + conv.fecha_vencimiento * 24 * 60 * 60 * 1000)
        : null;

      const result = await db.query(
        `INSERT INTO conversaciones
          (cliente_nombre, cliente_telefono, cliente_whatsapp_id, tipo_seguro,
           estado, prioridad, requiere_respuesta, numero_poliza,
           fecha_vencimiento_poliza, activo, created_at, updated_at, ultimo_mensaje_at)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,true,NOW(),NOW(),$10)
         RETURNING id`,
        [
          conv.nombre,
          conv.telefono,
          conv.telefono,
          conv.tipo,
          conv.estado,
          conv.prioridad || 'normal',
          conv.requiere_respuesta || false,
          conv.numero_poliza || null,
          vencimiento,
          new Date(hoy.getTime() - (conv.mensajes[conv.mensajes.length - 1]?.horas || 1) * 60 * 60 * 1000),
        ]
      );

      const convId = result.rows[0].id;

      for (const msg of conv.mensajes) {
        const ts = new Date(hoy.getTime() - msg.horas * 60 * 60 * 1000);
        await db.query(
          `INSERT INTO mensajes
            (conversacion_id, autor, nombre_autor, contenido, tipo_mensaje, timestamp_mensaje)
           VALUES ($1,$2,$3,$4,'text',$5)`,
          [
            convId,
            msg.autor,
            msg.autor === 'cliente' ? conv.nombre : msg.autor === 'agente' ? 'Agente Carguill' : 'Sistema',
            msg.contenido,
            ts,
          ]
        );
      }

      // Insertar cambio de estado inicial
      await db.query(
        `INSERT INTO cambios_estado_historico
          (conversacion_id, estado_anterior, estado_nuevo, realizado_por, nombre_quien_realizo, motivo)
         VALUES ($1,null,$2,'sistema','Sistema','Estado inicial')`,
        [convId, conv.estado]
      );
    }

    console.log(`[Seed] ${conversacionesPrueba.length} conversaciones de prueba insertadas`);
}

async function runSeed() {
  try {
    const existe = await db.query('SELECT COUNT(*) FROM conversaciones');
    if (parseInt(existe.rows[0].count, 10) > 0) {
      console.log('[Seed] Ya hay datos, omitiendo seed');
      return;
    }
    await insertarDatos();
  } catch (err) {
    console.error('[Seed] Error:', err.message);
  }
}

async function runSeedForce() {
  try {
    await limpiarDatos();
    await insertarDatos();
  } catch (err) {
    console.error('[Seed] Error forzado:', err.message);
    throw err;
  }
}

module.exports = { runSeed, runSeedForce };
