from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.config.database import query

router = APIRouter()


@router.get("/api/health")
def health():
    try:
        query("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        # 503 para que el orquestador (Railway) marque el servicio como unhealthy;
        # devolver 200 con status:error hace que crea que está sano con la BD caída.
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": str(e)},
        )
