const schedule = require('node-schedule');
const db = require('../config/database');

async function detectarSinRespuesta() {
  try {
    const hace2Horas = new Date(Date.now() - 2 * 60 * 60 * 1000);

    const result = await db.query(
      `UPDATE conversaciones
       SET requiere_respuesta = true, prioridad = 'alta', updated_at = NOW()
       WHERE ultimo_mensaje_at < $1
         AND requiere_respuesta = false
         AND activo = true
         AND estado NOT IN ('churn', 'poliza_activa', 'gestion_continua', 'renovado_activo')
       RETURNING id`,
      [hace2Horas]
    );

    if (result.rows.length > 0) {
      console.log(`[Jobs] ${result.rows.length} conversaciones marcadas como requieren respuesta`);
    }
  } catch (err) {
    console.error('[Jobs] Error en detectarSinRespuesta:', err);
  }
}

async function detectarProximasRenovacion() {
  try {
    const en30Dias = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);

    const result = await db.query(
      `UPDATE conversaciones
       SET estado = 'renovacion', prioridad = 'alta', updated_at = NOW()
       WHERE fecha_vencimiento_poliza IS NOT NULL
         AND fecha_vencimiento_poliza <= $1
         AND estado = 'poliza_activa'
         AND activo = true
       RETURNING id`,
      [en30Dias]
    );

    if (result.rows.length > 0) {
      console.log(`[Jobs] ${result.rows.length} pólizas marcadas para renovación`);
    }
  } catch (err) {
    console.error('[Jobs] Error en detectarProximasRenovacion:', err);
  }
}

async function limpiarIdempotencia() {
  try {
    await db.query(
      `DELETE FROM idempotencia_webhooks WHERE processed_at < NOW() - INTERVAL '7 days'`
    );
  } catch (err) {
    console.error('[Jobs] Error en limpiarIdempotencia:', err);
  }
}

function iniciarJobs() {
  // Cada 30 minutos: detectar conversaciones sin respuesta
  setInterval(detectarSinRespuesta, 30 * 60 * 1000);

  // Diario a las 09:00: detectar pólizas próximas a vencer
  schedule.scheduleJob('0 9 * * *', detectarProximasRenovacion);

  // Diario a las 03:00: limpiar idempotencia vieja
  schedule.scheduleJob('0 3 * * *', limpiarIdempotencia);

  console.log('[Jobs] Background jobs iniciados');

  // Ejecutar inmediatamente al arrancar
  detectarSinRespuesta();
  detectarProximasRenovacion();
}

module.exports = { iniciarJobs, detectarSinRespuesta, detectarProximasRenovacion };
