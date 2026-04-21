from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from db.models import Assignment, Bus, Line, User
from db.session import ENGINE


USERS = [
    ("admin", "admin", "admin", "Admin Principal"),
    ("sofia", "admin", "admin", "Sofía Álvarez"),
    ("juan", "1234", "driver", "Juan García"),
    ("maria", "1234", "driver", "María López"),
    ("pedro", "1234", "driver", "Pedro Sánchez"),
    ("lucia", "1234", "driver", "Lucía Fernández"),
    ("carlos", "1234", "driver", "Carlos Ruiz"),
]

BUSES = [
    ("0412-BUS", "Mercedes Citaro", "standard", 90, None),
    ("0523-BUS", "Mercedes CapaCity L", "articulated", 150, "18m — cuidado en curvas estrechas"),
    ("0674-BUS", "Irizar ie tram", "electric", 95, "Autonomía 180km — revisar recarga si turno >8h"),
    ("0712-BUS", "Iveco Urbanway", "standard", 85, None),
    ("0833-BUS", "BYD K9", "electric", 80, "Silencioso — aviso sonoro a peatones en zonas escolares"),
    ("0901-BUS", "Mercedes Citaro G", "articulated", 150, "18m — plataforma baja"),
    ("1021-BUS", "Otokar Navigo", "midibus", 45, "Acceso a calles estrechas casco histórico"),
    ("1152-BUS", "Scania Citywide", "standard", 95, None),
]

LINES = [
    ("1", "Prosperidad - Cristo Rey", "Prosperidad", "Cristo Rey"),
    ("27", "Plaza Castilla - Embajadores", "Plaza Castilla", "Embajadores"),
    ("52", "Plaza de Cibeles - Colonia Jardín", "Plaza de Cibeles", "Colonia Jardín"),
    ("74", "Aluche - Colonia Manzanares", "Aluche", "Colonia Manzanares"),
    ("150", "Plaza Castilla - Barrio del Pilar", "Plaza Castilla", "Barrio del Pilar"),
    ("N26", "Alonso Martínez - Alameda de Osuna", "Alonso Martínez", "Alameda de Osuna"),
]


def seed_all() -> None:
    today = date.today()
    with Session(ENGINE) as s:
        for username, password, role, full in USERS:
            s.add(User(username=username, password=password, role=role, full_name=full))
        for plate, model, btype, cap, notes in BUSES:
            s.add(Bus(plate=plate, model=model, type=btype, capacity=cap, notes=notes))
        for code, name, start, end in LINES:
            s.add(Line(code=code, name=name, start_stop=start, end_stop=end))
        s.commit()

        driver_ids = [u.id for u in s.exec(select(User).where(User.role == "driver")).all()]
        bus_ids = [b.id for b in s.exec(select(Bus)).all()]
        line_ids = [l.id for l in s.exec(select(Line)).all()]

        for i, d_id in enumerate(driver_ids):
            s.add(
                Assignment(
                    driver_id=d_id,
                    bus_id=bus_ids[i % len(bus_ids)],
                    line_id=line_ids[i % len(line_ids)],
                    shift_date=today,
                )
            )
        s.commit()
