"""Bounded access to subject-level raw sensor data.

The raw folders can contain many gigabytes per subject. This module exposes
small aggregate previews for charts and a streaming ZIP source for downloads;
it never assembles a complete subject dataset in application memory.
"""

import json
import math
import os
import re
import shutil
import statistics
import subprocess
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from django.conf import settings

from jdash.config import runtime_config as config


class RawSubjectDataError(Exception):
    """Base error for raw subject data access."""


class RawSubjectDataNotFound(RawSubjectDataError):
    """Raised when a requested study, subject, or sensor does not exist."""


class RawSubjectDataValidationError(RawSubjectDataError):
    """Raised when request parameters are unsafe or unsupported."""


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9_.-]+$")
_FILE_TIMESTAMP = re.compile(
    r"_(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})\.json$"
)
_RESOLUTION_FORMATS = {
    "minute": "%Y-%m-%dT%H:%M:00Z",
    "hour": "%Y-%m-%dT%H:00:00Z",
    "day": "%Y-%m-%dT00:00:00Z",
}
_STATISTICS = {"mean", "median", "minimum", "maximum", "sum", "count"}

_SENSOR_METRICS = {
    "accelerometer": [
        ("magnitude", "Magnitude", None),
        ("x", "X axis", None),
        ("y", "Y axis", None),
        ("z", "Z axis", None),
    ],
    "gyroscope": [
        ("magnitude", "Magnitude", None),
        ("x", "X axis", None),
        ("y", "Y axis", None),
        ("z", "Z axis", None),
    ],
    "activity": [("confidence", "Activity confidence", "%")],
    "location": [
        ("accuracy", "Location accuracy", "m"),
        ("alt", "Altitude", "m"),
    ],
    "pedometer": [("stepCount", "Step count", "steps")],
    "application_usage": [
        ("totalTimeinForeground", "Foreground duration", "ms")
    ],
    "lockUnlock": [("events", "Screen events", "events")],
    "ema": [
        ("responses", "Questions answered", "responses"),
        ("submissions", "Submissions", "submissions"),
    ],
}
_GARMIN_METRICS = {
    "garmin_HEART_RATE": ("Heart rate", "bpm"),
    "garmin_STEPS": ("Step count", "steps"),
    "garmin_STRESS": ("Stress level", None),
    "garmin_SPO2": ("Blood oxygen", "%"),
    "garmin_RESPIRATION": ("Respiration rate", "breaths/min"),
    "garmin_BBI": ("Inter-beat interval", "ms"),
    "garmin_ENHANCED_BBI": ("Enhanced inter-beat interval", "ms"),
    "garmin_ACTIGRAPHY_1": ("Activity value", None),
}


def _setting(name, default):
    return getattr(settings, name, default)


def _storage_root():
    configured = _setting("RAW_DATA_STORAGE_ROOT", config.analytics_storage_folder)
    return Path(configured).expanduser().resolve()


def _validate_component(value, label):
    value = str(value or "").strip()
    if (
        not value
        or value in {".", ".."}
        or value.startswith("-")
        or not _SAFE_COMPONENT.fullmatch(value)
    ):
        raise RawSubjectDataValidationError(f"Invalid {label}.")
    return value


def _safe_child(root, *parts):
    candidate = root.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RawSubjectDataValidationError("The requested data path is invalid.") from exc
    return candidate


def _subject_dir(study_name, subject_id):
    study_name = _validate_component(study_name, "study name")
    subject_id = _validate_component(subject_id, "subject ID")
    root = _storage_root()
    path = _safe_child(root, study_name, "inputs", subject_id)
    if not path.is_dir():
        raise RawSubjectDataNotFound("Raw data was not found for this subject.")
    return path


def _raw_dir(study_name, subject_id):
    path = _safe_child(_subject_dir(study_name, subject_id), "raw")
    if not path.is_dir():
        raise RawSubjectDataNotFound("This subject has no raw data folder.")
    return path


def _sensor_source(sensor):
    normalized = sensor.lower()
    if normalized == "ema":
        return "ema"
    if normalized.startswith("garmin_"):
        return "wearable"
    return "smartphone"


def _humanize_sensor(sensor):
    if sensor.lower().startswith("garmin_"):
        sensor = sensor[len("garmin_") :]
    return sensor.replace("_", " ").strip().title()


def _metric_rows(sensor):
    normalized = sensor.lower()
    if normalized.startswith("garmin_"):
        label, unit = _GARMIN_METRICS.get(sensor, ("Value", None))
        rows = [("value", label, unit)]
    else:
        rows = _SENSOR_METRICS.get(sensor, _SENSOR_METRICS.get(normalized))
        if rows is None:
            rows = [("value", "Value", None), ("records", "Records", "records")]
    return [
        {"value": value, "label": label, "unit": unit}
        for value, label, unit in rows
    ]


def _filename_datetime(path):
    match = _FILE_TIMESTAMP.search(path.name)
    if not match:
        return None
    try:
        parsed = datetime.strptime(match.group("timestamp"), "%Y-%m-%dT%H-%M-%S")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc)


def _json_files(sensor_dir):
    files = []
    try:
        entries = os.scandir(sensor_dir)
    except OSError as exc:
        raise RawSubjectDataError("The raw sensor folder could not be read.") from exc
    with entries:
        for entry in entries:
            if entry.is_file(follow_symlinks=False) and entry.name.endswith(".json"):
                files.append(Path(entry.path))
    files.sort(key=lambda path: (_filename_datetime(path) or datetime.min.replace(tzinfo=timezone.utc), path.name))
    return files


def _subject_joined_at(subject_dir):
    metadata_files = sorted(subject_dir.glob("*.json"))
    for path in metadata_files:
        try:
            with path.open("r", encoding="utf-8") as stream:
                payload = json.load(stream)
        except (OSError, ValueError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        joined = _parse_timestamp(payload.get("time_joined"))
        if joined:
            return joined
        joined = _parse_timestamp(payload.get("time_joined_ema"))
        if joined:
            return joined
    return None


def subject_raw_metadata(study_name, subject_id):
    """Return available streams and chart-safe measures for one subject."""
    subject_dir = _subject_dir(study_name, subject_id)
    raw_dir = _raw_dir(study_name, subject_id)
    sensors = []

    try:
        sensor_entries = sorted(os.scandir(raw_dir), key=lambda entry: entry.name.lower())
    except OSError as exc:
        raise RawSubjectDataError("The raw data folder could not be read.") from exc

    for entry in sensor_entries:
        if not entry.is_dir(follow_symlinks=False):
            continue
        sensor = entry.name
        files = _json_files(Path(entry.path))
        if not files:
            continue
        dated_files = [(_filename_datetime(path), path) for path in files]
        dates = [value for value, _path in dated_files if value is not None]
        metrics = _metric_rows(sensor)
        sensors.append(
            {
                "name": sensor,
                "label": _humanize_sensor(sensor),
                "source": _sensor_source(sensor),
                "file_count": len(files),
                "first_data_at": min(dates).isoformat() if dates else None,
                "latest_data_at": max(dates).isoformat() if dates else None,
                "metrics": metrics,
                "default_metric": metrics[0]["value"],
            }
        )

    joined_at = _subject_joined_at(subject_dir)
    return {
        "study": str(study_name),
        "subject_id": str(subject_id),
        "joined_at": joined_at.isoformat() if joined_at else None,
        "sensors": sensors,
        "sources": {
            source: [sensor for sensor in sensors if sensor["source"] == source]
            for source in ("smartphone", "wearable", "ema")
        },
    }


def _parse_date(value, label):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise RawSubjectDataValidationError(
            f"{label} must use YYYY-MM-DD format."
        ) from exc


def _parse_timestamp(value):
    if value in (None, ""):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = None
    if numeric is not None and math.isfinite(numeric):
        if abs(numeric) > 10_000_000_000:
            numeric /= 1000
        try:
            return datetime.fromtimestamp(numeric, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _series_range(files, start, end, period_days):
    max_days = int(_setting("RAW_DATA_MAX_RANGE_DAYS", 31))
    if period_days is not None:
        try:
            period_days = int(period_days)
        except (TypeError, ValueError) as exc:
            raise RawSubjectDataValidationError("Period must be a number of days.") from exc
        if period_days < 1 or period_days > max_days:
            raise RawSubjectDataValidationError(
                f"Period must be between 1 and {max_days} days."
            )

    start_date = _parse_date(start, "Start date")
    end_date = _parse_date(end, "End date")
    file_dates = [value.date() for value in map(_filename_datetime, files) if value]
    latest_date = max(file_dates) if file_dates else datetime.now(timezone.utc).date()
    earliest_date = min(file_dates) if file_dates else latest_date
    end_date = end_date or latest_date
    start_date = start_date or (
        end_date - timedelta(days=period_days - 1)
        if period_days is not None
        else earliest_date
    )
    if start_date > end_date:
        raise RawSubjectDataValidationError("Start date must not be after end date.")
    if period_days is not None and (end_date - start_date).days + 1 > max_days:
        raise RawSubjectDataValidationError(
            f"The requested range cannot exceed {max_days} days."
        )
    return (
        datetime.combine(start_date, time.min, tzinfo=timezone.utc),
        datetime.combine(end_date, time.max, tzinfo=timezone.utc),
    )


def _even_sample(items, limit):
    if len(items) <= limit:
        return items
    if limit <= 1:
        return [items[-1]]
    last_index = len(items) - 1
    indexes = sorted({round(index * last_index / (limit - 1)) for index in range(limit)})
    return [items[index] for index in indexes]


def _bucket_datetime(value, resolution):
    if resolution == "minute":
        return value.replace(second=0, microsecond=0)
    if resolution == "hour":
        return value.replace(minute=0, second=0, microsecond=0)
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def _numeric(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _record_value(record, metric):
    if metric in {"records", "events", "responses", "submissions"}:
        return 1.0
    if metric == "magnitude":
        axes = [_numeric(record.get(axis)) for axis in ("x", "y", "z")]
        if any(value is None for value in axes):
            return None
        return math.sqrt(sum(value * value for value in axes))
    return _numeric(record.get(metric))


def _read_json_records(path, max_file_bytes):
    try:
        if path.stat().st_size > max_file_bytes:
            return None
        with path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, ValueError, TypeError):
        return None
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        records = payload.get("data")
        return records if isinstance(records, list) else [payload]
    return None


def _aggregate(values, statistic):
    if statistic == "count":
        return float(len(values))
    if statistic == "sum":
        return float(sum(values))
    if statistic == "minimum":
        return float(min(values))
    if statistic == "maximum":
        return float(max(values))
    if statistic == "median":
        return float(statistics.median(values))
    return float(statistics.fmean(values))


def subject_sensor_series(
    study_name,
    subject_id,
    sensor,
    metric=None,
    statistic="mean",
    resolution="day",
    start=None,
    end=None,
    period_days=None,
):
    """Aggregate one raw sensor into a bounded chart-ready time series."""
    sensor = _validate_component(sensor, "sensor")
    if resolution not in _RESOLUTION_FORMATS:
        raise RawSubjectDataValidationError("Unsupported resolution.")
    if statistic not in _STATISTICS:
        raise RawSubjectDataValidationError("Unsupported statistic.")

    subject_dir = _subject_dir(study_name, subject_id)
    sensor_dir = _safe_child(_raw_dir(study_name, subject_id), sensor)
    if not sensor_dir.is_dir():
        raise RawSubjectDataNotFound("The requested raw sensor was not found.")

    available_metrics = {row["value"]: row for row in _metric_rows(sensor)}
    metric = metric or next(iter(available_metrics))
    if metric not in available_metrics:
        raise RawSubjectDataValidationError("Unsupported metric for this sensor.")
    if metric in {"records", "events", "responses", "submissions"}:
        statistic = "count"

    all_files = _json_files(sensor_dir)
    if not all_files:
        raise RawSubjectDataNotFound("No raw files were found for this sensor.")
    joined_at = _subject_joined_at(subject_dir)
    if period_days is None:
        start = start or (joined_at.date().isoformat() if joined_at else None)
        end = end or datetime.now(timezone.utc).date().isoformat()
    start_at, end_at = _series_range(all_files, start, end, period_days)
    matching_files = [
        path
        for path in all_files
        if _filename_datetime(path) is None
        or start_at.date() <= _filename_datetime(path).date() <= end_at.date()
    ]
    file_limit = int(_setting("RAW_DATA_MAX_FILES_PER_SERIES", 120))
    selected_files = _even_sample(matching_files, max(1, file_limit))
    record_limit = int(_setting("RAW_DATA_MAX_RECORDS_PER_SERIES", 500_000))
    max_file_bytes = int(_setting("RAW_DATA_MAX_FILE_BYTES", 50 * 1024 * 1024))

    buckets = defaultdict(list)
    submission_keys = defaultdict(set)
    records_seen = 0
    records_used = 0
    skipped_large_or_invalid_files = 0
    truncated = False

    for path in selected_files:
        records = _read_json_records(path, max_file_bytes)
        if records is None:
            skipped_large_or_invalid_files += 1
            continue
        for record in records:
            records_seen += 1
            if records_seen > record_limit:
                truncated = True
                break
            if not isinstance(record, dict):
                continue
            timestamp = _parse_timestamp(record.get("timestamp"))
            if timestamp is None or timestamp < start_at or timestamp > end_at:
                continue
            value = _record_value(record, metric)
            if value is None:
                continue
            bucket = _bucket_datetime(timestamp, resolution)
            if metric == "submissions":
                submission_key = str(record.get("timestamp") or path.name)
                submission_keys[bucket].add(submission_key)
            else:
                buckets[bucket].append(value)
            records_used += 1
        if truncated:
            break

    if metric == "submissions":
        buckets = {
            bucket: [1.0] * len(keys)
            for bucket, keys in submission_keys.items()
        }

    points = []
    for bucket in sorted(buckets):
        values = buckets[bucket]
        if not values:
            continue
        points.append(
            {
                "timestamp": bucket.strftime(_RESOLUTION_FORMATS[resolution]),
                "date": bucket.date().isoformat(),
                "study_day": (
                    (bucket.date() - joined_at.date()).days if joined_at else None
                ),
                "study_day_position": (
                    round((bucket - joined_at).total_seconds() / 86400, 4)
                    if joined_at
                    else None
                ),
                "value": _aggregate(values, statistic),
                "records": len(values),
            }
        )

    metric_row = available_metrics[metric]
    return {
        "study": str(study_name),
        "subject_id": str(subject_id),
        "sensor": sensor,
        "sensor_label": _humanize_sensor(sensor),
        "source": _sensor_source(sensor),
        "metric": metric,
        "metric_label": metric_row["label"],
        "unit": metric_row["unit"],
        "statistic": statistic,
        "resolution": resolution,
        "start": start_at.date().isoformat(),
        "end": end_at.date().isoformat(),
        "joined_at": joined_at.isoformat() if joined_at else None,
        "points": points,
        "preview": {
            "matching_files": len(matching_files),
            "files_read": len(selected_files),
            "files_sampled": len(selected_files) < len(matching_files),
            "records_seen": records_seen,
            "records_used": records_used,
            "record_limit_reached": truncated,
            "skipped_large_or_invalid_files": skipped_large_or_invalid_files,
        },
    }


def raw_download_target(study_name, subject_id):
    """Return the authorized subject directory and a stable download name."""
    subject_dir = _subject_dir(study_name, subject_id)
    return subject_dir, f"{subject_dir.name}_raw_data.zip"


def zip_command_available():
    return shutil.which("zip") is not None


def stream_directory_as_zip(directory):
    """Yield a ZIP archive produced by the system zip command."""
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise RawSubjectDataNotFound("The subject data folder was not found.")
    if not zip_command_available():
        raise RawSubjectDataError("The server ZIP utility is unavailable.")

    process = subprocess.Popen(
        [
            "zip",
            "-q",
            "-r",
            "-",
            directory.name,
            "-x",
            f"{directory.name}/combined/*",
            f"{directory.name}/.DS_Store",
        ],
        cwd=str(directory.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        while True:
            chunk = process.stdout.read(1024 * 1024)
            if not chunk:
                break
            yield chunk
        return_code = process.wait()
        if return_code:
            raise RawSubjectDataError("The subject archive could not be created.")
    finally:
        if process.stdout:
            process.stdout.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
