import logging
import httpx
from app.config.env import KAPSO_API_KEY, KAPSO_PHONE_NUMBER_ID

logger = logging.getLogger(__name__)


def enviar_mensaje(telefono: str, texto: str) -> None:
    if not KAPSO_API_KEY or not KAPSO_PHONE_NUMBER_ID:
        logger.warning("KAPSO_API_KEY o KAPSO_PHONE_NUMBER_ID no configurados")
        return

    to = telefono.lstrip("+")

    with httpx.Client(timeout=20) as client:
        client.post(
            f"https://api.kapso.ai/meta/whatsapp/v24.0/{KAPSO_PHONE_NUMBER_ID}/messages",
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"body": texto},
            },
            headers={"X-API-Key": KAPSO_API_KEY, "Content-Type": "application/json"},
        )
