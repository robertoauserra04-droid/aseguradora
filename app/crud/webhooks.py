from app.config.database import query


def ya_existe(idempotency_key: str) -> bool:
    r = query(
        "SELECT idempotency_key FROM idempotencia_webhooks WHERE idempotency_key = %s",
        [idempotency_key],
    )
    return len(r.rows) > 0


def registrar(idempotency_key: str, event_type: str = "whatsapp.message.received") -> None:
    query(
        "INSERT INTO idempotencia_webhooks (idempotency_key, event_type) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        [idempotency_key, event_type],
    )


def limpiar_viejos() -> None:
    query("DELETE FROM idempotencia_webhooks WHERE processed_at < NOW() - INTERVAL '7 days'")
