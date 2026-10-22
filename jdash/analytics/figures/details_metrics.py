"""Shared metric helpers for analytics dashboard figures."""

import logging
import math

import pandas as pd
import plotly.graph_objects as go
from django.utils.translation import gettext_lazy as _
from plotly.subplots import make_subplots

from jdash.utils.fileutils import parse_get_dashboard_csv

logger = logging.getLogger("django")


def _text(message):
    return str(_(message))


def _coverage_color(value):
    return "#87B5E2"


def _issue_color(value):
    return "#0d6efd"


def _empty_figure(message):
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        showarrow=False,
        font={"size": 15, "color": "#6c757d"},
    )
    fig.update_layout(
        template="plotly_white",
        height=260,
        margin={"l": 24, "r": 24, "t": 24, "b": 24},
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


def _subject_key(subject_name):
    value = str(subject_name or "").strip()
    return value[:-2] if len(value) > 2 else value


def _load_dashboard_data(study_name):
    if not study_name:
        return pd.DataFrame()

    try:
        return pd.DataFrame(parse_get_dashboard_csv(study_name))
    except Exception:
        logger.exception("details_metrics:: failed to load dashboard data for %s", study_name)
        return pd.DataFrame()


def _sensor_names(df):
    return sorted(
        column[: -len(" n_batches")]
        for column in df.columns
        if str(column).endswith(" n_batches")
    )


def _is_real_sensor_name(sensor):
    value = str(sensor or "").strip().lower()
    return value not in {"", "none", "nan", "null"}


def _dataframe_with_metrics(study_name):
    df = _load_dashboard_data(study_name)
    if df.empty:
        return df, [], 0

    sensors = [sensor for sensor in _sensor_names(df) if _is_real_sensor_name(sensor)]
    batch_columns = [f"{sensor} n_batches" for sensor in sensors]
    for column in batch_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    sensors = [sensor for sensor in sensors if df[f"{sensor} n_batches"].gt(0).any()]
    batch_columns = [f"{sensor} n_batches" for sensor in sensors]


    total_subjects = df["subject_name"].map(_subject_key).nunique() if "subject_name" in df.columns else 0

    return df, sensors, total_subjects


def _last_received_columns(df, sensors):
    sensor_columns = [f"{sensor} last_time_received" for sensor in sensors]
    available_sensor_columns = [column for column in sensor_columns if column in df.columns]
    legacy_columns = [
        column for column in df.columns
        if str(column).startswith("last_time_received_")
    ]
    return sorted(set(available_sensor_columns + legacy_columns))


def _subject_coverage_figure(df, sensors, total_subjects):
    subject_column = "subject_name" if "subject_name" in df.columns else None
    time_columns = _last_received_columns(df, sensors)
    if not subject_column or not time_columns:
        return _empty_figure(_text("No dashboard metrics available."))

    timestamp_df = df[[subject_column] + time_columns].copy()
    timestamp_df["subject_key"] = timestamp_df[subject_column].map(_subject_key)
    timestamp_df = timestamp_df[timestamp_df["subject_key"].astype(bool)]
    for column in time_columns:
        timestamp_df[column] = pd.to_datetime(timestamp_df[column], errors="coerce")

    timestamp_df["latest_received"] = timestamp_df[time_columns].max(axis=1)
    subject_latest = timestamp_df.groupby("subject_key", as_index=False)["latest_received"].max()
    subject_latest = subject_latest.dropna(subset=["latest_received"])
    if subject_latest.empty:
        return _empty_figure(_text("No dashboard metrics available."))

    latest_day = subject_latest["latest_received"].max().normalize()
    stale_cutoff = latest_day - pd.Timedelta(days=2)
    subject_latest["latest_day"] = subject_latest["latest_received"].dt.normalize()

    active_latest_day = int(subject_latest["latest_day"].eq(latest_day).sum())
    stale_subjects = int(
        subject_latest["latest_day"].isna().sum()
        + subject_latest["latest_day"].lt(stale_cutoff).sum()
    )
    denominator = max(total_subjects, 1)
    coverage_items = [
        (
            _text("Latest day"),
            active_latest_day,
            _coverage_color,
            [],
        ),
        (
            _text("No Data > 2 Days"),
            stale_subjects,
            _issue_color,
            [],
        ),
    ]

    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "indicator"}, {"type": "indicator"}]],
        horizontal_spacing=0.14,
    )
    for index, (label, subjects, color_fn, gauge_steps) in enumerate(coverage_items, start=1):
        coverage = round((subjects / denominator) * 100, 1)
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=coverage,
                number={"suffix": "%", "font": {"size": 28}},
                title={
                    "text": f"{label}<br><span style='font-size:0.78em;color:#6c757d'>{subjects}/{total_subjects} subjects</span>",
                    "font": {"size": 16},
                },
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "rgba(0,0,0,0)"},
                    "bar": {"color": color_fn(coverage), "thickness": 0.28},
                    "bgcolor": "#f1f3f5",
                    "borderwidth": 0,
                    "steps": gauge_steps,
                },
            ),
            row=1,
            col=index,
        )

    fig.add_annotation(
        text=f"{_text('Latest data day')}: {latest_day.date()}",
        x=0,
        y=1.02,
        xref="paper",
        yref="paper",
        showarrow=False,
        xanchor="left",
        font={"size": 12, "color": "#6c757d"},
    )
    fig.update_layout(
        template="plotly_white",
        height=340,
        margin={"l": 18, "r": 18, "t": 64, "b": 24},
        font={"family": "Arial, sans-serif", "size": 12},
        paper_bgcolor="#ffffff",
    )
    return fig


def _sensor_radial_figure(df, sensors, total_subjects):
    if not sensors:
        return _empty_figure(_text("No dashboard metrics available."))

    available_sensors = [sensor for sensor in sensors if f"{sensor} n_batches" in df.columns]
    if not available_sensors:
        return _empty_figure(_text("No dashboard metrics available."))

    cols = min(3, len(available_sensors))
    rows = math.ceil(len(available_sensors) / cols)
    specs = [[{"type": "indicator"} for _col in range(cols)] for _row in range(rows)]
    fig = make_subplots(
        rows=rows,
        cols=cols,
        specs=specs,
        horizontal_spacing=0.08,
        vertical_spacing=0.18,
    )

    denominator = max(total_subjects, 1)
    for index, sensor in enumerate(available_sensors):
        row = (index // cols) + 1
        col = (index % cols) + 1
        sensor_batches = pd.to_numeric(df[f"{sensor} n_batches"], errors="coerce").fillna(0)
        if "subject_name" in df.columns:
            sensor_df = pd.DataFrame(
                {
                    "subject_key": df["subject_name"].map(_subject_key),
                    "has_data": sensor_batches.gt(0),
                }
            )
            sensor_df = sensor_df[sensor_df["subject_key"].astype(bool)]
            count = int(sensor_df.groupby("subject_key")["has_data"].max().sum())
        else:
            count = int(sensor_batches.gt(0).sum())
        coverage = round((count / denominator) * 100, 1)
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=coverage,
                number={"suffix": "%", "font": {"size": 22}},
                title={
                    "text": f"{sensor}<br><span style='font-size:0.78em;color:#6c757d'>{count}/{total_subjects}</span>",
                    "font": {"size": 16},
                },
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "rgba(0,0,0,0)"},
                    "bar": {"color": _coverage_color(coverage), "thickness": 0.28},
                    "bgcolor": "#f1f3f5",
                    "borderwidth": 0,
                    "steps": [],
                },
            ),
            row=row,
            col=col,
        )

    fig.update_layout(
        template="plotly_white",
        height=max(340, rows * 240),
        margin={"l": 18, "r": 18, "t": 72, "b": 28},
        font={"family": "Arial, sans-serif", "size": 12},
        paper_bgcolor="#ffffff",
    )
    return fig
