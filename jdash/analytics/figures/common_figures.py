"""Shared helpers for analytics figures."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from django.utils.translation import gettext_lazy as _

from ..data.dashboard_data import first_matching_column


def status_color(value):
    status = str(value).lower()
    if status in ("healthy", "ok", "pass", "good"):
        return "#198754"
    if status in ("watch", "warning"):
        return "#ffc107"
    if status in ("critical", "fail", "error"):
        return "#dc3545"
    return "#6c757d"

def status_alert_color(value):
    status = str(value).lower()
    if status in ("healthy", "ok", "pass", "good"):
        return "success"
    if status in ("watch", "warning"):
        return "warning"
    if status in ("critical", "fail", "error"):
        return "danger"
    return "secondary"

def issue_status(value):
    value = pd.to_numeric(value, errors="coerce")
    if pd.isna(value):
        return "critical"
    if value <= 10:
        return "healthy"
    if value <= 25:
        return "warning"
    return "critical"

def blank_quality_figure(title, message="No data available."):
    fig = go.Figure()
    fig.add_annotation(
        text=str(message),
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 14, "color": "#6c757d"},
    )
    fig.update_layout(
        title=None,
        template="simple_white",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig

def finish_quality_figure(fig):
    fig.update_layout(
        title=None,
        template="simple_white",
        margin=dict(l=20, r=20, t=20, b=35),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig

def add_coverage_percent_column(df):
    coverage_col = first_matching_column(
        df.columns,
        [
            "Coverage_percent",
            "coverage_percent",
            "Availability_percent",
            "Adherence_percent",
        ],
    )
    if not coverage_col:
        return df

    coverage_df = df.copy()
    coverage_df["Coverage_percent"] = coverage_df[coverage_col]
    return coverage_df

def add_missing_percent_column(df):
    missing_col = first_matching_column(
        df.columns,
        [
            "Missing_percent",
            "missing_percent",
            "Technical_missing_percent",
            "Technical_missing_percentage",
            "Missingness_percent",
        ],
    )
    if missing_col:
        missing_df = df.copy()
        missing_df["Missing_percent"] = missing_df[missing_col]
        return missing_df

    availability_col = first_matching_column(
        df.columns,
        ["Availability_percent", "Adherence_percent"],
    )
    if not availability_col:
        return df

    missing_df = df.copy()
    availability = pd.to_numeric(missing_df[availability_col], errors="coerce")
    missing_df["Missing_percent"] = (100 - availability).clip(lower=0, upper=100)
    return missing_df

def distinct_data_heatmap(matrix, labels=None):
    labels = {key: str(value) for key, value in (labels or {}).items()}
    plot_matrix = matrix.copy()
    plot_matrix = plot_matrix.apply(pd.to_numeric, errors="coerce")
    max_value = plot_matrix.max().max()
    zmax = 1 if pd.isna(max_value) or max_value <= 0 else max_value
    fig = px.imshow(
        plot_matrix,
        aspect="auto",
        color_continuous_scale=[
            [0.0, "#e9ecef"],
            [0.0001, "#e9ecef"],
            [0.35, "#d9f0ed"],
            [0.7, "#71c7bd"],
            [1.0, "#00796b"],
        ],
        range_color=[0, zmax],
        labels=labels,
    )
    fig.update_traces(
        hoverongaps=False,
        xgap=1,
        ygap=1,
        colorbar=dict(title=dict(text=labels.get("color", ""))),
    )
    fig.update_layout(
        xaxis=dict(showgrid=True, gridcolor="#eef2f5"),
        yaxis=dict(showgrid=True, gridcolor="#eef2f5"),
    )
    return fig

def timeline_x_column(df, preferred_axis=None):
    if preferred_axis == "date":
        preferred_columns = ["Date", "date", "Data", "data"]
        fallback_columns = ["Study_day", "study_day"]
    else:
        preferred_columns = ["Study_day", "study_day"]
        fallback_columns = ["Date", "date", "Data", "data"]

    return (
        first_matching_column(df.columns, preferred_columns)
        or first_matching_column(df.columns, fallback_columns)
    )

def availability_threshold(df, default=80):
    threshold_col = first_matching_column(
        df.columns,
        ["Adherence_threshold", "adherence_threshold"],
    )
    if not threshold_col:
        return float(default)

    values = pd.to_numeric(df[threshold_col], errors="coerce").dropna()
    values = values[values > 0]
    if values.empty:
        return float(default)
    return float(values.iloc[0])
