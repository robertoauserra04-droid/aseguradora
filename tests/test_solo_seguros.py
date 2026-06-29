"""Tests del modo "solo seguros" del bot.

Cubre:
  - detectar_tipo_seguro  (clasificación de tipo)
  - menciona_seguros      (¿el mensaje es sobre seguros? genérico + por tipo)
  - _es_sobre_seguros     (el candado real que usa ejecutar_bot)

Se ejecuta con pytest  ->  python -m pytest aseguradora/tests/test_solo_seguros.py -v
o directo            ->  python aseguradora/tests/test_solo_seguros.py
No requiere base de datos: se inyectan stubs de app.config.* y app.crud.
"""
import sys
import types
from pathlib import Path

# ── Hacer importable el paquete `app` ───────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]   # .../aseguradora
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Stub de app.config.env (sin .env real) ──────────────────────────────────
_fake_env = types.ModuleType("app.config.env")
_fake_env.OPENAI_API_KEY = "test-key"
_fake_env.GOOGLE_CALENDAR_ID = ""
_fake_env.DATABASE_URL = ""
_fake_env.NODE_ENV = "test"
_fake_env.__getattr__ = lambda name: ""          # cualquier otra var -> ""
sys.modules["app.config.env"] = _fake_env

# ── Stub de app.config.database (sin pool psycopg2) ─────────────────────────
_fake_db = types.ModuleType("app.config.database")


class QueryResult:
    def __init__(self, rows, rowcount=0):
        self.rows = rows
        self.rowcount = rowcount


_fake_db.QueryResult = QueryResult
_QUERY = {"fn": lambda sql, params=None: QueryResult([])}
_fake_db.query = lambda sql, params=None: _QUERY["fn"](sql, params)
sys.modules["app.config.database"] = _fake_db

# ── Stub de app.crud (webhook_service hace `from app import crud`) ───────────
import app  # paquete real (vacío)
_fake_crud = types.ModuleType("app.crud")
sys.modules["app.crud"] = _fake_crud
app.crud = _fake_crud

# ── Imports bajo prueba (ya con los stubs montados) ─────────────────────────
from app.utils.detectors import detectar_tipo_seguro, menciona_seguros
from app.services.webhook_service import _es_sobre_seguros


def _set_query(fn):
    _QUERY["fn"] = fn


def _handler(tipo_seguro=None, bot_existe=False, ultimo_cliente=None, hay_conv=True):
    """Construye un stub de `query` que responde según las 3 consultas que hace
    _es_sobre_seguros."""
    def h(sql, params=None):
        if "tipo_seguro FROM conversaciones" in sql:
            return QueryResult([{"tipo_seguro": tipo_seguro}] if hay_conv else [])
        if "autor = 'bot'" in sql:
            return QueryResult([{"existe": 1}] if bot_existe else [])
        if "autor = 'cliente'" in sql:
            return QueryResult([{"contenido": ultimo_cliente}] if ultimo_cliente is not None else [])
        return QueryResult([])
    return h


# ════════════════════════════════════════════════════════════════════════════
# PARTE A — detectar_tipo_seguro (clasificación de tipo)
# ════════════════════════════════════════════════════════════════════════════
CASOS_TIPO = [
    ("quiero un seguro de auto", "auto"),
    ("es un Honda 2020", "auto"),           # 'honda'? no -> revisar: 'auto' no está... ver nota
    ("necesito gastos médicos", "medical"),
    ("me interesa GMM", "medical"),
    ("seguro de vida para mi familia", "vida"),
    ("quiero asegurar mi casa", "daño"),
    ("seguro para mi negocio", "daño"),
    ("voy de viaje a Europa", "viaje"),
    ("tengo un perro", "mascotas"),
    ("hola buenas tardes", None),
    ("¿qué precio tiene un iphone?", None),
]


def test_detectar_tipo_seguro():
    fallos = []
    for texto, esperado in CASOS_TIPO:
        got = detectar_tipo_seguro(texto)
        # "es un Honda 2020" no tiene keyword de tipo -> None (caso de seguimiento)
        if texto == "es un Honda 2020":
            esperado = None
        if got != esperado:
            fallos.append(f"  detectar_tipo_seguro({texto!r}) = {got!r}, esperaba {esperado!r}")
    assert not fallos, "\n" + "\n".join(fallos)


# ════════════════════════════════════════════════════════════════════════════
# PARTE B — menciona_seguros (genérico + por tipo) — el arreglo del hueco
# ════════════════════════════════════════════════════════════════════════════
DEBE_SER_SEGUROS = [
    "quiero un seguro",
    "hola, me interesa un seguro",
    "info de seguros por favor",
    "me das una cotización",
    "quiero cotizar",
    "necesito una póliza",
    "necesito asegurar mi negocio",
    "¿qué cobertura tiene?",
    "seguro de auto",
    "gastos médicos mayores",
    "GMM",
    "quiero asegurar a mi mascota",
    "Seguros Carguill, ¿me ayudan?",
]

NO_ES_SEGUROS = [
    "hola",
    "buenas tardes",
    "¿qué precio tiene un iphone?",
    "gracias",
    "¿a qué hora abren?",
    "¿dónde están ubicados?",
    "",
    None,
    # Falsos positivos por subcadena que el fix de límite de palabra (\b) elimina:
    "saludos a todos",          # 'saludos' ya no matchea 'salud'
    "ya estoy casado",          # 'casado' ya no matchea 'casa'
    "necesito un motor nuevo",  # 'motor' ya no matchea 'moto'
    "se me olvida siempre",     # 'olvida' ya no matchea 'vida'
    # Falsos positivos por palabra ambigua que la neutralización elimina:
    "estoy seguro que no",      # 'seguro' = cierto, no el sustantivo
    "de seguro vienen mañana",  # 'de seguro' = seguramente
    "mi prima viene el lunes",  # 'prima' = pariente, no el costo del seguro
]


def test_menciona_seguros_positivos():
    fallos = [t for t in DEBE_SER_SEGUROS if not menciona_seguros(t)]
    assert not fallos, "Debió detectar SEGUROS y no lo hizo:\n  " + "\n  ".join(map(repr, fallos))


def test_menciona_seguros_negativos():
    fallos = [repr(t) for t in NO_ES_SEGUROS if menciona_seguros(t)]
    assert not fallos, "NO debió detectar seguros:\n  " + "\n  ".join(fallos)


def test_seguro_ambiguo_ya_no_es_falso_positivo():
    """'seguro' como adjetivo ('cierto') ya NO dispara al bot: la capa de
    neutralización lo descarta. Antes era un falso positivo aceptado a propósito;
    ahora se corrige para no responder fuera de tema."""
    assert menciona_seguros("estoy seguro que no quiero nada") is False


def test_mensaje_mixto_conserva_el_seguro_real():
    """Si el mensaje mezcla un uso ambiguo con uno real, la detección debe ganar:
    se neutraliza 'estoy seguro' pero se conserva el 'seguro de auto'."""
    assert menciona_seguros("estoy seguro que quiero un seguro de auto") is True


# ════════════════════════════════════════════════════════════════════════════
# PARTE C — _es_sobre_seguros (el candado de ejecutar_bot)
# ════════════════════════════════════════════════════════════════════════════
def test_modo_apagado_siempre_responde():
    # solo_seguros ausente/False -> comportamiento de siempre (responde a todo)
    _set_query(_handler(ultimo_cliente="hola"))
    assert _es_sobre_seguros("c1", {}) is True
    assert _es_sobre_seguros("c1", {"solo_seguros": False}) is True


def test_responde_si_ya_tiene_tipo_seguro():
    _set_query(_handler(tipo_seguro="auto", ultimo_cliente="es un honda 2020"))
    assert _es_sobre_seguros("c1", {"solo_seguros": True}) is True


def test_responde_si_bot_ya_enganchado():
    # tipo_seguro NULL pero el bot ya respondió antes -> sigue la conversación
    _set_query(_handler(tipo_seguro=None, bot_existe=True, ultimo_cliente="¿y qué más?"))
    assert _es_sobre_seguros("c1", {"solo_seguros": True}) is True


def test_responde_si_ultimo_mensaje_menciona_seguros():
    _set_query(_handler(tipo_seguro=None, bot_existe=False, ultimo_cliente="quiero un seguro"))
    assert _es_sobre_seguros("c1", {"solo_seguros": True}) is True


def test_callado_si_mensaje_no_es_de_seguros():
    _set_query(_handler(tipo_seguro=None, bot_existe=False, ultimo_cliente="hola, ¿precio de un iphone?"))
    assert _es_sobre_seguros("c1", {"solo_seguros": True}) is False


def test_callado_si_solo_saluda():
    _set_query(_handler(tipo_seguro=None, bot_existe=False, ultimo_cliente="hola"))
    assert _es_sobre_seguros("c1", {"solo_seguros": True}) is False


def test_callado_sin_mensajes():
    _set_query(_handler(tipo_seguro=None, bot_existe=False, ultimo_cliente=None, hay_conv=True))
    assert _es_sobre_seguros("c1", {"solo_seguros": True}) is False


# ── Runner standalone (sin pytest) ──────────────────────────────────────────
if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    ok = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
            ok += 1
        except AssertionError as e:
            print(f"FAIL  {fn.__name__}{e}")
        except Exception as e:
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{ok}/{len(fns)} tests OK")
    sys.exit(0 if ok == len(fns) else 1)
