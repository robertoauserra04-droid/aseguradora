import json
import logging
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from app.config.env import KAPSO_WEBHOOK_SECRET
from app.utils.webhook import verify_kapso_signature
from app.services.webhook_service import procesar_mensaje_entrante, ejecutar_bot

logger = logging.getLogger(__name__)
router = APIRouter()

# Cabeceras donde Kapso/Meta pueden enviar la firma HMAC del payload
_SIGNATURE_HEADERS = ("x-hub-signature-256", "x-kapso-signature", "x-signature")


def _extraer_firma(headers) -> str | None:
    for h in _SIGNATURE_HEADERS:
        if h in headers:
            return headers[h]
    return None


@router.post("/webhook/kapso/mensaje")
async def kapso_webhook(request: Request, background: BackgroundTasks):
    raw = await request.body()

    # Verificación de firma HMAC (solo si hay secreto configurado)
    if KAPSO_WEBHOOK_SECRET:
        firma = _extraer_firma(request.headers)
        if not firma or not verify_kapso_signature(raw, firma, KAPSO_WEBHOOK_SECRET):
            logger.warning("Webhook rechazado: firma HMAC inválida o ausente")
            raise HTTPException(401, detail="Firma inválida")

    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(400, detail="JSON inválido")

    idempotency_key = request.headers.get("x-idempotency-key")
    event_type = request.headers.get("x-webhook-event", "whatsapp.message.received")

    try:
        # Trabajo bloqueante (psycopg2) fuera del event loop
        result = await run_in_threadpool(
            procesar_mensaje_entrante, body, idempotency_key, event_type
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

    # El bot corre después de responder, en el threadpool (no bloquea, no se pierde por GC)
    if result.pop("disparar_bot", False):
        background.add_task(ejecutar_bot, result["conversacion_id"])

    return result
