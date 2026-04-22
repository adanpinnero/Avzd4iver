from __future__ import annotations

import uuid
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from sqlmodel import select

from db.models import Assignment, Bus, Incident, Line
from db.session import get_session
from services.llm import emergency_protocol
from services.tts import synthesize
from ui.auth import require_role

st.set_page_config(page_title="Reportar incidencia", page_icon="🚨", layout="centered")

user = require_role("driver")

st.title("🚨 Reportar incidencia")
st.caption("Envía una incidencia y recibe un protocolo de actuación inmediato con audio.")

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads" / "incidents"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

with get_session() as s:
    today = date.today()
    assignment = s.exec(
        select(Assignment).where(
            Assignment.driver_id == user.id,
            Assignment.shift_date == today,
        )
    ).first()
    bus = s.get(Bus, assignment.bus_id) if assignment else None
    line = s.get(Line, assignment.line_id) if assignment else None

st.info(
    "Asignación actual: "
    f"**{bus.plate if bus else 'Sin bus asignado hoy'}** en **línea {line.code if line else '—'}**. "
    "Puedes reportar incidencias aunque no tengas turno activo."
)

with st.expander("📝 Nueva incidencia", expanded=True):
    with st.form("new_incident", clear_on_submit=False):
        description = st.text_area(
            "Descripción de la incidencia",
            placeholder="Ej: avería en puerta trasera, no cierra correctamente...",
            height=120,
        )

        st.markdown("**Ubicación**")
        try:
            from streamlit_geolocation import streamlit_geolocation
            geo = streamlit_geolocation()
        except Exception:
            geo = None

        auto_lat = auto_lon = None
        if isinstance(geo, dict):
            auto_lat = geo.get("latitude")
            auto_lon = geo.get("longitude")

        col_lat, col_lon = st.columns(2)
        lat = col_lat.number_input(
            "Latitud",
            value=float(auto_lat) if auto_lat else 40.4168,
            format="%.6f",
        )
        lon = col_lon.number_input(
            "Longitud",
            value=float(auto_lon) if auto_lon else -3.7038,
            format="%.6f",
        )

        photo = st.camera_input("Adjuntar foto (opcional)")
        submitted = st.form_submit_button(
            "🚨 Enviar incidencia", type="primary", use_container_width=True
        )

if submitted:
    if not description.strip():
        st.error("La descripción es obligatoria.")
        st.stop()

    photo_path: str | None = None
    if photo is not None:
        fname = f"{uuid.uuid4().hex}.jpg"
        fpath = UPLOAD_DIR / fname
        fpath.write_bytes(photo.getvalue())
        photo_path = str(fpath.relative_to(UPLOAD_DIR.parent.parent))

    with st.spinner("Generando protocolo de actuación con IA..."):
        protocol = emergency_protocol(
            description=description,
            bus_type=bus.type if bus else "standard",
            line_code=line.code if line else "-",
            location_hint=f"({lat:.4f}, {lon:.4f})",
        )

    with get_session() as s:
        incident = Incident(
            driver_id=user.id,
            bus_id=bus.id if bus else None,
            line_id=line.id if line else None,
            description=description.strip(),
            lat=lat,
            lon=lon,
            photo_path=photo_path,
            ai_protocol=protocol,
            created_at=datetime.utcnow(),
            status="open",
        )
        s.add(incident)
        s.commit()
        s.refresh(incident)
        incident_id = incident.id

    st.success(f"Incidencia #{incident_id} registrada correctamente.")

    st.markdown("### 📣 Protocolo de actuación")
    st.markdown(protocol)

    with st.spinner("Generando audio..."):
        audio_bytes = synthesize(protocol)
    if audio_bytes:
        st.audio(audio_bytes, format="audio/mp3")
    else:
        st.caption("⚠️ Audio no disponible (sin conexión a TTS). Lee el protocolo arriba.")

st.divider()
st.subheader("Últimas incidencias reportadas por ti")
with get_session() as s:
    mine = s.exec(
        select(Incident)
        .where(Incident.driver_id == user.id)
        .order_by(Incident.created_at.desc())
        .limit(10)
    ).all()

if not mine:
    st.caption("Aún no has reportado ninguna incidencia.")
else:
    for inc in mine:
        with st.container(border=True):
            cols = st.columns([1, 4, 1])
            cols[0].markdown(f"**#{inc.id}**")
            cols[1].markdown(
                f"{inc.description[:120]}{'…' if len(inc.description) > 120 else ''}  \n"
                f"<small>{inc.created_at.strftime('%d/%m/%Y %H:%M')} UTC · "
                f"estado: `{inc.status}`</small>",
                unsafe_allow_html=True,
            )
            cols[2].markdown(
                f"<small>({inc.lat:.4f}, {inc.lon:.4f})</small>" if inc.lat else "—",
                unsafe_allow_html=True,
            )
