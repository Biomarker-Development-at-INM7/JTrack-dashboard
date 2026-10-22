"""Smartphone/passive sensor data-quality figure builders."""

import numpy as np
import pandas as pd
import plotly.express as px
from django.utils.translation import gettext_lazy as _

from jdash.config import constants as constants

from ..data.dashboard_data import (
    DEFAULT_DATA_QUALITY_FOLDER,
    apply_filter,
    first_matching_column,
    load_data_per_day_overview,
    load_subject_timeline_data,
    normalize_column_name,
)
from .common_figures import (
    add_missing_percent_column,
    availability_threshold,
    blank_quality_figure,
    distinct_data_heatmap,
    finish_quality_figure,
    timeline_x_column,
)


def build_daily_missingness_figure(df, sensors=None, subjects=None, timeline_axis=None):
    required_columns = {"Sensor", "Subject_ID", "Adherent"}
    if not required_columns.issubset(df.columns):
        return blank_quality_figure(_("Missingness Summary"), _("Daily adherence file is missing sensor, subject, or adherence columns."))

    x_col = timeline_x_column(df, timeline_axis)
    if not x_col:
        return blank_quality_figure(_("Missingness Summary"), _("Daily adherence file is missing study day or date columns."))

    missing_df = df.copy()
    missing_df = apply_filter(missing_df, "Sensor", sensors)
    missing_df = apply_filter(missing_df, "Subject_ID", subjects)
    if missing_df.empty:
        return blank_quality_figure(_("Missingness Summary"))

    missing_df["Adherent"] = pd.to_numeric(missing_df["Adherent"], errors="coerce").fillna(0)
    missing_df["Missing"] = np.where(missing_df["Adherent"] > 0, 0, 100)
    missing_df["Subject_ID"] = missing_df["Subject_ID"].astype(str)
    missing_df["Sensor"] = missing_df["Sensor"].astype(str)
    show_subject_detail = bool(subjects)

    if show_subject_detail:
        selected_sensors = missing_df["Sensor"].dropna().astype(str).unique()
        show_sensor_in_row = len(selected_sensors) != 1
        missing_df["Missingness_row"] = missing_df["Subject_ID"]
        if show_sensor_in_row:
            missing_df["Missingness_row"] = missing_df["Subject_ID"] + " | " + missing_df["Sensor"]
        row_col = "Missingness_row"
        y_label = _("Subject" if not show_sensor_in_row else "Subject | Sensor")
        row_order_by_missing = False
    else:
        row_col = "Sensor"
        y_label = _("Sensor")
        row_order_by_missing = True

    heatmap = missing_df.pivot_table(
        index=row_col,
        columns=x_col,
        values="Missing",
        aggfunc="mean",
        fill_value=0,
    )
    if heatmap.empty:
        return blank_quality_figure(_("Missingness Summary"))

    if row_order_by_missing:
        row_order = heatmap.mean(axis=1).sort_values(ascending=True).index
    else:
        row_order = sorted(heatmap.index)
    heatmap = heatmap.loc[row_order]
    if x_col:
        heatmap = heatmap.reindex(sorted(heatmap.columns), axis=1)

    fig = px.imshow(
        heatmap,
        aspect="auto",
        range_color=[0, 100],
        color_continuous_scale=[
            [0.0, "#e9ecef"],
            [0.35, "#fde2e2"],
            [0.7, "#f28482"],
            [1.0, "#c92a2a"],
        ],
        labels={"x": str(_(x_col)), "y": str(y_label), "color": str(_("Missing %"))},
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            f"{x_col}: %{{x}}<br>"
            "Missing: %{z:.1f}%<extra></extra>"
        ),
        xgap=1,
        ygap=1,
        colorbar=dict(
            title=dict(text=str(_("Missing %"))),
            thickness=14,
            len=0.78,
        ),
    )
    fig.update_layout(
        height=max(340, min(780, 36 * len(heatmap.index) + 130)),
        xaxis=dict(title=str(_(x_col)), type="category"),
        yaxis=dict(title=None),
        margin=dict(l=24, r=24, t=10, b=54),
    )
    return finish_quality_figure(fig)

def build_missingness_figure(df, subjects=None):
    sensor_col = first_matching_column(df.columns, ["Sensor", "sensor"])
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    missing_df = add_missing_percent_column(df)
    if not sensor_col or not subject_col or "Missing_percent" not in missing_df.columns:
        return blank_quality_figure(_("Missingness Summary"), _("Missingness file is missing sensor, subject, or percent columns."))

    missing_df["Sensor"] = missing_df[sensor_col].astype(str)
    missing_df["Subject_ID"] = missing_df[subject_col].astype(str)
    missing_df["Missing_percent"] = pd.to_numeric(missing_df["Missing_percent"], errors="coerce").fillna(0)
    if "Missing_days" not in missing_df.columns and "Technical_missing_days" in missing_df.columns:
        missing_df["Missing_days"] = missing_df["Technical_missing_days"]
    if "Missing_days" in missing_df.columns:
        missing_df["Missing_days"] = pd.to_numeric(missing_df["Missing_days"], errors="coerce").fillna(0)
    if "Days_with_data" not in missing_df.columns and "Days_any_data" in missing_df.columns:
        missing_df["Days_with_data"] = missing_df["Days_any_data"]
    if "Days_with_data" in missing_df.columns:
        missing_df["Days_with_data"] = pd.to_numeric(missing_df["Days_with_data"], errors="coerce").fillna(0)

    if subjects:
        heatmap = missing_df.pivot_table(
            index="Subject_ID",
            columns="Sensor",
            values="Missing_percent",
            aggfunc="mean",
            fill_value=0,
        )
        if heatmap.empty:
            return blank_quality_figure(_("Missingness Summary"))

        sensor_order = heatmap.mean(axis=0).sort_values(ascending=False).index
        subject_order = heatmap.mean(axis=1).sort_values(ascending=False).index
        heatmap = heatmap.loc[subject_order, sensor_order]
        fig = px.imshow(
            heatmap,
            aspect="auto",
            range_color=[0, 100],
            color_continuous_scale=[
                [0.0, "#e9ecef"],
                [0.35, "#fde2e2"],
                [0.7, "#f28482"],
                [1.0, "#c92a2a"],
            ],
            labels={"x": str(_("Sensor")), "y": str(_("Subject")), "color": str(_("Missing %"))},
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Sensor: %{x}<br>"
                "Missing: %{z:.1f}%<extra></extra>"
            ),
            xgap=1,
            ygap=1,
            colorbar=dict(title=dict(text=str(_("Missing %")))),
        )
        fig.update_layout(height=max(360, min(900, 28 * len(heatmap.index) + 150)))
        return fig

    aggregation = {"Missing_percent": "mean", "Subject_ID": "nunique"}
    if "Missing_days" in missing_df.columns:
        aggregation["Missing_days"] = "mean"
    if "Days_with_data" in missing_df.columns:
        aggregation["Days_with_data"] = "mean"

    sensor_summary = missing_df.groupby("Sensor", as_index=False).agg(aggregation)
    sensor_summary = sensor_summary.rename(
        columns={
            "Missing_percent": "Average missing %",
            "Subject_ID": "Subjects measured",
            "Missing_days": "Avg missing days",
            "Days_with_data": "Avg days with data",
        }
    ).sort_values("Average missing %", ascending=True)
    hover_data = {
        "Average missing %": ":.1f",
        "Subjects measured": True,
    }
    if "Avg missing days" in sensor_summary.columns:
        hover_data["Avg missing days"] = ":.1f"
    if "Avg days with data" in sensor_summary.columns:
        hover_data["Avg days with data"] = ":.1f"

    fig = px.bar(
        sensor_summary,
        x="Average missing %",
        y="Sensor",
        orientation="h",
        color="Average missing %",
        color_continuous_scale=[
            [0.0, "#e9ecef"],
            [0.5, "#f28482"],
            [1.0, "#c92a2a"],
        ],
        range_color=[0, 100],
        text=sensor_summary["Average missing %"].map(lambda value: f"{value:.1f}%"),
        hover_data=hover_data,
        labels={"Average missing %": str(_("Average missing %")), "Sensor": str(_("Sensor"))},
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
    )
    fig.update_layout(
        height=max(340, 38 * len(sensor_summary) + 120),
        xaxis=dict(range=[0, 105], ticksuffix="%", title=str(_("Average missing %"))),
        yaxis=dict(title=None),
        coloraxis_showscale=False,
    )
    fig.add_vline(x=50, line_dash="dot", line_color="#f59f00", opacity=0.75)
    fig.add_vline(x=80, line_dash="dot", line_color="#c92a2a", opacity=0.75)
    return fig

def build_dynamic_adherence_figure(study_name, sensors=None, subjects=None, timeline_axis=None, threshold=1):
    if not sensors:
        return blank_quality_figure(
            _("Adherence Heatmap"),
            _("Select a sensor to calculate adherence."),
        )

    df = load_data_per_day_overview(study_name)
    if df is None or df.empty:
        return blank_quality_figure(_("Adherence Heatmap"))

    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    day_col = timeline_x_column(df, timeline_axis)
    value_col = first_matching_column(df.columns, ["Data_per_day", "data_per_day", "Total_records", "records"])
    if not subject_col or not day_col or not value_col or "Sensor" not in df.columns:
        return blank_quality_figure(
            _("Adherence Heatmap"),
            _("Data_per_day files are missing sensor, subject, day/date, or value columns."),
        )

    adherence_df = df.copy()
    adherence_df = apply_filter(adherence_df, "Sensor", sensors)
    adherence_df = apply_filter(adherence_df, subject_col, subjects)
    if adherence_df.empty:
        return blank_quality_figure(_("Adherence Heatmap"))

    threshold = pd.to_numeric(threshold, errors="coerce")
    if pd.isna(threshold):
        threshold = 1
    threshold = max(float(threshold), 0)
    adherence_df[value_col] = pd.to_numeric(adherence_df[value_col], errors="coerce").fillna(0)
    adherence_df["Adherent"] = np.where(adherence_df[value_col] >= threshold, 1, 0)
    adherence_df[subject_col] = adherence_df[subject_col].astype(str)

    heatmap = adherence_df.pivot_table(
        index=subject_col,
        columns=day_col,
        values="Adherent",
        aggfunc="mean",
        fill_value=0,
    )
    if heatmap.empty:
        return blank_quality_figure(_("Adherence Heatmap"))

    heatmap = heatmap.loc[sorted(heatmap.index)]
    heatmap = heatmap.reindex(sorted(heatmap.columns), axis=1)
    fig = px.imshow(
        heatmap,
        aspect="auto",
        range_color=[0, 1],
        color_continuous_scale=[
            [0.0, "#e9ecef"],
            [0.499, "#e9ecef"],
            [0.5, "#00796b"],
            [1.0, "#00796b"],
        ],
        labels={
            "x": str(_(day_col)),
            "y": str(_(subject_col)),
            "color": str(_("Adherent")),
        },
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            f"{day_col}: %{{x}}<br>"
            f"Threshold: {threshold:g}<br>"
            "Adherent: %{z:.0f}<extra></extra>"
        ),
        xgap=1,
        ygap=1,
    )
    fig = finish_quality_figure(fig)
    fig.update_coloraxes(
        showscale=True,
        colorbar=dict(
            title=dict(text=""),
            tickvals=[0, 1],
            ticktext=[str(_("Non-adherent")), str(_("Adherent"))],
            thickness=14,
            len=0.78,
        ),
    )
    fig.update_layout(
        height=max(340, min(780, 22 * len(heatmap.index) + 130)),
        margin=dict(l=24, r=24, t=10, b=54),
    )
    fig.update_xaxes(title=str(_(day_col)), type="category")
    fig.update_yaxes(title=None)
    return fig

def build_sensor_availability_figure(df, sensors=None, title=None):
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    if not subject_col:
        return blank_quality_figure(title or _("Sensor Availability Matrix"))

    excluded_column_names = {
        normalize_column_name(subject_col),
        "adherence_threshold",
    }
    matrix_cols = [
        column
        for column in df.columns
        if normalize_column_name(column) not in excluded_column_names
    ]
    if sensors:
        selected = {str(sensor) for sensor in sensors}
        matrix_cols = [column for column in matrix_cols if str(column) in selected]
    if not matrix_cols:
        return blank_quality_figure(title or _("Sensor Availability Matrix"), _("No selected sensor columns available."))

    matrix = df[[subject_col] + matrix_cols].copy()
    matrix[subject_col] = matrix[subject_col].astype(str)
    for column in matrix_cols:
        matrix[column] = pd.to_numeric(matrix[column], errors="coerce").fillna(0)

    heatmap = matrix.groupby(subject_col, as_index=True)[matrix_cols].mean()
    if heatmap.empty:
        return blank_quality_figure(title or _("Sensor Availability Matrix"))
    row_order = heatmap.mean(axis=1).sort_values(ascending=True).index
    heatmap = heatmap.loc[row_order]

    threshold = availability_threshold(df)
    tickvals = sorted({0, round(threshold, 2), 100})
    ticktext = [
        f"{value:g}% threshold" if value == round(threshold, 2) else f"{value:g}%"
        for value in tickvals
    ]
    fig = px.imshow(
        heatmap,
        aspect="auto",
        range_color=[0, 100],
        color_continuous_scale=[
            [0.0, "#e9ecef"],
            [0.35, "#d9f0ed"],
            [0.7, "#71c7bd"],
            [1.0, "#00796b"],
        ],
        labels={
            "x": str(_("Sensor")),
            "y": str(_("Subject")),
            "color": str(_("Available %")),
        },
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Sensor: %{x}<br>"
            "Available: %{z:.1f}%<extra></extra>"
        ),
        xgap=1,
        ygap=1,
        colorbar=dict(
            title=dict(text=str(_("Available %"))),
            tickvals=tickvals,
            ticktext=ticktext,
            thickness=14,
            len=0.78,
        ),
    )
    fig = finish_quality_figure(fig)
    fig.update_layout(
        height=max(340, min(780, 24 * len(heatmap.index) + 130)),
        margin=dict(l=24, r=24, t=10, b=80),
    )
    fig.update_xaxes(title=None, tickangle=-35)
    fig.update_yaxes(title=None)
    return fig

def build_subject_availability_figure(df, title=None):
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    value_col = first_matching_column(
        df.columns,
        ["EMA_availability_percent", "Availability_percent", "Retention_percent"],
    )
    if not subject_col or not value_col:
        return blank_quality_figure(
            title or _("Subject Availability"),
            _("Availability file is missing subject or availability percent columns."),
        )

    availability_df = df[[subject_col, value_col]].copy()
    availability_df[subject_col] = availability_df[subject_col].astype(str)
    availability_df[value_col] = pd.to_numeric(availability_df[value_col], errors="coerce").fillna(0)
    availability_df = (
        availability_df
        .groupby(subject_col, as_index=False)[value_col]
        .mean()
        .sort_values(value_col, ascending=True)
    )
    if availability_df.empty:
        return blank_quality_figure(title or _("Subject Availability"))

    threshold = availability_threshold(df)
    availability_df["Status"] = np.where(
        availability_df[value_col] >= threshold,
        str(_("Meets threshold")),
        str(_("Below threshold")),
    )
    fig = px.bar(
        availability_df,
        x=value_col,
        y=subject_col,
        color="Status",
        orientation="h",
        range_x=[0, 100],
        text=availability_df[value_col].map(lambda value: f"{value:.1f}%"),
        color_discrete_map={
            str(_("Meets threshold")): "#00796b",
            str(_("Below threshold")): "#d36b4f",
        },
        labels={
            value_col: str(_("Available %")),
            subject_col: str(_("Subject")),
            "Status": str(_("Status")),
        },
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Available: %{x:.1f}%<extra></extra>"
        ),
    )
    fig.add_vline(
        x=threshold,
        line_dash="dash",
        line_color="#212529",
        line_width=1.5,
        annotation_text=str(_("Threshold")),
        annotation_position="top right",
    )
    fig = finish_quality_figure(fig)
    fig.update_layout(
        height=max(340, min(780, 24 * len(availability_df) + 130)),
        margin=dict(l=24, r=36, t=24, b=54),
        legend=dict(
            title=None,
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="left",
            x=0,
            font={"size": 10},
        ),
    )
    fig.update_xaxes(title=str(_("Available %")), ticksuffix="%", range=[0, 105])
    fig.update_yaxes(title=None)
    return fig

def build_daily_volume_figure(df, title=None):
    x_col = first_matching_column(df.columns, ["Study_day", "study_day"]) or timeline_x_column(df)
    y_col = first_matching_column(
        df.columns,
        ["Total_records", "records", "Total_submissions", "Submissions_count"],
    )
    if not x_col or not y_col:
        return blank_quality_figure(
            title or _("Daily Volume"),
            _("Daily volume file is missing study day or total count columns."),
        )

    volume_df = df.copy()
    volume_df[y_col] = pd.to_numeric(volume_df[y_col], errors="coerce").fillna(0)
    if normalize_column_name(x_col) == "study_day":
        volume_df[x_col] = pd.to_numeric(volume_df[x_col], errors="coerce")
    volume_df = volume_df.dropna(subset=[x_col])
    color_col = "Sensor" if "Sensor" in volume_df.columns else None
    sort_columns = [color_col, x_col] if color_col else [x_col]
    volume_df = volume_df.sort_values(sort_columns)
    if volume_df.empty:
        return blank_quality_figure(title or _("Daily Volume"))

    fig = px.bar(
        volume_df,
        x=x_col,
        y=y_col,
        color=color_col,
        labels={
            x_col: str(_("Study day") if normalize_column_name(x_col) == "study_day" else _(x_col)),
            y_col: str(_(y_col)),
            "Sensor": str(_("Sensor")),
        },
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{fullData.name}</b><br>" if color_col else ""
        ) + f"{x_col}: %{{x}}<br>{y_col}: %{{y:,.0f}}<extra></extra>"
    )
    fig = finish_quality_figure(fig)
    fig.update_layout(height=420, margin=dict(l=48, r=24, t=24, b=58))
    fig.update_xaxes(
        title=str(_("Study day") if normalize_column_name(x_col) == "study_day" else _(x_col)),
        showgrid=True,
        gridcolor="#eef2f5",
        zeroline=False,
        nticks=12,
    )
    fig.update_yaxes(title=str(_(y_col)), showgrid=True, gridcolor="#eef2f5", zeroline=False)
    return fig

def _safe_divide(numerator, denominator):
    numerator = pd.to_numeric(numerator, errors="coerce").fillna(0)
    denominator = pd.to_numeric(denominator, errors="coerce").fillna(0)
    return np.where(denominator > 0, numerator / denominator, 0)

def aggregate_subject_qc_timeline(
    study_name,
    quality_folder=DEFAULT_DATA_QUALITY_FOLDER,
    sensors=None,
    subjects=None,
    timeline_axis=None,
):
    timeline_df = load_subject_timeline_data(study_name, quality_folder)
    if timeline_df is None or timeline_df.empty:
        return None, None

    subject_col = first_matching_column(timeline_df.columns, ["Subject_ID", "subject_id", "subject"])
    sensor_col = first_matching_column(timeline_df.columns, ["Sensor", "sensor"])
    x_col = timeline_x_column(timeline_df, timeline_axis)
    value_candidates = ["Data_per_day", "data_per_day"]
    if quality_folder == "ema_data_quality":
        value_candidates = [
            "Total_submissions",
            "total_submissions",
            "Data_per_day",
            "data_per_day",
            "Total_questions_answered",
            "total_questions_answered",
            "Scheduled_questions_answered",
            "scheduled_questions_answered",
        ]
    value_col = first_matching_column(timeline_df.columns, value_candidates)
    if not sensor_col and quality_folder == "ema_data_quality":
        sensor_col = "Sensor"
        timeline_df = timeline_df.copy()
        timeline_df[sensor_col] = constants.ema
    if not subject_col or not sensor_col or not x_col or not value_col:
        return None, None

    daily_df = timeline_df.copy()
    daily_df = apply_filter(daily_df, sensor_col, sensors)
    daily_df = apply_filter(daily_df, subject_col, subjects)
    if daily_df.empty:
        return pd.DataFrame(), x_col

    daily_df[subject_col] = daily_df[subject_col].astype(str)
    daily_df[value_col] = pd.to_numeric(daily_df[value_col], errors="coerce").fillna(0)
    daily_df = daily_df.dropna(subset=[x_col])
    if daily_df.empty:
        return pd.DataFrame(), x_col

    group_columns = [sensor_col, x_col]
    aggregate_df = (
        daily_df
        .groupby(group_columns, as_index=False)
        .agg(
            Daily_volume=(value_col, "sum"),
            Subjects_selected=(subject_col, "nunique"),
        )
    )
    subjects_with_data = (
        daily_df[daily_df[value_col] > 0]
        .groupby(group_columns)[subject_col]
        .nunique()
        .rename("Subjects_with_data")
        .reset_index()
    )
    aggregate_df = aggregate_df.merge(subjects_with_data, on=group_columns, how="left")
    aggregate_df["Subjects_with_data"] = aggregate_df["Subjects_with_data"].fillna(0).astype(int)
    aggregate_df["Mean_volume_per_selected_subject"] = _safe_divide(
        aggregate_df["Daily_volume"],
        aggregate_df["Subjects_selected"],
    )
    aggregate_df["Mean_volume_per_active_subject"] = _safe_divide(
        aggregate_df["Daily_volume"],
        aggregate_df["Subjects_with_data"],
    )
    aggregate_df["Coverage_percent"] = _safe_divide(
        aggregate_df["Subjects_with_data"] * 100,
        aggregate_df["Subjects_selected"],
    )

    aggregate_df = aggregate_df.rename(columns={sensor_col: "Sensor"})
    if normalize_column_name(x_col) == "study_day":
        aggregate_df[x_col] = pd.to_numeric(aggregate_df[x_col], errors="coerce")
    aggregate_df = aggregate_df.dropna(subset=[x_col]).sort_values(["Sensor", x_col])
    return aggregate_df, x_col

def build_subject_timeline_daily_volume_figure(
    study_name,
    quality_folder=DEFAULT_DATA_QUALITY_FOLDER,
    sensors=None,
    subjects=None,
    timeline_axis=None,
    title=None,
):
    aggregate_df, x_col = aggregate_subject_qc_timeline(
        study_name,
        quality_folder,
        sensors,
        subjects,
        timeline_axis,
    )
    if aggregate_df is None:
        return None
    if aggregate_df.empty:
        return blank_quality_figure(title or _("Daily Volume"))

    is_ema = quality_folder == "ema_data_quality"
    y_col = "Daily_submissions" if is_ema else "Daily_volume"
    if is_ema:
        aggregate_df[y_col] = aggregate_df["Daily_volume"]

    fig = px.bar(
        aggregate_df,
        x=x_col,
        y=y_col,
        color="Sensor",
        labels={
            x_col: str(_("Study day") if normalize_column_name(x_col) == "study_day" else _(x_col)),
            y_col: str(_("Daily submissions") if is_ema else _("Daily volume")),
            "Sensor": str(_("Sensor")),
        },
        custom_data=[
            "Subjects_selected",
            "Subjects_with_data",
            "Mean_volume_per_selected_subject",
            "Mean_volume_per_active_subject",
        ],
    )
    hover_label = "Daily submissions" if is_ema else "Daily volume"
    fig.update_traces(
        marker_line_width=0,
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            f"{x_col}: %{{x}}<br>"
            f"{hover_label}: %{{y:,.0f}}<br>"
            "Selected subjects: %{customdata[0]:,.0f}<br>"
            "Subjects with data: %{customdata[1]:,.0f}<br>"
            "Mean per selected subject: %{customdata[2]:,.2f}<br>"
            "Mean per active subject: %{customdata[3]:,.2f}<extra></extra>"
        ),
    )
    fig = finish_quality_figure(fig)
    fig.update_layout(
        height=420,
        hovermode="x unified",
        legend=dict(title=None, orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0),
        margin=dict(l=48, r=24, t=24, b=58),
    )
    fig.update_xaxes(
        title=str(_("Study day") if normalize_column_name(x_col) == "study_day" else _(x_col)),
        showgrid=True,
        gridcolor="#eef2f5",
        zeroline=False,
        nticks=12,
    )
    fig.update_yaxes(
        title=str(_("Daily submissions") if is_ema else _("Daily volume")),
        showgrid=True,
        gridcolor="#eef2f5",
        zeroline=False,
    )
    return fig

def build_subject_timeline_daily_coverage_figure(
    study_name,
    quality_folder=DEFAULT_DATA_QUALITY_FOLDER,
    sensors=None,
    subjects=None,
    timeline_axis=None,
    title=None,
):
    aggregate_df, x_col = aggregate_subject_qc_timeline(
        study_name,
        quality_folder,
        sensors,
        subjects,
        timeline_axis,
    )
    if aggregate_df is None:
        return None
    if aggregate_df.empty:
        return blank_quality_figure(title or _("Sensor Coverage"))

    fig = px.line(
        aggregate_df,
        x=x_col,
        y="Coverage_percent",
        color="Sensor",
        markers=True,
        range_y=[0, 100],
        labels={
            x_col: str(_("Study day") if normalize_column_name(x_col) == "study_day" else _(x_col)),
            "Coverage_percent": str(_("Coverage %")),
            "Sensor": str(_("Sensor")),
        },
        custom_data=["Subjects_selected", "Subjects_with_data", "Daily_volume"],
    )
    fig.update_traces(
        mode="lines+markers",
        line={"width": 2.5},
        marker={"size": 6, "line": {"width": 1, "color": "#ffffff"}},
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            f"{x_col}: %{{x}}<br>"
            "Coverage: %{y:.1f}%<br>"
            "Selected subjects: %{customdata[0]:,.0f}<br>"
            "Subjects with data: %{customdata[1]:,.0f}<br>"
            "Daily volume: %{customdata[2]:,.0f}<extra></extra>"
        ),
    )
    fig = finish_quality_figure(fig)
    fig.update_layout(
        height=420,
        hovermode="x unified",
        legend=dict(title=None, orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0),
        margin=dict(l=48, r=24, t=24, b=58),
    )
    fig.update_xaxes(
        title=str(_("Study day") if normalize_column_name(x_col) == "study_day" else _(x_col)),
        showgrid=True,
        gridcolor="#eef2f5",
        zeroline=False,
        nticks=12,
    )
    fig.update_yaxes(
        title=str(_("Coverage %")),
        range=[0, 100],
        ticksuffix="%",
        showgrid=True,
        gridcolor="#eef2f5",
        zeroline=False,
    )
    return fig

def build_subject_retention_figure(df, title=None):
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    retention_col = first_matching_column(
        df.columns,
        [
            "Retention_percent",
            "Availability_percent",
            "Availability_retention_percent",
            "Adherence_retention_percent",
        ],
    )
    if not subject_col or not retention_col:
        return blank_quality_figure(
            title or _("Subject Retention"),
            _("Retention file is missing subject or retention percent columns."),
        )

    retention_df = df[[subject_col, retention_col] + (["Status"] if "Status" in df.columns else [])].copy()
    retention_df[retention_col] = pd.to_numeric(retention_df[retention_col], errors="coerce").fillna(0)
    retention_df = retention_df.sort_values(retention_col, ascending=True)
    fig = px.bar(
        retention_df,
        x=retention_col,
        y=subject_col,
        color="Status" if "Status" in retention_df.columns else None,
        orientation="h",
        range_x=[0, 100],
        labels={
            retention_col: str(_("Retention %")),
            subject_col: str(_("Subject")),
            "Status": str(_("Status")),
        },
    )
    fig = finish_quality_figure(fig)
    fig.update_layout(
        height=max(340, min(780, 22 * len(retention_df) + 130)),
        margin=dict(l=24, r=24, t=10, b=54),
    )
    fig.update_xaxes(ticksuffix="%", title=str(_("Retention %")))
    fig.update_yaxes(title=None)
    return fig
