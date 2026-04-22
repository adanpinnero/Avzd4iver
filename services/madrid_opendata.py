"""Cliente open data Ayuntamiento de Madrid.

Fuentes reales:
- Obras e incidencias en vías:
  https://datos.madrid.es/egob/catalogo/208627-0-transporte-incidencias-obras.json
- Calidad del aire tiempo real (CSV horario):
  https://datos.madrid.es/egob/catalogo/212531-10515086-calidad-aire-tiempo-real.csv
- Estaciones calidad aire (catálogo):
  https://datos.madrid.es/egob/catalogo/300199-0-calidad-aire-estaciones.csv

Todas las funciones caen a mock determinista si la red falla.
"""

from __future__ import annotations

import csv
import io
import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta

ROAD_WORKS_URL = (
    "https://datos.madrid.es/egob/catalogo/"
    "208627-0-transporte-incidencias-obras.json"
)
AIR_QUALITY_CSV = (
    "https://datos.madrid.es/egob/catalogo/"
    "212531-10515086-calidad-aire-tiempo-real.csv"
)
TIMEOUT = 3.0
USER_AGENT = "AvzdFleet/1.0 (+demo)"

# Coordenadas conocidas de estaciones Madrid (subconjunto principal).
# Fuente: catálogo open data (estaciones 4, 8, 35, 36, 38, 39, 48, 49, 50, 54, 56, 57, 58, 59, 60).
_STATIONS: dict[str, tuple[str, float, float]] = {
    "04": ("Plaza de España", 40.4238, -3.7122),
    "08": ("Escuelas Aguirre", 40.4218, -3.6824),
    "11": ("Avda. Ramón y Cajal", 40.4513, -3.6773),
    "16": ("Arturo Soria", 40.4402, -3.6392),
    "17": ("Villaverde", 40.3470, -3.7134),
    "18": ("Farolillo", 40.3948, -3.7318),
    "24": ("Casa de Campo", 40.4193, -3.7475),
    "27": ("Barajas Pueblo", 40.4769, -3.5800),
    "35": ("Pza. del Carmen", 40.4192, -3.7031),
    "36": ("Moratalaz", 40.4078, -3.6451),
    "38": ("Cuatro Caminos", 40.4455, -3.7077),
    "39": ("Barrio del Pilar", 40.4783, -3.7114),
    "40": ("Vallecas", 40.3881, -3.6517),
    "47": ("Méndez Álvaro", 40.3981, -3.6866),
    "48": ("Pº. Castellana", 40.4394, -3.6897),
    "49": ("Retiro", 40.4144, -3.6825),
    "50": ("Pza. Castilla", 40.4653, -3.6895),
    "54": ("Ensanche Vallecas", 40.3730, -3.6120),
    "55": ("Urb. Embajada", 40.4622, -3.5805),
    "56": ("Pza. Elíptica", 40.3850, -3.7183),
    "57": ("Sanchinarro", 40.4938, -3.6603),
    "58": ("El Pardo", 40.5180, -3.7745),
    "59": ("Juan Carlos I", 40.4656, -3.6160),
    "60": ("Tres Olivos", 40.5005, -3.6897),
}


def fetch_road_works(timeout: float = TIMEOUT) -> list[dict]:
    """Devuelve obras/incidencias viales vigentes en Madrid.

    Formato de cada item::

        {
            "id": str, "lat": float, "lon": float,
            "titulo": str, "distrito": str,
            "fecha_inicio": datetime|None, "fecha_fin": datetime|None,
            "severity": "alta"|"media"|"baja",
            "source": "madrid-obras",
        }
    """
    try:
        req = urllib.request.Request(ROAD_WORKS_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        data = json.loads(raw.decode("utf-8"))
        return _parse_road_works(data)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return _mock_road_works()


def _parse_road_works(data: dict) -> list[dict]:
    out: list[dict] = []
    items = data.get("@graph") or data.get("graph") or data.get("items") or []
    for i, it in enumerate(items):
        loc = it.get("location") or it.get("geo") or {}
        try:
            lat = float(loc.get("latitude") or it.get("latitud") or 0)
            lon = float(loc.get("longitude") or it.get("longitud") or 0)
        except (TypeError, ValueError):
            continue
        if lat == 0 or lon == 0:
            continue
        titulo = it.get("title") or it.get("titulo") or it.get("nombre") or "Obra"
        distrito = (
            it.get("address", {}).get("district", {}).get("@id", "")
            or it.get("distrito", "")
            or ""
        ).rsplit("/", 1)[-1] or "Madrid"
        start = _parse_iso(it.get("dtstart") or it.get("fecha_inicio"))
        end = _parse_iso(it.get("dtend") or it.get("fecha_fin"))
        out.append(
            {
                "id": str(it.get("id") or i),
                "lat": lat,
                "lon": lon,
                "titulo": titulo,
                "distrito": distrito,
                "fecha_inicio": start,
                "fecha_fin": end,
                "severity": _severity_for_work(titulo),
                "source": "madrid-obras",
            }
        )
    return out


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _severity_for_work(titulo: str) -> str:
    t = titulo.lower()
    if any(k in t for k in ("corte total", "cerrado", "desvío", "emergencia")):
        return "alta"
    if any(k in t for k in ("corte parcial", "ocupación", "estrechamiento")):
        return "media"
    return "baja"


def fetch_air_quality(timeout: float = TIMEOUT) -> list[dict]:
    """Estaciones de calidad del aire de Madrid con NO2 / PM2.5 / O3.

    Item: {estacion, lat, lon, no2, pm25, o3, aqi, aqi_label, ts}.
    """
    try:
        req = urllib.request.Request(AIR_QUALITY_CSV, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return _parse_air_quality(raw.decode("utf-8", errors="ignore"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return _mock_air_quality()


def _parse_air_quality(csv_text: str) -> list[dict]:
    """Parsea CSV horario EGM (formato largo: una fila por estación+magnitud+día)."""
    rows: dict[str, dict] = {}
    reader = csv.DictReader(io.StringIO(csv_text), delimiter=";")
    # Magnitudes: 8=NO2, 9=PM2.5, 14=O3 (códigos oficiales Ayto Madrid).
    mag_map = {"08": "no2", "09": "pm25", "14": "o3"}
    for r in reader:
        est_key = (r.get("ESTACION") or r.get("estacion") or "").zfill(3)[-3:]
        if not est_key:
            continue
        mag = mag_map.get((r.get("MAGNITUD") or r.get("magnitud") or "").zfill(2))
        if not mag:
            continue
        # Busca la última hora válida del día (V24..V01).
        last_val: float | None = None
        for h in range(24, 0, -1):
            key_v = f"V{h:02d}"
            key_h = f"H{h:02d}"
            if r.get(key_v) == "V":
                try:
                    last_val = float((r.get(key_h) or "0").replace(",", "."))
                    break
                except ValueError:
                    continue
        if last_val is None:
            continue
        row = rows.setdefault(est_key, {"estacion_id": est_key})
        row[mag] = last_val

    out: list[dict] = []
    now = datetime.utcnow()
    for est_key, vals in rows.items():
        meta = _STATIONS.get(est_key)
        if not meta:
            continue
        name, lat, lon = meta
        no2 = vals.get("no2")
        pm25 = vals.get("pm25")
        o3 = vals.get("o3")
        aqi, lbl = _aqi_from(no2, pm25, o3)
        out.append(
            {
                "estacion_id": est_key,
                "estacion": name,
                "lat": lat,
                "lon": lon,
                "no2": no2,
                "pm25": pm25,
                "o3": o3,
                "aqi": aqi,
                "aqi_label": lbl,
                "ts": now,
                "source": "madrid-aire",
            }
        )
    return out or _mock_air_quality()


def _aqi_from(no2: float | None, pm25: float | None, o3: float | None) -> tuple[int, str]:
    """Aproxima el AQI europeo (0=bueno, 100=peligroso) con las 3 variables."""

    def _score(val: float | None, thresholds: tuple[float, float, float, float]) -> int:
        if val is None:
            return 0
        t1, t2, t3, t4 = thresholds
        if val < t1:
            return 20
        if val < t2:
            return 40
        if val < t3:
            return 60
        if val < t4:
            return 80
        return 100

    # Umbrales (μg/m³) basados en CAQI europeo.
    score = max(
        _score(no2, (40, 100, 200, 400)),
        _score(pm25, (15, 30, 55, 110)),
        _score(o3, (60, 120, 180, 240)),
    )
    labels = {20: "muy buena", 40: "buena", 60: "regular", 80: "mala", 100: "muy mala"}
    return score, labels[score]


# ─── Mocks deterministas ──────────────────────────────────────────────────


def _mock_road_works() -> list[dict]:
    now = datetime.utcnow()
    samples = [
        ("Corte parcial en Gran Vía por rodaje publicitario",
         40.4200, -3.7053, "Centro", "media", 6),
        ("Obra reposición asfalto calle Alcalá (entre Cibeles y Sevilla)",
         40.4193, -3.6950, "Centro", "media", 72),
        ("Cerrado carril bici Paseo Castellana por mantenimiento",
         40.4440, -3.6900, "Chamartín", "baja", 24),
        ("Desvío temporal autobuses en Plaza Castilla por evento deportivo",
         40.4672, -3.6892, "Chamartín", "alta", 5),
        ("Ocupación acera Princesa 23 por mudanza industrial",
         40.4314, -3.7182, "Moncloa", "baja", 12),
        ("Estrechamiento calzada M-30 km 2 sentido sur",
         40.4461, -3.6925, "Chamberí", "media", 48),
        ("Obra pluviales calle Embajadores tramo 45-60",
         40.4049, -3.7063, "Arganzuela", "media", 168),
        ("Corte total rotonda Atocha por prueba carga",
         40.4074, -3.6916, "Retiro", "alta", 4),
    ]
    out: list[dict] = []
    for i, (tit, lat, lon, distrito, sev, hrs) in enumerate(samples):
        out.append(
            {
                "id": f"mo-{i}",
                "lat": lat,
                "lon": lon,
                "titulo": tit,
                "distrito": distrito,
                "fecha_inicio": now - timedelta(hours=hrs // 2),
                "fecha_fin": now + timedelta(hours=hrs),
                "severity": sev,
                "source": "madrid-obras-mock",
            }
        )
    return out


def _mock_air_quality() -> list[dict]:
    """Snapshot verosímil de 10 estaciones con NO2/PM2.5/O3."""
    now = datetime.utcnow()
    samples = [
        ("04", 42.0, 14.0, 65.0),
        ("08", 55.0, 18.0, 48.0),
        ("11", 38.0, 12.0, 72.0),
        ("24", 22.0, 9.0, 88.0),
        ("35", 48.0, 16.0, 55.0),
        ("38", 52.0, 17.0, 50.0),
        ("39", 35.0, 11.0, 78.0),
        ("47", 58.0, 19.0, 44.0),
        ("48", 50.0, 16.0, 58.0),
        ("49", 28.0, 10.0, 82.0),
        ("50", 45.0, 14.0, 62.0),
        ("56", 62.0, 22.0, 42.0),
    ]
    out: list[dict] = []
    for est_key, no2, pm25, o3 in samples:
        meta = _STATIONS.get(est_key)
        if not meta:
            continue
        name, lat, lon = meta
        aqi, lbl = _aqi_from(no2, pm25, o3)
        out.append(
            {
                "estacion_id": est_key,
                "estacion": name,
                "lat": lat,
                "lon": lon,
                "no2": no2,
                "pm25": pm25,
                "o3": o3,
                "aqi": aqi,
                "aqi_label": lbl,
                "ts": now,
                "source": "madrid-aire-mock",
            }
        )
    return out
