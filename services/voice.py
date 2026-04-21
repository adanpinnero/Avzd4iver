"""Asistente de voz del conductor.

- transcribe(audio_bytes) → texto (OpenAI Whisper si hay OPENAI_API_KEY, si no None).
- parse_intent(text) → dict con {"intent": ..., "category"?, "payload"?}.

El intent parser es offline, determinista y tolerante a acentos/errores.
"""

from __future__ import annotations

import os
import re
from io import BytesIO
from typing import Any

# Categorías de reporte que entiende el asistente (se mapean a services.crowd).
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "bump": ["bache"],
    "obstacle": ["obstaculo", "objeto", "rama", "basura en via", "piedra"],
    "jam": ["atasco", "retencion", "congestion", "parado", "caravana"],
    "protest": ["manifa", "manifestacion", "concentracion", "protesta"],
    "aggression": ["agresion", "pelea", "agresivo", "violencia"],
    "accident": ["accidente", "choque", "colision", "siniestro"],
    "construction": ["obra", "obras", "zanja"],
}

# Sinónimos conversacionales de "reportar".
_REPORT_VERBS = (
    "reporta",
    "reportar",
    "reporto",
    "avisa",
    "avisar",
    "aviso",
    "apunta",
    "apuntar",
    "marca",
    "marcar",
)

_PANIC_PHRASES = (
    "alerta roja",
    "emergencia",
    "panico",
    "auxilio",
    "socorro",
    "asistente alerta",
)

_STATUS_PHRASES = (
    "estado bateria",
    "cuanta bateria",
    "que bateria",
    "cuanto queda",
    "siguiente parada",
    "proxima parada",
    "voy adelantado",
    "voy retrasado",
    "voy a tiempo",
)

_READ_PHRASES = ("lee alertas", "leer alertas", "que incidencias", "alertas cercanas")

_PROTOCOL_PHRASES = (
    "protocolo",
    "que hago si",
    "guia",
    "guiame",
    "ayuda paso a paso",
)

_SILENCE_PHRASES = ("modo silencio", "silenciate", "callate", "no hables")

_STOP_PHRASES = ("para", "stop", "cancela", "cancelar")


def _normalize(text: str) -> str:
    # Quita tildes para matching tolerante.
    repl = str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUnN")
    return text.translate(repl).lower().strip()


def transcribe(audio_bytes: bytes, filename: str = "audio.wav") -> str | None:
    """Transcribe audio a texto con OpenAI Whisper si `OPENAI_API_KEY` está definida.

    Devuelve None si no hay API key o si falla. La UI debe ofrecer un
    campo de texto como fallback manual en ese caso.
    """
    if not audio_bytes:
        return None
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    try:
        client = OpenAI(api_key=key)
        buf = BytesIO(audio_bytes)
        buf.name = filename
        resp = client.audio.transcriptions.create(
            model="whisper-1",
            file=buf,
            language="es",
        )
        return (resp.text or "").strip() or None
    except Exception:
        return None


def parse_intent(text: str) -> dict[str, Any]:
    """Clasifica un comando del conductor en una intención accionable.

    Devuelve uno de:
      {"intent": "panic"}
      {"intent": "report", "category": "...", "note": "..."}
      {"intent": "status_query", "topic": "..."}
      {"intent": "read_alerts"}
      {"intent": "protocol", "hint": "..."}
      {"intent": "silence"}
      {"intent": "stop"}
      {"intent": "unknown", "text": "..."}
    """
    if not text:
        return {"intent": "unknown", "text": ""}

    norm = _normalize(text)

    for phrase in _PANIC_PHRASES:
        if phrase in norm:
            return {"intent": "panic"}

    for phrase in _STOP_PHRASES:
        # Evitar matchear "parada" / "parar" comunes: requerir palabra aislada.
        if re.search(rf"\b{re.escape(phrase)}\b", norm):
            return {"intent": "stop"}

    for phrase in _SILENCE_PHRASES:
        if phrase in norm:
            return {"intent": "silence"}

    # Reportes: "reporta bache", "avisa atasco", etc.
    if any(v in norm for v in _REPORT_VERBS):
        for category, keywords in _CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in norm:
                    return {
                        "intent": "report",
                        "category": category,
                        "note": text.strip(),
                    }
        # Verbo de reporte pero sin categoría reconocida.
        return {"intent": "report", "category": None, "note": text.strip()}

    for phrase in _STATUS_PHRASES:
        if phrase in norm:
            return {"intent": "status_query", "topic": phrase}

    for phrase in _READ_PHRASES:
        if phrase in norm:
            return {"intent": "read_alerts"}

    for phrase in _PROTOCOL_PHRASES:
        if phrase in norm:
            return {"intent": "protocol", "hint": text.strip()}

    return {"intent": "unknown", "text": text.strip()}


def short_ack(intent_result: dict[str, Any]) -> str:
    """Respuesta breve, aséptica, para TTS. Máximo 8 palabras."""
    i = intent_result.get("intent")
    if i == "panic":
        return "Alerta roja enviada. Central avisada."
    if i == "report":
        cat = intent_result.get("category")
        if cat:
            return "Reportado."
        return "No entendí la categoría. Repite."
    if i == "silence":
        return "Modo silencio activado."
    if i == "stop":
        return "Hecho."
    if i == "status_query":
        return "Consultando."
    if i == "read_alerts":
        return "Leyendo alertas."
    if i == "protocol":
        return "Selecciona un protocolo."
    return "No entendí, repite."
