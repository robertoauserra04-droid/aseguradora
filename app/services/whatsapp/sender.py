import logging
import httpx
from app.config.env import KAPSO_API_KEY, KAPSO_PHONE_NUMBER_ID

logger = logging.getLogger(__name__)

_KAPSO_URL = "https://api.kapso.ai/meta/whatsapp/v24.0/{phone_id}/messages"


def _headers() -> dict:
    return {"X-API-Key": KAPSO_API_KEY, "Content-Type": "application/json"}


def enviar_mensaje(telefono: str, texto: str) -> None:
    """Mensaje de texto libre — solo funciona dentro de la ventana de 24h del cliente."""
    if not KAPSO_API_KEY or not KAPSO_PHONE_NUMBER_ID:
        logger.warning("KAPSO_API_KEY o KAPSO_PHONE_NUMBER_ID no configurados")
        return

    to = telefono.lstrip("+")
    url = _KAPSO_URL.format(phone_id=KAPSO_PHONE_NUMBER_ID)

    with httpx.Client(timeout=20) as client:
        r = client.post(
            url,
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"body": texto},
            },
            headers=_headers(),
        )
        if r.status_code >= 400:
            logger.warning("enviar_mensaje error %s: %s", r.status_code, r.text[:300])


def enviar_template(telefono: str, template_name: str, params: list[str],
                    lang: str = "es_MX") -> None:
    """Envía un template de WhatsApp aprobado por Meta.

    Usar para notificaciones proactivas donde el cliente puede llevar más de 24h
    sin escribir — fuera de la ventana de atención, los mensajes de texto libre
    son rechazados silenciosamente por la API.

    Args:
        telefono:      Número en formato +52... o 52...
        template_name: Nombre exacto del template registrado en Meta Business Manager.
        params:        Lista de strings que reemplazan {{1}}, {{2}}, … en el cuerpo.
        lang:          Código de idioma del template (por defecto 'es_MX').
    """
    if not KAPSO_API_KEY or not KAPSO_PHONE_NUMBER_ID:
        logger.warning("KAPSO_API_KEY o KAPSO_PHONE_NUMBER_ID no configurados")
        return

    to = telefono.lstrip("+")
    url = _KAPSO_URL.format(phone_id=KAPSO_PHONE_NUMBER_ID)
    parameters = [{"type": "text", "text": str(p)} for p in params]

    with httpx.Client(timeout=20) as client:
        r = client.post(
            url,
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": lang},
                    "components": [
                        {"type": "body", "parameters": parameters}
                    ],
                },
            },
            headers=_headers(),
        )
        if r.status_code >= 400:
            logger.warning("enviar_template '%s' error %s: %s",
                           template_name, r.status_code, r.text[:300])
