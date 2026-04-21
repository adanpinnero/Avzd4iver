from __future__ import annotations

import streamlit as st
from sqlmodel import select

from db.models import User
from db.session import get_session


def current_user() -> User | None:
    return st.session_state.get("user")


def login_form() -> None:
    st.subheader("Iniciar sesión")
    with st.form("login"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar", use_container_width=True)
    if submitted:
        with get_session() as s:
            user = s.exec(
                select(User).where(User.username == username)
            ).first()
        if user and user.password == password:
            st.session_state["user"] = user
            st.success(f"Bienvenido/a, {user.full_name}")
            st.rerun()
        else:
            st.error("Credenciales inválidas")


def logout_button() -> None:
    if st.sidebar.button("Cerrar sesión", use_container_width=True):
        st.session_state.pop("user", None)
        st.rerun()


def require_role(role: str) -> User:
    user = current_user()
    if user is None:
        st.warning("Debes iniciar sesión en la página principal.")
        st.stop()
    if user.role != role:
        st.error(f"Acceso denegado. Esta página requiere el rol: {role}.")
        st.stop()
    logout_button()
    st.sidebar.caption(f"Sesión: {user.full_name} ({user.role})")
    return user
