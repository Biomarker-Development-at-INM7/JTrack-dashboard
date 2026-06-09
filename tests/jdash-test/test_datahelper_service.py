import pytest
from unittest.mock import MagicMock
from jdash.services import datahelper

# Patch gettext to simplify assertions
datahelper.gettext = lambda s: s

@pytest.mark.parametrize("value,expected", [
    ("non-empty", True),
    ("", False),
    (None, False),
    ("null", False)
])
def test_validate_empty(value, expected):
    assert datahelper.validate_empty(value) == expected

def test_get_study_form_data():
    form = MagicMock()
    form.cleaned_data = {
        'study_label': 'Study 1',
        'study_description': 'A description',
        'study_duration': 5,
        'number_of_subjects': 10,
        'ema_checkbox': True,
        'survey': '1',
        'is_test': True,
        'recording_freq': 'daily',
        'sensor_list_limited': ['acc'],
        'sensor_list': ['acc'],
    }

    taskform = MagicMock()
    taskform.cleaned_data = {
        'task_name': 'Walk',
        'task_preparation': 1,
        'task_duration': 5,
        'task_description': 'Walk description'
    }
    formset = MagicMock()
    formset.is_valid.return_value = True
    formset.__iter__.return_value = [taskform]

    request = MagicMock()
    request.FILES = {
        'json_file': MagicMock(read=lambda: b'{"questions": []}'),
        'images_zip_file': True
    }
    study_device_formset = MagicMock()
    study_device_formset.forms = []

    result = datahelper.get_study_form_data(
        form,
        formset,
        request,
        study_device_formset,
        [],
    )
    assert result['name'] == 'Study 1'
    assert result['images'] is True
    assert result['survey'] == {"questions": []}
    assert result['task_list'][0]['task_name'] == 'Walk'
    assert result['wearables'] == []
    assert result['device_sensor_rows'] == []


def test_get_study_device_config_builders_with_garmin_overrides():
    device = MagicMock()
    device.id = 11
    device.name = "Garmin"
    device.model = "Venu 3"

    sensor = MagicMock()
    sensor.label = "Heart Rate"

    default_sampling_rate = MagicMock()
    default_sampling_rate.value = "1Hz"
    default_sampling_rate.id = 101

    override_sampling_rate = MagicMock()
    override_sampling_rate.value = "5Hz"
    override_sampling_rate.id = 102

    default_unit = MagicMock()
    default_unit.value = "bpm"
    default_unit.id = 201

    override_unit = MagicMock()
    override_unit.value = "beats/minute"
    override_unit.id = 202

    device_sensor = MagicMock()
    device_sensor.id = 301
    device_sensor.device_id = device.id
    device_sensor.sensor = sensor
    device_sensor.default_sampling_rate = default_sampling_rate
    device_sensor.default_unit = default_unit

    device_form = MagicMock()
    device_form.cleaned_data = {"device": device}
    study_device_formset = MagicMock()
    study_device_formset.forms = [device_form]

    sensor_form = MagicMock()
    sensor_form.cleaned_data = {
        "device_sensor": device_sensor,
        "sampling_rate": override_sampling_rate,
        "unit": override_unit,
    }
    sensor_formset = MagicMock()
    sensor_formset.forms = [sensor_form]

    wearables = datahelper.get_study_device_config_json(
        study_device_formset,
        [sensor_formset],
    )
    db_rows = datahelper.get_study_device_config_rows_for_db(
        study_device_formset,
        [sensor_formset],
    )

    assert wearables == [{
        "id": device.id,
        "sensorname": "Garmin",
        "model": "Venu 3",
        "sensors": [{
            "wearable_sensor": "Heart Rate",
            "sampling_rate": "5Hz",
            "unit": "beats/minute",
        }],
    }]
    assert db_rows == [{
        "device_id": device.id,
        "device_sensor_id": device_sensor.id,
        "sampling_rate_id": override_sampling_rate.id,
        "unit_id": override_unit.id,
    }]


def test_get_study_device_config_builders_fall_back_to_device_default_unit():
    device = MagicMock()
    device.id = 11
    device.name = "Garmin"
    device.model = "Venu 3"

    sensor = MagicMock()
    sensor.label = "Heart Rate"

    default_sampling_rate = MagicMock()
    default_sampling_rate.value = "1Hz"
    default_sampling_rate.id = 101

    default_unit = MagicMock()
    default_unit.value = "bpm"
    default_unit.id = 201

    device_sensor = MagicMock()
    device_sensor.id = 301
    device_sensor.device_id = device.id
    device_sensor.sensor = sensor
    device_sensor.default_sampling_rate = default_sampling_rate
    device_sensor.default_unit = default_unit

    device_form = MagicMock()
    device_form.cleaned_data = {"device": device}
    study_device_formset = MagicMock()
    study_device_formset.forms = [device_form]

    sensor_form = MagicMock()
    sensor_form.cleaned_data = {
        "device_sensor": device_sensor,
        "sampling_rate": None,
        "unit": None,
    }
    sensor_formset = MagicMock()
    sensor_formset.forms = [sensor_form]

    wearables = datahelper.get_study_device_config_json(
        study_device_formset,
        [sensor_formset],
    )
    db_rows = datahelper.get_study_device_config_rows_for_db(
        study_device_formset,
        [sensor_formset],
    )

    assert wearables == [{
        "id": device.id,
        "sensorname": "Garmin",
        "model": "Venu 3",
        "sensors": [{
            "wearable_sensor": "Heart Rate",
            "sampling_rate": "1Hz",
            "unit": "bpm",
        }],
    }]
    assert db_rows == [{
        "device_id": device.id,
        "device_sensor_id": device_sensor.id,
        "sampling_rate_id": None,
        "unit_id": None,
    }]

def test_get_survey_form_data():
    form = MagicMock()
    form.cleaned_data = {
        'title': 'Survey 1',
        'description': 'desc',
        'splitbyCategory': False,
        'scrolling': True,
        'topN': 5
    }
    result = datahelper.get_survey_form_data(form)
    assert result['title'] == 'Survey 1'

def test_get_question_form_data():
    form = MagicMock()
    form.cleaned_data = {
        'title': 'Question?',
        'active': True,
        'sortId': 1,
        'subText': 'Some help',
        'frequency': 'daily',
        'clockTime': '08:00',
        'clockTime_start': '07:00',
        'clockTime_end': '09:00',
        'activate_question': True,
        'deactivate_question': False,
        'activation_condition': None,
        'deactivation_condition': None,
        'nextDayToAnswer': True,
        'category': 'Mood',
        'imageURL': 'http://image.url',
        'url': 'http://url.com',
        'questionType': 'slider',
        'deactivateOnAnswer': False,
        'deactivateOnDate': '2025-01-01',
        'clockTime_timezone': None
    }

    result = datahelper.get_question_form_data(form)
    assert result['title'] == 'Question?'
    assert result['clockTime_timezone'] == 'Europe/Berlin'

def test_get_answer_form_data():
    answer = MagicMock()
    answer.cleaned_data = {
        'answerSortId': 1,
        'text': 'Yes',
        'answerSubText': 'Positive',
        'value': None,
        'defaultValue': None,
        'stepSize': None,
        'minValue': None,
        'maxValue': None,
        'minText': None,
        'maxText': None
    }

    formset = MagicMock()
    formset.forms = [answer]

    result = datahelper.get_answer_form_data(formset)
    assert result['answers'][0]['text'] == 'Yes'
    assert result['answers'][0]['value'] == 0.1

def test_get_category_form_data():
    category = MagicMock()
    category.cleaned_data = {
        'categoryTitle': 'Category A',
        'didSubjectAsk': False,
        'categoryValue': 3
    }

    result = datahelper.get_category_form_data([category])
    assert result['category_list'][0]['categoryTitle'] == 'Category A'

def test_get_contactus_form_data():
    form = MagicMock()
    form.cleaned_data = {
        'fullname': 'John Doe',
        'email': 'john@example.com',
        'message': 'Need help'
    }
    name, email, msg = datahelper.get_contactus_form_data(form)
    assert name == 'John Doe'
    assert 'example.com' in email

def test_get_notification_form_data():
    form = MagicMock()
    form.cleaned_data = {
        'message_title': 'Alert',
        'message_text': 'Something happened',
        'receivers': ['admin']
    }
    title, text, rec = datahelper.get_notification_form_data(form)
    assert title == 'Alert'
    assert 'admin' in rec

def test_get_info_texts():
    result = datahelper.get_info_texts()
    assert "ema" in result

def test_get_help_texts_for_survey_form():
    result = datahelper.get_help_texts_for_survey_form()
    assert "title" in result

def test_get_help_texts_for_question_form():
    result = datahelper.get_help_texts_for_question_form()
    assert "sortId" in result

def test_get_help_texts_for_category_form():
    result = datahelper.get_help_texts_for_category_form()
    assert "title" in result

def test_get_help_texts_for_study_form():
    result = datahelper.get_help_texts_for_study_form()
    assert "title" in result
