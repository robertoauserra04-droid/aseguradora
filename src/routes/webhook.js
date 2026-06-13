const express = require('express');
const db = require('../config/database');
const { detectarTipoSeguro } = require('../utils/helpers');
const { generarRespuesta } = require('../services/botService');
const { enviarMensaje } = require('../services/kapsoService');

const router = express.Router();

router.post(
  '/webhook/kapso/mensaje',
  express.json(),
  async (req, res) => {
    try {
      const idempotencyKey = req.headers['x-idempotency-key'];
      const isTestEvent   = req.body?.test === true;

      // 1. Verificar idempotencia (evitar duplicados)
      if (idempotencyKey) {
        const existe = await db.query(
          'SELECT idempotency_key FROM idempotencia_webhooks WHERE idempotency_key = $1',
          [idempotencyKey]
        );
        if (existe.rows.length > 0) {
          return res.status(200).json({ status: 'ok', duplicado: true });
        }
      }

      // 3. Normalizar payload — Kapso usa estructura diferente a lo esperado
      const rawMsg  = req.body.message      || {};
      const rawConv = req.body.conversation || {};

      if (!rawMsg || !rawConv) {
        return res.status(400).json({ error: 'Payload inválido: faltan message o conversation' });
      }

      const message = {
        content:             rawMsg.text?.body          ?? rawMsg.content          ?? '',
        direction:           rawMsg.kapso?.direction    ?? rawMsg.direction         ?? 'inbound',
        whatsapp_message_id: rawMsg.id                  ?? rawMsg.whatsapp_message_id ?? null,
        message_type:        rawMsg.type                ?? rawMsg.message_type      ?? 'text',
        created_at:          rawMsg.timestamp
          ? new Date(parseInt(rawMsg.timestamp) * 1000)
          : rawMsg.created_at ? new Date(rawMsg.created_at) : new Date(),
      };

      // Teléfono: normalizar — quitar espacios, garantizar que empieza con +
      const rawPhone = (rawConv.phone_number ?? rawMsg.from ?? '').replace(/\s+/g, '');
      const phone = rawPhone.startsWith('+') ? rawPhone : `+${rawPhone}`;
      const conversation = {
        phone_number:  phone,
        metadata:      rawConv.metadata || { customer_name: rawConv.contact_name || rawConv.username || 'Cliente' },
      };

      if (!conversation.phone_number) {
        return res.status(400).json({ error: 'Payload inválido: falta phone_number' });
      }

      // 4. Obtener o crear conversación
      let convRow = await db.query(
        'SELECT id FROM conversaciones WHERE cliente_whatsapp_id = $1',
        [conversation.phone_number]
      );

      let conversacion_id;

      if (convRow.rows.length === 0) {
        const insert = await db.query(
          `INSERT INTO conversaciones
            (cliente_telefono, cliente_whatsapp_id, cliente_nombre, estado, requiere_respuesta, created_at, ultimo_mensaje_at)
           VALUES ($1, $2, $3, 'inicio', false, NOW(), NOW())
           RETURNING id`,
          [
            conversation.phone_number,
            conversation.phone_number,
            conversation.metadata?.customer_name || 'Cliente',
          ]
        );
        conversacion_id = insert.rows[0].id;
      } else {
        conversacion_id = convRow.rows[0].id;
      }

      // 5. Guardar mensaje (ignorar si ya existe el whatsapp_message_id)
      const mensajeExiste = message.whatsapp_message_id
        ? await db.query('SELECT id FROM mensajes WHERE whatsapp_message_id = $1', [message.whatsapp_message_id])
        : { rows: [] };

      if (mensajeExiste.rows.length === 0) {
        const requiereMensaje =
          !!(message.direction === 'inbound' && message.content && message.content.includes('?'));

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
            message.message_type,
            message.whatsapp_message_id || null,
            message.created_at,
            requiereMensaje,
          ]
        );

        // 6. Detectar tipo de seguro
        const tipoSeguro = detectarTipoSeguro(message.content);
        if (tipoSeguro) {
          await db.query(
            'UPDATE conversaciones SET tipo_seguro = $1 WHERE id = $2 AND tipo_seguro IS NULL',
            [tipoSeguro, conversacion_id]
          );
        }

        // 7. Actualizar último mensaje
        if (message.direction === 'inbound') {
          await db.query(
            `UPDATE conversaciones
             SET ultimo_mensaje_at = NOW(), updated_at = NOW(), requiere_respuesta = $1
             WHERE id = $2`,
            [requiereMensaje, conversacion_id]
          );
        } else {
          await db.query(
            'UPDATE conversaciones SET ultimo_mensaje_at = NOW(), updated_at = NOW(), requiere_respuesta = false WHERE id = $1',
            [conversacion_id]
          );
        }
      }

      // 8. Registrar idempotencia
      if (idempotencyKey) {
        await db.query(
          'INSERT INTO idempotencia_webhooks (idempotency_key, event_type) VALUES ($1, $2) ON CONFLICT DO NOTHING',
          [idempotencyKey, req.headers['x-webhook-event'] || 'whatsapp.message.received']
        );
      }

      // 9. Respuesta automática del bot (solo mensajes inbound reales, no bloquea el 200)
      if (message.direction === 'inbound' && !isTestEvent && process.env.OPENAI_API_KEY) {
        setImmediate(async () => {
          try {
            const convBot = await db.query(
              'SELECT bot_activo, cliente_telefono FROM conversaciones WHERE id = $1',
              [conversacion_id]
            );
            const conv = convBot.rows[0];
            if (!conv?.bot_activo) return;

            const texto = await generarRespuesta(conversacion_id);
            if (!texto) return;

            await enviarMensaje(conv.cliente_telefono, texto);

            await db.query(
              `INSERT INTO mensajes
                (conversacion_id, autor, nombre_autor, contenido, tipo_mensaje, timestamp_mensaje, requiere_respuesta)
               VALUES ($1, 'bot', 'Bot Carguill', $2, 'text', NOW(), false)`,
              [conversacion_id, texto]
            );

            await db.query(
              'UPDATE conversaciones SET ultimo_mensaje_at = NOW(), updated_at = NOW(), requiere_respuesta = false WHERE id = $1',
              [conversacion_id]
            );

            console.log(`[Bot] Respuesta enviada a ${conv.cliente_telefono}`);
          } catch (botErr) {
            console.error('[Bot] Error al generar/enviar respuesta:', botErr.message);
          }
        });
      }

      res.status(200).json({ status: 'ok', conversacion_id });
    } catch (err) {
      console.error('Error en webhook Kapso:', err);
      res.status(500).json({ error: 'Error interno del servidor' });
    }
  }
);

module.exports = router;
