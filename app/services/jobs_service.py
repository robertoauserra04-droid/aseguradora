import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from app.config.database import query
from app.crud.webhooks import limpiar_viejos

logger = logging.getLogger(__name__)

# Clave arbitraria para el advisory lock de Postgres que garantiza que solo un
# proceso (aunque haya varios workers de uvicorn) ejecute los jobs en background.
_JOBS_LOCK_KEY = 918273645
_lock_conn = None  # conexión dedicada que mantiene vivo el lock durante todo el proceso


def _soy_lider() -> bool:
    """Intenta tomar un advisory lock de sesión. Solo el proceso que lo obtiene
    ejecuta los jobs; los demás workers no. Si falla la conexión, se asume líder
    (mejor ejecutar que quedarse sin jobs)."""
    global _lock_conn
    try:
        import psycopg2
        from app.config.env import DATABASE_URL, NODE_ENV
        connect_args = {"sslmode": "require"} if NODE_ENV == "production" else {}
        _lock_conn = psycopg2.connect(DATABASE_URL, **connect_args)
        _lock_conn.autocommit = True
        with _lock_conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", [_JOBS_LOCK_KEY])
            obtenido = cur.fetchone()[0]
        if not obtenido:
            _lock_conn.close()
            _lock_conn = None
        return bool(obtenido)
    except Exception as e:
        logger.warning("[Jobs] No se pudo evaluar el advisory lock (%s); se ejecutará igual", e)
        return True


def detectar_sin_respuesta() -> None:
    try:
        hace_2h = datetime.utcnow() - timedelta(hours=2)
        r = query(
            """UPDATE conversaciones
               SET requiere_respuesta = true, prioridad = 'alta', updated_at = NOW()
               WHERE ultimo_mensaje_at < %s
                 AND requiere_respuesta = false
                 AND activo = true
                 AND estado NOT IN ('churn', 'poliza_activa', 'gestion_continua', 'renovado_activo')
               RETURNING id""",
            [hace_2h],
        )
        if r.rowcount:
            print(f"[Jobs] {r.rowcount} conversaciones marcadas como requieren respuesta")
    except Exception as e:
        print(f"[Jobs] Error en detectar_sin_respuesta: {e}")


def detectar_proximas_renovacion() -> None:
    try:
        en_30_dias = datetime.utcnow() + timedelta(days=30)
        r = query(
            """UPDATE conversaciones
               SET estado = 'renovacion', prioridad = 'alta', updated_at = NOW()
               WHERE fecha_vencimiento_poliza IS NOT NULL
                 AND fecha_vencimiento_poliza <= %s
                 AND estado = 'poliza_activa'
                 AND activo = true
               RETURNING id""",
            [en_30_dias],
        )
        if r.rowcount:
            print(f"[Jobs] {r.rowcount} pólizas marcadas para renovación")
    except Exception as e:
        print(f"[Jobs] Error en detectar_proximas_renovacion: {e}")


def sincronizar_drive() -> None:
    try:
        from app.services.drive.client import sincronizar_documentos
        n = sincronizar_documentos()
        if n:
            print(f"[Jobs] Drive sync: {n} documentos actualizados")
    except Exception as e:
        print(f"[Jobs] Error en sincronizar_drive: {e}")


def iniciar_jobs() -> None:
    # Instancia única: si hay varios workers, solo el que obtiene el lock corre los jobs
    # (evita UPDATEs y sync de Drive duplicados en paralelo).
    if not _soy_lider():
        logger.info("[Jobs] Otro proceso ya ejecuta los jobs; este worker no los inicia")
        return

    scheduler = BackgroundScheduler()

    # La corrida inicial de "puesta al día" se agenda ~15 s después del arranque
    # (vía el scheduler, en su propio hilo) en vez de correr síncrona dentro del
    # startup, que bloqueaba el arranque de FastAPI (incluida una sync de Drive).
    pronto = datetime.now(timezone.utc) + timedelta(seconds=15)

    scheduler.add_job(detectar_sin_respuesta, "interval", minutes=30, next_run_time=pronto)
    scheduler.add_job(detectar_proximas_renovacion, "cron", hour=9, minute=0, next_run_time=pronto)
    scheduler.add_job(limpiar_viejos, "cron", hour=3, minute=0)
    scheduler.add_job(sincronizar_drive, "interval", minutes=30, next_run_time=pronto)

    scheduler.start()
    logger.info("[Jobs] Background jobs iniciados")
