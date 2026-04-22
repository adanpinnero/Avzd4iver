from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st
from sqlmodel import select
from streamlit_autorefresh import st_autorefresh
from streamlit_folium import st_folium

from db.models import Assignment, Bus, Incident, Line, User
from db.session import get_session
from services import crowd, dgt, madrid_opendata
from services.transit import get_route
from ui.auth import require_role
from ui.components import data_source_badge, kpi_card, page_header
from ui.maps import build_admin_live_map
from ui.theme import inject_css

st.set_page_config(page_title="Mapa en vivo", page_icon="🛰️", layout="wide")
inject_css()

require_role("admin")

page_header(
    "Mapa de flota, incidencias y datos de ciudad",
    "Tiempo real: incidencias internas, crowd, DGT y open data Ayuntamiento Madrid.",
    icon="🛰️",
)

refresh_seconds = st.sidebar.slider(
    "Autorefresco (segundos)", min_value=5, max_value=60, value=15, step=5
)
st_autorefresh(interval=refresh_seconds * 1000, key="live_map_refresh")

hours_window = st.sidebar.slider(
    "Ventana de incidencias (horas)", min_value=1, max_value=72, value=24
)
show_crowd = st.sidebar.toggle("Mostrar reportes crowd", value=True)
show_dgt = st.sidebar.toggle("Mostrar DGT tiempo real", value=True)
show_madrid = st.sidebar.toggle("Mostrar obras Ayto. Madrid", value=True)
show_puntos = st.sidebar.toggle("Mostrar puntos negros DGT", value=False)
show_aqi = st.sidebar.toggle("Mostrar calidad del aire", value=True)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_dgt():
    return dgt.fetch_incidents(), datetime.utcnow()


@st.cache_data(ttl=300, show_spinner=False)
def _cached_puntos_negros():
    return dgt.load_puntos_negros(), datetime.utcnow()


@st.cache_data(ttl=300, show_spinner=False)
def _cached_road_works():
    return madrid_opendata.fetch_road_works(), datetime.utcnow()


@st.cache_data(ttl=300, show_spinner=False)
def _cached_air_quality():
    return madrid_opendata.fetch_air_quality(), datetime.utcnow()


crowd.expire_old()
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
    active_lines = (
        s.exec(select(Line).where(Line.id.in_(active_line_ids))).all()
        if active_line_ids
        else []
    )
    driver_map = {u.id: u.full_name for u in s.exec(select(User)).all()}
    bus_map = {b.id: b.plate for b in s.exec(select(Bus)).all()}
    line_map = {ln.id: ln.code for ln in s.exec(select(Line)).all()}

panic_incidents = [i for i in incidents if i.kind == "panic" or i.severity == "critical"]

dgt_incidents, dgt_ts = _cached_dgt() if show_dgt else ([], None)
puntos_negros, pn_ts = _cached_puntos_negros() if show_puntos else ([], None)
road_works, rw_ts = _cached_road_works() if show_madrid else ([], None)
aqi_stations, aqi_ts = _cached_air_quality() if show_aqi else ([], None)

dgt_is_mock = any("mock" in i.get("source", "") for i in dgt_incidents[:1])
rw_is_mock = any("mock" in i.get("source", "") for i in road_works[:1])
aqi_is_mock = any("mock" in i.get("source", "") for i in aqi_stations[:1])

aqi_critical = sum(1 for st_ in aqi_stations if st_.get("aqi", 0) >= 80)

if panic_incidents:
    st.error(
        f"🚨 **{len(panic_incidents)} alerta(s) de pánico activas.** "
        "Prioriza respuesta. Contacta por radio y envía unidad."
    )

kpis = st.columns(7)
with kpis[0]:
    kpi_card("Incidencias", len(incidents), color="primary")
with kpis[1]:
    kpi_card("Pánicos", len(panic_incidents), color="danger" if panic_incidents else "primary")
with kpis[2]:
    kpi_card("Conductores", len({a.driver_id for a in drivers_in_shift}), color="accent")
with kpis[3]:
    kpi_card("Buses hoy", len({a.bus_id for a in drivers_in_shift}), color="accent")
with kpis[4]:
    kpi_card("Crowd activos", len(crowd.active_reports()) if show_crowd else "—", color="ok")
with kpis[5]:
    kpi_card("DGT Madrid", len(dgt_incidents) if show_dgt else "—", color="warn")
with kpis[6]:
    kpi_card("AQI > 80", aqi_critical if show_aqi else "—", color="danger" if aqi_critical else "primary")

badges_cols = st.columns(4)
with badges_cols[0]:
    if show_dgt:
        data_source_badge("DGT DATEX2", dgt_ts, is_mock=dgt_is_mock)
with badges_cols[1]:
    if show_madrid:
        data_source_badge("Ayto. Madrid", rw_ts, is_mock=rw_is_mock)
with badges_cols[2]:
    if show_aqi:
        data_source_badge("Calidad aire Madrid", aqi_ts, is_mock=aqi_is_mock)
with badges_cols[3]:
    data_source_badge("Interno (DB)", datetime.utcnow())

crowd_payload: list[dict] = []
if show_crowd:
    for r in crowd.active_reports():
        crowd_payload.append(
            {
                "id": r.id,
                "category": r.category,
                "label": crowd.label_for(r.category),
                "lat": r.lat,
                "lon": r.lon,
                "severity": r.severity,
                "note": r.note or "",
                "confirmations": r.confirmations,
                "downvotes": r.downvotes,
                "reporter": driver_map.get(r.reporter_id, "-"),
                "line": line_map.get(r.line_id, "-") if r.line_id else "-",
                "map_color": crowd.color_for(r.category),
            }
        )

incident_payload = [
    {
        "id": inc.id,
        "lat": inc.lat,
        "lon": inc.lon,
        "description": inc.description,
        "severity": inc.severity,
        "kind": inc.kind,
        "created_at": inc.created_at.strftime("%d/%m %H:%M") + " UTC",
        "driver_name": driver_map.get(inc.driver_id, "-"),
        "bus_plate": bus_map.get(inc.bus_id, "-") if inc.bus_id else "-",
        "line_code": line_map.get(inc.line_id, "-") if inc.line_id else "-",
    }
    for inc in incidents
]

lines_geometry = {ln.code: get_route(ln.code).geometry for ln in active_lines}

fmap = build_admin_live_map(
    incident_payload,
    lines_geometry,
    crowd_reports=crowd_payload,
    dgt_incidents=dgt_incidents,
    road_works=road_works,
    puntos_negros=puntos_negros,
    aqi_stations=aqi_stations,
)
st_folium(fmap, height=620, use_container_width=True, returned_objects=[])

st.divider()

if panic_incidents:
    st.subheader("🚨 Pánicos activos")
    for inc in panic_incidents:
        with st.container(border=True):
            cols = st.columns([1, 4, 1])
            cols[0].markdown(f"**#{inc.id}**")
            cols[1].markdown(
                f"**{driver_map.get(inc.driver_id, '-')}** · "
                f"Bus {bus_map.get(inc.bus_id, '-') if inc.bus_id else '-'} · "
                f"Línea {line_map.get(inc.line_id, '-') if inc.line_id else '-'}  \n"
                f"{inc.description}  \n"
                f"<small>{inc.created_at.strftime('%d/%m/%Y %H:%M')} UTC · "
                f"({inc.lat:.4f}, {inc.lon:.4f})</small>",
                unsafe_allow_html=True,
            )
            if cols[2].button("Marcar atendida", key=f"panic_ack_{inc.id}"):
                with get_session() as s:
                    row = s.get(Incident, inc.id)
                    if row:
                        row.status = "resolved"
                        s.add(row)
                        s.commit()
                st.rerun()

non_panic = [i for i in incidents if i not in panic_incidents]
st.subheader(f"Incidencias abiertas ({len(non_panic)})")
if not non_panic:
    st.info("No hay incidencias abiertas en esta ventana.")
else:
    for inc in non_panic:
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

if show_crowd and crowd_payload:
    st.divider()
    st.subheader(f"Reportes crowd activos ({len(crowd_payload)})")
    for cr in crowd_payload:
        with st.container(border=True):
            cols = st.columns([1, 4, 1])
            cols[0].markdown(f"**#{cr['id']}**")
            cols[1].markdown(
                f"**{cr['label']}** · `{cr['severity']}`  \n"
                f"{cr['note']}  \n"
                f"<small>por {cr['reporter']} · línea {cr['line']} · "
                f"+{cr['confirmations']} / −{cr['downvotes']}</small>",
                unsafe_allow_html=True,
            )
            if cols[2].button("Descartar", key=f"crowd_dismiss_{cr['id']}"):
                with get_session() as s:
                    from db.models import CrowdReport

                    row = s.get(CrowdReport, cr["id"])
                    if row:
                        row.status = "dismissed"
                        s.add(row)
                        s.commit()
                st.rerun()
