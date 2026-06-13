const express = require('express');
const bcrypt  = require('bcrypt');
const db      = require('../config/database');
const { authenticateAgent, requireAdmin } = require('../middleware/auth');

const router = express.Router();

// GET /api/agentes — lista todos los agentes activos
router.get('/agentes', authenticateAgent, requireAdmin, async (req, res) => {
  try {
    const result = await db.query(
      `SELECT id, nombre, email, telefono_interno, rol, activo,
              conversaciones_asignadas, conversaciones_cerradas, tasa_cierre, created_at
       FROM agentes
       WHERE email != 'sistema@carguill.com'
       ORDER BY created_at DESC`
    );
    res.json(result.rows);
  } catch (err) {
    console.error('[Agentes] GET /agentes:', err.message);
    res.status(500).json({ error: 'Error al obtener agentes' });
  }
});

// POST /api/agentes — crear agente
router.post('/agentes', authenticateAgent, requireAdmin, async (req, res) => {
  try {
    const { nombre, email, password, telefono_interno, rol } = req.body;

    if (!nombre || !email || !password) {
      return res.status(400).json({ error: 'nombre, email y password son requeridos' });
    }

    const rolesValidos = ['vendedor', 'supervisor', 'admin'];
    if (rol && !rolesValidos.includes(rol)) {
      return res.status(400).json({ error: `Rol inválido. Usa: ${rolesValidos.join(', ')}` });
    }

    const hash = await bcrypt.hash(password, 10);

    const result = await db.query(
      `INSERT INTO agentes (nombre, email, contrasena, telefono_interno, rol, activo)
       VALUES ($1, $2, $3, $4, $5, true)
       RETURNING id, nombre, email, telefono_interno, rol, activo, created_at`,
      [nombre, email.toLowerCase(), hash, telefono_interno || null, rol || 'vendedor']
    );

    res.status(201).json(result.rows[0]);
  } catch (err) {
    if (err.code === '23505') {
      return res.status(409).json({ error: 'Ya existe un agente con ese email' });
    }
    console.error('[Agentes] POST /agentes:', err.message);
    res.status(500).json({ error: 'Error al crear agente' });
  }
});

// PUT /api/agentes/:id — editar datos del agente
router.put('/agentes/:id', authenticateAgent, requireAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const { nombre, email, telefono_interno, rol } = req.body;

    const result = await db.query(
      `UPDATE agentes
       SET nombre = COALESCE($1, nombre),
           email  = COALESCE($2, email),
           telefono_interno = COALESCE($3, telefono_interno),
           rol    = COALESCE($4, rol)
       WHERE id = $5 AND email != 'sistema@carguill.com'
       RETURNING id, nombre, email, telefono_interno, rol, activo`,
      [nombre || null, email ? email.toLowerCase() : null, telefono_interno || null, rol || null, id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Agente no encontrado' });
    }
    res.json(result.rows[0]);
  } catch (err) {
    if (err.code === '23505') {
      return res.status(409).json({ error: 'Ese email ya está en uso' });
    }
    console.error('[Agentes] PUT /agentes/:id:', err.message);
    res.status(500).json({ error: 'Error al actualizar agente' });
  }
});

// PUT /api/agentes/:id/password — cambiar contraseña (admin o el propio agente)
router.put('/agentes/:id/password', authenticateAgent, async (req, res) => {
  try {
    const { id } = req.params;
    const { password } = req.body;
    const esAdmin    = req.agente.rol === 'admin';
    const esPropio   = req.agente.agente_id === id;

    if (!esAdmin && !esPropio) {
      return res.status(403).json({ error: 'No tienes permiso para cambiar esta contraseña' });
    }
    if (!password || password.length < 6) {
      return res.status(400).json({ error: 'La contraseña debe tener al menos 6 caracteres' });
    }

    const hash = await bcrypt.hash(password, 10);
    const result = await db.query(
      'UPDATE agentes SET contrasena = $1 WHERE id = $2 RETURNING id',
      [hash, id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Agente no encontrado' });
    }
    res.json({ ok: true });
  } catch (err) {
    console.error('[Agentes] PUT password:', err.message);
    res.status(500).json({ error: 'Error al cambiar contraseña' });
  }
});

// DELETE /api/agentes/:id — desactivar (soft delete)
router.delete('/agentes/:id', authenticateAgent, requireAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const result = await db.query(
      `UPDATE agentes SET activo = false WHERE id = $1 AND email != 'sistema@carguill.com' RETURNING id`,
      [id]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Agente no encontrado' });
    }
    res.json({ ok: true });
  } catch (err) {
    console.error('[Agentes] DELETE /agentes/:id:', err.message);
    res.status(500).json({ error: 'Error al desactivar agente' });
  }
});

module.exports = router;
