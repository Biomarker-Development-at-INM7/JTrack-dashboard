"""Overview and live-monitoring figure builders."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html
from django.utils.translation import gettext_lazy as _

from jdash.analytics.data.study_metadata import get_analytics_study_json
from jdash.config import constants as constants

from ..data.dashboard_data import (
    DEFAULT_DATA_QUALITY_FOLDER,
    apply_filter,
    device_sensor_names,
    first_matching_column,
    load_data_per_day_overview,
    load_quality_csv,
    load_subject_timeline_data,
    normalize_column_name,
    visible_analytics_tabs,
)
from .common_figures import (
    add_coverage_percent_column,
    blank_quality_figure,
    finish_quality_figure,
    issue_status,
    status_color,
    timeline_x_column,
)
from .details_metrics import (
    _dataframe_with_metrics as details_dataframe_with_metrics,
    _empty_figure as details_empty_figure,
    _subject_coverage_figure as details_subject_coverage_figure,
)
from .ema_figures import build_ema_subject_timeline_figure
from .sensor_figures import (
    build_subject_timeline_daily_coverage_figure,
    build_subject_timeline_daily_volume_figure,
)


def format_kpi_value(value, fallback="--"):
    if value is None:
        return fallback
    if isinstance(value, float) and pd.isna(value):
        return fallback
    return str(value)


def kpi_status_color(status):
    if status == "healthy":
        return "#198754"
    if status == "warning":
        return "#f59f00"
    if status == "critical":
        return "#dc3545"
    return "#6c757d"


def kpi_card(
    label,
    value,
    subtitle="",
    status="neutral",
    drilldown_key=None,
    action=None,
):
    accent = kpi_status_color(status)
    label_content = html.Div(
        label,
        className="analytics-kpi-label",
        style={
            "color": "#6c757d",
            "fontSize": "0.78rem",
            "fontWeight": 600,
            "letterSpacing": "0",
            "textTransform": "uppercase",
        },
    )
    if action is not None:
        label_content = html.Div(
            [label_content, action],
            className="analytics-kpi-card-header",
        )

    children = [
            label_content,
            html.Div(
                format_kpi_value(value),
                className="analytics-kpi-value",
                style={
                    "marginTop": "0.25rem",
                    "color": "#212529",
                    "fontSize": "1.9rem",
                    "fontWeight": 600,
                    "lineHeight": "1.1",
                },
            ),
            html.Div(
                subtitle,
                className="analytics-kpi-subtitle",
                style={"marginTop": "0.35rem", "color": "#6c757d", "fontSize": "0.75rem"},
            ),
        ]
    component = html.Button if drilldown_key else html.Div
    component_args = {
        "children": children,
        "className": "analytics-kpi-card" + (" analytics-drilldown-card" if drilldown_key else ""),
        "style": {
            "padding": "1rem",
            "border": "1px solid #eef2f5",
            "borderTop": f"3px solid {accent}",
            "borderRadius": "0.45rem",
            "background": "#ffffff",
            "textAlign": "left",
        },
    }
    if drilldown_key:
        component_args.update(
            {
                "id": {"type": "analytics-drilldown", "key": drilldown_key},
                "n_clicks": 0,
                "n_clicks_timestamp": -1,
                "type": "button",
            }
        )
    return component(**component_args)


def parse_known_datetime_series(values):
    text = pd.Series(values).astype("string").str.strip()
    text = text.replace(
        {
            "": pd.NA,
            "none": pd.NA,
            "None": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "NaT": pd.NA,
        }
    )
    parsed = pd.Series(pd.NaT, index=text.index, dtype="datetime64[ns]")
    for date_format in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d-%b-%y",
    ):
        mask = parsed.isna() & text.notna()
        if not mask.any():
            break
        parsed.loc[mask] = pd.to_datetime(text.loc[mask], format=date_format, errors="coerce")
    return parsed


def format_display_date(value):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return "--"
    parsed = parse_known_datetime_series([value]).iloc[0]
    if pd.isna(parsed):
        return str(value)
    return parsed.strftime("%d-%b-%Y")


def latest_stream_activity(timeline_df, value_candidates, subjects=None):
    if timeline_df is None or timeline_df.empty:
        return None

    subject_col = first_matching_column(timeline_df.columns, ["Subject_ID", "subject_id", "subject"])
    day_col = first_matching_column(timeline_df.columns, ["Study_day", "study_day"])
    date_col = first_matching_column(timeline_df.columns, ["Date", "date"])
    value_col = first_matching_column(timeline_df.columns, value_candidates)
    if not subject_col or not value_col:
        return None

    activity_df = timeline_df.copy()
    if subjects:
        selected = subjects if isinstance(subjects, (list, tuple, set)) else [subjects]
        activity_df = activity_df[activity_df[subject_col].astype(str).isin([str(value) for value in selected])]
    if activity_df.empty:
        return None

    enrolled_subjects = activity_df[subject_col].dropna().astype(str).nunique()
    activity_df[value_col] = pd.to_numeric(activity_df[value_col], errors="coerce").fillna(0)
    active_df = activity_df[activity_df[value_col] > 0].copy()
    if active_df.empty:
        return {
            "latest_day": None,
            "latest_date": None,
            "subjects_recent": 0,
            "enrolled_subjects": enrolled_subjects,
            "latest_volume": 0,
        }

    if day_col:
        active_df[day_col] = pd.to_numeric(active_df[day_col], errors="coerce")
        latest_day = active_df[day_col].max()
        latest_df = active_df[active_df[day_col] == latest_day]
    elif date_col:
        active_df["_parsed_date"] = parse_known_datetime_series(active_df[date_col])
        latest_day = None
        latest_date_value = active_df["_parsed_date"].max()
        latest_df = active_df[active_df["_parsed_date"] == latest_date_value]
    else:
        latest_day = None
        latest_df = active_df

    latest_date = None
    if date_col and not latest_df.empty:
        latest_date_values = latest_df[date_col].dropna().astype(str)
        latest_date = latest_date_values.iloc[0] if not latest_date_values.empty else None

    return {
        "latest_day": latest_day,
        "latest_date": latest_date,
        "subjects_recent": latest_df[subject_col].dropna().astype(str).nunique(),
        "enrolled_subjects": enrolled_subjects,
        "latest_volume": int(pd.to_numeric(latest_df[value_col], errors="coerce").fillna(0).sum()),
    }


def stream_kpi_status(recent_subjects, enrolled_subjects):
    if not enrolled_subjects:
        return "neutral"
    ratio = recent_subjects / max(enrolled_subjects, 1)
    if ratio >= 0.8:
        return "healthy"
    if ratio >= 0.5:
        return "warning"
    return "critical"


def no_data_over_two_days_summary(study_name):
    subject_df = load_quality_csv(study_name, "Study_overview_subject_status.csv")
    if subject_df is None or subject_df.empty:
        return None

    latest_col = first_matching_column(subject_df.columns, ["Latest_study_day"])
    last_col = first_matching_column(subject_df.columns, ["Last_data_day"])
    subject_col = first_matching_column(subject_df.columns, ["Subject_ID", "subject_id", "subject"])
    if not latest_col or not last_col or not subject_col:
        return None

    summary_df = subject_df[[subject_col, latest_col, last_col]].drop_duplicates(subset=[subject_col]).copy()
    latest_day = pd.to_numeric(summary_df[latest_col], errors="coerce")
    last_data_day = pd.to_numeric(summary_df[last_col], errors="coerce")
    stale_subjects = (last_data_day.isna() | ((latest_day - last_data_day) > 2)).sum()
    expected_subjects = max(len(summary_df), 1)
    stale_percent = round((stale_subjects / expected_subjects) * 100, 2)
    return stale_percent, issue_status(stale_percent)


def _recency_status(days_since):
    days_since = pd.to_numeric(days_since, errors="coerce")
    if pd.isna(days_since):
        return "critical"
    if days_since <= 2:
        return "healthy"
    if days_since <= 7:
        return "warning"
    return "critical"


def _recency_label(days_since):
    status = _recency_status(days_since)
    if status == "healthy":
        return str(_("on track"))
    if status == "warning":
        return str(_("check soon"))
    return str(_("follow up"))


def _selected_subject_values(subjects):
    if not subjects:
        return []
    if isinstance(subjects, (list, tuple, set)):
        return [str(value) for value in subjects]
    return [str(subjects)]


def _single_selected_subject(subjects):
    selected = _selected_subject_values(subjects)
    return selected[0] if len(selected) == 1 else None


def _subject_stream_group(sensor_group, sensor, device_sensors):
    group = normalize_column_name(sensor_group)
    sensor_name = str(sensor or "").strip()
    normalized_sensor = normalize_column_name(sensor_name)

    if group == "ema" or normalized_sensor == constants.ema:
        return "ema"
    if group in ("garmin", "wearable", "wearables", "device_sensor", "device_sensors"):
        return "device_sensor"
    if sensor_name in device_sensors or "garmin" in normalized_sensor or "wearable" in normalized_sensor:
        return "device_sensor"
    if group in ("smartphone", "phone", "passive_sensor", "passive_sensors", "sensor", "sensors"):
        return "smartphone"
    return "other"


def _subject_latest_stream_dates(study_name, subject_id):
    status_df = load_quality_csv(study_name, "Study_overview_subject_sensor_status.csv")
    if status_df is None or status_df.empty:
        return {}, None

    subject_col = first_matching_column(status_df.columns, ["Subject_ID", "subject_id", "subject"])
    date_joined_col = first_matching_column(status_df.columns, ["Date_joined", "date_joined", "Joined_date"])
    sensor_group_col = first_matching_column(status_df.columns, ["Sensor_group", "sensor_group", "Group"])
    sensor_col = first_matching_column(status_df.columns, ["Sensor", "sensor"])
    last_date_col = first_matching_column(
        status_df.columns,
        ["Last_data_received_date", "Last_any_data_date", "Last_data_date"],
    )
    if not subject_col:
        return {}, None

    subject_rows = status_df[status_df[subject_col].astype(str).eq(str(subject_id))].copy()
    if subject_rows.empty:
        return {}, None

    date_joined = None
    if date_joined_col:
        joined_values = subject_rows[date_joined_col].dropna().astype(str)
        joined_values = joined_values[joined_values.str.strip().astype(bool)]
        if not joined_values.empty:
            date_joined = joined_values.iloc[0]

    if not sensor_col or not last_date_col:
        return {}, date_joined

    device_sensors = device_sensor_names(study_name, subject_rows[sensor_col].dropna().astype(str).unique())
    stream_dates = {"smartphone": None, "device_sensor": None, "ema": None}
    for _index, row in subject_rows.iterrows():
        stream = _subject_stream_group(
            row.get(sensor_group_col) if sensor_group_col else "",
            row.get(sensor_col),
            device_sensors,
        )
        if stream not in stream_dates:
            continue
        parsed_date = parse_known_datetime_series([row.get(last_date_col)]).iloc[0]
        if pd.isna(parsed_date):
            continue
        if stream_dates[stream] is None or parsed_date > stream_dates[stream]:
            stream_dates[stream] = parsed_date

    return stream_dates, date_joined


def _status_subject_overview(study_name, subjects=None):
    status_df = load_quality_csv(study_name, "Study_overview_subject_status.csv")
    if status_df is None or status_df.empty:
        return pd.DataFrame()

    subject_col = first_matching_column(status_df.columns, ["Subject_ID", "subject_id", "subject"])
    latest_col = first_matching_column(
        status_df.columns,
        ["Latest_expected_day", "Latest_study_day", "Current_study_day", "Study_day"],
    )
    last_data_col = first_matching_column(
        status_df.columns,
        ["Last_any_data_day", "Last_data_day", "Last_adherent_day"],
    )
    last_date_col = first_matching_column(
        status_df.columns,
        ["Last_any_data_date", "Last_data_date", "Last_adherent_date"],
    )
    if not subject_col:
        return pd.DataFrame()

    overview = status_df.copy()
    overview[subject_col] = overview[subject_col].fillna("").astype(str)
    overview = overview[overview[subject_col].astype(bool)]
    overview = apply_filter(overview, subject_col, subjects)
    if overview.empty:
        return pd.DataFrame()

    aggregate = {}
    if latest_col:
        overview[latest_col] = pd.to_numeric(overview[latest_col], errors="coerce")
        aggregate[latest_col] = "max"
    if last_data_col:
        overview[last_data_col] = pd.to_numeric(overview[last_data_col], errors="coerce")
        aggregate[last_data_col] = "max"
    if last_date_col:
        aggregate[last_date_col] = "last"
    if not aggregate:
        return overview[[subject_col]].drop_duplicates().rename(columns={subject_col: "Subject_ID"})

    summary = overview.groupby(subject_col, as_index=False).agg(aggregate)
    summary = summary.rename(columns={subject_col: "Subject_ID"})
    if latest_col:
        summary = summary.rename(columns={latest_col: "Latest_expected_day"})
    if last_data_col:
        summary = summary.rename(columns={last_data_col: "Last_any_data_day"})
    if last_date_col:
        summary = summary.rename(columns={last_date_col: "Last_any_data_date"})

    if "Latest_expected_day" in summary.columns and "Last_any_data_day" in summary.columns:
        summary["Days_since_last_data"] = (
            summary["Latest_expected_day"] - summary["Last_any_data_day"]
        )
    else:
        summary["Days_since_last_data"] = pd.NA
    summary["Recency_status"] = summary["Days_since_last_data"].map(_recency_status)
    summary["Recency_label"] = summary["Days_since_last_data"].map(_recency_label)
    return summary


def subject_raw_download_action():
    """Return the persistent download target used by raw-subject callbacks."""
    return html.A(
        html.I(
            className="fas fa-download",
            **{"aria-hidden": "true"},
        ),
        id="subject-raw-data-download",
        href=None,
        download="",
        className="analytics-subject-download-button",
        title=str(_("Download subject data")),
        **{"aria-label": str(_("Download subject data"))},
        style={"display": "none"},
    )


def _available_subject_profile_streams(sensors_map, study_name):
    """Return stream KPI keys using the same rules as the dashboard tabs."""
    tabs = visible_analytics_tabs(sensors_map, study_name)
    streams = set()
    if "sensor-data" in tabs:
        streams.add("smartphone")
    if "device-sensor-data" in tabs:
        streams.add("device_sensor")
    if "ema-data" in tabs:
        streams.add("ema")
    return streams


def build_subject_profile_summary(study_name, subjects=None, sensors_map=None):
    subject_id = _single_selected_subject(subjects)
    if not study_name or not subject_id:
        # Keep this callback Output in the layout even before a subject is
        # selected. Dash validates callback targets before concurrent updates
        # have finished rendering the selected-subject profile.
        return subject_raw_download_action()

    status_summary = _status_subject_overview(study_name, [subject_id])
    status_row = status_summary.iloc[0].to_dict() if not status_summary.empty else {}
    stream_dates, date_joined = _subject_latest_stream_dates(study_name, subject_id)
    current_day = status_row.get("Latest_expected_day")
    days_since = status_row.get("Days_since_last_data")
    status = status_row.get("Recency_status") or _recency_status(days_since)
    status_label = status_row.get("Recency_label") or _recency_label(days_since)

    current_day_value = "--" if pd.isna(current_day) else f"{float(current_day):.0f}"

    cards = [
            kpi_card(
                str(_("Subject ID")),
                subject_id,
                f"{str(_('current follow-up status'))}: {status_label}",
                status,
                action=subject_raw_download_action(),
            ),
            kpi_card(
                str(_("Date Joined")),
                format_display_date(date_joined),
                str(_("study enrollment date")),
            ),
            kpi_card(
                str(_("Current Study Day")),
                current_day_value,
                str(_("where the subject is in the study")),
            ),
    ]
    available_streams = _available_subject_profile_streams(sensors_map, study_name)
    if "smartphone" in available_streams:
        cards.append(
            kpi_card(
                str(_("Smartphone Sensors")),
                format_display_date(stream_dates.get("smartphone")),
                str(_("latest smartphone data")),
            )
        )
    if "device_sensor" in available_streams:
        cards.append(
            kpi_card(
                str(_("Wearables")),
                format_display_date(stream_dates.get("device_sensor")),
                str(_("latest wearable data")),
            )
        )
    if "ema" in available_streams:
        cards.append(
            kpi_card(
                str(_("EMA")),
                format_display_date(stream_dates.get("ema")),
                str(_("latest EMA response")),
            )
        )

    return html.Div(
        cards,
        className="analytics-subject-profile-grid",
    )


def build_subject_stream_progression_figure(card, study_name, subjects=None, timeline_axis=None):
    title = str(card.get("title") or _("Subject Progression"))
    subject_id = _single_selected_subject(subjects)
    if not study_name or not subject_id:
        return blank_quality_figure(title, _("Select one subject to view their progression."))

    stream = card.get("subject_detail_stream")
    if stream == "ema":
        df = load_subject_timeline_data(study_name, "ema_data_quality")
        if df is None or df.empty:
            return blank_quality_figure(title, _("No EMA timeline data available."))
        return build_ema_subject_timeline_figure(df, [subject_id], timeline_axis, title)

    quality_folder = "garmin_data_quality" if stream == "device_sensor" else DEFAULT_DATA_QUALITY_FOLDER
    fig = build_subject_timeline_daily_volume_figure(
        study_name,
        quality_folder,
        None,
        [subject_id],
        timeline_axis,
        title,
    )
    if fig is None:
        return blank_quality_figure(title)
    return fig


def _data_per_day_columns(df, timeline_axis=None):
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    study_day_col = first_matching_column(df.columns, ["Study_day", "study_day"])
    date_col = first_matching_column(df.columns, ["Date", "date", "Data", "data"])
    value_col = first_matching_column(
        df.columns,
        ["Data_per_day", "data_per_day", "Total_records", "records"],
    )
    x_col = timeline_x_column(df, timeline_axis)
    return subject_col, study_day_col, date_col, value_col, x_col


def _overview_data_per_day_frame(study_name, subjects=None, timeline_axis=None):
    df = load_data_per_day_overview(study_name)
    if df is None or df.empty:
        return None, None, None, None, None, None

    subject_col, study_day_col, date_col, value_col, x_col = _data_per_day_columns(df, timeline_axis)
    if not subject_col or not value_col or not x_col:
        return None, subject_col, study_day_col, date_col, value_col, x_col

    overview_df = df.copy()
    overview_df[subject_col] = overview_df[subject_col].fillna("").astype(str)
    overview_df = overview_df[overview_df[subject_col].astype(bool)]
    overview_df = apply_filter(overview_df, subject_col, subjects)
    overview_df[value_col] = pd.to_numeric(overview_df[value_col], errors="coerce").fillna(0)
    if study_day_col:
        overview_df[study_day_col] = pd.to_numeric(overview_df[study_day_col], errors="coerce")
    if date_col:
        overview_df["_parsed_date"] = parse_known_datetime_series(overview_df[date_col])
    return overview_df, subject_col, study_day_col, date_col, value_col, x_col


def _has_received_data(values):
    normalized = pd.Series(values, dtype="string").str.strip().str.lower()
    return normalized.notna() & ~normalized.isin(["", "--", "none", "nan", "nat"])


def _overview_follow_up_buckets(study_name, subjects=None):
    status_df = load_quality_csv(study_name, "Study_overview_subject_sensor_status.csv")
    if status_df is None or status_df.empty:
        return {
            "total": 0,
            "on_track": [],
            "check_soon": [],
            "follow_up": [],
            "no_data": [],
        }

    subject_col = first_matching_column(status_df.columns, ["Subject_ID", "subject_id", "subject"])
    last_date_col = first_matching_column(
        status_df.columns,
        ["Last_data_received_date", "Last_any_data_date", "Last_data_date"],
    )
    days_since_col = first_matching_column(
        status_df.columns,
        ["Days_since_last_data_received", "Days_since_last_any_data", "Days_since_last_data"],
    )
    if not subject_col or not last_date_col or not days_since_col:
        return {
            "total": 0,
            "on_track": [],
            "check_soon": [],
            "follow_up": [],
            "no_data": [],
        }

    table_df = status_df[[subject_col, last_date_col, days_since_col]].copy()
    table_df[subject_col] = table_df[subject_col].fillna("").astype(str)
    table_df = table_df[table_df[subject_col].astype(bool)]
    table_df = apply_filter(table_df, subject_col, subjects)
    if table_df.empty:
        return {
            "total": 0,
            "on_track": [],
            "check_soon": [],
            "follow_up": [],
            "no_data": [],
        }

    table_df["_has_data"] = _has_received_data(table_df[last_date_col])
    table_df["_days_since"] = pd.to_numeric(table_df[days_since_col], errors="coerce")
    subject_status = (
        table_df.groupby(subject_col, as_index=False)
        .agg(has_data=("_has_data", "max"), days_since=("_days_since", "max"))
    )

    has_data = subject_status["has_data"]
    days_since = subject_status["days_since"]
    known_recency = has_data & days_since.notna()

    def subject_ids(mask):
        return sorted(subject_status.loc[mask, subject_col].astype(str).tolist())

    return {
        "total": len(subject_status),
        "on_track": subject_ids(known_recency & days_since.le(1)),
        "check_soon": subject_ids(known_recency & days_since.between(2, 5, inclusive="both")),
        "follow_up": subject_ids(known_recency & days_since.gt(5)),
        "no_data": subject_ids(~has_data),
    }


def overview_activity_findings(study_name, subjects=None):
    finding_keys = ("current_gap", "consecutive_gap", "repeated_gap", "activity_decline")
    findings = {key: [] for key in finding_keys}
    data_df, subject_col, study_day_col, _date_col, value_col, _x_col = _overview_data_per_day_frame(
        study_name,
        subjects,
        "study_day",
    )
    status_summary = _status_subject_overview(study_name, subjects)
    if (
        data_df is None
        or data_df.empty
        or not subject_col
        or not study_day_col
        or not value_col
        or status_summary.empty
        or "Latest_expected_day" not in status_summary.columns
    ):
        return findings

    daily = (
        data_df.dropna(subset=[study_day_col])
        .groupby([subject_col, study_day_col], as_index=False)[value_col]
        .sum()
    )
    if daily.empty:
        return findings

    daily[study_day_col] = pd.to_numeric(daily[study_day_col], errors="coerce")
    daily[value_col] = pd.to_numeric(daily[value_col], errors="coerce").fillna(0)
    daily = daily.dropna(subset=[study_day_col])

    for _index, status_row in status_summary.iterrows():
        subject_id = str(status_row.get("Subject_ID") or "").strip()
        current_day = pd.to_numeric(status_row.get("Latest_expected_day"), errors="coerce")
        if not subject_id or pd.isna(current_day):
            continue

        current_day = int(current_day)
        subject_daily = daily[daily[subject_col].astype(str).eq(subject_id)]
        if subject_daily.empty:
            continue

        subject_daily = subject_daily[subject_daily[study_day_col].le(current_day)]
        if subject_daily.empty:
            continue

        first_expected_day = int(subject_daily[study_day_col].min())
        day_values = (
            subject_daily.groupby(study_day_col)[value_col]
            .sum()
            .to_dict()
        )

        def volume_for_day(day):
            return float(day_values.get(day, 0) or 0)

        if volume_for_day(current_day) <= 0:
            findings["current_gap"].append(subject_id)

        if current_day - first_expected_day >= 2:
            latest_three = range(current_day - 2, current_day + 1)
            if all(volume_for_day(day) <= 0 for day in latest_three):
                findings["consecutive_gap"].append(subject_id)

        if current_day - first_expected_day >= 6:
            latest_seven = range(current_day - 6, current_day + 1)
            if sum(volume_for_day(day) <= 0 for day in latest_seven) >= 3:
                findings["repeated_gap"].append(subject_id)

        if current_day - first_expected_day >= 13:
            recent_volume = sum(volume_for_day(day) for day in range(current_day - 6, current_day + 1))
            previous_volume = sum(volume_for_day(day) for day in range(current_day - 13, current_day - 6))
            if previous_volume > 0 and recent_volume <= previous_volume * 0.5:
                findings["activity_decline"].append(subject_id)

    return {key: sorted(set(subject_ids)) for key, subject_ids in findings.items()}


def activity_finding_card(label, subject_ids, subtitle, status, drilldown_key=None):
    preview_limit = 3
    preview = ", ".join(subject_ids[:preview_limit])
    if len(subject_ids) > preview_limit:
        preview = f"{preview} +{len(subject_ids) - preview_limit} {str(_('more'))}"
    if not preview:
        preview = str(_("No subjects identified"))

    effective_status = status if subject_ids else "healthy"
    children = [
            html.Div(
                [
                    html.Div(str(label), className="analytics-finding-label"),
                    html.Div(str(len(subject_ids)), className="analytics-finding-count"),
                ],
                className="analytics-finding-heading",
            ),
            html.Div(str(subtitle), className="analytics-finding-subtitle"),
            html.Div(preview, className="analytics-finding-subjects"),
        ]
    component = html.Button if drilldown_key and subject_ids else html.Div
    component_args = {
        "children": children,
        "className": (
            f"analytics-finding-card analytics-finding-card--{effective_status}"
            + (" analytics-drilldown-card" if component is html.Button else "")
        ),
    }
    if component is html.Button:
        component_args.update(
            {
                "id": {"type": "analytics-drilldown", "key": drilldown_key},
                "n_clicks": 0,
                "n_clicks_timestamp": -1,
                "type": "button",
            }
        )
    return component(**component_args)


def build_overview_activity_alerts(study_name, subjects=None):
    findings = overview_activity_findings(study_name, subjects)
    return html.Div(
        [
            html.Div(str(_("Activity Findings")), className="analytics-finding-section-title"),
            html.Div(
                [
                    activity_finding_card(
                        _("Current-day Gaps"),
                        findings["current_gap"],
                        _("No data on the current expected study day"),
                        "warning",
                    ),
                    activity_finding_card(
                        _("Consecutive Gaps"),
                        findings["consecutive_gap"],
                        _("No data for three consecutive study days"),
                        "critical",
                    ),
                    activity_finding_card(
                        _("Repeated Gaps"),
                        findings["repeated_gap"],
                        _("At least three zero-data days in the latest seven study days"),
                        "warning",
                    ),
                    activity_finding_card(
                        _("Activity Decline"),
                        findings["activity_decline"],
                        _("Latest seven-day volume is at least 50% below the previous seven days"),
                        "critical",
                    ),
                ],
                className="analytics-finding-grid",
            ),
        ],
        className="analytics-finding-section",
    )


def build_subject_data_per_day_heatmap(study_name, subjects=None, timeline_axis=None, title=None):
    df, subject_col, study_day_col, date_col, value_col, x_col = _overview_data_per_day_frame(
        study_name,
        subjects,
        timeline_axis,
    )
    if df is None or df.empty:
        return blank_quality_figure(str(title or _("Subject Activity by Study Day")))
    if not subject_col or not x_col or not value_col:
        return blank_quality_figure(
            str(title or _("Subject Activity by Study Day")),
            _("Subject activity data is missing subject, study day/date, or data amount columns."),
        )

    heatmap_df = df.copy()
    x_is_study_day = normalize_column_name(x_col) == "study_day"
    if x_is_study_day:
        heatmap_df = heatmap_df.dropna(subset=[x_col])
        heatmap_df[x_col] = heatmap_df[x_col].astype(int)
    else:
        heatmap_df[x_col] = heatmap_df[x_col].fillna("").astype(str)
        heatmap_df = heatmap_df[heatmap_df[x_col].astype(bool)]
    if heatmap_df.empty:
        return blank_quality_figure(str(title or _("Subject Activity by Study Day")))

    daily = (
        heatmap_df
        .groupby([subject_col, x_col], as_index=False)[value_col]
        .sum()
    )
    if daily.empty:
        return blank_quality_figure(str(title or _("Subject Activity by Study Day")))

    matrix = daily.pivot_table(
        index=subject_col,
        columns=x_col,
        values=value_col,
        aggfunc="sum",
        fill_value=0,
    )
    status_summary = _status_subject_overview(study_name, subjects)
    if not status_summary.empty and "Subject_ID" in status_summary.columns:
        status_subjects = status_summary["Subject_ID"].dropna().astype(str).tolist()
        status_subjects = [subject for subject in status_subjects if subject]
        if status_subjects:
            matrix = matrix.reindex(sorted(set(matrix.index).union(status_subjects)), fill_value=0)

    if x_is_study_day:
        day_values = list(pd.to_numeric(matrix.columns, errors="coerce").dropna().astype(int))
        if not status_summary.empty and "Latest_expected_day" in status_summary.columns:
            day_values += list(
                pd.to_numeric(status_summary["Latest_expected_day"], errors="coerce").dropna().astype(int)
            )
        if day_values:
            min_day = min(day_values)
            max_day = max(day_values)
            if max_day >= min_day and (max_day - min_day) <= 2000:
                matrix = matrix.reindex(columns=list(range(min_day, max_day + 1)), fill_value=0)
            else:
                matrix = matrix.reindex(columns=sorted(set(day_values)), fill_value=0)
    elif date_col and "_parsed_date" in heatmap_df.columns:
        order_df = heatmap_df[[x_col, "_parsed_date"]].drop_duplicates()
        order_df = order_df.sort_values(["_parsed_date", x_col], na_position="last")
        matrix = matrix.reindex(columns=order_df[x_col].dropna().astype(str).tolist(), fill_value=0)
    else:
        matrix = matrix.reindex(columns=sorted(matrix.columns), fill_value=0)

    if not status_summary.empty and "Days_since_last_data" in status_summary.columns:
        status_order = status_summary.copy()
        status_order["sort_days_since"] = pd.to_numeric(
            status_order["Days_since_last_data"],
            errors="coerce",
        ).fillna(999999)
        status_order = status_order.sort_values(["sort_days_since", "Subject_ID"], ascending=[False, True])
        ordered_subjects = [subject for subject in status_order["Subject_ID"].astype(str) if subject in matrix.index]
        ordered_subjects += sorted(subject for subject in matrix.index if subject not in ordered_subjects)
        matrix = matrix.reindex(ordered_subjects)
    else:
        matrix = matrix.reindex(sorted(matrix.index))

    actual_values = matrix.copy().apply(pd.to_numeric, errors="coerce").fillna(0)
    positive_values = actual_values.to_numpy().ravel()
    positive_values = positive_values[positive_values > 0]
    zmax = float(np.percentile(positive_values, 95)) if len(positive_values) else 1
    zmax = max(zmax, 1)
    plot_values = actual_values.clip(upper=zmax)

    status_lookup = {}
    if not status_summary.empty and "Subject_ID" in status_summary.columns:
        for _index, row in status_summary.iterrows():
            subject = str(row.get("Subject_ID") or "")
            if not subject:
                continue
            status_lookup[subject] = {
                "days_since": row.get("Days_since_last_data"),
                "latest_day": row.get("Latest_expected_day"),
                "last_data_day": row.get("Last_any_data_day"),
                "last_data_date": row.get("Last_any_data_date"),
                "label": row.get("Recency_label") or _recency_label(row.get("Days_since_last_data")),
                "status": row.get("Recency_status") or _recency_status(row.get("Days_since_last_data")),
            }

    status_text = []
    for subject in actual_values.index:
        status_info = status_lookup.get(str(subject), {})
        label = status_info.get("label", "")
        row_text = []
        for column in actual_values.columns:
            current_cell = False
            if x_is_study_day and status_info.get("latest_day") is not None:
                latest_day = pd.to_numeric(status_info.get("latest_day"), errors="coerce")
                current_cell = pd.notna(latest_day) and int(latest_day) == int(column)
            row_text.append(str(label) if current_cell else "")
        status_text.append(row_text)

    customdata = np.dstack((actual_values.to_numpy(), np.array(status_text, dtype=object)))
    fig = go.Figure(
        data=[
            go.Heatmap(
                z=plot_values.to_numpy(),
                x=list(plot_values.columns),
                y=list(plot_values.index),
                customdata=customdata,
                zmin=0,
                zmax=zmax,
                colorscale=[
                    [0.0, "#eef2f5"],
                    [0.0001, "#eef2f5"],
                    [0.35, "#ccece7"],
                    [0.75, "#4db6ac"],
                    [1.0, "#00796b"],
                ],
                colorbar={
                    "title": {"text": str(_("Data received"))},
                    "thickness": 14,
                    "len": 0.72,
                },
                xgap=1,
                ygap=1,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    f"{str(_('Study day') if x_is_study_day else _('Date'))}: %{{x}}<br>"
                    f"{str(_('Data received'))}: %{{customdata[0]:,.0f}}<br>"
                    f"{str(_('Follow-up status'))}: %{{customdata[1]}}<extra></extra>"
                ),
            )
        ]
    )

    marker_x = []
    marker_y = []
    marker_colors = []
    marker_custom = []
    for subject, status_info in status_lookup.items():
        if subject not in actual_values.index:
            continue
        marker_value = None
        if x_is_study_day:
            latest_day = pd.to_numeric(status_info.get("latest_day"), errors="coerce")
            if pd.notna(latest_day):
                marker_value = int(latest_day)
        elif status_info.get("last_data_date"):
            marker_value = str(status_info.get("last_data_date"))
        if marker_value is None or marker_value not in actual_values.columns:
            continue
        marker_x.append(marker_value)
        marker_y.append(subject)
        marker_colors.append(status_color(status_info.get("status")))
        days_since = status_info.get("days_since")
        marker_custom.append(
            [
                status_info.get("label") or "",
                "--" if pd.isna(days_since) else f"{float(days_since):.0f}",
                status_info.get("last_data_day") if status_info.get("last_data_day") is not None else "--",
                status_info.get("last_data_date") or "--",
            ]
        )

    if marker_x:
        fig.add_trace(
            go.Scatter(
                x=marker_x,
                y=marker_y,
                mode="markers",
                marker={
                    "symbol": "square",
                    "size": 15,
                    "color": marker_colors,
                    "line": {"color": "#ffffff", "width": 2},
                },
                customdata=marker_custom,
                name=str(_("Current study day")),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    f"{str(_('Current study day'))}: %{{x}}<br>"
                    f"{str(_('Status'))}: %{{customdata[0]}}<br>"
                    f"{str(_('Days since last data'))}: %{{customdata[1]}}<br>"
                    f"{str(_('Last data day'))}: %{{customdata[2]}}<br>"
                    f"{str(_('Last data date'))}: %{{customdata[3]}}<extra></extra>"
                ),
            )
        )

    fig = finish_quality_figure(fig)
    fig.update_layout(
        height=max(420, min(920, 26 * len(actual_values.index) + 150)),
        margin=dict(l=24, r=24, t=8, b=54),
        hovermode="closest",
        legend=dict(
            title=None,
            orientation="h",
            yanchor="bottom",
            y=1.0,
            xanchor="left",
            x=0,
            font={"size": 10},
        ),
    )
    fig.update_xaxes(
        title=str(_("Study day") if x_is_study_day else _("Date")),
        type="category" if x_is_study_day else None,
        showgrid=True,
        gridcolor="#eef2f5",
        nticks=14,
    )
    fig.update_yaxes(title=None, autorange="reversed")
    return fig

def live_sensor_coverage_summary(study_name):
    metrics = live_sensor_coverage_metrics(study_name)
    if not metrics:
        return None

    coverage_percent = round(float(np.mean([metric["coverage"] for metric in metrics])), 2)
    if coverage_percent < 50:
        status = "critical"
    elif coverage_percent < 80:
        status = "warning"
    else:
        status = "healthy"
    return coverage_percent, status

def dashboard_subject_key(subject_name):
    value = str(subject_name or "").strip()
    return value[:-2] if len(value) > 2 else value

def local_dashboard_metrics(study_name, include_ema=True):
    df, sensors, total_subjects = _details_metrics_data(study_name)
    if df.empty:
        return df, [], 0

    if not include_ema:
        sensors = [sensor for sensor in sensors if str(sensor).strip().lower() != constants.ema]

    return df, sensors, total_subjects

def local_last_received_columns(df, sensors):
    sensor_columns = [f"{sensor} last_time_received" for sensor in sensors]
    available_sensor_columns = [column for column in sensor_columns if column in df.columns]
    legacy_columns = [
        column
        for column in df.columns
        if str(column).startswith("last_time_received_")
    ]
    return sorted(set(available_sensor_columns + legacy_columns))

def coverage_status(coverage):
    if coverage < 50:
        return "critical"
    if coverage < 80:
        return "warning"
    return "healthy"

def subject_count_with_sensor_data(df, sensor):
    column = f"{sensor} n_batches"
    if column not in df.columns:
        return 0

    batches = pd.to_numeric(df[column], errors="coerce").fillna(0)
    if "subject_name" not in df.columns:
        return int(batches.gt(0).sum())

    sensor_df = pd.DataFrame(
        {
            "subject_key": df["subject_name"].map(dashboard_subject_key),
            "has_data": batches.gt(0),
        }
    )
    sensor_df = sensor_df[sensor_df["subject_key"].astype(bool)]
    if sensor_df.empty:
        return 0
    return int(sensor_df.groupby("subject_key")["has_data"].max().sum())

def live_sensor_coverage_metrics(study_name):
    df, sensors, total_subjects = local_dashboard_metrics(study_name, include_ema=False)
    if df.empty or not sensors:
        return []

    device_sensors = device_sensor_names(study_name, sensors)
    sensors = [sensor for sensor in sensors if sensor not in device_sensors]
    denominator = max(total_subjects, 1)

    metrics = []
    for sensor in sensors:
        column = f"{sensor} n_batches"
        if column not in df.columns:
            continue
        subjects_with_data = subject_count_with_sensor_data(df, sensor)
        coverage = round((subjects_with_data / denominator) * 100, 2)
        metrics.append(
            {
                "sensor": str(sensor),
                "coverage": coverage,
                "status": coverage_status(coverage),
                "subjects": subjects_with_data,
                "expected": total_subjects,
            }
        )
    return metrics

def subject_sensor_coverage_metrics(study_name):
    df, sensors, total_subjects = local_dashboard_metrics(study_name, include_ema=False)
    if df.empty or not sensors or "subject_name" not in df.columns:
        return []

    device_sensors = device_sensor_names(study_name, sensors)
    sensors = [sensor for sensor in sensors if sensor not in device_sensors]
    if not sensors:
        return []

    subject_df = df[["subject_name"] + [f"{sensor} n_batches" for sensor in sensors]].copy()
    subject_df["subject_key"] = subject_df["subject_name"].map(dashboard_subject_key)
    subject_df = subject_df[subject_df["subject_key"].astype(bool)]
    if subject_df.empty:
        return []

    sensor_columns = [f"{sensor} n_batches" for sensor in sensors]
    for column in sensor_columns:
        subject_df[column] = pd.to_numeric(subject_df[column], errors="coerce").fillna(0)

    subject_has_sensor = subject_df.groupby("subject_key")[sensor_columns].max().gt(0)
    subject_coverage = (subject_has_sensor.sum(axis=1) / max(len(sensor_columns), 1)) * 100

    total_subjects = len(subject_coverage)
    complete_subjects = int(subject_coverage.ge(80).sum())
    partial_subjects = int(subject_coverage.ge(50).mul(subject_coverage.lt(80)).sum())
    low_subjects = int(subject_coverage.lt(50).sum())
    denominator = max(total_subjects, 1)
    metrics = [
        {
            "sensor": str(_("Complete smartphone sensors")),
            "coverage": round((complete_subjects / denominator) * 100, 2),
            "status": "healthy",
            "subjects": complete_subjects,
            "expected": total_subjects,
        },
        {
            "sensor": str(_("Partial smartphone sensors")),
            "coverage": round((partial_subjects / denominator) * 100, 2),
            "status": "warning",
            "subjects": partial_subjects,
            "expected": total_subjects,
        },
        {
            "sensor": str(_("Low smartphone sensors")),
            "coverage": round((low_subjects / denominator) * 100, 2),
            "status": "critical",
            "subjects": low_subjects,
            "expected": total_subjects,
        },
    ]
    return metrics

def add_sensor_coverage_polar(fig, metrics, title, domain, subplot="polar"):
    if not metrics:
        return

    fig.add_trace(
        go.Barpolar(
            r=[metric["coverage"] for metric in metrics],
            theta=[metric["sensor"] for metric in metrics],
            marker={
                "color": [status_color(metric["status"]) for metric in metrics],
                "line": {"color": "#ffffff", "width": 2},
            },
            opacity=0.88,
            text=[
                f"{metric['sensor']}<br>{metric['coverage']}%"
                + (
                    f" ({metric['subjects']}/{metric['expected']})"
                    if metric["subjects"] is not None and metric["expected"] is not None
                    else ""
                )
                for metric in metrics
            ],
            hoverinfo="text",
            showlegend=False,
            name=str(title),
            subplot=subplot,
        )
    )
    fig.add_annotation(
        text=str(title),
        x=sum(domain["x"]) / 2,
        y=domain["y"][1] + 0.08,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 14, "color": "#212529"},
        align="center",
    )
    fig.update_layout(
        {
            subplot: {
                "domain": domain,
                "bgcolor": "#ffffff",
                "radialaxis": {
                    "range": [0, 100],
                    "ticksuffix": "%",
                    "tickfont": {"size": 9, "color": "#6c757d"},
                    "gridcolor": "#e9ecef",
                    "linecolor": "#dee2e6",
                },
                "angularaxis": {
                    "tickfont": {"size": 10, "color": "#212529"},
                    "gridcolor": "#f1f3f5",
                    "linecolor": "#dee2e6",
                },
            }
        }
    )

def _summary_metric(df, metric_name, fallback_label_contains=None):
    for _index, row in df.iterrows():
        row_metric_name = str(row.get("Metric") or "").lower()
        row_label = str(row.get("Label") or "").lower()
        if row_metric_name == metric_name or (
            fallback_label_contains and fallback_label_contains in row_label
        ):
            return row.copy()
    return None

def _summary_gauge_steps(max_value, is_issue=False):
    if is_issue:
        return [
            {"range": [0, float(max_value) * 0.1], "color": "#d1e7dd"},
            {"range": [float(max_value) * 0.1, float(max_value) * 0.25], "color": "#fff3cd"},
            {"range": [float(max_value) * 0.25, float(max_value)], "color": "#f8d7da"},
        ]
    return [
        {"range": [0, float(max_value) * 0.5], "color": "#f8d7da"},
        {"range": [float(max_value) * 0.5, float(max_value) * 0.8], "color": "#fff3cd"},
        {"range": [float(max_value) * 0.8, float(max_value)], "color": "#d1e7dd"},
    ]

def _status_for_percent(value):
    value = pd.to_numeric(value, errors="coerce")
    if pd.isna(value):
        return "critical"
    if value >= 80:
        return "healthy"
    if value >= 50:
        return "warning"
    return "critical"

def _subject_status_summary(study_name):
    df, sensors, enrolled_subjects = local_dashboard_metrics(study_name)
    if df.empty or "subject_name" not in df.columns:
        return {
            "enrolled": 0,
            "with_data": 0,
            "latest_active": 0,
            "left_study": 0,
            "silent_over_two_days": 0,
            "latest_day": None,
        }

    subject_df = df[["subject_name"]].copy()
    subject_df["subject_key"] = subject_df["subject_name"].map(dashboard_subject_key)
    subject_df = subject_df[subject_df["subject_key"].astype(bool)]
    subject_keys = subject_df["subject_key"].drop_duplicates()
    enrolled_subjects = enrolled_subjects or len(subject_keys)

    batch_columns = [f"{sensor} n_batches" for sensor in sensors if f"{sensor} n_batches" in df.columns]
    if batch_columns and enrolled_subjects:
        batches_df = df[["subject_name"] + batch_columns].copy()
        batches_df["subject_key"] = batches_df["subject_name"].map(dashboard_subject_key)
        batches_df = batches_df[batches_df["subject_key"].astype(bool)]
        for column in batch_columns:
            batches_df[column] = pd.to_numeric(batches_df[column], errors="coerce").fillna(0)
        subject_has_data = batches_df.groupby("subject_key")[batch_columns].max().gt(0).any(axis=1)
        subjects_with_data = int(subject_has_data.sum())
    else:
        subjects_with_data = 0

    latest_active = 0
    left_study = 0
    silent_over_two_days = 0
    latest_day = None

    status_col = first_matching_column(df.columns, ["status_code"])
    if status_col:
        status_df = df[["subject_name", status_col]].copy()
        status_df["subject_key"] = status_df["subject_name"].map(dashboard_subject_key)
        status_df = status_df[status_df["subject_key"].astype(bool)]
        status_df[status_col] = pd.to_numeric(status_df[status_col], errors="coerce").fillna(0)
        status_rank = {3: 0, 1: 1, 2: 2, 0: 3}
        subject_status_rank = (
            status_df[status_col]
            .map(lambda value: status_rank.get(int(value), 3))
            .groupby(status_df["subject_key"])
            .max()
        )
        left_study = int(subject_status_rank.eq(status_rank[1]).sum())

    time_columns = local_last_received_columns(df, sensors)
    if time_columns and enrolled_subjects:
        timestamp_df = df[["subject_name"] + time_columns].copy()
        timestamp_df["subject_key"] = timestamp_df["subject_name"].map(dashboard_subject_key)
        timestamp_df = timestamp_df[timestamp_df["subject_key"].astype(bool)]
        for column in time_columns:
            timestamp_df[column] = parse_known_datetime_series(timestamp_df[column])
        timestamp_df["latest_received"] = timestamp_df[time_columns].max(axis=1)
        subject_latest = timestamp_df.groupby("subject_key", as_index=False)["latest_received"].max()
        latest_received = subject_latest["latest_received"].dropna()
        if not latest_received.empty:
            latest_day = latest_received.max().normalize()
            stale_cutoff = latest_day - pd.Timedelta(days=2)
            subject_latest["latest_day"] = subject_latest["latest_received"].dt.normalize()
            latest_active = int(subject_latest["latest_day"].eq(latest_day).sum())
            silent_over_two_days = int(
                subject_latest["latest_day"].isna().sum()
                + subject_latest["latest_day"].lt(stale_cutoff).sum()
            )

    return {
        "enrolled": enrolled_subjects,
        "with_data": subjects_with_data,
        "latest_active": latest_active,
        "left_study": left_study,
        "silent_over_two_days": silent_over_two_days,
        "latest_day": latest_day,
    }

def build_monitoring_summary(study_name, title, subjects=None):
    subject_summary = _overview_follow_up_buckets(study_name, subjects)

    return [
        kpi_card(
            str(_("On Track")),
            len(subject_summary["on_track"]),
            str(_("data received within 1 study day")),
            "healthy" if subject_summary["on_track"] else "neutral",
        ),
        kpi_card(
            str(_("Check Soon")),
            len(subject_summary["check_soon"]),
            str(_("no data for 2 to 5 study days")),
            "warning" if subject_summary["check_soon"] else "healthy",
        ),
        kpi_card(
            str(_("Follow Up")),
            len(subject_summary["follow_up"]),
            str(_("no data for more than 5 study days")),
            "critical" if subject_summary["follow_up"] else "healthy",
        ),
        kpi_card(
            str(_("No Data Received")),
            len(subject_summary["no_data"]),
            str(_("no data recorded since enrollment")),
            "critical" if subject_summary["no_data"] else "healthy",
        ),
    ]


def latest_day_subtitle(activity):
    if not activity:
        return ""
    latest_day = activity.get("latest_day")
    if latest_day is None or pd.isna(latest_day):
        return str(_("latest data day"))
    try:
        latest_day_value = int(latest_day)
    except Exception:
        latest_day_value = latest_day
    return f"{str(_('study day'))} {latest_day_value}"


def build_smartphone_kpi_summary(study_name, subjects=None):
    activity = latest_stream_activity(
        load_subject_timeline_data(study_name, DEFAULT_DATA_QUALITY_FOLDER),
        ["Data_per_day", "data_per_day", "Total_records", "records"],
        subjects,
    )
    if not activity:
        return [
            kpi_card(str(_("Last Smartphone Data")), "--", str(_("no smartphone timeline data")), "neutral"),
            kpi_card(str(_("Recent Subjects")), "--", str(_("subjects with recent smartphone data")), "neutral"),
            kpi_card(str(_("Records Latest Day")), "--", str(_("smartphone records on latest data day")), "neutral"),
        ]

    enrolled = activity["enrolled_subjects"]
    recent = activity["subjects_recent"]
    return [
        kpi_card(
            str(_("Last Smartphone Data")),
            format_display_date(activity["latest_date"]),
            latest_day_subtitle(activity),
            "healthy" if activity["latest_date"] else "neutral",
        ),
        kpi_card(
            str(_("Recent Subjects")),
            f"{recent}/{enrolled}",
            str(_("enrolled subjects with recent smartphone data")),
            stream_kpi_status(recent, enrolled),
        ),
        kpi_card(
            str(_("Records Latest Day")),
            activity["latest_volume"],
            str(_("smartphone records on latest data day")),
            "healthy" if activity["latest_volume"] else "critical",
        ),
    ]


def build_device_sensor_kpi_summary(study_name, subjects=None):
    activity = latest_stream_activity(
        load_subject_timeline_data(study_name, "garmin_data_quality"),
        ["Data_per_day", "data_per_day", "Total_records", "records"],
        subjects,
    )
    if not activity:
        return [
            kpi_card(str(_("Last Device Sensor Data")), "--", str(_("no device sensor timeline data")), "neutral"),
            kpi_card(str(_("Recent Subjects")), "--", str(_("subjects with recent device sensor data")), "neutral"),
            kpi_card(str(_("Records Latest Day")), "--", str(_("device sensor records on latest data day")), "neutral"),
        ]

    enrolled = activity["enrolled_subjects"]
    recent = activity["subjects_recent"]
    return [
        kpi_card(
            str(_("Last Device Sensor Data")),
            format_display_date(activity["latest_date"]),
            latest_day_subtitle(activity),
            "healthy" if activity["latest_date"] else "neutral",
        ),
        kpi_card(
            str(_("Recent Subjects")),
            f"{recent}/{enrolled}",
            str(_("enrolled subjects with recent device sensor data")),
            stream_kpi_status(recent, enrolled),
        ),
        kpi_card(
            str(_("Records Latest Day")),
            activity["latest_volume"],
            str(_("device sensor records on latest data day")),
            "healthy" if activity["latest_volume"] else "critical",
        ),
    ]


def build_ema_kpi_summary(study_name, subjects=None):
    activity = latest_stream_activity(
        load_subject_timeline_data(study_name, "ema_data_quality"),
        [
            "Total_questions_answered",
            "Anytime_questions_answered",
            "Optional_questions_answered",
            "Scheduled_questions_answered",
            "Submissions_count",
            "Total_submissions",
        ],
        subjects,
    )
    if not activity:
        return [
            kpi_card(str(_("Latest EMA Date")), "--", str(_("no EMA response timeline data")), "neutral"),
            kpi_card(str(_("Subjects Completed")), "--", str(_("subjects with EMA responses on latest day")), "neutral"),
            kpi_card(str(_("Questions Answered")), "--", str(_("EMA questions answered on latest day")), "neutral"),
        ]

    enrolled = activity["enrolled_subjects"]
    completed = activity["subjects_recent"]
    return [
        kpi_card(
            str(_("Latest EMA Date")),
            format_display_date(activity["latest_date"]),
            latest_day_subtitle(activity),
            "healthy" if activity["latest_date"] else "neutral",
        ),
        kpi_card(
            str(_("Subjects Completed")),
            f"{completed}/{enrolled}",
            str(_("subjects with EMA responses on latest day")),
            stream_kpi_status(completed, enrolled),
        ),
        kpi_card(
            str(_("Questions Answered")),
            activity["latest_volume"],
            str(_("EMA questions answered on latest day")),
            "healthy" if activity["latest_volume"] else "critical",
        ),
    ]

def _details_metrics_data(study_name):
    return details_dataframe_with_metrics(study_name)

def study_has_ema(study_name):
    try:
        study_data = get_analytics_study_json(study_name)
    except Exception:
        study_data = {}

    survey = study_data.get(constants.field_name_survey) or study_data.get(constants.key_name_survey)
    if survey:
        return True

    sensor_list = study_data.get(constants.key_name_sensor_list) or study_data.get(constants.field_name_sensor_list) or []
    if isinstance(sensor_list, str):
        sensor_list = [sensor_list]
    if any(str(sensor).strip().lower() == constants.ema for sensor in sensor_list):
        return True

    try:
        _df, sensors, _total_subjects = _details_metrics_data(study_name)
    except Exception:
        return False
    return any(str(sensor).strip().lower() == constants.ema for sensor in sensors)

def build_overview_subject_coverage(study_name):
    df, sensors, total_subjects = _details_metrics_data(study_name)
    if df.empty:
        return details_empty_figure(str(_("No dashboard metrics available.")))
    return details_subject_coverage_figure(df, sensors, total_subjects)

def build_daily_sensor_coverage_figure(
    study_name,
    quality_folder,
    empty_message=None,
    subjects=None,
    timeline_axis=None,
):
    timeline_fig = build_subject_timeline_daily_coverage_figure(
        study_name,
        quality_folder,
        None,
        subjects,
        timeline_axis,
        _("Sensor Coverage"),
    )
    if timeline_fig is not None:
        return timeline_fig

    daily_df = load_quality_csv(
        study_name,
        "Data_quality_daily_subject_coverage.csv",
        quality_folder,
    )
    if daily_df is None or daily_df.empty:
        return details_empty_figure(str(empty_message or _("No sensor metrics available.")))

    coverage_df = add_coverage_percent_column(daily_df)
    x_col = (
        first_matching_column(coverage_df.columns, ["Study_day", "study_day"])
        or timeline_x_column(coverage_df)
    )
    if not x_col or "Coverage_percent" not in coverage_df.columns:
        return details_empty_figure(str(empty_message or _("No sensor metrics available.")))

    coverage_df["Coverage_percent"] = pd.to_numeric(
        coverage_df["Coverage_percent"],
        errors="coerce",
    )
    if normalize_column_name(x_col) == "study_day":
        coverage_df[x_col] = pd.to_numeric(coverage_df[x_col], errors="coerce")
    coverage_df = coverage_df.dropna(subset=[x_col, "Coverage_percent"])
    group_columns = [x_col]
    if "Sensor" in coverage_df.columns:
        group_columns.insert(0, "Sensor")
    coverage_df = (
        coverage_df
        .groupby(group_columns, as_index=False)["Coverage_percent"]
        .mean()
    )
    sort_columns = ["Sensor", x_col] if "Sensor" in coverage_df.columns else [x_col]
    coverage_df = coverage_df.sort_values(sort_columns)
    if coverage_df.empty:
        return details_empty_figure(str(empty_message or _("No sensor metrics available.")))

    fig = px.line(
        coverage_df,
        x=x_col,
        y="Coverage_percent",
        color="Sensor" if "Sensor" in coverage_df.columns else None,
        markers=True,
        range_y=[0, 100],
        labels={
            x_col: str(_("Study day") if normalize_column_name(x_col) == "study_day" else _(x_col)),
            "Coverage_percent": str(_("Coverage %")),
            "Sensor": str(_("Sensor")),
        },
    )
    fig.update_traces(
        mode="lines+markers",
        line={"width": 2.5},
        marker={"size": 6, "line": {"width": 1, "color": "#ffffff"}},
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            f"{x_col}: %{{x}}<br>"
            "Coverage: %{y:.1f}%<extra></extra>"
        ),
    )
    fig = finish_quality_figure(fig)
    fig.update_layout(
        height=420,
        hovermode="x unified",
        legend=dict(
            title=None,
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="left",
            x=0,
            font={"size": 10},
        ),
        margin=dict(l=48, r=24, t=24, b=58),
    )
    xaxis = {
        "title": str(_("Study day") if normalize_column_name(x_col) == "study_day" else _(x_col)),
        "showgrid": True,
        "gridcolor": "#eef2f5",
        "zeroline": False,
        "nticks": 12,
    }
    fig.update_xaxes(**xaxis)
    fig.update_yaxes(
        title=str(_("Coverage %")),
        range=[0, 100],
        ticksuffix="%",
        showgrid=True,
        gridcolor="#eef2f5",
        zeroline=False,
    )
    return fig

def build_overview_sensor_coverage(study_name, subjects=None, timeline_axis=None):
    return build_daily_sensor_coverage_figure(
        study_name,
        DEFAULT_DATA_QUALITY_FOLDER,
        _("No sensor metrics available."),
        subjects,
        timeline_axis,
    )

def build_overview_ema_coverage(study_name, subjects=None, timeline_axis=None):
    return build_daily_sensor_coverage_figure(
        study_name,
        "ema_data_quality",
        _("No EMA metrics available."),
        subjects,
        timeline_axis,
    )

def build_summary_gauge(df, title, study_name=None):
    from .device_sensor_figures import device_sensor_coverage_metrics

    fig = go.Figure()
    subject_metrics = subject_sensor_coverage_metrics(study_name) if study_name else []
    sensor_metrics = live_sensor_coverage_metrics(study_name) if study_name else []
    device_sensor_metrics = device_sensor_coverage_metrics(study_name) if study_name else []
    panels = [
        (subject_metrics, _("Subject Coverage"), "polar"),
        (sensor_metrics, _("Sensor Coverage"), "polar"),
        (device_sensor_metrics, _("Device Sensor Coverage"), "polar"),
    ]
    panels = [panel for panel in panels if panel[0]]

    if not panels:
        return blank_quality_figure(title, _("No sensor coverage data available."))

    if len(panels) == 1:
        domains = [{"x": [0, 1], "y": [0, 0.86]}]
        subplots = ["polar"]
    elif len(panels) == 2:
        domains = [
            {"x": [0, 0.47], "y": [0, 0.86]},
            {"x": [0.53, 1], "y": [0, 0.86]},
        ]
        subplots = ["polar", "polar2"]
    else:
        domains = [
            {"x": [0, 0.30], "y": [0, 0.86]},
            {"x": [0.35, 0.65], "y": [0, 0.86]},
            {"x": [0.70, 1], "y": [0, 0.86]},
        ]
        subplots = ["polar", "polar2", "polar3"]

    for index, (metrics, panel_title, _subplot) in enumerate(panels):
        add_sensor_coverage_polar(fig, metrics, panel_title, domains[index], subplots[index])

    fig.update_layout(height=380, showlegend=False)
    return finish_quality_figure(fig)
