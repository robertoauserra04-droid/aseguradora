import os
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", 3000))
NODE_ENV = os.getenv("NODE_ENV", "development")

DATABASE_URL = os.getenv("DATABASE_URL", "")

JWT_SECRET = os.getenv("JWT_SECRET", "carguill_secret_dev")
JWT_EXPIRY_HOURS = 12

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

KAPSO_API_KEY = os.getenv("KAPSO_API_KEY", "")
KAPSO_PHONE_NUMBER_ID = os.getenv("KAPSO_PHONE_NUMBER_ID", "")
KAPSO_WEBHOOK_SECRET = os.getenv("KAPSO_WEBHOOK_SECRET", "")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

GOOGLE_CLIENT_EMAIL = os.getenv("GOOGLE_CLIENT_EMAIL", "")
GOOGLE_PRIVATE_KEY = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "")
