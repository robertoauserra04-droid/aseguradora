import secrets
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from app.middleware.auth import get_agente
from app.config.database import query
from app.config.env import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, APP_URL

logger = logging.getLogger(__name__)
router = APIRouter()

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

_REDIRECT_URI = f"{APP_URL}/api/oauth/google/callback"

_CLIENT_CONFIG = {
    "web": {
        "client_id": "",
        "client_secret": "",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [],
    }
}


def _flow():
    from google_auth_oauthlib.flow import Flow
    cfg = dict(_CLIENT_CONFIG)
    cfg["web"] = {**cfg["web"],
                  "client_id": GOOGLE_CLIENT_ID,
                  "client_secret": GOOGLE_CLIENT_SECRET,
                  "redirect_uris": [_REDIRECT_URI]}
    return Flow.from_client_config(cfg, scopes=SCOPES, redirect_uri=_REDIRECT_URI)


@router.get("/api/oauth/google")
def oauth_google_start(agente=Depends(get_agente)):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(400, detail="GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET no configurados en Railway")

    state = secrets.token_urlsafe(32)
    query("UPDATE bot_config SET google_oauth_state = %s WHERE id = 1", [state])

    flow = _flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return RedirectResponse(auth_url)


@router.get("/api/oauth/google/callback")
def oauth_google_callback(code: str = None, state: str = None, error: str = None):
    if error:
        logger.warning("[OAuth] Usuario canceló: %s", error)
        return RedirectResponse("/?google_error=cancelado")

    if not code or not state:
        return RedirectResponse("/?google_error=invalido")

    r = query("SELECT google_oauth_state FROM bot_config WHERE id = 1")
    stored_state = (r.rows[0].get("google_oauth_state") or "") if r.rows else ""
    if not stored_state or stored_state != state:
        logger.warning("[OAuth] State inválido")
        return RedirectResponse("/?google_error=estado_invalido")

    try:
        flow = _flow()
        flow.fetch_token(code=code)
        creds = flow.credentials

        import httpx
        userinfo = httpx.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {creds.token}"},
            timeout=10,
        ).json()
        email = userinfo.get("email", "")

        query(
            """UPDATE bot_config
               SET google_refresh_token = %s,
                   google_email = %s,
                   google_oauth_state = NULL,
                   updated_at = NOW()
               WHERE id = 1""",
            [creds.refresh_token, email],
        )
        logger.info("[OAuth] Google conectado: %s", email)
        return RedirectResponse(f"/?google_connected={email}")

    except Exception as e:
        logger.error("[OAuth] Error al obtener token: %s", e)
        return RedirectResponse("/?google_error=token_fallido")


@router.delete("/api/oauth/google")
def oauth_google_disconnect(agente=Depends(get_agente)):
    query("UPDATE bot_config SET google_refresh_token = NULL, google_email = NULL WHERE id = 1")
    return {"ok": True}
