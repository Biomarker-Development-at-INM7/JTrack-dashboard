import pytest
from django import forms
from jdash.forms import (
    CreateStudyForm, SendNotificationForm, RemoveSubjectsForm,
    CreateSubjectForm, JSONUploadForm, SurveyForm, CategoryForm,
    AnswerForm, QuestionForm, DeleteSubjectForm, ContactUsForm,
    DateForm, TaskForm
)
from jdash.admin import DeviceSensorAdminForm
from jdash.models import (
    Survey,
    Study,
    Answer,
    Question,
    Category,
    DeviceCatalog,
    SensorCatalog,
    SamplingRateCatalog,
    UnitCatalog,
    DeviceSensor,
)
from jdash.config import constants


@pytest.mark.django_db
def test_create_study_form_valid_data():
    form_data = {
        'study_label': 'Study001',
        'study_duration': '30',
        'number_of_subjects': '10',
        'study_description': 'Some study',
        'is_test': False,
        'ema_checkbox': False,
        'passive_checkbox': False,
        'sensor_list': [],
        'sensor_list_limited': [],
        'recording_freq': 50,
        'active_labeling': 0,
        'survey': ''
    }
    form = CreateStudyForm(data=form_data, json_data={  # Optional, only if you want initial values
        'study_label': 'Study001',
        'study_duration': 30,
        'number_of_subjects': 10,
        'study_description': 'Some study',
    })
    if not form.is_valid():
        print("Form errors:", form.errors)
        print("Non-field errors:", form.non_field_errors())
        print("Cleaned data (if any):", getattr(form, 'cleaned_data', None))
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_survey_form_initial_json():
    post_data = {
        "title": "Stress Survey",
        "description": "Survey desc",
        "splitbyCategory": True,
        "scrolling": "V",
        "topN": 5
    }

    form = SurveyForm(data=post_data)  # simulate POST
    assert form.is_valid(), form.errors  # Print form errors if it fails


@pytest.mark.django_db
def test_answer_form_optional_fields():
    form = AnswerForm(data={
        'text': 'Answer text',
        'answerSortId': 1
    })
    assert form.is_valid()


@pytest.mark.django_db
def test_question_form_with_category_dropdown():
    categories = [{'categoryValue': 1, 'categoryTitle': 'Mood'}]

    form = QuestionForm(
        data={
            'sortId': 1,
            'title': 'How do you feel?',
            'questionType': 1,
            'category': 1,
            'frequency': 50,
            'active': True,
        },
        categories=categories,
        json_data={
            'sortId': 1,
            'title': 'How do you feel?',
            'questionType': 1,
            'category': 1
        }
    )

    assert form.is_valid(), form.errors

@pytest.mark.django_db
def test_remove_subjects_form_choices():
    receivers = ['subject1;extra', 'subject2;extra']
    form = RemoveSubjectsForm(receivers=receivers)
    choices = form.fields['subject_to_remove'].choices
    assert choices == [('subject1;extra', 'subject1'), ('subject2;extra', 'subject2')]


def test_task_form_optional():
    form = TaskForm(data={})
    assert not form.is_valid()


def test_json_upload_form_required():
    form = JSONUploadForm(data={})
    assert not form.is_valid()


def test_send_notification_form_receiver_choices():
    receivers = ['test1@example.com', 'test2@example.com']
    form = SendNotificationForm(receivers=receivers)
    choices = form.fields['receivers'].choices
    assert choices[0][0] == 'test1@example.com'
    assert choices[1][0] == 'test2@example.com'


def test_delete_subject_form_fields():
    form = DeleteSubjectForm(data={
        'subjectId': 'abc123',
        'email': 'user@example.com',
        'reason': 'Testing'
    })
    assert form.is_valid()


def test_contact_us_form_validation():
    form = ContactUsForm(data={
        'fullname': 'Test User',
        'email': 'test@example.com',
        'message': 'Help needed'
    })
    assert form.is_valid()


def test_date_form_valid_dates():
    form = DateForm(data={
        'start': '2024-01-01',
        'end': '2024-12-31'
    })
    assert form.is_valid()


@pytest.mark.django_db
def test_device_sensor_admin_form_filters_catalogs_by_instance_sensor():
    device = DeviceCatalog.objects.create(name="Garmin")
    sensor_a = SensorCatalog.objects.create(code="hr", label="Heart Rate")
    sensor_b = SensorCatalog.objects.create(code="tmp", label="Temperature")
    sampling_a = SamplingRateCatalog.objects.create(sensor=sensor_a, value="1Hz")
    SamplingRateCatalog.objects.create(sensor=sensor_b, value="5Hz")
    unit_a = UnitCatalog.objects.create(sensor=sensor_a, value="bpm")
    UnitCatalog.objects.create(sensor=sensor_b, value="celsius")
    device_sensor = DeviceSensor.objects.create(
        device=device,
        sensor=sensor_a,
        default_sampling_rate=sampling_a,
        default_unit=unit_a,
    )

    form = DeviceSensorAdminForm(instance=device_sensor)

    assert list(form.fields["default_sampling_rate"].queryset) == [sampling_a]
    assert list(form.fields["default_unit"].queryset) == [unit_a]


@pytest.mark.django_db
def test_device_sensor_admin_form_rejects_sampling_and_unit_from_other_sensor():
    device = DeviceCatalog.objects.create(name="Garmin")
    sensor_a = SensorCatalog.objects.create(code="hr", label="Heart Rate")
    sensor_b = SensorCatalog.objects.create(code="tmp", label="Temperature")
    sampling_a = SamplingRateCatalog.objects.create(sensor=sensor_a, value="1Hz")
    sampling_b = SamplingRateCatalog.objects.create(sensor=sensor_b, value="5Hz")
    unit_a = UnitCatalog.objects.create(sensor=sensor_a, value="bpm")
    unit_b = UnitCatalog.objects.create(sensor=sensor_b, value="celsius")

    form = DeviceSensorAdminForm(data={
        "device": device.id,
        "sensor": sensor_a.id,
        "default_sampling_rate": sampling_b.id,
        "default_unit": unit_b.id,
    })

    assert not form.is_valid()
    assert "default_sampling_rate" in form.errors
    assert "default_unit" in form.errors

    valid_form = DeviceSensorAdminForm(data={
        "device": device.id,
        "sensor": sensor_a.id,
        "default_sampling_rate": sampling_a.id,
        "default_unit": unit_a.id,
    })

    assert valid_form.is_valid(), valid_form.errors
