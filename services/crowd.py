from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

from sqlmodel import select

from db.models import CrowdReport, Line, User
from db.session import get_session


# TTL por categoría en minutos (cuánto tiempo es relevante un reporte fresco).
TTL_MIN: dict[str, int] = {
    "aggression": 120,
    "accident": 180,
    "protest": 240,
    "jam": 30,
    "obstacle": 60,
    "bump": 4320,          # bache: 72h
    "construction": 4320,
}

DEFAULT_SEVERITY: dict[str, str] = {
    "aggression": "alta",
    "accident": "alta",
    "protest": "media",
    "jam": "media",
    "obstacle": "media",
    "bump": "baja",
    "construction": "baja",
}

LABELS_ES: dict[str, str] = {
    "aggression": "Agresión / incidente",
    "accident": "Accidente",
    "protest": "Manifestación",
    "jam": "Atasco",
    "obstacle": "Obstáculo en vía",
    "bump": "Bache",
    "construction": "Obra",
}

COLOR: dict[str, str] = {
    "aggression": "red",
    "accident": "red",
    "protest": "purple",
    "jam": "orange",
    "obstacle": "orange",
    "bump": "beige",
    "construction": "lightgray",
}

VALID_CATEGORIES = set(TTL_MIN.keys())


def ttl_for(category: str) -> int:
    return TTL_MIN.get(category, 60)


def severity_for(category: str) -> str:
    return DEFAULT_SEVERITY.get(category, "media")


def label_for(category: str) -> str:
    return LABELS_ES.get(category, category)


def color_for(category: str) -> str:
    return COLOR.get(category, "blue")


def submit_report(
    reporter_id: int,
    category: str,
    lat: float,
    lon: float,
    line_id: int | None = None,
    note: str | None = None,
    severity: str | None = None,
) -> CrowdReport:
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Categoría inválida: {category}")
    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=ttl_for(category))
    report = CrowdReport(
        reporter_id=reporter_id,
        line_id=line_id,
        category=category,
        lat=lat,
        lon=lon,
        note=note,
        severity=severity or severity_for(category),
        created_at=now,
        expires_at=expires_at,
    )
    with get_session() as s:
        s.add(report)
        s.commit()
        s.refresh(report)
    return report


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def active_reports(now: datetime | None = None) -> list[CrowdReport]:
    now = now or datetime.utcnow()
    with get_session() as s:
        rows = s.exec(
            select(CrowdReport)
            .where(CrowdReport.status == "active")
            .where(CrowdReport.expires_at >= now)
        ).all()
    return list(rows)


def nearby(center: tuple[float, float], radius_m: float = 2000.0) -> list[dict[str, Any]]:
    """Reportes activos a menos de `radius_m` metros de `center`, ordenados por severidad y distancia."""
    reports = active_reports()
    with get_session() as s:
        users = {u.id: u.full_name for u in s.exec(select(User)).all()}
        lines = {ln.id: ln.code for ln in s.exec(select(Line)).all()}
    out: list[dict[str, Any]] = []
    for r in reports:
        dist = _haversine_m(center, (r.lat, r.lon))
        if dist > radius_m:
            continue
        out.append(
            {
                "id": r.id,
                "category": r.category,
                "label": label_for(r.category),
                "lat": r.lat,
                "lon": r.lon,
                "severity": r.severity,
                "note": r.note or "",
                "created_at": r.created_at,
                "expires_at": r.expires_at,
                "confirmations": r.confirmations,
                "downvotes": r.downvotes,
                "reporter": users.get(r.reporter_id, "—"),
                "line": lines.get(r.line_id, "—"),
                "distance_m": round(dist),
            }
        )
    severity_rank = {"alta": 0, "media": 1, "baja": 2}
    out.sort(key=lambda r: (severity_rank.get(r["severity"], 3), r["distance_m"]))
    return out


def confirm(report_id: int, confirm_: bool) -> None:
    """+1 confirmación o +1 downvote. Si downvotes > confirmations+1, se marca dismissed."""
    with get_session() as s:
        row = s.get(CrowdReport, report_id)
        if row is None:
            return
        if confirm_:
            row.confirmations += 1
            # confirmar eleva severidad a alta si está con 2+ confirmaciones
            if row.confirmations >= 2 and row.severity == "baja":
                row.severity = "media"
            if row.confirmations >= 3 and row.severity == "media":
                row.severity = "alta"
        else:
            row.downvotes += 1
            if row.downvotes > row.confirmations + 1:
                row.status = "dismissed"
        s.add(row)
        s.commit()


def expire_old() -> int:
    """Marca como 'expired' los reportes vencidos. Devuelve nº cambiados."""
    now = datetime.utcnow()
    changed = 0
    with get_session() as s:
        rows = s.exec(
            select(CrowdReport)
            .where(CrowdReport.status == "active")
            .where(CrowdReport.expires_at < now)
        ).all()
        for r in rows:
            r.status = "expired"
            s.add(r)
            changed += 1
        if changed:
            s.commit()
    return changed
