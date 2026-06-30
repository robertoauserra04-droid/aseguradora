"""Credenciales de Google unificadas: OAuth (usuario) o service account (fallback)."""
import logging
from app.config.env import (
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    GOOGLE_CLIENT_EMAIL, GOOGLE_PRIVATE_KEY,
)

logger = logging.getLogger(__name__)


def get_credentials(scopes: list[str]):
    """Retorna credenciales de Google.

    Prioridad:
    1. OAuth refresh_token guardado en bot_config (el cliente conectó su cuenta)
    2. Service account vía env vars (configuración manual legacy)
    """
    # 1. OAuth
    try:
        from app.config.database import query
        r = query("SELECT google_refresh_token FROM bot_config WHERE id = 1")
        refresh_token = (r.rows[0].get("google_refresh_token") or "").strip() if r.rows else ""
        if refresh_token and GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                client_id=GOOGLE_CLIENT_ID,
                client_secret=GOOGLE_CLIENT_SECRET,
                token_uri="https://oauth2.googleapis.com/token",
                scopes=scopes,
            )
            creds.refresh(Request())
            return creds
    except Exception as e:
        logger.warning("[GoogleAuth] OAuth falló, intentando service account: %s", e)

    # 2. Service account (fallback)
    if GOOGLE_CLIENT_EMAIL and GOOGLE_PRIVATE_KEY:
        try:
            from google.oauth2 import service_account
            return service_account.Credentials.from_service_account_info(
                {"client_email": GOOGLE_CLIENT_EMAIL,
                 "private_key": GOOGLE_PRIVATE_KEY,
                 "token_uri": "https://oauth2.googleapis.com/token"},
                scopes=scopes,
            )
        except Exception as e:
            logger.error("[GoogleAuth] Service account falló: %s", e)

    return None
