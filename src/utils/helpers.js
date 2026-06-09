const crypto = require('crypto');

const ESTADOS = {
  prospectiva: {
    key: 'prospectiva',
    label: 'Prospectiva',
    color: '#3B82F6',
    orden: 1,
    descripcion: 'Nuevo contacto, sin información de necesidad',
  },
  diagnostico: {
    key: 'diagnostico',
    label: 'Levantamiento de Información',
    color: '#8B5CF6',
    orden: 2,
    descripcion: 'Recopilando datos del cliente',
  },
  cotizacion_proceso: {
    key: 'cotizacion_proceso',
    label: 'Cotización en Proceso',
    color: '#F59E0B',
    orden: 3,
    descripcion: 'Esperando cotización de aseguradoras',
  },
  propuesta_enviada: {
    key: 'propuesta_enviada',
    label: 'Propuesta Enviada',
    color: '#EC4899',
    orden: 4,
    descripcion: 'Propuesta enviada, cliente en revisión',
  },
  propuesta_final: {
    key: 'propuesta_final',
    label: 'Propuesta Final',
    color: '#F97316',
    orden: 5,
    descripcion: 'Acuerdo alcanzado, listo para firmar',
  },
  documentacion: {
    key: 'documentacion',
    label: 'Contratación / Documentación',
    color: '#6366F1',
    orden: 6,
    descripcion: 'Documentos en firma, falta pago',
  },
  poliza_activa: {
    key: 'poliza_activa',
    label: 'Póliza Activa - Onboarding',
    color: '#10B981',
    orden: 7,
    descripcion: 'Póliza vigente, cliente en incorporación',
  },
  gestion_continua: {
    key: 'gestion_continua',
    label: 'Gestión / Mantenimiento',
    color: '#06B6D4',
    orden: 8,
    descripcion: 'Póliza activa, consultas y cambios',
  },
  renovacion: {
    key: 'renovacion',
    label: 'Renovación - Retención',
    color: '#EF4444',
    orden: 9,
    descripcion: 'Póliza próxima a vencer',
  },
  renovado_activo: {
    key: 'renovado_activo',
    label: 'Renovado / Activo',
    color: '#22C55E',
    orden: 10,
    descripcion: 'Póliza renovada, cliente retenido',
  },
  churn: {
    key: 'churn',
    label: 'Perdido / Churn',
    color: '#64748B',
    orden: 11,
    descripcion: 'Cliente no renovó',
  },
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

module.exports = { ESTADOS, verifyKapsoSignature, detectarTipoSeguro, esEstadoValido };
