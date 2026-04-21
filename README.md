# Avzd4iver — Gestión de Flota de Autobuses Madrid

Aplicación multipágina Streamlit para planificación diaria de rutas y
gestión de incidencias en tiempo real de la flota de autobuses urbanos
de Madrid.

## Arranque rápido

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

La base de datos SQLite (`fleet.db`) se crea y se siembra automáticamente
la primera vez que se arranca la app.

## Credenciales demo

| Rol    | Usuario | Contraseña |
|--------|---------|------------|
| Admin  | `admin` | `admin`    |
| Driver | `juan`  | `1234`     |
| Driver | `maria` | `1234`     |
| Driver | `pedro` | `1234`     |
| Driver | `lucia` | `1234`     |
| Driver | `carlos`| `1234`     |

## LLM real (opcional)

Por defecto las respuestas de emergencia usan un protocolo mock. Para
usar OpenRouter con Claude Haiku 4.5:

```bash
export OPENROUTER_API_KEY=sk-or-...
# opcional:
export OPENROUTER_MODEL="anthropic/claude-haiku-4.5"
streamlit run app.py
```

## Estructura

- `app.py` — login y landing.
- `pages/` — páginas Streamlit:
  - `1_Driver_Turno.py` — plan diario, briefing hablado, handoff, historial.
  - `2_Driver_Asistente.py` — radar crowdsourced, voz, protocolos paso a paso, pánico + dead-man.
  - `3_Driver_Incidencia.py` — incidencia formal con IA + audio.
  - `4_Admin_Asignaciones.py` — asignaciones editables.
  - `5_Admin_LiveMap.py` — mapa en vivo con pánicos, incidencias y crowd.
- `db/` — modelos SQLModel, sesión, seed.
- `services/` — mocks DGT/EMT/AEMET/eventos + LLM + TTS + crowd + voice + protocols.
- `ui/` — helpers de mapas, timeline, alertas, PDF, auth.

## Transcripción de voz (opcional)

La pestaña Voz del asistente graba con `st.audio_input`. Para transcribir audio:

```bash
export OPENAI_API_KEY=sk-...
```

Si no hay clave, escribe el comando en el campo de texto como fallback.
