import os
import sys
from unittest.mock import MagicMock

import django
import pytest
from django.http import HttpResponse


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
    assert isinstance(response, HttpResponse)
    assert response["Content-Disposition"].endswith(".zip")


@pytest.fixture
def dummy_user_details():
    return {"first_name": "Alice", "email": "alice@example.com"}


def test_initiate_download_study_dataset(monkeypatch, tmp_path, dummy_user_details):
    study_name = "StudyX"
    data_type = "type1"

    monkeypatch.setattr(study_workflows.settings, "REMOTE_USERNAME", "testuser")
    monkeypatch.setattr(study_workflows.settings, "JUSELESS_SERVER", "remotehost")
    monkeypatch.setattr(study_workflows.settings, "JUSELESS_SCRIPT_FOLDER", "/remote")
    monkeypatch.setattr(study_workflows.config, "storage_folder", str(tmp_path))
    monkeypatch.setattr(study_workflows.config, "download_folder", "downloads")

    os.makedirs(tmp_path / "downloads", exist_ok=True)
    monkeypatch.setattr(study_workflows, "change_permissions", lambda x: None)
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


def test_check_file_and_send_email(monkeypatch, tmp_path, dummy_user_details):
    monkeypatch.setattr(study_workflows.config, "storage_folder", str(tmp_path))
    monkeypatch.setattr(study_workflows.config, "download_folder", "downloads")
    monkeypatch.setattr(study_workflows.config, "download_zip_files_log", "log.csv")

    mock_token = MagicMock()
    mock_token.token = "abc123"
    create_mock = MagicMock(return_value=mock_token)
    monkeypatch.setattr(study_workflows.FileDownloadToken.objects, "create", create_mock)
    monkeypatch.setattr(study_workflows, "reverse", lambda name, args: "/download/token")
    monkeypatch.setattr(study_workflows, "change_permissions", lambda x: None)

    os.makedirs(tmp_path / "downloads", exist_ok=True)

    controller.check_file_and_send_email(dummy_user_details, "StudyX_type1_2025-01-01T00:00:00")

    create_mock.assert_called_once()
    mock_token.save.assert_called_once()
    assert (tmp_path / "downloads" / "log.csv").exists()


def test_get_all_survey_details_success(monkeypatch):
    dummy_user = "user_obj"
    dummy_session_key = "abc123"
    dummy_db_surveys = [{"id": 1, "title": "DB Survey"}]
    dummy_file_surveys = [{"id": "999", "title": "Study JSON"}]

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
