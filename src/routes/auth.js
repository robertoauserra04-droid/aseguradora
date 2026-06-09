const express = require('express');
const jwt = require('jsonwebtoken');

const router = express.Router();

// POST /api/auth/login
router.post('/auth/login', express.json(), (req, res) => {
  const { email, password } = req.body;

  const adminEmail = process.env.ADMIN_EMAIL;
  const adminPassword = process.env.ADMIN_PASSWORD;

  if (!adminEmail || !adminPassword) {
    return res.status(500).json({ error: 'Credenciales no configuradas en Railway (ADMIN_EMAIL, ADMIN_PASSWORD)' });
  }

  if (email !== adminEmail || password !== adminPassword) {
    return res.status(401).json({ error: 'Email o contraseña incorrectos' });
  }

  const token = jwt.sign(
    { id: 'admin', nombre: 'Administrador', email, rol: 'admin' },
    process.env.JWT_SECRET || 'carguill_secret_dev',
    { expiresIn: '12h' }
  );

  res.json({ token, nombre: 'Administrador', email, rol: 'admin' });
});

// POST /api/auth/logout (solo limpia en frontend, aquí devolvemos ok)
router.post('/auth/logout', (req, res) => {
  res.json({ ok: true });
});

module.exports = router;
