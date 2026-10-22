"""Thin router/facade for analytics dashboard figures."""

import pandas as pd
import plotly.express as px
from django.utils.translation import gettext_lazy as _

from ..data.dashboard_data import (
    DEFAULT_DATA_QUALITY_FOLDER,
    filtered_quality_csv,
    first_matching_column,
    load_quality_csv,
    load_subject_timeline_data,
    normalize_column_name,
    quality_csv_semantic_key,
)
from .common_figures import (
    add_coverage_percent_column,
    blank_quality_figure,
    distinct_data_heatmap,
    finish_quality_figure,
    status_color,
    timeline_x_column,
)
from .device_sensor_figures import (
    build_overview_device_sensor_coverage,
)
from .ema_figures import (
    build_ema_anytime_question_status_figure,
    build_ema_completion_matrix_figure,
    build_ema_daily_response_volume_figure,
    build_ema_frequency_window_detail_figure,
    build_ema_missingness_figure,
    build_ema_risk_ranking_figure,
    build_ema_subject_timeline_figure,
)
from .overview_figures import (
    build_device_sensor_kpi_summary,
    build_ema_kpi_summary,
    build_monitoring_summary,
    build_overview_ema_coverage,
    build_overview_sensor_coverage,
    build_overview_subject_coverage,
    build_subject_data_per_day_heatmap,
    build_subject_stream_progression_figure,
    build_smartphone_kpi_summary,
    build_summary_gauge,
    live_sensor_coverage_metrics,
    live_sensor_coverage_summary,
    no_data_over_two_days_summary,
    subject_sensor_coverage_metrics,
)
from .sensor_figures import (
    build_daily_missingness_figure,
    build_daily_volume_figure,
    build_dynamic_adherence_figure,
    build_missingness_figure,
    build_sensor_availability_figure,
    build_subject_availability_figure,
    build_subject_retention_figure,
    build_subject_timeline_daily_coverage_figure,
    build_subject_timeline_daily_volume_figure,
)
from .status_table_figures import (
    build_status_table,
    build_subject_sensor_status_table,
)


def build_quality_figure(
    card,
    study_name,
    sensors=None,
    subjects=None,
    stages=None,
    flags=None,
    timeline_axis=None,
    adherence_threshold=1,
):
    title = str(card["title"])
    filename = card["filename"]
    filename_key = quality_csv_semantic_key(filename)
    quality_folder = card.get("quality_folder", DEFAULT_DATA_QUALITY_FOLDER)
    if card.get("threshold_control"):
        return build_dynamic_adherence_figure(
            study_name,
            sensors,
            subjects,
            timeline_axis,
            adherence_threshold,
        )
    if card.get("figure_builder") == "subject_stream_progression":
        return build_subject_stream_progression_figure(card, study_name, subjects, timeline_axis)

    if quality_folder == "ema_data_quality":
        df = filtered_quality_csv(study_name, filename, sensors, subjects, stages, flags, quality_folder)
        if df is None or df.empty:
            return blank_quality_figure(title)

        try:
            if filename_key == "completion_matrix":
                return build_ema_completion_matrix_figure(df, subjects, title)
            if filename_key == "frequency_window_completion":
                return build_ema_frequency_window_detail_figure(df, subjects, timeline_axis, title, stages)
            if filename_key == "missingness_summary":
                return build_ema_risk_ranking_figure(df, subjects, title)
            if filename_key == "daily_submission_volume":
                timeline_df = load_subject_timeline_data(study_name, quality_folder)
                daily_source_df = timeline_df if timeline_df is not None and not timeline_df.empty else df
                return build_ema_daily_response_volume_figure(daily_source_df, subjects, timeline_axis, title)
            if filename_key == "subject_qc_timeline":
                return build_ema_subject_timeline_figure(df, subjects, timeline_axis, title)
            if filename_key == "anytime_question_status":
                return build_ema_anytime_question_status_figure(df, subjects, title)
        except Exception:
            return blank_quality_figure(title, _("Could not build EMA figure from this CSV."))

    if filename_key == "daily_subject_coverage":
        timeline_fig = build_subject_timeline_daily_coverage_figure(
            study_name,
            quality_folder,
            sensors,
            subjects,
            timeline_axis,
            title,
        )
        if timeline_fig is not None:
            return timeline_fig

    if filename_key in ("daily_data_volume", "daily_submission_volume"):
        timeline_fig = build_subject_timeline_daily_volume_figure(
            study_name,
            quality_folder,
            sensors,
            subjects,
            timeline_axis,
            title,
        )
        if timeline_fig is not None:
            return timeline_fig

    if filename == "Data_per_day*.csv":
        return build_subject_data_per_day_heatmap(study_name, subjects, timeline_axis, title)

    df = filtered_quality_csv(study_name, filename, sensors, subjects, stages, flags, quality_folder)
    if df is None or df.empty:
        return blank_quality_figure(title)

    try:
        if filename_key == "adherence_heatmap":
            x_col = timeline_x_column(df, timeline_axis)
            if not x_col:
                return blank_quality_figure(title, _("Timeline file is missing study day or date columns."))
            heatmap = df.pivot_table(
                index="Subject_ID",
                columns=x_col,
                values="Adherent",
                aggfunc="mean",
                fill_value=0,
            )
            fig = distinct_data_heatmap(
                heatmap,
                labels={"x": str(x_col), "y": _("Subject"), "color": _("Adherent")},
            )
        elif filename_key == "daily_subject_coverage":
            coverage_df = add_coverage_percent_column(df)
            x_col = first_matching_column(coverage_df.columns, ["Study_day", "study_day"]) or timeline_x_column(coverage_df)
            if not x_col or "Coverage_percent" not in coverage_df.columns:
                return blank_quality_figure(title, _("Daily coverage file is missing study day or coverage percent columns."))
            color_col = "Sensor" if "Sensor" in coverage_df.columns else None
            fig = px.line(coverage_df, x=x_col, y="Coverage_percent", color=color_col, markers=True, title=title)
        elif filename_key in ("daily_data_volume", "daily_submission_volume"):
            return build_daily_volume_figure(df, title)
        elif filename_key == "subject_retention":
            if "Study_day" in df.columns and "Retention_percent" in df.columns:
                fig = px.line(df, x="Study_day", y="Retention_percent", markers=True, title=title)
            else:
                return build_subject_retention_figure(df, title)
        elif filename_key == "missingness_summary":
            daily_df = load_quality_csv(
                study_name,
                "Data_quality_adherence_heatmap.csv",
                quality_folder,
            )
            if daily_df is not None and not daily_df.empty:
                if "Sensor" not in daily_df.columns:
                    return build_ema_missingness_figure(daily_df, subjects, timeline_axis, title)
                return build_daily_missingness_figure(daily_df, sensors, subjects, timeline_axis)
            else:
                fig = build_missingness_figure(df, subjects)
        elif filename_key == "subject_availability_matrix":
            return build_subject_availability_figure(df, title)
        elif filename_key == "sensor_availability_matrix":
            return build_sensor_availability_figure(df, sensors, title)
        elif filename_key == "qc_exclusion_funnel":
            fig = px.bar(df, x="Stage", y="Records", color="Sensor", title=title)
        elif filename_key == "qc_data_loss_by_stage":
            loss_columns = [
                "Rows_missing_timestamp",
                "Rows_outside_study_window",
                "Duplicates_removed",
                "Rows_lost",
            ]
            available_loss_columns = [column for column in loss_columns if column in df.columns]
            melted = df.melt(
                id_vars=["Sensor"],
                value_vars=available_loss_columns,
                var_name="Stage",
                value_name="Rows",
            )
            fig = px.bar(melted, x="Sensor", y="Rows", color="Stage", title=title)
        elif filename_key == "subject_qc_timeline":
            x_col = timeline_x_column(df, timeline_axis)
            if not x_col:
                return blank_quality_figure(title, _("Timeline file is missing study day or date columns."))
            value_col = first_matching_column(
                df.columns,
                ["Data_per_day", "Submissions_count", "Total_records", "records"],
            )
            if not value_col:
                return blank_quality_figure(title, _("Timeline file is missing count columns."))
            timeline = df.pivot_table(
                index="Subject_ID",
                columns=x_col,
                values=value_col,
                aggfunc="sum",
                fill_value=0,
            )
            fig = distinct_data_heatmap(
                timeline,
                labels={"x": str(x_col), "y": _("Subject"), "color": str(_(value_col))},
            )
        elif filename_key == "anomaly_flags":
            anomaly_df = df.copy()
            anomaly_df["Flag"] = anomaly_df["Flag"].astype(str)
            fig = px.scatter(anomaly_df, x="Study_day", y="Z_score", color="Flag", symbol="Sensor", title=title)
        else:
            return blank_quality_figure(title)
    except Exception as exc:
        return blank_quality_figure(title, f"Could not build chart: {exc}")

    return finish_quality_figure(fig)


def build_live_figure(card, study_name, sensors=None, subjects=None, stages=None, flags=None, timeline_axis=None):
    title = str(card["title"])
    filename = card["filename"]
    if filename.endswith("summary.csv"):
        return build_monitoring_summary(study_name, title, subjects)
    if filename == "__details_sensor_kpis__":
        return build_smartphone_kpi_summary(study_name, subjects)
    if filename == "__details_device_sensor_kpis__":
        return build_device_sensor_kpi_summary(study_name, subjects)
    if filename == "__details_ema_kpis__":
        return build_ema_kpi_summary(study_name, subjects)
    if filename == "__details_subject_coverage__":
        return build_overview_subject_coverage(study_name)
    if filename == "__details_sensor_coverage__":
        return build_overview_sensor_coverage(study_name, subjects, timeline_axis)
    if filename == "__details_ema_coverage__":
        return build_overview_ema_coverage(study_name, subjects, timeline_axis)
    if filename in ("__details_device_sensor_coverage__", "__details_wearable_sensor_coverage__"):
        return build_overview_device_sensor_coverage(study_name, subjects, timeline_axis)

    df = filtered_quality_csv(study_name, filename, sensors, subjects, stages, flags)
    if df is None or df.empty:
        return blank_quality_figure(title)

    try:
        if filename.endswith("subject_sensor_status.csv"):
            return build_subject_sensor_status_table(df)
        if filename.endswith("sensor_status.csv"):
            fig = build_status_table(
                df,
                [
                    "Sensor",
                    "Status",
                    "Coverage_percent",
                    "Recent_coverage_percent",
                    "Subjects_with_data",
                    "Expected_subjects",
                    "Last_data_day",
                    "Last_data_date",
                ],
            )
        elif filename.endswith("subject_status.csv"):
            fig = build_status_table(
                df,
                [
                    "Subject_ID",
                    "Status",
                    "Sensors_any_data",
                    "Last_any_data_day",
                    "Last_any_data_date",
                ],
            )
        elif filename.endswith("recent_coverage.csv"):
            fig = px.line(df, x="Study_day", y="Coverage_percent", color="Sensor", markers=True, range_y=[0, 100])
        elif filename.endswith("freshness.csv"):
            fresh_df = df.copy()
            fig = px.bar(
                fresh_df,
                x="Sensor",
                y="Hours_since_last_processed",
                color="Status",
                color_discrete_map={status: status_color(status) for status in fresh_df.get("Status", pd.Series(dtype=str)).dropna().unique()},
            )
        elif filename.endswith("warnings.csv"):
            warning_df = df.copy()
            if "Severity" in warning_df and "Warning_type" in warning_df:
                warning_counts = warning_df.groupby(["Severity", "Warning_type"], as_index=False).size()
                fig = px.bar(
                    warning_counts,
                    x="Warning_type",
                    y="size",
                    color="Severity",
                    color_discrete_map={severity: status_color(severity) for severity in warning_counts["Severity"]},
                )
            else:
                return blank_quality_figure(title)
        else:
            return blank_quality_figure(title)
    except Exception as exc:
        return blank_quality_figure(title, f"Could not build chart: {exc}")

    return finish_quality_figure(fig)
