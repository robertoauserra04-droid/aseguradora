const express = require('express');
const db = require('../config/database');
const { verifyKapsoSignature, detectarTipoSeguro } = require('../utils/helpers');

const router = express.Router();

// Kapso envía JSON; necesitamos el raw body para verificar la firma
router.post(
  '/webhook/kapso/mensaje',
  express.json({
    verify: (req, res, buf) => {
      req.rawBody = buf;
    },
  }),
  async (req, res) => {
    try {
      const signature = req.headers['x-webhook-signature'];
      const idempotencyKey = req.headers['x-idempotency-key'];

      // 1. Verificar firma Kapso
      if (process.env.KAPSO_WEBHOOK_SECRET) {
        const rawBody = req.rawBody ? req.rawBody.toString('utf8') : JSON.stringify(req.body);
        if (!verifyKapsoSignature(rawBody, signature, process.env.KAPSO_WEBHOOK_SECRET)) {
          return res.status(401).json({ error: 'Firma inválida' });
        }
      }

      // 2. Verificar idempotencia (evitar duplicados)
      if (idempotencyKey) {
        const existe = await db.query(
          'SELECT idempotency_key FROM idempotencia_webhooks WHERE idempotency_key = $1',
          [idempotencyKey]
        );
        if (existe.rows.length > 0) {
          return res.status(200).json({ status: 'ok', duplicado: true });
        }
      }

      const { message, conversation } = req.body;

      if (!message || !conversation) {
        return res.status(400).json({ error: 'Payload inválido: faltan message o conversation' });
      }

      // 3. Obtener o crear conversación
      let conversacion = await db.query(
        'SELECT id FROM conversaciones WHERE cliente_whatsapp_id = $1',
        [conversation.phone_number]
      );

      let conversacion_id;

      if (conversacion.rows.length === 0) {
        const insert = await db.query(
          `INSERT INTO conversaciones
            (cliente_telefono, cliente_whatsapp_id, cliente_nombre, estado, requiere_respuesta, created_at, ultimo_mensaje_at)
           VALUES ($1, $2, $3, 'prospectiva', false, NOW(), NOW())
           RETURNING id`,
          [
            conversation.phone_number,
            conversation.phone_number,
            conversation.metadata?.customer_name || 'Cliente',
          ]
        );
        conversacion_id = insert.rows[0].id;
      } else {
        conversacion_id = conversacion.rows[0].id;
      }

      // 4. Guardar mensaje (ignorar si ya existe el whatsapp_message_id)
      const mensajeExiste = message.whatsapp_message_id
        ? await db.query('SELECT id FROM mensajes WHERE whatsapp_message_id = $1', [
            message.whatsapp_message_id,
          ])
        : { rows: [] };

      if (mensajeExiste.rows.length === 0) {
        const requiereMensaje =
          message.direction === 'inbound' &&
          message.content &&
          message.content.includes('?');

        await db.query(
          `INSERT INTO mensajes
            (conversacion_id, autor, nombre_autor, contenido, tipo_mensaje,
             whatsapp_message_id, timestamp_mensaje, requiere_respuesta)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
          [
            conversacion_id,
            message.direction === 'inbound' ? 'cliente' : 'agente',
            message.direction === 'inbound' ? 'Cliente' : 'Agente',
            message.content || '',
            message.message_type || 'text',
            message.whatsapp_message_id || null,
            new Date(message.created_at),
            requiereMensaje,
          ]
        );

        // 5. Detectar tipo de seguro
        const tipoSeguro = detectarTipoSeguro(message.content);
        if (tipoSeguro) {
          await db.query(
            'UPDATE conversaciones SET tipo_seguro = $1 WHERE id = $2 AND tipo_seguro IS NULL',
            [tipoSeguro, conversacion_id]
          );
        }

        // 6. Actualizar último mensaje y requiere_respuesta si es del cliente
        if (message.direction === 'inbound') {
          await db.query(
            `UPDATE conversaciones
             SET ultimo_mensaje_at = NOW(),
                 updated_at = NOW(),
                 requiere_respuesta = $1
             WHERE id = $2`,
            [requiereMensaje, conversacion_id]
          );
        } else {
          // Mensaje del agente: ya no requiere respuesta
          await db.query(
            'UPDATE conversaciones SET ultimo_mensaje_at = NOW(), updated_at = NOW(), requiere_respuesta = false WHERE id = $1',
            [conversacion_id]
          );
        }
      }

      // 7. Registrar idempotencia
      if (idempotencyKey) {
        await db.query(
          'INSERT INTO idempotencia_webhooks (idempotency_key, event_type) VALUES ($1, $2) ON CONFLICT DO NOTHING',
          [idempotencyKey, req.headers['x-webhook-event'] || 'whatsapp.message.received']
        );
      }

      res.status(200).json({ status: 'ok', conversacion_id });
    } catch (err) {
      console.error('Error en webhook Kapso:', err);
      res.status(500).json({ error: 'Error interno del servidor' });
    }
  }
);

module.exports = router;
