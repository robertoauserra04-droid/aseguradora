from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from psycopg2 import errors as pg_errors
from app.middleware.auth import get_agente
from app.crud import clientes as crud

router = APIRouter()


class ClienteBody(BaseModel):
    nombre: str = "Cliente"
    telefono: Optional[str] = None
    email: Optional[str] = None
    rfc: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None
    agente_asignado: Optional[str] = None


class ClienteUpdateBody(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    rfc: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None
    agente_asignado: Optional[str] = None


@router.get("/api/clientes")
def listar(search: Optional[str] = None, agente=Depends(get_agente)):
    return crud.listar(search)


@router.get("/api/clientes/{cliente_id}")
def detalle(cliente_id: str, agente=Depends(get_agente)):
    resultado = crud.obtener_por_id(cliente_id)
    if not resultado:
        raise HTTPException(404, detail="Cliente no encontrado")
    return resultado


@router.post("/api/clientes", status_code=201)
def crear(body: ClienteBody, agente=Depends(get_agente)):
    try:
        return crud.crear(body.model_dump())
    except pg_errors.UniqueViolation:
        raise HTTPException(409, detail="Ya existe un cliente con ese teléfono")
    except Exception:
        raise HTTPException(500, detail="Error al crear cliente")


@router.put("/api/clientes/{cliente_id}")
def actualizar(cliente_id: str, body: ClienteUpdateBody, agente=Depends(get_agente)):
    try:
        resultado = crud.actualizar(cliente_id, body.model_dump(exclude_none=True))
    except pg_errors.UniqueViolation:
        raise HTTPException(409, detail="Ese teléfono ya está en uso")
    except Exception:
        raise HTTPException(500, detail="Error al actualizar cliente")
    if not resultado:
        raise HTTPException(404, detail="Cliente no encontrado")
    return resultado


@router.delete("/api/clientes/{cliente_id}")
def desactivar(cliente_id: str, agente=Depends(get_agente)):
    if not crud.desactivar(cliente_id):
        raise HTTPException(404, detail="Cliente no encontrado")
    return {"ok": True}
