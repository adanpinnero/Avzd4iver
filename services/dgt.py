"""Cliente DGT (Dirección General de Tráfico).

Fuentes reales:
- DATEX2 incidencias tiempo real:
  https://infocar.dgt.es/datex2/dgt/SituationPublication/all/contenido.xml
- Puntos negros anuales (dataset estático, snapshot en data/).

Diseñado para funcionar offline: cualquier fallo de red / parseo cae a un
mock determinista para Madrid.
"""

from __future__ import annotations

import csv
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

DATEX2_URL = (
    "https://infocar.dgt.es/datex2/dgt/SituationPublication/all/contenido.xml"
)
TIMEOUT = 3.0
USER_AGENT = "AvzdFleet/1.0 (+demo)"

# (min_lat, min_lon, max_lat, max_lon) — provincia de Madrid + accesos A1-A6, M30/M40/M45
MADRID_BBOX: tuple[float, float, float, float] = (40.20, -4.00, 40.70, -3.40)

_NS = {"d": "http://datex2.eu/schema/2/2_0"}

# Ruta al dataset estático de puntos negros (snapshot open data DGT).
_PUNTOS_NEGROS_CSV = Path(__file__).resolve().parent.parent / "data" / "dgt_puntos_negros_madrid.csv"


def _in_bbox(lat: float, lon: float, bbox: tuple[float, float, float, float]) -> bool:
    min_lat, min_lon, max_lat, max_lon = bbox
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def fetch_incidents(
    bbox: tuple[float, float, float, float] = MADRID_BBOX,
    timeout: float = TIMEOUT,
) -> list[dict]:
    """Devuelve incidencias DGT activas dentro de `bbox`.

    Formato de cada item::

        {
            "id": str, "lat": float, "lon": float,
            "severity": "alta"|"media"|"baja",
            "tipo": str,         # accidente|obra|retencion|meteo|otros
            "descripcion": str,
            "carretera": str, "pk": str,
            "start": datetime|None, "end": datetime|None,
            "source": "dgt",
        }

    Fallback mock si la red falla o el XML no se puede parsear.
    """
    try:
        req = urllib.request.Request(DATEX2_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return _parse_datex2(raw, bbox)
    except (urllib.error.URLError, TimeoutError, OSError, ET.ParseError, ValueError):
        return _mock_incidents(bbox)


def _parse_datex2(xml_bytes: bytes, bbox: tuple[float, float, float, float]) -> list[dict]:
    """Extrae situaciones con coords Lat/Lon y metadatos."""
    root = ET.fromstring(xml_bytes)
    out: list[dict] = []
    for sit in root.iter(f"{{{_NS['d']}}}situation"):
        sid = sit.get("id") or ""
        for rec in sit.iter(f"{{{_NS['d']}}}situationRecord"):
            lat_el = rec.find(".//d:latitude", _NS)
            lon_el = rec.find(".//d:longitude", _NS)
            if lat_el is None or lon_el is None:
                continue
            try:
                lat = float(lat_el.text)
                lon = float(lon_el.text)
            except (TypeError, ValueError):
                continue
            if not _in_bbox(lat, lon, bbox):
                continue
            probability = (rec.findtext("d:probabilityOfOccurrence", default="", namespaces=_NS) or "").lower()
            severity_raw = (rec.findtext("d:severity", default="", namespaces=_NS) or "").lower()
            start = _parse_ts(rec.findtext("d:validity/d:validityTimeSpecification/d:overallStartTime", default=None, namespaces=_NS))
            end = _parse_ts(rec.findtext("d:validity/d:validityTimeSpecification/d:overallEndTime", default=None, namespaces=_NS))
            comment = (
                rec.findtext(".//d:generalPublicComment//d:value", default="", namespaces=_NS)
                or rec.findtext(".//d:comment//d:value", default="", namespaces=_NS)
                or ""
            ).strip()
            tipo_tag = rec.tag.rsplit("}", 1)[-1]
            tipo = _classify(tipo_tag, comment)
            severity = _severity_from(severity_raw, probability, tipo)
            road = rec.findtext(".//d:roadNumber", default="", namespaces=_NS) or ""
            pk = rec.findtext(".//d:distanceAlong", default="", namespaces=_NS) or ""
            out.append(
                {
                    "id": f"{sid}-{rec.get('id', len(out))}",
                    "lat": lat,
                    "lon": lon,
                    "severity": severity,
                    "tipo": tipo,
                    "descripcion": comment or f"{tipo} DGT",
                    "carretera": road,
                    "pk": pk,
                    "start": start,
                    "end": end,
                    "source": "dgt",
                }
            )
    return out


def _parse_ts(txt: str | None) -> datetime | None:
    if not txt:
        return None
    try:
        # DATEX2 usa ISO 8601 con Z.
        return datetime.fromisoformat(txt.replace("Z", "+00:00"))
    except ValueError:
        return None


def _classify(tag: str, comment: str) -> str:
    t = (tag + " " + comment).lower()
    if any(k in t for k in ("accident", "accidente", "colision", "atropello")):
        return "accidente"
    if any(k in t for k in ("roadwork", "obra", "mantenimient", "corte")):
        return "obra"
    if any(k in t for k in ("abnormaltraffic", "conges", "retenci", "atasco", "trafico lento")):
        return "retencion"
    if any(k in t for k in ("weather", "lluvia", "nieve", "niebla", "hielo", "viento")):
        return "meteo"
    return "otros"


def _severity_from(sev: str, prob: str, tipo: str) -> str:
    if sev in ("high", "highest", "serious"):
        return "alta"
    if sev in ("low", "lowest"):
        return "baja"
    if tipo == "accidente":
        return "alta"
    if tipo == "retencion" and prob in ("certain", "probable"):
        return "media"
    return "media"


def load_puntos_negros() -> list[dict]:
    """Carga el snapshot CSV de puntos negros DGT Madrid.

    Columnas: lat, lon, carretera, pk, accidentes_5y, concentracion ('alta'|'media'|'baja').
    """
    if not _PUNTOS_NEGROS_CSV.exists():
        return _mock_puntos_negros()
    try:
        rows: list[dict] = []
        with _PUNTOS_NEGROS_CSV.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                rows.append(
                    {
                        "lat": float(r["lat"]),
                        "lon": float(r["lon"]),
                        "carretera": r.get("carretera", ""),
                        "pk": r.get("pk", ""),
                        "accidentes_5y": int(r.get("accidentes_5y", 0) or 0),
                        "concentracion": r.get("concentracion", "media"),
                        "source": "dgt",
                    }
                )
        return rows
    except (OSError, ValueError, KeyError):
        return _mock_puntos_negros()


# ─── Mocks deterministas ──────────────────────────────────────────────────


def _mock_incidents(bbox: tuple[float, float, float, float]) -> list[dict]:
    """Incidencias verosímiles distribuidas por Madrid. Determinista."""
    now = datetime.utcnow()
    base = [
        ("A-1 km 14", 40.4832, -3.6672, "alta", "accidente",
         "Colisión por alcance carril derecho — vehículo averiado retirándose"),
        ("M-30 salida 15 (Costa Rica)", 40.4538, -3.6812, "media", "retencion",
         "Retención de 1.2 km sentido norte por densidad de tráfico"),
        ("A-2 km 8 (Canillejas)", 40.4550, -3.6115, "media", "obra",
         "Obra de repavimentación — carril derecho cortado"),
        ("M-40 km 32 (Coslada)", 40.4208, -3.5650, "baja", "meteo",
         "Niebla baja intermitente — velocidad reducida recomendada"),
        ("A-5 km 10 (Alcorcón)", 40.3487, -3.8165, "alta", "accidente",
         "Accidente con salida de vía, presencia de Guardia Civil"),
        ("A-6 km 7 (Pozuelo)", 40.4370, -3.7980, "media", "retencion",
         "Retención 800 m sentido entrada — hora punta"),
        ("M-45 km 4 (Vallecas)", 40.3752, -3.6245, "baja", "obra",
         "Señalización provisional por mantenimiento nocturno"),
    ]
    out: list[dict] = []
    for i, (road, lat, lon, sev, tipo, desc) in enumerate(base):
        if not _in_bbox(lat, lon, bbox):
            continue
        out.append(
            {
                "id": f"mock-{i}",
                "lat": lat,
                "lon": lon,
                "severity": sev,
                "tipo": tipo,
                "descripcion": desc,
                "carretera": road.split(" ", 1)[0],
                "pk": road.split("km ", 1)[1].split(" ")[0] if "km " in road else "",
                "start": now - timedelta(minutes=15 + i * 10),
                "end": now + timedelta(hours=2),
                "source": "dgt-mock",
            }
        )
    return out


def _mock_puntos_negros() -> list[dict]:
    """Puntos negros sintéticos en Madrid (fallback si CSV no existe)."""
    return [
        {"lat": 40.4461, "lon": -3.6925, "carretera": "M-30", "pk": "2",
         "accidentes_5y": 38, "concentracion": "alta", "source": "dgt-mock"},
        {"lat": 40.4074, "lon": -3.6916, "carretera": "M-30", "pk": "6",
         "accidentes_5y": 27, "concentracion": "alta", "source": "dgt-mock"},
        {"lat": 40.4321, "lon": -3.6626, "carretera": "A-2", "pk": "4",
         "accidentes_5y": 22, "concentracion": "media", "source": "dgt-mock"},
        {"lat": 40.4832, "lon": -3.6672, "carretera": "A-1", "pk": "14",
         "accidentes_5y": 19, "concentracion": "media", "source": "dgt-mock"},
    ]
