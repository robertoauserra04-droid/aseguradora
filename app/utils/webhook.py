import hmac
import hashlib


def verify_kapso_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    if not signature or not secret:
        return False
    # Kapso manda hex plano; Meta usa el prefijo "sha256=". Aceptamos ambos.
    sig = signature.strip()
    if sig.lower().startswith("sha256="):
        sig = sig[len("sha256="):]
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    try:
        return hmac.compare_digest(sig.lower(), expected.lower())
    except Exception:
        return False
