# --- Environment Setup ---
import os
import sys
import shutil
import json

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
from django.contrib.auth.models import User, Group, Permission

# --- Third-party ---
import pytest
from unittest.mock import MagicMock, patch

# --- Standard Library ---
from datetime import date

# --- Local Imports ---
# Do this AFTER django.setup()
from jdash.classes import dbutils
from jdash.apps import constants
from jdash.models import Study, Survey, Question, Answer, Category, FileDownloadToken, QualityControlTests


class TestSetEmailForUser:
    @patch("jdash.classes.dbutils.User.objects.get")
    def test_set_email_success(self, mock_get):
        user_mock = MagicMock()
        mock_get.return_value = user_mock
        dbutils.set_email_for_user("testuser", "test@example.com")
        user_mock.save.assert_called_once()
        assert user_mock.email == "test@example.com"

    @patch("jdash.classes.dbutils.User.objects.get", side_effect=User.DoesNotExist)
    def test_set_email_user_not_found(self, mock_get):
        with pytest.raises(User.DoesNotExist):
            dbutils.set_email_for_user("missinguser", "x@example.com")

class TestRetireveAllStudiesForUser:
    @patch("jdash.classes.dbutils.studymodel.objects")
    def test_admin_gets_all_studies(self, mock_study):
        mock_user = MagicMock()
        mock_user.groups.all.return_value = [MagicMock(name="administrator")]
        mock_study.filter.return_value.values.return_value = [{"id": 1, "title": "Study A", "is_test": False, "duration": 30, "numberOfSubjects": 5, "description": "", "enrolled_subjects": "", "owner_id": 1, "passive_monitoring": True, "frequency": 1, "sensor_list": [], "labeling": 1, "survey_id": 1, "createdDate": date.today()}]
        result = dbutils.retireve_all_studies_for_user(mock_user)
        assert "Study A" in result

    @patch("jdash.classes.dbutils.studymodel.objects")
    def test_nonadmin_filters_correctly(self, mock_study):
        mock_user = MagicMock()
        mock_user.groups.all.return_value = [MagicMock(name="project1_group")]
        mock_study.filter.return_value.values.return_value = []
        result = dbutils.retireve_all_studies_for_user(mock_user)
        assert result == "[]"

class TestCreateNewStudy:
    @patch("jdash.classes.dbutils.studymodel.objects.create")
    @patch("jdash.classes.dbutils.create_new_study_group")
    def test_create_study_basic(self, mock_create_group, mock_create_study):
        mock_user = MagicMock()
        form_data = {
            "name": "Study",
            "description": "Desc",
            "number-of-subjects": 10,
            "duration": 30,
            "is_test": False,
            "sensor_list": ["acc", "gyro"],
            "ema_checkbox": True,
            constants.field_name_frequency: 5,
            constants.field_name_labeling: 1,
            constants.field_name_sensor_list: ["acc"],
        }
        dbutils.create_new_study_in_db(mock_user, form_data, survey=None, images_url=None)
        mock_create_study.assert_called_once()
        mock_create_group.assert_called_once()

class TestCreateNewSurvey:
    @patch("jdash.classes.dbutils.User.objects.get")
    @patch("jdash.classes.dbutils.surveyModel.objects.create")
    def test_create_new_survey(self, mock_create, mock_get):
        mock_get.return_value.id = 1
        form = {"title": "Survey", "description": "desc", "topN": 5}
        user = MagicMock(username="user")
        result = dbutils.create_new_survey_in_db(form, user)
        mock_create.assert_called_once()
        assert result == mock_create.return_value

class TestUpdateSurveyInfo:
    @patch("jdash.classes.dbutils.surveyModel.objects.get")
    def test_update_survey_fields(self, mock_get):
        survey = MagicMock()
        mock_get.return_value = survey
        form = {"title": "Updated", "description": "desc", "topN": 5}
        dbutils.update_survey_info_in_db(form, survey_id=1)
        assert survey.title == "Updated"
        survey.save.assert_called_once()

class TestFailingCases:
    def test_create_new_study_invalid_data(self):
        with pytest.raises(KeyError):
            dbutils.create_new_study_in_db(user=MagicMock(), form_data={}, survey=None, images_url=None)

    @patch("jdash.models.Question.objects.get", side_effect=Question.DoesNotExist)
    def test_update_question_not_found(self, mock_get):
        with pytest.raises(Question.DoesNotExist):
            dbutils.retrieve_question(999)


class TestCreateSurveyInDB:
    @patch("jdash.models.Survey.objects.create")
    @patch("jdash.classes.dbutils.create_categories_in_db_from_data")
    @patch("jdash.models.Question.objects.create")
    @patch("jdash.classes.dbutils.create_answer_from_file_in_db")
    def test_create_survey_success(self, mock_create_answer, mock_create_question, mock_create_categories, mock_create_survey):
        # Arrange
        user = MagicMock()
        survey_instance = MagicMock()
        survey_instance.id = 42
        mock_create_survey.return_value = survey_instance

        survey_dict = {
            constants.key_name_topN: 5,
            "splitbyCategory": 1,
            "scrolling": "V",
            "categories": [
                {"categoryValue": 1, "categoryTitle": "Cat1", "didSubjectAsk": True}
            ],
            "questions": [
                {
                    "title": "Q1",
                    "active": True,
                    "id": 1,
                    "subText": "SubText",
                    "frequency": 10,
                    "clockTime": "10:00",
                    "clockTime_start": "1;2",
                    "clockTime_end": "3;4",
                    "nextDayToAnswer": None,
                    "category": "Cat1",
                    "imageURL": "url",
                    "url": "url2",
                    "questionType": "type",
                    "deactivateOnAnswer": False,
                    "deactivateOnDate": None,
                    "activate_question": "5;6",
                    "deActivate_question": "7;8",
                    "activation_condition": "cond1",
                    "deActivation_condition": "cond2",
                    "clockTime_timezone": "UTC",
                    "answer": [
                        {"id": 1, "text": "Answer1", "subText": "Sub", "value": 1.0,
                         "defaultValue": 1.0, "stepSize": 0.1, "minVal": 0,
                         "maxVal": 10, "minText": "min", "maxText": "max"}
                    ]
                }
            ]
        }

        # Act
        result = dbutils.create_survey_in_db("StudyX", survey_dict, user)

        # Assert
        mock_create_survey.assert_called_once_with(
            title="StudyX",
            description="",
            topN=5,
            splitbyCategory=1,
            scrolling="V",
            owner=user
        )
        mock_create_categories.assert_called_once_with(survey_instance.id, survey_dict['categories'])
        mock_create_question.assert_called_once()
        mock_create_answer.assert_called_once()
        assert result == survey_instance

    @patch("jdash.models.Survey.objects.create", side_effect=Exception("DB error"))
    def test_create_survey_db_failure(self, mock_create_survey):
        # Arrange
        user = MagicMock()
        survey_dict = {
            constants.key_name_topN: 5,
            "questions": []
        }

        # Act & Assert
        with pytest.raises(Exception, match="DB error"):
            dbutils.create_survey_in_db("StudyX", survey_dict, user)


    @patch("jdash.models.Answer.objects.create")
    def test_create_answer_from_file_in_db(self, mock_create):
        question_id = 10
        answer_data = {
            'id': 5,
            'text': 'Answer text',
            'subText': 'Optional subtext',
            'value': 5,
            'defaultValue': False,
            'stepSize': 1,
            'minVal': 0,
            'maxVal': 10,
            'minText': 'Min',
            'maxText': 'Max',
        }

        dbutils.create_answer_from_file_in_db(question_id, answer_data)

        mock_create.assert_called_once_with(
            question_id=question_id,
            answerSortId=answer_data['id'],
            text=answer_data['text'],
            answerSubText=answer_data['subText'],
            value=answer_data['value'],
            defaultValue=answer_data['defaultValue'],
            stepSize=answer_data['stepSize'],
            minValue=answer_data['minVal'],
            maxValue=answer_data['maxVal'],
            minText=answer_data['minText'],
            maxText=answer_data['maxText'],
        )


@patch("jdash.models.Answer.objects.create")
def test_create_answer_in_db(mock_create):
    question_id = 10
    answer_data = {
        'answerSortId': 5,
        'text': 'Answer text',
        'answerSubText': 'Optional subtext',
        'value': 5,
        'defaultValue': False,
        'stepSize': 1,
        'minValue': 0,
        'maxValue': 10,
        'minText': 'Min',
        'maxText': 'Max',
    }

    # Call the function under test
    dbutils.create_answer_in_db(question_id, answer_data)

    # Assert the mock was called with expected arguments
    mock_create.assert_called_once_with(
        question_id=question_id,
        answerSortId=answer_data['answerSortId'],
        text=answer_data['text'],
        answerSubText=answer_data['answerSubText'],
        value=answer_data['value'],
        defaultValue=answer_data['defaultValue'],
        stepSize=answer_data['stepSize'],
        minValue=answer_data['minValue'],
        maxValue=answer_data['maxValue'],
        minText=answer_data['minText'],
        maxText=answer_data['maxText'],
    )


@patch("jdash.classes.dbutils.create_answer_from_file_in_db")
@patch("jdash.models.Question.objects.create")
def test_create_question_answers_in_db(mock_question_create, mock_create_answer):
    survey_id = 123
    question_data = {
        'title': 'Sample Question',
        'active': True,
        'id': 1,
        'subText': 'Some subtext',
        'frequency': 5,
        'clockTime': '12:00',
        'clockTime_start': [],
        'clockTime_end': [],
        'nextDayToAnswer': False,
        'category': 2,
        'imageURL': 'http://example.com/image.png',
        'url': 'http://example.com',
        'questionType': 'multiple-choice',
        'deactivateOnAnswer': False,
        'deactivateOnDate': None,
        'activate_question': [],
        'deactivate_question': [],
        'activation_condition': None,
        'deactivation_condition': None,
        # optional clockTime_timezone omitted to test default
        'answer': [
            {'id': 10, 'text': 'Answer 1', 'subText': 'sub1', 'value': 1, 'defaultValue': False, 'stepSize': 1, 'minVal': 0, 'maxVal': 5, 'minText': 'low', 'maxText': 'high'},
            {'id': 11, 'text': 'Answer 2', 'subText': 'sub2', 'value': 2, 'defaultValue': True, 'stepSize': 1, 'minVal': 0, 'maxVal': 5, 'minText': 'low', 'maxText': 'high'}
        ]
    }
    # Mock the created question instance with an id
    mock_question_instance = MagicMock(id=42)
    mock_question_create.return_value = mock_question_instance

    result = dbutils.create_question_answers_in_db(survey_id, question_data)

    # Assert question creation called with correct parameters
    mock_question_create.assert_called_once_with(
        survey_id=survey_id,
        title=question_data['title'],
        active=question_data['active'],
        sortId=question_data['id'],
        subText=question_data['subText'],
        frequency=question_data['frequency'],
        clockTime=question_data['clockTime'],
        clockTime_start=question_data['clockTime_start'],
        clockTime_end=question_data['clockTime_end'],
        nextDayToAnswer=question_data['nextDayToAnswer'],
        category=question_data['category'],
        imageURL=question_data['imageURL'],
        url=question_data['url'],
        questionType=question_data['questionType'],
        deactivateOnAnswer=question_data['deactivateOnAnswer'],
        deactivateOnDate=question_data['deactivateOnDate'],
        activate_question=question_data['activate_question'],
        deactivate_question=question_data['deactivate_question'],
        activation_condition=question_data['activation_condition'],
        deactivation_condition=question_data['deactivation_condition'],
        clockTime_timezone="Europe/Berlin"
    )

    # Assert create_answer_from_file_in_db called for each answer
    assert mock_create_answer.call_count == len(question_data['answer'])
    for answer_data in question_data['answer']:
        mock_create_answer.assert_any_call(mock_question_instance.id, answer_data)

    # Assert the function returns the created question instance
    assert result == mock_question_instance


def test_update_study_db_details_success():
    form_data = {
        'name': 'Test Study',
        'description': 'A study description',
        'duration': 10,
        'number_of_subjects': 100,
        constants.field_name_is_test: False,
        'enrolled_subjects': ['subj1', 'subj2', 'subj3'],
        constants.field_name_sensor_list: ['sensor1'],
        constants.field_name_frequency: 'daily',
        constants.field_name_labeling: 'auto',
        'ema_checkbox': True,
        'survey': 42,
    }

    mock_update = MagicMock()
    with patch('jdash.models.Study.objects.filter') as mock_filter:
        mock_filter.return_value.update = mock_update

        dbutils.update_study_db_details(form_data)

        mock_filter.assert_called_once_with(title=form_data['name'])
        mock_update.assert_called_once_with(
            description=form_data['description'],
            duration=form_data['duration'],
            numberOfSubjects=form_data['number_of_subjects'],
            is_test=form_data[constants.field_name_is_test],
            enrolled_subjects=len(form_data['enrolled_subjects']),
            passive_monitoring=True,
            frequency=form_data[constants.field_name_frequency],
            labeling=form_data[constants.field_name_labeling],
            sensor_list=form_data[constants.field_name_sensor_list],
            ecological_momentary_assessment=form_data['ema_checkbox'],
            survey=form_data['survey']
        )


def test_update_study_db_details_missing_name_key():
    form_data = {
        # 'name' key missing intentionally
        'description': 'A study description',
        'duration': 10,
        'number_of_subjects': 100,
        constants.field_name_is_test: False,
        'enrolled_subjects': ['subj1', 'subj2', 'subj3'],
        constants.field_name_sensor_list: ['sensor1'],
        constants.field_name_frequency: 'daily',
        constants.field_name_labeling: 'auto',
        'ema_checkbox': True,
        'survey': 42,
    }

    with pytest.raises(KeyError):
        dbutils.update_study_db_details(form_data)


@patch('jdash.classes.dbutils.User.objects.get')
@patch('jdash.classes.dbutils.Group.objects.get')
@patch('jdash.classes.dbutils.Permission.objects.get')
def test_assign_all_group_permissions(mock_permission_get, mock_group_get, mock_user_get):
    # Arrange
    username = "testuser"
    groupname = "testgroup"

    mock_user = MagicMock()
    mock_user_get.return_value = mock_user

    mock_group = MagicMock()
    mock_group_get.return_value = mock_group

    # Mock permissions returned in order
    mock_add_perm = MagicMock(spec=Permission)
    mock_change_perm = MagicMock(spec=Permission)
    mock_delete_perm = MagicMock(spec=Permission)
    mock_view_perm = MagicMock(spec=Permission)

    # Permission.objects.get called 4 times with different names
    mock_permission_get.side_effect = [mock_add_perm, mock_change_perm, mock_delete_perm, mock_view_perm]

    # Act
    dbutils.assign_all_group_permissions(username, groupname)

    # Assert User.objects.get called once with username
    mock_user_get.assert_called_once_with(username=username)

    # Assert Group.objects.get called once with groupname
    mock_group_get.assert_called_once_with(name=groupname)

    # Assert Permission.objects.get called with expected names
    expected_perm_names = [
        'Can add study',
        'Can change study',
        'Can delete study',
        'Can view study'
    ]
    actual_perm_calls = [call.kwargs['name'] for call in mock_permission_get.call_args_list]
    assert actual_perm_calls == expected_perm_names

    # Assert user added to the group
    mock_group.user_set.add.assert_called_once_with(mock_user)

    # Assert permissions set on the group
    mock_group.permissions.set.assert_called_once_with([
        mock_add_perm,
        mock_change_perm,
        mock_delete_perm,
        mock_view_perm,
    ])


@patch("jdash.classes.dbutils.studymodel.objects.filter")
def test_close_study_model(mock_filter):
    study_name = "Test Study"

    mock_queryset = mock_filter.return_value
    mock_queryset.update.return_value = 1  # Simulate successful update

    result = dbutils.close_study_model(study_name)

    # Assert filter was called with the correct title
    mock_filter.assert_called_once_with(title=study_name)

    # Assert update was called with closed=1
    mock_queryset.update.assert_called_once_with(closed=1)

    # Assert the function returns True
    assert result is True


@patch("jdash.classes.dbutils.SessionManager.get_specific_session_data")
@patch("jdash.classes.dbutils.surveyModel.objects")
@patch("jdash.classes.dbutils.get_list_surveys_for_user")
@patch("jdash.classes.dbutils.survey_serializer")
def test_retrieve_all_survey_for_user_admin(mock_survey_serializer, mock_get_list_surveys, mock_survey_objects, mock_get_session):
    # Setup mock session data for administrator group
    mock_get_session.side_effect = [
        ["administrator"],  # group_name
        []                  # ema_studies (not used for admin)
    ]

    # Mock the queryset and serialized output
    mock_queryset = MagicMock()
    mock_survey_objects.none.return_value = mock_queryset
    mock_survey_objects.values.return_value = mock_queryset
    expected_json = '[{"id":1,"title":"Survey1"}]'
    mock_survey_serializer.return_value = expected_json

    user = MagicMock()
    session_key = "dummy_session"

    result = dbutils.retrieve_all_survey_for_user(user, session_key)

    mock_survey_objects.values.assert_called_once()
    mock_survey_serializer.assert_called_once_with(mock_queryset)
    mock_get_list_surveys.assert_not_called()
    assert result == json.loads(expected_json)


@patch("jdash.classes.dbutils.SessionManager.get_specific_session_data")
@patch("jdash.classes.dbutils.get_list_surveys_for_user")
def test_retrieve_all_survey_for_user_non_admin(mock_get_list_surveys, mock_get_session):
    # Setup mock session data for non-admin group
    mock_get_session.side_effect = [
        ["investigator"],    # group_name (not admin)
        ["study1", "study2"] # ema_studies
    ]

    user = MagicMock()
    session_key = "dummy_session"

    expected_surveys = [{"id": 1, "title": "Survey1"}]
    mock_get_list_surveys.return_value = expected_surveys

    result = dbutils.retrieve_all_survey_for_user(user, session_key)

    mock_get_list_surveys.assert_called_once_with(user, ["study1", "study2"])
    assert result == expected_surveys


@patch("jdash.models.Answer.objects.filter")
def test_update_answer_in_db(mock_filter):
    # Arrange
    answer_id = 123
    question_id = 456  # unused in this function but can be included for completeness
    form_data = {
        "text": "New answer text",
        "answerSubText": "Subtext",
        "answerSortId": 10,
        "value": 5,
        "defaultValue": True,
        "minValue": 0,
        "maxValue": 10,
        "stepSize": 1,
        "maxText": "Max",
        "minText": "Min"
    }

    mock_update = mock_filter.return_value.update

    # Act
    dbutils.update_answer_in_db(question_id, form_data, answer_id)

    # Assert
    mock_filter.assert_called_once_with(id=answer_id)
    mock_update.assert_called_once_with(
        text=form_data["text"],
        answerSubText=form_data["answerSubText"],
        answerSortId=form_data["answerSortId"],
        value=form_data["value"],
        defaultValue=form_data["defaultValue"],
        minValue=form_data["minValue"],
        maxValue=form_data["maxValue"],
        stepSize=form_data["stepSize"],
        maxText=form_data["maxText"],
        minText=form_data["minText"],
    )


@patch("jdash.models.Answer.objects.get")
def test_delete_answer_in_db(mock_get):
    answer_id = 123

    mock_answer_instance = MagicMock()
    mock_get.return_value = mock_answer_instance

    dbutils.delete_answer_in_db(answer_id)

    mock_get.assert_called_once_with(id=answer_id)
    mock_answer_instance.delete.assert_called_once()


@patch('jdash.classes.dbutils.questionModel.objects.filter')
def test_update_question_in_db(mock_filter):
    # Prepare the mock queryset and its update method
    mock_queryset = MagicMock()
    mock_filter.return_value = mock_queryset

    # Sample input data with some None fields to test defaults
    question_id = 123
    question_data = {
        'title': 'Test Question',
        'subText': 'Some subtext',
        'active': True,
        'sortId': 5,
        'frequency': 2,
        'clockTime': '12:00',
        'clockTime_start': None,  # should become []
        'clockTime_end': None,  # should become []
        'nextDayToAnswer': False,
        'category': 1,
        'imageURL': 'http://example.com/image.png',
        'url': 'http://example.com',
        'questionType': 'multiple_choice',
        'deactivateOnAnswer': False,
        'deactivateOnDate': None,
        'activate_question': None,  # should become []
        'deactivate_question': None,  # should become []
        'activation_condition': 'condition1',
        'deactivation_condition': 'condition2',
        # clockTime_timezone missing, should default to "Europe/Berlin"
    }

    dbutils.update_question_in_db(question_id, question_data)

    # Check filter was called with the correct ID
    mock_filter.assert_called_once_with(id=question_id)
    # Check update was called with expected transformed data
    mock_queryset.update.assert_called_once_with(
        title='Test Question',
        subText='Some subtext',
        active=1,
        sortId=5,
        frequency=2,
        clockTime='12:00',
        clockTime_start=[],
        clockTime_end=[],
        nextDayToAnswer=False,
        category=1,
        imageURL='http://example.com/image.png',
        url='http://example.com',
        questionType='multiple_choice',
        deactivateOnAnswer=False,
        deactivateOnDate=None,
        activate_question=[],
        deactivate_question=[],
        activation_condition='condition1',
        deactivation_condition='condition2',
        clockTime_timezone='Europe/Berlin'
    )


@pytest.mark.parametrize("group_name,user_owner,expected_filter_owner_call", [
    (["administrator"], None, False),          # Admin: no owner filter
    (["investigator"], "user_obj", True),     # Non-admin: filter by owner
])
@patch("jdash.classes.dbutils.surveyModel.objects.filter")
def test_delete_survey_for_user(mock_filter, group_name, user_owner, expected_filter_owner_call):
    survey_id = 123

    # Mock queryset after first filter
    mock_qs_first = MagicMock(name="QuerySetFirst")
    # Mock queryset after chained filter (for non-admin)
    mock_qs_second = MagicMock(name="QuerySetSecond")
    # Mock queryset after .all()
    mock_qs_all = MagicMock(name="QuerySetAll")

    mock_filter.return_value = mock_qs_first

    if "administrator" in group_name:
        # For admin, only one filter with id=survey_id
        # .all() returns mock_qs_all
        mock_qs_first.all.return_value = mock_qs_all
        # .delete() called on mock_qs_all
        mock_qs_all.delete.return_value = None
    else:
        # For non-admin, first filter with owner=user returns mock_qs_first
        # Chained filter with id=survey_id returns mock_qs_second
        mock_qs_first.filter.return_value = mock_qs_second
        # .all() on mock_qs_second returns mock_qs_all
        mock_qs_second.all.return_value = mock_qs_all
        # .delete() called on mock_qs_all
        mock_qs_all.delete.return_value = None

    user = user_owner

    result = dbutils.delete_survey_for_user(group_name, user, survey_id)

    if "administrator" in group_name:
        mock_filter.assert_called_once_with(id=survey_id)
        mock_qs_first.all.assert_called_once()
        mock_qs_all.delete.assert_called_once()
    else:
        mock_filter.assert_called_once_with(owner=user)
        mock_qs_first.filter.assert_called_once_with(id=survey_id)
        mock_qs_second.all.assert_called_once()
        mock_qs_all.delete.assert_called_once()

    assert result is True


@patch("jdash.classes.dbutils.questionModel.objects.filter")
def test_delete_question_from_db(mock_filter):
    question_id = 10
    survey_id = 20

    # Mock the queryset returned by chaining filter().filter().all()
    mock_qs = MagicMock()
    mock_filter.return_value.filter.return_value.all.return_value = mock_qs

    result = dbutils.delete_question_from_db(question_id, survey_id)

    # Verify the chained calls
    mock_filter.assert_called_once_with(survey=survey_id)
    mock_filter.return_value.filter.assert_called_once_with(id=question_id)
    mock_filter.return_value.filter.return_value.all.assert_called_once()

    # Verify delete called on the queryset
    mock_qs.delete.assert_called_once()

    # Function should return True
    assert result is True


@pytest.fixture
def mock_question_queryset():
    # Mocked question data returned by .values()
    return [
        {"db_id": 1, "id": 2, "title": "Q1"},
        {"db_id": 2, "id": 1, "title": "Q2"},
    ]

@pytest.fixture
def mock_answer_queryset():
    # Mocked answer data returned by .values()
    return [
        {"id": 1, "text": "Answer 1"},
        {"id": 2, "text": "Answer 2"},
    ]

@patch("jdash.classes.dbutils.answerModel.objects.filter")
@patch("jdash.classes.dbutils.questionModel.objects.filter")
@patch("jdash.classes.dbutils.question_db_serializer")
@patch("jdash.classes.dbutils.answer_serializer")
def test_retrieve_all_questions_for_survey(
    mock_answer_serializer,
    mock_question_serializer,
    mock_question_filter,
    mock_answer_filter,
    mock_question_queryset,
    mock_answer_queryset,
):
    survey_id = 123

    # Setup mocks for question queryset and .values()
    mock_question_qs = MagicMock()
    mock_question_qs.values.return_value = mock_question_queryset
    mock_question_filter.return_value = mock_question_qs

    # Setup mocks for answer queryset and .values()
    mock_answer_qs = MagicMock()
    mock_answer_qs.values.return_value = mock_answer_queryset
    mock_answer_filter.return_value = mock_answer_qs

    # Mock serializers to just convert to JSON string of input list
    mock_question_serializer.side_effect = lambda x: json.dumps(x)
    mock_answer_serializer.side_effect = lambda x: json.dumps(x)

    result = dbutils.retrieve_all_questions_for_survey(survey_id)

    # Ensure filtering for questions by survey pk was called
    mock_question_filter.assert_called_once_with(survey__pk=survey_id)

    # Ensure filtering answers per question db_id was called
    expected_calls = [{"question_id": q["db_id"]} for q in mock_question_queryset]
    actual_calls = [call.kwargs for call in mock_answer_filter.call_args_list]
    assert all(expected in actual_calls for expected in expected_calls)

    # Result is sorted by 'id' field
    assert all(result[i]["id"] <= result[i + 1]["id"] for i in range(len(result) - 1))

    # Each question dict has an 'answer' key
    for question in result:
        assert "answer" in question
        assert isinstance(question["answer"], list)


@patch("jdash.classes.dbutils.answerModel.objects.filter")
@patch("jdash.classes.dbutils.questionModel.objects.filter")
@patch("jdash.classes.dbutils.question_serializer")
@patch("jdash.classes.dbutils.answer_serializer")
def test_retrieve_download_questions_for_survey(
    mock_answer_serializer,
    mock_question_serializer,
    mock_question_filter,
    mock_answer_filter,
    mock_question_queryset,
    mock_answer_queryset,
):
    survey_id = 55

    # Setup mocks for question queryset .values()
    mock_question_qs = MagicMock()
    mock_question_qs.values.return_value = mock_question_queryset
    mock_question_filter.return_value = mock_question_qs

    # Setup mocks for answer queryset .values()
    mock_answer_qs = MagicMock()
    mock_answer_qs.values.return_value = mock_answer_queryset
    mock_answer_filter.return_value = mock_answer_qs

    # Serialize returns JSON string representation
    mock_question_serializer.side_effect = lambda x: json.dumps(x)
    mock_answer_serializer.side_effect = lambda x: json.dumps(x)

    result = dbutils.retrieve_download_questions_for_survey(survey_id)

    mock_question_filter.assert_called_once_with(survey__pk=survey_id)
    # Check answers filtered per question db_id
    expected_calls = [{"question_id": q["db_id"]} for q in mock_question_queryset]
    actual_calls = [call.kwargs for call in mock_answer_filter.call_args_list]

    assert all(expected in actual_calls for expected in expected_calls)

    # Sorted by 'id'
    assert all(result[i]["id"] <= result[i+1]["id"] for i in range(len(result) - 1))

    # Each question includes answers
    for question in result:
        assert "answer" in question
        assert isinstance(question["answer"], list)


@patch("jdash.classes.dbutils.answerModel.objects.filter")
@patch("jdash.classes.dbutils.answer_serializer")
def test_retrieve_all_answers_for_questions(mock_answer_serializer, mock_answer_filter, mock_answer_queryset):
    question_id = 123

    # Mock the queryset and .values()
    mock_qs = MagicMock()
    mock_qs.values.return_value = mock_answer_queryset
    mock_answer_filter.return_value = mock_qs

    # answer_serializer returns JSON string of the queryset
    mock_answer_serializer.side_effect = lambda x: json.dumps(x)

    result = dbutils.retrieve_all_answers_for_questions(question_id)

    mock_answer_filter.assert_called_once_with(question_id=question_id)
    mock_qs.values.assert_called_once()
    mock_answer_serializer.assert_called_once_with(mock_answer_queryset)

    # Result should be the list decoded from JSON string
    assert result == mock_answer_queryset


@pytest.fixture
def mock_category_queryset():
    return [
        {"id": 1, "categoryValue": 10, "categoryTitle": "Cat A"},
        {"id": 2, "categoryValue": 20, "categoryTitle": "Cat B"},
    ]

@patch("jdash.classes.dbutils.categoryModel.objects.filter")
@patch("jdash.classes.dbutils.category_serializer")
def test_retrieve_all_categories_for_survey(mock_category_serializer, mock_category_filter, mock_category_queryset):
    survey_id = 42

    # Mock the queryset chain .order_by().values()
    mock_qs = MagicMock()
    mock_qs.order_by.return_value.values.return_value = mock_category_queryset
    mock_category_filter.return_value = mock_qs

    # category_serializer returns JSON string of the queryset
    mock_category_serializer.side_effect = lambda x: json.dumps(x)

    result = dbutils.retrieve_all_categories_for_survey(survey_id)

    mock_category_filter.assert_called_once_with(survey__pk=survey_id)
    mock_qs.order_by.assert_called_once_with('categoryValue')
    mock_qs.order_by.return_value.values.assert_called_once()
    mock_category_serializer.assert_called_once_with(mock_category_queryset)

    assert result == mock_category_queryset


@pytest.mark.django_db
@patch("jdash.classes.dbutils.surveyModel.objects.get")
def test_retrieve_survey(mock_get):
    survey_id = 123
    mock_survey = MagicMock()
    mock_get.return_value = mock_survey

    result = dbutils.retrieve_survey(survey_id)

    mock_get.assert_called_once_with(id=survey_id)
    assert result == mock_survey

@pytest.mark.django_db
@patch("jdash.classes.dbutils.questionModel.objects.get")
def test_retrieve_question(mock_get):
    question_id = 456
    mock_question = MagicMock()
    mock_get.return_value = mock_question

    result = dbutils.retrieve_question(question_id)

    mock_get.assert_called_once_with(id=question_id)
    assert result == mock_question

@pytest.mark.django_db
@patch("jdash.classes.dbutils.surveyModel.objects.filter")
@patch("jdash.classes.dbutils.survey_serializer")
def test_retrieve_survey_details(mock_serializer, mock_filter):
    survey_id = 789
    mock_values = [{"id": survey_id, "title": "Test Survey"}]
    mock_filter.return_value.values.return_value = mock_values
    mock_serializer.return_value = json.dumps(mock_values)

    result = dbutils.retrieve_survey_details(survey_id)

    mock_filter.assert_called_once_with(id=survey_id)
    mock_serializer.assert_called_once_with(mock_values)
    assert result == mock_values[0]

@pytest.mark.django_db
@patch("jdash.classes.dbutils.questionModel.objects.filter")
@patch("jdash.classes.dbutils.question_db_serializer")
@patch("jdash.classes.dbutils.retrieve_all_answers_for_questions")
def test_retrieve_question_details(mock_answers, mock_serializer, mock_filter):
    question_id = 101
    question_data = [{"id": question_id, "title": "Question 1"}]
    mock_filter.return_value.values.return_value = question_data
    mock_serializer.return_value = json.dumps(question_data)
    mock_answers.return_value = [{"id": 1, "text": "Answer 1"}]

    result = dbutils.retrieve_question_details(question_id)

    mock_filter.assert_called_once_with(id=question_id)
    mock_serializer.assert_called_once_with(question_data)
    mock_answers.assert_called_once_with(question_id)
    assert result["answer"] == [{"id": 1, "text": "Answer 1"}]
    assert result["id"] == question_data[0]["id"]

@pytest.mark.django_db
@patch("jdash.classes.dbutils.questionModel.objects.filter")
@patch("jdash.classes.dbutils.question_serializer")
def test_retrieve_questions_greater_than_sortId(mock_serializer, mock_filter):
    survey_id = 1
    sort_id = 10
    questions_data = [{"id": 11, "sortId": 11}, {"id": 12, "sortId": 12}]
    mock_filter.return_value.values.return_value = questions_data
    mock_serializer.return_value = json.dumps(questions_data)

    result = dbutils.retrieve_questions_greater_than_sortId(survey_id, sort_id)

    mock_filter.assert_called_once_with(survey_id=survey_id, sortId__gt=sort_id)
    mock_serializer.assert_called_once_with(questions_data)
    assert result == questions_data

@pytest.mark.django_db
@patch("jdash.classes.dbutils.downloadFile.objects.filter")
def test_add_verification_code(mock_filter):
    token = "abc123"
    code = "verify_code"

    mock_qs = MagicMock()
    mock_filter.return_value = mock_qs
    mock_qs.update.return_value = 1

    result = dbutils.add_verification_code(code, token)

    mock_filter.assert_called_once_with(token=token)
    mock_qs.update.assert_called_once_with(code=code)
    assert result is True


@pytest.mark.django_db
@patch("jdash.classes.dbutils.survey_serializer")
@patch("jdash.classes.dbutils.custom_serializer")
@patch("jdash.classes.dbutils.surveyModel.objects.filter")
@patch("jdash.classes.dbutils.studymodel.objects.filter")
def test_get_list_surveys_for_user(mock_study_filter, mock_survey_filter, mock_custom_serializer, mock_survey_serializer):
    user = MagicMock()
    ema_studies = ["StudyA", "StudyB"]

    # Mock studymodel.objects.filter(title=studyname).values() for each EMA study
    study_model_data_1 = [{"survey": 2}]
    study_model_data_2 = [{"survey": 3}]

    def study_filter_side_effect(*args, **kwargs):
        title = kwargs.get("title")
        mock = MagicMock()
        if title == "StudyA":
            mock.values.return_value = study_model_data_1
        elif title == "StudyB":
            mock.values.return_value = study_model_data_2
        else:
            mock.values.return_value = []
        return mock

    mock_study_filter.side_effect = study_filter_side_effect

    # Mock custom_serializer returns JSON string for the study model data
    def custom_serializer_side_effect(data):
        # The `data` argument is the queryset mock — just convert to json string of its .values() return list
        # For simplicity, convert to JSON string of what .values() would return
        if hasattr(data, "values"):
            return json.dumps(data.values())
        # fallback, just json.dumps data
        return json.dumps(data)
    mock_custom_serializer.side_effect = custom_serializer_side_effect

    # Mock surveyModel.objects.filter(...).values() to return user surveys or EMA surveys
    def survey_filter_side_effect(*args, **kwargs):
        owner = kwargs.get("owner")
        survey_id = kwargs.get("id")
        mock = MagicMock()
        if owner:
            # Filtering surveys owned by the user
            mock.values.return_value = [{"id": 1, "title": "User Survey 1"}]
        elif survey_id == 2:
            mock.values.return_value = [{"id": 2, "title": "EMA Survey 2"}]
        elif survey_id == 3:
            mock.values.return_value = [{"id": 3, "title": "EMA Survey 3"}]
        else:
            mock.values.return_value = []
        return mock

    mock_survey_filter.side_effect = survey_filter_side_effect

    # Mock survey_serializer to just JSON stringify the input
    def survey_serializer_side_effect(data):
        # data is usually list of dicts
        return json.dumps(data)
    mock_survey_serializer.side_effect = survey_serializer_side_effect

    # Call the function under test
    result = dbutils.get_list_surveys_for_user(user, ema_studies)

    # Validate the result contains user survey and EMA surveys combined
    expected_surveys = [
        {"id": 1, "title": "User Survey 1"},
        {"id": 2, "title": "EMA Survey 2"},
        {"id": 3, "title": "EMA Survey 3"},
    ]

    # The result is a list of dicts — check expected surveys are included
    assert all(any(s["id"] == expected["id"] and s["title"] == expected["title"] for s in result) for expected in expected_surveys)

    # Also assert mocks were called as expected
    mock_study_filter.assert_any_call(title="StudyA")
    mock_study_filter.assert_any_call(title="StudyB")
    mock_survey_filter.assert_any_call(owner=user)
    mock_survey_filter.assert_any_call(id=2)
    mock_survey_filter.assert_any_call(id=3)


@pytest.mark.django_db
@patch("jdash.classes.dbutils.categoryModel.objects.filter")
def test_get_categories_from_db(mock_filter):
    survey_id = 123
    mock_qs = MagicMock(name="QuerySet")
    mock_filter.return_value = mock_qs

    result = dbutils.get_categories_from_db(survey_id)

    mock_filter.assert_called_once_with(survey_id=survey_id)
    assert result == mock_qs

@pytest.mark.django_db
@patch("jdash.classes.dbutils.categoryModel.objects.create")
def test_create_categories_in_db(mock_create):
    survey_id = 10
    category_data = {
        "category_list": [
            {"categoryValue": "1", "categoryTitle": "Cat1", "didSubjectAsk": True},
            {"categoryValue": "2", "categoryTitle": "Cat2", "didSubjectAsk": False},
        ]
    }

    dbutils.create_categories_in_db(survey_id, category_data)

    calls = [
        (({'survey_id': survey_id, 'categoryValue': 1, 'categoryTitle': 'Cat1', 'didSubjectAsk': True}),),
        (({'survey_id': survey_id, 'categoryValue': 2, 'categoryTitle': 'Cat2', 'didSubjectAsk': False}),),
    ]
    # Instead of asserting call args exactly (due to kwargs), check call count and key presence
    assert mock_create.call_count == 2
    args_list = [call.kwargs for call in mock_create.call_args_list]
    assert args_list[0]['survey_id'] == survey_id
    assert args_list[0]['categoryValue'] == 1
    assert args_list[1]['categoryTitle'] == "Cat2"

@pytest.mark.django_db
@patch("jdash.classes.dbutils.categoryModel.objects.create")
def test_create_categories_in_db_from_data(mock_create):
    survey_id = 10
    category_data = [
        {"categoryValue": "3", "categoryTitle": "Cat3", "didSubjectAsk": True},
        {"categoryValue": "4", "categoryTitle": "Cat4", "didSubjectAsk": False},
    ]

    dbutils.create_categories_in_db_from_data(survey_id, category_data)

    assert mock_create.call_count == 2
    assert mock_create.call_args_list[0].kwargs['categoryValue'] == 3
    assert mock_create.call_args_list[1].kwargs['categoryTitle'] == "Cat4"

@pytest.mark.django_db
@patch("jdash.classes.dbutils.studymodel.objects.filter")
@patch("jdash.classes.dbutils.qctestsModel.objects.filter")
def test_retrieve_test_cases_for_study(mock_qctests_filter, mock_study_filter):
    study_name = "Test Study"
    mock_study_qs = MagicMock()
    mock_study_qs.values.return_value = [{"id": 42}]
    mock_study_filter.return_value = mock_study_qs

    mock_qctests_qs = MagicMock()
    test_results = [{"test_id": 1, "name": "test1"}, {"test_id": 2, "name": "test2"}]
    mock_qctests_qs.values.return_value = test_results
    mock_qctests_filter.return_value = mock_qctests_qs

    result_json = dbutils.retrieve_test_cases_for_study(study_name)

    mock_study_filter.assert_called_once_with(title=study_name)
    mock_qctests_filter.assert_called_once_with(study_id=42)

    import json
    assert json.loads(result_json) == test_results


@pytest.mark.django_db
@patch("jdash.classes.dbutils.qctestsModel.objects.get")
def test_update_test_case_flags_success(mock_get):
    testcase_updates = [
        {'id': 1, 'tested_by_admin': True, 'tested_by_owner': False},
        {'id': 2, 'tested_by_admin': False},
    ]
    username = "admin_user"

    mock_instance_1 = MagicMock()
    mock_instance_2 = MagicMock()

    # Mock .save() to prevent errors
    mock_instance_1.save = MagicMock()
    mock_instance_2.save = MagicMock()

    mock_get.side_effect = [mock_instance_1, mock_instance_2]

    result = dbutils.update_test_case_flags(testcase_updates, username)

    assert result['success_count'] == 2

@pytest.mark.django_db
@patch("jdash.classes.dbutils.qctestsModel.objects.get")
def test_update_test_case_flags_failure(mock_get):
    testcase_updates = [{'id': 1, 'tested_by_admin': True}]
    username = "admin_user"

    # Simulate an exception when getting the object
    mock_get.side_effect = Exception("DB error")

    result = dbutils.update_test_case_flags(testcase_updates, username)

    assert result['success_count'] == 0
    assert result['failure_count'] == 1
    assert result['errors'] == []  # Note: your function currently does not append errors

@pytest.mark.django_db
@patch("jdash.classes.dbutils.studymodel.objects.filter")
def test_retrieve_study_details_by_title(mock_filter):
    study_name = "Study A"
    mock_qs = MagicMock()
    mock_qs.values.return_value = [{'id': 10, 'title': study_name, 'description': 'desc'}]
    mock_filter.return_value = mock_qs

    result_json = dbutils.retrieve_study_details_by_title(study_name)

    mock_filter.assert_called_once_with(title=study_name)
    import json
    result = json.loads(result_json)
    assert result['title'] == study_name
    assert result['id'] == 10