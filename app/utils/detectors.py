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


def quiere_asesor_humano(texto: str) -> bool:
    if not texto:
        return False
    lower = texto.lower()
    triggers = ["hablar con", "hablar a", "comunicar con", "asesor", "agente",
                "persona", "humano", "representante", "ejecutivo", "llamar"]
    return any(t in lower for t in triggers)
