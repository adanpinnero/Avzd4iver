from __future__ import annotations

from collections import Counter
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from services import dgt, madrid_opendata
from ui.auth import require_role
from ui.components import data_source_badge, kpi_card, page_header, severity_badge
from ui.theme import inject_css

st.set_page_config(page_title="Info ciudad", page_icon="🏙️", layout="wide")
inject_css()

require_role("admin")

page_header(
    "Info ciudad · DGT + Ayuntamiento Madrid",
    "Dashboard de incidencias DGT, obras y calidad del aire con datos abiertos.",
    icon="🏙️",
)

st_autorefresh(interval=300_000, key="info_ciudad_refresh")


@st.cache_data(ttl=300, show_spinner=False)
def _get_dgt():
    return dgt.fetch_incidents(), datetime.utcnow()


@st.cache_data(ttl=300, show_spinner=False)
def _get_puntos():
    return dgt.load_puntos_negros(), datetime.utcnow()


@st.cache_data(ttl=300, show_spinner=False)
def _get_road_works():
    return madrid_opendata.fetch_road_works(), datetime.utcnow()


@st.cache_data(ttl=300, show_spinner=False)
def _get_aqi():
    return madrid_opendata.fetch_air_quality(), datetime.utcnow()


dgt_items, dgt_ts = _get_dgt()
puntos, pn_ts = _get_puntos()
road_works, rw_ts = _get_road_works()
aqi_stations, aqi_ts = _get_aqi()

dgt_is_mock = bool(dgt_items) and "mock" in dgt_items[0].get("source", "")
rw_is_mock = bool(road_works) and "mock" in road_works[0].get("source", "")
aqi_is_mock = bool(aqi_stations) and "mock" in aqi_stations[0].get("source", "")

# ─── KPIs ─────────────────────────────────────────────────────────────────
aqi_vals = [s.get("aqi", 0) for s in aqi_stations if s.get("aqi")]
aqi_mean = round(sum(aqi_vals) / len(aqi_vals), 1) if aqi_vals else 0
aqi_over = sum(1 for s in aqi_stations if (s.get("no2") or 0) > 40)

alta_dgt = sum(1 for i in dgt_items if i.get("severity") == "alta")
alta_rw = sum(1 for r in road_works if r.get("severity") == "alta")

kpis = st.columns(6)
with kpis[0]:
    kpi_card("Incidencias DGT", len(dgt_items), delta=f"{alta_dgt} alta", color="warn")
with kpis[1]:
    kpi_card("Obras Madrid", len(road_works), delta=f"{alta_rw} alta", color="warn")
with kpis[2]:
    kpi_card("AQI medio", aqi_mean, color="ok" if aqi_mean <= 40 else ("warn" if aqi_mean <= 60 else "danger"))
with kpis[3]:
    kpi_card("Estaciones NO₂>40", aqi_over, color="warn" if aqi_over else "ok")
with kpis[4]:
    kpi_card("Puntos negros", len(puntos), color="accent")
with kpis[5]:
    kpi_card("Actualización", datetime.utcnow().strftime("%H:%M"), color="primary")

# ─── Badges de fuentes ────────────────────────────────────────────────────
src_cols = st.columns(4)
with src_cols[0]:
    data_source_badge("DGT DATEX2", dgt_ts, is_mock=dgt_is_mock)
with src_cols[1]:
    data_source_badge("Ayto. Madrid obras", rw_ts, is_mock=rw_is_mock)
with src_cols[2]:
    data_source_badge("Calidad aire Madrid", aqi_ts, is_mock=aqi_is_mock)
with src_cols[3]:
    data_source_badge("Puntos negros DGT", pn_ts, is_mock=False)

st.divider()

# ─── Gráficos Plotly ──────────────────────────────────────────────────────
g1, g2 = st.columns(2)

with g1:
    st.subheader("🛣️ Incidencias DGT por tipo")
    if dgt_items:
        counter = Counter(i.get("tipo", "otros") for i in dgt_items)
        df = pd.DataFrame({"tipo": list(counter.keys()), "n": list(counter.values())})
        df["tipo"] = df["tipo"].str.title()
        fig = px.pie(df, names="tipo", values="n", hole=0.55,
                     color_discrete_sequence=px.colors.sequential.Reds_r)
        fig.update_traces(textinfo="label+percent")
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos DGT.")

with g2:
    st.subheader("🏗️ Obras Madrid por distrito")
    if road_works:
        counter = Counter(r.get("distrito", "-") for r in road_works)
        df = pd.DataFrame(
            sorted(counter.items(), key=lambda x: -x[1])[:10],
            columns=["distrito", "n"],
        )
        fig = px.bar(df, x="n", y="distrito", orientation="h",
                     color="n", color_continuous_scale="Oranges",
                     labels={"n": "Obras activas", "distrito": ""})
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos de obras.")

g3, g4 = st.columns(2)

with g3:
    st.subheader("🌫️ Calidad del aire por estación")
    if aqi_stations:
        df = pd.DataFrame(aqi_stations)
        df = df.sort_values("aqi", ascending=False).head(12)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="NO₂",
            x=df["estacion"],
            y=df["no2"],
            marker_color="#C81D25",
        ))
        fig.add_trace(go.Bar(
            name="PM₂.₅",
            x=df["estacion"],
            y=df["pm25"],
            marker_color="#1F6FEB",
        ))
        fig.add_trace(go.Scatter(
            name="AQI",
            x=df["estacion"],
            y=df["aqi"],
            mode="lines+markers",
            yaxis="y2",
            line=dict(color="#8F1319", width=2),
        ))
        fig.update_layout(
            barmode="group",
            margin=dict(l=0, r=0, t=10, b=80),
            height=360,
            xaxis_tickangle=-35,
            yaxis=dict(title="μg/m³"),
            yaxis2=dict(title="AQI", overlaying="y", side="right", range=[0, 100]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin estaciones AQI.")

with g4:
    st.subheader("📍 Puntos negros + DGT en mapa")
    scatter_points: list[dict] = []
    for p in puntos:
        scatter_points.append({
            "lat": p["lat"], "lon": p["lon"],
            "tipo": "Punto negro",
            "severidad": p.get("concentracion", "media"),
            "info": f"{p.get('carretera', '')} km {p.get('pk', '')} · {p.get('accidentes_5y', 0)} acc./5y",
        })
    for i in dgt_items:
        scatter_points.append({
            "lat": i["lat"], "lon": i["lon"],
            "tipo": f"DGT {i.get('tipo', '')}",
            "severidad": i.get("severity", "media"),
            "info": (i.get("descripcion") or "")[:120],
        })
    if scatter_points:
        df = pd.DataFrame(scatter_points)
        fig = px.scatter_mapbox(
            df,
            lat="lat", lon="lon",
            color="tipo",
            size_max=12,
            hover_name="tipo",
            hover_data={"severidad": True, "info": True, "lat": False, "lon": False},
            zoom=10,
            center={"lat": 40.4168, "lon": -3.7038},
            height=360,
        )
        fig.update_layout(
            mapbox_style="open-street-map",
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos para el mapa.")

st.divider()

# ─── Tabla últimas incidencias DGT ────────────────────────────────────────
st.subheader(f"Últimas incidencias DGT Madrid ({len(dgt_items)})")
if dgt_items:
    rows = []
    for i in dgt_items[:30]:
        rows.append(
            {
                "Tipo": i.get("tipo", "-").title(),
                "Severidad": i.get("severity", "-"),
                "Carretera": i.get("carretera", "-"),
                "PK": i.get("pk", "-"),
                "Descripción": (i.get("descripcion") or "")[:160],
                "Inicio": i.get("start").strftime("%d/%m %H:%M") if i.get("start") else "-",
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=360, hide_index=True)
else:
    st.info("No hay incidencias DGT.")

# ─── Tabla obras Madrid ───────────────────────────────────────────────────
st.subheader(f"Obras e incidencias Ayto. Madrid ({len(road_works)})")
if road_works:
    rows = []
    for r in road_works[:30]:
        rows.append(
            {
                "Título": r.get("titulo", "-"),
                "Distrito": r.get("distrito", "-"),
                "Severidad": r.get("severity", "-"),
                "Inicio": r.get("fecha_inicio").strftime("%d/%m") if r.get("fecha_inicio") else "-",
                "Fin": r.get("fecha_fin").strftime("%d/%m") if r.get("fecha_fin") else "-",
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=320, hide_index=True)
else:
    st.info("No hay obras activas.")
