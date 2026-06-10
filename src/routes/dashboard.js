const express = require('express');
const db = require('../config/database');
const { authenticateAgent } = require('../middleware/auth');

const router = express.Router();

router.get('/dashboard/kpis', authenticateAgent, async (req, res) => {
  try {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);

    const [
      porEstado,
      hoyNuevos,
      hoyPropuestas,
      hoyPolizas,
      pendientesAhora,
      criticas,
    ] = await Promise.all([
      db.query(
        `SELECT estado, COUNT(*) AS total
         FROM conversaciones
         WHERE activo = true
         GROUP BY estado`
      ),
      db.query(
        `SELECT COUNT(*) AS total FROM conversaciones WHERE created_at >= $1`,
        [hoy]
      ),
      db.query(
        `SELECT COUNT(*) AS total FROM cambios_estado_historico
         WHERE estado_nuevo IN ('presentada_cliente','propuesta_enviada') AND timestamp >= $1`,
        [hoy]
      ),
      db.query(
        `SELECT COUNT(*) AS total FROM cambios_estado_historico
         WHERE estado_nuevo IN ('poliza_activa','emitida') AND timestamp >= $1`,
        [hoy]
      ),
      db.query(
        `SELECT COUNT(*) AS total FROM conversaciones
         WHERE requiere_respuesta = true AND activo = true
           AND estado NOT IN ('no_renovada','cancelada','churn')`
      ),
      db.query(
        `SELECT c.id, c.cliente_nombre, c.estado, c.prioridad,
                EXTRACT(EPOCH FROM (NOW() - c.ultimo_mensaje_at)) / 3600 AS horas_sin_respuesta,
                m.contenido AS ultimo_mensaje
         FROM conversaciones c
         LEFT JOIN LATERAL (
           SELECT contenido FROM mensajes
           WHERE conversacion_id = c.id
           ORDER BY timestamp_mensaje DESC LIMIT 1
         ) m ON true
         WHERE c.requiere_respuesta = true AND c.activo = true
           AND c.estado NOT IN ('no_renovada','cancelada','churn')
         ORDER BY horas_sin_respuesta DESC
         LIMIT 10`
      ),
    ]);

    const conversaciones_por_estado = {};
    for (const row of porEstado.rows) {
      conversaciones_por_estado[row.estado] = parseInt(row.total, 10);
    }

    res.json({
      hoy: {
        nuevos_contactos: parseInt(hoyNuevos.rows[0].total, 10),
        pendientes_ahora: parseInt(pendientesAhora.rows[0].total, 10),
        propuestas_enviadas: parseInt(hoyPropuestas.rows[0].total, 10),
        polizas_activadas: parseInt(hoyPolizas.rows[0].total, 10),
      },
      conversaciones_por_estado,
      conversaciones_criticas: criticas.rows.map((r) => ({
        id: r.id,
        cliente_nombre: r.cliente_nombre,
        estado: r.estado,
        horas_sin_respuesta: Math.round(parseFloat(r.horas_sin_respuesta)),
        prioridad: r.prioridad,
        ultimo_mensaje: r.ultimo_mensaje,
      })),
    });
  } catch (err) {
    console.error('Error GET /dashboard/kpis:', err);
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

module.exports = router;
