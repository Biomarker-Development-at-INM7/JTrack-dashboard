import os
import re
import json
from pathlib import Path
from django import template
from django.contrib.auth.models import Group
from jdash.services.subject import Subject
from jdash.services import permissions
from jdash.config import constants
from jdash.models import SensorCatalog
from jdash.utils.fileutils import build_wearable_dashboard_sensor_name
register = template.Library()

def _iter_partner_logo_paths():
    """
    Yield relative static paths for partner logos from known static roots.

    Returns:
        list[str]: Sorted unique static-relative paths under icons/partners.
    """
    repo_root = Path(__file__).resolve().parents[2]
    candidate_dirs = [
        repo_root / "jdash" / "static" / "icons" / "partners",
        repo_root / "static" / "icons" / "partners",
    ]
    allowed_suffixes = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
    results = []

    for candidate_dir in candidate_dirs:
        if not candidate_dir.exists():
            continue
        for file_path in sorted(candidate_dir.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in allowed_suffixes:
                static_relative = file_path.relative_to(candidate_dir.parent.parent).as_posix()
                results.append(static_relative)

    # preserve order while removing duplicates
    return list(dict.fromkeys(results))


@register.simple_tag
def get_partner_logo_paths():
    """
    Return static-relative logo paths from the partners icon folder.

    Returns:
        list[str]: Paths that can be passed to the ``static`` template tag.
    """
    return _iter_partner_logo_paths()

def _normalize_sensor_token(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _get_wearable_sensor_code_map(wearables):
    """
    Build a label->code map for wearable sensors found in study JSON.

    Args:
        wearables (list): Wearable device configuration stored in study JSON.

    Returns:
        dict: Mapping from sensor label to DB sensor code.
    """
    labels = set()
    for wearable in wearables or []:
        if not isinstance(wearable, dict):
            continue
        for sensor in wearable.get("sensors", []):
            if not isinstance(sensor, dict):
                continue
            label = sensor.get("wearable_sensor", "")
            if label:
                labels.add(label)

    if not labels:
        return {}

    normalized_catalog = {
        _normalize_sensor_token(label): code
        for label, code in SensorCatalog.objects.all().values_list("label", "code")
    }
    return {
        label: normalized_catalog.get(_normalize_sensor_token(label), label)
        for label in labels
    }


def _normalize_dashboard_prefix(value):
    prefix = re.sub(r"[^A-Za-z0-9]+", "_", str(value or "").strip())
    return re.sub(r"_+", "_", prefix).strip("_").lower()


def _format_sensor_display_name(value):
    value = str(value or "").strip()
    if not value:
        return ""
    return value.lower()

def _get_wearable_dashboard_sensor_meta_map(study):
    """
    Build wearable metadata keyed by backend-provided dashboard sensor names.

    Args:
        study (dict): Study metadata dictionary containing ``wearables`` and
            ``dashboard_sensor_list``.

    Returns:
        dict: Mapping of normalized dashboard sensor name to display/button info.
    """
    wearables = (study or {}).get("wearables", []) or []
    dashboard_sensor_list = (study or {}).get("dashboard_sensor_list", []) or []
    sensor_code_map = _get_wearable_sensor_code_map(wearables)
    meta_map = {}
    available_dashboard_sensors = {
        str(sensor).strip().lower(): str(sensor).strip()
        for sensor in dashboard_sensor_list
    }

    for wearable in wearables or []:
        if not isinstance(wearable, dict):
            continue
        wearable_name = str(wearable.get("sensorname", "") or "").strip()
        wearable_prefix = _normalize_dashboard_prefix(wearable_name)
        wearable_prefix = f"{wearable_prefix}_" if wearable_prefix else ""
        for sensor in wearable.get("sensors", []) or []:
            if not isinstance(sensor, dict):
                continue
            label = str(sensor.get("wearable_sensor", "") or "").strip()
            if not label:
                continue
            normalized_label = _normalize_sensor_token(label)
            dashboard_sensor_name = None
            for normalized_sensor_name, original_sensor_name in available_dashboard_sensors.items():
                if wearable_prefix and not normalized_sensor_name.startswith(wearable_prefix):
                    continue
                remainder = normalized_sensor_name[len(wearable_prefix):] if wearable_prefix else normalized_sensor_name
                if _normalize_sensor_token(remainder) == normalized_label:
                    dashboard_sensor_name = original_sensor_name
                    break
            if not dashboard_sensor_name:
                continue
            sensor_code = sensor_code_map.get(label, label)
            button_label = f"{wearable_name}-{sensor_code}" if wearable_name else sensor_code
            formatted_label = _format_sensor_display_name(label)
            formatted_wearable_name = _format_sensor_display_name(wearable_name)
            display_label = f"{formatted_wearable_name} {formatted_label}".strip() if wearable_name else formatted_label
            meta_map[str(dashboard_sensor_name).strip().lower()] = {
                "button_label": button_label,
                "display_label": display_label,
            }

    return meta_map

@register.filter(name='get_n_batches')  
def get_n_batches(value, arg):
    """
    Retrieve the number of batches for a given sensor key from a dictionary.

    Args:
        value (dict): Dictionary containing sensor data.
        arg (str): Sensor name/key prefix.

    Returns:
        int: Number of batches for the sensor, or 0 if not found.
    """
    return value.get(arg + " n_batches", 0)


def get_last_time_received(value, arg):
    """
    Retrieve the last time data was received for a given sensor key from a dictionary.

    Args:
        value (dict): Dictionary containing sensor data.
        arg (str): Sensor name/key prefix.

    Returns:
        str: Timestamp of last time data received, or "none" if not found.
    """
    return value.get(arg + " last_time_received", "none")


def get_activity_status_tag(value, studyobj):
    """
    Generate an HTML span element with a CSS class and tooltip describing the subject's activity status.

    Args:
        value (dict): Subject data dictionary.
        studyobj (dict): Study object/dictionary used to determine status.

    Returns:
        str: HTML string representing the activity status with tooltip.
    """
    subject_instance = Subject(value, None)
    activity_status_code = subject_instance.get_activity_status_code(studyobj)

    title_map = {
        0: constants.no_data,
        1: constants.left_early,
        2: constants.duration_reached_left,
        3: constants.duration_reached,
        4: constants.multiple_qr,
    }
    class_map = {
        0: "text-danger",
        1: "text-primary",
        2: "text-warning",
        3: "text-success",
        4: "text-info",
    }
    css_class = class_map.get(activity_status_code, "text-secondary")
    title = title_map.get(activity_status_code, "Unknown status")
    subject_name = value.get("subject_name", "Unknown")

    return f'<span class="{css_class}" data-toggle="tooltip" data-placement="top" title="{title}">{subject_name}</span>'



@register.filter(name='get_status_tag') 
def get_status_tag(value):
    """
    Return an HTML strong span element describing subject's status code.

    Args:
        value (int): Status code of the subject.

    Returns:
        str: HTML string representing the status.
    """
    status_map = {
        0: ("Instudy", "text-primary"),
        1: ("Left study", "text-secondary"),
        2: ("Completed", "text-success"),
        3: ("Removed", "text-danger"),
    }
    label, css_class = status_map.get(value, ("Unknown", "text-secondary"))
    return f'<strong><span class="{css_class}">{label}</span></strong>'


@register.filter(name="get_subject_status_tag")
def get_subject_status_tag(subject_row, studyobj):
    """
    Return a subject status tag that can account for row-level timing details.

    Args:
        subject_row (dict): Dashboard-derived subject row.
        studyobj (dict): Study metadata dictionary.

    Returns:
        str: HTML string representing the status with tooltip.
    """
    if not isinstance(subject_row, dict):
        return get_status_tag(subject_row)

    status_code = subject_row.get("status_code")
    date_left_study = str(subject_row.get("date_left_study", "") or "").strip().lower()
    time_in_study = str(subject_row.get("time_in_study", "") or "").strip()
    study_duration = str((studyobj or {}).get("duration", "") or "").strip()

    def _parse_day_count(value):
        match = re.search(r"-?\d+", value)
        return int(match.group(0)) if match else None

    time_in_study_days = _parse_day_count(time_in_study)
    study_duration_days = _parse_day_count(study_duration)

    if (
        status_code == 0
        and date_left_study == "none"
        and time_in_study_days is not None
        and study_duration_days is not None
        and time_in_study_days > study_duration_days
    ):
        return (
            '<strong><span class="text-warning" data-bs-toggle="tooltip" '
            'data-bs-placement="top" title="Subject is still in study, but the configured duration is exceeded.">'
            'Instudy <small>(duration exceeded)</small></span></strong>'
        )

    return get_status_tag(status_code)


def get_sensor_tag(value, studyobj):
    """
    Generate HTML buttons for each sensor indicating their activity status.

    Args:
        value (dict): Subject data dictionary.
        studyobj (dict): Study object/dictionary used to determine sensor status.

    Returns:
        str: Concatenated HTML string of buttons for sensors with tooltips and status colors.
    """
    result = []
    subject_instance = Subject(value, None)
    sensor_dict = subject_instance.get_sensor_activity_code(value, studyobj)
    wearable_meta_map = _get_wearable_dashboard_sensor_meta_map(studyobj or {})
    if sensor_dict:
        for sensor, info in sensor_dict.items():
            status_code = info.get("status_code", -1)
            if status_code == 4:
                continue
            btn_class = {
                0: "btn-danger",
                1: "btn-warning",
                2: "btn-success",
                3: "btn-secondary",
                4: "btn-light",
            }.get(status_code, "btn-outline-secondary")

            desc = info.get("status_desc", "")
            wearable_meta = wearable_meta_map.get(str(sensor).strip().lower(), {})
            sensor_code = wearable_meta.get("button_label") or info.get("sensor_code", sensor)
            button_html = (
                f'<button style="margin-left:2px" class="btn {btn_class}" '
                f'data-sensor-name="{sensor}" data-bs-toggle="tooltip" '
                f'data-bs-placement="top" title="{desc}">{sensor_code}</button>'
            )
            result.append(button_html)

    return "".join(result)

@register.filter(name="get_sensor_activity_json")
def get_sensor_activity_json(value, studyobj):
    """
    Serialize the backend sensor activity map for a subject row so the
    details-panel UI can reuse the same status semantics as the sensor tags.

    Args:
        value (dict): Subject data dictionary.
        studyobj (dict): Study object/dictionary used to determine sensor status.

    Returns:
        str: JSON string for the per-sensor activity/status map.
    """
    subject_instance = Subject(value, None)
    sensor_dict = subject_instance.get_sensor_activity_code(value, studyobj)
    return json.dumps(sensor_dict)


@register.filter(name="get_dashboard_sensor_filter_values")
def get_dashboard_sensor_filter_values(study):
    """
    Build a JSON object of sensor filter labels -> values.

    Args:
        study (dict): Study metadata.

    Returns:
        dict: Mapping whose labels are user-friendly and whose values match the
        compact codes shown in the table.
    """
    values = {}

    def _add(label, value):
        label = str(label or "").strip()
        value = str(value or "").strip()
        if label and value and value not in values:
            values[value] = label

    wearables = study.get("wearables", []) or []
    wearable_sensor_meta_map = _get_wearable_dashboard_sensor_meta_map(study)
    wearable_dashboard_sensors = set(wearable_sensor_meta_map.keys())
    base_dashboard_sensors = {
        str(sensor).strip().lower()
        for sensor in (study.get("sensor_list", []) or [])
    }
    base_dashboard_sensors.update(
        str(sensor).strip().lower()
        for sensor in (study.get("sensor_list_limited", []) or [])
    )

    if study.get("survey"):
        _add(constants.ema, constants.ema)

    for sensor in study.get("dashboard_sensor_list", []) or []:
        normalized_sensor = str(sensor).strip().lower()
        if (
            normalized_sensor in wearable_dashboard_sensors
            and normalized_sensor not in base_dashboard_sensors
        ):
            continue
        sensor_code = constants.sensor_list.get(sensor, sensor)
        sensor_label = _format_sensor_display_name(sensor)
        if sensor_label != sensor_code:
            _add(f"{sensor_label} ({sensor_code})", sensor_code)
        else:
            _add(sensor_code, sensor_code)

    for wearable in wearables:
        if not isinstance(wearable, dict):
            continue
        wearable_name = str(wearable.get("sensorname", "") or "").strip()
        wearable_prefix = _normalize_dashboard_prefix(wearable_name)
        for sensor in wearable.get("sensors", []) or []:
            if not isinstance(sensor, dict):
                continue
            label = str(sensor.get("wearable_sensor", "") or "").strip()
            if not label:
                continue
            normalized_label = _normalize_sensor_token(label)
            meta = {}
            for dashboard_sensor_name, dashboard_sensor_meta in wearable_sensor_meta_map.items():
                if wearable_prefix and not dashboard_sensor_name.startswith(f"{wearable_prefix}_"):
                    continue
                remainder = dashboard_sensor_name[len(wearable_prefix) + 1:] if wearable_prefix else dashboard_sensor_name
                if _normalize_sensor_token(remainder) == normalized_label:
                    meta = dashboard_sensor_meta
                    break
            sensor_code = meta.get("button_label", label)

            formatted_label = _format_sensor_display_name(label)
            formatted_wearable_name = _format_sensor_display_name(wearable_name)
            if wearable_name:
                _add(f"{formatted_wearable_name} {formatted_label} ({sensor_code})", sensor_code)
            else:
                _add(f"{formatted_label} ({sensor_code})", sensor_code)

    return values

@register.filter(name="get_sensor_codes")
def get_sensor_codes(sensor_list, current_sensor_list):
    """
    Render sensor codes as HTML buttons, highlighting those active today.

    Args:
        sensor_list (list or str): List of sensor keys or single sensor key as string.
        current_sensor_list (list): List of sensors active today.

    Returns:
        str: Concatenated HTML string of buttons for sensors.
    """
    if sensor_list is None:
        sensor_list = []
    if current_sensor_list is None:
        current_sensor_list = []
    if isinstance(sensor_list, str):
        sensor_list = [sensor_list]

    result = []
    for sensor in sensor_list:
        label = constants.sensor_list.get(sensor, sensor)
        btn_class = "btn-light today-sensor" if sensor in current_sensor_list else "btn-light"
        button_html = (
            f'<button style="margin-left:2px" class="btn {btn_class}" '
            f'data-toggle="tooltip" data-placement="top" title="{sensor}">{label}</button>'
        )
        result.append(button_html)
    return "".join(result)

@register.filter(name="get_study_sensor_summary")
def get_study_sensor_summary(study, current_sensor_list):
    """
    Render passive and wearable sensors for a study in one combined HTML string.

    Args:
        study (dict): Study dictionary for the index page.
        current_sensor_list (list): List of sensors active today.

    Returns:
        str: Combined HTML for passive and wearable sensors.
    """
    if not isinstance(study, dict):
        return ""
    passive_html = get_sensor_codes(study.get("sensor_list"), current_sensor_list)
    wearable_html = get_wearable_sensor_codes(study.get("wearables"), current_sensor_list)
    return f"{passive_html}{wearable_html}"

@register.filter(name="get_size")
def get_size(obj):
    """
    Return the length of an object.

    Args:
        obj (iterable): Any iterable object.

    Returns:
        int: Length of the iterable.
    """
    return len(obj)

@register.filter(name="get_item")
def get_item(lst, index):
    """
    Retrieve the 'db_id' field of an item at a given index in a list.

    Args:
        lst (list): List of dictionaries.
        index (int): Index of the item.

    Returns:
        any or None: The 'db_id' of the item or None if not found.
    """
    try:
        return lst[index]["db_id"]
    except (IndexError, TypeError, KeyError):
        return None


@register.filter(name="get_subText")
def get_subText(obj):
    """
    Retrieve the 'subText' from the first dictionary in a list containing it.

    Args:
        obj (list): List of dictionaries.

    Returns:
        str or None: The 'subText' value or None if not found.
    """
    for answer in obj:
        if "subText" in answer:
            return answer["subText"]
    return None


@register.filter(name="get_id")
def get_id(obj):
    """
    Concatenate all 'db_id' fields from a list of dictionaries separated by semicolons.

    Args:
        obj (list): List of dictionaries.

    Returns:
        str: Semicolon-separated string of 'db_id's.
    """
    ids = [str(answer["db_id"]) for answer in obj if "db_id" in answer]
    return ";".join(ids)


@register.filter(name="get_sortId")
def get_sortId(obj):
    """
    Retrieve the 'id' field from the first dictionary in a list containing it.

    Args:
        obj (list): List of dictionaries.

    Returns:
        any or None: The 'id' value or None if not found.
    """
    for answer in obj:
        if "id" in answer:
            return answer["id"]
    return None


@register.filter(name="get_value")
def get_value(obj):
    """
    Retrieve the 'value' field from the first dictionary in a list.

    Args:
        obj (list): List of dictionaries.

    Returns:
        any or None: The 'value' or None if not found.
    """
    for answer in obj:
        if "value" in answer:
            return answer["value"]
    return None


@register.filter(name="get_defaultValue")
def get_defaultValue(obj):
    """
    Retrieve the 'defaultValue' field from the first dictionary in a list.

    Args:
        obj (list): List of dictionaries.

    Returns:
        any or None: The 'defaultValue' or None if not found.
    """
    for answer in obj:
        if "defaultValue" in answer:
            return answer["defaultValue"]
    return None


@register.filter(name="get_stepSize")
def get_stepSize(obj):
    """
    Retrieve the 'stepSize' field from the first dictionary in a list.

    Args:
        obj (list): List of dictionaries.

    Returns:
        any or None: The 'stepSize' or None if not found.
    """
    for answer in obj:
        if "stepSize" in answer:
            return answer["stepSize"]
    return None


@register.filter(name="get_minVal")
def get_minVal(obj):
    """
    Retrieve the 'minVal' or fallback to 'minValue' from the first dictionary in a list.

    Args:
        obj (list): List of dictionaries.

    Returns:
        any or None: The minimum value or None if not found.
    """
    for answer in obj:
        if "minVal" in answer:
            return answer["minVal"]
        elif "minValue" in answer:
            return answer["minValue"]
    return None


@register.filter(name="get_maxVal")
def get_maxVal(obj):
    """
    Retrieve the 'maxVal' or fallback to 'maxValue' from the first dictionary in a list.

    Args:
        obj (list): List of dictionaries.

    Returns:
        any or None: The maximum value or None if not found.
    """
    for answer in obj:
        if "maxVal" in answer:
            return answer["maxVal"]
        elif "maxValue" in answer:
            return answer["maxValue"]
    return None


@register.filter(name="get_minText")
def get_minText(obj):
    """
    Retrieve the 'minText' field from the first dictionary in a list.

    Args:
        obj (list): List of dictionaries.

    Returns:
        str or None: The 'minText' value or None if not found.
    """
    for answer in obj:
        if "minText" in answer:
            return answer["minText"]
    return None


@register.filter(name="get_maxText")
def get_maxText(obj):
    """
    Retrieve the 'maxText' field from the first dictionary in a list.

    Args:
        obj (list): List of dictionaries.

    Returns:
        str or None: The 'maxText' value or None if not found.
    """
    for answer in obj:
        if "maxText" in answer:
            return answer["maxText"]
    return None


@register.filter(name="get_question_category")
def get_question_category(value):
    """
    Map question category codes to human-readable strings.

    Args:
        value (int): Category code.

    Returns:
        str: Category name or "Unknown Category" if code not recognized.
    """
    categories = {
        0: 'Instruction for questions',
        1: 'Single Choice',
        2: 'Multiple Choice',
        3: 'Sliding',
        4: 'Free Text',
        5: 'Free Number',
        6: 'Time',
        7: 'Date',
        8: 'Time and Date',
        9: 'Duration',
        10: 'Location',
        11: 'Consent',
    }
    return categories.get(value, "Unknown Category")


@register.filter(name="get_category_title")
def get_category_title(category_value, categories):
    """
    Resolve a survey category value to its display title.

    Args:
        category_value (int): Stored question category value.
        categories (list): Survey category dictionaries.

    Returns:
        str or int: Matching category title, otherwise the original value.
    """
    if not categories:
        return category_value

    for category in categories:
        if category.get("categoryValue") == category_value:
            return category.get("categoryTitle", category_value)

    return category_value


@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Check if a user belongs to a specific group.

    Args:
        user (User): Django user instance.
        group_name (str): Name of the group to check.

    Returns:
        bool: True if user belongs to the group, False otherwise.
    """
    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return False
    return group in user.groups.all()


@register.filter(name="can_manage_study")
def can_manage_study(user):
    return permissions.can_manage_study(user)


@register.filter(name="is_administrator")
def is_administrator(user):
    return permissions.is_administrator(user)


@register.filter(name="is_investigator")
def is_investigator(user):
    return permissions.is_investigator(user)


@register.filter(name="is_viewer")
def is_viewer(user):
    return permissions.is_viewer(user)


@register.filter(name="role_group_label")
def role_group_label(user):
    if permissions.is_administrator(user):
        return "Administrator"
    if permissions.is_investigator(user):
        return "Investigator"
    if permissions.is_viewer(user):
        return "Viewer"
    return ""


@register.filter(name="can_qc_study")
def can_qc_study(user):
    return permissions.can_qc_study(user)


@register.filter(name="can_manage_subjects")
def can_manage_subjects(user):
    return permissions.can_manage_subjects(user)


@register.filter(name="can_manage_survey")
def can_manage_survey(user):
    return permissions.can_manage_survey(user)


@register.filter(name="can_manage_categories")
def can_manage_categories(user):
    return permissions.can_manage_categories(user)


@register.filter(name="can_manage_questions")
def can_manage_questions(user):
    return permissions.can_manage_questions(user)


@register.filter(name="can_duplicate_survey")
def can_duplicate_survey(user):
    return permissions.can_duplicate_survey(user)


@register.filter(name="can_delete_survey")
def can_delete_survey(user):
    return permissions.can_delete_survey(user)


@register.filter(name="get_text")
def get_text(obj):
    choicesStr = ""

    for answer in obj:
        choicesStr = choicesStr + answer["text"] + ";"

    return choicesStr

# Register filters
register.filter('get_last_time_received', get_last_time_received)
register.filter('get_n_batches', get_n_batches)
register.filter('get_status_tag', get_status_tag)
register.filter('get_sensor_tag', get_sensor_tag)
register.filter('get_activity_status_tag', get_activity_status_tag)



@register.filter(name="get_wearable_sensor_lines")
def get_wearable_sensor_lines(wearables):
    """
    Render wearable sensors as plain paragraph lines for the details page.

    Args:
        wearables (list): Wearable device configuration stored in study JSON.

    Returns:
        str: Concatenated HTML paragraphs for wearable sensors.
    """
    if not wearables:
        return ""

    result = []
    for wearable in wearables:
        if not isinstance(wearable, dict):
            continue
        device_name = " ".join(
            part for part in [wearable.get("sensorname", ""), wearable.get("model", "")]
            if part
        ).strip()
        for sensor in wearable.get("sensors", []):
            if not isinstance(sensor, dict):
                continue
            label = sensor.get("wearable_sensor", "")
            if not label:
                continue
            sampling_rate = sensor.get("sampling_rate", "-")
            unit = sensor.get("unit", "-")
            line = _format_sensor_display_name(label)
            if device_name:
                line = f"{line} ({device_name})"
            line = f"{line} - {sampling_rate}"
            result.append(f"<p>{line}</p>")

    return "".join(result)

@register.filter(name="get_wearable_sensor_display_map")
def get_wearable_sensor_display_map(study):
    """
    Build a case-insensitive display-name map for wearable sensors from the
    backend-provided dashboard sensor keys.

    Args:
        study (dict): Study metadata dictionary containing ``wearables`` and
            ``dashboard_sensor_list``.

    Returns:
        dict: Mapping from lower-cased wearable sensor label to display text.
    """
    display_map = {}
    for dashboard_sensor_name, meta in _get_wearable_dashboard_sensor_meta_map(study).items():
        display_map[dashboard_sensor_name] = meta["display_label"]
    return display_map

@register.filter(name="get_study_sensor_summary")
def get_study_sensor_summary(study, current_sensor_list):
    """
    Render passive and wearable sensors for a study in one combined HTML string.

    Args:
        study (dict): Study dictionary for the index page.
        current_sensor_list (list): List of sensors active today.

    Returns:
        str: Combined HTML for passive and wearable sensors.
    """
    if not isinstance(study, dict):
        return ""

    passive_html = get_sensor_codes(study.get("sensor_list"), current_sensor_list)
    wearable_html = get_wearable_sensor_codes(study.get("wearables"),current_sensor_list)
    return f"{passive_html}{wearable_html}"

def _sensor_key_matches_any(candidate_keys, active_sensor_keys):
    active_exact = {str(key or "").strip().lower() for key in active_sensor_keys or []}
    active_normalized = {_normalize_sensor_token(key) for key in active_sensor_keys or []}

    for candidate in candidate_keys:
        candidate = str(candidate or "").strip()
        if not candidate:
            continue
        if candidate.lower() in active_exact:
            return True
        if _normalize_sensor_token(candidate) in active_normalized:
            return True

    return False

@register.filter(name="get_wearable_sensor_codes")
def get_wearable_sensor_codes(wearables, current_sensor_list):
    """
    Render wearable sensor labels as HTML buttons.

    Args:
        wearables (list): Wearable device configuration stored in study JSON.
        current_sensor_list (list): Dashboard sensor keys active today.

    Returns:
        str: Concatenated HTML string of buttons for wearable sensors.
    """
    if not wearables:
        return ""
    print("SUMMARY DEBUG",  current_sensor_list)
    sensor_code_map = _get_wearable_sensor_code_map(wearables)
    result = []
    for wearable in wearables:
        sensor_entries = wearable.get("sensors", []) if isinstance(wearable, dict) else []
        device_name = ""
        wearable_name = ""
        if isinstance(wearable, dict):
            sensorname = wearable.get("sensorname", "")
            model = wearable.get("model", "")
            wearable_name = sensorname.strip()

        for sensor in sensor_entries:
            if not isinstance(sensor, dict):
                continue
            label = sensor.get("wearable_sensor", "")
            if not label:
                continue
            sensor_code = sensor_code_map.get(label, label)
            sampling_rate = sensor.get("sampling_rate", "-")
            tooltip_parts = [label, f"rate: {sampling_rate}"]
            tooltip = " | ".join(part for part in tooltip_parts if part)
            button_label = sensor_code
            if wearable_name:
                button_label = f"{wearable_name}-{sensor_code}"
            dashboard_sensor_name = build_wearable_dashboard_sensor_name(wearable_name, label)
            is_current = _sensor_key_matches_any([dashboard_sensor_name, button_label], current_sensor_list)
            btn_class = "btn-light today-sensor" if is_current else "btn-light"
            button_html = (
                f'<button style="margin-left:2px" class="btn {btn_class} wearable-sensor" '
                f'data-bs-toggle="tooltip" data-bs-placement="top" title="{tooltip}">{button_label}</button>'
            )
            result.append(button_html)

    return "".join(result)

@register.filter(name="has_ema_sensor")
def has_ema_sensor(study):
    """
    Return True when a study includes EMA/survey collection.
    """
    if not isinstance(study, dict):
        return False
    sensor_list = study.get("sensor_list") or []
    if isinstance(sensor_list, str):
        sensor_list = [sensor_list]
    return constants.ema in sensor_list or bool(study.get("survey"))


@register.filter(name="has_wearable_sensors")
def has_wearable_sensors(study):
    """
    Return True when a study includes at least one wearable sensor.
    """
    if not isinstance(study, dict):
        return False
    for wearable in study.get("wearables", []) or []:
        if isinstance(wearable, dict) and wearable.get("sensors"):
            return True
    return False


@register.filter(name="has_active_labeling")
def has_active_labeling(study):
    """
    Return True when a study has active labeling sensors configured.
    """
    if not isinstance(study, dict):
        return False
    sensor_list_limited = study.get(constants.field_name_sensor_list_limited) or []
    return bool(sensor_list_limited)

