import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from app.routes.health import router as health_router
from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.agentes import router as agentes_router
from app.routes.bot import router as bot_router
from app.routes.calendario import router as calendario_router
from app.routes.admin import router as admin_router
from app.routes.webhook import router as webhook_router
from app.routes.conversaciones import router as conversaciones_router
from app.routes.clientes import router as clientes_router
from app.routes.polizas import router as polizas_router
from app.routes.etapas import router as etapas_router
from app.routes.citas import router as citas_router
from app.routes.oauth import router as oauth_router

app = FastAPI(title="Seguros Carguill API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(agentes_router)
app.include_router(bot_router)
app.include_router(calendario_router)
app.include_router(admin_router)
app.include_router(webhook_router)
app.include_router(conversaciones_router)
app.include_router(clientes_router)
app.include_router(polizas_router)
app.include_router(etapas_router)
app.include_router(citas_router)
app.include_router(oauth_router)

# Servir el frontend estático
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "..", "public")
if os.path.isdir(PUBLIC_DIR):
    app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="static")


@app.on_event("startup")
def startup():
    from app.db.migrate import run_migrations, backfill_clientes_polizas, seed_etapas, seed_bot_config_defaults
    from app.db.seed import run_seed
    from app.services.jobs_service import iniciar_jobs

    run_migrations()
    seed_etapas()
    seed_bot_config_defaults()
    backfill_clientes_polizas()
    run_seed()
    iniciar_jobs()
