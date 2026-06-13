const express = require('express');
const db = require('../config/database');
const { authenticateAgent } = require('../middleware/auth');

const router = express.Router();

// Colores por tipo de evento
const COLORS = {
  poliza_vigente:      '#10B981', // verde
  poliza_vencimiento:  '#EF4444', // rojo
  cotizacion:          '#F97316', // naranja
  tramite:             '#3B82F6', // azul
  renovacion:          '#EF4444', // rojo
};

// GET /api/calendario/eventos
router.get('/calendario/eventos', authenticateAgent, async (req, res) => {
  try {
    const { start, end } = req.query;

    const eventos = [];

    // --- Pólizas: fecha inicio ---
    const polizasInicioResult = await db.query(
      `SELECT id, cliente_nombre, tipo_seguro, numero_poliza, fecha_inicio_poliza
       FROM conversaciones
       WHERE fecha_inicio_poliza IS NOT NULL AND activo = true
       ${start ? 'AND fecha_inicio_poliza >= $1' : ''}
       ${end   ? `AND fecha_inicio_poliza <= $${start ? 2 : 1}` : ''}
       ORDER BY fecha_inicio_poliza`,
      [start, end].filter(Boolean)
    );

    for (const row of polizasInicioResult.rows) {
      eventos.push({
        id:    `poliza-inicio-${row.id}`,
        title: `Inicio póliza: ${row.cliente_nombre}${row.tipo_seguro ? ` (${row.tipo_seguro})` : ''}`,
        start: row.fecha_inicio_poliza,
        color: COLORS.poliza_vigente,
        extendedProps: {
          tipo:            'poliza_inicio',
          conversacion_id: row.id,
          numero_poliza:   row.numero_poliza,
        },
      });
    }

    // --- Pólizas: fecha vencimiento ---
    const polizasVencResult = await db.query(
      `SELECT id, cliente_nombre, tipo_seguro, numero_poliza, fecha_vencimiento_poliza,
              fecha_vencimiento_poliza - NOW()::date AS dias_restantes
       FROM conversaciones
       WHERE fecha_vencimiento_poliza IS NOT NULL AND activo = true
       ${start ? 'AND fecha_vencimiento_poliza >= $1' : ''}
       ${end   ? `AND fecha_vencimiento_poliza <= $${start ? 2 : 1}` : ''}
       ORDER BY fecha_vencimiento_poliza`,
      [start, end].filter(Boolean)
    );

    for (const row of polizasVencResult.rows) {
      const proxima = parseInt(row.dias_restantes) <= 30;
      eventos.push({
        id:    `poliza-venc-${row.id}`,
        title: `Vence póliza: ${row.cliente_nombre}${row.tipo_seguro ? ` (${row.tipo_seguro})` : ''}`,
        start: row.fecha_vencimiento_poliza,
        color: proxima ? COLORS.poliza_vencimiento : COLORS.poliza_vigente,
        extendedProps: {
          tipo:            'poliza_vencimiento',
          conversacion_id: row.id,
          numero_poliza:   row.numero_poliza,
          dias_restantes:  row.dias_restantes,
        },
      });
    }

    // --- Cotizaciones por vencer ---
    const cotizacionesResult = await db.query(
      `SELECT co.id, co.aseguradora, co.fecha_vencimiento,
              c.id as conv_id, c.cliente_nombre, c.tipo_seguro
       FROM cotizaciones co
       JOIN conversaciones c ON c.id = co.conversacion_id
       WHERE co.fecha_vencimiento IS NOT NULL AND co.estado NOT IN ('rechazada')
       ${start ? 'AND co.fecha_vencimiento >= $1' : ''}
       ${end   ? `AND co.fecha_vencimiento <= $${start ? 2 : 1}` : ''}
       ORDER BY co.fecha_vencimiento`,
      [start, end].filter(Boolean)
    );

    for (const row of cotizacionesResult.rows) {
      eventos.push({
        id:    `cotizacion-${row.id}`,
        title: `Cotización vence: ${row.cliente_nombre} — ${row.aseguradora}`,
        start: row.fecha_vencimiento,
        color: COLORS.cotizacion,
        extendedProps: {
          tipo:            'cotizacion',
          conversacion_id: row.conv_id,
          aseguradora:     row.aseguradora,
        },
      });
    }

    // --- Conversaciones en trámite (fecha de cambio de estado) ---
    const tramitesResult = await db.query(
      `SELECT id, cliente_nombre, tipo_seguro, estado, fecha_cambio_estado
       FROM conversaciones
       WHERE estado IN ('tramite_oficina', 'tramite_aseguradora', 'entrega')
         AND fecha_cambio_estado IS NOT NULL AND activo = true
       ORDER BY fecha_cambio_estado`
    );

    for (const row of tramitesResult.rows) {
      const labels = {
        tramite_oficina:     'Trámite Oficina',
        tramite_aseguradora: 'Trámite Aseguradora',
        entrega:             'Entrega',
      };
      eventos.push({
        id:    `tramite-${row.id}`,
        title: `${labels[row.estado] || row.estado}: ${row.cliente_nombre}`,
        start: row.fecha_cambio_estado,
        color: COLORS.tramite,
        extendedProps: {
          tipo:            'tramite',
          conversacion_id: row.id,
          estado:          row.estado,
        },
      });
    }

    // --- Renovaciones próximas ---
    const renovacionesResult = await db.query(
      `SELECT id, cliente_nombre, tipo_seguro, fecha_vencimiento_poliza
       FROM conversaciones
       WHERE estado = 'renovacion' AND activo = true
       ORDER BY fecha_vencimiento_poliza`
    );

    for (const row of renovacionesResult.rows) {
      if (row.fecha_vencimiento_poliza) {
        eventos.push({
          id:    `renovacion-${row.id}`,
          title: `Renovación: ${row.cliente_nombre}${row.tipo_seguro ? ` (${row.tipo_seguro})` : ''}`,
          start: row.fecha_vencimiento_poliza,
          color: COLORS.renovacion,
          extendedProps: {
            tipo:            'renovacion',
            conversacion_id: row.id,
          },
        });
      }
    }

    res.json(eventos);
  } catch (err) {
    console.error('[Calendario] Error:', err.message);
    res.status(500).json({ error: 'Error al cargar eventos del calendario' });
  }
});

module.exports = router;
