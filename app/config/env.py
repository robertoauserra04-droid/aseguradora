import os
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", 3000))
NODE_ENV = os.getenv("NODE_ENV", "development")

DATABASE_URL = os.getenv("DATABASE_URL", "")

JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    if NODE_ENV == "production":
        # En producción NO se permite arrancar sin un secreto real: firmar tokens con
        # un valor conocido permitiría a cualquiera forjar un JWT de administrador.
        raise RuntimeError(
            "JWT_SECRET no está definido. Configura la variable de entorno JWT_SECRET "
            "en el entorno de producción antes de arrancar."
        )
    # En desarrollo se genera uno efímero por proceso (los tokens no sobreviven a un reinicio).
    import secrets as _secrets
    JWT_SECRET = _secrets.token_urlsafe(48)
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "JWT_SECRET no definido: usando un secreto aleatorio temporal (solo para desarrollo)."
    )
JWT_EXPIRY_HOURS = 12

# Orígenes permitidos para CORS. Lista separada por comas (ej. "https://panel.midominio.com").
# Por defecto vacío → sin credenciales cross-origin (ver main.py).
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

KAPSO_API_KEY = os.getenv("KAPSO_API_KEY", "")
KAPSO_PHONE_NUMBER_ID = os.getenv("KAPSO_PHONE_NUMBER_ID", "")
KAPSO_WEBHOOK_SECRET = os.getenv("KAPSO_WEBHOOK_SECRET", "")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

GOOGLE_CLIENT_EMAIL = os.getenv("GOOGLE_CLIENT_EMAIL", "")
GOOGLE_PRIVATE_KEY = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "")

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
APP_URL = os.getenv("RAILWAY_PUBLIC_DOMAIN", "https://aseguradora.up.railway.app")
if APP_URL and not APP_URL.startswith("http"):
    APP_URL = f"https://{APP_URL}"
