from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st
from sqlmodel import select
from streamlit_folium import st_folium

from db.models import Assignment, Bus, CrowdReport, Incident, Line, ShiftNote
from db.session import get_session
from services import crowd
from services.plan_builder import build_plan
from services.tts import synthesize
from ui.auth import require_role
from ui.components import aqi_banner, data_source_badge, kpi_card, page_header, severity_badge
from ui.maps import build_driver_map
from ui.pdf import render_plan_pdf
from ui.theme import inject_css
from ui.timeline import render_timeline_figure

st.set_page_config(page_title="Turno del conductor", page_icon="🗺️", layout="wide")
inject_css()

user = require_role("driver")

page_header(
    "Configuración de turno",
    "Plan personalizado con datos reales de tráfico DGT y ciudad.",
    icon="🗺️",
)

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

# ─── Handoff del bus (nota del conductor anterior) ────────────────────────
with get_session() as s:
    pending_note = s.exec(
        select(ShiftNote)
        .where(ShiftNote.bus_id == bus.id)
        .where(ShiftNote.acknowledged_at.is_(None))
        .order_by(ShiftNote.created_at.desc())
    ).first()

if pending_note:
    with st.container(border=True):
        st.markdown(f"### 🪝 Nota del turno anterior — {bus.plate}")
        author_name = "—"
        with get_session() as s:
            from db.models import User as _U

            author = s.get(_U, pending_note.author_id)
            if author:
                author_name = author.full_name
        st.caption(
            f"De **{author_name}** · {pending_note.created_at.strftime('%d/%m/%Y %H:%M')} UTC"
        )
        st.info(pending_note.body)
        if st.button("✔ Confirmar lectura", type="primary"):
            with get_session() as s:
                row = s.get(ShiftNote, pending_note.id)
                if row:
                    row.acknowledged_by = user.id
                    row.acknowledged_at = datetime.utcnow()
                    s.add(row)
                    s.commit()
            st.rerun()

# ─── Dejar nota para el siguiente conductor ───────────────────────────────
with st.expander("✍️ Dejar nota para el próximo conductor de este bus"):
    handoff_body = st.text_area(
        "Nota (breve, acciónable)",
        placeholder="Ej: luz puerta trasera intermitente, taller avisado.",
        key="handoff_body",
        height=80,
    )
    if st.button("Guardar nota", disabled=not handoff_body.strip()):
        with get_session() as s:
            s.add(
                ShiftNote(
                    bus_id=bus.id,
                    author_id=user.id,
                    body=handoff_body.strip(),
                )
            )
            s.commit()
        st.success("Nota guardada. La verá el siguiente conductor de este bus.")
        st.session_state["handoff_body"] = ""
        st.rerun()

# ─── Diff: incidencias / reportes crowd recientes en esta línea ───────────
with st.expander(f"📜 Historial reciente en línea {line.code} (últimos 7 días)"):
    since = datetime.utcnow() - timedelta(days=7)
    with get_session() as s:
        recent_incidents = s.exec(
            select(Incident)
            .where(Incident.line_id == line.id)
            .where(Incident.created_at >= since)
            .order_by(Incident.created_at.desc())
            .limit(5)
        ).all()
        recent_crowd = s.exec(
            select(CrowdReport)
            .where(CrowdReport.line_id == line.id)
            .where(CrowdReport.created_at >= since)
            .order_by(CrowdReport.created_at.desc())
            .limit(5)
        ).all()
    if not recent_incidents and not recent_crowd:
        st.caption("Sin actividad reciente en esta línea.")
    else:
        st.markdown(f"**Incidencias formales** ({len(recent_incidents)}):")
        for inc in recent_incidents:
            tag = "🚨" if inc.kind == "panic" else "•"
            st.markdown(
                f"{tag} {inc.created_at.strftime('%d/%m %H:%M')} — "
                f"{inc.description[:100]}"
            )
        st.markdown(f"**Reportes de compañeros** ({len(recent_crowd)}):")
        for r in recent_crowd:
            st.markdown(
                f"• {r.created_at.strftime('%d/%m %H:%M')} — "
                f"{crowd.label_for(r.category)} (severidad `{r.severity}`) — "
                f"{r.note or '(sin nota)'}"
            )

st.divider()

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

# ─── Banner calidad del aire (estación más cercana a la ruta) ─────────────
if plan.aqi:
    aqi_banner(plan.aqi)

# ─── Badges de fuentes ────────────────────────────────────────────────────
src_cols = st.columns(4)
with src_cols[0]:
    data_source_badge(
        "DGT DATEX2",
        plan.generated_at,
        is_mock=any("mock" in i.get("source", "") for i in plan.dgt_incidents[:1]),
    )
with src_cols[1]:
    data_source_badge(
        "Ayto. Madrid",
        plan.generated_at,
        is_mock=any("mock" in i.get("source", "") for i in plan.road_works[:1]),
    )
with src_cols[2]:
    data_source_badge(
        "Calidad aire",
        plan.generated_at,
        is_mock=bool(plan.aqi) and "mock" in (plan.aqi.get("source", "")),
    )
with src_cols[3]:
    data_source_badge("Interno", plan.generated_at)

tab_timeline, tab_map, tab_alerts, tab_trafico, tab_meta = st.tabs(
    ["🕒 Timeline", "🗺️ Mapa", "⚠️ Alertas", "🚧 Tráfico ciudad", "📊 Detalles"]
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

with tab_trafico:
    if not plan.dgt_incidents and not plan.road_works and not plan.black_spots:
        st.success("No se detectan incidencias de tráfico cerca de esta ruta en este momento.")
    if plan.dgt_incidents:
        st.markdown(f"**🛣️ DGT tiempo real · {len(plan.dgt_incidents)} cerca de la ruta**")
        for inc in plan.dgt_incidents[:10]:
            st.markdown(
                f"- {severity_badge(inc['severity'])} "
                f"**{inc['tipo'].title()}** · {inc.get('carretera', '')} "
                f"km {inc.get('pk', '')} · a **{int(inc['distance_m'])}m** — "
                f"{inc.get('descripcion', '')[:140]}",
                unsafe_allow_html=True,
            )
    if plan.road_works:
        st.markdown(f"**🏗️ Obras Ayto. Madrid · {len(plan.road_works)} cerca**")
        for rw in plan.road_works[:10]:
            st.markdown(
                f"- {severity_badge(rw['severity'])} "
                f"**{rw['titulo']}** · distrito {rw.get('distrito', '-')} · "
                f"a **{int(rw['distance_m'])}m**",
                unsafe_allow_html=True,
            )
    dgt_pn = [s for s in plan.black_spots if s.get("source") == "dgt"]
    if dgt_pn:
        st.markdown(f"**⚫ Puntos negros DGT cerca · {len(dgt_pn)}**")
        for sp in dgt_pn[:10]:
            st.markdown(
                f"- {severity_badge(sp.get('severity', 'media'))} "
                f"{sp.get('reason', '')}",
                unsafe_allow_html=True,
            )

with tab_meta:
    ws = plan.weather_summary
    cols = st.columns(4)
    with cols[0]:
        kpi_card("Tª mínima", f"{ws.get('min_temp', '?')}ºC", color="accent")
    with cols[1]:
        kpi_card("Tª máxima", f"{ws.get('max_temp', '?')}ºC", color="accent")
    with cols[2]:
        kpi_card("Lluvia acumulada", f"{ws.get('total_rain_mm', 0)} mm", color="primary")
    with cols[3]:
        kpi_card("Paradas", len(plan.stops), color="ok")
    st.caption(f"Condiciones previstas: {ws.get('conditions', '-')}")
    if plan.events:
        st.markdown("**Eventos en la ciudad hoy:**")
        for ev in plan.events:
            st.markdown(f"- {ev['name']} @ {ev['venue']} ({ev['start']}-{ev['end']})")

st.divider()


def _build_briefing_text(plan, recent_incidents_count: int, recent_crowd_count: int) -> str:
    ws = plan.weather_summary
    alerts_hi = [a for a in plan.alerts if a["severity"] == "error"]
    alerts_mid = [a for a in plan.alerts if a["severity"] == "warning"]

    parts: list[str] = []
    parts.append(
        f"Briefing. Línea {plan.line.code}, {plan.bus.model}, tipo {plan.bus.type}. "
        f"Fecha {plan.shift_date.strftime('%d de %m')}."
    )
    parts.append(
        f"Clima: {ws.get('min_temp', '?')} a {ws.get('max_temp', '?')} grados. "
        f"Lluvia prevista {ws.get('total_rain_mm', 0)} milímetros."
    )
    if alerts_hi:
        parts.append("Alertas críticas: " + "; ".join(a["message"] for a in alerts_hi[:2]) + ".")
    if alerts_mid:
        parts.append("Advertencias: " + "; ".join(a["message"] for a in alerts_mid[:3]) + ".")
    if plan.events:
        ev_names = ", ".join(e["name"] for e in plan.events[:3])
        parts.append(f"Eventos ciudad: {ev_names}.")
    if recent_incidents_count or recent_crowd_count:
        parts.append(
            f"Histórico 7 días en esta línea: {recent_incidents_count} incidencias formales, "
            f"{recent_crowd_count} reportes de compañeros."
        )
    parts.append("Fin de briefing. Turno seguro.")
    return " ".join(parts)


col_pdf, col_brief = st.columns(2)
with col_pdf:
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
with col_brief:
    if st.button(
        "🎧 Briefing hablado (60 s)",
        use_container_width=True,
        help="Genera un resumen por voz con clima, alertas y actividad reciente.",
    ):
        with get_session() as s:
            inc_count = len(
                s.exec(
                    select(Incident)
                    .where(Incident.line_id == line.id)
                    .where(Incident.created_at >= datetime.utcnow() - timedelta(days=7))
                ).all()
            )
            crowd_count = len(
                s.exec(
                    select(CrowdReport)
                    .where(CrowdReport.line_id == line.id)
                    .where(CrowdReport.created_at >= datetime.utcnow() - timedelta(days=7))
                ).all()
            )
        text = _build_briefing_text(plan, inc_count, crowd_count)
        st.session_state["briefing_text"] = text
        st.session_state["briefing_audio"] = synthesize(text)

if st.session_state.get("briefing_text"):
    with st.expander("📝 Texto del briefing", expanded=False):
        st.markdown(st.session_state["briefing_text"])
    audio = st.session_state.get("briefing_audio")
    if audio:
        st.audio(audio, format="audio/mp3")
    else:
        st.caption("⚠️ Audio no disponible (sin red). Lee el texto del briefing arriba.")
