import bcrypt
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel
from app.config.env import JWT_SECRET, JWT_EXPIRY_HOURS, ADMIN_EMAIL, ADMIN_PASSWORD
from app.crud.agentes import buscar_por_email

router = APIRouter()


class LoginBody(BaseModel):
    email: str
    password: str


def _make_token(payload: dict) -> str:
    payload["exp"] = datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@router.post("/api/auth/login")
def login(body: LoginBody):
    if ADMIN_EMAIL and ADMIN_PASSWORD and body.email == ADMIN_EMAIL and body.password == ADMIN_PASSWORD:
        token = _make_token({"id": "admin", "nombre": "Administrador", "email": body.email, "rol": "admin"})
        return {"token": token, "nombre": "Administrador", "email": body.email, "rol": "admin"}

    agente = buscar_por_email(body.email)
    if not agente or not agente.get("activo") or not agente.get("contrasena"):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    if not bcrypt.checkpw(body.password.encode(), agente["contrasena"].encode()):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    token = _make_token({
        "id": str(agente["id"]),
        "agente_id": str(agente["id"]),
        "nombre": agente["nombre"],
        "email": agente["email"],
        "rol": agente["rol"],
    })
    return {"token": token, "nombre": agente["nombre"], "email": agente["email"], "rol": agente["rol"]}


@router.post("/api/auth/logout")
def logout():
    return {"ok": True}
