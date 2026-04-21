from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import plotly.express as px


def build_timeline_df(shift_date: date, forecast: list[dict[str, Any]]) -> pd.DataFrame:
    """Segmentos horarios del turno con info de servicio y clima."""
    base = datetime.combine(shift_date, datetime.min.time())
    rows: list[dict[str, Any]] = []
    # 8 turnos de 2h entre 06:00 y 22:00 con 15 min de pausa al final.
    for turn in range(8):
        start = base + timedelta(hours=6 + 2 * turn)
        service_end = start + timedelta(hours=1, minutes=45)
        break_end = start + timedelta(hours=2)
        hour_weather = forecast[start.hour] if forecast else {}
        label = (
            f"Turno {turn + 1} — {hour_weather.get('condition', 'n/d')} "
            f"{hour_weather.get('temp_c', '')}ºC"
        )
        rows.append(
            {
                "Inicio": start,
                "Fin": service_end,
                "Tramo": label,
                "Tipo": "Servicio",
            }
        )
        rows.append(
            {
                "Inicio": service_end,
                "Fin": break_end,
                "Tramo": f"Pausa turno {turn + 1}",
                "Tipo": "Pausa",
            }
        )
    return pd.DataFrame(rows)


def render_timeline_figure(df: pd.DataFrame):
    fig = px.timeline(
        df,
        x_start="Inicio",
        x_end="Fin",
        y="Tipo",
        color="Tipo",
        hover_name="Tramo",
        color_discrete_map={"Servicio": "#2E86AB", "Pausa": "#F6AE2D"},
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        height=260,
        showlegend=True,
        xaxis_title=None,
        yaxis_title=None,
    )
    return fig
