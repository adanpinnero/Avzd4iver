from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from db.models import Assignment, Bus, CrowdReport, Line, ShiftNote, User
from db.session import ENGINE


# ─── Usuarios ─────────────────────────────────────────────────────────────
# 2 admins + 20 drivers. Todos los drivers usan contraseña "1234".
USERS: list[tuple[str, str, str, str]] = [
    ("admin", "admin", "admin", "Admin Principal"),
    ("sofia", "admin", "admin", "Sofía Álvarez"),
    # Drivers (20)
    ("juan", "1234", "driver", "Juan García"),
    ("maria", "1234", "driver", "María López"),
    ("pedro", "1234", "driver", "Pedro Sánchez"),
    ("lucia", "1234", "driver", "Lucía Fernández"),
    ("carlos", "1234", "driver", "Carlos Ruiz"),
    ("antonio", "1234", "driver", "Antonio Morales"),
    ("elena", "1234", "driver", "Elena Navarro"),
    ("miguel", "1234", "driver", "Miguel Ángel Torres"),
    ("isabel", "1234", "driver", "Isabel Romero"),
    ("javier", "1234", "driver", "Javier Gil"),
    ("cristina", "1234", "driver", "Cristina Serrano"),
    ("david", "1234", "driver", "David Hernández"),
    ("raquel", "1234", "driver", "Raquel Castro"),
    ("fernando", "1234", "driver", "Fernando Iglesias"),
    ("beatriz", "1234", "driver", "Beatriz Molina"),
    ("sergio", "1234", "driver", "Sergio Ortega"),
    ("patricia", "1234", "driver", "Patricia Ramos"),
    ("roberto", "1234", "driver", "Roberto Vega"),
    ("noelia", "1234", "driver", "Noelia Delgado"),
    ("alejandro", "1234", "driver", "Alejandro Prieto"),
]

# ─── Flota (30 buses Mercedes + Irizar) ────────────────────────────────────
# Mezcla realista EMT: Citaro/Conecto estándar y articulados, eCitaro/ie tram
# eléctricos. Capacidades aproximadas.
BUSES: list[tuple[str, str, str, int, str | None]] = [
    # Mercedes Citaro (estándar 12m)
    ("0101-BUS", "Mercedes Citaro", "standard", 90, None),
    ("0102-BUS", "Mercedes Citaro", "standard", 90, None),
    ("0103-BUS", "Mercedes Citaro", "standard", 90, "Climatización en revisión — probar antes de salir"),
    ("0104-BUS", "Mercedes Citaro", "standard", 90, None),
    ("0105-BUS", "Mercedes Citaro", "standard", 90, None),
    # Mercedes Citaro G (articulado 18m)
    ("0201-BUS", "Mercedes Citaro G", "articulated", 150, "18m — cuidado en curvas estrechas"),
    ("0202-BUS", "Mercedes Citaro G", "articulated", 150, "18m — plataforma baja"),
    ("0203-BUS", "Mercedes Citaro G", "articulated", 150, "18m — retrovisor derecho reparado"),
    ("0204-BUS", "Mercedes Citaro G", "articulated", 150, "18m"),
    # Mercedes eCitaro (eléctrico 12m)
    ("0301-BUS", "Mercedes eCitaro", "electric", 85, "Autonomía 200km — cargar al finalizar turno"),
    ("0302-BUS", "Mercedes eCitaro", "electric", 85, "Silencioso — aviso sonoro a peatones en zonas escolares"),
    ("0303-BUS", "Mercedes eCitaro", "electric", 85, "Autonomía 200km"),
    # Mercedes eCitaro G (eléctrico articulado)
    ("0401-BUS", "Mercedes eCitaro G", "articulated", 135, "Eléctrico 18m — autonomía 180km"),
    ("0402-BUS", "Mercedes eCitaro G", "articulated", 135, "Eléctrico 18m"),
    # Mercedes Conecto (estándar)
    ("0501-BUS", "Mercedes Conecto", "standard", 95, None),
    # Irizar i3 (estándar 12m)
    ("1101-BUS", "Irizar i3", "standard", 90, None),
    ("1102-BUS", "Irizar i3", "standard", 90, None),
    ("1103-BUS", "Irizar i3", "standard", 90, "Puerta central lenta — revisar sensor"),
    ("1104-BUS", "Irizar i3", "standard", 90, None),
    ("1105-BUS", "Irizar i3", "standard", 90, None),
    # Irizar i2e (eléctrico 12m)
    ("1201-BUS", "Irizar i2e", "electric", 80, "Autonomía 220km — zero emisiones"),
    ("1202-BUS", "Irizar i2e", "electric", 80, "Silencioso"),
    ("1203-BUS", "Irizar i2e", "electric", 80, "Autonomía 220km"),
    ("1204-BUS", "Irizar i2e", "electric", 80, None),
    # Irizar ie bus (eléctrico 12m)
    ("1301-BUS", "Irizar ie bus", "electric", 85, "Eléctrico nuevo — pantalla a bordo conectada"),
    ("1302-BUS", "Irizar ie bus", "electric", 85, None),
    # Irizar ie tram (eléctrico articulado 18m)
    ("1401-BUS", "Irizar ie tram", "articulated", 120, "Eléctrico 18m — autonomía 180km, revisar recarga"),
    ("1402-BUS", "Irizar ie tram", "articulated", 120, "Eléctrico 18m — plataforma baja"),
    ("1403-BUS", "Irizar ie tram", "articulated", 120, "Eléctrico 18m"),
    ("1404-BUS", "Irizar ie tram", "articulated", 120, "Eléctrico 18m — cámara trasera en calibración"),
]

# ─── Líneas EMT (10 reales/representativas) ────────────────────────────────
LINES: list[tuple[str, str, str, str]] = [
    ("1", "Prosperidad - Cristo Rey", "Prosperidad", "Cristo Rey"),
    ("5", "Sol - Chamartín", "Puerta del Sol", "Chamartín"),
    ("14", "Pacífico - Pío XII", "Pacífico", "Pío XII"),
    ("27", "Plaza Castilla - Embajadores", "Plaza Castilla", "Embajadores"),
    ("34", "Sol - Las Rosas", "Puerta del Sol", "Las Rosas"),
    ("52", "Plaza de Cibeles - Colonia Jardín", "Plaza de Cibeles", "Colonia Jardín"),
    ("74", "Aluche - Colonia Manzanares", "Aluche", "Colonia Manzanares"),
    ("150", "Plaza Castilla - Barrio del Pilar", "Plaza Castilla", "Barrio del Pilar"),
    ("N1", "Cibeles - Los Ángeles (nocturno)", "Plaza de Cibeles", "Los Ángeles"),
    ("N26", "Alonso Martínez - Alameda de Osuna (nocturno)", "Alonso Martínez", "Alameda de Osuna"),
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

        # Asignación de hoy: un bus y línea distintos por conductor (ciclos
        # sobre las colecciones; sobran buses — quedan disponibles para que el
        # admin los reasigne desde el data editor).
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

        # ─── Reportes crowd frescos (radar poblado al arrancar) ───────────
        now = datetime.utcnow()
        crowd_samples: list[tuple[str, float, float, str, str, int, int]] = [
            # (category, lat, lon, note, severity, ttl_min, line_idx)
            ("obstacle", 40.4200, -3.7053, "Bache profundo carril derecho Gran Vía", "media", 60, 3),
            ("jam", 40.4074, -3.6916, "Retención 15 min — obras túnel Atocha", "alta", 30, 3),
            ("protest", 40.4168, -3.7038, "Concentración autorizada en Sol", "media", 180, 1),
            ("construction", 40.4672, -3.6892, "Obra acera — chaflán reducido Pl. Castilla", "baja", 4320, 7),
            ("aggression", 40.4193, -3.6932, "Discusión fuerte entre pasajeros Cibeles", "alta", 120, 5),
            ("accident", 40.4321, -3.6626, "Turismo contra farola en Ventas", "alta", 90, 4),
            ("bump", 40.4461, -3.6925, "Badén mal señalizado Nuevos Ministerios", "baja", 4320, 3),
            ("jam", 40.4350, -3.7192, "Tráfico lento Moncloa", "media", 45, 5),
            ("obstacle", 40.4275, -3.6949, "Contenedor caído en calzada", "media", 90, 9),
        ]
        for i, (cat, lat, lon, note, sev, ttl_min, line_idx) in enumerate(crowd_samples):
            s.add(
                CrowdReport(
                    reporter_id=driver_ids[i % len(driver_ids)],
                    line_id=line_ids[line_idx % len(line_ids)],
                    category=cat,
                    lat=lat,
                    lon=lon,
                    note=note,
                    severity=sev,
                    created_at=now - timedelta(minutes=5 * i),
                    expires_at=now + timedelta(minutes=ttl_min),
                    confirmations=i % 3,
                )
            )

        # ─── Handoffs de ejemplo en varios buses ──────────────────────────
        handoff_samples = [
            (
                bus_ids[0],
                driver_ids[-1],
                "Piloto de aire acondicionado parpadea intermitente. Taller avisado, "
                "revisar al terminar turno.",
            ),
            (
                bus_ids[5],
                driver_ids[-2],
                "Puerta trasera necesita dos pulsaciones para cerrar. Reportado a taller.",
            ),
            (
                bus_ids[15],
                driver_ids[0],
                "Cinturón del conductor flojo — ajustar tornillería antes de ruta.",
            ),
            (
                bus_ids[26],
                driver_ids[3],
                "Cámara trasera en calibración. Usar retrovisores con precaución adicional.",
            ),
        ]
        for bus_id, author_id, body in handoff_samples:
            s.add(ShiftNote(bus_id=bus_id, author_id=author_id, body=body))

        s.commit()
