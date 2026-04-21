from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from fpdf import FPDF

if TYPE_CHECKING:
    from services.plan_builder import RoutePlan


def _safe(text: str) -> str:
    """fpdf2 con fuente core (Helvetica) solo soporta Latin-1."""
    return text.encode("latin-1", "replace").decode("latin-1")


def render_plan_pdf(plan: "RoutePlan") -> bytes:
    pdf = FPDF(format="A4", unit="mm")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _safe("Plan de ruta diario"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, _safe(f"Fecha: {plan.shift_date.strftime('%d/%m/%Y')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, _safe(f"Conductor: {plan.driver.full_name}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, _safe(f"Autobús: {plan.bus.plate} — {plan.bus.model} ({plan.bus.type})"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, _safe(f"Línea: {plan.line.code} — {plan.line.name}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, _safe(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _safe("Resumen meteorológico"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    ws = plan.weather_summary
    pdf.multi_cell(
        0,
        5,
        _safe(
            f"Temperatura: {ws.get('min_temp', '?')}ºC a {ws.get('max_temp', '?')}ºC | "
            f"Lluvia acumulada: {ws.get('total_rain_mm', 0)} mm | "
            f"Condiciones: {ws.get('conditions', '-')}"
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _safe("Alertas"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    if not plan.alerts:
        pdf.cell(0, 5, _safe("Sin alertas relevantes."), new_x="LMARGIN", new_y="NEXT")
    else:
        for alert in plan.alerts:
            prefix = {"error": "[!]", "warning": "[*]", "info": "[i]"}.get(
                alert["severity"], "[-]"
            )
            pdf.multi_cell(
                0,
                5,
                _safe(f"{prefix} {alert['message']}"),
                new_x="LMARGIN",
                new_y="NEXT",
            )
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _safe("Paradas clave"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for stop in plan.stops:
        pdf.cell(
            0,
            5,
            _safe(f"- {stop['name']}  ({stop['lat']:.4f}, {stop['lon']:.4f})"),
            new_x="LMARGIN",
            new_y="NEXT",
        )
    pdf.ln(2)

    if plan.events:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, _safe("Eventos en la ciudad"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for ev in plan.events:
            pdf.multi_cell(
                0,
                5,
                _safe(f"- {ev['name']} @ {ev['venue']} ({ev['start']}-{ev['end']})"),
                new_x="LMARGIN",
                new_y="NEXT",
            )

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)
