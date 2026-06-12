const express = require('express');
const db = require('../config/database');
const { authenticateAgent } = require('../middleware/auth');

const router = express.Router();

// GET /api/bot/config
router.get('/bot/config', authenticateAgent, async (req, res) => {
  try {
    const r = await db.query('SELECT instrucciones, activo_global FROM bot_config LIMIT 1');
    res.json(r.rows[0] || { instrucciones: '', activo_global: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PUT /api/bot/config
router.put('/bot/config', authenticateAgent, async (req, res) => {
  try {
    const { instrucciones, activo_global } = req.body;
    await db.query(
      `UPDATE bot_config SET
        instrucciones = COALESCE($1, instrucciones),
        activo_global = COALESCE($2, activo_global),
        updated_at = NOW()
       WHERE id = 1`,
      [instrucciones ?? null, activo_global ?? null]
    );
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/bot/faq
router.get('/bot/faq', authenticateAgent, async (req, res) => {
  try {
    const r = await db.query('SELECT * FROM bot_faq WHERE activo = true ORDER BY orden, created_at');
    res.json(r.rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/bot/faq
router.post('/bot/faq', authenticateAgent, async (req, res) => {
  try {
    const { pregunta, respuesta } = req.body;
    if (!pregunta || !respuesta) return res.status(400).json({ error: 'Faltan pregunta o respuesta' });
    const r = await db.query(
      'INSERT INTO bot_faq (pregunta, respuesta) VALUES ($1, $2) RETURNING *',
      [pregunta, respuesta]
    );
    res.json(r.rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// DELETE /api/bot/faq/:id
router.delete('/bot/faq/:id', authenticateAgent, async (req, res) => {
  try {
    await db.query('UPDATE bot_faq SET activo = false WHERE id = $1', [req.params.id]);
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PATCH /api/conversaciones/:id/bot  — toggle bot por conversación
router.patch('/conversaciones/:id/bot', authenticateAgent, async (req, res) => {
  try {
    const { bot_activo } = req.body;
    await db.query('UPDATE conversaciones SET bot_activo = $1 WHERE id = $2', [bot_activo, req.params.id]);
    res.json({ ok: true, bot_activo });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
