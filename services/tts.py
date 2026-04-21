from __future__ import annotations

from io import BytesIO


def synthesize(text: str, lang: str = "es") -> bytes:
    """Genera un MP3 con gTTS y lo devuelve en bytes.

    Si gTTS falla (sin red) devolvemos b"" para que el caller pueda
    omitir el reproductor sin romper la UI.
    """
    try:
        from gtts import gTTS  # import diferido para permitir arranque sin red
    except ImportError:
        return b""
    try:
        buf = BytesIO()
        gTTS(text=text, lang=lang).write_to_fp(buf)
        return buf.getvalue()
    except Exception:
        return b""
