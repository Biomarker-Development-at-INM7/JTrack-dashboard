from django import template
from django.contrib.auth.models import Group
from jdash.services.subject import Subject
from jdash.config import constants
from jdash.models import SensorCatalog

register = template.Library()


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

    return dict(
        SensorCatalog.objects.filter(label__in=labels).values_list("label", "code")
    )

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
    Return an HTML strong span element with a tooltip describing subject's status code.

    Args:
        value (int): Status code of the subject.

    Returns:
        str: HTML string representing the status with tooltip.
    """
    status_map = {
        0: ("Instudy", "Everything is fine", "text-warning"),
        1: ("Left study", "Subject left study with this QR Code", "text-primary"),
        2: ("Completed", "Subject reached study duration and left automatically", "text-success"),
        3: ("Removed", "Subject removed by dashboard", "text-danger"),
    }
    label, tooltip, css_class = status_map.get(value, ("Unknown", "Unknown status", "text-secondary"))
    return f'<strong><span class="{css_class}" data-toggle="tooltip" data-placement="top" title="{tooltip}">{label}</span></strong>'


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

    if sensor_dict:
        for sensor, info in sensor_dict.items():
            status_code = info.get("status_code", -1)
            btn_class = {
                1: "btn-primary",
                2: "btn-warning",
                3: "btn-success",
            }.get(status_code, "btn-danger")

            desc = info.get("status_desc", "")
            sensor_code = info.get("sensor_code", sensor)
            button_html = (
                f'<button style="margin-left:2px" class="btn {btn_class}" '
                f'data-toggle="tooltip" data-placement="top" title="{desc}">{sensor_code}</button>'
            )
            result.append(button_html)

    return "".join(result)


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
    wearable_html = get_wearable_sensor_codes(study.get("wearables"))
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
            line = label
            if device_name:
                line = f"{line} ({device_name})"
            line = f"{line} - {sampling_rate}"
            result.append(f"<p>{line}</p>")

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
    wearable_html = get_wearable_sensor_codes(study.get("wearables"))
    return f"{passive_html}{wearable_html}"

@register.filter(name="get_wearable_sensor_codes")
def get_wearable_sensor_codes(wearables):
    """
    Render wearable sensor labels as HTML buttons.

    Args:
        wearables (list): Wearable device configuration stored in study JSON.

    Returns:
        str: Concatenated HTML string of buttons for wearable sensors.
    """
    if not wearables:
        return ""

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
            device_name = " ".join(part for part in [sensorname, model] if part).strip()

        for sensor in sensor_entries:
            if not isinstance(sensor, dict):
                continue
            label = sensor.get("wearable_sensor", "")
            if not label:
                continue
            sensor_code = sensor_code_map.get(label, label)
            sampling_rate = sensor.get("sampling_rate", "-")
            unit = sensor.get("unit", "-")
            tooltip_parts = [device_name, label, f"rate: {sampling_rate}"]
            tooltip = " | ".join(part for part in tooltip_parts if part)
            button_label = sensor_code
            if wearable_name:
                button_label = f"{wearable_name}-{sensor_code}"
            button_html = (
                f'<button style="margin-left:2px" class="btn btn-light wearable-sensor" '
                f'data-toggle="tooltip" data-placement="top" title="{tooltip}">{button_label}</button>'
            )
            result.append(button_html)

    return "".join(result)


