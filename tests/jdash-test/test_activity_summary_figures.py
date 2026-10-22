from unittest.mock import patch

import pandas as pd

from jdash.analytics.figures import activity_summary_figures as figures
from jdash.analytics.figures import completed_study_figures as completed_figures


def _card_value(card):
    children = card.to_plotly_json()["props"]["children"]
    return children[1].to_plotly_json()["props"]["children"]


def test_current_status_uses_percentage_thresholds():
    assert figures._current_status(95, 100) == "healthy"
    assert figures._current_status(80, 100) == "warning"
    assert figures._current_status(79, 100) == "critical"
    assert figures._current_status(0, 0) == "neutral"


def test_overview_kpis_show_current_subjects_and_drill_into_issues():
    rows = []
    for source, sensor, issue_count in (
        ("smartphone", "lockUnlock", 48),
        ("device_sensor", "garmin_spo2", 45),
        ("ema", "ema", 50),
    ):
        rows.extend(
            {
                "Subject_ID": str(subject),
                "Sensor": sensor,
                "Sensor_group": source,
                "Last_data_received_date": "2026-10-12",
                "Days_since_last_data_received": 2 if subject < issue_count else 0,
            }
            for subject in range(50)
        )

    findings = {
        "current_gap": [],
        "consecutive_gap": [],
        "repeated_gap": [],
        "activity_decline": [],
    }
    with patch.object(figures, "load_quality_csv", return_value=pd.DataFrame(rows)), patch.object(
        figures, "overview_activity_findings", return_value=findings
    ), patch.object(figures, "_data_collection_completed", return_value=False):
        cards, _, payloads = figures._build_overview_summary("study")

    assert [_card_value(card) for card in cards] == [
        "0 / 50 current",
        "2 / 50 current",
        "5 / 50 current",
        "0 / 50 current",
    ]
    assert len(payloads["overview-all-on-track"]["subjects"]) == 50
    assert len(payloads["overview-smartphone-attention"]["subjects"]) == 48
    assert len(payloads["overview-device_sensor-attention"]["subjects"]) == 45
    assert len(payloads["overview-ema-attention"]["subjects"]) == 50


def test_completed_study_kpis_use_final_coverage_not_recency():
    rows = []
    for source, sensor in (
        ("smartphone", "lockUnlock"),
        ("device_sensor", "garmin_spo2"),
        ("ema", "ema"),
    ):
        rows.extend(
            {
                "Subject_ID": str(subject),
                "Sensor": sensor,
                "Sensor_group": source,
                "Last_data_received_date": None if subject == 4 else "2026-01-01",
                "Days_since_last_data_received": 200,
            }
            for subject in range(5)
        )

    findings = {
        "current_gap": [],
        "consecutive_gap": [],
        "repeated_gap": [],
        "activity_decline": [],
    }
    with patch.object(figures, "load_quality_csv", return_value=pd.DataFrame(rows)), patch.object(
        figures, "overview_activity_findings", return_value=findings
    ), patch.object(figures, "_data_collection_completed", return_value=True):
        cards, _, payloads = figures._build_overview_summary("study")

    assert [_card_value(card) for card in cards] == [
        "4 / 5 complete",
        "4 / 5 complete",
        "4 / 5 complete",
        "4 / 5 complete",
    ]
    assert payloads["overview-all-on-track"]["subjects"] == ["4"]


def test_completed_overview_keeps_coverage_without_drilldowns():
    status_df = pd.DataFrame(
        [
            {"Subject_ID": "1", "_source": "smartphone", "_has_data": True},
            {"Subject_ID": "2", "_source": "smartphone", "_has_data": False},
            {"Subject_ID": "1", "_source": "ema", "_has_data": True},
            {"Subject_ID": "2", "_source": "ema", "_has_data": True},
        ]
    )

    cards, _, payloads = completed_figures.build_completed_overview_summary(
        (status_df, "Subject_ID", "Sensor"),
        {"smartphone", "ema"},
    )

    assert [_card_value(card) for card in cards] == [
        "1 / 2 complete",
        "1 / 2 complete",
        "2 / 2 complete",
    ]
    assert payloads == {}
    assert all(card.to_plotly_json()["type"] == "Div" for card in cards)


def test_completed_sensor_summary_is_all_time_and_not_clickable():
    timeline = pd.DataFrame(
        [
            {"Subject_ID": "1", "Sensor": "steps", "Study_day": 1, "Data_per_day": 10},
            {"Subject_ID": "1", "Sensor": "heart_rate", "Study_day": 1, "Data_per_day": 20},
            {"Subject_ID": "2", "Sensor": "steps", "Study_day": 1, "Data_per_day": 0},
            {"Subject_ID": "2", "Sensor": "steps", "Study_day": 2, "Data_per_day": 5},
        ]
    )

    with patch.object(completed_figures, "load_subject_timeline_data", return_value=timeline):
        cards, _, payloads = completed_figures.build_completed_sensor_summary(
            "study",
            "data_quality",
        )

    assert [_card_value(card) for card in cards] == ["2 / 2", "2", "2", "35"]
    assert payloads == {}
    assert all(card.to_plotly_json()["type"] == "Div" for card in cards)
