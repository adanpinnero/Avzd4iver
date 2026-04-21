from __future__ import annotations

import streamlit as st

from db.session import init_db
from ui.auth import current_user, login_form, logout_button

st.set_page_config(
    page_title="Flota EMT Madrid",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

st.title("🚌 Gestión de Flota — Autobuses Madrid")
st.caption("Plataforma interna de planificación de rutas y gestión de incidencias.")

user = current_user()

if user is None:
    st.info(
        "Introduce tus credenciales para acceder. Usuarios demo: "
        "`admin/admin` (administrador) o `juan/1234`, `maria/1234`, `pedro/1234`, "
        "`lucia/1234`, `carlos/1234` (conductores)."
    )
    login_form()
else:
    logout_button()
    st.sidebar.caption(f"Sesión: {user.full_name} ({user.role})")
    st.success(f"Sesión iniciada como **{user.full_name}** ({user.role}).")
    if user.role == "driver":
        st.markdown(
            "Usa el menú lateral para acceder a:\n"
            "- **Driver Turno**: plan diario con briefing hablado y handoff.\n"
            "- **Driver Asistente**: radar crowd, voz, protocolos guiados y pánico.\n"
            "- **Driver Incidencia**: reporta una incidencia con asistencia IA."
        )
    else:
        st.markdown(
            "Usa el menú lateral para acceder a:\n"
            "- **Admin Asignaciones**: gestiona asignaciones conductor/bus/línea.\n"
            "- **Admin LiveMap**: mapa en vivo de incidencias, pánicos y crowd."
        )
