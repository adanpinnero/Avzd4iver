from __future__ import annotations

from datetime import date
from typing import Any

# Puntos conflictivos típicos asociados a cada línea (mock DGT).
_BLACK_SPOTS: dict[str, list[dict[str, Any]]] = {
    "1": [
        {"lat": 40.4193, "lon": -3.6932, "severity": "media", "reason": "Cibeles: obras en calzada"},
    ],
    "27": [
        {"lat": 40.4200, "lon": -3.7053, "severity": "alta", "reason": "Gran Vía: manifestación semanal"},
        {"lat": 40.4074, "lon": -3.6916, "severity": "media", "reason": "Atocha: congestión por taxis"},
    ],
    "52": [
        {"lat": 40.4234, "lon": -3.7121, "severity": "alta", "reason": "Plaza España: obras túnel"},
    ],
    "74": [
        {"lat": 40.3852, "lon": -3.7556, "severity": "baja", "reason": "Aluche: salida autovía"},
    ],
    "150": [
        {"lat": 40.4672, "lon": -3.6892, "severity": "media", "reason": "Plaza Castilla: intercambiador saturado"},
    ],
    "N26": [
        {"lat": 40.4514, "lon": -3.6150, "severity": "alta", "reason": "Canillejas: accidente frecuente nocturno"},
    ],
}


def get_black_spots(line_code: str, shift_date: date) -> list[dict[str, Any]]:
    base = list(_BLACK_SPOTS.get(line_code, []))
    # Los viernes añadimos un punto extra genérico (mock de patrón semanal).
    if shift_date.weekday() == 4:
        base.append(
            {
                "lat": 40.4168,
                "lon": -3.7038,
                "severity": "media",
                "reason": "Viernes tarde: tráfico salida Madrid",
            }
        )
    return base
