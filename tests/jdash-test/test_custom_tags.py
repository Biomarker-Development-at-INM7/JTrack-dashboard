import pytest
from unittest.mock import MagicMock, patch
from django.contrib.auth.models import Group, User
import jdash.templatetags.custom_tags as custom_tags
from jdash.apps import constants


@pytest.mark.parametrize("value,arg,expected", [
    ({"acc n_batches": 5}, "acc", 5),
    ({}, "gps", 0),  # missing key returns 0
])
def test_get_n_batches(value, arg, expected):
    assert custom_tags.get_n_batches(value, arg) == expected


@pytest.mark.parametrize("value,arg,expected", [
    ({"acc last_time_received": "2025-06-10 12:00:00"}, "acc", "2025-06-10 12:00:00"),
    ({}, "gps", "none"),  # missing key returns 'none'
])
def test_get_last_time_received(value, arg, expected):
    assert custom_tags.get_last_time_received(value, arg) == expected


def test_get_activity_status_tag(monkeypatch):
    # Patch Subject.get_activity_status_code to return each possible code
    subject_data = {
        "subject_name": "test_subject",
        "app": "app1",  # Add this key
        "status_code": 0,
        "time_in_study": "1 days",
        "date_registered": "2025-06-08 17:54:12",
        "date_left_study": "none",
        # add any other minimal keys required for Subject.__init__ if needed
    }
    study_obj = {}

    for code, expected_class in [(0, "text-danger"), (1, "text-primary"), (2, "text-warning"),
                                 (3, "text-success"), (4, "text-info")]:
        monkeypatch.setattr(custom_tags.Subject, "get_activity_status_code", lambda self, study: code)
        tag = custom_tags.get_activity_status_tag(subject_data, study_obj)
        assert expected_class in tag
        assert subject_data["subject_name"] in tag


@pytest.mark.parametrize("status_code,expected_label,expected_class", [
    (0, "Instudy", "text-warning"),
    (1, "Left study", "text-primary"),
    (2, "Completed", "text-success"),
    (3, "Removed", "text-danger"),
    (99, "Unknown", "text-secondary"),  # unknown code
])
def test_get_status_tag(status_code, expected_label, expected_class):
    tag = custom_tags.get_status_tag(status_code)
    assert expected_label in tag
    assert expected_class in tag


def test_get_sensor_tag(monkeypatch):
    subject_data = {
        "subject_name": "test_subject",
        "app": "app1",  # Add this key
        "status_code": 0,
        "time_in_study": "1 days",
        "date_registered": "2025-06-08 17:54:12",
        "date_left_study": "none",
        # add any other minimal keys required for Subject.__init__ if needed
    }
    study_obj = {}

    sensor_dict = {
        "acc": {"status_code": 1, "status_desc": "desc1", "sensor_code": "ACC"},
        "gps": {"status_code": 2, "status_desc": "desc2", "sensor_code": "GPS"},
        "temp": {"status_code": 3, "status_desc": "desc3", "sensor_code": "TEMP"},
        "other": {"status_code": 99, "status_desc": "desc4", "sensor_code": "OTH"},
    }

    # Patch get_sensor_activity_code to return sensor_dict
    monkeypatch.setattr(custom_tags.Subject, "get_sensor_activity_code", lambda self, val, st: sensor_dict)

    result = custom_tags.get_sensor_tag(subject_data, study_obj)
    assert 'btn-primary' in result
    assert 'btn-warning' in result
    assert 'btn-success' in result
    assert 'btn-danger' in result  # default for unknown status_code


@pytest.mark.parametrize("sensor_list,current_sensor_list,expected_count", [
    (["acc", "gps"], ["gps"], 2),
    ("acc", ["acc"], 1),
    ([], [], 0),
])
def test_get_sensor_codes(sensor_list, current_sensor_list, expected_count):
    # Ensure constants.sensor_list has dummy mappings
    constants.sensor_list.update({"acc": "ACC_CODE", "gps": "GPS_CODE"})
    result = custom_tags.get_sensor_codes(sensor_list, current_sensor_list)
    # Count number of <button> tags returned
    assert result.count("<button") == expected_count


def test_get_size():
    assert custom_tags.get_size([1, 2, 3]) == 3
    assert custom_tags.get_size("") == 0


def test_get_item():
    lst = [{"db_id": 5}, {"db_id": 6}]
    assert custom_tags.get_item(lst, 1) == 6
    assert custom_tags.get_item(lst, 2) is None
    assert custom_tags.get_item([], 0) is None


def test_get_subText():
    lst = [{"subText": "some text"}]
    assert custom_tags.get_subText(lst) == "some text"
    assert custom_tags.get_subText([{}]) is None


def test_get_id():
    lst = [{"db_id": 1}, {"db_id": 2}, {"no_id": 3}]
    assert custom_tags.get_id(lst) == "1;2"  # keep trailing semicolon


def test_get_sortId():
    lst = [{"id": 42}]
    assert custom_tags.get_sortId(lst) == 42
    assert custom_tags.get_sortId([{}]) is None


@pytest.mark.parametrize("func, key", [
    (custom_tags.get_value, "value"),
    (custom_tags.get_defaultValue, "defaultValue"),
    (custom_tags.get_stepSize, "stepSize"),
])
def test_get_value_default_step(func, key):
    lst = [{key: 123}]
    assert func(lst) == 123
    assert func([{}]) is None


def test_get_minVal_maxVal():
    lst1 = [{"minVal": 10, "maxVal": 100}]
    lst2 = [{"minValue": 20, "maxValue": 200}]
    lst3 = [{}]

    assert custom_tags.get_minVal(lst1) == 10
    assert custom_tags.get_minVal(lst2) == 20
    assert custom_tags.get_minVal(lst3) is None

    assert custom_tags.get_maxVal(lst1) == 100
    assert custom_tags.get_maxVal(lst2) == 200
    assert custom_tags.get_maxVal(lst3) is None


def test_get_minText_maxText():
    lst = [{"minText": "low", "maxText": "high"}]
    assert custom_tags.get_minText(lst) == "low"
    assert custom_tags.get_maxText(lst) == "high"
    assert custom_tags.get_minText([{}]) is None
    assert custom_tags.get_maxText([{}]) is None


@pytest.mark.parametrize("value, expected", [
    (0, 'Instruction for questions'),
    (1, 'Single Choice'),
    (2, 'Multiple Choice'),
    (3, 'Sliding'),
    (4, 'Free Text'),
    (5, 'Free Number'),
    (6, 'Time'),
    (7, 'Date'),
    (8, 'Time and Date'),
    (9, 'Duration'),
    (10, 'Unknown Category'),  # unknown
])
def test_get_question_category(value, expected):
    assert custom_tags.get_question_category(value) == expected


def test_has_group(monkeypatch):
    user = MagicMock()
    group = MagicMock()
    group.name = "testgroup"

    # Simulate group exists
    monkeypatch.setattr(Group.objects, "get", lambda name: group)
    user.groups.all.return_value = [group]
    assert custom_tags.has_group(user, "testgroup") is True

    # User not in group
    user.groups.all.return_value = []
    assert custom_tags.has_group(user, "testgroup") is False

    # Group does not exist
    def raise_does_not_exist(name):
        raise Group.DoesNotExist
    monkeypatch.setattr(Group.objects, "get", raise_does_not_exist)
    assert custom_tags.has_group(user, "nonexistentgroup") is False