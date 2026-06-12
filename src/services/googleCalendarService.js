const { google } = require('googleapis');

const TIMEZONE = 'America/Monterrey';
const HORA_INICIO = 9;   // 9am
const HORA_FIN    = 18;  // 6pm

function getAuth() {
  const email = process.env.GOOGLE_CLIENT_EMAIL;
  const key   = process.env.GOOGLE_PRIVATE_KEY;
  if (!email || !key) return null;
  return new google.auth.GoogleAuth({
    credentials: {
      client_email: email,
      private_key:  key.replace(/\\n/g, '\n'),
    },
    scopes: ['https://www.googleapis.com/auth/calendar'],
  });
}

function getCalendar() {
  const auth = getAuth();
  if (!auth) return null;
  return google.calendar({ version: 'v3', auth });
}

function proximosDiasHabiles(n = 3) {
  const dias = [];
  const d = new Date();
  d.setDate(d.getDate() + 1);
  while (dias.length < n) {
    const dow = d.getDay();
    if (dow !== 0 && dow !== 6) dias.push(new Date(d));
    d.setDate(d.getDate() + 1);
  }
  return dias;
}

function fmtFecha(date) {
  return date.toLocaleDateString('es-MX', {
    weekday: 'long', day: 'numeric', month: 'long', timeZone: TIMEZONE,
  });
}

async function consultarDisponibilidad() {
  const calendar  = getCalendar();
  const calId     = process.env.GOOGLE_CALENDAR_ID;
  if (!calendar || !calId) return { texto: '', slots: [] };

  const dias    = proximosDiasHabiles(3);
  const timeMin = new Date(dias[0]);   timeMin.setHours(0, 0, 0, 0);
  const timeMax = new Date(dias[dias.length - 1]); timeMax.setHours(23, 59, 59, 0);

  let busyPeriods = [];
  try {
    const fb = await calendar.freebusy.query({
      requestBody: {
        timeMin: timeMin.toISOString(),
        timeMax: timeMax.toISOString(),
        timeZone: TIMEZONE,
        items: [{ id: calId }],
      },
    });
    busyPeriods = fb.data.calendars[calId]?.busy || [];
  } catch (err) {
    console.error('[Calendar] freebusy error:', err.message);
  }

  const slots = [];
  for (const dia of dias) {
    for (let hora = HORA_INICIO; hora < HORA_FIN; hora++) {
      const inicio = new Date(dia); inicio.setHours(hora, 0, 0, 0);
      const fin    = new Date(dia); fin.setHours(hora + 1, 0, 0, 0);
      const ocupado = busyPeriods.some(b =>
        inicio < new Date(b.end) && fin > new Date(b.start)
      );
      if (!ocupado) slots.push({ inicio: inicio.toISOString(), fin: fin.toISOString(), label: `${fmtFecha(inicio)} a las ${hora}:00` });
    }
  }

  const mostrar = slots.slice(0, 6);
  const texto   = mostrar.length > 0
    ? 'Horarios disponibles:\n' + mostrar.map((s, i) => `${i + 1}. ${s.label}`).join('\n')
    : 'No hay horarios disponibles los próximos 3 días hábiles.';

  return { texto, slots: mostrar };
}

async function crearEvento({ titulo, descripcion, inicio, fin, emailCliente }) {
  const calendar = getCalendar();
  const calId    = process.env.GOOGLE_CALENDAR_ID;
  if (!calendar || !calId) throw new Error('Google Calendar no configurado');

  const event = {
    summary:     titulo,
    description: descripcion || '',
    start: { dateTime: inicio, timeZone: TIMEZONE },
    end:   { dateTime: fin,   timeZone: TIMEZONE },
    attendees:   emailCliente ? [{ email: emailCliente }] : [],
    reminders: { useDefault: false, overrides: [{ method: 'popup', minutes: 30 }] },
  };

  const r = await calendar.events.insert({
    calendarId:  calId,
    requestBody: event,
    sendUpdates: emailCliente ? 'all' : 'none',
  });
  return r.data;
}

const ETAPAS_EVENTO = {
  tramite_oficina:     'Trámite en oficina',
  tramite_aseguradora: 'Envío a aseguradora',
  entrega:             'Entrega de póliza',
  vigente:             'Póliza activa — seguimiento',
};

async function crearEventoEtapa(etapa, conversacion) {
  if (!ETAPAS_EVENTO[etapa]) return null;
  const calendar = getCalendar();
  const calId    = process.env.GOOGLE_CALENDAR_ID;
  if (!calendar || !calId) return null;

  const titulo      = `[${ETAPAS_EVENTO[etapa]}] ${conversacion.cliente_nombre}`;
  const descripcion = `Cliente: ${conversacion.cliente_nombre}\nTel: ${conversacion.cliente_telefono}\nTipo seguro: ${conversacion.tipo_seguro || 'No definido'}`;
  const manana      = new Date(); manana.setDate(manana.getDate() + 1);
  const fechaStr    = manana.toISOString().split('T')[0];

  try {
    const r = await calendar.events.insert({
      calendarId: calId,
      requestBody: {
        summary:     titulo,
        description: descripcion,
        start: { date: fechaStr },
        end:   { date: fechaStr },
        reminders: { useDefault: false, overrides: [{ method: 'popup', minutes: 60 }] },
      },
    });
    console.log(`[Calendar] Evento etapa "${etapa}" creado: ${r.data.id}`);
    return r.data;
  } catch (err) {
    console.error('[Calendar] Error evento etapa:', err.message);
    return null;
  }
}

module.exports = { consultarDisponibilidad, crearEvento, crearEventoEtapa };
