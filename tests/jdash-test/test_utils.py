import pytest
from unittest.mock import patch, MagicMock
from jdash.apps import constants
from jdash.classes import utils
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from jdash.interface.session_manager import SessionManager
from jdash.models import Study, Survey, Category, Question, Answer, FileDownloadToken, QualityControlTests
import json
import uuid
from django.utils import timezone


@pytest.mark.django_db
def test_set_email_for_user_case1():
    # Setup: Create user
    user = User.objects.create_user(username='testuser', email='old@example.com', password='password123')

    # Action: Change email
    new_email = 'new@example.com'
    utils.set_email_for_user('testuser', new_email)

    # Assert: Verify the email was updated
    user.refresh_from_db()
    assert user.email == new_email


@pytest.mark.django_db
def test_set_email_for_user_case2_invalid_username():
    with pytest.raises(User.DoesNotExist):
        utils.set_email_for_user('nonexistentuser', 'new@example.com')


@pytest.mark.django_db
def test_retrieve_all_studies_for_user_admin():
    # Create user and admin group
    user = User.objects.create_user(username='admin', password='pass')
    admin_group = Group.objects.create(name='administrator')
    user.groups.add(admin_group)

    # Create some studies
    Study.objects.create(title="Study A", closed=False, is_test=False, owner=user)
    Study.objects.create(title="Study B", closed=False, is_test=False, owner=user)
    Study.objects.create(title="Study Closed", closed=True, is_test=False, owner=user)

    # Call the function
    result = json.loads(utils.retrieve_all_studies_for_user(user))

    # Assert: Only non-closed studies are returned
    titles = [study["title"] for study in result]
    assert "Study A" in titles
    assert "Study B" in titles
    assert "Study Closed" not in titles

@pytest.mark.django_db
def test_retrieve_all_studies_for_user_non_admin():
    # Create user and group
    user = User.objects.create_user(username='invuser', password='pass')
    group = Group.objects.create(name='CoolStudy_group')
    user.groups.add(group)

    # Create studies
    Study.objects.create(title="CoolStudy_01", closed=False, is_test=False, owner=user)
    Study.objects.create(title="OtherStudy_01", closed=False, is_test=False, owner=user)
    Study.objects.create(title="CoolStudy_02", closed=True, is_test=False, owner=user)

    # Call the function
    result = json.loads(utils.retrieve_all_studies_for_user(user))

    # Assert: Only matching open studies returned
    titles = [study["title"] for study in result]
    assert "CoolStudy_01" in titles
    assert "OtherStudy_01" not in titles
    assert "CoolStudy_02" not in titles

@pytest.mark.django_db
def test_custom_serializer_valid_queryset():
    user = User.objects.create_user(username='testuser', password='pass')
    study = Study.objects.create(
        title='Study A',
        is_test=False,
        duration=30,
        numberOfSubjects=10,
        description='A test study',
        enrolled_subjects="005",
        owner=user,
        passive_monitoring=True,
        frequency=100,
        sensor_list='accel,gyro',
        labeling=1,
        survey=None
    )
    queryset = Study.objects.filter(id=study.id).values()

    result = utils.custom_serializer(queryset)
    data = json.loads(result)

    assert isinstance(data, list)
    assert data[0]["title"] == 'Study A'
    assert data[0]["numberOfSubjects"] == 10

def test_custom_serializer_empty_queryset():
    empty_queryset = Study.objects.none().values()
    result = utils.custom_serializer(empty_queryset)
    data = json.loads(result)

    assert data == []

@pytest.mark.django_db
def test_get_group_name_for_user_mapped_group():
    user = User.objects.create(username="investigator_user")
    group = Group.objects.create(name="Investigator")
    user.groups.add(group)

    group_name = utils.get_group_name_for_user(user)
    assert group_name == "Investigator"


@pytest.mark.django_db
def test_get_group_name_for_user_default_group():
    user = User.objects.create(username="random_user")
    group = Group.objects.create(name="SomeRandomGroup")
    user.groups.add(group)

    group_name = utils.get_group_name_for_user(user)
    assert group_name == constants.default_group  # Should fall back to "Viewer"

@pytest.mark.django_db
def test_create_new_study_in_db_success():
    user = User.objects.create(username="creator")
    survey = Survey.objects.create(title="Test Survey", description="desc", topN=3, owner=user)
    form_data = {
        "name": "Study A",
        "description": "A test study",
        "number-of-subjects": 10,
        "duration": 30,
        "is_test": False,
        "frequency": 50,
        "active_labeling": 1,
        "sensor_list": ["accelerometer"]
    }
    images_url = "/path/to/image"

    utils.create_new_study_in_db(user, form_data, survey, images_url)

    study = Study.objects.get(title="Study A")
    assert study.owner == user
    assert study.survey == survey
    assert study.passive_monitoring is True
    assert study.images == images_url


@pytest.mark.django_db
def test_create_new_study_in_db_missing_fields():
    user = User.objects.create(username="creator")
    survey = Survey.objects.create(title="Another Survey", description="", topN=1, owner=user)

    # Missing 'number-of-subjects'
    form_data = {
        "name": "Study B",
        "description": "Missing field test",
        "duration": 20,
        "is_test": True,
        "frequency": 100,
        "active_labeling": 0,
        "sensor_list": []
    }

    with pytest.raises(KeyError):
        utils.create_new_study_in_db(user, form_data, survey, "/img/path")

@pytest.mark.django_db
def test_create_new_survey_in_db_success():
    user = User.objects.create_user(username="testuser", password="pass")
    form = {
        "title": "Test Survey",
        "description": "A description",
        "topN": 5,
        "splitbyCategory": 1,
        "scrolling": "V"
    }

    survey = utils.create_new_survey_in_db(form, user)

    assert isinstance(survey, Survey)
    assert survey.title == "Test Survey"
    assert survey.description == "A description"
    assert survey.topN == 5
    assert survey.splitbyCategory == 1
    assert survey.scrolling == "V"
    assert survey.owner == user


@pytest.mark.django_db
def test_create_new_survey_in_db_missing_required_field():
    user = User.objects.create_user(username="testuser2", password="pass")
    # Missing 'title' in the form data
    form = {
        "description": "Missing title",
        "topN": 3
    }

    with pytest.raises(KeyError):
        utils.create_new_survey_in_db(form, user)

@pytest.mark.django_db
def test_update_survey_info_in_db_success():
    user = User.objects.create_user(username="editor", password="pass")
    survey = Survey.objects.create(
        title="Initial Title",
        description="Initial description",
        topN=2,
        owner=user
    )

    form = {
        "title": "Updated Title",
        "description": "Updated description",
        "topN": 7,
        "splitbyCategory": 1,
        "scrolling": "V"
    }

    updated = utils.update_survey_info_in_db(form, survey.id)

    assert updated.title == "Updated Title"
    assert updated.description == "Updated description"
    assert updated.topN == 7
    assert updated.splitbyCategory == 1
    assert updated.scrolling == "V"


@pytest.mark.django_db
def test_update_survey_info_in_db_invalid_id():
    form = {
        "title": "Title",
        "description": "Desc",
        "topN": 1
    }

    with pytest.raises(Survey.DoesNotExist):
        utils.update_survey_info_in_db(form, survey_id=9999)

@pytest.mark.django_db
def test_create_survey_in_db_success():
    user = User.objects.create_user(username="creator", password="secure")
    survey_dict = {
        "topN": 5,
        "splitbyCategory": 1,
        "scrolling": "V",
        "categories": [
            {"categoryTitle": "Mood", "categoryValue": 1, "didSubjectAsk": True}
        ],
        "questions": []
    }

    survey = utils.create_survey_in_db("New Survey", survey_dict, user)

    assert survey.title == "New Survey"
    assert survey.owner == user
    assert survey.topN == 5
    assert survey.splitbyCategory == 1
    assert survey.scrolling == "V"

    categories = Category.objects.filter(survey_id=survey.id)
    assert categories.count() == 1
    assert categories.first().categoryTitle == "Mood"


@pytest.mark.django_db
def test_create_survey_in_db_missing_topN():
    user = User.objects.create_user(username="creator", password="secure")
    survey_dict = {
        # Missing 'topN'
        "questions": []
    }

    with pytest.raises(KeyError):
        utils.create_survey_in_db("Bad Survey", survey_dict, user)

@pytest.mark.django_db
def test_create_answer_from_file_in_db_success():
    user = User.objects.create_user(username="owner", password="pwd")
    survey = Survey.objects.create(title="Test Survey", description="desc", topN=3, scrolling="H", owner=user)
    question = Question.objects.create(
        survey=survey,
        title="Q1",
        active=True,
        sortId=1,
        subText="sub",
        frequency=1,
        clockTime=600,
        clockTime_start=[],
        clockTime_end=[],
        nextDayToAnswer=0,
        category=1,
        imageURL="",
        url="",
        questionType=1,
        deactivateOnAnswer=False,
        deactivateOnDate=0,
        activate_question=[],
        deactivate_question=[],
        activation_condition="",
        deactivation_condition="",
        clockTime_timezone="Europe/Berlin"
    )

    answer_data = {
        "id": 1,
        "text": "Yes",
        "subText": "Agree",
        "value": 1,
        "defaultValue": 0,
        "stepSize": 1,
        "minVal": 0,
        "maxVal": 5,
        "minText": "Low",
        "maxText": "High"
    }

    utils.create_answer_from_file_in_db(question.id, answer_data)

    answer = Answer.objects.get(question=question)
    assert answer.text == "Yes"
    assert answer.answerSubText == "Agree"
    assert answer.value == 1


@pytest.mark.django_db
def test_create_answer_from_file_in_db_missing_required_field():
    user = User.objects.create_user(username="owner", password="pwd")
    survey = Survey.objects.create(title="Test Survey", description="desc", topN=3, scrolling="H", owner=user)
    question = Question.objects.create(
        survey=survey,
        title="Q1",
        active=True,
        sortId=1,
        subText="sub",
        frequency=1,
        clockTime=600,
        clockTime_start=[],
        clockTime_end=[],
        nextDayToAnswer=0,
        category=1,
        imageURL="",
        url="",
        questionType=1,
        deactivateOnAnswer=False,
        deactivateOnDate=0,
        activate_question=[],
        deactivate_question=[],
        activation_condition="",
        deactivation_condition="",
        clockTime_timezone="Europe/Berlin"
    )

    incomplete_data = {
        # Missing 'text'
        "id": 1,
        "value": 1,
        "defaultValue": 0,
        "stepSize": 1,
        "minVal": 0,
        "maxVal": 5,
        "minText": "Low",
        "maxText": "High"
    }

    with pytest.raises(KeyError):
        utils.create_answer_from_file_in_db(question.id, incomplete_data)

@pytest.mark.django_db
def test_create_answer_in_db_success():
    user = User.objects.create_user(username="testuser", password="pass")
    survey = Survey.objects.create(title="My Survey", description="Test desc", topN=5, scrolling="H", owner=user)
    question = Question.objects.create(
        survey=survey,
        title="Q1",
        active=True,
        sortId=1,
        subText="subtitle",
        frequency=1,
        clockTime=780,
        clockTime_start=[],
        clockTime_end=[],
        nextDayToAnswer=1,
        category=1,
        imageURL="",
        url="",
        questionType=1,
        deactivateOnAnswer=False,
        deactivateOnDate=0,
        activate_question=[],
        deactivate_question=[],
        activation_condition="",
        deactivation_condition="",
        clockTime_timezone="Europe/Berlin"
    )

    answer_data = {
        "answerSortId": 1,
        "text": "Yes",
        "answerSubText": "Definitely yes",
        "value": 5,
        "defaultValue": 1,
        "stepSize": 1,
        "minValue": 0,
        "maxValue": 5,
        "minText": "No",
        "maxText": "Yes"
    }

    utils.create_answer_in_db(question.id, answer_data)

    answer = Answer.objects.get(question_id=question.id)
    assert answer.text == "Yes"
    assert answer.answerSortId == 1
    assert answer.defaultValue == 1


@pytest.mark.django_db
def test_create_answer_in_db_missing_field():
    user = User.objects.create_user(username="testuser2", password="pass")
    survey = Survey.objects.create(title="Survey 2", description="Desc", topN=3, scrolling="V", owner=user)
    question = Question.objects.create(
        survey=survey,
        title="Q2",
        active=True,
        sortId=2,
        subText="subtitle",
        frequency=2,
        clockTime=780,
        clockTime_start=[],
        clockTime_end=[],
        nextDayToAnswer=2,
        category=2,
        imageURL="",
        url="",
        questionType=2,
        deactivateOnAnswer=True,
        deactivateOnDate=0,
        activate_question=[],
        deactivate_question=[],
        activation_condition="",
        deactivation_condition="",
        clockTime_timezone="Europe/Berlin"
    )

    # Missing required field 'text'
    incomplete_answer_data = {
        "answerSortId": 2,
        "answerSubText": "Maybe",
        "value": 2,
        "defaultValue": 0,
        "stepSize": 1,
        "minValue": 0,
        "maxValue": 5,
        "minText": "No",
        "maxText": "Yes"
    }

    with pytest.raises(KeyError):
        utils.create_answer_in_db(question.id, incomplete_answer_data)

@pytest.mark.django_db
def test_create_question_answers_in_db_success():
    user = User.objects.create_user(username="survey_owner", password="password")
    survey = Survey.objects.create(title="Survey QA", description="Survey for QA", topN=5, scrolling="H", owner=user)

    question_data = {
        "title": "How are you?",
        "active": True,
        "id": 1,
        "subText": "Please rate your current state.",
        "frequency": 1,
        "clockTime": 720,
        "clockTime_start": [],
        "clockTime_end": [],
        "nextDayToAnswer": 0,
        "category": 3,
        "imageURL": "",
        "url": "",
        "questionType": 1,
        "deactivateOnAnswer": False,
        "deactivateOnDate": 0,
        "activate_question": [],
        "deactivate_question": [],
        "activation_condition": "",
        "deactivation_condition": "",
        "clockTime_timezone": "Europe/Berlin",
        "answer": [
            {
                "id": 1,
                "text": "Good",
                "subText": "Feeling good",
                "value": 1,
                "defaultValue": 0,
                "stepSize": 1,
                "minVal": 0,
                "maxVal": 2,
                "minText": "Bad",
                "maxText": "Great"
            }
        ]
    }

    question = utils.create_question_answers_in_db(survey.id, question_data)

    assert Question.objects.filter(id=question.id).exists()
    assert Answer.objects.filter(question=question).count() == 1


@pytest.mark.django_db
def test_create_question_answers_in_db_missing_field():
    user = User.objects.create_user(username="survey_owner2", password="password")
    survey = Survey.objects.create(title="Survey QA 2", description="Survey with error", topN=3, scrolling="V", owner=user)

    question_data = {
        # Missing 'title'
        "active": True,
        "id": 2,
        "subText": "Missing title test",
        "frequency": 1,
        "clockTime": 780,
        "clockTime_start": [],
        "clockTime_end": [],
        "nextDayToAnswer": 0,
        "category": 3,
        "imageURL": "",
        "url": "",
        "questionType": 1,
        "deactivateOnAnswer": False,
        "deactivateOnDate": 0,
        "activate_question": [],
        "deactivate_question": [],
        "activation_condition": "",
        "deactivation_condition": "",
        "clockTime_timezone": "Europe/Berlin",
        "answer": []
    }

    with pytest.raises(KeyError):
        utils.create_question_answers_in_db(survey.id, question_data)

@pytest.mark.django_db
def test_update_study_db_details_success():
    user = User.objects.create_user(username="study_owner", password="password")
    survey = Survey.objects.create(title="Base Survey", description="base", topN=3, scrolling="H", owner=user)

    study = Study.objects.create(
        title="Test Study",
        description="Old description",
        duration=10,
        numberOfSubjects=5,
        is_test=False,
        enrolled_subjects="0",
        owner=user,
        passive_monitoring=False,
        frequency=50,
        labeling=0,
        sensor_list=[],
        ecological_momentary_assessment=False,
        survey=None
    )

    form_data = {
        'name': 'Test Study',
        'description': 'Updated description',
        'duration': 30,
        'number_of_subjects': 10,
        constants.field_name_is_test: True,
        'enrolled_subjects': [1, 2, 3],
        constants.field_name_sensor_list: ['ACC'],
        constants.field_name_frequency: 50,
        constants.field_name_labeling: 0,
        'ema_checkbox': True,
        'survey': survey.id
    }

    utils.update_study_db_details(form_data)
    study.refresh_from_db()

    assert study.description == 'Updated description'
    assert study.duration == 30
    assert study.is_test is True
    assert study.enrolled_subjects == '3'
    assert study.passive_monitoring is True
    assert study.survey == survey


@pytest.mark.django_db
def test_update_study_db_details_invalid_key():
    user = User.objects.create_user(username="study_owner2", password="password")
    Study.objects.create(
        title="Another Study",
        description="Initial",
        duration=15,
        numberOfSubjects=5,
        is_test=False,
        enrolled_subjects="0",
        owner=user,
        passive_monitoring=False,
        frequency=50,
        labeling=0,
        sensor_list=[],
        ecological_momentary_assessment=False,
        survey=None
    )

    invalid_data = {
        'name': 'Another Study',
        'description': 'Fails update',
        'duration': 20,
        # Missing required keys like 'number_of_subjects', 'enrolled_subjects', etc.
    }

    with pytest.raises(KeyError):
        utils.update_study_db_details(invalid_data)

@pytest.mark.django_db
def test_assign_all_group_permissions_success():
    user = User.objects.create_user(username="perm_user", password="testpass")
    group = Group.objects.create(name="test_group")

    # Create permissions manually for Study model
    content_type = ContentType.objects.get_for_model(Study)
    Permission.objects.get_or_create(codename='add_study', name='Can add study', content_type=content_type)
    Permission.objects.get_or_create(codename='change_study', name='Can change study', content_type=content_type)
    Permission.objects.get_or_create(codename='delete_study', name='Can delete study', content_type=content_type)
    Permission.objects.get_or_create(codename='view_study', name='Can view study', content_type=content_type)

    utils.assign_all_group_permissions(user.username, group.name)

    user.refresh_from_db()
    group.refresh_from_db()

    # Check group membership
    assert group in user.groups.all()

    # Check permissions
    perms = set(group.permissions.values_list("name", flat=True))
    assert "Can add study" in perms
    assert "Can change study" in perms
    assert "Can delete study" in perms
    assert "Can view study" in perms


@pytest.mark.django_db
def test_assign_all_group_permissions_missing_permission():
    user = User.objects.create_user(username="broken_user", password="pass")
    group = Group.objects.create(name="incomplete_group")

    content_type = ContentType.objects.get_for_model(Study)

    # Delete all relevant permissions before test
    Permission.objects.filter(
        content_type=content_type,
        codename__in=['add_study', 'change_study', 'delete_study', 'view_study']
    ).delete()

    # Create only one permission
    Permission.objects.create(codename='add_study', name='Can add study', content_type=content_type)

    with pytest.raises(Permission.DoesNotExist):
        utils.assign_all_group_permissions(user.username, group.name)

@pytest.mark.django_db
def test_close_study_model_success():
    user = User.objects.create_user(username="testuser", password="testpass")

    study = Study.objects.create(
        title="Test Study",
        closed=False,
        is_test=False,
        duration=10,
        numberOfSubjects=1,
        enrolled_subjects="000",
        owner=user,
        passive_monitoring=False,
        frequency=0,
        labeling=0,
        sensor_list=[],
    )

    result = utils.close_study_model("Test Study")
    study.refresh_from_db()

    assert result is True
    assert study.closed is True

@pytest.mark.django_db
def test_close_study_model_study_not_found():
    result = utils.close_study_model("Nonexistent Study")
    assert result is True
    assert not Study.objects.filter(title="Nonexistent Study").exists()

@pytest.mark.django_db
def test_retrieve_all_survey_for_user_as_admin(monkeypatch):
    # Create a test user
    user = User.objects.create_user(username="admin", password="testpass")

    # Create a survey that should be visible to admin
    Survey.objects.create(
        title="Admin Survey",
        description="Survey for admin",
        topN=1,
        splitbyCategory=0,
        scrolling='H',
        owner=user,
    )

    # Monkeypatch SessionManager.get_specific_session_data
    monkeypatch.setattr(
        SessionManager,
        "get_specific_session_data",
        lambda session_key, key, default=None: "administrator" if key == "groupname" else []
    )

    # Call the function
    result = utils.retrieve_all_survey_for_user(user, session_key="fake_session")

    # Validate
    assert any(s['title'] == "Admin Survey" for s in result)

@pytest.mark.django_db
def test_retrieve_all_survey_for_user_as_investigator_with_ema_study(monkeypatch):
    # Create user
    user = User.objects.create_user(username="investigator", password="pass")

    # Create a survey and associated EMA study
    survey = Survey.objects.create(
        title="Investigator Survey",
        description="Survey for investigator",
        topN=1,
        splitbyCategory=0,
        scrolling="H",
        owner=user,
    )

    study = Study.objects.create(
        title="investigator_study",
        duration=10,
        numberOfSubjects=5,
        enrolled_subjects="001,002",
        is_test=False,
        owner=user,
        passive_monitoring=False,
        frequency=1,
        labeling=1,
        sensor_list=[],
        ecological_momentary_assessment=True,
        survey=survey,
    )

    # Monkeypatch the session data for investigator group and EMA access
    monkeypatch.setattr(
        SessionManager,
        "get_specific_session_data",
        lambda session_key, key, default=None: (
            "investigator" if key == constants.session_key_groupname else [study.title]
        )
    )

    # Call the function
    result = utils.retrieve_all_survey_for_user(user, session_key="fake_session")

    # Assert the expected survey is included
    titles = [s["title"] for s in result]
    assert survey.title in titles

@pytest.mark.django_db
def test_update_answer_in_db_success():
    # Setup user, survey, question and initial answer
    user = User.objects.create_user(username="tester", password="pass")
    survey = Survey.objects.create(title="Update Test", description="", topN=1, splitbyCategory=0, scrolling="H", owner=user)
    question = Question.objects.create(title="Q1", survey=survey, sortId=1, active=True, questionType=1)

    answer = Answer.objects.create(
        question=question,
        answerSortId=1,
        text="Old Text",
        answerSubText="Old Sub",
        value=1,
        defaultValue=False,
        stepSize=1,
        minValue=0,
        maxValue=10,
        minText="Low",
        maxText="High",
    )

    # Form data to update
    form_data = {
        "text": "Updated Text",
        "answerSubText": "Updated Sub",
        "answerSortId": 2,
        "value": 99,
        "defaultValue": True,
        "stepSize": 5,
        "minValue": 1,
        "maxValue": 99,
        "minText": "Min",
        "maxText": "Max",
    }

    # Run update
    utils.update_answer_in_db(form_data, answer.id)

    # Refresh from DB and check
    answer.refresh_from_db()
    assert answer.text == "Updated Text"
    assert answer.value == 99
    assert answer.defaultValue == 1.0

@pytest.mark.django_db
def test_update_answer_in_db_not_found(caplog):
    # Prepare invalid answer_id and form_data
    form_data = {
        "text": "Nonexistent",
        "answerSubText": "None",
        "answerSortId": 1,
        "value": 1,
        "defaultValue": False,
        "stepSize": 1,
        "minValue": 0,
        "maxValue": 10,
        "minText": "Low",
        "maxText": "High",
    }

    # Should not raise, but log the failure
    utils.update_answer_in_db(form_data, answer_id=9999)

    # Optionally check logs
    assert "update_answer_in_db" in caplog.text or caplog.records

@pytest.mark.django_db
def test_delete_answer_in_db_success():
    user = User.objects.create_user(username="deleter", password="pass")
    survey = Survey.objects.create(title="Survey D", description="", topN=1, splitbyCategory=0, scrolling="H", owner=user)
    question = Question.objects.create(title="Q-del", survey=survey, sortId=1, active=True, questionType=1)

    answer = Answer.objects.create(
        question=question,
        answerSortId=1,
        text="Delete me",
        answerSubText="delete",
        value=1,
        defaultValue=False,
        stepSize=1,
        minValue=0,
        maxValue=10,
        minText="Min",
        maxText="Max"
    )

    assert Answer.objects.count() == 1

    utils.delete_answer_in_db(answer.id)

    assert Answer.objects.count() == 0

@pytest.mark.django_db
def test_delete_answer_in_db_invalid_id():
    # Using a non-existent ID
    with pytest.raises(Exception):
        utils.delete_answer_in_db(answer_id=9999)

@pytest.mark.django_db
def test_update_question_in_db_success():
    user = User.objects.create_user(username="testuser", password="pass")
    survey = Survey.objects.create(title="Update Survey", description="", topN=1, splitbyCategory=0, scrolling="H", owner=user)
    question = Question.objects.create(
        survey=survey,
        title="Original title",
        active=True,
        sortId=1,
        subText="original",
        frequency=1,
        questionType=1,
        category=1
    )

    updated_data = {
        "title": "Updated title",
        "subText": "updated",
        "active": True,
        "sortId": 2,
        "frequency": 50,
        "clockTime": 600,
        "clockTime_start": [9],
        "clockTime_end": [11],
        "nextDayToAnswer": 1,
        "category": 1,
        "imageURL": "http://image.com/img.png",
        "url": "http://link.com",
        "questionType": 1,
        "deactivateOnAnswer": "no",
        "deactivateOnDate": 0,
        "activate_question": [],
        "deactivate_question": [],
        "activation_condition": "",
        "deactivation_condition": "",
    }

    utils.update_question_in_db(question.id, updated_data)

    question.refresh_from_db()
    assert question.title == "Updated title"
    assert question.frequency == 50

@pytest.mark.django_db
def test_update_question_in_db_invalid_id():
    invalid_question_id = 9999  # Assuming this ID doesn't exist in the test DB

    invalid_data = {
        "title": "Should Fail",
        "subText": "",
        "active": False,
        "sortId": 99,
        "frequency": 1,
        "clockTime": None,
        "clockTime_start": [],
        "clockTime_end": [],
        "nextDayToAnswer": None,
        "category": 1,
        "imageURL": "",
        "url": "",
        "questionType": 1,
        "deactivateOnAnswer": "",
        "deactivateOnDate": None,
        "activate_question": [],
        "deactivate_question": [],
        "activation_condition": None,
        "deactivation_condition": None
    }

    # Run the update; it should silently fail (no matching record)
    utils.update_question_in_db(invalid_question_id, invalid_data)

    # Assert that the object still does not exist
    assert not Question.objects.filter(id=invalid_question_id).exists()

@pytest.mark.django_db
def test_delete_survey_for_user_as_admin():
    user = User.objects.create_user(username="admin", password="test")
    survey = Survey.objects.create(title="Test Survey", description="desc", topN=1, owner=user)

    result = utils.delete_survey_for_user("administrator", user, survey.id)

    assert result is True
    assert not Survey.objects.filter(id=survey.id).exists()

@pytest.mark.django_db
def test_delete_survey_for_user_as_owner():
    owner = User.objects.create_user(username="owner", password="pass")
    survey = Survey.objects.create(title="Owner Survey", description="desc", topN=1, owner=owner)

    result = utils.delete_survey_for_user("investigator", owner, survey.id)

    assert result is True
    assert not Survey.objects.filter(id=survey.id).exists()

@pytest.mark.django_db
def test_delete_survey_for_user_non_owner_cannot_delete():
    owner = User.objects.create_user(username="owner", password="test")
    other_user = User.objects.create_user(username="other", password="test")

    survey = Survey.objects.create(title="Protected Survey", description="desc", topN=1, owner=owner)

    result = utils.delete_survey_for_user("investigator", other_user, survey.id)

    assert result is True  # function still returns True, but survey should not be deleted
    assert Survey.objects.filter(id=survey.id).exists()

@pytest.mark.django_db
def test_delete_question_from_db_success():
    user = User.objects.create_user(username="testuser", password="pass")
    survey = Survey.objects.create(title="Survey A", description="", topN=1, owner=user)
    question = Question.objects.create(
        survey=survey,
        title="Q1",
        active=True,
        sortId=1,
        subText="",
        frequency=1,
        clockTime=600,
        clockTime_start=[],
        clockTime_end=[],
        nextDayToAnswer=0,
        category=1,
        imageURL="",
        url="",
        questionType=1,
        deactivateOnAnswer="",
        deactivateOnDate=0,
        activate_question=[],
        deactivate_question=[],
        activation_condition=None,
        deactivation_condition=None,
        clockTime_timezone="Europe/Berlin"
    )

    result = utils.delete_question_from_db(question.id, survey.id)

    assert result is True
    assert not Question.objects.filter(id=question.id).exists()

@pytest.mark.django_db
def test_delete_question_from_db_invalid_id():
    result = utils.delete_question_from_db(question_id=9999, survey_id=1234)

    assert result is True  # still returns True even if nothing was deleted

@pytest.mark.django_db
def test_retrieve_all_questions_for_survey_success():
    user = User.objects.create_user(username="testuser", password="pass")
    survey = Survey.objects.create(title="Test Survey", description="", topN=3, owner=user)
    question = Question.objects.create(
        survey=survey,
        title="Question 1",
        active=True,
        sortId=1,
        subText="Subtext",
        frequency=1,
        clockTime=600,
        clockTime_start=[],
        clockTime_end=[],
        nextDayToAnswer=0,
        category=1,
        imageURL="",
        url="",
        questionType=1,
        deactivateOnAnswer="",
        deactivateOnDate=0,
        activate_question=[],
        deactivate_question=[],
        activation_condition=None,
        deactivation_condition=None,
        clockTime_timezone="Europe/Berlin"
    )
    Answer.objects.create(
        question=question,
        answerSortId=1,
        text="Yes",
        answerSubText="",
        value=1,
        defaultValue=False,
        stepSize=1,
        minValue=0,
        maxValue=10,
        minText="Low",
        maxText="High"
    )

    result = utils.retrieve_all_questions_for_survey(survey.id)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["title"] == "Question 1"
    assert "answer" in result[0]
    assert result[0]["answer"][0]["text"] == "Yes"

@pytest.mark.django_db
def test_retrieve_all_questions_for_survey_empty():
    user = User.objects.create_user(username="testuser", password="pass")
    survey = Survey.objects.create(title="Empty Survey", description="", topN=1, owner=user)

    result = utils.retrieve_all_questions_for_survey(survey.id)

    assert isinstance(result, list)
    assert result == []

@pytest.mark.django_db
def test_retrieve_download_questions_for_survey_success():
    user = User.objects.create_user(username="testuser", password="pass")
    survey = Survey.objects.create(title="Download Survey", description="", topN=1, owner=user)
    question = Question.objects.create(
        survey=survey,
        title="Downloadable Question",
        active=True,
        sortId=1,
        subText="Download subtext",
        frequency=1,
        clockTime=600,
        clockTime_start=[8, 30],
        clockTime_end=[9, 0],
        nextDayToAnswer=0,
        category=1,
        imageURL="",
        url="",
        questionType=1,
        deactivateOnAnswer="",
        deactivateOnDate=0,
        activate_question=[2],
        deactivate_question=[3],
        activation_condition="if A then B",
        deactivation_condition="if C then D",
        clockTime_timezone="Europe/Berlin"
    )
    Answer.objects.create(
        question=question,
        answerSortId=1,
        text="Definitely",
        answerSubText="",
        value=5,
        defaultValue=True,
        stepSize=1,
        minValue=0,
        maxValue=10,
        minText="Min",
        maxText="Max"
    )

    result = utils.retrieve_download_questions_for_survey(survey.id)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["title"] == "Downloadable Question"
    assert result[0]["deActivate_question"] == "3"
    assert result[0]["answer"][0]["text"] == "Definitely"

@pytest.mark.django_db
def test_retrieve_download_questions_for_survey_empty():
    user = User.objects.create_user(username="testuser", password="pass")
    survey = Survey.objects.create(title="Empty Download Survey", description="", topN=1, owner=user)

    result = utils.retrieve_download_questions_for_survey(survey.id)

    assert isinstance(result, list)
    assert result == []

@pytest.mark.django_db
def test_retrieve_all_answers_for_questions_success():
    user = User.objects.create_user(username="ans_user", password="pass")
    survey = Survey.objects.create(title="Answer Survey", description="", topN=1, owner=user)

    question = Question.objects.create(
        survey=survey,
        title="Question with answers",
        active=True,
        sortId=1,
        subText="",
        frequency=1,
        clockTime=600,
        clockTime_start=[],
        clockTime_end=[],
        nextDayToAnswer=0,
        category=1,
        imageURL="",
        url="",
        questionType=1,
        deactivateOnAnswer="",
        deactivateOnDate=0,
        activate_question=[],
        deactivate_question=[],
        activation_condition="",
        deactivation_condition="",
        clockTime_timezone="Europe/Berlin"
    )

    Answer.objects.create(
        question=question,
        answerSortId=1,
        text="Yes",
        answerSubText="Sure",
        value=1,
        defaultValue=False,
        stepSize=1,
        minValue=0,
        maxValue=10,
        minText="Low",
        maxText="High"
    )

    answers = utils.retrieve_all_answers_for_questions(question.id)

    assert isinstance(answers, list)
    assert len(answers) == 1
    assert answers[0]["text"] == "Yes"
    assert answers[0]["value"] == 1

@pytest.mark.django_db
def test_retrieve_all_answers_for_questions_no_answers():
    answers = utils.retrieve_all_answers_for_questions(9999)  # Assuming this ID doesn't exist

    assert isinstance(answers, list)
    assert answers == []

@pytest.mark.django_db
def test_retrieve_all_categories_for_survey_success():
    user = User.objects.create_user(username="cat_user", password="pass")
    survey = Survey.objects.create(title="Survey with Categories", description="", topN=1, owner=user)

    Category.objects.create(
        survey=survey,
        categoryTitle="Mood",
        categoryValue=1,
        didSubjectAsk=True
    )

    result = utils.retrieve_all_categories_for_survey(survey.id)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["categoryTitle"] == "Mood"
    assert result[0]["categoryValue"] == 1
    assert result[0]["didSubjectAsk"] is True

@pytest.mark.django_db
def test_retrieve_all_categories_for_survey_empty():
    user = User.objects.create_user(username="no_cat_user", password="pass")
    survey = Survey.objects.create(title="Empty Category Survey", description="", topN=1, owner=user)

    result = utils.retrieve_all_categories_for_survey(survey.id)

    assert isinstance(result, list)
    assert result == []

@pytest.mark.django_db
def test_retrieve_survey_success():
    user = User.objects.create_user(username="survey_user", password="pass")
    survey = Survey.objects.create(title="My Survey", description="Testing", topN=5, owner=user)

    result = utils.retrieve_survey(survey.id)

    assert result is not None
    assert result.id == survey.id
    assert result.title == "My Survey"

@pytest.mark.django_db
def test_retrieve_survey_invalid_id():
    invalid_id = 99999  # Assuming this doesn't exist

    with pytest.raises(Survey.DoesNotExist):
        utils.retrieve_survey(invalid_id)

@pytest.mark.django_db
def test_retrieve_question_success():
    user = User.objects.create_user(username="question_user", password="pass")
    survey = Survey.objects.create(title="Survey Q", description="desc", topN=3, owner=user)
    question = Question.objects.create(
        survey=survey,
        title="What is your mood?",
        active=True,
        sortId=1,
        subText="Choose your mood",
        frequency=1,
        clockTime=600,
        clockTime_start=[],
        clockTime_end=[],
        nextDayToAnswer=0,
        category=1,
        imageURL="",
        url="",
        questionType=1,
        deactivateOnAnswer="",
        deactivateOnDate=0,
        activate_question=[],
        deactivate_question=[],
        activation_condition=None,
        deactivation_condition=None,
        clockTime_timezone="Europe/Berlin"
    )

    result = utils.retrieve_question(question.id)

    assert result is not None
    assert result.id == question.id
    assert result.title == "What is your mood?"

@pytest.mark.django_db
def test_retrieve_question_invalid_id():
    invalid_id = 99999  # Assuming this does not exist

    with pytest.raises(Question.DoesNotExist):
        utils.retrieve_question(invalid_id)

@pytest.mark.django_db
def test_retrieve_survey_details_success():
    user = User.objects.create_user(username="survey_user", password="pass")
    survey = Survey.objects.create(
        title="Daily Health",
        description="Track your daily health metrics",
        topN=5,
        splitbyCategory=True,
        scrolling='H',
        owner=user
    )

    details = utils.retrieve_survey_details(survey.id)

    assert isinstance(details, dict)
    assert details["id"] == survey.id
    assert details["title"] == "Daily Health"
    assert details["topN"] == 5
    assert details["splitbyCategory"] is True

@pytest.mark.django_db
def test_retrieve_survey_details_invalid_id():
    invalid_id = 123456

    with pytest.raises(Survey.DoesNotExist):
        _ = utils.retrieve_survey_details(invalid_id)


@pytest.mark.django_db
def test_retrieve_question_details_success():
    user = User.objects.create_user(username="question_user", password="pass")
    survey = Survey.objects.create(title="Daily Survey", description="", topN=3, splitbyCategory=False, scrolling='H',
                                   owner=user)

    question = Question.objects.create(
        survey=survey,
        title="How are you?",
        active=True,
        sortId=1,
        subText="Mood check",
        frequency=1,
        clockTime=600,
        clockTime_start=[],
        clockTime_end=[],
        nextDayToAnswer=0,
        category=1,
        imageURL="",
        url="",
        questionType=1,
        deactivateOnAnswer="",
        deactivateOnDate=0,
        activate_question=[],
        deactivate_question=[],
        activation_condition="",
        deactivation_condition="",
        clockTime_timezone="Europe/Berlin"
    )

    Answer.objects.create(
        question=question,
        answerSortId=0,
        text="Good",
        answerSubText="Feeling fine",
        value=5,
        defaultValue=True,
        stepSize=1,
        minValue=1,
        maxValue=10,
        minText="Bad",
        maxText="Great"
    )

    details = utils.retrieve_question_details(question.id)

    assert isinstance(details, dict)
    assert details["db_id"] == question.id
    assert details["title"] == "How are you?"
    assert len(details["answer"]) == 1
    assert details["answer"][0]["text"] == "Good"

@pytest.mark.django_db
def test_retrieve_question_details_invalid_id():
    with pytest.raises(Question.DoesNotExist):
        _ = utils.retrieve_question_details(9999)

@pytest.mark.django_db
def test_retrieve_questions_greater_than_sortId_found():
    user = User.objects.create_user(username="testuser")
    survey = Survey.objects.create(title="SortId Survey", description="desc", topN=3, scrolling='H', splitbyCategory=False, owner=user)

    Question.objects.create(survey=survey, title="Q1", sortId=1, questionType=1, category=1)
    q2 = Question.objects.create(survey=survey, title="Q2", sortId=5, questionType=1, category=1)
    q3 = Question.objects.create(survey=survey, title="Q3", sortId=10, questionType=1, category=1)

    result = utils.retrieve_questions_greater_than_sortId(survey.id, 4)

    assert len(result) == 2
    titles = [q["title"] for q in result]
    assert "Q2" in titles
    assert "Q3" in titles

@pytest.mark.django_db
def test_retrieve_questions_greater_than_sortId_none():
    user = User.objects.create_user(username="testuser")
    survey = Survey.objects.create(title="Empty SortId Survey", description="desc", topN=3, scrolling='H', splitbyCategory=False, owner=user)

    Question.objects.create(survey=survey, title="Q1", sortId=2, questionType=1, category=1)

    result = utils.retrieve_questions_greater_than_sortId(survey.id, 5)

    assert result == []


@pytest.mark.django_db
def test_answer_serializer_success():
    user = User.objects.create_user(username="testuser")
    survey = Survey.objects.create(title="Survey", description="desc", topN=3, scrolling='H', splitbyCategory=False,
                                   owner=user)
    question = Question.objects.create(survey=survey, title="Question", sortId=1, questionType=1, category=1)

    Answer.objects.create(
        question=question,
        answerSortId=1,
        text="Yes",
        answerSubText="",
        value=1,
        defaultValue=True,
        stepSize=1,
        minValue=0,
        maxValue=10,
        minText="Low",
        maxText="High"
    )

    queryset = Answer.objects.filter(question=question).values()
    serialized = utils.answer_serializer(queryset)
    data = json.loads(serialized)

    assert isinstance(data, list)
    assert data[0]["text"] == "Yes"
    assert data[0]["defaultValue"] == 1.0

@pytest.mark.django_db
def test_answer_serializer_empty():
    queryset = Answer.objects.none().values()
    serialized = utils.answer_serializer(queryset)
    assert json.loads(serialized) == []

@pytest.mark.django_db
def test_survey_serializer_success():
    user = User.objects.create_user(username="testuser")
    survey = Survey.objects.create(
        title="Mood Survey",
        description="Track your mood daily",
        topN=5,
        scrolling='H',
        splitbyCategory=True,
        owner=user
    )

    queryset = Survey.objects.filter(id=survey.id).values()
    serialized = utils.survey_serializer(queryset)
    data = json.loads(serialized)

    assert isinstance(data, list)
    assert data[0]["title"] == "Mood Survey"
    assert data[0]["splitbyCategory"] is True
    assert data[0]["scrolling"] == "H"

@pytest.mark.django_db
def test_survey_serializer_empty():
    queryset = Survey.objects.none().values()
    serialized = utils.survey_serializer(queryset)
    assert json.loads(serialized) == []

@pytest.mark.django_db
def test_category_serializer_valid():
    user = User.objects.create_user(username="testuser")
    survey = Survey.objects.create(
        title="Survey with categories",
        description="Has categories",
        topN=3,
        scrolling='H',
        splitbyCategory=True,
        owner=user
    )
    cat = Category.objects.create(
        survey=survey,
        categoryValue=1,
        categoryTitle="Wellbeing",
        didSubjectAsk=True
    )

    queryset = Category.objects.filter(id=cat.id).values()
    serialized = utils.category_serializer(queryset)
    data = json.loads(serialized)

    assert isinstance(data, list)
    assert data[0]["categoryValue"] == 1
    assert data[0]["categoryTitle"] == "Wellbeing"
    assert data[0]["didSubjectAsk"] is True

@pytest.mark.django_db
def test_category_serializer_empty():
    queryset = Category.objects.none().values()
    serialized = utils.category_serializer(queryset)
    assert json.loads(serialized) == []

@pytest.mark.django_db
def test_question_db_serializer_valid():
    user = User.objects.create_user(username="serializeruser")
    survey = Survey.objects.create(
        title="Serialization Survey",
        description="Survey to test question_db_serializer",
        topN=2,
        owner=user,
        scrolling='V',
        splitbyCategory=False
    )
    category = Category.objects.create(
        survey=survey,
        categoryValue=1,
        categoryTitle="Health",
        didSubjectAsk=True
    )
    question = Question.objects.create(
        survey=survey,
        title="Serialized question",
        active=True,
        sortId=10,
        subText="Details",
        frequency=1,
        clockTime=600,
        clockTime_start=[8, 30],
        clockTime_end=[9, 30],
        nextDayToAnswer=1,
        category=category.categoryValue,
        imageURL="img.png",
        url="https://example.com",
        questionType=1,
        deactivateOnAnswer="yes",
        deactivateOnDate=0,
        activate_question=[1],
        deactivate_question=[2],
        activation_condition="if answered",
        deactivation_condition="after 1 day",
        clockTime_timezone="UTC"
    )

    queryset = Question.objects.filter(id=question.id).values()
    serialized = utils.question_db_serializer(queryset)
    data = json.loads(serialized)

    assert data[0]['id'] == 10
    assert data[0]['title'] == "Serialized question"
    assert data[0]['clockTime_start'] == [8, 30]

@pytest.mark.django_db
def test_question_db_serializer_empty():
    queryset = Question.objects.none().values()
    result = utils.question_db_serializer(queryset)
    assert json.loads(result) == []

@pytest.mark.django_db
def test_category_serializer_valid():
    user = User.objects.create_user(username="cat_user")
    survey = Survey.objects.create(
        title="Category Survey",
        description="Category test",
        topN=1,
        owner=user,
        scrolling='H',
        splitbyCategory=False
    )
    category = Category.objects.create(
        survey=survey,
        categoryTitle="Mood",
        categoryValue=10,
        didSubjectAsk=True
    )

    queryset = Category.objects.filter(id=category.id).values()
    result = utils.category_serializer(queryset)
    data = json.loads(result)

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['categoryTitle'] == "Mood"
    assert data[0]['categoryValue'] == 10
    assert data[0]['didSubjectAsk'] is True

@pytest.mark.django_db
def test_category_serializer_empty():
    queryset = Category.objects.none().values()
    result = utils.category_serializer(queryset)
    assert json.loads(result) == []

@pytest.mark.django_db
def test_question_serializer_valid():
    user = User.objects.create_user(username="qs_user")
    survey = Survey.objects.create(
        title="QS Survey",
        description="Question Serializer Test",
        topN=3,
        owner=user,
        scrolling='V',
        splitbyCategory=True
    )
    question = Question.objects.create(
        survey=survey,
        title="How are you?",
        sortId=1,
        active=True,
        subText="Mood scale",
        frequency=50,
        clockTime=720,
        clockTime_start=[8],
        clockTime_end=[20],
        nextDayToAnswer=0,
        category=1,
        imageURL="",
        url="",
        questionType=1,
        deactivateOnAnswer="",
        deactivateOnDate=0,
        activate_question=[2],
        deactivate_question=[3],
        activation_condition="some condition",
        deactivation_condition="another condition",
        clockTime_timezone="Europe/Berlin"
    )

    queryset = Question.objects.filter(id=question.id).values()
    result = utils.question_serializer(queryset)
    data = json.loads(result)

    assert isinstance(data, list)
    assert len(data) == 1
    q = data[0]
    assert q['title'] == "How are you?"
    assert q['clockTime_start'] == "8"
    assert q['clockTime_end'] == "20"
    assert q['activate_question'] == "2"
    assert q['deActivate_question'] == "3"
    assert q['clockTime_timezone'] == "Europe/Berlin"

@pytest.mark.django_db
def test_question_serializer_empty():
    queryset = Question.objects.none().values()
    result = utils.question_serializer(queryset)
    assert json.loads(result) == []


@pytest.mark.django_db
def test_add_verification_code_success():
    test_token = uuid.uuid4()  # generates a valid UUID
    expiration = timezone.now() + timezone.timedelta(days=1)
    token_obj = FileDownloadToken.objects.create(token=test_token, code="", expiration_date=expiration)
    result = utils.add_verification_code("123456", test_token)
    token_obj.refresh_from_db()

    assert result is True
    assert token_obj.code == "123456"


@pytest.mark.django_db
def test_add_verification_code_token_not_found():
    test_token = uuid.uuid4()  # generates a valid UUID
    result = utils.add_verification_code("nochange", test_token)

    # The function doesn't raise or return False, just continues
    assert result is True
    # Optionally confirm nothing was created
    assert FileDownloadToken.objects.count() == 0

@pytest.mark.django_db
def test_get_list_surveys_for_user_owned_only():
    user = User.objects.create_user(username="owner", password="pass")
    Survey.objects.create(title="Survey A", description="desc", topN=5, splitbyCategory=0, scrolling="H", owner=user)
    Survey.objects.create(title="Survey B", description="desc", topN=3, splitbyCategory=0, scrolling="H", owner=user)

    surveys = utils.get_list_surveys_for_user(user, ema_studies=None)

    assert len(surveys) == 2
    assert any(s["title"] == "Survey A" for s in surveys)
    assert any(s["title"] == "Survey B" for s in surveys)

@pytest.mark.django_db
def test_get_list_surveys_for_user_with_ema_study():
    user = User.objects.create_user(username="investigator", password="pass")
    survey = Survey.objects.create(title="EMA Survey", description="desc", topN=1, splitbyCategory=0, scrolling="H", owner=user)
    Study.objects.create(title="Study X", survey=survey, is_test=False, duration=10, numberOfSubjects=5, enrolled_subjects="000", owner=user, frequency=1, labeling=1, sensor_list=[])

    ema_studies = ["Study X"]
    surveys = utils.get_list_surveys_for_user(user, ema_studies)

    assert len(surveys) == 1
    assert surveys[0]["title"] == "EMA Survey"

@pytest.mark.django_db
def test_get_list_surveys_for_user_returns_user_owned_surveys():
    user = User.objects.create_user(username="owner", password="testpass")
    Survey.objects.create(title="Survey A", description="", topN=3, splitbyCategory=0, scrolling='H', owner=user)

    result = utils.get_list_surveys_for_user(user, ema_studies=[])

    assert len(result) == 1
    assert result[0]["title"] == "Survey A"

@pytest.mark.django_db
def test_get_list_surveys_for_user_with_ema_study():
    user = User.objects.create_user(username="indirect_user", password="pass")
    survey = Survey.objects.create(title="EMA Survey", description="", topN=2, splitbyCategory=0, scrolling='V', owner=user)

    Study.objects.create(
        title="EmaStudy1",
        description="",
        duration=10,
        numberOfSubjects=5,
        enrolled_subjects="000",
        is_test=False,
        closed=False,
        owner=user,
        passive_monitoring=False,
        frequency=1,
        labeling=0,
        sensor_list=[],
        ecological_momentary_assessment=True,
        survey=survey,
    )

    result = utils.get_list_surveys_for_user(user, ema_studies=["EmaStudy1"])

    assert any(s["title"] == "EMA Survey" for s in result)

@pytest.mark.django_db
def test_get_list_surveys_for_user_with_ema_studies_none():
    user = User.objects.create_user(username="user_no_ema", password="pass")

    # User owns one survey
    Survey.objects.create(title="Owned Survey", description="", topN=1, splitbyCategory=0, scrolling='H', owner=user)

    result = utils.get_list_surveys_for_user(user, ema_studies=None)

    assert len(result) == 1
    assert result[0]["title"] == "Owned Survey"

@pytest.mark.django_db
def test_get_list_surveys_for_user_no_duplicates():
    user = User.objects.create_user(username="dupe_user", password="pass")

    # Create one survey
    survey = Survey.objects.create(title="Shared Survey", description="", topN=1, splitbyCategory=0, scrolling='H', owner=user)

    # User owns the survey
    # It's also referenced by an EMA study
    Study.objects.create(
        title="SharedStudy",
        description="",
        duration=5,
        numberOfSubjects=1,
        enrolled_subjects="000",
        is_test=False,
        closed=False,
        owner=user,
        passive_monitoring=False,
        frequency=1,
        labeling=0,
        sensor_list=[],
        ecological_momentary_assessment=True,
        survey=survey,
    )

    result = utils.get_list_surveys_for_user(user, ema_studies=["SharedStudy"])

    # Ensure it's only listed once
    assert len(result) == 1
    assert result[0]["title"] == "Shared Survey"

@pytest.mark.django_db
def test_get_list_surveys_for_user_no_surveys():
    user = User.objects.create_user(username="no_survey_user", password="pass")

    result = utils.get_list_surveys_for_user(user, ema_studies=[])

    assert result == []

@pytest.mark.django_db
def test_generete_survey_notification_obj_valid_input():
    survey = {
        "questions": [
            {
                "frequency": 2,
                "clockTime": 600,
                "startOnDay": 0,
                "endOnDay": 5
            }
        ]
    }
    study_duration = 5

    result = utils.generete_survey_notification_obj(survey, study_duration)

    expected = {
        0: [600],
        2: [600],
        4: [600]
    }
    assert result == expected

@pytest.mark.django_db
def test_generete_survey_notification_obj_zero_frequency():
    survey = {
        "questions": [
            {
                "frequency": 0,  # should skip logic
                "clockTime": 660,
                "startOnDay": 0,
                "endOnDay": 3
            }
        ]
    }
    study_duration = 3

    result = utils.generete_survey_notification_obj(survey, study_duration)

    assert result == {}  # No entries expected due to frequency 0

@pytest.mark.django_db
def test_generete_survey_notification_obj_with_varied_input():
    survey = {
        "questions": [
            {
                "frequency": 2,
                "clockTime": 800,
                "startOnDay": 1,
                "endOnDay": 6,
                "deactivateOnDate": 5,
            },
            {
                "frequency": 1,
                "clockTime": 1000,
                "startOnDay": 0,
                "endOnDay": 3,
                "deactivateOnDate": None,
            },
            {
                "frequency": 1,
                "clockTime": None,  # Should not be added
                "startOnDay": 0,
                "endOnDay": 2
            }
        ]
    }

    study_duration = 6
    result = utils.generete_survey_notification_obj(survey, study_duration)

    # Expected clock times only for valid, non-None values
    expected = {
        0: [1000],
        1: [800, 1000],
        2: [1000],
        3: [800]
    }

    # Sort lists to ensure equality check works
    for key in result:
        result[key] = sorted(result[key])
    for key in expected:
        expected[key] = sorted(expected[key])

    assert result == expected


@pytest.mark.django_db
def test_get_categories_from_db_success():
    user = User.objects.create_user(username="user1", password="pass")
    survey = Survey.objects.create(title="Survey", description="Desc", topN=3, splitbyCategory=1, scrolling='H',
                                   owner=user)

    Category.objects.create(survey=survey, categoryTitle="Cat A", categoryValue=1, didSubjectAsk=True)
    Category.objects.create(survey=survey, categoryTitle="Cat B", categoryValue=2, didSubjectAsk=False)

    result = utils.get_categories_from_db(survey.id)

    assert result.count() == 2
    assert result[0].categoryTitle == "Cat A"
    assert result[1].categoryValue == 2

@pytest.mark.django_db
def test_get_categories_from_db_empty():
    result = utils.get_categories_from_db(9999)  # Nonexistent survey ID
    assert result.count() == 0

@pytest.mark.django_db
def test_create_categories_in_db_success():
    user = User.objects.create_user(username="user1", password="pass")
    survey = Survey.objects.create(title="Survey", description="test", topN=1, splitbyCategory=0, scrolling='H', owner=user)

    category_payload = {
        "category_list": [
            {"categoryValue": 10, "categoryTitle": "Cat A", "didSubjectAsk": True},
            {"categoryValue": 20, "categoryTitle": "Cat B", "didSubjectAsk": False}
        ]
    }

    utils.create_categories_in_db(survey.id, category_payload)

    result = Category.objects.filter(survey=survey)
    assert result.count() == 2
    assert result[0].categoryTitle == "Cat A"
    assert result[1].categoryValue == 20

@pytest.mark.django_db
def test_create_categories_in_db_empty_list():
    user = User.objects.create_user(username="user2", password="pass")
    survey = Survey.objects.create(title="Survey2", description="test2", topN=1, splitbyCategory=0, scrolling='H', owner=user)

    empty_payload = {"category_list": []}
    utils.create_categories_in_db(survey.id, empty_payload)

    result = Category.objects.filter(survey=survey)
    assert result.count() == 0

@pytest.mark.django_db
def test_create_categories_in_db_from_data_success():
    user = User.objects.create_user(username="cat_user", password="pass")
    survey = Survey.objects.create(title="CatSurvey", description="desc", topN=3, splitbyCategory=0, scrolling='H', owner=user)

    category_data = [
        {"categoryValue": 1, "categoryTitle": "Title A", "didSubjectAsk": True},
        {"categoryValue": 2, "categoryTitle": "Title B", "didSubjectAsk": False}
    ]

    utils.create_categories_in_db_from_data(survey.id, category_data)

    categories = Category.objects.filter(survey=survey)
    assert categories.count() == 2
    assert categories[0].categoryValue == 1
    assert categories[1].categoryTitle == "Title B"

@pytest.mark.django_db
def test_create_categories_in_db_from_data_empty():
    user = User.objects.create_user(username="empty_user", password="pass")
    survey = Survey.objects.create(title="EmptySurvey", description="desc", topN=2, splitbyCategory=1, scrolling='H', owner=user)

    utils.create_categories_in_db_from_data(survey.id, [])

    categories = Category.objects.filter(survey=survey)
    assert categories.count() == 0

@pytest.mark.django_db
def test_retrieve_test_cases_for_study_success():
    user = User.objects.create_user(username="qc_user", password="pass")
    study = Study.objects.create(
        title="QC Study",
        owner=user,
        is_test=False,
        duration=10,
        numberOfSubjects=5,
        enrolled_subjects="123",
        passive_monitoring=False,
        frequency=1,
        labeling=0,
        sensor_list=[],
    )
    QualityControlTests.objects.create(
        study=study,
        testcase_id="tc_001",
        tested_by_admin=True
    )
    QualityControlTests.objects.create(
        study=study,
        testcase_id="tc_002",
        tested_by_owner=True
    )

    result = utils.retrieve_test_cases_for_study("QC Study")
    result_data = json.loads(result)

    assert len(result_data) == 2
    assert any(test["tested_by_admin"] is True for test in result_data)

@pytest.mark.django_db
def test_retrieve_test_cases_for_study_invalid_study():
    with pytest.raises(IndexError):
        utils.retrieve_test_cases_for_study("Nonexistent Study")


@pytest.mark.django_db
def test_update_test_case_flags_success():
    user = User.objects.create_user(username="testuser", password="pass")

    study = Study.objects.create(
        title="Test Study",
        duration=5,
        numberOfSubjects=1,
        enrolled_subjects="000",
        is_test=True,
        owner=user,
        passive_monitoring=False,
        frequency=0,
        labeling=0,
        sensor_list=[]
    )

    test_case = QualityControlTests.objects.create(
        study=study,
        testcase_id="TC_UNIQUE_001"  # ensure uniqueness
    )

    updates = [{
        "id": test_case.id,
        "tested_by_admin": True,
        "tested_by_owner": True
    }]

    result = utils.update_test_case_flags(updates, user.username)
    print("DEBUG:", result)

    test_case.refresh_from_db()
    print("AFTER UPDATE:", test_case.tested_by_admin, test_case.tested_by_owner, test_case.admin_username)

    assert result["success_count"] == 1
    assert result["failure_count"] == 0
    assert test_case.tested_by_admin is True
    assert test_case.tested_by_owner is True
    assert test_case.admin_username == user.username

@pytest.mark.django_db
def test_update_test_case_flags_invalid_id():
    updates = [{
        "id": 9999,  # Non-existent ID
        "tested_by_admin": True
    }]

    result = utils.update_test_case_flags(updates, "adminuser")

    assert result["success_count"] == 0
    assert result["failure_count"] == 1
    assert len(result["errors"]) == 0  # Logging is used but no error is appended