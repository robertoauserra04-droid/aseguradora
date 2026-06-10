const crypto = require('crypto');

// Etapas principales con sus subestados
const ETAPAS = {
  inicio: {
    key: 'inicio',
    label: 'Inicio',
    color: '#3B82F6',
    orden: 1,
    estados: [
      { key: 'solicitud_recibida',    label: 'Solicitud recibida',    orden: 1 },
      { key: 'prospecto_creado',      label: 'Prospecto creado',      orden: 2 },
      { key: 'informacion_pendiente', label: 'Información pendiente', orden: 3 },
    ],
  },
  cotizacion: {
    key: 'cotizacion',
    label: 'Cotización',
    color: '#8B5CF6',
    orden: 2,
    estados: [
      { key: 'cotizando',            label: 'Cotizando',              orden: 1 },
      { key: 'propuestas_recibidas', label: 'Propuestas recibidas',   orden: 2 },
      { key: 'presentada_cliente',   label: 'Presentada al cliente',  orden: 3 },
    ],
  },
  tramite_oficina: {
    key: 'tramite_oficina',
    label: 'Trámite Oficina',
    color: '#F59E0B',
    orden: 3,
    estados: [
      { key: 'documentacion_completa', label: 'Documentación completa',   orden: 1 },
      { key: 'solicitud_firmada',      label: 'Solicitud firmada',        orden: 2 },
      { key: 'integracion_expediente', label: 'Integración de expediente', orden: 3 },
    ],
  },
  tramite_aseguradora: {
    key: 'tramite_aseguradora',
    label: 'Trámite Aseguradora',
    color: '#EC4899',
    orden: 4,
    estados: [
      { key: 'en_emision',            label: 'En emisión',          orden: 1 },
      { key: 'en_dictamen',           label: 'En dictamen',         orden: 2 },
      { key: 'requisitos_pendientes', label: 'Requisitos pendientes', orden: 3 },
      { key: 'emitida',               label: 'Emitida',             orden: 4 },
    ],
  },
  entrega: {
    key: 'entrega',
    label: 'Entrega',
    color: '#F97316',
    orden: 5,
    estados: [
      { key: 'pago_pendiente',    label: 'Pago pendiente',    orden: 1 },
      { key: 'pago_confirmado',   label: 'Pago confirmado',   orden: 2 },
      { key: 'entrega_realizada', label: 'Entrega realizada', orden: 3 },
      { key: 'acuse_recibido',    label: 'Acuse recibido',    orden: 4 },
    ],
  },
  vigente: {
    key: 'vigente',
    label: 'Vigente',
    color: '#10B981',
    orden: 6,
    estados: [
      { key: 'poliza_activa',        label: 'Póliza activa',        orden: 1 },
      { key: 'sin_eventos_abiertos', label: 'Sin eventos abiertos', orden: 2 },
    ],
  },
  servicio: {
    key: 'servicio',
    label: 'Servicio / Siniestro',
    color: '#06B6D4',
    orden: 7,
    estados: [
      { key: 'endoso',                label: 'Endoso',                  orden: 1 },
      { key: 'cambio_datos',          label: 'Cambio de datos',         orden: 2 },
      { key: 'alta_baja_asegurados',  label: 'Alta/Baja de asegurados', orden: 3 },
      { key: 'reclamacion',           label: 'Reclamación',             orden: 4 },
      { key: 'seguimiento_siniestro', label: 'Seguimiento de siniestro', orden: 5 },
    ],
  },
  renovacion: {
    key: 'renovacion',
    label: 'Renovación',
    color: '#EF4444',
    orden: 8,
    estados: [
      { key: 'renovacion_90dias',     label: '90 días antes',           orden: 1 },
      { key: 'cotizacion_renovacion', label: 'Cotización renovación',   orden: 2 },
      { key: 'negociacion',           label: 'Negociación',             orden: 3 },
      { key: 'renovada',              label: 'Renovada',                orden: 4 },
      { key: 'no_renovada',           label: 'No renovada',             orden: 5 },
      { key: 'cancelada',             label: 'Cancelada',               orden: 6 },
    ],
  },
};

// Mapa plano estado_key → { label, color, etapa_key }
const ESTADOS = {};
for (const [etapaKey, etapa] of Object.entries(ETAPAS)) {
  for (const est of etapa.estados) {
    ESTADOS[est.key] = {
      key:       est.key,
      label:     est.label,
      color:     etapa.color,
      etapa:     etapaKey,
      etapaLabel: etapa.label,
      orden:     etapa.orden * 100 + est.orden,
    };
  }
}

// Migración de estados viejos a nuevos
const MIGRACION_ESTADOS = {
  prospectiva:        'prospecto_creado',
  diagnostico:        'informacion_pendiente',
  cotizacion_proceso: 'cotizando',
  propuesta_enviada:  'presentada_cliente',
  propuesta_final:    'solicitud_firmada',
  documentacion:      'documentacion_completa',
  poliza_activa:      'poliza_activa',
  gestion_continua:   'sin_eventos_abiertos',
  renovacion:         'renovacion_90dias',
  renovado_activo:    'renovada',
  churn:              'no_renovada',
};

function getEtapaFromEstado(estadoKey) {
  const est = ESTADOS[estadoKey];
  if (!est) return null;
  return ETAPAS[est.etapa] || null;
}

function verifyKapsoSignature(rawBody, signature, secret) {
  if (!signature || !secret) return false;
  const expectedSignature =
    'sha256=' +
    crypto.createHmac('sha256', secret).update(rawBody, 'utf8').digest('hex');
  try {
    return crypto.timingSafeEqual(
      Buffer.from(signature),
      Buffer.from(expectedSignature)
    );
  } catch {
    return false;
  }
}

function detectarTipoSeguro(contenido) {
  if (!contenido) return null;
  const texto = contenido.toLowerCase();

  if (texto.includes('vida') || texto.includes('seguro de vida')) return 'vida';
  if (
    texto.includes('auto') ||
    texto.includes('carro') ||
    texto.includes('vehículo') ||
    texto.includes('vehiculo')
  )
    return 'auto';
  if (
    texto.includes('médico') ||
    texto.includes('medico') ||
    texto.includes('salud') ||
    texto.includes('gastos médicos') ||
    texto.includes('gastos medicos')
  )
    return 'medical';
  if (texto.includes('daño') || texto.includes('daños') || texto.includes('dano'))
    return 'daño';
  if (texto.includes('viaje') || texto.includes('viajar')) return 'viaje';

  return null;
}

function esEstadoValido(estado) {
  return Object.keys(ESTADOS).includes(estado);
}

module.exports = { ESTADOS, ETAPAS, MIGRACION_ESTADOS, verifyKapsoSignature, detectarTipoSeguro, esEstadoValido, getEtapaFromEstado };
