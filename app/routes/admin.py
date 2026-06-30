from fastapi import APIRouter, Depends, BackgroundTasks
from app.middleware.auth import get_agente
from app.utils.estados import MIGRACION_ESTADOS
from app.config.database import query

router = APIRouter()


@router.delete("/api/admin/datos-prueba")
def limpiar_datos(agente=Depends(get_agente)):
    from app.db.seed import limpiar_datos as _limpiar
    _limpiar()
    return {"success": True, "mensaje": "Datos de prueba eliminados correctamente"}


@router.post("/api/admin/seed")
def cargar_seed(agente=Depends(get_agente)):
    from app.db.seed import run_seed_force
    run_seed_force()
    return {"success": True, "mensaje": "Conversaciones de prueba cargadas correctamente"}


@router.post("/api/admin/migrar-estados")
def migrar_estados(agente=Depends(get_agente)):
    actualizadas = 0
    for estado_viejo, estado_nuevo in MIGRACION_ESTADOS.items():
        r = query(
            "UPDATE conversaciones SET estado = %s WHERE estado = %s",
            [estado_nuevo, estado_viejo],
        )
        actualizadas += r.rowcount
    return {
        "success": True,
        "actualizadas": actualizadas,
        "mensaje": f"{actualizadas} conversaciones migradas al nuevo sistema de etapas",
    }


# ── Google Drive ──────────────────────────────────────────────────────────────

@router.get("/api/drive/documentos")
def listar_docs(agente=Depends(get_agente)):
    r = query(
        "SELECT file_id, nombre, mime_type, actualizado_at FROM documentos_drive ORDER BY actualizado_at DESC"
    )
    return {"documentos": r.rows, "total": len(r.rows)}


@router.post("/api/drive/sincronizar")
def sincronizar_drive(background: BackgroundTasks, agente=Depends(get_agente)):
    def _run():
        from app.services.drive.client import sincronizar_documentos
        sincronizar_documentos()
    background.add_task(_run)
    return {"success": True, "mensaje": "Sincronización iniciada en background"}
