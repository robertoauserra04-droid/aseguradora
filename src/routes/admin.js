const express = require('express');
const { authenticateAgent } = require('../middleware/auth');
const { runSeedForce } = require('../db/seed');
const { MIGRACION_ESTADOS } = require('../utils/helpers');

const db = require('../config/database');

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

// POST /api/admin/migrar-estados — convierte estados viejos al nuevo sistema
router.post('/admin/migrar-estados', authenticateAgent, async (req, res) => {
  try {
    let actualizadas = 0;
    for (const [estadoViejo, estadoNuevo] of Object.entries(MIGRACION_ESTADOS)) {
      const r = await db.query(
        `UPDATE conversaciones SET estado = $1 WHERE estado = $2`,
        [estadoNuevo, estadoViejo]
      );
      actualizadas += r.rowCount;
    }
    res.json({ success: true, actualizadas, mensaje: `${actualizadas} conversaciones migradas al nuevo sistema de etapas` });
  } catch (err) {
    res.status(500).json({ error: 'Error al migrar estados', detalle: err.message });
  }
});

module.exports = router;
