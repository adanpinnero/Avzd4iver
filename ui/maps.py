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
    dgt_incidents: Iterable[dict[str, Any]] | None = None,
    road_works: Iterable[dict[str, Any]] | None = None,
    puntos_negros: Iterable[dict[str, Any]] | None = None,
    aqi_stations: Iterable[dict[str, Any]] | None = None,
) -> folium.Map:
    """Mapa admin con capas toggleables via `folium.LayerControl`."""
    fmap = folium.Map(location=MADRID_CENTER, zoom_start=11, tiles="OpenStreetMap")

    fg_lines = folium.FeatureGroup(name="Líneas en servicio", show=True)
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
            ).add_to(fg_lines)
    fg_lines.add_to(fmap)

    fg_internal = folium.FeatureGroup(name="🚨 Incidencias internas", show=True)
    for inc in incidents or []:
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
        ).add_to(fg_internal)
        if is_panic:
            folium.Circle(
                location=(inc["lat"], inc["lon"]),
                radius=250,
                color="#B00020",
                fill=True,
                fill_opacity=0.15,
            ).add_to(fg_internal)
    fg_internal.add_to(fmap)

    fg_crowd = folium.FeatureGroup(name="👥 Reportes crowd", show=True)
    for cr in crowd_reports or []:
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
        ).add_to(fg_crowd)
    fg_crowd.add_to(fmap)

    fg_dgt = folium.FeatureGroup(name="🛣️ DGT tiempo real", show=True)
    dgt_icon_for = {
        "accidente": ("red", "warning-sign"),
        "obra": ("orange", "wrench"),
        "retencion": ("orange", "road"),
        "meteo": ("blue", "cloud"),
        "otros": ("gray", "info-sign"),
    }
    for inc in dgt_incidents or []:
        col, icn = dgt_icon_for.get(inc.get("tipo", "otros"), ("gray", "info-sign"))
        popup_html = (
            f"<b>DGT · {inc.get('tipo', '-').title()}</b><br>"
            f"{inc.get('carretera', '')} km {inc.get('pk', '')}<br>"
            f"Severidad: {inc.get('severity', '-')}<br>"
            f"<i>{(inc.get('descripcion') or '')[:200]}</i>"
        )
        folium.Marker(
            location=(inc["lat"], inc["lon"]),
            tooltip=f"DGT · {inc.get('tipo', '-')} · {inc.get('severity', '-')}",
            popup=folium.Popup(popup_html, max_width=320),
            icon=folium.Icon(color=col, icon=icn),
        ).add_to(fg_dgt)
    fg_dgt.add_to(fmap)

    fg_rw = folium.FeatureGroup(name="🏗️ Obras Madrid", show=False)
    for rw in road_works or []:
        sev = rw.get("severity", "media")
        col = {"alta": "red", "media": "orange", "baja": "lightgray"}.get(sev, "orange")
        popup_html = (
            f"<b>{rw.get('titulo', 'Obra')}</b><br>"
            f"Distrito: {rw.get('distrito', '-')}<br>"
            f"Severidad: {sev}"
        )
        folium.Marker(
            location=(rw["lat"], rw["lon"]),
            tooltip=rw.get("titulo", "Obra Madrid"),
            popup=folium.Popup(popup_html, max_width=320),
            icon=folium.Icon(color=col, icon="wrench"),
        ).add_to(fg_rw)
    fg_rw.add_to(fmap)

    fg_pn = folium.FeatureGroup(name="⚫ Puntos negros DGT", show=False)
    for pn in puntos_negros or []:
        sev = pn.get("concentracion", "media")
        col = {"alta": "#8B0000", "media": "#D35400", "baja": "#7D8A9E"}.get(sev, "#8B0000")
        popup_html = (
            f"<b>Punto negro DGT</b><br>"
            f"{pn.get('carretera', '')} km {pn.get('pk', '')}<br>"
            f"Accidentes 5 años: {pn.get('accidentes_5y', '-')}<br>"
            f"Concentración: {sev}"
        )
        folium.CircleMarker(
            location=(pn["lat"], pn["lon"]),
            radius=7,
            color=col,
            weight=2,
            fill=True,
            fill_color=col,
            fill_opacity=0.55,
            tooltip=f"Punto negro · {pn.get('carretera', '')} km {pn.get('pk', '')}",
            popup=folium.Popup(popup_html, max_width=280),
        ).add_to(fg_pn)
    fg_pn.add_to(fmap)

    fg_aqi = folium.FeatureGroup(name="🌫️ Calidad del aire", show=False)
    for stn in aqi_stations or []:
        aqi = stn.get("aqi", 0)
        col = (
            "#2F9E44" if aqi <= 40 else
            "#F2B73E" if aqi <= 60 else
            "#E08E0B" if aqi <= 80 else
            "#C81D25"
        )
        popup_html = (
            f"<b>{stn.get('estacion', '-')}</b><br>"
            f"AQI {aqi} — {stn.get('aqi_label', '-')}<br>"
            f"NO₂ {stn.get('no2', '-')} · PM₂.₅ {stn.get('pm25', '-')} · O₃ {stn.get('o3', '-')}"
        )
        folium.CircleMarker(
            location=(stn["lat"], stn["lon"]),
            radius=10,
            color=col,
            weight=2,
            fill=True,
            fill_color=col,
            fill_opacity=0.55,
            tooltip=f"{stn.get('estacion', '-')} · AQI {aqi}",
            popup=folium.Popup(popup_html, max_width=280),
        ).add_to(fg_aqi)
    fg_aqi.add_to(fmap)

    folium.LayerControl(collapsed=False, position="topright").add_to(fmap)
    return fmap
