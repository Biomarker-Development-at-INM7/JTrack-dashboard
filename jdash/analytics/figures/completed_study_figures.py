"""Read-only KPI summaries for studies whose data collection has ended."""

import pandas as pd
from dash import html
from django.utils.translation import gettext_lazy as _

from ..data.dashboard_data import (
    DEFAULT_DATA_QUALITY_FOLDER,
    apply_filter,
    first_matching_column,
    load_quality_csv,
    load_subject_timeline_data,
)
from ..data.ema_data import (
    EMA_MISSINGNESS_SUMMARY_CSV,
    EMA_QUALITY_FOLDER,
    EMA_RESPONSE_COUNT_COLUMNS,
    EMA_SUBJECT_QC_TIMELINE_CSV,
)
from .overview_figures import kpi_card


def _empty_findings():
    return html.Div([], className="analytics-activity-findings")


def _status(complete, total):
    if not total:
        return "neutral"
    ratio = complete / total
    if ratio >= 0.95:
        return "healthy"
    if ratio >= 0.80:
        return "warning"
    return "critical"


def _final_subtitle(missing_count, include_definition=False):
    lines = [
        html.Div(
            f"{missing_count} {str(_('subjects have missing recorded streams'))}",
            className="analytics-kpi-attention-count",
        )
    ]
    if include_definition:
        lines.append(
            html.Div(
                str(_("Complete = recorded data exists for every configured stream")),
                className="analytics-kpi-definition",
            )
        )
    return html.Div(lines)


def build_completed_overview_summary(source_status, available_sources):
    """Keep final coverage cards but remove operational drill-down behavior."""
    if source_status is None:
        cards = [
            kpi_card(str(_("Final Data Coverage")), "--", str(_("no subject status data")), "neutral")
        ]
        for source, label in (
            ("smartphone", _("Smartphone")),
            ("device_sensor", _("Garmin")),
            ("ema", _("EMA")),
        ):
            if source in available_sources:
                cards.append(
                    kpi_card(
                        f"{str(label)} {str(_('Final Coverage'))}",
                        "--",
                        str(_("no subject status data")),
                        "neutral",
                    )
                )
        return cards, _empty_findings(), {}

    status_df, subject_col, _sensor_col = source_status
    all_subjects = set(status_df[subject_col].dropna().astype(str).unique())
    missing_subjects = set(
        status_df.loc[~status_df["_has_data"], subject_col].dropna().astype(str).unique()
    )
    complete_subjects = all_subjects - missing_subjects
    cards = [
        kpi_card(
            str(_("Final Data Coverage")),
            f"{len(complete_subjects)} / {len(all_subjects)} complete",
            _final_subtitle(len(missing_subjects), include_definition=True),
            _status(len(complete_subjects), len(all_subjects)),
        )
    ]

    for source, label in (
        ("smartphone", _("Smartphone")),
        ("device_sensor", _("Garmin")),
        ("ema", _("EMA")),
    ):
        source_df = status_df[status_df["_source"].eq(source)]
        if source_df.empty:
            continue
        source_subjects = set(source_df[subject_col].dropna().astype(str).unique())
        missing = set(
            source_df.loc[~source_df["_has_data"], subject_col].dropna().astype(str).unique()
        )
        complete = source_subjects - missing
        cards.append(
            kpi_card(
                f"{str(label)} {str(_('Final Coverage'))}",
                f"{len(complete)} / {len(source_subjects)} complete",
                _final_subtitle(len(missing)),
                _status(len(complete), len(source_subjects)),
            )
        )
    return cards, _empty_findings(), {}


def build_completed_sensor_summary(study_name, quality_folder, subjects=None):
    """Return all-time, non-clickable sensor totals for a completed study."""
    timeline_df = load_subject_timeline_data(study_name, quality_folder)
    if timeline_df is None or timeline_df.empty:
        cards = [
            kpi_card(str(_("Subjects With Data")), "--", str(_("no sensor timeline data")), "neutral"),
            kpi_card(str(_("Sensors Recorded")), "--", str(_("no sensor timeline data")), "neutral"),
            kpi_card(str(_("Recorded Subject-days")), "--", str(_("no sensor timeline data")), "neutral"),
            kpi_card(str(_("Total Records")), "--", str(_("no sensor timeline data")), "neutral"),
        ]
        return cards, _empty_findings(), {}

    subject_col = first_matching_column(timeline_df.columns, ["Subject_ID", "subject_id", "subject"])
    sensor_col = first_matching_column(timeline_df.columns, ["Sensor", "sensor"])
    day_col = first_matching_column(timeline_df.columns, ["Study_day", "study_day"])
    value_col = first_matching_column(timeline_df.columns, ["Data_per_day", "data_per_day"])
    if not subject_col or not sensor_col or not day_col or not value_col:
        return [], _empty_findings(), {}

    timeline_df = apply_filter(timeline_df.copy(), subject_col, subjects)
    timeline_df[subject_col] = timeline_df[subject_col].fillna("").astype(str)
    timeline_df[sensor_col] = timeline_df[sensor_col].fillna("").astype(str)
    timeline_df[day_col] = pd.to_numeric(timeline_df[day_col], errors="coerce")
    timeline_df[value_col] = pd.to_numeric(timeline_df[value_col], errors="coerce").fillna(0)
    timeline_df = timeline_df[
        timeline_df[subject_col].astype(bool)
        & timeline_df[sensor_col].astype(bool)
        & timeline_df[day_col].notna()
    ]
    positive = timeline_df[timeline_df[value_col].gt(0)]
    all_subjects = set(timeline_df[subject_col].unique())
    subjects_with_data = set(positive[subject_col].unique())
    sensors_recorded = set(positive[sensor_col].unique())
    subject_days = positive[[subject_col, day_col]].drop_duplicates().shape[0]
    total_records = int(positive[value_col].sum())
    cards = [
        kpi_card(
            str(_("Subjects With Data")),
            f"{len(subjects_with_data)} / {len(all_subjects)}",
            str(_("participants with at least one recorded sensor value")),
            _status(len(subjects_with_data), len(all_subjects)),
        ),
        kpi_card(
            str(_("Sensors Recorded")),
            len(sensors_recorded),
            str(_("sensors with recorded data across the study")),
            "neutral",
        ),
        kpi_card(
            str(_("Recorded Subject-days")),
            subject_days,
            str(_("participant-days containing sensor data")),
            "neutral",
        ),
        kpi_card(
            str(_("Total Records")),
            f"{total_records:,}",
            str(_("sensor records collected across the study")),
            "neutral",
        ),
    ]
    return cards, _empty_findings(), {}


def build_completed_ema_summary(study_name, subjects=None):
    """Return all-time, non-clickable EMA totals for a completed study."""
    timeline_df = load_quality_csv(
        study_name,
        EMA_SUBJECT_QC_TIMELINE_CSV,
        EMA_QUALITY_FOLDER,
    )
    missing_df = load_quality_csv(
        study_name,
        EMA_MISSINGNESS_SUMMARY_CSV,
        EMA_QUALITY_FOLDER,
    )
    subject_col = (
        first_matching_column(timeline_df.columns, ["Subject_ID", "subject_id", "subject"])
        if timeline_df is not None and not timeline_df.empty
        else None
    )
    day_col = (
        first_matching_column(timeline_df.columns, ["Study_day", "study_day"])
        if timeline_df is not None and not timeline_df.empty
        else None
    )
    value_col = (
        first_matching_column(timeline_df.columns, EMA_RESPONSE_COUNT_COLUMNS)
        if timeline_df is not None and not timeline_df.empty
        else None
    )
    if not subject_col or not day_col or not value_col:
        cards = [
            kpi_card(str(_("Responding Subjects")), "--", str(_("no EMA activity data")), "neutral"),
            kpi_card(str(_("Responses Recorded")), "--", str(_("no EMA activity data")), "neutral"),
            kpi_card(str(_("Response Days")), "--", str(_("no EMA activity data")), "neutral"),
            kpi_card(str(_("Overall Completion")), "--", str(_("no EMA completion data")), "neutral"),
        ]
        return cards, _empty_findings(), {}

    timeline_df = apply_filter(timeline_df.copy(), subject_col, subjects)
    timeline_df[subject_col] = timeline_df[subject_col].fillna("").astype(str)
    timeline_df[day_col] = pd.to_numeric(timeline_df[day_col], errors="coerce")
    timeline_df[value_col] = pd.to_numeric(timeline_df[value_col], errors="coerce").fillna(0)
    timeline_df = timeline_df[timeline_df[subject_col].astype(bool) & timeline_df[day_col].notna()]
    positive = timeline_df[timeline_df[value_col].gt(0)]
    all_subjects = set(timeline_df[subject_col].unique())
    responding_subjects = set(positive[subject_col].unique())
    response_days = positive[[subject_col, day_col]].drop_duplicates().shape[0]
    responses = int(positive[value_col].sum())

    completion = None
    if missing_df is not None and not missing_df.empty:
        missing_subject_col = first_matching_column(missing_df.columns, ["Subject_ID", "subject_id", "subject"])
        completion_col = first_matching_column(
            missing_df.columns,
            ["Question_completion_percent", "Completion_percent", "Response_rate_percent"],
        )
        if missing_subject_col and completion_col:
            missing_df = apply_filter(missing_df.copy(), missing_subject_col, subjects)
            completion_values = pd.to_numeric(missing_df[completion_col], errors="coerce").dropna()
            if not completion_values.empty:
                completion = float(completion_values.mean())

    cards = [
        kpi_card(
            str(_("Responding Subjects")),
            f"{len(responding_subjects)} / {len(all_subjects)}",
            str(_("participants with at least one EMA response")),
            _status(len(responding_subjects), len(all_subjects)),
        ),
        kpi_card(
            str(_("Responses Recorded")),
            f"{responses:,}",
            str(_("EMA responses collected across the study")),
            "neutral",
        ),
        kpi_card(
            str(_("Response Days")),
            response_days,
            str(_("participant-days containing EMA responses")),
            "neutral",
        ),
        kpi_card(
            str(_("Overall Completion")),
            f"{completion:.0f}%" if completion is not None else "--",
            str(_("average questionnaire completion across participants")),
            "neutral" if completion is None else _status(completion, 100),
        ),
    ]
    return cards, _empty_findings(), {}


def build_completed_dashboard_summary(active_tab, study_name, subjects, source_status=None, available_sources=None):
    if active_tab == "sensor-data":
        return build_completed_sensor_summary(study_name, DEFAULT_DATA_QUALITY_FOLDER, subjects)
    if active_tab == "device-sensor-data":
        return build_completed_sensor_summary(study_name, "garmin_data_quality", subjects)
    if active_tab == "ema-data":
        return build_completed_ema_summary(study_name, subjects)
    return build_completed_overview_summary(source_status, available_sources or set())
