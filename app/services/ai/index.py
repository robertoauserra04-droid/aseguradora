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

    system_prompt = build_system_prompt(snapshot["cfg"], snapshot["faqs"], snapshot["slots_info"])
    messages = build_messages(system_prompt, snapshot["mensajes"])
    tools = build_tools(snapshot["slots_info"])

    kwargs = {"model": "gpt-4o-mini", "messages": messages, "max_tokens": 400, "temperature": 0.65}
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
            model="gpt-4o-mini", messages=messages, max_tokens=300, temperature=0.65
        )
        return (resp2.choices[0].message.content or "").strip() or None

    return (choice.message.content or "").strip() or None
