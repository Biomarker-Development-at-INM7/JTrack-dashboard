"""Data access and selector helpers for the analytics dashboard."""

import os
import re

import pandas as pd
from django.utils.translation import gettext_lazy as _

from jdash.config import constants as constants
from jdash.config import runtime_config as config
from jdash.analytics.csv_utils import get_csv_display_name, read_selected_csv
from jdash.analytics.data.study_metadata import get_analytics_study_json
from jdash.utils.fileutils import build_wearable_dashboard_sensor_name

DATA_QUALITY_PREFIX = "data_quality_"
DEVICE_SENSOR_KEYWORDS = ("garmin", "wearable", "device_sensor", "device-sensor", "device sensor")
DEFAULT_DATA_QUALITY_FOLDER = "data_quality"
DATA_QUALITY_FOLDERS = (
    DEFAULT_DATA_QUALITY_FOLDER,
    "ema_data_quality",
    "garmin_data_quality",
)
PER_DAY_FILE_PREFIXES = ("data_per_day", "device_per_day")
NO_MATCH_SUBJECT_FILTER = "__jdash_no_matching_subject__"


def get_selected_csv_mode(filename):
    """
    Infer which controls/graphs should handle an analytics CSV.

    The pipeline produces a fixed data-quality family named
    Data_quality_*.csv. Device sensor files are less standardized, so the
    filename heuristic intentionally accepts common Garmin/device variants.
    """
    name = get_csv_display_name(filename).lower()
    if name.startswith(DATA_QUALITY_PREFIX):
        return "data_quality"
    if "ema" in name:
        return "ema"
    if any(keyword in name for keyword in DEVICE_SENSOR_KEYWORDS):
        return "device_sensor"
    return "main"


def resolve_study_outputs_dir(study_name):
    """
    Resolve the analytics outputs folder for a study.

    Study names can differ in case between the dashboard metadata and the
    BIDS/output directory, for example ``Garmin_study`` vs ``garmin_study``.
    This keeps lookup tolerant without changing the selected study label.
    """
    if not study_name:
        return None

    exact_path = os.path.join(config.analytics_storage_folder, study_name, "outputs")
    if os.path.isdir(exact_path):
        return exact_path

    storage_root = config.analytics_storage_folder
    if not os.path.isdir(storage_root):
        return None

    target = str(study_name).casefold()
    for folder_name in os.listdir(storage_root):
        if folder_name.casefold() == target:
            candidate = os.path.join(storage_root, folder_name, "outputs")
            if os.path.isdir(candidate):
                return candidate

    return None


def discover_analytics_studies():
    storage_root = config.analytics_storage_folder
    if not os.path.isdir(storage_root):
        return []
    return sorted(
        folder_name
        for folder_name in os.listdir(storage_root)
        if os.path.isdir(os.path.join(storage_root, folder_name, "outputs"))
    )


def update_selector(selected_value):
    """
    List analytics CSV output files for the selected study.

    Args:
        selected_value (str | None): Selected study name.

    Returns:
        list[str]: Absolute paths to CSV files in the study's outputs folder.
    """
    if not selected_value:
        return []

    data_dir = resolve_study_outputs_dir(selected_value)
    if not data_dir:
        data_dir = resolve_study_outputs_dir(selected_value)

    if not data_dir or not os.path.isdir(data_dir):
        return []

    csv_files = []
    csv_dirs = [data_dir] + [os.path.join(data_dir, folder) for folder in DATA_QUALITY_FOLDERS]
    for csv_dir in csv_dirs:
        if not os.path.isdir(csv_dir):
            continue
        for filename in sorted(os.listdir(csv_dir)):
            if not filename.endswith('.csv'):
                continue

            filename_lower = filename.lower()
            if filename_lower == 'data_quality_tabs_manifest.csv':
                continue
            if filename_lower.startswith(('data_per_day_', 'device_per_day_')):
                continue
            if filename_lower.startswith('jutrack_dashboard_'):
                continue

            csv_files.append(os.path.join(csv_dir, filename))
    return csv_files


def study_has_analytics_csvs(study_name):
    """Return whether a study output tree contains any usable CSV data."""
    outputs_dir = resolve_study_outputs_dir(study_name)
    if not outputs_dir:
        return False
    for _root, _directories, filenames in os.walk(outputs_dir):
        if any(filename.lower().endswith(".csv") for filename in filenames):
            return True
    return False


def normalize_column_name(value):
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def first_matching_column(columns, candidates):
    normalized = {normalize_column_name(column): column for column in columns}
    for candidate in candidates:
        key = normalize_column_name(candidate)
        if key in normalized:
            return normalized[key]
    return None


def option_list(values):
    cleaned = sorted(str(value) for value in pd.Series(values).dropna().unique())
    return [{"label": value, "value": value} for value in cleaned]


def sensors_for_study_from_store(sensors_map, study_name):
    if not isinstance(sensors_map, dict) or not study_name:
        return []

    sensors = (
        sensors_map.get(study_name)
        or sensors_map.get(str(study_name))
        or next(
            (
                value
                for key, value in sensors_map.items()
                if str(key).casefold() == str(study_name).casefold()
            ),
            [],
        )
    )
    if isinstance(sensors, str):
        sensors = [sensors]

    sensor_values = []
    seen = set()
    for sensor in sensors or []:
        sensor_name = str(sensor).strip()
        if not sensor_name or sensor_name in seen:
            continue
        seen.add(sensor_name)
        sensor_values.append(sensor_name)
    for sensor in sensors_from_per_day_files(study_name):
        if sensor not in seen:
            seen.add(sensor)
            sensor_values.append(sensor)
    return sensor_values


def is_ema_sensor(sensor_name):
    return str(sensor_name or "").strip().casefold() == constants.ema.casefold()


def is_device_sensor_key(sensor_name):
    value = str(sensor_name or "").strip().casefold()
    return "garmin" in value or "wearable" in value or "device_sensor" in value or "device-sensor" in value


def visible_analytics_tabs(sensors_map, study_name):
    tabs = {"subject-data"}
    sensor_values = sensors_for_study_from_store(sensors_map, study_name)

    if any(is_ema_sensor(sensor) for sensor in sensor_values):
        tabs.add("ema-data")
    if any(is_device_sensor_key(sensor) for sensor in sensor_values):
        tabs.add("device-sensor-data")
    if any(
        not is_ema_sensor(sensor) and not is_device_sensor_key(sensor)
        for sensor in sensor_values
    ):
        tabs.add("sensor-data")

    return tabs



def is_optional_ema_response_activity_study(study_name):
    df = load_quality_csv(
        study_name,
        "Ema_data_quality_subject_qc_timeline.csv",
        "ema_data_quality",
    )
    if df is None or df.empty:
        return False

    scheduled_col = first_matching_column(df.columns, ["Scheduled_questions_answered"])
    response_col = first_matching_column(
        df.columns,
        [
            "Anytime_questions_answered",
            "Optional_questions_answered",
            "Total_questions_answered",
            "Submissions_count",
            "Total_submissions",
        ],
    )

    scheduled_total = (
        pd.to_numeric(df[scheduled_col], errors="coerce").fillna(0).sum()
        if scheduled_col
        else 0
    )
    response_total = (
        pd.to_numeric(df[response_col], errors="coerce").fillna(0).sum()
        if response_col
        else 0
    )
    if scheduled_total == 0 and response_total > 0:
        return True

    anytime_df = load_quality_csv(
        study_name,
        "Ema_data_quality_anytime_question_status.csv",
        "ema_data_quality",
    )
    if anytime_df is not None and not anytime_df.empty:
        return True

    missingness_df = load_quality_csv(
        study_name,
        "Ema_data_quality_missingness_summary.csv",
        "ema_data_quality",
    )
    if missingness_df is None or missingness_df.empty:
        return False

    expected_col = first_matching_column(missingness_df.columns, ["Expected_questions_total"])
    if not expected_col:
        return False

    expected_total = pd.to_numeric(missingness_df[expected_col], errors="coerce").fillna(0).sum()
    return scheduled_total == 0 and expected_total == 0



def analytics_tab_options(sensors_map, study_name):
    tabs = visible_analytics_tabs(sensors_map, study_name)
    options = [{"label": "overview", "value": "subject-data"}]
    if "sensor-data" in tabs:
        options.append({"label": "smartphone", "value": "sensor-data"})
    if "device-sensor-data" in tabs:
        options.append({"label": device_sensor_tab_label(study_name), "value": "device-sensor-data"})
    if "ema-data" in tabs:
        options.append({"label": "ema", "value": "ema-data"})
    return options


def apply_filter(df, column, selected_values):
    if not column or not selected_values:
        return df
    if isinstance(selected_values, (list, tuple, set)):
        selected = [str(value) for value in selected_values]
    else:
        selected = [str(selected_values)]
    return df[df[column].astype(str).isin(selected)]


def resolve_subject_filter(selected_subjects, mode="include", subject_options=None):
    """Return the subject IDs that downstream figures should include."""
    if not selected_subjects:
        return None

    if isinstance(selected_subjects, (list, tuple, set)):
        selected = [str(value) for value in selected_subjects]
    else:
        selected = [str(selected_subjects)]

    if mode != "exclude":
        return selected

    available = []
    for option in subject_options or []:
        value = option.get("value") if isinstance(option, dict) else option
        if value is not None and str(value) not in available:
            available.append(str(value))

    # Options are populated asynchronously when a study changes. Avoid a
    # temporary empty dashboard; the options update will trigger callbacks
    # again with the complete complement.
    if not available:
        return None

    excluded = set(selected)
    included = [subject for subject in available if subject not in excluded]
    return included or [NO_MATCH_SUBJECT_FILTER]


def is_data_quality_filename(filename):
    return "data_quality_" in os.path.basename(str(filename)).lower()


def is_study_overview_filename(filename):
    return os.path.basename(str(filename)).lower().startswith("study_overview_")


def quality_csv_semantic_key(filename):
    name = os.path.basename(str(filename)).casefold()
    if not name.endswith(".csv"):
        return None

    name = name[:-4]
    marker = "data_quality_"
    marker_index = name.find(marker)
    if marker_index < 0:
        return None

    suffix = name[marker_index + len(marker):]
    return re.sub(r"^\d+_", "", suffix)


def matching_quality_folder_csv_path(outputs_dir, quality_folder, filename):
    folder_path = os.path.join(outputs_dir, quality_folder)
    if not os.path.isdir(folder_path):
        return None

    target_name = os.path.basename(str(filename)).casefold()
    target_key = quality_csv_semantic_key(filename)
    for folder_filename in sorted(os.listdir(folder_path)):
        if not folder_filename.lower().endswith(".csv"):
            continue
        if folder_filename.casefold() == target_name:
            return os.path.join(folder_path, folder_filename)
        if target_key and quality_csv_semantic_key(folder_filename) == target_key:
            return os.path.join(folder_path, folder_filename)

    return None


def resolve_output_csv_path(study_name, filename, quality_folder=DEFAULT_DATA_QUALITY_FOLDER):
    outputs_dir = resolve_study_outputs_dir(study_name)
    if not outputs_dir:
        return None

    candidate_paths = []
    if quality_folder:
        candidate_paths.append(os.path.join(outputs_dir, quality_folder, filename))
    candidate_paths.append(os.path.join(outputs_dir, filename))

    for path in candidate_paths:
        if os.path.exists(path):
            return path

    if is_data_quality_filename(filename):
        matched_path = matching_quality_folder_csv_path(outputs_dir, quality_folder, filename)
        if matched_path:
            return matched_path

    return None


def load_quality_csv(study_name, filename, quality_folder=DEFAULT_DATA_QUALITY_FOLDER):
    path = resolve_output_csv_path(study_name, filename, quality_folder)
    if not path:
        return None
    return read_selected_csv(path)


def resolve_data_per_day_paths(study_name):
    outputs_dir = resolve_study_outputs_dir(study_name)
    if not outputs_dir:
        return []

    study_dir = os.path.dirname(outputs_dir)
    candidate_dirs = [study_dir, outputs_dir] + [
        os.path.join(outputs_dir, folder)
        for folder in DATA_QUALITY_FOLDERS
    ]
    paths = []
    for directory in candidate_dirs:
        if not os.path.isdir(directory):
            continue
        for filename in os.listdir(directory):
            filename_lower = filename.lower()
            if filename_lower.startswith(PER_DAY_FILE_PREFIXES) and filename_lower.endswith(".csv"):
                paths.append(os.path.join(directory, filename))
    return sorted(set(paths))


def sensor_name_from_data_per_day_path(path):
    filename = os.path.basename(str(path))
    name = filename[:-4] if filename.lower().endswith(".csv") else filename
    prefixes = [
        "Data_per_day_device_",
        "Data_per_day_",
        "Device_per_day_device_",
        "Device_per_day_",
    ]
    suffix = "_latest"
    for prefix in prefixes:
        if name.casefold().startswith(prefix.casefold()):
            name = name[len(prefix):]
            break
    if name.casefold().endswith(suffix.casefold()):
        name = name[:-len(suffix)]
    name = re.sub(r"_[0-9]{1,2}[A-Za-z]{3}[0-9]{4}_[0-9]{6}$", "", name)
    return name or _("Unknown sensor")


def sensors_from_per_day_files(study_name):
    sensors = []
    seen = set()
    for path in resolve_data_per_day_paths(study_name):
        sensor = str(sensor_name_from_data_per_day_path(path)).strip()
        if not sensor or sensor in seen:
            continue
        seen.add(sensor)
        sensors.append(sensor)
    return sensors


def load_data_per_day_overview(study_name):
    frames = []
    for path in resolve_data_per_day_paths(study_name):
        try:
            df = read_selected_csv(path)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        df = df.copy()
        df["Sensor"] = sensor_name_from_data_per_day_path(path)
        frames.append(df)

    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def load_subject_timeline_data(study_name, quality_folder=DEFAULT_DATA_QUALITY_FOLDER):
    timeline_filenames = {
        DEFAULT_DATA_QUALITY_FOLDER: "Data_quality_subject_qc_timeline.csv",
        "ema_data_quality": "Ema_data_quality_subject_qc_timeline.csv",
        "garmin_data_quality": "Garmin_data_quality_subject_qc_timeline.csv",
    }
    df = load_quality_csv(
        study_name,
        timeline_filenames.get(quality_folder, "Data_quality_subject_qc_timeline.csv"),
        quality_folder,
    )
    if df is None or df.empty:
        return None
    return df


def filtered_quality_csv(
    study_name,
    filename,
    sensors=None,
    subjects=None,
    stages=None,
    flags=None,
    quality_folder=DEFAULT_DATA_QUALITY_FOLDER,
):
    df = load_quality_csv(study_name, filename, quality_folder)
    if df is None:
        return None

    sensor_col = first_matching_column(df.columns, ["Sensor"])
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    stage_col = first_matching_column(df.columns, ["Stage", "Status"])
    flag_col = first_matching_column(df.columns, ["Flag"])

    df = apply_filter(df, sensor_col, sensors)
    df = apply_filter(df, subject_col, subjects)
    df = apply_filter(df, stage_col, stages)
    df = apply_filter(df, flag_col, flags)
    return df


def safe_download_filename(*parts, extension):
    base_name = "_".join(str(part) for part in parts if part)
    safe_name = "".join(character if character.isalnum() or character in ("-", "_") else "_" for character in base_name)
    return f"{safe_name or 'data_quality'}.{extension}"


def source_csv_path(card, study_name):
    source_type = card.get("source_csv")
    if source_type == "dashboard":
        path = os.path.join(config.storage_folder, f"{config.csv_prefix}{study_name}.csv")
        return path if os.path.isfile(path) else None

    filename = card.get("filename")
    if not filename or str(filename).startswith("__"):
        return None

    if filename == "Data_per_day*.csv":
        paths = resolve_data_per_day_paths(study_name)
        return paths or None

    return resolve_output_csv_path(
        study_name,
        filename,
        card.get("quality_folder", DEFAULT_DATA_QUALITY_FOLDER),
    )


def quality_download_frame(card, study_name, sensors=None, subjects=None, stages=None, flags=None):
    if card["filename"] == "Data_per_day*.csv":
        df = load_data_per_day_overview(study_name)
        if df is None:
            return pd.DataFrame()
        subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
        return apply_filter(df, subject_col, subjects)

    df = filtered_quality_csv(
        study_name,
        card["filename"],
        sensors,
        subjects,
        stages,
        flags,
        card.get("quality_folder", DEFAULT_DATA_QUALITY_FOLDER),
    )
    if df is None:
        return pd.DataFrame()
    return df


def live_download_frame(card, study_name, sensors=None, subjects=None, stages=None, flags=None):
    df = filtered_quality_csv(
        study_name,
        card["filename"],
        sensors,
        subjects,
        stages,
        flags,
        card.get("quality_folder", DEFAULT_DATA_QUALITY_FOLDER),
    )
    if df is None:
        return pd.DataFrame()
    return df



def configured_device_sensor_names(study_name):
    try:
        device_configs = get_analytics_study_json(study_name).get("wearables", [])
    except Exception:
        return set()

    sensor_names = set()
    for device_config in device_configs or []:
        device_name = str((device_config or {}).get("sensorname") or "").strip()
        for sensor in (device_config or {}).get("sensors", []):
            label = str((sensor or {}).get("wearable_sensor", "")).strip()
            if not label:
                continue
            sensor_names.add(build_wearable_dashboard_sensor_name(device_name, label))
    return sensor_names


def device_sensor_tab_label(study_name):
    try:
        device_configs = get_analytics_study_json(study_name).get("wearables", [])
    except Exception:
        return str(_("Device Sensor Data")).lower()

    device_sensor_labels = []
    seen = set()
    for device_config in device_configs or []:
        name = str((device_config or {}).get("sensorname") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        device_sensor_labels.append(name)

    if not device_sensor_labels:
        return str(_("Device Sensor Data")).lower()
    return " / ".join(device_sensor_labels).lower()


def device_sensor_names(study_name, available_sensors):
    configured_names = configured_device_sensor_names(study_name)
    device_sensor_prefixes = {
        f"{name.split('_', 1)[0].lower()}_"
        for name in configured_names
        if "_" in name
    }

    return {
        sensor
        for sensor in available_sensors
        if sensor in configured_names
        or any(str(sensor).lower().startswith(prefix) for prefix in device_sensor_prefixes)
    }


is_wearable_sensor_key = is_device_sensor_key
configured_wearable_sensor_names = configured_device_sensor_names
wearable_tab_label = device_sensor_tab_label
wearable_sensor_names = device_sensor_names
