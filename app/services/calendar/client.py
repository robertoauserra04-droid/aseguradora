from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
from googleapiclient.discovery import build
from app.config.env import GOOGLE_CALENDAR_ID
from app.services.google_auth import get_credentials

_SCOPES = ["https://www.googleapis.com/auth/calendar"]

TIMEZONE = "America/Monterrey"
_TZ = ZoneInfo(TIMEZONE)
HORA_INICIO = 9
HORA_FIN = 18

_DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fmt_slot_es(dt: datetime, hora: int) -> str:
    """Etiqueta legible en español sin depender del locale del contenedor."""
    return f"{_DIAS_ES[dt.weekday()]} {dt.day} de {_MESES_ES[dt.month - 1]} a las {hora}:00"


def _parse_google_dt(valor: str) -> datetime:
    """Parsea un dateTime de la API de Google preservando su offset real.
    Normaliza el sufijo 'Z' (UTC) que fromisoformat no acepta en versiones antiguas."""
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))

ETAPAS_EVENTO = {
    "tramite_oficina":     "Trámite en oficina",
    "tramite_aseguradora": "Envío a aseguradora",
    "entrega":             "Entrega de póliza",
    "vigente":             "Póliza activa — seguimiento",
}


def _get_calendar_id() -> str:
    """Retorna el Calendar ID: primero busca en bot_config (configurable desde panel),
    luego usa la variable de entorno como fallback."""
    try:
        from app.config.database import query as db_query
        r = db_query("SELECT calendar_id FROM bot_config WHERE id = 1")
        if r.rows:
            cal_id = (r.rows[0].get("calendar_id") or "").strip()
            if cal_id:
                return cal_id
    except Exception:
        pass
    return GOOGLE_CALENDAR_ID


def _get_service():
    creds = get_credentials(_SCOPES)
    if not creds:
        return None
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _proximos_dias_habiles(n: int = 3) -> list[datetime]:
    # En hora local (Monterrey): así los slots que se generan y muestran
    # coinciden con la hora real y con el campo timeZone que se envía a Google.
    dias = []
    d = datetime.now(_TZ) + timedelta(days=1)
    while len(dias) < n:
        if d.weekday() not in (5, 6):
            dias.append(d.replace(hour=0, minute=0, second=0, microsecond=0))
        d += timedelta(days=1)
    return dias


def consultar_disponibilidad() -> dict:
    svc = _get_service()
    cal_id = _get_calendar_id()
    if not svc or not cal_id:
        return {"texto": "", "slots": []}

    dias = _proximos_dias_habiles(3)
    time_min = dias[0].isoformat()
    time_max = (dias[-1] + timedelta(hours=23, minutes=59)).isoformat()

    busy = []
    try:
        fb = svc.freebusy().query(body={
            "timeMin": time_min,
            "timeMax": time_max,
            "timeZone": TIMEZONE,
            "items": [{"id": cal_id}],
        }).execute()
        busy = fb.get("calendars", {}).get(cal_id, {}).get("busy", [])
    except Exception as e:
        print(f"[Calendar] freebusy error: {e}")

    slots = []
    for dia in dias:
        for hora in range(HORA_INICIO, HORA_FIN):
            inicio = dia.replace(hour=hora)          # aware, tz=Monterrey
            fin = dia.replace(hour=hora + 1)
            ocupado = False
            for b in busy:
                b_ini, b_fin = b.get("start"), b.get("end")
                if not b_ini or not b_fin:
                    continue
                # Comparación entre datetimes aware; se preserva el offset real de Google
                # (no se fuerza UTC), así el solapamiento se calcula correctamente.
                if inicio < _parse_google_dt(b_fin) and fin > _parse_google_dt(b_ini):
                    ocupado = True
                    break
            if not ocupado:
                label = _fmt_slot_es(inicio, hora)
                slots.append({"inicio": inicio.isoformat(), "fin": fin.isoformat(), "label": label})

    mostrar = slots[:6]
    texto = ("Horarios disponibles:\n" + "\n".join(f"{i+1}. {s['label']}" for i, s in enumerate(mostrar))
             if mostrar else "No hay horarios disponibles los próximos 3 días hábiles.")

    return {"texto": texto, "slots": mostrar}


def crear_evento(titulo: str, descripcion: str, inicio: str, fin: str,
                 email_cliente: Optional[str] = None) -> dict:
    svc = _get_service()
    cal_id = _get_calendar_id()
    if not svc or not cal_id:
        raise RuntimeError("Google Calendar no configurado")

    event = {
        "summary": titulo,
        "description": descripcion or "",
        "start": {"dateTime": inicio, "timeZone": TIMEZONE},
        "end":   {"dateTime": fin,   "timeZone": TIMEZONE},
        "attendees": [{"email": email_cliente}] if email_cliente else [],
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 30}]},
    }
    r = svc.events().insert(
        calendarId=cal_id,
        body=event,
        sendUpdates="all" if email_cliente else "none",
    ).execute()
    return r


def crear_evento_etapa(etapa: str, conversacion: dict) -> Optional[dict]:
    if etapa not in ETAPAS_EVENTO:
        return None
    svc = _get_service()
    cal_id = _get_calendar_id()
    if not svc or not cal_id:
        return None

    titulo = f"[{ETAPAS_EVENTO[etapa]}] {conversacion.get('cliente_nombre', '')}"
    descripcion = (
        f"Cliente: {conversacion.get('cliente_nombre', '')}\n"
        f"Tel: {conversacion.get('cliente_telefono', '')}\n"
        f"Tipo seguro: {conversacion.get('tipo_seguro') or 'No definido'}"
    )
    # "Mañana" en hora local (no UTC). Para eventos all-day, Google exige que
    # end.date sea EXCLUSIVO (el día siguiente al último día del evento).
    hoy_local = datetime.now(_TZ).date()
    manana = (hoy_local + timedelta(days=1)).strftime("%Y-%m-%d")
    pasado_manana = (hoy_local + timedelta(days=2)).strftime("%Y-%m-%d")

    try:
        r = svc.events().insert(
            calendarId=cal_id,
            body={
                "summary": titulo,
                "description": descripcion,
                "start": {"date": manana},
                "end":   {"date": pasado_manana},
                "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 60}]},
            },
        ).execute()
        print(f"[Calendar] Evento etapa '{etapa}' creado: {r.get('id')}")
        return r
    except Exception as e:
        print(f"[Calendar] Error evento etapa: {e}")
        return None
