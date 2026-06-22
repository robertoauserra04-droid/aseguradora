import json
from openai import OpenAI
from app.config.env import OPENAI_API_KEY
from app.services.ai.snapshot import build_snapshot
from app.services.ai.prompt import build_system_prompt, build_messages
from app.services.ai.tools import build_tools
from app.services.ai.tool_handlers import handle_tool_call

_client = None


def _get_openai() -> OpenAI | None:
    global _client
    if not _client and OPENAI_API_KEY:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def generar_respuesta(conversacion_id: str) -> str | None:
    openai = _get_openai()
    if not openai:
        return None

    snapshot = build_snapshot(conversacion_id)
    if not snapshot["cfg"] or not snapshot["cfg"].get("activo_global"):
        return None

    contexto = snapshot["cfg"].get("contexto") or {}
    modelo = "gpt-4o-mini"  # modelo fijo (no configurable desde el panel)
    try:
        temperatura = float(contexto.get("temperatura", 0.65))
    except (ValueError, TypeError):
        temperatura = 0.65

    system_prompt = build_system_prompt(snapshot["cfg"], snapshot["faqs"], snapshot["slots_info"])
    messages = build_messages(system_prompt, snapshot["mensajes"])
    tools = build_tools(snapshot["slots_info"])

    kwargs = {"model": modelo, "messages": messages, "max_tokens": 400, "temperature": temperatura}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    resp = openai.chat.completions.create(**kwargs)
    choice = resp.choices[0]

    if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
        messages.append(choice.message)

        for tool_call in choice.message.tool_calls:
            args = json.loads(tool_call.function.arguments)
            result = handle_tool_call(
                tool_call.function.name,
                args,
                {"conversacion_id": conversacion_id,
                 "conversacion": snapshot["conversacion"],
                 "slots_info": snapshot["slots_info"]},
            )
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

        resp2 = openai.chat.completions.create(
            model=modelo, messages=messages, max_tokens=300, temperature=temperatura
        )
        return (resp2.choices[0].message.content or "").strip() or None

    return (choice.message.content or "").strip() or None


def _handle_tool_prueba(nombre: str, args: dict) -> str:
    """Handler de tools para el modo prueba — NO toca la base de datos."""
    if nombre == "registrar_interes":
        return f"Interés en seguro de tipo \"{args.get('tipo_seguro')}\" registrado (simulado)."
    if nombre == "escalar_a_agente":
        return "Conversación marcada para un asesor humano (simulado)."
    if nombre == "agendar_cita":
        return "Cita agendada (simulado)."
    return "Acción simulada."


def responder_prueba(historial: list) -> str:
    """Genera una respuesta del bot para el MODO PRUEBA del panel.

    Usa la misma configuración (perfil, tono, FAQs, reglas) pero:
    - no requiere que el bot esté activo globalmente,
    - no lee ni escribe conversaciones reales,
    - no ejecuta tools sobre la BD ni envía WhatsApp.
    """
    from app.config.database import query
    from app.config.env import OPENAI_API_KEY

    if not OPENAI_API_KEY:
        return "⚠️ Falta configurar OPENAI_API_KEY para poder probar el bot."

    openai = _get_openai()
    cfg_r = query("SELECT instrucciones, activo_global, contexto FROM bot_config WHERE id = 1")
    cfg = cfg_r.rows[0] if cfg_r.rows else {"instrucciones": "", "contexto": {}}
    faqs = query("SELECT pregunta, respuesta FROM bot_faq WHERE activo = true ORDER BY orden, created_at").rows

    contexto = cfg.get("contexto") or {}
    modelo = "gpt-4o-mini"  # modelo fijo (no configurable desde el panel)
    try:
        temperatura = float(contexto.get("temperatura", 0.65))
    except (ValueError, TypeError):
        temperatura = 0.65

    slots_info = {"texto": "", "slots": []}  # sin calendario en modo prueba
    system_prompt = build_system_prompt(cfg, faqs, slots_info)
    messages = [{"role": "system", "content": system_prompt}] + (historial or [])
    tools = build_tools(slots_info)

    kwargs = {"model": modelo, "messages": messages, "max_tokens": 400, "temperature": temperatura}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    resp = openai.chat.completions.create(**kwargs)
    choice = resp.choices[0]

    if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
        messages.append(choice.message)
        for tc in choice.message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except Exception:
                args = {}
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": _handle_tool_prueba(tc.function.name, args)})
        resp2 = openai.chat.completions.create(
            model=modelo, messages=messages, max_tokens=300, temperature=temperatura
        )
        return (resp2.choices[0].message.content or "").strip() or "(sin respuesta)"

    return (choice.message.content or "").strip() or "(sin respuesta)"
