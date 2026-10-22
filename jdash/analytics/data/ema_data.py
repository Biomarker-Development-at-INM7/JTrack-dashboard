"""EMA-specific analytics data helpers."""

import pandas as pd

from .dashboard_data import first_matching_column
from .dashboard_data import load_quality_csv

EMA_QUALITY_FOLDER = "ema_data_quality"

EMA_COMPLETION_MATRIX_CSV = "Ema_data_quality_completion_matrix.csv"
EMA_FREQUENCY_WINDOW_COMPLETION_CSV = "Ema_data_quality_frequency_window_completion.csv"
EMA_MISSINGNESS_SUMMARY_CSV = "Ema_data_quality_missingness_summary.csv"
EMA_DAILY_SUBMISSION_VOLUME_CSV = "Ema_data_quality_daily_submission_volume.csv"
EMA_SUBJECT_QC_TIMELINE_CSV = "Ema_data_quality_subject_qc_timeline.csv"
EMA_ANYTIME_QUESTION_STATUS_CSV = "Ema_data_quality_anytime_question_status.csv"

EMA_RESPONSE_COUNT_COLUMNS = [
    "Anytime_questions_answered",
    "Optional_questions_answered",
    "Total_questions_answered",
    "Submissions_count",
    "Total_submissions",
]


def load_ema_quality_csv(study_name, filename):
    return load_quality_csv(study_name, filename, EMA_QUALITY_FOLDER)


def is_optional_only_ema_study(study_name):
    timeline_df = load_ema_quality_csv(study_name, EMA_SUBJECT_QC_TIMELINE_CSV)
    if timeline_df is None or timeline_df.empty:
        return False

    scheduled_col = first_matching_column(timeline_df.columns, ["Scheduled_questions_answered"])
    response_col = first_matching_column(timeline_df.columns, EMA_RESPONSE_COUNT_COLUMNS)

    scheduled_total = (
        pd.to_numeric(timeline_df[scheduled_col], errors="coerce").fillna(0).sum()
        if scheduled_col
        else 0
    )
    response_total = (
        pd.to_numeric(timeline_df[response_col], errors="coerce").fillna(0).sum()
        if response_col
        else 0
    )
    if scheduled_total == 0 and response_total > 0:
        return True

    anytime_df = load_ema_quality_csv(study_name, EMA_ANYTIME_QUESTION_STATUS_CSV)
    if anytime_df is not None and not anytime_df.empty:
        return True

    missingness_df = load_ema_quality_csv(study_name, EMA_MISSINGNESS_SUMMARY_CSV)
    if missingness_df is None or missingness_df.empty:
        return False

    expected_col = first_matching_column(missingness_df.columns, ["Expected_questions_total"])
    if not expected_col:
        return False

    expected_total = pd.to_numeric(missingness_df[expected_col], errors="coerce").fillna(0).sum()
    return scheduled_total == 0 and expected_total == 0
