import io
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from app.config.database import query
from app.services.google_auth import get_credentials

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

_EXPORTABLES = {
    "application/vnd.google-apps.document":     "text/plain",
    "application/vnd.google-apps.spreadsheet":  "text/csv",
}


def _get_service():
    try:
        creds = get_credentials(_SCOPES)
        if not creds:
            return None
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.error("[Drive] Error al crear servicio: %s", e)
        return None


def _get_folder_id() -> str | None:
    r = query("SELECT drive_folder_id FROM bot_config WHERE id = 1")
    if r.rows:
        return (r.rows[0].get("drive_folder_id") or "").strip() or None
    return None


def listar_archivos(folder_id: str) -> list:
    svc = _get_service()
    if not svc:
        return []
    try:
        res = svc.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id, name, mimeType, modifiedTime)",
            pageSize=50,
        ).execute()
        return res.get("files", [])
    except Exception as e:
        logger.error("[Drive] Error al listar archivos: %s", e)
        return []


def _leer_contenido(svc, file_id: str, mime_type: str) -> str | None:
    try:
        if mime_type in _EXPORTABLES:
            export_mime = _EXPORTABLES[mime_type]
            data = svc.files().export(fileId=file_id, mimeType=export_mime).execute()
            return data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)

        if mime_type.startswith("text/"):
            buf = io.BytesIO()
            req = svc.files().get_media(fileId=file_id)
            dl = MediaIoBaseDownload(buf, req)
            done = False
            while not done:
                _, done = dl.next_chunk()
            return buf.getvalue().decode("utf-8", errors="replace")

        # PDF y formatos binarios sin conversión a texto: omitir contenido
        return None
    except Exception as e:
        logger.warning("[Drive] No se pudo leer %s (%s): %s", file_id, mime_type, e)
        return None


def sincronizar_documentos() -> int:
    folder_id = _get_folder_id()
    if not folder_id:
        logger.info("[Drive] Sin folder_id configurado, sync omitida")
        return 0

    svc = _get_service()
    if not svc:
        logger.warning("[Drive] Credenciales no configuradas, sync omitida")
        return 0

    archivos = listar_archivos(folder_id)
    actualizados = 0
    for f in archivos:
        contenido = _leer_contenido(svc, f["id"], f.get("mimeType", ""))
        if contenido is None:
            contenido = ""  # guardamos el nombre aunque no haya texto extraíble
        try:
            query(
                """INSERT INTO documentos_drive (file_id, nombre, mime_type, contenido_texto, actualizado_at)
                   VALUES (%s, %s, %s, %s, NOW())
                   ON CONFLICT (file_id) DO UPDATE
                   SET nombre = EXCLUDED.nombre,
                       mime_type = EXCLUDED.mime_type,
                       contenido_texto = EXCLUDED.contenido_texto,
                       actualizado_at = NOW()""",
                [f["id"], f["name"], f.get("mimeType"), contenido],
            )
            actualizados += 1
        except Exception as e:
            logger.error("[Drive] Error al guardar %s: %s", f["name"], e)

    # Limpiar registros de archivos que ya no están en Drive
    if archivos:
        ids_actuales = [f["id"] for f in archivos]
        placeholders = ", ".join(["%s"] * len(ids_actuales))
        query(
            f"DELETE FROM documentos_drive WHERE file_id NOT IN ({placeholders})",
            ids_actuales,
        )

    logger.info("[Drive] Sincronización completada: %d archivos", actualizados)
    return actualizados


def obtener_docs_para_contexto() -> list:
    """Retorna los documentos con texto para incluir en el prompt del bot."""
    r = query(
        """SELECT nombre, contenido_texto FROM documentos_drive
           WHERE contenido_texto IS NOT NULL AND contenido_texto <> ''
           ORDER BY actualizado_at DESC
           LIMIT 20"""
    )
    return r.rows
