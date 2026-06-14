def build_tools(slots_info: dict) -> list:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "registrar_interes",
                "description": (
                    "Registra el tipo de seguro que le interesa al cliente. "
                    "Úsalo tan pronto identifiques de qué seguro quiere hablar el cliente."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tipo_seguro": {
                            "type": "string",
                            "enum": ["vida", "medical", "auto", "daño", "viaje", "mascotas"],
                            "description": "Tipo de seguro de interés del cliente.",
                        },
                        "resumen_datos": {
                            "type": "string",
                            "description": "Resumen breve de los datos recopilados del cliente.",
                        },
                    },
                    "required": ["tipo_seguro"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "escalar_a_agente",
                "description": (
                    "Escala la conversación a un asesor humano cuando el cliente lo pide "
                    "explícitamente o cuando la consulta requiere atención personalizada."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "motivo": {
                            "type": "string",
                            "description": "Motivo por el que se escala.",
                        },
                    },
                    "required": ["motivo"],
                },
            },
        },
    ]

    slots = slots_info.get("slots", []) if slots_info else []
    if slots:
        tools.append({
            "type": "function",
            "function": {
                "name": "agendar_cita",
                "description": "Agenda una cita con un asesor de Seguros Carguill cuando el cliente confirma un horario disponible.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "slot_index": {"type": "number", "description": "Índice del slot elegido (0-based)."},
                        "motivo": {"type": "string", "description": "Motivo o tipo de seguro de la cita."},
                        "tipo_seguro": {
                            "type": "string",
                            "enum": ["vida", "medical", "auto", "daño", "viaje", "mascotas"],
                            "description": "Tipo de seguro para el que se agenda la cita.",
                        },
                    },
                    "required": ["slot_index", "motivo"],
                },
            },
        })

    return tools
