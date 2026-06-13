const express = require('express');
const jwt     = require('jsonwebtoken');
const bcrypt  = require('bcrypt');
const db      = require('../config/database');

const router = express.Router();

// POST /api/auth/login
router.post('/auth/login', express.json(), async (req, res) => {
  try {
    const { email, password } = req.body;
    const secret = process.env.JWT_SECRET || 'carguill_secret_dev';

    // 1. Verificar si es el admin del entorno
    const adminEmail    = process.env.ADMIN_EMAIL;
    const adminPassword = process.env.ADMIN_PASSWORD;

    if (adminEmail && adminPassword && email === adminEmail && password === adminPassword) {
      const token = jwt.sign(
        { id: 'admin', nombre: 'Administrador', email, rol: 'admin' },
        secret,
        { expiresIn: '12h' }
      );
      return res.json({ token, nombre: 'Administrador', email, rol: 'admin' });
    }

    // 2. Buscar en tabla de agentes
    const result = await db.query(
      'SELECT id, nombre, email, rol, contrasena, activo FROM agentes WHERE email = $1',
      [email.toLowerCase()]
    );

    const agente = result.rows[0];

    if (!agente || !agente.activo || !agente.contrasena) {
      return res.status(401).json({ error: 'Email o contraseña incorrectos' });
    }

    const match = await bcrypt.compare(password, agente.contrasena);
    if (!match) {
      return res.status(401).json({ error: 'Email o contraseña incorrectos' });
    }

    const token = jwt.sign(
      { id: agente.id, agente_id: agente.id, nombre: agente.nombre, email: agente.email, rol: agente.rol },
      secret,
      { expiresIn: '12h' }
    );

    res.json({ token, nombre: agente.nombre, email: agente.email, rol: agente.rol });
  } catch (err) {
    console.error('[Auth] Login error:', err.message);
    res.status(500).json({ error: 'Error interno al iniciar sesión' });
  }
});

// POST /api/auth/logout
router.post('/auth/logout', (req, res) => {
  res.json({ ok: true });
});

module.exports = router;
