from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from app.config.database import query
from app.crud.webhooks import limpiar_viejos


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
    scheduler = BackgroundScheduler()

    scheduler.add_job(detectar_sin_respuesta, "interval", minutes=30)
    scheduler.add_job(detectar_proximas_renovacion, "cron", hour=9, minute=0)
    scheduler.add_job(limpiar_viejos, "cron", hour=3, minute=0)
    scheduler.add_job(sincronizar_drive, "interval", minutes=30)

    scheduler.start()
    print("[Jobs] Background jobs iniciados")

    detectar_sin_respuesta()
    detectar_proximas_renovacion()
    sincronizar_drive()
