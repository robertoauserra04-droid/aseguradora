from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from psycopg2 import errors as pg_errors
from app.middleware.auth import get_agente, get_admin
from app.crud import agentes as crud

router = APIRouter()

ROLES_VALIDOS = {"vendedor", "supervisor", "admin"}


class AgenteBody(BaseModel):
    nombre: str
    email: str
    password: str
    telefono_interno: Optional[str] = None
    rol: Optional[str] = "vendedor"


class AgenteUpdateBody(BaseModel):
    nombre: Optional[str] = None
    email: Optional[str] = None
    telefono_interno: Optional[str] = None
    rol: Optional[str] = None


class PasswordBody(BaseModel):
    password: str


@router.get("/api/agentes")
def listar(agente=Depends(get_admin)):
    return crud.listar()


@router.post("/api/agentes", status_code=201)
def crear(body: AgenteBody, agente=Depends(get_admin)):
    if body.rol and body.rol not in ROLES_VALIDOS:
        raise HTTPException(400, detail=f"Rol inválido. Usa: {', '.join(ROLES_VALIDOS)}")
    try:
        return crud.crear(body.nombre, body.email, body.password, body.telefono_interno, body.rol or "vendedor")
    except pg_errors.UniqueViolation:
        raise HTTPException(409, detail="Ya existe un agente con ese email")
    except Exception:
        raise HTTPException(500, detail="Error al crear agente")


@router.put("/api/agentes/{agente_id}")
def actualizar(agente_id: str, body: AgenteUpdateBody, agente=Depends(get_admin)):
    try:
        resultado = crud.actualizar(agente_id, body.model_dump(exclude_none=True))
    except pg_errors.UniqueViolation:
        raise HTTPException(409, detail="Ese email ya está en uso")
    except Exception:
        raise HTTPException(500, detail="Error al actualizar agente")
    if not resultado:
        raise HTTPException(404, detail="Agente no encontrado")
    return resultado


@router.put("/api/agentes/{agente_id}/password")
def cambiar_password(agente_id: str, body: PasswordBody, agente=Depends(get_agente)):
    es_admin = agente.get("rol") == "admin"
    es_propio = agente.get("agente_id") == agente_id
    if not es_admin and not es_propio:
        raise HTTPException(403, detail="No tienes permiso para cambiar esta contraseña")
    if not body.password or len(body.password) < 6:
        raise HTTPException(400, detail="La contraseña debe tener al menos 6 caracteres")
    if not crud.cambiar_password(agente_id, body.password):
        raise HTTPException(404, detail="Agente no encontrado")
    return {"ok": True}


@router.delete("/api/agentes/{agente_id}")
def desactivar(agente_id: str, agente=Depends(get_admin)):
    if not crud.desactivar(agente_id):
        raise HTTPException(404, detail="Agente no encontrado")
    return {"ok": True}
