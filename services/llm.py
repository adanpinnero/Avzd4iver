from __future__ import annotations

import os

SYSTEM_PROTOCOL_ES = (
    "Eres un supervisor de seguridad de la EMT Madrid. Un conductor acaba de "
    "reportar una incidencia desde su autobús. Devuelve un protocolo de "
    "actuación claro, en español, en máximo 6 pasos numerados, cada paso en "
    "una sola frase corta. Prioriza: seguridad de pasajeros, comunicación con "
    "centro de control, señalización, evacuación si procede. Evita jerga técnica "
    "y no inventes teléfonos."
)


def _client():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)


def _mock_protocol(description: str, bus_type: str) -> str:
    extra = ""
    if bus_type == "articulated":
        extra = " Ten en cuenta que el vehículo es articulado de 18m: señaliza ambos extremos."
    elif bus_type == "electric":
        extra = " Corta alimentación de alta tensión antes de abrir compartimentos."
    return (
        "**Protocolo de actuación (modo offline)**\n\n"
        "1. Detén el vehículo en zona segura y activa luces de emergencia.\n"
        "2. Informa por radio al centro de control del suceso: "
        f"'{description[:80]}'.\n"
        "3. Tranquiliza a los pasajeros y comprueba si hay heridos.\n"
        "4. Coloca triángulos o señaliza el perímetro si hay riesgo externo.\n"
        "5. Si procede evacuar, usa las puertas del lado derecho.\n"
        f"6. Permanece localizable hasta que llegue asistencia.{extra}"
    )


def emergency_protocol(
    description: str,
    bus_type: str,
    line_code: str,
    location_hint: str,
) -> str:
    client = _client()
    if client is None:
        return _mock_protocol(description, bus_type)
    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-haiku-4.5")
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROTOCOL_ES},
                {
                    "role": "user",
                    "content": (
                        f"Tipo de bus: {bus_type}. Línea: {line_code}. "
                        f"Ubicación aproximada: {location_hint}. "
                        f"Incidencia reportada: {description}"
                    ),
                },
            ],
            max_tokens=400,
            temperature=0.3,
        )
        content = resp.choices[0].message.content or ""
        return content.strip() or _mock_protocol(description, bus_type)
    except Exception as e:  # red caída, rate limit, etc.
        return _mock_protocol(description, bus_type) + f"\n\n_(fallback: {e.__class__.__name__})_"
