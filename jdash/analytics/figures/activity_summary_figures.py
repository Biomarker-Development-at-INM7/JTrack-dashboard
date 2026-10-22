"""Connected KPI and activity-finding summaries for analytics tabs."""

from collections import defaultdict
import re

import pandas as pd
from dash import html
from django.utils.translation import gettext_lazy as _

from jdash.models import Study

from ..data.dashboard_data import (
    DEFAULT_DATA_QUALITY_FOLDER,
    apply_filter,
    first_matching_column,
    load_data_per_day_overview,
    load_quality_csv,
    load_subject_timeline_data,
    normalize_column_name,
)
from ..data.ema_data import (
    EMA_FREQUENCY_WINDOW_COMPLETION_CSV,
    EMA_MISSINGNESS_SUMMARY_CSV,
    EMA_QUALITY_FOLDER,
    EMA_RESPONSE_COUNT_COLUMNS,
    EMA_SUBJECT_QC_TIMELINE_CSV,
    is_optional_only_ema_study,
)
from .overview_figures import (
    activity_finding_card,
    kpi_card,
    overview_activity_findings,
)


OVERVIEW_TAB = "subject-data"
SMARTPHONE_TAB = "sensor-data"
DEVICE_SENSOR_TAB = "device-sensor-data"
EMA_TAB = "ema-data"


def _data_collection_completed(study_name):
    """Return the admin-managed collection state for a study."""
    try:
        return bool(
            Study.objects.filter(title=study_name)
            .values_list("data_collection_completed", flat=True)
            .first()
        )
    except Exception:
        # Analytics still renders with active-study semantics if the database
        # is temporarily unavailable or the manually managed column is absent.
        return False


def _selected_subjects(subjects):
    if not subjects:
        return []
    if isinstance(subjects, (list, tuple, set)):
        return [str(subject) for subject in subjects]
    return [str(subjects)]


def _display_sensor(sensor):
    value = str(sensor or "").strip()
    if value.lower().startswith("garmin_"):
        value = value[len("garmin_"):]
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value).replace("_", " ")
    return (value[:1].upper() + value[1:]) if value else "--"


def _compact_number(value):
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return str(value)
    return str(int(number)) if float(number).is_integer() else f"{float(number):g}"


def _subject_preview(subject_ids, limit=3):
    subject_ids = sorted(set(str(subject_id) for subject_id in subject_ids if subject_id))
    preview = ", ".join(subject_ids[:limit])
    if len(subject_ids) > limit:
        preview = f"{preview} +{len(subject_ids) - limit} {str(_('more'))}"
    return preview


def _register_payload(payloads, key, tab, subject_ids, label, sensor=None):
    subject_ids = sorted(set(str(subject_id) for subject_id in subject_ids if subject_id))
    if not subject_ids:
        return None
    payloads[key] = {
        "tab": tab,
        "subjects": subject_ids,
        "label": str(label),
    }
    if sensor:
        payloads[key]["sensor"] = str(sensor)
    return key


def _connected_kpi(
    payloads,
    key,
    tab,
    label,
    value,
    subtitle,
    status,
    subject_ids=None,
    sensor=None,
):
    drilldown_key = _register_payload(
        payloads,
        key,
        tab,
        subject_ids or [],
        label,
        sensor,
    )
    return kpi_card(label, value, subtitle, status, drilldown_key)


def _connected_finding(
    payloads,
    key,
    tab,
    label,
    subject_ids,
    subtitle,
    status,
    sensor=None,
):
    drilldown_key = _register_payload(
        payloads,
        key,
        tab,
        subject_ids,
        label,
        sensor,
    )
    return activity_finding_card(
        label,
        sorted(set(subject_ids)),
        subtitle,
        status,
        drilldown_key,
    )


def _finding_section(cards):
    return html.Div(
        [
            html.Div(str(_("Activity Findings")), className="analytics-finding-section-title"),
            html.Div(cards, className="analytics-finding-grid"),
        ],
        className="analytics-finding-section",
    )


def _has_data(values):
    normalized = pd.Series(values, dtype="string").str.strip().str.lower()
    return normalized.notna() & ~normalized.isin(["", "--", "none", "nan", "nat"])


def _source_group(row, group_col, sensor_col):
    group = normalize_column_name(row.get(group_col)) if group_col else ""
    sensor = normalize_column_name(row.get(sensor_col)) if sensor_col else ""
    if group == "ema" or sensor == "ema":
        return "ema"
    if group in ("garmin", "wearable", "wearables", "device_sensor", "device_sensors"):
        return "device_sensor"
    if sensor.startswith("garmin_"):
        return "device_sensor"
    return "smartphone"


def _overview_source_status(study_name, subjects=None):
    status_df = load_quality_csv(study_name, "Study_overview_subject_sensor_status.csv")
    if status_df is None or status_df.empty:
        return None

    subject_col = first_matching_column(status_df.columns, ["Subject_ID", "subject_id", "subject"])
    group_col = first_matching_column(status_df.columns, ["Sensor_group", "sensor_group", "Group"])
    sensor_col = first_matching_column(status_df.columns, ["Sensor", "sensor"])
    last_date_col = first_matching_column(
        status_df.columns,
        ["Last_data_received_date", "Last_any_data_date", "Last_data_date"],
    )
    days_col = first_matching_column(
        status_df.columns,
        ["Days_since_last_data_received", "Days_since_last_any_data", "Days_since_last_data"],
    )
    if not subject_col or not sensor_col or not last_date_col or not days_col:
        return None

    status_df = status_df.copy()
    status_df[subject_col] = status_df[subject_col].fillna("").astype(str)
    status_df = status_df[status_df[subject_col].astype(bool)]
    status_df = apply_filter(status_df, subject_col, subjects)
    if status_df.empty:
        return None

    status_df["_source"] = status_df.apply(
        lambda row: _source_group(row, group_col, sensor_col),
        axis=1,
    )
    status_df["_has_data"] = _has_data(status_df[last_date_col])
    status_df["_days_since"] = pd.to_numeric(status_df[days_col], errors="coerce")
    status_df["_needs_attention"] = ~status_df["_has_data"] | status_df["_days_since"].ge(2)
    return status_df, subject_col, sensor_col


def _issue_breakdown(source_df, subject_col, sensor_col):
    issues = source_df[source_df["_needs_attention"]]
    if issues.empty:
        return str(_("All configured sensors are current"))
    counts = (
        issues.groupby(sensor_col)[subject_col]
        .nunique()
        .sort_values(ascending=False)
    )
    parts = [f"{_display_sensor(sensor)}: {count}" for sensor, count in counts.head(2).items()]
    if len(counts) > 2:
        parts.append(f"+{len(counts) - 2} {str(_('sensors'))}")
    return f"{str(_('Top gaps'))}: " + " · ".join(parts)


def _current_status(current_count, total_count):
    """Return a glanceable status based on the share of current subjects."""
    if not total_count:
        return "neutral"
    current_rate = current_count / total_count
    if current_rate >= 0.95:
        return "healthy"
    if current_rate >= 0.80:
        return "warning"
    return "critical"


def _current_kpi_subtitle(issue_count, breakdown=None, include_definition=False):
    lines = [
        html.Div(
            f"{issue_count} {str(_('subjects need attention'))}",
            className="analytics-kpi-attention-count",
        )
    ]
    if breakdown:
        lines.append(html.Div(breakdown, className="analytics-kpi-gap-summary"))
    if include_definition:
        lines.append(
            html.Div(
                str(_("Current = data received within the last 2 days")),
                className="analytics-kpi-definition",
            )
        )
    if issue_count:
        lines.append(
            html.Div(
                str(_("View affected subjects →")),
                className="analytics-kpi-drilldown-label",
            )
        )
    return html.Div(lines)


def _final_kpi_subtitle(missing_count, breakdown=None, include_definition=False):
    lines = [
        html.Div(
            f"{missing_count} {str(_('subjects have missing recorded streams'))}",
            className="analytics-kpi-attention-count",
        )
    ]
    if breakdown:
        lines.append(html.Div(breakdown, className="analytics-kpi-gap-summary"))
    if include_definition:
        lines.append(
            html.Div(
                str(_("Complete = recorded data exists for every configured stream")),
                className="analytics-kpi-definition",
            )
        )
    if missing_count:
        lines.append(
            html.Div(
                str(_("View affected subjects →")),
                className="analytics-kpi-drilldown-label",
            )
        )
    return html.Div(lines)


def _available_overview_sources(study_name):
    sources = set()
    per_day_df = load_data_per_day_overview(study_name)
    if per_day_df is not None and not per_day_df.empty:
        sensor_col = first_matching_column(per_day_df.columns, ["Sensor", "sensor"])
        if sensor_col:
            for sensor in per_day_df[sensor_col].dropna().unique():
                sources.add(_source_group({sensor_col: sensor}, None, sensor_col))

    for source, quality_folder in (
        ("smartphone", DEFAULT_DATA_QUALITY_FOLDER),
        ("device_sensor", "garmin_data_quality"),
        ("ema", EMA_QUALITY_FOLDER),
    ):
        timeline_df = load_subject_timeline_data(study_name, quality_folder)
        if timeline_df is not None and not timeline_df.empty:
            sources.add(source)
    return sources


def _build_overview_summary(study_name, subjects=None):
    payloads = {}
    collection_completed = _data_collection_completed(study_name)
    source_status = _overview_source_status(study_name, subjects)
    if source_status is None:
        available_sources = _available_overview_sources(study_name)
        cards = [
            kpi_card(
                str(_("Final Data Coverage") if collection_completed else _("Subjects Current Across All Streams")),
                "--",
                str(_("no subject status data")),
                "neutral",
            ),
        ]
        fallback_cards = (
            ("smartphone", _("Smartphone")),
            ("device_sensor", _("Garmin")),
            ("ema", _("EMA")),
        )
        cards.extend(
            kpi_card(
                f"{str(label)} {str(_('Final Coverage'))}" if collection_completed else str(label),
                "--",
                str(_("no subject status data")),
                "neutral",
            )
            for source, label in fallback_cards
            if source in available_sources
        )
    else:
        status_df, subject_col, sensor_col = source_status
        all_subjects = sorted(status_df[subject_col].dropna().astype(str).unique())
        source_issues = {}
        source_frames = {}
        for source in ("smartphone", "device_sensor", "ema"):
            source_df = status_df[status_df["_source"].eq(source)]
            source_frames[source] = source_df
            source_issues[source] = sorted(
                source_df.loc[source_df["_needs_attention"], subject_col]
                .dropna()
                .astype(str)
                .unique()
            )

        if collection_completed:
            missing_rows = status_df[~status_df["_has_data"]]
            all_issue_subjects = set(
                missing_rows[subject_col].dropna().astype(str).unique()
            )
        else:
            all_issue_subjects = set().union(*[set(values) for values in source_issues.values()])
        all_on_track = sorted(set(all_subjects) - all_issue_subjects)
        cards = [
            _connected_kpi(
                payloads,
                "overview-all-on-track",
                OVERVIEW_TAB,
                str(_("Final Data Coverage") if collection_completed else _("Subjects Current Across All Streams")),
                (
                    f"{len(all_on_track)} / {len(all_subjects)} complete"
                    if collection_completed
                    else f"{len(all_on_track)} / {len(all_subjects)} current"
                ),
                (
                    _final_kpi_subtitle(len(all_issue_subjects), include_definition=True)
                    if collection_completed
                    else _current_kpi_subtitle(len(all_issue_subjects), include_definition=True)
                ),
                _current_status(len(all_on_track), len(all_subjects)),
                sorted(all_issue_subjects),
            )
        ]
        source_cards = [
            ("smartphone", SMARTPHONE_TAB, _("Smartphone")),
            ("device_sensor", DEVICE_SENSOR_TAB, _("Garmin")),
            ("ema", EMA_TAB, _("EMA")),
        ]
        for source, tab, label in source_cards:
            source_df = source_frames[source]
            if source_df.empty:
                continue
            issue_subjects = (
                sorted(
                    source_df.loc[~source_df["_has_data"], subject_col]
                    .dropna()
                    .astype(str)
                    .unique()
                )
                if collection_completed
                else source_issues[source]
            )
            source_subjects = sorted(
                source_df[subject_col].dropna().astype(str).unique()
            )
            current_count = len(set(source_subjects) - set(issue_subjects))
            cards.append(
                _connected_kpi(
                    payloads,
                    f"overview-{source}-attention",
                    tab,
                    f"{str(label)} {str(_('Final Coverage') if collection_completed else _('Current'))}",
                    (
                        f"{current_count} / {len(source_subjects)} complete"
                        if collection_completed
                        else f"{current_count} / {len(source_subjects)} current"
                    ),
                    (
                        _final_kpi_subtitle(len(issue_subjects))
                        if collection_completed
                        else _current_kpi_subtitle(
                            len(issue_subjects),
                            _issue_breakdown(source_df, subject_col, sensor_col),
                        )
                    ),
                    _current_status(current_count, len(source_subjects)),
                    issue_subjects,
                )
            )

    findings = overview_activity_findings(study_name, subjects)
    finding_specs = [
        (
            "overview-current-gap",
            _("Current-day Gaps"),
            "current_gap",
            _("No data on the current expected study day"),
            "warning",
        ),
        (
            "overview-consecutive-gap",
            _("Consecutive Gaps"),
            "consecutive_gap",
            _("No data for three consecutive study days"),
            "critical",
        ),
        (
            "overview-repeated-gap",
            _("Repeated Gaps"),
            "repeated_gap",
            _("At least three zero-data days in the latest seven study days"),
            "warning",
        ),
        (
            "overview-activity-decline",
            _("Activity Decline"),
            "activity_decline",
            _("Latest seven-day volume is at least 50% below the previous seven days"),
            "critical",
        ),
    ]
    finding_cards = [
        _connected_finding(
            payloads,
            key,
            OVERVIEW_TAB,
            label,
            findings[finding_key],
            subtitle,
            status,
        )
        for key, label, finding_key, subtitle, status in finding_specs
    ]
    return cards, _finding_section(finding_cards), payloads


def _sensor_activity_metrics(study_name, quality_folder, subjects=None):
    timeline_df = load_subject_timeline_data(study_name, quality_folder)
    if timeline_df is None or timeline_df.empty:
        return {}

    subject_col = first_matching_column(timeline_df.columns, ["Subject_ID", "subject_id", "subject"])
    sensor_col = first_matching_column(timeline_df.columns, ["Sensor", "sensor"])
    day_col = first_matching_column(timeline_df.columns, ["Study_day", "study_day"])
    value_col = first_matching_column(timeline_df.columns, ["Data_per_day", "data_per_day"])
    expected_col = first_matching_column(timeline_df.columns, ["Expected", "expected"])
    if not subject_col or not sensor_col or not day_col or not value_col:
        return {}

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
    if expected_col:
        expected = pd.to_numeric(timeline_df[expected_col], errors="coerce").fillna(0)
        timeline_df = timeline_df[expected.gt(0)]
    if timeline_df.empty:
        return {}

    daily = (
        timeline_df.groupby([subject_col, sensor_col, day_col], as_index=False)[value_col]
        .sum()
    )
    metrics = defaultdict(
        lambda: {
            "recent_expected": 0,
            "recent_active": 0,
            "recent_volume": 0.0,
            "comparable_recent_volume": 0.0,
            "previous_volume": 0.0,
            "affected": set(),
            "current_gap": set(),
            "consecutive_gap": set(),
            "repeated_gap": set(),
            "decline": set(),
        }
    )

    for (subject_id, sensor), subject_sensor_df in daily.groupby([subject_col, sensor_col]):
        current_day = int(subject_sensor_df[day_col].max())
        first_day = int(subject_sensor_df[day_col].min())
        values = subject_sensor_df.groupby(day_col)[value_col].sum().to_dict()

        def volume(day):
            return float(values.get(day, 0) or 0)

        recent_days = list(range(max(first_day, current_day - 6), current_day + 1))
        recent_active = sum(volume(day) > 0 for day in recent_days)
        recent_coverage = (recent_active / len(recent_days)) * 100 if recent_days else 0
        sensor_metrics = metrics[str(sensor)]
        sensor_metrics["recent_expected"] += len(recent_days)
        sensor_metrics["recent_active"] += recent_active
        sensor_metrics["recent_volume"] += sum(volume(day) for day in recent_days)

        if recent_coverage < 80:
            sensor_metrics["affected"].add(str(subject_id))
        if volume(current_day) <= 0:
            sensor_metrics["current_gap"].add(str(subject_id))
        if current_day - first_day >= 2 and all(
            volume(day) <= 0 for day in range(current_day - 2, current_day + 1)
        ):
            sensor_metrics["consecutive_gap"].add(str(subject_id))
        if current_day - first_day >= 6 and sum(
            volume(day) <= 0 for day in range(current_day - 6, current_day + 1)
        ) >= 3:
            sensor_metrics["repeated_gap"].add(str(subject_id))
        if current_day - first_day >= 13:
            previous_volume = sum(volume(day) for day in range(current_day - 13, current_day - 6))
            recent_volume = sum(volume(day) for day in range(current_day - 6, current_day + 1))
            sensor_metrics["comparable_recent_volume"] += recent_volume
            sensor_metrics["previous_volume"] += previous_volume
            if previous_volume > 0 and recent_volume <= previous_volume * 0.5:
                sensor_metrics["decline"].add(str(subject_id))

    for sensor_metrics in metrics.values():
        expected = sensor_metrics["recent_expected"]
        sensor_metrics["coverage"] = (
            (sensor_metrics["recent_active"] / expected) * 100 if expected else 0
        )
        previous_volume = sensor_metrics["previous_volume"]
        sensor_metrics["volume_change"] = (
            (
                (sensor_metrics["comparable_recent_volume"] - previous_volume)
                / previous_volume
            )
            * 100
            if previous_volume > 0
            else None
        )
    return dict(metrics)


def _sensor_with_most_subjects(metrics, finding_key):
    candidates = [
        (sensor, values)
        for sensor, values in metrics.items()
        if values[finding_key]
    ]
    if not candidates:
        return None, None
    return max(
        candidates,
        key=lambda item: (len(item[1][finding_key]), -item[1]["coverage"]),
    )


def _build_sensor_summary(study_name, tab, quality_folder, subjects=None):
    payloads = {}
    metrics = _sensor_activity_metrics(study_name, quality_folder, subjects)
    source_label = str(_("Garmin")) if tab == DEVICE_SENSOR_TAB else str(_("Smartphone"))
    if not metrics:
        cards = [
            kpi_card(str(_("Most Affected Sensor")), "--", str(_("no sensor timeline data")), "neutral"),
            kpi_card(str(_("Lowest 7-day Coverage")), "--", str(_("no sensor timeline data")), "neutral"),
            kpi_card(str(_("Largest Volume Decline")), "--", str(_("no sensor timeline data")), "neutral"),
            kpi_card(str(_("Healthy Sensors")), "--", str(_("no sensor timeline data")), "neutral"),
        ]
        return cards, _finding_section([]), payloads

    most_affected_sensor = max(
        metrics,
        key=lambda sensor: (len(metrics[sensor]["affected"]), -metrics[sensor]["coverage"]),
    )
    lowest_coverage_sensor = min(metrics, key=lambda sensor: metrics[sensor]["coverage"])
    declining_sensors = [
        sensor
        for sensor, values in metrics.items()
        if values["volume_change"] is not None and values["volume_change"] < 0
    ]
    largest_decline_sensor = (
        min(declining_sensors, key=lambda sensor: metrics[sensor]["volume_change"])
        if declining_sensors
        else None
    )
    healthy_sensors = sorted(sensor for sensor, values in metrics.items() if values["coverage"] >= 80)

    most_affected = metrics[most_affected_sensor]
    lowest_coverage = metrics[lowest_coverage_sensor]
    cards = [
        _connected_kpi(
            payloads,
            f"{tab}-most-affected",
            tab,
            str(_("Most Affected Sensor")),
            _display_sensor(most_affected_sensor),
            f"{len(most_affected['affected'])} {str(_('subjects below 80% recent coverage'))}",
            "critical" if most_affected["affected"] else "healthy",
            most_affected["affected"],
            most_affected_sensor,
        ),
        _connected_kpi(
            payloads,
            f"{tab}-lowest-coverage",
            tab,
            str(_("Lowest 7-day Coverage")),
            _display_sensor(lowest_coverage_sensor),
            f"{lowest_coverage['coverage']:.0f}% {str(_('recent coverage'))}",
            "healthy" if lowest_coverage["coverage"] >= 80 else (
                "warning" if lowest_coverage["coverage"] >= 50 else "critical"
            ),
            lowest_coverage["affected"],
            lowest_coverage_sensor,
        ),
        _connected_kpi(
            payloads,
            f"{tab}-largest-decline",
            tab,
            str(_("Largest Volume Decline")),
            _display_sensor(largest_decline_sensor),
            (
                f"{metrics[largest_decline_sensor]['volume_change']:.0f}% {str(_('versus previous 7 days'))}"
                if largest_decline_sensor
                else str(_("no comparable decline"))
            ),
            "critical" if largest_decline_sensor and metrics[largest_decline_sensor]["volume_change"] <= -50 else (
                "warning" if largest_decline_sensor else "healthy"
            ),
            metrics[largest_decline_sensor]["decline"] if largest_decline_sensor else [],
            largest_decline_sensor,
        ),
        kpi_card(
            str(_("Healthy Sensors")),
            f"{len(healthy_sensors)}/{len(metrics)}",
            _subject_preview([_display_sensor(sensor) for sensor in healthy_sensors])
            or f"{source_label} {str(_('sensors at or above 80% coverage'))}",
            "healthy" if len(healthy_sensors) == len(metrics) else "warning",
        ),
    ]

    finding_specs = [
        ("current_gap", _("Current-day Gap"), _("subjects with no data on their latest expected sensor day"), "warning"),
        ("consecutive_gap", _("Three-day Interruption"), _("subjects with no data for three consecutive expected days"), "critical"),
        ("repeated_gap", _("Repeated Gaps"), _("subjects with at least three gaps in the latest seven days"), "warning"),
        ("decline", _("Volume Decline"), _("subjects whose latest seven-day volume fell by at least 50%"), "critical"),
    ]
    finding_cards = []
    for finding_key, finding_label, subtitle, status in finding_specs:
        sensor, values = _sensor_with_most_subjects(metrics, finding_key)
        subject_ids = values[finding_key] if values else []
        label = f"{_display_sensor(sensor)} · {str(finding_label)}" if sensor else str(finding_label)
        finding_cards.append(
            _connected_finding(
                payloads,
                f"{tab}-{finding_key}",
                tab,
                label,
                subject_ids,
                subtitle,
                status,
                sensor,
            )
        )
    return cards, _finding_section(finding_cards), payloads


def _window_label(row):
    return f"freq_{_compact_number(row.get('Frequency'))}_window_{_compact_number(row.get('Window_index'))}"


def _build_scheduled_ema_summary(study_name, subjects=None):
    payloads = {}
    detail_df = load_quality_csv(
        study_name,
        EMA_FREQUENCY_WINDOW_COMPLETION_CSV,
        EMA_QUALITY_FOLDER,
    )
    missing_df = load_quality_csv(
        study_name,
        EMA_MISSINGNESS_SUMMARY_CSV,
        EMA_QUALITY_FOLDER,
    )
    if detail_df is None or detail_df.empty:
        cards = [
            kpi_card(str(_("Latest Window Completion")), "--", str(_("no EMA window data")), "neutral"),
            kpi_card(str(_("Lowest Completion Window")), "--", str(_("no EMA window data")), "neutral"),
            kpi_card(str(_("Subjects Below 50%")), "--", str(_("no EMA completion data")), "neutral"),
            kpi_card(str(_("Completion Trend")), "--", str(_("no comparable EMA windows")), "neutral"),
        ]
        return cards, _finding_section([]), payloads

    subject_col = first_matching_column(detail_df.columns, ["Subject_ID", "subject_id", "subject"])
    completion_col = first_matching_column(detail_df.columns, ["Question_completion_percent", "Completion_percent"])
    if not subject_col or not completion_col or "Frequency" not in detail_df or "Window_index" not in detail_df:
        return _build_scheduled_ema_summary_empty(payloads)

    detail_df = apply_filter(detail_df.copy(), subject_col, subjects)
    detail_df[subject_col] = detail_df[subject_col].fillna("").astype(str)
    detail_df[completion_col] = pd.to_numeric(detail_df[completion_col], errors="coerce")
    detail_df["_window_label"] = detail_df.apply(_window_label, axis=1)
    end_day_col = first_matching_column(detail_df.columns, ["Window_end_day", "window_end_day"])
    if end_day_col:
        detail_df["_window_order"] = pd.to_numeric(detail_df[end_day_col], errors="coerce")
    else:
        detail_df["_window_order"] = pd.to_numeric(detail_df["Window_index"], errors="coerce")

    window_summary = (
        detail_df.groupby("_window_label", as_index=False)
        .agg(completion=(completion_col, "mean"), window_order=("_window_order", "max"))
        .dropna(subset=["completion", "window_order"])
    )
    if window_summary.empty:
        return _build_scheduled_ema_summary_empty(payloads)

    latest_order = window_summary["window_order"].max()
    latest_window = window_summary[window_summary["window_order"].eq(latest_order)].sort_values("completion").iloc[0]
    lowest_window = window_summary.sort_values(["completion", "window_order"]).iloc[0]

    latest_rows = detail_df[detail_df["_window_label"].eq(latest_window["_window_label"])]
    latest_issue_subjects = latest_rows.loc[latest_rows[completion_col].lt(80), subject_col].tolist()
    lowest_rows = detail_df[detail_df["_window_label"].eq(lowest_window["_window_label"])]
    lowest_issue_subjects = lowest_rows.loc[lowest_rows[completion_col].lt(80), subject_col].tolist()

    below_fifty_subjects = []
    no_response_subjects = []
    if missing_df is not None and not missing_df.empty:
        missing_subject_col = first_matching_column(missing_df.columns, ["Subject_ID", "subject_id", "subject"])
        overall_completion_col = first_matching_column(
            missing_df.columns,
            ["Question_completion_percent", "Completion_percent", "Response_rate_percent"],
        )
        answered_col = first_matching_column(
            missing_df.columns,
            ["Answered_questions_total", "Total_questions_answered", "Total_submissions"],
        )
        if missing_subject_col:
            missing_df = apply_filter(missing_df.copy(), missing_subject_col, subjects)
            missing_df[missing_subject_col] = missing_df[missing_subject_col].fillna("").astype(str)
            if overall_completion_col:
                completion = pd.to_numeric(missing_df[overall_completion_col], errors="coerce")
                below_fifty_subjects = missing_df.loc[completion.lt(50), missing_subject_col].tolist()
            if answered_col:
                answered = pd.to_numeric(missing_df[answered_col], errors="coerce").fillna(0)
                no_response_subjects = missing_df.loc[answered.le(0), missing_subject_col].tolist()

    latest_missed = set()
    consecutive_missed = set()
    declining_subjects = set()
    trend_values = []
    for (subject_id, _frequency), subject_windows in detail_df.groupby([subject_col, "Frequency"]):
        subject_windows = subject_windows.sort_values("_window_order")
        completion_values = subject_windows[completion_col].dropna().tolist()
        if not completion_values:
            continue
        if completion_values[-1] <= 0:
            latest_missed.add(str(subject_id))
        if len(completion_values) >= 2:
            change = completion_values[-1] - completion_values[-2]
            trend_values.append(change)
            if completion_values[-1] <= 0 and completion_values[-2] <= 0:
                consecutive_missed.add(str(subject_id))
            if change <= -30:
                declining_subjects.add(str(subject_id))

    trend = sum(trend_values) / len(trend_values) if trend_values else None
    cards = [
        _connected_kpi(
            payloads,
            "ema-latest-window",
            EMA_TAB,
            str(_("Latest Window Completion")),
            latest_window["_window_label"],
            f"{latest_window['completion']:.0f}% {str(_('average completion'))}",
            "healthy" if latest_window["completion"] >= 80 else (
                "warning" if latest_window["completion"] >= 50 else "critical"
            ),
            latest_issue_subjects,
        ),
        _connected_kpi(
            payloads,
            "ema-lowest-window",
            EMA_TAB,
            str(_("Lowest Completion Window")),
            lowest_window["_window_label"],
            f"{lowest_window['completion']:.0f}% {str(_('average completion'))}",
            "healthy" if lowest_window["completion"] >= 80 else (
                "warning" if lowest_window["completion"] >= 50 else "critical"
            ),
            lowest_issue_subjects,
        ),
        _connected_kpi(
            payloads,
            "ema-subjects-below-fifty",
            EMA_TAB,
            str(_("Subjects Below 50%")),
            len(set(below_fifty_subjects)),
            str(_("overall scheduled-question completion")),
            "critical" if below_fifty_subjects else "healthy",
            below_fifty_subjects,
        ),
        _connected_kpi(
            payloads,
            "ema-completion-trend",
            EMA_TAB,
            str(_("Completion Trend")),
            f"{trend:+.0f} pp" if trend is not None else "--",
            str(_("latest versus previous frequency window")),
            "critical" if trend is not None and trend <= -30 else (
                "warning" if trend is not None and trend < 0 else "healthy"
            ),
            declining_subjects,
        ),
    ]
    findings = [
        _connected_finding(
            payloads,
            "ema-latest-window-missed",
            EMA_TAB,
            _("Latest Window Missed"),
            latest_missed,
            _("subjects with zero completion in their latest scheduled window"),
            "critical",
        ),
        _connected_finding(
            payloads,
            "ema-consecutive-windows-missed",
            EMA_TAB,
            _("Consecutive Windows Missed"),
            consecutive_missed,
            _("subjects with zero completion in their latest two windows"),
            "critical",
        ),
        _connected_finding(
            payloads,
            "ema-completion-decline",
            EMA_TAB,
            _("Completion Decline"),
            declining_subjects,
            _("subjects whose completion fell by at least 30 percentage points"),
            "warning",
        ),
        _connected_finding(
            payloads,
            "ema-no-response",
            EMA_TAB,
            _("No EMA Responses"),
            no_response_subjects,
            _("subjects with no recorded EMA response since enrollment"),
            "critical",
        ),
    ]
    return cards, _finding_section(findings), payloads


def _build_scheduled_ema_summary_empty(payloads):
    cards = [
        kpi_card(str(_("Latest Window Completion")), "--", str(_("no EMA window data")), "neutral"),
        kpi_card(str(_("Lowest Completion Window")), "--", str(_("no EMA window data")), "neutral"),
        kpi_card(str(_("Subjects Below 50%")), "--", str(_("no EMA completion data")), "neutral"),
        kpi_card(str(_("Completion Trend")), "--", str(_("no comparable EMA windows")), "neutral"),
    ]
    return cards, _finding_section([]), payloads


def _build_ema_activity_summary(study_name, subjects=None):
    payloads = {}
    timeline_df = load_quality_csv(
        study_name,
        EMA_SUBJECT_QC_TIMELINE_CSV,
        EMA_QUALITY_FOLDER,
    )
    if timeline_df is None or timeline_df.empty:
        cards = [
            kpi_card(str(_("Responding Subjects")), "--", str(_("no EMA activity data")), "neutral"),
            kpi_card(str(_("Response Days")), "--", str(_("no EMA activity data")), "neutral"),
            kpi_card(str(_("Responses Recorded")), "--", str(_("no EMA activity data")), "neutral"),
            kpi_card(str(_("Response Trend")), "--", str(_("no comparable EMA activity")), "neutral"),
        ]
        return cards, _finding_section([]), payloads

    subject_col = first_matching_column(timeline_df.columns, ["Subject_ID", "subject_id", "subject"])
    day_col = first_matching_column(timeline_df.columns, ["Study_day", "study_day"])
    value_col = first_matching_column(timeline_df.columns, EMA_RESPONSE_COUNT_COLUMNS)
    if not subject_col or not day_col or not value_col:
        return [], _finding_section([]), payloads

    timeline_df = apply_filter(timeline_df.copy(), subject_col, subjects)
    timeline_df[subject_col] = timeline_df[subject_col].fillna("").astype(str)
    timeline_df[day_col] = pd.to_numeric(timeline_df[day_col], errors="coerce")
    timeline_df[value_col] = pd.to_numeric(timeline_df[value_col], errors="coerce").fillna(0)
    timeline_df = timeline_df[timeline_df[subject_col].astype(bool) & timeline_df[day_col].notna()]

    responding_subjects = set()
    stopped_subjects = set()
    declining_subjects = set()
    one_day_subjects = set()
    no_activity_subjects = set()
    recent_response_days = 0
    recent_responses = 0.0
    recent_total = 0.0
    previous_total = 0.0

    for subject_id, subject_df in timeline_df.groupby(subject_col):
        current_day = int(subject_df[day_col].max())
        first_day = int(subject_df[day_col].min())
        values = subject_df.groupby(day_col)[value_col].sum().to_dict()

        def responses(day):
            return float(values.get(day, 0) or 0)

        recent_days = range(max(first_day, current_day - 6), current_day + 1)
        recent_values = [responses(day) for day in recent_days]
        recent_sum = sum(recent_values)
        recent_total += recent_sum
        recent_response_days += sum(value > 0 for value in recent_values)
        if recent_sum > 0:
            responding_subjects.add(str(subject_id))
            recent_responses += recent_sum
        if sum(value > 0 for value in recent_values) == 1:
            one_day_subjects.add(str(subject_id))
        if sum(float(value) for value in values.values()) <= 0:
            no_activity_subjects.add(str(subject_id))

        if current_day - first_day >= 13:
            previous_sum = sum(responses(day) for day in range(current_day - 13, current_day - 6))
            previous_total += previous_sum
            if previous_sum > 0 and recent_sum <= 0:
                stopped_subjects.add(str(subject_id))
            if previous_sum > 0 and recent_sum <= previous_sum * 0.5:
                declining_subjects.add(str(subject_id))

    trend = ((recent_total - previous_total) / previous_total) * 100 if previous_total > 0 else None
    all_subjects = sorted(timeline_df[subject_col].unique())
    cards = [
        _connected_kpi(
            payloads,
            "ema-responding-subjects",
            EMA_TAB,
            str(_("Responding Subjects")),
            f"{len(responding_subjects)}/{len(all_subjects)}",
            str(_("responses during the latest seven study days")),
            "healthy" if len(responding_subjects) == len(all_subjects) else "warning",
            responding_subjects,
        ),
        _connected_kpi(
            payloads,
            "ema-response-days",
            EMA_TAB,
            str(_("Response Days")),
            recent_response_days,
            str(_("subject-days with EMA activity in the latest seven days")),
            "healthy" if recent_response_days else "critical",
            responding_subjects,
        ),
        _connected_kpi(
            payloads,
            "ema-responses-recorded",
            EMA_TAB,
            str(_("Responses Recorded")),
            f"{recent_responses:.0f}",
            str(_("EMA activity recorded in the latest seven days")),
            "healthy" if recent_responses else "critical",
            responding_subjects,
        ),
        _connected_kpi(
            payloads,
            "ema-response-trend",
            EMA_TAB,
            str(_("Response Trend")),
            f"{trend:+.0f}%" if trend is not None else "--",
            str(_("latest seven days versus previous seven days")),
            "critical" if trend is not None and trend <= -50 else (
                "warning" if trend is not None and trend < 0 else "healthy"
            ),
            declining_subjects,
        ),
    ]
    findings = [
        _connected_finding(
            payloads,
            "ema-activity-stopped",
            EMA_TAB,
            _("Response Activity Stopped"),
            stopped_subjects,
            _("previously active subjects with no response in the latest seven days"),
            "critical",
        ),
        _connected_finding(
            payloads,
            "ema-activity-decline",
            EMA_TAB,
            _("Response Activity Decline"),
            declining_subjects,
            _("subjects with at least 50% fewer responses than the previous seven days"),
            "warning",
        ),
        _connected_finding(
            payloads,
            "ema-one-response-day",
            EMA_TAB,
            _("One Response Day"),
            one_day_subjects,
            _("subjects active on only one of their latest seven study days"),
            "warning",
        ),
        _connected_finding(
            payloads,
            "ema-no-activity",
            EMA_TAB,
            _("No EMA Activity"),
            no_activity_subjects,
            _("subjects with no recorded EMA activity"),
            "critical",
        ),
    ]
    return cards, _finding_section(findings), payloads


def build_connected_dashboard_summary(active_tab, study_name, subjects=None):
    if _data_collection_completed(study_name):
        from .completed_study_figures import build_completed_dashboard_summary

        source_status = _overview_source_status(study_name, subjects) if active_tab == OVERVIEW_TAB else None
        available_sources = _available_overview_sources(study_name) if active_tab == OVERVIEW_TAB else None
        return build_completed_dashboard_summary(
            active_tab,
            study_name,
            subjects,
            source_status=source_status,
            available_sources=available_sources,
        )
    if active_tab == SMARTPHONE_TAB:
        return _build_sensor_summary(
            study_name,
            SMARTPHONE_TAB,
            DEFAULT_DATA_QUALITY_FOLDER,
            subjects,
        )
    if active_tab == DEVICE_SENSOR_TAB:
        return _build_sensor_summary(
            study_name,
            DEVICE_SENSOR_TAB,
            "garmin_data_quality",
            subjects,
        )
    if active_tab == EMA_TAB:
        if is_optional_only_ema_study(study_name):
            return _build_ema_activity_summary(study_name, subjects)
        return _build_scheduled_ema_summary(study_name, subjects)
    return _build_overview_summary(study_name, subjects)
