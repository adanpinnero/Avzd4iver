from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import pandas as pd

from db.models import Bus, Line, User
from services import dgt, events, madrid_opendata, traffic, transit, weather
from services.crowd import _haversine_m
from ui.alerts import build_alerts
from ui.timeline import build_timeline_df


NEAR_ROUTE_METERS = 1500.0  # radio para considerar algo "cerca de la ruta"


@dataclass
class RoutePlan:
    driver: User
    bus: Bus
    line: Line
    shift_date: date
    stops: list[dict[str, Any]] = field(default_factory=list)
    geometry: list[tuple[float, float]] = field(default_factory=list)
    timetable: pd.DataFrame = field(default_factory=pd.DataFrame)
    timeline_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    black_spots: list[dict[str, Any]] = field(default_factory=list)
    forecast: list[dict[str, Any]] = field(default_factory=list)
    weather_summary: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    alerts: list[dict[str, str]] = field(default_factory=list)
    # Datos reales integrados
    dgt_incidents: list[dict[str, Any]] = field(default_factory=list)
    road_works: list[dict[str, Any]] = field(default_factory=list)
    aqi: dict[str, Any] | None = None
    generated_at: datetime = field(default_factory=datetime.utcnow)


def _min_distance_to_route(
    point: tuple[float, float], geometry: list[tuple[float, float]]
) -> float:
    if not geometry:
        return float("inf")
    return min(_haversine_m(point, g) for g in geometry)


def _route_center(geometry: list[tuple[float, float]]) -> tuple[float, float] | None:
    if not geometry:
        return None
    lat = sum(p[0] for p in geometry) / len(geometry)
    lon = sum(p[1] for p in geometry) / len(geometry)
    return (lat, lon)


def _nearby(
    items: list[dict[str, Any]],
    geometry: list[tuple[float, float]],
    radius_m: float = NEAR_ROUTE_METERS,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for it in items:
        lat, lon = it.get("lat"), it.get("lon")
        if lat is None or lon is None:
            continue
        d = _min_distance_to_route((lat, lon), geometry)
        if d <= radius_m:
            item = dict(it)
            item["distance_m"] = round(d, 0)
            out.append(item)
    return sorted(out, key=lambda x: x["distance_m"])


def _nearest_station(
    stations: list[dict[str, Any]], center: tuple[float, float] | None
) -> dict[str, Any] | None:
    if not stations or center is None:
        return None
    best = min(stations, key=lambda s: _haversine_m(center, (s["lat"], s["lon"])))
    return best


def _dedupe_black_spots(spots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[float, float]] = set()
    out: list[dict[str, Any]] = []
    for s in spots:
        key = (round(s.get("lat", 0), 4), round(s.get("lon", 0), 4))
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def _severity_to_ui(sev: str) -> str:
    return {"alta": "error", "media": "warning", "baja": "info"}.get(sev, "warning")


def build_plan(driver: User, bus: Bus, line: Line, shift_date: date) -> RoutePlan:
    route = transit.get_route(line.code)
    geometry = route.geometry

    # ─── Fuentes base ──────────────────────────────────────────────────────
    mock_spots = traffic.get_black_spots(line.code, shift_date)
    forecast = weather.get_forecast(shift_date)
    wsummary = weather.summary(forecast)
    city_events = events.get_city_events(shift_date)

    # ─── Datos reales DGT + Madrid ─────────────────────────────────────────
    all_dgt = dgt.fetch_incidents()
    dgt_nearby = _nearby(all_dgt, geometry)

    all_rw = madrid_opendata.fetch_road_works()
    rw_nearby = _nearby(all_rw, geometry)

    # Puntos negros DGT cerca + mocks originales → lista unificada.
    pn_nearby = _nearby(dgt.load_puntos_negros(), geometry)
    # Forma compatible con traffic.get_black_spots: {lat, lon, severity, reason}
    pn_as_spots = [
        {
            "lat": p["lat"],
            "lon": p["lon"],
            "severity": p.get("concentracion", "media"),
            "reason": f"Punto negro DGT {p.get('carretera', '')} km {p.get('pk', '')} "
                      f"({p.get('accidentes_5y', 0)} acc./5 años)",
            "source": "dgt",
        }
        for p in pn_nearby
    ]
    black_spots = _dedupe_black_spots(mock_spots + pn_as_spots)

    # AQI: estación más cercana al centro de la ruta.
    center = _route_center(geometry)
    aqi = _nearest_station(madrid_opendata.fetch_air_quality(), center)

    # ─── Alertas ──────────────────────────────────────────────────────────
    alerts = build_alerts(
        bus_type=bus.type,
        bus_notes=bus.notes,
        line_code=line.code,
        black_spots=black_spots,
        weather_summary=wsummary,
        events=city_events,
    )

    for inc in dgt_nearby:
        alerts.append(
            {
                "severity": _severity_to_ui(inc.get("severity", "media")),
                "message": (
                    f"DGT — {inc['tipo'].title()} en {inc.get('carretera', '')} "
                    f"km {inc.get('pk', '')}: {inc['descripcion']} "
                    f"(a {int(inc['distance_m'])}m de la ruta)"
                ),
            }
        )
    for rw in rw_nearby:
        alerts.append(
            {
                "severity": _severity_to_ui(rw.get("severity", "media")),
                "message": (
                    f"Ayto. Madrid — {rw['titulo']} · distrito {rw.get('distrito', '-')} "
                    f"(a {int(rw['distance_m'])}m de la ruta)"
                ),
            }
        )

    if aqi and aqi.get("aqi", 0) >= 80:
        alerts.append(
            {
                "severity": "warning",
                "message": (
                    f"Calidad del aire {aqi['aqi_label']} en {aqi['estacion']} "
                    f"(AQI {aqi['aqi']}) — ventilación reducida recomendada."
                ),
            }
        )

    timeline_df = build_timeline_df(shift_date, forecast)

    return RoutePlan(
        driver=driver,
        bus=bus,
        line=line,
        shift_date=shift_date,
        stops=route.stops,
        geometry=geometry,
        timetable=route.timetable,
        timeline_df=timeline_df,
        black_spots=black_spots,
        forecast=forecast,
        weather_summary=wsummary,
        events=city_events,
        alerts=alerts,
        dgt_incidents=dgt_nearby,
        road_works=rw_nearby,
        aqi=aqi,
    )
