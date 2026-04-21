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
- `pages/` — páginas Streamlit (driver / admin).
- `db/` — modelos SQLModel, sesión, seed.
- `services/` — mocks de DGT, EMT, AEMET, eventos + cliente LLM + TTS.
- `ui/` — helpers de mapas, timeline, alertas, PDF, auth.
