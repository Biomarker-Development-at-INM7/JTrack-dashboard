"""Figures and downloads for bounded subject raw-data previews."""

from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
from django.utils.translation import gettext_lazy as _

from .common_figures import blank_quality_figure, finish_quality_figure


SOURCE_COLORS = {
    "smartphone": "#087f8c",
    "wearable": "#3569a8",
    "ema": "#c06c31",
}


def _daily_plot_points(payload):
    """Insert empty daily slots so missing study days remain visible."""
    points = payload.get("points", [])
    if payload.get("resolution") != "day" or not payload.get("start") or not payload.get("end"):
        return points
    try:
        joined_value = payload.get("joined_at")
        joined_date = (
            datetime.fromisoformat(str(joined_value).replace("Z", "+00:00")).date()
            if joined_value
            else date.fromisoformat(payload["start"])
        )
        dates = pd.date_range(payload["start"], payload["end"], freq="D")
    except (TypeError, ValueError):
        return points

    points_by_date = {point.get("date"): point for point in points}
    return [
        points_by_date.get(day.date().isoformat())
        or {
            "timestamp": day.date().isoformat(),
            "date": day.date().isoformat(),
            "study_day": (day.date() - joined_date).days,
            "study_day_position": float((day.date() - joined_date).days),
            "value": None,
            "records": 0,
        }
        for day in dates
    ]


def raw_series_frame(payload, timeline_axis="study_day"):
    points = payload.get("points", []) if isinstance(payload, dict) else []
    if not points:
        return pd.DataFrame(
            columns=[
                "Subject_ID",
                "Sensor",
                "Metric",
                "Statistic",
                "Resolution",
                "Date",
                "Study_day",
                "Timestamp_UTC",
                "Value",
                "Records",
            ]
        )
    rows = []
    for point in points:
        rows.append(
            {
                "Subject_ID": payload.get("subject_id"),
                "Sensor": payload.get("sensor"),
                "Metric": payload.get("metric"),
                "Statistic": payload.get("statistic"),
                "Resolution": payload.get("resolution"),
                "Date": point.get("date"),
                "Study_day": point.get("study_day"),
                "Timestamp_UTC": point.get("timestamp"),
                "Value": point.get("value"),
                "Records": point.get("records"),
            }
        )
    return pd.DataFrame(rows)


def build_raw_subject_figure(payload, timeline_axis="study_day"):
    if not isinstance(payload, dict):
        return blank_quality_figure(
            "",
            str(_("No raw data is available for this selection.")),
        )
    if not payload.get("points"):
        preview = payload.get("preview") or {}
        message = str(_("No raw data is available for this selection."))
        if preview.get("skipped_large_or_invalid_files"):
            message = str(_("The available files could not be included in the preview."))
        return blank_quality_figure("", message)

    points = _daily_plot_points(payload)
    use_study_day = timeline_axis == "study_day" and any(
        point.get("study_day_position") is not None for point in points
    )
    x_values = [
        point.get("study_day_position") if use_study_day else point.get("timestamp")
        for point in points
    ]
    y_values = [point.get("value") for point in points]
    custom_data = [
        [point.get("date"), point.get("study_day"), point.get("records")]
        for point in points
    ]
    color = SOURCE_COLORS.get(payload.get("source"), "#087f8c")
    is_activity_count = (
        payload.get("statistic") == "count"
        or payload.get("source") == "ema"
        or payload.get("metric") in {
            "records",
            "events",
            "responses",
            "submissions",
        }
    )
    value_label = str(payload.get("metric_label") or _("Value"))
    is_record_count = payload.get("statistic") == "count" and payload.get("metric") not in {
        "records",
        "events",
        "responses",
        "submissions",
    }
    if is_record_count:
        value_label = str(_("Records"))
    value_hover = "%{y:,.0f}" if is_activity_count else "%{y:,.2f}"
    hover_template = (
        "Date: %{customdata[0]}<br>"
        "Study day: %{customdata[1]}<br>"
        f"{value_label}: {value_hover}<br>"
        "Records: %{customdata[2]}<extra></extra>"
    )

    if is_activity_count:
        trace = go.Bar(
            x=x_values,
            y=y_values,
            marker_color=color,
            customdata=custom_data,
            hovertemplate=hover_template,
            name=str(payload.get("metric_label") or _("Value")),
        )
    else:
        trace = go.Scatter(
            x=x_values,
            y=y_values,
            mode="lines+markers",
            line={"color": color, "width": 2},
            marker={"color": color, "size": 6},
            customdata=custom_data,
            hovertemplate=hover_template,
            name=str(payload.get("metric_label") or _("Value")),
        )

    figure = go.Figure(trace)
    unit = None if is_record_count else payload.get("unit")
    y_title = value_label
    if unit:
        y_title = f"{y_title} ({unit})"
    figure.update_xaxes(title=str(_("Study day")) if use_study_day else str(_("Date")))
    range_start = payload.get("start")
    range_end = payload.get("end")
    if use_study_day and range_start and range_end:
        try:
            joined_value = payload.get("joined_at")
            joined_date = (
                datetime.fromisoformat(str(joined_value).replace("Z", "+00:00")).date()
                if joined_value
                else date.fromisoformat(range_start)
            )
            first_study_day = (date.fromisoformat(range_start) - joined_date).days
            last_study_day = (date.fromisoformat(range_end) - joined_date).days
            figure.update_xaxes(
                range=[first_study_day - 0.5, last_study_day + 0.5],
                dtick=1,
            )
        except (TypeError, ValueError):
            pass
    elif not use_study_day and range_start and range_end:
        figure.update_xaxes(range=[range_start, range_end])
    figure.update_yaxes(title=y_title, rangemode="tozero" if is_activity_count else "normal")

    preview = payload.get("preview") or {}
    notes = []
    if preview.get("files_sampled"):
        notes.append(
            str(_("Preview uses %(used)s of %(total)s files."))
            % {
                "used": preview.get("files_read", 0),
                "total": preview.get("matching_files", 0),
            }
        )
    if preview.get("record_limit_reached"):
        notes.append(str(_("The preview record limit was reached.")))
    if preview.get("skipped_large_or_invalid_files"):
        notes.append(
            str(_("Some large or invalid files were skipped."))
        )
    if notes:
        figure.add_annotation(
            text=" ".join(notes),
            x=0,
            y=1.08,
            xref="paper",
            yref="paper",
            xanchor="left",
            showarrow=False,
            font={"size": 11, "color": "#667085"},
        )

    figure.update_layout(hovermode="x unified", showlegend=False)
    return finish_quality_figure(figure)
