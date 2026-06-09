import os
import json
import pytest
import shutil
import numpy as np
import pandas as pd
import tempfile
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from jdash.services import study
from jdash.utils import utils
from jdash.config import constants
from jdash.exceptions import studyexceptions
from jdash.models import QualityControlComment, QualityControlTests, Study as StudyModel

@pytest.fixture
def mock_config(tmp_path, monkeypatch):
    monkeypatch.setattr(study.config, "studies_folder", tmp_path / "studies")
    monkeypatch.setattr(study.config, "analytics_storage_folder", tmp_path / "analytics")
    monkeypatch.setattr(study.config, "dash_folder", tmp_path / "dash")
    monkeypatch.setattr(study.config, "app_study_folder", "app_studies")
    monkeypatch.setattr(study.config, "qr_folder", "qr")
    monkeypatch.setattr(study.config, "sheets_folder", "sheets")
    monkeypatch.setattr(study.config, "analytics_outputs_folder", "outputs")
    monkeypatch.setattr(study.config, "csv_prefix", "study_")
    monkeypatch.setattr(study.config, "storage_folder", tmp_path / "storage")
    monkeypatch.setattr(study.config, "archive_folder", tmp_path / "archive")
    monkeypatch.setattr(study.config, "zip_file", "unused.zip")
    return tmp_path

@pytest.mark.django_db
@patch("jdash.services.study.create_subjects_for_study")
@patch("jdash.services.study.create_new_study_in_db")
@patch("jdash.services.study.generate_survey_json_for_download")
@patch("jdash.services.study.save_study_json")
@patch("jdash.services.study.change_permissions")
def test_create_study_success(mock_chmod, mock_save_json, mock_generate_survey_json,
                               mock_create_study, mock_create_subjects):
    # Use a writable path you fully control
    base_path = os.path.abspath("tests/pytest-tmp/safe-study-path")
    os.makedirs(base_path, exist_ok=True)

    # Patch jdash config values to point into this safe location
    study.config.studies_folder = base_path
    study.config.dash_folder = base_path
    study.config.analytics_storage_folder = base_path
    study.config.app_study_folder = ""
    study.config.qr_folder = "qr"
    study.config.sheets_folder = "sheets"
    study.config.analytics_outputs_folder = "outputs"

    # Simulate logged-in user
    dummy_user = MagicMock()
    dummy_user.username = "testuser"

    # Valid study dictionary
    study_dict = {
        "name": "NewStudy2",
        "number-of-subjects": 3,
        "duration": "2 weeks",
        "description": "Sample",
        "sensor_list": ["acc n_batches", "gps n_batches"]
    }

    try:
        result, error = study.create_study(study_dict, dummy_user)

        assert result is True
        assert error == ""
    finally:
        # Clean up the created study directory
        study_path = os.path.join(base_path, study_dict["name"])
        if os.path.exists(study_path):
            shutil.rmtree(study_path)

@pytest.mark.django_db
def test_create_study_already_exists(mock_config):
    dummy_user = MagicMock()
    study_name = "TestStudy"
    study_path = os.path.join(mock_config / "studies", study_name)
    os.makedirs(study_path)

    study_dict = {
        constants.field_name_name: study_name,
    }

    response, error = study.create_study(study_dict, dummy_user)
    assert response is False
    assert error == "Study folder already exists"

@pytest.mark.django_db
def test_display_study_file_not_found():
    result = study.display_study("nonexistent_study")
    assert "error_message" in result
    assert result["error_message"] == "File not Found"

@patch("jdash.services.study.get_json_data", return_value={"number_of_subjects": 5})
@patch("jdash.services.study.retrieve_all_studies_for_user", return_value=json.dumps([{
    constants.key_name_study_title: "MockStudy",
    constants.key_name_created_date: "2020-01-01"
}]))
@patch("jdash.services.study.get_json_data", return_value={})
@patch("jdash.services.study._get_study_group_members", return_value=([], []))
@patch("jdash.services.study.get_latest_received_study_sensor_details", return_value=[])
@patch("jdash.services.study.calculate_stats_of_number_of_subjects", return_value={})
def test_get_all_study_details_valid(
    mock_stats, mock_sensors, mock_group_members, mock_json, mock_retrieve, mock_get_json):

    user = MagicMock()
    total_studies, stats, error = study.get_all_study_details(user)
    assert isinstance(total_studies, list)
    assert isinstance(stats, dict)
    assert error == ""
    assert stats == {"MockStudy": {}}


@patch("jdash.services.study.get_json_data", return_value={})
@patch("jdash.services.study._get_study_group_members", return_value=([], []))
@patch("jdash.services.study.get_latest_received_study_sensor_details", return_value=[])
@patch("jdash.services.study.calculate_stats_of_number_of_subjects", return_value={})
@patch(
    "jdash.services.study.retrieve_all_studies_for_user",
    return_value=json.dumps([
        {
            constants.key_name_study_title: "OlderStudy",
            constants.key_name_created_date: "2020-01-01",
        },
        {
            constants.key_name_study_title: "NewerStudy",
            constants.key_name_created_date: "2021-02-01",
        },
    ]),
)
def test_get_all_study_details_sorts_newest_first(
    mock_retrieve, mock_stats, mock_sensors, mock_group_members, mock_json
):
    user = MagicMock()

    total_studies, stats, error = study.get_all_study_details(user)

    assert error == ""
    assert [item[constants.key_name_study_title] for item in total_studies] == [
        "NewerStudy",
        "OlderStudy",
    ]

@patch("jdash.services.study.open_study_json")
@patch("jdash.services.study.save_study_json")
def test_update_study_details(mock_save, mock_open):
    mock_open.return_value = {
        "duration": 5,
        "description": "desc",
        "is_test": False,
        "images": False
    }
    result = study.update_study_details("TestStudy", {
        "duration": 10,
        "description": "new desc",
        "is_test": True,
        "images": True,
        "sensor_list": ["acc"],
        "frequency": 5,
        "sensor_list_limited": [],
        "task_list": []
    })
    assert isinstance(result, dict)


def test_study_survey_property_keeps_empty_survey_key():
    study_service = study.Study("TestStudy", None)
    study_service.meta = {"name": "TestStudy"}

    result = study_service.survey

    assert result is None
    assert study_service.meta["survey"] == {}


def test_get_dashboard_sensor_names_prefixes_wearable_sensor_names():
    meta_data = {
        "sensor_list": ["activity"],
        "sensor_list_limited": [],
        "wearables": [{
            "sensorname": "Garmin",
            "sensors": [
                {"wearable_sensor": "HEART_RATE"},
                {"wearable_sensor": "STEPS"},
            ],
        }],
    }

    result = study.Study._get_dashboard_sensor_names(meta_data)

    assert result == ["activity", "garmin_HEART_RATE", "garmin_STEPS"]


def test_get_dashboard_sensor_names_normalizes_camel_case_wearable_sensor_names():
    meta_data = {
        "sensor_list": [],
        "sensor_list_limited": [],
        "wearables": [{
            "sensorname": "Garmin",
            "sensors": [
                {"wearable_sensor": "HeartRate"},
                {"wearable_sensor": "ZeroCrossing"},
            ],
        }],
    }

    result = study.Study._get_dashboard_sensor_names(meta_data)

    assert result == ["garmin_HEART_RATE", "garmin_ZERO_CROSSING"]


@patch.object(study.Study, "_trigger_update_json_script")
@patch.object(study.Study, "_refresh_test_cases")
@patch("jdash.services.study.update_study_db_details")
@patch.object(study.Study, "update_details")
def test_update_refreshes_quality_control_tests(
    mock_update_details,
    mock_update_study_db_details,
    mock_refresh_test_cases,
    mock_trigger_update_json_script,
):
    mock_update_details.return_value = {
        "sensor_list": ["accelerometer"],
        "survey": {"questions": [{"title": "Mood"}]},
        "wearables": [],
        "version": 2,
    }

    result = study.Study("TestStudy", None).update({"name": "TestStudy"})

    assert result == mock_update_details.return_value
    mock_update_study_db_details.assert_called_once_with({"name": "TestStudy"})
    mock_refresh_test_cases.assert_called_once()
    mock_trigger_update_json_script.assert_called_once()


@patch("jdash.services.study.create_backup_json_file")
@patch("jdash.services.study.open_study_json")
@patch("jdash.services.study.save_study_json")
def test_update_details_restores_missing_survey_key(
    mock_save_study_json,
    mock_open_study_json,
    mock_create_backup_json_file,
):
    mock_open_study_json.return_value = {
        "name": "TestStudy",
        "duration": 5,
        "description": "desc",
        "is_test": False,
        "images": False,
        "version": 1,
    }

    study_service = study.Study("TestStudy", None)
    result = study_service.update_details({
        "duration": 10,
        "description": "new desc",
        "is_test": True,
        "images": False,
    })

    assert result["survey"] == {}
    mock_save_study_json.assert_called_once()
    saved_payload = mock_save_study_json.call_args.args[1]
    assert saved_payload["survey"] == {}


@pytest.mark.django_db
def test_refresh_test_cases_preserves_comments_when_sensor_removed():
    user = get_user_model().objects.create(username="sensor-owner")
    study_row = StudyModel.objects.create(
        title="TestStudy",
        description="desc",
        numberOfSubjects=1,
        enrolled_subjects="0",
        duration="7",
        is_test=False,
        passive_monitoring=True,
        frequency=1,
        labeling=0,
        sensor_list=["accelerometer", "gps"],
        ecological_momentary_assessment=False,
        owner=user,
    )
    acc_case = QualityControlTests.objects.create(
        testcase_id="PSEN-AND-0",
        test_type="Sensor",
        description="Verify passive sensor data is logged correctly for accelerometer on Android",
        steps="1. Simulate accelerometer for a subject on Android. 2. Check if accelerometer json is generated.",
        expected_outcome="accelerometer data from Android should appear in json accurately with timestamps.",
        admin_username="",
        owner_username="",
        study=study_row,
    )
    gps_case = QualityControlTests.objects.create(
        testcase_id="PSEN-AND-1",
        test_type="Sensor",
        description="Verify passive sensor data is logged correctly for gps on Android",
        steps="1. Simulate gps for a subject on Android. 2. Check if gps json is generated.",
        expected_outcome="gps data from Android should appear in json accurately with timestamps.",
        admin_username="",
        owner_username="",
        study=study_row,
    )
    QualityControlComment.objects.create(test_case=gps_case, text="keep me", username="owner")

    study_service = study.Study("TestStudy", None)
    study_service.meta = {
        "name": "TestStudy",
        "survey": {},
        "sensor_list": ["gps"],
        "sensor_list_limited": [],
        "wearables": [],
    }

    study_service._refresh_test_cases()

    assert not QualityControlTests.objects.filter(id=acc_case.id).exists()
    updated_gps_case = QualityControlTests.objects.get(id=gps_case.id)
    assert updated_gps_case.testcase_id == "PSEN-AND-0"
    assert updated_gps_case.description.endswith("gps on Android")
    assert updated_gps_case.comments.count() == 1


@pytest.mark.django_db
def test_refresh_test_cases_updates_ema_case_without_losing_comments():
    user = get_user_model().objects.create(username="ema-owner")
    study_row = StudyModel.objects.create(
        title="TestStudyEma",
        description="desc",
        numberOfSubjects=1,
        enrolled_subjects="0",
        duration="7",
        is_test=False,
        passive_monitoring=False,
        frequency=1,
        labeling=0,
        sensor_list=[],
        ecological_momentary_assessment=True,
        owner=user,
    )
    ema_case = QualityControlTests.objects.create(
        testcase_id="EMA-42",
        test_type="EMA",
        description="Old title",
        steps="",
        expected_outcome="Check the data stored variable",
        admin_username="",
        owner_username="",
        study=study_row,
    )
    QualityControlComment.objects.create(test_case=ema_case, text="keep me too", username="owner")

    study_service = study.Study("TestStudyEma", None)
    study_service.meta = {
        "name": "TestStudyEma",
        "survey": {"questions": [{"db_id": 42, "id": 1, "title": "New title"}]},
        "sensor_list": [],
        "sensor_list_limited": [],
        "wearables": [],
    }

    study_service._refresh_test_cases()

    refreshed_case = QualityControlTests.objects.get(id=ema_case.id)
    assert refreshed_case.testcase_id == "EMA-42"
    assert refreshed_case.description == "New title"
    assert refreshed_case.comments.count() == 1


@pytest.mark.django_db
def test_refresh_test_cases_migrates_legacy_ema_case_to_db_id_without_losing_comments():
    user = get_user_model().objects.create(username="ema-migrate-owner")
    study_row = StudyModel.objects.create(
        title="TestStudyLegacyEma",
        description="desc",
        numberOfSubjects=1,
        enrolled_subjects="0",
        duration="7",
        is_test=False,
        passive_monitoring=False,
        frequency=1,
        labeling=0,
        sensor_list=[],
        ecological_momentary_assessment=True,
        owner=user,
    )
    legacy_ema_case = QualityControlTests.objects.create(
        testcase_id="EMA-0",
        test_type="EMA",
        description="Mood question",
        steps="",
        expected_outcome="Check the data stored variable",
        admin_username="",
        owner_username="",
        study=study_row,
    )
    QualityControlComment.objects.create(test_case=legacy_ema_case, text="keep me too", username="owner")

    study_service = study.Study("TestStudyLegacyEma", None)
    study_service.meta = {
        "name": "TestStudyLegacyEma",
        "survey": {"questions": [{"db_id": 77, "id": 1, "title": "Mood question"}]},
        "sensor_list": [],
        "sensor_list_limited": [],
        "wearables": [],
    }

    study_service._refresh_test_cases()

    refreshed_case = QualityControlTests.objects.get(id=legacy_ema_case.id)
    assert refreshed_case.testcase_id == "EMA-77"
    assert refreshed_case.description == "Mood question"
    assert refreshed_case.comments.count() == 1

@patch("jdash.services.study.open_study_json")
@patch("jdash.services.study.save_study_json")
def test_update_survey_details_question(mock_save, mock_open):
    mock_open.return_value = {
        "survey": {
            "questions": [{"id": 1}]
        }
    }
    result = study.update_survey_details("TestStudy", {
        "id": 1,
        "title": "Q1",
        "subText": "",
        "frequency": 1,
        "clockTime": 480,
        "nextDayToAnswer": 0,
        "category": 1,
        "imageURL": "",
        "url": "",
        "questionType": "text",
        "deactivateOnAnswer": False,
        "deactivateOnDate": None
    }, is_question=True)
    assert result is True

@pytest.mark.django_db
@patch("jdash.services.study.get_all_study_details", return_value=([], {}, ""))
@patch("jdash.services.study.close_study_model", return_value=False)
@patch("jdash.services.study.os.rename")
def test_close_study_success(mock_rename, mock_close_model, mock_get_all, tmp_path):
    study_name = "TestStudy"
    dummy_user = MagicMock()
    dummy_user.username = "testuser"

    # Redirect folders to temp path
    study.config.studies_folder = str(tmp_path / "studies")
    study.config.archive_folder = str(tmp_path / "archive")
    study.config.storage_folder = str(tmp_path / "storage")
    study.config.csv_prefix = "csv_"

    # Actually create required directories
    os.makedirs(os.path.join(study.config.studies_folder, study_name), exist_ok=True)
    os.makedirs(study.config.archive_folder, exist_ok=True)
    os.makedirs(study.config.storage_folder, exist_ok=True)

    # Create a dummy CSV file
    csv_path = os.path.join(study.config.storage_folder, f"csv_{study_name}.csv")
    with open(csv_path, "w") as f:
        f.write("subject_name,status_code\n")

    # Run test
    result = study.close_study(study_name, dummy_user)

    # Assertions
    assert result == ([], {}, "")
    assert mock_rename.call_count >= 1


@patch("jdash.services.study.os.system")
@patch("jdash.services.study.os.remove")
@patch("jdash.services.study.os.path.isfile", return_value=True)
@patch("jdash.services.study.os.listdir")
@patch("jdash.services.study.read_study_df")
@patch("jdash.services.study.os.chdir")
def test_zip_unused_sheets(mock_chdir, mock_read_df, mock_listdir, mock_isfile, mock_remove, mock_system, tmp_path):
    study_name = "TestStudy"
    base_dir = tmp_path / "base"
    sheets_dir = base_dir / study_name / "sheets"
    os.makedirs(sheets_dir, exist_ok=True)

    study.config.dash_folder = str(base_dir)
    study.config.app_study_folder = str(base_dir)
    study.config.sheets_folder = "sheets"
    study.config.zip_file = "unused.zip"

    # Mock a DataFrame with a subject
    df = pd.DataFrame({"subject_name": ["user_001"]})
    mock_read_df.return_value = df
    mock_listdir.return_value = ["user_001.pdf", "user_002.pdf"]

    context = study.zip_unused_sheets(study_name)

    assert context["msg"] == "download unused files"
    mock_chdir.assert_called_once_with(str(base_dir))
    mock_system.assert_called_once()


def test_open_study_json(tmp_path):
    study_name = "StudyX"
    folder = tmp_path / study_name
    folder.mkdir()
    json_data = {"name": "StudyX", "number-of-subjects": 2}
    json_path = folder / f"{study_name}.json"
    json_path.write_text(json.dumps(json_data))

    study.config.studies_folder = str(tmp_path)
    result = study.open_study_json(study_name)

    assert result == json_data


def test_update_study_df(tmp_path):
    study_name = "StudyY"
    study.config.storage_folder = str(tmp_path)
    study.config.csv_prefix = "csv_"

    csv_path = tmp_path / f"csv_{study_name}.csv"
    df = pd.DataFrame([
        {"subject_name": "abc_123", "app": "ios", "status_code": 0},
        {"subject_name": "xyz_456", "app": "android", "status_code": 0}
    ])
    df.to_csv(csv_path, index=False)

    study.update_study_df(study_name, "abc_123:ios")
    updated_df = pd.read_csv(csv_path)

    assert updated_df.loc[0, "status_code"] == 3
    assert updated_df.loc[1, "status_code"] == 0


def test_read_study_df(tmp_path):
    study_name = "StudyZ"
    study.config.storage_folder = str(tmp_path)
    study.config.csv_prefix = "csv_"

    df = pd.DataFrame([{"subject_name": "test", "app": "ios", "status_code": 0}])
    csv_path = tmp_path / f"csv_{study_name}.csv"
    df.to_csv(csv_path, index=False)

    result_df = study.read_study_df(study_name)
    assert not result_df.empty
    assert result_df.iloc[0]["subject_name"] == "test"


def test_get_user_list():
    df = pd.DataFrame({
        "subject_name": ["user1_001", "user1_002", "user2_001"]
    })
    result = study.get_user_list(df)
    assert set(result) == {"user1", "user2"}


def test_get_ids_and_app_list():
    users_per_app = {
        "ios": ["abc", "def"],
        "android": ["xyz"]
    }
    result = study.get_ids_and_app_list(users_per_app)
    assert sorted(result) == ["abc:ios", "def:ios", "xyz:android"]


def test_get_modified_json_form_csv():
    data = [
        {"subject_name": "grpA_01"},
        {"subject_name": "grpA_02"},
        {"subject_name": "grpB_01"}
    ]
    result_json, count = study.get_modified_json_form_csv(data)
    parsed = json.loads(result_json)

    assert "grpA_" in parsed
    assert "grpB_" in parsed
    assert count == 2



@pytest.mark.django_db
@patch("jdash.utils.utils.retrieve_all_categories_for_survey")
@patch("jdash.utils.utils.retrieve_survey_details")
@patch("jdash.services.study.generate_survey_json_for_download")
@patch("os.path.isdir")
@patch("os.makedirs")
@patch("jdash.services.study.change_permissions")
@patch("jdash.services.study.retrieve_survey")
@patch("jdash.services.study.create_survey_in_db")
@patch("jdash.services.study.save_study_json")
@patch("jdash.services.study.create_new_study_in_db")
@patch("jdash.services.study.create_subjects_for_study")
@pytest.mark.parametrize("existing_dir, expected_response, expected_error", [
    (True, False, "Study already exists"),
    (False, True, ""),
])
def test_create_study_basic_flow(
    mock_create_subjects_for_study,
    mock_create_new_study_in_db,
    mock_save_study_json,
    mock_create_survey_in_db,
    mock_retrieve_survey,
    mock_change_permissions,
    mock_makedirs,
    mock_isdir,
    mock_generate_survey_json,
    mock_retrieve_survey_details,
    mock_retrieve_all_categories_for_survey,
    existing_dir,
    expected_response,
    expected_error,
):
    # Arrange mocks
    mock_retrieve_all_categories_for_survey.return_value = []
    mock_retrieve_survey_details.return_value = []
    mock_generate_survey_json.return_value = {"id": 1, "questions": []}
    mock_retrieve_survey.return_value = MagicMock(id=1)
    mock_create_survey_in_db.return_value = MagicMock(id=1)

    study_name = "TestStudy13"
    study_dict = {
        constants.field_name_name: study_name,
        "number-of-subjects": 5,
        constants.field_name_survey: 1
    }
    user = MagicMock()

    # Setup isdir mock: simulate existing or not existing study folder
    def isdir_side_effect(path):
        if study_name in path:
            return existing_dir
        return False
    mock_isdir.side_effect = isdir_side_effect

    # Cleanup any leftover directory before test
    base_test_path = os.path.join("tests", "pytest-tmp")
    study_path = os.path.join(base_test_path, study_name)
    if os.path.exists(study_path):
        shutil.rmtree(study_path)

    # Patch config paths to our test folder
    study.config.studies_folder = base_test_path
    study.config.analytics_storage_folder = base_test_path
    study.config.dash_folder = base_test_path
    study.config.app_study_folder = ""
    study.config.qr_folder = "qr"
    study.config.sheets_folder = "sheets"
    study.config.analytics_outputs_folder = "outputs"

    # Act
    response, errors = study.create_study(study_dict, user)

    # Assert
    assert response == expected_response
    if existing_dir:
        assert "already exists" in errors.lower()
    else:
        assert errors == ""

@pytest.mark.parametrize("exception_to_raise, expected_response", [
    (ValueError("bad value"), False),
    (Exception("some error"), False),
])
@patch("jdash.services.study.os.makedirs")
@patch("jdash.services.study.os.path.isdir", return_value=False)
@patch("jdash.services.study.change_permissions")
@patch("jdash.services.study.save_study_json")
@patch("jdash.services.study.create_new_study_in_db")
@patch("jdash.services.study.create_subjects_for_study")
def test_create_study_exceptions(
    mock_create_subjects,
    mock_create_new_study,
    mock_save_json,
    mock_change_permissions,
    mock_isdir,
    mock_makedirs,
    exception_to_raise,
    expected_response,
):
    study_dict = {
        "name": "TestStudy",
        "number-of-subjects": 5,
        "survey": 1
    }
    user = MagicMock()

    # Cause exception when making directories
    mock_makedirs.side_effect = exception_to_raise

    response, errors = study.create_study(study_dict, user)
    assert response == expected_response
    assert errors != ""

    # Ensure no DB or subject creation happened
    mock_create_new_study.assert_not_called()
    mock_create_subjects.assert_not_called()


@pytest.mark.parametrize("sensor_list", [
    ["acc", "gps"],  # example sensor list
    [],             # empty sensor list
])
@patch("jdash.services.study.get_json_data")
@patch("jdash.services.study.read_study_df")
@patch("jdash.services.study.get_modified_json_form_csv")
@patch("jdash.services.study.get_subject_details_of_study")
def test_display_study_basic(mock_get_subject_details, mock_get_modified_json, mock_read_df, mock_get_json_data, sensor_list):
    study_name = "TestStudy"

    # Prepare mocks
    json_meta = {
        "sensor_list": sensor_list,
        "number_of_enrolled_subjects": 0
    }
    mock_get_json_data.return_value = json_meta

    # Mock dataframe with two dummy records
    df = pd.DataFrame([{"subject_name": "subj1"}, {"subject_name": "subj2"}])
    mock_read_df.return_value = df

    # The JSON stringified modified data that would be returned by get_modified_json_form_csv
    dummy_data = {
        "subj1": [{
            "subject_name": "subj1",
            "acc n_batches": 0,
            "acc last_time_received": "none",
            "gps n_batches": 0,
            "gps last_time_received": "none"
        }],
        "subj2": [{
            "subject_name": "subj2",
            "acc n_batches": 0,
            "acc last_time_received": "none",
            "gps n_batches": 0,
            "gps last_time_received": "none"
        }],
    }
    json_str = json.dumps(dummy_data)
    mock_get_modified_json.return_value = (json_str, len(dummy_data))

    # Mock the subject details dictionary
    mock_get_subject_details.return_value = {"ids_to_be_removed": ["subj1:app:False", "subj2:app:False"]}

    # Call the function under test
    result = study.display_study(study_name)

    # Basic assertions
    assert "d" in result
    assert "meta_data" in result
    assert "subject_details" in result

    # Check that number_of_enrolled_subjects was updated
    assert result["meta_data"]["number_of_enrolled_subjects"] == 2

    # For each sensor in the sensor list, check that the keys exist in the data
    for sensor in sensor_list:
        for subj_data in result["d"].values():
            for obj in subj_data:
                assert sensor + " n_batches" in obj
                assert sensor + " last_time_received" in obj

    # Check subject_details returned as expected
    assert "ids_to_be_removed" in result["subject_details"]


@pytest.mark.parametrize("mock_data, expected_sensors", [
    (
        {
            'd': {
                'subj1': [{'acc last_time_received': '2025-06-12T12:00:00', 'gps last_time_received': 'none'}],
                'subj2': [{'acc last_time_received': 'none', 'gps last_time_received': '2025-06-12T08:00:00'}],
            }
        },
        ['acc', 'gps']
    ),
    (
        {
            'd': {
                'subj1': [{'acc last_time_received': '2025-06-11T12:00:00', 'gps last_time_received': None}],
            }
        },
        []
    ),
])
@patch("jdash.services.study.display_study")
def test_get_latest_received_study_sensor_details(mock_display, mock_data, expected_sensors):
    mock_display.return_value = mock_data

    # Patch current_date to match the test date in mock_data
    import jdash.services.study as study_module
    study_module.current_date = "2025-06-12"

    result = study_module.get_latest_received_study_sensor_details("TestStudy")
    assert sorted(result) == sorted(expected_sensors)


@pytest.mark.parametrize("df_data, number_of_subjects, expected_stats", [
    (
        # DataFrame with different status codes
        pd.DataFrame([
            {"subject_name": "subj1", "status_code": 0},
            {"subject_name": "subj2", "status_code": 1},
            {"subject_name": "subj3", "status_code": 2},
            {"subject_name": "subj4", "status_code": 3},
            {"subject_name": "subj5", "status_code": 0},
        ]),
        5,
        {
            "leftstudy": 1,
            "leftstudy_percentage": 20.0,
            "instudy": 2,
            "instudy_percentage": 40.0,
            "completed": 1,
            "completed_percentage": 20.0,
            "removed": 1,
            "removed_percentage": 20.0,
        }
    ),
    (
        # Empty DataFrame should return empty stats
        pd.DataFrame([]),
        5,
        {}
    ),
    (
        # Percentages are normalized by enrolled/status-counted subjects, not planned capacity.
        pd.DataFrame([
            {"subject_name": "subj1", "status_code": 0},
            {"subject_name": "subj2", "status_code": 0},
            {"subject_name": "subj3", "status_code": 0},
            {"subject_name": "subj4", "status_code": 0},
            {"subject_name": "subj5", "status_code": 0},
            {"subject_name": "subj6", "status_code": 0},
            {"subject_name": "subj7", "status_code": 0},
            {"subject_name": "subj8", "status_code": 1},
        ]),
        200,
        {
            "leftstudy": 1,
            "leftstudy_percentage": 12.5,
            "instudy": 7,
            "instudy_percentage": 87.5,
            "completed": 0,
            "completed_percentage": 0.0,
            "removed": 0,
            "removed_percentage": 0.0,
        }
    ),
])
@patch("jdash.utils.utils.read_study_df")
def test_calculate_stats_of_number_of_subjects(mock_read_df, df_data, number_of_subjects, expected_stats):
    mock_read_df.return_value = df_data

    import jdash.services.study as study_module

    result = study_module.calculate_stats_of_number_of_subjects("TestStudy", number_of_subjects)

    assert result == expected_stats
