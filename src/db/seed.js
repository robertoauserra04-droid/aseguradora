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
  {
    nombre: 'Gabriela Ríos Montemayor',
    telefono: '+528112345616',
    tipo: 'medical',
    estado: 'inicio',
    prioridad: 'alta',
    requiere_respuesta: true,
    mensajes: [
      { autor: 'cliente', contenido: 'Hola buenas tardes, acabo de tener un bebé y quiero incluirlo en mi seguro médico', horas: 2 },
    ],
  },
  {
    nombre: 'Ernesto Sánchez Blanco',
    telefono: '+528112345617',
    tipo: 'auto',
    estado: 'inicio',
    prioridad: 'normal',
    mensajes: [
      { autor: 'cliente', contenido: 'Me recomendaron con ustedes para asegurar una pickup Ram 2023', horas: 8 },
      { autor: 'agente', contenido: 'Hola Ernesto! Claro, con gusto. ¿Es de uso personal o de trabajo?', horas: 7 },
      { autor: 'cliente', contenido: 'Es de trabajo, la uso para mi empresa de construcción', horas: 6 },
    ],
  },
  {
    nombre: 'Claudia Espinoza Treviño',
    telefono: '+528112345618',
    tipo: 'vida',
    estado: 'cotizacion',
    prioridad: 'alta',
    mensajes: [
      { autor: 'cliente', contenido: 'Tengo 42 años, quiero un seguro de vida con cobertura de 3 millones', horas: 72 },
      { autor: 'agente', contenido: 'Perfecto Claudia, ¿tiene alguna enfermedad crónica o ha sido hospitalizada recientemente?', horas: 70 },
      { autor: 'cliente', contenido: 'No, estoy completamente sana. Solo tomo vitaminas', horas: 68 },
      { autor: 'agente', contenido: 'Excelente. Te estoy cotizando con Metlife, Monterrey y Seguros Banamex', horas: 48 },
    ],
  },
  {
    nombre: 'Ricardo Longoria Garza',
    telefono: '+528112345619',
    tipo: 'daño',
    estado: 'cotizacion',
    prioridad: 'normal',
    mensajes: [
      { autor: 'cliente', contenido: 'Quiero asegurar mi bodega industrial, tiene equipos de refrigeración', horas: 96 },
      { autor: 'agente', contenido: '¿Cuál es el valor aproximado del contenido y del inmueble?', horas: 95 },
      { autor: 'cliente', contenido: 'El inmueble vale como 8 millones y el equipo otros 4 millones', horas: 94 },
      { autor: 'agente', contenido: 'Entendido, ya estoy armando la cotización de daños. Te escribo mañana', horas: 72 },
    ],
  },
  {
    nombre: 'Karla Gutiérrez Peña',
    telefono: '+528112345620',
    tipo: 'medical',
    estado: 'tramite_oficina',
    prioridad: 'alta',
    mensajes: [
      { autor: 'cliente', contenido: 'Ya decidí, me quedo con el plan familiar de GNP', horas: 120 },
      { autor: 'agente', contenido: 'Perfecto Karla, necesito que llenes la solicitud de afiliación. Te la mando ahora', horas: 119 },
      { autor: 'cliente', contenido: 'Ya la llené y te la mandé por correo', horas: 96 },
      { autor: 'agente', contenido: 'La recibí, estamos procesando tu solicitud en oficinas. En 2-3 días hábiles confirmo', horas: 72 },
    ],
  },
  {
    nombre: 'Javier Tello Acosta',
    telefono: '+528112345621',
    tipo: 'auto',
    estado: 'tramite_oficina',
    prioridad: 'normal',
    mensajes: [
      { autor: 'cliente', contenido: 'Aquí te mando la factura de mi carro y mi licencia escaneada', horas: 48 },
      { autor: 'agente', contenido: 'Los recibí Javier. ¿Puedes también mandarnos foto del carro por los 4 lados?', horas: 47 },
      { autor: 'cliente', contenido: 'Listo, ya te las mandé por WhatsApp', horas: 24 },
      { autor: 'agente', contenido: 'Todo correcto, ya subimos tu expediente a Qualitas. Esperamos su validación', horas: 20 },
    ],
  },
  {
    nombre: 'Natalia Berumen Flores',
    telefono: '+528112345622',
    tipo: 'vida',
    estado: 'tramite_aseguradora',
    prioridad: 'alta',
    mensajes: [
      { autor: 'agente', contenido: 'Natalia, ya mandamos tu solicitud a Metlife. Nos pidieron un examen médico', horas: 96 },
      { autor: 'cliente', contenido: '¿A dónde voy para el examen?', horas: 90 },
      { autor: 'agente', contenido: 'Puedes ir al laboratorio Médica Norte en San Pedro, ellos ya tienen la orden', horas: 88 },
      { autor: 'cliente', contenido: 'Ya fui, me lo hicieron hoy en la mañana', horas: 10 },
      { autor: 'agente', contenido: 'Perfecto, ahora esperamos que Metlife reciba y apruebe los resultados (3-5 días)', horas: 9 },
    ],
  },
  {
    nombre: 'Óscar Martínez Zavala',
    telefono: '+528112345623',
    tipo: 'medical',
    estado: 'tramite_aseguradora',
    prioridad: 'normal',
    mensajes: [
      { autor: 'agente', contenido: 'Óscar, AXA nos solicitó información adicional sobre la condición de tu esposa', horas: 72 },
      { autor: 'cliente', contenido: 'Claro, ¿qué necesitan exactamente?', horas: 60 },
      { autor: 'agente', contenido: 'Necesitan el historial clínico de los últimos 2 años y la carta de su médico', horas: 58 },
      { autor: 'cliente', contenido: 'Ok, lo estoy consiguiendo con su médico, me lo dan en 3 días', horas: 12 },
    ],
  },
  {
    nombre: 'Paola Hinojosa Vidal',
    telefono: '+528112345624',
    tipo: 'auto',
    estado: 'entrega',
    prioridad: 'normal',
    mensajes: [
      { autor: 'agente', contenido: 'Paola, ya tenemos tu póliza lista. La cobertura empieza mañana a las 00:01', horas: 24 },
      { autor: 'cliente', contenido: 'Qué bueno! ¿Me mandan el documento al correo?', horas: 20 },
      { autor: 'agente', contenido: 'Ya te la mandé a tu Gmail. También te mando la tarjeta de circulación digital', horas: 18 },
      { autor: 'cliente', contenido: 'La recibí, muchas gracias por todo', horas: 15 },
    ],
  },
  {
    nombre: 'Armando Cisneros Luna',
    telefono: '+528112345625',
    tipo: 'daño',
    estado: 'vigente',
    prioridad: 'normal',
    numero_poliza: 'HDI-2024-336699',
    mensajes: [
      { autor: 'sistema', contenido: 'Póliza de daños activada. Cobertura: incendio, robo, inundación. Vigencia 12 meses', horas: 500 },
      { autor: 'cliente', contenido: '¿Cómo reporto un siniestro si llegara a pasar?', horas: 240 },
      { autor: 'agente', contenido: 'Llamas al 800-HDI-AYUDA las 24hrs. También puedes abrir el reporte en su app móvil', horas: 239 },
    ],
  },
  {
    nombre: 'Sandra Medina Quiroga',
    telefono: '+528112345626',
    tipo: 'medical',
    estado: 'vigente',
    prioridad: 'normal',
    numero_poliza: 'AXA-2025-778899',
    mensajes: [
      { autor: 'cliente', contenido: 'Hola, quiero saber si mi póliza cubre cirugía de rodilla', horas: 72 },
      { autor: 'agente', contenido: 'Hola Sandra, tu plan cubre cirugías ortopédicas sí. ¿Ya tienes diagnóstico del médico?', horas: 70 },
      { autor: 'cliente', contenido: 'Sí, el ortopedista dice que necesito artroscopía', horas: 68 },
      { autor: 'agente', contenido: 'Perfecto, necesitas preautorización. Te explico el proceso paso a paso', horas: 67 },
    ],
  },
  {
    nombre: 'Francisco Alvarado Ruiz',
    telefono: '+528112345627',
    tipo: 'auto',
    estado: 'servicio',
    prioridad: 'critica',
    requiere_respuesta: true,
    numero_poliza: 'QUA-2024-112244',
    mensajes: [
      { autor: 'cliente', contenido: 'Tuve un choque, ¿qué hago?', horas: 5 },
      { autor: 'agente', contenido: 'Francisco, ¿estás bien? Lo primero es tu seguridad. ¿Hay lesionados?', horas: 4 },
      { autor: 'cliente', contenido: 'Todos bien gracias a Dios. Solo daños materiales', horas: 3 },
      { autor: 'agente', contenido: 'Qué bueno. Ya abrí tu siniestro en Qualitas, folio #Q2024-8834. El ajustador llega en 45 min', horas: 2 },
      { autor: 'cliente', contenido: '¿Y el otro carro queda cubierto también?', horas: 1 },
    ],
  },
  {
    nombre: 'Teresa Longoria Cantú',
    telefono: '+528112345628',
    tipo: 'medical',
    estado: 'servicio',
    prioridad: 'alta',
    numero_poliza: 'GNP-2025-445500',
    mensajes: [
      { autor: 'cliente', contenido: 'Mi hijo está hospitalizado y no sé cómo activar el seguro', horas: 12 },
      { autor: 'agente', contenido: 'Teresa, con calma. ¿En qué hospital están?', horas: 11 },
      { autor: 'cliente', contenido: 'Estamos en el Hospital Christus Muguerza', horas: 10 },
      { autor: 'agente', contenido: 'Perfecto, ese hospital es de la red GNP. Ya le avisé a admisiones, solo muestra tu tarjeta de asegurado', horas: 9 },
      { autor: 'cliente', contenido: 'Muchas gracias, ya nos atendieron sin problema', horas: 6 },
    ],
  },
  {
    nombre: 'Benjamín Ortega Salinas',
    telefono: '+528112345629',
    tipo: 'vida',
    estado: 'renovacion',
    prioridad: 'alta',
    requiere_respuesta: true,
    numero_poliza: 'MET-2023-667788',
    fecha_vencimiento: 10,
    mensajes: [
      { autor: 'sistema', contenido: 'Póliza próxima a vencer en 10 días', horas: 72 },
      { autor: 'agente', contenido: 'Hola Benjamín, tu seguro de vida vence el 22 de junio. ¿Renovamos en las mismas condiciones?', horas: 48 },
      { autor: 'cliente', contenido: '¿Puede quedar con mayor suma asegurada? Quiero subir a 2 millones', horas: 6 },
    ],
  },
  {
    nombre: 'Lorena Cavazos Ibarra',
    telefono: '+528112345630',
    tipo: 'auto',
    estado: 'renovacion',
    prioridad: 'normal',
    numero_poliza: 'AXA-2023-990011',
    fecha_vencimiento: 25,
    mensajes: [
      { autor: 'agente', contenido: 'Lorena, te recuerdo que tu póliza de auto vence en 25 días. ¿Renovamos?', horas: 48 },
      { autor: 'cliente', contenido: 'Sí claro, ¿el precio sube mucho este año?', horas: 24 },
      { autor: 'agente', contenido: 'Hay un ajuste del 8% por inflación, quedaría en $9,200 anuales. ¿Procedemos?', horas: 20 },
      { autor: 'cliente', contenido: 'Está bien, va. ¿Cómo pago?', horas: 16 },
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

module.exports = { runSeed, runSeedForce, limpiarDatos };
