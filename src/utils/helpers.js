const crypto = require('crypto');

// Solo 8 estados — uno por etapa, sin subestados
const ESTADOS = {
  inicio:              { key: 'inicio',              label: 'Inicio',               color: '#3B82F6', orden: 1 },
  cotizacion:          { key: 'cotizacion',          label: 'Cotización',           color: '#8B5CF6', orden: 2 },
  tramite_oficina:     { key: 'tramite_oficina',     label: 'Trámite Oficina',      color: '#F59E0B', orden: 3 },
  tramite_aseguradora: { key: 'tramite_aseguradora', label: 'Trámite Aseguradora',  color: '#EC4899', orden: 4 },
  entrega:             { key: 'entrega',             label: 'Entrega',              color: '#F97316', orden: 5 },
  vigente:             { key: 'vigente',             label: 'Vigente',              color: '#10B981', orden: 6 },
  servicio:            { key: 'servicio',            label: 'Servicio / Siniestro', color: '#06B6D4', orden: 7 },
  renovacion:          { key: 'renovacion',          label: 'Renovación',           color: '#EF4444', orden: 8 },
};

// Migración de TODOS los estados viejos (11 originales + 30 subestados) → 8 etapas
const MIGRACION_ESTADOS = {
  // 11 originales
  prospectiva:        'inicio',
  diagnostico:        'inicio',
  cotizacion_proceso: 'cotizacion',
  propuesta_enviada:  'cotizacion',
  propuesta_final:    'tramite_oficina',
  documentacion:      'tramite_oficina',
  poliza_activa:      'vigente',
  gestion_continua:   'vigente',
  renovado_activo:    'renovacion',
  churn:              'renovacion',
  // 30 subestados de la versión anterior
  solicitud_recibida:      'inicio',
  prospecto_creado:        'inicio',
  informacion_pendiente:   'inicio',
  cotizando:               'cotizacion',
  propuestas_recibidas:    'cotizacion',
  presentada_cliente:      'cotizacion',
  documentacion_completa:  'tramite_oficina',
  solicitud_firmada:       'tramite_oficina',
  integracion_expediente:  'tramite_oficina',
  en_emision:              'tramite_aseguradora',
  en_dictamen:             'tramite_aseguradora',
  requisitos_pendientes:   'tramite_aseguradora',
  emitida:                 'tramite_aseguradora',
  pago_pendiente:          'entrega',
  pago_confirmado:         'entrega',
  entrega_realizada:       'entrega',
  acuse_recibido:          'entrega',
  sin_eventos_abiertos:    'vigente',
  endoso:                  'servicio',
  cambio_datos:            'servicio',
  alta_baja_asegurados:    'servicio',
  reclamacion:             'servicio',
  seguimiento_siniestro:   'servicio',
  renovacion_90dias:       'renovacion',
  cotizacion_renovacion:   'renovacion',
  negociacion:             'renovacion',
  renovada:                'renovacion',
  no_renovada:             'renovacion',
  cancelada:               'renovacion',
};

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
  if (texto.includes('auto') || texto.includes('carro') || texto.includes('vehículo') || texto.includes('vehiculo')) return 'auto';
  if (texto.includes('médico') || texto.includes('medico') || texto.includes('salud') || texto.includes('gastos médicos') || texto.includes('gastos medicos')) return 'medical';
  if (texto.includes('daño') || texto.includes('daños') || texto.includes('dano')) return 'daño';
  if (texto.includes('viaje') || texto.includes('viajar')) return 'viaje';
  return null;
}

function esEstadoValido(estado) {
  return Object.keys(ESTADOS).includes(estado);
}

module.exports = { ESTADOS, MIGRACION_ESTADOS, verifyKapsoSignature, detectarTipoSeguro, esEstadoValido };
