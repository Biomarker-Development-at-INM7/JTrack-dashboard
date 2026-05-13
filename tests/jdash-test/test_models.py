import pytest
from datetime import timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

from jdash.models import (
    Survey, Study, Category, Question, Answer, Subject,
    FileDownloadToken, QualityControlTests
)

@pytest.fixture
def user():
    return User.objects.create_user(username='testuser', password='testpass')


# Survey
@pytest.mark.django_db
def test_create_survey(user):
    survey = Survey.objects.create(
        title="Test Survey",
        description="Test Description",
        owner=user
    )
    assert survey.title == "Test Survey"
    assert survey.owner.username == "testuser"


# Study
@pytest.mark.django_db
def test_create_study(user):
    study = Study.objects.create(
        title="Test Study",
        owner=user,
        duration=30,
        numberOfSubjects=10
    )
    assert str(study) == "Test Study"
    assert study.owner == user


# Category
@pytest.mark.django_db
def test_create_category():
    cat = Category.objects.create(
        categoryTitle="Mood",
        categoryValue=1,
        didSubjectAsk=True
    )
    assert cat.categoryTitle == "Mood"


# Question – valid clean
def test_valid_question_clean():
    q = Question(
        title="How do you feel?",
        questionType=1,
        category=1,
        activate_question=[1],
        deactivate_question=[2],
        clockTime_start=[300],
        clockTime_end=[400]
    )
    q.clean()  # Should pass


# Question – activate_question not list
def test_question_clean_activate_not_list():
    q = Question(
        title="Bad Format",
        questionType=1,
        category=1,
        activate_question="notalist",
        deactivate_question=[],
        clockTime_start=[1],
        clockTime_end=[1]
    )
    with pytest.raises(ValidationError):
        q.clean()


# Question – deactivate_question has string
def test_question_clean_deactivate_invalid_items():
    q = Question(
        title="Bad Deactivate",
        questionType=1,
        category=1,
        activate_question=[1],
        deactivate_question=["bad"],
        clockTime_start=[1],
        clockTime_end=[1]
    )
    with pytest.raises(ValidationError):
        q.clean()


# Question – mismatched clock times
def test_question_clean_clock_time_mismatch():
    q = Question(
        title="Mismatch Clocks",
        questionType=1,
        category=1,
        activate_question=[1],
        deactivate_question=[2],
        clockTime_start=[1, 2],
        clockTime_end=[1]
    )
    with pytest.raises(ValidationError):
        q.clean()


# Answer
@pytest.mark.django_db
def test_create_answer():
    q = Question.objects.create(title="Q", questionType=1, category=1)
    answer = Answer.objects.create(
        text="Yes",
        answerSubText="Sure",
        question=q
    )
    assert answer.text == "Yes"


# Subject
@pytest.mark.django_db
def test_create_subject():
    subject = Subject.objects.create(
        appVersion_ema="1.0",
        applicationType="Android",
        deviceBrand_ema="BrandA",
        deviceModel_ema="ModelX",
        osVersion_ema="12",
        deviceid_ema="device123",
        status_ema=1,
        pushNotification_token_ema="token123",
        studyId="study001",
        time_joined_ema=timezone.now(),
        time_left_ema=timezone.now(),
        username="test_user",
        study_duration=30,
        active_labeling=1,
        status=1,
        deviceBrand="BrandB",
        deviceModel="ModelY",
        osVersion="13",
        deviceid="device456",
        pushNotification_token="token456",
        time_joined=timezone.now(),
        time_left=timezone.now(),
        timejoined_timezone="Europe/Berlin",
        timeZoneOffSetMinutes="+120"
    )

    assert subject.username == "test_user"
    assert subject.status == 1


# FileDownloadToken – is_code_valid & is_token_valid
def test_file_download_token_validity():
    now = timezone.now()
    token = FileDownloadToken(
        file_name="report.csv",
        expiration_date=now + timedelta(minutes=15),
        code_emailed=now,
        dowloaded=now
    )
    assert token.is_code_valid() is True
    assert token.is_token_valid() is True


# QualityControlTests
@pytest.mark.django_db
def test_quality_control_testcase(user):
    study = Study.objects.create(title="QC Study", owner=user)
    qc = QualityControlTests.objects.create(
        testcase_id="TC-001",
        test_type="EMA",
        description="Test description",
        steps="1. Do X, 2. Expect Y",
        expected_outcome="Y occurs",
        admin_username="admin",
        owner_username="owner",
        study=study
    )
    assert str(qc) == "TestCaseID: TC-001"