from __future__ import annotations

from datetime import date

import streamlit as st
from sqlmodel import select
from streamlit_folium import st_folium

from db.models import Assignment, Bus, Line
from db.session import get_session
from services.plan_builder import build_plan
from ui.auth import require_role
from ui.maps import build_driver_map
from ui.pdf import render_plan_pdf
from ui.timeline import render_timeline_figure

st.set_page_config(page_title="Turno del conductor", page_icon="🗺️", layout="wide")

user = require_role("driver")

st.title("🗺️ Configuración de turno")
st.caption("Selecciona tu asignación y genera tu plan personalizado.")

with get_session() as s:
    buses = s.exec(select(Bus).order_by(Bus.plate)).all()
    lines = s.exec(select(Line).order_by(Line.code)).all()
    today = date.today()
    todays_assignment = s.exec(
        select(Assignment).where(
            Assignment.driver_id == user.id,
            Assignment.shift_date == today,
        )
    ).first()

if not buses or not lines:
    st.error("No hay autobuses o líneas en la base de datos. Ejecuta el seed.")
    st.stop()

default_bus_idx = 0
default_line_idx = 0
if todays_assignment:
    for i, b in enumerate(buses):
        if b.id == todays_assignment.bus_id:
            default_bus_idx = i
            break
    for i, ln in enumerate(lines):
        if ln.id == todays_assignment.line_id:
            default_line_idx = i
            break

col_a, col_b, col_c = st.columns(3)
with col_a:
    bus = st.selectbox(
        "Autobús",
        buses,
        index=default_bus_idx,
        format_func=lambda b: f"{b.plate} — {b.model} ({b.type})",
    )
with col_b:
    line = st.selectbox(
        "Línea",
        lines,
        index=default_line_idx,
        format_func=lambda ln: f"{ln.code} — {ln.name}",
    )
with col_c:
    shift_date = st.date_input("Fecha del turno", value=today)

if st.button("⚡ Generar plan", type="primary", use_container_width=True):
    st.session_state["current_plan"] = build_plan(user, bus, line, shift_date)

plan = st.session_state.get("current_plan")
if plan is None:
    st.info("Configura los parámetros y pulsa **Generar plan** para ver tu turno.")
    st.stop()

if (
    plan.driver.id != user.id
    or plan.bus.id != bus.id
    or plan.line.id != line.id
    or plan.shift_date != shift_date
):
    st.warning("Los parámetros han cambiado. Pulsa de nuevo **Generar plan** para actualizar.")

st.divider()
st.subheader(
    f"Plan — Línea {plan.line.code} · {plan.bus.plate} · {plan.shift_date.strftime('%d/%m/%Y')}"
)

tab_timeline, tab_map, tab_alerts, tab_meta = st.tabs(
    ["🕒 Timeline", "🗺️ Mapa", "⚠️ Alertas", "📊 Detalles"]
)

with tab_timeline:
    fig = render_timeline_figure(plan.timeline_df)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Horario por parada"):
        st.dataframe(plan.timetable, use_container_width=True, height=300)

with tab_map:
    fmap = build_driver_map(plan.geometry, plan.stops, plan.black_spots, plan.events)
    st_folium(fmap, height=520, use_container_width=True, returned_objects=[])

with tab_alerts:
    if not plan.alerts:
        st.success("Sin alertas relevantes para este turno.")
    for alert in plan.alerts:
        msg = alert["message"]
        if alert["severity"] == "error":
            st.error(msg)
        elif alert["severity"] == "warning":
            st.warning(msg)
        else:
            st.info(msg)

with tab_meta:
    ws = plan.weather_summary
    cols = st.columns(4)
    cols[0].metric("Tª mínima", f"{ws.get('min_temp', '?')}ºC")
    cols[1].metric("Tª máxima", f"{ws.get('max_temp', '?')}ºC")
    cols[2].metric("Lluvia acumulada", f"{ws.get('total_rain_mm', 0)} mm")
    cols[3].metric("Paradas", len(plan.stops))
    st.caption(f"Condiciones previstas: {ws.get('conditions', '-')}")
    if plan.events:
        st.markdown("**Eventos en la ciudad hoy:**")
        for ev in plan.events:
            st.markdown(f"- {ev['name']} @ {ev['venue']} ({ev['start']}-{ev['end']})")

st.divider()
pdf_bytes = render_plan_pdf(plan)
st.download_button(
    "📄 Descargar plan en PDF",
    data=pdf_bytes,
    file_name=(
        f"plan_{plan.line.code}_{plan.bus.plate}_"
        f"{plan.shift_date.strftime('%Y%m%d')}.pdf"
    ),
    mime="application/pdf",
    use_container_width=True,
)
