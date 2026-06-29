import re

SEGUROS_KEYWORDS = {
    "vida":    ["vida", "seguro de vida", "fallecimiento", "muerte", "beneficiario", "ahorro", "plan de ahorro"],
    "medical": ["médico", "medico", "salud", "gastos médicos", "gastos medicos",
                "hospital", "hospitalización", "hospitalizacion", "enfermedad",
                "consulta médica", "doctor", "seguro de salud", "gmm"],
    "auto":    ["auto", "carro", "coche", "vehículo", "vehiculo", "automóvil", "automovil",
                "flota", "camioneta", "pickup", "moto", "motocicleta", "seguro de auto"],
    "daño":    ["daño", "daños", "dano", "casa", "hogar", "negocio", "empresa",
                "propiedad", "incendio", "robo", "responsabilidad civil"],
    "viaje":   ["viaje", "viajar", "viajero", "turista", "vuelo", "vacaciones", "continental assist"],
    "mascotas":["mascota", "perro", "gato", "veterinario", "animal"],
}

# Para cada tipo, una regex que exige LÍMITE DE PALABRA (\b) alrededor de cada
# keyword. Esto evita los falsos positivos por subcadena: 'saludos' ya no matchea
# 'salud', 'casado' ya no matchea 'casa', 'motor' ya no matchea 'moto', etc.
# (mismo patrón determinista que consultorios-medicos/services/ai/guards.py).
_TIPO_REGEX = {
    tipo: re.compile(r"\b(?:" + "|".join(re.escape(kw) for kw in kws) + r")\b", re.IGNORECASE)
    for tipo, kws in SEGUROS_KEYWORDS.items()
}


def detectar_tipo_seguro(texto: str) -> str | None:
    if not texto:
        return None
    for tipo, rx in _TIPO_REGEX.items():
        if rx.search(texto):
            return tipo
    return None


# Términos genéricos de seguros que NO definen un tipo concreto, pero sí indican
# que el mensaje es sobre seguros (para el modo "solo seguros" del bot).
SEGUROS_GENERICOS = [
    "seguro", "seguros", "aseguranza", "asegurar", "aseguro", "asegura",
    "aseguradora", "póliza", "poliza", "cotización", "cotizacion", "cotizar",
    "cotiza", "cobertura", "prima", "asegurado", "coberturas",
]

_GENERICOS_REGEX = re.compile(
    r"\b(?:" + "|".join(re.escape(g) for g in SEGUROS_GENERICOS) + r")\b", re.IGNORECASE
)

# Frases donde una palabra de seguros aparece, pero NO habla de un seguro:
#   - 'seguro/a/os/as' como adjetivo ('estoy seguro', 'seguro que sí', 'de seguro')
#   - 'prima' como pariente ('mi/tu/su prima') — pero NO 'la prima' (= el costo del seguro)
# Se BORRAN del texto antes de detectar, así un mensaje mixto como
# "estoy seguro que quiero un seguro de auto" conserva el 'seguro de auto' real.
_EXCLUSIONES_REGEX = re.compile(
    r"\b(?:estoy|estás|estas|está|esta|estaba|estamos|están|estan|estuve|"
    r"es|sea|ser[ií]a|muy|tan|bien|m[áa]s|nada)\s+segur[oa]s?\b"
    r"|\bsegur[oa]s?\s+(?:que|de\s+que)\b"
    r"|\bde\s+segur[oa]\b"
    r"|\b(?:mi|mis|tu|tus|su|sus)\s+prima(?:s)?\b",
    re.IGNORECASE,
)


def _neutralizar(texto: str) -> str:
    """Borra las frases ambiguas-pero-NO-seguros, dejando un espacio en su lugar."""
    return _EXCLUSIONES_REGEX.sub(" ", texto)


def menciona_seguros(texto: str) -> bool:
    """True si el mensaje habla de seguros, ya sea un tipo concreto (auto, vida…)
    o un término genérico (seguro, póliza, cotización…).

    Se usa en el modo 'solo seguros': sirve para decidir si el bot debe arrancar.
    La detección usa límites de palabra (\\b) y una capa de neutralización que
    descarta usos no-seguros de palabras ambiguas ('estoy seguro' = cierto,
    'mi prima' = pariente), para no disparar al bot por error.
    """
    if not texto:
        return False
    limpio = _neutralizar(texto)
    if _GENERICOS_REGEX.search(limpio):
        return True
    return detectar_tipo_seguro(limpio) is not None


def quiere_asesor_humano(texto: str) -> bool:
    if not texto:
        return False
    lower = texto.lower()
    triggers = ["hablar con", "hablar a", "comunicar con", "asesor", "agente",
                "persona", "humano", "representante", "ejecutivo", "llamar"]
    return any(t in lower for t in triggers)
