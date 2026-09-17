import os
import sys
import zipfile
from unittest.mock import MagicMock

import django
import pytest
from django.http import FileResponse, HttpResponse


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin.settings")
django.setup()

from jdash.config import constants
from jdash.services import controller
from jdash.services import study_workflows, survey_workflows


def test_controller_exposes_study_download_functions():
    assert controller.dowload_unused_qr_code_files is study_workflows.dowload_unused_qr_code_files
    assert controller.download_subject_qr_file is study_workflows.download_subject_qr_file
    assert controller.download_dataset is study_workflows.download_dataset
    assert controller.initiate_download_study_dataset is study_workflows.initiate_download_study_dataset
    assert controller.check_file_and_send_email is study_workflows.check_file_and_send_email


def test_controller_exposes_study_workflow_functions():
    assert controller.create_new_study is study_workflows.create_new_study
    assert controller.update_study_meta_data is study_workflows.update_study_meta_data
    assert controller.remove_subjects_from_study is study_workflows.remove_subjects_from_study
    assert controller.create_subjects_for_study is study_workflows.create_subjects_for_study
    assert controller.send_push_notification is study_workflows.send_push_notification
    assert controller.create_display_sop_list_of_study is study_workflows.create_display_sop_list_of_study
    assert controller.close_study is study_workflows.close_study
    assert controller.delete_subjects_from_server is study_workflows.delete_subjects_from_server


def test_controller_exposes_survey_workflow_functions():
    assert controller.get_all_survey_details is survey_workflows.get_all_survey_details
    assert controller.create_question_answer_for_survey is survey_workflows.create_question_answer_for_survey
    assert controller.update_question_answer_for_survey is survey_workflows.update_question_answer_for_survey
    assert controller.update_old_survey_details is survey_workflows.update_old_survey_details
    assert controller.create_survey_from_surveyForm is survey_workflows.create_survey_from_surveyForm
    assert controller.update_survey_from_surveyForm is survey_workflows.update_survey_from_surveyForm
    assert controller.upload_survey_json_file is survey_workflows.upload_survey_json_file
    assert controller.upload_survey_file is survey_workflows.upload_survey_file
    assert controller.delete_question_from_survey is survey_workflows.delete_question_from_survey
    assert controller.delete_questions_from_survey is survey_workflows.delete_questions_from_survey
    assert controller.delete_question_from_file is survey_workflows.delete_question_from_file
    assert controller.duplicate_and_create_new_survey_id is survey_workflows.duplicate_and_create_new_survey_id
    assert controller.duplicate_and_create_new_question_id is survey_workflows.duplicate_and_create_new_question_id


def test_download_dataset(monkeypatch, tmp_path):
    dataset_name = "StudyDataset"
    zip_file = tmp_path / f"{dataset_name}.zip"
    zip_file.write_text("dummy zip content")

    monkeypatch.setattr(study_workflows.config, "storage_folder", str(tmp_path))
    monkeypatch.setattr(study_workflows.config, "download_folder", "")
    monkeypatch.setattr(constants, "zip_extension", ".zip")
    monkeypatch.setattr(constants, "zip_content_type", "application/zip")

    response = controller.download_dataset(dataset_name)
    assert isinstance(response, FileResponse)
    assert response["Content-Disposition"].endswith(".zip")


def test_download_study_dashboard_csv(monkeypatch, tmp_path):
    csv_file = tmp_path / "jutrack_dashboard_StudyX.csv"
    csv_file.write_text("subject,status\nA,active\n", encoding="utf-8")
    monkeypatch.setattr(study_workflows.config, "storage_folder", str(tmp_path))
    monkeypatch.setattr(study_workflows.config, "csv_prefix", "jutrack_dashboard_")

    response = controller.download_study_dashboard_csv("StudyX")

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv; charset=utf-8"
    assert "jutrack_dashboard_StudyX.csv" in response["Content-Disposition"]
    assert b"".join(response.streaming_content) == b"subject,status\nA,active\n"


def test_download_study_dashboard_csv_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(study_workflows.config, "storage_folder", str(tmp_path))

    with pytest.raises(study_workflows.Http404):
        controller.download_study_dashboard_csv("MissingStudy")


@pytest.fixture
def dummy_user_details():
    return {"first_name": "Alice", "email": "alice@example.com"}


def test_initiate_download_study_dataset(monkeypatch, tmp_path, dummy_user_details):
    study_name = "StudyX"
    data_type = "raw"

    monkeypatch.setattr(study_workflows.settings, "REMOTE_USERNAME", "testuser")
    monkeypatch.setattr(study_workflows.settings, "JUSELESS_SERVER", "remotehost")
    monkeypatch.setattr(study_workflows.settings, "JUSELESS_SCRIPT_FOLDER", "/remote")
    monkeypatch.setattr(study_workflows.config, "storage_folder", str(tmp_path))
    monkeypatch.setattr(study_workflows.config, "download_folder", "downloads")

    os.makedirs(tmp_path / "downloads", exist_ok=True)
    monkeypatch.setattr(study_workflows, "change_permissions", lambda x: None)
    monkeypatch.setattr(study_workflows, "is_test_study", lambda _study_name: False)
    thread_mock = MagicMock()
    monkeypatch.setattr(study_workflows.threading, "Thread", thread_mock)

    result = controller.initiate_download_study_dataset(study_name, data_type, dummy_user_details)

    assert result is True
    script_path = tmp_path / "downloads" / "download_dataset.sh"
    assert script_path.exists()
    with open(script_path, "r", encoding="utf-8") as file_handle:
        content = file_handle.read()
        assert "ssh testuser@remotehost" in content
    thread_mock.assert_called_once()


def test_test_study_download_is_forced_to_raw(monkeypatch, dummy_user_details):
    monkeypatch.setattr(study_workflows, "is_test_study", lambda _study_name: True)
    thread_mock = MagicMock()
    monkeypatch.setattr(study_workflows.threading, "Thread", thread_mock)

    result = study_workflows.initiate_download_study_dataset(
        "Test_Study",
        "processed",
        dummy_user_details,
    )

    assert result is True
    thread_args = thread_mock.call_args.kwargs["args"]
    assert thread_args[0] == "Test_Study"
    assert thread_args[1] == "raw"
    assert thread_args[2].startswith("Test_Study_raw_")
    thread_mock.return_value.start.assert_called_once()


def test_create_local_test_study_dataset_matches_remote_archive_layout(
    monkeypatch,
    tmp_path,
    dummy_user_details,
):
    study_root = tmp_path / "studies" / "TestStudy"
    (study_root / "inputs" / "subject1" / "raw").mkdir(parents=True)
    (study_root / "inputs" / "subject1" / "processed").mkdir(parents=True)
    (study_root / "inputs" / "subject1" / "combined").mkdir(parents=True)
    (study_root / "metadata").mkdir()
    (study_root / "inputs" / "subject1" / "raw" / "raw.json").write_text("raw")
    (study_root / "inputs" / "subject1" / "processed" / "processed.csv").write_text("processed")
    (study_root / "inputs" / "subject1" / "combined" / "combined.csv").write_text("combined")
    (study_root / "metadata" / "TestStudy.json").write_text("{}")

    monkeypatch.setattr(study_workflows.config, "studies_folder", str(tmp_path / "studies"))
    monkeypatch.setattr(study_workflows.config, "storage_folder", str(tmp_path))
    monkeypatch.setattr(study_workflows.config, "download_folder", "downloads")
    notify_mock = MagicMock()
    monkeypatch.setattr(study_workflows, "check_file_and_send_email", notify_mock)

    study_workflows.create_local_test_study_dataset(
        "TestStudy",
        "raw",
        "TestStudy_raw_timestamp",
        dummy_user_details,
    )

    zip_path = tmp_path / "downloads" / "TestStudy_raw_timestamp.zip"
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as archive:
        assert set(archive.namelist()) == {
            "inputs/subject1/raw/raw.json",
            "metadata/TestStudy.json",
        }
    notify_mock.assert_called_once_with(
        dummy_user_details,
        "TestStudy_raw_timestamp",
        send_link_email=True,
    )


def test_create_local_test_study_dataset_normalizes_legacy_local_layout(
    monkeypatch,
    tmp_path,
    dummy_user_details,
):
    studies_root = tmp_path / "studies"
    study_root = studies_root / "Legacy_Test"
    activation_root = study_root / "Legacy_Test_00001_1"
    shared_subject_root = studies_root / "inputs" / "Legacy_Test_00002"
    (activation_root / "device-id").mkdir(parents=True)
    (shared_subject_root / "raw").mkdir(parents=True)
    (shared_subject_root / "processed").mkdir()
    (activation_root / "device-id" / "payload.json").write_text("legacy")
    (shared_subject_root / "raw" / "sensor.json").write_text("raw")
    (shared_subject_root / "processed" / "sensor.csv").write_text("processed")
    (study_root / "Legacy_Test.json").write_text("{}")
    (study_root / "stats.json").write_text("{}")

    monkeypatch.setattr(study_workflows.config, "studies_folder", str(studies_root))
    monkeypatch.setattr(study_workflows.config, "storage_folder", str(tmp_path))
    monkeypatch.setattr(study_workflows.config, "download_folder", "downloads")
    notify_mock = MagicMock()
    monkeypatch.setattr(study_workflows, "check_file_and_send_email", notify_mock)

    study_workflows.create_local_test_study_dataset(
        "Legacy_Test",
        "raw",
        "Legacy_Test_raw_timestamp",
        dummy_user_details,
    )

    zip_path = tmp_path / "downloads" / "Legacy_Test_raw_timestamp.zip"
    with zipfile.ZipFile(zip_path) as archive:
        assert set(archive.namelist()) == {
            "inputs/Legacy_Test_00001_1/device-id/payload.json",
            "inputs/Legacy_Test_00002/raw/sensor.json",
            "metadata/Legacy_Test.json",
            "metadata/stats.json",
        }
    notify_mock.assert_called_once_with(
        dummy_user_details,
        "Legacy_Test_raw_timestamp",
        send_link_email=True,
    )


def test_check_file_and_send_email(monkeypatch, tmp_path, dummy_user_details):
    monkeypatch.setattr(study_workflows.config, "storage_folder", str(tmp_path))
    monkeypatch.setattr(study_workflows.config, "download_folder", "downloads")

    mock_token = MagicMock()
    mock_token.token = "abc123"
    create_mock = MagicMock(return_value=mock_token)
    monkeypatch.setattr(study_workflows.FileDownloadToken.objects, "create", create_mock)
    monkeypatch.setattr(study_workflows, "reverse", lambda name, args: "/download/token")
    send_email_mock = MagicMock(return_value=True)
    monkeypatch.setattr(study_workflows, "send_email", send_email_mock)

    os.makedirs(tmp_path / "downloads", exist_ok=True)
    (tmp_path / "downloads" / "StudyX_type1_2025-01-01T00:00:00.zip").write_bytes(
        b"zip"
    )

    result = controller.check_file_and_send_email(
        dummy_user_details,
        "StudyX_type1_2025-01-01T00:00:00",
        send_link_email=True,
    )

    assert result is True
    create_mock.assert_called_once()
    send_email_mock.assert_called_once_with(
        "",
        dummy_user_details["email"],
        "",
        "https://jdash.inm7.de/download/token",
    )
    assert mock_token.status == "sent email"


def test_remote_download_registration_does_not_send_email_or_wait_for_file(
    monkeypatch,
    tmp_path,
    dummy_user_details,
):
    monkeypatch.setattr(study_workflows.config, "storage_folder", str(tmp_path))
    monkeypatch.setattr(study_workflows.config, "download_folder", "downloads")
    mock_token = MagicMock(token="abc123")
    monkeypatch.setattr(
        study_workflows.FileDownloadToken.objects,
        "create",
        MagicMock(return_value=mock_token),
    )
    monkeypatch.setattr(
        study_workflows,
        "reverse",
        lambda name, args: "/download/token",
    )
    send_email_mock = MagicMock()
    monkeypatch.setattr(study_workflows, "send_email", send_email_mock)

    result = study_workflows.check_file_and_send_email(
        dummy_user_details,
        "RemoteStudy_raw_timestamp",
    )

    assert result is True
    assert mock_token.status != "sent email"
    send_email_mock.assert_not_called()


def test_get_all_survey_details_success(monkeypatch):
    dummy_user = "user_obj"
    dummy_session_key = "abc123"
    dummy_db_surveys = [{"id": 1, "title": "DB Survey"}]
    dummy_file_surveys = [{"title": "Study JSON"}]

    monkeypatch.setattr(
        survey_workflows,
        "retrieve_all_survey_for_user",
        lambda user, session_key: dummy_db_surveys,
    )
    monkeypatch.setattr(
        survey_workflows,
        "get_survey_list",
        lambda session_key: dummy_file_surveys,
    )

    result = controller.get_all_survey_details(dummy_user, dummy_session_key)

    assert "survey_list" in result
    assert len(result["survey_list"]) == 2
    assert result["survey_list"][0]["title"] == "DB Survey"
    assert result["survey_list"][1]["title"] == "Study JSON"


def test_get_all_survey_details_failure(monkeypatch):
    monkeypatch.setattr(
        survey_workflows,
        "retrieve_all_survey_for_user",
        lambda user, session_key: (_ for _ in ()).throw(Exception("DB fail")),
    )

    result = controller.get_all_survey_details("user_obj", "abc123")

    assert constants.key_name_error_message in result
    assert result[constants.key_name_error_message] == "get_all_survey_details:: Exception occured"


def test_create_survey_from_survey_form_success(monkeypatch):
    monkeypatch.setattr(survey_workflows.Survey, "create_from_data", lambda form_data, user: 42)
    monkeypatch.setattr(
        survey_workflows,
        "context_for_create_survey_page",
        lambda survey_id: {"survey_id": survey_id},
    )

    result = controller.create_survey_from_surveyForm({"title": "My Survey"}, MagicMock())

    assert result == {"survey_id": 42}


def test_create_survey_from_survey_form_failure(monkeypatch):
    monkeypatch.setattr(
        survey_workflows.Survey,
        "create_from_data",
        lambda form_data, user: (_ for _ in ()).throw(RuntimeError("Database error")),
    )
    monkeypatch.setattr(survey_workflows, "context_for_survey_list_page", lambda: {})

    result = controller.create_survey_from_surveyForm({"title": "My Survey"}, MagicMock())

    assert constants.key_name_error_message in result
    assert "Database error" in result[constants.key_name_error_message]


def test_update_survey_from_survey_form_success(monkeypatch):
    monkeypatch.setattr(
        survey_workflows.Survey,
        "update_from_data",
        lambda form_data, survey_id: survey_id,
    )
    monkeypatch.setattr(
        survey_workflows,
        "context_for_create_survey_page",
        lambda survey_id: {"survey_id": survey_id},
    )

    result = controller.update_survey_from_surveyForm({"title": "Updated Survey"}, 123)

    assert result == {"survey_id": 123}
