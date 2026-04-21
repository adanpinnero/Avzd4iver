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
    crowd_reports: Iterable[dict[str, Any]] | None = None,
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
        is_panic = inc.get("kind") == "panic" or inc.get("severity") == "critical"
        color = "darkred" if is_panic else "red"
        icon_name = "fire" if is_panic else "warning-sign"
        title = "🚨 PÁNICO" if is_panic else f"Incidencia #{inc['id']}"
        popup_html = (
            f"<b>{title} #{inc['id']}</b><br>"
            f"Bus: {inc.get('bus_plate', '-')}<br>"
            f"Línea: {inc.get('line_code', '-')}<br>"
            f"Conductor: {inc.get('driver_name', '-')}<br>"
            f"<i>{inc.get('description', '')[:160]}</i><br>"
            f"<small>{inc.get('created_at', '')}</small>"
        )
        folium.Marker(
            location=(inc["lat"], inc["lon"]),
            tooltip=title,
            popup=folium.Popup(popup_html, max_width=320),
            icon=folium.Icon(color=color, icon=icon_name),
        ).add_to(fmap)
        if is_panic:
            # Halo pulsante visual: círculo rojo extra.
            folium.Circle(
                location=(inc["lat"], inc["lon"]),
                radius=250,
                color="#B00020",
                fill=True,
                fill_opacity=0.15,
            ).add_to(fmap)

    if crowd_reports:
        for cr in crowd_reports:
            popup_html = (
                f"<b>{cr.get('label', cr['category'])}</b><br>"
                f"Severidad: {cr.get('severity', '-')}<br>"
                f"Reporta: {cr.get('reporter', '-')}<br>"
                f"Línea: {cr.get('line', '-')}<br>"
                f"Confirmaciones: {cr.get('confirmations', 0)} · "
                f"Descartes: {cr.get('downvotes', 0)}<br>"
                f"<i>{(cr.get('note') or '')[:140]}</i>"
            )
            folium.Marker(
                location=(cr["lat"], cr["lon"]),
                tooltip=f"{cr.get('label', cr['category'])} · {cr.get('severity', '-')}",
                popup=folium.Popup(popup_html, max_width=320),
                icon=folium.Icon(color=cr.get("map_color", "blue"), icon="info-sign"),
            ).add_to(fmap)

    return fmap
