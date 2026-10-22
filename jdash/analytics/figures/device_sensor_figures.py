"""Device sensor figure builders."""

from django.utils.translation import gettext_lazy as _

from ..data.dashboard_data import device_sensor_names
from .overview_figures import (
    build_daily_sensor_coverage_figure,
    coverage_status,
    local_dashboard_metrics,
    subject_count_with_sensor_data,
)


def device_sensor_coverage_metrics(study_name):
    df, sensors, total_subjects = local_dashboard_metrics(study_name)
    if df.empty:
        return []

    configured_device_sensors = device_sensor_names(study_name, sensors)
    sensors = [sensor for sensor in sensors if sensor in configured_device_sensors]
    if not sensors:
        return []

    metrics = []
    denominator = max(total_subjects, 1)
    for sensor in sensors:
        value = str(sensor or "").strip().lower()
        if value in {"", "none", "nan", "null"}:
            continue
        column = f"{sensor} n_batches"
        if column not in df.columns:
            continue
        subjects = subject_count_with_sensor_data(df, sensor)
        if subjects == 0:
            continue
        coverage = round((subjects / denominator) * 100, 2)
        metrics.append(
            {
                "sensor": sensor,
                "coverage": coverage,
                "status": coverage_status(coverage),
                "subjects": subjects,
                "expected": total_subjects,
            }
        )
    return metrics

def build_device_sensor_coverage_from_quality(study_name, subjects=None, timeline_axis=None):
    return build_daily_sensor_coverage_figure(
        study_name,
        "garmin_data_quality",
        _("No device sensor metrics available."),
        subjects,
        timeline_axis,
    )

def build_overview_device_sensor_coverage(study_name, subjects=None, timeline_axis=None):
    return build_device_sensor_coverage_from_quality(study_name, subjects, timeline_axis)


wearable_sensor_coverage_metrics = device_sensor_coverage_metrics
build_overview_wearable_sensor_coverage = build_overview_device_sensor_coverage
