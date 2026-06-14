from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.config.env import JWT_SECRET

bearer = HTTPBearer()


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


def get_agente(credentials: HTTPAuthorizationCredentials = Security(bearer)) -> dict:
    return _decode(credentials.credentials)


def get_admin(credentials: HTTPAuthorizationCredentials = Security(bearer)) -> dict:
    agente = _decode(credentials.credentials)
    if agente.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="Se requiere rol de administrador")
    return agente


def get_supervisor(credentials: HTTPAuthorizationCredentials = Security(bearer)) -> dict:
    agente = _decode(credentials.credentials)
    if agente.get("rol") not in ("admin", "supervisor"):
        raise HTTPException(status_code=403, detail="Se requiere rol de supervisor o administrador")
    return agente
