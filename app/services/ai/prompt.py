def build_system_prompt(cfg: dict, faqs: list, slots_info: dict) -> str:
    c = cfg.get("contexto") or {}
    partes = []

    # ── Identidad: 100% desde la configuración del panel (sin nada hardcodeado de aseguradora) ──
    nombre_bot = (c.get("bot_nombre") or "Asistente").strip()
    empresa = (c.get("empresa") or "la empresa").strip()
    ciudad = (c.get("ciudad") or "").strip()
    ubic = f", ubicada en {ciudad}, México" if ciudad else ""
    partes.append(
        f"Eres {nombre_bot}, el asistente virtual de {empresa}{ubic}. "
        "Responde siempre en español, de forma clara y concisa."
    )

    # Descripción/rol del negocio: lo define el panel. Si no hay, un rol neutro mínimo.
    descripcion = (c.get("descripcion") or "").strip()
    if descripcion:
        partes.append(descripcion)
    else:
        partes.append(
            f"Tu función es atender a los clientes de {empresa}: entender lo que necesitan, "
            "resolver sus dudas con la información disponible y conectarlos con un asesor humano "
            "cuando haga falta."
        )

    if c.get("seguros"):
        partes.append("Productos/servicios que ofrecemos:\n" + "\n".join(f"• {s}" for s in c["seguros"]))

    if c.get("aseguradoras"):
        partes.append(f"Aseguradoras con las que trabajamos: {c['aseguradoras']}.")

    # Flujo de atención: lo define el panel (campo "proceso"). Ya no hay flujo de aseguradora fijo.
    if c.get("proceso"):
        partes.append("CÓMO DEBES ATENDER (síguelo en orden):\n" + c["proceso"].strip())

    # Las funciones siguen disponibles con cualquier flujo.
    partes.append(
        "Tienes funciones para registrar el interés del cliente, escalar la conversación a un "
        "asesor humano y agendar una cita; úsalas cuando corresponda."
    )

    # Datos que el bot SIEMPRE debe recopilar
    if c.get("datos_obligatorios"):
        partes.append(
            "Antes de agendar o escalar, asegúrate de tener estos datos del cliente:\n"
            + c["datos_obligatorios"].strip()
        )

    # Datos de la oficina
    oficina = []
    if c.get("direccion"): oficina.append(f"Dirección: {c['direccion']}")
    if c.get("telefono"): oficina.append(f"Teléfono: {c['telefono']}")
    if c.get("web"): oficina.append(f"Sitio web: {c['web']}")
    if oficina:
        partes.append("Datos de la oficina:\n" + "\n".join(f"• {o}" for o in oficina))

    if c.get("horario"):
        partes.append(f"Horario de atención: {c['horario']}.")

    tonos = {
        "formal":   "Responde en tono formal y profesional.",
        "amigable": "Responde en tono amigable y cercano.",
        "ambos":    "Responde en tono formal pero amigable y cálido.",
    }
    if c.get("tono") and c["tono"] in tonos:
        partes.append(tonos[c["tono"]])

    if c.get("bienvenida"):
        partes.append(f'Cuando un cliente escriba por primera vez salúdalo así: "{c["bienvenida"]}"')

    restricciones_extra = f"\n• {c['restricciones']}" if c.get("restricciones") else ""
    politica = f"\n• {c['politica_precios']}" if c.get("politica_precios") else ""
    prohibidos = f"\n• Temas prohibidos (no respondas sobre esto, escala a un asesor): {c['temas_prohibidos']}" if c.get("temas_prohibidos") else ""
    partes.append(
        "RESTRICCIONES IMPORTANTES:\n"
        "• NO inventes ni supongas información. Si algo NO está en esta configuración ni en la "
        "BASE DE CONOCIMIENTO, dilo con honestidad y ofrece conectar con un asesor humano. "
        "Prefiere decir \"no tengo ese dato, te conecto con un asesor\" antes que arriesgar una respuesta.\n"
        "• No inventes precios, cifras, fechas ni hagas promesas.\n"
        "• No proporciones datos personales de terceros.\n"
        f"• No te desvíes a temas ajenos a {empresa}; si insisten, ofrece pasar con un asesor.{politica}{prohibidos}{restricciones_extra}"
    )

    if cfg.get("instrucciones", "").strip():
        partes.append(cfg["instrucciones"].strip())

    if faqs:
        faq_texto = "\n\n".join(f"P: {f['pregunta']}\nR: {f['respuesta']}" for f in faqs)
        partes.append(f"BASE DE CONOCIMIENTO:\n{faq_texto}")

    if slots_info and slots_info.get("texto"):
        partes.append(
            slots_info["texto"] +
            '\nSi el cliente quiere agendar, usa la función "agendar_cita" con el índice del slot elegido (0-based).'
        )

    # Límite de longitud y firma
    if c.get("max_palabras"):
        partes.append(f"Responde de forma breve: máximo {c['max_palabras']} palabras por mensaje.")
    if c.get("firma"):
        partes.append(f'Cierra tus mensajes con: "{c["firma"]}"')

    # MODO ESTRICTO: el bot responde SOLO con lo configurado; si no, pasa a un humano.
    if c.get("modo_estricto"):
        handoff = (c.get("mensaje_handoff") or
                   "Excelente pregunta. Déjame conectarte con un asesor que te dará el detalle exacto. 🙌")
        partes.append(
            "MODO ESTRICTO (OBLIGATORIO): Responde ÚNICAMENTE con base en la información de esta "
            "configuración, las RESTRICCIONES y la BASE DE CONOCIMIENTO. Si la información necesaria "
            "para responder NO está aquí, NO la inventes, NO supongas ni uses conocimiento externo: "
            'llama a la función "escalar_a_agente" y responde EXACTAMENTE con este texto: '
            f'"{handoff}"'
        )

    return "\n\n".join(partes)


def build_messages(system_prompt: str, mensajes: list) -> list:
    messages = [{"role": "system", "content": system_prompt}]
    for m in reversed(mensajes):
        role = "user" if m["autor"] == "cliente" else "assistant"
        messages.append({"role": role, "content": m["contenido"]})
    return messages
