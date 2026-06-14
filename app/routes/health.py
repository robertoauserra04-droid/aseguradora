from fastapi import APIRouter
from app.config.database import query

router = APIRouter()


@router.get("/api/health")
def health():
    try:
        query("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}
