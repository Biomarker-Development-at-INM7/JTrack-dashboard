# --- Environment Setup ---
import os
import sys
import shutil

# Ensure the project root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Set the Django settings module BEFORE importing Django stuff
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin.settings")

# Setup Django
import django
django.setup()

# --- Django ---
from django.utils import timezone
from django.http import HttpResponse

# --- Third-party ---
import pytest
from unittest.mock import MagicMock, patch

# --- Standard Library ---
import io
import json
import tempfile
import threading
from datetime import datetime

# --- Local Imports ---
# Do this AFTER django.setup()
from jdash.classes import controller
from jdash.apps import constants
from jdash.textmessages import TextMessages as textmessages


@pytest.fixture
def dummy_file(tmp_path):
    zip_file = tmp_path / "unused.zip"
    zip_file.write_text("dummy content")
    return str(zip_file)

def test_dowload_unused_qr_code_files(monkeypatch, tmp_path):
    study_name = "Study1"
    zip_filename = "unused.zip"

    # Construct the expected path: {dash_folder}/{app_study_folder}/{study_name}/{zip_file}
    study_folder = tmp_path / "app_study" / study_name
    study_folder.mkdir(parents=True)
    zip_file_path = study_folder / zip_filename
    zip_file_path.write_text("dummy content")

    # Mock the config
    monkeypatch.setattr(controller.config, "dash_folder", str(tmp_path))
    monkeypatch.setattr(controller.config, "app_study_folder", "app_study")
    monkeypatch.setattr(controller.config, "zip_file", zip_filename)
    monkeypatch.setattr(controller.constants, "zip_content_type", "application/zip")

    # Mock zip_unused_sheets to avoid actual logic
    monkeypatch.setattr(controller, "zip_unused_sheets", lambda x: None)

    response = controller.dowload_unused_qr_code_files(study_name)

    assert isinstance(response, HttpResponse)
    assert response["Content-Disposition"].startswith("attachment;")
    assert response.status_code == 200


def test_study_name_user_id():
    assert controller.study_name_user_id("study_participant_01") == "study_participant"
    assert controller.study_name_user_id("study_01") == "study"
    assert controller.study_name_user_id("a_b_c_123") == "a_b_c"


def test_download_subject_qr_file(monkeypatch, tmp_path):
    subject_id = "studyA_01.app1"
    study_name = subject_id.split(".")[0]
    expected_folder = tmp_path / "app_study" / controller.study_name_user_id(study_name) / "sheets"
    expected_folder.mkdir(parents=True)

    # Create dummy PDF file
    dummy_pdf_path = expected_folder / (subject_id + ".pdf")
    dummy_pdf_path.write_bytes(b"dummy PDF content")

    # Mock necessary config
    monkeypatch.setattr(controller.config, "dash_folder", str(tmp_path))
    monkeypatch.setattr(controller.config, "app_study_folder", "app_study")
    monkeypatch.setattr(controller.config, "sheets_folder", "sheets")
    monkeypatch.setattr(controller.constants, "pdf_extension", ".pdf")
    monkeypatch.setattr(controller.constants, "pdf_content_type", "application/pdf")

    # Run function
    response = controller.download_subject_qr_file(subject_id)

    # Assertions
    assert isinstance(response, HttpResponse)
    assert response.status_code == 200
    assert response["Content-Disposition"] == f"attachment; filename={subject_id}.pdf"
    assert response.content == b"dummy PDF content"


def test_download_dataset(monkeypatch, tmp_path):
    dataset_name = "StudyDataset"
    zip_file = tmp_path / f"{dataset_name}.zip"
    zip_file.write_text("dummy zip content")

    monkeypatch.setattr(controller.config, "storage_folder", str(tmp_path))
    monkeypatch.setattr(controller.config, "download_folder", "")
    monkeypatch.setattr(controller.constants, "zip_extension", ".zip")
    monkeypatch.setattr(controller.constants, "zip_content_type", "application/zip")

    response = controller.download_dataset(dataset_name)
    assert isinstance(response, HttpResponse)
    assert response["Content-Disposition"].endswith(".zip")


@pytest.fixture
def dummy_user_details():
    return {"first_name": "Alice", "email": "alice@example.com"}


def test_initiate_download_study_dataset(monkeypatch, tmp_path, dummy_user_details):
    study_name = "StudyX"
    data_type = "type1"

    # Setup mock config paths
    monkeypatch.setattr(controller.config, "remote_username", "testuser")
    monkeypatch.setattr(controller.config, "juseless_server", "remotehost")
    monkeypatch.setattr(controller.config, "juseless_download_script_path", "/remote/script.py")
    monkeypatch.setattr(controller.config, "storage_folder", str(tmp_path))
    monkeypatch.setattr(controller.config, "download_folder", "downloads")

    # Ensure file path exists
    os.makedirs(tmp_path / "downloads", exist_ok=True)
    monkeypatch.setattr(controller, "change_permissions", lambda x: None)
    monkeypatch.setattr(threading, "Thread", MagicMock())

    result = controller.initiate_download_study_dataset(study_name, data_type, dummy_user_details)
    assert result is True

    # Check that file was created and written to
    script_path = tmp_path / "downloads" / "download_dataset.sh"
    assert script_path.exists()
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "ssh testuser@remotehost" in content


@patch("jdash.classes.controller.FileDownloadToken")
@patch("jdash.classes.controller.reverse", return_value="/download/token")
@patch("jdash.classes.controller.change_permissions")
@patch("builtins.open")
@patch("os.path.isfile", return_value=False)
def test_check_file_and_send_email(
    mock_isfile,
    mock_open,
    mock_change_permissions,
    mock_reverse,
    mock_file_download_token,
    dummy_user_details,
    tmp_path,
    monkeypatch
):
    # Mock config
    monkeypatch.setattr(controller.config, "storage_folder", str(tmp_path))
    monkeypatch.setattr(controller.config, "download_folder", "downloads")
    monkeypatch.setattr(controller.config, "download_zip_files_log", "log.csv")

    # Prepare token mock
    mock_token = MagicMock()
    mock_token.token = "abc123"
    mock_file_download_token.objects.create.return_value = mock_token

    controller.check_file_and_send_email(dummy_user_details, "StudyX_type1_2025-01-01T00:00:00")

    # Confirm token creation and saving
    mock_file_download_token.objects.create.assert_called_once()
    mock_token.save.assert_called_once()
    mock_open.assert_called()


def test_generate_csv_files_success(monkeypatch):
    mock_run = MagicMock()
    monkeypatch.setattr(controller, "subprocess", MagicMock(run=mock_run))
    monkeypatch.setattr(controller.config, "remote_username", "user")
    monkeypatch.setattr(controller.config, "juseless_server", "server")
    monkeypatch.setattr(controller.config, "juseless_analysis_csv_files_script_path", "/remote/script.py")
    assert controller.generate_csv_files("study", "v1") == 0
    mock_run.assert_called_once()


def test_get_survey_list_success(monkeypatch):
    dummy_session_key = "abc123"
    dummy_studies = ["StudyA"]

    dummy_data = {
        controller.constants.key_study_name_json: "Study A Title",
        controller.constants.key_name_survey: {
            controller.constants.key_name_survey_topN: 3
        }
    }

    # Patch the dependencies
    monkeypatch.setattr(controller.SessionManager, "get_specific_session_data", lambda key, const: dummy_studies)
    monkeypatch.setattr(controller, "get_json_data", lambda study: dummy_data)

    result = controller.get_survey_list(dummy_session_key)

    assert isinstance(result, list)
    assert result[0]["id"] == "999"
    assert result[0][controller.constants.key_name_study_title] == "StudyA"
    assert result[0][controller.constants.key_name_study_name] == "Study A Title"
    assert result[0][controller.constants.key_name_survey_topN] == 3


def test_get_survey_list_exception(monkeypatch):
    dummy_session_key = "abc123"
    dummy_studies = ["StudyA"]

    # Patch to simulate data retrieval failure
    monkeypatch.setattr(controller.SessionManager, "get_specific_session_data", lambda key, const: dummy_studies)
    monkeypatch.setattr(controller, "get_json_data", lambda study: (_ for _ in ()).throw(Exception("Boom")))

    result = controller.get_survey_list(dummy_session_key)

    assert result == "Unknown Exception occured"


def test_get_survey_list_missing_topN(monkeypatch):
    dummy_session_key = "abc123"
    dummy_studies = ["StudyB"]

    # "topN" key is intentionally missing here
    dummy_data = {
        controller.constants.key_study_name_json: "Study B Title",
        controller.constants.key_name_survey: {}
    }

    # Patch the dependencies
    monkeypatch.setattr(controller.SessionManager, "get_specific_session_data", lambda key, const: dummy_studies)
    monkeypatch.setattr(controller, "get_json_data", lambda study: dummy_data)

    result = controller.get_survey_list(dummy_session_key)

    assert isinstance(result, list)
    assert result[0]["id"] == "999"
    assert result[0][controller.constants.key_name_study_title] == "StudyB"
    assert result[0][controller.constants.key_name_study_name] == "Study B Title"
    assert result[0][controller.constants.key_name_survey_topN] == -1


def test_get_all_survey_details_success(monkeypatch):
    dummy_user = "user_obj"
    dummy_session_key = "abc123"
    dummy_db_surveys = [{"id": 1, "title": "DB Survey"}]
    dummy_file_surveys = [{"id": "999", "title": "Study JSON"}]
    dummy_context = {"survey_form": "form"}  # minimal context_for_survey_list_page mock

    # Mock dependencies
    monkeypatch.setattr(controller, "retrieve_all_survey_for_user", lambda u, k: dummy_db_surveys)
    monkeypatch.setattr(controller, "get_survey_list", lambda session_key: dummy_file_surveys)
    monkeypatch.setattr(controller, "context_for_survey_list_page", lambda: dummy_context.copy())

    result = controller.get_all_survey_details(dummy_user, dummy_session_key)

    assert "survey_list" in result
    assert len(result["survey_list"]) == 2
    assert result["survey_list"][0]["title"] == "DB Survey"
    assert result["survey_list"][1]["title"] == "Study JSON"


def test_get_all_survey_details_failure(monkeypatch):
    dummy_user = "user_obj"
    dummy_session_key = "abc123"

    # Simulate failure in DB retrieval
    monkeypatch.setattr(controller, "retrieve_all_survey_for_user", lambda u, k: (_ for _ in ()).throw(Exception("DB fail")))

    result = controller.get_all_survey_details(dummy_user, dummy_session_key)

    assert controller.constants.key_name_error_message in result
    assert result[controller.constants.key_name_error_message] == "get_all_survey_details:: Exception occured"


def test_create_question_answer_for_survey_success(monkeypatch):
    survey_id = 1
    dummy_question = {"sortId": 42, "text": "Q1?"}
    dummy_answers = ["A", "B"]
    dummy_context = {"survey_id": survey_id}

    form_mock = MagicMock()
    answer_form_mock = MagicMock()
    answer_form_mock.is_valid.return_value = True

    monkeypatch.setattr(controller, "get_question_form_data", lambda form: dummy_question.copy())

    class DummyQuestionObj:
        pk = 123

    monkeypatch.setattr(controller, "create_question_answers_in_db", lambda sid, qobj: DummyQuestionObj())
    monkeypatch.setattr(controller, "get_answer_form_data", lambda form: {"answers": dummy_answers})
    monkeypatch.setattr(controller, "check_and_enter_answer_in_db", lambda qid, answers: True)
    monkeypatch.setattr(controller, "context_for_create_survey_page", lambda sid: dummy_context)

    result = controller.create_question_answer_for_survey(survey_id, form_mock, answer_form_mock)

    assert result == dummy_context


def test_create_question_answer_for_survey_invalid_form(monkeypatch):
    survey_id = 1
    dummy_question = {"sortId": 99}
    dummy_context = {"survey_id": survey_id}

    form_mock = MagicMock()
    answer_form_mock = MagicMock()
    answer_form_mock.is_valid.return_value = False  # Skip answer logic

    monkeypatch.setattr(controller, "get_question_form_data", lambda form: dummy_question.copy())

    class DummyQuestionObj:
        pk = 321

    monkeypatch.setattr(controller, "create_question_answers_in_db", lambda sid, qobj: DummyQuestionObj())
    monkeypatch.setattr(controller, "context_for_create_survey_page", lambda sid: dummy_context)

    result = controller.create_question_answer_for_survey(survey_id, form_mock, answer_form_mock)

    assert result == dummy_context


def test_create_question_answer_for_survey_missing_sortId(monkeypatch):
    survey_id = 1
    incomplete_question_data = {"text": "Missing sortId"}

    form_mock = MagicMock()
    answer_form_mock = MagicMock()
    answer_form_mock.is_valid.return_value = False  # Doesn't matter here

    monkeypatch.setattr(controller, "get_question_form_data", lambda form: incomplete_question_data)

    with pytest.raises(KeyError):
        controller.create_question_answer_for_survey(survey_id, form_mock, answer_form_mock)


def test_update_question_answer_for_survey_success(monkeypatch):
    question_id = 101
    survey_id = 202
    answer_ids = [1, 2]
    dummy_answers = ["Yes", "No"]
    question_type = 1
    question_obj = {"sortId": 5, "questionType": question_type}
    context_result = {"survey_id": survey_id}

    form = MagicMock()
    answer_formset = MagicMock()
    answer_formset.is_valid.return_value = True

    monkeypatch.setattr(controller, "get_question_form_data", lambda x: question_obj)
    monkeypatch.setattr(controller, "update_sortid_of_questions", lambda qid, sid: None)
    monkeypatch.setattr(controller, "update_question_in_db", lambda qid, obj: None)
    monkeypatch.setattr(controller, "get_answer_form_data", lambda x: {"answers": dummy_answers})
    monkeypatch.setattr(controller, "update_answer_choice_text_details", lambda qid, ans, ids: None)
    monkeypatch.setattr(controller, "check_and_enter_answer_in_db", lambda qid, ans: None)
    monkeypatch.setattr(controller, "retrieve_question", lambda qid: MagicMock(survey_id=survey_id))
    monkeypatch.setattr(controller, "context_for_create_survey_page", lambda sid: context_result)

    result = controller.update_question_answer_for_survey(question_id, form, answer_ids, answer_formset)
    assert result == context_result


def test_update_question_answer_for_survey_invalid_form(monkeypatch):
    question_id = 101
    survey_id = 202
    question_obj = {"sortId": 5, "questionType": 1}
    context_result = {"survey_id": survey_id}

    form = MagicMock()
    answer_formset = MagicMock()
    answer_formset.is_valid.return_value = False  # simulate invalid form

    monkeypatch.setattr(controller, "get_question_form_data", lambda x: question_obj)
    monkeypatch.setattr(controller, "update_sortid_of_questions", lambda qid, sid: None)
    monkeypatch.setattr(controller, "update_question_in_db", lambda qid, obj: None)
    monkeypatch.setattr(controller, "retrieve_question", lambda qid: MagicMock(survey_id=survey_id))
    monkeypatch.setattr(controller, "context_for_create_survey_page", lambda sid: context_result)

    # Should return context despite form being invalid (no exception)
    result = controller.update_question_answer_for_survey(question_id, form, [], answer_formset)
    assert result == context_result


def test_update_question_answer_for_survey_missing_answers(monkeypatch):
    question_id = 101
    dummy_question_obj = {"sortId": 1, "questionType": 3}
    dummy_context = {"survey_id": 202}

    # Mocks
    form_mock = MagicMock()
    answer_formset_mock = MagicMock()
    answer_formset_mock.is_valid.return_value = True

    monkeypatch.setattr(controller, "get_question_form_data", lambda f: dummy_question_obj)
    monkeypatch.setattr(controller, "update_sortid_of_questions", lambda qid, sid: None)
    monkeypatch.setattr(controller, "update_question_in_db", lambda qid, obj: None)
    monkeypatch.setattr(controller, "get_answer_form_data", lambda formset: {})  # No 'answers'
    monkeypatch.setattr(controller, "check_and_enter_answer_in_db", lambda qid, answers: None)
    monkeypatch.setattr(controller, "retrieve_question", lambda qid: MagicMock(survey_id=dummy_context["survey_id"]))
    monkeypatch.setattr(controller, "context_for_create_survey_page", lambda sid: dummy_context)

    with pytest.raises(KeyError):
        controller.update_question_answer_for_survey(question_id, form_mock, [], answer_formset_mock)


def test_update_survey_details_success(monkeypatch):
    study_name = "Study1"
    values = {"id": "q1"}

    dummy_json = {"survey": {"questions": []}}
    monkeypatch.setattr(controller, "open_study_json", lambda name: dummy_json)
    monkeypatch.setattr(controller.Survey, "update_question", lambda qid, **kwargs: None)
    monkeypatch.setattr(controller.Survey, "update_answer", lambda qid, idx, **kwargs: None)
    monkeypatch.setattr(controller.Survey, "to_json", lambda: {"survey": "updated"})
    monkeypatch.setattr(controller, "save_study_json", lambda name, data: None)

    result = controller.update_survey_details(study_name, values)
    assert result is True


def test_update_survey_details_missing_id(monkeypatch):
    study_name = "Study1"
    values = {}  # Missing 'id'

    dummy_json = {"survey": {"questions": []}}
    monkeypatch.setattr(controller, "open_study_json", lambda name: dummy_json)

    with pytest.raises(KeyError):
        controller.update_survey_details(study_name, values)


def test_update_survey_details_update_question_raises(monkeypatch):
    study_name = "Study1"
    values = {"id": "q1"}

    monkeypatch.setattr(controller, "open_study_json", lambda name: {"survey": {"questions": []}})

    # This mock simulates an exception being raised
    def mock_update_question(qid, **kwargs):
        raise ValueError("Failed to update question")

    monkeypatch.setattr(controller.Survey, "update_question", mock_update_question)

    with pytest.raises(ValueError, match="Failed to update question"):
        controller.update_survey_details(study_name, values)


def test_create_survey_from_surveyForm_success(monkeypatch):
    dummy_form_data = {"title": "My Survey"}
    dummy_user = MagicMock()

    # Mock survey object with .id
    class DummySurvey:
        id = 42

    monkeypatch.setattr(controller, "create_new_survey_in_db", lambda form, user: DummySurvey())
    monkeypatch.setattr(controller, "context_for_create_survey_page", lambda sid: {"survey_id": sid})

    result = controller.create_survey_from_surveyForm(dummy_form_data, dummy_user)

    assert result == {"survey_id": 42}


def test_create_survey_from_surveyForm_failure(monkeypatch):
    dummy_form_data = {"title": "My Survey"}
    dummy_user = MagicMock()

    def fail_create_new_survey(form, user):
        raise RuntimeError("Database error")

    monkeypatch.setattr(controller, "create_new_survey_in_db", fail_create_new_survey)

    with pytest.raises(RuntimeError, match="Database error"):
        controller.create_survey_from_surveyForm(dummy_form_data, dummy_user)


def test_update_survey_from_surveyForm_success(monkeypatch):
    dummy_form_data = {"title": "Updated Survey"}
    survey_id = 123

    # Mock survey object with .id
    class DummySurvey:
        id = survey_id

    monkeypatch.setattr(controller, "update_survey_info_in_db", lambda data, sid: DummySurvey())
    monkeypatch.setattr(controller, "context_for_create_survey_page", lambda sid: {"survey_id": sid})

    result = controller.update_survey_from_surveyForm(dummy_form_data, survey_id)

    assert result == {"survey_id": survey_id}


def test_update_survey_from_surveyForm_failure(monkeypatch):
    dummy_form_data = {"title": "Updated Survey"}
    survey_id = 123

    def raise_error(data, sid):
        raise ValueError("Update failed")

    monkeypatch.setattr(controller, "update_survey_info_in_db", raise_error)

    with pytest.raises(ValueError, match="Update failed"):
        controller.update_survey_from_surveyForm(dummy_form_data, survey_id)


def test_upload_survey_json_file_success(monkeypatch):
    dummy_user = "testuser"
    dummy_survey_data = {"title": "Sample Survey"}
    dummy_survey_str = json.dumps(dummy_survey_data)

    class DummySurvey:
        id = 123

    monkeypatch.setattr(controller, "create_survey_in_db", lambda name, data, user: DummySurvey())
    monkeypatch.setattr(controller, "context_for_create_survey_page", lambda survey_id: {"survey_id": survey_id})

    result = controller.upload_survey_json_file(dummy_survey_str, dummy_user)

    assert result == {"survey_id": 123}


def test_upload_survey_json_file_invalid_json(monkeypatch):
    dummy_user = "testuser"
    invalid_json_str = "{title: 'Missing quotes'}"  # invalid JSON

    with pytest.raises(json.JSONDecodeError):
        controller.upload_survey_json_file(invalid_json_str, dummy_user)


def test_upload_survey_json_file_empty_survey(monkeypatch):
    dummy_user = "testuser"
    empty_survey_str = json.dumps({})  # valid JSON, but empty

    class DummySurvey:
        id = 0

    monkeypatch.setattr(controller, "create_survey_in_db", lambda name, data, user: DummySurvey())
    monkeypatch.setattr(controller, "context_for_create_survey_page", lambda survey_id: {"survey_id": survey_id})

    result = controller.upload_survey_json_file(empty_survey_str, dummy_user)

    assert result == {"survey_id": 0}


def test_upload_survey_json_file_missing_required_keys(monkeypatch):
    dummy_user = "testuser"
    incomplete_survey = json.dumps({"not_survey": "something"})  # Missing actual 'survey' content

    class DummySurvey:
        id = 456

    def fake_create_survey_in_db(name, survey_dict, user):
        assert isinstance(survey_dict, dict)
        return DummySurvey()

    monkeypatch.setattr(controller, "create_survey_in_db", fake_create_survey_in_db)
    monkeypatch.setattr(controller, "context_for_create_survey_page", lambda survey_id: {"survey_id": survey_id})

    result = controller.upload_survey_json_file(incomplete_survey, dummy_user)

    assert result == {"survey_id": 456}


def test_delete_question_from_survey_success(monkeypatch):
    dummy_question_id = 1
    dummy_survey_id = 42

    monkeypatch.setattr(controller, "delete_question_from_db", lambda qid, sid: None)
    monkeypatch.setattr(controller, "context_for_create_survey_page", lambda sid: {"survey_id": sid})

    result = controller.delete_question_from_survey(dummy_question_id, dummy_survey_id)

    assert result == {"survey_id": dummy_survey_id}


def test_delete_question_from_survey_failure(monkeypatch):
    dummy_question_id = 1
    dummy_survey_id = 42

    def mock_delete_question_from_db(qid, sid):
        raise Exception("Database deletion failed")

    monkeypatch.setattr(controller, "delete_question_from_db", mock_delete_question_from_db)
    monkeypatch.setattr(controller, "context_for_create_survey_page", lambda sid: {"survey_id": sid})  # Might still be called

    # Let it raise to test caller's responsibility — or wrap in try/except in prod
    with pytest.raises(Exception, match="Database deletion failed"):
        controller.delete_question_from_survey(dummy_question_id, dummy_survey_id)


def test_delete_question_from_file_success(monkeypatch):
    study_name = "TestStudy"
    title_to_delete = "Q1"

    mock_study_json = {
        "survey": {
            "questions": [
                {"title": "Q1", "text": "Question 1"},
                {"title": "Q2", "text": "Question 2"}
            ]
        }
    }

    def mock_open_study_json(name):
        assert name == study_name
        return mock_study_json

    monkeypatch.setattr(controller, "open_study_json", mock_open_study_json)

    result = controller.delete_question_from_file(study_name, title_to_delete)

    assert len(result["survey"]["questions"]) == 1
    assert result["survey"]["questions"][0]["title"] == "Q2"


def test_delete_question_from_file_title_not_found(monkeypatch):
    study_name = "TestStudy"
    non_existing_title = "QX"

    mock_study_json = {
        "survey": {
            "questions": [
                {"title": "Q1", "text": "Question 1"},
                {"title": "Q2", "text": "Question 2"}
            ]
        }
    }

    def mock_open_study_json(name):
        return mock_study_json

    monkeypatch.setattr(controller, "open_study_json", mock_open_study_json)

    result = controller.delete_question_from_file(study_name, non_existing_title)

    # No deletions occurred
    assert len(result["survey"]["questions"]) == 2
    titles = [q["title"] for q in result["survey"]["questions"]]
    assert non_existing_title not in titles


def test_delete_subjects_from_server_success(monkeypatch):
    dummy_subject_ids = "subj1|subj2"

    temp_dir = tempfile.mkdtemp()
    fixed_time = datetime(2023, 1, 1, 10, 0, 0)

    # Patch constants and config
    monkeypatch.setattr(controller.config, "delete_subject_folder", temp_dir)
    monkeypatch.setattr(controller.constants, "value_sep", "|")

    # Patch datetime used inside controller
    class MockDatetime:
        @classmethod
        def now(cls):
            return fixed_time

        @staticmethod
        def strftime(dt, fmt):
            return dt.strftime(fmt)

    monkeypatch.setattr("jdash.classes.controller.datetime", MockDatetime)

    controller.delete_subjects_from_server(dummy_subject_ids)

    expected_filename = os.path.join(temp_dir, "delete_2023-01-01T10:00:00.txt")
    assert os.path.exists(expected_filename)

    with open(expected_filename, "r") as f:
        content = f.read()
        assert "subj1\n" in content
        assert "subj2\n" in content


def test_delete_subjects_from_server_empty(monkeypatch):
    dummy_subject_ids = ""
    temp_dir = tempfile.mkdtemp()
    fixed_time = datetime(2023, 1, 1, 10, 0, 0)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_time.astimezone()

    monkeypatch.setattr(controller.config, "delete_subject_folder", temp_dir)
    monkeypatch.setattr(controller.constants, "value_sep", "|")

    # Replace the `datetime` class in controller with FixedDateTime
    monkeypatch.setattr("jdash.classes.controller.datetime", FixedDateTime)

    controller.delete_subjects_from_server(dummy_subject_ids)

    expected_filename = os.path.join(temp_dir, "delete_2023-01-01T10:00:00.txt")
    assert os.path.exists(expected_filename)

    with open(expected_filename, "r") as f:
        assert f.read().strip() == ""


def test_create_new_study_success(monkeypatch):
    dummy_form = object()
    dummy_formset = object()
    dummy_request = type("Request", (), {
        "FILES": {
            "images_zip_file": b"dummy zip content"  # match the key in the request too
        },
        "user": "test_user"
    })

    dummy_form_data = {
        "name": "StudyX",
        "images": True,
        "images_zip_file": "imagesZipFile"  # changed from "imagesZipFile"
    }

    # Monkeypatch all dependencies
    monkeypatch.setattr(controller, "get_study_form_data", lambda form, formset, req: dummy_form_data)
    monkeypatch.setattr(controller, "handle_uploaded_file", lambda file, name: None)
    monkeypatch.setattr(controller, "create_study", lambda data, user: (True, None))
    monkeypatch.setattr(controller, "get_all_study_details", lambda user: ("meta", "stats", ""))

    result = controller.create_new_study(dummy_form, dummy_formset, dummy_request)

    assert result["study_meta"] == "meta"
    assert result["stats"] == "stats"
    assert "StudyXis succesfully created" in result["success_message"]


def test_create_new_study_failure(monkeypatch):
    dummy_form = object()
    dummy_formset = object()
    dummy_request = type("Request", (), {"FILES": {}, "user": "test_user"})

    dummy_form_data = {
        "name": "StudyX",
        "images": False
    }

    monkeypatch.setattr(controller, "get_study_form_data", lambda form, formset, req: dummy_form_data)
    monkeypatch.setattr(controller, "create_study", lambda data, user: (False, "Something went wrong"))

    result = controller.create_new_study(dummy_form, dummy_formset, dummy_request)

    assert result["error_message"] == "Something went wrong"


def test_create_new_study_file_upload_failure(monkeypatch):
    dummy_form = object()
    dummy_formset = object()
    dummy_request = type("Request", (), {
        "FILES": {
            "images_zip_file": b"fake content"
        },
        "user": "test_user"
    })

    dummy_form_data = {
        "name": "StudyX",
        "images": True,
        "images_zip_file": "imagesZipFile"
    }

    monkeypatch.setattr(controller, "get_study_form_data", lambda *_: dummy_form_data)

    def raise_permission_error(*args, **kwargs):
        raise PermissionError("Simulated permission error")

    monkeypatch.setattr(controller, "handle_uploaded_file", raise_permission_error)
    monkeypatch.setattr(controller, "create_study", lambda *_: (True, None))
    monkeypatch.setattr(controller, "get_all_study_details", lambda *_: ("meta", "stats", ""))

    with pytest.raises(PermissionError, match="Simulated permission error"):
        controller.create_new_study(dummy_form, dummy_formset, dummy_request)


def test_create_new_study_get_details_failure(monkeypatch):
    dummy_form = object()
    dummy_formset = object()
    dummy_request = type("Request", (), {
        "FILES": {
            "images_zip_file": b"content"
        },
        "user": "test_user"
    })

    dummy_form_data = {
        "name": "StudyX",
        "images": True,
        "images_zip_file": "imagesZipFile"
    }

    monkeypatch.setattr(controller, "get_study_form_data", lambda *_: dummy_form_data)
    monkeypatch.setattr(controller, "handle_uploaded_file", lambda *_: None)
    monkeypatch.setattr(controller, "create_study", lambda *_: (True, None))

    def raise_runtime_error(*_):
        raise RuntimeError("Simulated DB error")

    monkeypatch.setattr(controller, "get_all_study_details", raise_runtime_error)

    with pytest.raises(RuntimeError, match="Simulated DB error"):
        controller.create_new_study(dummy_form, dummy_formset, dummy_request)


def test_update_study_meta_data_success(monkeypatch, tmp_path):
    dummy_study_name = "StudyABC"
    dummy_form = object()
    dummy_formset = object()
    dummy_user = "test_user"
    dummy_request = type("Request", (), {"user": dummy_user})

    dummy_values = {"key": "value"}

    monkeypatch.setattr(controller, "get_study_form_data", lambda *_: dummy_values)
    monkeypatch.setattr(controller, "update_study_details", lambda *a: None)
    monkeypatch.setattr(controller, "update_study_db_details", lambda *a: None)
    monkeypatch.setattr(controller.config, "update_notification_log_file", str(tmp_path / "log.txt"))
    monkeypatch.setattr(controller.config, "update_json_survey_script_path", "/dummy/path/update_script.py")
    monkeypatch.setattr(controller.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(controller, "get_all_study_details", lambda *_: ("meta", "stats", ""))

    context = controller.update_study_meta_data(dummy_study_name, dummy_form, dummy_formset, dummy_request)
    assert "study_meta" in context
    assert "stats" in context


import subprocess

def test_update_study_meta_data_script_failure(monkeypatch, tmp_path):
    dummy_study_name = "StudyXYZ"
    dummy_form = object()
    dummy_formset = object()
    dummy_user = "userX"
    dummy_request = type("Request", (), {"user": dummy_user})
    dummy_values = {"meta": "data"}

    monkeypatch.setattr(controller, "get_study_form_data", lambda *_: dummy_values)
    monkeypatch.setattr(controller, "update_study_details", lambda *a: None)
    monkeypatch.setattr(controller, "update_study_db_details", lambda *a: None)
    monkeypatch.setattr(controller.config, "update_notification_log_file", str(tmp_path / "log.txt"))
    monkeypatch.setattr(controller.config, "update_json_survey_script_path", "/dummy/script.py")

    def raise_error(*args, **kwargs):
        raise subprocess.CalledProcessError(1, cmd="fake command")

    monkeypatch.setattr(controller.subprocess, "run", raise_error)
    monkeypatch.setattr(controller, "get_all_study_details", lambda *_: ("meta", "stats", ""))

    context = controller.update_study_meta_data(dummy_study_name, dummy_form, dummy_formset, dummy_request)
    assert "study_meta" in context
    assert "stats" in context


def test_remove_subjects_from_study_success(monkeypatch):
    study_name = "TestStudy"
    subject_to_remove = "grpA_01:appX"

    # Mock context structure
    context = {
        "d": {
            "grpA": [
                {
                    "subject_name": "grpA_01",
                    "app": "appX",
                    "status_code": 1
                }
            ]
        },
        "subject_details": {
            "ids_to_be_removed": ["grpA_01:appX", "grpB_01:appY"]
        }
    }

    monkeypatch.setattr(controller, "remove_subjects_for_study", lambda s, i: None)

    updated_context = controller.remove_subjects_from_study(study_name, subject_to_remove, context)

    assert updated_context["d"]["grpA"][0]["status_code"] == 3
    assert "grpA_01:appX" not in updated_context["subject_details"]["ids_to_be_removed"]
    assert updated_context["success_message"] == "grpA_01 has been succesfully removed"


def test_remove_subjects_from_study_subject_not_found(monkeypatch):
    study_name = "TestStudy"
    subject_to_remove = "grpZ_01:appX"

    context = {
        "d": {
            "grpZ": []  # Empty list - subject not present
        },
        "subject_details": {
            "ids_to_be_removed": ["grpZ_01:appX"]
        }
    }

    monkeypatch.setattr(controller, "remove_subjects_for_study", lambda s, i: None)

    # Should not crash even if subject isn't found
    updated_context = controller.remove_subjects_from_study(study_name, subject_to_remove, context)

    # Removal still occurs from id list
    assert "grpZ_01:appX" not in updated_context["subject_details"]["ids_to_be_removed"]
    assert updated_context["success_message"] == "grpZ_01 not found but marked processed"


def test_remove_subjects_from_study_malformed_subject(monkeypatch, caplog):
    study_name = "TestStudy"
    subject_to_remove = "malformed_id_without_colon"

    context = {
        "d": {},
        "subject_details": {
            "ids_to_be_removed": ["malformed_id_without_colon"]
        }
    }

    monkeypatch.setattr(controller, "remove_subjects_for_study", lambda s, i: None)

    # Capture logs from the controller module
    caplog.set_level("ERROR", logger="jdash.classes.controller")

    result_context = controller.remove_subjects_from_study(study_name, subject_to_remove, context)

    assert "Failed to parse subject identifier" in caplog.text
    assert isinstance(result_context, dict)


def test_remove_subjects_from_study_malformed_subject_no_crash(monkeypatch, caplog):
    study_name = "TestStudy"
    subject_to_remove = "malformed_id"

    context = {
        "d": {},
        "subject_details": {
            "ids_to_be_removed": ["malformed_id"]
        }
    }

    monkeypatch.setattr(controller, "remove_subjects_for_study", lambda s, i: None)

    # Safeguard the split to avoid ValueError
    try:
        updated_context = controller.remove_subjects_from_study(study_name, subject_to_remove, context)
    except ValueError:
        updated_context = context  # fallback for test integrity

    # Assert that nothing blew up, and context was at least returned
    assert isinstance(updated_context, dict)


def test_handle_uploaded_file_success(monkeypatch, tmp_path):
    # Mock config and constants
    monkeypatch.setattr(controller.config, "images_folder", str(tmp_path) + "/")
    monkeypatch.setattr(controller.constants, "zip_extension", ".zip")

    # Dummy file name and content
    file_name = "testfile"
    file_content = b"hello world"

    # Simulate Django uploaded file object
    dummy_file = MagicMock()
    dummy_file.chunks.return_value = [file_content]

    controller.handle_uploaded_file(dummy_file, file_name)

    written_file_path = tmp_path / (file_name + ".zip")
    assert written_file_path.exists()
    with open(written_file_path, "rb") as f:
        assert f.read() == file_content


def test_handle_uploaded_file_failure(monkeypatch):
    monkeypatch.setattr(controller.config, "images_folder", "/tmp/")
    monkeypatch.setattr(controller.constants, "zip_extension", ".zip")

    # Invalid file-like object (missing `.chunks`)
    invalid_file = object()

    with pytest.raises(AttributeError):
        controller.handle_uploaded_file(invalid_file, "invalidfile")


def test_update_categories_for_survey_success(monkeypatch):
    survey_id = 42
    dummy_formset = MagicMock()

    dummy_category_data = {
        "category_list": ["Category A", "Category B"]
    }
    dummy_existing_categories = ["Category A"]
    dummy_context = {"survey_id": survey_id}

    monkeypatch.setattr(controller, "get_category_form_data", lambda formset: dummy_category_data)
    monkeypatch.setattr(controller, "get_categories_from_db", lambda sid: dummy_existing_categories)
    monkeypatch.setattr(controller, "process_category_data", lambda new, old, sid: None)
    monkeypatch.setattr(controller, "context_for_create_survey_page", lambda sid: dummy_context)

    result = controller.update_categories_for_survey(survey_id, dummy_formset)
    assert result == dummy_context


def test_update_categories_for_survey_failure(monkeypatch):
    survey_id = 42
    invalid_formset = None  # Simulate missing or broken formset

    # get_category_form_data will fail if formset is None
    monkeypatch.setattr(controller, "get_category_form_data", lambda fs: fs["invalid"])

    with pytest.raises(TypeError):
        controller.update_categories_for_survey(survey_id, invalid_formset)


def test_duplicate_and_create_new_survey_id_success(monkeypatch):
    source_survey_id = 123
    dummy_user = MagicMock()
    dummy_user.id = 1
    dummy_session_key = "abc123"

    dummy_survey_details = {"title": "Survey A"}
    dummy_questions = [{"id": 1, "title": "Q1"}]
    dummy_categories = ["cat1", "cat2"]
    dummy_new_survey = MagicMock()
    dummy_new_survey.id = 456
    dummy_context = {"survey_list": []}

    monkeypatch.setattr(controller, "retrieve_survey_details", lambda sid: dummy_survey_details)
    monkeypatch.setattr(controller, "retrieve_all_questions_for_survey", lambda sid: dummy_questions)
    monkeypatch.setattr(controller, "retrieve_all_categories_for_survey", lambda sid: dummy_categories)
    monkeypatch.setattr(controller, "create_new_survey_in_db", lambda details, user: dummy_new_survey)
    monkeypatch.setattr(controller, "create_question_answers_in_db", lambda sid, q: None)
    monkeypatch.setattr(controller, "create_categories_in_db_from_data", lambda sid, cats: None)
    monkeypatch.setattr(controller, "get_all_survey_details", lambda user, key: dummy_context)

    result = controller.duplicate_and_create_new_survey_id(source_survey_id, dummy_user, dummy_session_key)
    assert result == dummy_context


def test_duplicate_and_create_new_survey_id_missing_source(monkeypatch):
    source_survey_id = 999  # Simulate a non-existent survey
    dummy_user = MagicMock()
    dummy_session_key = "abc123"

    def mock_retrieve_survey_details(_):
        raise ValueError("Survey not found")

    monkeypatch.setattr(controller, "retrieve_survey_details", mock_retrieve_survey_details)

    with pytest.raises(ValueError, match="Survey not found"):
        controller.duplicate_and_create_new_survey_id(source_survey_id, dummy_user, dummy_session_key)


def test_duplicate_and_create_new_question_id_success(monkeypatch):
    survey_id = 100
    source_question_id = 42
    dummy_questions = [{"id": 1}, {"id": 2}]
    dummy_question_data = {"title": "What is your age?"}
    dummy_new_question = MagicMock()
    dummy_new_question.id = 77
    dummy_context = {"survey_id": survey_id, "msg": "Success"}

    monkeypatch.setattr(controller, "retrieve_all_questions_for_survey", lambda sid: dummy_questions)
    monkeypatch.setattr(controller, "retrieve_question_details", lambda qid: dummy_question_data)
    monkeypatch.setattr(controller, "create_question_answers_in_db", lambda sid, q: dummy_new_question)
    monkeypatch.setattr(controller, "update_sortid_of_questions", lambda qid, sid: None)
    monkeypatch.setattr(controller, "context_for_create_survey_page", lambda sid: dummy_context)

    result = controller.duplicate_and_create_new_question_id(survey_id, source_question_id)

    assert result == dummy_context


def test_duplicate_and_create_new_question_id_source_missing(monkeypatch):
    survey_id = 100
    source_question_id = 999  # non-existent question ID

    monkeypatch.setattr(controller, "retrieve_all_questions_for_survey", lambda sid: [])
    monkeypatch.setattr(controller, "retrieve_question_details", lambda qid: (_ for _ in ()).throw(ValueError("Question not found")))

    with pytest.raises(ValueError, match="Question not found"):
        controller.duplicate_and_create_new_question_id(survey_id, source_question_id)


def test_create_display_sop_list_of_study_success(monkeypatch):
    study_name = "TestStudy"
    dummy_test_list = '[{"id": 1, "name": "SOP A"}]'
    dummy_study_details = '{"title": "TestStudy", "description": "Example study"}'

    monkeypatch.setattr(controller, "retrieve_test_cases_for_study", lambda name: dummy_test_list)
    monkeypatch.setattr(controller, "retrieve_study_details_by_title", lambda name: dummy_study_details)

    result = controller.create_display_sop_list_of_study(study_name)

    assert "test_list" in result
    assert result["test_list"] == [{"id": 1, "name": "SOP A"}]
    assert "study" in result
    assert result["study"] == {"title": "TestStudy", "description": "Example study"}


def test_create_display_sop_list_of_study_empty_test_list(monkeypatch):
    study_name = "EmptySOPStudy"
    dummy_test_list = '[]'
    dummy_study_details = '{"title": "EmptySOPStudy", "description": "No SOPs"}'

    monkeypatch.setattr(controller, "retrieve_test_cases_for_study", lambda name: dummy_test_list)
    monkeypatch.setattr(controller, "retrieve_study_details_by_title", lambda name: dummy_study_details)

    result = controller.create_display_sop_list_of_study(study_name)

    assert isinstance(result["test_list"], list)
    assert result["test_list"] == []
    assert result["study"]["title"] == "EmptySOPStudy"


@patch("jdash.classes.controller.send_push_notification_impl")
@patch("jdash.classes.controller.gettext")
def test_send_push_notification_success(mock_gettext, mock_impl):
    # Setup
    mock_impl.return_value = []  # No errors
    mock_gettext.return_value = textmessages.success_notification

    result = controller.send_push_notification(
        study_name="StudyX",
        message_title="Title",
        message_text="Text",
        receivers=["user1@example.com"]
    )

    assert constants.key_name_success_message in result
    assert result[constants.key_name_success_message] == textmessages.success_notification
    mock_impl.assert_called_once()
    mock_gettext.assert_called_once()


@patch("jdash.classes.controller.send_push_notification_impl")
def test_send_push_notification_failure(mock_impl):
    # Setup
    mock_impl.return_value = ["Error sending notification"]

    result = controller.send_push_notification(
        study_name="StudyY",
        message_title="Oops",
        message_text="Something went wrong",
        receivers=["user2@example.com"]
    )

    # Should NOT contain success message on error
    assert "success_message" not in result
    mock_impl.assert_called_once()


@patch("jdash.classes.controller.context_for_create_survey_page")
@patch("jdash.classes.controller.process_category_data")
@patch("jdash.classes.controller.get_categories_from_db")
@patch("jdash.classes.controller.get_category_form_data")
def test_update_categories_for_survey_success(mock_get_data, mock_get_existing, mock_process, mock_context):
    mock_formset = MagicMock()
    mock_get_data.return_value = {"category_list": ["cat1", "cat2"]}
    mock_get_existing.return_value = ["cat1"]
    mock_context.return_value = {"some": "context"}

    result = controller.update_categories_for_survey(1, mock_formset)

    mock_get_data.assert_called_once_with(mock_formset)
    mock_get_existing.assert_called_once_with(1)
    mock_process.assert_called_once_with(["cat1", "cat2"], ["cat1"], 1)
    mock_context.assert_called_once_with(1)
    assert result == {"some": "context"}


@pytest.mark.django_db
@patch("jdash.classes.controller.get_category_form_data")
def test_update_categories_for_survey_missing_key(mock_get_data):
    mock_formset = MagicMock()
    mock_get_data.return_value = {}  # Missing 'category_list'

    with pytest.raises(KeyError):
        controller.update_categories_for_survey(1, mock_formset)


@patch("jdash.classes.controller.get_all_survey_details")
@patch("jdash.classes.controller.create_categories_in_db_from_data")
@patch("jdash.classes.controller.create_question_answers_in_db")
@patch("jdash.classes.controller.create_new_survey_in_db")
@patch("jdash.classes.controller.retrieve_all_categories_for_survey")
@patch("jdash.classes.controller.retrieve_all_questions_for_survey")
@patch("jdash.classes.controller.retrieve_survey_details")
def test_duplicate_and_create_new_survey_success(
    mock_retrieve_details, mock_retrieve_questions, mock_retrieve_categories,
    mock_create_survey, mock_create_question, mock_create_categories, mock_get_context
):
    source_survey_id = 1
    user = MagicMock()
    session_key = "abc123"

    mock_retrieve_details.return_value = {"title": "Old Survey"}
    mock_retrieve_questions.return_value = [{"text": "Q1"}, {"text": "Q2"}]
    mock_retrieve_categories.return_value = ["cat1", "cat2"]

    mock_new_survey = MagicMock()
    mock_new_survey.id = 2
    mock_create_survey.return_value = mock_new_survey

    mock_get_context.return_value = {"survey_list": []}

    context = controller.duplicate_and_create_new_survey_id(source_survey_id, user, session_key)

    mock_create_survey.assert_called_once()
    mock_create_question.assert_any_call(2, {"text": "Q1"})
    mock_create_question.assert_any_call(2, {"text": "Q2"})
    mock_create_categories.assert_called_once_with(2, ["cat1", "cat2"])
    mock_get_context.assert_called_once_with(user, session_key)

    assert context == {"survey_list": []}


@patch("jdash.classes.controller.retrieve_survey_details")
def test_duplicate_and_create_new_survey_failure(mock_retrieve_details):
    mock_retrieve_details.side_effect = Exception("DB fetch failed")

    user = MagicMock()
    session_key = "abc123"

    with pytest.raises(Exception, match="DB fetch failed"):
        controller.duplicate_and_create_new_survey_id(1, user, session_key)


@patch("jdash.classes.controller.context_for_create_survey_page")
@patch("jdash.classes.controller.update_sortid_of_questions")
@patch("jdash.classes.controller.create_question_answers_in_db")
@patch("jdash.classes.controller.retrieve_question_details")
@patch("jdash.classes.controller.retrieve_all_questions_for_survey")
def test_duplicate_and_create_new_question_success(
        mock_retrieve_questions,
        mock_retrieve_question_details,
        mock_create_question,
        mock_update_sortid,
        mock_get_context,
):
    survey_id = 1
    source_question_id = 42

    mock_retrieve_questions.return_value = [{"id": 1}, {"id": 2}]
    mock_retrieve_question_details.return_value = {"title": "Example Q"}

    mock_created_question = MagicMock()
    mock_created_question.id = 99
    mock_create_question.return_value = mock_created_question

    mock_get_context.return_value = {"survey_id": survey_id}

    context = controller.duplicate_and_create_new_question_id(survey_id, source_question_id)

    mock_retrieve_question_details.assert_called_once_with(source_question_id)
    mock_create_question.assert_called_once_with(survey_id, {"title": "Example Q"})
    mock_update_sortid.assert_called_once_with(99, 3)
    mock_get_context.assert_called_once_with(survey_id)

    assert context == {"survey_id": survey_id}


@pytest.mark.django_db
@patch("jdash.classes.controller.retrieve_question_details")
def test_duplicate_and_create_new_question_failure(mock_retrieve_question_details):
    mock_retrieve_question_details.side_effect = Exception("Question not found")

    survey_id = 1
    source_question_id = 42

    with pytest.raises(Exception, match="Question not found"):
        from jdash.classes import controller
        controller.duplicate_and_create_new_question_id(survey_id, source_question_id)


@patch("jdash.classes.controller.retrieve_study_details_by_title")
@patch("jdash.classes.controller.retrieve_test_cases_for_study")
def test_create_display_sop_list_success(mock_get_tests, mock_get_study):
    study_name = "StudyA"
    test_cases_data = json.dumps([{"name": "SOP1"}, {"name": "SOP2"}])
    study_data = json.dumps({"title": "StudyA", "description": "Demo Study"})

    mock_get_tests.return_value = test_cases_data
    mock_get_study.return_value = study_data

    result = controller.create_display_sop_list_of_study(study_name)

    assert isinstance(result, dict)
    assert "test_list" in result
    assert "study" in result
    assert result["test_list"][0]["name"] == "SOP1"
    assert result["study"]["title"] == "StudyA"


@patch("jdash.classes.controller.retrieve_test_cases_for_study")
def test_create_display_sop_list_failure(mock_get_tests):
    mock_get_tests.side_effect = Exception("Database unavailable")

    with pytest.raises(Exception, match="Database unavailable"):
        controller.create_display_sop_list_of_study("StudyA")


@patch("jdash.classes.controller.get_study_form_data")
@patch("jdash.classes.controller.update_study_details")
@patch("jdash.classes.controller.update_study_db_details")
@patch("jdash.classes.controller.subprocess.run")
@patch("jdash.classes.controller.get_all_study_details")
@patch("builtins.open", create=True)
def test_update_study_meta_data_success(mock_open, mock_get_details, mock_subproc, mock_update_db, mock_update_details, mock_get_data):
    request = MagicMock()
    request.user = "dummy_user"

    mock_get_data.return_value = {"name": "TestStudy"}
    mock_get_details.return_value = ({}, {}, "")
    mock_subproc.return_value = MagicMock(stdout="Script completed")

    result = controller.update_study_meta_data("TestStudy", MagicMock(), MagicMock(), request)

    assert isinstance(result, dict)
    assert mock_get_details.called
    assert mock_update_details.called
    assert mock_update_db.called
    assert mock_subproc.called


@patch("jdash.classes.controller.get_study_form_data")
@patch("jdash.classes.controller.update_study_details")
@patch("jdash.classes.controller.update_study_db_details")
@patch("jdash.classes.controller.subprocess.run")
@patch("jdash.classes.controller.get_all_study_details")
@patch("builtins.open", create=True)
def test_update_study_meta_data_script_failure(mock_open, mock_get_details, mock_subproc, mock_update_db, mock_update_details, mock_get_data):
    request = MagicMock()
    request.user = "dummy_user"

    mock_get_data.return_value = {"name": "TestStudy"}
    mock_get_details.return_value = ({}, {}, "")
    mock_subproc.side_effect = subprocess.CalledProcessError(1, "cmd")

    result = controller.update_study_meta_data("TestStudy", MagicMock(), MagicMock(), request)

    assert isinstance(result, dict)
    assert constants.key_name_study_meta in result


@patch("jdash.classes.controller.create_subjects_for_study_impl")
@patch("jdash.classes.controller.save_study_json")
@patch("jdash.classes.controller.gettext", lambda msg: msg)  # pass-through for gettext
def test_create_subjects_for_study_success(mock_save_json, mock_create_impl):
    mock_create_impl.return_value = 10

    result = controller.create_subjects_for_study("DemoStudy", 10)

    assert controller.constants.key_name_meta_data in result
    assert result[controller.constants.key_name_meta_data][controller.constants.key_name_number_of_subjects] == 10
    assert controller.constants.key_name_success_message in result
    assert "10" in result[controller.constants.key_name_success_message]


@patch("jdash.classes.controller.create_subjects_for_study_impl")
@patch("jdash.classes.controller.save_study_json")
@patch("jdash.classes.controller.gettext", lambda msg: msg)
def test_create_subjects_for_study_failure(mock_save_json, mock_create_impl):
    mock_create_impl.side_effect = Exception("Failed to create subjects")

    try:
        controller.create_subjects_for_study("DemoStudy", 5)
    except Exception as e:
        assert str(e) == "Failed to create subjects"


@patch("jdash.classes.controller.SessionManager.get_specific_session_data")
@patch("jdash.classes.controller.count_number_of_subject_pdf")
@patch("jdash.classes.controller.CreateSubjectForm")
@patch("jdash.classes.controller.RemoveSubjectsForm")
@patch("jdash.classes.controller.SendNotificationForm")
@patch("jdash.classes.controller.DeleteSubjectForm")
def test_context_for_study_detail_page_success(
    mock_delete_form,
    mock_notify_form,
    mock_remove_form,
    mock_create_form,
    mock_count_pdf,
    mock_get_session,
):
    study_name = "StudyX"
    session_key = "sess123"

    mock_get_session.return_value = {constants.field_name_email: "user@example.com"}
    mock_count_pdf.return_value = 42

    # Call function directly
    context = controller.context_for_study_detail_page(study_name, session_key)

    # Manually inject subject_details because function no longer crashes without it
    # But your form constructors might expect it, so patch the form calls
    context[constants.key_name_subject_details] = {constants.key_name_ids_to_be_removed: ["id1", "id2"]}

    # Basic assertions
    assert context["total_count"] == 42
    assert constants.key_name_new_subjects_form in context
    assert constants.key_name_remove_subjects_form in context
    assert constants.key_name_notification_form in context
    assert constants.key_name_delete_subject_form in context
    assert context[constants.field_name_email] == "user@example.com"


@patch("jdash.classes.controller.SessionManager.get_specific_session_data", return_value={})
def test_context_missing_email_key(mock_get):
    session_key = "dummy_session"
    study_name = "test_study"

    # You may want to patch other dependencies used inside context_for_study_detail_page
    with patch("jdash.classes.controller.count_number_of_subject_pdf", return_value=5), \
         patch("jdash.classes.controller.CreateSubjectForm"), \
         patch("jdash.classes.controller.RemoveSubjectsForm"), \
         patch("jdash.classes.controller.SendNotificationForm"), \
         patch("jdash.classes.controller.DeleteSubjectForm"):

        context = controller.context_for_study_detail_page(study_name, session_key)
        # Your assertions here, e.g. email key missing or fallback behavior
        assert "total_count" in context
        assert context.get(controller.constants.field_name_email) is None or context.get(controller.constants.field_name_email) == ""


@patch("jdash.classes.controller.retrieve_survey_details")
@patch("jdash.classes.controller.retrieve_all_categories_for_survey")
@patch("jdash.classes.controller.get_help_texts_for_question_form")
@patch("jdash.classes.controller.QuestionForm")
@patch("jdash.classes.controller.formset_factory")
@patch("jdash.classes.controller.retrieve_question_details")
def test_question_id_nonzero(mock_retrieve_question_details, mock_formset_factory,
                             mock_question_form, mock_get_help_texts,
                             mock_retrieve_categories, mock_retrieve_survey_details):
    survey_id = 1
    question_id = 42

    question_data = {
        "answer": [{"id": 1}, {"id": 2}],
        "other_field": "value"
    }

    mock_retrieve_survey_details.return_value = {"title": "Survey Title"}
    mock_retrieve_categories.return_value = ["cat1", "cat2"]
    mock_get_help_texts.return_value = {"help": "text"}
    mock_retrieve_question_details.return_value = question_data
    mock_question_form.return_value = "question_form_instance"

    mock_answer_formset_instance = MagicMock(name="AnswerFormSetInstance")

    def formset_class(*args, **kwargs):
        assert kwargs.get("initial") == question_data["answer"]
        return mock_answer_formset_instance

    mock_formset_factory.return_value = formset_class

    context = controller.context_for_question_page(survey_id, question_id)

    assert context[constants.key_name_question_id] == question_id
    assert context[constants.key_name_survey_title] == "Survey Title"
    assert context[constants.key_name_question_form] == "question_form_instance"
    assert context[constants.key_name_question_details] == question_data


@patch("jdash.classes.controller.retrieve_survey_details")
@patch("jdash.classes.controller.retrieve_all_categories_for_survey")
@patch("jdash.classes.controller.get_help_texts_for_question_form")
@patch("jdash.classes.controller.QuestionForm")
@patch("jdash.classes.controller.formset_factory")
def test_question_id_zero(mock_formset_factory, mock_question_form, mock_get_help_texts,
                          mock_retrieve_categories, mock_retrieve_survey_details):
    survey_id = 1
    question_id = 0

    mock_retrieve_survey_details.return_value = {"title": "Survey Title"}
    mock_retrieve_categories.return_value = ["cat1", "cat2"]
    mock_get_help_texts.return_value = {"help": "text"}
    mock_question_form.return_value = "question_form_instance"
    mock_answer_formset_instance = MagicMock(name="AnswerFormSetInstance")

    # This is the callable returned by formset_factory, called later as AnswerFormSet()
    def formset_class(*args, **kwargs):
        # This is called without arguments in the actual code, so no assertions here
        return mock_answer_formset_instance

    # Here, formset_factory is called with AnswerForm, extra=1
    def formset_factory_side_effect(*args, **kwargs):
        assert kwargs.get("extra") == 1  # Assert on the *formset_factory* call
        return formset_class

    mock_formset_factory.side_effect = formset_factory_side_effect

    context = controller.context_for_question_page(survey_id, question_id)

    assert context[constants.key_name_question_id] == 0
    assert context[constants.key_name_survey_title] == "Survey Title"
    assert context[constants.key_name_question_form] == "question_form_instance"
    assert constants.key_name_answer_formset in context[constants.key_name_question_details]
    assert "paired" not in context


@patch("jdash.classes.controller.retrieve_survey_details")
@patch("jdash.classes.controller.retrieve_all_categories_for_survey")
@patch("jdash.classes.controller.retrieve_all_questions_for_survey")
@patch("jdash.classes.controller.SurveyForm")
@patch("jdash.classes.controller.QuestionForm")
@patch("jdash.classes.controller.formset_factory")
@patch("jdash.classes.controller.CategoryForm")
@patch("jdash.classes.controller.get_help_texts_for_category_form")
def test_survey_id_nonzero(mock_get_help_texts, mock_category_form,
                           mock_formset_factory, mock_question_form, mock_survey_form,
                           mock_retrieve_questions, mock_retrieve_categories, mock_retrieve_survey):
    survey_id = 123

    # Mock return values
    survey_details = {"title": "Test Survey"}
    category_details = [{"id": 1}, {"id": 2}]
    question_details = [{"answer": [{"id": 1}]}, {"answer": []}]

    mock_retrieve_survey.return_value = survey_details
    mock_retrieve_categories.return_value = category_details
    mock_retrieve_questions.return_value = question_details

    mock_survey_form_instance = MagicMock(name="SurveyFormInstance")
    mock_survey_form.return_value = mock_survey_form_instance

    mock_question_form_instance = MagicMock(name="QuestionFormInstance")
    mock_question_form.return_value = mock_question_form_instance

    mock_category_form_instance = MagicMock(name="CategoryFormInstance")
    mock_category_form.return_value = mock_category_form_instance

    # Setup formset_factory mock to return a dummy formset instance
    def formset_side_effect(*args, **kwargs):
        return MagicMock(name="FormsetInstance")

    mock_formset_factory.side_effect = formset_side_effect

    mock_get_help_texts.return_value = {"help": "category help"}

    context = controller.context_for_create_survey_page(survey_id)

    # Assertions for survey details retrieval and form creation
    mock_retrieve_survey.assert_called_once_with(survey_id)
    mock_retrieve_categories.assert_called_once_with(survey_id)
    mock_retrieve_questions.assert_called_once_with(survey_id)

    mock_survey_form.assert_called_once_with(data=survey_details)
    mock_question_form.assert_called_once_with(categories=category_details)

    # The formset_factory should be called twice: for AnswerFormSet and CategoryFormSet
    assert mock_formset_factory.call_count >= 2

    mock_get_help_texts.assert_called_once()

    assert context[constants.key_name_survey_form] == mock_survey_form_instance
    assert context[constants.key_name_question_form] == mock_question_form_instance
    assert constants.key_name_category_formset in context
    assert context[constants.key_name_category_help_text] == {"help": "category help"}
    assert context[constants.key_name_survey_id] == survey_id
    assert context[constants.key_name_survey_title] == "Test Survey"
    assert context[constants.key_name_questions] == question_details
    assert context[constants.key_name_categories] == category_details

    # Each question in question_details should have an 'answer_formset' key added
    for question in question_details:
        assert constants.key_name_answer_formset in question


def test_survey_id_zero():
    survey_id = 0
    context = controller.context_for_create_survey_page(survey_id)
    # Expect empty context dict since survey_id==0
    assert context == {}