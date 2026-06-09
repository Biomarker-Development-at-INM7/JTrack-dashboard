import os
import json
import time
import pytest
from unittest.mock import patch, MagicMock, mock_open, call
from datetime import datetime, timedelta
from jdash.services import subject
from jdash.config import constants

@pytest.fixture
def sample_subject_obj():
    now = datetime.now()
    registered = (now - timedelta(days=5)).strftime(subject.timestamp_format)
    left_none = 'none'
    return {
        "subject_name": "subj1",
        "app": "app",
        "sensor1 last_time_received": "2025-06-10 17:48:23",
        'status_code': 0,
        "date_registered": "2025-06-08 17:48:23",
        "date_left_study": "none",
        "time_in_study": "1 days",
        'last_time_received sensor1': (now - timedelta(days=3)).strftime(subject.timestamp_format),
        'last_time_received sensor2': 'none',
    }

@pytest.fixture
def sample_subject_json():
    return {'studyId': 'study1'}

def test_subject_init_populates_fields(sample_subject_obj, sample_subject_json):
    subj = subject.Subject(sample_subject_obj, sample_subject_json)
    assert subj.subject_name == sample_subject_obj['subject_name']
    assert subj.app == sample_subject_obj['app']
    assert 'sensor1' in subj.sensor_last_times_received
    assert 'sensor2' in subj.sensor_last_times_received
    assert subj.study_enrolled_in == sample_subject_json['studyId']

def test_get_activity_status_code_various_conditions(sample_subject_obj, sample_subject_json):
    subj = subject.Subject(sample_subject_obj, sample_subject_json)
    study_obj = {'duration': '4'}

    # Test case: time_in_study less than duration, date_left_study 'none'
    code = subj.get_activity_status_code(study_obj)
    assert code in [0, 2, 4]

    # Test case: date_left_study not 'none' and duration reached
    past_date = (datetime.now() - timedelta(days=5)).strftime(subject.timestamp_format)
    sample_subject_obj['date_left_study'] = past_date
    subj = subject.Subject(sample_subject_obj, sample_subject_json)
    code = subj.get_activity_status_code(study_obj)
    assert code in [1, 3]

@pytest.mark.parametrize("sample_subject_obj,sample_subject_json", [
    (
        {
            "subject_name": "subj1",
            "app": "app",
            'status_code': 0,
            "date_registered": "2025-06-08 17:54:12",
            "date_left_study": "none",
            "time_in_study": "1 days",
            "last_time_received sensor1": "2025-06-10 17:54:12",
        },
        {"studyId": "study1"}
    )
])
def test_get_sensor_activity_code_logic(sample_subject_obj, sample_subject_json, monkeypatch):
    # Monkeypatch sensor_list to include 'sensor1'
    monkeypatch.setitem(constants.sensor_list, 'sensor1', 'Sensor 1 Code')

    subj = subject.Subject(sample_subject_obj, sample_subject_json)
    study_obj = {'duration': '4'}

    result = subj.get_sensor_activity_code(None, study_obj)

    assert 'sensor1' in result
    assert result['sensor1']['sensor_code'] == 'Sensor 1 Code'


def test_get_sensor_activity_code_left_study_forces_completed_status(monkeypatch):
    monkeypatch.setitem(constants.sensor_list, 'sensor1', 'Sensor 1 Code')
    subject_obj = {
        "subject_name": "subj1",
        "app": "app",
        "sensor1 last_time_received": "2025-06-10 17:54:12",
        "status_code": 1,
        "date_registered": "2025-06-08 17:54:12",
        "date_left_study": "2025-06-09 17:54:12",
        "time_in_study": "1 days",
    }

    subj = subject.Subject(subject_obj, {"studyId": "study1"})
    result = subj.get_sensor_activity_code(None, {'duration': '4'})

    assert result['sensor1']['status_code'] == 3
    assert result['sensor1']['status_desc'] == constants.no_sensor_left_early


def test_get_sensor_activity_code_duration_exceeded_uses_warning_status(monkeypatch):
    monkeypatch.setitem(constants.sensor_list, 'sensor1', 'Sensor 1 Code')
    subject_obj = {
        "subject_name": "subj1",
        "app": "app",
        "sensor1 last_time_received": "2025-06-10 17:54:12",
        "status_code": 0,
        "date_registered": "2025-06-08 17:54:12",
        "date_left_study": "none",
        "time_in_study": "5 days",
    }

    subj = subject.Subject(subject_obj, {"studyId": "study1"})
    result = subj.get_sensor_activity_code(None, {'duration': '4'})

    assert result['sensor1']['status_code'] == 1
    assert result['sensor1']['status_desc'] == constants.no_sensor_duration_exceeded


def test_get_sensor_activity_code_none_timestamp_uses_no_data_yet_status(monkeypatch):
    monkeypatch.setitem(constants.sensor_list, 'sensor1', 'Sensor 1 Code')
    subject_obj = {
        "subject_name": "subj1",
        "app": "app",
        "sensor1 last_time_received": "none",
        "status_code": 0,
        "date_registered": "2025-06-08 17:54:12",
        "date_left_study": "none",
        "time_in_study": "1 days",
    }

    subj = subject.Subject(subject_obj, {"studyId": "study1"})
    result = subj.get_sensor_activity_code(None, {'duration': '4'})

    assert result['sensor1']['status_code'] == 4
    assert result['sensor1']['status_desc'] == constants.no_sensor_not_received


def test_get_sensor_activity_code_none_timestamp_overrides_duration_exceeded(monkeypatch):
    monkeypatch.setitem(constants.sensor_list, 'sensor1', 'Sensor 1 Code')
    subject_obj = {
        "subject_name": "subj1",
        "app": "app",
        "sensor1 last_time_received": "none",
        "status_code": 0,
        "date_registered": "2025-06-08 17:54:12",
        "date_left_study": "none",
        "time_in_study": "5 days",
    }

    subj = subject.Subject(subject_obj, {"studyId": "study1"})
    result = subj.get_sensor_activity_code(None, {'duration': '4'})

    assert result['sensor1']['status_code'] == 4
    assert result['sensor1']['status_desc'] == constants.no_sensor_not_received


def test_get_sensor_activity_code_none_timestamp_overrides_left_study(monkeypatch):
    monkeypatch.setitem(constants.sensor_list, 'sensor1', 'Sensor 1 Code')
    subject_obj = {
        "subject_name": "subj1",
        "app": "app",
        "sensor1 last_time_received": "none",
        "status_code": 1,
        "date_registered": "2025-06-08 17:54:12",
        "date_left_study": "2025-06-09 17:54:12",
        "time_in_study": "1 days",
    }

    subj = subject.Subject(subject_obj, {"studyId": "study1"})
    result = subj.get_sensor_activity_code(None, {'duration': '4'})

    assert result['sensor1']['status_code'] == 4
    assert result['sensor1']['status_desc'] == constants.no_sensor_not_received


def test_get_sensor_activity_code_blank_timestamp_overrides_left_study(monkeypatch):
    monkeypatch.setitem(constants.sensor_list, 'sensor1', 'Sensor 1 Code')
    subject_obj = {
        "subject_name": "subj1",
        "app": "app",
        "sensor1 last_time_received": "",
        "status_code": 1,
        "date_registered": "2025-06-08 17:54:12",
        "date_left_study": "2025-06-09 17:54:12",
        "time_in_study": "1 days",
    }

    subj = subject.Subject(subject_obj, {"studyId": "study1"})
    result = subj.get_sensor_activity_code(None, {'duration': '4'})

    assert result['sensor1']['status_code'] == 4
    assert result['sensor1']['status_desc'] == constants.no_sensor_not_received


def test_get_sensor_activity_code_filters_to_dashboard_sensor_list(monkeypatch):
    monkeypatch.setitem(constants.sensor_list, 'sensor1', 'Sensor 1 Code')
    monkeypatch.setitem(constants.sensor_list, 'sensor2', 'Sensor 2 Code')
    subject_obj = {
        "subject_name": "subj1",
        "app": "app",
        "sensor1 last_time_received": "2025-06-10 17:54:12",
        "sensor2 last_time_received": "2025-06-10 17:54:12",
        "status_code": 0,
        "date_registered": "2025-06-08 17:54:12",
        "date_left_study": "none",
        "time_in_study": "1 days",
    }

    subj = subject.Subject(subject_obj, {"studyId": "study1"})
    result = subj.get_sensor_activity_code(None, {
        'duration': '4',
        'dashboard_sensor_list': ['sensor1'],
    })

    assert 'sensor1' in result
    assert 'sensor2' not in result


def test_get_sensor_activity_code_empty_dashboard_sensor_list_returns_no_sensors(monkeypatch):
    monkeypatch.setitem(constants.sensor_list, 'sensor1', 'Sensor 1 Code')
    subject_obj = {
        "subject_name": "subj1",
        "app": "app",
        "sensor1 last_time_received": "2025-06-10 17:54:12",
        "status_code": 0,
        "date_registered": "2025-06-08 17:54:12",
        "date_left_study": "none",
        "time_in_study": "1 days",
    }

    subj = subject.Subject(subject_obj, {"studyId": "study1"})
    result = subj.get_sensor_activity_code(None, {
        'duration': '4',
        'dashboard_sensor_list': [],
    })

    assert result == {}


def test_get_sensor_activity_code_keeps_ema_when_dashboard_sensor_list_is_empty():
    subject_obj = {
        "subject_name": "subj1",
        "app": "ema",
        "status_code": 0,
        "date_registered": "2025-06-08 17:54:12",
        "date_left_study": "none",
        "time_in_study": "1 days",
        "last_time_received_ema": "2025-06-10 17:54:12",
    }

    subj = subject.Subject(subject_obj, {"studyId": "study1"})
    result = subj.get_sensor_activity_code(None, {
        'duration': '4',
        'dashboard_sensor_list': [],
    })

    assert 'ema' in result


def test_check_format_of_timestamp_datetime_and_unix():
    obj = {
        'subject_name': 'subj1',
        'app': 'app1',
        'status_code': 0,
        'time_in_study': '1 days',
        'date_registered': '2023-01-01 00:00:00',
        'date_left_study': 'none',
    }
    subj = subject.Subject(obj, None)

    # Test ISO datetime string returns datetime object
    dt_string = '2023-01-01 00:00:00'
    dt_obj = subj.check_format_of_timestamp(dt_string)
    assert dt_obj.year == 2023

    # Test unix timestamp returns datetime object
    unix_ts = '1672531200'  # corresponds to 2023-01-01 00:00:00 UTC
    dt_obj_unix = subj.check_format_of_timestamp(unix_ts)
    assert dt_obj_unix.year == 2023

def test_check_multi_registration_true_false():
    # For check_multi_registration to work, date_left_study must be something that supports len() and == ''
    # But in your Subject class, date_left_study is expected to be a string normally, so the check
    # with time_left_col == '' won't work if date_left_study is string.

    # To simulate multiple registrations, patch the method or test with a mock having attribute with len() > 1
    # Alternatively, you can modify check_multi_registration to handle strings properly.

    obj = {
        'subject_name': 'subj1',
        'app': 'app1',
        'status_code': 0,
        'time_in_study': '1 days',
        'date_registered': '2023-01-01 00:00:00',
        'date_left_study': '',  # simulate no date left
    }
    subj = subject.Subject(obj, None)

    # Patch the attribute date_left_study to simulate multiple active qr codes (a list with multiple empty strings)
    subj.date_left_study = ['', '']  # simulate multiple empty values

    assert subj.check_multi_registration() is True

    # Single empty string (simulate single active registration)
    subj.date_left_study = ['']
    assert subj.check_multi_registration() is False

    # Non-empty date_left_study (simulate none active)
    subj.date_left_study = ['2023-01-01']
    assert subj.check_multi_registration() is False

@patch('builtins.open', new_callable=mock_open, read_data='{"key": "value"}')
def test_get_subject_details_success(mock_file):
    result = subject.get_subject_details('study1', 'subj1')
    assert result == {"key": "value"}

@patch('builtins.open', side_effect=FileNotFoundError)
def test_get_subject_details_file_not_found(mock_file):
    result = subject.get_subject_details('study1', 'subj1')
    assert result == {}

@patch('builtins.open', side_effect=json.JSONDecodeError('msg', 'doc', 0))
def test_get_subject_details_json_error(mock_file):
    result = subject.get_subject_details('study1', 'subj1')
    assert result == {}

@patch('os.chown')
@patch('os.path.isfile')
@patch('jdash.services.subject.create_qr_codes')
@patch('jdash.services.subject.write_to_pdf')
def test_create_subjects_for_study_creates_new_files(mock_write_pdf, mock_create_qr, mock_isfile, mock_chown, tmp_path):
    # Setup paths in config to tmp_path
    subject.config.dash_folder = str(tmp_path)
    subject.config.app_study_folder = ""
    subject.config.qr_folder = "qr"
    subject.config.sheets_folder = "sheets"

    study_name = "TestStudy"
    number_to_create = 2

    # Simulate that PDFs do not exist initially
    mock_isfile.return_value = False

    # Create necessary folders
    os.makedirs(tmp_path / study_name / subject.config.sheets_folder, exist_ok=True)
    os.makedirs(tmp_path / study_name / subject.config.qr_folder, exist_ok=True)

    start_num = subject.create_subjects_for_study(study_name, number_to_create)

    assert start_num == number_to_create + 1
    assert mock_create_qr.call_count == number_to_create
    assert mock_write_pdf.call_count == number_to_create
    mock_chown.assert_called()  # Ensure chown was called but no error

@patch('os.path.exists')
@patch('os.listdir')
def test_count_number_of_subject_pdf_counts_files(mock_listdir, mock_exists):
    study_name = "TestStudy"
    base_path = "/tmp/test"
    subject.config.dash_folder = base_path
    subject.config.app_study_folder = ""

    # Directory exists and has 3 files
    mock_exists.return_value = True
    mock_listdir.return_value = ['file1.pdf', 'file2.pdf', 'file3.pdf']

    count = subject.count_number_of_subject_pdf(study_name)
    assert count == 3

    # Directory does not exist
    mock_exists.return_value = False
    count = subject.count_number_of_subject_pdf(study_name)
    assert count == 0

@patch('builtins.open', new_callable=mock_open, read_data='{"pushNotification_token": "token"}')
@patch('json.load')
@patch('jdash.services.subject.constants')
@patch('os.setuid')
@patch('builtins.open', new_callable=mock_open)
@patch('json.dump')
def test_remove_subjects_for_study_updates_json(mock_json_dump, mock_open_file, mock_setuid, mock_constants, mock_json_load, mock_open_read):
    study_name = "TestStudy"
    subject_to_remove = "subj1:app"

    mock_constants.sep = ':'
    mock_constants.suffix_per_modality_dict = {'app': '_app'}
    mock_constants.remove_status_code = 3

    mock_json_load.return_value = {}
    mock_open_read.return_value.__enter__.return_value = mock_open(read_data='{}').return_value

    subject.remove_subjects_for_study(study_name, subject_to_remove)

    mock_setuid.assert_called_once_with(33)
    mock_json_dump.assert_called_once()

@patch('qrcode.QRCode')
def test_create_qr_codes_calls_save(mock_qr_code_class, tmp_path):
    subject.config.dash_folder = str(tmp_path)
    subject.config.app_study_folder = ""
    subject.config.qr_folder = "qr"
    study_id = "TestStudy"
    subject_name = "subj1"

    mock_qr = MagicMock()
    mock_img = MagicMock()
    mock_qr.make_image.return_value = mock_img
    mock_qr_code_class.return_value = mock_qr

    os.makedirs(tmp_path / study_id / subject.config.qr_folder, exist_ok=True)

    subject.create_qr_codes(study_id, subject_name)

    assert mock_qr_code_class.called
    assert mock_qr.make_image.called
    mock_img.save.assert_called()

@patch('os.chmod')
@patch('pdfkit.from_string')
def test_write_to_pdf_generates_pdf_and_sets_permissions(mock_pdfkit, mock_chmod, tmp_path):
    subject.config.dash_folder = str(tmp_path)
    subject.config.app_study_folder = ""
    subject.config.qr_folder = "qr"
    subject.config.sheets_folder = "sheets"

    study_id = "TestStudy"
    subject_name = "subj1"

    # Create required directories
    os.makedirs(tmp_path / study_id / subject.config.qr_folder, exist_ok=True)
    os.makedirs(tmp_path / study_id / subject.config.sheets_folder, exist_ok=True)

    subject.write_to_pdf(study_id, subject_name)

    pdf_path = os.path.join(tmp_path, study_id, subject.config.sheets_folder, subject_name + '.pdf')
    mock_pdfkit.assert_called_once()
    mock_chmod.assert_called_once_with(pdf_path, 0o0775)
