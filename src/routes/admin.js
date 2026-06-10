const express = require('express');
const { authenticateAgent } = require('../middleware/auth');
const { runSeedForce } = require('../db/seed');

const router = express.Router();

// POST /api/admin/seed — recarga datos de prueba (solo con token valido)
router.post('/admin/seed', authenticateAgent, async (req, res) => {
  try {
    await runSeedForce();
    res.json({ success: true, mensaje: '15 conversaciones de prueba cargadas correctamente' });
  } catch (err) {
    res.status(500).json({ error: 'Error al cargar datos de prueba', detalle: err.message });
  }
});

module.exports = router;
