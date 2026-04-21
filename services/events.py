from __future__ import annotations

from datetime import date
from typing import Any

# Calendario recurrente de eventos típicos de Madrid (mock).
# impact_zone aproxima con (lat, lon, radio_m).
_EVENTS_BY_WEEKDAY: dict[int, list[dict[str, Any]]] = {
    0: [  # Lunes
        {
            "name": "Manifestación Plaza Sol",
            "venue": "Puerta del Sol",
            "start": "18:30",
            "end": "21:00",
            "impact_zone": (40.4168, -3.7038, 600),
        },
    ],
    2: [  # Miércoles
        {
            "name": "Partido Champions — Real Madrid",
            "venue": "Santiago Bernabéu",
            "start": "21:00",
            "end": "23:30",
            "impact_zone": (40.4531, -3.6883, 800),
        },
    ],
    4: [  # Viernes
        {
            "name": "Concierto WiZink Center",
            "venue": "WiZink Center",
            "start": "21:30",
            "end": "00:00",
            "impact_zone": (40.4236, -3.6718, 500),
        },
    ],
    5: [  # Sábado
        {
            "name": "Partido Atlético de Madrid",
            "venue": "Metropolitano",
            "start": "18:30",
            "end": "20:45",
            "impact_zone": (40.4362, -3.5994, 900),
        },
    ],
    6: [  # Domingo
        {
            "name": "Rastro de Madrid",
            "venue": "La Latina",
            "start": "09:00",
            "end": "15:00",
            "impact_zone": (40.4106, -3.7094, 600),
        },
    ],
}


def get_city_events(shift_date: date) -> list[dict[str, Any]]:
    return list(_EVENTS_BY_WEEKDAY.get(shift_date.weekday(), []))
