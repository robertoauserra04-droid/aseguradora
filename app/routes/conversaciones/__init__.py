from fastapi import APIRouter
from .lista import router as lista_router
from .detalle import router as detalle_router
from .estado import router as estado_router
from .notas import router as notas_router
from .cotizaciones import router as cotizaciones_router
from .cliente import router as cliente_router
from .seguros import router as seguros_router

router = APIRouter()
router.include_router(lista_router)
router.include_router(detalle_router)
router.include_router(estado_router)
router.include_router(notas_router)
router.include_router(cotizaciones_router)
router.include_router(cliente_router)
router.include_router(seguros_router)
