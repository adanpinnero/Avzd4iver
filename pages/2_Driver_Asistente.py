from __future__ import annotations

from datetime import date, datetime, timedelta

import folium
import streamlit as st
from sqlmodel import select
from streamlit_autorefresh import st_autorefresh
from streamlit_folium import st_folium

from db.models import Assignment, Bus, Incident, Line
from db.session import get_session
from services import crowd
from services.protocols import get_protocol, list_protocols
from services.tts import synthesize
from services.voice import parse_intent, short_ack, transcribe
from ui.auth import require_role
from ui.components import page_header
from ui.theme import inject_css

st.set_page_config(page_title="Asistente", page_icon="🎧", layout="wide")
inject_css()

user = require_role("driver")

page_header(
    "Asistente del conductor",
    "Radar de compañeros, voz, protocolos guiados y pánico.",
    icon="🎧",
)

# ─── Contexto del turno ─────────────────────────────────────────────────────
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

# Centro del radar: si hay línea asignada, primer punto de su ruta; si no, Madrid centro.
from services.transit import get_route

if line:
    route = get_route(line.code)
    default_center = route.geometry[len(route.geometry) // 2] if route.geometry else (40.4168, -3.7038)
else:
    default_center = (40.4168, -3.7038)

state = st.session_state
state.setdefault("assist_center", default_center)
state.setdefault("assist_radius_m", 2000)
state.setdefault("last_interaction_ts", datetime.utcnow())
state.setdefault("deadman_enabled", False)
state.setdefault("silence_mode", False)
state.setdefault("protocol_key", None)
state.setdefault("protocol_step", 0)
state.setdefault("last_tts_ack", b"")
state.setdefault("last_command_feedback", "")

# ─── Expirar reportes vencidos (barato, 1 query) ────────────────────────────
crowd.expire_old()

# ─── Cabecera con estado ────────────────────────────────────────────────────
head_l, head_c, head_r = st.columns([2, 2, 1])
head_l.markdown(
    f"**Turno**: {line.code if line else '—'} · {bus.plate if bus else '—'} · "
    f"{bus.type if bus else '—'}"
)
head_c.markdown(
    f"**Centro radar**: `{state['assist_center'][0]:.4f}, {state['assist_center'][1]:.4f}` "
    f"(radio {state['assist_radius_m']} m)"
)
head_r.toggle("🤫 Silencio", key="silence_mode", help="El asistente no sintetiza audio.")

def _trigger_panic(user, bus, line, center, origin: str = "button") -> int:
    """Crea un Incident crítico y devuelve su id."""
    with get_session() as s:
        inc = Incident(
            driver_id=user.id,
            bus_id=bus.id if bus else None,
            line_id=line.id if line else None,
            description=f"[PÁNICO · origen={origin}] Conductor solicita asistencia inmediata.",
            lat=center[0],
            lon=center[1],
            created_at=datetime.utcnow(),
            status="open",
            severity="critical",
            kind="panic",
            ai_protocol="Central: priorizar. Enviar unidad a coordenadas. Contactar al conductor por radio.",
        )
        s.add(inc)
        s.commit()
        s.refresh(inc)
        return inc.id


tab_radar, tab_voz, tab_protocol, tab_panic = st.tabs(
    ["📡 Radar", "🎙️ Voz", "📘 Protocolos", "🚨 Pánico"]
)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — RADAR crowdsourced
# ═══════════════════════════════════════════════════════════════════════════
with tab_radar:
    refresh_s = st.sidebar.slider("Autorefresco radar (s)", 5, 60, 15, 5, key="radar_refresh")
    st_autorefresh(interval=refresh_s * 1000, key="radar_autoref")

    c1, c2, c3 = st.columns([1, 1, 2])
    c1.number_input(
        "Radio (m)",
        min_value=500,
        max_value=10_000,
        step=500,
        key="assist_radius_m",
    )
    lat_col, lon_col = c2.columns(2)
    lat_col.number_input(
        "Lat",
        value=float(state["assist_center"][0]),
        format="%.4f",
        key="radar_lat",
    )
    lon_col.number_input(
        "Lon",
        value=float(state["assist_center"][1]),
        format="%.4f",
        key="radar_lon",
    )
    if c3.button("📍 Centrar en línea", use_container_width=True) and line:
        state["assist_center"] = default_center
        st.rerun()

    # Sincronizar el centro con los inputs editables por el conductor.
    state["assist_center"] = (state["radar_lat"], state["radar_lon"])

    reports = crowd.nearby(state["assist_center"], state["assist_radius_m"])

    fmap = folium.Map(location=state["assist_center"], zoom_start=14, tiles="OpenStreetMap")
    folium.Circle(
        location=state["assist_center"],
        radius=state["assist_radius_m"],
        color="#1F77B4",
        fill=True,
        fill_opacity=0.05,
        tooltip="Radar",
    ).add_to(fmap)
    folium.Marker(
        location=state["assist_center"],
        tooltip="Tú",
        icon=folium.Icon(color="blue", icon="user"),
    ).add_to(fmap)
    for r in reports:
        ttl_left = max(0, (r["expires_at"] - datetime.utcnow()).seconds // 60)
        popup = (
            f"<b>{r['label']}</b><br>"
            f"Severidad: {r['severity']}<br>"
            f"Distancia: {r['distance_m']} m<br>"
            f"TTL restante: ~{ttl_left} min<br>"
            f"Confirmaciones: {r['confirmations']} · Descartes: {r['downvotes']}<br>"
            f"<i>{r['note']}</i>"
        )
        folium.Marker(
            location=(r["lat"], r["lon"]),
            tooltip=f"{r['label']} · {r['severity']} · {r['distance_m']} m",
            popup=folium.Popup(popup, max_width=320),
            icon=folium.Icon(color=crowd.color_for(r["category"]), icon="info-sign"),
        ).add_to(fmap)

    st_folium(fmap, height=480, use_container_width=True, returned_objects=[])

    st.markdown(f"**{len(reports)} reportes activos** en radio {state['assist_radius_m']} m")

    for r in reports[:12]:
        with st.container(border=True):
            cols = st.columns([3, 1, 1])
            ttl_left = max(0, (r["expires_at"] - datetime.utcnow()).seconds // 60)
            cols[0].markdown(
                f"**{r['label']}** · severidad `{r['severity']}` · {r['distance_m']} m · "
                f"TTL ~{ttl_left} min  \n"
                f"<small>por {r['reporter']} — {r['note'] or '(sin nota)'} · "
                f"+{r['confirmations']} confirmaciones / −{r['downvotes']} descartes</small>",
                unsafe_allow_html=True,
            )
            if cols[1].button("✔ Confirmo", key=f"conf_{r['id']}", use_container_width=True):
                crowd.confirm(r["id"], True)
                st.rerun()
            if cols[2].button("✖ Descarto", key=f"dismiss_{r['id']}", use_container_width=True):
                crowd.confirm(r["id"], False)
                st.rerun()

    st.divider()
    st.subheader("Reporte rápido")
    fast_cols = st.columns(7)
    quick_categories = [
        ("bump", "🕳 Bache"),
        ("obstacle", "📦 Obstáculo"),
        ("jam", "🚦 Atasco"),
        ("protest", "🪧 Manifa"),
        ("aggression", "⚠ Agresión"),
        ("accident", "💥 Accidente"),
        ("construction", "🚧 Obra"),
    ]
    for idx, (cat, label) in enumerate(quick_categories):
        if fast_cols[idx].button(label, key=f"quick_{cat}", use_container_width=True):
            crowd.submit_report(
                reporter_id=user.id,
                category=cat,
                lat=state["assist_center"][0],
                lon=state["assist_center"][1],
                line_id=line.id if line else None,
                note=f"Reporte rápido desde radar ({user.full_name})",
            )
            state["last_interaction_ts"] = datetime.utcnow()
            st.toast(f"Reportado: {crowd.label_for(cat)}", icon="✅")
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — VOZ
# ═══════════════════════════════════════════════════════════════════════════
with tab_voz:
    st.markdown(
        "Habla o escribe un comando. Ejemplos: "
        "`reporta bache`, `avisa atasco`, `alerta roja`, `lee alertas`, "
        "`modo silencio`, `protocolo agresión`."
    )

    audio = None
    try:
        audio = st.audio_input("🎙️ Graba un comando (opcional)")
    except Exception:
        audio = None

    typed = st.text_input(
        "Comando escrito (fallback si no hay transcripción)",
        key="voice_typed",
        placeholder="Ej: reporta bache en Gran Vía",
    )

    run = st.button("Ejecutar comando", type="primary", use_container_width=True)

    if run:
        transcript: str | None = None
        if audio is not None:
            audio_bytes = audio.getvalue()
            if audio_bytes:
                transcript = transcribe(audio_bytes, filename="cmd.wav")
        text = (transcript or typed or "").strip()
        if not text:
            st.warning("No se recibió ningún comando. Escribe algo o graba audio.")
        else:
            intent = parse_intent(text)
            state["last_interaction_ts"] = datetime.utcnow()

            feedback_lines = [f"🗣️ Entrada: *{text}*", f"🎯 Intent: `{intent}`"]

            if intent["intent"] == "report" and intent.get("category"):
                rep = crowd.submit_report(
                    reporter_id=user.id,
                    category=intent["category"],
                    lat=state["assist_center"][0],
                    lon=state["assist_center"][1],
                    line_id=line.id if line else None,
                    note=text,
                )
                feedback_lines.append(
                    f"✅ CrowdReport #{rep.id} · {crowd.label_for(rep.category)} · "
                    f"expira {rep.expires_at.strftime('%H:%M')} UTC"
                )
            elif intent["intent"] == "panic":
                _trigger_panic(user, bus, line, state["assist_center"], origin="voice")
                feedback_lines.append("🚨 Pánico activado. Central avisada.")
            elif intent["intent"] == "read_alerts":
                reports = crowd.nearby(state["assist_center"], state["assist_radius_m"])
                if not reports:
                    feedback_lines.append("Sin alertas cercanas.")
                else:
                    top = reports[:3]
                    feedback_lines.append("Top alertas: " + " · ".join(
                        f"{r['label']} a {r['distance_m']}m" for r in top
                    ))
            elif intent["intent"] == "silence":
                state["silence_mode"] = True
                feedback_lines.append("Modo silencio activado.")
            elif intent["intent"] == "stop":
                feedback_lines.append("Detenido.")
            elif intent["intent"] == "protocol":
                feedback_lines.append("Abre la pestaña **Protocolos** y selecciona uno.")
            elif intent["intent"] == "status_query":
                feedback_lines.append("Consulta procesada. Revisa la pestaña Turno.")
            else:
                feedback_lines.append("No entendí. Intenta: `reporta bache`, `alerta roja`, `lee alertas`.")

            state["last_command_feedback"] = "\n\n".join(feedback_lines)
            if not state["silence_mode"]:
                ack = short_ack(intent)
                audio_bytes = synthesize(ack)
                state["last_tts_ack"] = audio_bytes

    if state["last_command_feedback"]:
        st.markdown(state["last_command_feedback"])
    if state["last_tts_ack"] and not state["silence_mode"]:
        st.audio(state["last_tts_ack"], format="audio/mp3")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — PROTOCOLOS guiados
# ═══════════════════════════════════════════════════════════════════════════
with tab_protocol:
    st.markdown("Selecciona una situación. El asistente te guiará paso a paso.")

    choices = list_protocols()
    keys = [k for k, _ in choices]
    labels = {k: t for k, t in choices}

    sel = st.selectbox(
        "Protocolo",
        options=[""] + keys,
        format_func=lambda k: "— elige —" if k == "" else labels[k],
        key="protocol_selector",
    )
    col_start, col_reset = st.columns([1, 1])
    if col_start.button("▶ Iniciar", type="primary", use_container_width=True, disabled=not sel):
        state["protocol_key"] = sel
        state["protocol_step"] = 0
        state["last_interaction_ts"] = datetime.utcnow()
    if col_reset.button("⏹ Terminar protocolo", use_container_width=True):
        state["protocol_key"] = None
        state["protocol_step"] = 0

    if state["protocol_key"]:
        proto = get_protocol(state["protocol_key"])
        if proto:
            steps = proto["steps"]
            step_idx = state["protocol_step"]
            if step_idx >= len(steps):
                st.success("✅ Protocolo completado. Registra la incidencia si procede.")
            else:
                st.subheader(proto["title"])
                st.progress((step_idx + 1) / len(steps), text=f"Paso {step_idx + 1} de {len(steps)}")
                current_step = steps[step_idx]
                st.markdown(f"### Paso {step_idx + 1}")
                st.info(current_step)
                if not state["silence_mode"]:
                    audio_step = synthesize(current_step)
                    if audio_step:
                        st.audio(audio_step, format="audio/mp3")

                nav = st.columns([1, 1, 2])
                if nav[0].button("✔ Hecho", type="primary", use_container_width=True):
                    state["protocol_step"] += 1
                    state["last_interaction_ts"] = datetime.utcnow()
                    st.rerun()
                if nav[1].button("↶ Anterior", use_container_width=True, disabled=step_idx == 0):
                    state["protocol_step"] = max(0, step_idx - 1)
                    st.rerun()
                nav[2].caption("Confirma **Hecho** para avanzar. Queda siempre visible el paso actual.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 4 — PÁNICO + DEAD-MAN
# ═══════════════════════════════════════════════════════════════════════════
with tab_panic:
    st.markdown(
        "Pulsa si necesitas asistencia inmediata. Envía tu posición al centro de control "
        "y crea una incidencia crítica marcada como `panic`."
    )

    panic_col1, panic_col2 = st.columns([2, 3])
    with panic_col1:
        st.markdown(
            "<div style='background:#B00020;padding:32px;border-radius:16px;text-align:center;'>"
            "<h2 style='color:white;margin:0;'>🚨 ALERTA ROJA</h2>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button(
            "Activar alerta roja ahora",
            type="primary",
            use_container_width=True,
            key="panic_button",
        ):
            new_id = _trigger_panic(user, bus, line, state["assist_center"], origin="button")
            state["last_interaction_ts"] = datetime.utcnow()
            st.error(f"🚨 Incidencia crítica #{new_id} creada. Central avisada.")
            if not state["silence_mode"]:
                ack = synthesize("Alerta roja enviada. Central avisada.")
                if ack:
                    st.audio(ack, format="audio/mp3")

    with panic_col2:
        st.markdown("### Dead-man switch")
        st.caption(
            "Si se activa, el asistente pedirá confirmación pasado el tiempo configurado. "
            "Si no hay respuesta, dispara alerta roja automáticamente."
        )
        st.toggle("Activar dead-man", key="deadman_enabled")
        st.slider(
            "Tiempo sin interacción (min)",
            min_value=3,
            max_value=30,
            value=10,
            step=1,
            key="deadman_minutes",
            disabled=not state["deadman_enabled"],
        )

        if state["deadman_enabled"]:
            st_autorefresh(interval=30_000, key="deadman_autoref")
            elapsed = datetime.utcnow() - state["last_interaction_ts"]
            warn_after = timedelta(minutes=state.get("deadman_minutes", 10))
            auto_after = warn_after + timedelta(seconds=45)
            remaining = warn_after - elapsed
            if elapsed >= auto_after:
                # Auto-pánico.
                new_id = _trigger_panic(user, bus, line, state["assist_center"], origin="deadman")
                state["last_interaction_ts"] = datetime.utcnow()
                st.error(
                    f"⛔ Dead-man: sin respuesta tras {state['deadman_minutes']} min. "
                    f"Pánico automático #{new_id} enviado."
                )
            elif elapsed >= warn_after:
                st.warning(
                    f"⚠ No ha habido interacción en {state['deadman_minutes']} min. "
                    "Pulsa **Estoy bien** en 45 s o se enviará pánico automático."
                )
                if st.button("Estoy bien — cancelar dead-man", type="primary", use_container_width=True):
                    state["last_interaction_ts"] = datetime.utcnow()
                    st.success("Registrado. Dead-man reiniciado.")
                    st.rerun()
            else:
                mins, secs = divmod(int(remaining.total_seconds()), 60)
                st.info(
                    f"Dead-man activo. Próximo ping en ~{mins:02d}:{secs:02d}. "
                    "Cualquier reporte/confirmación reinicia el contador."
                )
