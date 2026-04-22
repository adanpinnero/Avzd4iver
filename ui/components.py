"""Componentes UI reusables (branded). Requieren `ui.theme.inject_css` inyectado."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st


def page_header(title: str, subtitle: str = "", icon: str = "🚌") -> None:
    """Cabecera branded con gradiente, icono grande y subtítulo."""
    sub_html = f'<div class="hero-sub">{_escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="hero-icon">{icon}</div>
            <div>
                <h1>{_escape(title)}</h1>
                {sub_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: Any, delta: str | None = None, color: str = "primary") -> None:
    """Tarjeta KPI. `color` ∈ {primary, accent, ok, warn, danger}."""
    color_class = "" if color == "primary" else color
    delta_html = ""
    if delta:
        dclass = "positive" if delta.startswith("+") else ("negative" if delta.startswith("-") else "")
        delta_html = f'<div class="kpi-delta {dclass}">{_escape(delta)}</div>'
    st.markdown(
        f"""
        <div class="kpi-card {color_class}">
            <div class="kpi-label">{_escape(label)}</div>
            <div class="kpi-value">{_escape(str(value))}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def data_source_badge(source: str, last_update: datetime | None = None, is_mock: bool = False) -> None:
    """Badge que indica origen del dato y tiempo desde última actualización."""
    cls = "mock" if is_mock else ""
    fresh_text = "sin datos" if last_update is None else _humanize_delta(last_update)
    if not is_mock and last_update and _age_seconds(last_update) > 900:
        cls = "stale"
    st.markdown(
        f'<span class="source-badge {cls}"><span class="dot"></span>'
        f'{_escape(source)} · {_escape(fresh_text)}</span>',
        unsafe_allow_html=True,
    )


def severity_badge(severity: str) -> str:
    """Devuelve HTML de un `<span>` badge según severidad ('baja'|'media'|'alta')."""
    mapping = {
        "alta": ("badge-danger", "alta"),
        "media": ("badge-warn", "media"),
        "baja": ("badge-ok", "baja"),
    }
    cls, lbl = mapping.get(severity, ("badge-neutral", severity))
    return f'<span class="badge {cls}">{_escape(lbl)}</span>'


def aqi_banner(station: dict) -> None:
    """Banner de calidad del aire para la estación más cercana a la ruta."""
    aqi = station.get("aqi", 0)
    label = station.get("aqi_label", "sin datos")
    name = station.get("estacion", "-")
    no2 = station.get("no2")
    pm25 = station.get("pm25")
    o3 = station.get("o3")
    if aqi >= 80:
        badge_cls, emoji, msg = "badge-danger", "🚨", "Ventilación reducida recomendada."
    elif aqi >= 60:
        badge_cls, emoji, msg = "badge-warn", "⚠️", "Precaución colectivos sensibles."
    else:
        badge_cls, emoji, msg = "badge-ok", "🟢", "Condiciones aceptables."

    def _fmt(v):
        return "—" if v is None else f"{v:.0f}"

    st.markdown(
        f"""
        <div class="kpi-card {('danger' if aqi >= 80 else 'warn' if aqi >= 60 else 'ok')}"
             style="margin-bottom:0.8rem;">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;">
                <div>
                    <div class="kpi-label">Calidad del aire · {_escape(name)}</div>
                    <div class="kpi-value">
                        {emoji} {_escape(label.capitalize())}
                        <span class="badge {badge_cls}" style="margin-left:.5rem;">AQI {aqi}</span>
                    </div>
                    <div class="kpi-delta">{_escape(msg)}</div>
                </div>
                <div style="display:flex;gap:1.2rem;font-size:.88rem;color:var(--text-soft);">
                    <div><b>NO₂</b> {_fmt(no2)} µg/m³</div>
                    <div><b>PM₂.₅</b> {_fmt(pm25)} µg/m³</div>
                    <div><b>O₃</b> {_fmt(o3)} µg/m³</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _humanize_delta(when: datetime) -> str:
    secs = _age_seconds(when)
    if secs < 60:
        return f"hace {int(secs)}s"
    if secs < 3600:
        return f"hace {int(secs // 60)}m"
    if secs < 86400:
        return f"hace {int(secs // 3600)}h"
    return f"hace {int(secs // 86400)}d"


def _age_seconds(when: datetime) -> float:
    now = datetime.now(timezone.utc) if when.tzinfo else datetime.utcnow()
    return max(0.0, (now - when).total_seconds())


def _escape(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
