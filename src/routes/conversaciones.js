const express = require('express');
const db = require('../config/database');
const { esEstadoValido } = require('../utils/helpers');
const { authenticateAgent } = require('../middleware/auth');

const router = express.Router();

// GET /api/conversaciones — lista con filtros
router.get('/conversaciones', authenticateAgent, async (req, res) => {
  try {
    const {
      estado,
      estados, // lista separada por coma para filtro por etapa
      tipo_seguro,
      agente_asignado,
      requiere_respuesta,
      search,
      limit = 50,
      offset = 0,
      sort_by = 'mas_reciente',
    } = req.query;

    const conditions = ['c.activo = true'];
    const params = [];
    let idx = 1;

    if (estado) {
      conditions.push(`c.estado = $${idx++}`);
      params.push(estado);
    } else if (estados) {
      const estadosList = estados.split(',').map(s => s.trim()).filter(Boolean);
      if (estadosList.length > 0) {
        const placeholders = estadosList.map(() => `$${idx++}`).join(', ');
        conditions.push(`c.estado IN (${placeholders})`);
        params.push(...estadosList);
      }
    }
    if (tipo_seguro) {
      conditions.push(`c.tipo_seguro = $${idx++}`);
      params.push(tipo_seguro);
    }
    if (agente_asignado) {
      conditions.push(`c.agente_asignado = $${idx++}`);
      params.push(agente_asignado);
    }
    if (requiere_respuesta !== undefined) {
      conditions.push(`c.requiere_respuesta = $${idx++}`);
      params.push(requiere_respuesta === 'true');
    }
    if (search) {
      conditions.push(
        `(c.cliente_nombre ILIKE $${idx} OR c.cliente_telefono ILIKE $${idx})`
      );
      params.push(`%${search}%`);
      idx++;
    }

    const where = conditions.length ? 'WHERE ' + conditions.join(' AND ') : '';

    const orderMap = {
      mas_reciente: 'c.ultimo_mensaje_at DESC NULLS LAST',
      mas_urgente: "CASE c.prioridad WHEN 'critica' THEN 0 WHEN 'alta' THEN 1 WHEN 'normal' THEN 2 WHEN 'baja' THEN 3 ELSE 4 END ASC",
      sin_respuesta: 'c.requiere_respuesta DESC, c.ultimo_mensaje_at ASC NULLS LAST',
    };
    const order = orderMap[sort_by] || orderMap.mas_reciente;

    const countResult = await db.query(
      `SELECT COUNT(*) FROM conversaciones c ${where}`,
      params
    );
    const total = parseInt(countResult.rows[0].count, 10);

    params.push(parseInt(limit, 10), parseInt(offset, 10));
    const dataResult = await db.query(
      `SELECT
         c.id, c.cliente_nombre, c.cliente_telefono, c.tipo_seguro,
         c.estado, c.agente_asignado, c.agente_nombre,
         c.requiere_respuesta, c.prioridad, c.dias_en_estado,
         c.created_at, c.updated_at, c.ultimo_mensaje_at,
         m.contenido AS ultimo_mensaje_contenido,
         m.timestamp_mensaje AS ultimo_mensaje_timestamp,
         m.autor AS ultimo_mensaje_autor
       FROM conversaciones c
       LEFT JOIN LATERAL (
         SELECT contenido, timestamp_mensaje, autor
         FROM mensajes
         WHERE conversacion_id = c.id
         ORDER BY timestamp_mensaje DESC
         LIMIT 1
       ) m ON true
       ${where}
       ORDER BY ${order}
       LIMIT $${idx++} OFFSET $${idx++}`,
      params
    );

    const conversaciones = dataResult.rows.map((r) => ({
      id: r.id,
      cliente_nombre: r.cliente_nombre,
      cliente_telefono: r.cliente_telefono,
      tipo_seguro: r.tipo_seguro,
      estado: r.estado,
      agente_asignado: r.agente_asignado,
      agente_nombre: r.agente_nombre,
      requiere_respuesta: r.requiere_respuesta,
      prioridad: r.prioridad,
      dias_en_estado: r.dias_en_estado,
      ultimo_mensaje: r.ultimo_mensaje_contenido
        ? {
            contenido: r.ultimo_mensaje_contenido,
            timestamp: r.ultimo_mensaje_timestamp,
            autor: r.ultimo_mensaje_autor,
          }
        : null,
      created_at: r.created_at,
      updated_at: r.updated_at,
    }));

    res.json({ conversaciones, total, limit: parseInt(limit), offset: parseInt(offset) });
  } catch (err) {
    console.error('Error GET /conversaciones:', err);
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

// GET /api/conversaciones/:id — detalle completo
router.get('/conversaciones/:id', authenticateAgent, async (req, res) => {
  try {
    const { id } = req.params;

    const convResult = await db.query('SELECT * FROM conversaciones WHERE id = $1', [id]);
    if (convResult.rows.length === 0) {
      return res.status(404).json({ error: 'Conversación no encontrada' });
    }

    const [mensajes, cotizaciones, notas, historial] = await Promise.all([
      db.query(
        `SELECT id, autor, nombre_autor, contenido, tipo_mensaje,
                timestamp_mensaje, palabras_clave, sentimiento, requiere_respuesta
         FROM mensajes WHERE conversacion_id = $1 ORDER BY timestamp_mensaje ASC`,
        [id]
      ),
      db.query(
        `SELECT id, aseguradora, prima, moneda, cobertura, estado,
                fecha_cotizacion, fecha_vencimiento
         FROM cotizaciones WHERE conversacion_id = $1 ORDER BY created_at DESC`,
        [id]
      ),
      db.query(
        `SELECT id, agente_nombre, contenido, created_at
         FROM notas_internas WHERE conversacion_id = $1 ORDER BY created_at DESC`,
        [id]
      ),
      db.query(
        `SELECT estado_anterior, estado_nuevo, realizado_por, nombre_quien_realizo, motivo, timestamp
         FROM cambios_estado_historico WHERE conversacion_id = $1 ORDER BY timestamp ASC`,
        [id]
      ),
    ]);

    res.json({
      conversacion: convResult.rows[0],
      mensajes: mensajes.rows,
      cotizaciones: cotizaciones.rows,
      notas: notas.rows,
      historial_estados: historial.rows,
    });
  } catch (err) {
    console.error('Error GET /conversaciones/:id:', err);
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

// POST /api/conversaciones/:id/estado — cambiar estado
router.post('/conversaciones/:id/estado', authenticateAgent, async (req, res) => {
  try {
    const { id } = req.params;
    const { estado_nuevo, motivo } = req.body;

    if (!estado_nuevo || !motivo) {
      return res.status(400).json({ error: 'estado_nuevo y motivo son requeridos' });
    }

    if (!esEstadoValido(estado_nuevo)) {
      return res.status(400).json({ error: `Estado inválido: ${estado_nuevo}` });
    }

    const convResult = await db.query(
      'SELECT id, estado FROM conversaciones WHERE id = $1',
      [id]
    );
    if (convResult.rows.length === 0) {
      return res.status(404).json({ error: 'Conversación no encontrada' });
    }

    const estadoActual = convResult.rows[0].estado;

    await db.query(
      `UPDATE conversaciones
       SET estado = $1, estado_anterior = $2, fecha_cambio_estado = NOW(),
           motivo_cambio_estado = $3, updated_at = NOW()
       WHERE id = $4`,
      [estado_nuevo, estadoActual, motivo, id]
    );

    const agenteNombre = req.agente ? req.agente.nombre : 'Sistema';
    const agenteId = req.agente ? req.agente.id : 'sistema';

    await db.query(
      `INSERT INTO cambios_estado_historico
         (conversacion_id, estado_anterior, estado_nuevo, realizado_por, nombre_quien_realizo, motivo)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [id, estadoActual, estado_nuevo, agenteId, agenteNombre, motivo]
    );

    res.json({ success: true, conversacion_id: id });

    // Evento automático en Google Calendar para ciertas etapas (no bloquea respuesta)
    setImmediate(async () => {
      try {
        const { crearEventoEtapa } = require('../services/googleCalendarService');
        const convFull = await db.query(
          'SELECT cliente_nombre, cliente_telefono, tipo_seguro FROM conversaciones WHERE id = $1', [id]
        );
        if (convFull.rows[0]) await crearEventoEtapa(estado_nuevo, convFull.rows[0]);
      } catch {}
    });

  } catch (err) {
    console.error('Error POST /conversaciones/:id/estado:', err);
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

// POST /api/conversaciones/:id/notas
router.post('/conversaciones/:id/notas', authenticateAgent, async (req, res) => {
  try {
    const { id } = req.params;
    const { contenido } = req.body;

    if (!contenido) {
      return res.status(400).json({ error: 'contenido es requerido' });
    }

    const agenteNombre = req.agente ? req.agente.nombre : 'Agente';
    const agenteId = req.agente ? req.agente.id : null;

    const result = await db.query(
      `INSERT INTO notas_internas (conversacion_id, agente_id, agente_nombre, contenido)
       VALUES ($1, $2, $3, $4) RETURNING id`,
      [id, agenteId, agenteNombre, contenido]
    );

    res.status(201).json({ success: true, nota_id: result.rows[0].id });
  } catch (err) {
    console.error('Error POST /conversaciones/:id/notas:', err);
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

// POST /api/conversaciones/:id/cotizaciones
router.post('/conversaciones/:id/cotizaciones', authenticateAgent, async (req, res) => {
  try {
    const { id } = req.params;
    const {
      aseguradora,
      prima,
      moneda = 'MXN',
      cobertura,
      estado = 'cotizando',
      fecha_vencimiento,
    } = req.body;

    if (!aseguradora) {
      return res.status(400).json({ error: 'aseguradora es requerida' });
    }

    const result = await db.query(
      `INSERT INTO cotizaciones
         (conversacion_id, aseguradora, prima, moneda, cobertura, estado, fecha_vencimiento)
       VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id`,
      [id, aseguradora, prima || null, moneda, cobertura || null, estado, fecha_vencimiento || null]
    );

    res.status(201).json({ success: true, cotizacion_id: result.rows[0].id });
  } catch (err) {
    console.error('Error POST /conversaciones/:id/cotizaciones:', err);
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

// PATCH /api/conversaciones/:id/cliente — editar datos del cliente
router.patch('/conversaciones/:id/cliente', authenticateAgent, async (req, res) => {
  try {
    const { id } = req.params;
    const { cliente_nombre, cliente_email, tipo_seguro } = req.body;

    // Solo tipo_seguro
    if (tipo_seguro !== undefined && !cliente_nombre) {
      const TIPOS_VALIDOS = ['vida', 'auto', 'medical', 'daño', 'viaje'];
      if (tipo_seguro && !TIPOS_VALIDOS.includes(tipo_seguro)) {
        return res.status(400).json({ error: 'Tipo de seguro no válido' });
      }
      await db.query(
        `UPDATE conversaciones SET tipo_seguro = $1, updated_at = NOW() WHERE id = $2`,
        [tipo_seguro || null, id]
      );
      return res.json({ success: true });
    }

    if (!cliente_nombre) {
      return res.status(400).json({ error: 'cliente_nombre es requerido' });
    }

    await db.query(
      `UPDATE conversaciones SET cliente_nombre = $1, cliente_email = $2, updated_at = NOW() WHERE id = $3`,
      [cliente_nombre.trim(), cliente_email || null, id]
    );

    res.json({ success: true });
  } catch (err) {
    console.error('Error PATCH /conversaciones/:id/cliente:', err);
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

module.exports = router;
