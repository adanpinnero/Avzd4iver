from __future__ import annotations

import math
from datetime import date
from typing import Any


def get_forecast(shift_date: date) -> list[dict[str, Any]]:
    """Genera un pronóstico horario determinista (mock AEMET/OpenWeather).

    Usa el día del año como semilla para que el mismo día dé la misma previsión
    en cada ejecución, variando a lo largo del año.
    """
    day_of_year = shift_date.timetuple().tm_yday
    rows: list[dict[str, Any]] = []
    for hour in range(24):
        base = 12 + 10 * math.sin((day_of_year / 365) * 2 * math.pi - 1.5)
        swing = 6 * math.sin((hour - 6) / 24 * 2 * math.pi)
        temp = round(base + swing, 1)
        rain = 0.0
        condition = "Despejado"
        if (day_of_year + hour) % 17 == 0:
            condition = "Lluvia"
            rain = round(1.2 + (hour % 3), 1)
        elif (day_of_year + hour) % 9 == 0:
            condition = "Nublado"
        rows.append(
            {
                "hour": hour,
                "temp_c": temp,
                "condition": condition,
                "rain_mm": rain,
            }
        )
    return rows


def summary(forecast: list[dict[str, Any]]) -> dict[str, Any]:
    total_rain = sum(f["rain_mm"] for f in forecast)
    temps = [f["temp_c"] for f in forecast]
    conditions = {f["condition"] for f in forecast}
    return {
        "min_temp": min(temps),
        "max_temp": max(temps),
        "total_rain_mm": round(total_rain, 1),
        "conditions": ", ".join(sorted(conditions)),
    }
