from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd


@dataclass
class RouteData:
    stops: list[dict[str, Any]] = field(default_factory=list)
    geometry: list[tuple[float, float]] = field(default_factory=list)
    timetable: pd.DataFrame = field(default_factory=pd.DataFrame)


# Geometrías aproximadas (lat, lon) de recorridos reales EMT en Madrid.
# Fuente: trazado manual sobre paradas conocidas, suficiente para visualización.
_ROUTES: dict[str, dict[str, Any]] = {
    "1": {
        "stops": [
            ("Prosperidad", 40.4483, -3.6720),
            ("Avda. América", 40.4371, -3.6779),
            ("Goya", 40.4257, -3.6760),
            ("Cibeles", 40.4193, -3.6932),
            ("Ópera", 40.4183, -3.7098),
            ("Cristo Rey", 40.4399, -3.7220),
        ],
    },
    "5": {
        "stops": [
            ("Puerta del Sol", 40.4168, -3.7038),
            ("Gran Vía", 40.4200, -3.7053),
            ("Alonso Martínez", 40.4275, -3.6949),
            ("Rubén Darío", 40.4335, -3.6900),
            ("Nuevos Ministerios", 40.4461, -3.6925),
            ("Chamartín", 40.4721, -3.6832),
        ],
    },
    "14": {
        "stops": [
            ("Pacífico", 40.4020, -3.6773),
            ("Retiro", 40.4150, -3.6820),
            ("Goya", 40.4257, -3.6760),
            ("Avda. América", 40.4371, -3.6779),
            ("República Argentina", 40.4455, -3.6861),
            ("Pío XII", 40.4631, -3.6758),
        ],
    },
    "27": {
        "stops": [
            ("Plaza Castilla", 40.4672, -3.6892),
            ("Nuevos Ministerios", 40.4461, -3.6925),
            ("Gregorio Marañón", 40.4381, -3.6908),
            ("Bilbao", 40.4301, -3.7005),
            ("Gran Vía", 40.4200, -3.7053),
            ("Atocha", 40.4074, -3.6916),
            ("Embajadores", 40.4049, -3.7063),
        ],
    },
    "34": {
        "stops": [
            ("Puerta del Sol", 40.4168, -3.7038),
            ("Gran Vía", 40.4200, -3.7053),
            ("Goya", 40.4257, -3.6760),
            ("Ventas", 40.4321, -3.6626),
            ("San Blas", 40.4280, -3.6110),
            ("Las Rosas", 40.4318, -3.5950),
        ],
    },
    "52": {
        "stops": [
            ("Plaza de Cibeles", 40.4193, -3.6932),
            ("Gran Vía", 40.4200, -3.7053),
            ("Plaza de España", 40.4234, -3.7121),
            ("Princesa", 40.4314, -3.7182),
            ("Moncloa", 40.4350, -3.7192),
            ("Colonia Jardín", 40.4083, -3.7750),
        ],
    },
    "74": {
        "stops": [
            ("Aluche", 40.3852, -3.7556),
            ("Oporto", 40.3946, -3.7307),
            ("Carabanchel", 40.3864, -3.7286),
            ("Colonia Manzanares", 40.3987, -3.7400),
        ],
    },
    "150": {
        "stops": [
            ("Plaza Castilla", 40.4672, -3.6892),
            ("Virgen del Cortijo", 40.4921, -3.6750),
            ("Monteforte", 40.4830, -3.6955),
            ("Peñagrande", 40.4795, -3.7200),
            ("Barrio del Pilar", 40.4783, -3.7090),
        ],
    },
    "N1": {
        "stops": [
            ("Plaza de Cibeles", 40.4193, -3.6932),
            ("Atocha", 40.4074, -3.6916),
            ("Legazpi", 40.3909, -3.6949),
            ("Usera", 40.3811, -3.7013),
            ("Los Ángeles", 40.3550, -3.7100),
        ],
    },
    "N26": {
        "stops": [
            ("Alonso Martínez", 40.4275, -3.6949),
            ("Cibeles", 40.4193, -3.6932),
            ("Atocha", 40.4074, -3.6916),
            ("Ventas", 40.4321, -3.6626),
            ("Canillejas", 40.4514, -3.6150),
            ("Alameda de Osuna", 40.4575, -3.5878),
        ],
    },
}


def get_route(line_code: str) -> RouteData:
    raw = _ROUTES.get(line_code)
    if raw is None:
        return RouteData()
    stops = [{"name": n, "lat": la, "lon": lo} for (n, la, lo) in raw["stops"]]
    geometry = [(la, lo) for (_, la, lo) in raw["stops"]]
    timetable = _build_timetable(stops)
    return RouteData(stops=stops, geometry=geometry, timetable=timetable)


def _build_timetable(stops: list[dict[str, Any]]) -> pd.DataFrame:
    """Genera un horario sintético: 8 turnos de ida/vuelta entre 06:00 y 22:00."""
    base = datetime.combine(date.today(), datetime.min.time()).replace(hour=6)
    rows: list[dict[str, Any]] = []
    for turn in range(8):
        start = base + timedelta(hours=2 * turn)
        for idx, stop in enumerate(stops):
            arrival = start + timedelta(minutes=6 * idx)
            rows.append(
                {
                    "turno": turn + 1,
                    "parada": stop["name"],
                    "hora": arrival.strftime("%H:%M"),
                }
            )
    return pd.DataFrame(rows)
