from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from app.middleware.auth import get_agente
from app.crud import polizas as crud

router = APIRouter()


class PolizaBody(BaseModel):
    cliente_id: str
    conversacion_id: Optional[str] = None
    numero_poliza: Optional[str] = None
    ramo: str
    aseguradora: str
    estado: Optional[str] = "vigente"
    fecha_inicio: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    suma_asegurada: Optional[float] = None
    prima: Optional[float] = None
    moneda: Optional[str] = "MXN"
    forma_pago: Optional[str] = "anual"
    comision_pct: Optional[float] = 0
    comision_monto: Optional[float] = None
    notas: Optional[str] = None


class PolizaUpdateBody(BaseModel):
    numero_poliza: Optional[str] = None
    ramo: Optional[str] = None
    aseguradora: Optional[str] = None
    estado: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    suma_asegurada: Optional[float] = None
    prima: Optional[float] = None
    moneda: Optional[str] = None
    forma_pago: Optional[str] = None
    comision_pct: Optional[float] = None
    notas: Optional[str] = None


@router.get("/api/polizas")
def listar(request: Request, agente=Depends(get_agente)):
    return crud.listar(dict(request.query_params))


@router.get("/api/polizas/comisiones")
def comisiones(fecha_inicio: Optional[str] = None, fecha_fin: Optional[str] = None, agente=Depends(get_agente)):
    return crud.resumen_comisiones(fecha_inicio, fecha_fin)


@router.post("/api/polizas", status_code=201)
def crear(body: PolizaBody, agente=Depends(get_agente)):
    try:
        return crud.crear(body.model_dump())
    except Exception:
        raise HTTPException(500, detail="Error al crear póliza")


@router.put("/api/polizas/{poliza_id}")
def actualizar(poliza_id: str, body: PolizaUpdateBody, agente=Depends(get_agente)):
    resultado = crud.actualizar(poliza_id, body.model_dump(exclude_none=True))
    if not resultado:
        raise HTTPException(404, detail="Póliza no encontrada")
    return {"ok": True}


@router.delete("/api/polizas/{poliza_id}")
def eliminar(poliza_id: str, agente=Depends(get_agente)):
    if not crud.eliminar(poliza_id):
        raise HTTPException(404, detail="Póliza no encontrada")
    return {"ok": True}
