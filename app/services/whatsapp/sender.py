import logging
import re
import httpx
from app.config.env import KAPSO_API_KEY, KAPSO_PHONE_NUMBER_ID

logger = logging.getLogger(__name__)

_KAPSO_URL = "https://api.kapso.ai/meta/whatsapp/v24.0/{phone_id}/messages"


def _headers() -> dict:
    return {"X-API-Key": KAPSO_API_KEY, "Content-Type": "application/json"}


def _normalizar_telefono(telefono: str) -> str:
    """Deja solo dígitos: quita '+', espacios, guiones, paréntesis y el prefijo
    internacional '00'. La API de WhatsApp espera el número en formato E.164 sin '+'.
    Nota: NO se toca el '1' histórico después del '52' (MX) para no alterar números
    ya guardados; si se necesita, se maneja aparte."""
    solo_digitos = re.sub(r"\D", "", telefono or "")
    if solo_digitos.startswith("00"):
        solo_digitos = solo_digitos[2:]
    return solo_digitos


def _post(payload: dict, descripcion: str) -> None:
    """POST resiliente a Kapso: nunca propaga excepciones (timeout/conexión) para
    no abortar el job o la request que lo invoca; solo loguea."""
    url = _KAPSO_URL.format(phone_id=KAPSO_PHONE_NUMBER_ID)
    try:
        with httpx.Client(timeout=20) as client:
            r = client.post(url, json=payload, headers=_headers())
        if r.status_code >= 400:
            logger.warning("%s error %s: %s", descripcion, r.status_code, r.text[:300])
    except httpx.HTTPError as e:
        logger.warning("%s fallo de red: %s", descripcion, e)


def enviar_mensaje(telefono: str, texto: str) -> None:
    """Mensaje de texto libre — solo funciona dentro de la ventana de 24h del cliente."""
    if not KAPSO_API_KEY or not KAPSO_PHONE_NUMBER_ID:
        logger.warning("KAPSO_API_KEY o KAPSO_PHONE_NUMBER_ID no configurados")
        return

    to = _normalizar_telefono(telefono)
    _post(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": texto},
        },
        "enviar_mensaje",
    )


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

    to = _normalizar_telefono(telefono)
    parameters = [{"type": "text", "text": str(p)} for p in params]

    _post(
        {
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
        f"enviar_template '{template_name}'",
    )
