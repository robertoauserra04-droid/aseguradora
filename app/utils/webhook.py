import hmac
import hashlib


def verify_kapso_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    if not signature or not secret:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    try:
        return hmac.compare_digest(signature.encode(), expected.encode())
    except Exception:
        return False
