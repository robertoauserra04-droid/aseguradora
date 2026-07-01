import base64
import hmac
import hashlib


def verify_kapso_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    if not signature or not secret:
        return False
    # Kapso manda hex plano; Meta usa el prefijo "sha256=". Aceptamos ambos.
    sig = signature.strip()
    if sig.lower().startswith("sha256="):
        sig = sig[len("sha256="):]

    digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).digest()
    expected_hex = digest.hex()
    expected_b64 = base64.b64encode(digest).decode()

    try:
        # Comparación en hex (caso principal) o en base64 (algunos emisores firman así).
        if hmac.compare_digest(sig.lower(), expected_hex.lower()):
            return True
        return hmac.compare_digest(sig, expected_b64)
    except Exception:
        return False
