from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
from sqlmodel import select

from db.models import Assignment, Bus, Line, User
from db.session import get_session
from ui.auth import require_role

st.set_page_config(page_title="Asignaciones", page_icon="📋", layout="wide")

require_role("admin")

st.title("📋 Asignaciones del día")
st.caption("Edita las filas y pulsa **Guardar cambios** para persistir.")

shift_date = st.date_input("Fecha", value=date.today())

with get_session() as s:
    drivers = s.exec(select(User).where(User.role == "driver").order_by(User.full_name)).all()
    buses = s.exec(select(Bus).order_by(Bus.plate)).all()
    lines = s.exec(select(Line).order_by(Line.code)).all()
    assignments = s.exec(
        select(Assignment).where(Assignment.shift_date == shift_date)
    ).all()

driver_options = {d.full_name: d.id for d in drivers}
bus_options = {b.plate: b.id for b in buses}
line_options = {ln.code: ln.id for ln in lines}

driver_by_id = {d.id: d.full_name for d in drivers}
bus_by_id = {b.id: b.plate for b in buses}
line_by_id = {ln.id: ln.code for ln in lines}

rows = [
    {
        "id": a.id,
        "Conductor": driver_by_id.get(a.driver_id, ""),
        "Autobús": bus_by_id.get(a.bus_id, ""),
        "Línea": line_by_id.get(a.line_id, ""),
    }
    for a in assignments
]
if not rows:
    rows = [{"id": None, "Conductor": "", "Autobús": "", "Línea": ""}]

df = pd.DataFrame(rows)

edited = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "id": st.column_config.NumberColumn("id", disabled=True),
        "Conductor": st.column_config.SelectboxColumn(
            "Conductor", options=list(driver_options.keys()), required=True
        ),
        "Autobús": st.column_config.SelectboxColumn(
            "Autobús", options=list(bus_options.keys()), required=True
        ),
        "Línea": st.column_config.SelectboxColumn(
            "Línea", options=list(line_options.keys()), required=True
        ),
    },
    hide_index=True,
    key="assignments_editor",
)

cols = st.columns([1, 1, 5])
save = cols[0].button("💾 Guardar cambios", type="primary", use_container_width=True)
if cols[1].button("🔄 Recargar", use_container_width=True):
    st.rerun()

if save:
    try:
        with get_session() as s:
            existing = s.exec(
                select(Assignment).where(Assignment.shift_date == shift_date)
            ).all()
            for a in existing:
                s.delete(a)
            s.commit()

            inserted = 0
            for _, row in edited.iterrows():
                driver_name = row.get("Conductor")
                bus_plate = row.get("Autobús")
                line_code = row.get("Línea")
                if not (driver_name and bus_plate and line_code):
                    continue
                if (
                    driver_name not in driver_options
                    or bus_plate not in bus_options
                    or line_code not in line_options
                ):
                    continue
                s.add(
                    Assignment(
                        driver_id=driver_options[driver_name],
                        bus_id=bus_options[bus_plate],
                        line_id=line_options[line_code],
                        shift_date=shift_date,
                    )
                )
                inserted += 1
            s.commit()
        st.success(f"Asignaciones del {shift_date} actualizadas ({inserted} filas).")
        st.rerun()
    except Exception as e:
        st.error(f"Error guardando asignaciones: {e}")

st.divider()
kpis = st.columns(3)
kpis[0].metric("Conductores", len(drivers))
kpis[1].metric("Autobuses", len(buses))
kpis[2].metric("Líneas", len(lines))
