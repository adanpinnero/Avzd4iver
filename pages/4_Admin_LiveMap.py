from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st
from sqlmodel import select
from streamlit_autorefresh import st_autorefresh
from streamlit_folium import st_folium

from db.models import Assignment, Bus, Incident, Line, User
from db.session import get_session
from services.transit import get_route
from ui.auth import require_role
from ui.maps import build_admin_live_map

st.set_page_config(page_title="Mapa en vivo", page_icon="🛰️", layout="wide")

require_role("admin")

st.title("🛰️ Mapa de flota e incidencias en vivo")

refresh_seconds = st.sidebar.slider(
    "Autorefresco (segundos)", min_value=5, max_value=60, value=10, step=5
)
st_autorefresh(interval=refresh_seconds * 1000, key="live_map_refresh")

hours_window = st.sidebar.slider(
    "Ventana de incidencias (horas)", min_value=1, max_value=72, value=24
)

since = datetime.utcnow() - timedelta(hours=hours_window)
today = date.today()

with get_session() as s:
    incidents = s.exec(
        select(Incident)
        .where(Incident.status == "open")
        .where(Incident.created_at >= since)
        .order_by(Incident.created_at.desc())
    ).all()
    drivers_in_shift = s.exec(
        select(Assignment).where(Assignment.shift_date == today)
    ).all()
    active_line_ids = {a.line_id for a in drivers_in_shift}
    active_lines = s.exec(select(Line).where(Line.id.in_(active_line_ids))).all() if active_line_ids else []

    driver_map = {u.id: u.full_name for u in s.exec(select(User)).all()}
    bus_map = {b.id: b.plate for b in s.exec(select(Bus)).all()}
    line_map = {ln.id: ln.code for ln in s.exec(select(Line)).all()}

kpi_a, kpi_b, kpi_c, kpi_d = st.columns(4)
kpi_a.metric("Incidencias abiertas", len(incidents))
kpi_b.metric("Conductores en turno", len({a.driver_id for a in drivers_in_shift}))
kpi_c.metric("Buses asignados hoy", len({a.bus_id for a in drivers_in_shift}))
kpi_d.metric("Líneas activas", len(active_line_ids))

incident_payload = [
    {
        "id": inc.id,
        "lat": inc.lat,
        "lon": inc.lon,
        "description": inc.description,
        "created_at": inc.created_at.strftime("%d/%m %H:%M") + " UTC",
        "driver_name": driver_map.get(inc.driver_id, "-"),
        "bus_plate": bus_map.get(inc.bus_id, "-") if inc.bus_id else "-",
        "line_code": line_map.get(inc.line_id, "-") if inc.line_id else "-",
    }
    for inc in incidents
]

lines_geometry = {ln.code: get_route(ln.code).geometry for ln in active_lines}

fmap = build_admin_live_map(incident_payload, lines_geometry)
st_folium(fmap, height=560, use_container_width=True, returned_objects=[])

st.divider()
st.subheader("Incidencias abiertas (últimas en ventana seleccionada)")
if not incidents:
    st.info("No hay incidencias abiertas en esta ventana.")
else:
    for inc in incidents:
        with st.container(border=True):
            top = st.columns([1, 4, 1])
            top[0].markdown(f"**#{inc.id}**")
            top[1].markdown(
                f"**{driver_map.get(inc.driver_id, '-')}** · "
                f"Bus {bus_map.get(inc.bus_id, '-') if inc.bus_id else '-'} · "
                f"Línea {line_map.get(inc.line_id, '-') if inc.line_id else '-'}  \n"
                f"{inc.description}  \n"
                f"<small>{inc.created_at.strftime('%d/%m/%Y %H:%M')} UTC · "
                f"({inc.lat:.4f}, {inc.lon:.4f})</small>",
                unsafe_allow_html=True,
            )
            if top[2].button("Marcar resuelta", key=f"resolve_{inc.id}"):
                with get_session() as s:
                    row = s.get(Incident, inc.id)
                    if row:
                        row.status = "resolved"
                        s.add(row)
                        s.commit()
                st.rerun()
            if inc.ai_protocol:
                with st.expander("Ver protocolo IA"):
                    st.markdown(inc.ai_protocol)
