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


def detectar_tipo_seguro(texto: str) -> str | None:
    if not texto:
        return None
    lower = texto.lower()
    for tipo, keywords in SEGUROS_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return tipo
    return None


# Términos genéricos de seguros que NO definen un tipo concreto, pero sí indican
# que el mensaje es sobre seguros (para el modo "solo seguros" del bot).
SEGUROS_GENERICOS = [
    "seguro", "seguros", "aseguranza", "asegurar", "aseguro", "asegura",
    "aseguradora", "póliza", "poliza", "cotización", "cotizacion", "cotizar",
    "cotiza", "cobertura", "prima", "asegurado", "coberturas",
]


def menciona_seguros(texto: str) -> bool:
    """True si el mensaje habla de seguros, ya sea un tipo concreto (auto, vida…)
    o un término genérico (seguro, póliza, cotización…).

    Se usa en el modo 'solo seguros': sirve para decidir si el bot debe arrancar.
    Nota: 'seguro' también significa 'cierto/a salvo' en español, así que en raras
    ocasiones puede dar un falso positivo (ej. "estoy seguro"); se prioriza no dejar
    callado al cliente que sí pregunta por un seguro.
    """
    if not texto:
        return False
    lower = texto.lower()
    if any(g in lower for g in SEGUROS_GENERICOS):
        return True
    return detectar_tipo_seguro(texto) is not None


def quiere_asesor_humano(texto: str) -> bool:
    if not texto:
        return False
    lower = texto.lower()
    triggers = ["hablar con", "hablar a", "comunicar con", "asesor", "agente",
                "persona", "humano", "representante", "ejecutivo", "llamar"]
    return any(t in lower for t in triggers)
