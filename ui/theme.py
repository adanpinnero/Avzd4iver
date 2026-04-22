"""Inyección de CSS global para un look consistente en todas las páginas.

Llama `inject_css()` una sola vez por página, arriba del todo. Es idempotente:
Streamlit deduplica el `<style>` por su contenido.
"""

from __future__ import annotations

import streamlit as st

_CSS = """
<style>
:root {
    --primary: #C81D25;
    --primary-dark: #8F1319;
    --accent: #1F6FEB;
    --bg: #FFFFFF;
    --bg-soft: #F4F5F7;
    --text: #1A1D24;
    --text-soft: #5A6270;
    --ok: #2F9E44;
    --warn: #E08E0B;
    --danger: #C81D25;
    --radius: 10px;
    --shadow: 0 1px 2px rgba(0,0,0,.06), 0 2px 8px rgba(0,0,0,.04);
}

/* Cabecera branded */
.app-hero {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: #fff;
    padding: 1.1rem 1.4rem;
    border-radius: var(--radius);
    margin: 0 0 1.2rem 0;
    box-shadow: var(--shadow);
    display: flex;
    align-items: center;
    gap: 1rem;
}
.app-hero .hero-icon {
    font-size: 2.4rem;
    line-height: 1;
}
.app-hero h1 {
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0;
    color: #fff;
}
.app-hero .hero-sub {
    font-size: 0.92rem;
    opacity: 0.88;
    margin-top: 0.15rem;
    color: #fff;
}

/* Tarjetas KPI */
.kpi-card {
    background: var(--bg-soft);
    border-left: 4px solid var(--primary);
    border-radius: var(--radius);
    padding: 0.9rem 1.1rem;
    min-height: 86px;
    box-shadow: var(--shadow);
}
.kpi-card.accent { border-left-color: var(--accent); }
.kpi-card.ok { border-left-color: var(--ok); }
.kpi-card.warn { border-left-color: var(--warn); }
.kpi-card.danger { border-left-color: var(--danger); }

.kpi-card .kpi-label {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-soft);
    margin-bottom: 0.35rem;
}
.kpi-card .kpi-value {
    font-size: 1.7rem;
    font-weight: 700;
    color: var(--text);
    line-height: 1.1;
}
.kpi-card .kpi-delta {
    font-size: 0.78rem;
    color: var(--text-soft);
    margin-top: 0.15rem;
}
.kpi-card .kpi-delta.positive { color: var(--ok); }
.kpi-card .kpi-delta.negative { color: var(--danger); }

/* Badges */
.badge {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    line-height: 1.4;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
.badge-ok { background: #E6F4EA; color: var(--ok); }
.badge-warn { background: #FFF4D6; color: var(--warn); }
.badge-danger { background: #FDECEE; color: var(--danger); }
.badge-neutral { background: var(--bg-soft); color: var(--text-soft); }

/* Data source badge (indica origen + frescura) */
.source-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.72rem;
    color: var(--text-soft);
    background: var(--bg-soft);
    border: 1px solid rgba(0,0,0,0.06);
    border-radius: 999px;
    padding: 0.15rem 0.6rem;
    margin-right: 0.35rem;
}
.source-badge .dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--ok);
}
.source-badge.stale .dot { background: var(--warn); }
.source-badge.mock .dot { background: var(--text-soft); }

/* Bloques de alerta más limpios dentro de expanders */
div[data-testid="stAlert"] {
    border-radius: var(--radius) !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--bg-soft);
}

/* Tabs más legibles */
button[data-baseweb="tab"] {
    font-weight: 600;
}

/* Inputs y selects redondeados */
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div {
    border-radius: 8px;
}

/* Tipografía ajustes finos */
h1, h2, h3 { letter-spacing: -0.01em; }

@media (prefers-color-scheme: dark) {
    :root {
        --bg: #15181E;
        --bg-soft: #1F232B;
        --text: #F3F4F6;
        --text-soft: #9AA3B2;
    }
    .kpi-card { background: var(--bg-soft); }
    .source-badge { border-color: rgba(255,255,255,0.08); }
    .badge-ok { background: #1A3C2A; }
    .badge-warn { background: #402E0E; }
    .badge-danger { background: #3C1418; }
}
</style>
"""


def inject_css() -> None:
    """Inyecta el CSS global. Idempotente."""
    st.markdown(_CSS, unsafe_allow_html=True)
