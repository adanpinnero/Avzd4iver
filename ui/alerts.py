from __future__ import annotations

from typing import Any


def build_alerts(
    bus_type: str,
    bus_notes: str | None,
    line_code: str,
    black_spots: list[dict[str, Any]],
    weather_summary: dict[str, Any],
    events: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Devuelve una lista de alertas con forma {severity, message}.

    severity ∈ {"info", "warning", "error"}.
    """
    alerts: list[dict[str, str]] = []

    if bus_type == "articulated":
        alerts.append(
            {
                "severity": "warning",
                "message": "Autobús articulado (18m): extrema precaución en giros y calles estrechas.",
            }
        )
    elif bus_type == "electric":
        alerts.append(
            {
                "severity": "info",
                "message": "Vehículo eléctrico: comprueba estado de carga antes de iniciar turno.",
            }
        )
    elif bus_type == "midibus":
        alerts.append(
            {
                "severity": "info",
                "message": "Midibús: acceso autorizado a calles estrechas del casco histórico.",
            }
        )

    if bus_notes:
        alerts.append({"severity": "info", "message": f"Nota del vehículo: {bus_notes}"})

    for spot in black_spots:
        sev = {"alta": "error", "media": "warning", "baja": "info"}.get(
            spot.get("severity", "media"), "warning"
        )
        alerts.append(
            {
                "severity": sev,
                "message": f"Tráfico — {spot['reason']}",
            }
        )

    if weather_summary.get("total_rain_mm", 0) >= 2:
        alerts.append(
            {
                "severity": "warning",
                "message": (
                    f"Lluvia prevista acumulada: {weather_summary['total_rain_mm']} mm. "
                    "Reduce velocidad y aumenta distancia de seguridad."
                ),
            }
        )
    if weather_summary.get("max_temp", 0) >= 35:
        alerts.append(
            {
                "severity": "warning",
                "message": f"Máxima prevista {weather_summary['max_temp']}ºC — hidrátate.",
            }
        )

    for ev in events:
        alerts.append(
            {
                "severity": "info",
                "message": f"Evento ciudad: {ev['name']} en {ev['venue']} ({ev['start']}-{ev['end']}).",
            }
        )

    return alerts
