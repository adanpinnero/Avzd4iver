from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd

from db.models import Bus, Line, User
from services import events, traffic, transit, weather
from ui.alerts import build_alerts
from ui.timeline import build_timeline_df


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


def build_plan(driver: User, bus: Bus, line: Line, shift_date: date) -> RoutePlan:
    route = transit.get_route(line.code)
    black_spots = traffic.get_black_spots(line.code, shift_date)
    forecast = weather.get_forecast(shift_date)
    wsummary = weather.summary(forecast)
    city_events = events.get_city_events(shift_date)
    alerts = build_alerts(
        bus_type=bus.type,
        bus_notes=bus.notes,
        line_code=line.code,
        black_spots=black_spots,
        weather_summary=wsummary,
        events=city_events,
    )
    timeline_df = build_timeline_df(shift_date, forecast)
    return RoutePlan(
        driver=driver,
        bus=bus,
        line=line,
        shift_date=shift_date,
        stops=route.stops,
        geometry=route.geometry,
        timetable=route.timetable,
        timeline_df=timeline_df,
        black_spots=black_spots,
        forecast=forecast,
        weather_summary=wsummary,
        events=city_events,
        alerts=alerts,
    )
