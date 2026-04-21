from __future__ import annotations

from typing import Any, Iterable

import folium

MADRID_CENTER = (40.4168, -3.7038)


def build_driver_map(
    geometry: list[tuple[float, float]],
    stops: list[dict[str, Any]],
    black_spots: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> folium.Map:
    center = geometry[len(geometry) // 2] if geometry else MADRID_CENTER
    fmap = folium.Map(location=center, zoom_start=12, tiles="OpenStreetMap")

    if len(geometry) >= 2:
        folium.PolyLine(
            locations=geometry,
            color="#1F77B4",
            weight=5,
            opacity=0.8,
            tooltip="Ruta asignada",
        ).add_to(fmap)

    for stop in stops:
        folium.CircleMarker(
            location=(stop["lat"], stop["lon"]),
            radius=5,
            color="#1F77B4",
            fill=True,
            fill_opacity=0.9,
            tooltip=stop["name"],
        ).add_to(fmap)

    for spot in black_spots:
        color = {"alta": "red", "media": "orange", "baja": "beige"}.get(
            spot.get("severity", "media"), "orange"
        )
        folium.Marker(
            location=(spot["lat"], spot["lon"]),
            tooltip=f"Tráfico: {spot['reason']}",
            icon=folium.Icon(color=color, icon="exclamation-sign"),
        ).add_to(fmap)

    for ev in events:
        lat, lon, radius = ev["impact_zone"]
        folium.Circle(
            location=(lat, lon),
            radius=radius,
            color="#9467BD",
            fill=True,
            fill_opacity=0.15,
            tooltip=f"{ev['name']} ({ev['start']}-{ev['end']})",
        ).add_to(fmap)

    return fmap


def build_admin_live_map(
    incidents: Iterable[dict[str, Any]],
    lines_geometry: dict[str, list[tuple[float, float]]] | None = None,
) -> folium.Map:
    fmap = folium.Map(location=MADRID_CENTER, zoom_start=11, tiles="OpenStreetMap")

    if lines_geometry:
        for code, geom in lines_geometry.items():
            if len(geom) < 2:
                continue
            folium.PolyLine(
                locations=geom,
                color="#2CA02C",
                weight=3,
                opacity=0.5,
                tooltip=f"Línea {code}",
            ).add_to(fmap)

    for inc in incidents:
        if inc.get("lat") is None or inc.get("lon") is None:
            continue
        popup_html = (
            f"<b>Incidencia #{inc['id']}</b><br>"
            f"Bus: {inc.get('bus_plate', '-')}<br>"
            f"Línea: {inc.get('line_code', '-')}<br>"
            f"Conductor: {inc.get('driver_name', '-')}<br>"
            f"<i>{inc.get('description', '')[:120]}</i><br>"
            f"<small>{inc.get('created_at', '')}</small>"
        )
        folium.Marker(
            location=(inc["lat"], inc["lon"]),
            tooltip=f"Incidencia #{inc['id']}",
            popup=folium.Popup(popup_html, max_width=320),
            icon=folium.Icon(color="red", icon="warning-sign"),
        ).add_to(fmap)

    return fmap
